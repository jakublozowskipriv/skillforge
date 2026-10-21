# CLAUDE.md — konwencje projektu skillforge

Lokalna aplikacja do nauki AE + AI dla analityki. Opis i architektura: `README.md`.
Decyzje: `DECISIONS.md` (jedna linijka na decyzję). Pomysły spoza zakresu: `ROADMAP.md`.

## Zasady nadrzędne

- **Zero LLM w runtime aplikacji.** Tutorem jest Claude Code przez `.claude/commands/`;
  aplikacja tylko wyświetla, sprawdza i śledzi postęp. Nie dodawaj wywołań API modeli do `src/`.
- **Repo jest publiczne.** Nigdy nie commituj `docs/brief.md`, `profile.yaml`, niczego z `var/`
  ani `build/`, danych firmowych ani osobistych. Treści w `content/` muszą być ogólne i oparte
  na syntetycznym datasecie. Z briefu bierz tylko tematy, nigdy nazwy firm, osób czy wartości KPI.
- Treści po polsku; kod, identyfikatory i terminy techniczne po angielsku.
- Decyzje niezmieniające architektury → jedna linijka w `DECISIONS.md`. Zmiany architektury
  lub zakresu → zapytaj użytkownika. Pomysły spoza zakresu → `ROADMAP.md`, nie kod.
- Miejsca `TODO(learn)` pisze użytkownik — nie implementuj ich, chyba że wprost poprosi.
  Po jego implementacji: przejrzyj kod, odpowiedz na pytania z komentarzy, zdejmij `xfail`
  w `tests/test_partial_score.py` / `enabled=false` w dbt, jeśli to on o to poprosi.

## Środowisko użytkownika

- Użytkownik pracuje na **Windows w PowerShell 5.1**: komendy, które mu podajesz, pisz po jednej
  w linii (bez `&&`), używaj `Copy-Item`/`Remove-Item` zamiast `cp`/`rm`.
- Kod musi działać na Windows i Linux (CI testuje oba): `pathlib`, `encoding="utf-8"` przy każdym
  odczycie/zapisie tekstu, konsolowe skrypty z venv przez `skillforge.venv.executable()`.

## Struktura

| Ścieżka | Co tam jest |
|---|---|
| `src/skillforge/data/` | generator datasetu (`generate.py`, deterministyczny; nowe losowania dodawaj **na końcu**) i build hurtowni (`build.py` → dbt) |
| `dbt/` | projekt dbt-duckdb; schematy `raw`, `staging`, `intermediate`, `marts` |
| `src/skillforge/evaluator/` | golden set evaluator — publiczne API w `__init__.py` |
| `src/skillforge/content/` | modele pydantic treści, loader (`ContentIndex`), snapshot, walidacja |
| `src/skillforge/progress/` | log zdarzeń: `events.py` (typy), `store.py` (`EventStore`), `projections.py` (czyste funkcje), `service.py` (`Progress` — jedyne API dla UI/CLI), `export.py` |
| `src/skillforge/srs.py` | FSRS jako fold zdarzeń `card.reviewed` (bez fuzzingu) |
| `src/skillforge/ui/` | Streamlit: `app.py`, `nav.py`, `state.py`, `pages/*` |
| `src/skillforge/site/` + `site/` | strona offline (MkDocs Material, service worker) |
| `content/` | `tree.yaml` + `paths/<ścieżka>/{lessons,exercises,cards}` |

Postęp **zawsze** jako nowe zdarzenie (append-only) — nigdy UPDATE/DELETE. Edycja/usunięcie
= nowe zdarzenie (np. `brag.retracted`), stan liczą projekcje.

## Format treści

Prefiksy id: `ai-engineering` → `ai`, `analytics-engineering` → `ae`, `business-thinking` → `bt`,
`statistics` → `st`, `forecasting-ml` → `fm`. Lekcje `<p>-NN`, ćwiczenia `<p>-ex-NN`,
fiszki `<p>-c-NN`. Nazwa pliku = id. Tematy (`topic`) muszą istnieć w `content/tree.yaml`.

**Lekcja** `content/paths/<ścieżka>/lessons/<id>.md` — frontmatter YAML (`id`, `path`, `topic`,
`title`, `minutes` 5–30, `order`, `exercises`), potem Markdown zaczynający się od `# Tytuł`.
Obowiązkowo sekcja `## Jak zastosować w pracy`.

**Ćwiczenie** `content/paths/<ścieżka>/exercises/<id>.yaml`:

```yaml
id: ae-ex-NN
title: ...
kind: sql            # albo python
lesson: ae-NN
topic: ae.xxx
difficulty: 1        # 1–3
question: |          # Markdown; tabela oczekiwanych kolumn; bez wymagania zaokrągleń
hints: [...]         # 2–3, stopniowane
reference: |         # rozwiązanie referencyjne
compare: {}          # opcjonalnie: order_matters, match_columns, rel_tol, abs_tol
negatives: [...]     # ≥ 1 typowa błędna odpowiedź, która MUSI oblać
# tylko python:
function: nazwa_funkcji
starter: |
tests: [{name, args, kwargs, expected}]
```

SQL: obok powstaje `<id>.expected.json` (snapshot) — generowany komendą, nie ręcznie.

**Fiszki** `content/paths/<ścieżka>/cards/<p>-cards.yaml` → `cards: [{id, topic, lesson, front, back, tags}]`.
`front` z dwukropkiem lub backtickami bierz w cudzysłów.

## Jak dodać ćwiczenie

1. `uv run skillforge data schema` — sprawdź dostępne tabele.
2. Napisz YAML wg formatu wyżej (najpierw zapytanie referencyjne, potem pytanie, które jednoznacznie
   je opisuje, potem negatywne kontrolki).
3. `uv run skillforge content snapshot <id>` → przejrzyj `<id>.expected.json` (niepusty, ≤ ~50 wierszy).
4. `uv run skillforge content validate` — referencja zgodna ze snapshotem, każda negatywna
   kontrolka oblewa. Jeśli kontrolka przechodzi, zmień pytanie/zakres albo dane (generator).
5. Dopisz id do `exercises:` w lekcji.

Zmiana generatora danych zmienia snapshoty: po `uv run skillforge data build` uruchom
`content validate`, a świadome zmiany zaktualizuj `content snapshot` i opisz w commicie.

## Komendy

```bash
uv sync                                  # instalacja (grupy dev + site)
uv run skillforge data build             # dataset + dbt build
uv run skillforge content validate       # treści + golden set
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
uv run skillforge site build             # strona offline (strict)
uv run streamlit run app.py              # aplikacja
```

Testy nie mogą dotykać `var/progress.db` ani `profile.yaml` (fixture `isolated_progress`
w `tests/conftest.py`). Testy wymagające hurtowni oznaczaj `@pytest.mark.integration` i używaj
fixture `warehouse` (mała hurtownia, scale 0.05).

## Komendy tutora

`/next-lesson`, `/review <id>`, `/quiz <temat>`, `/weekly-review` — definicje w `.claude/commands/`.
Komunikują się z danymi wyłącznie przez CLI `skillforge` (`progress export|summary|attempts|record-quiz`,
`check`, `data schema`, `content snapshot|validate`).
