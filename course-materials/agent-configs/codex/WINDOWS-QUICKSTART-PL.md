# Codex na Windows: ustawienia użytkownika i kursu

## 1. Ustaw konfigurację użytkownika

Jeśli provisioning poprosi o UAC, zatwierdza go uprawniony użytkownik lub IT. Bez potrzebnych uprawnień poproś prowadzącego/IT o przygotowanie środowiska; nie obchodź polityki firmy.

Otwórz **zwykły PowerShell Windows**. Znajdź plik używany przez Codex:

Na VM katalogi konfiguracji Codex i Claude Code są skonfigurowane pod `D:\AI\labuser`. Zachowaj skonfigurowane `CODEX_HOME` i `CLAUDE_CONFIG_DIR`. Repozytorium: `D:\jsystems-claude-codex-gis-2026-11`.

```powershell
micro (Join-Path $env:CODEX_HOME 'config.toml')
```

Zrób kopię pliku przed edycją. **Scal poniższe wpisy z istniejącym plikiem**; zachowaj pozostałe ustawienia i nie dodawaj drugiej tabeli `[windows]` ani `[features]`.

```toml
# Przykład do demonstracji: wyłącza lokalny sandbox. Pozostaw zakomentowany.
# sandbox_mode = "danger-full-access"

# Normalny sandbox i automatyczny recenzent próśb o dodatkowy dostęp.
default_permissions = ":workspace"
approval_policy = "on-request"
approvals_reviewer = "auto_review"

[windows]
sandbox = "elevated"

[features]
prefer_mxc = false
network_proxy = false
```

Zakomentuj inne aktywne `sandbox_mode` i usuń aktywną tabelę `[sandbox_workspace_write]`, jeśli przechodzisz na ten system profili. Nie łącz obu systemów konfiguracji. `prefer_mxc = false` wraz z wyborem `elevated` ustawia kursowy wariant Windows. Jawne `network_proxy = false` wyłącza także wcześniejsze ustawienie użytkownika. Polityka administratora lub jawne nadpisanie ustawień nadal może mieć wyższy priorytet.

## 2. Zrestartuj serwer i rozpocznij nową rozmowę

Zakończ zadania agentów i zamknij interfejsy Codex. Restart serwera rozłącza wszystkie korzystające z niego sesje tego użytkownika. W zwykłym PowerShellu, w katalogu swojego repozytorium, wykonaj kolejno:

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

Sprawdź, czy restart się udał. Ustaw PATH przed restartem daemona. Wiersz z PATH udostępnia zainstalowany Playwright CLI w tym oknie i uruchamianym z niego Codexie; nie instaluje narzędzia. Uruchom nową rozmowę, aby sprawdzić nowe domyślne ustawienia. Wznowiona rozmowa może przywrócić zapisany profil. Nie używaj `--no-daemon` w standardowym teście kursu.

Po aktualizacji **samego CLI**, gdy chcesz użyć tej samej wersji serwera, wykonaj przed restartem `codex app-server daemon update --from-cli` i zatwierdź zastąpienie pakietu. Nie potrzeba tego po zwykłej edycji konfiguracji. Komendy sprawdzono w pomocy CLI 0.166.0. W TUI alternatywą jest `/daemon` i **Restart background server**.

## 3. Wybierz, gdzie ma obowiązywać profil kursowy

- **Tylko w repozytorium kursowym:** pozostaw globalne `default_permissions = ":workspace"`. Bieżąca konfiguracja `.codex/config.toml` wybiera ścisły `course-root`. Do ćwiczenia narzędzi hostowych na danych syntetycznych scal definicję `course-tools` z [permissions.toml](permissions.toml) z konfiguracją projektu, ustaw w niej `default_permissions = "course-tools"` i scal przejrzane [rules/course.rules](rules/course.rules) z regułami projektu. Zachowaj inne ustawienia, w tym ścieżki map-qa i MCP; nie nadpisuj całego pliku.
- **Dla wszystkich swoich projektów:** scal definicje `[permissions]` z [permissions.toml](permissions.toml) albo [config.toml](config.toml) do konfiguracji użytkownika. Następnie ustaw w niej `default_permissions = "course-tools"` i skopiuj przejrzany [rules/course.rules](rules/course.rules) do `$CODEX_HOME/rules/course.rules` (domyślnie `~/.codex/rules/course.rules`). Reguły będą wtedy obowiązywać użytkownika w innych projektach. Konfiguracja konkretnego projektu może wybrać inny profil.

