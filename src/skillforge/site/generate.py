"""``content/`` → Markdown pages for MkDocs.

The site is read-only learning material for the phone: lessons, exercise questions with hints and
reference solutions (collapsed), and flashcards to browse. Checking answers and FSRS scheduling
stay in the app (stage 2: PWA). Only public ``content/`` is published — never progress or profile.
"""

from __future__ import annotations

import shutil
import textwrap
from pathlib import Path

from skillforge.content.loader import ContentIndex
from skillforge.content.models import Card, Exercise, Lesson

DIFFICULTY = {1: "łatwe", 2: "średnie", 3: "trudne"}


def _indent(text: str, spaces: int = 4) -> str:
    return textwrap.indent(text.strip("\n"), " " * spaces)


def _admonition(kind: str, title: str, body: str, *, collapsed: bool = True) -> str:
    marker = "???" if collapsed else "!!!"
    safe_title = title.replace('"', "'")
    return f'{marker} {kind} "{safe_title}"\n\n{_indent(body)}\n'


def exercise_md(ex: Exercise) -> str:
    parts = [
        f"### {ex.id} · {ex.title}",
        f"*{ex.kind.upper()} · {DIFFICULTY[ex.difficulty]}* — sprawdź rozwiązanie w aplikacji.",
        ex.question.strip(),
    ]
    if ex.starter:
        parts.append(f"```python\n{ex.starter.strip()}\n```")
    parts.extend(
        _admonition("tip", f"Podpowiedź {i}", hint) for i, hint in enumerate(ex.hints, start=1)
    )
    language = "sql" if ex.kind == "sql" else "python"
    parts.append(
        _admonition(
            "success", "Rozwiązanie referencyjne", f"```{language}\n{ex.reference.strip()}\n```"
        )
    )
    return "\n\n".join(parts) + "\n"


def card_md(card: Card) -> str:
    return _admonition("question", card.front.strip(), card.back)


def lesson_md(lesson: Lesson, index: ContentIndex) -> str:
    topic = index.tree.topic(lesson.topic)
    meta = f"*{topic.title if topic else lesson.topic} · ok. {lesson.minutes} min*\n\n"
    body = lesson.body.strip()
    title, _, rest = body.partition("\n")  # keep the H1 first so MkDocs uses it as page title
    parts = [title, meta + rest.strip()]
    exercises = index.exercises_for_lesson(lesson.id)
    if exercises:
        parts.append("## Zadania do lekcji\n\n" + "\n".join(exercise_md(e) for e in exercises))
    cards = index.cards_for_lesson(lesson.id)
    if cards:
        parts.append(
            "## Fiszki\n\nKliknij pytanie, żeby zobaczyć odpowiedź. Powtórki z harmonogramem FSRS "
            "są w aplikacji.\n\n" + "\n".join(card_md(c) for c in cards)
        )
    return "\n\n".join(parts) + "\n"


def write_docs(index: ContentIndex, docs_dir: Path, assets_dir: Path) -> list[Path]:
    """(Re)create ``docs_dir`` with one page per lesson plus index pages. Returns written files."""
    if docs_dir.exists():
        shutil.rmtree(docs_dir)
    docs_dir.mkdir(parents=True)
    shutil.copytree(assets_dir, docs_dir / "assets")
    written: list[Path] = []

    def write(rel: str, text: str) -> None:
        path = docs_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(path)

    home = [
        "# skillforge — lekcje",
        "Materiały do nauki Analytics Engineering i AI dla analityki: lekcje, zadania z "
        "rozwiązaniami i fiszki. Strona działa offline po pierwszej wizycie — dodaj ją do ekranu "
        "głównego telefonu.",
        "Zadania sprawdzisz automatycznie w aplikacji `skillforge` (golden set evaluator).",
        "## Ścieżki",
    ]
    for path in index.tree.paths:
        lessons = index.lessons_for_path(path.id)
        if not lessons:
            home.append(f"- {path.title} — *wkrótce*")
            continue
        home.append(f"- [{path.title}]({path.id}/index.md) — lekcje: {len(lessons)}")
        page = [f"# {path.title}", path.description, "## Lekcje"]
        page += [f"{i}. [{x.title}]({x.id}.md) · {x.minutes} min" for i, x in enumerate(lessons, 1)]
        page.append("## Tematy")
        page += [
            f"- **{t.title}**" + (f" — {t.description}" if t.description else "")
            for t in path.topics
        ]
        write(f"{path.id}/index.md", "\n\n".join(p for p in page if p) + "\n")
        for lesson in lessons:
            write(f"{path.id}/{lesson.id}.md", lesson_md(lesson, index))
    write("index.md", "\n\n".join(home) + "\n")
    return written
