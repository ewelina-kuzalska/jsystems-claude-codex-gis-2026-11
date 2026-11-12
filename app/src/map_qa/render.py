"""Raport Markdown i HTML przez Jinja2 (ADR-004 §3.3–3.5, §3.8, D-07, D-402).

HTML: autoescape + StrictUndefined, bez filtra `safe`, bez JS i zasobów zewnętrznych.
Markdown: osobne środowisko bez autoescape, każda wartość z danych przez `md_escape`.
"""

from __future__ import annotations

import shutil
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

from map_qa.export import attribution_text
from map_qa.model import CHECK_ORDER, NotComparable, Task
from map_qa.tasks import count_by_check, count_by_reason

CHECK_LABELS = {
    "C1": "Brakujące atrybuty",
    "C2": "Rozbieżności OSM–Overture",
    "C3": "Niepewne dopasowania zdjęcie–droga",
    "C4": "Odczyt znaków B-33 przez AI",
    "C4-manual": "Kolejka ręczna znaków",
}
ANCHORS = {"C1": "c1", "C2": "c2", "C3": "c3", "C4": "c4", "C4-manual": "manual"}

TEXT_CANDIDATE = "Kandydat wymaga sprawdzenia. Różnica między źródłami nie dowodzi błędu mapy."
TEXT_MODEL = "Odczyt modelu nie jest prawdą terenową."
TEXT_LABELS = "Etykiety referencyjne znaków pochodzą z odczytów modeli AI i nie są prawdą terenową."
TEXT_OUTSIDE = "Znaki spoza obszaru snapshotu są odczytywane, ale nie są porównywane z mapą."
TEXT_HEADING = (
    "Kierunek aparatu nie jest kierunkiem jazdy. Najbliższa droga nie dowodzi, że znak jej dotyczy."
)
TEXT_LINKS = "Dopasowania zdjęć do dróg są kandydatami w promieniu 25 m, nie prawdą terenową."
MANDATORY_TEXTS = (TEXT_CANDIDATE, TEXT_MODEL, TEXT_LABELS, TEXT_OUTSIDE, TEXT_HEADING, TEXT_LINKS)
MISSING_IMAGE = "Obraz niedostępny lokalnie"
NC_SAMPLE = 20


@dataclass(frozen=True)
class ImageRef:
    rel_path: str | None
    author: str = ""
    license: str = ""
    url: str = ""


def _c4_not_run(reason: str = "C4 nie zostało włączone (brak --with-signs).") -> dict:
    return {"status": "not_run", "reason": reason}


