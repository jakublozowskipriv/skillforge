"""Compare a candidate result with the golden expected result and explain the difference.

Defaults reflect how analysts judge "the same answer":
- row order does not matter (unless the question asks for ordering → ``order_matters: true``),
- floats are equal within a tolerance (``avg()`` on another engine/plan may differ in last bits),
- columns are matched by name (case-insensitive), so column order does not matter.

The comparison is a *multiset* comparison: duplicates count. Returning a row twice is a bug
(fan-out after a join!), not a cosmetic issue.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from skillforge.evaluator.resultset import Cell, ResultSet, Row

MAX_REPORTED_ROWS = 50


class CompareSpec(BaseModel):
    """Per-case comparison settings (``compare:`` block in exercise YAML)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    order_matters: bool = False
    match_columns: Literal["name", "position"] = "name"
    rel_tol: float = 1e-6
    abs_tol: float = 1e-9


def cells_equal(a: Cell, b: Cell, spec: CompareSpec) -> bool:
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, int | float) and isinstance(b, int | float):
        return math.isclose(a, b, rel_tol=spec.rel_tol, abs_tol=spec.abs_tol)
    return a == b


def rows_equal(a: Row, b: Row, spec: CompareSpec) -> bool:
    return len(a) == len(b) and all(cells_equal(x, y, spec) for x, y in zip(a, b, strict=True))


def _bucket_key(row: Row) -> tuple[Cell, ...]:
    """Exact-match part of a row: everything except non-integral numbers.

    Rows can only be tolerance-equal if their bucket keys are equal (or a float sits right at an
    integer — handled by the cross-bucket fallback in :func:`match_rows`).
    """
    key: list[Cell] = []
    for cell in row:
        if isinstance(cell, float) and not isinstance(cell, bool):
            key.append(int(cell) if cell.is_integer() else "<float>")
        else:
            key.append(cell)
    return tuple(key)


@dataclass(frozen=True)
class RowMatch:
    matched: int
    missing: tuple[Row, ...]  # expected rows with no counterpart in actual
    extra: tuple[Row, ...]  # actual rows with no counterpart in expected


def _greedy_match(
    expected: list[Row], actual: list[Row], spec: CompareSpec
) -> tuple[int, list[Row], list[Row]]:
    remaining = list(actual)
    missing: list[Row] = []
    matched = 0
    for exp in expected:
        for i, act in enumerate(remaining):
            if rows_equal(exp, act, spec):
                del remaining[i]
                matched += 1
                break
        else:
            missing.append(exp)
    return matched, missing, remaining


def match_rows(expected: tuple[Row, ...], actual: tuple[Row, ...], spec: CompareSpec) -> RowMatch:
    """Multiset matching with float tolerance, ignoring order.

    Rows are first bucketed by their exact-match part (strings, ints, dates...) so that matching
    is ~linear for typical results; only rows inside a bucket are compared pairwise.
    """
    exp_buckets: dict[tuple[Cell, ...], list[Row]] = defaultdict(list)
    act_buckets: dict[tuple[Cell, ...], list[Row]] = defaultdict(list)
    for row in expected:
        exp_buckets[_bucket_key(row)].append(row)
    for row in actual:
        act_buckets[_bucket_key(row)].append(row)

    matched = 0
    left_missing: list[Row] = []
    left_extra: list[Row] = []
    for key, exp_rows in exp_buckets.items():
        m, miss, extra = _greedy_match(exp_rows, act_buckets.pop(key, []), spec)
        matched += m
        left_missing.extend(miss)
        left_extra.extend(extra)
    for rows in act_buckets.values():
        left_extra.extend(rows)

    # Fallback across buckets (e.g. 2.9999999 vs 3): leftovers are usually few.
    m, missing, extra = _greedy_match(left_missing, left_extra, spec)
    return RowMatch(matched=matched + m, missing=tuple(missing), extra=tuple(extra))


