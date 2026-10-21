"""Lessons: competence tree (path → topic, level 0–3) and lesson reader."""

from __future__ import annotations

import streamlit as st

from skillforge.content.loader import ContentIndex
from skillforge.content.models import LearningPath
from skillforge.ui import nav, state

LEVELS = {
    0: "0 · nie znam",
    1: "1 · rozumiem pojęcia",
    2: "2 · robię samodzielnie",
    3: "3 · uczę innych / prod",
}


def _set_level(topic_id: str, key: str) -> None:
    state.progress().set_level(topic_id, int(st.session_state[key]))


def _tree(path: LearningPath, index: ContentIndex) -> None:
    levels = state.progress().levels()
    for topic in path.topics:
        n_lessons = len(index.lessons_for_topic(topic.id))
        key = f"level:{topic.id}"
        current = levels.get(topic.id, 0)
        if st.session_state.get(key) != current:
            st.session_state[key] = current
        st.selectbox(
            f"{topic.title}" + (f" · lekcje: {n_lessons}" if n_lessons else ""),
            list(LEVELS),
            format_func=LEVELS.__getitem__,
            key=key,
            help=topic.description or None,
            on_change=_set_level,
            args=(topic.id, key),
        )


def _default_path(index: ContentIndex) -> str:
    lesson_id = st.query_params.get("lesson")
    if lesson_id and lesson_id in index.lessons:
        return index.lessons[lesson_id].path
    priority = [p for p in state.profile().path_priority if index.lessons_for_path(p)]
    with_lessons = [p.id for p in index.tree.paths if index.lessons_for_path(p.id)]
    return (priority or with_lessons or [index.tree.paths[0].id])[0]


def render() -> None:
    st.title("📖 Lekcje")
    index = state.content()
    paths_by_id = {p.id: p for p in index.tree.paths}
    path_ids = list(paths_by_id)
    path_id = st.selectbox(
        "Ścieżka",
        path_ids,
        index=path_ids.index(_default_path(index)),
        format_func=lambda i: (
            paths_by_id[i].title + (" (opcjonalna)" if paths_by_id[i].optional else "")
        ),
    )
    path = paths_by_id[path_id]
    left, right = st.columns([1, 2.4], gap="large")
    with left, st.expander("🌳 Drzewo kompetencji · poziomy 0–3", expanded=False):
        _tree(path, index)

    with right:
        lessons = index.lessons_for_path(path_id)
        if not lessons:
            st.info(
                "Brak lekcji w tej ścieżce. Wygeneruj kolejną komendą `/next-lesson` w Claude Code."
            )
            return
        ids = [lesson.id for lesson in lessons]
        wanted = st.query_params.get("lesson")
        lesson_id = st.radio(
            "Lekcja",
            ids,
            index=ids.index(wanted) if wanted in ids else 0,
            format_func=lambda i: f"{index.lessons[i].title} · {index.lessons[i].minutes} min",
            horizontal=False,
        )
        lesson = index.lessons[lesson_id]
        topic = index.tree.topic(lesson.topic)
        st.caption(f"Temat: {topic.title if topic else lesson.topic} · ok. {lesson.minutes} min")
        with st.container(border=True):
            st.markdown(lesson.body)

        st.markdown("#### Praktyka")
        exercises = index.exercises_for_lesson(lesson.id)
        stats = state.progress().exercise_stats()
        for ex in exercises:
            s = stats.get(ex.id)
            icon = "✅" if s and s.solved else ("🟠" if s else "⚪")
            nav.link("cwiczenia", f"{icon} {ex.id} · {ex.title}", ex=ex.id)
        cards = index.cards_for_lesson(lesson.id)
        if cards:
            nav.link("fiszki", f"🃏 Fiszki do tej lekcji: {len(cards)}")
