# ADR-006: Modele C4 (Jev, Luna Decisions, Luna LLM) i testy na prawdziwych endpointach

**Data:** 2026-11-12
**Status:** Accepted (decyzja użytkownika). Identyfikatory modeli oznaczone ⏳ potwierdza pierwsze prawdziwe wywołanie (zadanie T00b w planie)
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
  | Luna Decisions | `openai/gpt-6-luna-decisions` ⏳ | — | — | **brak w publicznym katalogu** |
  | Jev 1.14 | `typesafe/jev-1.14` ⏳ | — | — | **brak w publicznym katalogu** |

- **Wycinki znaków:** 108 ze 119 ma krótszy bok poniżej 256 px (min 49, mediana 130, max 1536 px). Według ADR-000 D-03 Jev wymaga co najmniej 256 px na bok.

## 2. Decyzje

### D-601: Krok 1 z wyborem modelu decyzyjnego
- Nowa opcja CLI `--tier1-model {luna-decisions,jev}`, domyślnie `luna-decisions`. Oba modele działają przez Decisions API (`POST /api/alpha/decisions`) z tym samym pytaniem `choice` (ADR-003 §3.3).
- Klucz cache zawiera `model_id`, więc wyniki obu modeli współistnieją (ADR-003 §3.7).
- Raport pokazuje accuracy osobno per model kroku 1 (AC-28 per tier **i** per model).
- **Porównanie** to osobne uruchomienia z różnym `--tier1-model` na tej samej próbce. Każde mieści się w limicie 25 żądań. Nie ma trybu „oba modele w jednym uruchomieniu”, żeby nie łamać AC-23.

### D-602: Krok 2 to Luna LLM (`openai/gpt-6-luna`)
- Chat completions jak w ADR-003 §3.4: `reasoning.effort = "medium"`, `response_format` `json_schema` strict, `provider.require_parameters = true`.
- **Świadomy kompromis:** kroki 1 i 2 pochodzą z jednej rodziny (OpenAI Luna), więc mogą mylić się na tych samych obrazach. Mierzy to accuracy per krok (AC-28). Review trigger poniżej.

### D-603: Obraz dla Jev
- Luna Decisions i Luna LLM dostają **oryginalne bajty** wycinka, jak dotąd (D-304).
- Jev dostaje wycinek **deterministycznie powiększony** tak, żeby krótszy bok miał 256 px: Pillow 12.0.0 (już używany przez skrypty danych), filtr `LANCZOS`, zapis PNG bez metadanych. Wycinki, które już mają ≥ 256 px, idą bez zmian.
- Kontrola fail-closed (hash z `signs.csv`, format, brak EXIF) działa na **oryginale**, przed powiększeniem. Klucz cache i streszczenie żądania zawierają SHA-256 **wysłanych** bajtów oraz wersję transformacji `JEV_UPSCALE_V1`.
- Pillow staje się zależnością aplikacji (`pillow==12.0.0`). To zmienia D-304 tylko dla ścieżki Jev.
- ⏳ Wymóg 256 px pochodzi z dokumentacji z 2026-11-03. Pierwsze prawdziwe wywołanie (T00b) sprawdza, czy Jev przyjmuje wycinek < 256 px. Jeśli tak, D-603 upraszczamy do oryginalnych bajtów.

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

## 5. Review trigger
- Accuracy kroku 2 nie lepsze niż kroku 1 na eskalowanych wycinkach → rozważyć model innej rodziny.
- Jev przyjmuje obrazy < 256 px (T00b) → usunąć D-603.
- Luna Decisions albo Jev 1.14 pojawiają się w publicznym katalogu z ceną → uzupełnić tabelę i limit kosztu.
