"""
Manipulator Injection Fast Tests

Ultra-fast tests for manipulator target injection data flows and transformations.
Tests service boundaries without API calls using synthetic data.
"""

import pytest
from datetime import datetime
from typing import Dict, List, Any

from core.services.manipulator_service import ManipulatorService
from models import ParticipantContext, ExperimentPhase, ExperimentStage, JusticePrinciple

from tests.support.mock_utilities import (
    MockLanguageManager, MockLogger, MockLanguage,
    MockParticipantContext, create_multilingual_test_setup
)


class TestManipulatorInjectionDataFlow:
    """Test manipulator target injection data flows."""

    def test_injection_data_transformation(self):
        """Test target injection transforms context data correctly."""
        service = ManipulatorService(
            language_manager=MockLanguageManager(MockLanguage.ENGLISH),
            logger=MockLogger()
        )

        # Create test context
        original_role = "You are an economics professor"
        context = ParticipantContext(
            name="Manipulator",
            role_description=original_role,
            bank_balance=100.0,
            memory="Test memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2,
            memory_character_limit=10000,
            stage=ExperimentStage.DISCUSSION
        )

        contexts = [context]

        # Injection data
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

        # Perform injection
        result = service.inject_target_instructions(
            contexts=contexts,
            manipulator_name="Manipulator",
            target_principle="maximizing_floor",
            aggregation_details=aggregation_details
        )

        # Validate data transformation
        assert result['delivered'] is True
        assert context.role_description != original_role
        assert original_role in context.role_description
        assert "**MANIPULATOR TARGET**" in context.role_description
        assert "maximizing_floor" in context.role_description

        # Validate other context fields unchanged
        assert context.bank_balance == 100.0
        assert context.memory == "Test memory"
        assert context.round_number == 1

    def test_injection_metadata_structure(self):
        """Test injection metadata has correct structure."""
        service = ManipulatorService(
            language_manager=MockLanguageManager(MockLanguage.ENGLISH),
            logger=MockLogger()
        )

        context = MockParticipantContext("Alice", "english")
        contexts = [context]

        aggregation_details = {
            'least_popular_principle': 'maximizing_average',
            'principle_scores': {},
            'tiebreak_applied': False,
            'aggregation_method': 'borda_count'
        }

        result = service.inject_target_instructions(
            contexts=contexts,
            manipulator_name="Alice",
            target_principle="maximizing_average",
            aggregation_details=aggregation_details
        )

        # Validate metadata structure
        required_fields = [
            'delivered', 'delivered_at', 'delivery_channel',
            'target_principle', 'manipulator_name', 'injection_method',
            'tiebreak_applied'
        ]

        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

        # Validate types
        assert isinstance(result['delivered'], bool)
        assert isinstance(result['delivered_at'], str)
        assert isinstance(result['delivery_channel'], str)
        assert isinstance(result['target_principle'], str)
        assert isinstance(result['manipulator_name'], str)
        assert isinstance(result['tiebreak_applied'], bool)

    def test_tiebreak_data_flow(self):
        """Test tiebreak data flows correctly through injection."""
        service = ManipulatorService(
            language_manager=MockLanguageManager(MockLanguage.ENGLISH),
            logger=MockLogger()
        )

        context = MockParticipantContext("Bob", "english")
        contexts = [context]

        # Tiebreak scenario
        aggregation_details = {
            'least_popular_principle': 'maximizing_floor',
            'principle_scores': {
                'maximizing_floor': 8.0,
                'maximizing_average': 10.0,
                'maximizing_average_floor_constraint': 8.0,
                'maximizing_average_range_constraint': 7.0
            },
            'tiebreak_applied': True,
            'tied_principles': ['maximizing_floor', 'maximizing_average_floor_constraint'],
            'tiebreak_order': ['maximizing_floor', 'maximizing_average_floor_constraint'],
            'aggregation_method': 'borda_count'
        }

        result = service.inject_target_instructions(
            contexts=contexts,
            manipulator_name="Bob",
            target_principle="maximizing_floor",
            aggregation_details=aggregation_details
        )

        # Validate tiebreak data in metadata
        assert result['tiebreak_applied'] is True
        assert 'tied_principles' in result
        assert result['tied_principles'] == ['maximizing_floor', 'maximizing_average_floor_constraint']

        # Validate tiebreak message in role description
        role_desc = context.role_description
        assert len(role_desc) > 0
        # Should contain additional tiebreak information
        # (Exact text depends on language, but should be longer)

    def test_multilingual_injection_data_consistency(self):
        """Test injection data consistency across languages."""
        multilingual_setup = create_multilingual_test_setup()

        test_results = {}

        for language, setup in multilingual_setup.items():
            service = ManipulatorService(
                language_manager=setup["language_manager"],
                logger=MockLogger()
            )

            context = MockParticipantContext(f"Agent_{language}", language)
            contexts = [context]

            aggregation_details = {
                'least_popular_principle': 'maximizing_average',
                'principle_scores': {},
                'tiebreak_applied': False,
                'aggregation_method': 'borda_count'
            }

            result = service.inject_target_instructions(
                contexts=contexts,
                manipulator_name=f"Agent_{language}",
                target_principle="maximizing_average",
                aggregation_details=aggregation_details
            )

            test_results[language] = result

        # Validate consistency across languages
        for language, result in test_results.items():
            assert result['delivered'] is True, f"Delivery failed for {language}"
            assert result['delivery_channel'] == 'role_description'
            assert result['target_principle'] == 'maximizing_average'
            assert result['tiebreak_applied'] is False

            # All should have same metadata structure
            assert set(result.keys()) == set(test_results['english'].keys())


