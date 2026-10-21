import uuid
from datetime import date

from skillforge.planner import plan_week, week_start
from skillforge.profile import Profile
from skillforge.progress.projections import Session

PROFILE = Profile.model_validate(
    {
        "rhythm": [
            {"id": "t", "label": "Teoria", "kind": "theory", "days": ["tue"], "minutes": 60},
            {
                "id": "p",
                "label": "Praktyka",
                "kind": "practice",
                "days": ["sat", "sun"],
                "minutes": 75,
            },
            {"id": "r", "label": "Przegląd", "kind": "review", "days": ["fri"], "minutes": 10},
        ],
        "light_months": [12],
    }
)


def session(day: date, kind: str, minutes: int = 60) -> Session:
    return Session(uuid.uuid4(), day, minutes, kind, None, "", "pc")


def test_week_start_is_monday() -> None:
    assert week_start(date(2026, 10, 22)) == date(2026, 10, 19)  # Thursday → Monday


def test_slot_statuses_midweek() -> None:
    # Friday 2026-10-23: theory was done on Wednesday (not Tuesday) and still counts.
    plan = plan_week(PROFILE, [session(date(2026, 10, 21), "theory")], date(2026, 10, 23))
    status = {s.slot.id: s.status for s in plan.slots}
    assert status == {"t": "done", "p": "upcoming", "r": "today"}
    assert plan.minutes_planned == 145 and plan.minutes_done == 60
    assert not plan.light


def test_missed_and_other_weeks_ignored() -> None:
    sessions = [session(date(2026, 10, 12), "practice"), session(date(2026, 10, 26), "practice")]
    plan = plan_week(PROFILE, sessions, date(2026, 10, 25))  # Sunday
    status = {s.slot.id: s.status for s in plan.slots}
    assert status == {"t": "missed", "p": "today", "r": "missed"}
    assert plan.sessions == ()


def test_light_month() -> None:
    assert plan_week(PROFILE, [], date(2026, 12, 9)).light
