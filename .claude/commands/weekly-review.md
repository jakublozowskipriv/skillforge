---
description: Piątkowy przegląd tygodnia — postęp, KPI, szkic wpisu do brag doca, plan na kolejny tydzień
allowed-tools: Read, Write, Glob, Grep, Bash(uv run skillforge:*)
---

Przygotuj przegląd tygodnia (zgodnie z rytmem: piątek, ~10 minut czytania).

1. `uv run skillforge progress export` i przeczytaj `var/progress.json`: zdarzenia z ostatnich
   7 dni (`events` — sesje, próby ćwiczeń, powtórki fiszek, quizy, wpisy brag, KPI) i `summary`.
2. Przeczytaj `profile.yaml` (lub `profile.example.yaml`): rytm, KPI i cele z terminami,
   `light_months` (w luźniejszym miesiącu nie wywieraj presji).
3. Napisz po polsku raport w Markdown:
   - **Tydzień w liczbach** — sesje vs rytm (który slot zrobiony), minuty, ćwiczenia
     (rozwiązane / próby), fiszki powtórzone, quizy.
   - **Co poszło dobrze / co utknęło** — konkretnie, na podstawie danych (np. ćwiczenie z wieloma
     próbami).
   - **KPI** — wartość, cel i termin, tempo („przy tym tempie cel 03.2027 jest/nie jest realny”).
     Jeśli KPI nie był aktualizowany od >14 dni, przypomnij o aktualizacji na Dashboardzie.
   - **Szkic wpisu do brag doca** w formacie: data · kontekst · moja rola · efekt (liczba) ·
     dowód (link) — oparty o to, co zastosowano w pracy (zapytaj, jeśli brak danych; nie
     wymyślaj liczb). Użytkownik dodaje wpis w aplikacji (Dziennik → Brag doc).
   - **Plan na kolejny tydzień** wg rytmu: wtorek (teoria: która lekcja), weekend (praktyka:
     które ćwiczenia), piątek (przegląd) + jedno działanie „zastosuj w pracy”.
4. Zapisz raport do `var/reviews/<RRRR>-W<tydzień ISO>.md` (prywatne, gitignored) i pokaż go
   użytkownikowi. Niczego nie commituj.
