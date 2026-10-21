"""Flashcards: FSRS daily queue, reveal, rate Again/Hard/Good/Easy (keys: space, 1–4)."""

from __future__ import annotations

import time

import streamlit as st

from skillforge.content.models import Card
from skillforge.progress.events import utcnow
from skillforge.srs import (
    RATING_LABELS,
    card_state,
    daily_queue,
    format_interval,
    preview_intervals,
)
from skillforge.ui import state

RATING_PL = {1: "Nie pamiętam", 2: "Trudne", 3: "Dobrze", 4: "Łatwe"}
ALL = "__all__"


def _rate(card_id: str, rating: int) -> None:
    started = st.session_state.pop("card_shown_at", None)
    duration = time.monotonic() - started if started else None
    state.progress().review_card(card_id, rating, duration_s=duration)
    st.session_state["card_revealed"] = False


def _render_card(card: Card) -> None:
    reviews = state.progress().card_reviews().get(card.id, [])
    current = card_state(card.id, reviews)
    st.session_state.setdefault("card_shown_at", time.monotonic())
    with st.container(border=True):
        st.caption(
            f"`{card.id}` · {card.topic} · "
            + ("nowa" if current.state == "new" else f"powtórka #{current.reviews + 1}")
        )
        st.markdown(f"### {card.front}")
        if not st.session_state.get("card_revealed"):
            if st.button(
                "Pokaż odpowiedź", type="primary", shortcut="Space", key=f"reveal:{card.id}"
            ):
                st.session_state["card_revealed"] = True
                st.rerun()
            return
        st.divider()
        st.markdown(card.back)

    preview = preview_intervals(reviews, utcnow())
    cols = st.columns(4)
    for col, rating in zip(cols, RATING_LABELS, strict=True):
        col.button(
            f"{rating} · {RATING_PL[rating]} ({format_interval(preview[rating])})",
            key=f"rate:{card.id}:{rating}",
            on_click=_rate,
            args=(card.id, rating),
            shortcut=str(rating),
            width="stretch",
            type="primary" if rating == 3 else "secondary",
        )


def render() -> None:
    st.title("🃏 Fiszki")
    index = state.content()
    if not index.cards:
        st.info("Brak fiszek w `content/`. Wygeneruj je komendą `/next-lesson`.")
        return
    paths = {ALL: "Wszystkie ścieżki"} | {p.id: p.title for p in index.tree.paths}
    path_id = st.selectbox("Talia", list(paths), format_func=paths.__getitem__)
    card_ids = [
        c.id
        for c in index.cards.values()
        if path_id == ALL or ((p := index.tree.path_of(c.topic)) is not None and p.id == path_id)
    ]
    queue = daily_queue(card_ids, state.progress().card_reviews(), utcnow())
    c1, c2, c3 = st.columns(3)
    c1.metric("Do powtórki", len(queue.due))
    c2.metric("Nowe na dziś", len(queue.new))
    c3.metric("Nowe później", queue.new_remaining)

    if not queue.items:
        st.success("Na dziś wszystko powtórzone. Wróć jutro — FSRS sam zaplanuje kolejne powtórki.")
        return
    _render_card(index.cards[queue.items[0].card_id])
    st.caption("Skróty: spacja — pokaż odpowiedź · 1–4 — ocena.")
