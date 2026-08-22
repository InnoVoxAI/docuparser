from __future__ import annotations

from docuparse_orchestrator.results import TaskError, TaskResult


def test_task_result_ok_defaults() -> None:
    result = TaskResult(status="ok", payload={"document_id": "abc"})

    assert result.status == "ok"
    assert result.payload == {"document_id": "abc"}
    assert result.error is None
    assert result.attempt == 1
    assert result.duration_ms == 0


def test_task_result_error_carries_task_error() -> None:
    error = TaskError(type="ValueError", message="boom", traceback="Traceback...")
    result = TaskResult(
        status="error",
        payload={},
        error=error,
        task_name="ocr",
        task_id="task-1",
        run_id="run-1",
        attempt=3,
        duration_ms=42,
    )

    assert result.status == "error"
    assert result.error is error
    assert result.error.type == "ValueError"
    assert result.task_name == "ocr"
    assert result.attempt == 3


def test_results_module_importable_without_django() -> None:
    import subprocess
    import sys
    from pathlib import Path

    shared_root = Path(__file__).resolve().parents[1]
    script = (
        "import sys; "
        "assert 'django' not in sys.modules; "
        "from docuparse_orchestrator.results import TaskResult; "
        "TaskResult(status='ok', payload={}); "
        "assert 'django' not in sys.modules"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=shared_root,
        env={"PYTHONPATH": str(shared_root)},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
