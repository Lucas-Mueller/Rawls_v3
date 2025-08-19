#!/usr/bin/env python3
"""
Demonstration script showing the ghost agent fix in action.
This simulates the exact scenario that caused the original issue.
"""

from models.experiment_types import GroupDiscussionState

def test_ghost_agent_scenario():
    """Simulate the exact ghost agent contamination scenario."""
    print("=== GHOST AGENT FIX DEMONSTRATION ===\n")
    
    # Simulate two concurrent experiments
    print("1. Creating two concurrent experiments:")
    
    # Experiment 1: 3 agents
    experiment_3_agents = GroupDiscussionState()
    experiment_3_agents.valid_participants = ["Agent_1", "Agent_2", "Agent_3"]
    print(f"   - 3-agent experiment (ID: {experiment_3_agents.experiment_id[:8]}...)")
    
    # Experiment 2: 4 agents  
    experiment_4_agents = GroupDiscussionState()
    experiment_4_agents.valid_participants = ["Agent_1", "Agent_2", "Agent_3", "Agent_4"]
    print(f"   - 4-agent experiment (ID: {experiment_4_agents.experiment_id[:8]}...)")
    
    print("\n2. Adding valid statements to both experiments:")
    
    # Add valid statements
    experiment_3_agents.add_statement("Agent_1", "I prefer maximizing average income")
    experiment_4_agents.add_statement("Agent_4", "I think we should maximize the floor")
    
    print("   ✓ Agent_1 statement added to 3-agent experiment")
    print("   ✓ Agent_4 statement added to 4-agent experiment")
    
    print("\n3. Attempting ghost agent contamination (this should now be blocked):")
    
    try:
        # This would have caused the original ghost agent issue
        experiment_3_agents.add_statement("Agent_4", "Ghost agent trying to contaminate 3-agent experiment!")
        print("   ❌ ERROR: Ghost agent was allowed! Fix failed.")
        return False
    except ValueError as e:
        print(f"   ✅ SUCCESS: Ghost agent blocked - {str(e)}")
    
    print("\n4. Verifying experiment isolation:")
    print(f"   - 3-agent experiment has {len(experiment_3_agents.statements)} statements")
    print(f"   - 4-agent experiment has {len(experiment_4_agents.statements)} statements")
    print(f"   - 3-agent history: {repr(experiment_3_agents.public_history.strip())}")
    print(f"   - 4-agent history: {repr(experiment_4_agents.public_history.strip())}")
    
    # Verify no cross-contamination
    if "Agent_4" in experiment_3_agents.public_history:
        print("   ❌ ERROR: Cross-contamination detected!")
        return False
    
    print("   ✅ Perfect isolation maintained!")
    return True

def test_backward_compatibility():
    """Test that the fix doesn't break existing functionality."""
    print("\n=== BACKWARD COMPATIBILITY TEST ===\n")
    
    # Test without validation (legacy mode)
    legacy_state = GroupDiscussionState()
    # valid_participants is None by default - should allow any agent
    
    legacy_state.add_statement("Any_Agent", "This should work in legacy mode")
    legacy_state.add_statement("Random_Name", "This should also work")
    
    print("✅ Legacy mode (no validation) works correctly")
    
    return True

if __name__ == "__main__":
    print("Testing ghost agent contamination fix...\n")
    
    success = test_ghost_agent_scenario()
    success = test_backward_compatibility() and success
    
    if success:
        print("\n" + "="*50)
        print("🎉 ALL TESTS PASSED! Ghost agent fix is working!")
        print("="*50)
    else:
        print("\n" + "="*50) 
        print("❌ TESTS FAILED! Fix needs more work.")
        print("="*50)
        exit(1)