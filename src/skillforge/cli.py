"""Command line entry point (``uv run skillforge ...``).

The CLI is the stable interface used by both humans and the Claude Code tutor commands in
``.claude/commands/``: commands call the CLI instead of touching databases directly.
"""

from __future__ import annotations

import typer

from skillforge import __version__

app = typer.Typer(
    help="skillforge: local learning app (AE + AI for analytics).", no_args_is_help=True
)


@app.callback()
def main() -> None:
    """skillforge CLI."""


@app.command()
def version() -> None:
    """Print the installed version."""
    typer.echo(__version__)


if __name__ == "__main__":
    app()
