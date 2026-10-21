"""Freeze the expected result of a SQL exercise by running its reference solution.

Snapshots are committed and reviewed like code. Validation later re-runs the reference and fails
on any drift, instead of silently moving the goalposts.
"""

from __future__ import annotations

from pathlib import Path

from skillforge.content.models import Exercise
from skillforge.evaluator.resultset import ResultSet
from skillforge.evaluator.sql_runner import run_sql


def snapshot_exercise(exercise: Exercise, warehouse: Path) -> ResultSet | None:
    """Write ``<id>.expected.json`` for SQL exercises. Python ones carry expectations in YAML."""
    if exercise.kind != "sql":
        return None
    result = run_sql(exercise.reference, warehouse)
    if result.truncated:
        raise ValueError(f"{exercise.id}: reference result too large to snapshot")
    if not exercise.compare.order_matters:
        result = result.sorted()
    result.to_json_file(exercise.expected_path)
    return result
