# Pytania Codex: formularze, Plan i odpowiedzi w rozmowie

**Do ustalania wymaganych decyzji wybierz Plan. Jeśli formularz znika, odpowiedz zwykłą wiadomością i nazwij decyzję.**

Instrukcja dotyczy Codex CLI/TUI 0.166.0. Aplikacja desktopowa ma własny interfejs; dostępność narzędzi zależy też od modelu i ustawień sesji.

## 1. Zbierz decyzje przed pisaniem

Sprawdź wersję:

```bash
codex --version
```

Gdy Codex nie pracuje, wpisz `/plan`. Następnie wklej:

```text
Przeczytaj opis zadania i istotne pliki. Zbierz decyzje potrzebne do PRD.
W Plan korzystaj z request_user_input, gdy jest dostępny.
Grupuj po 2-3 niezależne pytania, jeśli narzędzie na to pozwala.
Jeśli odpowiedź zmienia treść kolejnego pytania, pytaj pojedynczo.
Poczekaj na moje odpowiedzi przed zależnymi decyzjami. Nie zapisuj jeszcze plików.
```

Formularz `request_user_input` w Plan zatrzymuje dalsze wykonanie do otrzymania odpowiedzi. Jego instrukcje przewidują do trzech pytań w jednym wywołaniu. Przycisk Other pozwala podać własną odpowiedź.

Skille kursowe `write-prd` i `write-adr` wymagają co najmniej pięciu pytań i odpowiedzi przed napisaniem dokumentu. Możesz zebrać je w dwóch rundach, np. 3+2. To wymaganie tych skilli, a nie ogólna zasada Codex.

## 2. Odróżniaj pytanie wymagane od opcjonalnego

**Wymagane:** bez odpowiedzi nie można wykonać następnego zależnego kroku, np. wybrać zakresu MVP. Zbierz odpowiedź w Plan albo przez zwykłą rozmowę.

**Opcjonalne:** odpowiedź pomaga, ale agent może w tym czasie wykonywać niezależną pracę, np. sprawdzać repozytorium. Tak działa formularz `request_user_input_async`, gdy jest dostępny. Jego schemat i limity różnią się od zwykłego formularza; nie przenoś na niego automatycznie limitu trzech pytań.

`accepted:true` oznacza przyjęcie pytania przez narzędzie. **Nie oznacza Twojej odpowiedzi ani zgody na działanie.** Zaznaczona domyślnie rekomendacja, cisza i upływ czasu również nie są Twoją decyzją.

## 3. Obsługa panelu async w terminalu

| Działanie | Domyślny skrót |
|---|---|
| Otwórz panel przy `? N questions`; przejdź dalej między pytaniami | Shift+Left; alternatywnie Alt+Up |
| Wróć; przy pierwszym pytaniu zwiń panel | Shift+Right; alternatywnie Alt+Down |
| Wybierz odpowiedź | Strzałki Up/Down |
| Wyślij bieżącą odpowiedź | Enter |
| Własna odpowiedź | Other albo rozpocznij pisanie, potem Enter |
| Pomiń pytanie | Ctrl+] - pominięcie nie jest odpowiedzią |

Numer nazwanej opcji może **od razu wysłać odpowiedź**. Najpierw przeczytaj wybór. Panel async wysyła odpowiedzi osobno; zwykły formularz z kilkoma pytaniami przechodzi przez pytania i wysyła komplet na końcu. Patrz na podpowiedzi klawiszy w swoim interfejsie.

Nie traktuj Esc jako uniwersalnego "wstecz": jego działanie zależy od fokusu i klienta. W desktopie zgłoszono przypadek utraty niewysłanej odpowiedzi po Esc.

## 4. Gdy formularz znika

Kontrolki async mogą zamknąć się po zakończeniu tury agenta. To opisane ograniczenie cyklu życia formularza. Podobne objawy podczas pracy z Goal opisano w zgłoszeniu obejmującym 0.166.0. Komentarze OpenAI i ślad tej wersji wskazują również na możliwe granice tur; nie potwierdzono oddzielnego błędu wywołanego zdarzeniem wewnątrz jednej tury.

Jeśli pytanie nadal jest dostępne, spróbuj Shift+Left. Jeśli nie możesz odpowiedzieć w panelu, wyślij zwykłą wiadomość:

```text
Odpowiedź na pytanie o zakres MVP: aplikacja tylko dla jednego zespołu.
To moja decyzja. Poczekaj z PRD, aż odpowiem na pozostałe wymagane pytania.
Jeśli potrzebujesz kolejnej wymaganej decyzji, zadaj jedno pytanie zwykłym tekstem
i zakończ turę, żebym mógł odpowiedzieć.
```

Powtórzenie formularza i natychmiastowe zakończenie tury może ponownie ukryć kontrolki. Polecenie "poczekaj 60 sekund" nie naprawia błędu interfejsu. Licznik na panelu async nie jest dowodem automatycznej akceptacji wyboru.

## 5. Po odpowiedziach zapisz dokument

