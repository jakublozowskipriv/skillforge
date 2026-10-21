"""Golden cases, candidates and evaluation results — the evaluator's public model.

    evaluate(case, candidate, ctx) -> EvalResult
    run_suite(cases, provider, ctx) -> SuiteReport

``provider`` maps a case to a candidate answer. Today: the human (UI) or the reference solution
(content validation). Next phase: an LLM agent — same suite, same metrics, comparable reports.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from skillforge.evaluator.compare import CompareSpec, Diff, PartialScore, compare_results
from skillforge.evaluator.compare import partial_score as _partial_score
from skillforge.evaluator.python_runner import (
    PythonExecutionError,
    PythonTest,
    PythonTestResult,
    run_python,
)
from skillforge.evaluator.resultset import ResultSet
from skillforge.evaluator.sql_runner import SqlExecutionError, run_sql


@dataclass(frozen=True)
class SqlCase:
    id: str
    question: str
    reference: str
    expected: ResultSet
    compare: CompareSpec = field(default_factory=CompareSpec)
    kind: Literal["sql"] = "sql"


@dataclass(frozen=True)
class PythonCase:
    id: str
    question: str
    reference: str
    function: str
    tests: tuple[PythonTest, ...]
    compare: CompareSpec = field(default_factory=CompareSpec)
    kind: Literal["python"] = "python"


GoldenCase = SqlCase | PythonCase
CandidateProvider = Callable[[GoldenCase], str]


def reference_candidate(case: GoldenCase) -> str:
    """Provider that answers with the reference solution (used to validate the golden set)."""
    return case.reference


@dataclass(frozen=True)
class EvalContext:
    warehouse: Path
    timeout_s: float = 10.0


@dataclass(frozen=True)
class EvalResult:
    case_id: str
    kind: Literal["sql", "python"]
    passed: bool
    score: float  # 1.0 pass; else partial credit (row F1 for SQL, share of tests for Python)
    duration_ms: float
    error: str | None = None
    diff: Diff | None = None
    actual: ResultSet | None = None
    partial: PartialScore | None = None
    test_results: tuple[PythonTestResult, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """JSON-friendly summary for storing attempts (the full actual result is not stored)."""
        return {
            "case_id": self.case_id,
            "kind": self.kind,
            "passed": self.passed,
            "score": self.score,
            "duration_ms": round(self.duration_ms, 1),
            "error": self.error,
            "diff_summary": self.diff.summary() if self.diff else None,
            "partial": asdict(self.partial) if self.partial else None,
            "tests": [asdict(t) for t in self.test_results],
        }


def _try_partial(expected: ResultSet, actual: ResultSet, spec: CompareSpec) -> PartialScore | None:
    try:
        return _partial_score(expected, actual, spec)
    except NotImplementedError:  # TODO(learn) #3 not done yet — evaluator works without it
        return None


def _evaluate_sql(case: SqlCase, candidate: str, ctx: EvalContext) -> EvalResult:
    start = time.perf_counter()
    try:
        actual = run_sql(candidate, ctx.warehouse, timeout_s=ctx.timeout_s)
    except SqlExecutionError as exc:
        ms = (time.perf_counter() - start) * 1000
        return EvalResult(case.id, "sql", False, 0.0, ms, error=str(exc))
    diff = compare_results(case.expected, actual, case.compare)
    partial = _try_partial(case.expected, actual, case.compare)
    ms = (time.perf_counter() - start) * 1000
    score = 1.0 if diff.is_match else (partial.f1 if partial else 0.0)
    return EvalResult(
        case.id, "sql", diff.is_match, score, ms, diff=diff, actual=actual, partial=partial
    )


def _evaluate_python(case: PythonCase, candidate: str, ctx: EvalContext) -> EvalResult:
    start = time.perf_counter()
    try:
        results = run_python(
            candidate, case.function, case.tests, spec=case.compare, timeout_s=ctx.timeout_s
        )
    except PythonExecutionError as exc:
        ms = (time.perf_counter() - start) * 1000
        return EvalResult(case.id, "python", False, 0.0, ms, error=str(exc))
    ms = (time.perf_counter() - start) * 1000
    passed = sum(r.passed for r in results)
    score = passed / len(results) if results else 0.0
    return EvalResult(
        case.id, "python", passed == len(results), score, ms, test_results=tuple(results)
    )


def evaluate(case: GoldenCase, candidate: str, ctx: EvalContext) -> EvalResult:
    if isinstance(case, SqlCase):
        return _evaluate_sql(case, candidate, ctx)
    return _evaluate_python(case, candidate, ctx)


@dataclass(frozen=True)
class SuiteReport:
    results: tuple[EvalResult, ...]

    @property
    def pass_rate(self) -> float:
        return sum(r.passed for r in self.results) / len(self.results) if self.results else 0.0

    @property
    def mean_score(self) -> float:
        return sum(r.score for r in self.results) / len(self.results) if self.results else 0.0

    @property
    def failed(self) -> tuple[EvalResult, ...]:
        return tuple(r for r in self.results if not r.passed)


def run_suite(
    cases: Iterable[GoldenCase], provider: CandidateProvider, ctx: EvalContext
) -> SuiteReport:
    return SuiteReport(tuple(evaluate(case, provider(case), ctx) for case in cases))
