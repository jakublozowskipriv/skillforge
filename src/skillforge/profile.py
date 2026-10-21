"""``profile.yaml``: weekly rhythm, KPI definitions and path priorities (private, gitignored)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from skillforge import paths

Weekday = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
WEEKDAYS: tuple[Weekday, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class RhythmSlot(_Model):
    id: str
    label: str
    kind: Literal["theory", "practice", "review"]
    days: list[Weekday] = Field(min_length=1)
    minutes: int = Field(gt=0)


class KpiTarget(_Model):
    by: date
    value: float


class KpiDef(_Model):
    id: str
    name: str
    unit: str = ""
    baseline: float = 0
    targets: list[KpiTarget] = Field(default_factory=list)

    def next_target(self, today: date) -> KpiTarget | None:
        upcoming = [t for t in self.targets if t.by >= today]
        return min(upcoming, key=lambda t: t.by) if upcoming else None


class Profile(_Model):
    rhythm: list[RhythmSlot]
    light_months: list[int] = Field(default_factory=list)
    path_priority: list[str] = Field(default_factory=list)
    kpis: list[KpiDef] = Field(default_factory=list)

    @property
    def weekly_minutes(self) -> int:
        return sum(s.minutes for s in self.rhythm)


def profile_path() -> Path:
    return paths.PROFILE_PATH if paths.PROFILE_PATH.exists() else paths.PROFILE_EXAMPLE_PATH


def load_profile(path: Path | None = None) -> Profile:
    data = yaml.safe_load((path or profile_path()).read_text(encoding="utf-8"))
    return Profile.model_validate(data)
