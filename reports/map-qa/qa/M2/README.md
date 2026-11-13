# Manual QA — kamień milowy M2 (pełna aplikacja z C4)

**Data:** 2026-11-12 · **Commit aplikacji:** `1a2453a` (po poprawkach z przeglądu T27)
**Wykonał:** orkiestrator (Claude Code). **Akceptacja wyglądu przez człowieka:** ✅ zaakceptowano 2026-11-13.

## Polecenia (prawdziwe endpointy OpenRouter, świeży cache)

```bash
MAP_QA_CACHE_DIR=<scratch>/m2cache uv run --project app map-qa run --input <snapshot> --with-signs --yes --tier1-model jev
MAP_QA_CACHE_DIR=<scratch>/m2cache uv run --project app map-qa run --input <snapshot> --with-signs --yes --tier1-model luna-decisions
```

`<snapshot>`: wierna kopia snapshotu z gita (patrz [M1](../M1/README.md)). Pełne wyjście konsoli: [`console-jev.txt`](console-jev.txt), [`console-luna-decisions.txt`](console-luna-decisions.txt).

| | Jev 1.14 (`20261112T163549Z`) | Luna Decisions (`20261112T163649Z`) |
|---|---|---|
| Kod wyjścia, czas | 0, 58,8 s | 0, 69,7 s |
| Żądania krok 1 / krok 2 / limit | 12 / 0 / 25 | 12 / 4 / 25 |
| Koszt (USD, BYOK `upstream_inference_cost`) | 0,000488 | 0,001141 |
| decision_model / general_llm / human_pending / not_run | 12 / 0 / 0 / 107 | 8 / 2 / 2 / 107 |
| Zgodność z roboczą referencją — krok 1 | 12 / 12 | 8 / 8 |
| Zgodność — krok 2 | 0 / 0 | 2 / 2 |
| Zgodność — wszystkie ostateczne | 12 / 12 | 10 / 10 |
| Surowa zgodność kroku 1 (przed progiem) | 12 / 12 | 8 / 12 |
| Kolejka ręczna | 0 | 2 × `below_threshold` |
| Kandydaci C1 / C2 / C3 / C4 / C4-manual | 170 / 9 / 170 / 6 / 0 | 170 / 9 / 170 / 6 / 2 |

Próbka to pierwsze 12 wycinków (`floor(25/2)`), więc porównanie modeli jest orientacyjne. Powtórka na tym samym cache i tych samych wycinkach (`--sign-sample 0`) wysyła 0 żądań — sprawdza to test `live_api` `tests/e2e/test_cli_c4_live.py` (zaliczony dla obu modeli).

## Przeglądarka (Playwright 1.56.1, Edge, plik z dysku)

| | Jev | Luna Decisions |
|---|---|---|
| Błędy konsoli / strony / nieudane żądania / żądania zewnętrzne | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| Obrazy załadowane | 51 / 51 | 53 / 53 |
| Polskie znaki | OK | OK |
| `data-count` C4 / C4-manual | 6 / 0 | 6 / 2 |

Zrzuty każdej sekcji: [`jev/`](jev/) i [`luna-decisions/`](luna-decisions/) (m.in. `03-c4-block.png`: blok C4 z zastrzeżeniem o etykietach i tabelą wszystkich odczytów; `08-manual.png`: kolejka ręczna z wycinkami i podpowiedziami obu kroków, bez etykiety referencyjnej).

## Ślad jednego wiersza C4

Zadanie `7d1716b93c62c686` (run Jev, C4 `osm_missing_speed`):
1. `signs/signs.csv`: `mapillary_1032959014995687`, `compass_angle` 347,9°, Mapillary `maximum-speed-limit-60`.
2. Kontrola wycinka: hash zgodny, JPEG bez APP1 → wysłany (po `JEV_RESIZE_V1`).
3. Jev: `60`, p = 0,99 ≥ 0,70 → `decision_model`.
4. `signs/nearest_osm.csv`: way 1266239200 ze snapshotu, 0,59 m, bez `maxspeed` → `osm_missing_speed`.
5. Wiersz w `tasks.csv`, `tasks.geojson` (pełne tagi drogi w `osm_raw`) i `report.html`. Etykieta referencyjna (60, `certain`) użyta tylko w ewaluacji.

## Uwagi

- Wszystkie 3 pliki `signs/` mają ostrzeżenie `hash_not_in_manifest` (zgodnie z ADR-001 §3.1); integralność wycinków zapewnia `crop_sha256`.
- Odczyty modeli nie są prawdą terenową, a etykiety referencyjne to zgodność dwóch modeli AI — raport to zaznacza.
