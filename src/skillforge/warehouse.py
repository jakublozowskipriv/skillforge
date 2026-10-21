"""Read-only helpers for browsing the exercise warehouse."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import duckdb

SCHEMA_ORDER = ("marts", "intermediate", "staging", "raw")


def describe(warehouse: Path) -> dict[str, dict[str, list[tuple[str, str]]]]:
    """``{schema: {table: [(column, type), ...]}}`` for the layers exercises can query."""
    with duckdb.connect(str(warehouse), read_only=True) as con:
        rows = con.execute(
            "SELECT table_schema, table_name, column_name, data_type "
            "FROM information_schema.columns "
            "WHERE table_schema IN ('marts', 'intermediate', 'staging', 'raw') "
            "ORDER BY table_schema, table_name, ordinal_position"
        ).fetchall()
    out: dict[str, dict[str, list[tuple[str, str]]]] = defaultdict(lambda: defaultdict(list))
    for schema, table, column, dtype in rows:
        out[schema][table].append((column, dtype))
    return {s: dict(out[s]) for s in SCHEMA_ORDER if s in out}
