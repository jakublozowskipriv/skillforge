"""Pydantic models of content files. ``extra="forbid"`` turns YAML typos into clear errors."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from skillforge.evaluator import CompareSpec, GoldenCase, PythonCase, PythonTest, ResultSet, SqlCase

ID_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
TOPIC_PATTERN = r"^[a-z]+\.[a-z0-9]+(-[a-z0-9]+)*$"
APPLY_AT_WORK_HEADING = "## Jak zastosować w pracy"


class Topic(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=TOPIC_PATTERN)
    title: str
    description: str = ""


class LearningPath(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=ID_PATTERN)
    title: str
    description: str = ""
    optional: bool = False
    topics: list[Topic]


class CompetenceTree(BaseModel):
    """``content/tree.yaml``: path → topic. Levels 0–3 live in the progress log, not here."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    paths: list[LearningPath]

    def topic(self, topic_id: str) -> Topic | None:
        return next((t for p in self.paths for t in p.topics if t.id == topic_id), None)

    def path_of(self, topic_id: str) -> LearningPath | None:
        return next((p for p in self.paths if any(t.id == topic_id for t in p.topics)), None)

    @property
    def topic_ids(self) -> set[str]:
        return {t.id for p in self.paths for t in p.topics}


class Lesson(BaseModel):
    """Markdown file with YAML frontmatter in ``paths/<path>/lessons/``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=ID_PATTERN)
    path: str
    topic: str = Field(pattern=TOPIC_PATTERN)
    title: str
    minutes: int = Field(ge=5, le=30)
    order: int = 0
    exercises: list[str] = Field(default_factory=list)
    body: str
    source_path: Path | None = Field(default=None, exclude=True)

    @property
    def has_apply_at_work(self) -> bool:
        return any(line.strip() == APPLY_AT_WORK_HEADING for line in self.body.splitlines())


class Card(BaseModel):
    """Flashcard. Front/back are Markdown."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=ID_PATTERN)
    topic: str = Field(pattern=TOPIC_PATTERN)
    lesson: str | None = None
    front: str
    back: str
    tags: list[str] = Field(default_factory=list)


class CardDeck(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    cards: list[Card]


class Exercise(BaseModel):
    """One exercise = one golden case (see README: golden set evaluator)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=ID_PATTERN)
    title: str
    kind: Literal["sql", "python"]
    lesson: str | None = None
    topic: str = Field(pattern=TOPIC_PATTERN)
    difficulty: int = Field(ge=1, le=3)
    question: str
    hints: list[str] = Field(default_factory=list)
    reference: str
    compare: CompareSpec = Field(default_factory=CompareSpec)
    # Negative controls: typical wrong answers that MUST fail. Proves the golden set (data +
    # expected result + compare spec) discriminates right from wrong, not just that it passes.
    negatives: list[str] = Field(default_factory=list)
    # python only
    function: str | None = None
    starter: str | None = None
    tests: list[PythonTest] = Field(default_factory=list)

    # set by the loader, not by YAML authors
    source_path: Path | None = Field(default=None, exclude=True)

    @model_validator(mode="after")
    def _python_fields(self) -> Exercise:
        if self.kind == "python" and (not self.function or not self.tests):
            raise ValueError("python exercises need `function` and at least one test")
        if self.kind == "sql" and (self.function or self.tests):
            raise ValueError("sql exercises must not define `function`/`tests`")
        return self

    @property
    def expected_path(self) -> Path:
        if self.source_path is None:
            raise ValueError(f"{self.id}: source_path unknown")
        return self.source_path.with_name(f"{self.id}.expected.json")

    def to_case(self) -> GoldenCase:
        if self.kind == "python":
            assert self.function is not None
            return PythonCase(
                id=self.id,
                question=self.question,
                reference=self.reference,
                function=self.function,
                tests=tuple(self.tests),
                compare=self.compare,
            )
        return SqlCase(
            id=self.id,
            question=self.question,
            reference=self.reference,
            expected=ResultSet.from_json_file(self.expected_path),
            compare=self.compare,
        )
