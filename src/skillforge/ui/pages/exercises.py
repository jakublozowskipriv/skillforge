"""Exercise page: question, editor, explore (run) and check, readable diff, hints, history."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from skillforge import paths, warehouse
from skillforge.content.models import Exercise
from skillforge.evaluator import EvalContext, EvalResult, ResultSet, evaluate
from skillforge.evaluator.sql_runner import SqlExecutionError, run_sql
from skillforge.progress.projections import ExerciseStats
from skillforge.text import pl_plural
from skillforge.ui import nav, state
from skillforge.ui.components import render_eval_result, rows_df

DIFFICULTY = {1: "●○○ łatwe", 2: "●●○ średnie", 3: "●●● trudne"}
EXPLORE_MAX_ROWS = 1_000


@st.cache_data(show_spinner=False)
def _schema(path: str, mtime: float) -> dict[str, dict[str, list[tuple[str, str]]]]:
    return warehouse.describe(Path(path))


def _render_schema_browser(wh: Path) -> None:
    with st.expander("📚 Schemat hurtowni (marts / intermediate / staging / raw)"):
        schema = _schema(str(wh), wh.stat().st_mtime)
        for layer, tables in schema.items():
            st.markdown(f"**{layer}**")
            for table, cols in tables.items():
                st.markdown(
                    f"`{layer}.{table}` — " + ", ".join(f"{c} *{t.lower()}*" for c, t in cols)
                )


def _render_hints(ex: Exercise) -> None:
    key = f"hints_shown:{ex.id}"
    shown = int(st.session_state.get(key, 0))
    for i, hint in enumerate(ex.hints[:shown], start=1):
        st.info(f"**Podpowiedź {i}.** {hint}")
    if shown < len(ex.hints) and st.button(
        f"💡 Pokaż podpowiedź ({shown + 1}/{len(ex.hints)})", key=f"hint-btn:{ex.id}"
    ):
        st.session_state[key] = shown + 1
        st.rerun()


def _explore(code: str, wh: Path) -> ResultSet | str:
    """Run a query for exploration only: read-only, nothing compared, nothing recorded."""
    try:
        return run_sql(code, wh, max_rows=EXPLORE_MAX_ROWS)
    except SqlExecutionError as exc:
        return str(exc)


def _render_explore(outcome: ResultSet | str | None) -> None:
    if outcome is None:
        return
    with st.container(border=True):
        st.caption("Podgląd wyniku · nie jest sprawdzany ani zapisywany jako próba")
        if isinstance(outcome, str):
            st.error(f"**Błąd wykonania**\n\n```\n{outcome}\n```")
            return
        count = pl_plural(outcome.row_count, "wiersz", "wiersze", "wierszy")
        if outcome.truncated:
            count = f"pierwsze {count} (wynik obcięty)"
        st.caption(count)
        st.dataframe(
            rows_df(outcome.columns, outcome.rows), hide_index=True, width="stretch", height=320
        )


def _status_icon(stats: ExerciseStats | None) -> str:
    if stats is None:
        return "⚪"
    return "✅" if stats.solved else "🟠"


def _render_history(ex: Exercise) -> None:
    history = state.progress().attempts(ex.id)
    if not history:
        return
    solved = "✅ rozwiązane" if any(a.passed for a in history) else "jeszcze nierozwiązane"
    st.caption(f"Próby: {len(history)} · {solved}")
    with st.expander("🕘 Historia prób"):
        df = pd.DataFrame(
            [
                {
                    "kiedy": f"{a.at.astimezone():%d.%m %H:%M}",
                    "wynik": "✅" if a.passed else "❌",
                    "score": round(a.score, 2),
                    "kod": a.code,
                }
                for a in reversed(history)
            ]
        )
        st.dataframe(df, hide_index=True, width="stretch")
        st.caption(f"Feedback od tutora: w Claude Code uruchom `/review {ex.id}`.")


def render() -> None:
    st.title("🧪 Ćwiczenia")
    wh = paths.WAREHOUSE_PATH
    if not wh.exists():
        st.warning("Brak hurtowni ćwiczeń. Zbuduj ją jedną komendą:")
        st.code("uv run skillforge data build", language="bash")
        return

    index = state.content()
    if not index.exercises:
        st.info("Brak ćwiczeń w `content/`. Wygeneruj je komendą `/next-lesson`.")
        return
    stats = state.progress().exercise_stats()
    ids = sorted(index.exercises)
    wanted = st.query_params.get("ex")
    ex_id = st.selectbox(
        "Ćwiczenie",
        ids,
        index=ids.index(wanted) if wanted in ids else 0,
        format_func=lambda i: f"{_status_icon(stats.get(i))} {i} · {index.exercises[i].title}",
    )
    ex = index.exercises[ex_id]

    st.subheader(ex.title)
    st.caption(f"{ex.kind.upper()} · {DIFFICULTY[ex.difficulty]} · temat `{ex.topic}`")
    if ex.lesson and ex.lesson in index.lessons:
        nav.link("lekcje", f"Lekcja: {index.lessons[ex.lesson].title}", icon="📖", lesson=ex.lesson)
    st.markdown(ex.question)
    if ex.kind == "sql":
        _render_schema_browser(wh)

    default = ex.starter or ("-- Twoje zapytanie\nselect\n" if ex.kind == "sql" else "")
    code = st.text_area("Twoje rozwiązanie", value=default, height=240, key=f"code:{ex.id}")
    result_key = f"result:{ex.id}"
    explore_key = f"explore:{ex.id}"
    check_col, run_col, _ = st.columns([1, 1, 4])
    if check_col.button("▶ Sprawdź", type="primary", key=f"check:{ex.id}", width="stretch"):
        with st.spinner("Uruchamiam i porównuję z golden setem…"):
            outcome = evaluate(ex.to_case(), code, EvalContext(wh))
        st.session_state[result_key] = outcome
        state.progress().record_attempt(ex.id, code, outcome)
    if ex.kind == "sql" and run_col.button(
        "▷ Uruchom",
        key=f"run:{ex.id}",
        width="stretch",
        help="Podgląd wyniku zapytania: bez porównania z oczekiwanym i bez zapisu próby.",
    ):
        st.session_state[explore_key] = _explore(code, wh)
    if ex.kind == "sql":
        _render_explore(st.session_state.get(explore_key))

    _render_history(ex)
    result: EvalResult | None = st.session_state.get(result_key)
    if result is not None:
        render_eval_result(result)

    _render_hints(ex)
    if result is not None:
        with st.expander("🔑 Rozwiązanie referencyjne"):
            st.code(ex.reference, language=ex.kind)
