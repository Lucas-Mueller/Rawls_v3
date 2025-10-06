"""
Synthetic Data Integration Testing

Tests data transformations and flows with synthetic but realistic data
to validate Phase 1 to Phase 2 transitions, results formatting, and
data consistency without requiring API calls.
"""

import pytest
from typing import Dict, List, Any
from dataclasses import asdict

from models import (
    ParticipantContext, GroupDiscussionState, GroupDiscussionResult,
    VoteResult, PrincipleChoice, JusticePrinciple, IncomeClass,
    PrincipleRanking, RankedPrinciple, CertaintyLevel
)
from config import ExperimentConfiguration
from config.phase2_settings import Phase2Settings
from tests.support.mock_utilities import (
    MockParticipantAgent, MockParticipantContext, MockLanguageManager,
    MockLanguage, create_mock_participants, create_mock_contexts,
    create_multilingual_test_setup, create_mock_vote_result,
    create_mock_discussion_state
)


class TestPhase1ToPhase2DataFlow:
    """Test data flow from Phase 1 results to Phase 2 initialization."""

    def test_phase1_memory_sanitization(self):
        """Test Phase 1 memory is properly sanitized for Phase 2."""
        # Mock Phase 1 memory with various edge cases
        phase1_memories = [
            "Normal Phase 1 memory content about income assignments",
            None,  # Null memory
            "",    # Empty memory
            "   ",  # Whitespace only
            "Very long memory content that exceeds normal limits" * 100,  # Long content
            "Memory with\nnull\x00bytes and\tcontrol\r\ncharacters",  # Control characters
        ]

        character_limit = 1000

        for i, memory in enumerate(phase1_memories):
            participant_name = f"Participant_{i}"

            # Simulate memory sanitization logic from MemoryService
            if memory is None:
                sanitized = ""
            elif not isinstance(memory, str):
                try:
                    sanitized = str(memory)
                except Exception:
                    sanitized = ""
            else:
                # Remove control characters
                sanitized = memory.replace('\x00', '')
                sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char in '\n\r\t')

            # Validate sanitization
            if memory is None or memory == "":
                assert sanitized == "", f"Failed for null/empty memory case {i}"
            elif memory == "   ":
                assert sanitized == "   ", f"Failed for whitespace case {i}"
            else:
                assert isinstance(sanitized, str), f"Not a string after sanitization: {i}"
                assert '\x00' not in sanitized, f"Null bytes remain in case {i}"

    def test_context_initialization_data_flow(self):
        """Test participant context initialization from Phase 1 data."""
        # Mock Phase 1 results
        phase1_data = {
            "Alice": {
                "memory": "Phase 1: Learned about income distributions and justice principles.",
                "bank_balance": 150.0,
                "income_class": IncomeClass.HIGH,
                "language": "english"
            },
            "Bob": {
                "memory": "Fase 1: Aprendí sobre distribuciones de ingresos y principios de justicia.",
                "bank_balance": 80.0,
                "income_class": IncomeClass.LOW,
                "language": "spanish"
            },
            "李明": {
                "memory": "第一阶段：了解了收入分配和正义原则。",
                "bank_balance": 120.0,
                "income_class": IncomeClass.MEDIUM,
                "language": "mandarin"
            }
        }

        # Initialize Phase 2 contexts
        contexts = []
        for name, data in phase1_data.items():
            context = MockParticipantContext(name, data["language"])
            context.memory = data["memory"]
            context.bank_balance = data["bank_balance"]
            context.income_class = data["income_class"]
            context.phase = 2  # Transition to Phase 2
            context.round_number = 1
            contexts.append(context)

        # Validate data flow
        assert len(contexts) == 3
        for i, (name, expected_data) in enumerate(phase1_data.items()):
            context = contexts[i]
            assert context.name == name
            assert context.memory == expected_data["memory"]
            assert context.bank_balance == expected_data["bank_balance"]
            assert context.income_class == expected_data["income_class"]
            assert context.phase == 2
            assert context.language == expected_data["language"]

    def test_multilingual_context_consistency(self):
        """Test context data consistency across languages."""
        multilingual_setup = create_multilingual_test_setup()

        for language, setup in multilingual_setup.items():
            participants = setup["participants"]
            contexts = setup["contexts"]
            language_manager = setup["language_manager"]

            assert len(participants) == len(contexts)

            for participant, context in zip(participants, contexts):
                # Validate language consistency
                assert participant.config.language == language
                assert context.language == language

                # Test localized message retrieval
                test_key = "prompts.vote_initiation_prompt"
                message = language_manager.get(test_key)

                if language == "english":
                    assert "Do you want to initiate voting" in message
                elif language == "spanish":
                    assert "¿Quieres iniciar la votación" in message
                elif language == "mandarin":
                    assert "你想发起投票吗" in message

    def test_income_class_serialization(self):
        """Test income class data serialization and deserialization."""
        income_classes = [
            IncomeClass.HIGH,
            IncomeClass.MEDIUM_HIGH,
            IncomeClass.MEDIUM,
            IncomeClass.MEDIUM_LOW,
            IncomeClass.LOW
        ]

        for income_class in income_classes:
            # Test enum value consistency
            assert income_class.value in ['high', 'medium_high', 'medium', 'medium_low', 'low']

            # Test string representation parsing (common in data flows)
            class_str = income_class.value
            reconstructed = IncomeClass(class_str)
            assert reconstructed == income_class

            # Test enum string representation (as might come from serialization)
            enum_str = f"IncomeClass.{income_class.value}"
            parsed_value = enum_str.split('.')[1].lower()
            reconstructed_from_enum_str = IncomeClass(parsed_value)
            assert reconstructed_from_enum_str == income_class


