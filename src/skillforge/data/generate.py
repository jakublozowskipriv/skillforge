"""Synthetic e-commerce logistics dataset → ``raw`` schema in DuckDB.

The dataset mimics what lands in a warehouse from operational systems: orders, shipments,
carriers with SLA history, tracking events, courier pickups (first mile) and complaints.

It is **deterministic** for a given ``(seed, scale)``: every random draw comes from a single
``numpy.random.Generator`` in a fixed order. Exercise snapshots (golden expected results) rely on
this, so do not reorder draws casually — CI rebuilds the dataset and fails on any drift.

Deliberate data-quality issues (material for staging exercises):
- carrier codes in ``raw.shipments`` are inconsistent (case, whitespace),
- ``raw.shipment_events`` contains duplicated events (same payload, new ``event_id``),
- some events arrive late (``loaded_at`` days after ``event_at``) — incremental models,
- returned parcels have two ``delivery_failed`` events (not every event type is 1 per shipment),
- ``event_at`` lands as an ISO-8601 string, some ``location_city`` values are NULL.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from numpy.typing import NDArray

DEFAULT_SEED = 42
START = datetime(2026, 1, 1, tzinfo=UTC)
N_DAYS = 181  # 2026-01-01 .. 2026-06-30
# Snapshot of the source systems: events after this moment are not in the extract.
EXTRACT_AT = datetime(2026, 7, 3, tzinfo=UTC)

HOUR = 3600
DAY = 24 * HOUR

I64 = NDArray[np.int64]
F64 = NDArray[np.float64]


@dataclass(frozen=True)
class Carrier:
    carrier_id: int
    code: str
    name: str
    service_type: str
    pickup_hour: int  # start of the daily pickup window (local hour)
    pickup_delay_min: float  # mean arrival delay vs window start, minutes
    no_show_rate: float
    transit_factor: float  # >1 means slower than baseline
    damage_rate: float


# Fictional carriers on purpose: synthetic performance must not be read as claims about real firms.
CARRIERS: tuple[Carrier, ...] = (
    Carrier(1, "SWIFT", "SwiftParcel", "courier", 14, 5, 0.02, 0.85, 0.004),
    Carrier(2, "NORTH", "NorthExpress", "courier", 15, 20, 0.04, 1.05, 0.006),
    Carrier(3, "PAKO", "Pakomat24", "locker", 16, 10, 0.03, 0.95, 0.003),
    Carrier(4, "RAPID", "RapidKurier", "courier", 13, 35, 0.06, 1.25, 0.010),
    Carrier(5, "ECO", "EcoPost", "courier", 17, 15, 0.03, 1.40, 0.005),
)

# (carrier_id, service_level, sla_hours, valid_from, valid_to) — SCD2-style history.
SLA_HISTORY: tuple[tuple[int, str, int, str, str | None], ...] = (
    (1, "standard", 48, "2025-01-01", None),
    (1, "express", 24, "2025-01-01", None),
    (2, "standard", 48, "2025-01-01", "2026-04-01"),
    (2, "standard", 72, "2026-04-01", None),
    (2, "express", 24, "2025-01-01", None),
    (3, "standard", 48, "2025-01-01", None),
    (3, "express", 24, "2025-01-01", "2026-03-15"),
    (3, "express", 36, "2026-03-15", None),
    (4, "standard", 72, "2025-01-01", None),
    (4, "express", 36, "2025-01-01", None),
    (5, "standard", 96, "2025-01-01", None),
    (5, "express", 48, "2025-06-01", None),
)

WAREHOUSES: tuple[tuple[int, str, str, str], ...] = (
    (1, "WAW1", "Warszawa", "mazowieckie"),
    (2, "POZ1", "Poznań", "wielkopolskie"),
    (3, "WRO1", "Wrocław", "dolnośląskie"),
)
# Carrier mix per warehouse (rows: warehouses, cols: carriers). Zero = carrier not served there.
CARRIER_MIX = np.array(
    [
        [0.35, 0.25, 0.25, 0.10, 0.05],
        [0.30, 0.00, 0.40, 0.20, 0.10],
        [0.25, 0.30, 0.30, 0.00, 0.15],
    ]
)
WAREHOUSE_SHARE = np.array([0.5, 0.3, 0.2])

DESTINATIONS: tuple[tuple[str, str], ...] = (
    ("Warszawa", "mazowieckie"),
    ("Kraków", "małopolskie"),
    ("Łódź", "łódzkie"),
    ("Wrocław", "dolnośląskie"),
    ("Poznań", "wielkopolskie"),
    ("Gdańsk", "pomorskie"),
    ("Szczecin", "zachodniopomorskie"),
    ("Lublin", "lubelskie"),
    ("Katowice", "śląskie"),
    ("Białystok", "podlaskie"),
    ("Rzeszów", "podkarpackie"),
    ("Olsztyn", "warmińsko-mazurskie"),
)
DESTINATION_WEIGHTS = np.array([18, 10, 7, 8, 7, 7, 4, 4, 9, 3, 3, 2], dtype=float)
HUBS = ("Stryków", "Piotrków Trybunalski", "Błonie", "Gliwice")

COMPLAINT_CATEGORIES = ("damaged", "late", "lost", "wrong_address", "other")


@dataclass(frozen=True)
class RawTables:
    carriers: pd.DataFrame
    carrier_sla_history: pd.DataFrame
    warehouses: pd.DataFrame
    orders: pd.DataFrame
    shipments: pd.DataFrame
    shipment_events: pd.DataFrame
    courier_pickups: pd.DataFrame
    complaints: pd.DataFrame

    def as_dict(self) -> dict[str, pd.DataFrame]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


def _ts(seconds: NDArray[np.int64] | NDArray[np.float64]) -> pd.Series[pd.Timestamp]:
    """Seconds since START → naive UTC timestamps (second precision)."""
    base = pd.Timestamp(START).tz_localize(None)
    return pd.Series(base + pd.to_timedelta(np.asarray(seconds, dtype=np.int64), unit="s"))


def _time_of_day(seconds: I64) -> I64:
    return seconds % DAY


def _generate_orders(rng: np.random.Generator, scale: float) -> pd.DataFrame:
    weekday_factor = np.array([1.15, 1.10, 1.05, 1.0, 0.95, 0.75, 0.70])  # Mon..Sun
    start_weekday = START.weekday()
    days = np.arange(N_DAYS)
    lam = 110.0 * scale * weekday_factor[(days + start_weekday) % 7]
    per_day = rng.poisson(lam)
    n = int(per_day.sum())
    day_idx = np.repeat(days, per_day)
    # Hour of day: bimodal (lunch + evening), clipped to the day.
    hours = np.where(rng.random(n) < 0.4, rng.normal(12.5, 2.0, n), rng.normal(20.0, 2.5, n))
    hours = np.clip(hours, 0.0, 23.99)
    ordered_at = (day_idx * DAY + (hours * HOUR).astype(np.int64)).astype(np.int64)
    order_by_time = np.argsort(ordered_at, kind="stable")
    ordered_at = ordered_at[order_by_time]

    n_customers = max(1, int(n * 0.6))
    dest_idx = rng.choice(
        len(DESTINATIONS), size=n, p=DESTINATION_WEIGHTS / DESTINATION_WEIGHTS.sum()
    )
    return pd.DataFrame(
        {
            "order_id": np.arange(1, n + 1, dtype=np.int64),
            "customer_id": [f"C{c:06d}" for c in rng.integers(1, n_customers + 1, n)],
            "warehouse_id": rng.choice([w[0] for w in WAREHOUSES], size=n, p=WAREHOUSE_SHARE),
            "ordered_at_s": ordered_at,
            "service_level": np.where(rng.random(n) < 0.2, "express", "standard"),
            "order_value_pln": np.round(rng.lognormal(np.log(140.0), 0.6, n), 2),
            "destination_city": [DESTINATIONS[i][0] for i in dest_idx],
            "destination_region": [DESTINATIONS[i][1] for i in dest_idx],
        }
    )


def _generate_shipments(rng: np.random.Generator, orders: pd.DataFrame) -> pd.DataFrame:
    n_orders = len(orders)
    u = rng.random(n_orders)
    n_parcels = np.where(u < 0.02, 0, np.where(u < 0.08, 2, 1))  # 2% cancelled, 6% split
    order_idx = np.repeat(np.arange(n_orders), n_parcels)
    n = len(order_idx)
    wh = orders["warehouse_id"].to_numpy()[order_idx]
    carrier_idx = np.empty(n, dtype=np.int64)
    for w_pos, (w_id, *_rest) in enumerate(WAREHOUSES):
        mask = wh == w_id
        carrier_idx[mask] = rng.choice(len(CARRIERS), size=int(mask.sum()), p=CARRIER_MIX[w_pos])
    created_at = (
        orders["ordered_at_s"].to_numpy()[order_idx] + (rng.uniform(0.5, 20.0, n) * HOUR)
    ).astype(np.int64)

    canonical = np.array([CARRIERS[i].code for i in carrier_idx], dtype=object)
    dirt = rng.random(n)
    carrier_code = np.where(
        dirt < 0.10,
        np.char.lower(canonical.astype(str)),
        np.where(
            dirt < 0.15, np.char.add(np.char.capitalize(canonical.astype(str)), " "), canonical
        ),
    )
    return pd.DataFrame(
        {
            "shipment_id": np.arange(1, n + 1, dtype=np.int64),
            "order_id": orders["order_id"].to_numpy()[order_idx],
            "order_pos": order_idx,
            "warehouse_id": wh,
            "carrier_idx": carrier_idx,
            "carrier_code": carrier_code,
            "tracking_number": [f"TRK{t:010d}" for t in rng.integers(0, 10**10, n)],
            "created_at_s": created_at,
            "parcel_size": rng.choice(["A", "B", "C"], size=n, p=[0.5, 0.35, 0.15]),
            "weight_kg": np.round(rng.gamma(2.0, 1.5, n) + 0.1, 2),
            "shipping_cost_pln": np.round(rng.uniform(9.0, 19.0, n), 2),
        }
    )


def _generate_pickups(rng: np.random.Generator) -> pd.DataFrame:
    rows: list[tuple[int, int, int, int, float, float]] = []
    start_weekday = START.weekday()
    for day in range(N_DAYS):
        if (day + start_weekday) % 7 == 6:  # no pickups on Sundays
            continue
        for w_pos, (w_id, *_rest) in enumerate(WAREHOUSES):
            for c_pos, carrier in enumerate(CARRIERS):
                if CARRIER_MIX[w_pos, c_pos] == 0:
                    continue
                scheduled = day * DAY + carrier.pickup_hour * HOUR
                no_show = rng.random() < carrier.no_show_rate
                delay_min = rng.normal(carrier.pickup_delay_min, 25.0)
                stay_min = rng.uniform(5.0, 20.0)
                arrived = np.nan if no_show else scheduled + delay_min * 60
                rows.append((w_id, carrier.carrier_id, c_pos, scheduled, arrived, stay_min))
    df = pd.DataFrame(
        rows,
        columns=[
            "warehouse_id",
            "carrier_id",
            "carrier_idx",
            "scheduled_s",
            "arrived_s",
            "stay_min",
        ],
    )
    df.insert(0, "pickup_id", np.arange(1, len(df) + 1, dtype=np.int64))
    return df


def _assign_pickups(shipments: pd.DataFrame, pickups: pd.DataFrame) -> F64:
    """For each shipment: arrival time of the first courier pickup after it is ready (or NaN)."""
    picked = np.full(len(shipments), np.nan)
    pickup_ids = np.full(len(shipments), -1, dtype=np.int64)
    ready = shipments["created_at_s"].to_numpy() + 30 * 60  # 30 min to pack and label
    showed = pickups.dropna(subset=["arrived_s"])
    for (w_id, c_idx), group in showed.groupby(["warehouse_id", "carrier_idx"], sort=True):
        arrivals = group["arrived_s"].to_numpy()
        order = np.argsort(arrivals, kind="stable")
        arrivals = arrivals[order]
        ids = group["pickup_id"].to_numpy()[order]
        mask = (shipments["warehouse_id"].to_numpy() == w_id) & (
            shipments["carrier_idx"].to_numpy() == c_idx
        )
        pos = np.searchsorted(arrivals, ready[mask], side="left")
        ok = pos < len(arrivals)
        sel = np.where(mask)[0]
        picked[sel[ok]] = arrivals[pos[ok]]
        pickup_ids[sel[ok]] = ids[pos[ok]]
    shipments["pickup_id"] = pickup_ids
    return picked


def _clamp_to_delivery_hours(rng: np.random.Generator, t: I64) -> I64:
    """Couriers deliver 08:00-20:00; push anything outside to the next morning."""
    tod = _time_of_day(t)
    day_start = t - tod
    late = tod >= 20 * HOUR
    early = tod < 8 * HOUR
    morning = (8 * HOUR + rng.uniform(0, 4 * HOUR, len(t))).astype(np.int64)
    out = np.where(late, day_start + DAY + morning, t)
    return np.where(early & ~late, day_start + morning, out).astype(np.int64)


def generate(seed: int = DEFAULT_SEED, scale: float = 1.0) -> RawTables:
    """Generate all raw tables in memory. ``scale`` multiplies order volume (1.0 ≈ 20k orders)."""
    if scale <= 0:
        raise ValueError("scale must be > 0")
    rng = np.random.default_rng(seed)
    extract_s = int((EXTRACT_AT - START).total_seconds())

    orders = _generate_orders(rng, scale)
    shipments = _generate_shipments(rng, orders)
    pickups = _generate_pickups(rng)
    picked_s = _assign_pickups(shipments, pickups)
    n = len(shipments)

    c_idx = shipments["carrier_idx"].to_numpy()
    transit_factor = np.array([c.transit_factor for c in CARRIERS])[c_idx]
    express = orders["service_level"].to_numpy()[shipments["order_pos"].to_numpy()] == "express"
    base_hours = np.where(express, 20.0, 34.0)
    transit_h = rng.lognormal(np.log(base_hours * transit_factor), 0.45, n)

    has_pickup = ~np.isnan(picked_s)
    picked_i = np.nan_to_num(picked_s, nan=0.0).astype(np.int64)
    first_attempt = _clamp_to_delivery_hours(rng, picked_i + (transit_h * HOUR).astype(np.int64))

    fate = rng.random(n)
    lost = has_pickup & (fate < 0.004)
    returned = has_pickup & (fate >= 0.004) & (fate < 0.014)
    failed_then_ok = has_pickup & (fate >= 0.014) & (fate < 0.054)
    delivered_ok = has_pickup & ~lost & ~returned
    second_attempt = _clamp_to_delivery_hours(rng, first_attempt + DAY)
    delivered_s = np.where(failed_then_ok, second_attempt, first_attempt)

    span = np.maximum(delivered_s - picked_i, HOUR)
    in_transit_s = picked_i + (0.1 * span).astype(np.int64)
    out_for_delivery_s = delivered_s - np.minimum(3 * HOUR, (0.3 * span).astype(np.int64))
    out_for_delivery_s = np.maximum(out_for_delivery_s, in_transit_s + 60)

    wh_city = {w[0]: w[2] for w in WAREHOUSES}
    origin = np.array([wh_city[w] for w in shipments["warehouse_id"]], dtype=object)
    dest = orders["destination_city"].to_numpy()[shipments["order_pos"].to_numpy()]
    hub = np.array(HUBS, dtype=object)[rng.integers(0, len(HUBS), n)]
    sid = shipments["shipment_id"].to_numpy()

    parts: list[pd.DataFrame] = []

    def add(mask: NDArray[np.bool_], etype: str, t: I64, city: NDArray[np.object_]) -> None:
        parts.append(
            pd.DataFrame(
                {"shipment_id": sid[mask], "event_type": etype, "t": t[mask], "city": city[mask]}
            )
        )

    created = shipments["created_at_s"].to_numpy()
    add(np.ones(n, dtype=bool), "label_created", created, origin)
    add(has_pickup, "picked_up", picked_i, origin)
    add(has_pickup, "in_transit", in_transit_s, hub)
    add(delivered_ok | returned, "out_for_delivery", out_for_delivery_s, dest)
    add(failed_then_ok | returned, "delivery_failed", first_attempt, dest)
    # Carriers try twice before returning a parcel: a second failed attempt the next day.
    add(returned, "delivery_failed", second_attempt, dest)
    add(delivered_ok, "delivered", delivered_s, dest)
    add(returned, "returned", second_attempt + 2 * DAY, origin)
    events = pd.concat(parts, ignore_index=True)
    events = events[events["t"] < extract_s].reset_index(drop=True)

    m = len(events)
    late_arrival = rng.random(m) < 0.02
    lag = np.where(late_arrival, rng.uniform(2 * DAY, 5 * DAY, m), rng.uniform(5 * 60, 3600, m))
    events["loaded_s"] = events["t"].to_numpy() + lag.astype(np.int64)
    events.loc[rng.random(m) < 0.02, "city"] = None
    dup = events[rng.random(m) < 0.03].copy()
    dup["loaded_s"] = dup["loaded_s"] + rng.uniform(60, 6 * HOUR, len(dup)).astype(np.int64)
    events = pd.concat([events, dup], ignore_index=True)
    events = events.sort_values(
        ["loaded_s", "shipment_id", "event_type"], kind="stable"
    ).reset_index(drop=True)
    events = events[events["loaded_s"] < extract_s].reset_index(drop=True)
    event_at = _ts(events["t"].to_numpy())
    shipment_events = pd.DataFrame(
        {
            "event_id": np.arange(1, len(events) + 1, dtype=np.int64),
            "shipment_id": events["shipment_id"].to_numpy(),
            "event_type": events["event_type"].to_numpy(),
            "event_at": event_at.dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "location_city": events["city"].to_numpy(),
            "loaded_at": _ts(events["loaded_s"].to_numpy()),
        }
    )

    # Courier pickups: parcels_collected = shipments actually handed over at that visit.
    collected = (
        pd.Series(shipments["pickup_id"].to_numpy()[has_pickup])
        .value_counts()
        .rename("n")
        .to_frame()
    )
    pickups = pickups.merge(collected, left_on="pickup_id", right_index=True, how="left")
    arrived = pickups["arrived_s"].to_numpy()
    showed = ~np.isnan(arrived)
    courier_pickups = pd.DataFrame(
        {
            "pickup_id": pickups["pickup_id"].to_numpy(),
            "warehouse_id": pickups["warehouse_id"].to_numpy(),
            "carrier_id": pickups["carrier_id"].to_numpy(),
            "window_start_at": _ts(pickups["scheduled_s"].to_numpy()),
            "window_end_at": _ts(pickups["scheduled_s"].to_numpy() + 2 * HOUR),
            "arrived_at": _ts(np.nan_to_num(arrived)).where(showed),
            "departed_at": _ts(np.nan_to_num(arrived + pickups["stay_min"].to_numpy() * 60)).where(
                showed
            ),
            "parcels_collected": pickups["n"].fillna(0).astype(np.int64).where(showed),
        }
    )
    courier_pickups = courier_pickups[
        courier_pickups["window_start_at"] < pd.Timestamp(EXTRACT_AT).tz_localize(None)
    ]

    # Complaints: more likely when late, damaged or lost.
    sla_hours = np.where(express, 24.0, 48.0)
    late = delivered_ok & ((delivered_s - picked_i) > sla_hours * HOUR)
    damage = np.array([c.damage_rate for c in CARRIERS])[c_idx]
    p = np.where(lost, 0.7, np.where(delivered_ok, 0.008 + damage + 0.05 * late, 0.1 * returned))
    has_complaint = rng.random(n) < p
    k = int(has_complaint.sum())
    base_t = np.where(lost, picked_i + 7 * DAY, np.where(delivered_ok, delivered_s, first_attempt))
    complaint_t = base_t[has_complaint] + rng.exponential(2 * DAY, k).astype(np.int64)
    cat_draw = rng.random(k)
    damaged_rate_share = (damage / (damage + 0.05 * late + 0.008))[has_complaint]
    category = np.where(
        lost[has_complaint],
        "lost",
        np.where(
            late[has_complaint] & (cat_draw < 0.7),
            "late",
            np.where(
                cat_draw < damaged_rate_share,
                "damaged",
                np.array(["wrong_address", "other", "late"], dtype=object)[rng.integers(0, 3, k)],
            ),
        ),
    )
    status_draw = rng.random(k)
    status = np.where(
        status_draw < 0.55, "accepted", np.where(status_draw < 0.85, "rejected", "open")
    )
    order_value = orders["order_value_pln"].to_numpy()[shipments["order_pos"].to_numpy()][
        has_complaint
    ]
    compensation = np.where(
        np.isin(category, ["lost", "damaged"]),
        order_value,
        np.round(rng.uniform(10.0, 30.0, k), 2),
    )
    complaints = pd.DataFrame(
        {
            "shipment_id": sid[has_complaint],
            "created_at": _ts(complaint_t),
            "category": category,
            "status": status,
            "compensation_pln": np.where(status == "accepted", compensation, np.nan),
            "t": complaint_t,
        }
    )
    complaints = complaints[complaints["t"] < extract_s].sort_values(
        ["t", "shipment_id"], kind="stable"
    )
    complaints = complaints.drop(columns="t").reset_index(drop=True)
    complaints.insert(0, "complaint_id", np.arange(1, len(complaints) + 1, dtype=np.int64))

    cancelled = ~np.isin(orders["order_id"].to_numpy(), shipments["order_id"].to_numpy())
    orders_out = pd.DataFrame(
        {
            "order_id": orders["order_id"],
            "customer_id": orders["customer_id"],
            "warehouse_id": orders["warehouse_id"],
            "ordered_at": _ts(orders["ordered_at_s"].to_numpy()),
            "service_level": orders["service_level"],
            "order_status": np.where(cancelled, "cancelled", "placed"),
            "order_value_pln": orders["order_value_pln"],
            "destination_city": orders["destination_city"],
            "destination_region": orders["destination_region"],
        }
    )
    shipments_out = pd.DataFrame(
        {
            "shipment_id": shipments["shipment_id"],
            "order_id": shipments["order_id"],
            "warehouse_id": shipments["warehouse_id"],
            "carrier_code": shipments["carrier_code"],
            "tracking_number": shipments["tracking_number"],
            "created_at": _ts(created),
            "parcel_size": shipments["parcel_size"],
            "weight_kg": shipments["weight_kg"],
            "shipping_cost_pln": shipments["shipping_cost_pln"],
        }
    )
    carriers = pd.DataFrame(
        {
            "carrier_id": [c.carrier_id for c in CARRIERS],
            "carrier_code": [c.code for c in CARRIERS],
            "carrier_name": [c.name for c in CARRIERS],
            "service_type": [c.service_type for c in CARRIERS],
        }
    )
    sla = pd.DataFrame(
        SLA_HISTORY, columns=["carrier_id", "service_level", "sla_hours", "valid_from", "valid_to"]
    )
    sla["valid_from"] = pd.to_datetime(sla["valid_from"]).dt.date
    sla["valid_to"] = pd.to_datetime(sla["valid_to"]).dt.date
    warehouses = pd.DataFrame(
        WAREHOUSES, columns=["warehouse_id", "warehouse_code", "city", "region"]
    )

    return RawTables(
        carriers=carriers,
        carrier_sla_history=sla,
        warehouses=warehouses,
        orders=orders_out,
        shipments=shipments_out,
        shipment_events=shipment_events,
        courier_pickups=courier_pickups.reset_index(drop=True),
        complaints=complaints,
    )


# Explicit DDL: raw tables get stable, documented types regardless of pandas inference.
RAW_DDL: dict[str, str] = {
    "carriers": """
        carrier_id INTEGER, carrier_code VARCHAR, carrier_name VARCHAR, service_type VARCHAR""",
    "carrier_sla_history": """
        carrier_id INTEGER, service_level VARCHAR, sla_hours INTEGER,
        valid_from DATE, valid_to DATE""",
    "warehouses": """
        warehouse_id INTEGER, warehouse_code VARCHAR, city VARCHAR, region VARCHAR""",
    "orders": """
        order_id BIGINT, customer_id VARCHAR, warehouse_id INTEGER, ordered_at TIMESTAMP,
        service_level VARCHAR, order_status VARCHAR, order_value_pln DECIMAL(10, 2),
        destination_city VARCHAR, destination_region VARCHAR""",
    "shipments": """
        shipment_id BIGINT, order_id BIGINT, warehouse_id INTEGER, carrier_code VARCHAR,
        tracking_number VARCHAR, created_at TIMESTAMP, parcel_size VARCHAR,
        weight_kg DECIMAL(6, 2), shipping_cost_pln DECIMAL(8, 2)""",
    "shipment_events": """
        event_id BIGINT, shipment_id BIGINT, event_type VARCHAR, event_at VARCHAR,
        location_city VARCHAR, loaded_at TIMESTAMP""",
    "courier_pickups": """
        pickup_id BIGINT, warehouse_id INTEGER, carrier_id INTEGER, window_start_at TIMESTAMP,
        window_end_at TIMESTAMP, arrived_at TIMESTAMP, departed_at TIMESTAMP,
        parcels_collected INTEGER""",
    "complaints": """
        complaint_id BIGINT, shipment_id BIGINT, created_at TIMESTAMP, category VARCHAR,
        status VARCHAR, compensation_pln DECIMAL(10, 2)""",
}


def load_raw(tables: RawTables, warehouse_path: Path) -> dict[str, int]:
    """(Re)create the ``raw`` schema in the DuckDB file and load all tables. Returns row counts."""
    warehouse_path.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    with duckdb.connect(str(warehouse_path)) as con:
        con.execute("DROP SCHEMA IF EXISTS raw CASCADE")
        con.execute("CREATE SCHEMA raw")
        for name, df in tables.as_dict().items():
            con.execute(f"CREATE TABLE raw.{name} ({RAW_DDL[name]})")
            con.register("_src", df)
            cols = ", ".join(df.columns)
            con.execute(f"INSERT INTO raw.{name} ({cols}) SELECT {cols} FROM _src")
            con.unregister("_src")
            counts[name] = len(df)
    return counts
