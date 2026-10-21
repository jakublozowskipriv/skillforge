import random
from datetime import UTC, datetime, timedelta

from skillforge.progress.projections import Review
from skillforge.srs import card_state, daily_queue, format_interval, preview_intervals

T0 = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)


def rv(days: float, rating: int) -> Review:
    return Review(at=T0 + timedelta(days=days), rating=rating, duration_s=None)


HISTORY = [rv(0, 3), rv(0.01, 3), rv(2, 3), rv(9, 1), rv(9.01, 3), rv(12, 4)]


def test_new_card_is_due_immediately() -> None:
    state = card_state("c", [])
    assert state.state == "new" and state.is_due(T0) and state.reviews == 0


def test_state_is_independent_of_write_order() -> None:
    shuffled = HISTORY.copy()
    random.Random(1).shuffle(shuffled)
    assert card_state("c", shuffled) == card_state("c", HISTORY)


def test_late_synced_phone_review_lands_in_place() -> None:
    # Phone review on day 2 was synced after the PC review on day 9: same state as real time.
    pc_first = [r for r in HISTORY if r != rv(2, 3)] + [rv(2, 3)]
    assert card_state("c", pc_first) == card_state("c", HISTORY)


def test_good_pushes_due_further_than_again() -> None:
    preview = preview_intervals(HISTORY, T0 + timedelta(days=30))
    assert preview[1] < preview[2] < preview[3] < preview[4]
    assert preview[1] <= timedelta(minutes=10)


def test_deterministic_no_fuzz() -> None:
    assert [card_state("c", HISTORY) for _ in range(3)] == [card_state("c", HISTORY)] * 3


def test_daily_queue_due_first_then_new_with_limit() -> None:
    reviews = {"seen": [rv(-10, 3)]}
    ids = ["seen", *(f"new{i}" for i in range(5))]
    q = daily_queue(ids, reviews, T0, new_per_day=3)
    assert [s.card_id for s in q.due] == ["seen"]
    assert [s.card_id for s in q.new] == ["new0", "new1", "new2"]
    assert q.new_remaining == 2


def test_new_budget_counts_cards_introduced_today() -> None:
    reviews = {"a": [rv(0, 3)], "b": [rv(0, 3)]}
    q = daily_queue(["a", "b", "c", "d"], reviews, T0 + timedelta(hours=1), new_per_day=3)
    assert [s.card_id for s in q.new] == ["c"]


def test_format_interval() -> None:
    assert format_interval(timedelta(minutes=10)) == "10 min"
    assert format_interval(timedelta(hours=5)) == "5 h"
    assert format_interval(timedelta(days=3)) == "3 d"
