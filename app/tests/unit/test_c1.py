"""AC-08, AC-09, AC-10; ADR-001 §3.5."""

import json

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString

from map_qa.checks.c1 import check_missing


def osm(rows):
    return gpd.GeoDataFrame(
        [
            {
                "osm_id": i,
                "highway": hw,
                "tags": json.dumps(tags),
                "geometry": LineString([(19.9, 50.0), (19.901, 50.0)]),
            }
            for i, hw, tags in rows
        ],
        crs=4326,
    )


def overture(rows):
    return gpd.GeoDataFrame(
        [
            {"id": i, "class": c, "speed_limits": sl, "road_surface": rs, "geometry": None}
            for i, c, sl, rs in rows
        ]
    )


def links(pairs):
    return pd.DataFrame(
        [{"photo_id": p, "osm_way_id": str(w) if w else "", "file_flags": ()} for p, w in pairs]
    )


def test_summary_counts_per_class():
    o = osm(
        [
            (1, "residential", {"highway": "residential", "maxspeed": "50", "surface": "asphalt"}),
            (2, "residential", {"highway": "residential", "maxspeed:backward": "30"}),
            (3, "service", {"highway": "service", "lanes": "1", "lit": "yes"}),
        ]
    )
    ov = overture([("a", "service", [], ["{}"]), ("b", "service", ["{}"], [])])
    summary, _ = check_missing(o, ov, links([]))
    res = {r["highway"]: r for r in summary["osm"]}
    assert res["residential"]["total"] == 2
    assert res["residential"]["missing"] == {"maxspeed": 0, "surface": 1, "lanes": 2, "lit": 2}
    assert res["service"]["missing"]["maxspeed"] == 1
    ovr = {r["class"]: r for r in summary["overture"]}
    assert ovr["service"] == {
        "class": "service",
        "total": 2,
        "missing_speed": 1,
        "missing_surface": 1,
    }


def test_tasks_only_for_roads_with_photos():
    o = osm(
        [
            (
                1,
                "residential",
                {"highway": "residential", "surface": "asphalt", "lanes": "2", "lit": "yes"},
            ),
            (
                2,
                "residential",
                {"highway": "residential", "surface": "asphalt", "lanes": "2", "lit": "yes"},
            ),
        ]
    )
    _, cands = check_missing(o, overture([]), links([("pb", 2), ("pa", 2)]))
    assert len(cands) == 1  # droga 1 bez zdjęcia: tylko w podsumowaniu
    c = cands[0]
    assert (c.check, c.reason_code, c.osm_id) == ("C1", "missing_maxspeed", 2)
    assert c.photo_ids == ("pa", "pb") and c.photo_id == "pa"  # 2 zdjęcia → 1 zadanie
    assert json.loads(c.osm_raw)["surface"] == "asphalt"  # pełne tagi (AC-04)
    assert "wymaga sprawdzenia" in c.description_pl.lower()
