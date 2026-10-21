"""Command line entry point (``uv run skillforge ...``).

The CLI is the stable interface used by both humans and the Claude Code tutor commands in
``.claude/commands/``: commands call the CLI instead of touching databases directly.
"""

from __future__ import annotations

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

SeedOpt = Annotated[int, typer.Option(help="Random seed (dataset is deterministic per seed).")]
ScaleOpt = Annotated[float, typer.Option(help="Volume multiplier; 1.0 ≈ 19k orders.")]
WarehouseOpt = Annotated[Path, typer.Option(help="DuckDB warehouse file.")]


@app.callback()
def main() -> None:
    """skillforge CLI."""


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


if __name__ == "__main__":
    app()
