"""Well-known filesystem locations, resolved relative to the repo root.

Everything private (warehouse, progress, reviews) lives under ``var/``, which is gitignored.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(os.environ.get("SKILLFORGE_ROOT", Path(__file__).resolve().parents[2]))
VAR_DIR = Path(os.environ.get("SKILLFORGE_VAR", REPO_ROOT / "var"))
CONTENT_DIR = REPO_ROOT / "content"
DBT_DIR = REPO_ROOT / "dbt"

WAREHOUSE_PATH = VAR_DIR / "warehouse.duckdb"
PROGRESS_DB_PATH = VAR_DIR / "progress.db"
PROGRESS_JSON_PATH = VAR_DIR / "progress.json"

PROFILE_PATH = REPO_ROOT / "profile.yaml"
PROFILE_EXAMPLE_PATH = REPO_ROOT / "profile.example.yaml"
