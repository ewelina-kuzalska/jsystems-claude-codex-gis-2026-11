"""AC-11–AC-15; ADR-001 §3.6, D-103, D-104 (dane syntetyczne w EPSG:2180)."""

import json

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString

from map_qa.checks.c2 import check_discrepancy, geometry_direction
from map_qa.crs import to_2180_xy, to_4326_xy

E0, N0 = to_2180_xy(19.9373, 50.0614)
LINE = LineString([(E0, N0), (E0 + 100, N0)])
REVERSED = LineString([(E0 + 100, N0), (E0, N0)])
NORTH = LineString([(E0 + 50, N0 - 50), (E0 + 50, N0 + 50)])


def to4326(line):
    return LineString([to_4326_xy(x, y) for x, y in line.coords])


def speed(value, between=None, when=None, variable=None):
    return json.dumps(
        {
            "max_speed": {"value": value, "unit": "km/h"},
            "is_max_speed_variable": variable,
            "when": when,
            "between": between,
        }
    )


def src(way, between=None):
    return json.dumps({"dataset": "OpenStreetMap", "record_id": f"w{way}@1", "between": between})


def run(osm_tags, seg_speed=(), seg_surface=(), sources=None, seg_line=LINE, links_rows=()):
    osm = gpd.GeoDataFrame(
        [
            {
                "osm_id": 1,
                "highway": "residential",
                "tags": json.dumps(osm_tags),
                "geometry": to4326(LINE),
            }
        ],
        crs=4326,
    )
    seg = gpd.GeoDataFrame(
        [
            {
                "id": "s1",
                "class": "residential",
                "speed_limits": list(seg_speed),
                "road_surface": list(seg_surface),
                "sources": sources or [src(1)],
                "geometry": to4326(seg_line),
            }
        ],
        crs="OGC:CRS84",
    )
    links = pd.DataFrame(
        list(links_rows),
        columns=[
            "photo_id",
            "osm_way_id",
            "overture_id",
            "match_method",
            "distance_m",
            "file_flags",
        ],
    )
    return check_discrepancy(osm, seg, links, "2026-11-01T21:21:36Z", "2026-10-21.0")


def reasons(result):
    return sorted((n.attribute, n.direction, n.reason_code) for n in result.not_comparable)


def test_speed_mismatch_with_both_values_and_dates():
    r = run({"maxspeed": "50"}, [speed(60)])
    (c,) = r.candidates
    assert (c.check, c.reason_code, c.osm_id, c.segment_id, c.direction) == (
        "C2",
        "speed_mismatch",
        1,
        "s1",
        "both",
    )
    assert c.osm_normalized == "50" and c.overture_normalized == "60"
    assert c.extra["osm_value_raw"] == "maxspeed=50"
    assert "2026-11-01" in c.description_pl and "2026-10-21.0" in c.description_pl
    assert r.stats["comparisons"] == 1


def test_equal_values_no_candidate():
    r = run({"maxspeed": "50"}, [speed(50)])
    assert r.candidates == [] and r.stats["equal"] == 1


def test_unconditional_plus_mode_is_single_rule():
    r = run({"maxspeed": "50"}, [speed(70), speed(50, when={"mode": ["bus", "hgv"]})])
    assert [c.overture_normalized for c in r.candidates] == ["70"]
    assert r.not_comparable == []


def test_not_comparable_reasons():
    assert reasons(run({"maxspeed": "PL:urban"}, [speed(50)])) == [("speed", "both", "not_numeric")]
    assert reasons(run({"maxspeed": "50"}, [speed(50, between=[0.2, 0.6])])) == [
        ("speed", "both", "partial_segment")
    ]
    assert reasons(run({"maxspeed": "50"}, [speed(50, when={"during": "Mo-Fr"})])) == [
        ("speed", "both", "conditional")
    ]
    assert reasons(run({"maxspeed": "50"}, [speed(50, variable=True)])) == [
        ("speed", "both", "variable")
    ]
    assert reasons(run({"maxspeed": "50"}, [speed(50), speed(60)])) == [
        ("speed", "both", "multiple_rules")
    ]


