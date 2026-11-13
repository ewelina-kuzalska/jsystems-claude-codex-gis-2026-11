"""AC-05; ADR-001 §3.3, D-102."""

import json

import pytest

from map_qa.inputs import load_overture_raw, verify_snapshot
from map_qa.normalize.overture import (
    osm_way_id_from_record,
    rules_for_segment,
    sources_for_segment,
)


def rule(value, between=None, when=None, variable=None, unit="km/h"):
    return json.dumps(
        {
            "min_speed": None,
            "max_speed": {"value": value, "unit": unit},
            "is_max_speed_variable": variable,
            "when": when,
            "between": between,
        }
    )


@pytest.fixture(scope="module")
def segments(fixtures_dir_module):
    return load_overture_raw(verify_snapshot(fixtures_dir_module / "map_qa")).set_index("id")


def test_three_rules_keep_index_and_between(segments):
    row = segments.loc["00836247-b00a-40ea-99b0-703841eb9028"]
    rules = [
        r
        for r in rules_for_segment(row.name, row.speed_limits, row.road_surface)
        if r.rule_kind == "speed"
    ]
    assert [r.rule_index for r in rules] == [0, 1, 2]
    assert all(not r.whole_segment for r in rules)
    assert [r.value_kmh for r in rules] == [70.0, 60.0, 70.0]
    assert rules[1].raw_json == row.speed_limits[1]


def test_unconditional_plus_mode_rule(segments):
    row = segments.loc["009debd5-c2b6-4f7c-9742-b798fd175449"]
    speed = [r for r in rules_for_segment(row.name, row.speed_limits, []) if r.rule_kind == "speed"]
    assert [(r.value_kmh, r.unconditional) for r in speed] == [(70.0, True), (50.0, False)]


def test_when_all_null_is_unconditional():
    w = dict.fromkeys(("during", "heading", "using", "recognized", "mode", "vehicle"))
    (r,) = rules_for_segment("s", [rule(50, when=w)], [])
    assert r.unconditional and r.heading is None and r.when_raw is None


def test_heading_only_is_unconditional_directional():
    (r,) = rules_for_segment("s", [rule(50, when={"heading": "forward", "mode": None})], [])
    assert r.unconditional and r.heading == "forward"
    (r2,) = rules_for_segment("s", [rule(50, when={"heading": "forward", "mode": ["bus"]})], [])
    assert not r2.unconditional and r2.heading == "forward"


def test_partial_and_whole_between():
    a, b = rules_for_segment("s", [rule(50, between=[0.2, 0.6]), rule(50, between=[0, 1])], [])
    assert (a.whole_segment, a.between_start, a.between_end) == (False, 0.2, 0.6)
    assert b.whole_segment


def test_mph_and_variable():
    (r,) = rules_for_segment("s", [rule(30, unit="mph", variable=True)], [])
    assert r.value_kmh == 48.3 and r.unit_raw == "mph" and r.is_variable


def test_surface_rules_unconditional():
    (r,) = rules_for_segment("s", [], [json.dumps({"value": "gravel", "between": [0.1, 0.5]})])
    assert r.rule_kind == "surface" and r.surface_raw == "gravel"
    assert r.unconditional and r.when_raw is None and not r.whole_segment


def test_record_id():
    assert osm_way_id_from_record("w123@4") == 123
    assert osm_way_id_from_record("n5@1") is None
    assert osm_way_id_from_record("") is None
    assert osm_way_id_from_record(None) is None
    assert osm_way_id_from_record("w123") is None
    assert osm_way_id_from_record("wabc@1") is None


def test_sources_partial():
    src = [
        json.dumps(
            {"dataset": "OpenStreetMap", "record_id": "w75390950@17", "between": [0, 0.2996]}
        ),
        json.dumps({"dataset": "OpenStreetMap", "record_id": "w1@2", "between": None}),
        json.dumps({"dataset": "TomTom", "record_id": None, "between": None}),
    ]
    a, b, c = sources_for_segment("s", src)
    assert (a.osm_way_id, a.source_whole_segment, a.source_index) == (75390950, False, 0)
    assert (b.osm_way_id, b.source_whole_segment) == (1, True)
    assert c.osm_way_id is None
