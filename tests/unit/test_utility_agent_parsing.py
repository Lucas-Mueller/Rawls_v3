"""Targeted unit tests for UtilityAgent parsing helpers."""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

from experiment_agents.utility_agent import UtilityAgent
from models import JusticePrinciple


@pytest.mark.unit
def test_normalize_principle_name_handles_duplicate_floor_constraint():
    agent = UtilityAgent(experiment_language="english")
    text = "Maximizing the average income with a floor constraint with a floor constraint"
    normalized = agent._normalize_principle_name(text)
    assert normalized == "maximizing_average_floor_constraint"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_parse_choice_normalizes_duplicate_json_response():
    agent = UtilityAgent(experiment_language="english")
    agent.async_init = AsyncMock()

    fake_response = Mock()
    fake_response.final_output = (
        '{"principle": "Maximizing the average income with a floor constraint with a floor constraint",'
        ' "constraint_amount": 13000, "certainty": "sure"}'
    )

    with patch("experiment_agents.utility_agent.run_without_tracing", AsyncMock(return_value=fake_response)):
        result = await agent.parse_principle_choice_enhanced("ignored")

    assert result.principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
    assert result.constraint_amount == 13000
