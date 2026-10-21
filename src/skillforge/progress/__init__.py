"""User progress as an append-only event log.

Every user action (session, brag entry, KPI value, card review, exercise attempt, ...) is an
immutable event with a UUID and a source device. Current state is always *derived* from the log
by pure projection functions. Consequences:

- sync between devices is a set union of events by ``event_id`` — no merge conflicts,
- edits and deletions are new events (e.g. ``brag.retracted``), never UPDATE/DELETE,
- the storage backend is swappable: UI and CLI only see :class:`Progress` and the projections.
"""
