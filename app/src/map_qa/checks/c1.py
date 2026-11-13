"""C1: brakujące atrybuty (AC-08–AC-10, ADR-001 §3.5)."""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from map_qa.checks import apply_photo, photos_by_link
from map_qa.model import C1_ATTRIBUTES, Candidate
from map_qa.normalize.osm import has_speed, load_tags

ATTR_LABEL_PL = {
    "maxspeed": "ograniczenia prędkości (maxspeed)",
    "surface": "nawierzchni (surface)",
    "lanes": "liczby pasów (lanes)",
    "lit": "oświetlenia (lit)",
}


def _missing(tags: dict[str, str], tags_raw: str, attr: str) -> bool:
    if attr == "maxspeed":
        return not has_speed(tags_raw)
    return not tags.get(attr, "").strip()


def check_missing(
    osm: gpd.GeoDataFrame,
    overture: gpd.GeoDataFrame,
    links: pd.DataFrame,
    photos: pd.DataFrame | None = None,
) -> tuple[dict, list[Candidate]]:
    """(podsumowanie C1, kandydaci C1). Zadania tylko dla dróg ze zdjęciem (AC-10)."""
    with_photo = photos_by_link(links)
    per_class: dict[str, dict] = {}
    candidates: list[Candidate] = []
    for osm_id, highway, tags_raw, geom in zip(
        osm["osm_id"], osm["highway"], osm["tags"], osm.geometry, strict=True
    ):
        tags = load_tags(tags_raw)
        hw = highway or "(brak)"
        row = per_class.setdefault(
            hw, {"highway": hw, "total": 0, "missing": dict.fromkeys(C1_ATTRIBUTES, 0)}
        )
        row["total"] += 1
        for attr in C1_ATTRIBUTES:
            if not _missing(tags, tags_raw, attr):
                continue
            row["missing"][attr] += 1
            pids = with_photo.get(int(osm_id))
            if not pids:
                continue
            cand = Candidate(
                check="C1",
                reason_code=f"missing_{attr}",
                osm_id=int(osm_id),
                photo_id=pids[0],
                photo_ids=pids,
                osm_raw=tags_raw,
                description_pl=(
                    f"Droga OSM {int(osm_id)} ({hw}) nie ma informacji o "
                    f"{ATTR_LABEL_PL[attr]}. Wymaga sprawdzenia na zdjęciu "
                    f"({len(pids)} zdj.). Brak tagu nie dowodzi błędu mapy."
                ),
                geometry=geom,
            )
            apply_photo(cand, photos)
            candidates.append(cand)

    ovt: dict[str, dict] = {}
    if overture.empty:
        overture = overture.reindex(columns=["class", "speed_limits", "road_surface"])
    for cls, speed, surface in zip(
        overture["class"], overture["speed_limits"], overture["road_surface"], strict=True
    ):
        key = cls if isinstance(cls, str) and cls else "(brak)"
        row = ovt.setdefault(
            key, {"class": key, "total": 0, "missing_speed": 0, "missing_surface": 0}
        )
        row["total"] += 1
        row["missing_speed"] += int(not speed)
        row["missing_surface"] += int(not surface)

    summary = {
        "osm": sorted(per_class.values(), key=lambda r: (-r["total"], r["highway"])),
        "overture": sorted(ovt.values(), key=lambda r: (-r["total"], r["class"])),
        "osm_total": int(len(osm)),
        "overture_total": int(len(overture)),
        "exported": len(candidates),
    }
    return summary, candidates
