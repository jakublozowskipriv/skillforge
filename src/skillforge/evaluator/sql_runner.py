"""Execute a candidate SQL query against the warehouse, safely enough for a local app.

- read-only connection: candidates cannot modify the warehouse,
- ``enable_external_access = false``: no reading/writing files or URLs (COPY, read_csv, ATTACH),
- one statement only, a wall-clock timeout (``interrupt()`` from a timer thread),
- a row limit so a cartesian product does not eat the memory of the UI process.
"""

from __future__ import annotations

import threading
from pathlib import Path

import duckdb

from skillforge.evaluator.resultset import ResultSet

DEFAULT_TIMEOUT_S = 10.0
DEFAULT_MAX_ROWS = 10_000


class SqlExecutionError(Exception):
    """The candidate query could not be executed (syntax error, unknown column, timeout...)."""


def run_sql(
    sql: str,
    warehouse: Path,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    max_rows: int = DEFAULT_MAX_ROWS,
) -> ResultSet:
    query = sql.strip().rstrip(";").strip()
    if not query:
        raise SqlExecutionError("Puste zapytanie.")
    if not warehouse.exists():
        raise SqlExecutionError(f"Brak hurtowni {warehouse}. Uruchom: uv run skillforge data build")
    con = duckdb.connect(str(warehouse), read_only=True, config={"enable_external_access": False})
    timer = threading.Timer(timeout_s, con.interrupt)
    try:
        statements = con.extract_statements(query)
        if len(statements) != 1:
            raise SqlExecutionError("Wyślij dokładnie jedno zapytanie (bez średników w środku).")
        timer.start()
        cursor = con.execute(query)
        if cursor.description is None:
            raise SqlExecutionError("Zapytanie nie zwraca wyniku — oczekiwano SELECT.")
        columns = [d[0] for d in cursor.description]
        types = [str(d[1]) for d in cursor.description]
        rows = cursor.fetchmany(max_rows + 1)
    except duckdb.InterruptException as exc:
        raise SqlExecutionError(f"Przekroczono limit czasu ({timeout_s:.0f} s).") from exc
    except duckdb.Error as exc:
        raise SqlExecutionError(str(exc)) from exc
    finally:
        timer.cancel()
        con.close()
    truncated = len(rows) > max_rows
    return ResultSet.from_rows(columns, rows[:max_rows], types, truncated=truncated)
