from __future__ import annotations

import runpy
from pathlib import Path
from typing import Iterable

import pytest

ROOT = Path(__file__).resolve().parents[1]


EXAMPLES: dict[str, Iterable[str]] = {
    "step_workflow.py": ["hello", "world"],
    "async_step_workflow.py": ["hello", "async world"],
    "typed_task_workflow.py": ["10"],
    "async_typed_task_workflow.py": ["10"],
    "combined_workflow.py": ["result:", "done"],
    "math_workflow.py": ["result: 9"],
    "async_math_workflow.py": ["result: 9"],
    "parallel_math_workflow.py": ["results: 6, 9"],
    "async_parallel_math_workflow.py": ["results: 6, 9"],
    "export_workflow.py": ["results: 6, 9", "exported to"],
}


@pytest.mark.parametrize("name,expected", EXAMPLES.items(), ids=list(EXAMPLES))
def test_examples(name: str, expected: Iterable[str], capsys: pytest.CaptureFixture[str]) -> None:
    """Run each example script and assert expected output fragments."""

    runpy.run_path(str(ROOT / "examples" / name), run_name="__main__")
    out = capsys.readouterr().out
    for fragment in expected:
        assert fragment in out


