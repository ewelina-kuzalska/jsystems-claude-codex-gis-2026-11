"""AC-17, AC-18; ADR-002 §3.1, §5, D-201, D-202, TAC-002-01/02."""

import re
from pathlib import Path

import pytest
from pyproj import Geod
from shapely.geometry import LineString, Point

import map_qa
from map_qa.crs import (
    angle_diff,
    angle_diffs,
    distance_m,
    geodesic_bearing,
    local_bearing,
    to_2180_xy,
    to_4326_xy,
)


def test_axis_order_rynek():
    e, n = to_2180_xy(19.9373, 50.0614)
    assert 560_000 <= e <= 575_000 and 240_000 <= n <= 255_000
    e2, n2 = to_2180_xy(50.0614, 19.9373)  # zamienione osie muszą wypaść poza zakres
    assert not (560_000 <= e2 <= 575_000 and 240_000 <= n2 <= 255_000)


def test_roundtrip_and_crs84():
    lon, lat = to_4326_xy(*to_2180_xy(19.9373, 50.0614))
    assert abs(lon - 19.9373) < 1e-7 and abs(lat - 50.0614) < 1e-7
    assert to_2180_xy(19.9373, 50.0614, source="OGC:CRS84") == pytest.approx(
        to_2180_xy(19.9373, 50.0614), abs=1e-6
    )


def test_known_distance_100m():
    lon2, lat2, _ = Geod(ellps="GRS80").fwd(19.9373, 50.0614, 90, 100.0)
    a = Point(*to_2180_xy(19.9373, 50.0614))
    b = Point(*to_2180_xy(lon2, lat2))
    assert distance_m(a, b) == pytest.approx(100.0, abs=0.1)


def test_distance_to_line_and_beyond_end():
    line = LineString([(560000, 245000), (560100, 245000)])
    assert distance_m(Point(560050, 245003), line) == pytest.approx(3.0)
    assert distance_m(Point(560103, 245004), line) == pytest.approx(5.0)


def test_distance_rejects_degrees():  # TAC-002-01
    with pytest.raises(ValueError):
        distance_m(Point(19.9, 50.0), LineString([(19.9, 50.0), (19.91, 50.0)]))


def test_local_bearing_west_east():
    e, n = to_2180_xy(19.9373, 50.0614)
    line = LineString([(e - 50, n), (e + 50, n)])
    assert local_bearing(line, Point(e, n)) == pytest.approx(90.0, abs=1.5)
    assert local_bearing(line, Point(e + 50, n)) == pytest.approx(90.0, abs=1.5)  # okno przycięte
    back = LineString([(e + 50, n), (e - 50, n)])
    assert local_bearing(back, Point(e, n)) == pytest.approx(270.0, abs=1.5)


def test_geodesic_bearing_north():
    assert geodesic_bearing((19.9, 50.0), (19.9, 50.01)) == pytest.approx(0.0, abs=1e-6)


def test_angle_diffs():
    assert angle_diffs(359.0, 1.0) == pytest.approx((2.0, 2.0))
    assert angle_diffs(90.0, 270.0) == pytest.approx((180.0, 0.0))
    assert angle_diffs(0.0, 90.0) == pytest.approx((90.0, 90.0))  # 0 to północ, nie brak
    assert angle_diffs(None, 90.0) == (None, None)
    assert angle_diff(10, 350) == pytest.approx(20.0)


def test_transformers_always_xy():  # TAC-002-02
    for path in Path(map_qa.__file__).parent.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"Transformer\.from_crs\(([^)]*)\)", text):
            assert path.name == "crs.py", f"Transformer poza crs.py: {path}"
            assert "always_xy=True" in m.group(1)
