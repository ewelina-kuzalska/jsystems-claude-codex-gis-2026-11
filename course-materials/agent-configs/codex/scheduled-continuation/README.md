# Jednorazowa kontynuacja Codex po resecie limitu

**W Codex CLI 0.166.0 użyj `queue` do konkretnego UUID; jednorazowy timer uruchom o godzinie resetu + 10 minut.** To próba wysłania kontynuacji, nie gwarancja, że limit zniknął lub praca została zakończona.

**Granica tego rozwiązania:** timer nie przywraca automatycznie trwałego celu `usage_limited` do `active`. Pełne bezobsługowe wznowienie celu wymaga natywnego API app-server albo dodatkowej zweryfikowanej integracji. Tutaj bezpieczna droga dla celu to `/goal resume` we właściwej sesji po resecie. Helper obsługuje zweryfikowany domyślny lokalny daemon i odrzuca znane selektory executora/stanu; pozostałe zmienne procesu są dziedziczone.

## 1. Przed przerwą

We właściwej sesji sprawdź `/status`: konto, model, limity i godzinę resetu. Zapisz dokładny UUID sesji, np. z polecenia `codex resume UUID` pokazywanego przy wyjściu z TUI. Zachowaj absolutny katalog projektu i katalog `CODEX_HOME` używany przez tę sesję. Nie używaj `--last`.

Jeżeli pracujesz z celem, sprawdź `/goal`. Po błędzie limitu może być `usage_limited`; w TUI po resecie użyj `/goal resume`. Ponowne otwarcie wątku samo w sobie nie gwarantuje aktywowania celu. Tekst `"/goal resume"` wysłany przez `queue --message` nie zastępuje komendy wpisanej w TUI.

## 2. Sprawdź daemon przed ustawieniem timera

`queue` nie uruchamia brakującego daemona. Zarządzany daemon działa niezależnie od terminala; serwer embedded używany np. z `--no-daemon` ma inny cykl życia. Nie zakładaj, że pozostawienie dowolnego okna zapewnia działający daemon.

Na VM zachowaj istniejące `CODEX_HOME` pod `D:\AI\labuser`; nie twórz nowego katalogu logowania dla timera. Dla tego samego pliku wykonywalnego i `CODEX_HOME` wykonaj odczyt stanu, który nie startuje daemona ani modelu:

```bash
CODEX_HOME='/home/TWOJ_LOGIN/.codex' codex app-server daemon version
```

```powershell
$courseCodexHome = $env:CODEX_HOME
```

```powershell
codex app-server daemon version
```

Wymagaj kodu 0 oraz JSON z `status: "running"` i `appServerVersion`. Jeśli odczyt się nie uda, nie uzbrajaj timera; sprawdź sposób uruchomienia sesji. Ten preflight zweryfikowano w kodzie i help wersji 0.166.0, bez próby na rzeczywistym daemonie. Także poprawny preflight nie gwarantuje, że daemon będzie działał za kilka godzin.

## 3. Polecenie natywne

Linux/WSL, po podstawieniu swoich danych:

```bash
CODEX_HOME='/home/TWOJ_LOGIN/.codex' codex queue  -C '/absolutny/katalog/projektu'  --thread '11111111-1111-4111-8111-111111111111'  --message 'Kontynuuj uzgodnione zadanie od ostatniego punktu. Zachowaj zakres, model i uprawnienia. Jeśli limit nadal blokuje pracę, zakończ tę próbę i podaj przyczynę.'  --resume
```

Windows PowerShell, dla **natywnej sesji Windows**:

```powershell
$courseCodexHome = $env:CODEX_HOME
```

```powershell
codex queue -C 'D:\jsystems-claude-codex-gis-2026-11'  --thread '11111111-1111-4111-8111-111111111111'  --message 'Kontynuuj uzgodnione zadanie od ostatniego punktu. Zachowaj zakres, model i uprawnienia. Jeśli limit nadal blokuje pracę, zakończ tę próbę i podaj przyczynę.'  --resume
```

Przykładowy UUID trzeba zastąpić prawdziwym. Jeśli sesja wymaga profilu, zweryfikuj osobno połączenie z jej serwerem - samo dopisanie `-p` może wyłączyć współdzielenie lokalnego daemona. Queue używa modelu wątku i wymaga lokalnego daemona lub jawnie wybranego serwera. Nie dodawaj `--model` ani flag obchodzących zgody/sandbox.

**Ostrzeżenie:** CLI może wypisać `Warning: message was queued, but could not resume thread ...` i zwrócić kod 0. Sprawdź komunikat oraz właściwy wątek. Nie wysyłaj od razu duplikatu: pierwsza wiadomość może już być w kolejce.

## 4. Jednorazowy timer z załączonym helperem

Skrypt `resume_once.py` wymaga Python 3 i działa w pierwszym planie. Najpierw uruchom dry-run. Przykład: reset 6 listopada 2026 o 05:50 UTC, uruchomienie o 06:00 UTC. Jeżeli reset jest o 06:00, podaj 06:00 i otrzymasz próbę o 06:10. Użyj własnej daty, offsetu i ścieżek.

Linux/WSL:

```bash
python3 '/absolutna/sciezka/resume_once.py'  --session '11111111-1111-4111-8111-111111111111'  --project '/absolutny/katalog/projektu'  --codex-home '/home/TWOJ_LOGIN/.codex'  --codex '/absolutna/sciezka/do/codex'  --reset-at '2026-11-06T05:50:00+00:00'  --buffer-minutes 10  --message 'Kontynuuj uzgodnione zadanie od ostatniego punktu; zachowaj zakres i uprawnienia. Jeśli limit nadal blokuje pracę, zakończ tę próbę i podaj przyczynę.'  --log '/absolutna/sciezka/nowy-log-wznowienia.jsonl'
```

