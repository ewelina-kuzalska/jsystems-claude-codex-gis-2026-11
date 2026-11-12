"""AC-32–AC-35; ADR-004 §3.6, D-401, D-403, TAC-004-02."""

import csv
import io
import json

from shapely.geometry import LineString, Point

from map_qa.export import PROPERTIES, export_csv, export_geojson
from map_qa.model import Candidate
from map_qa.tasks import build_tasks

META = {
    "osm_extract_date": "2026-11-01T21:21:36Z",
    "overture_release": "2026-10-21.0",
    "snapshot_created_at": "2026-11-02T23:52:58.440512+00:00",
    "threshold": 0.7,
}


def tasks():
    return build_tasks(
        [
            Candidate(
                check="C1",
                reason_code="missing_lit",
                osm_id=5,
                photo_id="p1",
                photo_url="https://example.org/p1",
                photo_author="Łukasz Ćma",
                photo_license="CC-BY-SA-4.0",
                osm_raw='{"name":"Świętego Wawrzyńca","highway":"residential"}',
                description_pl="Brak oświetlenia; wymaga sprawdzenia.",
                geometry=LineString([(19.93730001234, 50.0614), (19.9383, 50.0614)]),
            ),
            Candidate(
                check="C3",
                reason_code="uncertain_link",
                osm_id=7,
                photo_id="p2",
                distance_m=3.1,
                uncertain_link=True,
                file_flags=("ambiguous_candidates", "service_way"),
                own_flags=("restricted_access",),
                geometry=Point(19.95, 50.05),
            ),
        ]
    )


def test_geojson_rfc7946(tmp_path):
    out = tmp_path / "tasks.geojson"
    export_geojson(tasks(), META, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["type"] == "FeatureCollection"
    assert "crs" not in data
    assert data["metadata"]["overture_release"] == "2026-10-21.0"
    assert "OpenStreetMap" in data["metadata"]["attribution"]
    ids = [f["properties"]["task_id"] for f in data["features"]]
    assert len(ids) == len(set(ids)) == 2
    for f in data["features"]:
        assert list(f["properties"]) == PROPERTIES  # TAC-004-02
        coords = f["geometry"]["coordinates"]
        pts = coords if f["geometry"]["type"] == "LineString" else [coords]
        for lon, lat in pts:
            assert 19.8 <= lon <= 20.15 and 49.95 <= lat <= 50.15
            assert len(repr(lon).split(".")[1]) <= 7
    assert data["features"][0]["geometry"]["coordinates"][0][0] == 19.9373
    assert "Świętego" in out.read_text(encoding="utf-8")  # ensure_ascii=False
    assert b"\r\n" not in out.read_bytes()


def test_csv_matches_geojson(tmp_path):
    export_geojson(tasks(), META, tmp_path / "tasks.geojson")
    export_csv(tasks(), tmp_path / "tasks.csv")
    raw = (tmp_path / "tasks.csv").read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # utf-8-sig
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    feats = json.loads((tmp_path / "tasks.geojson").read_text(encoding="utf-8"))["features"]
    assert [r["task_id"] for r in rows] == [f["properties"]["task_id"] for f in feats]
    for r, f in zip(rows, feats, strict=True):
        for key in PROPERTIES:
            value = f["properties"][key]
            expected = (
                ""
                if value is None
                else (str(value).lower() if isinstance(value, bool) else str(value))
            )
            assert r[key] == expected, key
        assert "OpenStreetMap" in r["attribution"]
    assert rows[1]["file_flags"] == "ambiguous_candidates;service_way"
    assert float(rows[1]["lon"]) == 19.95 and float(rows[1]["lat"]) == 50.05
    assert 19.937 < float(rows[0]["lon"]) < 19.939  # środek linii
    assert rows[0]["photo_author"] == "Łukasz Ćma"


def test_empty_export(tmp_path):
    export_geojson([], META, tmp_path / "t.geojson")
    export_csv([], tmp_path / "t.csv")
    assert json.loads((tmp_path / "t.geojson").read_text(encoding="utf-8"))["features"] == []
    lines = (tmp_path / "t.csv").read_text(encoding="utf-8-sig").splitlines()
    assert len(lines) == 1 and lines[0].startswith("task_id,")


def test_export_is_byte_stable(tmp_path):
    export_geojson(tasks(), META, tmp_path / "a.geojson")
    export_geojson(tasks(), META, tmp_path / "b.geojson")
    assert (tmp_path / "a.geojson").read_bytes() == (tmp_path / "b.geojson").read_bytes()
