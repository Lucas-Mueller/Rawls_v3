"""Unit tests for ExperimentErrorHandler retry logic and statistics."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from utils.error_handling import (
    AgentCommunicationError,
    ErrorSeverity,
    ExperimentErrorCategory,
    ExperimentErrorHandler,
    MemoryError,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_error_async_retries_until_success(monkeypatch):
    handler = ExperimentErrorHandler()

    # Avoid real sleep delays during backoff
    monkeypatch.setattr("utils.error_handling.asyncio.sleep", AsyncMock())

    call_count = {"attempts": 0}

    async def flaky_operation():
        call_count["attempts"] += 1
        if call_count["attempts"] < 3:
            raise AgentCommunicationError("transient failure")
        return "OK"

    error = AgentCommunicationError("initial failure")
    result = await handler.handle_error_async(error, flaky_operation)

    assert result == "OK"
    assert call_count["attempts"] == 3

    stats = handler.get_error_statistics()
    assert stats["total_errors"] == 1
    assert stats["by_category"][ExperimentErrorCategory.AGENT_COMMUNICATION_ERROR.value] == 1
    assert stats["by_severity"][ErrorSeverity.RECOVERABLE.value] == 1
    assert handler.error_history[0].attempt_count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_error_async_raises_after_max_retries(monkeypatch):
    handler = ExperimentErrorHandler()
    handler.retry_config[ExperimentErrorCategory.AGENT_COMMUNICATION_ERROR].max_retries = 2
    monkeypatch.setattr("utils.error_handling.asyncio.sleep", AsyncMock())

    async def failing_operation():
        raise AgentCommunicationError("still failing")

    error = AgentCommunicationError("initial failure")

    with pytest.raises(AgentCommunicationError) as exc_info:
        await handler.handle_error_async(error, failing_operation)

    final_error = exc_info.value
    assert final_error.severity == ErrorSeverity.FATAL
    assert final_error.category == ExperimentErrorCategory.AGENT_COMMUNICATION_ERROR

    stats = handler.get_error_statistics()
    assert stats["total_errors"] == 1
    assert stats["by_category"][ExperimentErrorCategory.AGENT_COMMUNICATION_ERROR.value] == 1
    assert stats["by_severity"][ErrorSeverity.RECOVERABLE.value] == 1


@pytest.mark.unit
def test_get_error_statistics_groups_by_category_and_severity():
    handler = ExperimentErrorHandler()

    handler.error_history.extend([
        AgentCommunicationError("network blip", severity=ErrorSeverity.RECOVERABLE),
        MemoryError("memory overflow", severity=ErrorSeverity.DEGRADED),
    ])

    stats = handler.get_error_statistics()

    assert stats["total_errors"] == 2
    assert stats["by_category"][ExperimentErrorCategory.AGENT_COMMUNICATION_ERROR.value] == 1
    assert stats["by_category"][ExperimentErrorCategory.MEMORY_ERROR.value] == 1
    assert stats["by_severity"][ErrorSeverity.RECOVERABLE.value] == 1
    assert stats["by_severity"][ErrorSeverity.DEGRADED.value] == 1
    assert len(stats["recent_errors"]) == 2
