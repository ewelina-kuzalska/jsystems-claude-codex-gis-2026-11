> **Windows, Codex CLI 0.166.0, pomiary 5-6.11.2026:** opcjonalny profil course-tools zachowuje sandbox zwykłych poleceń i zgody on-request, ale nie blokuje odczytu .env/secrets na poziomie systemu. Dotychczasowy profil projektu to course-root. Zanim wybierzesz course-tools do danych syntetycznych, przeczytaj [instrukcję Windows](../agent-configs/codex/WINDOWS-QUICKSTART-PL.md) i [wyniki pomiarów](../Research/codex-windows-sandbox-compatibility-2026-11-05.md).

# Sandbox Safety Mini-Module

## Bezpieczeństwo pracy z agentami

Sprawdź cztery elementy środowiska:
1. sandbox vs brak sandboxa,
2. dlaczego **WSL ≠ izolacja**,
3. różnice zachowania agenta w bash vs PowerShell,
4. bezpieczne ustawienia domyślne do codziennej pracy.

---

## 1) Sandbox vs no-sandbox - szybkie porównanie

### Sandbox (zalecany start)
- Agent działa w ograniczonym środowisku (kontrola dostępu do systemu/plików/sieci).
- Łatwiej ograniczyć "blast radius" błędnej komendy.
- Lepszy tryb do nauki, eksperymentów i pracy na niepewnym kodzie.

### No-sandbox (tylko świadomie)
- Agent może dotknąć więcej zasobów hosta.
- Szybciej "działa", ale rośnie ryzyko nieodwracalnych zmian.
- Wymaga dojrzałych guardrails (approvals, branch policy, backup, review discipline).

### Co to oznacza
> "Sandbox nie jest o spowalnianiu. Jest o tym, żeby błąd był mały i odwracalny."

---

## 2) WSL != izolacja

WSL to **środowisko uruchomieniowe** Linux na Windows, a nie pełna granica bezpieczeństwa.

- WSL poprawia zgodność narzędzi CLI i developer UX.
- Sam fakt "pracuję w WSL" nie oznacza automatycznie izolacji od hosta.
- Izolację daje dopiero konkretny sandbox/policy/permission model.

### Co to oznacza
> "WSL pomaga narzędziom działać, ale nie jest automatycznym sejfem. Sejfem są dopiero ograniczenia i approvale."

---

## 3) bash vs PowerShell - co praktycznie zmienia dla agentów

## Bash
- Często lepiej opisane ścieżki dla narzędzi open-source i skryptów dev.
- Spójniejsze zachowanie wielu przykładów z dokumentacji narzędzi AI/CLI.
- Wymaga uwagi na quoting i operatory powłoki.

## PowerShell
- Bardzo dobry w ekosystemie Windows/.NET i automatyzacji administracyjnej.
- Inna składnia, quoting i pipeline niż w bash (częsty punkt potknięć przy kopiowaniu komend 1:1).
- Agent musi dostać jasny kontekst, że komendy mają być generowane pod PowerShell.

### Wybór powłoki
- Nie ma "jedynej słusznej" powłoki.
- Na VM używaj PowerShell do natywnych sesji Windows; przykłady Bash uruchamiaj w odpowiednim środowisku Linux/WSL. Sprawdź składnię przed przeniesieniem polecenia między powłokami.

---

## 4) Safe defaults - checklista na start zespołu

1. **Dedykowane repo/branch na ćwiczenie** (bez pracy na produkcyjnym main).
2. **Sandbox ON** jako domyślny tryb startowy.
3. **Approvals ON** dla działań potencjalnie ryzykownych.
4. **Małe taski** (jeden cel, mały diff, krótka pętla feedbacku).
5. **Review każdego diffu** przed kolejnym krokiem.
6. **Celowany test/lint** po zmianie (nie wszystko naraz).
7. **Commit po małym kroku** z jasnym opisem decyzji.
8. **Zero sekretów w promptach** i outputach.

### Zasady do instrukcji projektu
```text
Bezpieczny start z agentem:
- pracujemy na dedykowanym branchu,
- sandbox + approvals są domyślnie włączone,
- zadania dzielimy na małe kroki,
- każdy diff czytamy przed testem/commitem,
- AI daje draft, człowiek podejmuje decyzję.
```

---

## 5) Typowe antywzorce
- "WSL mam, więc jestem bezpieczny".
- "Agent zrobił szybko, to merge bez czytania diffu".
- "Wrzucam duży prompt i liczę, że jakoś wyjdzie".
- "Najpierw wygoda, potem bezpieczeństwo".

---

## 6) Połączenie z resztą kursu
- Start pracy: ustawienie bezpiecznych nawyków.
- Implementacja i debugowanie: utrzymanie guardrails.
- Weryfikacja: quality/security review jako domknięcie procesu.
