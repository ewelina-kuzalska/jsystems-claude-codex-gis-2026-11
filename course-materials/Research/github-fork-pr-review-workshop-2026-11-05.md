# Fork, pull request i odpowiedź na code review

Sprawdzone 5.11.2026. Ćwiczenie: wypchnij uzgodnioną zmianę w pipeline GIS do własnego forka, utwórz PR do repo prowadzącego, przeczytaj review, sprawdź uwagi, popraw kod i opublikuj jedną zbiorczą odpowiedź. PR służy ćwiczeniu review; nie merguj go do wspólnego main bez decyzji właściciela.

## Dwa repozytoria i dwa rodzaje uprawnień

- **Head:** Twoja gałąź w Twoim forku. Tu zapisujesz poprawki i robisz push.
- **Base:** `LucasMatuszewski/jsystems-claude-codex-gis-2026-11:main`. Tu należy numer PR, komentarze, review i wątki.

Fine-grained PAT wybrany tylko dla Twojego forka nie daje prawa tworzenia PR lub dodawania komentarzy w repo prowadzącego. Publiczny odczyt nie oznacza prawa zapisu przez ten token. Token ma jednego resource ownera i określony wybór repozytoriów; nie można po prostu dopisać drugiego osobistego właściciela do tego samego zakresu.

**Rekomendacja na ćwiczenie:** zostaw obecny token do własnego forka. PR i zbiorczą odpowiedź opublikuj przez zalogowaną przeglądarkę. Agent nadal czyta publiczne uwagi, przygotowuje poprawki/testy i wypycha tę samą gałąź forka. Nie zapraszamy całej grupy jako collaboratorów tylko po to, by obejść token.

`Course-Tools` i sandbox sterują dostępem narzędzia do środowiska lokalnego. Nie rozszerzają zdalnych uprawnień PAT w GitHub. Rozróżnij brak dostępu do credential store w sandboxie od rzeczywistej odmowy zapisu do upstream.

Dokładne ścieżki dla administratora firmy i właściciela forka: [ChatGPT Business, GitHub App i Copilot Business](github-code-review-company-settings-2026-11-05.md).

## 1. Push i PR

Przed synchronizacją zachowaj lokalną pracę, potwierdź remotes oraz gałąź. Zaktualizuj main swojego forka z upstream/main, a implementację prowadź na osobnej gałęzi; nie resetuj ani nie nadpisuj cudzej pracy. Nie twórz ponownie forka, który już istnieje.

Po pushu swojej gałęzi w GitHub wybierz **Contribute / Open pull request** albo **Compare & pull request**. Sprawdź: base repository prowadzącego, base `main`, head Twój fork, compare Twoja gałąź. W treści podaj cel zmiany i faktyczną weryfikację. [Szablon opisu PR](../agent-configs/github-review/pr-body.md).

Tworzenie PR przez API/CLI wymaga osobno wybranego uwierzytelnienia z uprawnieniami do repo bazowego. Poniższy kształt jest dla takiego świadomie skonfigurowanego wariantu; **nie jest obejściem tokenu ograniczonego do forka**:

```bash
gh pr create --repo LucasMatuszewski/jsystems-claude-codex-gis-2026-11 --base main --head STUDENT_LOGIN:exercise-branch --title 'Exercise: concrete change' --body-file pr-body.md
```

Zastąp placeholdery. `gh pr create --dry-run` nie jest bezpiecznym testem braku zapisu: help ostrzega, że może wykonać push.

## 2. Reviewer: repo i dashboard to dwie warstwy

Repozytoryjne instrukcje określają kryteria review. Połączenie GitHub, dostęp do repo i wyzwalacze włącza się osobno w usłudze. Skopiowanie AGENTS.md ani utworzenie forka nie instaluje bota i nie kopiuje ustawień konta prowadzącego.

### Copilot

Sprawdź dostępność Copilot review w swoim PR. Obecność opcji albo zdarzenia żądania nie dowodzi wykonania recenzji ani automatyki obejmującej wszystkich autorów.

