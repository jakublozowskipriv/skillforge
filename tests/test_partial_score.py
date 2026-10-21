"""Spec for TODO(learn) #3 — ``partial_score`` in src/skillforge/evaluator/compare.py.

The tests are marked xfail(strict) while the stub raises NotImplementedError. Once your
implementation passes, pytest reports XPASS(strict) as a failure: remove the marker then.
"""

import pytest

from skillforge.evaluator import CompareSpec, ResultSet
from skillforge.evaluator.compare import partial_score

pytestmark = pytest.mark.xfail(raises=NotImplementedError, strict=True)

COLS = ["carrier", "n"]


def rs(rows: list[tuple[object, ...]], columns: list[str] = COLS) -> ResultSet:
    return ResultSet.from_rows(columns, rows)


EXPECTED = rs([("SWIFT", 10), ("PAKO", 5), ("ECO", 2)])


def test_identical_is_perfect() -> None:
    s = partial_score(EXPECTED, EXPECTED)
    assert (s.precision, s.recall, s.f1) == (1.0, 1.0, 1.0)


def test_one_wrong_row() -> None:
    s = partial_score(EXPECTED, rs([("SWIFT", 10), ("PAKO", 5), ("ECO", 3)]))
    assert s.precision == pytest.approx(2 / 3)
    assert s.recall == pytest.approx(2 / 3)
    assert s.f1 == pytest.approx(2 / 3)


def test_subset_has_full_precision() -> None:
    s = partial_score(EXPECTED, rs([("SWIFT", 10)]))
    assert s.precision == 1.0
    assert s.recall == pytest.approx(1 / 3)
    assert s.f1 == pytest.approx(0.5)


def test_duplicates_lower_precision() -> None:
    s = partial_score(rs([("SWIFT", 10)]), rs([("SWIFT", 10), ("SWIFT", 10)]))
    assert s.precision == 0.5
    assert s.recall == 1.0


def test_float_tolerance_applies() -> None:
    expected = rs([("SWIFT", 0.8)])
    s = partial_score(expected, rs([("SWIFT", 0.801)]), CompareSpec(abs_tol=0.01))
    assert s.f1 == 1.0


def test_column_order_and_case_do_not_matter() -> None:
    s = partial_score(EXPECTED, rs([(10, "SWIFT"), (5, "PAKO"), (2, "ECO")], ["N", "Carrier"]))
    assert s.f1 == 1.0


def test_incompatible_columns_score_zero() -> None:
    s = partial_score(EXPECTED, rs([("SWIFT", 10)], ["carrier", "cnt"]))
    assert (s.precision, s.recall, s.f1) == (0.0, 0.0, 0.0)


def test_empty_actual_scores_zero() -> None:
    s = partial_score(EXPECTED, rs([]))
    assert (s.precision, s.recall, s.f1) == (0.0, 0.0, 0.0)


def test_both_empty_is_perfect() -> None:
    s = partial_score(rs([]), rs([]))
    assert (s.precision, s.recall, s.f1) == (1.0, 1.0, 1.0)
