"""Weryfikacja snapshotu i odczyt wejść (ADR-001 §3.1, §5; ADR-002 §3.1).

Wejścia są otwierane wyłącznie do odczytu. Weryfikacja kończy się, zanim powstanie katalog
wyników (AC-01). Geometrię czyta GeoPandas, a listy struktur Overture rozpakowuje DuckDB.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import duckdb
import geopandas as gpd
import pandas as pd
import pyarrow.parquet as pq
from pyproj import CRS

from map_qa.model import InputError, Snapshot

CORE_FILES = {
    "osm_roads.parquet": ("osm", "osm_roads"),
    "overture_segments.parquet": ("overture", "overture_segments"),
    "photos.csv": ("photos", "photos"),
    "photo_road_links.csv": ("links", "photo_road_links"),
}
SIGN_FILES = ("signs/signs.csv", "signs/nearest_osm.csv", "signs/labels.csv")
HINT_INPUT = "uruchom z korzenia repozytorium albo podaj --input"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _csv_rows(path: Path) -> int:
    with path.open(encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.reader(f)) - 1


def _rows(path: Path) -> int:
    if path.suffix == ".parquet":
        return pq.ParquetFile(path).metadata.num_rows
    return _csv_rows(path)


def verify_snapshot(input_dir: Path, with_signs: bool = False) -> Snapshot:
    """Sprawdza manifest, SHA-256 i liczności. Zwraca `Snapshot` albo rzuca `InputError`."""
    input_dir = Path(input_dir)
    if not input_dir.is_dir():
        raise InputError(str(input_dir), "input_dir_missing", HINT_INPUT)
    manifest_path = input_dir / "sources.json"
    if not manifest_path.is_file():
        raise InputError("sources.json", "missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        files = manifest["files"]
    except (OSError, ValueError, KeyError) as exc:
        raise InputError("sources.json", "unreadable", str(exc)) from exc

    warnings: list[str] = []
    for name in CORE_FILES:
        if not (input_dir / name).is_file():
            raise InputError(name, "missing")
        if name not in files:
            raise InputError(name, "hash_mismatch", "brak hasha w manifeście")
    for name, meta in sorted(files.items()):
        path = input_dir / name
        if not path.is_file():
            warnings.append(f"{name}: brak pliku opcjonalnego (missing)")
            continue
        try:
            digest = _sha256(path)
        except OSError as exc:
            raise InputError(name, "unreadable", str(exc)) from exc
        if digest != meta.get("sha256"):
            raise InputError(name, "hash_mismatch")
    if with_signs:
        for name in SIGN_FILES:
            if not (input_dir / name).is_file():
                raise InputError(name, "missing")
            if name not in files:
                warnings.append(f"{name}: hash_not_in_manifest (sprawdzono tylko obecność)")

    rows: dict[str, int] = {}
    for name, (section, key) in CORE_FILES.items():
        expected = manifest.get(section, {}).get("rows")
        actual = _rows(input_dir / name)
        if expected is not None and actual != expected:
            raise InputError(name, "row_count_mismatch", f"plik {actual}, manifest {expected}")
        rows[key] = actual

    return Snapshot(
        input_dir=input_dir,
        osm_extract_date=manifest["osm"]["extract_date"],
        overture_release=manifest["overture"]["release"],
        created_at=manifest["created_at"],
        rows=rows,
        osm_crs=manifest["osm"].get("crs", "EPSG:4326"),
        overture_crs=manifest["overture"].get("crs", "OGC:CRS84"),
        warnings=tuple(warnings),
    )


def _check_crs(gdf: gpd.GeoDataFrame, expected: str, name: str) -> None:
    """Porównanie przez obiekty `pyproj.CRS`, nie napisy (ADR-002 §3.1)."""
    want = CRS.from_user_input(expected)
    got = gdf.crs
    ok = got is not None and (got == want or (want.to_epsg() == 4326 and got.to_epsg() == 4326))
    if not ok:
        raise InputError(name, "crs_mismatch", f"plik {got}, manifest {expected}")


OSM_COLUMNS = [
    "osm_id",
    "highway",
    "tags",
    "node_ids",
    "boundary_crossing",
    "oneway",
    "geometry",
]


def load_osm(snapshot: Snapshot) -> gpd.GeoDataFrame:
    """Drogi OSM w EPSG:4326 z pełnym `tags` jako tekst (AC-04)."""
    gdf = gpd.read_parquet(Path(snapshot.input_dir) / "osm_roads.parquet", columns=OSM_COLUMNS)
    _check_crs(gdf, snapshot.osm_crs, "osm_roads.parquet")
    gdf["osm_id"] = gdf["osm_id"].astype("int64")
    return gdf.sort_values("osm_id").reset_index(drop=True)


def load_overture_raw(snapshot: Snapshot) -> gpd.GeoDataFrame:
    """Segmenty Overture z regułami i źródłami jako listy elementów JSON (pełna struktura)."""
    path = Path(snapshot.input_dir) / "overture_segments.parquet"
    gdf = gpd.read_parquet(path, columns=["id", "class", "geometry"])
    _check_crs(gdf, snapshot.overture_crs, "overture_segments.parquet")
    con = duckdb.connect()
    try:
        lists = con.execute(
            """
            SELECT id,
                   list_transform(speed_limits, lambda x: to_json(x)::VARCHAR) AS speed_limits,
                   list_transform(road_surface, lambda x: to_json(x)::VARCHAR) AS road_surface,
                   list_transform(sources, lambda x: to_json(x)::VARCHAR) AS sources
            FROM read_parquet(?)
            """,
            [str(path)],
        ).fetchall()
    finally:
        con.close()
    by_id = {row[0]: row[1:] for row in lists}
    for i, col in enumerate(("speed_limits", "road_surface", "sources")):
        gdf[col] = [list(by_id[seg][i] or []) for seg in gdf["id"]]
    return gdf.sort_values("id").reset_index(drop=True)


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=object, na_filter=False, encoding="utf-8")


def _opt_float(value: str) -> float | None:
    value = (value or "").strip()
    return None if value == "" else float(value)


def load_photos(snapshot: Snapshot) -> pd.DataFrame:
    """`photos.csv`; pusty `heading` to brak (None), a 0.0 to północ (AC-18)."""
    df = _read_csv(Path(snapshot.input_dir) / "photos.csv")
    df["heading"] = pd.Series([_opt_float(v) for v in df["heading"]], dtype=object)
    df["longitude"] = df["longitude"].astype(float)
    df["latitude"] = df["latitude"].astype(float)
    df["is_panorama"] = df["is_panorama"].str.lower() == "true"
    return df


def load_links(snapshot: Snapshot) -> pd.DataFrame:
    df = _read_csv(Path(snapshot.input_dir) / "photo_road_links.csv")
    df["file_flags"] = df["candidate_flags"].apply(
        lambda s: tuple(f for f in s.split(";") if f) if s else ()
    )
    return df


def load_offline_attribution(input_dir: Path) -> pd.DataFrame:
    path = Path(input_dir) / "offline" / "ATTRIBUTION.csv"
    return _read_csv(path) if path.is_file() else pd.DataFrame(columns=["photo_id", "filename"])


def load_signs(snapshot: Snapshot) -> tuple[pd.DataFrame, pd.DataFrame]:
    """`signs/signs.csv` i `signs/nearest_osm.csv`. Etykiet nie czytamy (TAC-003-04)."""
    base = Path(snapshot.input_dir) / "signs"
    signs = _read_csv(base / "signs.csv").sort_values("photo_id").reset_index(drop=True)
    nearest = _read_csv(base / "nearest_osm.csv")
    return signs, nearest
