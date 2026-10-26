from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path


class ExecutionError(RuntimeError):
    pass


class ExecutionTimeout(ExecutionError):
    pass


class SubprocessExecutionBackend:
    """Run a command without a shell, with a hard timeout and process-group kill."""

    def __init__(self, max_output_bytes: int = 64 * 1024) -> None:
        self.max_output_bytes = max_output_bytes

    def run(self, command: list[str], timeout_seconds: int, cwd: Path) -> int:
        if not command or not all(isinstance(part, str) and part for part in command):
            raise ExecutionError("command must be a non-empty list of strings")
        if timeout_seconds <= 0:
            raise ExecutionError("timeout must be positive")
        directory = Path(cwd)
        if not directory.is_dir():
            raise ExecutionError("working directory does not exist")

        process = subprocess.Popen(
            command,
            cwd=directory,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
            raise ExecutionTimeout("execution timed out") from None

        if len(stdout) > self.max_output_bytes or len(stderr) > self.max_output_bytes:
            raise ExecutionError("execution output exceeded the configured limit")
        return process.returncode
