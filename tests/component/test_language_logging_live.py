"""Live component tests for multilingual language/logging behaviours."""
from __future__ import annotations

import pytest

from tests.support import parametrize_languages, capture_process_flow_output
from utils.logging.process_flow_logger import create_process_logger
from core.phase1_manager import Phase1Manager


@parametrize_languages()
@pytest.mark.component
@pytest.mark.live
@pytest.mark.slow
@pytest.mark.requires_openai
@pytest.mark.asyncio
async def test_phase1_logging_multilingual(language, prompt_harness):
    prompt_harness.ensure_seed()
    participants = await prompt_harness.create_participants(language, agent_count=1)
    localized_config = prompt_harness.last_localized_config

    utility_agent = await prompt_harness.create_utility_agent(language)
    language_manager = prompt_harness.create_language_manager(language)

    manager = Phase1Manager(participants, utility_agent, language_manager, seed_manager=prompt_harness.seed_manager)
    process_logger = create_process_logger("detailed", use_colors=False)

    with capture_process_flow_output(process_logger) as logs:
        await manager.run_phase1(localized_config)

    assert logs.text
    assert language.value.lower()[:3] in logs.text.lower()
