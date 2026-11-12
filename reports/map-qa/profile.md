# Profil danych Map QA (krok M2)

**Data profilu:** 2026-11-12
**Snapshot:** `course-materials/exercise-data/map-qa/` (manifest `sources.json`, `created_at` 2026-11-02T23:52:58Z)
**OSM extract:** 2026-11-01T21:21:36Z (Geofabrik małopolskie) · **Overture release:** 2026-10-21.0
**Powiązane:** [PRD](../../docs/PRD.md), [ADR-000](../../docs/ADR/000-main-architecture.md)–[ADR-004](../../docs/ADR/004-report-export.md)

## Polecenia i wersje

Źródła wiedzy: `course-materials/exercise-data/map-qa/README.md`, `profile.sql`, `sources.json`, `DATABRICKS.md`. Wszystkie polecenia tylko czytają dane, nie zmieniają wejść i nie wywołują płatnego API.

| Narzędzie | Wersja |
|---|---|
| uv | 0.13.7 (winget) |
| Python (uv) | 3.12.16 |
| DuckDB (skrypty profilu, PEP 723) | 1.5.6. Aplikacja przypina 2.0.0 (ADR-000) |
| GeoPandas / pyarrow (kontrola z README) | 1.2.0 / 23.0.1 |
| Pillow (`build_signs.py`) | 12.0.0, wg README danych |
| Databricks CLI | 1.26.0, profil `map-qa`, SQL Statement Execution API 2.0 |

```bash
# 1. Profil kursowy (course-materials/exercise-data/map-qa/profile.sql)
PYTHONUTF8=1 uv run --python 3.12 course-materials/exercise-data/map-qa/profile_data.py

# 2. Zapytania dodatkowe (struktury Overture, relacje kluczy, formaty tagów prędkości, znaki)
PYTHONUTF8=1 uv run --python 3.12 reports/map-qa/profile_extra.py course-materials/exercise-data/map-qa

# 3. GeoPandas: CRS, poprawność geometrii, transformacja do EPSG:2180 (z README danych)
uv run --python 3.12 --with geopandas==1.2.0 --with pyarrow==23.0.1 python -c "import geopandas as gpd; r=gpd.read_parquet('course-materials/exercise-data/map-qa/osm_roads.parquet'); print(len(r), r.crs, r.geometry.is_valid.all(), r.to_crs(2180).crs)"

# 4. Weryfikacja zestawu signs/ offline (hashe, spójność ID), bez tokenu i sieci
uv run --python 3.12 course-materials/exercise-data/map-qa/signs/build_signs.py --verify-only

# 5. Databricks: liczności workspace.map_qa (§8). Git Bash wymaga MSYS_NO_PATHCONV=1
MSYS_NO_PATHCONV=1 databricks api post /api/2.0/sql/statements --profile map-qa --json '{...}'
```

Sekrety: sprawdzano tylko obecność `~/.databrickscfg` (profil `map-qa`) i `DATABRICKS_SQL_WAREHOUSE_ID`, nigdy ich wartości. Na Windows `PYTHONUTF8=1` jest potrzebne przy przekierowaniu wyjścia do pliku. Bez tego tabele DuckDB (znaki ramek Unicode) dają `UnicodeEncodeError` w cp1250.

---

## 1. Liczności i integralność

| Wejście | Wiersze | Manifest | Uwagi |
|---|---:|---:|---|
| `osm_roads.parquet` | 99 768 | 99 768 ✓ | `osm_id` unikalne, 0 niepoprawnych geometrii, `GEOMETRY('EPSG:4326')` |
| `overture_segments.parquet` | 85 405 | 85 405 ✓ | `id` unikalne, 0 niepoprawnych geometrii, `GEOMETRY('OGC:CRS84')` |
| `photos.csv` | 561 | 561 ✓ | Panoramax 461, Mapillary 100 |
| `photo_road_links.csv` | 561 | 561 ✓ | 558 z kandydatem OSM, 558 z Overture |
| `signs/signs.csv` | 119 | — | Brak w `sources.json` → `hash_not_in_manifest` (ADR-001 §3.1) |
| `signs/crops/*.jpg` | 119 | — | Wszystkie hashe zgodne z `crop_sha256` |
| `signs/` (całość) | 119 | — | `build_signs.py --verify-only`: `checked=119 missing=0`, exit 0 |
| `offline/` | 40 miniatur | 40 ✓ | `offline/ATTRIBUTION.csv` ma 40 wierszy |
| `reference_labels.csv` | 320 (100 zdjęć × pytania) | — | para (`photo_id`, `question`) unikalna |
| `traffic_signs.geojson` | 1 730 | 1 730 ✓ | 12 klas `maximum-speed-limit-N` (5–110) |

