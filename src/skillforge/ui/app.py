"""App shell: page config and navigation."""

from __future__ import annotations

import streamlit as st

from skillforge.ui import nav
from skillforge.ui.pages import dashboard, exercises, flashcards, journal, lessons


def main() -> None:
    st.set_page_config(page_title="skillforge", page_icon="🛠️", layout="wide")
    st.markdown(
        "<style>textarea { font-family: ui-monospace, Menlo, Consolas, monospace !important; }"
        "</style>",
        unsafe_allow_html=True,
    )
    pages = [
        nav.register(dashboard.render, "Dashboard", "🏠", "dashboard", default=True),
        nav.register(lessons.render, "Lekcje", "📖", "lekcje"),
        nav.register(exercises.render, "Ćwiczenia", "🧪", "cwiczenia"),
        nav.register(flashcards.render, "Fiszki", "🃏", "fiszki"),
        nav.register(journal.render, "Dziennik", "📝", "dziennik"),
    ]
    st.navigation(pages).run()
