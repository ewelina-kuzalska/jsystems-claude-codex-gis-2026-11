# Zapisy prawdziwych odpowiedzi OpenRouter (T00b)

Źródło mocków dla testów unit/integration `ai_client` (ADR-003 §8, ADR-006 D-604). Nie edytuj ręcznie, nie wymyślaj nowych kształtów odpowiedzi.

- **Data:** 2026-11-12 · **Skrypt:** `app/scripts/capture_openrouter.py` · **httpx:** 0.28.1
- **Endpointy:** `POST https://openrouter.ai/api/alpha/decisions` (krok 1), `POST https://openrouter.ai/api/v1/chat/completions` (krok 2)
- **Wycinki:** `mapillary_1237130608489136` (etykieta 50, 175×172) i `mapillary_137982605041578` (etykieta `unreadable`, 85×78)
- Plik nie zawiera nagłówka autoryzacji ani obrazu; `request_summary` ma `<image sha256=…>` w miejscu data URL.

| Plik | Model | Status | Zawartość |
|---|---|---|---|
| `tier1-jev-readable.json` | `typesafe/jev-1.14` | 200 | `choice=50`, p=1,0 (obraz 285×280, `JEV_RESIZE_V1`) |
| `tier1-jev-hard.json` | `typesafe/jev-1.14` | 200 | `choice=50`, p=0,84 na wycinku nieczytelnym |
| `tier1-luna-readable.json` | `openai/gpt-6-luna-decisions` | 200 | `choice=50`, p=0,97 |
| `tier1-luna-hard.json` | `openai/gpt-6-luna-decisions` | 200 | `choice=unreadable` |
| `tier2-luna-readable.json` | `openai/gpt-6-luna` | 200 | `{"answer":"50","value_kmh":50,"confidence":0.99}` |
| `tier2-luna-hard.json` | `openai/gpt-6-luna` | 200 | `{"answer":"30","value_kmh":30,"confidence":0.38}` |
| `error-401-decisions.json` | `typesafe/jev-1.14` | 401 | Żądanie bez klucza |
| `jev-small-original.json` | `typesafe/jev-1.14` | 400 | Oryginał 175×172: `Invalid image dimensions.` |
| `jev-283x278-rejected.json` | `typesafe/jev-1.14` | 400 | 283×278 (< 280 px): `Invalid image dimensions.` |

Pola pliku (`CapturedFixture`, ADR-003 §4): `captured_at`, `endpoint`, `model`, `contract_versions`, `httpx_version`, `note`, `sent_image_sha256`, `sent_image_size`, `elapsed_s`, `request_summary`, `status`, `headers` (tylko `content-type`, `date`, `x-request-id`, `x-generation-id`), `body` (ciało odpowiedzi bez zmian, jako tekst).

Klucz był typu BYOK: `usage.cost = 0`, koszt w `usage.cost_details.upstream_inference_cost` (ADR-006 §5).