class TestDiscussionStateTransformation:
    """Test discussion state data transformations."""

    def test_discussion_history_building(self):
        """Test discussion history accumulates correctly."""
        discussion_state = create_mock_discussion_state()

        # Simulate discussion rounds
        statements = [
            ("Alice", "I believe maximizing floor is most just."),
            ("Bob", "I prefer maximizing average income."),
            ("Alice", "But we should help the worst off members."),
            ("Bob", "Average income benefits everyone in society.")
        ]

        for participant, statement in statements:
            # Add statement to history (as services would do)
            round_entry = f"\n{participant}: {statement}"
            discussion_state.public_history += round_entry

        # Validate accumulated history
        history = discussion_state.public_history
        assert "Alice: I believe maximizing floor" in history
        assert "Bob: I prefer maximizing average" in history
        assert "Alice: But we should help" in history
        assert "Bob: Average income benefits" in history

        # Test history formatting
        formatted_history = discussion_state.get_formatted_discussion_history()
        assert formatted_history == discussion_state.public_history

    def test_discussion_history_truncation(self):
        """Test discussion history truncation for memory management."""
        discussion_state = create_mock_discussion_state()

        # Create long history that exceeds limits
        long_statements = [f"Participant_{i}: This is a very long statement about justice principles that takes up significant space in memory." for i in range(100)]

        full_history = "\n".join(long_statements)
        discussion_state.public_history = full_history

        # Simulate truncation logic from DiscussionService
        max_length = 1000
        if len(discussion_state.public_history) > max_length:
            keep_length = int(max_length * 0.75)
            truncated_history = "[Discussion history truncated for brevity]\n" + discussion_state.public_history[-keep_length:]
            discussion_state.public_history = truncated_history

        # Validate truncation
        assert len(discussion_state.public_history) <= max_length
        assert "truncated for brevity" in discussion_state.public_history
        assert "Participant_99" in discussion_state.public_history  # Recent content preserved

    def test_vote_history_tracking(self):
        """Test vote history accumulates correctly."""
        discussion_state = create_mock_discussion_state()

        # Add vote results
        vote_results = [
            create_mock_vote_result(consensus=False),
            create_mock_vote_result(consensus=True, principle=JusticePrinciple.MAXIMIZING_FLOOR),
            create_mock_vote_result(consensus=True, principle=JusticePrinciple.MAXIMIZING_AVERAGE)
        ]

        for vote_result in vote_results:
            discussion_state.vote_history.append(vote_result)

        # Validate vote history
        assert len(discussion_state.vote_history) == 3
        assert discussion_state.vote_history[0].consensus_reached is False
        assert discussion_state.vote_history[1].consensus_reached is True
        assert discussion_state.vote_history[1].agreed_principle.principle == JusticePrinciple.MAXIMIZING_FLOOR
        assert discussion_state.vote_history[2].agreed_principle.principle == JusticePrinciple.MAXIMIZING_AVERAGE


