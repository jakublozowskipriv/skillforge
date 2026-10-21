"""Page registry, so pages can link to each other without circular imports."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

_PAGES: dict[str, Any] = {}


def register(
    fn: Callable[[], None], title: str, icon: str, url_path: str, *, default: bool = False
) -> Any:
    page = st.Page(fn, title=title, icon=icon, url_path=url_path, default=default)
    _PAGES[url_path] = page
    return page


def link(url_path: str, label: str, icon: str | None = None, **query: str) -> None:
    page = _PAGES.get(url_path)
    if page is not None:
        st.page_link(page, label=label, icon=icon, query_params=query or None)
