"""Kolejność etapów, katalog uruchomienia i kontrola spójności liczników (ADR-000 §4, ADR-004)."""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

from map_qa.model import CHECK_ORDER


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