Samo wpisanie nazwy `course-tools` globalnie nie wystarczy: definicja profilu musi być dostępna również poza repozytorium kursu. Nie kopiuj całego pliku na istniejącą konfigurację bez przejrzenia; scal potrzebne sekcje. Pełny przykład zawiera też opcjonalne modele i MCP.

## 4. Sprawdź działanie

W nowej sesji sprawdź `/permissions`, `/status` i `/mcp`. Sprawdź profil, który świadomie wybrałeś: dotychczasowy `course-root` albo opcjonalny `course-tools`. Pełny przykład włącza Context7; aktywny projekt obecnie go wyłącza. Do ćwiczenia dokumentacji włącz wpis Context7 również w projekcie, bez obowiązkowego nagłówka klucza, i sprawdź połączenie w `/mcp`. Profil plików/sieci i recenzent zgód są oddzielnymi ustawieniami: kombinacja `on-request` + `auto_review` włącza "Approve for me" także z własnym profilem.

Poproś agenta kolejno o:
1. Context7: `resolve-library-id` dla GeoPandas, potem `query-docs` przez zwrócony identyfikator.
2. `gh repo view OWNER/REPO --json name` dla swojego repozytorium.
3. Osobne `playwright-cli open about:blank --browser=chrome --headed`, `playwright-cli snapshot`, `playwright-cli close`.

Sukces tych trzech narzędzi nie dowodzi izolacji: działają również przy wyłączonym sandboxie. Poproś dodatkowo o dwa osobne polecenia **bez eskalacji, bez wyjątku allow i bez próby ponowienia poza sandboxem**: zapis nowego pliku syntetycznego w workspace (ma się udać) oraz zapis pliku o unikalnej nazwie poza wszystkimi dozwolonymi katalogami, np. w katalogu domowym, jeśli nie jest workspace/temp (ma być odmowa). Nie zatwierdzaj eskalacji tego testu; auto-review może ją zatwierdzić bez ręcznego pytania, dlatego sprawdź w przebiegu narzędzi, że polecenie rzeczywiście pozostało w sandboxie. Jeśli plik poza granicą powstał, usuń wyłącznie ten rozpoznany plik z własnego terminala. Jeśli zapis poza granicą się uda, nie uznawaj sandboxa za zweryfikowany; sprawdź efektywną konfigurację. To osobny test granicy, nie powtórka wywołań gh/Playwright.

W tym teście użyj domyślnej sesji Playwright i komendy przed opcjami, aby pasowała reguła prefiksu. Jeśli narzędzie nie działa, przekaż prowadzącemu komendę i niesekretny błąd. 401 z sandboxa nie oznacza automatycznie wylogowania użytkownika. Nie drukuj tokenów ani całego środowiska.

Porównanie błędów ACL/MXC i zachowania formularzy: [fakty i ograniczenia Codex](../../Research/codex-sandbox-facts-and-limitations-2026-11-06.md).

### Zanim dodasz prawdziwy klucz API

Dane testowe mogą być syntetyczne, ale klucz API jest prawdziwym sekretem. Nie dodawaj go do workspace z aktywnym `course-tools`.

Najpierw utwórz plik z **fałszywą** wartością w dokładnie tej lokalizacji i pod tą nazwą, których użyjesz dla klucza, np. `app/.env`. Wybierz profil ścisły (`course-root`/`course-workspace`) w nowej sesji i sprawdź blokadę odczytu tego pliku. Lista obejmuje `.env`, `.env.local`, `.env.dev`, `.env.prod`, `.env.test` i wskazane `secrets`; nie obejmuje dowolnej nazwy typu `.env.development.local`. Jeśli test nie potwierdzi ochrony, nie dodawaj klucza.

