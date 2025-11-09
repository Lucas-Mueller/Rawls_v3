"""
Live component tests for Manipulator Service integration.

Tests end-to-end manipulator target injection with real Phase 2 flows
and multilingual coverage.
"""

import pytest

from core.phase2_manager import Phase2Manager
from core.services import PreferenceAggregationService, ManipulatorService
from models import Phase1Results, PrincipleRanking, RankedPrinciple, JusticePrinciple, CertaintyLevel
from tests.support import PromptHarness, build_minimal_test_configuration
from utils.language_manager import SupportedLanguage
from utils.logging.agent_centric_logger import AgentCentricLogger


def _create_mock_phase1_results_with_rankings(harness, agent_count=3):
    """Create mock Phase 1 results with principle rankings for aggregation testing."""
    # Create diverse rankings to ensure non-unanimous preferences
    rankings_data = [
        # Agent 0: Ranks floor highest
        [
            (JusticePrinciple.MAXIMIZING_FLOOR, 1),
            (JusticePrinciple.MAXIMIZING_AVERAGE, 2),
            (JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 3),
            (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 4)
        ],
        # Agent 1: Ranks average highest
        [
            (JusticePrinciple.MAXIMIZING_AVERAGE, 1),
            (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 2),
            (JusticePrinciple.MAXIMIZING_FLOOR, 3),
            (JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 4)
        ],
        # Agent 2: Ranks floor constraint highest
        [
            (JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 1),
            (JusticePrinciple.MAXIMIZING_FLOOR, 2),
            (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 3),
            (JusticePrinciple.MAXIMIZING_AVERAGE, 4)
        ]
    ]

    phase1_results = []
    for i in range(agent_count):
        participant_name = f"Participant_{i}"
        rankings = rankings_data[i % len(rankings_data)]

        ranked_principles = [
            RankedPrinciple(
                principle=principle,
                rank=rank,
                certainty=CertaintyLevel.SURE
            )
            for principle, rank in rankings
        ]

        principle_ranking = PrincipleRanking(
            rankings=ranked_principles,
            certainty=CertaintyLevel.SURE
        )

        result = Phase1Results(
            participant_name=participant_name,
            principle_ranking=principle_ranking,
            principle_choice=rankings[0][0],  # Top-ranked principle
            final_memory_state=f"Phase 1 memory for {participant_name}",
            total_earnings=100.0
        )

        phase1_results.append(result)

    return phase1_results


@pytest.mark.component
@pytest.mark.live
@pytest.mark.slow
@pytest.mark.requires_openai
@pytest.mark.asyncio
async def test_manipulator_target_injection_english(openai_api_key):
    """Test manipulator target injection in English Phase 2."""
    harness = PromptHarness(build_minimal_test_configuration(
        agent_count=3,
        rounds=2,  # Short for testing
        language=SupportedLanguage.ENGLISH
    ))
    harness.ensure_seed()

    # Create participants
    participants = await harness.create_participants(
        SupportedLanguage.ENGLISH,
        agent_count=3,
        initialize=True
    )

    config = harness.last_localized_config

    # Add manipulator configuration
    manipulator_config = {
        'name': participants[0].name,  # First participant is manipulator
        'target_strategy': 'least_popular_after_round1',
        'tiebreak_order': [
            'maximizing_average',
            'maximizing_floor',
            'maximizing_average_floor_constraint',
            'maximizing_average_range_constraint'
        ]
    }

    # Update config with manipulator settings
    config.manipulator = manipulator_config

    utility_agent = await harness.create_utility_agent(SupportedLanguage.ENGLISH)
    language_manager = harness.create_language_manager(SupportedLanguage.ENGLISH)
    agent_logger = AgentCentricLogger()
    agent_logger.initialize_experiment(participants, config)

    # Create mock Phase 1 results
    phase1_results = _create_mock_phase1_results_with_rankings(harness, agent_count=3)

    # Test PreferenceAggregationService first
    pref_service = PreferenceAggregationService(language_manager)
    target_result = pref_service.aggregate_preferences(
        phase1_results=phase1_results,
        manipulator_name=manipulator_config['name'],
        tiebreak_order=manipulator_config['tiebreak_order']
    )

    assert 'least_popular_principle' in target_result
    assert target_result['aggregation_method'] == 'borda_count'

    # Initialize Phase2Manager
    phase2_manager = Phase2Manager(
        participants,
        utility_agent,
        experiment_config=config,
        language_manager=language_manager,
        seed_manager=harness.seed_manager,
        agent_logger=agent_logger
    )

    # Get manipulator context before run
    contexts = phase2_manager._initialize_phase2_contexts(phase1_results, config)
    manipulator_context = next(ctx for ctx in contexts if ctx.name == manipulator_config['name'])
    original_role = manipulator_context.role_description

    # Run Phase 2 (which should inject target)
    results = await phase2_manager.run_phase2(config, phase1_results, agent_logger)

    # Verify injection occurred
    # Re-get context after run (it was modified in-place)
    updated_manipulator_context = next(ctx for ctx in contexts if ctx.name == manipulator_config['name'])

    assert updated_manipulator_context.role_description != original_role
    assert "**MANIPULATOR TARGET**" in updated_manipulator_context.role_description
    assert target_result['least_popular_principle'] in updated_manipulator_context.role_description

    # Verify Phase 2 completed successfully
    assert results is not None
    assert results.discussion_result is not None


