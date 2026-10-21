from pathlib import Path

import pytest

from skillforge.data.build import build_warehouse

TEST_SCALE = 0.05


@pytest.fixture(scope="session")
def warehouse(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A small, fully built warehouse (raw + dbt marts), shared by integration tests."""
    path = tmp_path_factory.mktemp("wh") / "warehouse.duckdb"
    code = build_warehouse(path, scale=TEST_SCALE, quiet=True)
    assert code == 0, "dbt build failed for the test warehouse"
    return path
