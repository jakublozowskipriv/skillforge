"""Locate console scripts installed in the same environment as this interpreter."""

from __future__ import annotations

import sys
from pathlib import Path


def executable(name: str) -> str:
    """``.venv/bin/<name>`` (Linux/macOS) or ``.venv\\Scripts\\<name>.exe`` (Windows); else PATH."""
    bin_dir = Path(sys.executable).parent
    for candidate in (bin_dir / name, bin_dir / f"{name}.exe"):
        if candidate.exists():
            return str(candidate)
    return name