**GeoPandas (README danych):** OSM 99 768, CRS EPSG:4326, `is_valid.all() = True`, `to_crs(2180)` → EPSG:2180. Overture 85 405, CRS `OGC:CRS84`, `is_valid.all() = True`. GeoPandas zwraca CRS OSM jako pełny PROJJSON, a nie napis `EPSG:4326`. Kontrola `crs_mismatch` (ADR-002 §3.1) musi więc porównywać obiekty `pyproj.CRS` (`==` lub `to_epsg()`), a nie napisy.

### Duplikaty i relacje kluczy

| Plik / relacja | Wynik |
|---|---|
| `photo_id` unikalne w `photos`, `photo_road_links`, `signs`, `nearest_osm`, `labels`, `offline/ATTRIBUTION` | ✓ 0 duplikatów |
| `photo_road_links` ↔ `photos` | 1:1, 0 sierot w obu kierunkach (561/561) |
| `offline/ATTRIBUTION` → `photos` | 0 sierot (40/40) |
| `reference_labels` → `photos` | 0 sierot (100 zdjęć) |
| `nearest_osm`, `labels` ↔ `signs` | 1:1, 0 sierot (119/119) |
| `signs` ∩ `photos.csv` | 3 wspólne `photo_id`. Zestaw `signs/` jest osobną próbką |
| `photo_road_links.osm_way_id` → `osm_roads` | 0 sierot (558) |
| `photo_road_links.overture_id` → `overture_segments` | 0 sierot (558) |
| **`signs/nearest_osm.osm_way_id` → `osm_roads`** | **24 sieroty / 119**. Te way pochodzą z OSM API, spoza snapshotu (§5) |

**Pliki w `sources.json.files`:** `osm_roads.parquet`, `osm_roads_sample.geojson`, `overture_segments.parquet`, `photos.csv`, `photo_road_links.csv`, `reference_labels.csv`, `traffic_signs.geojson`, `mapillary_detections.json.gz`. Pliki z `signs/` **nie mają hashy w manifeście**.

**Katalog `data/`** (pobrane zdjęcia z `download_photos.py`) nie istnieje. Raport ma więc miniatury tylko dla 40 zdjęć z `offline/`. Pozostałe dostaną „Obraz niedostępny lokalnie” i link (PRD 4.4).

---

## 2. OSM (`osm_roads.parquet`)

### Schemat
`osm_id` BIGINT, `osm_version`, `osm_timestamp`, `node_ids` BIGINT[], `start_node`, `end_node`, `boundary_crossing` BOOLEAN, **`tags` VARCHAR (pełny JSON)**, oraz kolumny wyciągnięte z tagów: `highway`, `maxspeed`, `surface`, `lanes`, `oneway`, `lit`, `sidewalk`, `sidewalk:left`, `sidewalk:right`, `junction`, `ref`, `name`, `geometry`.

- Kolumna z pełnymi tagami nazywa się **`tags`**. ADR używa nazwy modelu `tags_raw`, co jest w porządku, ale odczyt musi brać `tags`.
- `maxspeed` w kolumnie jest identyczny z `tags.maxspeed` (0 rozbieżności).

### Pokrycie atrybutów per `highway` (C1)

| highway | drogi | maxspeed | surface | lanes | lit |
|---|---:|---:|---:|---:|---:|
| service | 72 113 | 1 997 | 17 390 | 849 | 3 379 |
| residential | 11 799 | 5 467 | 9 598 | 2 334 | 5 103 |
| track | 4 296 | 2 | 1 657 | 0 | 86 |
| tertiary | 3 838 | 2 839 | 3 772 | 2 888 | 2 451 |
| secondary | 2 073 | 1 897 | 2 065 | 2 015 | 1 633 |
| living_street | 1 938 | 1 140 | 1 524 | 109 | 638 |
| primary | 1 586 | 1 539 | 1 584 | 1 562 | 1 260 |
| unclassified | 880 | 316 | 770 | 342 | 331 |
| motorway | 459 | 453 | 453 | 454 | 213 |
| motorway_link | 229 | 192 | 226 | 214 | 116 |
| secondary_link | 180 | 142 | 178 | 166 | 166 |
| trunk | 147 | 143 | 129 | 143 | 45 |
| primary_link | 127 | 110 | 127 | 119 | 116 |
| trunk_link | 54 | 21 | 44 | 42 | 9 |
| tertiary_link | 46 | 32 | 46 | 36 | 42 |
| road | 2 | 0 | 2 | 0 | 1 |
| busway | 1 | 0 | 1 | 0 | 0 |

