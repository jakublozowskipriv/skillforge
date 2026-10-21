---
description: Krótki quiz w terminalu z tematu; wynik zapisany do postępu
argument-hint: "<temat: id z content/tree.yaml, np. ae.dimensional-modeling, albo nazwa>"
allowed-tools: Read, Glob, Grep, Bash(uv run skillforge progress record-quiz:*), Bash(uv run skillforge data schema:*)
---

Przeprowadź krótki quiz z tematu `$ARGUMENTS`.

1. Ustal `topic` (id) na podstawie `content/tree.yaml` — dopasuj nazwę, jeśli podano ją słownie.
   Jeśli niejednoznaczne, zapytaj.
2. Przeczytaj lekcje i fiszki tego tematu (`content/paths/*/lessons`, `content/paths/*/cards`).
3. Zadaj **5 pytań, po jednym naraz** — czekaj na odpowiedź przed kolejnym. Mieszaj typy:
   pojęcie, „co zwróci ten SQL?”, „co jest nie tak w tym zapytaniu?”, scenariusz z logistyki
   e-commerce (na syntetycznym datasecie), decyzja projektowa („view czy table i dlaczego?”).
   Nie powtarzaj dosłownie fiszek.
4. Po każdej odpowiedzi: oceń (1 / 0,5 / 0 pkt — zaokrąglaj w dół do pełnych punktów na koniec),
   w 1–3 zdaniach wyjaśnij, czego brakowało.
5. Na koniec zapisz wynik:
   `uv run skillforge progress record-quiz --topic <id> --score <punkty> --total 5 --note "<co poprawić>"`
6. Podsumuj: wynik, 1–2 luki, rekomendacja (lekcja/ćwiczenie/fiszki). Jeśli wynik ≥ 4/5,
   zasugeruj podniesienie poziomu tematu w aplikacji (strona Lekcje → drzewo kompetencji).
