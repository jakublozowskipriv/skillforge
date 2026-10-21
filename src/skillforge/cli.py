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


if __name__ == "__main__":
    app()
