"""Rodziny nawierzchni z wersjonowanego CSV (ADR-001 §3.4, AC-13)."""

from __future__ import annotations

import csv
from functools import cache
from importlib.resources import files


@cache
def _mapping() -> dict[tuple[str, str], str]:
    path = files("map_qa") / "data" / "surface_families.csv"
    with path.open(encoding="utf-8") as f:
        return {(r["source"], r["value"]): r["family"] for r in csv.DictReader(f)}


def surface_family(source: str, value: str | None) -> str:
    """`paved` | `unpaved` | `unknown`. Dokładne dopasowanie, bez poprawiania literówek."""
    if value is None:
        return "unknown"
    return _mapping().get((source, value), "unknown")


def surface_mapping() -> list[tuple[str, str, str]]:
    """Pełne mapowanie do raportu, posortowane."""
    return sorted((s, v, f) for (s, v), f in _mapping().items())
