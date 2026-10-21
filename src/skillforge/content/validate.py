"""Validate content: schemas, cross-references, and the golden set itself.

Two levels:
- :func:`validate_structure` — fast, no warehouse: schemas, unique ids, references to the tree and
  lessons, the mandatory "Jak zastosować w pracy" section. Runs in unit tests.
- :func:`validate_golden_set` — every reference solution must reproduce its frozen expectation.
  Needs the full-scale warehouse; runs in CI after `skillforge data build` and in `/next-lesson`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from skillforge.content.loader import (
    ContentError,
    deck_files,
    exercise_files,
    lesson_files,
    load_deck,
    load_exercise,
    load_lesson,
    load_tree,
)
from skillforge.content.models import APPLY_AT_WORK_HEADING, Card, CompetenceTree, Exercise, Lesson
from skillforge.evaluator import EvalContext, evaluate, reference_candidate


@dataclass(frozen=True)
class Problem:
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.where}: {self.message}"


def _try_load[T](
    path: Path, root: Path, loader: Callable[[Path], T], problems: list[Problem]
) -> T | None:
    try:
        return loader(path)
    except (ValidationError, ContentError, ValueError, OSError) as exc:
        problems.append(Problem(str(path.relative_to(root)), f"invalid: {exc}"))
        return None


@dataclass(frozen=True)
class _Loaded:
    tree: CompetenceTree | None
    lessons: list[Lesson]
    exercises: list[Exercise]
    cards: list[tuple[Path, Card]]


def _load_all(root: Path, problems: list[Problem]) -> _Loaded:
    tree = _try_load(root / "tree.yaml", root, lambda p: load_tree(p.parent), problems)
    lessons = [
        lesson for f in lesson_files(root) if (lesson := _try_load(f, root, load_lesson, problems))
    ]
    exercises = [
        ex for f in exercise_files(root) if (ex := _try_load(f, root, load_exercise, problems))
    ]
    cards: list[tuple[Path, Card]] = []
    for f in deck_files(root):
        deck = _try_load(f, root, load_deck, problems)
        cards.extend((f, c) for c in deck or [])
    return _Loaded(tree, lessons, exercises, cards)


def validate_structure(root: Path) -> list[Problem]:
    problems: list[Problem] = []
    loaded = _load_all(root, problems)

    def rel(path: Path | None) -> str:
        return str(path.relative_to(root)) if path else "?"

    def check_unique(kind: str, items: list[tuple[str, str]]) -> None:
        seen: dict[str, str] = {}
        for item_id, where in items:
            if item_id in seen:
                problems.append(
                    Problem(where, f"duplicate {kind} id `{item_id}` ({seen[item_id]})")
                )
            seen.setdefault(item_id, where)

    if loaded.tree is not None:
        tree = loaded.tree
        check_unique("path", [(p.id, "tree.yaml") for p in tree.paths])
        check_unique("topic", [(t.id, "tree.yaml") for p in tree.paths for t in p.topics])
        topics = tree.topic_ids
        path_ids = {p.id for p in tree.paths}
    else:
        topics, path_ids = set(), set()

    lesson_ids = {lesson.id for lesson in loaded.lessons}
    exercise_ids = {e.id for e in loaded.exercises}
    check_unique("lesson", [(x.id, rel(x.source_path)) for x in loaded.lessons])
    check_unique("exercise", [(x.id, rel(x.source_path)) for x in loaded.exercises])
    check_unique("card", [(c.id, rel(f)) for f, c in loaded.cards])

    for lesson in loaded.lessons:
        where = rel(lesson.source_path)
        assert lesson.source_path is not None
        if lesson.source_path.stem != lesson.id:
            problems.append(Problem(where, f"file name must equal id `{lesson.id}`"))
        if lesson.source_path.parent.parent.name != lesson.path:
            problems.append(Problem(where, f"`path: {lesson.path}` does not match its folder"))
        if path_ids and lesson.path not in path_ids:
            problems.append(Problem(where, f"unknown path `{lesson.path}`"))
        if topics and lesson.topic not in topics:
            problems.append(Problem(where, f"unknown topic `{lesson.topic}` (add it to tree.yaml)"))
        if not lesson.has_apply_at_work:
            problems.append(Problem(where, f"missing section `{APPLY_AT_WORK_HEADING}`"))
        for ex_id in lesson.exercises:
            if ex_id not in exercise_ids:
                problems.append(Problem(where, f"lists unknown exercise `{ex_id}`"))

    for ex in loaded.exercises:
        where = rel(ex.source_path)
        assert ex.source_path is not None
        if ex.source_path.stem != ex.id:
            problems.append(Problem(where, f"file name must equal id `{ex.id}`"))
        if topics and ex.topic not in topics:
            problems.append(Problem(where, f"unknown topic `{ex.topic}`"))
        if ex.lesson and ex.lesson not in lesson_ids:
            problems.append(Problem(where, f"unknown lesson `{ex.lesson}`"))
        if ex.kind == "sql" and not ex.expected_path.exists():
            problems.append(Problem(where, "missing snapshot — run `skillforge content snapshot`"))

    for f, card in loaded.cards:
        if topics and card.topic not in topics:
            problems.append(Problem(rel(f), f"card `{card.id}`: unknown topic `{card.topic}`"))
        if card.lesson and card.lesson not in lesson_ids:
            problems.append(Problem(rel(f), f"card `{card.id}`: unknown lesson `{card.lesson}`"))
    return problems


def validate_golden_set(root: Path, warehouse: Path) -> list[Problem]:
    """Run every reference solution through the evaluator against its frozen expectation."""
    problems: list[Problem] = []
    ctx = EvalContext(warehouse)
    for path in exercise_files(root):
        ex = _try_load(path, root, load_exercise, problems)
        if ex is None or (ex.kind == "sql" and not ex.expected_path.exists()):
            continue  # reported by validate_structure
        case = ex.to_case()
        result = evaluate(case, reference_candidate(case), ctx)
        if result.passed:
            continue
        detail = result.error or "; ".join(result.diff.summary() if result.diff else [])
        if result.test_results:
            failed = [t.name for t in result.test_results if not t.passed]
            detail = f"reference fails tests: {', '.join(failed)}"
        problems.append(
            Problem(str(path.relative_to(root)), f"reference does not match expectation: {detail}")
        )
    return problems


def validate_content(root: Path, warehouse: Path | None) -> list[Problem]:
    problems = validate_structure(root)
    if warehouse is not None:
        problems += validate_golden_set(root, warehouse)
    return problems
