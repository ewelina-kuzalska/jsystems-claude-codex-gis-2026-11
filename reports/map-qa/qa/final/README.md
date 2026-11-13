# Akceptacja końcowa — PRD/ADR wobec stanu końcowego

**Data:** 2026-11-13 · **Stan:** gałąź `map-app-implementation` po `3c98fb7` · **Uruchomienie:** `20261113T082857Z` z kopii roboczej repo (domyślne `--input`), `--with-signs --yes` (Jev), cache z M2.

Konsola: C1 170, C2 9, C3 170, C4 11, C4-manual 0; C4: 12 nowych żądań kroku 1 + 12 z cache, 24 × `decision_model`, 95 × `not_run`; kod 0.
Playwright (Edge) na tym `report.html`: 0 błędów konsoli i strony, 0 nieudanych i 0 zewnętrznych żądań, 56/56 obrazów, polskie znaki OK, zrzuty sekcji w tym katalogu.
GIS (zamiast QGIS, którego nie ma na VM): `tasks.geojson` otwarty sterownikiem GDAL GeoJSON (pyogrio, ten sam sterownik co QGIS): 360 obiektów, EPSG:4326, zasięg 19,797–20,149 E, 49,950–50,150 N; 3 linie mają środek tuż poza bbox, bo snapshot zawiera całe drogi przecinające granicę (`boundary_crossing`).
Testy na snapshocie w repo: 290 zaliczonych, 0 pominiętych; `live_api`: 5/5.

| Kryterium | Dowód |
|---|---|
| AC-01 manifest, kod 2 bez wyników | `test_inputs.py` (hash_mismatch, missing, row_count), `test_pipeline.py::test_invalid_input_writes_nothing`; checkout z CRLF dawał kod 2 |
| AC-02 wejścia nietknięte | `test_cli_e2e.py::test_inputs_unchanged` |
| AC-03 nagłówek: daty i liczności | `test_header_counts`, zrzut `01-top.png` |
| AC-04 pełne tagi OSM w eksporcie | `test_every_task_with_osm_id_exports_full_tags`, `test_c1`, `test_checks`, `test_c4::test_full_osm_tags…` |
| AC-05 wszystkie reguły Overture | `test_normalize_overture`, E2E TAC-001-02 |
| AC-06/07 mph, strefy, not_numeric | `test_normalize_osm` (każdy kod i sufiks) |
| AC-08–10 C1 | `test_c1`, `test_checks` (suma klas = 99 768), zadania tylko ze zdjęciem |
| AC-11–15 C2 | `test_c2` (pary przez referencję, kierunki, warunki, rodziny, daty), E2E TAC-001-04, TAC-001-05 |
| AC-16–19 C3 i „uncertain link” | `test_linking` (558/558 ok), `test_c3`, TAC-002-04 |
| AC-20 C4 tylko po włączeniu i potwierdzeniu | `test_cli_signs::test_answer_no_is_not_run` |
| AC-21 tylko obraz i pytanie | `test_ai_requests` (ciała = zapisy T00b, brak pól zakazanych) |
| AC-22–22e odpowiedzi, próg, eskalacja, stany | `test_resolve`, `test_render::test_all_c4_readings_listed`, AC-22e assert w pipeline |
| AC-23 limit 25 | `test_budget`, `test_resolve` (limit 1, najgorszy przypadek), `live_api` |
| AC-24 bez ponowień, stop | `test_resolve_http` (401 → 1 wywołanie), `test_cli_signs::test_401…` |
| AC-25 40 s | `test_ai_requests::test_real_deadline_aborts_blocked_read` |
| AC-26 cache, zero żądań | `test_cli_signs::test_full_flow_then_cache_rerun`, `test_cli_c4_live.py` (prawdziwe endpointy) |
| AC-27–28a porównanie, accuracy per tier i model, kolejka | `test_c4`, `test_evaluate`, M2 (Jev vs Luna Decisions) |
| AC-29, AC-36 teksty obowiązkowe | `test_render::test_mandatory_texts`, `test_never_states_map_is_wrong` |
| AC-30 spójne liczniki | `verify_counts` (kod 4), `test_verify_counts`, E2E, `data-count` w Playwright |
| AC-31 HTML offline, escapowanie | `test_render` (XSS, `javascript:`, brak base64/zewnętrznych), Playwright 0 żądań zewnętrznych |
| AC-32 atrybucje | `test_attribution_and_header`, kolumna `attribution` w CSV, `metadata` w GeoJSON |
| AC-33–35 GeoJSON/CSV, powtarzalność | `test_export`, E2E `test_repeatable_exports`, odczyt GDAL powyżej |
| AC-37 sekrety | `test_cli_signs` (TAC-06, pusty klucz), `redact()` |
| AC-38 polski | zrzuty, `polish_chars_ok`, CSV `utf-8-sig` |
| TAC-01–03 | `uv sync --frozen`, ruff czysty, `test_network_blocked` |
| TAC-04 < 120 s z repo | 46 s, kod 0 (`20261113T082342Z`) |
| TAC-05, TAC-06, TAC-07 | `test_verify_counts`; `test_cli_signs`; dowody uruchomień M1/M2/final |
| TAC-001-01…05, TAC-002-01…04, TAC-003-01…05, TAC-004-01…04 | testy wymienione w ADR, pomiary w ADR-003 §9 i ADR-006 §5 |
| ADR-005 katalog roboczy | `test_default_input_missing_hint`, E2E z `cwd` = korzeń repo |

**Poza zakresem tej akceptacji (decyzje planu):** PR (T29) odroczony decyzją użytkownika (plan §1). Plik logu uruchomienia (proponowany ADR-007, opcjonalny) nie powstał; zredagowana treść błędów API trafia do `summary.json` i raportu.
