# UPDATES !!!

## Przed blokiem 2 (12-13.11)

- [Codex czy Claude Code: stan na listopad 2026 i moja rekomendacja](course-materials/Research/codex-vs-claude-2026-11.md), w tym sandbox, zgody i pytania interaktywne.
- [Ctrl+G: długi prompt w edytorze](course-materials/agent-configs/README.md#ctrlg-długi-prompt-w-edytorze), przyda się przy promptach planu.
- [Sandbox Codex na Windows: profile uprawnień, gh i Playwright](course-materials/agent-configs/codex/WINDOWS-QUICKSTART-PL.md).
- [Review PR z forka](course-materials/Research/github-fork-pr-review-workshop-2026-11-05.md).

## Po pierwszych dwóch dniach (2-3.11)

**Projekt z zajęć:**

- Praca nad aplikacją (PRD, ADR, plan) jest w [PR #6](https://github.com/LucasMatuszewski/jsystems-claude-codex-gis-2026-11/pull/6), gałąź `worktree-prototype-a`.
- Gałąź `main` zostaje bazą startową kursu z materiałami i aktualizacjami.

**Podsumowania i historia czatu** (wszystkie linki, komendy i konfiguracje z zajęć):

- Dzień 1: [podsumowanie](course-materials/zoom-summary-chat-history/day-1-summary.md), [historia czatu](course-materials/zoom-summary-chat-history/day-1-chat-history.md)
- Dzień 2: [podsumowanie](course-materials/zoom-summary-chat-history/day-2-summary.md), [historia czatu](course-materials/zoom-summary-chat-history/day-2-chat-history.md)

**Konta szkoleniowe działają do 29 listopada.** Korzystajcie z nich jak najwięcej.

- OpenAI (ChatGPT, Codex): logowanie prywatnym adresem e-mail.
- Anthropic (Claude Code): logowanie adresem w domenie devpowers.com, który ode mnie dostaliście.

**Zadanie na dwa tygodnie przerwy:**

- Dokończcie po swojemu ćwiczenie z planem (PRD, ADR, plan, realizacja) albo zbudujcie własną aplikację.
- Użyjcie jak najwięcej z tego, co przerobiliśmy: skills, MCP i Context7, uprawnienia, Git Worktree, GitHub CLI.
- 12 listopada wrócimy do tego razem i dokończymy wspólnie. Pójdzie szybciej, bo prawie wszystko dla agentów jest już zainstalowane.

**`/goal` w Codex** (więcej 12 listopada):

- Ustawia cel, do którego agent dąży przez wiele kolejnych tur, aż uzna go za osiągnięty, np. `/goal zrealizuj plan z pliku @plik-z-planem.md`.
- Cel można wstrzymać i wznowić (`/goal pause`, `/goal resume`) albo usunąć (`/goal clear`).
- Długie cele zużywają dużo tokenów.

**Spec-Driven Development:**

- PRD, ADR i plan, nad którymi pracowaliśmy, to moja wersja SDD. Najlepiej dopasować ją do swojego projektu i zespołu.
- Najważniejsze: dać agentom kompletne środowisko informacji i dobrze skonfigurowany harness, tak aby mogli samodzielnie przejść cały proces.
- Inne podejścia: [GitHub Spec Kit](https://github.com/github/spec-kit), [specs.md](https://specs.md/) z przepływem [FIRE](https://specs.md/fire-flow/overview.md).
- Skills: [write-prd](https://github.com/EdukeyTeam/agent-toolbox/tree/main/skills/write-prd), [write-adr](https://github.com/EdukeyTeam/agent-toolbox/tree/main/skills/write-adr), [skill planowania](https://github.com/EdukeyTeam/agent-toolbox/pull/28) (otwarty PR).

---

# AI dla programistów: agenci AI w pracy z danymi GIS (Claude Code i Codex) (JSystems)

Wybierz materiał do zadania:

- **Główne ćwiczenie:** [kontrola mapy: od danych do raportu](course-materials/exercises/map-qa-decisions/README.md). PRD, ADR, plan, pipeline z testami i model decyzyjny na [danych OSM, Overture i zdjęciach Krakowa](course-materials/exercise-data/map-qa/README.md).
- **Rekomendowane ćwiczenie na danych publicznych:** [ładowarki EV + decyzje Jev + opcjonalny trening Modal](course-materials/exercises/ev-chargers-jev/). Prowadzisz agentów od pobrania danych do ewaluacji i dashboardu.
- **Projekty na danych publicznych:** [cztery pomysły i pełne prompty PRD](course-materials/Prompt%20examples/PRD-ideas-overview.md), [skrypty pobierania realnych danych GIS](course-materials/exercise-data/real/).
- **Syntetyczne dane GIS z celowo wprowadzonymi błędami:** [POI, drogi i dzielnice](course-materials/exercise-data/gis/).
- **Prompty i planowanie:** [PRD](course-materials/Prompt%20examples/PRD-electronics-returns-complains-app.md), [ADR](course-materials/Prompt%20examples/ADR-generation-typescript-vercel-ai-sdk.md), [plan implementacji](course-materials/Prompt%20examples/Plan-SubAgents-matrix-dependency-map.md), [propozycja skilla planowania](https://github.com/EdukeyTeam/agent-toolbox/pull/28) (otwarty PR).
- **Konfiguracje agentów:** [ustawienia, uprawnienia, profile i skróty Bash/PowerShell](course-materials/agent-configs/).
- **Hooki i zgody:** [ochrona plików i przykłady hooków](course-materials/hooks-example/), [Context7](course-materials/hooks-example/context7/), [permissions a hooki](course-materials/hooks-example/context7/permissions-vs-hooks.md).
- **CI/CD i code review:** [przegląd przykładów](course-materials/cicd-headless/), [agent review dla różnych CI](course-materials/cicd-headless/agent-review/), [PR-Agent i Qodo](course-materials/cicd-headless/PR-Agent-Qodo/), [Codex i Bitbucket](course-materials/cicd-headless/codex-bitbucket/).
- **Ćwiczenia i dalsza lektura:** [dane syntetyczne](course-materials/exercise-data/), [workflow agentów i oszczędzanie tokenów](course-materials/Research/agent-workflows-and-token-budget-2026-10-24.md).

**Materiały szkoleniowe: [devpowers.com/szkolenia/jsystems/tomtom-ai-2026-11](https://devpowers.com/szkolenia/jsystems/tomtom-ai-2026-11/)**

- [Zakres i wszystkie materiały](https://devpowers.com/szkolenia/jsystems/tomtom-ai-2026-11/index.html#prezentacje)
- [Slajdy](https://devpowers.com/szkolenia/jsystems/tomtom-ai-2026-11/index.html#prezentacje)
- [Biblioteka promptów](https://devpowers.com/szkolenia/jsystems/tomtom-ai-2026-11/prompty.html) · [Ćwiczenia](https://devpowers.com/szkolenia/jsystems/tomtom-ai-2026-11/cwiczenia.html) · [Checklisty](https://devpowers.com/szkolenia/jsystems/tomtom-ai-2026-11/checklisty.html) · [Słownik AI](https://devpowers.com/szkolenia/jsystems/tomtom-ai-2026-11/slownik-ai.html)
- [Wyniki ankiety przed szkoleniem](https://devpowers.com/szkolenia/jsystems/tomtom-ai-2026-11/raport-przed.html) · [Odpowiedzi na pytania z kursu](https://devpowers.com/szkolenia/jsystems/tomtom-ai-2026-11/pytania.html) (uzupełniamy po każdym dniu)


Repozytorium uczestnika szkolenia JSystems (2-3.11 i 12-13.11.2026, online, 09:00-16:00). W czasie szkolenia (4 dni w dwóch blokach po 2 dni) uczymy się pracy z agentami AI na zadaniach z danymi przestrzennymi: od rozpoznania danych, przez trwałe zasady pracy agenta, plan i powtarzalny pipeline z testami, po podział pracy między modele i agentów, code review w GitHub, łączenie agentów z usługami przez API i MCP.

Pracujemy w terminalu z dwoma agentami: **Claude Code** i **OpenAI Codex CLI**, na kontach szkoleniowych i maszynach wirtualnych. Claude Code pełni rolę agenta prowadzącego i recenzenta, Codex wykonuje zlecone zadania; porównujemy też, kiedy wystarczy tańszy model. Ćwiczenia piszemy w **Pythonie** (uv, pandas, GeoPandas, Shapely, DuckDB z rozszerzeniem spatial, pytest). Kod generują agenci, a Ty prowadzisz proces i sprawdzasz wyniki.

Głównym projektem jest **pipeline kontroli jakości danych mapowych**: syntetyczne punkty POI, odcinki dróg i dzielnice z typowymi błędami. Dane wejściowe i opis ćwiczeń są w [`course-materials/exercise-data/gis/`](course-materials/exercise-data/gis/); kod pipeline'u powstaje w `app/` podczas zajęć. Dane projektu bazowego są syntetyczne; opcjonalne ćwiczenia poniżej korzystają z jawnie wskazanych danych publicznych. Nie używamy danych ani środowisk firmowych.

## Stan początkowy i pierwsze uruchomienie

To celowo nierozwiązany starter: aplikacja i jej zestaw testów powstaną podczas ćwiczeń. Nie ma jeszcze jednej komendy testów aplikacji do uruchomienia. Na start poproś agenta o przeczytanie `AGENTS.md`, tego README i opisu danych GIS, wskazanie dostępnych plików oraz oddzielenie ustalonych zasad od brakujących decyzji. Nie dopisuj testów ani reguł CRS na podstawie domysłów.

Do zwykłej pracy w Claude Code i Codexie wystarczą konta szkoleniowe. Klucz API OpenRouter i dodatkowe serwery MCP nie są wymagane na start. `.mcp.json` jest pusty; `.mcp.example.json` zachowuje przykłady integracji dla Windows do jawnego skonfigurowania w ćwiczeniu MCP. Logowanie OAuth Context7 jest opisane w [oficjalnej instrukcji](https://context7.com/docs/clients/claude-code). Nie kopiuj całej konfiguracji bez sprawdzenia jej narzędzi i uprawnień.

## Biblioteka dodatkowa

`course-materials/` zawiera szeroką bibliotekę pełnych promptów, danych syntetycznych, checklist, przykładów konfiguracji i materiałów o innych agentach. To zasób do późniejszego czytania, nie lista narzędzi wymaganych na warsztacie. [Pełne prompty historyczne](course-materials/Prompt%20examples/) zachowano bez skracania; starsze twierdzenia o produktach, licencjach i komendach wymagają ponownego sprawdzenia. Podczas pracy z wybraną aplikacją agent nie powinien sam przeszukiwać `course-materials/`: zawarte tam PRD, ADR i instrukcje są przykładami, a nie wymaganiami tego projektu. Otwórz konkretny materiał dopiero wtedy, gdy go o to poprosisz.

W bibliotece znajdują się również **archiwalne materiały z wcześniejszego kursu o Claude Code**: [notatki](course-materials/Course%20INDEX%20-%20AI%20in%20Programming.md), [quiz](course-materials/quizzes/day-1-anonymous-ai-basics-quiz.md), [przykłady konfiguracji](course-materials/agent-configs/claude/) i [słownik PDF](course-materials/AI%20dla%20Programist%C3%B3w%20-%20S%C5%82ownik%20przed%20szkoleniem.pdf). Zachowano je jako źródła do ponownego wykorzystania, **nie jako aktualną konfigurację tego warsztatu**. Przykłady ustawień i skrypty należy dostosować i sprawdzić przed użyciem. `course-materials/exercise-data/hidden-patterns.md` jest archiwalnym kluczem trenerskim do danych syntetycznych.


Przykłady z biblioteki są opcjonalne i nie instalują się globalnie. Po zaufaniu repozytorium agenty mogą wczytać jego konfigurację projektową, więc przeczytaj ją przed pracą. Przykładowe [hooki do zależności Maven](course-materials/hooks-example/maven-agent-hooks.example.json) pozostają nieaktywne w starterze GIS; własny hook ochrony danych zbudujesz w ćwiczeniu. Przed użyciem przykładu sprawdź jego instrukcję, wersję narzędzia i politykę organizacji.

## Granice

Używaj danych syntetycznych lub publicznych źródeł wskazanych w wybranym ćwiczeniu, z zachowaniem ich licencji. Przed przekazaniem kontekstu agentowi sprawdź politykę organizacji i zakres dostępu. Przejrzyj każdy diff, wynik testów i uprawnienia proponowanych narzędzi. Testów nie zmieniaj po to, by ukryć nieukończone zachowanie.

Możliwość użycia agenta chmurowego, MCP, CLI i pul AI Credits zależy od planu oraz ustawień organizacji. Agent w IDE i agent chmurowy to osobne środowiska. Funkcje edytora mogą się różnić od CLI i od innych IDE. [Stan narzędzi i źródła](docs/tool-facts.md) wymagają ponownego sprawdzenia przed zajęciami.

Trener: Łukasz Matuszewski · [LinkedIn](https://www.linkedin.com/in/lukaszmatuszewski/) · [X](https://x.com/mrLumatic)