Windows PowerShell, **wyłącznie jeżeli masz sprawdzony natywny `codex.exe` i Python**:

```powershell
$resumeArgs = @('D:\jsystems-claude-codex-gis-2026-11\course-materials\agent-configs\codex\scheduled-continuation\resume_once.py', '--session', '11111111-1111-4111-8111-111111111111', '--project', 'D:\jsystems-claude-codex-gis-2026-11', '--codex-home', $courseCodexHome, '--codex', 'C:\absolutna\sciezka\codex.exe', '--reset-at', '2026-11-06T06:50:00+01:00', '--buffer-minutes', '10', '--message', 'Kontynuuj uzgodnione zadanie; zachowaj zakres i uprawnienia. Jeśli limit nadal blokuje pracę, zakończ tę próbę i podaj przyczynę.', '--log', 'C:\Users\TWOJ_LOGIN\prywatne\nowy-log-wznowienia.jsonl')
```

```powershell
py -3 @resumeArgs
```

Powyższe warianty wskazują ten sam moment: 05:50 UTC = 06:50 w Polsce w listopadzie. Aby uzbroić timer po przejrzeniu planu, ponów polecenie Linux z końcowym `--run`; w PowerShell użyj `py -3 @resumeArgs --run`. Katalog logu musi już istnieć, plik logu musi być nowy. Na Windows wybierz prywatny katalog z odpowiednim ACL.

Helper nie instaluje harmonogramu, nie odnawia limitu, nie wydaje kredytów i nie przełącza konta/modelu. Nie obsługuje profili ani zdalnych serwerów - dla nich użyj jawnego natywnego polecenia w odpowiednim środowisku. Odrzuca znane nadpisania executora, tożsamości lub lokalizacji stanu (np. `CODEX_EXEC_SERVER_URL`, `CODEX_SQLITE_HOME`), wypisując tylko nazwy zmiennych. Nie analizuje konfiguracji zdalnej w plikach ani w działającym daemonie - potwierdź lokalny kontekst wątku przed uruchomieniem. Kod 2 oznacza błąd walidacji/argumentów; 4 - przerwanie bez wysłania (spóźnienie, zmiana zegara lub wyczerpany czas oczekiwania). Kod 1 oznacza błąd wywołania CLI (oryginalny kod zapisany w logu); 5 - brak rozpoznanego potwierdzenia dla wskazanego UUID. Kod 3 oznacza "wiadomość zakolejkowana, resume się nie powiodło"; 124 oznacza timeout z niepewnym dostarczeniem. Brak automatycznych ponowień.

Przed użyciem zweryfikuj lokalność daemona i środowiska. Helper odrzuca obecność dokładnie tych zmiennych, również z pustą wartością:

- `CODEX_SQLITE_HOME`, `CODEX_EXEC_SERVER_URL`;
- `CODEX_EXEC_SERVER_NOISE_REGISTRY_URL`, `CODEX_EXEC_SERVER_NOISE_ENVIRONMENT_ID`, `CODEX_EXEC_SERVER_NOISE_AUTH_TOKEN`, `CODEX_EXEC_SERVER_NOISE_CHATGPT_ACCOUNT_ID`;
- `OPENAI_FEDERATION_RULE_ID`, `OPENAI_IDENTITY_TOKEN_FILE`, `OPENAI_WORKLOAD_IDENTITY_CONTEXT`.

Nie analizuje `CODEX_HOME/environments.toml` ani konfiguracji działającego daemona. Nie pokazuj wartości tokenów ani nie usuwaj ustawień w ciemno. [Raport i źródła](../../../Research/codex-scheduled-continuation-2026-11-05.md).

Pozostaw działający proces timera i daemon. Terminala nie zamykaj, komputera nie wyłączaj ani nie usypiaj. WSL timer uruchom w tej samej dystrybucji co sesja. Helper może przerwać próbę po zbyt późnym wybudzeniu; nie budzi komputera. Po czasie sprawdź docelowy wątek i log. Sam sukces wysłania nie oznacza zakończenia zadania.

Odczyt wyjścia jest jawnie UTF-8. Na Windows helper odrzuca wrappery `.cmd`, `.bat` i `.ps1`; dla instalacji npm sprawdź `(Get-Command codex).Source` i właściwy sposób uruchomienia. Nie zgaduj ścieżki wewnątrz pakietu. Wariant Windows jest nieprzetestowany; na kursie użyj go jako referencji, a praktyczne wznowienie sprawdź przez natywne polecenie.

## 5. Alternatywa natywna w aplikacji

Jeśli pracujesz w czacie aplikacji/webie, sprawdź dostępność Scheduled i poproś o **jednorazową kontynuację tego samego czatu** o konkretnej dacie/godzinie ze strefą. To funkcja aplikacji, a nie komenda CLI do dowolnego lokalnego UUID. Dla plików lokalnych potrzebujesz działającej aplikacji na włączonym komputerze. Tego harmonogramu nie testowano na rzeczywistym koncie.

Dokumentacja OpenAI: [queue i resume](https://learn.chatgpt.com/docs/developer-commands?surface=cli), [Scheduled tasks](https://learn.chatgpt.com/docs/automations?surface=app), [Goals](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex).

Weryfikacja: składnia CLI 0.166.0 i 14 syntetycznych testów helpera na Linuksie. Rzeczywiste wznowienie po limicie i Windows nie były testowane.

Kontrola czasu używa zegara monotonicznego i ponownego sprawdzenia budżetu po wybudzeniu, przed wysłaniem. Nie sumuje samych żądanych interwałów sleep.