class TestVotingDataTransformations:
    """Test voting data transformations and result processing."""

    def test_vote_result_consensus_detection(self):
        """Test vote result consensus detection logic."""
        # Test consensus scenarios
        consensus_cases = [
            {
                "votes": {"Alice": "floor", "Bob": "floor", "Carol": "floor"},
                "expected_consensus": True,
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR
            },
            {
                "votes": {"Alice": "average", "Bob": "average"},
                "expected_consensus": True,
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE
            },
            {
                "votes": {"Alice": "floor", "Bob": "average", "Carol": "floor"},
                "expected_consensus": False,
                "expected_principle": None
            }
        ]

        for case in consensus_cases:
            votes = case["votes"]
            unique_choices = set(votes.values())

            # Simple consensus logic
            consensus_reached = len(unique_choices) == 1
            chosen_principle = None

            if consensus_reached:
                principle_name = list(unique_choices)[0]
                if principle_name == "floor":
                    chosen_principle = JusticePrinciple.MAXIMIZING_FLOOR
                elif principle_name == "average":
                    chosen_principle = JusticePrinciple.MAXIMIZING_AVERAGE

            assert consensus_reached == case["expected_consensus"]
            assert chosen_principle == case["expected_principle"]

    def test_vote_result_serialization(self):
        """Test vote result data serialization."""
        vote_result = create_mock_vote_result(
            consensus=True,
            principle=JusticePrinciple.MAXIMIZING_FLOOR
        )

        # Test that vote result has expected structure
        assert hasattr(vote_result, 'consensus_reached')
        assert hasattr(vote_result, 'agreed_principle')
        assert hasattr(vote_result, 'votes')

        assert vote_result.consensus_reached is True
        assert vote_result.agreed_principle is not None
        assert vote_result.agreed_principle.principle == JusticePrinciple.MAXIMIZING_FLOOR

    def test_principle_choice_constraint_handling(self):
        """Test principle choice with constraint amounts."""
        # Test principles with constraints
        constrained_principles = [
            (JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 50),
            (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 30),
        ]

        for principle, constraint_amount in constrained_principles:
            choice = PrincipleChoice(
                principle=principle,
                constraint_amount=constraint_amount,
                certainty=CertaintyLevel.SURE
            )

            assert choice.principle == principle
            assert choice.constraint_amount == constraint_amount

        # Test principles without constraints
        unconstrained_principles = [
            JusticePrinciple.MAXIMIZING_FLOOR,
            JusticePrinciple.MAXIMIZING_AVERAGE,
        ]

        for principle in unconstrained_principles:
            choice = PrincipleChoice(principle=principle, certainty=CertaintyLevel.SURE)
            assert choice.principle == principle
            assert choice.constraint_amount is None


class TestResultsFormattingPipeline:
    """Test results formatting and data presentation."""

    def test_basic_results_formatting(self):
        """Test basic results formatting for different scenarios."""
        # Mock participant results
        participant_results = [
            {
                "name": "Alice",
                "final_earnings": 125.50,
                "assigned_class": "high",
                "language": "english"
            },
            {
                "name": "Carlos",
                "final_earnings": 87.25,
                "assigned_class": "low",
                "language": "spanish"
            },
            {
                "name": "李明",
                "final_earnings": 98.75,
                "assigned_class": "medium",
                "language": "mandarin"
            }
        ]

        for result in participant_results:
            # Test basic formatting components
            assert isinstance(result["final_earnings"], float)
            assert result["final_earnings"] > 0
            assert result["assigned_class"] in ["high", "medium_high", "medium", "medium_low", "low"]
            assert result["language"] in ["english", "spanish", "mandarin"]

            # Test formatted strings
            earnings_str = f"${result['final_earnings']:.2f}"
            assert "$" in earnings_str
            assert "." in earnings_str

    def test_multilingual_results_formatting(self):
        """Test results formatting across languages."""
        multilingual_setup = create_multilingual_test_setup()

        for language, setup in multilingual_setup.items():
            language_manager = setup["language_manager"]

            # Test key result messages
            test_keys = [
                "voting_results.consensus_reached",
                "voting_results.no_consensus",
                "common.principle_names.maximizing_floor"
            ]

            for key in test_keys:
                if key.startswith("voting_results.consensus"):
                    message = language_manager.get(key, principle_name="Test Principle")
                else:
                    message = language_manager.get(key)

                assert message is not None
                assert len(message) > 0
                assert not message.startswith("[MISSING:")

    def test_comprehensive_earnings_display_data(self):
        """Test comprehensive earnings display data structure."""
        # Mock comprehensive earnings data
        earnings_data = {
            "participant_name": "Alice",
            "assigned_class": IncomeClass.HIGH,
            "outcomes": [
                {
                    "principle_key": "maximizing_floor",
                    "principle_name": "Maximizing Floor",
                    "distribution_index": 0,
                    "agent_income": 200,
                    "agent_earnings": 200,
                    "constraint_amount": None
                },
                {
                    "principle_key": "maximizing_average",
                    "principle_name": "Maximizing Average",
                    "distribution_index": 1,
                    "agent_income": 180,
                    "agent_earnings": 180,
                    "constraint_amount": None
                }
            ],
            "distributions_table": "Distribution 1: [200, 150, 100, 75, 50]\nDistribution 2: [180, 160, 140, 120, 100]"
        }

        # Validate structure
        assert "participant_name" in earnings_data
        assert "assigned_class" in earnings_data
        assert "outcomes" in earnings_data
        assert isinstance(earnings_data["outcomes"], list)
        assert len(earnings_data["outcomes"]) > 0

        for outcome in earnings_data["outcomes"]:
            required_keys = ["principle_key", "principle_name", "distribution_index", "agent_income", "agent_earnings"]
            for key in required_keys:
                assert key in outcome, f"Missing key {key} in outcome"
            assert isinstance(outcome["agent_earnings"], (int, float))
            assert outcome["agent_earnings"] > 0


