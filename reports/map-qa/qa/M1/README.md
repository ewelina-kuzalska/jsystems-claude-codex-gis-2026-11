# Manual QA — kamień milowy M1 (aplikacja bez C4)

**Data:** 2026-11-12 · **Commit aplikacji:** `b9c6a98` · **Uruchomienie:** `20261112T154614Z`
**Wykonał:** orkiestrator (Claude Code). **Akceptacja wyglądu przez człowieka:** ⏳ oczekuje (plan §6, bramka 2).

## Polecenie

```bash
uv run --project app map-qa run --input <snapshot> --output reports/map-qa/runs
```

`<snapshot>` to wierna kopia `course-materials/exercise-data/map-qa` z gita
(`git -c core.autocrlf=false archive HEAD … | tar -x`). Kopia robocza w tym checkoucie ma CRLF w
plikach tekstowych (Windows `core.autocrlf=true`), więc ich SHA-256 nie zgadza się z manifestem;
`map-qa run` na niej kończy się kodem 2 bez wyników, zgodnie z AC-01 (sprawdzone).

| Sprawdzenie | Wynik |
|---|---|
| Kod wyjścia, czas | 0, 44,6 s (TAC-04: < 120 s) |
| Konsola | daty snapshotu, liczności 99 768 / 85 405 / 561 / 561, linia postępu per kontrola, liczniki, 4 ścieżki |
| Liczniki | C1 170 · C2 9 · C3 170 · C4 0 · C4-manual 0, identyczne w MD, HTML (`data-count`), GeoJSON, CSV |
| C2 | 105 809 par, 64 643 porównań = 9 kandydatów + 32 249 nieporównywalnych + 32 385 zgodnych |
| C3 | 558/558 sprawdzonych linków `ok` (TAC-002-03), 170 zdjęć z flagą = 170 wierszy C3 (TAC-002-04) |
| C4 | „nie uruchomiono” z powodem (AC-20) |

## Przeglądarka (Playwright 1.56.1, Microsoft Edge, plik z dysku)

Wynik automatycznej części: [`playwright-result.json`](playwright-result.json).

- `lang="pl"`, tytuł po polsku, polskie znaki poprawne (brak `U+FFFD`).
- Błędy konsoli: 0. Błędy strony: 0. Nieudane żądania: 0. Żądania poza `file:`: 0.
- Obrazy: 45/45 załadowane (`images/…`, ścieżki względne, bez base64). Miniatury lokalne 32 z 267 zdjęć w zadaniach; pozostałe pokazują „Obraz niedostępny lokalnie” + link (ADR-004 §3.3, decyzja 2A).
- Zrzut każdej sekcji: [01 nagłówek](01-top.png) · [02 podsumowanie](02-summary.png) · [03 blok C4](03-c4-block.png) · [04 C1](04-c1.png) · [05 C2](05-c2.png) · [06 C3](06-c3.png) · [07 C4](07-c4.png) · [08 kolejka ręczna](08-manual.png) · [09 nieporównywalne](09-not-comparable.png) · [10 tylko przestrzenne](10-spatial-only.png) · [11 mapowanie nawierzchni](11-surface-mapping.png) · [12 zastrzeżenia](12-disclaimers.png).

## Ślad jednego wiersza (wejście → raport)

Zadanie `54418d9b6a492b09` (C1 `missing_maxspeed`):
1. `photo_road_links.csv`: `mapillary_1393481265317315` → `osm_way_id` 42289812, 4,551 m, bez flag.
2. `osm_roads.parquet`: way 42289812, `highway=tertiary`, brak `maxspeed`, `maxspeed:forward`, `maxspeed:backward`.
3. `tasks.csv` / `tasks.geojson`: ten sam `task_id`, `osm_raw` identyczne w obu plikach (pełne tagi, AC-04), punkt środkowy linii 20.1411615 E, 50.0657541 N (Kraków).
4. Wiersz obecny w `report.html` i `report.md`.

## Wzorzec wizualny

Brak `docs/design-guidelines.md` i `assets/design-tokens.json` (decyzja planu §1): obowiązuje minimalny CSS z ADR-004 §3.4. Strona jest czytelna, tabele mają przewijanie poziome, kolory notatek o niepewności są wyróżnione. Ostateczną akceptację wyglądu daje człowiek.

## Uwagi

- Nieporównywalnych jest 32 249 (głównie `partial_source`: segmenty Overture zbudowane z kilku way). Raport pokazuje liczniki per kod i do 20 przykładów na kod; pełna lista jest w `not_comparable.csv` w katalogu uruchomienia.
- `tasks.geojson` sprawdzony automatycznie: wszystkie współrzędne w okolicy Krakowa (test E2E `test_geojson_in_krakow`); otwarcie w QGIS pozostaje do ręcznej akceptacji.
