"""
Test hypothesis: Does setting context.stage affect Runner.run() behavior?

HYPOTHESIS: When context.stage=VOTING and context.formatted_context_header is set,
but we call _generate_dynamic_instructions(), it might fail if experiment_config is missing.
"""

import asyncio
from models import ParticipantContext, ExperimentPhase, ExperimentStage
from experiment_agents.participant_agent import _generate_dynamic_instructions
from utils.language_manager import LanguageManager, SupportedLanguage
from config.models import AgentConfiguration

def test_generate_instructions_with_voting_stage():
    """Test if _generate_dynamic_instructions works with VOTING stage."""

    # Create language manager
    lang_mgr = LanguageManager(SupportedLanguage.ENGLISH)

    # Create agent config
    config = AgentConfiguration(
        name="Alice",
        personality="Test participant",
        model="gpt-4o-mini",
        language="English",
        reasoning_enabled=False,
        temperature=0.0,
        memory_character_limit=25000
    )

    # Create context with VOTING stage (like during confirmation)
    context = ParticipantContext(
        name="Alice",
        role_description="Test",
        bank_balance=0.0,
        memory="Test memory",
        round_number=1,
        phase=ExperimentPhase.PHASE_2,
        stage=ExperimentStage.VOTING,  # This is what's set during confirmation
        formatted_context_header="Round 1 of 7\nParticipants: Sophie, Alice\n\nDiscussion history...",
        interaction_type="vote_confirmation",
        allow_vote_tool=False  # This is disabled during confirmation
    )

    # Test Case 1: WITH experiment_config
    print("=" * 60)
    print("TEST 1: Generating instructions WITH experiment_config")
    print("=" * 60)

    try:
        # Mock minimal experiment config
        class MockConfig:
            phase2_rounds = 7
            agents = [
                type('obj', (object,), {'name': 'Sophie'}),
                type('obj', (object,), {'name': 'Alice'})
            ]

        instructions = _generate_dynamic_instructions(
            context,
            config,
            lang_mgr,
            experiment_config=MockConfig()
        )
        print("✅ SUCCESS with experiment_config")
        print(f"Instructions length: {len(instructions)} chars")
        print(f"First 500 chars:\n{instructions[:500]}")
        if "voting" in instructions.lower():
            print("✅ Contains voting-related instructions")
        else:
            print("⚠️ Does NOT contain voting instructions")

    except Exception as e:
        print(f"❌ FAILED with experiment_config: {type(e).__name__}: {str(e)}")

    # Test Case 2: WITHOUT experiment_config (might be the issue!)
    print("\n" + "=" * 60)
    print("TEST 2: Generating instructions WITHOUT experiment_config")
    print("=" * 60)

    try:
        instructions = _generate_dynamic_instructions(
            context,
            config,
            lang_mgr,
            experiment_config=None  # This might cause the problem!
        )
        print("✅ SUCCESS without experiment_config")
        print(f"Instructions length: {len(instructions)} chars")

    except Exception as e:
        print(f"❌ FAILED without experiment_config: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

    # Test Case 3: WITH stage=DISCUSSION (should require formatted_context_header)
    print("\n" + "=" * 60)
    print("TEST 3: With stage=DISCUSSION")
    print("=" * 60)

    context_discussion = ParticipantContext(
        name="Alice",
        role_description="Test",
        bank_balance=0.0,
        memory="Test memory",
        round_number=1,
        phase=ExperimentPhase.PHASE_2,
        stage=ExperimentStage.DISCUSSION,  # Discussion requires formatted_context_header
        formatted_context_header=None,  # Try with None to see if it raises ValueError
        interaction_type="public_statement"
    )

    try:
        instructions = _generate_dynamic_instructions(
            context_discussion,
            config,
            lang_mgr,
            experiment_config=MockConfig()
        )
        print("✅ SUCCESS with DISCUSSION stage and formatted_context_header=None")

    except ValueError as e:
        print(f"❌ EXPECTED ValueError: {str(e)[:200]}")

    except Exception as e:
        print(f"❌ UNEXPECTED Exception: {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    test_generate_instructions_with_voting_stage()
