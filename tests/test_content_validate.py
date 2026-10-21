import json
from pathlib import Path

import pytest

from skillforge.content.loader import load_exercise
from skillforge.content.snapshot import snapshot_exercise
from skillforge.content.validate import validate_exercises

pytestmark = pytest.mark.integration

EXERCISE = """\
id: t-ex-01
title: Carriers
kind: sql
topic: test
difficulty: 1
question: List carrier codes.
reference: select carrier_code from marts.dim_carrier
"""


@pytest.fixture
def content(tmp_path: Path) -> Path:
    ex_dir = tmp_path / "paths" / "test" / "exercises"
    ex_dir.mkdir(parents=True)
    (ex_dir / "t-ex-01.yaml").write_text(EXERCISE, encoding="utf-8")
    return tmp_path


def test_snapshot_then_validate_passes(content: Path, warehouse: Path) -> None:
    path = content / "paths/test/exercises/t-ex-01.yaml"
    assert validate_exercises(content, warehouse)[0].message.startswith("missing snapshot")
    snapshot_exercise(load_exercise(path), warehouse)
    assert validate_exercises(content, warehouse) == []


def test_drift_is_detected(content: Path, warehouse: Path) -> None:
    path = content / "paths/test/exercises/t-ex-01.yaml"
    ex = load_exercise(path)
    snapshot_exercise(ex, warehouse)
    data = json.loads(ex.expected_path.read_text(encoding="utf-8"))
    data["rows"] = data["rows"][1:]
    ex.expected_path.write_text(json.dumps(data), encoding="utf-8")
    problems = validate_exercises(content, warehouse)
    assert len(problems) == 1 and "does not match" in problems[0].message


def test_schema_errors_are_reported(content: Path, warehouse: Path) -> None:
    bad = content / "paths/test/exercises/t-ex-02.yaml"
    bad.write_text(EXERCISE.replace("t-ex-01", "t-ex-02") + "difficulty_typo: 3\n", "utf-8")
    problems = validate_exercises(content, warehouse)
    assert any("t-ex-02" in p.where and "invalid" in p.message for p in problems)
