from pathlib import Path

import pytest

from skillforge.evaluator import PythonTest
from skillforge.evaluator.python_runner import PythonExecutionError, run_python
from skillforge.evaluator.sql_runner import SqlExecutionError, run_sql

# --- SQL (needs the built test warehouse) -------------------------------------------------


@pytest.mark.integration
def test_run_sql_returns_normalized_result(warehouse: Path) -> None:
    rs = run_sql(
        "select carrier_code, count(*) as n from marts.dim_carrier group by 1 order by 1;",
        warehouse,
    )
    assert rs.columns == ("carrier_code", "n")
    assert rs.types == ("VARCHAR", "BIGINT")
    assert rs.row_count == 5


@pytest.mark.integration
@pytest.mark.parametrize(
    ("sql", "message"),
    [
        ("create table x as select 1", "read-only"),
        ("select * from read_csv('/etc/passwd')", "disabled"),
        ("select 1; select 2", "jedno zapytanie"),
        ("select nope from marts.dim_carrier", "nope"),
        ("   ", "Puste"),
    ],
)
def test_run_sql_rejects(warehouse: Path, sql: str, message: str) -> None:
    with pytest.raises(SqlExecutionError, match=message):
        run_sql(sql, warehouse)


@pytest.mark.integration
def test_run_sql_timeout(warehouse: Path) -> None:
    with pytest.raises(SqlExecutionError, match="limit czasu"):
        run_sql("select count(*) from range(100000000000)", warehouse, timeout_s=0.3)


@pytest.mark.integration
def test_run_sql_truncates(warehouse: Path) -> None:
    rs = run_sql("select * from range(50)", warehouse, max_rows=10)
    assert rs.row_count == 10 and rs.truncated


def test_run_sql_missing_warehouse(tmp_path: Path) -> None:
    with pytest.raises(SqlExecutionError, match="data build"):
        run_sql("select 1", tmp_path / "nope.duckdb")


# --- Python ---------------------------------------------------------------------------------

TESTS = [
    PythonTest(name="adds", args=[1, 2], expected=3),
    PythonTest(name="floats", args=[0.1, 0.2], expected=0.3),
    PythonTest(name="kwargs", kwargs={"a": 2, "b": 5}, expected=7),
]


def test_run_python_all_pass() -> None:
    results = run_python("def add(a, b):\n    return a + b\n", "add", TESTS)
    assert [r.passed for r in results] == [True, True, True]


def test_run_python_wrong_answer_and_exception() -> None:
    code = "def add(a, b):\n    if a == 2:\n        raise ValueError('boom')\n    return a - b\n"
    results = run_python(code, "add", TESTS)
    assert [r.passed for r in results] == [False, False, False]
    assert results[0].got == -1
    assert results[2].error == "ValueError: boom"


def test_run_python_structures() -> None:
    code = "def f():\n    return {'a': [1, 2.0000000001], 'b': None}\n"
    expected = {"a": [1, 2], "b": None}
    assert run_python(code, "f", [PythonTest(name="t", expected=expected)])[0].passed


def test_run_python_load_errors() -> None:
    with pytest.raises(PythonExecutionError, match="SyntaxError"):
        run_python("def add(:\n", "add", TESTS)
    with pytest.raises(PythonExecutionError, match="add"):
        run_python("def other():\n    pass\n", "add", TESTS)


def test_run_python_timeout() -> None:
    with pytest.raises(PythonExecutionError, match="limit czasu"):
        run_python("def add(a, b):\n    while True:\n        pass\n", "add", TESTS, timeout_s=1)
