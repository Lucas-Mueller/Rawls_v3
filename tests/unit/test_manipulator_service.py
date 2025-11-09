"""
ManipulatorService Unit Tests

Unit tests for the ManipulatorService following the services-first architecture.
Tests cover target injection, error handling, and multilingual support.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from core.services.manipulator_service import ManipulatorService
from models import ParticipantContext, ExperimentPhase, ExperimentStage

from tests.support.mock_utilities import (
    MockLanguageManager, MockLogger, MockLanguage,
    create_multilingual_test_setup
)


class TestManipulatorServiceInterface:
    """Test ManipulatorService interface and contracts."""

    def setup_method(self):
        """Set up test fixtures."""
        self.language_manager = MockLanguageManager(MockLanguage.ENGLISH)
        self.logger = MockLogger()

    def test_manipulator_service_initialization(self):
        """Test ManipulatorService initializes with protocol dependencies."""
        service = ManipulatorService(
            language_manager=self.language_manager,
            logger=self.logger
        )

        assert service.language_manager is self.language_manager
        assert service.logger is self.logger

    def test_successful_injection_without_tiebreak(self):
        """Test successful target injection without tiebreak."""
        service = ManipulatorService(
            language_manager=self.language_manager,
            logger=self.logger
        )

        # Create participant contexts
        manipulator_context = ParticipantContext(
            name="Alice",
            role_description="Economics professor",
            bank_balance=100.0,
            memory="Initial memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2,
            memory_character_limit=10000,
            stage=ExperimentStage.DISCUSSION
        )

        other_context = ParticipantContext(
            name="Bob",
            role_description="Teacher",
            bank_balance=100.0,
            memory="Initial memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2,
            memory_character_limit=10000,
            stage=ExperimentStage.DISCUSSION
        )

        contexts = [manipulator_context, other_context]

        # Aggregation details without tiebreak
        aggregation_details = {
            'least_popular_principle': 'maximizing_floor',
            'principle_scores': {
                'maximizing_floor': 5.0,
                'maximizing_average': 10.0,
                'maximizing_average_floor_constraint': 8.0,
                'maximizing_average_range_constraint': 7.0
            },
            'tiebreak_applied': False,
            'aggregation_method': 'borda_count'
        }

        # Call inject_target_instructions
        result = service.inject_target_instructions(
            contexts=contexts,
            manipulator_name="Alice",
            target_principle="maximizing_floor",
            aggregation_details=aggregation_details
        )

        # Verify delivery metadata
        assert result['delivered'] is True
        assert result['delivery_channel'] == 'role_description'
        assert result['target_principle'] == 'maximizing_floor'
        assert result['manipulator_name'] == 'Alice'
        assert 'delivered_at' in result
        assert isinstance(result['delivered_at'], str)

        # Verify role_description was updated
        assert "**MANIPULATOR TARGET**" in manipulator_context.role_description
        assert "Principle: maximizing_floor" in manipulator_context.role_description
        assert "Borda count" in manipulator_context.role_description

        # Verify other context was not modified
        assert "**MANIPULATOR TARGET**" not in other_context.role_description

    def test_successful_injection_with_tiebreak(self):
        """Test successful target injection with tiebreak scenario."""
        service = ManipulatorService(
            language_manager=self.language_manager,
            logger=self.logger
        )

        manipulator_context = ParticipantContext(
            name="Carol",
            role_description="Philosopher",
            bank_balance=100.0,
            memory="Initial memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2,
            memory_character_limit=10000,
            stage=ExperimentStage.DISCUSSION
        )

        contexts = [manipulator_context]

        # Aggregation details WITH tiebreak
        aggregation_details = {
            'least_popular_principle': 'maximizing_average_floor_constraint',
            'principle_scores': {
                'maximizing_floor': 8.0,
                'maximizing_average': 10.0,
                'maximizing_average_floor_constraint': 8.0,
                'maximizing_average_range_constraint': 7.0
            },
            'tiebreak_applied': True,
            'tied_principles': ['maximizing_floor', 'maximizing_average_floor_constraint'],
            'tiebreak_order': ['maximizing_average_floor_constraint', 'maximizing_floor'],
            'aggregation_method': 'borda_count'
        }

        result = service.inject_target_instructions(
            contexts=contexts,
            manipulator_name="Carol",
            target_principle="maximizing_average_floor_constraint",
            aggregation_details=aggregation_details
        )

        # Verify delivery
        assert result['delivered'] is True
        assert result['tiebreak_applied'] is True
        assert result['tied_principles'] == ['maximizing_floor', 'maximizing_average_floor_constraint']

        # Verify tiebreak note is in role_description
        assert "Tiebreaker applied" in manipulator_context.role_description or "Desempate aplicado" in manipulator_context.role_description

    def test_manipulator_not_found_error(self):
        """Test error handling when manipulator is not found."""
        service = ManipulatorService(
            language_manager=self.language_manager,
            logger=self.logger
        )

        contexts = [
            ParticipantContext(
                name="Alice",
                role_description="Professor",
                bank_balance=100.0,
                memory="Memory",
                round_number=1,
                phase=ExperimentPhase.PHASE_2,
                memory_character_limit=10000,
                stage=ExperimentStage.DISCUSSION
            )
        ]

        aggregation_details = {
            'least_popular_principle': 'maximizing_floor',
            'principle_scores': {},
            'tiebreak_applied': False,
            'aggregation_method': 'borda_count'
        }

        # Call with non-existent manipulator
        result = service.inject_target_instructions(
            contexts=contexts,
            manipulator_name="NonExistentAgent",
            target_principle="maximizing_floor",
            aggregation_details=aggregation_details
        )

        # Verify delivery failed
        assert result['delivered'] is False
        assert 'error_message' in result
        assert "not found" in result['error_message'].lower()

    def test_injection_with_empty_contexts(self):
        """Test error handling with empty contexts list."""
        service = ManipulatorService(
            language_manager=self.language_manager,
            logger=self.logger
        )

        aggregation_details = {
            'least_popular_principle': 'maximizing_floor',
            'principle_scores': {},
            'tiebreak_applied': False,
            'aggregation_method': 'borda_count'
        }

        # Should raise ValueError for empty contexts
        with pytest.raises(ValueError, match="contexts list is empty"):
            service.inject_target_instructions(
                contexts=[],
                manipulator_name="Alice",
                target_principle="maximizing_floor",
                aggregation_details=aggregation_details
            )

    def test_multilingual_injection(self):
        """Test target injection works across different languages."""
        multilingual_setup = create_multilingual_test_setup()

        for language, setup in multilingual_setup.items():
            service = ManipulatorService(
                language_manager=setup["language_manager"],
                logger=MockLogger()
            )

            # Create context for each language
            manipulator_context = ParticipantContext(
                name=f"Agent_{language}",
                role_description="Test role",
                bank_balance=100.0,
                memory="Test memory",
                round_number=1,
                phase=ExperimentPhase.PHASE_2,
                memory_character_limit=10000,
                stage=ExperimentStage.DISCUSSION
            )

            contexts = [manipulator_context]

            aggregation_details = {
                'least_popular_principle': 'maximizing_average',
                'principle_scores': {
                    'maximizing_floor': 6.0,
                    'maximizing_average': 5.0,
                    'maximizing_average_floor_constraint': 9.0,
                    'maximizing_average_range_constraint': 8.0
                },
                'tiebreak_applied': False,
                'aggregation_method': 'borda_count'
            }

            result = service.inject_target_instructions(
                contexts=contexts,
                manipulator_name=f"Agent_{language}",
                target_principle="maximizing_average",
                aggregation_details=aggregation_details
            )

            # Verify successful delivery for all languages
            assert result['delivered'] is True, f"Delivery failed for {language}"
            assert result['delivery_channel'] == 'role_description'

            # Verify target message was injected
            role_desc = manipulator_context.role_description
            assert len(role_desc) > len("Test role"), f"Role description not updated for {language}"

    def test_injection_preserves_existing_role_description(self):
        """Test that injection appends to existing role_description without overwriting."""
        service = ManipulatorService(
            language_manager=self.language_manager,
            logger=self.logger
        )

        original_role = "You are a thoughtful economics professor with strong views on justice."

        manipulator_context = ParticipantContext(
            name="Dave",
            role_description=original_role,
            bank_balance=100.0,
            memory="Memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2,
            memory_character_limit=10000,
            stage=ExperimentStage.DISCUSSION
        )

        contexts = [manipulator_context]

        aggregation_details = {
            'least_popular_principle': 'maximizing_floor',
            'principle_scores': {},
            'tiebreak_applied': False,
            'aggregation_method': 'borda_count'
        }

        result = service.inject_target_instructions(
            contexts=contexts,
            manipulator_name="Dave",
            target_principle="maximizing_floor",
            aggregation_details=aggregation_details
        )

        # Verify original role description is preserved
        assert original_role in manipulator_context.role_description
        # Verify target was added
        assert "**MANIPULATOR TARGET**" in manipulator_context.role_description
        # Verify it's prepended (target message comes first)
        assert manipulator_context.role_description.startswith("**MANIPULATOR TARGET**")

    def test_metadata_completeness(self):
        """Test that delivery metadata includes all required fields."""
        service = ManipulatorService(
            language_manager=self.language_manager,
            logger=self.logger
        )

        manipulator_context = ParticipantContext(
            name="Eve",
            role_description="Test",
            bank_balance=100.0,
            memory="Memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2,
            memory_character_limit=10000,
            stage=ExperimentStage.DISCUSSION
        )

        contexts = [manipulator_context]

        aggregation_details = {
            'least_popular_principle': 'maximizing_average_range_constraint',
            'principle_scores': {'maximizing_average_range_constraint': 5.0},
            'tiebreak_applied': False,
            'aggregation_method': 'borda_count'
        }

        result = service.inject_target_instructions(
            contexts=contexts,
            manipulator_name="Eve",
            target_principle="maximizing_average_range_constraint",
            aggregation_details=aggregation_details
        )

        # Required fields
        required_fields = [
            'delivered', 'delivered_at', 'delivery_channel',
            'target_principle', 'manipulator_name', 'injection_method',
            'tiebreak_applied'
        ]

        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

        # Verify types
        assert isinstance(result['delivered'], bool)
        assert isinstance(result['delivered_at'], str)
        assert isinstance(result['delivery_channel'], str)
        assert isinstance(result['tiebreak_applied'], bool)


class TestManipulatorServiceHelperMethods:
    """Test internal helper methods of ManipulatorService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.language_manager = MockLanguageManager(MockLanguage.ENGLISH)
        self.logger = MockLogger()
        self.service = ManipulatorService(
            language_manager=self.language_manager,
            logger=self.logger
        )

    def test_find_manipulator_context_success(self):
        """Test _find_manipulator_context finds the correct context."""
        target_context = ParticipantContext(
            name="Alice",
            role_description="Test",
            bank_balance=100.0,
            memory="Memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2,
            memory_character_limit=10000,
            stage=ExperimentStage.DISCUSSION
        )

        other_context = ParticipantContext(
            name="Bob",
            role_description="Test",
            bank_balance=100.0,
            memory="Memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2,
            memory_character_limit=10000,
            stage=ExperimentStage.DISCUSSION
        )

        contexts = [other_context, target_context]

        found_context = self.service._find_manipulator_context(contexts, "Alice")

        assert found_context is target_context
        assert found_context.name == "Alice"

    def test_find_manipulator_context_not_found(self):
        """Test _find_manipulator_context returns None when not found."""
        contexts = [
            ParticipantContext(
                name="Alice",
                role_description="Test",
                bank_balance=100.0,
                memory="Memory",
                round_number=1,
                phase=ExperimentPhase.PHASE_2,
                memory_character_limit=10000,
                stage=ExperimentStage.DISCUSSION
            )
        ]

        found_context = self.service._find_manipulator_context(contexts, "NonExistent")

        assert found_context is None

    def test_build_target_message_without_tiebreak(self):
        """Test _build_target_message constructs correct message without tiebreak."""
        aggregation_details = {
            'tiebreak_applied': False,
            'principle_scores': {}
        }

        message = self.service._build_target_message(
            target_principle="maximizing_floor",
            aggregation_details=aggregation_details
        )

        assert isinstance(message, str)
        assert len(message) > 0
        assert "maximizing_floor" in message
        # Should NOT contain tiebreak note
        assert "Tiebreaker" not in message and "Desempate" not in message

    def test_build_target_message_with_tiebreak(self):
        """Test _build_target_message includes tiebreak note when applicable."""
        aggregation_details = {
            'tiebreak_applied': True,
            'tied_principles': ['maximizing_floor', 'maximizing_average'],
            'tiebreak_order': ['maximizing_floor', 'maximizing_average'],
            'principle_scores': {}
        }

        message = self.service._build_target_message(
            target_principle="maximizing_floor",
            aggregation_details=aggregation_details
        )

        assert isinstance(message, str)
        assert len(message) > 0
        # Should contain tiebreak information
        # Note: Exact text depends on language, but should be present
        assert len(message) > 100  # Tiebreak note adds significant length

    def test_inject_into_role_description(self):
        """Test _inject_into_role_description correctly updates context."""
        context = ParticipantContext(
            name="Frank",
            role_description="Original role",
            bank_balance=100.0,
            memory="Memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2,
            memory_character_limit=10000,
            stage=ExperimentStage.DISCUSSION
        )

        target_message = "\n\n**MANIPULATOR TARGET**\nPrinciple: maximizing_floor"

        self.service._inject_into_role_description(context, target_message)

        # Verify injection
        assert "Original role" in context.role_description
        assert "**MANIPULATOR TARGET**" in context.role_description
        assert "maximizing_floor" in context.role_description


class TestManipulatorServiceEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.language_manager = MockLanguageManager(MockLanguage.ENGLISH)
        self.logger = MockLogger()

    def test_injection_with_null_aggregation_details(self):
        """Test error handling with minimal aggregation details."""
        service = ManipulatorService(
            language_manager=self.language_manager,
            logger=self.logger
        )

        manipulator_context = ParticipantContext(
            name="Grace",
            role_description="Test",
            bank_balance=100.0,
            memory="Memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2,
            memory_character_limit=10000,
            stage=ExperimentStage.DISCUSSION
        )

        contexts = [manipulator_context]

        # Minimal aggregation details (some keys missing)
        aggregation_details = {
            'tiebreak_applied': False
        }

        result = service.inject_target_instructions(
            contexts=contexts,
            manipulator_name="Grace",
            target_principle="maximizing_floor",
            aggregation_details=aggregation_details
        )

        # Should still succeed (graceful degradation)
        assert result['delivered'] is True

    def test_injection_preserves_multiline_role_description(self):
        """Test that injection handles multiline role descriptions correctly."""
        service = ManipulatorService(
            language_manager=self.language_manager,
            logger=self.logger
        )

        multiline_role = """You are an economics professor.
You have strong views on distributive justice.
You value fairness and equality."""

        manipulator_context = ParticipantContext(
            name="Helen",
            role_description=multiline_role,
            bank_balance=100.0,
            memory="Memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2,
            memory_character_limit=10000,
            stage=ExperimentStage.DISCUSSION
        )

        contexts = [manipulator_context]

        aggregation_details = {
            'least_popular_principle': 'maximizing_floor',
            'tiebreak_applied': False,
            'principle_scores': {}
        }

        result = service.inject_target_instructions(
            contexts=contexts,
            manipulator_name="Helen",
            target_principle="maximizing_floor",
            aggregation_details=aggregation_details
        )

        # Verify success
        assert result['delivered'] is True

        # Verify all original lines are preserved
        for line in multiline_role.split('\n'):
            assert line in manipulator_context.role_description


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
