# Wznowienie konkretnej sesji Codex po resecie limitu

Badanie: 2026-11-05, lokalny `codex-cli 0.166.0`. Żadna rzeczywista sesja nie została wznowiona, żaden kredyt/reset nie został wykorzystany, nie utworzono harmonogramu ani usługi.

## Decyzja

**Dla istniejącej sesji obsługiwanej przez lokalny daemon najlepszym dostępnym poleceniem jest `codex queue --thread UUID --message TEKST --resume`, uruchomione raz o podanej godzinie resetu + 10 minut.** Korzysta z modelu wątku. Nie uruchamia drugiej kopii przez `exec resume`. Nie jest potwierdzeniem rozpoczęcia ani zakończenia pracy.

**Dla samego CLI nie znaleziono udokumentowanego polecenia "czekaj do naturalnego resetu i sam wznów ten UUID".** Zewnętrzny jednorazowy timer może wywołać natywne `queue`. Dołączony `resume_once.py` jest takim timerem: domyślnie tylko pokazuje plan, działanie wymaga `--run`.

**Nierozwiązana część automatyzacji:** timer queue może wysłać jedną kontynuację, ale nie przywraca trwałego celu ze stanu `usage_limited` do `active`. Istnieje natywne API app-server, które to umożliwia, opisane niżej. Nie przygotowano ani nie przetestowano klienta tego API. Nie należy sprzedawać obecnego helpera jako pełnego automatycznego powrotu do `/goal`.

**Uwaga przed użyciem helpera:** kod dziedziczy całe środowisko procesu. W badaniu wykazano ryzyko konfiguracji innego executora/stanu. Helper nie jest zatwierdzony do bezobsługowego uruchomienia w dowolnym środowisku bez opisanej poniżej walidacji. Zachowano go bez zmian na prośbę koordynatora; poprawka należy do właściciela końcowego artefaktu.

## Zweryfikowane natywne możliwości

| Mechanizm | Co robi | Istotne ograniczenie |
|---|---|---|
| `codex queue --thread UUID --message "..." --resume` | Kolejkuje wiadomość do istniejącego wątku; w razie potrzeby próbuje go załadować na lokalnym daemonie | Wymaga daemona lub wskazanego zdalnego serwera. Samo exit 0 nie dowodzi wznowienia: CLI może ostrzec o nieudanym resume i mimo to zwrócić 0 |
| `codex resume UUID` | Otwiera poprzedni wątek w interaktywnym TUI | Wymaga terminala; nie jest harmonogramem |
| `codex exec -C /abs/project -m MODEL -s SANDBOX resume UUID "..."` | Uruchamia kontynuację bez TUI z zachowaniem UUID i historii | Ponownie ładuje konfigurację i przekazuje do resume model/provider/cwd/uprawnienia z tej konfiguracji. Nie zakładać identycznych ustawień poprzedniej sesji |
| `/goal` | Trwały cel przypisany do wątku | Cel nie jest timerem resetu. Po `UsageLimitExceeded` implementacja ustawia stan `usage_limited` |
| Scheduled tasks w aplikacji/webie | Mogą zaplanować kontynuację w istniejącym czacie albo osobny run | CLI nie ma interfejsu Scheduled. Nie potwierdzono, że dowolny lokalny UUID CLI da się wybrać z weba/aplikacji |

Dokumentacja OpenAI potwierdza semantykę queue i jego ostrzeżenie oraz rozróżnienie CLI/exec/TUI: [Developer commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli).

