from pathlib import Path

import duckdb
import pytest

pytestmark = pytest.mark.integration


def test_marts_are_built(warehouse: Path) -> None:
    with duckdb.connect(str(warehouse), read_only=True) as con:
        tables = {
            row[0]
            for row in con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'marts'"
            ).fetchall()
        }
        assert {"fct_shipments", "dim_carrier", "dim_carrier_sla", "fct_complaints"} <= tables

        shipments = con.execute("SELECT count(*) FROM marts.fct_shipments").fetchone()
        raw = con.execute("SELECT count(*) FROM raw.shipments").fetchone()
        assert shipments == raw  # grain: one row per shipment, nothing lost in joins


def test_staging_removes_duplicate_events(warehouse: Path) -> None:
    with duckdb.connect(str(warehouse), read_only=True) as con:
        row = con.execute(
            "SELECT (SELECT count(*) FROM raw.shipment_events)"
            " - (SELECT count(*) FROM staging.stg_raw__shipment_events)"
        ).fetchone()
        assert row is not None and row[0] > 0
