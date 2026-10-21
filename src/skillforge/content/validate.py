"""Validate the golden set: every reference solution must reproduce its frozen expectation.

Run in CI after `skillforge data build` and by `/next-lesson` after generating content.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from skillforge.content.loader import load_exercise
from skillforge.evaluator import EvalContext, evaluate, reference_candidate


@dataclass(frozen=True)
class Problem:
    where: str
    message: str


def validate_exercises(content_dir: Path, warehouse: Path) -> list[Problem]:
    problems: list[Problem] = []
    seen: dict[str, Path] = {}
    ctx = EvalContext(warehouse)
    for path in sorted(content_dir.glob("paths/*/exercises/*.yaml")):
        where = str(path.relative_to(content_dir))
        try:
            ex = load_exercise(path)
        except (ValidationError, ValueError) as exc:
            problems.append(Problem(where, f"invalid YAML/schema: {exc}"))
            continue
        if path.stem != ex.id:
            problems.append(Problem(where, f"file name must equal id `{ex.id}`"))
        if ex.id in seen:
            problems.append(Problem(where, f"duplicate id `{ex.id}` (also in {seen[ex.id]})"))
        seen[ex.id] = path
        if ex.kind == "sql" and not ex.expected_path.exists():
            problems.append(Problem(where, "missing snapshot — run `skillforge content snapshot`"))
            continue
        result = evaluate(ex.to_case(), reference_candidate(ex.to_case()), ctx)
        if not result.passed:
            detail = result.error or "; ".join(result.diff.summary() if result.diff else [])
            if result.test_results:
                failed = [t.name for t in result.test_results if not t.passed]
                detail = f"reference fails tests: {', '.join(failed)}"
            problems.append(Problem(where, f"reference does not match expectation: {detail}"))
    return problems
