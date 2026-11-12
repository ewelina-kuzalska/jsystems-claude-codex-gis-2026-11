"""Kolejność etapów, katalog uruchomienia i kontrola spójności liczników (ADR-000 §4, ADR-004)."""

from __future__ import annotations

import csv
import io
import json
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from map_qa.checks.c1 import check_missing
from map_qa.checks.c2 import check_discrepancy
from map_qa.checks.c3 import check_uncertain, label_uncertain
from map_qa.config import RunConfig
from map_qa.crs import to_2180
from map_qa.export import export_csv, export_geojson
from map_qa.inputs import load_links, load_osm, load_overture_raw, load_photos, verify_snapshot
from map_qa.linking import OsmIndex, recheck_links
from map_qa.model import CHECK_ORDER, NotComparable, SignResolution
from map_qa.normalize.surface import surface_mapping
from map_qa.render import ReportInput, build_context, prepare_images, render_html, render_markdown
from map_qa.tasks import build_tasks, count_by_check, count_by_reason

CONTRACT_VERSIONS = {"task_id": "V1", "export": "V1"}


class RunDirError(Exception):
    """Błąd zapisu wyników (kod wyjścia 3)."""

    exit_code = 3


class CountMismatch(Exception):
    """Niezgodność liczników między wynikami (kod wyjścia 4, TAC-05)."""

    exit_code = 4

    def __init__(self, check: str, sources: dict[str, int], expected: int) -> None:
        self.check = check
        self.sources = sources
        self.expected = expected
        found = ", ".join(f"{k}={v}" for k, v in sources.items())
        super().__init__(f"Niezgodne liczniki {check}: summary.json={expected}, {found}")


def prepare_run_dir(output_dir: Path, run_id: str) -> Path:
    """Tworzy `<run_id>.partial/`. Istniejący katalog nigdy nie jest nadpisywany."""
    output_dir = Path(output_dir)
    final = output_dir / run_id
    partial = output_dir / f"{run_id}.partial"
    if final.exists() or partial.exists():
        raise RunDirError(f"Katalog wyników już istnieje: {final}")
    try:
        partial.mkdir(parents=True)
    except OSError as exc:
        raise RunDirError(f"Nie można utworzyć katalogu wyników {partial}: {exc}") from exc
    return partial


def finalize_run_dir(partial: Path) -> Path:
    final = partial.with_name(partial.name.removesuffix(".partial"))
    try:
        partial.rename(final)
    except OSError as exc:
        raise RunDirError(f"Nie można zmienić nazwy {partial} na {final}: {exc}") from exc
    return final


def write_summary(run_dir: Path, summary: dict) -> None:
    text = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=False, default=str)
    (Path(run_dir) / "summary.json").write_text(text + "\n", encoding="utf-8", newline="\n")


def _count(values) -> dict[str, int]:
    counts = dict.fromkeys(CHECK_ORDER, 0)
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    return counts


_HTML_COUNT = re.compile(r'data-check="([^"]+)" data-count="(\d+)"')
_MD_ROW = re.compile(r"^\| (C1|C2|C3|C4|C4-manual) \| (\d+) \|", re.M)


def read_counts(run_dir: Path) -> dict[str, dict[str, int]]:
    """Liczniki per kontrola odczytane z czterech plików wyników."""
    run_dir = Path(run_dir)
    geo = json.loads((run_dir / "tasks.geojson").read_text(encoding="utf-8"))
    rows = csv.DictReader(io.StringIO((run_dir / "tasks.csv").read_text(encoding="utf-8-sig")))
    html = (run_dir / "report.html").read_text(encoding="utf-8")
    md = (run_dir / "report.md").read_text(encoding="utf-8")
    md_block = md.split("<!-- summary-counts -->", 1)[-1].split("<!-- /summary-counts -->", 1)[0]
    return {
        "tasks.geojson": _count(f["properties"]["check"] for f in geo["features"]),
        "tasks.csv": _count(r["check"] for r in rows),
        "report.html": {c: int(n) for c, n in _HTML_COUNT.findall(html)},
        "report.md": {c: int(n) for c, n in _MD_ROW.findall(md_block)},
    }