@dataclass(frozen=True)
class CellMismatch:
    """A missing and an extra row that agree on most columns: likely the same row, wrong value."""

    expected_row: Row
    actual_row: Row
    columns: tuple[str, ...]


@dataclass(frozen=True)
class Diff:
    expected_columns: tuple[str, ...]
    actual_columns: tuple[str, ...]
    expected_row_count: int
    actual_row_count: int
    column_issues: tuple[str, ...] = ()
    missing_rows: tuple[Row, ...] = ()
    extra_rows: tuple[Row, ...] = ()
    cell_mismatches: tuple[CellMismatch, ...] = ()
    order_issues: tuple[int, ...] = ()  # 0-based positions differing when order matters
    notes: tuple[str, ...] = field(default=())

    @property
    def is_match(self) -> bool:
        return not (self.column_issues or self.missing_rows or self.extra_rows or self.order_issues)

    def summary(self) -> list[str]:
        """Human-readable explanation (Polish UI)."""
        if self.is_match:
            return ["Wynik zgodny z oczekiwanym."]
        lines = list(self.column_issues)
        if self.expected_row_count != self.actual_row_count:
            lines.append(
                f"Liczba wierszy: oczekiwano {self.expected_row_count}, "
                f"otrzymano {self.actual_row_count}."
            )
        if self.missing_rows:
            lines.append(f"Brakuje {len(self.missing_rows)} oczekiwanych wierszy.")
        if self.extra_rows:
            lines.append(f"{len(self.extra_rows)} wierszy nadmiarowych (nie ma ich w oczekiwanym).")
        if self.cell_mismatches:
            cols = sorted({c for m in self.cell_mismatches for c in m.columns})
            lines.append(f"Różne wartości w kolumnach: {', '.join(cols)}.")
        if self.order_issues:
            lines.append(
                f"Kolejność wierszy ma znaczenie: pierwsza różnica na pozycji "
                f"{self.order_issues[0] + 1}."
            )
        lines.extend(self.notes)
        return lines


@dataclass(frozen=True)
class PartialScore:
    precision: float
    recall: float
    f1: float


def _align_columns(
    expected: ResultSet, actual: ResultSet, spec: CompareSpec
) -> tuple[tuple[Row, ...] | None, list[str]]:
    """Reorder actual columns to match expected. Returns (aligned rows | None, issues)."""
    if spec.match_columns == "position":
        if len(expected.columns) != len(actual.columns):
            return None, [
                f"Liczba kolumn: oczekiwano {len(expected.columns)}, "
                f"otrzymano {len(actual.columns)}."
            ]
        return actual.rows, []

    exp_names = [c.lower() for c in expected.columns]
    act_names = [c.lower() for c in actual.columns]
    issues: list[str] = []
    dupes = sorted({c for c in act_names if act_names.count(c) > 1})
    if dupes:
        issues.append(f"Zduplikowane nazwy kolumn w wyniku: {', '.join(dupes)}.")
    missing = [c for c in exp_names if c not in act_names]
    extra = [c for c in act_names if c not in exp_names]
    if missing:
        issues.append(f"Brakujące kolumny: {', '.join(missing)}.")
    if extra:
        issues.append(f"Nadmiarowe kolumny: {', '.join(extra)}.")
    if missing and len(exp_names) == len(act_names):
        issues.append("Liczba kolumn się zgadza — może brakuje aliasów (`AS nazwa`)?")
    if issues:
        return None, issues
    order = [act_names.index(c) for c in exp_names]
    return tuple(tuple(row[i] for i in order) for row in actual.rows), []


