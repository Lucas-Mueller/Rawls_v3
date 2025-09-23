"""Helpers for capturing ``ProcessFlowLogger`` output in tests."""
from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass
from typing import Generator

from utils.logging.process_flow_logger import ProcessFlowLogger


@dataclass
class ProcessLogCapture:
    """Minimal container exposing captured text and convenience views."""

    logger: ProcessFlowLogger
    _buffer: io.StringIO

    @property
    def text(self) -> str:
        return self._buffer.getvalue()

    @property
    def lines(self) -> list[str]:
        return [line for line in self.text.splitlines() if line.strip()]


@contextlib.contextmanager
def capture_process_flow_output(logger: ProcessFlowLogger) -> Generator[ProcessLogCapture, None, None]:
    """Capture stdout emitted by ``ProcessFlowLogger`` within the context."""
    buffer = io.StringIO()
    capture = ProcessLogCapture(logger=logger, _buffer=buffer)
    with contextlib.redirect_stdout(buffer):
        yield capture