1. W PR wybierz **Reviewers -> Copilot**, jeżeli masz odpowiedni dostęp. Brak opcji sprawdź w kontekście planu/polityk, nie naprawiaj go rozszerzaniem PAT w ciemno.
2. Na własnym repo sprawdź uprawnienia i osobiste ustawienia **Copilot -> Code review**. Dla automatyki repozytorium administrator może ustawić ruleset **Automatically request Copilot code review**.
3. Na początek jedno review aktualnego SHA, bez automatycznego ponawiania po każdym pushu. Zobacz rzeczywisty wynik, nie tylko event zamówienia.

Copilot Code Review wymaga kwalifikującego dostępu Copilot. ChatGPT Business nie jest GitHub Copilot Business. Aktualne rozliczenie obejmuje AI credits oraz ewentualne Actions minutes; nie zakładaj dawnego stałego kosztu jednego premium requestu. Nie włączaj nowego płatnego usage bez ustalenia konta i kosztu.

### Codex

1. We właściwym workspace Codex połącz GitHub i wybierz tylko potrzebne repozytorium.
2. W ustawieniach **Code review / Review code** włącz dostęp dla repo. Ręczny przegląd zamawia `@codex review`; automatyka jest osobnym ustawieniem.
3. Sprawdź docelowy workspace, zakres autorów i quota. Dostęp do Codex w ChatGPT Business sam nie nadaje uprawnień GitHub ani nie włącza integracji.
4. AGENTS.md w repo zawiera kryteria review; ustawienie pliku nie zastępuje powyższych kroków.

Konfiguruj aplikację na własnym forku jako jego właściciel. Zacznij od jednego forka/PR i jednego reviewera. Jeśli nie masz dostępu lub limitu, wykonaj review lokalne. Korzystaj wyłącznie z własnego uwierzytelnienia.

### Claude, PR-Agent i CI/CD

- **Lokalny Claude/Codex CLI:** korzysta z faktycznego logowania CLI i jego limitu lub API. To dobry fallback; sprawdź model i wykonuj review bez zmian/publikacji, dopóki nie są zlecone.
- **Zarządzane Claude Code Review:** Team/Enterprise oraz osobne usage credits organizacji. Nie traktuj go jako bezpłatnego dodatku do abonamentu. Fork PR ma odrębne zasady; maintainer bazowego repo może zamawiać review ręcznie zgodnie z aktualną dokumentacją.
- **Claude Code GitHub Action:** workflow i wybrana autoryzacja API lub kwalifikującego abonamentu OAuth; dochodzą Actions i właściwe usage. Nie jest tą samą usługą co zarządzany reviewer.
- **Codex Action / `codex exec` w CI / Community PR-Agent:** osobny workflow i provider. ChatGPT Business nie pokrywa automatycznie API w pipeline. Przykłady są w [cicd-headless](../cicd-headless/README.md).

Dla fork PR nie uruchamiaj nieufnego kodu z dostępem do sekretów repo bazowego. Nie dodawaj `pull_request_target` z checkoutem i wykonaniem kodu PR jako szybkiego obejścia. Na warsztacie najpierw działająca natywna integracja albo lokalny reviewer, potem świadome CI.

## 3. Odczytaj pełne review

Nie wystarcza `gh pr view --comments`: zbierz podsumowania review, inline comments i odpowiedzi, komentarze konwersacji, stan wątków oraz checks aktualnego commita.

```bash
gh api --paginate repos/LucasMatuszewski/jsystems-claude-codex-gis-2026-11/pulls/PR_NUMBER/reviews
```

```bash
gh api --paginate repos/LucasMatuszewski/jsystems-claude-codex-gis-2026-11/pulls/PR_NUMBER/comments
```

```bash
gh api --paginate repos/LucasMatuszewski/jsystems-claude-codex-gis-2026-11/issues/PR_NUMBER/comments
```