def _pair_mismatches(
    missing: tuple[Row, ...], extra: tuple[Row, ...], columns: tuple[str, ...], spec: CompareSpec
) -> tuple[CellMismatch, ...]:
    pairs: list[CellMismatch] = []
    pool = list(extra[:MAX_REPORTED_ROWS])
    for exp in missing[:MAX_REPORTED_ROWS]:
        best_i, best_same = -1, 0
        for i, act in enumerate(pool):
            same = sum(cells_equal(a, b, spec) for a, b in zip(exp, act, strict=True))
            if same > best_same:
                best_i, best_same = i, same
        if best_i >= 0 and best_same * 2 >= len(columns):
            act = pool.pop(best_i)
            diff_cols = tuple(
                col
                for col, a, b in zip(columns, exp, act, strict=True)
                if not cells_equal(a, b, spec)
            )
            pairs.append(CellMismatch(exp, act, diff_cols))
    return tuple(pairs)


def compare_results(
    expected: ResultSet, actual: ResultSet, spec: CompareSpec | None = None
) -> Diff:
    """Compare and explain. ``diff.is_match`` is the pass/fail verdict (execution accuracy)."""
    spec = spec or CompareSpec()

    def make(**details: Any) -> Diff:
        return Diff(
            expected.columns, actual.columns, expected.row_count, actual.row_count, **details
        )

    aligned, issues = _align_columns(expected, actual, spec)
    if aligned is None:
        return make(column_issues=tuple(issues))

    notes: list[str] = []
    if actual.truncated:
        notes.append("Wynik został obcięty (limit wierszy) — porównanie może być niepełne.")

    if spec.order_matters:
        positions = tuple(
            i
            for i, (e, a) in enumerate(zip(expected.rows, aligned, strict=False))
            if not rows_equal(e, a, spec)
        )
        n = min(len(expected.rows), len(aligned))
        missing = expected.rows[n:]
        extra = aligned[n:]
        if positions and match_rows(expected.rows, aligned, spec).matched == len(expected.rows):
            notes.append("Te same wiersze, ale w innej kolejności — sprawdź ORDER BY.")
        return make(
            missing_rows=missing[:MAX_REPORTED_ROWS],
            extra_rows=extra[:MAX_REPORTED_ROWS],
            order_issues=positions[:MAX_REPORTED_ROWS],
            notes=tuple(notes),
        )

    match = match_rows(expected.rows, aligned, spec)
    mismatches = _pair_mismatches(match.missing, match.extra, expected.columns, spec)
    if match.extra and not match.missing:
        notes.append("Wszystkie oczekiwane wiersze są, ale są też dodatkowe — duplikaty po JOIN?")
    return make(
        missing_rows=match.missing[:MAX_REPORTED_ROWS],
        extra_rows=match.extra[:MAX_REPORTED_ROWS],
        cell_mismatches=mismatches,
        notes=tuple(notes),
    )


def partial_score(
    expected: ResultSet, actual: ResultSet, spec: CompareSpec | None = None
) -> PartialScore:
    """Row-level precision / recall / F1 of ``actual`` against ``expected``.

    TODO(learn) #3 — zaimplementuj sam (ok. 30 min). Testy: tests/test_partial_score.py.

    Binarny werdykt (``Diff.is_match``) to *execution accuracy* — standard w ewaluacji
    text-to-SQL. Ale przy porównywaniu wersji promptu/agenta przydaje się też miara częściowa:
      precision = trafione wiersze / wiersze w actual     (ile z tego, co zwrócono, jest dobre)
      recall    = trafione wiersze / wiersze w expected   (ile z oczekiwanego udało się zwrócić)
      f1        = średnia harmoniczna obu

    Wskazówki:
      - „trafione” to dopasowanie multizbiorów z tolerancją — masz już :func:`match_rows`;
      - kolumny trzeba najpierw wyrównać (:func:`_align_columns`); gdy się nie da → wszystko 0.0;
      - przypadki brzegowe (zdecyduj i opisz w docstringu): oba wyniki puste? actual pusty?

    Do przemyślenia: kiedy F1 na wierszach wprowadza w błąd? (Podpowiedź: pytanie
    „jaki jest on-time rate?” zwraca jeden wiersz — prawie dobra liczba daje F1 = 0.)
    """
    raise NotImplementedError("TODO(learn) #3: implement partial_score")
