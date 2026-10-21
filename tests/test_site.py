import json
from pathlib import Path

from skillforge import paths
from skillforge.content.loader import load_content
from skillforge.site.generate import write_docs
from skillforge.site.offline import manifest, precache_list, write_service_worker


def test_write_docs_from_repo_content(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    written = write_docs(load_content(), docs, paths.SITE_DIR / "assets")
    assert (docs / "index.md").exists() and (docs / "assets" / "register-sw.js").exists()
    lesson = (docs / "analytics-engineering" / "ae-02.md").read_text(encoding="utf-8")
    assert lesson.startswith("# Modelowanie wymiarowe")
    assert "### ae-ex-07 · Klucz surogatowy" in lesson
    assert '??? success "Rozwiązanie referencyjne"' in lesson
    assert "## Fiszki" in lesson and '??? question "' in lesson
    assert len(written) == 1 + 1 + 3  # home + path index + 3 lessons


def test_rewrite_removes_stale_pages(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    (docs / "old").mkdir(parents=True)
    (docs / "old" / "gone.md").write_text("x", encoding="utf-8")
    write_docs(load_content(), docs, paths.SITE_DIR / "assets")
    assert not (docs / "old").exists()


def test_service_worker_precaches_built_files(tmp_path: Path) -> None:
    site = tmp_path / "site"
    (site / "lesson").mkdir(parents=True)
    (site / "index.html").write_text("<h1>home</h1>", encoding="utf-8")
    (site / "lesson" / "index.html").write_text("<h1>l</h1>", encoding="utf-8")
    (site / "sitemap.xml").write_text("<x/>", encoding="utf-8")
    assert precache_list(site) == ["./", "index.html", "lesson/", "lesson/index.html"]

    sw = write_service_worker(site).read_text(encoding="utf-8")
    first_version = sw.split('"')[1]
    (site / "lesson" / "index.html").write_text("<h1>changed</h1>", encoding="utf-8")
    assert write_service_worker(site).read_text(encoding="utf-8").split('"')[1] != first_version


def test_manifest_is_installable() -> None:
    data = manifest("skillforge")
    assert data["display"] == "standalone" and data["start_url"] == "./"
    icons = data["icons"]
    assert isinstance(icons, list)
    assert {"192x192", "512x512"} <= {icon["sizes"] for icon in icons}
    for icon in icons:
        assert (paths.SITE_DIR / icon["src"]).exists()
    json.dumps(data)
