"""Shared, cached access to content, progress and profile for all pages."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from skillforge import paths
from skillforge.content.loader import ContentIndex, load_content
from skillforge.profile import Profile, load_profile, profile_path
from skillforge.progress.service import Progress, default_progress


def _signature(root: Path) -> float:
    """Latest mtime under ``root`` — cache key so new lessons from /next-lesson show up live."""
    return max((p.stat().st_mtime for p in root.rglob("*") if p.is_file()), default=0.0)


@st.cache_resource(show_spinner=False)
def _content(root: str, signature: float) -> ContentIndex:
    return load_content(Path(root))


def content() -> ContentIndex:
    return _content(str(paths.CONTENT_DIR), _signature(paths.CONTENT_DIR))


def progress() -> Progress:
    return default_progress()


@st.cache_resource(show_spinner=False)
def _profile(path: str, mtime: float) -> Profile:
    return load_profile(Path(path))


def profile() -> Profile:
    path = profile_path()
    return _profile(str(path), path.stat().st_mtime)