`service` to 72% dróg, a tylko ok. 3% z nich ma `maxspeed`. Podsumowanie C1 będzie przez to zdominowane przez `service`, dlatego w raporcie warto pokazać klasy główne osobno.

### `maxspeed`

- **Wszystkie** wartości `maxspeed` (16 290 dróg) to liczby całkowite bez jednostki (16 różnych: 4–140). W samym `maxspeed` nie ma `mph`, `PL:urban`, `none`, `signals` ani wartości wielokrotnych.
- **Formaty wszystkich kluczy `maxspeed*` w pełnym JSON `tags`:**

  | Klucz | Wartości | Liczba km/h | mph | Kod strefy `XX:…` | `none`/`signals`/`walk` | Wiele (`;`/`\|`) | Składnia `@` |
  |---|---:|---:|---:|---:|---:|---:|---:|
  | `maxspeed` | 16 290 | 16 290 | 0 | 0 | 0 | 0 | 0 |
  | `maxspeed:forward` | 261 | 260 | 0 | **1** (`PL:urban`) | 0 | 0 | 0 |
  | `maxspeed:backward` | 247 | 243 | 0 | **4** (`PL:urban`) | 0 | 0 | 0 |
  | `maxspeed:conditional` | 92 | 0 | 0 | 0 | 0 | 0 | 92 |
  | `maxspeed:type` | 2 578 | 0 | 0 | 2 325 | 0 | 0 | 0 |
  | `maxspeed:hgv` / `:bus` / `:trailer` (+ `:forward`/`:backward`) | 1 007 / 1 031 / 1 028 (+53) | wszystkie | 0 | 0 | 0 | 0 | 0 |
  | `maxspeed:variable` | 82 | 0 | 0 | 0 | 0 | 0 | 0 |
  | `maxspeed:lanes` | 10 | 0 | 0 | 0 | 0 | **10** (`\|`) | 0 |

- **`PL:urban` występuje w danych**: 5 tagów kierunkowych. Ścieżka parsera `not_numeric / zone` (AC-07) zadziała więc na prawdziwych drogach. Mph, `none`, `signals` i wartości wielokrotne w kluczach prędkości dla C2 nie występują, więc te ścieżki testujemy syntetycznie (TAC-001-01).
- `maxspeed:conditional` ma zawsze jedną postać: **`110 @ (Mo-Fr 06:00-18:00)`** (92 drogi).
- Kontekst prędkości (bez `value_kmh`, ADR-001 §3.2): `maxspeed:type` (PL:urban 1 603, PL:zone30 564, sign 253, PL:zone40 59, PL:rural 55, PL:zone20 27, PL:living_street 12, PL:zone 5), `source:maxspeed` (m.in. PL:urban 4 371, PL:zone30 3 033, sign 2 090), `zone:maxspeed` (PL:30, 19 dróg).
- Klucze pojazdowe (`maxspeed:hgv`, `:bus`, `:trailer`) i `maxspeed:lanes` są **poza listą kluczy C2** w ADR-001 §3.2. Zostają tylko w `tags_raw`.
- `boundary_crossing = true`: 560 dróg.

### `surface`: wartości (36 różnych)

asphalt 23 313 · paving_stones 7 631 · gravel 1 395 · concrete 1 153 · ground 1 050 · paved 846 · unpaved 795 · grass 672 · dirt 581 · fine_gravel 451 · sett 443 · compacted 437 · concrete:plates 396 · grass_paver 196 · pebblestone 73 · cobblestone 30 · concrete:lanes 24 · sand 18 · mud 14 · unhewn_cobblestone 9 · earth 8 · wood 6 · concrete_slabs 6 · rock 3 · contrete:plates 3 · metal_grid 2 · metal 2 · conrete:plates 1 · utwardzona 1 · bad 1 · ompacted 1 · kostka\_/\_płyty_chodnikowex 1 · paving_Stones 1 · grass/dirt 1 · bricks 1 · concrete:slabs 1

**Spoza listy startowej ADR-001 §3.4** (dostaną `unknown`, jeśli nie zdecydujemy inaczej): `concrete_slabs` (6), `metal_grid` (2), `concrete:slabs` (1) oraz literówki i wartości lokalne: `contrete:plates`, `conrete:plates`, `ompacted`, `paving_Stones`, `utwardzona`, `kostka_/_płyty_chodnikowex`, `grass/dirt`, `bad`. Razem 11 wartości, 19 dróg. Raport i tak ma pokazać listę takich wartości (ADR-001 §3.4).

