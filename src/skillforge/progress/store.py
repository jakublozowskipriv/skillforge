"""Event storage behind a small interface. SQLite today; anything append-only tomorrow."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Collection, Iterable
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from skillforge.progress.events import Event

TS_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"  # fixed width ⇒ lexicographic order == time order


def _ts(value: datetime) -> str:
    return value.astimezone(UTC).strftime(TS_FORMAT)


def _parse_ts(value: str) -> datetime:
    return datetime.strptime(value, TS_FORMAT).replace(tzinfo=UTC)


class EventStore(Protocol):
    def append(self, event: Event) -> bool:
        """Store the event; False if an event with this ``event_id`` already exists."""

    def extend(self, events: Iterable[Event]) -> int:
        """Store many events idempotently; returns how many were new."""

    def read(
        self, types: Collection[str] | None = None, since: datetime | None = None
    ) -> list[Event]:
        """Events (optionally filtered by type / ``occurred_at >= since``) in ``sort_key`` order."""


class InMemoryEventStore:
    def __init__(self) -> None:
        self._events: dict[str, Event] = {}

    def append(self, event: Event) -> bool:
        return self.extend([event]) == 1

    def extend(self, events: Iterable[Event]) -> int:
        new = 0
        for event in events:
            key = str(event.event_id)
            if key not in self._events:
                self._events[key] = event
                new += 1
        return new

    def read(
        self, types: Collection[str] | None = None, since: datetime | None = None
    ) -> list[Event]:
        found = [
            e
            for e in self._events.values()
            if (types is None or e.type in types) and (since is None or e.occurred_at >= since)
        ]
        return sorted(found, key=lambda e: e.sort_key)


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    event_id    TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    source      TEXT NOT NULL,
    payload     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_type_occurred ON events (type, occurred_at);
"""


class SqliteEventStore:
    """One append-only table. WAL mode lets the UI, CLI and tutor commands write concurrently."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as con:
            con.execute("PRAGMA journal_mode=WAL")
            con.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=10)

    def append(self, event: Event) -> bool:
        return self.extend([event]) == 1

    def extend(self, events: Iterable[Event]) -> int:
        rows = [
            (
                str(e.event_id),
                e.type,
                _ts(e.occurred_at),
                _ts(e.recorded_at),
                e.source,
                json.dumps(e.payload, ensure_ascii=False, sort_keys=True),
            )
            for e in events
        ]
        with closing(self._connect()) as con, con:
            before = con.total_changes
            con.executemany("INSERT OR IGNORE INTO events VALUES (?, ?, ?, ?, ?, ?)", rows)
            return con.total_changes - before

    def read(
        self, types: Collection[str] | None = None, since: datetime | None = None
    ) -> list[Event]:
        sql = "SELECT event_id, type, occurred_at, recorded_at, source, payload FROM events"
        where: list[str] = []
        params: list[str] = []
        if types is not None:
            where.append(f"type IN ({', '.join('?' for _ in types)})")
            params.extend(types)
        if since is not None:
            where.append("occurred_at >= ?")
            params.append(_ts(since))
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY occurred_at, recorded_at, event_id"
        with closing(self._connect()) as con:
            rows = con.execute(sql, params).fetchall()
        return [
            Event.model_validate(
                {
                    "event_id": r[0],
                    "type": r[1],
                    "occurred_at": _parse_ts(r[2]),
                    "recorded_at": _parse_ts(r[3]),
                    "source": r[4],
                    "payload": json.loads(r[5]),
                }
            )
            for r in rows
        ]
