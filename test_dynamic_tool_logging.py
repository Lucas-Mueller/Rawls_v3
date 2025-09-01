#!/usr/bin/env python3
"""
Test script to verify the dynamic tool logging functionality works.
"""
import logging
import asyncio
import sys
import os

# Configure logging to show our output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import Phase1Manager, Phase2Manager
from experiment_agents.tools.voting_tools import propose_vote, _is_phase2_group_discussion
from config.models import AgentConfiguration
from models import ParticipantContext, ExperimentPhase

async def test_dynamic_tool_logging():
    """Test the dynamic tool logging functionality."""
    
    print("Testing Dynamic Tool Logging Functionality")
    print("=" * 50)
    
    # Create a minimal mock participant agent with real propose_vote tool
    class MockParticipantAgent:
        def __init__(self, name, model="test_model"):
            self.config = AgentConfiguration(
                name=name,
                personality="Test personality",
                model=model,
                temperature=0.7,
                memory_character_limit=1000
            )
            # Mock the agent with real propose_vote tool
            self.agent = type('MockAgent', (), {
                '_tools': [propose_vote]
            })()
    
    # Create mock utility agent
    class MockUtilityAgent:
        def __init__(self):
            self.utility_model = "test_utility_model"
    
    # Create test participants
    participants = [
        MockParticipantAgent("Alice", "gpt-4"),
        MockParticipantAgent("Bob", "gpt-3.5-turbo")
    ]
    
    utility_agent = MockUtilityAgent()
    
    # Create managers
    phase1_manager = Phase1Manager(participants, utility_agent, None)
    phase2_manager = Phase2Manager(participants, utility_agent, None, None)
    
    print("\n--- Testing Phase 1 Dynamic Tool Logging ---")
    phase1_manager._log_agent_tools("Phase 1")
    
    print("\n--- Testing Phase 2 Dynamic Tool Logging ---") 
    phase2_manager._log_agent_tools("Phase 2")
    
    print("\n--- Testing Direct Tool Enablement Check ---")
    # Test the actual is_enabled function directly
    mock_context_phase1 = type('MockContext', (), {
        'context': ParticipantContext(
            name="Alice",
            role_description="",
            bank_balance=0.0,
            memory="",
            round_number=0,
            phase=ExperimentPhase.PHASE_1,
            memory_character_limit=1000
        )
    })()
    
    mock_context_phase2 = type('MockContext', (), {
        'context': ParticipantContext(
            name="Alice",
            role_description="",
            bank_balance=0.0,
            memory="",
            round_number=0,
            phase=ExperimentPhase.PHASE_2,
            memory_character_limit=1000
        )
    })()
    
    print(f"propose_vote enabled in Phase 1: {_is_phase2_group_discussion(mock_context_phase1, None)}")
    print(f"propose_vote enabled in Phase 2: {_is_phase2_group_discussion(mock_context_phase2, None)}")
    
    print("\n✅ Dynamic tool logging test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_dynamic_tool_logging())