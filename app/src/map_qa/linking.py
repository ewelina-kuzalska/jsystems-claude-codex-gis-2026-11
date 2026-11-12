"""Kontrola dopasowań zdjęcie–droga i flagi niepewności (ADR-002 §3.2, §3.3, D-06, D-203).

Linki z pliku zostają kandydatami; rozjazd kontroli dodaje flagę `link_recheck_mismatch`
i nigdy nie podmienia drogi.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from map_qa.crs import angle_diff, angle_diffs, local_bearing, to_2180_xy
from map_qa.model import SignRoadContext
from map_qa.normalize.osm import load_tags

RADIUS_M = 25.0
TOL_DISTANCE_M = 0.5
TOL_BEARING_DEG = 5.0
MISSING_HEADING_PENALTY_M = 5.0
RESTRICTED_ACCESS = {"private", "no", "customers", "delivery", "permit"}


@dataclass
class OsmIndex:
    """Drogi OSM w EPSG:2180 z indeksem przestrzennym i tagami."""

    lines: gpd.GeoSeries  # index = osm_id, CRS 2180
    tags: dict[int, dict[str, str]] = field(default_factory=dict)

    @classmethod
    def build(cls, osm_4326: gpd.GeoDataFrame, osm_2180_geoms: gpd.GeoSeries) -> OsmIndex:
        lines = gpd.GeoSeries(
            osm_2180_geoms.values, index=osm_4326["osm_id"].astype("int64").values, crs=2180
        )
        tags = {
            int(i): load_tags(t) for i, t in zip(osm_4326["osm_id"], osm_4326["tags"], strict=True)
        }
        return cls(lines=lines, tags=tags)

    def within(self, point: Point, radius: float = RADIUS_M) -> list[int]:
        pos = self.lines.sindex.query(point, predicate="dwithin", distance=radius)
        return sorted(int(self.lines.index[p]) for p in pos)


def _is_grade_separated(tags: dict[str, str]) -> bool:
    for key in ("bridge", "tunnel"):
        value = tags.get(key, "").strip()
        if value and value != "no":
            return True
    layer = tags.get("layer", "").strip()
    if layer:
        try:
            return float(layer) != 0.0
        except ValueError:
            return True
    return False


def own_flags_for(osm_way_id: int | None, nearby: list[int], index: OsmIndex) -> list[str]:
    flags: list[str] = []
    tags = index.tags.get(osm_way_id, {}) if osm_way_id is not None else {}
    if tags.get("access", "").strip() in RESTRICTED_ACCESS:
        flags.append("restricted_access")
    ids = set(nearby) | ({osm_way_id} if osm_way_id is not None else set())
    if any(_is_grade_separated(index.tags.get(i, {})) for i in ids):
        flags.append("grade_separated_nearby")
    return flags


def _opt(value: str) -> float | None:
    value = (value or "").strip()
    return None if value == "" else float(value)


def recheck_links(links: pd.DataFrame, photos: pd.DataFrame, index: OsmIndex) -> pd.DataFrame:
    """Dodaje do linków pola kontroli i flagi własne (ADR-002 §4)."""
    by_photo = photos.set_index("photo_id")
    rows = []
    for link in links.itertuples(index=False):
        photo = by_photo.loc[link.photo_id]
        heading = photo["heading"]
        point = Point(*to_2180_xy(float(photo["longitude"]), float(photo["latitude"])))
        nearby = index.within(point)
        way_id = int(link.osm_way_id) if link.osm_way_id else None
        rec = {
            "recheck_distance_m": None,
            "recheck_bearing": None,
            "recheck_candidate_count": len(nearby),
            "recheck_top_osm_id": None,
            "directed_diff": None,
            "undirected_diff": None,
            "recheck_status": "not_checked",
            "camera_x": point.x,
            "camera_y": point.y,
        }
        own: list[str] = []
        if way_id is None:
            if nearby:
                own.append("link_recheck_mismatch")
        else:
            ranked = []
            for cand in nearby:
                line = index.lines.loc[cand]
                dist = float(line.distance(point))
                bearing = local_bearing(line, point)
                _, undirected = angle_diffs(heading, bearing)
                penalty = MISSING_HEADING_PENALTY_M if undirected is None else undirected / 9.0
                ranked.append((dist + penalty, dist, cand))
            ranked.sort()
            line = index.lines.loc[way_id]
            rec["recheck_distance_m"] = float(line.distance(point))
            rec["recheck_bearing"] = local_bearing(line, point)
            rec["directed_diff"], rec["undirected_diff"] = angle_diffs(
                heading, rec["recheck_bearing"]
            )
            rec["recheck_top_osm_id"] = ranked[0][2] if ranked else None
            mismatch = (
                abs(rec["recheck_distance_m"] - float(link.distance_m)) > TOL_DISTANCE_M
                or angle_diff(rec["recheck_bearing"], float(link.way_bearing)) > TOL_BEARING_DEG
                or rec["recheck_candidate_count"] != int(link.osm_candidate_count or 0)
                or rec["recheck_top_osm_id"] != way_id
            )
            rec["recheck_status"] = "mismatch" if mismatch else "ok"
            if mismatch:
                own.append("link_recheck_mismatch")
        own.extend(own_flags_for(way_id, nearby, index))
        rec["own_flags"] = tuple(
            f
            for f in ("link_recheck_mismatch", "restricted_access", "grade_separated_nearby")
            if f in own
        )
        rows.append(rec)
    out = links.reset_index(drop=True).copy()
    for col in rows[0] if rows else ():
        # dtype object: brak (None) nie może stać się NaN ani 0 (AC-18)
        out[col] = pd.Series([r[col] for r in rows], dtype=object).values
    out["uncertain"] = [
        bool(f or o) for f, o in zip(out["file_flags"], out["own_flags"], strict=True)
    ]
    return out


# --- Kierunek OSM dla znaku C4 (ADR-002 §3.4, D-204) ----------------------------------

SNAPSHOT_SOURCE = "osm_roads.parquet"
SPEED_COLUMNS = {
    "maxspeed": "maxspeed",
    "maxspeed_forward": "maxspeed:forward",
    "maxspeed_backward": "maxspeed:backward",
    "maxspeed_conditional": "maxspeed:conditional",
}


def _text(row, key: str) -> str:
    value = row.get(key, "") if hasattr(row, "get") else ""
    return "" if value is None else str(value).strip()


def sign_road_context(sign, nearest_row, index: OsmIndex) -> SignRoadContext:
    """Wartość OSM do porównania ze znakiem; `outside_snapshot` dla way spoza snapshotu."""
    from map_qa.normalize.osm import parse_maxspeed

    photo_id = _text(sign, "photo_id")
    way_text = _text(nearest_row, "osm_way_id")
    way_id = int(way_text) if way_text else None
    raw = {
        tag: _text(nearest_row, col)
        for col, tag in SPEED_COLUMNS.items()
        if _text(nearest_row, col)
    }
    flags = [f for f in _text(nearest_row, "match_flags").split(";") if f]
    oneway = _text(nearest_row, "oneway")
    from_api = _text(nearest_row, "source") != SNAPSHOT_SOURCE
    missing_way = way_id is None or way_id not in index.lines.index
    if from_api or missing_way:
        if from_api != missing_way:
            flags.append("nearest_osm_source_inconsistent")  # błąd danych, raportowany
        return SignRoadContext(
            photo_id, way_id, raw, "unknown", None, "outside_snapshot", None, tuple(flags), oneway
        )

    directed = None
    compass = _text(sign, "compass_angle")
    if compass:
        point = Point(*to_2180_xy(float(_text(sign, "longitude")), float(_text(sign, "latitude"))))
        directed, _ = angle_diffs(float(compass), local_bearing(index.lines.loc[way_id], point))

    if "maxspeed:forward" in raw or "maxspeed:backward" in raw:
        if directed is None or 45.0 < directed < 135.0:
            return SignRoadContext(
                photo_id,
                way_id,
                raw,
                "unknown",
                None,
                "direction_unknown",
                directed,
                tuple(flags),
                oneway,
            )
        direction = "forward" if directed <= 45.0 else "backward"
        value_raw = raw.get(f"maxspeed:{direction}") or raw.get("maxspeed", "")
    else:
        direction = "both"
        value_raw = raw.get("maxspeed", "")

    parsed = parse_maxspeed(value_raw)
    if parsed is None:
        status, value = "missing", None
    elif parsed[0] != "numeric":
        status, value = "not_numeric", None
    else:
        status, value = "ok", parsed[1]
    return SignRoadContext(
        photo_id, way_id, raw, direction, value, status, directed, tuple(flags), oneway
    )
