"""Tabular results in a normalized, JSON-serializable form.

Both sides of a comparison go through :func:`normalize_value`, so a freshly executed query
(Decimal, datetime, ...) and a snapshot loaded from JSON (float, ISO strings) compare equal.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

# What a normalized cell can be. Dates and timestamps become ISO strings.
Cell = None | bool | int | float | str
Row = tuple[Cell, ...]


def normalize_value(value: Any) -> Cell:
    """Map a DB/Python value to a JSON-friendly canonical form."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return None if math.isnan(value) else value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date | time):
        return value.isoformat()
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, str):
        return value
    return str(value)


_TYPE_RANK = {bool: 1, int: 2, float: 2, str: 3}


def _row_sort_key(row: Row) -> tuple[tuple[int, Any], ...]:
    return tuple((0, 0) if c is None else (_TYPE_RANK[type(c)], c) for c in row)


@dataclass(frozen=True)
class ResultSet:
    """Column names + rows of normalized cells. ``types`` are informational (DB type names)."""

    columns: tuple[str, ...]
    rows: tuple[Row, ...]
    types: tuple[str, ...] = ()
    truncated: bool = field(default=False, compare=False)

    @classmethod
    def from_rows(
        cls,
        columns: list[str] | tuple[str, ...],
        rows: list[tuple[Any, ...]] | list[list[Any]],
        types: list[str] | tuple[str, ...] = (),
        *,
        truncated: bool = False,
    ) -> ResultSet:
        return cls(
            columns=tuple(columns),
            rows=tuple(tuple(normalize_value(v) for v in row) for row in rows),
            types=tuple(types),
            truncated=truncated,
        )

    @property
    def row_count(self) -> int:
        return len(self.rows)

    def to_dict(self) -> dict[str, Any]:
        return {
            "columns": list(self.columns),
            "types": list(self.types),
            "rows": [list(r) for r in self.rows],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResultSet:
        return cls.from_rows(data["columns"], data["rows"], data.get("types", ()))

    def sorted(self) -> ResultSet:
        """Rows in a canonical order (NULLs first, then by type and value) — for stable files."""
        return ResultSet(self.columns, tuple(sorted(self.rows, key=_row_sort_key)), self.types)

    def to_json_file(self, path: Path) -> None:
        """One row per line: snapshots stay readable in code review and produce small git diffs."""

        def dump(value: Any) -> str:
            return json.dumps(value, ensure_ascii=False)

        rows = ",\n".join(f"    {dump(list(r))}" for r in self.rows)
        text = (
            "{\n"
            f'  "columns": {dump(list(self.columns))},\n'
            f'  "types": {dump(list(self.types))},\n'
            f'  "rows": [\n{rows}\n  ]\n'
            "}\n"
        )
        path.write_text(text, encoding="utf-8")

    @classmethod
    def from_json_file(cls, path: Path) -> ResultSet:
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