class TestRoleDescriptionTransformation:
    """Test role description transformation during injection."""

    def test_role_description_append_logic(self):
        """Test that injection appends to existing role description."""
        service = ManipulatorService(
            language_manager=MockLanguageManager(MockLanguage.ENGLISH),
            logger=MockLogger()
        )

        original_roles = [
            "You are an economics professor.",
            "You have strong views on justice.\nYou value equality above all.",
            ""  # Empty role
        ]

        for original_role in original_roles:
            context = ParticipantContext(
                name="Test",
                role_description=original_role,
                bank_balance=100.0,
                memory="Memory",
                round_number=1,
                phase=ExperimentPhase.PHASE_2,
                memory_character_limit=10000,
                stage=ExperimentStage.DISCUSSION
            )

            service._inject_into_role_description(
                context,
                "\n\n**MANIPULATOR TARGET**\nPrinciple: maximizing_floor",
                method="append"
            )

            # Validate transformation
            if original_role:
                assert context.role_description.startswith(original_role)
            assert "**MANIPULATOR TARGET**" in context.role_description
            assert "maximizing_floor" in context.role_description

    def test_role_description_preserves_formatting(self):
        """Test that injection preserves multiline formatting."""
        service = ManipulatorService(
            language_manager=MockLanguageManager(MockLanguage.ENGLISH),
            logger=MockLogger()
        )

        multiline_role = """You are an economics professor.

You have the following traits:
- Analytical thinking
- Strong moral compass
- Focus on fairness

Your background:
PhD in Economics from Harvard.
20 years teaching experience."""

        context = ParticipantContext(
            name="Test",
            role_description=multiline_role,
            bank_balance=100.0,
            memory="Memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2,
            memory_character_limit=10000,
            stage=ExperimentStage.DISCUSSION
        )

        service._inject_into_role_description(
            context,
            "\n\n**MANIPULATOR TARGET**\nTest injection"
        )

        # Validate all original lines preserved
        for line in multiline_role.split('\n'):
            if line.strip():  # Skip empty lines
                assert line in context.role_description

        # Validate injection added
        assert "**MANIPULATOR TARGET**" in context.role_description

    def test_role_description_character_encoding(self):
        """Test role description handles different character encodings."""
        service = ManipulatorService(
            language_manager=MockLanguageManager(MockLanguage.MANDARIN),
            logger=MockLogger()
        )

        # Roles with different character sets
        roles = [
            "Standard ASCII role",
            "Español: Profesor de economía",
            "中文：经济学教授",
            "Mixed: 教授 with múltiple languages"
        ]

        for role in roles:
            context = ParticipantContext(
                name="Test",
                role_description=role,
                bank_balance=100.0,
                memory="Memory",
                round_number=1,
                phase=ExperimentPhase.PHASE_2,
                memory_character_limit=10000,
                stage=ExperimentStage.DISCUSSION
            )

            service._inject_into_role_description(
                context,
                "\n\nTarget injection"
            )

            # Original role should be preserved with correct encoding
            assert role in context.role_description
            # Injection should be added
            assert "Target injection" in context.role_description


