"""Weekly plan: the rhythm from ``profile.yaml`` vs the sessions actually logged."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from skillforge.profile import WEEKDAYS, Profile, RhythmSlot
from skillforge.progress.projections import Session

SlotStatus = Literal["done", "today", "upcoming", "missed"]


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


@dataclass(frozen=True)
class SlotProgress:
    slot: RhythmSlot
    dates: tuple[date, ...]  # concrete dates this week the slot may happen on
    minutes_done: int
    status: SlotStatus


@dataclass(frozen=True)
class WeekPlan:
    start: date
    slots: tuple[SlotProgress, ...]
    sessions: tuple[Session, ...]
    light: bool  # a "lighter" month per profile (e.g. December, August)

    @property
    def minutes_planned(self) -> int:
        return sum(s.slot.minutes for s in self.slots)

    @property
    def minutes_done(self) -> int:
        return sum(s.minutes for s in self.sessions)

    @property
    def end(self) -> date:
        return self.start + timedelta(days=6)


def plan_week(profile: Profile, sessions: Sequence[Session], today: date) -> WeekPlan:
    """A slot is *done* once a session of its kind (theory/practice/review) is logged this week.

    Slots are matched by kind, not by exact day: life happens, and a Tuesday theory hour done on
    Wednesday still counts. ``missed`` = all candidate days have passed without such a session.
    """
    start = week_start(today)
    week = tuple(s for s in sessions if start <= s.day <= start + timedelta(days=6))
    slots = []
    for slot in profile.rhythm:
        dates = tuple(start + timedelta(days=WEEKDAYS.index(d)) for d in slot.days)
        minutes = sum(s.minutes for s in week if s.kind == slot.kind)
        status: SlotStatus
        if minutes > 0:
            status = "done"
        elif today in dates:
            status = "today"
        elif all(d < today for d in dates):
            status = "missed"
        else:
            status = "upcoming"
        slots.append(SlotProgress(slot, dates, minutes, status))
    return WeekPlan(start, tuple(slots), week, today.month in profile.light_months)