def test_partial_source():
    r = run(
        {"maxspeed": "50", "surface": "asphalt"},
        [speed(60)],
        ['{"value":"gravel"}'],
        sources=[src(1, [0.0, 0.2996])],
    )
    assert r.candidates == []
    assert reasons(r) == [("speed", "both", "partial_source"), ("surface", "", "partial_source")]


def test_no_reference_no_comparison():  # AC-11, TAC-001-04
    r = run({"maxspeed": "50"}, [speed(60)], sources=[json.dumps({"dataset": "TomTom"})])
    assert r.candidates == [] and r.stats["comparisons"] == 0


def test_missing_side_is_c1_not_c2():
    r = run({"highway": "residential"}, [speed(60)])  # brak maxspeed i surface w OSM
    assert r.candidates == [] and r.not_comparable == [] and r.stats["missing"] == 2
    assert r.stats["comparisons"] == 0


def test_directional_reversed_geometry():
    # Overture forward wzdłuż odwróconej geometrii odpowiada OSM backward
    r = run(
        {"maxspeed:forward": "50", "maxspeed:backward": "70"},
        [speed(70, when={"heading": "forward"}), speed(50, when={"heading": "backward"})],
        seg_line=REVERSED,
    )
    assert r.candidates == []
    assert r.stats["equal"] == 2


def test_directional_mismatch_same_geometry():
    r = run({"maxspeed:forward": "50"}, [speed(60, when={"heading": "forward"})])
    assert [(c.direction, c.osm_normalized, c.overture_normalized) for c in r.candidates] == [
        ("forward", "50", "60")
    ]


def test_direction_unknown_at_90_degrees():
    r = run({"maxspeed": "50"}, [speed(60, when={"heading": "forward"})], seg_line=NORTH)
    assert ("speed", "forward", "direction_unknown") in reasons(r)
    assert geometry_direction(NORTH, LINE) == "unknown"
    assert geometry_direction(LINE, LINE) == "same"
    assert geometry_direction(REVERSED, LINE) == "reversed"


def test_conditional_flag_on_candidate():
    r = run({"maxspeed": "50", "maxspeed:conditional": "110 @ (Mo-Fr 06:00-18:00)"}, [speed(60)])
    assert r.candidates[0].extra["osm_conditional_present"] is True


@pytest.mark.parametrize(
    "osm_surface,ovt,expected",
    [
        ("asphalt", "gravel", "surface_family_mismatch"),
        ("asphalt", "paved", None),
        ("grass_paver", "gravel", "unknown_family"),
        ("contrete:plates", "gravel", "unknown_family"),
        ("asphalt", "unknown", "unknown_family"),
    ],
)
def test_surface(osm_surface, ovt, expected):
    r = run({"surface": osm_surface}, [], [json.dumps({"value": ovt, "between": None})])
    got = [c.reason_code for c in r.candidates] + [n.reason_code for n in r.not_comparable]
    assert got == ([expected] if expected else [])


def test_sum_of_outcomes_equals_comparisons():  # TAC-001-05
    r = run(
        {"maxspeed": "50", "maxspeed:forward": "PL:urban", "surface": "asphalt"},
        [speed(60), speed(40, when={"heading": "forward"})],
        ['{"value":"gravel","between":null}'],
    )
    s = r.stats
    assert s["candidates"] + s["not_comparable"] + s["equal"] == s["comparisons"]
    assert s["comparisons"] >= 3


def test_spatial_only_list():
    r = run({"maxspeed": "50"}, [], links_rows=[("p1", "1", "s1", "spatial_fallback", "3.2", ())])
    assert [x["photo_id"] for x in r.spatial_only] == ["p1"]
