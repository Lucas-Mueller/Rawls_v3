# Recent Activity Duplication Fix Plan

## Issue Summary

Agents are experiencing duplication of their own discussion statements during Phase 2:

1. **First occurrence**: In reasoning prompts via "Discussion History" which contains their own previous statements
2. **Second occurrence**: In memory update prompts via "Recent Activity" which shows the same statements again

This creates redundant information processing and potentially confuses agents about what content is new vs. already seen.

## Root Cause Analysis

### The Duplication Flow

1. **Discussion Phase**: Agent makes a statement in discussion
2. **Discussion History**: Statement gets added to `GroupDiscussionState.public_history`
3. **Reasoning Prompt**: Next agent sees "Discussion History" containing the previous statement
4. **Memory Update**: Same agent then gets LLM memory update with "Recent Activity" showing the same statement again

### Technical Root Cause

The issue stems from `MemoryEventType.DISCUSSION_STATEMENT` events being classified as **complex events** that trigger full LLM memory updates:

**File**: `utils/selective_memory_manager.py`
- `DISCUSSION_STATEMENT` is in `COMPLEX_MEMORY_EVENTS`
- Complex events route to `_full_memory_update()` which calls `MemoryManager.prompt_agent_for_memory_update()`

**File**: `utils/memory_manager.py`
- `_create_memory_update_prompt()` uses templates from translations
- Templates include a "Recent Activity" section with `{round_content}`

**File**: `translations/english_prompts.json`
- `prompts.memory_memory_update_prompt` and `prompts.memory_narrative_update_prompt` include "Recent Activity:\n{round_content}"

### Where Interaction Types Are Set

**Discussion Service** (`core/services/discussion_service.py`):
- Sets `context.interaction_type = "internal_reasoning"` for reasoning calls
- Sets `context.interaction_type = "statement"` for discussion statement calls

**Voting Service** (`core/services/voting_service.py`):
- Sets `context.interaction_type = "vote_prompt"` (vote initiation)
- Sets `context.interaction_type = "vote_confirmation"` (vote confirmation)

**Two-Stage Voting Manager** (`core/two_stage_voting_manager.py`):
- Sets `context.interaction_type = "ballot"` (ballot voting)

## Affected Components

### Primary Files to Modify
1. **`utils/memory_manager.py`** - Core memory update prompt generation
2. **`translations/english_prompts.json`** - Memory update templates
3. **`translations/spanish_prompts.json`** - Spanish memory templates  
4. **`translations/mandarin_prompts.json`** - Mandarin memory templates

### Files Using Memory Updates (for testing)
1. **`core/services/memory_service.py`** - Calls memory update functions
2. **`utils/selective_memory_manager.py`** - Routes to complex updates
3. **`core/phase2_manager.py`** - Triggers discussion memory updates

## Implementation Strategy

### Approach: Context-Aware Template Selection

Instead of modifying the complex routing logic, implement a surgical fix by making the memory update templates context-aware based on `interaction_type`.

### Step 1: Modify Memory Manager Template Creation (with fallback)

**File**: `utils/memory_manager.py`

**Current Method**: `_create_memory_update_prompt()`

**Modification**: Add context-aware template selection that checks for discussion-related interaction types and uses "Recent Activity"-free templates. Include a robust fallback to existing templates if new keys are missing to avoid KeyErrors in other languages or stale deployments.

```python
def _create_memory_update_prompt(
    current_memory: str,
    round_content: str,
    guidance_style: str = "narrative",
    language_manager=None,
    interaction_type: Optional[str] = None  # NEW PARAMETER
) -> str:
    """Create context-aware prompt for memory update based on interaction type."""

    # Check if this is a discussion-related interaction that already saw content
    discussion_interaction_types = {"internal_reasoning", "statement"}
    exclude_recent_activity = interaction_type in discussion_interaction_types

    # Choose appropriate template based on guidance style and context
    def pick_key(no_recent: bool) -> str:
        if guidance_style == "narrative":
            return f"prompts.memory_narrative_update_prompt{('_no_recent_activity' if no_recent else '')}"
        else:
            return f"prompts.memory_memory_update_prompt{('_no_recent_activity' if no_recent else '')}"

    primary_key = pick_key(no_recent=exclude_recent_activity)
    fallback_key = pick_key(no_recent=False)

    # Try new key first; if missing, gracefully fall back
    try:
        return language_manager.get(
            primary_key,
            current_memory=current_memory if current_memory.strip() else language_manager.get("prompts.memory_empty_memory_placeholder"),
            round_content=round_content
        )
    except Exception:
        return language_manager.get(
            fallback_key,
            current_memory=current_memory if current_memory.strip() else language_manager.get("prompts.memory_empty_memory_placeholder"),
            round_content=round_content
        )
```

