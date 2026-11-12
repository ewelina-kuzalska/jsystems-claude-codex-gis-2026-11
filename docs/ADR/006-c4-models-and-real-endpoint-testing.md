# ADR-006: Modele C4 (Jev, Luna Decisions, Luna LLM) i testy na prawdziwych endpointach

**Data:** 2026-11-12
**Status:** Accepted (decyzja użytkownika). ID modeli: `typesafe/jev-1.14` (domyślny krok 1), `openai/gpt-6-luna-decisions` (opcjonalny krok 1), `openai/gpt-6-luna` (krok 2). **T00b (2026-11-12) potwierdził** przyjęcie żądań dla wszystkich trzech ID, kształt obrazu w `state` (`image_url` z data URL), pytanie `choice` i opóźnienie (§6)
**Supersedes:** [ADR-000](000-main-architecture.md) D-03 i D-04
**Relates to:** [ADR-003](003-ai-sign-reading.md), [PRD AC-20–AC-28](../PRD.md)

---

## 1. Kontekst

- ADR-000 wybrał Lunę Decisions dla kroku 1 i Claude Haiku 5.5 dla kroku 2, żeby kroki pochodziły z różnych rodzin modeli.
- 2026-11-12 użytkownik zdecydował:
  - krok 1 do wyboru: **Jev** albo **Luna Decisions**, porównywane na próbce znaków,
  - krok 2: **zwykła Luna LLM** zamiast Haiku 5.5,
  - limity aplikacji bez zmian (25 żądań i 0,50 USD na uruchomienie, PRD AC-23),
  - wywołania tych trzech modeli w testach są tanie (łącznie znacznie poniżej 1 USD) i **nie wymagają osobnej zgody** na każde wywołanie.
- **Fakty sprawdzone 2026-11-12** (publiczny `GET https://openrouter.ai/api/v1/models`, bez klucza):

  | Model | ID | Wejście | Cena (USD / mln tokenów, wejście / wyjście) | Parametry |
  |---|---|---|---|---|
  | Luna LLM | `openai/gpt-6-luna` | text, image, file | 0,10 / 0,50 | `reasoning`, `response_format`, `structured_outputs` |
  | Luna LLM Pro (niewybrana) | `openai/gpt-6-luna-pro` | text, image, file | 0,10 / 0,50 | jak wyżej |
  | Jev (router) | `typesafe/jev-router` | audio, file, image, text, video | cena dynamiczna (`-1`) | `reasoning`, `response_format`, `structured_outputs` |
  | Luna Decisions | `openai/gpt-6-luna-decisions` | text, image | **0,10 / 0** (kontekst 1,1 mln) | Decisions API; brak w `/api/v1/models`, dane z karty modelu https://openrouter.ai/openai/gpt-6-luna-decisions |
  | Jev 1.14 | `typesafe/jev-1.14` | text, image | **0,042 / 0** (kontekst 262 tys.) | Decisions API; brak w `/api/v1/models`, dane z karty modelu https://openrouter.ai/typesafe/jev-1.14 |

  Ceny i kontekst modeli decyzyjnych pochodzą z kart modeli przekazanych przez prowadzącego (2026-11-12). Wyjście modeli decyzyjnych jest bezpłatne. Opóźnienie, obsługiwane typy pytań i rzeczywisty koszt (`usage.cost`) mierzy T00b.

- **Wycinki znaków:** 108 ze 119 ma krótszy bok poniżej 256 px (min 49, mediana 130, max 1536 px). Według ADR-000 D-03 Jev wymaga co najmniej 256 px na bok.

## 2. Decyzje

