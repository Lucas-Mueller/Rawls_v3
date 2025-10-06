"""
Unit tests for ParticipantContext.formatted_context_header field.

Tests the new field added for Phase 2 prompt streamlining refactoring.
"""

import pytest
from models import ParticipantContext, ExperimentPhase, ExperimentStage


class TestFormattedContextHeaderField:
    """Test the formatted_context_header field in ParticipantContext."""

    def test_formatted_context_header_defaults_to_none(self):
        """Verify formatted_context_header defaults to None (backward compatible)."""
        context = ParticipantContext(
            name="Alice",
            role_description="Test participant",
            bank_balance=1000.0,
            memory="Test memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2
        )

        assert context.formatted_context_header is None, (
            "formatted_context_header should default to None for backward compatibility"
        )

    def test_formatted_context_header_can_be_set(self):
        """Verify formatted_context_header can be set to a string value."""
        context = ParticipantContext(
            name="Alice",
            role_description="Test participant",
            bank_balance=1000.0,
            memory="Test memory",
            round_number=2,
            phase=ExperimentPhase.PHASE_2
        )

        # Set the formatted header
        test_header = "## Phase 2 Discussion - Round 2 of 5\n\nDiscussion history:\nAlice: Hello\nBob: Hi"
        context.formatted_context_header = test_header

        assert context.formatted_context_header == test_header, (
            "formatted_context_header should store the assigned value"
        )

    def test_formatted_context_header_can_be_set_in_constructor(self):
        """Verify formatted_context_header can be set during construction."""
        test_header = "Test context header"

        context = ParticipantContext(
            name="Bob",
            role_description="Test participant",
            bank_balance=2000.0,
            memory="Memory content",
            round_number=3,
            phase=ExperimentPhase.PHASE_2,
            formatted_context_header=test_header
        )

        assert context.formatted_context_header == test_header, (
            "formatted_context_header should be settable in constructor"
        )

    def test_formatted_context_header_works_with_phase1_context(self):
        """Verify formatted_context_header works with Phase 1 contexts (unused but allowed)."""
        context = ParticipantContext(
            name="Charlie",
            role_description="Test participant",
            bank_balance=1500.0,
            memory="Phase 1 memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_1,
            formatted_context_header="This shouldn't be used in Phase 1 but is allowed"
        )

        assert context.formatted_context_header is not None, (
            "Field should work with any phase (even if not used in Phase 1)"
        )

    def test_formatted_context_header_with_discussion_stage(self):
        """Verify formatted_context_header works with DISCUSSION stage."""
        context = ParticipantContext(
            name="David",
            role_description="Test participant",
            bank_balance=3000.0,
            memory="Discussion memory",
            round_number=2,
            phase=ExperimentPhase.PHASE_2,
            stage=ExperimentStage.DISCUSSION
        )

        # Initially None
        assert context.formatted_context_header is None

        # Set it (as Phase2Manager would)
        context.formatted_context_header = "Round 2 discussion context"

        assert context.formatted_context_header == "Round 2 discussion context"

    def test_formatted_context_header_can_be_cleared(self):
        """Verify formatted_context_header can be set back to None."""
        context = ParticipantContext(
            name="Eve",
            role_description="Test participant",
            bank_balance=1000.0,
            memory="Test memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2,
            formatted_context_header="Initial header"
        )

        assert context.formatted_context_header == "Initial header"

        # Clear it
        context.formatted_context_header = None

        assert context.formatted_context_header is None, (
            "formatted_context_header should be clearable"
        )

    def test_formatted_context_header_preserves_multiline_strings(self):
        """Verify formatted_context_header correctly stores multiline strings."""
        multiline_header = """## Phase 2 Discussion - Round 3 of 5

Current Participants: Alice, Bob, Charlie

Discussion History:
    Round 1 / Alice: I prefer principle 1
    Round 1 / Bob: I agree with Alice
    Round 2 / Charlie: Let's consider principle 2

What is your statement for this round?"""

        context = ParticipantContext(
            name="Frank",
            role_description="Test participant",
            bank_balance=2500.0,
            memory="Memory",
            round_number=3,
            phase=ExperimentPhase.PHASE_2,
            formatted_context_header=multiline_header
        )

        assert context.formatted_context_header == multiline_header, (
            "Multiline strings should be preserved exactly"
        )
        assert "\n" in context.formatted_context_header, (
            "Newlines should be preserved"
        )


class TestBackwardCompatibility:
    """Test that existing code continues to work with the new field."""

    def test_existing_context_creation_still_works(self):
        """Verify existing ParticipantContext creation patterns still work."""
        # This is how contexts are created throughout the codebase
        context = ParticipantContext(
            name="Test",
            role_description="Participant",
            bank_balance=1000.0,
            memory="",
            round_number=1,
            phase=ExperimentPhase.PHASE_1
        )

        # Should work without any issues
        assert context.name == "Test"
        assert context.formatted_context_header is None  # New field defaults to None

    def test_pydantic_model_validation_passes(self):
        """Verify Pydantic validation still works correctly."""
        # Valid context
        valid_context = ParticipantContext(
            name="Valid",
            role_description="Test",
            bank_balance=1000.0,
            memory="Memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2,
            formatted_context_header="Optional header"
        )

        assert valid_context.formatted_context_header == "Optional header"

        # Context without formatted_context_header (should also be valid)
        minimal_context = ParticipantContext(
            name="Minimal",
            role_description="Test",
            bank_balance=1000.0,
            memory="Memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2
        )

        assert minimal_context.formatted_context_header is None

    def test_context_can_be_serialized(self):
        """Verify ParticipantContext with new field can be serialized."""
        context = ParticipantContext(
            name="Serializable",
            role_description="Test",
            bank_balance=1000.0,
            memory="Memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2,
            formatted_context_header="Test header"
        )

        # Should be serializable to dict
        context_dict = context.model_dump()

        assert "formatted_context_header" in context_dict
        assert context_dict["formatted_context_header"] == "Test header"

        # Should be deserializable from dict
        restored_context = ParticipantContext(**context_dict)
        assert restored_context.formatted_context_header == "Test header"