### Flagi kontekstu dla C3 (z `tags`)

| Warunek | Drogi |
|---|---:|
| `access` ∈ {private, no, customers, delivery, permit} (`restricted_access`) | 15 394 |
| `bridge` obecny | 781 |
| `tunnel` obecny | 827 |
| `layer` ≠ 0 | 1 207 |

---

## 3. Overture (`overture_segments.parquet`)

### Schemat (pola istotne dla ADR-001)

```
speed_limits  STRUCT(min_speed STRUCT(value INTEGER, unit VARCHAR),
                     max_speed STRUCT(value INTEGER, unit VARCHAR),
                     is_max_speed_variable BOOLEAN,
                     "when" STRUCT(during VARCHAR, heading VARCHAR, "using" VARCHAR[],
                                   recognized VARCHAR[], "mode" VARCHAR[],
                                   vehicle STRUCT(dimension, comparison, value, unit)[]),
                     "between" DOUBLE[])[]
road_surface  STRUCT("value" VARCHAR, "between" DOUBLE[])[]          -- BEZ "when"
sources       STRUCT(property, dataset, license, record_id, update_time,
                     confidence DOUBLE, "between" DOUBLE[], provider, resource, "version")[]
```

Pozostałe kolumny: `id`, `geometry`, `class`, `subclass`, `name`, `connectors`, `road_flags`, `access_restrictions`, `level_rules`, `bbox`, `version`.

Nazwy pól z ADR-001 §3.3 (`max_speed.value`, `max_speed.unit`, `when`, `when.heading`, `between`, `is_max_speed_variable`) **zgadzają się**. W SQL `when`, `between`, `using`, `mode` i `value` trzeba cytować (`s['when']`) albo pisać `"when"`, bo to słowa kluczowe DuckDB.

### Klasy i pokrycie regułami (C1)

| class | segmenty | z regułą speed | z regułą surface |
|---|---:|---:|---:|
| service | 60 968 | 1 624 | 14 027 |
| residential | 11 185 | 5 129 | 8 781 |
| track | 3 663 | 2 | 1 321 |
| tertiary | 3 102 | 2 180 | 3 032 |
| living_street | 2 278 | 1 378 | 1 768 |
| secondary | 1 335 | 1 192 | 1 303 |
| primary | 916 | 840 | 896 |
| unknown | 844 | 2 | 8 |
| unclassified | 816 | 262 | 704 |
| motorway | 211 | 172 | 187 |
| trunk | 87 | 66 | 81 |

Overture nie ma klas `*_link`, a ma `unknown`. Klasy OSM i Overture nie są wymienne, dlatego podsumowanie C1 pokazujemy osobno dla każdego źródła.

### `speed_limits`

- **Reguły na segment:** 1 → 11 936 segmentów, 2 → 647, 3 → 169, 4 → 45, 5 → 30, 6 → 16, 7 → 1, 9 → 1, 13 → 2. Łącznie **14 205 reguł**, co potwierdza wymóg AC-05 (jedna reguła = jeden rekord).
- `max_speed.unit`: **wyłącznie `km/h`**. `min_speed` nigdy nie występuje. `is_max_speed_variable = true`: 16 reguł.
- `when` niepuste: 880 reguł. Najczęstsze postacie:

  | `when` | reguły | Klasyfikacja (ADR-001) |
  |---|---:|---|
  | `mode: [bus, hgv]` | 395 | warunkowa |
  | `heading: forward` | 212 | bezwarunkowa, kierunkowa |
  | `heading: backward` | 209 | bezwarunkowa, kierunkowa |
  | `mode: [bus]` | 23 | warunkowa |
  | `during: "Mo-Fr06:00-18:00"` | 19 | warunkowa |
  | `mode: [hgv]` | 9 | warunkowa |
  | `heading` + `mode` | 13 | warunkowa |

- `between` niepuste: 1 925 reguł (`partial_segment`). Typowy wzorzec to kilka reguł pokrywających kolejne odcinki, np. `[0, 0.064]` = 40 i `[0.064, 1]` = 30.
- Często występuje para „reguła bezwarunkowa + reguła `mode: [bus, hgv]`” (np. segment `009debd5-…`: 70 dla wszystkich, 50 dla bus/hgv). Do porównania kwalifikuje się tylko reguła bezwarunkowa, więc taka para **nie** daje `multiple_rules`.
- Wartości: 50 (4 651), 30 (4 473), 20 (2 150), 40 (1 403), 70 (703), 80 (188), 10 (158), 90 (151), 60 (100), 100 (71), 140 (60), 120 (38), 5 (28), 110 (19), 25 (7), 15 (2), 4 (2), 75 (1).

