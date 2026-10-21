# Roadmap (poza MVP)

Wszystko, co nie mieści się w MVP (1–2 weekendy), ląduje tutaj — nie w kodzie.

## Następna faza
- [ ] **Tryb ewaluacji agenta text-to-SQL** na golden secie: `CandidateProvider` = LLM/agent, raport execution accuracy + partial score, regresja między wersjami promptu/kontekstu.
- [ ] **Ćwiczenia stricte w dbt**: użytkownik pisze model, aplikacja odpala `dbt build --select` na kopii hurtowni i sprawdza tabelę wynikową (te same `CompareSpec`).
- [ ] **Serwer MCP** (Python) udostępniający postęp, ćwiczenia i ewaluator agentom.

## Treści
- [ ] Ścieżka: AI engineering dla analityki (generowana przez `/next-lesson`).
- [ ] Ścieżka: myślenie biznesowe (drzewa metryk, unit economics logistyki, Minto, memo).
- [ ] Ścieżka: statystyka pod eksperymenty (CI, bootstrap, A/B, holdout, DiD).
- [ ] Ścieżka opcjonalna: prognozowanie szeregów czasowych, podstawy ML.

## Aplikacja
- [ ] Eksport CV / brag doca (szablony pod rekrutację).
- [ ] Edytor kodu z podświetlaniem składni w UI.
- [ ] Optymalizacja parametrów FSRS na własnej historii powtórek.
- [ ] Playwright: testy e2e UI i automatyczne screenshoty do README.
- [ ] Wykresy postępu KPI w czasie.
