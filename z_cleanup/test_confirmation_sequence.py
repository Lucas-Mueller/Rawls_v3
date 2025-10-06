"""
Test the exact sequence of confirmation phase to find what causes abort.

This test simulates:
1. Sophie initiates vote (auto-confirmed, skips Runner.run)
2. Alice confirms (calls Runner.run - THIS IS WHERE IT ABORTS)
"""

import asyncio
import sys
from models import ParticipantContext, ExperimentPhase, ExperimentStage
from core.services.voting_service import VotingService
from utils.language_manager import LanguageManager, SupportedLanguage
from config.phase2_settings import Phase2Settings
from config.models import ExperimentConfiguration, AgentConfiguration
from experiment_agents import ParticipantAgent

async def test_confirmation_sequence():
    """Test if confirmation sequence causes abort."""

    print("\n" + "=" * 70)
    print("SIMULATING EXACT CONFIRMATION SEQUENCE FROM EXPERIMENT")
    print("=" * 70 + "\n")

    # Create language manager
    lang_mgr = LanguageManager(SupportedLanguage.ENGLISH)

    # Create Phase2 settings
    settings = Phase2Settings.get_default()

    # Create participant agent configurations (matching fast.yaml)
    sophie_config = AgentConfiguration(
        name="Sophie",
        personality="You are an american college student.",
        model="gpt-4o-mini",  # Use working model instead of gpt-4.1-nano
        language="English",
        reasoning_enabled=False,  # Disable for faster testing
        temperature=0.0,
        memory_character_limit=25000
    )

    alice_config = AgentConfiguration(
        name="Alice",
        personality="You are an american college student.",
        model="gpt-4o-mini",
        language="English",
        reasoning_enabled=False,
        temperature=0.0,
        memory_character_limit=25000
    )

    # Create experiment config
    exp_config = ExperimentConfiguration(
        language="English",
        seed=42,
        agents=[sophie_config, alice_config],
        utility_agent_model="gpt-4o-mini",
        utility_agent_temperature=0.0,
        phase2_rounds=7,
        distribution_range_phase2=[4, 8]
    )

    print("Creating participant agents...")

    # Create participant agents
    sophie = ParticipantAgent(sophie_config, experiment_config=exp_config, language_manager=lang_mgr)
    alice = ParticipantAgent(alice_config, experiment_config=exp_config, language_manager=lang_mgr)

    # Initialize agents asynchronously
    await sophie.async_init()
    await alice.async_init()

    print(f"✅ Sophie agent initialized: {sophie.agent is not None}")
    print(f"✅ Alice agent initialized: {alice.agent is not None}")

    # Create participant contexts (CRITICAL: These are set up like Phase2Manager does)
    sophie_context = ParticipantContext(
        name="Sophie",
        role_description="Participant in distributive justice experiment",
        bank_balance=0.0,
        memory="Test memory for Sophie",
        round_number=1,
        phase=ExperimentPhase.PHASE_2,
        stage=ExperimentStage.VOTING,  # Set to VOTING (not DISCUSSION)
        formatted_context_header=lang_mgr.format_phase2_discussion_instructions(
            round_number=1,
            max_rounds=7,
            participant_names=["Sophie", "Alice"],
            discussion_history="Round 1 / Speaker: Sophie Statement: I think we should vote.\nRound 1 / Speaker: Alice Statement: I agree."
        ),
        interaction_type=None,
        allow_vote_tool=True  # Initially true
    )

    alice_context = ParticipantContext(
        name="Alice",
        role_description="Participant in distributive justice experiment",
        bank_balance=0.0,
        memory="Test memory for Alice",
        round_number=1,
        phase=ExperimentPhase.PHASE_2,
        stage=ExperimentStage.VOTING,
        formatted_context_header=lang_mgr.format_phase2_discussion_instructions(
            round_number=1,
            max_rounds=7,
            participant_names=["Sophie", "Alice"],
            discussion_history="Round 1 / Speaker: Sophie Statement: I think we should vote.\nRound 1 / Speaker: Alice Statement: I agree."
        ),
        interaction_type=None,
        allow_vote_tool=True
    )

    # Create discussion state
    from models import GroupDiscussionState
    discussion_state = GroupDiscussionState(
        round_number=1,
        public_history="Round 1 / Speaker: Sophie Statement: I think we should vote.\nRound 1 / Speaker: Alice Statement: I agree."
    )

    # Create utility agent for voting service
    utility_agent_config = AgentConfiguration(
        name="Utility",
        personality="",
        model="gpt-4o-mini",
        language="English",
        reasoning_enabled=False,
        temperature=0.0,
        memory_character_limit=10000
    )

    from experiment_agents import UtilityAgent
    utility_agent = UtilityAgent(utility_agent_config, language_manager=lang_mgr)
    await utility_agent.async_init()

    print(f"✅ Utility agent initialized\n")

    # Create voting service
    voting_service = VotingService(
        language_manager=lang_mgr,
        utility_agent=utility_agent,
        settings=settings,
        logger=None,
        memory_service=None,
        agent_logger=None
    )

    print("=" * 70)
    print("CALLING conduct_confirmation_phase")
    print("=" * 70)
    print(f"Initiator: Sophie")
    print(f"Participants: [Sophie, Alice]")
    print(f"Contexts: [sophie_context, alice_context]")
    print(f"Sophie will be auto-confirmed (no API call)")
    print(f"Alice will call Runner.run() - WATCHING FOR ABORT")
    print("=" * 70 + "\n")

    try:
        # This is the EXACT call that happens in production
        all_confirmed = await voting_service.conduct_confirmation_phase(
            participants=[sophie, alice],
            initiator_name="Sophie",
            initiation_statement="I think we should vote.",
            contexts=[sophie_context, alice_context],
            discussion_state=discussion_state
        )

        print(f"\n✅ Confirmation phase completed")
        print(f"All confirmed: {all_confirmed}")
        print(f"Discussion state public history:\n{discussion_state.public_history}")

    except Exception as e:
        print(f"\n❌ EXCEPTION during confirmation phase:")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\n🔍 TESTING VOTING CONFIRMATION ABORT ISSUE\n")
    asyncio.run(test_confirmation_sequence())
