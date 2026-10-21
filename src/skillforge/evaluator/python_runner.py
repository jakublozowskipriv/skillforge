"""Run a candidate Python function against golden test cases in a subprocess.

The candidate code runs in a separate interpreter (``python -I``) with a timeout, so an infinite
loop or a crash cannot take down the app. This is isolation, not a security sandbox — fine for a
single-user local app where the author of the code is the user (see DECISIONS.md).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from skillforge.evaluator.compare import CompareSpec, cells_equal
from skillforge.evaluator.resultset import normalize_value

DEFAULT_TIMEOUT_S = 10.0

_HARNESS = r"""
import importlib.util, json, sys, traceback

sol_path, func_name, cases_path, out_path = sys.argv[1:5]
cases = json.loads(open(cases_path, encoding="utf-8").read())
out = {"load_error": None, "results": []}
try:
    spec = importlib.util.spec_from_file_location("solution", sol_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fn = getattr(module, func_name)
except Exception as exc:
    out["load_error"] = "".join(traceback.format_exception_only(type(exc), exc)).strip()
else:
    for case in cases:
        try:
            value = fn(*case["args"], **case["kwargs"])
            out["results"].append({"ok": True, "value": value})
        except Exception as exc:
            out["results"].append({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(out, fh, default=repr)
"""


class PythonTest(BaseModel):
    """One golden test: call ``function(*args, **kwargs)`` and expect ``expected``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    args: list[Any] = Field(default_factory=list)
    kwargs: dict[str, Any] = Field(default_factory=dict)
    expected: Any = None


@dataclass(frozen=True)
class PythonTestResult:
    name: str
    passed: bool
    expected: Any
    got: Any = None
    error: str | None = None


class PythonExecutionError(Exception):
    """The candidate module could not be loaded or the run timed out."""


def values_equal(a: Any, b: Any, spec: CompareSpec) -> bool:
    """Structural equality with float tolerance (lists/tuples and dicts recursively)."""
    if isinstance(a, list | tuple) and isinstance(b, list | tuple):
        return len(a) == len(b) and all(values_equal(x, y, spec) for x, y in zip(a, b, strict=True))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(values_equal(a[k], b[k], spec) for k in a)
    return cells_equal(normalize_value(a), normalize_value(b), spec)


def run_python(
    code: str,
    function: str,
    tests: tuple[PythonTest, ...] | list[PythonTest],
    *,
    spec: CompareSpec | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> list[PythonTestResult]:
    spec = spec or CompareSpec()
    with tempfile.TemporaryDirectory(prefix="skillforge-py-") as tmp:
        tmp_dir = Path(tmp)
        sol = tmp_dir / "solution.py"
        harness = tmp_dir / "harness.py"
        cases = tmp_dir / "cases.json"
        out = tmp_dir / "out.json"
        sol.write_text(code, encoding="utf-8")
        harness.write_text(_HARNESS, encoding="utf-8")
        payload = [{"args": t.args, "kwargs": t.kwargs} for t in tests]
        cases.write_text(json.dumps(payload), encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(harness), str(sol), function, str(cases), str(out)],
                cwd=tmp_dir,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise PythonExecutionError(f"Przekroczono limit czasu ({timeout_s:.0f} s).") from exc
        if not out.exists():
            raise PythonExecutionError(proc.stderr.strip() or "Proces zakończył się bez wyniku.")
        data = json.loads(out.read_text(encoding="utf-8"))

    if data["load_error"]:
        raise PythonExecutionError(f"Nie udało się wczytać `{function}`: {data['load_error']}")
    results: list[PythonTestResult] = []
    for test, res in zip(tests, data["results"], strict=True):
        if res["ok"]:
            ok = values_equal(test.expected, res["value"], spec)
            results.append(PythonTestResult(test.name, ok, test.expected, got=res["value"]))
        else:
            results.append(PythonTestResult(test.name, False, test.expected, error=res["error"]))
    return results
