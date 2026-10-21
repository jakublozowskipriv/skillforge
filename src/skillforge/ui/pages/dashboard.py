"""Dashboard: this week vs the rhythm, today's flashcards, development KPIs."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from skillforge.planner import WeekPlan, plan_week
from skillforge.profile import Profile
from skillforge.progress.events import utcnow
from skillforge.srs import daily_queue
from skillforge.ui import nav, state

WEEKDAY_PL = {
    "mon": "pn",
    "tue": "wt",
    "wed": "śr",
    "thu": "czw",
    "fri": "pt",
    "sat": "sob",
    "sun": "nd",
}
STATUS = {
    "done": ("✅", "zrobione"),
    "today": ("👉", "dziś"),
    "upcoming": ("🗓️", "przed Tobą"),
    "missed": ("➖", "pominięte"),
}


def _week(plan: WeekPlan) -> None:
    st.subheader(f"Ten tydzień · {plan.start:%d.%m} – {plan.end:%d.%m}")
    if plan.light:
        st.caption("🌿 Luźniejszy miesiąc wg profilu — plan jest orientacyjny.")
    cols = st.columns(len(plan.slots) or 1)
    for col, sp in zip(cols, plan.slots, strict=False):
        icon, label = STATUS[sp.status]
        days = ", ".join(WEEKDAY_PL[d] for d in sp.slot.days)
        with col, st.container(border=True):
            st.markdown(f"**{icon} {sp.slot.label}**")
            st.caption(f"{days} · {sp.slot.minutes} min · {label}")
            if sp.minutes_done:
                st.caption(f"zalogowano {sp.minutes_done} min")
    done, planned = plan.minutes_done, plan.minutes_planned
    st.progress(min(1.0, done / planned) if planned else 0.0, text=f"{done} / {planned} min")
    nav.link("dziennik", "Zaloguj sesję", icon="📝")


def _cards() -> None:
    st.subheader("Fiszki na dziś")
    index = state.content()
    queue = daily_queue(index.cards, state.progress().card_reviews(), utcnow())
    c1, c2, c3 = st.columns(3)
    c1.metric("Do powtórki", len(queue.due))
    c2.metric("Nowe na dziś", len(queue.new))
    c3.metric("Później", queue.new_remaining)
    if queue.items:
        nav.link("fiszki", "Zacznij powtórkę", icon="🃏")
    else:
        st.caption("Na dziś wszystko powtórzone. 🎉")


def _kpis(profile: Profile) -> None:
    st.subheader("KPI rozwoju")
    if not profile.kpis:
        st.caption("Brak KPI w profile.yaml.")
        return
    latest = state.progress().kpi_latest()
    today = date.today()
    rows = []
    for k in profile.kpis:
        point = latest.get(k.id)
        current = point.value if point else k.baseline
        target = k.next_target(today)
        rows.append(
            {
                "KPI": k.name,
                "teraz": f"{current:g} {k.unit}".strip(),
                "start": f"{k.baseline:g}",
                "następny cel": f"{target.value:g} do {target.by:%m.%Y}" if target else "—",
                "postęp do celu": (
                    max(0.0, min(1.0, (current - k.baseline) / (target.value - k.baseline)))
                    if target and target.value != k.baseline
                    else None
                ),
                "aktualizacja": f"{point.at:%d.%m.%Y}" if point else "—",
            }
        )
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        column_config={
            "postęp do celu": st.column_config.ProgressColumn(min_value=0.0, max_value=1.0)
        },
    )
    with st.form("kpi-update", clear_on_submit=True):
        st.markdown("**Zaktualizuj KPI** (ręcznie)")
        c1, c2, c3 = st.columns([2, 1, 3])
        names = {k.id: k.name for k in profile.kpis}
        kpi_id = c1.selectbox("KPI", list(names), format_func=names.__getitem__)
        value = c2.number_input("Wartość", step=1.0)
        note = c3.text_input("Notatka (co się zmieniło?)")
        if st.form_submit_button("Zapisz"):
            state.progress().record_kpi(kpi_id, float(value), note)
            st.toast("KPI zapisane")
            st.rerun()


def render() -> None:
    st.title("🏠 Dashboard")
    profile = state.profile()
    plan = plan_week(profile, state.progress().sessions(), date.today())
    _week(plan)
    st.divider()
    left, right = st.columns([1, 2])
    with left:
        _cards()
    with right:
        _kpis(profile)
