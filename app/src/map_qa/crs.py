"""Transformacje CRS, odległości i azymuty (ADR-002 §3.1, D-201, D-202).

Jedyne miejsce tworzenia `Transformer` w kodzie; zawsze `always_xy=True` (TAC-002-02).
Odległości liczymy wyłącznie w EPSG:2180 (TAC-002-01).
"""

from __future__ import annotations

from functools import cache

import geopandas as gpd
import shapely
from pyproj import CRS, Geod, Transformer
from shapely.geometry.base import BaseGeometry

from map_qa.model import InputError

EPSG_2180 = "EPSG:2180"
_GEOD = Geod(ellps="GRS80")
# Zakres współrzędnych EPSG:2180 dla Polski (easting/northing); stopnie są daleko poza nim.
_MIN_2180 = 100_000.0


@cache
def _transformer(source: str, target: str) -> Transformer:
    return Transformer.from_crs(source, target, always_xy=True)


def to_2180_xy(lon: float, lat: float, source: str = "EPSG:4326") -> tuple[float, float]:
    return _transformer(source, EPSG_2180).transform(lon, lat)


def to_4326_xy(x: float, y: float) -> tuple[float, float]:
    return _transformer(EPSG_2180, "EPSG:4326").transform(x, y)


def geometry_to_2180(geom: BaseGeometry, source: str = "EPSG:4326") -> BaseGeometry:
    return shapely.transform(geom, lambda c: _vec(c, source, EPSG_2180))


def geometry_to_4326(geom: BaseGeometry) -> BaseGeometry:
    return shapely.transform(geom, lambda c: _vec(c, EPSG_2180, "EPSG:4326"))


def _vec(coords, source: str, target: str):
    import numpy as np

    x, y = _transformer(source, target).transform(coords[:, 0], coords[:, 1])
    return np.column_stack([x, y])


def _expect_crs(gdf: gpd.GeoDataFrame, accepted: tuple[str, ...], name: str) -> None:
    if gdf.crs is None or not any(gdf.crs == CRS.from_user_input(a) for a in accepted):
        raise InputError(name, "crs_mismatch", f"oczekiwano {' / '.join(accepted)}, jest {gdf.crs}")


def to_2180(gdf: gpd.GeoDataFrame, name: str = "warstwa") -> gpd.GeoDataFrame:
    """Ramka 4326/CRS84 → EPSG:2180; inny CRS daje `InputError(crs_mismatch)`."""
    _expect_crs(gdf, ("EPSG:4326", "OGC:CRS84"), name)
    out = gdf.copy()
    source = "OGC:CRS84" if gdf.crs == CRS.from_user_input("OGC:CRS84") else "EPSG:4326"
    out["geometry"] = shapely.transform(gdf.geometry.values, lambda c: _vec(c, source, EPSG_2180))
    return out.set_crs(EPSG_2180, allow_override=True)


def to_4326(gdf: gpd.GeoDataFrame, name: str = "warstwa") -> gpd.GeoDataFrame:
    _expect_crs(gdf, (EPSG_2180,), name)
    out = gdf.copy()
    out["geometry"] = shapely.transform(
        gdf.geometry.values, lambda c: _vec(c, EPSG_2180, "EPSG:4326")
    )
    return out.set_crs("EPSG:4326", allow_override=True)


def _assert_metric(*geoms: BaseGeometry) -> None:
    for g in geoms:
        minx, miny, _, _ = g.bounds
        if minx < _MIN_2180 and miny < _MIN_2180:
            raise ValueError("Odległość wymaga geometrii w EPSG:2180 (metry), nie w stopniach")


def distance_m(a: BaseGeometry, b: BaseGeometry) -> float:
    _assert_metric(a, b)
    return float(a.distance(b))


def geodesic_bearing(p1_lonlat: tuple[float, float], p2_lonlat: tuple[float, float]) -> float:
    """Azymut geodezyjny od północy rzeczywistej, zakres [0, 360)."""
    az, _, _ = _GEOD.inv(p1_lonlat[0], p1_lonlat[1], p2_lonlat[0], p2_lonlat[1])
    return az % 360.0


def local_bearing(line_2180: BaseGeometry, point_2180: BaseGeometry, half_window_m=5.0) -> float:
    """Styczna w oknie ±5 m wokół rzutu punktu, jako azymut geodezyjny (D-202)."""
    _assert_metric(line_2180, point_2180)
    along = line_2180.project(point_2180)
    start = max(0.0, along - half_window_m)
    end = min(line_2180.length, along + half_window_m)
    p1 = line_2180.interpolate(start)
    p2 = line_2180.interpolate(end)
    return geodesic_bearing(to_4326_xy(p1.x, p1.y), to_4326_xy(p2.x, p2.y))


def angle_diff(a: float, b: float) -> float:
    """Najmniejszy kąt między dwoma kierunkami, zakres 0–180."""
    d = abs(a - b) % 360.0
    return 360.0 - d if d > 180.0 else d


def angle_diffs(heading: float | None, bearing: float) -> tuple[float | None, float | None]:
    """(directed 0–180, undirected 0–90). Brak heading daje (None, None) (AC-18)."""
    if heading is None:
        return None, None
    directed = angle_diff(heading, bearing)
    return directed, min(directed, 180.0 - directed)