### `road_surface`

- **Brak pola `when`**, są tylko `value` i `between`. Każda reguła nawierzchni jest bezwarunkowa, a jedynym powodem „not comparable” jest `partial_segment`.
- Reguły na segment: 1 → 30 677, 2 → 1 148, 3 → 236, 4 → 34, 5 → 11, 6 → 2.
- **Wartości (komplet):**

  | value | reguły | z `between` | Proponowana rodzina |
  |---|---:|---:|---|
  | paved | 21 041 | 1 944 | paved |
  | paving_stones | 7 574 | 1 426 | paved |
  | unpaved | 2 886 | 715 | unpaved |
  | gravel | 1 789 | 554 | unpaved |
  | dirt | 539 | 133 | unpaved |
  | unknown | 53 | 16 | unknown |
  | metal | 2 | 2 | paved |

### `sources` (pary dla C2)

| dataset | prefiks `record_id` | wpisy | wzorzec `w<id>@<ver>` |
|---|---|---:|---:|
| OpenStreetMap | `w` | 106 274 | 106 270 |
| OpenStreetMap | `r` | 1 854 | 0 |
| TomTom | — | 791 | 0 |

- Segmenty z referencją do way: **84 611 / 85 405** (99,1%). Way obecny w snapshocie: 84 385.
- Pary (segment, way): 106 270, z czego 105 809 ma way w snapshocie. Jeden segment bywa zbudowany z kilku way.
- 4 wpisy z prefiksem `w` nie pasują do `w<liczba>@<wersja>`. Parser z ADR-001 §3.3 je odrzuci, co jest poprawne.
- `sources[].between` występuje (np. `w75390950@17`, `[0.0, 0.2996]`), czyli way pokrywa tylko część segmentu. **ADR-001 tego nie opisuje** (punkt otwarty w §7).
- Udział segmentów bez referencji OSM to ok. 0,9%, daleko od progu 20% z D-103.

---

## 4. Zdjęcia i linki (C3)

### `photos.csv`

| source | zdjęcia | sekwencje | `heading` pusty | `heading = 0` | `is_panorama` |
|---|---:|---:|---:|---:|---:|
| Panoramax | 461 | 56 | 15 | 21 | 31 |
| Mapillary | 100 | 52 | 0 | 2 | 0 |

- 15 pustych `heading` odpowiada 15 flagom `missing_heading` w linkach.
- 23 zdjęcia mają `heading = 0.0`. To **północ, a nie brak** (AC-18). Test musi to pokryć na prawdziwym wierszu, np. `panoramax_646ecfdd-…`.
- Wszystkie zdjęcia mają `author` i `license` (CC-BY-SA-4.0). Pole `transformation` mówi m.in. „EXIF removed”.

### `photo_road_links.csv`

- `match_method`: `osm_source_reference` 557, `spatial_fallback` 1, `none` 3.
- `distance_m`: min 0,0 · mediana 2,43 · p95 9,82 · max 22,17 m.
- `bearing_diff` mieści się w 0–88,6° (nieskierowany, 0–90). `directed_bearing_diff` mieści się w 0–179,9° (skierowany). Zgadza się z `sources.json.links`.
- `candidate_flags` są rozdzielane znakiem **`;`**. Zdjęcia z ≥ 1 flagą: **146 / 561** (przed dodaniem flag własnych z ADR-002).

| Flaga z pliku | Linki |
|---|---:|
| ambiguous_candidates | 65 |
| camera_against_way_direction | 35 |
| panorama_heading_ambiguous | 31 |
| boundary_crossing | 27 |
| poor_heading_alignment | 27 |
| missing_heading | 15 |
| service_way | 14 |
| no_osm_within_25m | 3 |
| overture_spatial_only | 1 |

Wszystkie 9 flag z AC-16 występuje w danych.

---

## 5. Znaki (C4)

