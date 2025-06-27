import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_step_workflow_example(capsys):
    runpy.run_path(str(ROOT / "examples" / "step_workflow.py"), run_name="__main__")
    out = capsys.readouterr().out
    assert "hello" in out
    assert "world" in out


def test_async_step_workflow_example(capsys):
    runpy.run_path(str(ROOT / "examples" / "async_step_workflow.py"), run_name="__main__")
    out = capsys.readouterr().out
    assert "hello" in out
    assert "async world" in out


def test_typed_task_workflow_example(capsys):
    runpy.run_path(str(ROOT / "examples" / "typed_task_workflow.py"), run_name="__main__")
    out = capsys.readouterr().out
    assert "10" in out


def test_async_typed_task_workflow_example(capsys):
    runpy.run_path(str(ROOT / "examples" / "async_typed_task_workflow.py"), run_name="__main__")
    out = capsys.readouterr().out
    assert "10" in out


def test_combined_workflow_example(capsys):
    runpy.run_path(str(ROOT / "examples" / "combined_workflow.py"), run_name="__main__")
    out = capsys.readouterr().out
    assert "result:" in out
    assert "done" in out


