import json
from pathlib import Path

import pytest

from skillforge import paths
from skillforge.content.loader import load_content, load_exercise, split_frontmatter
from skillforge.content.snapshot import snapshot_exercise
from skillforge.content.validate import validate_golden_set, validate_structure

TREE = """\
paths:
  - id: test
    title: Test
    topics:
      - id: ts.basics
        title: Basics
"""

LESSON = """\
---
id: ts-01
path: test
topic: ts.basics
title: Basics
minutes: 15
exercises: [t-ex-01]
---
# Basics

Text.

## Jak zastosować w pracy

- Do it.
"""

EXERCISE = """\
id: t-ex-01
title: Carriers
kind: sql
lesson: ts-01
topic: ts.basics
difficulty: 1
question: List carrier codes.
reference: select carrier_code from marts.dim_carrier
"""

CARDS = """\
cards:
  - id: ts-c-01
    topic: ts.basics
    lesson: ts-01
    front: Q?
    back: A.
"""


@pytest.fixture
def content(tmp_path: Path) -> Path:
    base = tmp_path / "paths" / "test"
    for sub in ("lessons", "exercises", "cards"):
        (base / sub).mkdir(parents=True)
    (tmp_path / "tree.yaml").write_text(TREE, encoding="utf-8")
    (base / "lessons" / "ts-01.md").write_text(LESSON, encoding="utf-8")
    (base / "exercises" / "t-ex-01.yaml").write_text(EXERCISE, encoding="utf-8")
    (base / "exercises" / "t-ex-01.expected.json").write_text(
        '{"columns": ["carrier_code"], "rows": []}', encoding="utf-8"
    )
    (base / "cards" / "deck.yaml").write_text(CARDS, encoding="utf-8")
    return tmp_path


def messages(root: Path) -> list[str]:
    return [str(p) for p in validate_structure(root)]


def test_repo_content_structure_is_valid() -> None:
    assert messages(paths.CONTENT_DIR) == []


def test_valid_fixture_and_index(content: Path) -> None:
    assert messages(content) == []
    index = load_content(content)
    assert [e.id for e in index.exercises_for_lesson("ts-01")] == ["t-ex-01"]
    assert [c.id for c in index.cards_for_lesson("ts-01")] == ["ts-c-01"]
    assert index.tree.path_of("ts.basics") is not None


def test_frontmatter_parsing() -> None:
    meta, body = split_frontmatter("---\nid: x\n---\n# Title\n")
    assert meta == {"id": "x"} and body == "# Title\n"


def test_missing_apply_at_work_section(content: Path) -> None:
    lesson = content / "paths/test/lessons/ts-01.md"
    lesson.write_text(LESSON.replace("## Jak zastosować w pracy", "## Podsumowanie"), "utf-8")
    assert any("Jak zastosować w pracy" in m for m in messages(content))


def test_unknown_references(content: Path) -> None:
    ex = content / "paths/test/exercises/t-ex-01.yaml"
    ex.write_text(EXERCISE.replace("lesson: ts-01", "lesson: nope"), "utf-8")
    cards = content / "paths/test/cards/deck.yaml"
    cards.write_text(CARDS.replace("ts.basics", "ts.unknown"), "utf-8")
    found = messages(content)
    assert any("unknown lesson `nope`" in m for m in found)
    assert any("unknown topic `ts.unknown`" in m for m in found)


def test_duplicate_ids_and_file_names(content: Path) -> None:
    dup = content / "paths/test/exercises/t-ex-02.yaml"
    dup.write_text(EXERCISE, "utf-8")
    found = messages(content)
    assert any("duplicate exercise id" in m for m in found)
    assert any("file name must equal id" in m for m in found)


def test_schema_errors_are_reported(content: Path) -> None:
    bad = content / "paths/test/exercises/t-ex-03.yaml"
    bad.write_text(EXERCISE.replace("t-ex-01", "t-ex-03") + "difficulty_typo: 3\n", "utf-8")
    assert any("t-ex-03" in m and "invalid" in m for m in messages(content))


def test_missing_snapshot(content: Path) -> None:
    (content / "paths/test/exercises/t-ex-01.expected.json").unlink()
    assert any("missing snapshot" in m for m in messages(content))


@pytest.mark.integration
def test_golden_set_snapshot_and_drift(content: Path, warehouse: Path) -> None:
    ex = load_exercise(content / "paths/test/exercises/t-ex-01.yaml")
    assert validate_golden_set(content, warehouse)  # placeholder snapshot is wrong
    snapshot_exercise(ex, warehouse)
    assert validate_golden_set(content, warehouse) == []

    data = json.loads(ex.expected_path.read_text(encoding="utf-8"))
    data["rows"] = data["rows"][1:]
    ex.expected_path.write_text(json.dumps(data), encoding="utf-8")
    problems = validate_golden_set(content, warehouse)
    assert len(problems) == 1 and "does not match" in problems[0].message