### Step 2: Pass Interaction Type Through Call Stack (SelectiveMemoryManager + direct callers)

**File**: `utils/selective_memory_manager.py`

**Method**: `_full_memory_update()`

**Modification**: Extract interaction type from context and pass to memory manager.

```python
@staticmethod
async def _full_memory_update(
    agent: "ParticipantAgent",
    context: "ParticipantContext", 
    content: str,
    config=None,
    language_manager=None,
    error_handler=None,
    utility_agent=None,
    **kwargs
) -> str:
    # ... existing code ...
    
    # Extract interaction type from context
    interaction_type = getattr(context, 'interaction_type', None)
    
    # Use existing MemoryManager for full LLM updates
    return await MemoryManager.prompt_agent_for_memory_update(
        agent=agent,
        context=context,
        round_content=content,
        memory_guidance_style=memory_guidance_style,
        language_manager=language_manager,
        error_handler=error_handler,
        utility_agent=utility_agent,
        interaction_type=interaction_type,  # NEW PARAMETER
        **kwargs_clean
    )
```

Also update any direct callers (e.g., voting or Phase 1 flows) to optionally pass `interaction_type` when meaningful. Defaults preserve backward compatibility.

**File**: `utils/memory_manager.py`

**Method**: `prompt_agent_for_memory_update()`

**Modification**: Accept and pass interaction_type to template creation.

```python
@staticmethod
async def prompt_agent_for_memory_update(
    agent: "ParticipantAgent",
    context: "ParticipantContext", 
    round_content: str,
    max_retries: int = 5,
    memory_guidance_style: str = "narrative",
    language_manager=None,
    error_handler=None,
    utility_agent=None,
    interaction_type: Optional[str] = None  # NEW PARAMETER
) -> str:
    # ... existing code until template creation ...
    
    # Create memory update prompt with interaction type context
    prompt = MemoryManager._create_memory_update_prompt(
        memory_to_use, round_content, memory_guidance_style, language_manager, interaction_type
    )
    
    # ... rest of existing code ...
```

### Step 3: Create New Translation Templates

**Files**: `translations/english_prompts.json`, `translations/spanish_prompts.json`, `translations/mandarin_prompts.json`

**New Templates** (English example):

```json
{
  "prompts": {
    "memory_memory_update_prompt_no_recent_activity": "Return your complete updated memory incorporating insights from your recent reasoning and statement. Include both important information from your previous memory and new learnings. Focus on information that might influence your choices about justice principles or help you in group discussions.\n\nYour Previous Memory:\n{current_memory}\n\nYour Recent Reasoning and Statement:\n{round_content}\n\nRETURN: Your complete updated memory (not incremental changes or prefixes like 'Memory update:')",
    
    "memory_narrative_update_prompt_no_recent_activity": "Return your complete updated memory incorporating new insights from your recent reasoning and statement. Include everything important from your previous memory plus what you learned. Focus on what changed and key insights, not rules or transcripts.\n\nYour Previous Memory:\n{current_memory}\n\nYour Recent Reasoning and Statement:\n{round_content}\n\nRETURN: Your complete updated memory as a continuous narrative (do not add prefixes like 'Memory update:')"
  }
}
```

Note: These templates continue to include `{round_content}` (the agent’s own latest statement/reasoning). The main change is avoiding the explicit "Recent Activity" framing that could suggest novel content when it’s already been seen in the prior discussion prompt.

## Technical Considerations

### Current Round Content Scope
- `MemoryService.update_discussion_memory` already limits `round_content` to the agent’s own latest statement (and optional internal reasoning), not the full discussion history. The change here is about framing in the template and avoiding the "Recent Activity" label for discussion interactions — not about removing that content entirely.

### Maintaining Backward Compatibility
- Voting interactions (`vote_prompt`, `vote_confirmation`, `ballot`) will continue using "Recent Activity" templates
- Default behavior (when `interaction_type` is None or unrecognized) remains unchanged
- Simple memory events (vote decisions) continue using direct insertion without LLM calls
 
Implementation includes explicit template fallback so deployments missing the new keys will seamlessly use existing templates.

### Template Language Consistency
- New templates maintain the same core functionality as existing ones
- Only difference is removal of "Recent Activity" section and rewording to "Your Recent Reasoning and Statement"
- All three languages (English, Spanish, Mandarin) need consistent template updates

### Error Handling
- Explicit fallback to existing templates if new templates are missing (implemented in `_create_memory_update_prompt`)
- Graceful handling of missing interaction_type parameter
- No changes to retry logic or error recovery mechanisms

