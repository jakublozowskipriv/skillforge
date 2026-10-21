# skillforge

Lokalna aplikacja do nauki **Analytics Engineering + AI dla analityki**: lekcje, ćwiczenia SQL/Python
sprawdzane automatycznie (golden set evaluator), fiszki z powtórkami FSRS i śledzenie postępu.
Zero LLM w runtime — rolę tutora pełni Claude Code przez komendy w `.claude/commands/`.

> README w budowie — pełna wersja (architektura, golden set evaluator, zrzuty ekranu) powstaje
> w ostatnim kroku MVP. Postęp prac: [`ROADMAP.md`](ROADMAP.md), decyzje: [`DECISIONS.md`](DECISIONS.md).

## Szybki start

Wymagania: [uv](https://docs.astral.sh/uv/) (instaluje też Pythona 3.12) i git.

**Windows (PowerShell)** — komendy po jednej w linii (PowerShell 5.1 nie obsługuje `&&`):

```powershell
winget install astral-sh.uv          # jednorazowo; potem otwórz nowy terminal
git clone https://github.com/jakublozowskipriv/skillforge.git
cd skillforge
uv sync
uv run skillforge data build         # dataset + dbt build (ok. 10 s)
Copy-Item profile.example.yaml profile.yaml   # jednorazowo; wpisz swój rytm i KPI
uv run streamlit run app.py
```

**Linux / macOS (bash/zsh)**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # jednorazowo
git clone https://github.com/jakublozowskipriv/skillforge.git && cd skillforge
uv sync
uv run skillforge data build
cp profile.example.yaml profile.yaml
uv run streamlit run app.py
```

Aplikacja startuje pod http://localhost:8501. Twoje dane (postęp, KPI, brag doc) zapisują się
w `var/progress.db`, a profil w `profile.yaml` — oba są w `.gitignore` i nie trafiają do repo.

## Przydatne komendy

| Komenda | Co robi |
|---|---|
| `uv run skillforge data build` | generuje syntetyczny dataset i buduje hurtownię dbt (z testami) |
| `uv run skillforge content validate` | sprawdza treści i czy rozwiązania referencyjne odtwarzają zamrożone wyniki |
| `uv run skillforge progress export` | zapisuje postęp do `var/progress.json` (czyta go tutor) |
| `uv run skillforge progress brag --out brag.md` | eksport brag doca do Markdown |
| `uv run pytest` | testy |
