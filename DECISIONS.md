# Decisions

Jedna linijka na decyzję: data · decyzja · dlaczego. Decyzje zmieniające architekturę lub zakres są uzgadniane osobno (patrz plan MVP).

- 2026-10-21 · Python 3.12 (`requires-python >=3.12,<3.14`), zależności przypięte w `uv.lock` · powtarzalne środowisko = powtarzalny dataset i snapshoty.
- 2026-10-21 · Postęp w SQLite (stdlib), hurtownia ćwiczeń w DuckDB · postęp to OLTP (dużo małych zapisów z kilku procesów: Streamlit, CLI, Claude); DuckDB ma jednego pisarza i jest OLAP.
- 2026-10-21 · Fiszki: FSRS (`fsrs`) zamiast SM-2, za adapterem `srs.py` · nauka 2–3×/tydzień ⇒ powtórki często po terminie; FSRS modeluje zapominanie w realnym czasie, SM-2 ignoruje spóźnienie.
- 2026-10-21 · Dane prywatne (`var/`, `profile.yaml`, `docs/brief.md`) poza gitem; w repo tylko `*.example.*` z fikcyjnym profilem · repo publiczne (portfolio).
- 2026-10-21 · Aplikacja czyta `profile.yaml` (rytm, KPI, priorytety), a nie parsuje `brief.md` · brief to proza dla tutora; parsowanie Markdownu jest kruche.
- 2026-10-21 · CLI `typer` jako jedyny interfejs komend Claude do danych · komendy `.claude/commands/` nie dotykają baz bezpośrednio ⇒ testowalny, stabilny kontrakt.
- 2026-10-21 · Ścieżki plików w `skillforge.paths`, nadpisywalne przez `SKILLFORGE_ROOT` / `SKILLFORGE_VAR` · testy działają na katalogach tymczasowych.
- 2026-10-21 · Ruff: line-length 100, reguły E/F/W/I/B/UP/SIM/RUF/PTH/N; mypy `strict` dla `src` i `tests` · jeden spójny standard od pierwszego commita.
