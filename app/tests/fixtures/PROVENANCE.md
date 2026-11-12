# Pochodzenie fixture'ów (T04)

Wycinki prawdziwych plików z `course-materials/exercise-data/map-qa/`, zbudowane przez
`app/tests/fixtures/build_fixtures.py`. Nie edytuj ręcznie; zmień skrypt i zbuduj ponownie.

| Plik fixture'a | Źródło | SHA-256 źródła | Wiersze |
|---|---|---|---|
| `map_qa/osm_roads.parquet` | `osm_roads.parquet` | `b429a97aef4e9e9f6c9cf760081a215eeb14cdc97b678812730a318b0e61d32b` | 131 |
| `map_qa/overture_segments.parquet` | `overture_segments.parquet` | `cf4ee780992cfab94eeda799ef6aa6ee67c86539d14aef572e937b35b8259760` | 11 |
| `map_qa/photo_road_links.csv` | `photo_road_links.csv` | `d71d0857ae0ffc3eeae395a67d2f9ea2bcb869e1fab44c222d2755e60e70763b` | 10 |
| `map_qa/photos.csv` | `photos.csv` | `9cc6b79f5fc147a774e43fb685db61b5bc3e2e2d15c38daa4cf665ba6e657e9c` | 10 |
| `map_qa/signs/signs.csv` | `signs/signs.csv` | `a3d3f29fa676c44e6be684abb9d3ea6f91bd439c81e4a373596a4de29e5a6c2f` | 8 |
| `map_qa/signs/nearest_osm.csv` | `signs/nearest_osm.csv` | `52baf1291906a5e86344198aea18bec724b38a5877a4a041e336a38df3e1dea3` | 8 |
| `map_qa/signs/labels.csv` | `signs/labels.csv` | `a25b37d9d65dd824413cfe1d6d9b797e951d179f3e87b89dd75789959046ca32` | 8 |

- Zdjęcia: `panoramax_334a574d-18cb-4c2e-be3f-f99307e080d9`, `panoramax_646ecfdd-ab57-4a28-b411-fb112ced3c97`, `panoramax_0c05d025-f885-4006-8b93-c36481eb46f2`, `panoramax_707ebe2f-8e75-4fb7-b8e2-b61f1f7b6549`, `panoramax_b35a913d-cbc1-48d5-95bb-140a77cc2f1f`, `panoramax_30f08d1e-fe31-42d9-b042-607f5237d9ff`, `panoramax_5c501d68-11d1-4948-9cde-1cc00fb19184`, `panoramax_df4d3a9c-5fb6-427f-8c54-293ed6ea354b`, `mapillary_1127617272466620`, `panoramax_f0339c3f-3c1d-400f-bbcc-33d755a23899`.
- Znaki (wycinki skopiowane bez zmian): `mapillary_1237130608489136`, `mapillary_137982605041578`, `mapillary_1931009810597411`, `mapillary_224324516912032`, `mapillary_915915556657317`, `mapillary_491666962263649`, `mapillary_305451881039193`, `mapillary_1543264237143674`.
- Segmenty Overture jawne: `00836247-b00a-40ea-99b0-703841eb9028`, `009debd5-c2b6-4f7c-9742-b798fd175449`, `a7b4060f-7450-4498-8e5c-2597699e692c`, `34a9916c-f931-4812-8145-9006092e4169` + segmenty z linków.
- Drogi OSM: wszystkie w promieniu 60 m od zdjęć i znaków (EPSG:2180), drogi z `sources` wybranych segmentów oraz `w75390950` i 5 dróg z `PL:urban`.
- Miniatury offline: 8.
- `sources.json` to kopia manifestu z przeliczonymi `files` i `rows` dla mini-snapshotu.
