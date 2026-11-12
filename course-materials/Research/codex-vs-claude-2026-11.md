# Codex czy Claude Code: stan na listopad 2026 i moja rekomendacja

Krótkie podsumowanie tego, co sprawdziłem i czego doświadczam w codziennej pracy. Stan na 11.11.2026. Narzędzia zmieniają się co tydzień, więc traktuj to jako migawkę, nie stały ranking.

## Moja rekomendacja

Gdybym dziś miał wybrać jedno narzędzie, wybrałbym **Claude Code**, a **Codex z Sol 6.1** trzymałbym jako zapasowe narzędzie i wykonawcę zadań delegowanych przez `codex exec`.

- **Opus 5.5** to obecnie najlepszy model do codziennej pracy: planuje, orkiestruje subagentów i dobrze odczytuje intencję.
- **Fable 5.2** (premiera 9.11.2026) według Anthropic jest mocniejszy od Opus 5.5 i tańszy od Fable 5.1: 8 USD za milion tokenów wejściowych i 40 USD za milion wyjściowych, wobec 10 i 50 USD dla 5.1. Używaj go do najtrudniejszych zadań.
- **Harness Claude Code** działa dziś stabilniej w moich workflow: tryb auto, subagenci, z którymi można rozmawiać bezpośrednio, i brak problemów z sandboxem Windows opisanych niżej.

**To kwestia stylu pracy.** Sol wykonuje polecenia dosłownie, jak specjalista, który robi dokładnie to, co mu kazano. Opus częściej domyśla się, o co Ci naprawdę chodzi, i działa jak kreatywny kierownik albo orkiestrator. Ja wolę Opus. Jeśli lubisz prowadzić model krok po kroku i chcesz, żeby nie interpretował poleceń, Sol może Ci odpowiadać bardziej. Sprawdź oba na tym samym zadaniu.

## Co się dzieje w OpenAI

