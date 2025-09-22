"""Resilience tests for ExperimentErrorHandler."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from utils.error_handling import AgentCommunicationError, ErrorSeverity, ExperimentErrorHandler

pytestmark = pytest.mark.resilience


@dataclass
class StubLogger:
    infos: list
    warnings: list
    errors: list

    def info(self, message, *args, **kwargs):  # pragma: no cover - logging helper
        self.infos.append(message)

    def warning(self, message, *args, **kwargs):  # pragma: no cover - logging helper
        self.warnings.append(message)

    def error(self, message, *args, **kwargs):  # pragma: no cover - logging helper
        self.errors.append(message)


def test_handle_error_sync_retries_then_succeeds():
    logger = StubLogger(infos=[], warnings=[], errors=[])
    handler = ExperimentErrorHandler(logger=logger)

    error = AgentCommunicationError("temporary failure", severity=ErrorSeverity.RECOVERABLE)
    error.operation = "vote_prompt"

    call_count = {"count": 0}

    def flaky_operation():
        call_count["count"] += 1
        if call_count["count"] < 2:
            raise RuntimeError("try again")
        return "success"

    result = handler.handle_error_sync(error, flaky_operation)

    assert result == "success"
    assert call_count["count"] == 2
    assert len(handler.error_history) == 1
    assert any("Retry attempt" in warning for warning in logger.warnings)
