from __future__ import annotations

import json
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
    "parallel_math_workflow.py": ["results: 6, 9", "exported to"],
    "async_parallel_math_workflow.py": ["results: 6, 9", "exported to"],
    "conditional_workflow.py": ["deciding", "skip branch"],
    "export_workflow.py": ["results: 6, 9", "exported to"],
    "trace_workflow.py": ["workflow traced"],
}


@pytest.mark.parametrize("name,expected", EXAMPLES.items(), ids=list(EXAMPLES))
def test_examples(name: str, expected: Iterable[str], capsys: pytest.CaptureFixture[str]) -> None:
    """Run each example script and assert expected output fragments."""

    runpy.run_path(str(ROOT / "examples" / name), run_name="__main__")
    out = capsys.readouterr().out
    for fragment in expected:
        assert fragment in out
    if name == "trace_workflow.py":
        trace_file = ROOT / "examples" / "trace_workflow.trace"
        assert trace_file.exists()
        entries = [json.loads(line) for line in trace_file.read_text().splitlines()]
        assert [e["event"] for e in entries][:2] == ["workflow_started", "step_enqueued"]
        assert "process_id" in entries[0]
        assert "host_id" in entries[0]
        trace_file.unlink()


