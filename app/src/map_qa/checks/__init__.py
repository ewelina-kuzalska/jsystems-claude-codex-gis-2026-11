"""Kontrole C1–C4 (ADR-001 §3.5–3.6, ADR-002 §3.3, ADR-003 §3.8)."""

from __future__ import annotations

import pandas as pd

UNCERTAIN_NOTE = (
    " Dopasowanie zdjęcia do drogi jest niepewne (flagi: {flags}), więc kandydat może być "
    "fałszywym alarmem."
)


def photos_by_link(links: pd.DataFrame) -> dict[int, tuple[str, ...]]:
    """osm_way_id → posortowane photo_id zdjęć z linkiem do tej drogi."""
    out: dict[int, list[str]] = {}
    if links is None or links.empty:
        return {}
    for pid, way in zip(links["photo_id"], links["osm_way_id"], strict=True):
        if way:
            out.setdefault(int(way), []).append(pid)
    return {k: tuple(sorted(v)) for k, v in out.items()}


def apply_photo(candidate, photos: pd.DataFrame | None) -> None:
    """Uzupełnia link, autora i licencję pierwszego zdjęcia kandydata (AC-32, AC-33)."""
    if photos is None or not candidate.photo_id:
        return
    match = photos[photos["photo_id"] == candidate.photo_id]
    if match.empty:
        return
    row = match.iloc[0]
    candidate.photo_url = str(row.get("source_url", "") or row.get("url", ""))
    candidate.photo_author = str(row.get("author", ""))
    candidate.photo_license = str(row.get("license", ""))