### `signs/signs.csv`
- 119 wycinków, wszystkie z Mapillary. `compass_angle` wypełniony w 100%. `build_signs.py --verify-only` daje 119/119 zgodnych.
- **Obszar (README: zestaw `signs/` „może obejmować inne obszary Polski”):**

  | `area` | Źródło kontekstu OSM (`nearest_osm.source`) | Znaki | Dystans > 25 m | Max dystans |
  |---|---|---:|---:|---:|
  | Kraków | `osm_roads.parquet` | 95 | 2 | 28,5 m |
  | Warszawa | `osm_api` | 11 | 2 | 102,9 m |
  | Poznań | `osm_api` | 6 | 0 | 5,0 m |
  | Kraków | `osm_api` | 4 | 0 | 3,6 m |
  | Łódź, Wrocław, Gdańsk | `osm_api` | 1 + 1 + 1 | 0 | 3,6 m |

  Tylko **95 / 119** znaków leży w bbox Krakowa z PRD i ma way w `osm_roads.parquet`. Dla pozostałych 24 kontekst OSM pochodzi z oficjalnego OSM API (pobrany przez autora danych, bez daty snapshotu, z polem `context_retrieved_at`). Ich way **nie istnieje w snapshocie**, więc nie mamy ich geometrii do stycznej (ADR-002 §3.4) ani pełnych `tags`. Są tylko surowe kolumny prędkości z `nearest_osm.csv`.
- `mapillary_value`: 92 wiersze z `regulatory--maximum-speed-limit-<N>--g1` (N = 20–120). Pozostałe to inne znaki (`no-entry`, `speed-limit-zone`, `weight-limit`, `end-of-*`, `no-overtaking`, `no-stopping`) albo `NULL` (6).
- **Wycinki:** 119/119 JPEG, hash = `crop_sha256`, **0 z segmentem APP1 (EXIF/XMP)**. Kontrola fail-closed z D-304 nie zablokuje żadnego wycinka.

### `signs/nearest_osm.csv`
- 119 wierszy, każdy z `osm_way_id`. 24 z nich nie ma w `osm_roads.parquet` (`source = osm_api`, wyżej).
- Promień: podstawowy 25 m, awaryjny 100 m (README danych). 4 kandydatów leży dalej niż 25 m (flaga `outside_standard_25m`), najdalszy 102,9 m.
- **`heading_diff_deg` ma zakres 0,01–87,86°, więc jest nieskierowany (0–90).** To potwierdza D-204: kierunek liczymy sami z `compass_angle` i stycznej way.
- `maxspeed` wypełniony: 97. Bez wartości: 22, które w C4 dadzą `osm_missing_speed`. Z tagami kierunkowymi: **tylko 2**. Z `maxspeed_conditional`: 9.
- `match_flags` (rozdzielane `;`), wiersze z flagą: 44 / 119. Występują `ambiguous_candidates`, `poor_heading_alignment`, `service_way` i **`outside_standard_25m` (4 wiersze)**. Tej ostatniej flagi **nie ma na liście AC-16** (punkt otwarty w §7).

### `signs/labels.csv`
Kolumny: `photo_id`, `sign_value`, `status`, `method`, `reviewers`, `note`, `negative_type`.

| `sign_value` | `status` | wiersze | `negative_type` |
|---|---|---:|---|
| liczba (20–120) | certain | 89 | — |
| `none` | certain | 25 | no_speed_sign 6, no_entry 4, zone_end 4, weight 2, no_overtaking 2, cancelled_sign 2, false_positive_object 2, zone 1, no_stopping 1, limit_end 1 |
| `none` | uncertain | 4 | zone 3, weight 1 |
| `unreadable` | certain | 1 | unreadable |

- **Mapowanie ma iść po `sign_value`, nie po `negative_type`.** ADR-003 §3.9 mówi: „wiersz z `negative_type` → `none`”. To błąd, bo `unreadable` też ma `negative_type`.
- Mianownik accuracy (`status = certain`): **115**. Etykiety `uncertain`: 4, raportowane osobno.
- Wszystkie wartości liczbowe mieszczą się w opcjach kroku 1 (10–140 co 10), więc w tej próbce `other` nie wystąpi.
- **Pochodzenie etykiet (README danych):** odczyt agenta Codex i niezależny odczyt modelu GLM-5.3-Flash. `certain` oznacza **zgodność dwóch modeli, nie pewność terenową**. To robocza referencja, nie ground truth. Raport accuracy (AC-28) musi to zaznaczyć.

