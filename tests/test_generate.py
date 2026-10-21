import itertools
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from skillforge.data.generate import RawTables, generate, load_raw

SCALE = 0.05


@pytest.fixture(scope="module")
def tables() -> RawTables:
    return generate(seed=7, scale=SCALE)


def test_deterministic_for_same_seed(tables: RawTables) -> None:
    again = generate(seed=7, scale=SCALE)
    for name, df in tables.as_dict().items():
        pd.testing.assert_frame_equal(df, again.as_dict()[name], obj=name)


def test_different_seed_differs(tables: RawTables) -> None:
    other = generate(seed=8, scale=SCALE)
    assert not tables.orders.equals(other.orders)


def test_scale_controls_volume(tables: RawTables) -> None:
    # 110 orders/day * 181 days * weekday factors (~0.96) * scale
    assert 700 < len(tables.orders) < 1200


def test_referential_integrity(tables: RawTables) -> None:
    assert set(tables.shipments["order_id"]) <= set(tables.orders["order_id"])
    assert set(tables.shipment_events["shipment_id"]) <= set(tables.shipments["shipment_id"])
    assert set(tables.complaints["shipment_id"]) <= set(tables.shipments["shipment_id"])
    assert set(tables.courier_pickups["carrier_id"]) <= set(tables.carriers["carrier_id"])
    assert set(tables.orders["warehouse_id"]) <= set(tables.warehouses["warehouse_id"])


def test_primary_keys_unique(tables: RawTables) -> None:
    for name, key in [
        ("orders", "order_id"),
        ("shipments", "shipment_id"),
        ("shipment_events", "event_id"),
        ("courier_pickups", "pickup_id"),
        ("complaints", "complaint_id"),
    ]:
        assert tables.as_dict()[name][key].is_unique, name


def test_deliberate_dirt_is_present(tables: RawTables) -> None:
    codes = tables.shipments["carrier_code"]
    assert (codes != codes.str.strip().str.upper()).any()

    ev = tables.shipment_events
    dupes = ev.duplicated(subset=["shipment_id", "event_type", "event_at"], keep=False)
    assert dupes.any()

    lag = ev["loaded_at"] - pd.to_datetime(ev["event_at"]).dt.tz_localize(None)
    assert (lag > pd.Timedelta(days=1)).any()
    assert ev["location_city"].isna().any()


def test_event_milestones_are_chronological(tables: RawTables) -> None:
    ev = tables.shipment_events.drop_duplicates(subset=["shipment_id", "event_type"])
    wide = ev.pivot(index="shipment_id", columns="event_type", values="event_at")
    order = ["label_created", "picked_up", "in_transit", "out_for_delivery", "delivered"]
    for earlier, later in itertools.pairwise(order):
        both = wide[[earlier, later]].dropna()
        assert (both[earlier] <= both[later]).all(), (earlier, later)


def test_no_show_pickups_have_no_arrival(tables: RawTables) -> None:
    p = tables.courier_pickups
    no_show = p["arrived_at"].isna()
    assert no_show.any()
    assert p.loc[no_show, "parcels_collected"].isna().all()
    assert p.loc[~no_show, "parcels_collected"].notna().all()


def test_load_raw_roundtrip(tables: RawTables, tmp_path: Path) -> None:
    db = tmp_path / "wh.duckdb"
    counts = load_raw(tables, db)
    with duckdb.connect(str(db), read_only=True) as con:
        for name, n in counts.items():
            row = con.execute(f"SELECT count(*) FROM raw.{name}").fetchone()
            assert row is not None and row[0] == n
        dtype = con.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_schema = 'raw' AND table_name = 'orders' "
            "AND column_name = 'order_value_pln'"
        ).fetchone()
        assert dtype == ("DECIMAL(10,2)",)
    # reloading replaces the schema instead of appending
    assert load_raw(tables, db) == counts
