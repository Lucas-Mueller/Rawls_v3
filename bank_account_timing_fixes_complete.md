# Bank Account Timing Fixes - Complete Resolution

## Issues Identified and Fixed

You were absolutely correct about the "one round behind" bank balance issue. This problem existed in **both Phase 1 and Phase 2**.

### Phase 1 Issue (FIXED)

**Location**: `core/phase1_manager.py:198-212`

**Problem**: During application rounds, the sequence was:
1. Agent makes principle choice
2. Earnings calculated 
3. **Memory update** with results showing new earnings BUT context still has old bank balance
4. **Bank balance updated AFTER** memory update

**Fix Applied**: Moved bank balance update to happen BEFORE memory update:

```python
# Update context with earnings FIRST so bank balance is correct during memory update
context = update_participant_context(
    context,
    balance_change=result.earnings,
    new_round=round_num
)

# Update memory with agent using new guidance style (now with correct bank balance)
context.memory = await MemoryManager.prompt_agent_for_memory_update(
    participant, context, round_content, ...
)
```

### Phase 2 Issue (FIXED)

**Location**: `core/services/counterfactuals_service.py:559-563`

**Problem**: After group discussion, the sequence was:
1. Phase 2 earnings calculated
2. **Memory update** with results showing Phase 2 earnings BUT context still has old bank balance (only Phase 1 total)
3. **Bank balance NEVER updated** with Phase 2 earnings

**Fix Applied**: Added bank balance update BEFORE memory update:

```python
# Update context bank balance with Phase 2 earnings FIRST
context.bank_balance += final_earnings

# Update participant memory with results (now with correct bank balance)
if self.memory_service:
    updated_memory = await self.memory_service.update_final_results_memory(...)
```

## Impact of Fixes

### Before Fixes:
- **Phase 1**: Agents saw new earnings in memory content but bank balance lagged by one round
- **Phase 2**: Agents saw Phase 2 earnings in memory content but bank balance never included them

### After Fixes:
- **Phase 1**: Bank balance immediately reflects current round earnings during memory updates
- **Phase 2**: Bank balance includes both Phase 1 + Phase 2 earnings during final memory updates

## Context Consistency Achieved

Now agents will see:
- ✅ **Correct earnings** in their result content 
- ✅ **Matching bank balance** in their context during memory updates
- ✅ **Consistent totals** throughout both phases

The timing disconnect that was causing confusion for agents has been completely resolved.