"""
Minimal test to reproduce the voting confirmation error.
"""
import asyncio
from models import ParticipantContext, ExperimentPhase, ExperimentStage
from config.models import AgentConfiguration
from experiment_agents import ParticipantAgent
from agents import Runner

async def test_confirmation_call():
    """Test if we can reproduce the error with a minimal setup."""

    # Create a context similar to what would be used during confirmation
    context = ParticipantContext(
        name="Alice",
        role_description="Test participant",
        bank_balance=0.0,
        memory="Test memory",
        round_number=1,
        phase=ExperimentPhase.PHASE_2,
        stage=ExperimentStage.VOTING,
        formatted_context_header="Test header with discussion history",
        interaction_type="vote_confirmation",
        allow_vote_tool=False  # Disabled during confirmation
    )

    # Create a minimal agent config
    agent_config = AgentConfiguration(
        name="Alice",
        personality="You are a test participant.",
        model="gpt-4o-mini",  # Use a known good model
        language="English",
        reasoning_enabled=False,
        temperature=0.0,
        memory_character_limit=25000
    )

    # Create participant agent
    participant = ParticipantAgent(agent_config, language="English", verbosity="minimal")

    # Try to run a confirmation prompt
    confirmation_prompt = "Do you agree to vote? Reply 1 for yes, 0 for no."

    try:
        print(f"Calling Runner.run with context.stage={context.stage}")
        print(f"Context.formatted_context_header exists: {context.formatted_context_header is not None}")

        result = await asyncio.wait_for(
            Runner.run(participant.agent, confirmation_prompt, context=context),
            timeout=30
        )

        print(f"SUCCESS: {result.final_output}")

    except asyncio.TimeoutError:
        print("ERROR: Timeout")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_confirmation_call())
