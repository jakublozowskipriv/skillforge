from pathlib import Path

import pytest

from skillforge.evaluator import (
    EvalContext,
    PythonCase,
    PythonTest,
    SqlCase,
    evaluate,
    reference_candidate,
    run_suite,
)
from skillforge.evaluator.sql_runner import run_sql

REFERENCE = """
select c.carrier_code, round(avg(f.is_on_time::int), 4) as on_time_rate
from marts.fct_shipments f join marts.dim_carrier c using (carrier_id)
where f.delivered_at is not null
group by 1
"""


@pytest.fixture
def sql_case(warehouse: Path) -> SqlCase:
    return SqlCase(
        id="t-sql",
        question="On-time rate per carrier",
        reference=REFERENCE,
        expected=run_sql(REFERENCE, warehouse),
    )


PY_CASE = PythonCase(
    id="t-py",
    question="Add two numbers",
    reference="def add(a, b):\n    return a + b\n",
    function="add",
    tests=(
        PythonTest(name="1+2", args=[1, 2], expected=3),
        PythonTest(name="0+5", args=[0, 5], expected=5),
    ),
)


@pytest.mark.integration
def test_reference_passes_and_wrong_candidate_fails(sql_case: SqlCase, warehouse: Path) -> None:
    ctx = EvalContext(warehouse)
    ok = evaluate(sql_case, reference_candidate(sql_case), ctx)
    assert ok.passed and ok.score == 1.0 and ok.error is None

    wrong = REFERENCE.replace("where f.delivered_at is not null", "where f.carrier_id <> 1")
    bad = evaluate(sql_case, wrong, ctx)
    assert not bad.passed
    assert bad.diff is not None and bad.diff.missing_rows
    assert bad.to_dict()["diff_summary"]


@pytest.mark.integration
def test_sql_error_is_reported_not_raised(sql_case: SqlCase, warehouse: Path) -> None:
    result = evaluate(sql_case, "select from", EvalContext(warehouse))
    assert not result.passed and result.error


def test_python_case_partial_score(tmp_path: Path) -> None:
    ctx = EvalContext(tmp_path)
    assert evaluate(PY_CASE, PY_CASE.reference, ctx).passed
    half = evaluate(PY_CASE, "def add(a, b):\n    return b\n", ctx)
    assert not half.passed and half.score == 0.5


@pytest.mark.integration
def test_run_suite_with_reference_provider(sql_case: SqlCase, warehouse: Path) -> None:
    report = run_suite([sql_case, PY_CASE], reference_candidate, EvalContext(warehouse))
    assert report.pass_rate == 1.0 and report.mean_score == 1.0 and not report.failed
