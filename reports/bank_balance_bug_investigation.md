# Bank Balance Bug Investigation Report

## Issue Summary

**Problem**: Agent bank balance suddenly drops to $0 during the experiment despite agents never being able to lose money.

**Severity**: Critical - This affects the core experimental economics and agent instructions about their earnings.

**Location**: `experiment_agents/participant_agent.py:52` in the `update_memory` method.

## Root Cause Analysis

### The Bug

The bug is located in the `ParticipantAgent.update_memory()` method at `participant_agent.py:52`. When agents are prompted to update their memory throughout the experiment, a temporary context is created that incorrectly sets the `bank_balance` to `0.0`:

```python
# BUGGY CODE in experiment_agents/participant_agent.py:46-57
async def update_memory(self, prompt: str) -> str:
    """Agent updates their own memory based on prompt."""
    # Create a temporary context just for memory update
    temp_context = ParticipantContext(
        name=self.config.name,
        role_description="Memory update",
        bank_balance=0.0,  # ← BUG: This should be the current bank balance
        memory="",
        round_number=0,
        phase=ExperimentPhase.PHASE_1,
        memory_character_limit=self.config.memory_character_limit
    )
    
    result = await Runner.run(self.agent, prompt, context=temp_context)
    return result.final_output
```

### How This Causes the Problem

1. **Phase 1**: Agents earn money through principle applications, building up their bank balance (e.g., reaching $3.68).

2. **Memory Updates**: Throughout the experiment, agents are frequently prompted to update their memory using `MemoryManager.prompt_agent_for_memory_update()`.

3. **Context Exposure**: When agents update their memory, they receive a context with `bank_balance=0.0`, which gets displayed in their instructions:
   ```
   Bank Balance: $0.00  # ← Agent sees this incorrect value
   ```

4. **Agent Confusion**: Agents see their bank balance as $0 during memory updates, leading to confusion about their earnings status.

5. **State Persistence**: While the actual `ParticipantContext` maintains the correct bank balance, agents are temporarily shown incorrect financial information during memory operations.

### Verification of Root Cause

The bank balance transfer from Phase 1 to Phase 2 is implemented correctly in `phase2_manager.py:76`:

```python
# CORRECT CODE in core/phase2_manager.py:76
bank_balance=phase1_result.total_earnings,  # Carry forward earnings
```

This confirms that the issue is not with phase transitions but specifically with the temporary context used during memory updates.

## Impact Analysis

### What Works Correctly
- ✅ Bank balance accumulation during Phase 1 principle applications
- ✅ Bank balance transfer from Phase 1 to Phase 2 
- ✅ Final earnings calculations and payoffs
- ✅ Actual participant context state maintenance

### What Is Broken
- ❌ Agents see incorrect bank balance ($0.00) during memory update operations
- ❌ Agents may make decisions based on incorrect financial information
- ❌ Experimental integrity compromised as agents receive wrong earnings feedback

### Frequency of Bug
This bug occurs every time an agent updates their memory, which happens:
- After each Phase 1 ranking step
- After the detailed explanation step  
- After each of the 4 Phase 1 application rounds
- After Phase 1 final ranking
- After each Phase 2 discussion statement
- After Phase 2 vote results
- Before Phase 2 final rankings

**Total**: ~15-20 times per agent per experiment, meaning agents frequently see incorrect bank balance information.

## Recommended Fix

Replace the hardcoded `bank_balance=0.0` with the actual current bank balance by passing it as a parameter:

```python
# PROPOSED FIX
async def update_memory(self, prompt: str, current_bank_balance: float = 0.0) -> str:
    """Agent updates their own memory based on prompt."""
    # Create a temporary context just for memory update
    temp_context = ParticipantContext(
        name=self.config.name,
        role_description="Memory update",
        bank_balance=current_bank_balance,  # Use actual balance
        memory="",
        round_number=0,
        phase=ExperimentPhase.PHASE_1,
        memory_character_limit=self.config.memory_character_limit
    )
    
    result = await Runner.run(self.agent, prompt, context=temp_context)
    return result.final_output
```

And update all calls to `MemoryManager.prompt_agent_for_memory_update()` to pass the current balance.

## Verification Steps

1. Search for all instances of `bank_balance=0.0` to ensure no other hardcoded zero balances exist
2. Verify that `update_participant_context()` function correctly preserves bank balances
3. Test that Phase 1 to Phase 2 transfer maintains correct balances
4. Review agent instructions generation to ensure correct balance display

## Priority

**HIGH PRIORITY**: This bug affects the core experimental mechanism where agents make economic decisions based on their earnings. Agents receiving incorrect balance information can lead to invalid experimental results and compromised data integrity.