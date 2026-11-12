# Plan implementacji: Map QA (cała aplikacja, fazami)

> **Status: SZKIC, czeka na review użytkownika.** Planowanie nie autoryzuje wykonania, uruchamiania agentów, publikacji ani merge.
>
> **Data:** 2026-11-12 · **Gałąź:** `map-app-implementation` (śledzi `fork/map-app-implementation`) · **Orkiestrator:** Claude Code (Opus 5.5)
>
> **Źródła prawdy:** [PRD](../PRD.md) · [ADR-000](../ADR/000-main-architecture.md) · [ADR-001](../ADR/001-data-ingest-normalization.md) · [ADR-002](../ADR/002-crs-photo-road-linking.md) · [ADR-003](../ADR/003-ai-sign-reading.md) · [ADR-004](../ADR/004-report-export.md) · [Profil danych M2](../../reports/map-qa/profile.md) · [AGENTS.md](../../AGENTS.md)

Plan nie kopiuje wymagań, tylko linkuje do konkretnych AC i sekcji ADR. Brakująca architektura trafia do proponowanego ADR (§9), a nie do założeń planu.

---

## 1. Decyzje użytkownika dla tego planu (2026-11-12)

| Temat | Decyzja |
|---|---|
| Zakres | **Cała aplikacja** w jednym przepływie, podzielona na logiczne fazy z priorytetami. Wykonanie ma iść bez zatrzymywania się, z wyjątkiem bramek ludzkich w §6 |
| Tracker | Kolumna **Status** w macierzy zależności (§4), aktualizowana przez orkiestratora przy każdym commicie |
| Wzorzec wizualny HTML | Minimalny CSS z [ADR-004 §3.4](../ADR/004-report-export.md). Brak `docs/design-guidelines.md` i `assets/design-tokens.json` jest świadomy |
| Pull request | **Na razie bez PR.** Wynik to commity na gałęzi i push do `fork` (T29 jest odroczone) |

---

## 2. Stan faktyczny repozytorium (zweryfikowany 2026-11-12)

| Element | Stan |
|---|---|
| `app/` | Tylko `README.md` (ogólna checklista kursu, nastawiona na TypeScript i nieaktualna dla tego stosu). **Brak kodu, `pyproject.toml`, testów i punktu wejścia** |
| Drzewo robocze | Czyste. HEAD `3dbd215`, zsynchronizowane z `fork/map-app-implementation` |
| Dokumentacja | PRD, ADR 000–004 (zaktualizowane po profilu M2), `reports/map-qa/profile.md` + `profile_extra.py` |
| Design | Brak `docs/design-guidelines.md` i `assets/design-tokens.json` (decyzja w §1) |
| Tracker | Brak. Issues w forku są wyłączone (decyzja w §1) |
| Role agentów | Brak `.claude/agents/`, `.opencode/` i `opencode.json`. Istnieją `.claude/settings.json` (allow/ask/deny, `plansDirectory: ./docs/plans`), `.codex/config.toml` (`default_permissions = "course-root"`, `approval_policy = "on-request"`, `approvals_reviewer = "auto_review"`) i `.codex/rules/course.rules` |
| `.agent-briefs/` | Ignorowany przez `.gitignore` („private agent briefs”). Trwały na dysku, ale poza repo |
| Worktree | Tylko główny checkout |
| Sekrety | `OPENROUTER_API_KEY`: obecny (sprawdzono tylko obecność). `~/.databrickscfg` profil `map-qa`: obecny |

**Polecenia zweryfikowane:**

