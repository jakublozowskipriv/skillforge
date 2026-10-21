"""Load content files from disk.

Layout::

    content/
      tree.yaml                                   # CompetenceTree
      paths/<path-id>/lessons/<lesson-id>.md      # Lesson (YAML frontmatter + Markdown)
      paths/<path-id>/exercises/<exercise-id>.yaml (+ <exercise-id>.expected.json for SQL)
      paths/<path-id>/cards/<deck>.yaml           # CardDeck
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from skillforge import paths
from skillforge.content.models import Card, CardDeck, CompetenceTree, Exercise, Lesson

FRONTMATTER_DELIMITER = "---"


class ContentError(ValueError):
    """A content file cannot be parsed."""


def _read_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ContentError(f"invalid YAML: {exc}") from exc


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """``---\\n<yaml>\\n---\\n<markdown>`` → (metadata, body)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIMITER:
        raise ContentError("lesson must start with a `---` YAML frontmatter block")
    try:
        end = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration as exc:
        raise ContentError("frontmatter is not closed with `---`") from exc
    meta = yaml.safe_load("\n".join(lines[1:end])) or {}
    if not isinstance(meta, dict):
        raise ContentError("frontmatter must be a mapping")
    return meta, "\n".join(lines[end + 1 :]).strip() + "\n"


def load_tree(content_dir: Path | None = None) -> CompetenceTree:
    root = content_dir or paths.CONTENT_DIR
    return CompetenceTree.model_validate(_read_yaml(root / "tree.yaml"))


def load_lesson(path: Path) -> Lesson:
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    return Lesson.model_validate({**meta, "body": body, "source_path": path})


def load_exercise(path: Path) -> Exercise:
    data = _read_yaml(path)
    if not isinstance(data, dict):
        raise ContentError("exercise file must be a mapping")
    return Exercise.model_validate({**data, "source_path": path})


def load_deck(path: Path) -> list[Card]:
    return CardDeck.model_validate(_read_yaml(path)).cards


def lesson_files(root: Path) -> Iterator[Path]:
    return iter(sorted(root.glob("paths/*/lessons/*.md")))


def exercise_files(root: Path) -> Iterator[Path]:
    return iter(sorted(root.glob("paths/*/exercises/*.yaml")))


def deck_files(root: Path) -> Iterator[Path]:
    return iter(sorted(root.glob("paths/*/cards/*.yaml")))


def load_exercises(content_dir: Path | None = None) -> list[Exercise]:
    root = content_dir or paths.CONTENT_DIR
    return [load_exercise(f) for f in exercise_files(root)]


@dataclass(frozen=True)
class ContentIndex:
    """Everything in ``content/``, with lookups the UI and the tutor need."""

    tree: CompetenceTree
    lessons: dict[str, Lesson] = field(default_factory=dict)
    exercises: dict[str, Exercise] = field(default_factory=dict)
    cards: dict[str, Card] = field(default_factory=dict)

    def lessons_for_topic(self, topic_id: str) -> list[Lesson]:
        found = [lesson for lesson in self.lessons.values() if lesson.topic == topic_id]
        return sorted(found, key=lambda lesson: (lesson.order, lesson.id))

    def lessons_for_path(self, path_id: str) -> list[Lesson]:
        found = [lesson for lesson in self.lessons.values() if lesson.path == path_id]
        return sorted(found, key=lambda lesson: (lesson.order, lesson.id))

    def exercises_for_lesson(self, lesson_id: str) -> list[Exercise]:
        lesson = self.lessons.get(lesson_id)
        listed = lesson.exercises if lesson else []
        extra = sorted(
            e.id for e in self.exercises.values() if e.lesson == lesson_id and e.id not in listed
        )
        return [self.exercises[i] for i in [*listed, *extra] if i in self.exercises]

    def cards_for_lesson(self, lesson_id: str) -> list[Card]:
        return [c for c in self.cards.values() if c.lesson == lesson_id]


def load_content(content_dir: Path | None = None) -> ContentIndex:
    """Load all content; raises on the first invalid file (use ``validate`` for a full report)."""
    root = content_dir or paths.CONTENT_DIR
    lessons = {lesson.id: lesson for lesson in map(load_lesson, lesson_files(root))}
    exercises = {e.id: e for e in map(load_exercise, exercise_files(root))}
    cards = {c.id: c for f in deck_files(root) for c in load_deck(f)}
    return ContentIndex(load_tree(root), lessons, exercises, cards)
