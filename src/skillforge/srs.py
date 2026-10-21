"""Spaced repetition (FSRS) as a fold over review events.

The card state is never stored: it is recomputed from the ``card.reviewed`` events of that card,
replayed in ``occurred_at`` order. A review made on the phone and synced days later is replayed at
the moment it actually happened, so every device computes the same schedule from the same log.

Why FSRS and not SM-2: see DECISIONS.md. The ``fsrs`` library is used only in this module.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from fsrs import Card as FsrsCard
from fsrs import Rating, Scheduler, State

from skillforge.progress.projections import Review

# No fuzzing: fuzz adds randomness to intervals, so two devices folding the same log would
# disagree. Determinism matters more than spreading reviews for a small personal deck.
SCHEDULER = Scheduler(enable_fuzzing=False)

RATING_LABELS: dict[int, str] = {1: "Again", 2: "Hard", 3: "Good", 4: "Easy"}
_STATE_NAMES = {State.Learning: "learning", State.Review: "review", State.Relearning: "relearning"}


@dataclass(frozen=True)
class CardState:
    card_id: str
    state: str  # new | learning | review | relearning
    due: datetime | None  # None = new card, available now
    reviews: int
    last_review: datetime | None
    stability: float | None
    difficulty: float | None

    def is_due(self, now: datetime) -> bool:
        return self.due is None or self.due <= now


def _fold(reviews: Sequence[Review]) -> FsrsCard | None:
    if not reviews:
        return None
    ordered = sorted(reviews, key=lambda r: r.at)
    card = FsrsCard(card_id=0, due=ordered[0].at)
    for review in ordered:
        card, _ = SCHEDULER.review_card(card, Rating(review.rating), review_datetime=review.at)
    return card


def card_state(card_id: str, reviews: Sequence[Review]) -> CardState:
    card = _fold(reviews)
    if card is None:
        return CardState(card_id, "new", None, 0, None, None, None)
    return CardState(
        card_id=card_id,
        state=_STATE_NAMES[card.state],
        due=card.due,
        reviews=len(reviews),
        last_review=card.last_review,
        stability=card.stability,
        difficulty=card.difficulty,
    )


def preview_intervals(reviews: Sequence[Review], now: datetime) -> dict[int, timedelta]:
    """What each rating would do right now — shown on the rating buttons."""
    out: dict[int, timedelta] = {}
    for rating in RATING_LABELS:
        simulated = [*reviews, Review(at=now, rating=rating, duration_s=None)]
        card = _fold(simulated)
        assert card is not None
        out[rating] = card.due - now
    return out


def format_interval(delta: timedelta) -> str:
    minutes = delta.total_seconds() / 60
    if minutes < 60:
        return f"{max(1, round(minutes))} min"
    if minutes < 24 * 60:
        return f"{round(minutes / 60)} h"
    days = minutes / (24 * 60)
    return f"{round(days)} d" if days < 60 else f"{days / 30:.1f} mies."


@dataclass(frozen=True)
class Queue:
    due: list[CardState]  # reviewed before, due now (most overdue first)
    new: list[CardState]  # never reviewed, within today's new-card limit
    new_remaining: int  # new cards left in the deck after today's limit

    @property
    def items(self) -> list[CardState]:
        return [*self.due, *self.new]


def daily_queue(
    card_ids: Iterable[str],
    reviews: dict[str, list[Review]],
    now: datetime,
    *,
    new_per_day: int = 10,
) -> Queue:
    """Today's queue: due reviews first, then new cards up to ``new_per_day``.

    The new-card budget counts cards first reviewed on ``now``'s date, so it holds across
    sessions and devices.
    """
    states = [card_state(cid, reviews.get(cid, [])) for cid in card_ids]
    introduced_today = sum(
        1
        for cid, items in reviews.items()
        if items and min(r.at for r in items).date() == now.date()
    )
    budget = max(0, new_per_day - introduced_today)
    due = sorted(
        (s for s in states if s.state != "new" and s.is_due(now)),
        key=lambda s: s.due or now,
    )
    new = [s for s in states if s.state == "new"]
    return Queue(due=due, new=new[:budget], new_remaining=max(0, len(new) - budget))
