"""Exercise page: question, editor, check, readable diff, hints."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from skillforge import paths, warehouse
from skillforge.content.loader import load_exercises
from skillforge.content.models import Exercise
from skillforge.evaluator import EvalContext, EvalResult, evaluate
from skillforge.progress.service import default_progress
from skillforge.ui.components import render_eval_result

DIFFICULTY = {1: "●○○ łatwe", 2: "●●○ średnie", 3: "●●● trudne"}


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


def render() -> None:
    st.title("🧪 Ćwiczenia")
    wh = paths.WAREHOUSE_PATH
    if not wh.exists():
        st.warning("Brak hurtowni ćwiczeń. Zbuduj ją jedną komendą:")
        st.code("uv run skillforge data build", language="bash")
        return

    exercises = load_exercises()
    if not exercises:
        st.info("Brak ćwiczeń w `content/`. Wygeneruj je komendą `/next-lesson`.")
        return
    by_id = {e.id: e for e in exercises}
    ex_id = st.selectbox("Ćwiczenie", list(by_id), format_func=lambda i: f"{i} · {by_id[i].title}")
    ex = by_id[ex_id]

    st.subheader(ex.title)
    st.caption(f"{ex.kind.upper()} · {DIFFICULTY[ex.difficulty]} · temat `{ex.topic}`")
    st.markdown(ex.question)
    if ex.kind == "sql":
        _render_schema_browser(wh)

    default = ex.starter or ("-- Twoje zapytanie\nselect\n" if ex.kind == "sql" else "")
    code = st.text_area("Twoje rozwiązanie", value=default, height=240, key=f"code:{ex.id}")
    result_key = f"result:{ex.id}"
    if st.button("▶ Sprawdź", type="primary", key=f"check:{ex.id}"):
        with st.spinner("Uruchamiam i porównuję z golden setem…"):
            outcome = evaluate(ex.to_case(), code, EvalContext(wh))
        st.session_state[result_key] = outcome
        default_progress().record_attempt(ex.id, code, outcome)

    history = default_progress().attempts(ex.id)
    if history:
        solved = "✅ rozwiązane" if any(a.passed for a in history) else "jeszcze nierozwiązane"
        st.caption(f"Próby: {len(history)} · {solved}")

    result: EvalResult | None = st.session_state.get(result_key)
    if result is not None:
        render_eval_result(result)

    _render_hints(ex)
    if result is not None:
        with st.expander("🔑 Rozwiązanie referencyjne"):
            st.code(ex.reference, language=ex.kind)
