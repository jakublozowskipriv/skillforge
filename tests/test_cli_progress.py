import json
from pathlib import Path

import pytest
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


@pytest.mark.integration
def test_check_from_file(tmp_path: Path, warehouse: Path) -> None:
    from skillforge import paths

    ok = tmp_path / "ok.sql"
    ok.write_text("select carrier_code from marts.dim_carrier", encoding="utf-8")
    bad = tmp_path / "bad.sql"
    bad.write_text("select 1 as x", encoding="utf-8")
    # ae-ex-08 snapshot comes from the full warehouse; on the small test warehouse we only check
    # that the command runs, reports and records attempts.
    args = ["check", "ae-ex-08", str(bad), "--record", "--warehouse", str(warehouse)]
    result = runner.invoke(app, args)
    assert result.exit_code == 1 and "FAIL ae-ex-08" in result.output
    assert "Brakujące kolumny" in result.output
    unknown = runner.invoke(app, ["check", "nope", str(ok)])
    assert unknown.exit_code == 2
    assert paths.PROGRESS_DB_PATH.exists()


@pytest.mark.integration
def test_data_schema(warehouse: Path) -> None:
    out = invoke("data", "schema", "marts", "--warehouse", str(warehouse))
    assert "marts.fct_shipments: shipment_id bigint" in out
    assert "raw." not in out


@pytest.mark.integration
def test_sql_explore(tmp_path: Path, warehouse: Path) -> None:
    from skillforge import paths

    out = invoke(
        "sql",
        "select carrier_code from marts.dim_carrier order by 1",
        "--warehouse",
        str(warehouse),
    )
    assert "ECO" in out and "5 rows" in out
    query = tmp_path / "q.sql"
    query.write_text("select * from range(100)", encoding="utf-8")
    out = invoke("sql", "--file", str(query), "--limit", "5", "--warehouse", str(warehouse))
    assert "5 rows (more rows available" in out
    bad = runner.invoke(app, ["sql", "select nope", "--warehouse", str(warehouse)])
    assert bad.exit_code == 1
    assert runner.invoke(app, ["sql"]).exit_code == 2
    assert not paths.PROGRESS_DB_PATH.exists()  # exploring never records anything
