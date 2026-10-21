---
description: Wybierz kolejny temat, wygeneruj lekcję + 3–5 ćwiczeń + 5 fiszek, zwaliduj i zacommituj
argument-hint: "[opcjonalnie: id tematu, np. ai.llm-evals]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(uv run:*), Bash(git status:*), Bash(git diff:*), Bash(git add:*), Bash(git commit:*), Bash(git log:*)
---

Jesteś tutorem w projekcie skillforge. Twoim zadaniem jest przygotować **jedną** kolejną lekcję
z kompletem ćwiczeń i fiszek, zwalidować ją i zacommitować. Najpierw przeczytaj `CLAUDE.md`
(konwencje, format treści, prywatność) — obowiązuje bez wyjątków.

## 1. Zbierz kontekst

1. Profil ucznia: `docs/brief.md` (jeśli nie istnieje — `docs/brief.example.md`) oraz
   `profile.yaml` (jeśli nie istnieje — `profile.example.yaml`): priorytety ścieżek
   (`path_priority`), rytm, KPI.
2. Postęp: uruchom `uv run skillforge progress export`, potem przeczytaj `var/progress.json`
   → `summary`: `levels` (0–3 per temat), `weak_exercises`, `quizzes`, ostatnie sesje.
3. Program: `content/tree.yaml` oraz istniejące lekcje, ćwiczenia i fiszki
   (`content/paths/*/lessons|exercises|cards`). Zanotuj ostatnie numery id w każdej ścieżce.
4. Dane do ćwiczeń: `uv run skillforge data schema` (jeśli brak hurtowni:
   `uv run skillforge data build`).

## 2. Wybierz temat

Jeśli podano argument (`$ARGUMENTS`) — użyj tego tematu. W przeciwnym razie:

- idź po ścieżkach w kolejności `path_priority`; ścieżki `optional: true` pomijaj, dopóki
  wcześniejsze nie mają lekcji dla każdego tematu,
- w ścieżce wybierz temat z **najniższym poziomem**, a przy remisie — z najmniejszą liczbą lekcji;
  tematy ze słabymi wynikami (`weak_exercises`, quiz < 60%) mają pierwszeństwo, ale nie generuj
  dwóch lekcji z rzędu o tym samym temacie,
- zasada z briefu: maks. jedna **nowa technologia** na kwartał — preferuj tematy, które budują
  na znanym stacku (SQL, Python, DuckDB, dbt z tego repo).

W 2–3 zdaniach napisz użytkownikowi, co wybrałeś i dlaczego (z odwołaniem do priorytetu/poziomu).

## 3. Wygeneruj treści

Prefiksy id per ścieżka: `ai-engineering` → `ai`, `analytics-engineering` → `ae`,
`business-thinking` → `bt`, `statistics` → `st`, `forecasting-ml` → `fm`.
Numeruj dalej od ostatniego istniejącego (dwie cyfry).

**Lekcja** `content/paths/<ścieżka>/lessons/<prefix>-NN.md`:
- frontmatter: `id`, `path`, `topic`, `title`, `minutes` (15–20), `order`, `exercises: [...]`,
- po polsku, kod i terminy po angielsku; 15–20 min czytania; przykłady na **syntetycznym
  datasecie logistycznym** z tego repo (tabele z `data schema`),
- obowiązkowa sekcja `## Jak zastosować w pracy` z 2–4 konkretnymi działaniami na najbliższy
  tydzień — bez nazw firm, systemów, osób i danych z briefu.

**3–5 ćwiczeń** `content/paths/<ścieżka>/exercises/<prefix>-ex-NN.yaml` (format jak
`content/paths/analytics-engineering/exercises/ae-ex-04.yaml` i `ae-ex-07.yaml`):
- SQL na hurtowni (`marts` / `staging` / `raw`) albo Python (funkcja + `tests` z `expected`),
- pytanie z tabelą oczekiwanych kolumn; nie wymagaj zaokrąglania (porównanie ma tolerancję),
- 2–3 stopniowane `hints` (nie zdradzaj rozwiązania w pierwszej),
- `reference` — rozwiązanie referencyjne,
- **co najmniej jedna `negatives`** — typowy błąd, który MUSI oblać (np. fan-out, zła
  granica okresu, średnia średnich). Jeśli przechodzi, zmień pytanie lub zakres danych,
- wynik referencji: niepusty i czytelny (najlepiej ≤ 50 wierszy).

**5 fiszek** dopisz do `content/paths/<ścieżka>/cards/<prefix>-cards.yaml` (utwórz plik, jeśli
nie istnieje, z kluczem `cards:`), z polami `id`, `topic`, `lesson`, `front`, `back`.
Teksty z dwukropkiem lub backtickami w `front` bierz w cudzysłów.

Jeśli temat nie istnieje w `content/tree.yaml` — nie dodawaj go bez pytania użytkownika.

## 4. Zwaliduj (pętla aż do zielonego)

```
uv run skillforge content snapshot <id ćwiczeń SQL>
uv run skillforge content validate
uv run pytest -q
uv run ruff check .
```

- Przejrzyj każdy `*.expected.json`: czy liczby są sensowne, czy wynik nie jest pusty.
- Dla każdego ćwiczenia sprawdź też ręcznie jedną błędną odpowiedź:
  `uv run skillforge check <id> <plik>` musi zwrócić FAIL.
- Prywatność: upewnij się, że w nowych plikach nie ma niczego z `docs/brief.md` poza ogólnymi
  tematami (żadnych nazw firm, ludzi, wartości KPI).

## 5. Commit

```
git add content/
git commit -m "Add lesson <id>: <tytuł>"
```

Tylko pliki z `content/`. Nie pushuj, chyba że użytkownik poprosi.

## 6. Podsumowanie dla użytkownika

Krótko: wybrany temat i dlaczego, lista ćwiczeń (id · tytuł · trudność), liczba fiszek, oraz jak
zacząć — w składni **PowerShell** (osobne linie, bez `&&`):

```
uv run streamlit run app.py
```

i że lekcja pojawi się też na stronie offline po pushu na `main`.
