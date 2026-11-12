> **Stan na 5.11.2026:** WezTerm nie był zainstalowany/wykryty w środowisku pomiarowym (wezterm nie występował na PATH). Nie wykonano porównania stabilności ani testu konfiguracji Lua. Terminal emulator nie wybiera sandboxa Codex i nie naprawi logowania gh, IPC Chrome ani uprawnień executora. Traktuj poniższe różnice ergonomii jako hipotezy do osobnego sprawdzenia; Windows Terminal/PowerShell wystarcza do kursu.

# WezTerm mini-module

## Ergonomia terminala
Sprawdź, **dlaczego i kiedy** WezTerm może być wygodniejszy od Windows Terminal w workflow z agentami (Claude Code/Codex), bez robienia z tego osobnej ścieżki narzędziowej.

## Kiedy go wypróbować
- **Ergonomia terminala**: codzienny rytm pracy.
- **Porównanie narzędzi**: szybkie przypomnienie podczas pracy z TUI/debug.

## 5-min porównanie: WezTerm vs Windows Terminal

### WezTerm - co zwykle pomaga w pracy agentowej
1. **Możliwa korzyść ergonomiczna:** splity, przewijanie i rendering przy długich sesjach CLI (nieporównane w tym środowisku).
2. **Lepsza konfigurowalność skrótów i layoutów** pod szybkie przełączanie: kod / test / logi / agent.
3. **Powiadomienia i sygnały dźwiękowe** (np. koniec dłuższego polecenia, potrzeba uwagi).
4. **Spójność cross-platform** (Windows/macOS/Linux) - łatwiej odtworzyć workflow na różnych maszynach.

### Windows Terminal - kiedy jest OK
- Dla prostego, lokalnego workflow bez wielu splitów i bez długich sesji TUI.
- Gdy zespół chce minimalny setup i brak dodatkowych instalacji.

## Dopasuj terminal do swojej pracy
- Wybierz terminal, który działa stabilnie w Twoim środowisku.
- Zmieniaj narzędzie, gdy rozwiązuje konkretny problem z pracą.
- Możesz pozostać przy obecnym terminalu i wykonać te same ćwiczenia.

## Wybór terminala
`WezTerm jest opcjonalnym terminalem. W tym kursie nie potwierdziliśmy jego przewagi ani wpływu na sandbox. Użyj terminala dostępnego na VM; sprawdź WezTerm osobno, jeśli zależy Ci na jego ergonomii.`

## Mikro-checklista dla uczestnika
- Czy obecny terminal gubi mnie przy dłuższych sesjach agenta?
- Czy brakuje mi wygodnych splitów i szybkich skrótów?
- Czy potrzebuję powiadomień o zakończeniu długich komend?
- Jeśli 2+ odpowiedzi to "tak" -> warto przetestować WezTerm po zajęciach.