Gdy plik klucza ma pozostać w repo, ustaw także skuteczny domyślny profil projektu na `default_permissions = "course-root"` (nie tylko wybór bieżącej sesji), zrestartuj daemon i sprawdzaj `/permissions` w każdej nowej rozmowie. Nie wznawiaj starych rozmów `course-tools`. Na czas obecności klucza wyłącz wyjątki `allow` dla gh/Playwright we wszystkich wczytywanych regułach projektu i użytkownika; zachowaj reguły `forbidden`. Narzędzia hostowe wykonuj samodzielnie. Przed powrotem do `course-tools` usuń rzeczywisty klucz z workspace.

Blokada obejmuje także serwer i testy uruchamiane przez agenta, więc uruchomienia z prawdziwym kluczem wykonuj z własnego terminala. Wyjątki hostowe gh/Playwright mogą pod profilem ścisłym przestać działać. Samej zmiennej środowiskowej nie traktuj jako ochrony przed agentem.

Do tego czasu używaj modelu testowego bez klucza. Używaj odwoływalnego klucza z ograniczonym budżetem; nie wpisuj go do rozmowy ani Git.

## Jak to działa

Sandbox ogranicza zwykłe polecenia. `:workspace` pozwala zapisywać w workspace i katalogach tymczasowych. `course-tools` dodatkowo włącza sieć i nie dodaje OS-owych blokad odczytu .env/secrets: używaj go wyłącznie na syntetycznych danych kursowych. Lista domen nie ogranicza bezpośrednich połączeń bez aktywnego proxy sieciowego.

Reguły `allow` pozwalają wskazanym odczytowym poleceniom gh oraz Playwright open/snapshot/close działać **poza sandboxem**, z uprawnieniami użytkownika Windows. To daje im dostęp do logowania i przeglądarki. Prefiks open nie ogranicza URL. Reguły gh nie ograniczają repozytorium: z opcją `-R właściciel/repo` agent odczyta każde repozytorium dostępne dla Twojego tokenu, więc używaj tokenu ograniczonego do repozytoriów kursowych. Inne działania podlegają zwykłej polityce; `prompt` trafia do recenzenta, a `forbidden` blokuje. Auto-review nie recenzuje każdej dozwolonej komendy. Prefiksy nie filtrują też opcji: `snapshot --filename` może zapisać plik poza workspace, a `open --profile`, `--persistent` lub `--config` wybierać dodatkowy stan lub konfigurację. Używaj własnej sesji kursowej, danych syntetycznych i przejrzanych opcji.

| Profil | Zastosowanie |
|---|---|
| `course-tools` | Opcjonalny dla danych syntetycznych: edycja, sieć, wyjątki hostowe z reguł; bez deny-read sekretów. |
| `course-workspace` | Ścisła edycja: blokady wskazanych .env/secrets; może ograniczać eskalację hostową. |
| `course-root` | Alias zgodności dla course-workspace; bez dodatkowych uprawnień. |
| `course-review` | Workspace tylko do odczytu; ścisłe blokady; temp zapisywalne. |
| `course-docs` | Jak review, lecz docs/ można edytować. |
| `course-jetbrains` | Opcjonalny przykład listy domen; wymaga osobno aktywnego proxy, aby ją egzekwować. |

"Low integrity" to etykieta ograniczeń procesu Windows. Zwykły PowerShell zwykle ma poziom medium, administrator high, a low ogranicza m.in. zapis do zasobów zwykłych aplikacji. To nie jest komunikat o uszkodzeniu programu. AppContainer nakłada dodatkowe ograniczenia; sam poziom low nie rozstrzyga przyczyny błędu narzędzia.

WezTerm jest opcjonalnym terminalem. Nie wybiera sandboxa. Nie wykonano tu testu jego działania ani porównania stabilności.

Szczegóły i wyniki pomiarów: [wyniki pomiarów](../../Research/codex-windows-sandbox-compatibility-2026-11-05.md). Źródła: [profile](https://learn.chatgpt.com/docs/permissions), [Auto-review](https://learn.chatgpt.com/docs/sandboxing/auto-review), [Windows](https://learn.chatgpt.com/docs/windows/windows-sandbox), [reguły](https://learn.chatgpt.com/docs/agent-configuration/rules).