### `reference_labels.csv` (w manifeście)
To osobny zbiór: etykiety wizualne **zdjęć** z `photos.csv`, 320 wierszy dla 100 zdjęć (`question` ∈ {`surface`, `junction_visible`, `street_lighting_visible`, `speed_limit_value`}, `label`, `status`, `reviewer`). Etykiety przygotował agent Codex, bez pełnej weryfikacji przez człowieka. Dotyczy atrybutów, których MVP nie czyta z obrazów (PRD §7, „Other visual attributes”). **Poza zakresem MVP.** Nie mylić z `signs/labels.csv`.

---

## 6. Rozstrzygnięcia punktów „do potwierdzenia w profilu”

| ADR | Punkt | Wynik profilu |
|---|---|---|
| 001 §3.3 | Nazwy pól `speed_limits` | ✓ Zgodne: `max_speed.{value,unit}`, `when.heading`, `between`, `is_max_speed_variable` |
| 001 §3.3 | `road_surface` ma `when`/`between` | ✗ **Tylko `between`**, bez `when` |
| 001 §3.4 | Wartości Overture `road_surface` | 7 wartości. Proponowane mapowanie w §3 |
| 001 §3.4 | Wartości OSM `surface` spoza listy | 11 wartości / 19 dróg → `unknown` |
| 001 / AC-06/07 | Formaty `maxspeed` OSM | `maxspeed`: same liczby. **`PL:urban` w 5 tagach kierunkowych**. `:conditional` zawsze `110 @ (Mo-Fr 06:00-18:00)`. Mph, `none`, `signals` i wiele wartości tylko w testach syntetycznych |
| 002 §3.1 | CRS z metadanych GeoParquet | OSM EPSG:4326 (PROJJSON), Overture OGC:CRS84. Porównanie przez `pyproj.CRS` |
| 002 §3.4 | Kontekst OSM znaków | 95 / 119 w snapshocie, 24 z OSM API spoza snapshotu (pytanie 1 w §10) |
| 001 / D-102 | Segment z ≥ 2 regułami do fixture'a | Np. `00836247-b00a-40ea-99b0-703841eb9028` (3 reguły z `between`), `009debd5-c2b6-4f7c-9742-b798fd175449` (bezwarunkowa + `mode`) |
| 001 / D-103 | Udział segmentów bez referencji OSM | ok. 0,9% (próg 20%) |
| 002 §3.4 / D-204 | Zakres `heading_diff_deg` | **0–90 (nieskierowany)**. D-204 bez zmian |
| 003 §3.9 | Kodowanie `labels.csv` | `sign_value` ∈ {liczba, `none`, `unreadable`}, `status` ∈ {certain, uncertain} |
| 003 / D-304 | Metadane w wycinkach | Brak (0/119 z APP1) |
| 000 / ADR-001 §3.1 | Hashe plików `signs/` w manifeście | Brak → ścieżka `hash_not_in_manifest` |

---

## 7. Punkty otwarte (decyzja przed implementacją danego etapu)

Punkty 1–5 rozstrzygnięto w aktualizacji ADR z 2026-11-12.

1. ✅ **`sources[].between` w Overture** (C2): way może pokrywać tylko część segmentu. Przyjęto wariant (b), nowy kod „not comparable” `partial_source` (ADR-001 §3.3, §3.6).
2. ✅ **Mapowanie `surface`:** dopisano `concrete_slabs`, `concrete:slabs`, `metal_grid` → paved. Literówki zostają `unknown`. Dodano mapowanie Overture (ADR-001 §3.4).
3. ✅ **Flaga `outside_standard_25m`:** przenoszona jak każda flaga z `match_flags` (ADR-002 §3.4).
4. ✅ **Mapowanie etykiet** po `sign_value` (ADR-003 §3.9).
5. ✅ **`road_surface` bez `when`**, kolumna OSM `tags` (ADR-001 §3.2, §3.3).
6. ⏳ **Miniatury:** bez uruchomienia `download_photos.py` raport ma obrazy tylko dla 40 zdjęć `offline/` i 119 wycinków znaków (pytanie 2 w §10).
7. ⏳ **Znaki spoza snapshotu:** 24 / 119 znaków ma kontekst OSM z OSM API (pytanie 1 w §10).
8. ⏳ **Etykieta `unreadable` w ewaluacji:** decyzja dopisana w ADR-003 §3.9 do akceptacji (pytanie 3 w §10).

---

## 8. Kontrola zgodności z Databricks (ADR-000, D-02)

**Data:** 2026-11-12 · **Źródło:** `workspace.map_qa` (SQL Statement Execution API 2.0, Databricks CLI v1.26.0, profil `map-qa`). Kontrola ręczna, poza pipeline'em.

