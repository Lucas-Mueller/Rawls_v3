# Plan: Fix Phase 2 Round Counter Display Error

## Problem Statement
Phase 2 memory updates incorrectly display "phase 1 round 0" instead of proper phase and round information. This occurs when memory update calls bypass the services architecture and directly call `MemoryManager.prompt_agent_for_memory_update()` without required `round_number` and `phase` parameters.

## Root Cause Analysis

### Working System (No Fix Needed)
Most Phase 2 memory updates correctly use:
- **MemoryService** → **SelectiveMemoryManager.update_memory_selective()** → automatically extracts `round_number` and `phase` from context
- These calls work correctly and show proper round counters

### Broken System (Needs Fix)
**Only 1 location** needs fixing (investigation revealed the voting manager method is deprecated/unused):

1. **CounterfactualsService.py:1051** - `_fallback_memory_update()` method
   - Context: Final ranking retry experience updates
   - Current: Missing `round_number` and `phase` parameters
   - Impact: Shows "phase 1 round 0" during Phase 2 final ranking retries

## Focused Solution

### Single Fix Required
**File:** `core/services/counterfactuals_service.py`
**Location:** Line 1051 in `_fallback_memory_update()` method

**Current Code:**
```python
updated_memory = await MemoryManager.prompt_agent_for_memory_update(
    participant, context, retry_memory_content,
    memory_guidance_style=memory_guidance_style,
    language_manager=self.language_manager,
    error_handler=None,
    utility_agent=None
    # MISSING: round_number and phase parameters
)
```

**Fixed Code:**
```python
updated_memory = await MemoryManager.prompt_agent_for_memory_update(
    participant, context, retry_memory_content,
    memory_guidance_style=memory_guidance_style,
    language_manager=self.language_manager,
    error_handler=None,
    utility_agent=None,
    round_number=getattr(context, 'round_number', None),
    phase="phase_2"
)
```

## Implementation Details

### Context Analysis
- **When called:** During final ranking retry experiences in Phase 2
- **Context state:** Final ranking phase (post-voting, post-results delivery)
- **Round number source:** Should use `context.round_number` (may be 0 or None for final ranking phase)
- **Phase:** Always "phase_2" since this only occurs in CounterfactualsService (Phase 2 only)

### Safe Implementation Pattern
- Use `getattr(context, 'round_number', None)` to safely extract round number
- Use `phase="phase_2"` as constant since CounterfactualsService is Phase 2 specific
- This matches the pattern used in `SelectiveMemoryManager.update_memory_selective()`

## Testing Strategy

### Validation Tests
1. **Memory Update Display Test:**
   - Enable `memory_update_on_retry=true` in test config
   - Trigger final ranking retry in Phase 2
   - Verify memory prompt shows correct phase/round instead of "phase 1 round 0"

2. **Regression Test:**
   - Ensure fix doesn't break existing final ranking retry functionality
   - Verify memory content is still properly updated

3. **Integration Test:**
   - Run full Phase 2 experiment with retries enabled
   - Confirm all memory updates show consistent phase/round information

### Expected Outcome
- Final ranking retry memory updates will display correct phase information
- Round counter will show actual round (likely 0 for final ranking phase) instead of incorrect "phase 1 round 0"
- No functional changes to memory content or retry behavior

## Files to Modify
- `core/services/counterfactuals_service.py` (1 line change at line 1051)

## Risk Assessment
- **Very Low Risk:** Minimal change adding only missing parameters
- **No Breaking Changes:** Only fixes display issue, no behavioral changes
- **Isolated Impact:** Only affects final ranking retry memory display
- **Rollback Simple:** Single line change easily reverted if needed

## Implementation Confidence: HIGH
This is a **focused, minimal fix** that addresses the specific Phase 2 round counter issue without overengineering. The solution follows existing patterns in the codebase and requires only a single line modification.