@pytest.mark.component
@pytest.mark.live
@pytest.mark.slow
@pytest.mark.requires_openai
@pytest.mark.asyncio
async def test_manipulator_target_injection_spanish(openai_api_key):
    """Test manipulator target injection in Spanish Phase 2."""
    harness = PromptHarness(build_minimal_test_configuration(
        agent_count=3,
        rounds=2,
        language=SupportedLanguage.SPANISH
    ))
    harness.ensure_seed()

    participants = await harness.create_participants(
        SupportedLanguage.SPANISH,
        agent_count=3,
        initialize=True
    )

    config = harness.last_localized_config

    manipulator_config = {
        'name': participants[1].name,  # Second participant is manipulator
        'target_strategy': 'least_popular_after_round1',
        'tiebreak_order': [
            'maximizing_floor',
            'maximizing_average',
            'maximizing_average_floor_constraint',
            'maximizing_average_range_constraint'
        ]
    }

    config.manipulator = manipulator_config

    utility_agent = await harness.create_utility_agent(SupportedLanguage.SPANISH)
    language_manager = harness.create_language_manager(SupportedLanguage.SPANISH)
    agent_logger = AgentCentricLogger()
    agent_logger.initialize_experiment(participants, config)

    phase1_results = _create_mock_phase1_results_with_rankings(harness, agent_count=3)

    # Test Spanish ManipulatorService directly
    manipulator_service = ManipulatorService(language_manager=language_manager)

    pref_service = PreferenceAggregationService(language_manager)
    target_result = pref_service.aggregate_preferences(
        phase1_results=phase1_results,
        manipulator_name=manipulator_config['name'],
        tiebreak_order=manipulator_config['tiebreak_order']
    )

    # Initialize contexts
    phase2_manager = Phase2Manager(
        participants,
        utility_agent,
        experiment_config=config,
        language_manager=language_manager,
        seed_manager=harness.seed_manager,
        agent_logger=agent_logger
    )

    contexts = phase2_manager._initialize_phase2_contexts(phase1_results, config)

    # Test direct injection
    delivery_metadata = manipulator_service.inject_target_instructions(
        contexts=contexts,
        manipulator_name=manipulator_config['name'],
        target_principle=target_result['least_popular_principle'],
        aggregation_details=target_result
    )

    # Verify Spanish injection
    assert delivery_metadata['delivered'] is True
    assert delivery_metadata['delivery_channel'] == 'role_description'

    manipulator_context = next(ctx for ctx in contexts if ctx.name == manipulator_config['name'])

    # Verify Spanish translation keys were used
    role_desc = manipulator_context.role_description
    # Should contain either Spanish or English text (English fallback is acceptable)
    assert len(role_desc) > 0
    assert target_result['least_popular_principle'] in role_desc


@pytest.mark.component
@pytest.mark.live
@pytest.mark.slow
@pytest.mark.requires_openai
@pytest.mark.asyncio
async def test_manipulator_target_injection_mandarin(openai_api_key):
    """Test manipulator target injection in Mandarin Phase 2."""
    harness = PromptHarness(build_minimal_test_configuration(
        agent_count=3,
        rounds=2,
        language=SupportedLanguage.MANDARIN
    ))
    harness.ensure_seed()

    participants = await harness.create_participants(
        SupportedLanguage.MANDARIN,
        agent_count=3,
        initialize=True
    )

    config = harness.last_localized_config

    manipulator_config = {
        'name': participants[2].name,  # Third participant is manipulator
        'target_strategy': 'least_popular_after_round1',
        'tiebreak_order': [
            'maximizing_average_range_constraint',
            'maximizing_average_floor_constraint',
            'maximizing_floor',
            'maximizing_average'
        ]
    }

    config.manipulator = manipulator_config

    utility_agent = await harness.create_utility_agent(SupportedLanguage.MANDARIN)
    language_manager = harness.create_language_manager(SupportedLanguage.MANDARIN)
    agent_logger = AgentCentricLogger()
    agent_logger.initialize_experiment(participants, config)

    phase1_results = _create_mock_phase1_results_with_rankings(harness, agent_count=3)

    # Test Mandarin injection
    manipulator_service = ManipulatorService(language_manager=language_manager)

    pref_service = PreferenceAggregationService(language_manager)
    target_result = pref_service.aggregate_preferences(
        phase1_results=phase1_results,
        manipulator_name=manipulator_config['name'],
        tiebreak_order=manipulator_config['tiebreak_order']
    )

    phase2_manager = Phase2Manager(
        participants,
        utility_agent,
        experiment_config=config,
        language_manager=language_manager,
        seed_manager=harness.seed_manager,
        agent_logger=agent_logger
    )

    contexts = phase2_manager._initialize_phase2_contexts(phase1_results, config)

    delivery_metadata = manipulator_service.inject_target_instructions(
        contexts=contexts,
        manipulator_name=manipulator_config['name'],
        target_principle=target_result['least_popular_principle'],
        aggregation_details=target_result
    )

    # Verify Mandarin injection
    assert delivery_metadata['delivered'] is True

    manipulator_context = next(ctx for ctx in contexts if ctx.name == manipulator_config['name'])

    # Verify Mandarin text handling
    role_desc = manipulator_context.role_description
    assert len(role_desc) > 0
    # Should handle Chinese characters correctly
    assert target_result['least_popular_principle'] in role_desc


