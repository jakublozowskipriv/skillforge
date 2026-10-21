"""Command line entry point (``uv run skillforge ...``).

The CLI is the stable interface used by both humans and the Claude Code tutor commands in
``.claude/commands/``: commands call the CLI instead of touching databases directly.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Annotated

import typer

from skillforge import __version__, paths

app = typer.Typer(
    help="skillforge: local learning app (AE + AI for analytics).", no_args_is_help=True
)
data_app = typer.Typer(help="Synthetic dataset and dbt warehouse.", no_args_is_help=True)
app.add_typer(data_app, name="data")
content_app = typer.Typer(
    help="Lessons, exercises and flashcards in content/.", no_args_is_help=True
)
app.add_typer(content_app, name="content")
progress_app = typer.Typer(
    help="Your progress (event log in var/progress.db).", no_args_is_help=True
)
app.add_typer(progress_app, name="progress")
site_app = typer.Typer(help="Static lesson site for the phone (MkDocs).", no_args_is_help=True)
app.add_typer(site_app, name="site")

SeedOpt = Annotated[int, typer.Option(help="Random seed (dataset is deterministic per seed).")]
ScaleOpt = Annotated[float, typer.Option(help="Volume multiplier; 1.0 ≈ 19k orders.")]
WarehouseOpt = Annotated[Path, typer.Option(help="DuckDB warehouse file.")]


@app.callback()
def main() -> None:
    """skillforge CLI."""
    # Windows pipes/redirects may use a legacy code page (cp1250/cp1252): never crash on → or ✓.
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(errors="replace")


@app.command()
def version() -> None:
    """Print the installed version."""
    typer.echo(__version__)


@data_app.command("generate")
def data_generate(
    seed: SeedOpt = 42,
    scale: ScaleOpt = 1.0,
    warehouse: WarehouseOpt = paths.WAREHOUSE_PATH,
) -> None:
    """Generate the synthetic dataset into the `raw` schema."""
    from skillforge.data.generate import generate, load_raw

    counts = load_raw(generate(seed=seed, scale=scale), warehouse)
    for name, n in counts.items():
        typer.echo(f"raw.{name:<20} {n:>8,}")
    typer.echo(f"→ {warehouse}")


@data_app.command("build")
def data_build(
    seed: SeedOpt = 42,
    scale: ScaleOpt = 1.0,
    warehouse: WarehouseOpt = paths.WAREHOUSE_PATH,
) -> None:
    """Generate raw data and run `dbt build` (models + tests). One command after a fresh clone."""
    from skillforge.data.build import build_warehouse

    code = build_warehouse(warehouse, seed=seed, scale=scale)
    if code != 0:
        typer.secho("dbt build failed — see output above.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code)
    typer.secho(f"Warehouse ready → {warehouse}", fg=typer.colors.GREEN)


@content_app.command("snapshot")
def content_snapshot(
    ids: Annotated[list[str] | None, typer.Argument(help="Exercise ids; default: all.")] = None,
    warehouse: WarehouseOpt = paths.WAREHOUSE_PATH,
) -> None:
    """Run reference solutions and freeze their results as `<id>.expected.json`."""
    from skillforge.content.loader import load_exercises
    from skillforge.content.snapshot import snapshot_exercise

    selected = [e for e in load_exercises() if not ids or e.id in ids]
    missing = set(ids or []) - {e.id for e in selected}
    if missing:
        typer.secho(f"Unknown exercise ids: {', '.join(sorted(missing))}", fg="red", err=True)
        raise typer.Exit(1)
    for ex in selected:
        result = snapshot_exercise(ex, warehouse)
        info = f"{result.row_count} rows" if result else "python — expectations live in YAML"
        typer.echo(f"{ex.id:<12} {info}")


@content_app.command("validate")
def content_validate(
    warehouse: WarehouseOpt = paths.WAREHOUSE_PATH,
    golden: Annotated[
        bool, typer.Option(help="Also run reference solutions against snapshots (needs warehouse).")
    ] = True,
) -> None:
    """Check schemas, cross-references and that every reference reproduces its snapshot."""
    from skillforge.content.loader import load_content
    from skillforge.content.validate import validate_content

    problems = validate_content(paths.CONTENT_DIR, warehouse if golden else None)
    for p in problems:
        typer.secho(f"✗ {p}", fg="red", err=True)
    if problems:
        raise typer.Exit(1)
    index = load_content()
    typer.secho(
        f"✓ content valid: {len(index.lessons)} lessons, {len(index.exercises)} exercises, "
        f"{len(index.cards)} cards" + ("" if golden else " (golden set not checked)"),
        fg="green",
    )


def _echo_json(data: object) -> None:
    import json

    typer.echo(json.dumps(data, ensure_ascii=False, indent=2, default=str))


@progress_app.command("export")
def progress_export(
    out: Annotated[Path, typer.Option(help="Output file.")] = paths.PROGRESS_JSON_PATH,
) -> None:
    """Write the event log + summary to progress.json (read by the tutor commands)."""
    from skillforge.progress.export import export_json
    from skillforge.progress.service import default_progress

    n = export_json(default_progress().store, out)
    typer.echo(f"{n} events → {out}")


@progress_app.command("import")
def progress_import(file: Annotated[Path, typer.Argument(help="progress.json to merge.")]) -> None:
    """Merge events from another device's export (idempotent)."""
    from skillforge.progress.export import import_json
    from skillforge.progress.service import default_progress

    n = import_json(default_progress().store, file)
    typer.echo(f"{n} new events imported")


