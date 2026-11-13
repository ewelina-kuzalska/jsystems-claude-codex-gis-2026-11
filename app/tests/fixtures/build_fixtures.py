"""Buduje mini-snapshot z prawdziwych danych map-qa (plan T04, ADR-000 §10).

Uruchomienie (z katalogu app/): uv run python tests/fixtures/build_fixtures.py

Skrypt tylko czyta `course-materials/exercise-data/map-qa/` i zapisuje wycinki do
`tests/fixtures/map_qa/` (ten sam układ plików, własny `sources.json` z przeliczonymi hashami
i licznościami) oraz `tests/fixtures/PROVENANCE.md`. Wynik jest deterministyczny.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path

import geopandas as gpd
import pyarrow.compute as pc
import pyarrow.parquet as pq
from shapely.geometry import Point

APP = Path(__file__).resolve().parents[2]
SRC = APP.parent / "course-materials" / "exercise-data" / "map-qa"
OUT = APP / "tests" / "fixtures" / "map_qa"
RADIUS_M = 60.0

PHOTOS = [
    "panoramax_334a574d-18cb-4c2e-be3f-f99307e080d9",  # bez flag, miniatura offline
    "panoramax_646ecfdd-ab57-4a28-b411-fb112ced3c97",  # heading = 0.0, poor_heading_alignment
    "panoramax_0c05d025-f885-4006-8b93-c36481eb46f2",  # panorama_heading_ambiguous
    "panoramax_707ebe2f-8e75-4fb7-b8e2-b61f1f7b6549",  # camera_against_way_direction
    "panoramax_b35a913d-cbc1-48d5-95bb-140a77cc2f1f",  # boundary_crossing
    "panoramax_30f08d1e-fe31-42d9-b042-607f5237d9ff",  # service_way
    "panoramax_5c501d68-11d1-4948-9cde-1cc00fb19184",  # missing_heading (pusty heading)
    "panoramax_df4d3a9c-5fb6-427f-8c54-293ed6ea354b",  # no_osm_within_25m
    "mapillary_1127617272466620",  # overture_spatial_only (spatial_fallback)
    "panoramax_f0339c3f-3c1d-400f-bbcc-33d755a23899",  # ambiguous_candidates
]
SIGNS = [
    "mapillary_1237130608489136",  # maxspeed:forward 50 / backward 70, etykieta 50
    "mapillary_137982605041578",  # etykieta unreadable, OSM 140 + conditional
    "mapillary_1931009810597411",  # OSM 40, etykieta 20
    "mapillary_224324516912032",  # brak maxspeed (osm_missing_speed)
    "mapillary_915915556657317",  # osm_api Warszawa, outside_standard_25m
    "mapillary_491666962263649",  # osm_api Kraków
    "mapillary_305451881039193",  # etykieta uncertain
    "mapillary_1543264237143674",  # etykieta none, Łódź (osm_api)
]
SEGMENTS = [
    "00836247-b00a-40ea-99b0-703841eb9028",  # 3 reguły speed z between
    "009debd5-c2b6-4f7c-9742-b798fd175449",  # bezwarunkowa 70 + mode [bus, hgv] 50
    "a7b4060f-7450-4498-8e5c-2597699e692c",  # sources: w75390950@17 + inny way
    "34a9916c-f931-4812-8145-9006092e4169",  # sources: w75390950@17
]
EXTRA_OSM = [75390950, 907138970, 1362930293, 1446272667, 1491960205, 1491960207]  # PL:urban


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def filter_csv(name: str, ids: set[str]) -> int:
    """Kopiuje nagłówek i wiersze o danym photo_id bajt w bajt (pierwsza kolumna)."""
    lines = (SRC / name).read_bytes().decode("utf-8").splitlines(keepends=True)
    keep = [lines[0]] + [ln for ln in lines[1:] if ln.split(",", 1)[0] in ids]
    dest = OUT / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes("".join(keep).encode("utf-8"))
    return len(keep) - 1


def filter_parquet(name: str, column: str, values: list) -> int:
    table = pq.read_table(SRC / name)
    mask = pc.is_in(table[column], value_set=__import__("pyarrow").array(values))
    sub = table.filter(mask).sort_by(column)
    pq.write_table(sub, OUT / name, compression="zstd")
    return sub.num_rows


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "signs" / "crops").mkdir(parents=True)
    (OUT / "offline").mkdir(parents=True)

    photos = {r["photo_id"]: r for r in csv.DictReader((SRC / "photos.csv").open(encoding="utf-8"))}
    links = {
        r["photo_id"]: r
        for r in csv.DictReader((SRC / "photo_road_links.csv").open(encoding="utf-8"))
    }
    nearest = {
        r["photo_id"]: r
        for r in csv.DictReader((SRC / "signs" / "nearest_osm.csv").open(encoding="utf-8"))
    }
    signs = {
        r["photo_id"]: r
        for r in csv.DictReader((SRC / "signs" / "signs.csv").open(encoding="utf-8"))
    }

    # OSM: wszystkie drogi w promieniu 60 m od zdjęć i znaków + drogi wskazane jawnie
    osm = gpd.read_parquet(SRC / "osm_roads.parquet", columns=["osm_id", "geometry"])
    osm_2180 = osm.to_crs(2180)
    points = [Point(float(photos[p]["longitude"]), float(photos[p]["latitude"])) for p in PHOTOS]
    points += [
        Point(float(signs[s]["longitude"]), float(signs[s]["latitude"]))
        for s in SIGNS
        if nearest[s]["source"] == "osm_roads.parquet"
    ]
    pts = gpd.GeoSeries(points, crs=4326).to_crs(2180)
    osm_ids: set[int] = set(EXTRA_OSM)
    for pt in pts:
        osm_ids |= set(osm.loc[osm_2180.distance(pt) <= RADIUS_M, "osm_id"].astype(int))
    for p in PHOTOS:
        if links[p]["osm_way_id"]:
            osm_ids.add(int(links[p]["osm_way_id"]))

    segments = set(SEGMENTS) | {links[p]["overture_id"] for p in PHOTOS if links[p]["overture_id"]}
    seg_table = pq.read_table(SRC / "overture_segments.parquet", columns=["id", "sources"])
    for seg_id, sources in zip(
        seg_table["id"].to_pylist(), seg_table["sources"].to_pylist(), strict=True
    ):
        if seg_id in segments:
            for s in sources or []:
                rid = s.get("record_id") or ""
                if rid.startswith("w") and "@" in rid and rid[1:].split("@")[0].isdigit():
                    osm_ids.add(int(rid[1:].split("@")[0]))

    rows = {
        "osm_roads.parquet": filter_parquet("osm_roads.parquet", "osm_id", sorted(osm_ids)),
        "overture_segments.parquet": filter_parquet(
            "overture_segments.parquet", "id", sorted(segments)
        ),
        "photos.csv": filter_csv("photos.csv", set(PHOTOS)),
        "photo_road_links.csv": filter_csv("photo_road_links.csv", set(PHOTOS)),
    }
    for name in ("signs.csv", "nearest_osm.csv", "labels.csv"):
        filter_csv(f"signs/{name}", set(SIGNS))
    for s in SIGNS:
        shutil.copyfile(SRC / "signs" / "crops" / f"{s}.jpg", OUT / "signs" / "crops" / f"{s}.jpg")
    offline_ids = {
        r["photo_id"]
        for r in csv.DictReader((SRC / "offline" / "ATTRIBUTION.csv").open(encoding="utf-8"))
    } & set(PHOTOS)
    filter_csv("offline/ATTRIBUTION.csv", offline_ids)
    for p in sorted(offline_ids):
        shutil.copyfile(SRC / "offline" / f"{p}.jpg", OUT / "offline" / f"{p}.jpg")

    manifest = json.loads((SRC / "sources.json").read_text(encoding="utf-8"))
    manifest["osm"]["rows"] = rows["osm_roads.parquet"]
    manifest["overture"]["rows"] = rows["overture_segments.parquet"]
    manifest["photos"]["rows"] = rows["photos.csv"]
    manifest["links"]["rows"] = rows["photo_road_links.csv"]
    manifest["files"] = {
        name: {"bytes": (OUT / name).stat().st_size, "sha256": sha256(OUT / name)}
        for name in sorted(rows)
    }
    manifest["fixture_note"] = "Mini-snapshot testowy z prawdziwych danych (app/tests/fixtures)."
    (OUT / "sources.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    prov = [
        "# Pochodzenie fixture'ów (T04)",
        "",
        "Wycinki prawdziwych plików z `course-materials/exercise-data/map-qa/`, zbudowane przez",
        "`app/tests/fixtures/build_fixtures.py`. Nie edytuj ręcznie;",
        "zmień skrypt i zbuduj ponownie.",
        "",
        "| Plik fixture'a | Źródło | SHA-256 źródła | Wiersze |",
        "|---|---|---|---|",
    ]
    for name in sorted(rows):
        prov.append(f"| `map_qa/{name}` | `{name}` | `{sha256(SRC / name)}` | {rows[name]} |")
    for name in ("signs/signs.csv", "signs/nearest_osm.csv", "signs/labels.csv"):
        prov.append(f"| `map_qa/{name}` | `{name}` | `{sha256(SRC / name)}` | {len(SIGNS)} |")
    prov += [
        "",
        f"- Zdjęcia: {', '.join(f'`{p}`' for p in PHOTOS)}.",
        f"- Znaki (wycinki skopiowane bez zmian): {', '.join(f'`{s}`' for s in SIGNS)}.",
        f"- Segmenty Overture jawne: {', '.join(f'`{s}`' for s in SEGMENTS)} + segmenty z linków.",
        f"- Drogi OSM: wszystkie w promieniu {RADIUS_M:.0f} m od zdjęć i znaków (EPSG:2180), "
        "drogi z `sources` wybranych segmentów oraz `w75390950` i 5 dróg z `PL:urban`.",
        f"- Miniatury offline: {len(offline_ids)}.",
        "- `sources.json` to kopia manifestu z przeliczonymi `files` i `rows` dla mini-snapshotu.",
        "",
    ]
    (APP / "tests" / "fixtures" / "PROVENANCE.md").write_text(
        "\n".join(prov), encoding="utf-8", newline="\n"
    )
    print(rows, "offline", len(offline_ids))


if __name__ == "__main__":
    main()