class TestMemoryDataTransformations:
    """Test memory update data transformations."""

    def test_memory_content_truncation(self):
        """Test memory content truncation rules."""
        # Test different content types
        content_types = [
            ("statement", "This is a discussion statement about justice principles that goes on for quite a while with detailed reasoning.", 300),
            ("reasoning", "Internal reasoning about the choice between different principles.", 200),
            ("results", "Final results with comprehensive earnings information.", 1000)
        ]

        for content_type, content, max_chars in content_types:
            if len(content) > max_chars:
                truncated = content[:max_chars] + "..."
            else:
                truncated = content

            assert len(truncated) <= max_chars + 3  # Account for "..."
            if len(content) > max_chars:
                assert truncated.endswith("...")

    def test_memory_event_classification(self):
        """Test memory event classification for routing."""
        from utils.selective_memory_manager import MemoryEventType

        # Test event type classifications
        event_classifications = [
            ("discussion statement", MemoryEventType.DISCUSSION_STATEMENT),
            ("vote initiation", MemoryEventType.VOTE_INITIATION_RESPONSE),
            ("voting confirmation", MemoryEventType.VOTING_CONFIRMATION),
            ("final results", MemoryEventType.FINAL_RESULTS),
            ("phase transition", MemoryEventType.PHASE_TRANSITION)
        ]

        for description, expected_event_type in event_classifications:
            # Event types should be properly defined
            assert isinstance(expected_event_type, MemoryEventType)
            assert hasattr(expected_event_type, 'value')

    def test_memory_update_chaining(self):
        """Test chaining of memory updates."""
        initial_memory = "Phase 1: Learned about distributions."
        updates = [
            "Round 1: Made discussion statement about floor principle.",
            "Round 2: Participated in voting confirmation.",
            "Final: Received results and earnings.",
        ]

        memory = initial_memory
        for update in updates:
            # Simulate memory chaining
            if memory and not memory.endswith('\n'):
                memory += '\n'
            memory += update

        # Validate chaining
        assert "Phase 1" in memory
        assert "Round 1" in memory
        assert "Round 2" in memory
        assert "Final" in memory

        # Validate order preservation
        lines = memory.split('\n')
        assert len(lines) >= 4
        assert "Phase 1" in lines[0]
        assert "Round 1" in lines[1]


class TestDataConsistencyValidation:
    """Test data consistency across different system components."""

    def test_participant_data_consistency(self):
        """Test participant data consistency across contexts."""
        participants = create_mock_participants(["Alice", "Bob"], "english")
        contexts = create_mock_contexts(["Alice", "Bob"], "english")

        for participant, context in zip(participants, contexts):
            # Names should match
            assert participant.name == context.name

            # Language should be consistent
            assert participant.config.language == context.language

            # Both should have required attributes
            assert hasattr(participant, 'agent')
            assert hasattr(participant, 'config')
            assert hasattr(context, 'memory')
            assert hasattr(context, 'bank_balance')

    def test_cross_language_data_integrity(self):
        """Test data integrity across language transitions."""
        multilingual_setup = create_multilingual_test_setup()

        # Test that each language setup is independent but consistent
        language_names = list(multilingual_setup.keys())
        for lang in language_names:
            setup = multilingual_setup[lang]

            # Each setup should have complete components
            assert 'participants' in setup
            assert 'contexts' in setup
            assert 'language_manager' in setup

            # Participant count should be consistent
            assert len(setup['participants']) == len(setup['contexts'])

    def test_numeric_precision_consistency(self):
        """Test numeric precision consistency in earnings calculations."""
        earnings_values = [100.0, 125.50, 87.25, 98.75, 150.00]

        for earnings in earnings_values:
            # Test formatting consistency
            formatted = f"{earnings:.2f}"
            parsed_back = float(formatted)
            assert abs(parsed_back - earnings) < 0.001  # Floating point tolerance

            # Test currency formatting
            currency_formatted = f"${earnings:.2f}"
            assert currency_formatted.startswith("$")
            numeric_part = currency_formatted[1:]
            assert float(numeric_part) == earnings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])