def verify_counts(run_dir: Path, expected: dict[str, int]) -> None:
    """Porównuje liczniki z `summary.json` z czterema wynikami; rzuca `CountMismatch`."""
    found = read_counts(run_dir)
    for check in CHECK_ORDER:
        per_source = {name: counts.get(check, -1) for name, counts in found.items()}
        if any(v != expected.get(check, 0) for v in per_source.values()):
            bad = {k: v for k, v in per_source.items() if v != expected.get(check, 0)}
            raise CountMismatch(check, bad, expected.get(check, 0))


# --- Pełny przebieg (PRD 4.1) -------------------------------------------------------


@dataclass
class C4Outcome:
    candidates: list = field(default_factory=list)
    not_comparable: list = field(default_factory=list)
    block: dict = field(default_factory=dict)
    processed: int = 0


@dataclass
class RunResult:
    run_dir: Path
    summary: dict
    tasks: list


def c4_not_run(reason: str) -> C4Outcome:
    return C4Outcome(block={"status": "not_run", "reason": reason})


def _c4_stage(cfg, snapshot, data, confirm, echo) -> C4Outcome:
    """C4 z planem, potwierdzeniem, budżetem i eskalacją (PRD 4.2–4.3, ADR-003)."""
    from map_qa import ai_client
    from map_qa.cache import AiCache
    from map_qa.checks.c4 import compare_signs
    from map_qa.inputs import load_signs
    from map_qa.linking import sign_road_context
    from map_qa.signs.crop_check import check_crop
    from map_qa.signs.evaluate import evaluate
    from map_qa.signs.resolve import CropItem, plan_sign_run, resolve_signs, select_sample

    if not cfg.with_signs:
        return c4_not_run("C4 nie zostało włączone (brak --with-signs).")
    signs, nearest = load_signs(snapshot)
    crops_dir = Path(cfg.input_dir) / "signs" / "crops"
    items = []
    for row in signs.itertuples(index=False):
        check = check_crop(crops_dir / f"{row.photo_id}.jpg", row.crop_sha256)
        items.append(CropItem(row.photo_id, row.crop_sha256, check.data, check.reason))
    cache = AiCache(cfg.cache_dir)
    client = ai_client.OpenRouterClient()
    try:
        reader = ai_client.SignReader(client, cfg.tier1_model_id)
        sample, not_run_items = select_sample(items, cache, reader, cfg.new_crop_budget)
        plan = plan_sign_run(
            sample,
            cache,
            reader,
            threshold=cfg.threshold,
            limit=cfg.max_requests,
            cost_limit=cfg.max_cost_usd,
            not_run=len(not_run_items),
        )
        echo(
            f"Plan C4 ({cfg.tier1_model_id} → {ai_client.TIER2_MODEL}): wycinki w próbce "
            f"{plan.sample_size} z {len(items)} (w cache {plan.cached_tier1}, odrzucone przed "
            f"wysłaniem {plan.invalid}); nowe żądania kroku 1: {plan.new_tier1}; najgorszy "
            f"przypadek kroku 2: {plan.worst_tier2}; próg {cfg.threshold:.2f}; limit żądań "
            f"{cfg.max_requests}; limit kosztu {cfg.max_cost_usd:.2f} USD."
        )
        if not confirm(plan):
            return c4_not_run("Brak potwierdzenia planu żądań (odpowiedź inna niż „tak”).")
        if not ai_client.RESPONSE_CONTRACT_VERIFIED:
            return c4_not_run(
                "contract_unverified: kontrakt odpowiedzi nie jest zweryfikowany na zapisach; "
                "nie wysłano żadnego żądania."
            )
        if not ai_client.api_key_present():
            return c4_not_run("Brak klucza OPENROUTER_API_KEY — nie wysłano żadnego żądania.")
        budget = ai_client.RequestBudget(limit=cfg.max_requests, cost_limit_usd=cfg.max_cost_usd)
        resolutions = resolve_signs(sample, budget, cache, reader, cfg.threshold)
    finally:
        client.close()
    resolutions += [SignResolution(i.photo_id, "not_run") for i in not_run_items]
    by_state = Counter(r.resolved_by for r in resolutions)
    assert sum(by_state.values()) == len(items)  # AC-22e: dokładnie jeden stan na wycinek

    sign_rows = {r["photo_id"]: r for r in signs.to_dict("records")}
    near_rows = {r["photo_id"]: r for r in nearest.to_dict("records")}
    processed = [r for r in resolutions if r.resolved_by != "not_run"]
    contexts = {
        r.photo_id: sign_road_context(sign_rows[r.photo_id], near_rows[r.photo_id], data["index"])
        for r in processed
    }
    osm_tags_raw = dict(zip(data["osm"]["osm_id"].astype(int), data["osm"]["tags"], strict=True))
    candidates, not_comparable = compare_signs(processed, contexts, signs, nearest, osm_tags_raw)
    readings = [
        {
            "photo_id": r.photo_id,
            "resolved_by": r.resolved_by,
            "final": r.final_value,
            "tier1": (r.tier1.answer or "") if r.tier1 else "",
            "tier1_p": r.tier1.probability if r.tier1 else None,
            "tier2": (r.tier2.answer or "") if r.tier2 else "",
            "tier2_p": r.tier2.probability if r.tier2 else None,
            "status": r.manual_reason or "",
            "detail": r.detail,
        }
        for r in processed
    ]
    metrics = evaluate(resolutions, Path(cfg.input_dir) / "signs" / "labels.csv")
    cached = Counter(
        rd.tier
        for r in processed
        for rd in (r.tier1, r.tier2)
        if rd is not None and rd.request_outcome == "cached"
    )
    for acc in metrics["accuracy"]:
        model = cfg.tier1_model_id if acc["key"] == "tier1" else ai_client.TIER2_MODEL
        if acc["key"] != "all":
            acc["label"] = f"{acc['label']} ({model})"
    cost = f"{budget.cost_used_usd:.6f}".replace(".", ",")
    if budget.cost_unknown:
        cost += " (część odpowiedzi bez kosztu: cost_unknown)"
    if budget.stopped_reason == "none":
        stop = "nie zatrzymano"
    else:
        stop = f"{budget.stopped_reason} przy {budget.stopped_at_photo_id}"
        if budget.last_error:
            stop += f" ({budget.last_error[:200]})"
    final, total = metrics["coverage"]
    raw_ok, raw_n = metrics["raw_tier1"]
    block = {
        "status": "run",
        "tier1_model": cfg.tier1_model_id,
        "tier2_model": ai_client.TIER2_MODEL,
        "threshold": cfg.threshold,
        "limit": cfg.max_requests,
        "cost_limit": cfg.max_cost_usd,
        "requests": {
            "tier1": budget.used_per_tier[1],
            "tier2": budget.used_per_tier[2],
            "total": budget.used,
        },
        "cached": {"tier1": cached.get(1, 0), "tier2": cached.get(2, 0)},
        "cost_usd": round(budget.cost_used_usd, 8),
        "cost_unknown": budget.cost_unknown,
        "cost_text": cost,
        "processed": len(processed),
        "sample_total": len(items),
        "resolved": {
            k: by_state.get(k, 0)
            for k in ("decision_model", "general_llm", "human_pending", "not_run")
        },
        "stop_reason": budget.stopped_reason,
        "stop_text": stop,
        "accuracy": metrics["accuracy"],
        "raw_tier1": list(metrics["raw_tier1"]),
        "coverage": list(metrics["coverage"]),
        "manual_by_reason": metrics["manual_by_reason"],
        "readings": readings,
        "uncertain_labels": metrics["uncertain_labels"],
        "label_unparsable": metrics["label_unparsable"],
        "evaluation_note": (
            f"Pokrycie: {final} ostatecznych z {total} przetworzonych. Surowa zgodność kroku 1 "
            f"przed progiem: {raw_ok} / {raw_n}. Mianownik obejmuje tylko etykiety „certain”; "
            f"etykiety „uncertain”: {metrics['uncertain_labels']}, nieczytelne kody etykiet "
            f"(label_unparsable): {metrics['label_unparsable']}. Kolejka ręczna nie jest liczona "
            "jako poprawna ani błędna."
        ),
    }
    echo(
        f"C4: żądania krok 1 {budget.used_per_tier[1]} / krok 2 {budget.used_per_tier[2]} "
        f"(razem {budget.used} / limit {cfg.max_requests}), z cache {cached.get(1, 0)} + "
        f"{cached.get(2, 0)}; decision_model {block['resolved']['decision_model']}, "
        f"general_llm {block['resolved']['general_llm']}, human_pending "
        f"{block['resolved']['human_pending']}, not_run {block['resolved']['not_run']}."
    )
    if budget.stopped_reason != "none":
        echo(f"C4: płatna pętla zatrzymana — {stop}.")
    return C4Outcome(candidates, not_comparable, block, len(processed))


