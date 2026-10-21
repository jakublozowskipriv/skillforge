import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from skillforge.evaluator import EvalResult
from skillforge.progress import projections as proj
from skillforge.progress.events import BragAdded, Event, KpiRecorded, SessionLogged
from skillforge.progress.export import brag_markdown, export_json, import_json, summary
from skillforge.progress.service import Progress
from skillforge.progress.store import EventStore, InMemoryEventStore, SqliteEventStore

T0 = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def clock_from(start: datetime) -> Callable[[], datetime]:
    state = {"t": start}

    def tick() -> datetime:
        state["t"] += timedelta(minutes=1)
        return state["t"]

    return tick


StoreFactory = Callable[[Path], EventStore]
STORES: list[StoreFactory] = [
    lambda tmp: InMemoryEventStore(),
    lambda tmp: SqliteEventStore(tmp / "p.db"),
]


@pytest.fixture(params=STORES, ids=["memory", "sqlite"])
def store(request: pytest.FixtureRequest, tmp_path: Path) -> EventStore:
    factory: StoreFactory = request.param
    return factory(tmp_path)


# --- events ---------------------------------------------------------------------------------


def test_event_new_sets_type_and_validates_payload() -> None:
    e = Event.new(SessionLogged(day=date(2026, 10, 1), minutes=30), source="pc")
    assert e.type == "session.logged" and e.payload["minutes"] == 30
    with pytest.raises(ValidationError):
        Event.model_validate({**e.model_dump(), "payload": {"minutes": -5}})


def test_event_requires_timezone() -> None:
    e = Event.new(KpiRecorded(kpi_id="k", value=1), source="pc")
    with pytest.raises(ValidationError, match="timezone"):
        Event.model_validate({**e.model_dump(), "occurred_at": datetime(2026, 1, 1)})


# --- stores (same contract for every backend) -----------------------------------------------


def test_store_append_is_idempotent(store: EventStore) -> None:
    e = Event.new(KpiRecorded(kpi_id="k", value=1), source="pc")
    assert store.append(e) is True
    assert store.append(e) is False
    assert store.extend([e, e]) == 0
    assert len(store.read()) == 1


def test_store_orders_by_occurrence_not_insertion(store: EventStore) -> None:
    late = Event.new(KpiRecorded(kpi_id="k", value=2), source="phone", occurred_at=T0)
    early = Event.new(
        KpiRecorded(kpi_id="k", value=1), source="pc", occurred_at=T0 - timedelta(days=1)
    )
    store.extend([late, early])
    assert [e.payload["value"] for e in store.read()] == [1, 2]
    assert store.read(since=T0) == [late]
    assert store.read(types=["session.logged"]) == []


def test_sqlite_roundtrip_preserves_events(tmp_path: Path) -> None:
    e = Event.new(BragAdded(day=date(2026, 10, 1), context="c", role="r", effect="e"), source="pc")
    SqliteEventStore(tmp_path / "p.db").append(e)
    assert SqliteEventStore(tmp_path / "p.db").read() == [e]


# --- projections via the facade -------------------------------------------------------------


def test_brag_retraction_hides_entry() -> None:
    p = Progress(InMemoryEventStore(), clock=clock_from(T0))
    keep = p.add_brag(date(2026, 9, 1), "Raport SLA", "autor", "-2 h/tydz.", 2, "h", "https://x")
    drop = p.add_brag(date(2026, 9, 2), "Duplikat", "autor", "nic")
    p.retract_brag(drop.event_id)
    entries = p.brag_entries()
    assert [b.entry_id for b in entries] == [keep.event_id]
    md = brag_markdown(entries)
    assert "**2026-09-01** · Raport SLA · autor · -2 h/tydz. (**2 h**) · [dowód](https://x)" in md


