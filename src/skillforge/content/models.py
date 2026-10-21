"""Pydantic models of content files. ``extra="forbid"`` turns YAML typos into clear errors."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from skillforge.evaluator import CompareSpec, GoldenCase, PythonCase, PythonTest, ResultSet, SqlCase


class Exercise(BaseModel):
    """One exercise = one golden case (see README: golden set evaluator)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    title: str
    kind: Literal["sql", "python"]
    lesson: str | None = None
    topic: str
    difficulty: int = Field(ge=1, le=3)
    question: str
    hints: list[str] = Field(default_factory=list)
    reference: str
    compare: CompareSpec = Field(default_factory=CompareSpec)
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
