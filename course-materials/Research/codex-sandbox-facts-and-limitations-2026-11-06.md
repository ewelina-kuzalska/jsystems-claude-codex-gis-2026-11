# Codex: sandbox Windows, regresje i pytania interaktywne

Stan: 6.11.2026, sprawdzane źródła i CLI 0.166.0. Problemy z uruchomieniem narzędzi oraz znikającymi pytaniami mają publiczne zgłoszenia i potrafią przerwać pracę mimo poprawnej intencji użytkownika. Nie każdy błąd jest błędem konfiguracji. Rozdzielamy jednak zgłoszenia użytkowników, poprawki w kodzie i wynik konkretnego testu.

## Działająca procedura kursowa

Pomiary z 5-6.11.2026 potwierdziły działanie zwykłej sesji z daemonem przy ustawieniach: Windows `elevated`, `prefer_mxc = false`, profil `course-tools`, `on-request` i `auto_review`. Context7, odczyt `gh repo view` i cykl Playwright działały. Po zmianie ustawień trzeba było **zrestartować daemon i rozpocząć nową sesję**, zamiast wznawiać poprzednią.

W zwykłym PowerShellu, po zakończeniu aktywnych zadań, z tym samym `CODEX_HOME`, którego używa klient:

```powershell
$env:Path = "$env:APPDATA\npm;$env:Path"
```

```powershell
codex app-server daemon restart
```

```powershell
codex app-server daemon version
```

```powershell
codex
```

Rozpocznij nową rozmowę i sprawdź `/permissions`, `/status`, `/mcp`, a następnie odczyt gh i własną sesję Playwright. Zamknięcie samego TUI nie dowodzi restartu serwera. Restart może przerwać inne zadania tego użytkownika. Jest to sprawdzona procedura tego kursu, nie twierdzenie, że żadnych ustawień nigdy nie można zmienić we wznowionej rozmowie. [Źródło: cykl życia daemona](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/app-server-daemon/README.md).

Pełna konfiguracja i granice uprawnień: [instrukcja Windows](../agent-configs/codex/WINDOWS-QUICKSTART-PL.md). `course-tools` zachowuje sandbox dla zwykłych poleceń, ale nie dodaje blokad odczytu .env/secrets, a wybrane prefiksy gh/Playwright dopuszczają wykonanie na hoście. Nie jest to dowód, że GitHub lub Chrome działają wewnątrz sandboxa. Nie umieszczaj sekretów w workspace kursowym. Reguły prefiksowe nie ograniczają wszystkich opcji, ścieżek i profili przeglądarki.

## Różne awarie, różne diagnozy

