"""Load content files from disk."""

from __future__ import annotations

from pathlib import Path

import yaml

from skillforge import paths
from skillforge.content.models import Exercise


def load_exercise(path: Path) -> Exercise:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Exercise.model_validate({**data, "source_path": path})


def load_exercises(content_dir: Path | None = None) -> list[Exercise]:
    root = content_dir or paths.CONTENT_DIR
    files = sorted(root.glob("paths/*/exercises/*.yaml"))
    return [load_exercise(f) for f in files]
