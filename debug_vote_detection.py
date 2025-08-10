#!/usr/bin/env python3
"""Minimal test to debug the vote detection issue."""
import asyncio
import logging
import sys
import os
from pathlib import Path

# Setup logging to see debug output
logging.basicConfig(level=logging.INFO)

sys.path.insert(0, str(Path(__file__).parent))

# Set environment variables to avoid missing keys
os.environ.setdefault('OPENAI_API_KEY', 'test-key')

# Test with the exact statements that failed
FAILED_STATEMENTS = [
    "I propose we vote on maximizing the average income with a floor constraint of $12,000.",
    "Since we have reached agreement on both the principle and floor amount, I propose that we vote.",
    "I am ready to call for a vote. The group has repeatedly converged on the same principle.",
    "Therefore, I propose we vote on maximizing the average income with a floor constraint of $12,000.",
    "I fully support moving forward with a vote on maximizing the average income with a floor constraint of $12,000.",
]

async def debug_vote_detection():
    """Test vote detection with minimal setup."""
    print("=== DEBUGGING VOTE DETECTION ===")
    print("Testing the exact statements that failed in the experiment...")
    
    try:
        from experiment_agents.utility_agent import UtilityAgent
        
        utility_agent = UtilityAgent()
        
        for i, statement in enumerate(FAILED_STATEMENTS):
            print(f"\n--- Test {i+1} ---")
            print(f"Statement: {statement}")
            
            try:
                proposal = await utility_agent.extract_vote_from_statement(statement)
                print(f"Result: {proposal}")
                print(f"Detected: {'YES' if proposal else 'NO'}")
                if proposal:
                    print(f"Proposal text: {proposal.proposal_text}")
            except Exception as e:
                print(f"ERROR: {e}")
                import traceback
                traceback.print_exc()
    
    except ImportError as e:
        print(f"Import error: {e}")
        print("This suggests there may be missing dependencies or circular imports")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_vote_detection())