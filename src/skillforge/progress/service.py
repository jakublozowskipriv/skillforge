"""Facade used by the UI and the CLI. Writes events; reads through projections."""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable
from datetime import date, datetime
from typing import TYPE_CHECKING, Literal, cast

from skillforge import paths
from skillforge.progress import projections as proj
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
    _Payload,
    utcnow,
)
from skillforge.progress.store import EventStore, SqliteEventStore

if TYPE_CHECKING:
    from skillforge.evaluator import EvalResult

SessionKind = Literal["theory", "practice", "review", "other"]


class Progress:
    def __init__(
        self,
        store: EventStore,
        *,
        source: EventSource = "pc",
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self.store = store
        self.source = source
        self.clock = clock

    def _emit(self, payload: _Payload, occurred_at: datetime | None = None) -> Event:
        event = Event.new(payload, source=self.source, occurred_at=occurred_at or self.clock())
        self.store.append(event)
        return event

    # --- writes -----------------------------------------------------------------------------
    def log_session(
        self,
        day: date,
        minutes: int,
        kind: SessionKind = "other",
        topic: str | None = None,
        note: str = "",
    ) -> Event:
        return self._emit(
            SessionLogged(day=day, minutes=minutes, kind=kind, topic=topic, note=note)
        )

    def add_brag(
        self,
        day: date,
        context: str,
        role: str,
        effect: str,
        effect_value: float | None = None,
        effect_unit: str | None = None,
        evidence: str = "",
    ) -> Event:
        return self._emit(
            BragAdded(
                day=day,
                context=context,
                role=role,
                effect=effect,
                effect_value=effect_value,
                effect_unit=effect_unit,
                evidence=evidence,
            )
        )

    def retract_brag(self, entry_id: uuid.UUID, reason: str = "") -> Event:
        return self._emit(BragRetracted(entry_id=entry_id, reason=reason))

    def record_kpi(self, kpi_id: str, value: float, note: str = "") -> Event:
        return self._emit(KpiRecorded(kpi_id=kpi_id, value=value, note=note))

    def set_level(self, topic: str, level: int) -> Event:
        return self._emit(LevelSet(topic=topic, level=level))

    def record_attempt(self, exercise_id: str, code: str, result: EvalResult) -> Event:
        return self._emit(
            ExerciseAttempted(
                exercise_id=exercise_id,
                passed=result.passed,
                score=result.score,
                code=code,
                result=result.to_dict(),
            )
        )

    def review_card(
        self, card_id: str, rating: int, duration_s: float | None = None, at: datetime | None = None
    ) -> Event:
        r = cast(Literal[1, 2, 3, 4], rating)
        return self._emit(CardReviewed(card_id=card_id, rating=r, duration_s=duration_s), at)

    def record_quiz(self, topic: str, score: int, total: int, note: str = "") -> Event:
        return self._emit(QuizCompleted(topic=topic, score=score, total=total, note=note))

    # --- reads ------------------------------------------------------------------------------
    def events(self) -> list[Event]:
        return self.store.read()

    def sessions(self) -> list[proj.Session]:
        return proj.sessions(self.store.read(["session.logged"]))

    def brag_entries(self) -> list[proj.BragEntry]:
        return proj.brag_entries(self.store.read(["brag.added", "brag.retracted"]))

    def kpi_history(self) -> dict[str, list[proj.KpiPoint]]:
        return proj.kpi_history(self.store.read(["kpi.recorded"]))

    def kpi_latest(self) -> dict[str, proj.KpiPoint]:
        return proj.kpi_latest(self.store.read(["kpi.recorded"]))

    def levels(self) -> dict[str, int]:
        return proj.levels(self.store.read(["level.set"]))

    def attempts(self, exercise_id: str | None = None) -> list[proj.Attempt]:
        return proj.attempts(self.store.read(["exercise.attempted"]), exercise_id)

    def exercise_stats(self) -> dict[str, proj.ExerciseStats]:
        return proj.exercise_stats(self.store.read(["exercise.attempted"]))

    def card_reviews(self) -> dict[str, list[proj.Review]]:
        return proj.card_reviews(self.store.read(["card.reviewed"]))

    def quiz_results(self) -> list[proj.QuizResult]:
        return proj.quiz_results(self.store.read(["quiz.completed"]))


def default_progress() -> Progress:
    """Progress backed by ``var/progress.db``. Device label from ``SKILLFORGE_SOURCE``."""
    source = cast(EventSource, os.environ.get("SKILLFORGE_SOURCE", "pc"))
    return Progress(SqliteEventStore(paths.PROGRESS_DB_PATH), source=source)
