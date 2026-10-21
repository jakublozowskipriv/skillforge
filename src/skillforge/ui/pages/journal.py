"""Journal: learning sessions log and the brag doc (with Markdown export)."""

from __future__ import annotations

import uuid
from datetime import date

import pandas as pd
import streamlit as st

from skillforge.progress.export import brag_markdown
from skillforge.progress.service import SessionKind
from skillforge.ui import state

KINDS: dict[SessionKind, str] = {
    "theory": "teoria",
    "practice": "praktyka",
    "review": "przegląd",
    "other": "inne",
}
KIND_LABELS: dict[str, str] = {str(k): v for k, v in KINDS.items()}
NO_TOPIC = "—"


def _sessions() -> None:
    index = state.content()
    topics = {NO_TOPIC: "— (bez tematu)"} | {
        t.id: f"{p.title} › {t.title}" for p in index.tree.paths for t in p.topics
    }
    with st.form("session", clear_on_submit=True):
        st.markdown("**Zaloguj sesję nauki**")
        c1, c2, c3 = st.columns([1, 1, 1])
        day = c1.date_input("Data", value=date.today(), format="DD.MM.YYYY")
        minutes = c2.number_input("Minuty", min_value=5, max_value=600, value=60, step=5)
        kind = c3.selectbox("Rodzaj", list(KINDS), format_func=KINDS.__getitem__)
        topic = st.selectbox("Temat", list(topics), format_func=topics.__getitem__)
        note = st.text_area("Notatka (co zrobione, co zostało?)", height=80)
        if st.form_submit_button("Zapisz sesję", type="primary"):
            state.progress().log_session(
                day,
                int(minutes),
                kind,
                None if topic == NO_TOPIC else topic,
                note.strip(),
            )
            st.toast("Sesja zapisana")
            st.rerun()

    sessions = state.progress().sessions()
    if not sessions:
        st.caption("Brak zalogowanych sesji.")
        return
    total = sum(s.minutes for s in sessions)
    st.caption(f"Sesje: {len(sessions)} · razem {total / 60:.1f} h")
    df = pd.DataFrame(
        [
            {
                "data": s.day,
                "min": s.minutes,
                "rodzaj": KIND_LABELS.get(s.kind, s.kind),
                "temat": topics.get(s.topic or NO_TOPIC, s.topic),
                "notatka": s.note,
                "źródło": s.source,
            }
            for s in reversed(sessions)
        ]
    )
    st.dataframe(df, hide_index=True, width="stretch")


def _brag() -> None:
    with st.form("brag", clear_on_submit=True):
        st.markdown("**Nowy wpis**: data · kontekst · moja rola · efekt (liczba) · dowód (link)")
        c1, c2 = st.columns([1, 3])
        day = c1.date_input("Data", value=date.today(), format="DD.MM.YYYY")
        context = c2.text_input("Kontekst", placeholder="np. Analiza opóźnień first mile")
        role = st.text_input("Moja rola", placeholder="np. autor analizy i rekomendacji")
        c3, c4, c5 = st.columns([3, 1, 1])
        effect = c3.text_input("Efekt", placeholder="np. skrócenie czasu odbioru z magazynu")
        value = c4.number_input("Liczba", value=None, step=1.0, placeholder="np. 12")
        unit = c5.text_input("Jednostka", placeholder="%, PLN, h…")
        evidence = st.text_input("Dowód (link)", placeholder="https://…")
        if st.form_submit_button("Dodaj wpis", type="primary"):
            if not (context.strip() and role.strip() and effect.strip()):
                st.error("Kontekst, rola i efekt są wymagane.")
            else:
                state.progress().add_brag(
                    day,
                    context.strip(),
                    role.strip(),
                    effect.strip(),
                    float(value) if value is not None else None,
                    unit.strip() or None,
                    evidence.strip(),
                )
                st.toast("Wpis dodany")
                st.rerun()

    entries = state.progress().brag_entries()
    if not entries:
        st.caption("Brak wpisów. Piątkowy przegląd to dobry moment na pierwszy.")
        return
    md = brag_markdown(entries)
    st.download_button("⬇️ Eksport do Markdown", md, file_name="brag-doc.md", mime="text/markdown")
    for b in reversed(entries):
        with st.container(border=True):
            number = (
                f" — **{b.effect_value:g}{(' ' + b.effect_unit) if b.effect_unit else ''}**"
                if b.effect_value is not None
                else ""
            )
            st.markdown(f"**{b.day:%d.%m.%Y}** · {b.context}\n\n{b.role} · {b.effect}{number}")
            if b.evidence:
                st.markdown(f"[dowód]({b.evidence})")
            if st.button("Wycofaj wpis", key=f"retract:{b.entry_id}", type="tertiary"):
                state.progress().retract_brag(uuid.UUID(str(b.entry_id)))
                st.rerun()


def render() -> None:
    st.title("📝 Dziennik")
    tab_sessions, tab_brag = st.tabs(["Sesje nauki", "Brag doc"])
    with tab_sessions:
        _sessions()
    with tab_brag:
        _brag()
