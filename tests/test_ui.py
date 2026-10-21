from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from skillforge import paths

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def run_app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert not at.exception, at.exception
    return at


def test_missing_warehouse_shows_build_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(paths, "WAREHOUSE_PATH", tmp_path / "missing.duckdb")
    at = run_app()
    assert any("skillforge data build" in c.value for c in at.code)


@pytest.mark.integration
def test_exercise_check_renders_result(warehouse: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths, "WAREHOUSE_PATH", warehouse)
    at = run_app()
    assert at.title[0].value == "🧪 Ćwiczenia"

    at.text_area[0].set_value("select event_type from raw.shipment_events group by 1").run()
    at.button(key="check:ae-ex-01").click().run()
    assert not at.exception
    assert any("Brakujące kolumny" in m.value for m in at.markdown)

    at.text_area[0].set_value("select from").run()
    at.button(key="check:ae-ex-01").click().run()
    assert any("Błąd wykonania" in e.value for e in at.error)


@pytest.mark.integration
def test_hints_are_revealed_one_by_one(warehouse: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths, "WAREHOUSE_PATH", warehouse)
    at = run_app()
    assert not at.info
    at.button(key="hint-btn:ae-ex-01").click().run()
    assert len(at.info) == 1 and "Podpowiedź 1" in at.info[0].value