Dokumentacja aplikacji opisuje zaplanowane zadania w istniejącym czacie. Zadania lokalne wymagają włączonego komputera i działającej aplikacji. Web nie utrzymuje lokalnego folderu. To osobna powierzchnia produktu; dostępność trzeba sprawdzić w używanej aplikacji: [Scheduled tasks](https://learn.chatgpt.com/docs/automations?surface=app).

## Ważne ustalenia z kodu dokładnej wersji 0.166.0

1. `queue` wysyła `thread/queue/add`; przy `--resume` sprawdza status bez pobierania treści rozmowy. Jeżeli wątek nie jest załadowany, wysyła `thread/resume` z samym UUID i `exclude_turns: true`. Nie nadpisuje modelu/cwd/uprawnień wątku. `--model` i `-c model=...` są odrzucane. Źródła: [queue_cmd.rs](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/cli/src/queue_cmd.rs), [session_queue_commands.rs](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/tui/src/session_queue_commands.rs).
2. `exec resume` przekazuje konfigurację wywołania do `ThreadResumeParams`. Headless domyślnie nie pyta człowieka o eskalację (`approval_policy=never`); sandbox nadal obowiązuje. Nie należy utożsamiać tego z pełnym zachowaniem interaktywnej polityki zgód ani z obejściem sandboxa. Źródło: [exec/src/lib.rs](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/exec/src/lib.rs), funkcje `thread_resume_params_from_config`, `build_exec_config` i ustawienie `ConfigOverrides`.
3. Terminalny `UsageLimitExceeded` zatrzymuje aktywny cel jako `usage_limited`. Przy ponownym załadowaniu runtime przywraca automatyczną kontynuację wyłącznie celu `active`. TUI oferuje wznowienie celu także dla `paused`, `blocked`, `usage_limited`. Samo ponowne otwarcie wątku ani wysłanie tekstu `/goal resume` przez queue nie jest dowodem wykonania komendy TUI. Źródła: [goal runtime](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/ext/goal/src/runtime.rs), [goal extension](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/ext/goal/src/extension.rs), [TUI goal actions](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/tui/src/app/thread_goal_actions.rs).

Ogólny opis trwałości celu i bezpiecznych granic kontynuacji: [Using Goals in Codex](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex). Dla stanu celu po limicie rozstrzygające było źródło 0.166.0 powyżej, nie ogólna obietnica "Goals persist".

## Tożsamość i ustawienia

- UUID musi pochodzić z właściwej sesji, np. z polecenia wznowienia wyświetlanego przy wyjściu z TUI. Nie używać `--last`, nazw mogących się powtarzać ani wyszukiwania całych transkryptów.
- `CODEX_HOME` jest ścieżką do istniejącego katalogu konfiguracji/stanu/autoryzacji, a nie adresem konta. Ta sama ścieżka nie gwarantuje, że ktoś w międzyczasie nie zmienił logowania. Przed odłożeniem pracy sprawdzić konto i model we właściwej sesji przez `/status`; nie czytać plików z tokenami.
- `queue -C /abs/project` określa kontekst uruchomienia lokalnego klienta. Faktyczny katalog istniejącego wątku pozostaje ustawieniem wątku. Wskazanie projektu nie przenosi kontekstu między maszynami ani Windows i WSL.
- Sesja wymagająca profilu `-p NAZWA` wymaga osobnej walidacji połączenia. Profil/kustomowy loader może wyłączyć współdzielenie lokalnego daemona; samo dopisanie `-p` nie gwarantuje dostarczenia do istniejącego właściciela. Helper celowo nie przyjmuje profili, zdalnych endpointów ani dowolnych nadpisań: korzystać z niego tylko dla zweryfikowanego domyślnego lokalnego daemona w podanym `CODEX_HOME`.
- Jeśli potrzebny jest headless `exec resume`, jawnie dobrać wcześniejszy model/provider/profil i ten sam lub węższy sandbox. Nie kopiować `--approve-for-me`, `danger-full-access`, `--ignore-rules` lub bypassów w celu "naprawienia" bezobsługowości.
- Nie uruchamiać dwóch niezależnych `exec resume` dla tego samego aktywnego wątku. Queue komunikuje się z istniejącym właścicielem.

## Limit pięciogodzinny i czas

Nie liczyć automatycznie `teraz + 5 h`: użyć rzeczywistej godziny resetu pokazanej dla konta i konkretnego limitu, potem dodać 10 minut. Reset okna krótkiego nie usuwa limitu tygodniowego ani innych blokad. Aktualna strona cenowa różnicuje limity według planu i odsyła do `/status`/dashboardu; nie należy obiecywać każdemu kontu resetu co pięć godzin: [Pricing / usage limits](https://learn.chatgpt.com/docs/pricing).

Przykład: reset `2026-11-06T05:50:00+00:00` -> pojedyncza próba `2026-11-06T06:00:00+00:00`. Reset o 06:00 -> próba o 06:10. Data i offset są obowiązkowe, więc "06:00" nie zależy od przypadkowej strefy systemu. Dla Polski w listopadzie offset wynosi `+01:00`; dla Lizbony `+00:00`. W dniu zmiany czasu brać offset właściwy dla daty uruchomienia.

## Istniejące narzędzia i skills

- Wbudowane `queue` jest obecnie lepiej dopasowane niż własne sterowanie TUI lub drugi headless proces.
- Zainstalowany `codexbar 0.30.0`: sprawdzono wyłącznie `--help`. Wystawia odczyt `usage` oraz wybór konta/provider/source, nie wystawia w help polecenia planowania lub wznowienia sesji. Nie odpytywano rzeczywistego konta ani cookie/tokenów.
- W katalogach zainstalowanych skills nie znaleziono dedykowanego skillu wznawiającego Codex po limicie. `agent-usage-analytics` ma odczyt quota przez uwierzytelniony CLI bez model turn; `respond-to-code-review` ma ograniczony watcher innego rodzaju. Żaden z tych opisów nie stanowi mechanizmu wznowienia konkretnej sesji o godzinie resetu. Przeszukano nazwy/teksty SKILL.md i nazwy plików; nie otwierano transkryptów.
- Context7: najpierw `library "OpenAI Codex"`, potem dwa odczyty docs `/openai/codex`. Wyniki wyjaśniły resume, lecz informacje o harmonogramie były zbyt ogólne; uzupełniono oficjalnymi stronami i źródłami wydania.

## Helper i walidacja

Instrukcja i skrypty: [scheduled-continuation](../agent-configs/codex/scheduled-continuation/README.md).

Helper przyjmuje dokładny UUID, absolutne istniejące ścieżki Codex/projektu/CODEX_HOME, reset z offsetem, bufor i nowy log. Domyślny dry-run nie śpi, nie zapisuje logu, nie wywołuje CLI. `--run` czeka w pierwszym planie i wykonuje jeden `queue --resume`; nie instaluje usługi. Log POSIX tworzy jako 0600 i nie nadpisuje istniejącego. W Windows należy użyć już prywatnego katalogu z właściwym ACL; nie deklarujemy, że tryb 0600 zastępuje ACL.

Domyślnie maksymalnie 12 h oczekiwania, 5 min dopuszczalnego spóźnienia po wybudzeniu, 120 s na samo wywołanie queue. Limit czekania obowiązuje także przy zatrzymaniu/cofnięciu zegara. Błąd/timeout nie wywołuje ponowienia. Timeout oznacza niepewny wynik dostarczenia: nie uruchamiać automatycznie ponownie. Wykrywane ostrzeżenie `could not resume thread` daje kod 3 pomimo exit 0 CLI. Kod 5 oznacza brak rozpoznanego potwierdzenia dla wskazanego UUID. Kod 0 helpera znaczy tylko rozpoznane potwierdzenie zakolejkowania i brak wykrytego ostrzeżenia, nigdy "agent skończył zadanie". Dalsza praca w daemonie ma własny czas życia i zgody; timeout helpera jej nie ogranicza.

Weryfikacja: `python3 -m unittest -v test_resume_once.py` - **14 testów OK**, w tym faktyczny subprocess syntetycznego CLI i wstrzykiwany zegar. Sprawdzono: dry-run, dokładny UUID/cwd/CODEX_HOME, bufor, niepoprawne daty/brak offsetu, brak ścieżki, zbyt odległy/przeszły termin, brak sesji zgłoszony przez stub, warning resume z exit 0, timeout bez retry, późne wybudzenie, zatrzymany zegar, prywatny i nienadpisywalny log, odrzucenie komendy slash. Helper celowo nie skanuje sesji: rzeczywistą nieistniejącą sesję odrzuca serwer podczas pojedynczej próby.

Potwierdzono parser rzeczywistego CLI tylko poleceniami zakończonymi `--help`, ze sztucznym UUID. **Nie sprawdzono live** wznowienia po wyczerpaniu quota, odblokowania celu `usage_limited`, przebiegu na Windows ani wybudzania sprzętu. Nie planowano żadnej rzeczywistej próby.

## Ograniczenia platform

Linux/WSL: timer i daemon muszą działać w tej samej dystrybucji/środowisku co sesja; terminal/proces timera musi pozostać aktywny, komputer nie może być wyłączony. Samo zablokowanie ekranu jest czym innym niż uśpienie. Nie obiecywać wybudzenia.

Windows: natywna sesja PowerShell wymaga natywnego Codex i jego Windows CODEX_HOME. Sesja z WSL wymaga uruchomienia timera we właściwym WSL, nie z windowsowym katalogiem `.codex`. Helper Python obsługuje ścieżki Windows, lecz nie uruchamiano go na Windows. Dla instalacji udostępniającej wyłącznie wrapper `codex.cmd` zweryfikować bezpieczne uruchomienie w PowerShell; nie zakładać, że jest natywnym `codex.exe`.

Jeżeli ktoś uważa, że `queue` automatycznie aktywuje cel `usage_limited` albo że scheduled tasks mogą bezpośrednio celować w każdy lokalny UUID CLI, potrzebny jest test na tej wersji lub konkretny kontrakt API. Obecne dowody tego nie potwierdzają.

## Uzupełnienie: natywne wznowienie celu bez TUI

**API istnieje: `thread/goal/set`.** W 0.166.0 metoda nie jest oznaczona experimental; repozytorium ma test `thread_goal_methods_are_not_marked_experimental`. Samo narzędzie `codex app-server` nadal ma w CLI etykietę experimental. To kontrakt dla klienta app-server, nie gotowe polecenie `codex goal resume`.

Minimalne żądanie JSON-RPC do już właściwie zainicjalizowanego połączenia z właścicielem sesji, **po wyraźnym upoważnieniu użytkownika do wznowienia tego celu**:

```json
{"id":2,"method":"thread/goal/set","params":{"threadId":"11111111-1111-4111-8111-111111111111","origin":"user","status":"active"}}
```

Pominięcie `objective` zachowuje cel, a pominięcie `tokenBudget` zachowuje budżet. Nie wysyłać `tokenBudget: null`, ponieważ oznacza zmianę budżetu, nie jego zachowanie. Jeśli cel nie istnieje, żądanie zmiany samego statusu jest odrzucane. Przekroczony budżet celu nadal ogranicza pracę; ustawienie statusu nie jest sposobem obejścia budżetu ani quota konta.

TUI `/goal resume` korzysta z `thread_goal_set` z `origin: User`. Procesor zapisuje intencję użytkownika, aktualizuje stan i stosuje efekty runtime. Dla załadowanego wątku przejście do `active` uruchamia `continue_if_idle()`; dla niezaładowanego potrzebne jest jeszcze poprawne `thread/resume` na tym samym serwerze. Klient powinien najpierw pobrać `thread/goal/get`, upewnić się, że to właściwy istniejący cel w stanie `usage_limited`/innym jawnie wskazanym, potem zmienić wyłącznie status i sprawdzić odpowiedź. Wysyłanie do serwera kilku linii bez obsługi handshake/odpowiedzi nie jest zweryfikowaną automatyzacją.

Kontrakty i implementacja:

- [ThreadGoalSetParams i ThreadGoalMutationOrigin](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/app-server-protocol/src/protocol/v2/thread.rs), linie 870-900: `threadId`, opcjonalne `origin`, `objective`, `status`, `tokenBudget`.
- [Metoda i test braku oznaczenia experimental](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/app-server-protocol/src/protocol/common.rs), `ThreadGoalSet` oraz `thread_goal_methods_are_not_marked_experimental`.
- [TUI wywołuje ten sam kontrakt](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/tui/src/app_server_session.rs), `thread_goal_set`.
- [Procesor zachowuje opuszczone pola i stosuje runtime](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/app-server/src/request_processors/thread_goal_processor.rs), `thread_goal_set_inner`.
- [GoalService zachowuje objective/budżet](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/ext/goal/src/api.rs), `set_thread_goal`; [runtime kontynuuje aktywny cel](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/ext/goal/src/runtime.rs), `apply_external_goal_set`.

Agent odbierający zwykłą wiadomość queue **nie ma narzędzia resume celu**: dostępne są `get_goal`, `create_goal`, `update_goal`. `update_goal` akceptuje tylko `complete`, `blocked`, `paused` i wprost zabrania wznowienia. `create_goal` odrzuca nowy cel, jeśli istniejący jest niedokończony. Wniosek: prośba "wznów cel" w wiadomości nie zastępuje natywnego wywołania API albo komendy użytkownika w TUI. Źródła: [goal spec](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/ext/goal/src/spec.rs), [goal tool](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/ext/goal/src/tool.rs).

`codex app-server proxy --help` potwierdza natywny transport stdio do już działającego lokalnego socketu, także przez `--sock`. Nie uruchamiano proxy i nie zbudowano klienta. Najlepsza zweryfikowana użytkowa droga pozostaje `/goal resume` we właściwej sesji; bezobsługowy jednorazowy klient `thread/goal/set` byłby osobnym zadaniem implementacji i testów.

## Uzupełnienie: dziedziczenie środowiska

Syntetyczny test wykazał, że początkowa wersja helpera dziedziczyła selektory executora i lokalizacji stanu. Finalna wersja odrzuca obecność znanych nadpisań, również z pustą wartością `CODEX_SQLITE_HOME`, `CODEX_EXEC_SERVER_URL`, czterech selektorów `CODEX_EXEC_SERVER_NOISE_` wymienionych poniżej oraz tożsamości federacyjnej. Test regresyjny najpierw wykazał brak tej ochrony, potem przeszedł po poprawce; błąd podaje wyłącznie nazwy zmiennych. Nie odczytywano rzeczywistych wartości ani sekretów.

W sprawdzonym kodzie CLI **nie ma automatycznej interpretacji ogólnego prefiksu `CODEX_REMOTE_*`** jako `--remote`: endpoint wynika z jawnego argumentu `remote`, a nazwa zmiennej tokenu z `--remote-auth-token-env`. Przykładowe `CODEX_REMOTE_TOKEN` w testach są nazwami wskazanymi flagą, nie magicznym selektorem. Nie należy twierdzić, że każdy `CODEX_REMOTE_*` sam przekierowuje daemon. Sam fakt przekazania tych zmiennych przez helper jest jednak potwierdzony.

Rzeczywiste selektory w źródłach:

| Zmienna / konfiguracja | Efekt |
|---|---|
| `CODEX_EXEC_SERVER_URL` | Legacy wybór środowiska wykonawczego; może oznaczać zdalnego executora. Wartość `none` wyłącza dostęp do środowiska, nie wymusza lokalności |
| `CODEX_EXEC_SERVER_NOISE_REGISTRY_URL`, `CODEX_EXEC_SERVER_NOISE_ENVIRONMENT_ID`, `CODEX_EXEC_SERVER_NOISE_AUTH_TOKEN`, opcjonalne `CODEX_EXEC_SERVER_NOISE_CHATGPT_ACCOUNT_ID` | Konfiguracja zdalnego środowiska Noise |
| `CODEX_SQLITE_HOME` | Zmienia lokalizację bazy stanu niezależnie od `CODEX_HOME` |
| `OPENAI_FEDERATION_RULE_ID`, `OPENAI_IDENTITY_TOKEN_FILE`, `OPENAI_WORKLOAD_IDENTITY_CONTEXT` | Wybierają/konfigurują workload identity; ścieżka może omijać zwykłe współdzielenie lokalnego daemona |
| `$CODEX_HOME/environments.toml` | Może określać zdalne środowiska również bez powyższych zmiennych |

Źródła: [executor environment](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/exec-server/src/environment.rs), [environment provider](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/exec-server/src/environment_provider.rs), [state constant](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/state/src/lib.rs), [workload identity](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/login/src/auth/workload_identity.rs), [CLI remote parser](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/cli/src/main.rs), [session-command connection selection](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/tui/src/session_archive_commands.rs).

Helper przerywa przy znanych selektorach środowiskowych zamiast potajemnie usuwać zmienne. Nie analizuje `environments.toml` ani aktywnej konfiguracji daemona. Przed uruchomieniem użytkownik musi więc potwierdzić kontekst istniejącego wątku; dla skonfigurowanego zdalnego środowiska użyć sprawdzonego natywnego klienta. W błędzie podawane są wyłącznie nazwy zmiennych, nigdy wartości. Sama blokada środowiska helpera nie zmienia już działającego daemona i nie dowodzi, gdzie istniejący wątek wykonuje narzędzia - to należy zweryfikować przed uzbrojeniem timera.

## Dodatkowa weryfikacja dla recenzji

**Dokładny odczyt stanu daemona:** `CODEX_HOME='/absolutny/katalog/.codex' /absolutna/sciezka/codex app-server daemon version`. Wbudowane help 0.166.0 opisuje odczyt wersji CLI i działającego app-server jako JSON. Nie istnieje `codex app-server daemon status` (parser sprawdzono z `--help`, odrzuca tę nazwę). Dla `version` sprawdź kod zakończenia 0 oraz JSON `status: "running"` i `appServerVersion`; sam wydruk lokalnej wersji Codex nie wystarcza. Brak daemona/błąd probe oznacza błąd, a nie automatyczny start. Użyj dokładnie tego samego binarium i `CODEX_HOME` co przy queue.

Weryfikacja bezpieczeństwa preflightu z kodu: [app-server-daemon/lib.rs](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/app-server-daemon/src/lib.rs), linie 416-419 kierują Version bezpośrednio do `version()` przed blokadą/ścieżką zmian; `version()` w liniach 691-702 odczytuje ustawienia, wykonuje probe istniejącego socketu i zwraca `LifecycleStatus::Running` z wersją serwera. [client.rs](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/app-server-daemon/src/client.rs), `probe` 34-60 ma timeout 2 s, łączy się do socketu, wykonuje initialize/initialized i zamyka połączenie. Nie uruchamia daemona, nie wznawia sesji, nie wykonuje model turn. Tutaj sprawdzono wyłącznie help i kod - nie wykonywano rzeczywistego probe konta/daemona.

**Queue nie uruchamia brakującego zarządzanego daemona.** `start_app_server_for_session_command` sprawdza istniejący domyślny socket. Przy braku socketu `app_server_target_for_launch` wybiera `Embedded`; po nieudanym połączeniu z istniejącym socketem może również nastąpić fallback do embedded. Queue może wtedy zapisać wiadomość, ale `resume_if_unloaded` odrzuca embedded z tekstem `start a local daemon or specify a server with --remote`, po czym wypisywane jest ostrzeżenie z exit 0. Źródła: [session_archive_commands.rs](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/tui/src/session_archive_commands.rs), linie 271-294; [tui/lib.rs](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/tui/src/lib.rs), `app_server_target_for_launch` 1063-1100 i `start_app_server` 580-624; [session_queue_commands.rs](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/tui/src/session_queue_commands.rs), `resume_if_unloaded`.

**Zarządzany daemon przeżywa zamknięcie TUI/terminala; embedded app-server nie ma tego kontraktu.** Backend ma null stdin, na Unix uruchamia `setsid()`, na Windows `DETACHED_PROCESS | CREATE_BREAKAWAY_FROM_JOB | CREATE_NO_WINDOW`, z komentarzem chroniącym przed śmiercią po zamknięciu terminala/SSH. Shutdown klienta Remote zamyka websocket przez `stream.close()`, zamiast wysyłać shutdown usługi. Źródła: [backend/pid_start.rs](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/app-server-daemon/src/backend/pid_start.rs), linie 112 i 160-183; [remote.rs](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/app-server-client/src/remote.rs), linie 351-363. Dowód z kodu; nie zamykano rzeczywistego TUI. To nie gwarantuje dostępności po uśpieniu lub restarcie ani nie utrzymuje osobnego foreground timera.

**Dokładne komunikaty wydania 0.166.0** z [session_queue_commands.rs](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/tui/src/session_queue_commands.rs), linie 84-96:

```text
stdout: Queued message {queued_submission.id} for thread {thread_id}.
stderr przy nieudanym resume: Warning: message was queued, but could not resume thread {thread_id}: {err:#}
```

To literały tej wersji, nie obietnica niezmiennego tekstowego kontraktu przyszłych wersji. Receipt potwierdza kolejkę, nie rozpoczęcie turnu.

**Wniosek z implementacji: sam stan celu `usage_limited` nie blokuje zwykłego wejścia użytkownika z queue.** `ThreadQueueRequestProcessor::add` sprawdza własność/dopuszczalność direct input, a `QueuedItemService::enqueue` budzi załadowany wątek. `dispatch_if_idle` wysyła `TurnInput::UserInput` przez `start_turn_if_idle` z triggerem `queue`. W tej ścieżce i przyjęciu turnu nie ma testu statusu celu. Limit konta może oczywiście nadal odrzucić wywołanie. Warunki: wątek załadowany i bezczynny, dozwolone direct input, serwer i quota dostępne. `wake_if_loaded` nie budzi `AgentStatus::Interrupted`, a hook idle pomija `ThreadIdleCause::Interrupted`. Nie przeprowadzano live testu po limicie. Źródła: [thread_queue_processor.rs](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/app-server/src/request_processors/thread_queue_processor.rs), `add` 76-96; [queue/service.rs](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/ext/queue/src/service.rs), `enqueue` 265-279, `dispatch_if_idle` 405-465, `wake_if_loaded` 472-482, `on_thread_idle` 549-566; [core/session/turn_input.rs](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/core/src/session/turn_input.rs); [core/codex_thread.rs](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/core/src/codex_thread.rs), `start_turn_if_idle`, `submit_turn_input_with_mode`.

**`-C` po `queue` działa lokalnie.** `configure_help` w [queue_cmd.rs](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/cli/src/queue_cmd.rs) prezentuje cd w `Local server options (without --remote)`, a `validate_options` dopuszcza cd bez remote i odrzuca cd+remote. Lokalny parser sprawdzono poleceniem zakończonym `--help`: `codex queue -C /tmp --thread 11111111-1111-4111-8111-111111111111 --message 'synthetic grammar check' --resume --help` zakończył się 0. Nie wysyłano wiadomości.

Kontrola czasu używa zegara monotonicznego i ponownego sprawdzenia budżetu po wybudzeniu, przed wysłaniem. Nie sumuje samych żądanych interwałów sleep.