| Polecenie | Wynik |
|---|---|
| `uv --version` | `uv 0.13.7` |
| `uv run --python 3.12 python -c "import sys; print(sys.version)"` | `3.12.16` |
| `PYTHONUTF8=1 uv run --python 3.12 course-materials/exercise-data/map-qa/profile_data.py` | exit 0 |
| `uv run --python 3.12 course-materials/exercise-data/map-qa/signs/build_signs.py --verify-only` | `checked=119 missing=0`, exit 0 |
| `codex --version` · `codex exec --help` | `codex-cli 0.167.2`, tryb `exec` dostępny |
| `opencode --version` · `opencode run --help` · `opencode models` | `v2.2.5`, model `xiaomi-token-plan-ams/mimo-v2.6-flash` dostępny |
| `claude --version` | `2.1.322`. Narzędzie Agent z `model: haiku` (Haiku 5.5) dostępne w tej sesji |
| `databricks version` | `1.26.0` (poza pipeline'em, ADR-000 D-02) |

**Baseline:** `uv run pytest` daje `error: Failed to spawn: pytest`, bo nie ma jeszcze projektu. **Nie ma testów, buildu ani startu aplikacji do uruchomienia.** Pierwsza faza tworzy tę infrastrukturę (AGENTS.md: „If the area has no suitable test infrastructure yet, add it as part of the task”).

**Pułapki środowiska (Windows + Git Bash), obowiązują wszystkich wykonawców:**
- `PYTHONUTF8=1` przy przekierowaniu wyjścia Pythona do pliku (cp1250 i `UnicodeEncodeError`),
- `MSYS_NO_PATHCONV=1` dla argumentów zaczynających się od `/` (np. `databricks api`),
- uruchomienie nowej powłoki po instalacji narzędzi (PATH).

---

## 3. Fazy i priorytety

Kolejność wynika z zależności, nie z wygody. Każda faza kończy się zielonymi testami, uruchomieniem prawdziwego CLI (TAC-07) i commitem.

| Faza | Cel | Kamień milowy (demonstrowalny) |
|---|---|---|
| **F0** Fundament | Smoke test agentów, scaffold `app/`, kontrakty typów, fixture'y z prawdziwych danych | `uv sync --frozen`, `uv run pytest` (0 testów domenowych) i `uv run map-qa --help` działają |
| **F1** Wejścia | Weryfikacja manifestu i odczyt danych | `map-qa run` kończy się kodem 2 na zmienionym pliku i drukuje daty i liczności na prawdziwym snapshocie |
| **F2** Normalizacja + CRS | Czyste funkcje ADR-001 §3.2–3.4 i ADR-002 §3.1 | Testy jednostkowe parserów i transformacji |
| **F3** Kontrole C1–C3 | Kandydaci i listy „not comparable” | Liczniki C1–C3 na pełnym snapshocie |
| **F4** Wyniki | Zadania, eksporty, raporty, kontrola spójności | Cztery pliki w `reports/map-qa/runs/<run_id>/` |
| **F5** Pipeline + CLI bez C4 | Pełny przepływ PRD 4.1 z C4 jako „not run” | **M1: działająca aplikacja bez AI** (E2E, Manual QA, push do forka) |
| **F6** C4 bez sieci | Kontekst znaku, budżet, cache, kontrola wycinków, budowa żądań | Testy jednostkowe C4. `--with-signs` bez klucza lub bez zgody kończy się „not run” |
| **F7** C4 z API | Zapis prawdziwych odpowiedzi (bramka G-C4), eskalacja, ewaluacja | **M2: pełna aplikacja** z C4 na cache (zero nowych żądań przy powtórce) |
| **F8** Akceptacja | Pełna weryfikacja, niezależny review, Manual QA, push | Raport akceptacji. PR odroczony |

**Ścieżka krytyczna:** T01 → T02 → T04 → T03 → T05/T06 → T10 (C2) → T12 → T13/T14 → T15 → T16 → T17 → T18 (**M1**) → T20/T21 → **G-C4** → T22 → T23 → T24 → T25 → T26 → T27 → T28 (**M2**).

---

## 4. Macierz zależności (jedyne źródło statusu)

Legenda statusu: `todo` · `brief` (brief gotowy) · `running` · `review` (orkiestrator sprawdza) · `done` (commit) · `blocked`.
Granica commita: **jeden wiersz = jeden commit** `Area: summary` (AGENTS.md), chyba że kolumna mówi inaczej.
Modele: **Orch** to orkiestrator (Opus 5.5, ta sesja). **Haiku** to subagent Claude Code (Haiku 5.5). **Sol** to Codex `gpt-6.1-sol`. **Luna** to Codex Luna 6 (ID do potwierdzenia w T00). **MiMo** to OpenCode `xiaomi-token-plan-ams/mimo-v2.6-flash`.

| Task | Observable outcome | PRD/ADR links | Prerequisites | Owner/model | Editable files | Verification and handoff | Status |
|---|---|---|---|---|---|---|---|
| **T00** Smoke test agentów | Każdy kanał (Haiku, Sol, Luna, MiMo) wykonuje brief „utwórz plik X o treści Y” i raportuje. Potwierdzone ID modeli i zachowanie uprawnień | §7 tego planu | — | Orch | `.agent-briefs/T00-*.md` (poza git). Proponowany `opencode.json` (deny jak `.claude/settings.json`) | Pliki istnieją, zakazane polecenie (`rm`) zablokowane w każdym kanale. Bez commita kodu. Commit `Chore: add opencode permissions` tylko po akceptacji użytkownika | todo |
| **T01** Scaffold `app/` | `uv sync --frozen` i `uv run pytest` przechodzą (0 testów), `uv run map-qa --help` drukuje pomoc po polsku, `uv run ruff check` czysty | ADR-000 §2 (piny), §3 (struktura), §10 TAC-01–03; AGENTS.md TDD | T00 | Orch (lockfile, punkt wejścia) | `app/pyproject.toml`, `app/uv.lock`, `app/src/map_qa/__init__.py`, `app/src/map_qa/cli.py` (szkielet), `app/tests/conftest.py`, `app/AGENTS.md` (krótki, lokalny), `app/README.md`, `.gitignore` (`reports/map-qa/runs/`) | Test „CLI help zwraca 0” napisany przed `cli.py` (red→green). Piny zweryfikowane w Context7/PyPI przed zapisaniem. `--block-network` w `addopts`. Commit `Backend: scaffold map-qa uv project` | todo |
| **T02** Kontrakty typów | Dataclasses i enumy z ADR-000 §5 importują się. Kody przyczyn jako stałe | ADR-000 §5; ADR-001 §4; ADR-002 §4; ADR-003 §4; ADR-004 §4 | T01 | Orch (wspólny kontrakt) | `app/src/map_qa/model.py`, `app/src/map_qa/config.py`, `app/tests/unit/test_model.py`, `app/tests/unit/test_config.py` | Testy: walidacja `--max-requests` 1–25 i `--threshold` 0–1 (AC-22a, AC-23), zamknięte listy kodów. **Po commicie `model.py` jest zamrożony.** Zmiany tylko przez Orch. Commit `Backend: add domain model and config` | todo |
| **T04** Fixture'y z prawdziwych danych | Małe wycinki prawdziwych plików z adnotacją źródła (plik, ID, SHA-256 źródła) | ADR-000 §10 „Fixture'y z prawdziwych danych”; profil §2–§5 (konkretne ID) | T01 | Haiku | `app/tests/fixtures/build_fixtures.py`, `app/tests/fixtures/map_qa/**`, `app/tests/fixtures/PROVENANCE.md` | Skrypt idempotentny, tylko odczyt wejść. Zawiera segmenty `00836247-…`, `009debd5-…`, `w75390950@17`, wiersze z `PL:urban`, `heading=0` (`panoramax_646ecfdd-…`), znak `osm_api`, etykiety `unreadable`. Orch sprawdza rozmiar (< 2 MB) i hashe. Commit `Test: add real-data fixtures` | todo |
| **T03** `inputs` | `verify_snapshot` zwraca `Snapshot` albo `InputError`. Kod 2 i brak katalogu wyników przy błędzie. Liczności z manifestu | AC-01, AC-02, AC-03; ADR-001 §3.1, §5 | T02, T04 | Sol | `app/src/map_qa/inputs.py`, `app/tests/integration/test_inputs.py` | Red: test z kopią w tmp z jednym zmienionym bajtem (`hash_mismatch`), brak pliku (`missing`), `hash_not_in_manifest` dla `signs/`. Green na prawdziwym snapshocie (99 768 / 85 405 / 561 / 561). Commit `Backend: verify snapshot manifest` | todo |
| **T05** `normalize` OSM | `parse_maxspeed` i ekstrakcja `SpeedValue` z `tags` | AC-04, AC-06, AC-07; ADR-001 §3.2, D-101, TAC-001-01 | T02, T04 | Haiku | `app/src/map_qa/normalize/__init__.py`, `app/src/map_qa/normalize/osm.py`, `app/tests/unit/test_normalize_osm.py` | Red: każdy kod przyczyny i sufiks jednostki. Prawdziwy wiersz z `PL:urban` w `maxspeed:backward` daje `zone`. `110 @ (Mo-Fr 06:00-18:00)` daje `conditional`. **Równolegle z T06 i T07** (rozłączne pliki; `normalize/__init__.py` tworzy tylko T05). Commit `Backend: normalize OSM speed tags` | todo |
| **T06** `normalize` Overture + nawierzchnia | `OvertureRule`, `OvertureSource` (z `source_between`), `surface_family` | AC-05, AC-13; ADR-001 §3.3, §3.4, D-102, TAC-001-02/03 | T02, T04 | Haiku | `app/src/map_qa/normalize/overture.py`, `app/src/map_qa/normalize/surface.py`, `app/src/map_qa/data/surface_families.csv`, `app/tests/unit/test_normalize_overture.py`, `app/tests/unit/test_surface.py` | Red: segment `00836247-…` daje 3 reguły z `rule_index` 0..2. `road_surface` bez `when` daje `unconditional`. `record_id` `w123@4` / `n5@1` / pusty. CSV bez duplikatów. **Równolegle z T05 i T07.** Commit `Backend: normalize Overture rules and surface families` | todo |
| **T07** `crs` | Transformatory `always_xy`, `local_bearing`, `angle_diffs`, porównanie CRS przez `pyproj.CRS` | AC-17, AC-18; ADR-002 §3.1, §5, D-201, D-202, TAC-002-01/02 | T02 | Haiku | `app/src/map_qa/crs.py`, `app/tests/unit/test_crs.py` | Red: Rynek Główny w zakresie 2180, powrót < 1e−7°, 100 m ± 0,1 m, heading 359/1, `None` ≠ 0, PROJJSON OSM ≠ `crs_mismatch`. **Równolegle z T05 i T06.** Commit `Backend: add CRS and bearing utilities` | todo |
| **T08** C1 | Podsumowanie braków per klasa (OSM i Overture) i zadania tylko dla dróg ze zdjęciem | AC-08, AC-09, AC-10; ADR-001 §3.5 | T03, T05, T06 | Haiku | `app/src/map_qa/checks/__init__.py`, `app/src/map_qa/checks/c1.py`, `app/tests/unit/test_c1.py` | Red: droga bez `maxspeed` i bez linku nie daje zadania, droga z 2 zdjęciami daje 1 zadanie. Suma po klasach = liczność (integration). **Równolegle z T09.** Commit `Backend: add C1 missing attributes check` | todo |
| **T09** `linking` (recheck) | `recheck_links` i flagi plikowe oraz własne | AC-16, AC-18, AC-19; ADR-002 §3.2, §3.3, D-203, TAC-002-03 | T03, T07 | Sol | `app/src/map_qa/linking.py`, `app/tests/unit/test_linking.py`, `app/tests/integration/test_linking.py` | Red: rozjazd 1 m daje `link_recheck_mismatch`, 0,4 m nie daje. Remisy, `restricted_access`, `grade_separated_nearby`. Na pełnym snapshocie ≥ 95% `ok`, a wynik poniżej to raport, nie zmiana tolerancji. **Równolegle z T08.** Commit `Backend: recheck photo-road links` | todo |
| **T10** C2 | Kandydaci `speed_mismatch` / `surface_family_mismatch`, lista „not comparable”, „tylko przestrzenne” | AC-11–AC-15; ADR-001 §3.6, D-103, D-104, TAC-001-04/05 | T05, T06, T07 | Sol | `app/src/map_qa/checks/c2.py`, `app/tests/unit/test_c2.py`, `app/tests/integration/test_c2.py` | Red: OSM 50 / Overture 60, geometria odwrócona, azymut 90° daje `direction_unknown`, `partial_source`, para bezwarunkowa + `mode` bez `multiple_rules`. TAC-001-05 (suma porównań). Commit `Backend: add C2 OSM vs Overture check` | todo |
| **T11** C3 | Podsumowanie flag i zadania C3. Etykieta „uncertain link” dla C1/C2 | AC-16, AC-19; ADR-002 §3.3, TAC-002-04 | T09 | Haiku | `app/src/map_qa/checks/c3.py`, `app/tests/unit/test_c3.py` | Red: 146 zdjęć z flagą z pliku (przed flagami własnymi, integration), liczność per flaga. Commit `Backend: add C3 uncertain links check` | todo |
| **T12** `tasks` | Stabilne `task_id` i deterministyczna kolejność | AC-33, AC-35; ADR-004 §3.2, §5 | T08, T10, T11 | Haiku | `app/src/map_qa/tasks.py`, `app/tests/unit/test_tasks.py` | Red: ten sam kandydat daje ten sam ID, puste pola, kolejność sortowania. **Zamraża kontrakt `Task` dla T13 i T14.** Commit `Backend: build stable tasks` | todo |
| **T13** `export` | `tasks.geojson` (RFC 7946, 7 miejsc) i `tasks.csv` (`utf-8-sig`, `lon`/`lat`, `attribution`) | AC-32, AC-33, AC-34, AC-35; ADR-004 §3.6, D-401, D-403, TAC-004-02 | T12, T07 | MiMo | `app/src/map_qa/export.py`, `app/tests/unit/test_export.py` | Red: brak `crs`, zakresy lon/lat, te same `task_id` w CSV i GeoJSON, polskie znaki, pusta kolekcja. **Równolegle z T14.** Commit `Backend: export GeoJSON and CSV` | todo |
| **T14** `render` | `report.md` i `report.html` z Jinja2, miniatury w `images/`, teksty obowiązkowe | AC-29, AC-31, AC-32, AC-36, AC-38; PRD §9.2–9.4; ADR-004 §3.3–3.5, §3.8, D-07, D-402, TAC-004-01 | T12 | Sol (szablony + escapowanie), wsparcie MiMo dla `md_escape` | `app/src/map_qa/render.py`, `app/src/map_qa/templates/report.html.j2`, `app/src/map_qa/templates/report.md.j2`, `app/tests/unit/test_render.py`, `app/tests/integration/test_render_golden.py`, `app/tests/integration/__snapshots__/**` | Red: `<script>` escapowany, zakaz `\|safe`, `StrictUndefined`, `javascript:` jako tekst, brak `data:image`, „Obraz niedostępny lokalnie”. Golden syrupy. **Równolegle z T13.** Commit `Frontend: render Markdown and HTML report` | todo |
| **T15** Katalog uruchomienia + `verify_counts` | `.partial` → rename. Kod 4 przy niezgodności liczników | AC-30; ADR-004 §3.1, §3.7; ADR-000 §6.1 (kody 3, 4), TAC-05 | T13, T14 | Haiku | `app/src/map_qa/rundir.py`, `app/tests/integration/test_verify_counts.py` | Red: usunięty wiersz CSV daje kod 4 i zostaje `.partial`, kolizja `run_id` daje kod 3. Commit `Backend: atomic run folder and count check` | todo |
| **T16** `pipeline` + `cli run` (bez C4) | `uv run map-qa run` daje 4 pliki, liczniki i ścieżki. C4 jako „not run” | PRD 4.1, 4.4, §9.1; AC-20 (ścieżka „not run”), AC-37; ADR-000 §6.1, §9.3 | T03, T08, T10, T11, T15 | Orch (integracja) | `app/src/map_qa/pipeline.py`, `app/src/map_qa/cli.py`, `app/tests/integration/test_pipeline.py` | Red: pipeline na fixture'ach daje zgodne liczniki we wszystkich 4 plikach. `--with-signs` bez zgody daje „not run”. Polskie komunikaty. Commit `Backend: wire pipeline and CLI run` | todo |
| **T17** E2E bez C4 | Pełny snapshot: kod 0 < 120 s, hashe wejść bez zmian, dwa uruchomienia bajtowo identyczne | AC-02, AC-03, AC-30, AC-35; TAC-04, TAC-004-03/04, TAC-001-02/04, TAC-002-03/04 | T16 | Orch | `app/tests/e2e/test_cli_e2e.py` | Bez mocków (`subprocess`). Raport: liczba wykrytych / zaliczonych / pominiętych testów. Commit `Test: add end-to-end run without C4` | todo |
| **T18** Manual QA M1 | Zrzuty każdej sekcji HTML (Playwright CLI), polskie znaki, brak błędów konsoli, `tasks.geojson` w Krakowie, ślad jednego wiersza od wejścia do raportu | AGENTS.md „Manual QA”; ADR-004 §8 „Ręczna kontrola” | T17 | Orch + **człowiek** (akceptacja wyglądu) | `reports/map-qa/qa/M1/**` (zrzuty, notatki) | Lista sprawdzeń i zrzuty w notatce QA. **Push do `fork` po akceptacji.** Commit `Docs: M1 manual QA evidence` | todo |
| **T19** `sign_road_context` | Kierunek znaku i wartość OSM; `outside_snapshot` dla 24 znaków | AC-27, AC-29; ADR-002 §3.4, D-204 | T07, T04 | Haiku | `app/src/map_qa/signs/__init__.py`, `app/src/map_qa/signs/context.py`, `app/tests/unit/test_sign_context.py` | Red: `compass_angle` 10/170/90 daje forward/backward/`direction_unknown`. Wiersz `osm_api` daje `outside_snapshot`. **Równolegle z T20 i T21.** Commit `Backend: sign road context` | todo |
| **T20** `cache` + `RequestBudget` + kontrola wycinka | Cache po kluczu kontraktu, licznik przed wysłaniem, fail-closed na hash/format/EXIF | AC-23, AC-26; ADR-003 §3.2, §3.6, §3.7, D-303, D-304, D-305, TAC-003-02 | T02, T04 | Haiku | `app/src/map_qa/cache.py`, `app/src/map_qa/budget.py`, `app/src/map_qa/signs/crop_check.py`, `app/tests/unit/test_cache.py`, `app/tests/unit/test_budget.py`, `app/tests/unit/test_crop_check.py` | Red: limit 1 daje jedno żądanie i resztę `budget_exhausted`, zmiana `model_id` daje nowy klucz, kopia z APP1 daje `metadata_present`. **Równolegle z T19 i T21.** Commit `Backend: AI cache, budget and crop checks` | todo |
| **T21** `ai_client`: budowa żądań (bez sieci) | Ciała żądań kroków 1 i 2 zgodne z kontraktem, bez zakazanych pól | AC-21, AC-22, AC-24, AC-25, AC-37; ADR-003 §3.3, §3.4, §3.6, D-05, D-301, D-302, TAC-003-01 | T02 | Sol | `app/src/map_qa/ai_client.py`, `app/tests/unit/test_ai_requests.py` | Red: rekurencyjne sprawdzenie kluczy (brak `photo_id`, współrzędnych, wyniku kroku 1), `reasoning.effort=medium`, `json_schema` strict, transport bez ponowień, termin 40 s z wstrzykniętym zegarem. **Brak wywołań sieci.** Commit `Backend: build AI requests` | todo |
| **G-C4** Bramka: zapis prawdziwych odpowiedzi | 3 pliki capture: tier1, tier2 (płatne, łącznie ≤ 2 żądania), 401 bez klucza (bezpłatne) | ADR-003 §8 „Zasada mocków”, §9, TAC-003-03, TAC-003-05; AGENTS.md (mock z prawdziwej odpowiedzi) | T21 | **Człowiek** (zgoda i budżet) + Orch (wykonanie) | `app/tests/fixtures/openrouter/*.json` | **Wykonanie nie przechodzi tej bramki automatycznie.** Bez zgody: testy integracyjne `ai_client` są oznaczone `skip("brak capture")`, a F7 kończy się na T25 z C4 = „not run”. Test: brak `Authorization`/`Bearer` w plikach. Commit `Test: capture OpenRouter responses` | todo |
| **T22** `ai_client`: interpretacja odpowiedzi | `SignReading` z prawdziwych zapisów. 401 zatrzymuje pętlę bez ponowień | AC-22, AC-24; ADR-003 §3.3–3.4, §5 | G-C4, T21 | Sol | `app/src/map_qa/ai_client.py` (rozszerzenie), `app/tests/integration/test_ai_client.py` | pytest-httpx tylko na plikach capture. Mock 401 wywołany dokładnie raz. Commit `Backend: interpret AI responses` | todo |
| **T23** `signs.resolve` + `signs.evaluate` | Eskalacja tier1 → tier2 → kolejka, stany końcowe, accuracy „zgodne / ocenione” | AC-22a–e, AC-26, AC-28; ADR-003 §3.1, §3.5, §3.9, §3.10, TAC-003-04 | T19, T20, T22 | Sol | `app/src/map_qa/signs/resolve.py`, `app/src/map_qa/signs/evaluate.py`, `app/tests/unit/test_resolve.py`, `app/tests/unit/test_evaluate.py` | Red: p 0,70 / 0,69, `other` eskaluje, suma stanów = próbka, `unreadable` + ostateczna odpowiedź = błąd (decyzja 3A), tylko `evaluate` otwiera `labels.csv`. Commit `Backend: resolve and evaluate sign readings` | todo |
| **T24** C4 w wynikach | Kandydaci `C4` / `C4-manual`, blok C4 w raporcie, zastrzeżenia | AC-27, AC-28, AC-28a, AC-29; PRD §9.2–9.3; ADR-003 §3.8; ADR-004 §3.4, §3.6, §3.8 | T23, T12, T13, T14 | Orch (wspólne pliki szablonów i eksportu) | `app/src/map_qa/checks/c4.py`, `app/src/map_qa/templates/*.j2`, `app/src/map_qa/export.py`, testy odpowiednie | Red: kolejka ręczna bez etykiety referencyjnej, `outside_snapshot` w „Nieporównywalne”, pusty stan „Żaden znak nie wymaga ręcznej kontroli”. Commit `Backend: add C4 to report and exports` | todo |
| **T25** CLI `--with-signs` | Plan, potwierdzenie „tak/nie”, `--yes`, podsumowanie żądań per krok, brak klucza = zero żądań | PRD 4.2, 4.3, §9.1; AC-20, AC-23, AC-37; ADR-000 §6.1, D-08; ADR-003 §3.6 | T23, T24, T16 | Orch | `app/src/map_qa/cli.py`, `app/src/map_qa/pipeline.py`, `app/tests/integration/test_cli_signs.py` | Red: odpowiedź „nie” daje „not run”, pusta zmienna = brak klucza, TAC-06 (fałszywy klucz nie pojawia się w wynikach i logach). Commit `Backend: CLI sign reading flow` | todo |
| **T26** Pełna weryfikacja | `uv sync --frozen`, `ruff check`, `ruff format --check`, `pytest` (liczby), E2E, start CLI. Osobno build / testy / start | ADR-000 §10 TAC-01–07; AGENTS.md „Verification” | T25 (lub T18 przy fallbacku) | Orch | — | Raport z trzema osobnymi sekcjami i liczbami pominięć z powodami. Bez commita, jeśli nic nie zmieniono | todo |
| **T27** Niezależny review | Lista problemów z ważnością, bez edycji kodu | AGENTS.md „Completion Criteria” | T26 | Sol (`codex exec review`, sandbox read-only), drugi przegląd Claude `/code-review` | `.agent-briefs/T27-review.md` (wynik) | Orch weryfikuje każde znalezisko. Poprawki jako osobne zadania z własnymi commitami | todo |
| **T28** Manual QA M2 + pomiary C4 | Zrzuty z C4 i kolejką ręczną. Powtórka z cache = 0 nowych żądań. Uzupełnione ADR-003 §9 (koszt, czas, kształt obrazu) | AC-26; ADR-003 §9, TAC-003-05; AGENTS.md „Manual QA” | T27 | Orch + **człowiek** | `reports/map-qa/qa/M2/**`, `docs/ADR/003-ai-sign-reading.md` (§9) | Notatka QA i diff ADR. Push do `fork`. Commity `Docs: M2 manual QA evidence`, `Docs: record C4 measurements` | todo |
| **T29** Pull request | — | AGENTS.md „Commit Rules” | T28 | Orch | — | **Odroczone (decyzja użytkownika).** Gotowy opis PR w `.agent-briefs/T29-pr.md` | blocked |

---

## 5. Równoległość, gorące pliki i worktree

**Okna równoległe** (rozłączne pliki, niezależne wejścia; każdy wykonawca dostaje w briefie listę zadań równoległych):

| Okno | Zadania | Warunek |
|---|---|---|
| W1 | T05 ‖ T06 ‖ T07 | Po T02 i T04. `normalize/__init__.py` tworzy tylko T05 |
| W2 | T08 ‖ T09 | Po T03, T05, T06, T07. `checks/__init__.py` tworzy tylko T08 |
| W3 | T13 ‖ T14 | Po T12 (zamrożony `Task`) |
| W4 | T19 ‖ T20 ‖ T21 | Po F5. `signs/__init__.py` tworzy tylko T19 |

**Szeregowane zawsze:** `app/pyproject.toml` i `app/uv.lock` (tylko Orch; wykonawcy zgłaszają potrzebę zależności, a nie dodają jej), `model.py` po T02, `tests/conftest.py`, `tests/fixtures/**` po T04, `pipeline.py`, `cli.py`, szablony po T14 i `export.py` po T13 (zmiany C4 tylko w T24 przez Orch).

**Worktree:** nie są potrzebne. Wszystkie okna mają rozłączne pliki, więc pracujemy w jednym checkoucie. Gdyby kiedyś trzeba było równolegle edytować te same pliki, worktree wymaga zgody (`.claude/settings.json` „ask”) i konwencji `D:/jsystems-claude-codex-gis-2026-11-worktrees/<branch>/` (globalny CLAUDE.md), a po pracy `git worktree remove` + `git worktree prune`.

---

## 6. Bramki ludzkie, obsługa błędów i fallback

**Bramki (wykonanie bez zatrzymywania się kończy się na nich):**
1. **T00:** akceptacja `opencode.json` (nowy plik uprawnień).
2. **T18 / T28:** akceptacja wyglądu raportu (brak formalnego design reference, AGENTS.md Manual QA pkt 5).
3. **G-C4:** zgoda na ≤ 2 płatne żądania (kurs płaci z budżetu; PRD §8, ADR-003 §8).
4. Każdy push do `fork` po kamieniu milowym. Push na `main` i force push blokują reguły repo.

**Obsługa błędów i rollback:**
- Wykonawca kończy z czerwonym testem albo z wynikiem spoza zakresu. Orch czyta diff i raport, przywraca pliki zadania (`git restore <pliki zadania>`) i wysyła **jeden** zawężony brief. Przy drugiej porażce przejmuje zadanie sam.
- Wykonawca zgłasza sprzeczność ze specyfikacją. Zadanie dostaje status `blocked`. Orch rozstrzyga ją na podstawie PRD/ADR, a jeśli dotyczy architektury, proponuje zmianę ADR i pyta człowieka. **Testów się nie osłabia.**
- Kanał niedostępny (limit, brak modelu, błąd CLI). Łańcuch zastępczy: MiMo → Luna → Haiku → Orch. Sol → Haiku z węższym briefem → Orch. Zmianę kanału odnotowuje się w kolumnie Status.
- Commit per zadanie pozwala cofnąć zadanie przez `git revert <sha>` bez naruszania innych.
- Błąd płatnego API w trakcie G-C4: jedno żądanie, bez ponowień (AC-24). Zapisujemy wynik i decyduje człowiek.

**Fallback przy braku czasu, narzędzi lub modeli (malejąco):**
1. **M1 bez C4** (F0–F5). Działająca aplikacja z C1–C3 i czterema wynikami, C4 = „not run”. To pierwszy priorytet.
2. **M1 okrojone:** C2 tylko dla kierunku `both` (reguły kierunkowe → `direction_unknown`) oraz C3 bez flag własnych (`grade_separated_nearby`, `restricted_access`). Każde okrojenie jest jawnie opisane w raporcie.
3. **Minimum:** wejścia + C1 + Markdown + CSV, wykonane sekwencyjnie przez jednego agenta według tej samej macierzy.

---

## 7. Delegowanie do agentów (headless)

### 7.1 Zasady
- **Domyślnie subagenci ad hoc z dokładnym briefem.** Nie tworzymy plików ról (`.claude/agents/`). Wartość daje brief, a nie rola. Własną definicję warto dodać dopiero dla powtarzalnej roli z ograniczeniami narzędzi (np. read-only reviewer), jeśli T27 będzie powtarzany.
- Wykonawca **nie** zmienia zakresu, nie edytuje plików spoza listy, nie dodaje zależności, nie robi commitów i nie akceptuje własnej pracy. Raportuje: zmienione pliki, polecenia z wynikami (red, potem green), sprzeczności.
- Orch przed integracją: czyta diff, sam uruchamia testy zadania i testy sąsiednie, potem commituje (AGENTS.md „Commit Rules”).
- Harness: narzędzie Agent w Claude Code jest dostępne (zweryfikowane). Gdyby nie było któregoś kanału, tę samą macierz wykonuje sekwencyjnie jeden agent.

### 7.2 Brief (`.agent-briefs/<TASK>.md`, tworzony tuż przed wysłaniem)
Katalog jest ignorowany przez git, czyli trwały na dysku i prywatny. Szablon:

```markdown
# <TASK> — <tytuł>
## Cel i obserwowalny wynik        (z macierzy §4)
## Kontekst (wyciągi, nie linki do przeczytania całości)
- Kontrakty: fragment model.py / sygnatury z poprzedników
- Reguły: cytaty z PRD AC-xx i ADR §x.y (z linkami dla śledzalności)
- Dane testowe: ścieżki fixture'ów i oczekiwane wartości
## Pliki do edycji (wyłącznie): ...
## Zadania równoległe w tym czasie: ... (nie dotykaj ich plików)
## Kroki: 1) test red i jego uruchomienie  2) minimum kodu  3) green  4) ruff
## Polecenia weryfikacji: cd app && uv run pytest <ścieżki> -q ; uv run ruff check <pliki>
## Zakazy: brak zmian w pyproject/uv.lock, brak sieci w testach, brak osłabiania testów, brak commitów
## Raport końcowy → .agent-briefs/<TASK>.result.md
```

### 7.3 Polecenia uruchomienia (z katalogu głównego repo; Orch uruchamia w tle i czeka na powiadomienie)

**Claude Code subagent (Haiku 5.5):** narzędzie Agent w tej sesji, `model: "haiku"`, prompt: „Wykonaj brief `.agent-briefs/T05.md`. Raport zapisz w `.agent-briefs/T05.result.md`.” Subagent dziedziczy uprawnienia z `.claude/settings.json`.

**Codex (Sol 6.1 dla złożonych zadań i review, Luna 6 dla prostych i researchu):**
```bash
# Implementacja: brief przez stdin, uprawnienia z .codex/config.toml (course-root), bez pytań o zgodę
codex exec -C . -m gpt-6.1-sol -c approval_policy='"never"' \
  -o .agent-briefs/T10.result.md - < .agent-briefs/T10.md

# Review bez edycji
codex exec -C . -m gpt-6.1-sol --sandbox read-only -c approval_policy='"never"' \
  -o .agent-briefs/T27-review.md review
```
- `-` czyta prompt ze stdin. `-o/--output-last-message` zapisuje ostatnią wiadomość. `--json` daje strumień zdarzeń JSONL do logu.
- `approval_policy="never"` nie pyta. Akcje wymagające zgody są **odrzucane**, a nie dopuszczane (komentarz w `.codex/config.toml`).
- Nie łączymy `--sandbox workspace-write` z nazwanym profilem uprawnień. `--sandbox` ma wyższe pierwszeństwo i przełącza na tryb legacy, gubiąc zakazy odczytu `.env` z `course-workspace`. Dla implementacji zostajemy przy `default_permissions = "course-root"`.
- **Do potwierdzenia w T00:** ID modelu Luna 6 (Sol `gpt-6.1-sol` pochodzi z komentarza w `.codex/config.toml`) oraz to, czy `exec` na Windows respektuje `course-root` (próba zapisu `.env` ma się nie udać).

**OpenCode (MiMo-V2.6-Flash, Xiaomi Token Plan):**
```bash
opencode run -m xiaomi-token-plan-ams/mimo-v2.6-flash --auto --format json \
  --title T13 -f .agent-briefs/T13.md \
  "Wykonaj załączony brief dokładnie. Raport zapisz w .agent-briefs/T13.result.md." \
  > .agent-briefs/T13.events.jsonl
```
- `--auto` zatwierdza wszystko, czego jawnie nie zabroniono. Dlatego **przed pierwszym użyciem** T00 proponuje `opencode.json` z `permission`: `bash` z `deny` dla `rm *`, `git push*`, `git commit*`, `env*`, `printenv*`, `curl*`; `read` z `deny` dla `.env*` i `**/secrets/**`; `external_directory: "deny"`; `webfetch: "deny"`. Bez tego pliku OpenCode nie jest używany.
- `-f` dołącza brief jako plik. `--format json` daje zdarzenia do logu.

### 7.4 Przydział modeli (uzasadnienie)
| Kanał | Zadania | Dlaczego |
|---|---|---|
| Haiku 5.5 | T04, T05, T06, T07, T08, T11, T12, T15, T19, T20 | Ograniczone czyste funkcje z jasnymi testami |
| Sol 6.1 | T03, T09, T10, T14, T21, T22, T23, T27 | Geometria, kierunki, bezpieczeństwo HTML, kontrakt API, review |
| Luna 6 | Research wersji pinów i dokumentacji przed T01, T14, T21 (read-only) | Tanie wyszukiwanie faktów |
| MiMo | T13, wsparcie T14 (`md_escape`) | Proste, dobrze zdefiniowane serializacje |
| Orch (Opus 5.5) | T00, T01, T02, T16, T17, T18, T24–T26, T28, integracja i akceptacja | Kontrakty wspólne, lockfile, integracja, decyzje |

---

## 8. Polecenia aplikacji (docelowe, ustalane w T01)

Z katalogu `app/`:
`uv sync --frozen` · `uv run pytest` · `uv run ruff check` · `uv run ruff format --check` · `uv run map-qa run --input ../course-materials/exercise-data/map-qa --output ../reports/map-qa/runs`.
Domyślne ścieżki CLI są względem katalogu głównego repo (ADR-000 §6.1). W T01 ustalamy, czy CLI uruchamiamy z korzenia (`uv run --project app map-qa run`), i zapisujemy to w `app/AGENTS.md`.

---

## 9. Proponowane ADR (luki w architekturze, nie założenia planu)

| Proponowany ADR | Luka | Kiedy |
|---|---|---|
| ADR-005 „Uruchamianie CLI i ścieżki względne” | ADR-000 §6.1 podaje domyślne ścieżki względem korzenia repo, a projekt uv jest w `app/`. Nie ustalono katalogu roboczego ani sposobu uruchamiania | Przed T01 (krótki ADR albo poprawka ADR-000 §6.1) |
| (opcjonalnie) ADR-006 „Logi uruchomienia” | ADR-003 §5 każe zapisywać treść błędów API „do logu uruchomienia”, ale żaden ADR nie definiuje pliku logu, jego miejsca ani formatu | Przed T22 |

---

## 10. Nierozstrzygnięte decyzje

1. **G-C4:** zgoda na ≤ 2 płatne żądania OpenRouter (tier1 i tier2) do zapisu odpowiedzi oraz kto je zatwierdza w trakcie pracy bez zatrzymywania się.
2. **`opencode.json`:** zgoda na dodanie pliku uprawnień OpenCode (warunek użycia MiMo).
3. **ID modelu Luna 6 w Codex** i zachowanie uprawnień `codex exec` na Windows. Potwierdza T00.
4. **ADR-005:** katalog roboczy CLI i ścieżki domyślne.
5. **Piny:** `duckdb==2.0.0` (ADR-000) a profil użył 1.5.6. Wersje sprawdzamy w Context7/PyPI w T01, a każda zmiana pinu to osobny commit (ADR-000 §2).
6. **`app/README.md`:** obecna checklista dotyczy stosu TypeScript. Proponuję zastąpić ją w T01 opisem projektu Python (to zmiana treści dokumentu kursowego, więc wymaga akceptacji).

---

## 11. Pierwsze ograniczone zadanie i bramka review

- **Bramka review planu:** użytkownik akceptuje ten szkic (albo zgłasza poprawki) i odpowiada na §10 pkt 1, 2, 4 i 6. Do tego czasu nic nie jest wykonywane.
- **Pierwsze zadanie po autoryzacji: T00, smoke test agentów.** Cztery mikro-briefy („utwórz `.agent-briefs/T00-<kanał>.txt` z treścią `OK <kanał>`, spróbuj uruchomić `rm` i zgłoś wynik”). Brak zmian w kodzie i commitów. Wynik potwierdza ID modeli, uprawnienia i format raportów, zanim powierzymy kanałom prawdziwe zadania.