ACL (Access Control List) to lista uprawnień pliku lub katalogu Windows; wpisy ACE opisują prawa użytkowników/grup. Starszy backend elevated przygotowuje ograniczone konta i ACL. Podniesienie uprawnień przy instalacji nie oznacza, że wszystkie komendy agenta działają jako administrator. MXC jest innym mechanizmem; nie należy diagnozować każdego jego błędu jako uszkodzenia ACL. [Dokumentacja Windows](https://learn.chatgpt.com/docs/windows/windows-sandbox).

| Objaw | Co wiadomo i co sprawdzić |
|---|---|
| `parse deny-read ACL state` / `expected value at line 1 column 1` | Zgłoszono plik `deny_read_acl_state.json` wypełniony NUL po awarii. Najpierw potwierdź ten konkretny błąd i zrób kopię stanu; nie kasuj całego CODEX_HOME. Odtworzenie uszkodzonego pliku nie naprawia każdego problemu sandboxa. [#34841](https://github.com/openai/codex/issues/34841), [#35718](https://github.com/openai/codex/issues/35718). |
| `os error 32` przy `node_repl.exe` lub DLL | Udokumentowano konflikt otwartego pliku z operacją ACL. PR #51822 scalono 7.10: zwykłe pliki nie są już otwierane przez `MAXIMUM_ALLOWED`; `WRITE_DAC` jest żądane, gdy trzeba zmienić ACL. Sprawdź wersję i dokładny błąd. Build `26.1007.21434` ma zgłoszenia poprawy, lecz nie ustalono tu pierwszej wydanej wersji zawierającej fix. [#51601](https://github.com/openai/codex/issues/51601), [poprawka #51822](https://github.com/openai/codex/pull/51822). |
| MXC: okresowe błędy `apply_patch` lub `blocked by policy` | #56999 dokumentuje problem edycji. Późniejszy komentarz opisuje odmowę uruchomienia przeglądarki także w Full Access, ale nie identyfikuje warstwy blokującej. To dowody zgłoszonych problemów, nie dowód, że każdy MXC ignoruje wszystkie reguły. [#56999](https://github.com/openai/codex/issues/56999). |
| `helper_unknown_error: setup refresh had errors` | To komunikat zbiorczy. Potrzebny jest błąd wewnętrzny; sama etykieta nie rozstrzyga, czy chodzi o JSON, blokadę pliku, provisioning czy politykę. #52545 nie potwierdza wspólnej przyczyny z `os error 32`. [#52545](https://github.com/openai/codex/issues/52545). |

`unelevated` nie zapewnia tych samych blokad deny-read; nie jest równoważnym zamiennikiem profilu ścisłego. Nie zaczynaj od wyłączania sandboxa ani zgód. Zachowaj działający, przetestowany backend; WSL2 lub osobna VM to alternatywne środowiska wymagające własnej weryfikacji, a nie automatyczne lekarstwo. Nie zmieniaj ACL rekursywnie i nie kasuj stanu na podstawie samego ogólnego komunikatu.

## Dlaczego pytanie może zniknąć

W CLI 0.166.0 synchroniczne `request_user_input` jest blokujące w Plan Mode. Poza nim dostępność zależy od klienta i flag funkcji, a nieblokujące pytanie ma timer: w sprawdzonym kodzie TUI **60 s niewidocznego czasu + 60 s widocznego odliczania**, nie uniwersalne 10-15 s. Schemat narzędzia zawiera pytania; model nie ma parametru ustawiającego timeout ani `is_blocking`. Polecenie "czekaj" nie zmienia implementacji klienta. [Zgłoszenie #37472](https://github.com/openai/codex/issues/37472), [handler](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/core/src/tools/handlers/request_user_input.rs), [timer TUI](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/tui/src/bottom_pane/request_user_input/mod.rs).

Dla wymaganej decyzji użyj Plan Mode. Gdy formularz jest niedostępny, agent powinien zadać trwałe pytania tekstowe i poczekać. Pusty wynik `answers` ani upływ czasu nie oznacza odpowiedzi lub zgody. Nie mieszaj synchronicznego narzędzia z osobnymi pytaniami async, których karta może mieć inny cykl życia. Publiczne zgłoszenia potwierdzają problem UX; nie dowodzą, że każdy kolejny token zawsze usuwa kartę. Nie instaluj nieudokumentowanej flagi `default_mode_is_blocking` i nie łataj ASAR jako instrukcji kursowej.

## Jak oceniać krytyczne raporty

Regresje klienta, provisioning, niejasne komunikaty i obsługa pytań mogą realnie zablokować sensowny workflow. Krytyka tych zachowań jest uzasadniona. Zgłoszenie, wersja, reprodukcja i poprawka są jednak mocniejszym dowodem niż przypuszczenie o przyczynach organizacyjnych.

Zmiany partnerstw lub połączenie aplikacji nie dowodzą, że spowodowały konkretną awarię albo pogorszenie modelu. Ten materiał nie potwierdza związku z rotacją zarządu, kwantyzacją czy awaryjnym zaostrzaniem guardrails ani twierdzenia, że inne narzędzie wymaga zawsze 40% mniej tur. Jakość modeli i porównania dostawców oceniaj na tych samych zadaniach, ustawieniach, kosztach i datach; nie wyprowadzaj ich z logu błędu sandboxa.
