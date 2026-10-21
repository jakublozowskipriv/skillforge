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

## Nauka na telefonie

### 1. Lekcje offline — GitHub Pages (komputer może być wyłączony)

Lekcje, zadania (z podpowiedziami i rozwiązaniami w rozwijanych blokach) i fiszki do
przeglądania są publikowane jako statyczna strona: **https://jakublozowskipriv.github.io/skillforge/**

- Otwórz ją raz na telefonie i wybierz *Dodaj do ekranu głównego* — service worker zapisze całą
  stronę, więc potem działa **bez internetu**. Po każdej zmianie treści (push na `main`)
  telefon pobierze nową wersję przy najbliższej wizycie online.
- Na stronę trafia wyłącznie `content/` — nigdy postęp, profil ani brief.
- Jednorazowo w repo: *Settings → Pages → Source = GitHub Actions* (deploy robi
  `.github/workflows/pages.yml`).
- Lokalny podgląd: `uv run skillforge site build --serve` → http://127.0.0.1:8000/skillforge/

### 2. Pełna aplikacja z telefonu — Tailscale (komputer włączony)

[Tailscale](https://tailscale.com/download) tworzy prywatną sieć między Twoimi urządzeniami —
aplikacja nie jest wystawiona do internetu. Zainstaluj Tailscale na komputerze i telefonie
i zaloguj się na to samo konto.

**Wariant zalecany — `tailscale serve` (HTTPS, bez zmian w firewallu):**

```powershell
uv run skillforge serve                 # aplikacja na localhost:8501
tailscale serve --bg 8501               # w drugim terminalu, jednorazowo
```

Na telefonie otwórz adres pokazany przez `tailscale serve status`
(`https://<nazwa-komputera>.<tailnet>.ts.net`). Wyłączenie: `tailscale serve --https=443 off`.

**Wariant prosty — nasłuch w sieci lokalnej:**

```powershell
uv run skillforge serve --lan           # wypisze adresy, np. http://100.x.y.z:8501
```

Na telefonie otwórz `http://<adres-tailscale-komputera>:8501` (adres 100.x.y.z z aplikacji
Tailscale). Windows zapyta o firewall — zezwól tylko dla sieci prywatnych. Aplikacja nie ma
logowania, więc `--lan` uruchamiaj tylko w zaufanej sieci.

## Przydatne komendy

| Komenda | Co robi |
|---|---|
| `uv run skillforge data build` | generuje syntetyczny dataset i buduje hurtownię dbt (z testami) |
| `uv run skillforge content validate` | sprawdza treści i czy rozwiązania referencyjne odtwarzają zamrożone wyniki |
| `uv run skillforge progress export` | zapisuje postęp do `var/progress.json` (czyta go tutor) |
| `uv run skillforge progress brag --out brag.md` | eksport brag doca do Markdown |
| `uv run skillforge site build` | buduje statyczną stronę lekcji (offline) do `build/site` |
| `uv run skillforge serve --lan` | aplikacja dostępna z innych urządzeń (np. telefon przez Tailscale) |
| `uv run pytest` | testy |