Zastąp `PR_NUMBER`. Wątki resolved/unresolved sprawdź w **Files changed** albo przez GraphQL `reviewThreads.isResolved`. Skrypty odczytu: [Bash](../agent-configs/github-review/read-review.sh), [PowerShell](../agent-configs/github-review/read-review.ps1). To odczyty, nie test uprawnień zapisu do upstream. Jeśli credential nie pozwala nawet na odczyt publicznej strony, użyj przeglądarki lub publicznego REST bez credential; nie poszerzaj scope automatycznie.

## 4. Popraw i odpowiedz raz

Wklej do lokalnego agenta po podaniu prawdziwego URL PR:

```text
Use respond-to-code-review for the upstream PR URL I provide. Read all review
summaries, inline comments/replies, unresolved threads and current-head checks.
Verify each finding against the code and reproduce substantive failures.
Apply only justified fixes, run relevant checks, and commit/push only to my
existing fork branch as authorized. Preserve unrelated work.
The fine-grained token selects only my fork. Do not attempt upstream writes.
Prepare review-response.md with one consolidated response covering every finding,
fix/test evidence and reasons for items not changed. I will publish it once in
the GitHub browser. Recheck feedback on the final head. Do not merge.
```

[Szablon odpowiedzi](../agent-configs/github-review/review-response.md). Odpowiedź obejmuje wszystkie uwagi, także niepotwierdzone lub już poprawione. Nie stosuj sugestii wyłącznie po to, by zamknąć wątek. Dodatkowe odpowiedzi w każdym wątku są potrzebne tylko przy wymaganiu projektu/platformy lub wyraźnej prośbie.

Push poprawki do tej samej gałęzi forka aktualizuje upstream PR. Sprawdź nowy SHA i wynik checks. Opublikuj jedną zbiorczą odpowiedź jako autor PR w przeglądarce. Emoji bota, sam request, zielony workflow lub brak uwag nie są dowodem pełnego review. Nie zatwierdzaj własnego PR jako zamiennika odpowiedzi.

## Szersze uwierzytelnienie: osobna decyzja

Pełny agentowy zapis w upstream może wymagać innego uwierzytelnienia. OAuth `gh auth login` domyślnie ma szersze zakresy, a classic PAT `public_repo` obejmuje wiele publicznych repozytoriów. Żaden wariant nie jest odpowiednikiem obecnego tokenu ograniczonego do jednego forka. Do opublikowania odpowiedzi wybierz przeglądarkę, jeśli nie potrzebujesz szerszego zakresu tokenu.

`GH_TOKEN`/`GITHUB_TOKEN` mogą nadpisywać credential z keyringu. Sprawdzaj źródło przez `gh auth status`, bez `--show-token` i bez wypisywania wartości. Naprawa sandboxa, źródła uwierzytelnienia i uprawnień do repo to trzy różne sprawy.

## Źródła

GitHub: ograniczenia fine-grained PAT i resource owner
https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens

GitHub: konfiguracja code review i dostęp/rozliczenie
https://docs.github.com/en/copilot/how-tos/copilot-on-github/set-up-copilot/configure-code-review
https://docs.github.com/en/copilot/concepts/agent-capabilities/agent-powered-workflows-and-operations/code-review

OpenAI: GitHub Code Review
https://learn.chatgpt.com/docs/third-party/github

Claude: zarządzane review, koszty i Actions
https://code.claude.com/docs/en/code-review
https://code.claude.com/docs/en/code-review-costs
https://code.claude.com/docs/en/github-actions

GitHub CLI: tworzenie PR i komentarze
https://cli.github.com/manual/gh_pr_create
https://cli.github.com/manual/gh_pr_comment

Metadane kursowego repo odczytano bez zmian ustawień. Nie testowano zapisu tokenem uczestnika, nie aktywowano nowych billingów, nie instalowano aplikacji ani nie uruchomiono płatnego CI. PowerShell helper sprawdzono statycznie; Bash przeszedł bash -n.