@progress_app.command("summary")
def progress_summary() -> None:
    """Print the tutor summary (levels, weak exercises, KPI, recent sessions) as JSON."""
    from skillforge.progress.export import summary
    from skillforge.progress.service import default_progress

    _echo_json(summary(default_progress().events()))


@progress_app.command("attempts")
def progress_attempts(
    exercise_id: Annotated[str, typer.Argument(help="Exercise id, e.g. ae-ex-01.")],
    last: Annotated[bool, typer.Option("--last", help="Only the most recent attempt.")] = False,
) -> None:
    """Print attempts (code + evaluation result) as JSON — input for /review."""
    from dataclasses import asdict

    from skillforge.progress.service import default_progress

    found = default_progress().attempts(exercise_id)
    if not found:
        typer.secho(f"No attempts for {exercise_id}", fg="yellow", err=True)
        raise typer.Exit(1)
    selected = found[-1:] if last else found
    _echo_json([asdict(a) for a in selected])


@progress_app.command("record-quiz")
def progress_record_quiz(
    topic: Annotated[str, typer.Option(help="Topic id from content/tree.yaml.")],
    score: Annotated[int, typer.Option(help="Correct answers.")],
    total: Annotated[int, typer.Option(help="Number of questions.")],
    note: Annotated[str, typer.Option(help="Short note: what went wrong.")] = "",
) -> None:
    """Record a quiz result (used by /quiz)."""
    from skillforge.progress.service import default_progress

    default_progress().record_quiz(topic, score, total, note)
    typer.echo(f"quiz {topic}: {score}/{total} recorded")


@progress_app.command("brag")
def progress_brag(
    out: Annotated[Path | None, typer.Option(help="Write to file instead of stdout.")] = None,
) -> None:
    """Export the brag doc as Markdown."""
    from skillforge.progress.export import brag_markdown
    from skillforge.progress.service import default_progress

    text = brag_markdown(default_progress().brag_entries())
    if out:
        out.write_text(text, encoding="utf-8")
        typer.echo(f"→ {out}")
    else:
        typer.echo(text)


@site_app.command("build")
def site_build(
    serve: Annotated[bool, typer.Option(help="Serve locally with live reload instead.")] = False,
) -> None:
    """Generate pages from content/ and build the offline-capable site into build/site."""
    import subprocess

    from skillforge.content.loader import load_content
    from skillforge.site.generate import write_docs
    from skillforge.venv import executable

    pages = write_docs(load_content(), paths.BUILD_DIR / "site_docs", paths.SITE_DIR / "assets")
    typer.echo(f"{len(pages)} pages generated")
    config = str(paths.SITE_DIR / "mkdocs.yml")
    cmd = [executable("mkdocs"), "serve" if serve else "build", "-f", config]
    if not serve:
        cmd.append("--strict")
    code = subprocess.run(cmd, cwd=paths.REPO_ROOT, check=False).returncode
    if code != 0:
        raise typer.Exit(code)
    if not serve:
        typer.secho(f"Site ready → {paths.BUILD_DIR / 'site'}", fg=typer.colors.GREEN)


def _lan_addresses() -> list[str]:
    """Best-effort local IPv4 addresses (LAN and Tailscale 100.x), without external calls."""
    import socket

    found: set[str] = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            found.add(str(info[4][0]))
    except OSError:
        pass
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("192.0.2.1", 9))  # TEST-NET address: no packet is sent for UDP connect
            found.add(s.getsockname()[0])
        except OSError:
            pass
    return sorted(ip for ip in found if not ip.startswith("127."))


@app.command()
def serve(
    lan: Annotated[
        bool, typer.Option("--lan", help="Listen on all interfaces (phone via Wi-Fi/Tailscale).")
    ] = False,
    port: Annotated[int, typer.Option(help="Port.")] = 8501,
) -> None:
    """Run the app. With --lan it is reachable from other devices — see README (Tailscale)."""
    import subprocess

    address = "0.0.0.0" if lan else "localhost"
    if lan:
        typer.secho(
            "Uwaga: aplikacja nie ma logowania. Udostępniaj ją tylko w zaufanej sieci "
            "albo przez Tailscale.",
            fg=typer.colors.YELLOW,
        )
        for ip in _lan_addresses():
            typer.echo(f"  → http://{ip}:{port}")
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(paths.REPO_ROOT / "app.py"),
        "--server.address",
        address,
        "--server.port",
        str(port),
    ]
    raise typer.Exit(subprocess.run(cmd, cwd=paths.REPO_ROOT, check=False).returncode)


if __name__ == "__main__":
    app()
