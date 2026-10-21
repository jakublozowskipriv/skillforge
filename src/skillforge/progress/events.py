"""Event envelope and typed payloads."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EventSource = Literal["pc", "phone"]
EventType = Literal[
    "session.logged",
    "brag.added",
    "brag.retracted",
    "kpi.recorded",
    "level.set",
    "exercise.attempted",
    "card.reviewed",
    "quiz.completed",
]


class _Payload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SessionLogged(_Payload):
    day: date
    minutes: int = Field(gt=0, le=600)
    kind: Literal["theory", "practice", "review", "other"] = "other"
    topic: str | None = None
    note: str = ""


class BragAdded(_Payload):
    """Brag doc entry: date · context · my role · effect (number) · evidence (link)."""

    day: date
    context: str
    role: str
    effect: str
    effect_value: float | None = None
    effect_unit: str | None = None
    evidence: str = ""


class BragRetracted(_Payload):
    entry_id: uuid.UUID  # event_id of the brag.added event
    reason: str = ""


class KpiRecorded(_Payload):
    kpi_id: str
    value: float
    note: str = ""


class LevelSet(_Payload):
    topic: str
    level: int = Field(ge=0, le=3)


class ExerciseAttempted(_Payload):
    exercise_id: str
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    code: str
    result: dict[str, Any] = Field(default_factory=dict)


class CardReviewed(_Payload):
    card_id: str
    rating: Literal[1, 2, 3, 4]  # FSRS: 1 Again, 2 Hard, 3 Good, 4 Easy
    duration_s: float | None = None


class QuizCompleted(_Payload):
    topic: str
    score: int = Field(ge=0)
    total: int = Field(gt=0)
    note: str = ""

    @model_validator(mode="after")
    def _score_le_total(self) -> QuizCompleted:
        if self.score > self.total:
            raise ValueError("score cannot exceed total")
        return self


PAYLOADS: dict[str, type[_Payload]] = {
    "session.logged": SessionLogged,
    "brag.added": BragAdded,
    "brag.retracted": BragRetracted,
    "kpi.recorded": KpiRecorded,
    "level.set": LevelSet,
    "exercise.attempted": ExerciseAttempted,
    "card.reviewed": CardReviewed,
    "quiz.completed": QuizCompleted,
}
PAYLOAD_TYPES: dict[type[_Payload], str] = {v: k for k, v in PAYLOADS.items()}


def utcnow() -> datetime:
    return datetime.now(UTC)


class Event(BaseModel):
    """Immutable envelope. ``occurred_at`` = when it happened; ``recorded_at`` = when written."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: uuid.UUID
    type: EventType
    occurred_at: datetime
    recorded_at: datetime
    source: EventSource
    payload: dict[str, Any]

    @field_validator("occurred_at", "recorded_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def _valid_payload(self) -> Event:
        PAYLOADS[self.type].model_validate(self.payload)
        return self

    @classmethod
    def new(
        cls,
        payload: _Payload,
        *,
        source: EventSource,
        occurred_at: datetime | None = None,
        event_id: uuid.UUID | None = None,
    ) -> Event:
        now = utcnow()
        return cls(
            event_id=event_id or uuid.uuid4(),
            type=PAYLOAD_TYPES[type(payload)],  # type: ignore[arg-type]
            occurred_at=occurred_at or now,
            recorded_at=now,
            source=source,
            payload=payload.model_dump(mode="json"),
        )

    def parsed(self) -> _Payload:
        return PAYLOADS[self.type].model_validate(self.payload)

    @property
    def sort_key(self) -> tuple[datetime, datetime, str]:
        """Deterministic order on every device: by occurrence, then write time, then id."""
        return (self.occurred_at, self.recorded_at, str(self.event_id))
