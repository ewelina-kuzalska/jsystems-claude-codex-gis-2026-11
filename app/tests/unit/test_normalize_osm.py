"""AC-04, AC-06, AC-07; ADR-001 §3.2, D-101, TAC-001-01."""

import json

import pyarrow.parquet as pq
import pytest

from map_qa.normalize.osm import has_speed, parse_maxspeed, speed_for_direction, speed_values


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("50", ("numeric", 50.0, None)),
        (" 50 ", ("numeric", 50.0, None)),
        ("50 km/h", ("numeric", 50.0, None)),
        ("50km/h", ("numeric", 50.0, None)),
        ("50kmh", ("numeric", 50.0, None)),
        ("50 kmh", ("numeric", 50.0, None)),
        ("32.5", ("numeric", 32.5, None)),
        ("30 mph", ("numeric", 48.3, None)),
        ("30mph", ("numeric", 48.3, None)),
        ("10 knots", ("not_numeric", None, "unparsable")),
        ("PL:urban", ("not_numeric", None, "zone")),
        ("PL:zone30", ("not_numeric", None, "zone")),
        ("none", ("not_numeric", None, "none")),
        ("signals", ("not_numeric", None, "signals")),
        ("walk", ("not_numeric", None, "zone")),
        ("50;70", ("not_numeric", None, "multi_value")),
        ("50|70", ("not_numeric", None, "multi_value")),
        ("fast", ("not_numeric", None, "unparsable")),
    ],
)
def test_parse_maxspeed(raw, expected):
    assert parse_maxspeed(raw) == expected


def test_empty_is_missing():
    assert parse_maxspeed("") is None
    assert parse_maxspeed("  ") is None
    assert parse_maxspeed(None) is None


def test_speed_values_keys_and_directions():
    tags = json.dumps(
        {
            "maxspeed": "50",
            "maxspeed:forward": "70",
            "maxspeed:conditional": "110 @ (Mo-Fr 06:00-18:00)",
            "maxspeed:type": "PL:urban",
            "source:maxspeed": "sign",
            "maxspeed:hgv": "40",
        }
    )
    vals = {v.tag_key: v for v in speed_values(7, tags)}
    assert set(vals) == {
        "maxspeed",
        "maxspeed:forward",
        "maxspeed:conditional",
        "maxspeed:type",
        "source:maxspeed",
    }
    assert vals["maxspeed"].direction == "both" and vals["maxspeed"].value_kmh == 50.0
    assert vals["maxspeed:forward"].direction == "forward"
    cond = vals["maxspeed:conditional"]
    assert cond.status == "conditional" and cond.reason == "conditional"
    assert cond.value_kmh is None and cond.raw == "110 @ (Mo-Fr 06:00-18:00)"
    assert vals["maxspeed:type"].value_kmh is None  # tylko kontekst


def test_direction_inheritance():
    vals = speed_values(1, json.dumps({"maxspeed": "50", "maxspeed:forward": "70"}))
    assert speed_for_direction(vals, "forward").value_kmh == 70.0
    assert speed_for_direction(vals, "backward").value_kmh == 50.0  # dziedziczy both
    assert speed_for_direction(vals, "both").value_kmh == 50.0
    only_back = speed_values(2, json.dumps({"maxspeed:backward": "30"}))
    assert speed_for_direction(only_back, "forward") is None
    assert speed_for_direction(only_back, "backward").value_kmh == 30.0


def test_has_speed():  # AC-08
    assert has_speed(json.dumps({"maxspeed:backward": "30"}))
    assert not has_speed(json.dumps({"maxspeed:conditional": "110 @ (x)"}))
    assert not has_speed(json.dumps({"highway": "service"}))


def test_real_pl_urban_backward(fixtures_dir):
    """Prawdziwy wiersz z PL:urban w maxspeed:backward daje `zone` (profil M2)."""
    t = pq.read_table(fixtures_dir / "map_qa" / "osm_roads.parquet", columns=["osm_id", "tags"])
    tags = dict(zip(t["osm_id"].to_pylist(), t["tags"].to_pylist(), strict=True))[907138970]
    vals = {v.tag_key: v for v in speed_values(907138970, tags)}
    back = vals["maxspeed:backward"]
    assert (back.status, back.reason, back.raw) == ("not_numeric", "zone", "PL:urban")
    assert vals["maxspeed:forward"].value_kmh == 30.0
