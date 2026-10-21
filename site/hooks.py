"""MkDocs hooks: after the build, write the web app manifest and the precaching service worker."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from skillforge.site.offline import manifest, write_service_worker


def on_post_build(config: Any, **kwargs: Any) -> None:
    site_dir = Path(config["site_dir"])
    (site_dir / "manifest.webmanifest").write_text(
        json.dumps(manifest(config["site_name"]), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_service_worker(site_dir)  # last: it hashes and precaches everything above