class TestDeliveryMetadataValidation:
    """Test delivery metadata validation and consistency."""

    def test_delivery_metadata_timestamp_format(self):
        """Test delivery metadata timestamp has correct format."""
        service = ManipulatorService(
            language_manager=MockLanguageManager(MockLanguage.ENGLISH),
            logger=MockLogger()
        )

        context = MockParticipantContext("Carol", "english")
        contexts = [context]

        aggregation_details = {
            'least_popular_principle': 'maximizing_floor',
            'principle_scores': {},
            'tiebreak_applied': False,
            'aggregation_method': 'borda_count'
        }

        result = service.inject_target_instructions(
            contexts=contexts,
            manipulator_name="Carol",
            target_principle="maximizing_floor",
            aggregation_details=aggregation_details
        )

        # Validate timestamp format
        assert 'delivered_at' in result
        timestamp_str = result['delivered_at']

        # Should be parseable as datetime
        try:
            parsed_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            assert isinstance(parsed_time, datetime)
        except ValueError:
            pytest.fail(f"Invalid timestamp format: {timestamp_str}")

    def test_error_metadata_completeness(self):
        """Test error metadata is complete when delivery fails."""
        service = ManipulatorService(
            language_manager=MockLanguageManager(MockLanguage.ENGLISH),
            logger=MockLogger()
        )

        # Context without manipulator (will cause delivery failure)
        contexts = [MockParticipantContext("Alice", "english")]

        aggregation_details = {
            'least_popular_principle': 'maximizing_floor',
            'principle_scores': {},
            'tiebreak_applied': False,
            'aggregation_method': 'borda_count'
        }

        result = service.inject_target_instructions(
            contexts=contexts,
            manipulator_name="NonExistent",
            target_principle="maximizing_floor",
            aggregation_details=aggregation_details
        )

        # Validate error metadata
        assert result['delivered'] is False
        assert 'error_message' in result
        assert isinstance(result['error_message'], str)
        assert len(result['error_message']) > 0

        # Other fields should still be present
        assert 'manipulator_name' in result
        assert 'target_principle' in result

    def test_metadata_field_types_consistency(self):
        """Test metadata field types are consistent across scenarios."""
        service = ManipulatorService(
            language_manager=MockLanguageManager(MockLanguage.ENGLISH),
            logger=MockLogger()
        )

        # Test multiple scenarios
        scenarios = [
            {
                "name": "success_no_tiebreak",
                "contexts": [MockParticipantContext("Alice", "english")],
                "manipulator_name": "Alice",
                "tiebreak": False
            },
            {
                "name": "success_with_tiebreak",
                "contexts": [MockParticipantContext("Bob", "english")],
                "manipulator_name": "Bob",
                "tiebreak": True
            }
        ]

        metadata_results = []

        for scenario in scenarios:
            aggregation_details = {
                'least_popular_principle': 'maximizing_floor',
                'principle_scores': {},
                'tiebreak_applied': scenario['tiebreak'],
                'tied_principles': ['maximizing_floor', 'maximizing_average'] if scenario['tiebreak'] else [],
                'aggregation_method': 'borda_count'
            }

            result = service.inject_target_instructions(
                contexts=scenario['contexts'],
                manipulator_name=scenario['manipulator_name'],
                target_principle="maximizing_floor",
                aggregation_details=aggregation_details
            )

            metadata_results.append(result)

        # Validate type consistency
        for result in metadata_results:
            assert isinstance(result['delivered'], bool)
            assert isinstance(result['delivered_at'], str)
            assert isinstance(result['delivery_channel'], str)
            assert isinstance(result['tiebreak_applied'], bool)


