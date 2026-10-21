"""Reusable rendering helpers."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import streamlit as st

from skillforge.evaluator import EvalResult
from skillforge.evaluator.resultset import Row
from skillforge.text import pl_plural


def rows_df(columns: Sequence[str], rows: Sequence[Row]) -> pd.DataFrame:
    return pd.DataFrame([list(r) for r in rows], columns=list(columns))


def render_eval_result(result: EvalResult) -> None:
    if result.error:
        st.error(f"**Błąd wykonania**\n\n```\n{result.error}\n```")
        return
    if result.passed:
        st.success(f"✅ Zaliczone — wynik zgodny z oczekiwanym ({result.duration_ms:.0f} ms).")
    elif result.kind == "python":
        passed = sum(t.passed for t in result.test_results)
        st.error(f"❌ Jeszcze nie — zaliczone testy: {passed}/{len(result.test_results)}")
    elif result.partial is not None:
        st.error(f"❌ Jeszcze nie — częściowa zgodność (F1 wierszy): {result.score:.0%}")
    else:
        st.error("❌ Jeszcze nie — wynik różni się od oczekiwanego.")

    if result.kind == "python":
        df = pd.DataFrame(
            [
                {
                    "test": t.name,
                    "ok": "✅" if t.passed else "❌",
                    "oczekiwano": repr(t.expected),
                    "otrzymano": t.error or repr(t.got),
                }
                for t in result.test_results
            ]
        )
        st.dataframe(df, hide_index=True, width="stretch")
        return

    diff = result.diff
    if diff is None:
        return
    if not result.passed:
        st.markdown("\n".join(f"- {line}" for line in diff.summary()))
    if result.partial:
        p = result.partial
        st.caption(f"Precision {p.precision:.2f} · recall {p.recall:.2f} · F1 {p.f1:.2f}")

    tabs: list[str] = []
    if diff.cell_mismatches:
        tabs.append("Różne wartości")
    if diff.missing_rows:
        tabs.append(f"Brakujące ({len(diff.missing_rows)})")
    if diff.extra_rows:
        tabs.append(f"Nadmiarowe ({len(diff.extra_rows)})")
    tabs.append("Twój wynik")
    containers = dict(zip(tabs, st.tabs(tabs), strict=True))

    if diff.cell_mismatches:
        with containers["Różne wartości"]:
            records = []
            for m in diff.cell_mismatches:
                for col in m.columns:
                    i = diff.expected_columns.index(col)
                    key = {
                        c: v
                        for c, v in zip(diff.expected_columns, m.expected_row, strict=True)
                        if c not in m.columns
                    }
                    records.append(
                        {
                            "wiersz (pozostałe kolumny)": str(key),
                            "kolumna": col,
                            "oczekiwano": m.expected_row[i],
                            "otrzymano": m.actual_row[i],
                        }
                    )
            st.dataframe(pd.DataFrame(records), hide_index=True, width="stretch")
    for label, rows in (
        (f"Brakujące ({len(diff.missing_rows)})", diff.missing_rows),
        (f"Nadmiarowe ({len(diff.extra_rows)})", diff.extra_rows),
    ):
        if label in containers:
            with containers[label]:
                cols = diff.expected_columns if "Brak" in label else _actual_cols(result)
                st.dataframe(rows_df(cols, rows), hide_index=True, width="stretch")
    with containers["Twój wynik"]:
        if result.actual is not None:
            st.caption(pl_plural(result.actual.row_count, "wiersz", "wiersze", "wierszy"))
            st.dataframe(
                rows_df(result.actual.columns, result.actual.rows[:200]),
                hide_index=True,
                width="stretch",
            )


def _actual_cols(result: EvalResult) -> Sequence[str]:
    # Extra rows are reported in the *expected* column order after alignment.
    assert result.diff is not None
    return result.diff.expected_columns
