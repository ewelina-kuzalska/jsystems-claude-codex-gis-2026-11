"""AC-01, AC-02, AC-03; ADR-001 §3.1, ADR-002 §3.1 (CRS)."""

import hashlib
import json
import shutil

import geopandas as gpd
import pytest

from map_qa.inputs import (
    load_links,
    load_osm,
    load_overture_raw,
    load_photos,
    load_signs,
    verify_snapshot,
)
from map_qa.model import InputError


@pytest.fixture
def snap_dir(fixtures_dir, tmp_path):
    dest = tmp_path / "map_qa"
    shutil.copytree(fixtures_dir / "map_qa", dest)
    return dest


def test_fixture_snapshot_ok(snap_dir):
    snap = verify_snapshot(snap_dir)
    assert snap.osm_extract_date == "2026-11-01T21:21:36Z"
    assert snap.overture_release == "2026-10-21.0"
    assert snap.created_at.startswith("2026-11-02")
    assert snap.rows == {
        "osm_roads": 131,
        "overture_segments": 11,
        "photos": 10,
        "photo_road_links": 10,
    }


def test_changed_byte_gives_hash_mismatch(snap_dir):
    p = snap_dir / "photos.csv"
    data = bytearray(p.read_bytes())
    data[-2] = ord("X") if data[-2] != ord("X") else ord("Y")
    p.write_bytes(bytes(data))
    with pytest.raises(InputError) as exc:
        verify_snapshot(snap_dir)
    assert exc.value.file == "photos.csv"
    assert exc.value.reason == "hash_mismatch"


def test_missing_file(snap_dir):
    (snap_dir / "photo_road_links.csv").unlink()
    with pytest.raises(InputError) as exc:
        verify_snapshot(snap_dir)
    assert (exc.value.file, exc.value.reason) == ("photo_road_links.csv", "missing")


def test_missing_input_dir(tmp_path):
    with pytest.raises(InputError) as exc:
        verify_snapshot(tmp_path / "nope")
    assert exc.value.reason == "input_dir_missing"
    assert "korzenia repozytorium" in str(exc.value)


def test_row_count_mismatch(snap_dir):
    manifest = json.loads((snap_dir / "sources.json").read_text(encoding="utf-8"))
    manifest["photos"]["rows"] = 11
    (snap_dir / "sources.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(InputError) as exc:
        verify_snapshot(snap_dir)
    assert (exc.value.file, exc.value.reason) == ("photos.csv", "row_count_mismatch")


def test_signs_without_manifest_hash_warns(snap_dir):
    snap = verify_snapshot(snap_dir, with_signs=True)
    assert any("hash_not_in_manifest" in w and "signs/signs.csv" in w for w in snap.warnings)


def test_signs_required_only_with_signs(snap_dir):
    (snap_dir / "signs" / "labels.csv").unlink()
    verify_snapshot(snap_dir)  # bez --with-signs nie wymagamy
    with pytest.raises(InputError) as exc:
        verify_snapshot(snap_dir, with_signs=True)
    assert (exc.value.file, exc.value.reason) == ("signs/labels.csv", "missing")


def test_loaders_read_fixture(snap_dir):
    snap = verify_snapshot(snap_dir)
    osm = load_osm(snap)
    assert len(osm) == 131 and osm.crs.to_epsg() == 4326
    assert isinstance(osm["tags"].iloc[0], str)
    seg = load_overture_raw(snap)
    assert len(seg) == 11 and str(seg.crs) == "OGC:CRS84"
    photos = load_photos(snap)
    p0 = photos.set_index("photo_id").loc["panoramax_646ecfdd-ab57-4a28-b411-fb112ced3c97"]
    assert p0["heading"] == 0.0  # AC-18: 0 to północ, nie brak
    missing = photos.set_index("photo_id").loc["panoramax_5c501d68-11d1-4948-9cde-1cc00fb19184"]
    assert missing["heading"] is None
    links = load_links(snap)
    assert len(links) == 10
    signs, nearest = load_signs(snap)
    assert len(signs) == 8 and len(nearest) == 8
    assert "sign_value" not in signs.columns  # etykiety czyta tylko signs.evaluate


def test_crs_mismatch(snap_dir):
    path = snap_dir / "osm_roads.parquet"
    gdf = gpd.read_parquet(path).set_crs(2180, allow_override=True)
    gdf.to_parquet(path)
    manifest = json.loads((snap_dir / "sources.json").read_text(encoding="utf-8"))
    manifest["files"]["osm_roads.parquet"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    (snap_dir / "sources.json").write_text(json.dumps(manifest), encoding="utf-8")
    snap = verify_snapshot(snap_dir)
    with pytest.raises(InputError) as exc:
        load_osm(snap)
    assert exc.value.reason == "crs_mismatch"


def test_real_snapshot_counts(real_input):  # AC-03
    snap = verify_snapshot(real_input)
    assert snap.rows == {
        "osm_roads": 99768,
        "overture_segments": 85405,
        "photos": 561,
        "photo_road_links": 561,
    }
