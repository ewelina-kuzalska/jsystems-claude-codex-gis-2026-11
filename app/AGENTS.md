# app/ — map-qa (Python 3.12 + uv)

Lokalne zasady dla agentów pracujących w `app/`. Ogólne reguły są w `../AGENTS.md`, wymagania w `../docs/PRD.md`, decyzje w `../docs/ADR/`.

## Polecenia (z katalogu `app/`)
- `uv sync --frozen` — instalacja z `uv.lock`
- `uv run pytest` — testy unit + integration + e2e bez sieci (`--block-network`, marker `live_api` wykluczony)
- `uv run pytest -m live_api -p no:recording` — testy na prawdziwych endpointach OpenRouter (ADR-006 D-604, wymaga `OPENROUTER_API_KEY`)
- `uv run ruff check` · `uv run ruff format --check`

## Uruchamianie CLI (ADR-005)
- Z korzenia repo: `uv run --project app map-qa run` (domyślne ścieżki są względne do bieżącego katalogu).
- Z `app/`: `uv run map-qa run --input ../course-materials/exercise-data/map-qa --output ../reports/map-qa/runs`.
- Na Windows przy przekierowaniu wyjścia do pliku ustaw `PYTHONUTF8=1`.

## Snapshot z CRLF (Windows, `core.autocrlf=true`)
- Hashe w `sources.json` dotyczą bajtów z gita (LF). Checkout z `autocrlf=true` zamienia LF→CRLF w plikach tekstowych snapshotu i `map-qa run` słusznie kończy się kodem 2 (AC-01). Nie osłabiaj tej kontroli.
- Wierna kopia do testów i QA: `git -c core.autocrlf=false archive HEAD course-materials/exercise-data/map-qa | tar -x -C <katalog>`, potem `MAP_QA_REAL_INPUT=<katalog>/course-materials/exercise-data/map-qa` (testy na pełnym snapshocie) albo `--input` (CLI).

## Zasady
- Piny `==` w `pyproject.toml`; zmiana wersji tylko osobnym commitem po sprawdzeniu dokumentacji (ADR-000 §2).
- Wejścia w `course-materials/exercise-data/map-qa/` są tylko do odczytu. Testy piszą wyłącznie do `tmp_path`.
- Mocki HTTP tylko z zapisów w `tests/fixtures/openrouter/` (ADR-003 §8). Nie wymyślaj kształtów odpowiedzi.
- Teksty dla użytkownika po polsku; identyfikatory, kody przyczyn i pola eksportu po angielsku.
- Szablony Jinja2: zakaz filtra `safe`, `StrictUndefined`.
