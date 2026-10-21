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
- 2026-10-21 · Fikcyjni przewoźnicy (SwiftParcel, NorthExpress, Pakomat24…) zamiast prawdziwych marek · syntetyczne wyniki nie mogą wyglądać jak twierdzenia o realnych firmach.
- 2026-10-21 · Stały zakres dat datasetu (2026-01-01..06-30, ekstrakt 2026-07-03), a nie „względem dziś” · snapshoty ćwiczeń muszą być stabilne w czasie.
- 2026-10-21 · Generator ładuje dane do schematu `raw` w DuckDB (a nie do plików CSV/Parquet) · ćwiczenia mogą działać z `enable_external_access=false`; `raw` gra rolę „landing zone” z EL.
- 2026-10-21 · `raw.shipment_events.event_at` jako tekst ISO-8601 + celowy brud (kody przewoźników, duplikaty, spóźnione eventy, NULL-e) · materiał do ćwiczeń warstwy staging.
- 2026-10-21 · Generator na numpy + pandas (z `pandas-stubs` dla mypy) · wektorowo ~1 s dla 100k eventów; pandas i tak jest zależnością Streamlit.
- 2026-10-21 · dbt: staging i intermediate jako `view`, marts jako `table` · staging/int to tanie, zawsze świeże transformacje; marts to stabilny interfejs dla BI i ćwiczeń.
- 2026-10-21 · Własne makro `generate_schema_name` (czyste schematy `staging`/`intermediate`/`marts`) · jeden lokalny target, nie ma czego izolować; czytelne `marts.fct_shipments` w ćwiczeniach.
- 2026-10-21 · Bez pakietów dbt (dbt_utils): własne `surrogate_key` i `unique_combination_of_columns` · brak `dbt deps` = działa offline po świeżym klonie; przy okazji widać, że test to zapytanie zwracające błędne wiersze.
- 2026-10-21 · Deduplikacja eventów w staging (`qualify row_number()`), zostaje najwcześniej załadowana kopia · duplikaty to cecha źródła (at-least-once), nie logiki biznesowej.
- 2026-10-21 · `fct_shipments`: grain = przesyłka; zegar SLA startuje od `picked_up_at`, SLA z wersji SCD2 ważnej w dniu odbioru; kontrakt dbt `enforced` · on-time to definicja biznesowa — jawna w kodzie, YAML i kontrakcie.
- 2026-10-21 · `fct_shipment_events` incremental (`delete+insert`, `unique_key`, lookback po `loaded_at` = 3 dni); `data build` zawsze `--full-refresh` · lekcja o spóźnionych eventach; raw jest generowany od zera.
- 2026-10-21 · dbt uruchamiany jako subprocess z venv (`skillforge data build`), ścieżka hurtowni przez `SKILLFORGE_WAREHOUSE` · testy integracyjne budują małą hurtownię (scale=0.05) w katalogu tymczasowym.

## Dostęp z telefonu (wymaganie dodane 2026-10-21)
- 2026-10-21 · Lekcje jako statyczna strona MkDocs Material na GitHub Pages, deploy z CI (z `main`) · czytelne na telefonie bez włączonego PC; lekcje i tak są publiczne. Zensical (następca) jeszcze 0.x — migracja później, czyta ten sam `mkdocs.yml`.
- 2026-10-21 · Offline: własny service worker + manifest generowany hookiem MkDocs po buildzie (precache wszystkich stron) · plugin `offline` Material służy do `file://`, nie do cache w przeglądarce telefonu.
- 2026-10-21 · `skillforge serve --lan` (Streamlit na 0.0.0.0) + Tailscale w README · pełna aplikacja z telefonu, gdy PC włączony, bez wystawiania portów do internetu.
- 2026-10-21 · Postęp = append-only log zdarzeń (`event_id` UUID, `type`, `occurred_at`, `recorded_at`, `source` pc|phone, `payload` JSON); stan (FSRS kart, sesje, brag, KPI, poziomy, próby) to projekcja liczona z logu · synchronizacja z wielu urządzeń = suma zbiorów zdarzeń po UUID, bez konfliktów; idempotentny import.
- 2026-10-21 · Stan FSRS karty = fold zdarzeń `card.reviewed` posortowanych po `occurred_at` (nie po kolejności zapisu) · powtórka z telefonu zsynchronizowana później trafia na właściwe miejsce w historii.
- 2026-10-21 · Warstwa postępu za interfejsem `EventStore` (Protocol: `append`, `extend`, `read`) + projekcje w czystym Pythonie; SQLite to jedna implementacja · UI i CLI nie znają SQL-a postępu; podmiana na inny magazyn bez zmian w UI.
- 2026-10-21 · Usunięcie/edycja wpisu = nowe zdarzenie (`brag.retracted`, `kpi.recorded` z nowszym `occurred_at`), nigdy UPDATE/DELETE · log jest prawdą; projekcja decyduje o stanie bieżącym.
