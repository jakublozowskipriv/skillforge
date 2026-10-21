"""Build the warehouse: generate ``raw`` and run ``dbt build`` (staging → intermediate → marts)."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from skillforge import paths
from skillforge.data.generate import DEFAULT_SEED, generate, load_raw


def dbt_executable() -> str:
    """The ``dbt`` CLI installed in the same environment as this interpreter.

    venv layout differs per OS: ``.venv/bin/dbt`` (Linux/macOS), ``.venv\\Scripts\\dbt.exe``
    (Windows). Falls back to whatever ``dbt`` is on PATH.
    """
    bin_dir = Path(sys.executable).parent
    for name in ("dbt", "dbt.exe"):
        candidate = bin_dir / name
        if candidate.exists():
            return str(candidate)
    return "dbt"


def run_dbt(args: Sequence[str], warehouse: Path, *, quiet: bool = False) -> int:
    """Run a dbt command against ``warehouse``; returns the exit code."""
    env = {
        **os.environ,
        # Forward slashes on every OS: DuckDB accepts them on Windows and they need no escaping.
        "SKILLFORGE_WAREHOUSE": warehouse.resolve().as_posix(),
        "DBT_PROFILES_DIR": str(paths.DBT_DIR),
        "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
        "PYTHONUTF8": "1",  # dbt logs contain non-ASCII model descriptions
    }
    cmd = [dbt_executable(), *args]
    if quiet:
        cmd.insert(1, "--quiet")
    completed = subprocess.run(cmd, cwd=paths.DBT_DIR, env=env, check=False)
    return completed.returncode


def build_warehouse(
    warehouse: Path = paths.WAREHOUSE_PATH,
    *,
    seed: int = DEFAULT_SEED,
    scale: float = 1.0,
    quiet: bool = False,
) -> int:
    """Regenerate ``raw`` and rebuild every dbt model with tests.

    ``--full-refresh`` because raw is recreated from scratch: incremental models must not keep
    rows from a previous (possibly different-seed) dataset.
    """
    load_raw(generate(seed=seed, scale=scale), warehouse)
    return run_dbt(["build", "--full-refresh"], warehouse, quiet=quiet)
