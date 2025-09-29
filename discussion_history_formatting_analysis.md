# Discussion History Formatting Analysis Report

## Issue Summary

The discussion history is formatted inconsistently across different contexts in Phase 2. When agents are asked to make statements to the group, the discussion history appears with bold formatting, but when agents are updating their memory, the same discussion history appears without bold formatting. The user wants unified formatting that matches the memory update style (no bold).

## Root Cause Analysis

### Two Different Formatting Paths

**1. Statement Request Context (WITH Bold Formatting)**
- **Flow**: `ParticipantAgent._generate_dynamic_instructions()` → `LanguageManager.format_phase2_discussion_instructions()` → `context_discussion_history_section_format`
- **Location**: `experiment_agents/participant_agent.py:272-277`
- **Key Method**: `format_phase2_discussion_instructions()`
- **Template Used**: `context_discussion_history_section_format`

**2. Memory Update Context (WITHOUT Bold Formatting)**
- **Flow**: `MemoryService.update_discussion_memory()` → Direct inclusion
- **Location**: `core/services/memory_service.py:234-236`
- **Key Method**: `update_discussion_memory()`
- **Template Used**: Direct string concatenation `f"{discussion_history}\n\n"`

### The Bold Formatting Source

The bold formatting is applied through translation templates in all language files:

**English** (`translations/english_prompts.json`):
```json
"context_discussion_history_section_format": "**=== DISCUSSION HISTORY ===**\n{discussion_history}\n=========================="
```

**Spanish** (`translations/spanish_prompts.json`):
```json
"context_discussion_history_section_format": "**=== HISTORIAL DE DISCUSIÓN ===**\n{discussion_history}\n================================"
```

**Mandarin** (`translations/mandarin_prompts.json`):
```json
"context_discussion_history_section_format": "**=== 讨论历史 ===**\n{discussion_history}\n=================="
```

## Technical Deep Dive

### Statement Request Flow

1. **Trigger**: Agent asked to make statement to group
2. **Entry Point**: `ParticipantAgent._generate_dynamic_instructions()` (line 272)
3. **Conditional Logic**: `if context.phase == ExperimentPhase.PHASE_2:`
4. **Method Call**: `language_manager.format_phase2_discussion_instructions()`
5. **Template Application**: Uses `context_discussion_history_section_format` with bold headers
6. **Result**: Discussion history wrapped in `**=== DISCUSSION HISTORY ===**`

### Memory Update Flow

1. **Trigger**: Agent memory being updated after statement
2. **Entry Point**: `MemoryService.update_discussion_memory()` (line 234)
3. **Direct Inclusion**: `round_content = f"{discussion_history}\n\n"`
4. **Result**: Raw discussion history without any formatting headers

### Context Differentiation

The key differentiation happens in `ParticipantAgent._generate_dynamic_instructions()`:

```python
# Memory update path (line 235)
if context.role_description == "MemoryUpdate":
    return language_manager.format_memory_context(...)  # No discussion history

# Regular statement path (line 272)
phase_instructions = language_manager.format_phase2_discussion_instructions(
    discussion_history=getattr(context, 'discussion_history', '') or ''
)  # Includes bold formatted discussion history
```

## Current System Architecture

### LanguageManager Methods
- **`format_memory_context()`**: Used for memory updates, does NOT include discussion history
- **`format_phase2_discussion_instructions()`**: Used for statements, INCLUDES bold formatted discussion history
- **`format_context_info()`**: General context formatting that calls phase-specific instructions

### Service Responsibilities
- **DiscussionService**: Handles statement prompts but delegates history formatting to LanguageManager
- **MemoryService**: Directly includes discussion history in memory without formatting headers
- **ParticipantAgent**: Routes between different formatting paths based on context

## Impact Assessment

### User Experience
- **Inconsistency**: Same content appears differently in different contexts
- **Cognitive Load**: Bold formatting draws attention in statement context but not in memory
- **Expectation Mismatch**: User expects unified formatting across all contexts

### Technical Implications
- **No Functional Issues**: Both formatting approaches work correctly
- **Maintenance Complexity**: Two different formatting approaches to maintain
- **Translation Consistency**: Bold formatting patterns replicated across 3 languages

## Solution Requirements

Based on user request to match memory update formatting (no bold), the solution should:

1. **Remove Bold Headers**: Eliminate `**=== DISCUSSION HISTORY ===**` formatting
2. **Maintain Multilingual Support**: Update all 3 language files consistently
3. **Preserve Structure**: Keep discussion history clearly separated but without bold emphasis
4. **No Breaking Changes**: Ensure existing functionality continues to work
5. **Keep Simple**: Minimal change approach that addresses root cause

## Files Requiring Changes

### Translation Files (Primary Changes)
- `translations/english_prompts.json`
- `translations/spanish_prompts.json`
- `translations/mandarin_prompts.json`

### Key Location
- Template: `context_discussion_history_section_format`
- Current: `"**=== DISCUSSION HISTORY ===**\n{discussion_history}\n=========================="`
- Target: `"=== DISCUSSION HISTORY ===\n{discussion_history}\n=========================="`

## Implementation Complexity

**Complexity Level**: **Low**
- **Primary Change**: Remove bold markdown from 3 translation templates
- **No Code Logic Changes**: All formatting logic remains the same
- **No Architecture Changes**: Service boundaries and responsibilities unchanged
- **Risk Level**: Minimal - only affects visual presentation

## Testing Considerations

### Areas to Validate
1. **Visual Consistency**: Discussion history appears identical in both contexts
2. **Multilingual Support**: All 3 languages show consistent non-bold formatting
3. **Existing Functionality**: No regression in statement generation or memory updates
4. **Edge Cases**: Empty discussion history, truncated history still work correctly

### Test Approach
- **Unit Tests**: Verify template formatting produces expected output
- **Integration Tests**: Confirm end-to-end formatting consistency
- **Multilingual Tests**: Validate across English, Spanish, Mandarin

## Conclusion

This is a straightforward formatting inconsistency issue with a simple, targeted solution. The bold formatting was intentionally added to emphasize discussion history in statement contexts, but the user prefers the cleaner, non-bold approach used in memory updates. Removing the bold markdown from translation templates will achieve the desired unified formatting while maintaining all existing functionality.