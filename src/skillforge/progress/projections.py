"""Pure functions: event log → current state. No I/O, trivially testable, portable to JS."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from skillforge.progress.events import (
    BragAdded,
    BragRetracted,
    CardReviewed,
    Event,
    EventSource,
    ExerciseAttempted,
    KpiRecorded,
    LevelSet,
    QuizCompleted,
    SessionLogged,
)


def _ordered(events: Iterable[Event], event_type: str) -> list[Event]:
    return sorted((e for e in events if e.type == event_type), key=lambda e: e.sort_key)


@dataclass(frozen=True)
class Session:
    event_id: uuid.UUID
    day: date
    minutes: int
    kind: str
    topic: str | None
    note: str
    source: EventSource


def sessions(events: Iterable[Event]) -> list[Session]:
    out = []
    for e in _ordered(events, "session.logged"):
        p = SessionLogged.model_validate(e.payload)
        out.append(Session(e.event_id, p.day, p.minutes, p.kind, p.topic, p.note, e.source))
    return sorted(out, key=lambda s: s.day)


@dataclass(frozen=True)
class BragEntry:
    entry_id: uuid.UUID
    day: date
    context: str
    role: str
    effect: str
    effect_value: float | None
    effect_unit: str | None
    evidence: str


def brag_entries(events: Iterable[Event]) -> list[BragEntry]:
    events = list(events)
    retracted = {
        BragRetracted.model_validate(e.payload).entry_id for e in _ordered(events, "brag.retracted")
    }
    out = []
    for e in _ordered(events, "brag.added"):
        if e.event_id in retracted:
            continue
        p = BragAdded.model_validate(e.payload)
        out.append(
            BragEntry(
                e.event_id,
                p.day,
                p.context,
                p.role,
                p.effect,
                p.effect_value,
                p.effect_unit,
                p.evidence,
            )
        )
    return sorted(out, key=lambda b: b.day)


@dataclass(frozen=True)
class KpiPoint:
    at: datetime
    value: float
    note: str


def kpi_history(events: Iterable[Event]) -> dict[str, list[KpiPoint]]:
    out: dict[str, list[KpiPoint]] = defaultdict(list)
    for e in _ordered(events, "kpi.recorded"):
        p = KpiRecorded.model_validate(e.payload)
        out[p.kpi_id].append(KpiPoint(e.occurred_at, p.value, p.note))
    return dict(out)


def kpi_latest(events: Iterable[Event]) -> dict[str, KpiPoint]:
    """Last value per KPI by ``occurred_at`` (a correction is just a newer value)."""
    return {k: points[-1] for k, points in kpi_history(events).items()}


def levels(events: Iterable[Event]) -> dict[str, int]:
    out: dict[str, int] = {}
    for e in _ordered(events, "level.set"):
        p = LevelSet.model_validate(e.payload)
        out[p.topic] = p.level
    return out


@dataclass(frozen=True)
class Attempt:
    event_id: uuid.UUID
    at: datetime
    exercise_id: str
    passed: bool
    score: float
    code: str
    result: dict[str, Any]


def attempts(events: Iterable[Event], exercise_id: str | None = None) -> list[Attempt]:
    out = []
    for e in _ordered(events, "exercise.attempted"):
        p = ExerciseAttempted.model_validate(e.payload)
        if exercise_id is None or p.exercise_id == exercise_id:
            out.append(
                Attempt(
                    e.event_id, e.occurred_at, p.exercise_id, p.passed, p.score, p.code, p.result
                )
            )
    return out


@dataclass(frozen=True)
class ExerciseStats:
    attempts: int
    solved: bool
    best_score: float
    last_at: datetime
    first_try: bool  # solved on the first attempt


def exercise_stats(events: Iterable[Event]) -> dict[str, ExerciseStats]:
    grouped: dict[str, list[Attempt]] = defaultdict(list)
    for a in attempts(events):
        grouped[a.exercise_id].append(a)
    return {
        ex_id: ExerciseStats(
            attempts=len(items),
            solved=any(a.passed for a in items),
            best_score=max(a.score for a in items),
            last_at=items[-1].at,
            first_try=items[0].passed,
        )
        for ex_id, items in grouped.items()
    }


@dataclass(frozen=True)
class Review:
    at: datetime
    rating: int
    duration_s: float | None


def card_reviews(events: Iterable[Event]) -> dict[str, list[Review]]:
    """Reviews per card in occurrence order — the input of the FSRS fold (see ``srs``)."""
    out: dict[str, list[Review]] = defaultdict(list)
    for e in _ordered(events, "card.reviewed"):
        p = CardReviewed.model_validate(e.payload)
        out[p.card_id].append(Review(e.occurred_at, p.rating, p.duration_s))
    return dict(out)


@dataclass(frozen=True)
class QuizResult:
    at: datetime
    topic: str
    score: int
    total: int
    note: str


def quiz_results(events: Iterable[Event]) -> list[QuizResult]:
    out = []
    for e in _ordered(events, "quiz.completed"):
        p = QuizCompleted.model_validate(e.payload)
        out.append(QuizResult(e.occurred_at, p.topic, p.score, p.total, p.note))
    return out
