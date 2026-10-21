# CLAUDE.md — konwencje projektu skillforge

> Wersja robocza (krok 1 MVP). Pełna wersja powstaje w kroku 11.

## Zasady nadrzędne
- **Zero LLM w runtime aplikacji.** Tutorem jest Claude Code przez `.claude/commands/`; aplikacja tylko wyświetla, sprawdza i śledzi postęp.
- **Repo publiczne.** Nigdy nie commituj `docs/brief.md`, `profile.yaml`, niczego z `var/`, danych firmowych ani osobistych. Treści w `content/` muszą być ogólne (dataset syntetyczny).
- Treści po polsku; kod, identyfikatory i terminy techniczne po angielsku.
- Decyzje nie zmieniające architektury → jedna linijka w `DECISIONS.md`. Pomysły spoza MVP → `ROADMAP.md`.
- Miejsca `TODO(learn)` pisze użytkownik — nie implementuj ich, chyba że wprost poprosi.

## Komendy
```bash
uv sync                      # instalacja
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
```
