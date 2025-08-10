# Phase 2 Voting Mechanism - Minimal Fix Plan

**Approach**: Debug first, then fix the specific issue  
**Timeline**: 30-60 minutes  
**Principle**: Simplicity - find and fix the root cause, nothing more

## Step 1: Add Strategic Logging (15 minutes)

The issue is somewhere in this flow:
1. Agent makes statement → 2. Vote detection → 3. Unanimous agreement check → 4. Vote

Let's add logging to see exactly where it breaks.

**File**: `core/phase2_manager.py`

```python
# Around line 153, after vote detection
vote_proposal = await self.utility_agent.extract_vote_from_statement(statement)

# ADD THIS LOGGING:
import logging
logger = logging.getLogger(__name__)

logger.info(f"=== VOTE DETECTION DEBUG ===")
logger.info(f"Agent: {participant.name}")
logger.info(f"Statement: {statement}")
logger.info(f"Vote proposal detected: {vote_proposal is not None}")
if vote_proposal:
    logger.info(f"Vote proposal text: {vote_proposal.proposal_text}")
else:
    logger.info(f"No vote proposal detected")

if vote_proposal:
    logger.info(f"Checking unanimous agreement...")
    unanimous_agreement = await self._check_unanimous_vote_agreement(
        discussion_state, contexts, config
    )
    logger.info(f"Unanimous agreement result: {unanimous_agreement}")
    # ... rest of existing code
```

**File**: `core/phase2_manager.py` in `_check_unanimous_vote_agreement()`

```python
# Around line 326, after getting responses
responses = await asyncio.gather(*agreement_tasks)

# ADD THIS LOGGING:
logger.info(f"=== UNANIMOUS AGREEMENT DEBUG ===")
for i, response in enumerate(responses):
    participant_name = self.participants[i].name
    response_text = response.final_output
    contains_yes = "YES" in response_text.upper()
    logger.info(f"{participant_name} response: '{response_text}' -> Contains YES: {contains_yes}")

agreements = [("YES" in response.final_output.upper()) for response in responses]
logger.info(f"All agreements: {agreements}")
logger.info(f"Unanimous result: {all(agreements)}")
```

## Step 2: Create Simple Reproduction Test (10 minutes)

**File**: `debug_vote_detection.py`

```python
#!/usr/bin/env python3
"""Minimal test to debug the vote detection issue."""
import asyncio
import logging
import sys
from pathlib import Path

# Setup logging to see debug output
logging.basicConfig(level=logging.INFO)

sys.path.insert(0, str(Path(__file__).parent))

# Test with the exact statements that failed
FAILED_STATEMENTS = [
    "I propose we vote on maximizing the average income with a floor constraint of $12,000.",
    "Since we have reached agreement on both the principle and floor amount, I propose that we vote.",
    "I am ready to call for a vote. The group has repeatedly converged on the same principle."
]

async def debug_vote_detection():
    """Test vote detection with minimal setup."""
    from experiment_agents.utility_agent import UtilityAgent
    
    utility_agent = UtilityAgent()
    
    for i, statement in enumerate(FAILED_STATEMENTS):
        print(f"\n--- Test {i+1} ---")
        print(f"Statement: {statement}")
        
        try:
            proposal = await utility_agent.extract_vote_from_statement(statement)
            print(f"Result: {proposal}")
            print(f"Detected: {'YES' if proposal else 'NO'}")
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(debug_vote_detection())
```

## Step 3: Run and Diagnose (10 minutes)

```bash
cd /path/to/project
python debug_vote_detection.py
```

This will show us exactly what the vote detection is returning.

Then run a quick experiment to see the logging:
```bash
python main.py config/default_config.yaml
# Watch the logs for "=== VOTE DETECTION DEBUG ===" messages
```

## Step 4: Fix the Specific Issue (15-30 minutes)

Based on what we find, there are only a few likely fixes:

### If vote detection is failing:
- **Fix the prompt** in `utils/language_manager.py` to be more explicit
- **Fix the response parsing** in `extract_vote_from_statement()`

### If unanimous agreement is failing:
- **Fix the agreement prompt** to be clearer about when to say YES vs NO
- **Fix the response parsing** to handle different YES formats

### Most likely fix needed:
The current `get_vote_detection_prompt()` probably doesn't exist or is too rigid. Add this to `utils/language_manager.py`:

```python
def get_vote_detection_prompt(self, statement: str) -> str:
    """Simple, explicit vote detection prompt."""
    return f"""Is this participant proposing to conduct a vote?

Statement: "{statement}"

Look for phrases like:
- "I propose we vote"
- "I propose a vote"  
- "Let's vote"
- "Ready to vote"
- "Call for a vote"
- "Should we vote"

If YES, respond: VOTE_PROPOSAL: vote on [what they want to vote on]
If NO, respond: NO_VOTE"""
```

## Step 5: Verify Fix (5 minutes)

Run the reproduction test again:
```bash
python debug_vote_detection.py  # Should now show "Detected: YES"
```

Run a quick experiment:
```bash
python main.py config/default_config.yaml  # Should reach consensus
```

## That's It.

Total time: ~1 hour maximum. No fancy consensus detection, no emergency triggers, no multi-method approaches. Just find the bug and fix it.

The beauty of this approach:
- **Fast**: We'll know what's broken within 15 minutes
- **Focused**: Fix only the specific issue we find  
- **Low risk**: Minimal changes to existing code
- **Debuggable**: Comprehensive logging to prevent future issues

Let's see what we actually discover before building any elaborate solutions.