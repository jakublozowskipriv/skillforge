from datetime import date, datetime
from decimal import Decimal

from skillforge.evaluator import CompareSpec, ResultSet, compare_results


def rs(columns: list[str], rows: list[tuple[object, ...]]) -> ResultSet:
    return ResultSet.from_rows(columns, rows)


EXPECTED = rs(["carrier", "n", "rate"], [("SWIFT", 10, 0.8), ("PAKO", 5, 0.75)])


def test_identical_results_match() -> None:
    assert compare_results(EXPECTED, EXPECTED).is_match


def test_row_order_ignored_by_default() -> None:
    actual = rs(["carrier", "n", "rate"], [("PAKO", 5, 0.75), ("SWIFT", 10, 0.8)])
    assert compare_results(EXPECTED, actual).is_match


def test_float_tolerance_and_numeric_types() -> None:
    actual = rs(
        ["carrier", "n", "rate"],
        [("SWIFT", 10.0, 0.8000000001), ("PAKO", Decimal("5"), Decimal("0.75"))],
    )
    assert compare_results(EXPECTED, actual).is_match


def test_float_outside_tolerance_is_cell_mismatch() -> None:
    actual = rs(["carrier", "n", "rate"], [("SWIFT", 10, 0.81), ("PAKO", 5, 0.75)])
    diff = compare_results(EXPECTED, actual)
    assert not diff.is_match
    assert len(diff.cell_mismatches) == 1
    assert diff.cell_mismatches[0].columns == ("rate",)
    assert any("rate" in line for line in diff.summary())


def test_custom_tolerance() -> None:
    actual = rs(["carrier", "n", "rate"], [("SWIFT", 10, 0.801), ("PAKO", 5, 0.75)])
    assert compare_results(EXPECTED, actual, CompareSpec(abs_tol=0.01)).is_match


def test_columns_matched_by_name_case_insensitive_any_order() -> None:
    actual = rs(["RATE", "Carrier", "n"], [(0.8, "SWIFT", 10), (0.75, "PAKO", 5)])
    assert compare_results(EXPECTED, actual).is_match


def test_missing_alias_is_explained() -> None:
    actual = rs(["carrier", "count_star()", "rate"], [("SWIFT", 10, 0.8), ("PAKO", 5, 0.75)])
    diff = compare_results(EXPECTED, actual)
    assert not diff.is_match
    assert any("aliasów" in line for line in diff.column_issues)


def test_match_by_position_ignores_names() -> None:
    actual = rs(["a", "b", "c"], [("SWIFT", 10, 0.8), ("PAKO", 5, 0.75)])
    assert compare_results(EXPECTED, actual, CompareSpec(match_columns="position")).is_match


def test_duplicates_count_fanout_detected() -> None:
    actual = rs(
        ["carrier", "n", "rate"], [("SWIFT", 10, 0.8), ("SWIFT", 10, 0.8), ("PAKO", 5, 0.75)]
    )
    diff = compare_results(EXPECTED, actual)
    assert not diff.is_match
    assert diff.extra_rows == (("SWIFT", 10, 0.8),)
    assert any("JOIN" in note for note in diff.notes)


def test_missing_rows_reported() -> None:
    actual = rs(["carrier", "n", "rate"], [("SWIFT", 10, 0.8)])
    diff = compare_results(EXPECTED, actual)
    assert diff.missing_rows == (("PAKO", 5, 0.75),)
    assert diff.actual_row_count == 1


def test_order_matters_when_requested() -> None:
    actual = rs(["carrier", "n", "rate"], [("PAKO", 5, 0.75), ("SWIFT", 10, 0.8)])
    diff = compare_results(EXPECTED, actual, CompareSpec(order_matters=True))
    assert not diff.is_match
    assert diff.order_issues == (0, 1)
    assert any("ORDER BY" in note for note in diff.notes)


def test_nulls_and_bools() -> None:
    expected = rs(["x", "flag"], [(None, True)])
    assert compare_results(expected, rs(["x", "flag"], [(None, True)])).is_match
    assert not compare_results(expected, rs(["x", "flag"], [(0, True)])).is_match
    assert not compare_results(expected, rs(["x", "flag"], [(None, 1)])).is_match


def test_dates_compare_after_json_roundtrip() -> None:
    fresh = rs(["d", "ts"], [(date(2026, 3, 1), datetime(2026, 3, 1, 12, 30))])
    snapshot = ResultSet.from_dict(fresh.to_dict())
    assert snapshot.rows == (("2026-03-01", "2026-03-01 12:30:00"),)
    assert compare_results(snapshot, fresh).is_match


def test_integral_float_vs_int_across_buckets() -> None:
    expected = rs(["k", "v"], [(1, 3)])
    actual = rs(["k", "v"], [(1, 2.99999999999)])
    assert compare_results(expected, actual).is_match