@dataclass
class ReportInput:
    snapshot: dict
    run_started_at: str
    threshold: float
    tasks: list[Task]
    images: dict[str, ImageRef]
    rows_checked: dict[str, int]
    c1: dict = field(default_factory=dict)
    c2_stats: dict = field(default_factory=dict)
    c3: dict = field(default_factory=dict)
    c4: dict = field(default_factory=_c4_not_run)
    not_comparable: list[NotComparable] = field(default_factory=list)
    not_comparable_file: str = "not_comparable.csv"
    spatial_only: list[dict] = field(default_factory=list)
    surface_mapping: list[tuple[str, str, str]] = field(default_factory=list)
    unknown_surface: list[tuple[str, int]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def md_escape(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    out = []
    for ch in text:
        if ch in "\\|*_[]<>#`":
            out.append("\\")
        out.append(ch)
    return "".join(out)


def md_url(value: object) -> str:
    """Bezpieczny adres do linku Markdown: tylko https, nawiasy i spacje zakodowane."""
    url = str(value or "")
    if not url.startswith("https://"):
        return ""
    return url.replace(" ", "%20").replace("(", "%28").replace(")", "%29").replace("<", "%3C")


def num(value: object) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, float) and not value.is_integer():
        return f"{value:.1f}".replace(".", ",")
    return f"{int(value):,}".replace(",", " ")


def prob(value: object) -> str:
    return "—" if value is None or value == "" else f"{float(value):.2f}".replace(".", ",")


def is_https(value: object) -> bool:
    return isinstance(value, str) and value.startswith("https://")


def _env(autoescape: bool) -> Environment:
    env = Environment(
        loader=PackageLoader("map_qa", "templates"),
        autoescape=select_autoescape(["html", "html.j2"]) if autoescape else False,
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters.update(md=md_escape, md_url=md_url, num=num, prob=prob)
    env.tests["https"] = is_https
    return env


def task_row(task: Task, images: dict[str, ImageRef]) -> dict:
    c = task.candidate
    image = images.get(c.photo_id, ImageRef(None))
    crop = images.get(f"{c.photo_id}#crop", ImageRef(None))
    return {
        "task_id": task.task_id,
        "check": c.check,
        "reason_code": c.reason_code,
        "osm_id": c.osm_id,
        "segment_id": c.segment_id,
        "rule_index": c.rule_index,
        "direction": c.direction,
        "photo_id": c.photo_id,
        "photo_count": len(c.photo_ids),
        "photo_url": c.photo_url,
        "photo_author": c.photo_author,
        "photo_license": c.photo_license,
        "image": image.rel_path,
        "crop": crop.rel_path,
        "osm_value": c.extra.get("osm_value_raw", ""),
        "osm_normalized": c.osm_normalized,
        "overture_raw": c.overture_raw,
        "overture_normalized": c.overture_normalized,
        "distance_m": c.distance_m,
        "uncertain_link": c.uncertain_link,
        "file_flags": ", ".join(c.file_flags),
        "own_flags": ", ".join(c.own_flags),
        "resolved_by": c.resolved_by,
        "tier1_model": c.tier1_model,
        "tier1_answer": c.tier1_answer,
        "tier1_probability": c.tier1_probability,
        "tier2_answer": c.tier2_answer,
        "tier2_confidence": c.tier2_confidence,
        "mapillary_value": c.mapillary_value,
        "osm_speed_tags": c.extra.get("osm_speed_tags", ""),
        "highway": c.extra.get("highway", ""),
        "description": c.description_pl,
    }


def build_context(ri: ReportInput) -> dict:
    counts = count_by_check(ri.tasks)
    rows = {check: [] for check in CHECK_ORDER}
    for t in ri.tasks:
        rows[t.candidate.check].append(task_row(t, ri.images))
    nc_counter = Counter((n.attribute or "", n.reason_code) for n in ri.not_comparable)
    nc_samples: dict[str, list] = {}
    for n in ri.not_comparable:
        bucket = nc_samples.setdefault(n.reason_code, [])
        if len(bucket) < NC_SAMPLE:
            bucket.append(n)
    photo_ids = {t.candidate.photo_id for t in ri.tasks if t.candidate.photo_id}
    with_thumb = sum(1 for p in photo_ids if ri.images.get(p, ImageRef(None)).rel_path)
    return {
        "meta": {
            **ri.snapshot,
            "run_started_at": ri.run_started_at,
            "threshold": ri.threshold,
            "attribution": attribution_text(ri.snapshot.get("overture_release", "")),
            "warnings": list(ri.warnings),
        },
        "checks": [
            {
                "check": check,
                "label": CHECK_LABELS[check],
                "anchor": ANCHORS[check],
                "count": counts[check],
                "rows_checked": ri.rows_checked.get(check, 0),
            }
            for check in CHECK_ORDER
        ],
        "reasons": [
            {"check": c, "reason_code": r, "count": n, "anchor": ANCHORS[c]}
            for c, r, n in count_by_reason(ri.tasks)
        ],
        "rows": rows,
        "c1": ri.c1,
        "c2_stats": ri.c2_stats,
        "c3": ri.c3,
        "c4": ri.c4,
        "nc_counts": [
            {"attribute": a, "reason_code": r, "count": n}
            for (a, r), n in sorted(nc_counter.items())
        ],
        "nc_total": len(ri.not_comparable),
        "nc_samples": sorted(nc_samples.items()),
        "nc_sample_size": NC_SAMPLE,
        "nc_file": ri.not_comparable_file,
        "spatial_only": ri.spatial_only,
        "surface_mapping": ri.surface_mapping,
        "unknown_surface": ri.unknown_surface,
        "thumbs": {"with": with_thumb, "total": len(photo_ids)},
        "texts": {
            "candidate": TEXT_CANDIDATE,
            "model": TEXT_MODEL,
            "labels": TEXT_LABELS,
            "outside": TEXT_OUTSIDE,
            "heading": TEXT_HEADING,
            "links": TEXT_LINKS,
            "missing_image": MISSING_IMAGE,
        },
    }


def render_html(ctx: dict, out_path: Path) -> None:
    html = _env(True).get_template("report.html.j2").render(**ctx)
    Path(out_path).write_text(html, encoding="utf-8", newline="\n")


def render_markdown(ctx: dict, out_path: Path) -> None:
    md = _env(False).get_template("report.md.j2").render(**ctx)
    Path(out_path).write_text(md, encoding="utf-8", newline="\n")


def find_photo(input_dir: Path, photo_id: str, filename: str | None) -> Path | None:
    """Pierwsze dostępne źródło: data/photos, offline, signs/photos (ADR-004 §3.3)."""
    name = filename or f"{photo_id}.jpg"
    for path in (
        input_dir / "data" / "photos" / name,
        input_dir / "offline" / name,
        input_dir / "signs" / "photos" / f"{photo_id}.jpg",
    ):
        if path.is_file():
            return path
    return None


def prepare_images(
    tasks: list[Task], input_dir: Path, out_dir: Path, filenames: dict[str, str]
) -> dict[str, ImageRef]:
    """Kopiuje użyte obrazy do `images/` i zwraca ścieżki względne (D-402, AC-31)."""
    images: dict[str, ImageRef] = {}
    img_dir = Path(out_dir) / "images"
    for t in tasks:
        c = t.candidate
        if not c.photo_id or c.photo_id in images:
            continue
        src = find_photo(Path(input_dir), c.photo_id, filenames.get(c.photo_id))
        rel = None
        if src is not None:
            img_dir.mkdir(parents=True, exist_ok=True)
            rel = f"images/{c.photo_id}{src.suffix.lower()}"
            shutil.copyfile(src, Path(out_dir) / rel)
        images[c.photo_id] = ImageRef(rel, c.photo_author, c.photo_license, c.photo_url)
        if c.check in ("C4", "C4-manual"):
            crop = Path(input_dir) / "signs" / "crops" / f"{c.photo_id}.jpg"
            crop_rel = None
            if crop.is_file():
                img_dir.mkdir(parents=True, exist_ok=True)
                crop_rel = f"images/{c.photo_id}_crop.jpg"
                shutil.copyfile(crop, Path(out_dir) / crop_rel)
            images[f"{c.photo_id}#crop"] = ImageRef(crop_rel)
    return images
