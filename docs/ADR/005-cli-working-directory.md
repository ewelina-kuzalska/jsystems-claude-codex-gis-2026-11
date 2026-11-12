# ADR-005: Katalog roboczy CLI i ścieżki domyślne

**Data:** 2026-11-12
**Status:** Accepted
**Relates to:** [`000-main-architecture.md`](000-main-architecture.md) §3 i §6.1, [plan implementacji §9](../plans/implementation-plan.md)

---

## 1. Kontekst

- Projekt uv leży w `app/` (`app/pyproject.toml`, `app/uv.lock`), zgodnie z ADR-000 §3.
- ADR-000 §6.1 podaje ścieżki domyślne CLI względem korzenia repozytorium: `--input course-materials/exercise-data/map-qa` i `--output reports/map-qa/runs`.
- Wejścia, wyniki i cache leżą więc poza katalogiem projektu uv. Dotąd nie ustalono, z którego katalogu uruchamiamy CLI ani jak rozwiązywać ścieżki względne.
- Testy (pytest uruchamiany w `app/`) i E2E muszą działać niezależnie od katalogu, z którego ktoś wywoła polecenie.

## 2. Decyzja

**D-501: CLI uruchamiamy z korzenia repozytorium.**
- Polecenie referencyjne: `uv run --project app map-qa run` (z korzenia). Działa też `cd app && uv run map-qa run --input ../course-materials/exercise-data/map-qa --output ../reports/map-qa/runs`.
- Ścieżki względne w opcjach (`--input`, `--output`) rozwiązujemy względem **bieżącego katalogu roboczego** procesu, tak jak każde narzędzie CLI. Nie szukamy korzenia repo heurystycznie.
- Gdy domyślny `--input` nie istnieje, CLI kończy się kodem 2 i polskim komunikatem: brak katalogu wejść, z podpowiedzią „uruchom z korzenia repozytorium albo podaj `--input`”.

**D-502: Cache AI wynika z katalogu wejść, nie z katalogu roboczego.**
- Domyślny cache to `<input>/data/cache/ai/` (dla dostarczonego snapshotu: `course-materials/exercise-data/map-qa/data/cache/ai/`, zgodnie z ADR-000 §3 i README danych). `MAP_QA_CACHE_DIR` nadal go nadpisuje.

**D-503: Testy nie zależą od katalogu roboczego.**
- Testy jednostkowe i integracyjne podają ścieżki jawnie (fixture'y z `app/tests/fixtures/`, katalogi wyników w `tmp_path`).
- E2E uruchamia `map-qa run` przez `subprocess` z `cwd` ustawionym na korzeń repo (wyliczony z położenia pliku testu) i z `--output` w `tmp_path`, żeby nie zaśmiecać `reports/map-qa/runs/`.

## 3. Odrzucone alternatywy

- **Wyszukiwanie korzenia repo w górę katalogów** (np. po `.git` albo `course-materials/`): magiczne zachowanie i różne wyniki zależnie od miejsca uruchomienia.
- **Ścieżki domyślne względem pakietu (`__file__`)**: działa tylko w instalacji edytowalnej z repo i psuje się po zbudowaniu pakietu.
- **Przeniesienie `pyproject.toml` do korzenia repo**: miesza projekt aplikacji z materiałami kursu, wbrew ADR-000 §3.

## 4. Konsekwencje

- (+) Przewidywalne zachowanie, zgodne z konwencją narzędzi CLI.
- (+) Testy działają z dowolnego katalogu.
- (−) Uruchomienie z `app/` wymaga jawnych ścieżek. Dokumentują to `app/README.md` i `app/AGENTS.md` (plan T01).

## 5. Strategia testów

| Scenariusz | Typ | Oczekiwany wynik |
|---|---|---|
| Domyślny `--input` nie istnieje (cwd = `tmp_path`) | Integration | Kod 2, komunikat z podpowiedzią, brak katalogu wyników |
| Cache domyślny | Unit | `<input>/data/cache/ai` przy braku `MAP_QA_CACHE_DIR` |
| E2E z korzenia | E2E | Kod 0, wyniki w `tmp_path` |

**Review trigger:** pakowanie aplikacji do dystrybucji poza repozytorium.
