# Roadmap (poza MVP)

Wszystko, co nie mieści się w MVP (1–2 weekendy), ląduje tutaj — nie w kodzie.

## Następna faza
- [ ] **Tryb ewaluacji agenta text-to-SQL** na golden secie: `CandidateProvider` = LLM/agent, raport execution accuracy + partial score, regresja między wersjami promptu/kontekstu.
- [ ] **Ćwiczenia stricte w dbt**: użytkownik pisze model, aplikacja odpala `dbt build --select` na kopii hurtowni i sprawdza tabelę wynikową (te same `CompareSpec`).
- [ ] **Serwer MCP** (Python) udostępniający postęp, ćwiczenia i ewaluator agentom.

## Etap 2: nauka z telefonu przy wyłączonym PC
- [ ] **PWA na GitHub Pages**: fiszki offline (FSRS w JS, ten sam fold zdarzeń co w Pythonie + testy zgodności na wspólnych wektorach), szybkie wpisy sesji i brag doca, kolejka zdarzeń w IndexedDB.
- [ ] **Lokalne API na PC** (np. FastAPI): `POST /events` (push zdarzeń, idempotentnie po UUID), `GET /state` i `GET /cards?since=` (pull stanu i nowych fiszek); udostępnione przez `tailscale serve` po HTTPS, CORS dla domeny GitHub Pages.
- [ ] Opcjonalnie: ćwiczenia SQL w przeglądarce przez DuckDB-WASM (hurtownia jako plik Parquet na Pages).

## Treści
- [ ] Ścieżka: AI engineering dla analityki (generowana przez `/next-lesson`).
- [ ] Ścieżka: myślenie biznesowe (drzewa metryk, unit economics logistyki, Minto, memo).
- [ ] Ścieżka: statystyka pod eksperymenty (CI, bootstrap, A/B, holdout, DiD).
- [ ] Ścieżka opcjonalna: prognozowanie szeregów czasowych, podstawy ML.

## Aplikacja
- [ ] Migracja strony z MkDocs 1.x na Zensical (następca Material; MkDocs 2.0 łamie wtyczki i nadpisania motywu — dlatego `mkdocs<2`).
- [ ] Eksport CV / brag doca (szablony pod rekrutację).
- [ ] Edytor kodu z podświetlaniem składni w UI.
- [ ] Optymalizacja parametrów FSRS na własnej historii powtórek.
- [ ] Playwright: testy e2e UI i automatyczne screenshoty do README.
- [ ] Wykresy postępu KPI w czasie.
