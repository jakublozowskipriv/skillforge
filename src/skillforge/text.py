"""Small Polish-language text helpers for the UI."""

from __future__ import annotations


def pl_plural(n: int, one: str, few: str, many: str) -> str:
    """``n`` with the right Polish noun form: 1 wiersz, 2 wiersze, 5 wierszy, 22 wiersze."""
    if n == 1:
        form = one
    elif n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        form = few
    else:
        form = many
    return f"{n} {form}"