### D-601: Krok 1 z wyborem modelu decyzyjnego
- Nowa opcja CLI `--tier1-model {jev,luna-decisions}`, **domyślnie `jev`** (`typesafe/jev-1.14`; decyzja prowadzącego/użytkownika 2026-11-12: „Model decyzyjny: typesafe/jev-1.14, opcjonalnie zamiast Jev: openai/gpt-6-luna-decisions”). Jev jest też ponad 2× tańszy na wejściu (0,042 wobec 0,10 USD za mln tokenów). Oba modele działają przez Decisions API (`POST /api/alpha/decisions`) z tym samym pytaniem `choice` (ADR-003 §3.3).
- Klucz cache zawiera `model_id`, więc wyniki obu modeli współistnieją (ADR-003 §3.7).
- Raport pokazuje accuracy osobno per model kroku 1 (AC-28 per tier **i** per model).
- **Porównanie** to osobne uruchomienia z różnym `--tier1-model` na tej samej próbce. Każde mieści się w limicie 25 żądań. Nie ma trybu „oba modele w jednym uruchomieniu”, żeby nie łamać AC-23.

### D-602: Krok 2 to Luna LLM (`openai/gpt-6-luna`)
- Chat completions jak w ADR-003 §3.4: `reasoning.effort = "medium"`, `response_format` `json_schema` strict, `provider.require_parameters = true`.
- **Świadomy kompromis:** kroki 1 i 2 pochodzą z jednej rodziny (OpenAI Luna), więc mogą mylić się na tych samych obrazach. Mierzy to accuracy per krok (AC-28). Review trigger poniżej.

