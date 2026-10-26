from __future__ import annotations

import sys

import pytest

from app.execution import ExecutionError, ExecutionTimeout, SubprocessExecutionBackend


def test_success_and_nonzero_exit(tmp_path):
    backend = SubprocessExecutionBackend()
    assert backend.run([sys.executable, "-c", "print('ok')"], 5, tmp_path) == 0
    assert backend.run([sys.executable, "-c", "raise SystemExit(7)"], 5, tmp_path) == 7


def test_timeout_is_enforced(tmp_path):
    backend = SubprocessExecutionBackend()
    with pytest.raises(ExecutionTimeout):
        backend.run(
            [sys.executable, "-c", "import time; time.sleep(5)"],
            1,
            tmp_path,
        )


def test_no_shell_interpolation(tmp_path):
    backend = SubprocessExecutionBackend()
    code = "print('a; echo injected')"
    assert backend.run([sys.executable, "-c", code], 5, tmp_path) == 0


def test_invalid_command_and_output_limit(tmp_path):
    backend = SubprocessExecutionBackend(max_output_bytes=8)
    with pytest.raises(ExecutionError):
        backend.run([], 5, tmp_path)
    with pytest.raises(ExecutionError):
        backend.run([sys.executable, "-c", "print('x' * 100)"], 5, tmp_path)
