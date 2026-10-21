import json
from pathlib import Path

from typer.testing import CliRunner

from skillforge.cli import app

runner = CliRunner()


def invoke(*args: str) -> str:
    result = runner.invoke(app, list(args))
    assert result.exit_code == 0, result.output
    return result.output


def test_quiz_summary_export_import(tmp_path: Path) -> None:
    invoke("progress", "record-quiz", "--topic", "ae.dbt-layers", "--score", "4", "--total", "5")
    data = json.loads(invoke("progress", "summary"))
    assert data["quizzes"][0]["score"] == 4

    out = tmp_path / "export.json"
    assert "1 events" in invoke("progress", "export", "--out", str(out))
    assert "0 new events" in invoke("progress", "import", str(out))


def test_attempts_missing_exercise_fails() -> None:
    result = runner.invoke(app, ["progress", "attempts", "nope"])
    assert result.exit_code == 1


def test_brag_markdown_empty() -> None:
    assert "# Brag doc" in invoke("progress", "brag")