def test_kpi_latest_uses_occurrence_time() -> None:
    store = InMemoryEventStore()
    pc = Progress(store, source="pc", clock=clock_from(T0))
    pc.record_kpi("talks", 2)
    # phone recorded an *older* value that syncs later: must not override the newer one
    store.append(
        Event.new(
            KpiRecorded(kpi_id="talks", value=1),
            source="phone",
            occurred_at=T0 - timedelta(days=3),
        )
    )
    assert pc.kpi_latest()["talks"].value == 2
    assert [p.value for p in pc.kpi_history()["talks"]] == [1, 2]


def test_levels_last_write_wins() -> None:
    p = Progress(InMemoryEventStore(), clock=clock_from(T0))
    p.set_level("ae.dbt-layers", 1)
    p.set_level("ae.dbt-layers", 2)
    assert p.levels() == {"ae.dbt-layers": 2}


def test_attempts_and_stats() -> None:
    p = Progress(InMemoryEventStore(), clock=clock_from(T0))
    fail = EvalResult("ex", "sql", False, 0.0, 5.0, error="boom")
    ok = EvalResult("ex", "sql", True, 1.0, 5.0)
    p.record_attempt("ex", "select 1", fail)
    p.record_attempt("ex", "select 2", ok)
    stats = p.exercise_stats()["ex"]
    assert (stats.attempts, stats.solved, stats.first_try, stats.best_score) == (
        2,
        True,
        False,
        1.0,
    )
    assert p.attempts("ex")[-1].code == "select 2"
    assert p.attempts("ex")[0].result["error"] == "boom"


def test_quiz_validation() -> None:
    p = Progress(InMemoryEventStore())
    with pytest.raises(ValidationError):
        p.record_quiz("ae.dbt-layers", 6, 5)


def test_summary_for_tutor() -> None:
    p = Progress(InMemoryEventStore(), clock=clock_from(T0))
    p.log_session(date(2026, 9, 30), 60, "theory", "ae.dbt-layers")
    p.record_attempt("ex", "x", EvalResult("ex", "sql", False, 0.0, 1.0))
    s = summary(p.events(), now=T0)
    assert s["weak_exercises"] == ["ex"]
    assert s["sessions_last_28_days"][0]["minutes"] == 60
    assert s["sessions_last_28_days"][0]["day"] == "2026-09-30"


# --- multi-device sync -----------------------------------------------------------------------


def test_two_devices_converge(tmp_path: Path) -> None:
    pc = Progress(SqliteEventStore(tmp_path / "pc.db"), source="pc", clock=clock_from(T0))
    phone = Progress(SqliteEventStore(tmp_path / "phone.db"), source="phone", clock=clock_from(T0))
    pc.log_session(date(2026, 10, 1), 60, "theory")
    pc.review_card("ae-c-01", 3)
    phone.review_card("ae-c-01", 1)
    phone.add_brag(date(2026, 10, 2), "Demo", "prowadzący", "2 zespoły")

    export_json(pc.store, tmp_path / "pc.json")
    export_json(phone.store, tmp_path / "phone.json")
    assert import_json(pc.store, tmp_path / "phone.json") == 2
    assert import_json(phone.store, tmp_path / "pc.json") == 2
    assert import_json(phone.store, tmp_path / "pc.json") == 0  # idempotent

    assert {e.event_id for e in pc.events()} == {e.event_id for e in phone.events()}
    assert pc.card_reviews() == phone.card_reviews()
    assert pc.brag_entries() == phone.brag_entries()
    # phone reviewed at T0+1min, pc at T0+2min: order follows occurrence, not sync order
    assert [r.rating for r in pc.card_reviews()["ae-c-01"]] == [1, 3]


def test_import_rejects_unknown_schema(tmp_path: Path) -> None:
    f = tmp_path / "x.json"
    f.write_text('{"schema_version": 99, "events": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="schema_version"):
        import_json(InMemoryEventStore(), f)


def test_projection_functions_are_pure() -> None:
    e = Event.new(SessionLogged(day=date(2026, 10, 1), minutes=10), source="pc")
    assert proj.sessions([e]) == proj.sessions([e])
    assert proj.brag_entries([]) == [] and proj.levels([]) == {}
    assert isinstance(e.event_id, uuid.UUID)
