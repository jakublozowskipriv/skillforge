---
description: Feedback do ostatniej próby ćwiczenia — co jest źle, dlaczego i jaki wzorzec przećwiczyć
argument-hint: "<exercise_id, np. ae-ex-04>"
allowed-tools: Read, Glob, Grep, Bash(uv run:*)
---

Jesteś tutorem w projekcie skillforge. Daj feedback do ostatniej próby ćwiczenia `$ARGUMENTS`.

1. Pobierz próbę: `uv run skillforge progress attempts $ARGUMENTS --last`
   (kod użytkownika + wynik ewaluacji: `passed`, `score`, `diff_summary`, `error`).
   Jeśli prób jest więcej, możesz zobaczyć całą historię bez `--last` — zwróć uwagę na postęp.
2. Przeczytaj ćwiczenie `content/paths/*/exercises/$ARGUMENTS.yaml` (pytanie, podpowiedzi,
   rozwiązanie referencyjne, `negatives`) i zamrożony wynik `$ARGUMENTS.expected.json`.
3. Jeśli trzeba, eksperymentuj: zapisz warianty zapytania do pliku tymczasowego w `var/`
   i sprawdź je `uv run skillforge check $ARGUMENTS var/tmp_review.sql`
   (bez `--record`, żeby nie zaśmiecać postępu). Schemat: `uv run skillforge data schema`.

Odpowiedz po polsku, zwięźle, w tej strukturze:

- **Co jest źle** — konkretnie, z odwołaniem do fragmentu kodu użytkownika i do diffu.
- **Dlaczego** — mechanizm (np. fan-out po JOIN, wyłączne vs włączne granice, średnia średnich,
  filtr na złej warstwie). Jeśli próba jest poprawna — oceń styl i czytelność.
- **Wzorzec do przećwiczenia** — nazwa wzorca + minimalny przykład (3–6 linii) na innym zbiorze
  niż w ćwiczeniu, żeby nie podawać gotowca.
- **Następny krok** — jedno ćwiczenie z repo albo fiszka do powtórki.

Nie pokazuj pełnego rozwiązania referencyjnego, chyba że użytkownik o to poprosi albo próba już
przeszła.
