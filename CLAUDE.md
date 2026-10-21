# CLAUDE.md — konwencje projektu skillforge

> Wersja robocza (krok 1 MVP). Pełna wersja powstaje w kroku 11.

## Zasady nadrzędne
- **Zero LLM w runtime aplikacji.** Tutorem jest Claude Code przez `.claude/commands/`; aplikacja tylko wyświetla, sprawdza i śledzi postęp.
- **Repo publiczne.** Nigdy nie commituj `docs/brief.md`, `profile.yaml`, niczego z `var/`, danych firmowych ani osobistych. Treści w `content/` muszą być ogólne (dataset syntetyczny).
- Treści po polsku; kod, identyfikatory i terminy techniczne po angielsku.
- Decyzje nie zmieniające architektury → jedna linijka w `DECISIONS.md`. Pomysły spoza MVP → `ROADMAP.md`.
- Miejsca `TODO(learn)` pisze użytkownik — nie implementuj ich, chyba że wprost poprosi.

## Środowisko użytkownika
- Użytkownik pracuje na **Windows w PowerShell 5.1**: komendy, które mu podajesz, pisz po jednej w linii
  (bez `&&`), używaj `Copy-Item`/`Remove-Item` zamiast `cp`/`rm`, ścieżki względne z `/` działają.
- Kod musi działać na Windows i Linux (CI testuje oba): `pathlib`, `encoding="utf-8"` przy każdym
  odczycie/zapisie plików tekstowych, żadnych założeń o `bin/` vs `Scripts/` w venv.

## Komendy
```bash
uv sync                      # instalacja
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
```