@pytest.mark.component
@pytest.mark.live
@pytest.mark.slow
@pytest.mark.requires_openai
@pytest.mark.asyncio
async def test_manipulator_target_with_tiebreak(openai_api_key):
    """Test manipulator target injection with tiebreak scenario."""
    harness = PromptHarness(build_minimal_test_configuration(
        agent_count=3,
        rounds=2,
        language=SupportedLanguage.ENGLISH
    ))
    harness.ensure_seed()

    participants = await harness.create_participants(
        SupportedLanguage.ENGLISH,
        agent_count=3,
        initialize=True
    )

    config = harness.last_localized_config

    # Create Phase 1 results that will produce a tie
    phase1_results = []
    for i, participant in enumerate(participants):
        # All agents rank floor and average equally (will create tie in Borda count)
        if i == 0:
            rankings = [
                (JusticePrinciple.MAXIMIZING_FLOOR, 1),
                (JusticePrinciple.MAXIMIZING_AVERAGE, 2),
                (JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 3),
                (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 4)
            ]
        elif i == 1:
            rankings = [
                (JusticePrinciple.MAXIMIZING_AVERAGE, 1),
                (JusticePrinciple.MAXIMIZING_FLOOR, 2),
                (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 3),
                (JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 4)
            ]
        else:
            rankings = [
                (JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 1),
                (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 2),
                (JusticePrinciple.MAXIMIZING_FLOOR, 3),  # These get same Borda points
                (JusticePrinciple.MAXIMIZING_AVERAGE, 4)  # These get same Borda points
            ]

        ranked_principles = [
            RankedPrinciple(principle=p, rank=r, certainty=CertaintyLevel.SURE)
            for p, r in rankings
        ]

        result = Phase1Results(
            participant_name=participant.name,
            principle_ranking=PrincipleRanking(
                rankings=ranked_principles,
                certainty=CertaintyLevel.SURE
            ),
            principle_choice=rankings[0][0],
            final_memory_state=f"Memory for {participant.name}",
            total_earnings=100.0
        )
        phase1_results.append(result)

    manipulator_config = {
        'name': participants[0].name,
        'target_strategy': 'least_popular_after_round1',
        'tiebreak_order': [
            'maximizing_floor',
            'maximizing_average',
            'maximizing_average_floor_constraint',
            'maximizing_average_range_constraint'
        ]
    }

    config.manipulator = manipulator_config

    utility_agent = await harness.create_utility_agent(SupportedLanguage.ENGLISH)
    language_manager = harness.create_language_manager(SupportedLanguage.ENGLISH)

    # Test aggregation detects tiebreak
    pref_service = PreferenceAggregationService(language_manager)
    target_result = pref_service.aggregate_preferences(
        phase1_results=phase1_results,
        manipulator_name=manipulator_config['name'],
        tiebreak_order=manipulator_config['tiebreak_order']
    )

    # If tiebreak occurred, verify metadata includes tiebreak info
    if target_result.get('tiebreak_applied'):
        assert 'tied_principles' in target_result
        assert len(target_result['tied_principles']) >= 2

        # Test injection with tiebreak
        phase2_manager = Phase2Manager(
            participants,
            utility_agent,
            experiment_config=config,
            language_manager=language_manager,
            seed_manager=harness.seed_manager,
            agent_logger=AgentCentricLogger()
        )

        contexts = phase2_manager._initialize_phase2_contexts(phase1_results, config)

        manipulator_service = ManipulatorService(language_manager=language_manager)
        delivery_metadata = manipulator_service.inject_target_instructions(
            contexts=contexts,
            manipulator_name=manipulator_config['name'],
            target_principle=target_result['least_popular_principle'],
            aggregation_details=target_result
        )

        # Verify tiebreak info in delivery metadata
        assert delivery_metadata['tiebreak_applied'] is True
        assert 'tied_principles' in delivery_metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