## Testing Strategy

### Unit Tests
1. **Memory Manager Template Selection**
   - Test context-aware template selection with different interaction types
   - Verify fallback to standard templates when interaction_type is None
   - Test both narrative and structured guidance styles
   - Test missing new keys: ensure graceful fallback without raising and that prompt contains "Recent Activity:" when the no-recent template is absent

2. **Template Content Validation**
   - Verify new templates exist in all language files
   - Test template rendering with sample data
   - Ensure templates produce valid prompts

### Integration Tests
1. **Discussion Flow Testing**
   - Test internal reasoning calls use no-duplication templates
   - Test statement calls use no-duplication templates  
   - Verify voting calls still use standard templates with "Recent Activity"

2. **Memory Update Validation**
   - Compare memory updates before/after fix
   - Ensure voting context still receives full information
   - Test multilingual memory updates

3. **Prompt Content Checks**
   - Assert that discussion-related memory prompts do not include the literal string "Recent Activity:" and instead include "Your Recent Reasoning and Statement:"

### End-to-End Testing
1. **Complete Phase 2 Workflow**
   - Run full Phase 2 discussion with memory updates
   - Verify no duplication in reasoning/statement memory updates
   - Confirm voting interactions still work correctly

2. **Cross-Language Testing**  
   - Test fix with Spanish and Mandarin experiments
   - Verify template translations are accurate
   - Ensure multilingual consistency

## Risk Assessment

### Low Risk Changes
- ✅ Template additions are additive (no existing functionality removed)
- ✅ Parameter additions have defaults (backward compatible)
- ✅ Changes are localized to memory update flow only

### Medium Risk Areas
- ⚠️ New translation templates need careful review for accuracy
- ⚠️ Context extraction logic needs thorough testing
- ⚠️ Interaction type propagation through call stack

### Mitigation Strategies
1. **Gradual Rollout**: Test with single-language experiments first
2. **Fallback Logic**: Maintain existing templates as fallback
3. **Comprehensive Testing**: Test all interaction types and languages
4. **Rollback Plan**: Easy revert by removing new parameter usage
5. **Config Guard (Optional)**: If desired, gate the new behavior behind a config flag (e.g., `phase2_settings.suppress_recent_activity_in_discussion_memory_prompts`) defaulting to `True` for even safer rollout.

## Timeline Estimation

### Phase 1: Core Implementation (2-3 hours)
- [ ] Modify `memory_manager.py` template selection logic
- [ ] Update `selective_memory_manager.py` parameter passing
- [ ] Create English translation templates

### Phase 2: Multilingual Support (1-2 hours)  
- [ ] Create Spanish translation templates
- [ ] Create Mandarin translation templates
- [ ] Validate template translations

### Phase 3: Testing & Validation (2-3 hours)
- [ ] Unit test template selection logic
- [ ] Integration test discussion workflows
- [ ] End-to-end test Phase 2 experiments

### Phase 4: Documentation & Cleanup (1 hour)
- [ ] Update code comments and docstrings  
- [ ] Document new template parameters
- [ ] Clean up any temporary testing code

**Total Estimated Time**: 6-9 hours

## Dependencies

### Prerequisites
- Understanding of existing memory update flow
- Access to all three translation files
- Ability to run Phase 2 experiments for testing

### Blocking Factors
- No major blocking dependencies identified
- Changes are isolated and don't require other system modifications

## Success Criteria

### Primary Goals
1. ✅ Internal reasoning calls (`interaction_type = "internal_reasoning"`) no longer show "Recent Activity" 
2. ✅ Discussion statement calls (`interaction_type = "statement"`) no longer show "Recent Activity"
3. ✅ Voting calls (`interaction_type` in `["vote_prompt", "vote_confirmation", "ballot"]`) continue showing "Recent Activity"

### Secondary Goals  
1. ✅ No breaking changes to existing functionality
2. ✅ Consistent behavior across all supported languages
3. ✅ Maintainable code with clear separation of concerns
4. ✅ Comprehensive test coverage for new functionality

### Validation Methods
1. **Log Analysis**: Review memory update logs to confirm template usage
2. **Agent Testing**: Run sample experiments and verify no duplication complaints
3. **Functionality Testing**: Ensure voting information remains complete
4. **Performance Testing**: Confirm no degradation in memory update performance

## Conclusion

This surgical fix addresses the specific "Recent Activity" duplication issue while maintaining all existing functionality. The context-aware approach ensures that discussion-related memory updates avoid duplication while preserving the full information context needed for voting decisions.

The implementation is low-risk, backward compatible, and easily testable. The modular approach allows for incremental rollout and easy rollback if issues are discovered.
