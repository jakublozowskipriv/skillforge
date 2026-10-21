from datetime import date

from skillforge import paths
from skillforge.profile import load_profile


def test_example_profile_is_valid() -> None:
    profile = load_profile(paths.PROFILE_EXAMPLE_PATH)
    assert profile.rhythm and profile.kpis
    assert profile.weekly_minutes > 0


def test_next_target() -> None:
    kpi = load_profile(paths.PROFILE_EXAMPLE_PATH).kpis[1]
    target = kpi.next_target(date(2027, 4, 1))
    assert target is not None and target.by == date(2027, 6, 30)
    assert kpi.next_target(date(2030, 1, 1)) is None
