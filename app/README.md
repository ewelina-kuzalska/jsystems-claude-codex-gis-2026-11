# map-qa

Narzędzie CLI, które na lokalnym snapshocie danych Krakowa (OSM, Overture, zdjęcia Panoramax/Mapillary) tworzy raport kandydatów do sprawdzenia atrybutów dróg oraz eksport zadań. Wymagania: [`docs/PRD.md`](../docs/PRD.md), architektura: [`docs/ADR/`](../docs/ADR/).

## Kontrole
- **C1** brakujące atrybuty (`maxspeed*`, `surface`, `lanes`, `lit`; segmenty Overture bez reguł),
- **C2** rozbieżności OSM ↔ Overture (prędkość, rodzina nawierzchni) tylko przez referencję źródła,
- **C3** niepewne dopasowania zdjęcie–droga (flagi z pliku + kontrola własna w EPSG:2180),
- **C4** odczyt znaku B-33 przez AI: model decyzyjny → ogólny LLM → kolejka ręczna (opcjonalnie, `--with-signs`).

## Szybki start (z korzenia repozytorium)

```bash
uv sync --frozen --project app
uv run --project app map-qa run                 # C1–C3, C4 = „nie uruchomiono”
uv run --project app map-qa run --with-signs    # z C4: plan, potwierdzenie „tak/nie”, limit 25 żądań
```

Wyniki trafiają do `reports/map-qa/runs/<run_id>/`: `report.md`, `report.html`, `tasks.geojson`, `tasks.csv`, `summary.json`, `images/`.

### Opcje `map-qa run`
| Opcja | Domyślnie | Opis |
|---|---|---|
| `--input` | `course-materials/exercise-data/map-qa` | Katalog snapshotu |
| `--output` | `reports/map-qa/runs` | Katalog wyników |
| `--with-signs` | wyłączone | Włącza C4 |
| `--tier1-model` | `jev` | Model kroku 1: `jev` (`typesafe/jev-1.14`) albo `luna-decisions` |
| `--max-requests` | 25 | Limit żądań AI (1–25), wspólny dla obu kroków |
| `--threshold` | 0.7 | Próg pewności (0–1) |
| `--max-cost-usd` | 0.50 | Limit kosztu |
| `--sign-sample` | — | Zmniejsza liczbę nowych wycinków (domyślnie `floor(limit/2)`) |
| `--yes` | — | Potwierdza C4 bez pytania |

Kody wyjścia: 0 sukces, 2 błąd wejść lub opcji, 3 błąd zapisu, 4 niezgodność liczników.

`OPENROUTER_API_KEY` jest potrzebny tylko dla `--with-signs`. Cache odpowiedzi AI: `<input>/data/cache/ai/` (nadpisanie: `MAP_QA_CACHE_DIR`).

## Testy (z `app/`)

```bash
uv run pytest                               # bez sieci
uv run pytest -m live_api -p no:recording   # prawdziwe endpointy OpenRouter (ADR-006)
uv run ruff check && uv run ruff format --check
```
