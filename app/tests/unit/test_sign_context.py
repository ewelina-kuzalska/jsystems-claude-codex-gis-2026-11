"""AC-27, AC-29; ADR-002 §3.4, D-204."""

import geopandas as gpd
import pytest
from shapely.geometry import LineString

from map_qa.crs import local_bearing, to_2180_xy, to_4326_xy
from map_qa.linking import OsmIndex, sign_road_context

E0, N0 = to_2180_xy(19.9373, 50.0614)
EAST = LineString([(E0 - 50, N0 + 3), (E0 + 50, N0 + 3)])


def idx():
    return OsmIndex(lines=gpd.GeoSeries([EAST], index=[1], crs=2180), tags={1: {}})


def sign(compass="10", pid="s1"):
    lon, lat = to_4326_xy(E0, N0)
    return {"photo_id": pid, "longitude": str(lon), "latitude": str(lat), "compass_angle": compass}


def nearest(**kw):
    row = {
        "photo_id": "s1",
        "osm_way_id": "1",
        "source": "osm_roads.parquet",
        "maxspeed": "",
        "maxspeed_forward": "",
        "maxspeed_backward": "",
        "maxspeed_conditional": "",
        "oneway": "",
        "match_flags": "",
        "distance_m": "3.0",
    }
    row.update(kw)
    return row


def east_bearing():
    from shapely.geometry import Point

    return local_bearing(EAST, Point(E0, N0))


@pytest.mark.parametrize(
    "offset,direction,value",
    [(10, "forward", 50.0), (170, "backward", 70.0), (90, "unknown", None)],
)
def test_directional_choice(offset, direction, value):
    compass = str((east_bearing() + offset) % 360)
    ctx = sign_road_context(
        sign(compass), nearest(maxspeed_forward="50", maxspeed_backward="70"), idx()
    )
    assert ctx.chosen_direction == direction
    assert ctx.osm_value_kmh == value
    assert ctx.status == ("ok" if value else "direction_unknown")
    assert ctx.osm_speed_raw == {"maxspeed:forward": "50", "maxspeed:backward": "70"}


def test_missing_compass_is_direction_unknown():
    ctx = sign_road_context(sign(""), nearest(maxspeed_forward="50"), idx())
    assert ctx.status == "direction_unknown"


def test_plain_maxspeed_and_conditional_raw():
    ctx = sign_road_context(
        sign(), nearest(maxspeed="140", maxspeed_conditional="110 @ (Mo-Fr 06:00-18:00)"), idx()
    )
    assert (ctx.chosen_direction, ctx.osm_value_kmh, ctx.status) == ("both", 140.0, "ok")
    assert ctx.osm_speed_raw["maxspeed:conditional"] == "110 @ (Mo-Fr 06:00-18:00)"


def test_missing_and_not_numeric():
    assert sign_road_context(sign(), nearest(), idx()).status == "missing"
    assert sign_road_context(sign(), nearest(maxspeed="PL:urban"), idx()).status == "not_numeric"


def test_outside_snapshot_osm_api():
    ctx = sign_road_context(
        sign(), nearest(source="osm_api", osm_way_id="999", maxspeed="50"), idx()
    )
    assert (ctx.status, ctx.chosen_direction) == ("outside_snapshot", "unknown")
    assert ctx.osm_value_kmh is None


def test_inconsistent_source_is_flagged():
    ctx = sign_road_context(sign(), nearest(source="osm_roads.parquet", osm_way_id="999"), idx())
    assert ctx.status == "outside_snapshot"
    assert "nearest_osm_source_inconsistent" in ctx.flags


def test_match_flags_and_oneway():
    ctx = sign_road_context(
        sign(),
        nearest(maxspeed="50", match_flags="outside_standard_25m;service_way", oneway="-1"),
        idx(),
    )
    assert ctx.flags == ("outside_standard_25m", "service_way")
    assert ctx.oneway == "-1" and ctx.chosen_direction == "both"


def test_real_fixture_osm_api_sign(fixtures_dir):
    from map_qa.crs import to_2180
    from map_qa.inputs import load_osm, load_signs, verify_snapshot

    snap = verify_snapshot(fixtures_dir / "map_qa", with_signs=True)
    osm = load_osm(snap)
    index = OsmIndex.build(osm, to_2180(osm).geometry)
    signs, near = load_signs(snap)
    s = signs.set_index("photo_id")
    n = near.set_index("photo_id")
    pid = "mapillary_915915556657317"  # Warszawa, osm_api
    ctx = sign_road_context({"photo_id": pid, **s.loc[pid]}, {"photo_id": pid, **n.loc[pid]}, index)
    assert ctx.status == "outside_snapshot"
    pid = "mapillary_1237130608489136"  # Kraków, forward 50 / backward 70
    ctx = sign_road_context({"photo_id": pid, **s.loc[pid]}, {"photo_id": pid, **n.loc[pid]}, index)
    assert ctx.status in ("ok", "direction_unknown") and ctx.osm_way_id == 557114409
