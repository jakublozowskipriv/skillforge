"""App shell: page config and navigation."""

from __future__ import annotations

import streamlit as st

from skillforge.ui.pages import exercises


def main() -> None:
    st.set_page_config(page_title="skillforge", page_icon="🛠️", layout="wide")
    st.markdown(
        "<style>textarea { font-family: ui-monospace, Menlo, Consolas, monospace !important; }"
        "</style>",
        unsafe_allow_html=True,
    )
    pages = [st.Page(exercises.render, title="Ćwiczenia", icon="🧪", url_path="cwiczenia")]
    st.navigation(pages).run()
