"""ADR-002 §3.2–3.3, D-203, AC-16, AC-18 (geometria syntetyczna w EPSG:2180)."""

import json

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString

from map_qa.crs import to_2180_xy, to_4326_xy
from map_qa.linking import OsmIndex, recheck_links

E0, N0 = to_2180_xy(19.9373, 50.0614)


def index(ways):
    """ways: list of (osm_id, line_2180, tags)."""
    lines = gpd.GeoSeries([w[1] for w in ways], index=[w[0] for w in ways], crs=2180)
    return OsmIndex(lines=lines, tags={w[0]: w[2] for w in ways})


def photo(heading, de=0.0, dn=0.0, pid="p1"):
    lon, lat = to_4326_xy(E0 + de, N0 + dn)
    return pd.DataFrame([{"photo_id": pid, "longitude": lon, "latitude": lat, "heading": heading}])


def link(way_id, distance, bearing, count, flags=(), pid="p1"):
    return pd.DataFrame(
        [
            {
                "photo_id": pid,
                "osm_way_id": str(way_id) if way_id else "",
                "distance_m": str(distance),
                "way_bearing": str(bearing),
                "osm_candidate_count": str(count),
                "file_flags": tuple(flags),
            }
        ]
    )


EAST = LineString([(E0 - 50, N0 + 3), (E0 + 50, N0 + 3)])  # 3 m na północ od aparatu


def bearing_east():
    from shapely.geometry import Point

    from map_qa.crs import local_bearing

    return local_bearing(EAST, Point(E0, N0))


def test_consistent_link_is_ok():
    out = recheck_links(link(1, 3.0, bearing_east(), 1), photo(90.0), index([(1, EAST, {})]))
    row = out.iloc[0]
    assert row.recheck_status == "ok"
    assert row.recheck_distance_m == pytest.approx(3.0)
    assert row.own_flags == ()
    assert not row.uncertain


def test_distance_off_by_1m_is_mismatch_04_is_not():
    idx = index([(1, EAST, {})])
    bad = recheck_links(link(1, 4.0, bearing_east(), 1), photo(90.0), idx).iloc[0]
    assert bad.recheck_status == "mismatch" and "link_recheck_mismatch" in bad.own_flags
    assert bad.uncertain
    ok = recheck_links(link(1, 3.4, bearing_east(), 1), photo(90.0), idx).iloc[0]
    assert ok.recheck_status == "ok"


def test_bearing_and_count_and_top_mismatch():
    idx = index([(1, EAST, {})])
    assert (
        recheck_links(link(1, 3.0, bearing_east() + 6, 1), photo(90.0), idx).iloc[0].recheck_status
        == "mismatch"
    )
    assert (
        recheck_links(link(1, 3.0, bearing_east(), 2), photo(90.0), idx).iloc[0].recheck_status
        == "mismatch"
    )


def test_tie_break_distance_then_osm_id():
    south = LineString([(E0 - 50, N0 - 3), (E0 + 50, N0 - 3)])  # ten sam dystans 3 m
    idx = index([(7, EAST, {}), (5, south, {})])
    out = recheck_links(link(5, 3.0, bearing_east(), 2), photo(90.0), idx).iloc[0]
    assert out.recheck_top_osm_id == 5
    assert out.recheck_status == "ok"


def test_missing_heading_adds_penalty_not_zero():
    out = recheck_links(link(1, 3.0, bearing_east(), 1), photo(None), index([(1, EAST, {})]))
    row = out.iloc[0]
    assert row.directed_diff is None and row.undirected_diff is None  # nigdy 0 zamiast braku


def test_heading_zero_is_north():
    out = recheck_links(link(1, 3.0, bearing_east(), 1), photo(0.0), index([(1, EAST, {})]))
    assert out.iloc[0].directed_diff == pytest.approx(90.0, abs=1.5)


def test_no_osm_link_checks_radius():
    far = LineString([(E0 - 50, N0 + 40), (E0 + 50, N0 + 40)])
    assert (
        recheck_links(link(None, "", "", 0), photo(90.0), index([(1, far, {})]))
        .iloc[0]
        .recheck_status
        == "not_checked"
    )
    near = recheck_links(link(None, "", "", 0), photo(90.0), index([(1, EAST, {})])).iloc[0]
    assert "link_recheck_mismatch" in near.own_flags


def test_restricted_access_and_grade_separation():
    idx = index([(1, EAST, {"access": "private"})])
    row = recheck_links(link(1, 3.0, bearing_east(), 1), photo(90.0), idx).iloc[0]
    assert "restricted_access" in row.own_flags
    bridge = LineString([(E0 - 50, N0 - 10), (E0 + 50, N0 - 10)])
    idx2 = index([(1, EAST, {}), (2, bridge, {"bridge": "yes"})])
    row2 = recheck_links(link(1, 3.0, bearing_east(), 2), photo(90.0), idx2).iloc[0]
    assert "grade_separated_nearby" in row2.own_flags
    idx3 = index([(1, EAST, {"layer": "0"})])
    row3 = recheck_links(link(1, 3.0, bearing_east(), 1), photo(90.0), idx3).iloc[0]
    assert row3.own_flags == ()


def test_reversed_geometry_directed_180():
    west = LineString([(E0 + 50, N0 + 3), (E0 - 50, N0 + 3)])
    out = recheck_links(
        link(1, 3.0, (bearing_east() + 180) % 360, 1),
        photo(90.0),
        index([(1, west, json.loads("{}"))]),
    )
    row = out.iloc[0]
    assert row.directed_diff == pytest.approx(180.0, abs=1.5)
    assert row.undirected_diff == pytest.approx(0.0, abs=1.5)