Poproś o krótką listę potwierdzonych decyzji. Następnie przełącz Plan na Default - w TUI służy do tego Shift+Tab; sprawdź oznaczenie trybu - i poproś o zapis PRD lub ADR.

Plan służy analizie i planowaniu; jego instrukcje zabraniają zapisywania plików. Samo zdanie "teraz napisz plik" nie przełącza trybu.

## Opcjonalny fragment do AGENTS.md na czas ćwiczenia

```markdown
## Pytania podczas tego ćwiczenia
- Najpierw sprawdź opis i istotne pliki; nie powtarzaj pytań z udzieloną odpowiedzią.
- Wymagane decyzje do PRD/ADR zbierz przed napisaniem dokumentu.
- W Plan używaj request_user_input, jeśli jest dostępny. Grupuj 2-3 niezależne pytania, gdy narzędzie to obsługuje; pytaj pojedynczo, gdy odpowiedź zmienia kolejne pytanie. Przestrzegaj aktualnego schematu narzędzia.
- W Default pytania opcjonalne mogą towarzyszyć niezależnej pracy. Jeśli decyzja jest wymagana albo formularz nie działa, zadaj jedno krótkie pytanie zwykłym tekstem i zakończ turę. Zaczekaj na moją odpowiedź przed zależną pracą.
- accepted:true, domyślny wybór, brak odpowiedzi i upływ czasu nie są moją decyzją ani zgodą.
- Zachowaj wymaganą przez wybrany skill liczbę pytań; przed pisaniem podsumuj ustalenia.
```

Po dodaniu fragmentu rozpocznij nową sesję, aby upewnić się, że instrukcje zostały wczytane. Po ćwiczeniu usuń reguły, których nie chcesz zachować.

Ten fragment pomaga wybrać sposób rozmowy. Nie dodaje brakujących narzędzi i nie naprawia interfejsu.

## Co sprawdzono w instrukcjach skilli

W aktualnie używanych `write-prd` (sekcja Step 3) i `write-adr` (Step 2) jest wymóg co najmniej pięciu pytań i oczekiwania na odpowiedzi. Nie ma jawnego wskazania `request_user_input`, `request_user_input_async`, timerów ani grupowania. Sam wybór skilla nie wymusza więc konkretnego formularza. Audyt objął identyczne kopie zainstalowane i źródłowe.

Źródła skilli: [write-prd](https://github.com/EdukeyTeam/agent-toolbox/blob/main/skills/write-prd/SKILL.md), [write-adr](https://github.com/EdukeyTeam/agent-toolbox/blob/main/skills/write-adr/SKILL.md).

## Timery: dwa różne zachowania w 0.166.0

- `request_user_input` w Default, jeśli klient udostępnia je m.in. przez flagę `default_mode_request_user_input`, jest nieblokujący. Nakładka ma 60 sekund niewidocznego czasu i 60 sekund odliczania; po tym zwraca pusty zestaw odpowiedzi, a nie rekomendowaną opcję. Interakcja wstrzymuje automatyczne zamknięcie. W Plan ten mechanizm jest wyłączony.
- Panel `request_user_input_async` ma osobny licznik prezentacji. W zbadanym kodzie upływ jego 30 sekund nie wysyła odpowiedzi i nie usuwa pytań. Nie należy mylić go z timerem poprzedniej nakładki.
- Instrukcja "bez timerów" nie zmienia kodu klienta. Dla wymaganej decyzji wybierz blokujący tryb Plan albo zwykłą rozmowę z zakończeniem tury i oczekiwaniem na odpowiedź.

Źródła wydania: [nakładka pytań](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/tui/src/bottom_pane/request_user_input/mod.rs#L264), [stan panelu async](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/tui/src/bottom_pane/async_questions/state.rs#L14). Zachowanie desktopu wymaga oddzielnej weryfikacji wersji.

## Źródła

Oficjalna dokumentacja komend, w tym `/plan`
https://learn.chatgpt.com/docs/developer-commands?surface=cli

Cykl życia pytań async - wyjaśnienie współtwórcy OpenAI w #49146, 1 października 2026
https://github.com/openai/codex/issues/49146

Znikające kontrolki podczas aktywnej pracy w TUI - zgłoszenie #54136
https://github.com/openai/codex/issues/54136

Zgłoszenie utraty odpowiedzi po Esc w aplikacji desktopowej, bez ustalonego numeru wersji aplikacji
https://github.com/openai/codex/issues/58997

Kod formularza synchronicznego w wydaniu 0.166.0
https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/core/src/tools/handlers/request_user_input_spec.rs

Kod formularza async w wydaniu 0.166.0
https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/core/src/tools/handlers/request_user_input_async.rs

Skróty panelu async w wydaniu 0.166.0
https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/tui/src/keymap.rs#L1724

Sprawdzone 5 listopada 2026: dokumentacja i kod wydania. Zgłoszenia użytkowników potwierdzają raportowane objawy; nie przeprowadzono niezależnego odtworzenia błędu na żywym formularzu.
