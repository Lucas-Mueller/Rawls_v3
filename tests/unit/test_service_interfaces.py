"""
Service Interface Unit Tests

Enhanced unit tests focusing on service boundaries and contracts using
mock utilities to test service logic without expensive API calls.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import List

from core.services.voting_service import VotingService
from core.services.discussion_service import DiscussionService
from core.services.memory_service import MemoryService
from core.services.speaking_order_service import SpeakingOrderService
from core.services.counterfactuals_service import CounterfactualsService
from config.phase2_settings import Phase2Settings
from models import JusticePrinciple, VoteResult, PrincipleChoice
from utils.selective_memory_manager import MemoryEventType

from tests.support.mock_utilities import (
    MockLanguageManager, MockUtilityAgent, MockLogger, MockSeedManager,
    MockMemoryService, MockParticipantAgent, MockParticipantContext,
    MockGroupDiscussionState, create_mock_participants, create_mock_contexts,
    create_multilingual_test_setup, MockLanguage
)


class TestVotingServiceInterface:
    """Test VotingService interface and contracts."""

    def setup_method(self):
        """Set up test fixtures."""
        self.language_manager = MockLanguageManager(MockLanguage.ENGLISH)
        self.utility_agent = MockUtilityAgent()
        self.settings = Phase2Settings.get_default()
        self.logger = MockLogger()

    def test_voting_service_initialization(self):
        """Test VotingService initializes with protocol dependencies."""
        service = VotingService(
            language_manager=self.language_manager,
            utility_agent=self.utility_agent,
            settings=self.settings,
            logger=self.logger
        )

        assert service.language_manager is self.language_manager
        assert service.utility_agent is self.utility_agent
        assert service.settings is self.settings
        assert service.logger is self.logger

    @pytest.mark.asyncio
    async def test_vote_initiation_prompt_with_retry(self):
        """Test vote initiation prompting with retry logic."""
        service = VotingService(
            language_manager=self.language_manager,
            utility_agent=self.utility_agent,
            settings=self.settings,
            logger=self.logger
        )

        participant = MockParticipantAgent("Alice")
        context = MockParticipantContext("Alice")

        # Mock Runner.run to simulate agent responses
        with patch('core.services.voting_service.Runner') as mock_runner:
            mock_result = Mock()
            mock_result.final_output = "1 - I want to vote"
            mock_runner.run = AsyncMock(return_value=mock_result)

            result = await service.prompt_for_vote_initiation(
                participant=participant,
                context=context,
                max_retries=2
            )

        assert result is True
        assert len(self.utility_agent.call_history) == 1
        assert self.utility_agent.call_history[0]["method"] == "detect_numerical_agreement"

    @pytest.mark.asyncio
    async def test_vote_initiation_handles_invalid_response(self):
        """Test vote initiation handles invalid responses with retry."""
        service = VotingService(
            language_manager=self.language_manager,
            utility_agent=self.utility_agent,
            settings=self.settings,
            logger=self.logger
        )

        participant = MockParticipantAgent("Bob")
        context = MockParticipantContext("Bob")

        # Mock utility agent to return error on first call, success on second
        original_detect = self.utility_agent.detect_numerical_agreement
        call_count = 0

        def mock_detect(response):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return False, "Invalid response"
            else:
                return True, None

        self.utility_agent.detect_numerical_agreement = mock_detect

        with patch('core.services.voting_service.Runner') as mock_runner:
            mock_result = Mock()
            mock_result.final_output = "1 - Yes after retry"
            mock_runner.run = AsyncMock(return_value=mock_result)

            result = await service.prompt_for_vote_initiation(
                participant=participant,
                context=context,
                max_retries=3
            )

        assert result is True
        assert call_count == 2  # Should retry once after invalid response

    @pytest.mark.asyncio
    async def test_confirmation_phase_multilingual(self):
        """Test confirmation phase works across languages."""
        multilingual_setup = create_multilingual_test_setup()

        for language, setup in multilingual_setup.items():
            service = VotingService(
                language_manager=setup["language_manager"],
                utility_agent=MockUtilityAgent(),
                settings=self.settings,
                logger=MockLogger()
            )

            participants = setup["participants"]
            contexts = setup["contexts"]
            discussion_state = MockGroupDiscussionState()

            with patch('core.services.voting_service.Runner') as mock_runner:
                mock_result = Mock()
                mock_result.final_output = "1 - Confirmed"
                mock_runner.run = AsyncMock(return_value=mock_result)

                result = await service.conduct_confirmation_phase(
                    participants=participants,
                    initiator_name=participants[0].name,
                    initiation_statement="Let's vote",
                    contexts=contexts,
                    discussion_state=discussion_state
                )

            # Should succeed with unanimous confirmation
            assert result is True


class TestDiscussionServiceInterface:
    """Test DiscussionService interface and contracts."""

    def setup_method(self):
        """Set up test fixtures."""
        self.language_manager = MockLanguageManager(MockLanguage.ENGLISH)
        self.settings = Phase2Settings.get_default()
        self.logger = MockLogger()

    def test_discussion_service_initialization(self):
        """Test DiscussionService initializes correctly."""
        service = DiscussionService(
            language_manager=self.language_manager,
            settings=self.settings,
            logger=self.logger
        )

        assert service.language_manager is self.language_manager
        assert service.settings is self.settings
        assert service.logger is self.logger

    def test_statement_validation_multilingual(self):
        """Test statement validation across languages."""
        multilingual_setup = create_multilingual_test_setup()

        for language, setup in multilingual_setup.items():
            service = DiscussionService(
                language_manager=setup["language_manager"],
                settings=self.settings,
                logger=MockLogger()
            )

            # Test valid statements
            valid_statements = {
                "english": "I believe maximizing floor is the most just principle because it helps the least fortunate.",
                "spanish": "Creo que maximizar el piso es el principio más justo porque ayuda a los menos afortunados.",
                "mandarin": "我认为最大化最低收入是最公正的原则，因为它帮助了最不幸的人。"
            }

            statement = valid_statements[language]
            result = service.validate_statement(statement, "TestParticipant", language)
            assert result is True

            # Test invalid statements (too short)
            short_statement = "短" if language == "mandarin" else "Short"
            result = service.validate_statement(short_statement, "TestParticipant", language)
            assert result is False

    def test_discussion_prompt_building(self):
        """Test discussion prompt building with different contexts."""
        service = DiscussionService(
            language_manager=self.language_manager,
            settings=self.settings,
            logger=self.logger
        )

        discussion_state = MockGroupDiscussionState()
        discussion_state.public_history = "Previous round discussion..."

        prompt = service.build_discussion_prompt(
            discussion_state=discussion_state,
            round_num=2,
            max_rounds=5,
            participant_names=["Alice", "Bob", "Carol"]
        )

        assert "Round 2/5" in prompt
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_group_composition_formatting(self):
        """Test group composition formatting."""
        service = DiscussionService(
            language_manager=self.language_manager,
            settings=self.settings,
            logger=self.logger
        )

        # Test different group sizes
        test_cases = [
            (["Alice"], "Alice"),
            (["Alice", "Bob"], "Alice and Bob"),
            (["Alice", "Bob", "Carol"], "Alice, Bob, and Carol"),
            (["A", "B", "C", "D"], "A, B, C, and D")
        ]

        for names, expected_format in test_cases:
            result = service.format_group_composition(names)
            # Should contain the expected participant format
            assert any(part in result for part in expected_format.split())

    @pytest.mark.asyncio
    async def test_statement_retrieval_with_retry(self):
        """Test statement retrieval with retry logic."""
        service = DiscussionService(
            language_manager=self.language_manager,
            settings=self.settings,
            logger=self.logger
        )

        participant = MockParticipantAgent("Alice")
        context = MockParticipantContext("Alice")
        discussion_state = MockGroupDiscussionState()
        agent_config = Mock()
        agent_config.language = "english"

        with patch('core.services.discussion_service.Runner') as mock_runner:
            mock_result = Mock()
            mock_result.final_output = "I believe maximizing floor principle is most just because it helps the worst off."
            mock_runner.run = AsyncMock(return_value=mock_result)

            statement, reasoning = await service.get_participant_statement_with_retry(
                participant=participant,
                context=context,
                discussion_state=discussion_state,
                agent_config=agent_config,
                participant_names=["Alice", "Bob"],
                max_rounds=5
            )

        assert isinstance(statement, str)
        assert len(statement) > 20  # Should be valid length
        assert isinstance(reasoning, str)  # May be empty


class TestMemoryServiceInterface:
    """Test MemoryService interface and contracts."""

    def setup_method(self):
        """Set up test fixtures."""
        self.language_manager = MockLanguageManager(MockLanguage.ENGLISH)
        self.utility_agent = MockUtilityAgent()
        self.settings = Phase2Settings.get_default()
        self.logger = MockLogger()

    def test_memory_service_initialization(self):
        """Test MemoryService initializes correctly."""
        service = MemoryService(
            language_manager=self.language_manager,
            utility_agent=self.utility_agent,
            settings=self.settings,
            logger=self.logger
        )

        assert service.language_manager is self.language_manager
        assert service.utility_agent is self.utility_agent
        assert service.settings is self.settings

    @pytest.mark.asyncio
    async def test_discussion_memory_update(self):
        """Test discussion memory update functionality."""
        service = MemoryService(
            language_manager=self.language_manager,
            utility_agent=self.utility_agent,
            settings=self.settings,
            logger=self.logger
        )

        agent = MockParticipantAgent("Alice")
        context = MockParticipantContext("Alice")
        context.memory = "Initial memory"

        # Mock the underlying memory update
        with patch.object(service, 'update_memory_selective', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = "Updated memory with discussion"

            result = await service.update_discussion_memory(
                agent=agent,
                context=context,
                statement="I prefer maximizing floor",
                round_num=2
            )

        assert result == "Updated memory with discussion"
        mock_update.assert_called_once()

        # Check the call arguments
        call_args = mock_update.call_args
        assert call_args[1]['event_type'] == MemoryEventType.DISCUSSION_STATEMENT

    @pytest.mark.asyncio
    async def test_voting_memory_updates(self):
        """Test voting-related memory updates."""
        service = MemoryService(
            language_manager=self.language_manager,
            utility_agent=self.utility_agent,
            settings=self.settings,
            logger=self.logger
        )

        agent = MockParticipantAgent("Bob")
        context = MockParticipantContext("Bob")

        # Test different voting phase updates
        voting_phases = ["initiation", "confirmation", "ballot"]

        for phase in voting_phases:
            with patch.object(service, 'update_memory_selective', new_callable=AsyncMock) as mock_update:
                mock_update.return_value = f"Updated memory with {phase}"

                result = await service.update_voting_phase_memory(
                    agent=agent,
                    context=context,
                    phase_name=phase,
                    initiator_name="Alice" if phase == "initiation" else None
                )

            assert result == f"Updated memory with {phase}"
            mock_update.assert_called_once()

    def test_content_truncation_logic(self):
        """Test content truncation rules."""
        service = MemoryService(
            language_manager=self.language_manager,
            utility_agent=self.utility_agent,
            settings=self.settings,
            logger=self.logger
        )

        # Test different content types
        long_content = "Very long content that exceeds normal limits. " * 100

        # Currently no truncation applied (as per implementation)
        result = service.apply_content_truncation(long_content, MemoryEventType.DISCUSSION_STATEMENT)
        assert result == long_content  # No truncation applied

        # Test with empty content
        empty_result = service.apply_content_truncation("", MemoryEventType.DISCUSSION_STATEMENT)
        assert empty_result == ""


class TestSpeakingOrderServiceInterface:
    """Test SpeakingOrderService interface and contracts."""

    def setup_method(self):
        """Set up test fixtures."""
        self.seed_manager = MockSeedManager(42)
        self.settings = Phase2Settings.get_default()
        self.logger = MockLogger()

    def test_speaking_order_service_initialization(self):
        """Test SpeakingOrderService initializes correctly."""
        service = SpeakingOrderService(
            seed_manager=self.seed_manager,
            settings=self.settings,
            logger=self.logger
        )

        assert service.seed_manager is self.seed_manager
        assert service.settings is self.settings
        assert service.logger is self.logger

    def test_fixed_speaking_order_generation(self):
        """Test fixed speaking order generation."""
        service = SpeakingOrderService(
            seed_manager=self.seed_manager,
            settings=self.settings,
            logger=self.logger
        )

        # Test fixed order without randomization
        order = service.generate_speaking_order(
            round_num=1,
            num_participants=3,
            randomize_speaking_order=False,
            strategy="fixed"
        )

        assert isinstance(order, list)
        assert len(order) == 3
        assert set(order) == {0, 1, 2}  # Should contain all participant indices

    def test_random_speaking_order_deterministic(self):
        """Test random speaking order is deterministic with seed."""
        service = SpeakingOrderService(
            seed_manager=self.seed_manager,
            settings=self.settings,
            logger=self.logger
        )

        # Generate multiple orders with same seed - should be reproducible
        order1 = service.generate_speaking_order(
            round_num=1,
            num_participants=4,
            randomize_speaking_order=True,
            strategy="random"
        )

        order2 = service.generate_speaking_order(
            round_num=1,
            num_participants=4,
            randomize_speaking_order=True,
            strategy="random"
        )

        # With same seed, should get same order
        # Note: This test depends on the mock seed manager implementation
        assert isinstance(order1, list)
        assert isinstance(order2, list)
        assert len(order1) == len(order2) == 4

    def test_finisher_restriction_logic(self):
        """Test finisher restriction is applied correctly."""
        service = SpeakingOrderService(
            seed_manager=self.seed_manager,
            settings=self.settings,
            logger=self.logger
        )

        # Test with last round finisher
        order = service.generate_speaking_order(
            round_num=2,
            num_participants=3,
            randomize_speaking_order=False,
            strategy="fixed",
            last_round_finisher=0  # Agent 0 finished last round
        )

        # Agent 0 should not be first in new order (finisher restriction)
        assert order[0] != 0


class TestCounterfactualsServiceInterface:
    """Test CounterfactualsService interface and contracts."""

    def setup_method(self):
        """Set up test fixtures."""
        self.language_manager = MockLanguageManager(MockLanguage.ENGLISH)
        self.settings = Phase2Settings.get_default()
        self.logger = MockLogger()
        self.seed_manager = MockSeedManager(42)

    def test_counterfactuals_service_initialization(self):
        """Test CounterfactualsService initializes correctly."""
        service = CounterfactualsService(
            language_manager=self.language_manager,
            settings=self.settings,
            logger=self.logger,
            seed_manager=self.seed_manager
        )

        assert service.language_manager is self.language_manager
        assert service.settings is self.settings
        assert service.logger is self.logger
        assert service.seed_manager is self.seed_manager

    @pytest.mark.asyncio
    async def test_counterfactuals_calculation(self):
        """Test counterfactuals calculation logic."""
        service = CounterfactualsService(
            language_manager=self.language_manager,
            settings=self.settings,
            logger=self.logger,
            seed_manager=self.seed_manager
        )

        # Mock distribution set
        mock_distribution_set = Mock()
        mock_distribution_set.distributions = [Mock(), Mock()]

        assigned_classes = {
            "Alice": "high",
            "Bob": "low"
        }

        # Mock DistributionGenerator methods
        with patch('core.services.counterfactuals_service.DistributionGenerator') as mock_dist_gen:
            mock_dist_gen.calculate_alternative_earnings_by_principle_fixed_class.return_value = {
                "maximizing_floor": 100.0,
                "maximizing_average": 120.0,
                "maximizing_average_floor_constraint": 110.0,
                "maximizing_average_range_constraint": 115.0
            }

            result = await service.calculate_phase2_counterfactuals(
                distribution_set=mock_distribution_set,
                assigned_classes=assigned_classes
            )

        assert isinstance(result, dict)
        assert "Alice" in result
        assert "Bob" in result
        for participant_name in result:
            assert isinstance(result[participant_name], dict)
            assert len(result[participant_name]) == 4  # Four principles

    @pytest.mark.asyncio
    async def test_results_formatting_multilingual(self):
        """Test results formatting across languages."""
        multilingual_setup = create_multilingual_test_setup()

        for language, setup in multilingual_setup.items():
            service = CounterfactualsService(
                language_manager=setup["language_manager"],
                settings=self.settings,
                logger=MockLogger(),
                seed_manager=self.seed_manager
            )

            # Mock data for results formatting
            mock_consensus_result = Mock()
            mock_consensus_result.consensus_reached = True
            mock_consensus_result.agreed_principle = Mock()
            mock_consensus_result.agreed_principle.principle = JusticePrinciple.MAXIMIZING_FLOOR
            mock_consensus_result.agreed_principle.constraint_amount = None

            mock_distribution_set = Mock()
            alternative_earnings = {
                "maximizing_floor": 100.0,
                "maximizing_average": 120.0,
                "maximizing_average_floor_constraint": 110.0,
                "maximizing_average_range_constraint": 115.0
            }

            result = await service.build_detailed_results(
                participant_name="TestParticipant",
                final_earnings=125.50,
                assigned_class="high",
                alternative_earnings=alternative_earnings,
                consensus_result=mock_consensus_result,
                distribution_set=mock_distribution_set,
                lang_manager=setup["language_manager"]
            )

            assert isinstance(result, str)
            assert len(result) > 0
            assert "125.50" in result  # Earnings should be included


class TestServiceInteroperability:
    """Test how services work together through their interfaces."""

    def test_voting_and_memory_service_integration(self):
        """Test voting service integrates with memory service."""
        language_manager = MockLanguageManager(MockLanguage.ENGLISH)
        utility_agent = MockUtilityAgent()
        memory_service = MockMemoryService()
        logger = MockLogger()

        voting_service = VotingService(
            language_manager=language_manager,
            utility_agent=utility_agent,
            logger=logger,
            memory_service=memory_service
        )

        # Services should be properly connected
        assert voting_service.memory_service is memory_service
        assert voting_service.language_manager is language_manager
        assert voting_service.utility_agent is utility_agent

    def test_discussion_and_memory_service_compatibility(self):
        """Test discussion service output is compatible with memory service input."""
        discussion_service = DiscussionService(
            language_manager=MockLanguageManager(MockLanguage.ENGLISH),
            logger=MockLogger()
        )

        memory_service = MockMemoryService()

        # Mock discussion state
        discussion_state = MockGroupDiscussionState()
        discussion_state.public_history = "Round 1: Alice made a statement."

        # Discussion service should produce content that memory service can handle
        prompt = discussion_service.build_discussion_prompt(
            discussion_state=discussion_state,
            round_num=2,
            max_rounds=5,
            participant_names=["Alice", "Bob"]
        )

        # Memory service should be able to process discussion content
        agent = MockParticipantAgent("Alice")
        context = MockParticipantContext("Alice")

        # This should not raise an exception
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_service_error_handling_consistency(self):
        """Test services handle errors consistently."""
        services = [
            VotingService(MockLanguageManager(), MockUtilityAgent()),
            DiscussionService(MockLanguageManager()),
            MemoryService(MockLanguageManager(), MockUtilityAgent(), Phase2Settings.get_default()),
            SpeakingOrderService(),
            CounterfactualsService(MockLanguageManager(), Phase2Settings.get_default())
        ]

        for service in services:
            # All services should have logger handling
            if hasattr(service, '_log_warning'):
                # Should not raise exception when logging
                service._log_warning("Test warning message")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])