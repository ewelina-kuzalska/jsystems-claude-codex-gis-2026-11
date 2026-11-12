# Podsumowanie - dzień 2, 3 listopada 2026

Źródła: podsumowania spotkania Zoom oraz [historia czatu](day-2-chat-history.md). Godziny w czasie polskim.

## Przegląd

Drugi dzień kursu poświęcono praktycznej pracy z Claude Code i Codex w środowiskach Windows. Grupa konfigurowała środowisko pracy i uprawnienia, sprawdzała sandbox MXC, pracowała z repozytorium projektu GIS oraz omawiała budowę aplikacji do analizy zdjęć ulicznych i danych mapowych. Ważnymi tematami były bezpieczeństwo, Git Worktree, integracja MCP z Context7, użycie GitHub CLI i dobór modeli do kolejnych etapów pracy.

## Organizacja

Prowadzący: Łukasz Matuszewski. Ćwiczenia odbywały się na wirtualnych maszynach Windows z użytkownikiem `labuser`. Konfiguracje agentów znajdowały się na Dev Drive w `D:\AI\labuser`, a repozytorium robocze w `D:\jsystems-claude-codex-gis-2026-11`.

Konta szkoleniowe pozostają dostępne do około 29-30 listopada 2026 r. Do ChatGPT logujemy się prywatnym adresem e-mail, a do Claude Code adresem w domenie devpowers.com przesłanym przez trenera.

