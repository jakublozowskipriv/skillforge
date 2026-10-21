import pytest

from skillforge.text import pl_plural


@pytest.mark.parametrize(
    ("n", "expected"),
    [
        (0, "0 wierszy"),
        (1, "1 wiersz"),
        (2, "2 wiersze"),
        (4, "4 wiersze"),
        (5, "5 wierszy"),
        (12, "12 wierszy"),
        (14, "14 wierszy"),
        (22, "22 wiersze"),
        (111, "111 wierszy"),
    ],
)
def test_pl_plural(n: int, expected: str) -> None:
    assert pl_plural(n, "wiersz", "wiersze", "wierszy") == expected