| Miara | Databricks | Lokalnie | Wynik |
|---|---:|---:|---|
| `osm_roads` | 99 768 | 99 768 | ✓ |
| `overture_segments` | 85 405 | 85 405 | ✓ |
| `photos` | 561 | 561 | ✓ |
| `photo_road_links` | 561 | 561 | ✓ |
| `traffic_signs` | 1 730 | 1 730 (`traffic_signs.geojson`) | ✓ |
| `photos.heading IS NULL` | 15 | 15 | ✓ |
| linki z `osm_way_id` | 558 | 558 | ✓ |
| `osm_roads.boundary_crossing` | 560 | 560 | ✓ |

Wniosek: tabele w Databricks to ten sam snapshot co pliki lokalne. Pipeline nadal czyta wyłącznie pliki lokalne (D-02).

**Uwagi techniczne (Git Bash na Windows):**
- Przed `databricks api post /api/2.0/...` ustaw `MSYS_NO_PATHCONV=1`. Bez tego Git Bash zamienia ścieżkę API na ścieżkę pliku i CLI zwraca `Error: Not Found`.
- Ścieżka endpointu to `/api/2.0/sql/statements`, bez końcowego `/`.
- CLI wypisuje na stderr podpowiedź o `databricks aitools install`. Przy parsowaniu JSON czytaj tylko stdout.

---

## 9. Pięć faktów, które zmieniają projekt

1. **24 ze 119 znaków C4 leży poza snapshotem.** Pochodzą z Warszawy, Poznania, Łodzi, Wrocławia, Gdańska oraz 4 z Krakowa z kontekstem z OSM API. Ich `osm_way_id` nie istnieje w `osm_roads.parquet`. ADR-002 §3.4 zakłada geometrię way do liczenia stycznej, a PRD ogranicza obszar do bbox Krakowa. Porównanie znaku z mapą musi więc korzystać z `signs/nearest_osm.csv`, a dla tych 24 znaków potrzebna jest osobna reguła.
2. **`PL:urban` występuje w `maxspeed:forward` i `maxspeed:backward` (5 tagów).** `maxspeed:conditional` ma jedną postać: `110 @ (Mo-Fr 06:00-18:00)`. Ścieżka `not_numeric / zone` w C2 zadziała na prawdziwych drogach, a nie tylko w testach. Fixture'y testów C2 powinny zawierać te wiersze.
3. **Overture `road_surface` nie ma `when`, a `sources[].between` istnieje.** Nawierzchnia jest zawsze bezwarunkowa. Way OSM może pokrywać tylko część segmentu, co daje nowy kod `partial_source` (ADR-001, już zaktualizowany).
4. **Etykiety znaków to zgodność dwóch modeli (Codex + GLM-5.3-Flash), nie ground truth.** Mapujemy je po `sign_value`, a nie po `negative_type`. Mianownik accuracy to 115 `certain`. Raport C4 musi opisać accuracy jako zgodność z roboczą referencją.
5. **Tylko 40 z 561 zdjęć ma lokalną miniaturę** (`offline/`), a katalog `data/` nie istnieje. Większość zadań C1 i C3 w raporcie HTML pokaże „Obraz niedostępny lokalnie”. Wpływa to na Manual QA (ADR-004) i na wartość raportu dla analityka.

## 10. Trzy pytania do człowieka

1. **Znaki spoza snapshotu (24 / 119):** czy w C4 odczytujemy i oceniamy wszystkie 119 wycinków, a z mapą porównujemy tylko 95 znaków z way w snapshocie, pozostałe oznaczając jako „not comparable / `outside_snapshot`”? Alternatywy: wykluczyć 24 znaki całkowicie albo porównywać je z surowymi tagami z `nearest_osm.csv` (OSM API, inna data niż snapshot). **Rekomendacja:** pierwszy wariant. Accuracy odczytu nie zależy od mapy, a porównanie z mapą wymaga tego samego snapshotu.
2. **Miniatury:** czy przed implementacją raportu uruchamiamy `download_photos.py`? Pobiera z sieci do ignorowanego `data/photos/` i kontroluje hashe. Alternatywą jest raport z 40 miniaturami `offline/` (reszta jako link do źródła). **Rekomendacja:** na start `offline/` + linki, a pełne pobranie dopiero do Manual QA etapu raportu.
3. **Etykieta `unreadable` (1 wycinek):** czy ostateczny odczyt AI (liczba lub `none`) dla wycinka z etykietą `unreadable` liczymy jako błędny (obecny zapis w ADR-003 §3.9), czy wykluczamy go z mianownika jak etykiety `uncertain`?