class TestTargetMessageConstruction:
    """Test target message construction logic."""

    def test_target_message_without_tiebreak(self):
        """Test target message construction without tiebreak."""
        service = ManipulatorService(
            language_manager=MockLanguageManager(MockLanguage.ENGLISH),
            logger=MockLogger()
        )

        aggregation_details = {
            'tiebreak_applied': False,
            'principle_scores': {
                'maximizing_floor': 5.0,
                'maximizing_average': 10.0
            }
        }

        message = service._build_target_message(
            target_principle="maximizing_floor",
            aggregation_details=aggregation_details
        )

        # Validate message structure
        assert isinstance(message, str)
        assert len(message) > 0
        assert "maximizing_floor" in message
        # Should NOT contain tiebreak information
        assert "tiebreak" not in message.lower() and "empate" not in message.lower()

    def test_target_message_with_tiebreak(self):
        """Test target message construction with tiebreak."""
        service = ManipulatorService(
            language_manager=MockLanguageManager(MockLanguage.ENGLISH),
            logger=MockLogger()
        )

        aggregation_details = {
            'tiebreak_applied': True,
            'tied_principles': ['maximizing_floor', 'maximizing_average'],
            'tiebreak_order': ['maximizing_floor', 'maximizing_average'],
            'principle_scores': {}
        }

        message = service._build_target_message(
            target_principle="maximizing_floor",
            aggregation_details=aggregation_details
        )

        # Validate message structure
        assert isinstance(message, str)
        assert len(message) > 0
        assert "maximizing_floor" in message

        # Should contain tiebreak information (more content)
        # Exact text depends on language, but should be significantly longer
        base_message = service._build_target_message(
            target_principle="maximizing_floor",
            aggregation_details={'tiebreak_applied': False, 'principle_scores': {}}
        )
        assert len(message) > len(base_message)

    def test_target_message_multilingual_consistency(self):
        """Test target message construction across languages."""
        multilingual_setup = create_multilingual_test_setup()

        messages = {}

        for language, setup in multilingual_setup.items():
            service = ManipulatorService(
                language_manager=setup["language_manager"],
                logger=MockLogger()
            )

            aggregation_details = {
                'tiebreak_applied': False,
                'principle_scores': {}
            }

            message = service._build_target_message(
                target_principle="maximizing_average",
                aggregation_details=aggregation_details
            )

            messages[language] = message

        # Validate all languages produce valid messages
        for language, message in messages.items():
            assert isinstance(message, str), f"Invalid message type for {language}"
            assert len(message) > 0, f"Empty message for {language}"
            assert "maximizing_average" in message, f"Missing principle in {language} message"


class TestInjectionEdgeCases:
    """Test edge cases in injection logic."""

    def test_injection_with_empty_principle_scores(self):
        """Test injection handles empty principle scores gracefully."""
        service = ManipulatorService(
            language_manager=MockLanguageManager(MockLanguage.ENGLISH),
            logger=MockLogger()
        )

        context = MockParticipantContext("Dave", "english")
        contexts = [context]

        aggregation_details = {
            'least_popular_principle': 'maximizing_floor',
            'principle_scores': {},  # Empty
            'tiebreak_applied': False,
            'aggregation_method': 'borda_count'
        }

        result = service.inject_target_instructions(
            contexts=contexts,
            manipulator_name="Dave",
            target_principle="maximizing_floor",
            aggregation_details=aggregation_details
        )

        # Should still succeed
        assert result['delivered'] is True

    def test_injection_with_missing_optional_fields(self):
        """Test injection handles missing optional fields in aggregation details."""
        service = ManipulatorService(
            language_manager=MockLanguageManager(MockLanguage.ENGLISH),
            logger=MockLogger()
        )

        context = MockParticipantContext("Eve", "english")
        contexts = [context]

        # Minimal aggregation details
        aggregation_details = {
            'tiebreak_applied': False
        }

        result = service.inject_target_instructions(
            contexts=contexts,
            manipulator_name="Eve",
            target_principle="maximizing_floor",
            aggregation_details=aggregation_details
        )

        # Should handle gracefully
        assert result['delivered'] is True

    def test_injection_preserves_context_immutability(self):
        """Test injection only modifies target context, not others."""
        service = ManipulatorService(
            language_manager=MockLanguageManager(MockLanguage.ENGLISH),
            logger=MockLogger()
        )

        target_context = MockParticipantContext("Manipulator", "english")
        other_contexts = [
            MockParticipantContext("Participant1", "english"),
            MockParticipantContext("Participant2", "english"),
            MockParticipantContext("Participant3", "english")
        ]

        contexts = [target_context] + other_contexts

        # Store original role descriptions
        original_roles = {ctx.name: ctx.role_description for ctx in contexts}

        aggregation_details = {
            'least_popular_principle': 'maximizing_floor',
            'principle_scores': {},
            'tiebreak_applied': False,
            'aggregation_method': 'borda_count'
        }

        result = service.inject_target_instructions(
            contexts=contexts,
            manipulator_name="Manipulator",
            target_principle="maximizing_floor",
            aggregation_details=aggregation_details
        )

        # Validate target was modified
        assert target_context.role_description != original_roles["Manipulator"]

        # Validate others unchanged
        for ctx in other_contexts:
            assert ctx.role_description == original_roles[ctx.name]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
