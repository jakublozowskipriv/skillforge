"""``progress.json``: the event log + a summary snapshot for the tutor (Claude Code commands).

Import is idempotent (set union by ``event_id``), so exporting on one device and importing on
another — in any order, any number of times — converges to the same state.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from skillforge.progress import projections as proj
from skillforge.progress.events import Event, utcnow
from skillforge.progress.store import EventStore

SCHEMA_VERSION = 1


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def summary(events: list[Event], *, now: datetime | None = None) -> dict[str, Any]:
    """Compact state for the tutor: what to teach next and how the week went."""
    now = now or utcnow()
    recent_since = (now - timedelta(days=28)).date()
    stats = proj.exercise_stats(events)
    result: dict[str, Any] = _jsonable(
        {
            "levels": proj.levels(events),
            "exercises": {k: asdict(v) for k, v in stats.items()},
            "weak_exercises": sorted(k for k, v in stats.items() if not v.solved or v.attempts > 2),
            "kpi_latest": {k: asdict(v) for k, v in proj.kpi_latest(events).items()},
            "sessions_last_28_days": [
                asdict(s) for s in proj.sessions(events) if s.day >= recent_since
            ],
            "quizzes": [asdict(q) for q in proj.quiz_results(events)],
            "brag_entries": len(proj.brag_entries(events)),
            "cards_reviewed": {k: len(v) for k, v in proj.card_reviews(events).items()},
        }
    )
    return result


def export_json(store: EventStore, path: Path, *, include_summary: bool = True) -> int:
    events = store.read()
    doc: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "exported_at": utcnow().isoformat(),
        "events": [e.model_dump(mode="json") for e in events],
    }
    if include_summary:
        doc["summary"] = summary(events)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return len(events)


def import_json(store: EventStore, path: Path) -> int:
    """Merge events from an export; returns the number of events that were new here."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version {doc.get('schema_version')!r}")
    return store.extend(Event.model_validate(e) for e in doc["events"])


def brag_markdown(entries: list[proj.BragEntry]) -> str:
    """Brag doc as Markdown: date · context · my role · effect (number) · evidence."""
    lines = ["# Brag doc", ""]
    for b in entries:
        number = ""
        if b.effect_value is not None:
            number = f" (**{b.effect_value:g}{(' ' + b.effect_unit) if b.effect_unit else ''}**)"
        evidence = f" · [dowód]({b.evidence})" if b.evidence else ""
        lines.append(
            f"- **{b.day.isoformat()}** · {b.context} · {b.role} · {b.effect}{number}{evidence}"
        )
    return "\n".join(lines) + "\n"
