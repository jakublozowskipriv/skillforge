"""Smoke tests of the Streamlit UI (AppTest runs the script in-process, no browser)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from skillforge import paths
from skillforge.progress.service import default_progress

APP = str(Path(__file__).resolve().parents[1] / "app.py")
TIMEOUT = 30


def _dashboard() -> None:
    from skillforge.ui.pages import dashboard

    dashboard.render()


def _lessons() -> None:
    from skillforge.ui.pages import lessons

    lessons.render()


def _exercises() -> None:
    from skillforge.ui.pages import exercises

    exercises.render()


def _flashcards() -> None:
    from skillforge.ui.pages import flashcards

    flashcards.render()


def _journal() -> None:
    from skillforge.ui.pages import journal

    journal.render()


def run_page(fn: object) -> AppTest:
    at = AppTest.from_function(fn, default_timeout=TIMEOUT)  # type: ignore[arg-type]
    at.run()
    assert not at.exception, at.exception
    return at


def test_app_starts_on_dashboard() -> None:
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.run()
    assert not at.exception, at.exception
    assert at.title[0].value == "🏠 Dashboard"


def test_dashboard_records_kpi() -> None:
    at = run_page(_dashboard)
    assert any(s.value.startswith("Ten tydzień") for s in at.subheader)
    at.number_input[0].set_value(3.0)
    at.button[-1].click().run()  # form submit button
    assert not at.exception
    assert next(iter(default_progress().kpi_latest().values())).value == 3.0


def test_lessons_render_and_set_level() -> None:
    at = run_page(_lessons)
    assert any("Warstwy w dbt" in m.value for m in at.markdown)
    at.selectbox(key="level:ae.dbt-layers").select(2).run()
    assert default_progress().levels() == {"ae.dbt-layers": 2}


def test_flashcards_reveal_and_rate() -> None:
    at = run_page(_flashcards)
    reveal = next(b for b in at.button if b.label == "Pokaż odpowiedź")
    reveal.click().run()
    good = next(b for b in at.button if b.label.startswith("3 ·"))
    good.click().run()
    assert not at.exception
    reviews = default_progress().card_reviews()
    assert len(reviews) == 1 and next(iter(reviews.values()))[0].rating == 3


def test_journal_logs_session_and_brag() -> None:
    at = run_page(_journal)
    at.number_input[0].set_value(45)
    at.text_area[0].set_value("dbt sources")
    next(b for b in at.button if b.label == "Zapisz sesję").click().run()
    assert [s.minutes for s in default_progress().sessions()] == [45]

    at.text_input[0].set_value("Analiza first mile")
    at.text_input[1].set_value("autor")
    at.text_input[2].set_value("krótszy odbiór")
    next(b for b in at.button if b.label == "Dodaj wpis").click().run()
    assert not at.exception
    assert [b.context for b in default_progress().brag_entries()] == ["Analiza first mile"]
    assert at.get("download_button")


def test_missing_warehouse_shows_build_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(paths, "WAREHOUSE_PATH", tmp_path / "missing.duckdb")
    at = run_page(_exercises)
    assert any("skillforge data build" in c.value for c in at.code)


@pytest.mark.integration
def test_exercise_check_records_attempt(warehouse: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths, "WAREHOUSE_PATH", warehouse)
    at = run_page(_exercises)
    at.text_area[0].set_value("select event_type from raw.shipment_events group by 1").run()
    at.button(key="check:ae-ex-01").click().run()
    assert not at.exception
    assert any("Brakujące kolumny" in m.value for m in at.markdown)

    at.text_area[0].set_value("select from").run()
    at.button(key="check:ae-ex-01").click().run()
    assert any("Błąd wykonania" in e.value for e in at.error)
    assert len(default_progress().attempts("ae-ex-01")) == 2
    assert any("Próby: 2" in c.value for c in at.caption)


@pytest.mark.integration
def test_hints_are_revealed_one_by_one(warehouse: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths, "WAREHOUSE_PATH", warehouse)
    at = run_page(_exercises)
    assert not at.info
    at.button(key="hint-btn:ae-ex-01").click().run()
    assert len(at.info) == 1 and "Podpowiedź 1" in at.info[0].value