### D-603: Obraz dla Jev
- Luna Decisions i Luna LLM dostają **oryginalne bajty** wycinka, jak dotąd (D-304).
- Jev dostaje wycinek **deterministycznie przeskalowany** (`JEV_RESIZE_V1`) tak, żeby spełnić limity TypeSafe: każdy bok **280–1568 px** i łącznie **78 400–2 458 624 px** (https://docs.typesafe.ai/images, sekcja „Limits”). Skala `s` to najmniejsza wartość ≥ 1 spełniająca minima (powiększenie, boki zaokrąglane w górę) albo największa wartość < 1 spełniająca maksima (zmniejszenie, boki zaokrąglane w dół). Pillow 12.0.0, filtr `LANCZOS`, zapis PNG bez metadanych. Wycinki, które już mieszczą się w limitach, idą bez zmian.
- Kontrola fail-closed (hash z `signs.csv`, format, brak EXIF) działa na **oryginale**, przed skalowaniem. Klucz cache i streszczenie żądania zawierają SHA-256 **wysłanych** bajtów oraz wersję transformacji `JEV_RESIZE_V1`.
- Pillow staje się zależnością aplikacji (`pillow==12.0.0`). To zmienia D-304 tylko dla ścieżki Jev.
- ✅ **Zweryfikowane w T00b (2026-11-12):** oryginał 175×172 i powiększenie do 283×278 (minimum 256 px z przewodnika OpenRouter) dają `400 Invalid image dimensions`. Powiększenie do 285×280 daje 200. Przewodnik OpenRouter podaje 256 px, ale obowiązuje 280 px z dokumentacji TypeSafe. 6 ze 119 wycinków ma dłuższy bok 2048 px (> 1568), więc `JEV_RESIZE_V1` także zmniejsza. Zapisy: `app/tests/fixtures/openrouter/jev-small-original.json`, `jev-283x278-rejected.json`, `tier1-jev-*.json`.

### D-604: Testy na prawdziwych endpointach (zasada obowiązująca w całym projekcie)
- **Testy manualne i E2E wołają prawdziwe endpointy** Jev, Luny Decisions i Luny LLM. E2E dla C4 to dwa uruchomienia na świeżym katalogu cache w `tmp_path`: pierwsze z prawdziwymi żądaniami (w limicie aplikacji), drugie na tym samym cache z zerem nowych żądań (AC-26).
- **Mocki wolno stosować tylko w testach jednostkowych i integracyjnych**, i tylko wyprowadzone z zapisu prawdziwego żądania i odpowiedzi (ADR-003 §8, AGENTS.md). Zapis robimy **przed** napisaniem pierwszego mocka i przed implementacją parsera.
- **Zapis obejmuje**: zaakceptowane ciało żądania (bez obrazu, z jego SHA-256), status, dozwolone nagłówki, pełne ciało odpowiedzi, datę, model i wersję httpx. Dla każdego modelu: odpowiedź poprawną, odpowiedź na wycinek „trudny” (`unreadable` lub niska pewność) i dla Decisions odpowiedź 401 bez klucza.
- Wywołania tych modeli w testach i podczas implementacji są z góry zatwierdzone przez użytkownika (zastępuje bramki G-401 i G-C4 z planu). Limity aplikacji (AC-23) obowiązują nadal w każdym uruchomieniu CLI.
- Testy E2E z prawdziwym API mają marker `live_api` i są wykluczone z domyślnego `uv run pytest` (który ma `--block-network`, TAC-03). Uruchamia się je jawnie: `uv run pytest -m live_api -p no:recording`. Brak klucza daje `skip` z powodem, a nie fałszywy sukces.

## 3. Odrzucone alternatywy
- **Pozostanie przy Haiku 5.5 w kroku 2:** odrzucone decyzją użytkownika (koszt, jednorodność).
- **Oba modele kroku 1 w jednym uruchomieniu:** podwaja żądania i łamie limit 25 (AC-23).
- **Powiększanie wszystkich wycinków:** zmienia wejście modeli, które obsługują małe obrazy, i miesza wyniki porównania.
- **Pominięcie Jev dla wycinków < 256 px:** zostałoby tylko 11 wycinków, więc porównanie byłoby bezwartościowe.

## 4. Konsekwencje
- (+) Tańsze kroki i porównanie dwóch modeli decyzyjnych na tej samej próbce.
- (+) Kontrakty odpowiedzi pochodzą z prawdziwych zapisów, a nie z dokumentacji.
- (−) Jedna rodzina modeli w krokach 1 (Luna) i 2 grozi skorelowanymi błędami.
- (−) Nowa zależność Pillow i transformacja obrazu dla Jev.
- (−) Testy `live_api` zależą od sieci i dostępności dostawcy, więc są wykluczone z domyślnego zestawu.

## 5. Pomiary T00b (2026-11-12, 9 żądań, z czego 7 płatnych)

| Model | Odpowiedź (`model`) | Czas (s) | Koszt na żądanie (USD) | Uwagi |
|---|---|---|---|---|
| Jev 1.14 | `typesafe/jev-1.14-20261014` | 0,36–0,55 | ok. 0,00004 | Obraz w `state` jako `image_url` (data URL PNG); ok. 950 tokenów wejścia |
| Luna Decisions | `openai/gpt-6-luna-decisions-20261006` | 0,67–0,95 | ok. 0,00004 | Oryginalny JPEG; ok. 400 tokenów wejścia, 0 wyjścia |
| Luna LLM | `openai/gpt-6-luna` (dostawca Azure) | 2,9–4,4 | 0,00005–0,00012 | `json_schema` strict przyjęty; treść poprzedzona białymi znakami (keep-alive) |

- **Koszt przy kluczu BYOK:** odpowiedzi mają `usage.is_byok = true` i `usage.cost = 0`, a rzeczywisty koszt jest w `usage.cost_details.upstream_inference_cost`. Licznik kosztu (ADR-003 §3.6) sumuje `usage.cost` **plus** `usage.cost_details.upstream_inference_cost`, gdy `is_byok = true`. Brak obu pól daje `cost_unknown`.
- 401 bez klucza: `{"error":{"message":"No cookie auth credentials found","code":401}}`.
- Na wycinku trudnym (etykieta `unreadable`) Jev odpowiedział `50` z p = 0,84, Luna Decisions `unreadable`, a Luna LLM `30` z pewnością 0,38. Jev może więc dawać pewne odpowiedzi na nieczytelnych wycinkach; porównanie modeli w T28.

## 6. Review trigger
- Accuracy kroku 2 nie lepsze niż kroku 1 na eskalowanych wycinkach → rozważyć model innej rodziny.
- Jev zacznie przyjmować obrazy < 280 px → uprościć D-603.
- Koszt lub opóźnienie zmierzone w T00b odbiegają od kart modeli → uzupełnić tabelę i limit kosztu.
- Jev ma accuracy niższe niż Luna Decisions na tej samej próbce (porównanie z D-601) → rozważyć zmianę domyślnego modelu.
