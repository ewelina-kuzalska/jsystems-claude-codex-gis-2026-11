"""Eksport zadań do GeoJSON (RFC 7946) i CSV (ADR-004 §3.6, D-401, D-403).

Własna serializacja przez `json`/`csv`: stała kolejność pól, 7 miejsc po przecinku, `\\n`.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry

from map_qa.crs import geometry_to_2180, to_4326_xy
from map_qa.model import Task

PRECISION = 7
PROPERTIES = [
    "task_id",
    "check",
    "reason_code",
    "resolved_by",
    "osm_id",
    "segment_id",
    "rule_index",
    "direction",
    "photo_id",
    "photo_url",
    "photo_author",
    "photo_license",
    "osm_raw",
    "osm_normalized",
    "overture_raw",
    "overture_normalized",
    "distance_m",
    "uncertain_link",
    "file_flags",
    "own_flags",
    "tier1_model",
    "tier1_answer",
    "tier1_probability",
    "tier2_answer",
    "tier2_confidence",
    "mapillary_value",
    "description_pl",
]


def attribution_text(overture_release: str = "") -> str:
    release = f", wydanie {overture_release}" if overture_release else ""
    return (
        "© OpenStreetMap contributors (ODbL 1.0); "
        f"© Overture Maps Foundation{release} (ODbL 1.0); "
        "Zdjęcia: CC BY-SA 4.0, autorzy przy każdym zdjęciu"
    )


def properties(task: Task) -> dict:
    c = task.candidate
    values = {
        "task_id": task.task_id,
        "file_flags": ";".join(c.file_flags),
        "own_flags": ";".join(c.own_flags),
        "resolved_by": c.resolved_by or None,
        "segment_id": c.segment_id or None,
        "direction": c.direction or None,
    }
    return {k: values[k] if k in values else getattr(c, k) for k in PROPERTIES}


def _round_coords(obj):
    if isinstance(obj, (list, tuple)):
        if obj and isinstance(obj[0], (int, float)):
            return [round(float(v), PRECISION) for v in obj]
        return [_round_coords(o) for o in obj]
    return obj


def geometry_json(geom: BaseGeometry | None) -> dict | None:
    if geom is None:
        return None
    m = mapping(geom)
    return {"type": m["type"], "coordinates": _round_coords(m["coordinates"])}


def representative_lonlat(geom: BaseGeometry | None) -> tuple[float | None, float | None]:
    """Punkt: jego współrzędne. Linia: punkt w połowie długości (liczony w EPSG:2180)."""
    if geom is None:
        return None, None
    if geom.geom_type == "Point":
        return round(geom.x, PRECISION), round(geom.y, PRECISION)
    mid = geometry_to_2180(geom).interpolate(0.5, normalized=True)
    lon, lat = to_4326_xy(mid.x, mid.y)
    return round(lon, PRECISION), round(lat, PRECISION)


def export_geojson(tasks: list[Task], metadata: dict, out_path: Path) -> None:
    meta = {
        "osm_extract_date": metadata.get("osm_extract_date"),
        "overture_release": metadata.get("overture_release"),
        "snapshot_created_at": metadata.get("snapshot_created_at"),
        "attribution": attribution_text(metadata.get("overture_release", "")),
        "threshold": metadata.get("threshold"),
        "contract_versions": metadata.get("contract_versions", {}),
    }
    doc = {
        "type": "FeatureCollection",
        "metadata": meta,
        "features": [
            {
                "type": "Feature",
                "geometry": geometry_json(t.candidate.geometry),
                "properties": properties(t),
            }
            for t in tasks
        ],
    }
    text = json.dumps(doc, ensure_ascii=False, indent=1) + "\n"
    Path(out_path).write_text(text, encoding="utf-8", newline="\n")


def _csv_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def export_csv(tasks: list[Task], out_path: Path, overture_release: str = "") -> None:
    header = [*PROPERTIES, "lon", "lat", "attribution"]
    attribution = attribution_text(overture_release)
    with Path(out_path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(header)
        for t in tasks:
            props = properties(t)
            lon, lat = representative_lonlat(t.candidate.geometry)
            writer.writerow(
                [_csv_value(props[k]) for k in PROPERTIES]
                + [_csv_value(lon), _csv_value(lat), attribution]
            )
