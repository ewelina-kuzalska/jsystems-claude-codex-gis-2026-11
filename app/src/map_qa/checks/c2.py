"""C2: rozbieżności OSM ↔ Overture tylko przez referencję źródła (AC-11–AC-15, ADR-001 §3.6).

Porównanie = para (way, segment) × kierunek × atrybut, gdy obie strony mają wartość.
Kierunek `both` porównujemy zawsze; `forward`/`backward` tylko wtedy, gdy któraś strona ma
wartość kierunkową (inaczej dziedziczenie `both` liczyłoby tę samą różnicę trzy razy).
Brak wartości po jednej stronie to sprawa C1 (liczone osobno jako `missing`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString

from map_qa.checks import apply_photo, photos_by_link
from map_qa.crs import angle_diff, to_2180
from map_qa.model import Candidate, NotComparable, OvertureRule
from map_qa.normalize.osm import load_tags, speed_for_direction, speed_values
from map_qa.normalize.overture import rules_for_segment, sources_for_segment
from map_qa.normalize.surface import surface_family

SAME_MAX_DEG = 45.0
REVERSED_MIN_DEG = 135.0
FLIP = {"forward": "backward", "backward": "forward"}


@dataclass
class C2Result:
    candidates: list[Candidate] = field(default_factory=list)
    not_comparable: list[NotComparable] = field(default_factory=list)
    spatial_only: list[dict] = field(default_factory=list)
    stats: dict[str, int] = field(
        default_factory=lambda: dict.fromkeys(
            ("pairs", "comparisons", "candidates", "not_comparable", "equal", "missing"), 0
        )
    )


def _azimuth(p1, p2) -> float:
    return math.degrees(math.atan2(p2[0] - p1[0], p2[1] - p1[1])) % 360.0


def geometry_direction(seg_2180: LineString, osm_2180: LineString) -> str:
    """`same` | `reversed` | `unknown` (D-104, progi 45° / 135°)."""
    a, b = seg_2180.coords[0], seg_2180.coords[-1]
    # Odcinek way OSM między punktami najbliższymi końcom segmentu, w kolejności node_ids
    ta = osm_2180.project(seg_2180.interpolate(0.0))
    tb = osm_2180.project(seg_2180.interpolate(seg_2180.length))
    pa = osm_2180.interpolate(min(ta, tb))
    pb = osm_2180.interpolate(max(ta, tb))
    if a == b or pa.distance(pb) < 1e-6:
        return "unknown"
    diff = angle_diff(_azimuth(a, b), _azimuth((pa.x, pa.y), (pb.x, pb.y)))
    if diff <= SAME_MAX_DEG:
        return "same"
    if diff >= REVERSED_MIN_DEG:
        return "reversed"
    return "unknown"


def _fmt(v: float | None) -> str:
    if v is None:
        return ""
    return str(int(v)) if float(v).is_integer() else f"{v:.1f}"


def check_discrepancy(
    osm: gpd.GeoDataFrame,
    overture: gpd.GeoDataFrame,
    links: pd.DataFrame,
    osm_extract_date: str,
    overture_release: str,
    photos: pd.DataFrame | None = None,
) -> C2Result:
    res = C2Result()
    osm_by_id = {int(i): k for k, i in enumerate(osm["osm_id"])}
    osm_tags_raw = dict(zip(osm_by_id, osm["tags"], strict=True))
    osm_geom = dict(zip(osm_by_id, osm.geometry.values, strict=True))
    way_cache: dict[int, tuple] = {}
    with_photo = photos_by_link(links)
    osm_2180 = None
    seg_2180 = None

    def osm_line(osm_id: int):
        nonlocal osm_2180
        if osm_2180 is None:
            osm_2180 = to_2180(osm, "osm_roads.parquet").geometry.values
        return osm_2180[osm_by_id[osm_id]]

    seg_pos = {sid: k for k, sid in enumerate(overture["id"])}

    def seg_line(seg_id: str):
        nonlocal seg_2180
        if seg_2180 is None:
            seg_2180 = to_2180(overture, "overture_segments.parquet").geometry.values
        return seg_2180[seg_pos[seg_id]]

    dates = f"Daty źródeł: ekstrakt OSM {osm_extract_date}, wydanie Overture {overture_release}."

    for seg in overture.itertuples(index=False):
        rules = rules_for_segment(seg.id, seg.speed_limits, seg.road_surface)
        speed_rules = [r for r in rules if r.rule_kind == "speed"]
        surface_rules = [r for r in rules if r.rule_kind == "surface"]
        has_heading = any(r.heading for r in speed_rules)
        for source in sources_for_segment(seg.id, seg.sources):
            way = source.osm_way_id
            if way is None or way not in osm_by_id:
                continue
            res.stats["pairs"] += 1
            if way not in way_cache:
                raw = osm_tags_raw[way]
                way_cache[way] = (raw, load_tags(raw), speed_values(way, raw))
            tags_raw, tags, values = way_cache[way]
            orientation = None
            directions = ["both"]
            directions += [
                d for d in ("forward", "backward") if f"maxspeed:{d}" in tags or has_heading
            ]
            base = {
                "osm_id": way,
                "segment_id": seg.id,
                "osm_tags": tags_raw,
                "geometry": osm_geom[way],
                "photos": with_photo.get(way, ()),
                "partial_source": not source.source_whole_segment,
            }
            for direction in directions:
                if direction != "both" and has_heading and orientation is None:
                    orientation = geometry_direction(seg_line(seg.id), osm_line(way))
                _compare_speed(
                    res, base, direction, values, speed_rules, orientation, dates, photos
                )
            _compare_surface(res, base, tags.get("surface"), surface_rules, dates, photos)

    if len(links):
        spatial = links[links["match_method"] == "spatial_fallback"]
        res.spatial_only = [
            {
                "photo_id": r.photo_id,
                "osm_way_id": r.osm_way_id,
                "overture_id": r.overture_id,
                "distance_m": r.distance_m,
            }
            for r in spatial.sort_values("photo_id").itertuples(index=False)
        ]
    return res


def _relevant_rules(
    rules: list[OvertureRule], direction: str, orientation: str | None
) -> tuple[list[OvertureRule], bool]:
    """Reguły Overture dla kierunku w układzie OSM. Zwraca (reguły, direction_unknown)."""
    plain = [r for r in rules if not r.heading]
    if direction == "both":
        return plain, False
    headed = [r for r in rules if r.heading]
    if headed:
        if orientation not in ("same", "reversed"):
            return [], True
        want = direction if orientation == "same" else FLIP[direction]
        match = [r for r in headed if r.heading == want]
        if match:
            return match, False
    return plain, False


def _not_comparable(res, base, attribute, direction, reason, osm_raw, ovt_rules, rule_index=None):
    res.stats["comparisons"] += 1
    res.stats["not_comparable"] += 1
    res.not_comparable.append(
        NotComparable(
            check="C2",
            reason_code=reason,
            osm_id=base["osm_id"],
            segment_id=base["segment_id"],
            rule_index=rule_index,
            direction=direction,
            attribute=attribute,
            osm_raw=osm_raw,
            overture_raw="; ".join(r.raw_json for r in ovt_rules),
        )
    )


def _candidate(
    res, base, reason, direction, rule, osm_norm, ovt_norm, osm_value_raw, text, photos, extra=None
):
    res.stats["comparisons"] += 1
    res.stats["candidates"] += 1
    pids = base["photos"]
    cand = Candidate(
        check="C2",
        reason_code=reason,
        osm_id=base["osm_id"],
        segment_id=base["segment_id"],
        rule_index=rule.rule_index,
        direction=direction,
        photo_id=pids[0] if pids else "",
        photo_ids=pids,
        osm_raw=base["osm_tags"],
        osm_normalized=osm_norm,
        overture_raw=rule.raw_json,
        overture_normalized=ovt_norm,
        description_pl=text,
        geometry=base["geometry"],
        extra={"osm_value_raw": osm_value_raw, **(extra or {})},
    )
    apply_photo(cand, photos)
    res.candidates.append(cand)


def _compare_speed(res, base, direction, values, speed_rules, orientation, dates, photos):
    sv = speed_for_direction(values, direction)
    rules, unknown = _relevant_rules(speed_rules, direction, orientation)
    osm_raw = f"{sv.tag_key}={sv.raw}" if sv else ""
    if sv is None or (not rules and not unknown):
        res.stats["missing"] += 1
        return
    if base["partial_source"]:
        return _not_comparable(res, base, "speed", direction, "partial_source", osm_raw, rules)
    if unknown:
        headed = [r for r in speed_rules if r.heading]
        return _not_comparable(res, base, "speed", direction, "direction_unknown", osm_raw, headed)
    qualifying = [r for r in rules if r.whole_segment and r.unconditional and not r.is_variable]
    if not qualifying:
        if any(r.is_variable and r.whole_segment and r.unconditional for r in rules):
            reason = "variable"
        elif any(not r.whole_segment for r in rules):
            reason = "partial_segment"
        else:
            reason = "conditional"
        return _not_comparable(res, base, "speed", direction, reason, osm_raw, rules)
    if len(qualifying) > 1:
        return _not_comparable(res, base, "speed", direction, "multiple_rules", osm_raw, qualifying)
    rule = qualifying[0]
    if sv.status != "numeric" or rule.value_kmh is None:
        return _not_comparable(
            res, base, "speed", direction, "not_numeric", osm_raw, [rule], rule.rule_index
        )
    if round(sv.value_kmh, 1) == round(rule.value_kmh, 1):
        res.stats["comparisons"] += 1
        res.stats["equal"] += 1
        return
    cond = any(v.tag_key == "maxspeed:conditional" for v in values)
    text = (
        f"Ograniczenie prędkości ({direction}) różni się między źródłami: OSM {osm_raw} "
        f"({_fmt(sv.value_kmh)} km/h), Overture {_fmt(rule.value_kmh)} km/h "
        f"(reguła {rule.rule_index}). Kandydat wymaga sprawdzenia. Różnica między źródłami "
        f"nie dowodzi błędu mapy; źródła mogą mieć różny wiek. {dates}"
    )
    if cond:
        text += " Droga OSM ma też ograniczenie warunkowe (maxspeed:conditional)."
    _candidate(
        res,
        base,
        "speed_mismatch",
        direction,
        rule,
        _fmt(sv.value_kmh),
        _fmt(rule.value_kmh),
        osm_raw,
        text,
        photos,
        {"osm_conditional_present": cond},
    )


def _compare_surface(res, base, osm_surface, surface_rules, dates, photos):
    osm_surface = (osm_surface or "").strip()
    if not osm_surface or not surface_rules:
        res.stats["missing"] += 1
        return
    osm_raw = f"surface={osm_surface}"
    if base["partial_source"]:
        return _not_comparable(res, base, "surface", "", "partial_source", osm_raw, surface_rules)
    whole = [r for r in surface_rules if r.whole_segment]
    if not whole:
        return _not_comparable(res, base, "surface", "", "partial_segment", osm_raw, surface_rules)
    if len(whole) > 1:
        return _not_comparable(res, base, "surface", "", "multiple_rules", osm_raw, whole)
    rule = whole[0]
    fam_osm = surface_family("osm", osm_surface)
    fam_ovt = surface_family("overture", rule.surface_raw)
    if "unknown" in (fam_osm, fam_ovt):
        return _not_comparable(
            res, base, "surface", "", "unknown_family", osm_raw, [rule], rule.rule_index
        )
    if fam_osm == fam_ovt:
        res.stats["comparisons"] += 1
        res.stats["equal"] += 1
        return
    text = (
        f"Rodzina nawierzchni różni się: OSM {osm_raw} ({fam_osm}), Overture "
        f"{rule.surface_raw} ({fam_ovt}). Kandydat wymaga sprawdzenia. Różnica między "
        f"źródłami nie dowodzi błędu mapy. {dates}"
    )
    _candidate(
        res, base, "surface_family_mismatch", "", rule, fam_osm, fam_ovt, osm_raw, text, photos
    )