def _unknown_surface(osm_tags: list[dict], overture_values: list) -> list[tuple[str, int]]:
    known = {(s, v) for s, v, _ in surface_mapping()}
    counter: Counter = Counter()
    for tags in osm_tags:
        value = tags.get("surface", "").strip()
        if value and ("osm", value) not in known:
            counter[f"osm: {value}"] += 1
    for value in overture_values:
        if value and ("overture", value) not in known:
            counter[f"overture: {value}"] += 1
    return sorted(counter.items())


NC_COLUMNS = [
    "check",
    "reason_code",
    "attribute",
    "direction",
    "osm_id",
    "segment_id",
    "rule_index",
    "photo_id",
    "osm_raw",
    "overture_raw",
]


def _write_not_comparable(path: Path, rows: list[NotComparable]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(NC_COLUMNS)
        for n in rows:
            writer.writerow(["" if getattr(n, c) is None else getattr(n, c) for c in NC_COLUMNS])


def run(
    cfg: RunConfig,
    started: datetime | None = None,
    echo: Callable[[str], None] = print,
    confirm: Callable[[object], bool] = lambda plan: False,
) -> RunResult:
    """Pełny przebieg: wejścia → C1–C3 → (C4) → zadania → 4 pliki → kontrola liczników."""
    started = started or datetime.now(UTC)
    run_id = started.strftime("%Y%m%dT%H%M%SZ")

    snapshot = verify_snapshot(cfg.input_dir, with_signs=cfg.with_signs)
    echo(
        f"Snapshot OK: ekstrakt OSM {snapshot.osm_extract_date}, wydanie Overture "
        f"{snapshot.overture_release}, utworzony {snapshot.created_at}."
    )
    echo(
        "Wiersze: drogi OSM {osm_roads}, segmenty Overture {overture_segments}, zdjęcia "
        "{photos}, linki {photo_road_links} (zgodne z manifestem).".format(**snapshot.rows)
    )
    for warning in snapshot.warnings:
        echo(f"Uwaga: {warning}")

    osm = load_osm(snapshot)
    overture = load_overture_raw(snapshot)
    photos = load_photos(snapshot)
    links = load_links(snapshot)

    c1_summary, c1 = check_missing(osm, overture, links, photos)
    echo(f"C1 brakujące atrybuty: {len(c1)} zadań (drogi ze zdjęciem).")
    c2 = check_discrepancy(
        osm, overture, links, snapshot.osm_extract_date, snapshot.overture_release, photos
    )
    echo(
        f"C2 OSM vs Overture: {len(c2.candidates)} kandydatów, "
        f"{len(c2.not_comparable)} nieporównywalnych, {c2.stats['comparisons']} porównań."
    )
    index = OsmIndex.build(osm, to_2180(osm, "osm_roads.parquet").geometry)
    rechecked = recheck_links(links, photos, index)
    c3_summary, c3 = check_uncertain(rechecked, photos)
    echo(f"C3 niepewne dopasowania: {c3_summary['photos_with_flag']} zdjęć z flagą.")

    data = {"osm": osm, "index": index, "photos": photos, "links": rechecked}
    c4 = _c4_stage(cfg, snapshot, data, confirm, echo)
    if c4.block.get("status") != "run":
        echo(f"C4: nie uruchomiono — {c4.block.get('reason', '')}")

    label_uncertain(c1 + c2.candidates, rechecked)
    tasks = build_tasks(c1 + c2.candidates + c3 + c4.candidates)
    counts = count_by_check(tasks)
    not_comparable = c2.not_comparable + c4.not_comparable
    rows_checked = {
        "C1": int(len(osm)),
        "C2": c2.stats["comparisons"],
        "C3": int(len(links)),
        "C4": c4.processed,
        "C4-manual": c4.processed,
    }
    summary = {
        "run_id": run_id,
        "run_started_at": started.isoformat(timespec="seconds"),
        "snapshot": {
            "osm_extract_date": snapshot.osm_extract_date,
            "overture_release": snapshot.overture_release,
            "created_at": snapshot.created_at,
            "rows": snapshot.rows,
        },
        "threshold": cfg.threshold,
        "counts": counts,
        "counts_by_reason": [list(x) for x in count_by_reason(tasks)],
        "rows_checked": rows_checked,
        "c1": c1_summary,
        "c2": c2.stats,
        "c3": c3_summary,
        "c4": c4.block,
        "not_comparable": dict(sorted(Counter(n.reason_code for n in not_comparable).items())),
        "spatial_only": len(c2.spatial_only),
    }

    partial = prepare_run_dir(cfg.output_dir, run_id)
    try:
        filenames = dict(zip(photos["photo_id"], photos["filename"], strict=True))
        images = prepare_images(tasks, cfg.input_dir, partial, filenames)
        write_summary(partial, summary)
        meta = {
            "osm_extract_date": snapshot.osm_extract_date,
            "overture_release": snapshot.overture_release,
            "snapshot_created_at": snapshot.created_at,
            "threshold": cfg.threshold,
            "contract_versions": CONTRACT_VERSIONS,
        }
        export_geojson(tasks, meta, partial / "tasks.geojson")
        export_csv(tasks, partial / "tasks.csv", snapshot.overture_release)
        _write_not_comparable(partial / "not_comparable.csv", not_comparable)
        overture_values = [
            json.loads(r).get("value") for lst in overture["road_surface"] for r in lst
        ]
        ctx = build_context(
            ReportInput(
                snapshot=summary["snapshot"],
                run_started_at=summary["run_started_at"],
                threshold=cfg.threshold,
                tasks=tasks,
                images=images,
                rows_checked=rows_checked,
                c1=c1_summary,
                c2_stats=c2.stats,
                c3=c3_summary,
                c4=c4.block,
                not_comparable=not_comparable,
                spatial_only=c2.spatial_only,
                surface_mapping=surface_mapping(),
                unknown_surface=_unknown_surface(list(index.tags.values()), overture_values),
                warnings=list(snapshot.warnings),
            )
        )
        render_html(ctx, partial / "report.html")
        render_markdown(ctx, partial / "report.md")
    except OSError as exc:
        raise RunDirError(f"Błąd zapisu wyników w {partial}: {exc}") from exc
    try:
        verify_counts(partial, counts)
    except CountMismatch as exc:
        exc.partial = partial
        raise
    run_dir = finalize_run_dir(partial)

    echo("Kandydaci per kontrola: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    echo("Wyniki:")
    for name in ("report.md", "report.html", "tasks.geojson", "tasks.csv"):
        echo(f"  {run_dir / name}")
    return RunResult(run_dir=run_dir, summary=summary, tasks=tasks)