- **Zmiany w zarządzie:** według doniesień z sierpnia 2026 r. z OpenAI odeszło w tym roku 14 członków kadry kierowniczej, m.in. z obszarów przychodów, produktu i nauki; firma przygotowuje się do IPO ([Yahoo Finance](https://finance.yahoo.com/technology/ai/articles/12-executives-left-openai-2026-022816160.html), [Axios](https://www.axios.com/2026/08/14/openai-executive-greg-brockman-ipo)).
- **Microsoft:** w kwietniu 2026 r. umowa została zmieniona. Microsoft stracił wyłączność na sprzedaż modeli OpenAI w chmurze, a licencja na IP jest niewyłączna do 2032 r. ([Irish Times](https://www.irishtimes.com/business/2026/04/28/openai-and-microsoft-loosen-ties-in-revised-ai-deal/), [Tom's Hardware](https://www.tomshardware.com/tech-industry/artificial-intelligence/openai-and-microsofts-alliance-fractures-as-cloud-exclusivity-deal-ends-azures-single-provider-monopoly-for-chatgpt-is-officially-over)).
- **"Selected model is at capacity" i wolne odpowiedzi:** użytkownicy zgłaszają te błędy na wszystkich planach, także Pro, m.in. w październiku 2026 r. ([#53591](https://github.com/openai/codex/issues/53591), [#59600](https://github.com/openai/codex/issues/59600), [#56206](https://github.com/openai/codex/issues/56206)). Na stronie statusu OpenAI oficjalny incydent tego typu znalazłem tylko z czerwca 2026 r.
- **Jakość Sol 6.1:** wielu użytkowników, w tym ja, ma wrażenie, że model działa słabiej niż w pierwszym miesiącu. Przyczyny nie znamy: mogą to być zmiany w harnessie i promptach systemowych, inne ustawienia albo coś innego. Nie ma publicznego dowodu na kwantyzację, więc traktuj to jako obserwację, nie fakt.
- **Aplikacja desktopowa:** po połączeniu Codex z aplikacją ChatGPT działa u mnie wolniej i jest bardziej przeładowana. To moje doświadczenie, nie pomiar.

Ani zmiany w zarządzie, ani umowa z Microsoftem nie dowodzą, że to one spowodowały konkretną awarię albo spadek jakości. Oceniaj modele na tych samych zadaniach, z tymi samymi ustawieniami. Historię awarii obu firm zobaczysz na [status.openai.com](https://status.openai.com/) i [status.claude.com](https://status.claude.com/).

## Pytania interaktywne w Codex

Poza trybem Plan pytania Codex nie zatrzymują agenta. W sprawdzonym kodzie CLI 0.166.0 formularz ma licznik: 60 s niewidocznego czasu i 60 s widocznego odliczania. Model nie ma parametru, którym mógłby ustawić czekanie na odpowiedź. Agent pracuje dalej, a niewypełniony formularz znika. Pełny opis i obejścia: [pytania Codex](codex-interactive-questions-2026-11-05.md).

**Co robić:** decyzje zbieraj w trybie Plan (`/plan`) albo odpowiadaj zwykłą wiadomością i nazwij decyzję. Pominięcie pytania albo upływ czasu nie jest Twoją odpowiedzią.

## Sandbox i zgody: Codex a Claude Code

| | Codex | Claude Code |
|---|---|---|
| Domyślna izolacja | Sandbox systemowy (`workspace-write`): zapis w projekcie, bez sieci | Na natywnym Windows brak sandboxa; `/sandbox` działa na macOS, Linux i WSL2 |
| Kto decyduje o akcji | Akcje wewnątrz sandboxa wykonują się bez pytania. Pytanie pojawia się tylko na granicy sandboxa: zapis poza projektem, sieć, `request_permissions`, narzędzia MCP ze skutkami ubocznymi | Każde wywołanie narzędzia przechodzi przez reguły i tryb uprawnień |
| Tryb automatyczny | **Approve for me** (`approvals_reviewer = "auto_review"`): agent-recenzent ocenia tylko te prośby o wyjście poza sandbox | **Tryb auto**: model-klasyfikator ocenia polecenia powłoki i żądania sieciowe; odczyty i edycje w katalogu roboczym przechodzą od razu |
| Bez izolacji | `--dangerously-bypass-approvals-and-sandbox`: brak sandboxa i brak zgód; recenzent nie ma czego oceniać | Tryb auto nadal działa bez sandboxa; `--dangerously-skip-permissions` wyłącza też klasyfikator |

**Approve for me w Codex zatwierdza więc to, co zablokował sandbox.** Jeśli wyłączysz sandbox, prawie nic nie trafia do recenzji ([dokumentacja Codex](https://learn.chatgpt.com/docs/agent-approvals-security)).

**Tryb auto w Claude Code ocenia akcje także bez sandboxa.** Domyślnie blokuje np. `curl | bash`, wdrożenia produkcyjne, force push i polecenia z ograniczeniami, które podałeś w rozmowie ("nie pushuj"). Usunięcie ważnych ścieżek i pytania `AskUserQuestion` nadal trafiają do Ciebie. Po 3 blokadach z rzędu albo 20 łącznie wraca do zwykłych pytań. Według Anthropic tryb auto ogranicza liczbę pytań, ale nie gwarantuje bezpieczeństwa ([dokumentacja Claude Code](https://code.claude.com/docs/en/permission-modes)).

## Sandbox Codex na Windows w praktyce

Nowy sandbox **MXC** nie obsługuje jeszcze wszystkich workflow z kursu. Blokuje między innymi:

- `gh`, który pobiera token z Menedżera poświadczeń Windows;
- Playwright z profilem użytkownika Chrome albo z rozszerzeniem Playwright.

Do tych narzędzi masz trzy możliwości:

- **sandbox `elevated` z regułami**, które wypuszczają wybrane polecenia poza sandbox. To przetestowana konfiguracja kursowa: [instrukcja Windows](../agent-configs/codex/WINDOWS-QUICKSTART-PL.md);
- **sandbox `unelevated`**, który jest prostszy, ale nie blokuje odczytu `.env` i sekretów tak jak profil ścisły;
- **pełny dostęp** (`--dangerously-bypass-approvals-and-sandbox`), tylko na maszynie bez sekretów i tylko na czas zadania.

Do zadań z `gh` i Playwright najprostszy jest dziś Claude Code. Szczegóły błędów i diagnostyki: [fakty o sandboxie](codex-sandbox-facts-and-limitations-2026-11-06.md), [zgodność sandboxa Windows](codex-windows-sandbox-compatibility-2026-11-05.md).