Materiały kursowe: [strona szkolenia](https://devpowers.com/szkolenia/jsystems/tomtom-ai-2026-11/index.html) i [repozytorium](https://github.com/LucasMatuszewski/jsystems-claude-codex-gis-2026-11).

## Temat 1: Dostęp, konfiguracja środowiska i sandbox Windows

Na początku wrócono do logowania przez CLI na zdalnych komputerach. Pokazano `codex login --device-auth` oraz stronę [uwierzytelniania urządzenia Codex](https://auth.openai.com/codex/device). W ćwiczeniu używano Codex 0.166.0. Dzień obejmował również ustawienie katalogów konfiguracji przez zmienne `CLAUDE_CONFIG_DIR` i `CODEX_HOME`, tak aby pliki agentów znajdowały się na Dev Drive (np. `D:\AI\labuser\.codex`). Informacje o Dev Drive: [dokumentacja Microsoft](https://learn.microsoft.com/en-us/windows/dev-drive/).

Sprawdzono sandbox MXC poleceniem `codex -c windows.sandbox=mxc sandbox --include-managed-config --permission-profile :workspace -- cmd.exe /d /c echo MXC_OK`. Test zwrócił `MXC_OK` i kod zakończenia `0`. Omówiono ustawienie `prefer_mxc = true` z powrotem do zwykłego sandboxa oraz wariant wymuszający wyłącznie MXC: sekcja `[windows]` z ustawieniem `sandbox = "mxc"`.

### Q&A

- **Czy sandbox MXC jest domyślnie włączony i czy wymaga uprawnień administratora?** Nie jest włączony automatycznie. Jego dostępność zależy od obsługiwanej konfiguracji Windows i uprawnień. Na maszynie wirtualnej wykonano testową komendę, która zakończyła się powodzeniem.
- **Jak przejść do poprzednich sesji lub sprawdzić stan pracy?** Pokazano `/status` i `/resume`.

## Temat 2: Bezpieczeństwo i uprawnienia agentów

Omówiono ryzyko przyznawania agentom zbyt szerokiego dostępu do plików i systemu, w tym do sekretów oraz poczty. Przy pracy w repozytorium pokazano ograniczenia blokujące pliki `.env` i katalogi `secrets`, przy pozostawieniu `.env.example` w trybie tylko do odczytu. Poruszono także ryzyko prompt injection oraz potrzebę sprawdzania zmian wykonywanych przez agentów.

Tryb `Approve for me` pozwala ograniczyć liczbę ręcznych potwierdzeń, ale wymaga ostrożności, szczególnie w środowisku z dostępem do lokalnych plików. Zalecono ograniczanie uprawnień tokenów i tworzenie kopii zapasowych przed dłuższymi zadaniami. Wspomniano [Restic](https://restic.net/) jako narzędzie do backupów.

W rozmowie przywołano [materiał OpenAI o incydencie związanym z Hugging Face](https://openai.com/pl-PL/index/hugging-face-incident-and-the-road-ahead/) oraz [materiał wideo na Netflix](https://www.netflix.com/watch/82772145?trackId=-1&tctx=-97%2C3%2C%2C%2C%2C%2C%2C%2C82772142%2CVideo%3A82772145%2CdetailsPageCollection%2C). Dyskusja o świadomości agentów nie doprowadziła do rozstrzygnięcia; praktyczny wniosek był taki, by zakładać możliwość błędów i nieoczekiwanych działań.

### Q&A

- **Czy agenci AI działają świadomie?** Nie przedstawiono pewnego rozstrzygnięcia. Z punktu widzenia praktycznej pracy należy projektować procesy tak, by ograniczać skutki błędów i weryfikować wyniki.

## Temat 3: Codzienna praca w CLI, sesje i Git Worktree

Przećwiczono pracę w repozytorium, zmianę katalogu roboczego poleceniem `/cd`, dodanie katalogu przez `/add-dir` oraz rozpoczynanie nowej sesji przez `/new` (w Claude Code `/clear`, z aliasem `/new`). `Ctrl+C` kończy pracę z Codex. Polecenie `!` pozwala przejść do trybu powłoki. Omówiono skróty Codex: dwukrotne `Esc` otwiera tryb transkrypcji, `Ctrl+T` pokazuje szczegóły wiadomości i wywołań funkcji, a `Ctrl+O` kopiuje ostatnią wiadomość agenta.

Omówiono Git Worktree jako sposób na pracę nad zadaniami w oddzielnych katalogach roboczych i ograniczanie konfliktów między równoległymi zmianami. Pokazano też fork jako wariant pracy z repozytorium, do którego nie ma się bezpośredniego dostępu. Dokumentacja: [git-worktree](https://git-scm.com/docs/git-worktree).

Wspomniano narzędzia ułatwiające pracę: [Atuin](https://atuin.sh/) do historii poleceń w PowerShell i Bash, [Handy](https://handy.computer/) do lokalnego dyktowania poleceń i promptów, a także `lazygit` i `delta` do obsługi Git i czytelniejszego przeglądania różnic. Do zrzutów ekranu wskazano [Flameshot](https://flameshot.org/).

### Q&A

- **Czy Git Worktree można utworzyć w trakcie sesji?** Tak. Można go przygotować w dowolnym momencie, również polecając agentowi wykonanie odpowiednich operacji Git.

## Temat 4: Projekt GIS, PRD i podejmowanie decyzji

Praktyczne ćwiczenie dotyczyło aplikacji do analizy danych mapowych i zdjęć ulicznych, w tym zdjęć znaków drogowych, skrzyżowań i ulic. Pracę nad wymaganiami oparto na PRD, które prowadzi agenta przez pytania o odbiorców, problem, źródła danych, technologię i potrzebne funkcje. Przykładowy prompt: [PRD do analizy zdjęć ulicznych](https://github.com/LucasMatuszewski/jsystems-claude-codex-gis-2026-11/blob/main/course-materials/Prompt%20examples/PRD-map-qa-street-photos.md).

Dla MVP zalecono rozpoczęcie od prostszego przepływu, z pominięciem interfejsu użytkownika na tym etapie. Źródło danych powinno dać się wskazać przez zmienną lub plik konfiguracyjny; omówiono możliwość późniejszego pobierania danych z różnych źródeł. Przy niepewnym wyniku model decyzyjny może przekazać zadanie zwykłemu modelowi językowemu, a jeśli nadal brakuje pewności, skierować je do człowieka i kolejki ręcznej weryfikacji.

Omówiono dobór modeli do kosztu i rodzaju zadania. W czacie podano nazwę GPT 6 Luna, a w materiałach planowania - warianty dla Codex Luna i Claude Haiku: [prompt planu dla Codex Luna](https://github.com/LucasMatuszewski/jsystems-claude-codex-gis-2026-11/blob/main/course-materials/Prompt%20examples/Plan-SubAgents-matrix-dependency-map-LUNA.md) oraz [prompt planu dla Claude Haiku](https://github.com/LucasMatuszewski/jsystems-claude-codex-gis-2026-11/blob/main/course-materials/Prompt%20examples/Plan-SubAgents-matrix-dependency-map.md). Plan zapisany w pliku można zrealizować poleceniem `/goal`, np. `/goal zrealizuj plan z pliku @plik-z-planem.md`. Pokazano również przykład promptu do ADR: [ADR dla projektu Python GIS](https://github.com/LucasMatuszewski/jsystems-claude-codex-gis-2026-11/blob/main/course-materials/Prompt%20examples/ADR-generation-python-gis-map-qa.md).

### Q&A

- **Czy model wskazany do analizy zdjęć obsługuje obrazy?** GPT 6 Luna został wskazany jako model do sprawdzenia w zadaniu z obrazami. Jego przydatność należy ocenić na danych ćwiczenia.
- **Jak postępować, gdy decyzja modelu jest niepewna?** Najpierw można przekazać zadanie zwykłemu modelowi językowemu, a następnie skierować nierozstrzygnięty przypadek do człowieka.

## Temat 5: MCP, Context7 i dokumentacja

Omówiono MCP jako Model Context Protocol - standard dostarczania narzędzi agentom. W przykładach użyto Context7 do wyszukiwania dokumentacji i kodu: [Context7](https://context7.com/), [strona dokumentacji TypeSafe w Context7](https://context7.com/websites/typesafe_ai) oraz [wprowadzenie do MCP](https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro).

Pokazano konfigurację Context7 w plikach Codex `D:\AI\labuser\.codex\config.toml` i Claude Code `D:\AI\labuser\.claude\.claude.json`, a także polecenie `npx ctx7 setup`. Adres serwera MCP to `https://mcp.context7.com/mcp`. Zademonstrowano `/mcp` do listowania i zarządzania serwerami. W instrukcjach projektu `AGENTS.md` zalecono najpierw korzystać z Context7, następnie szukać w internecie, jeśli dokumentacja nie wystarczy; dla CLI pierwszym krokiem powinno być `--help`.

### Q&A

- **Jak aktywować skill w Codex lub Claude Code?** Lista dostępnych skills nie wymaga osobnej aktywacji: `$` w Codex i `/` w Claude Code pozwalają wybrać narzędzie i dodać je do kontekstu sesji.
- **Jak ograniczyć zbędne pobieranie dokumentacji?** Korzystać z wyszukiwania dokumentacji przez Context7 i pobierać fragmenty odnoszące się do konkretnego pytania.

## Temat 6: GitHub CLI i uprawnienia do repozytorium

Pokazano uwierzytelnianie przez `gh auth login` i użycie [GitHub CLI](https://cli.github.com/) do pracy z repozytorium. Omówiono tokeny o ograniczonych uprawnieniach; jako zakresy wymagane w przedstawionym przykładzie podano `repo`, `read:org` i `workflow`. W konfiguracji tokena wskazano m.in. odczyt metadanych, zapis zawartości i pull requestów oraz uprawnienia tylko do odczytu dla Actions. Uprawnienia administracyjne mogą pozwalać na tworzenie i usuwanie repozytoriów, dlatego należy przyznawać je wyłącznie wtedy, gdy są potrzebne. Ustawienia tokenów: [personal access tokens](https://github.com/settings/personal-access-tokens) i [tworzenie tokena](https://github.com/settings/personal-access-tokens/new).

### Q&A

- **Jak uwierzytelnić GitHub CLI?** W ćwiczeniu wybrano logowanie tokenem i protokół HTTPS. Token powinien mieć tylko uprawnienia potrzebne do danego repozytorium i zadania.

## Temat 7: Dodatkowe skills i optymalizacja pracy

Omówiono Caveman i Ponytail jako narzędzia wpływające na sposób pracy agentów i oszczędzanie tokenów. Warto sprawdzić je na własnych zadaniach przed przyjęciem jako stałej praktyki: [Caveman](https://github.com/JuliusBrussee/caveman/tree/main), [skill Caveman](https://github.com/JuliusBrussee/caveman/blob/main/skills/caveman/SKILL.md), [Ponytail](https://github.com/DietrichGebert/ponytail/tree/main), [skill Ponytail](https://github.com/DietrichGebert/ponytail/blob/main/skills/ponytail/SKILL.md) i [Ponytail w skills.sh](https://www.skills.sh/dietrichgebert/ponytail/ponytail). Instalacja Ponytail: `npx skills add https://github.com/dietrichgebert/ponytail --skill ponytail`. Pokazano również `/write-adr` jako punkt wyjścia do pracy nad ADR.

## Plan na kolejne dni

Następne spotkania zaplanowano na 12-13 listopada 2026 r. Ma być kontynuowana praca nad aplikacją GIS, danymi geograficznymi i planowaniem z subagentami.

## Kolejne kroki

### Trener

- Wrócić do nierozwiązanych problemów z aktywacją lub autoryzacją urządzenia, jeśli nadal występują.
- Udostępnić grupie przykładową konfigurację MCP oraz materiały i prompty do ćwiczeń.

### Uczestnicy

- Kontynuować budowę aplikacji GIS na podstawie PRD i danych z repozytorium.
- Przećwiczyć własne repozytorium lub fork oraz uwierzytelnianie GitHub CLI z ograniczonymi uprawnieniami.
- Sprawdzić Context7 w projekcie oraz przetestować Caveman i Ponytail na konkretnych zadaniach.
- Przejrzeć materiały kursowe przed kolejnym spotkaniem.

### Wszyscy

- Zebrać pytania do dalszej pracy nad aplikacją i omówić je przed spotkaniami 12-13 listopada.
