# Memory Optimization Implementation Plan

## Problems We Are Fixing

The current memory system has four critical issues causing massive token waste and degraded performance:

### 1. **Repetitive Content Injection Every Turn**
- **What**: Full experiment explanations (400+ tokens) injected into EVERY turn, even round 15 of Phase 2
- **Where**: `ParticipantAgent._generate_dynamic_instructions()` calls `format_context_info()` every turn
- **Impact**: 400+ wasted tokens per turn × 20+ turns = 8,000+ unnecessary tokens per experiment

### 2. **Memory Stores Transcripts Instead of Insights**
- **What**: Agents store full prompts, distribution tables, and conversation transcripts in memory instead of strategic insights
- **Where**: Phase 1 `round_content` includes entire application prompts + full distribution tables, Phase 2 includes full discussion prompts
- **Impact**: Memory becomes a 10,000+ character transcript dump instead of actionable intelligence

### 3. **Duplicate Construction Waste in Phase 2**
- **What**: Phase 2 builds round content twice and discards the first version
- **Where**: `_get_participant_statement_with_retry()` returns round_content, then `_get_participant_statement_enhanced()` rebuilds it
- **Impact**: Double processing time and inconsistent content patterns

### 4. **Weak Memory Guidance Creates Bloat**
- **What**: Memory update prompt says "whatever you think is important" with no structure or focus
- **Where**: `memory_memory_update_prompt` in translations files
- **Impact**: Agents default to storing everything instead of extracting key strategic insights

## Solution: Replace the Old System Entirely

Remove all the inefficient patterns and replace them with optimized behavior by default:

- Experiment explanation only shown on first turn per phase
- Memory updates focus on insights, not transcripts  
- Round content becomes compact deltas
- Duplicate construction eliminated
- No configuration needed - this IS how the system works now

## ONE Set of Memory Prompts (English)

Replace the current `memory_memory_update_prompt` with this focused guidance:

```json
{
  "memory_memory_update_prompt": "Update your memory with the key insights from this round that will influence your future decisions. You will take this memory to the next rounds. 
  
  Refrain from conversation transcripts - these are saved separately in the logs. You will have access to them in the next rounds

  Similarliy you the instructions of the current rounds will be given to you in future rounds as well.
  "

  "memory_initial_prompt": "Use this memory space to track your evolving understanding of justice principles and strategic insights as you progress through the rounds. Keep it focused on learnings that will guide your future decisions.",
  
  "phase2_memory_context": "Phase 2: Group Discussion. Track the evolving group dynamics, key arguments from other participants, and how the discussion is influencing your position on justice principles."
}
```

## Implementation Plan

### Step 1: Update Memory Prompts  
- File: `translations/english_prompts.json`
- Replace current memory prompts with the focused versions above
- Update Spanish and Mandarin translations to match use Deepl MCP to translate

### Step 2: Gate Experiment Explanation
- File: `experiment_agents/participant_agent.py` 
- In `_generate_dynamic_instructions()`: Only include full explanation on first turn per phase
- Remove the repetitive context injection entirely from subsequent turns

### Step 3: Replace Round Content with Compact Deltas
- Files: `core/phase1_manager.py`, `core/phase2_manager.py`
- Replace verbose `round_content` with compact summaries
- Phase 1: "Round 3: Chose principle B (constraint: $40k), assigned middle class, earned $65k"
- Phase 2: "Round 2: Spoke 3rd, supported principle A, group still debating between A and C"
- Remove all full prompt/table injection into memory

### Step 4: Fix Phase 2 Duplicate Construction
- File: `core/phase2_manager.py`
- Remove duplicate round content building in `_get_participant_statement_enhanced()`
- Use single compact delta construction
- Remove redundant `continue` statements

### Step 5: Update Memory Manager
- File: `utils/memory_manager.py`
- Replace old unfocused memory prompts with new focused ones
- Remove any legacy prompt handling

## Expected Results

With the optimized memory system:
- **50-70% reduction in token usage** (eliminating 8,000+ redundant tokens per experiment)
- **Faster execution** (less content to process each turn)
- **Improved agent focus** (memory contains strategic insights, not noise)
- **Better decision quality** (agents can find relevant information in their memory)

## Testing Strategy

1. **Before/After Comparison**: Run identical experiments with current system, then with optimized system
2. **Token Counting**: Measure exact token reduction achieved
3. **Quality Validation**: Ensure agent decisions remain consistent or improve
4. **Integration Testing**: Verify all phases work correctly with new memory system

## Risk Mitigation

- **Comprehensive Testing**: Test all experiment configurations before full deployment
- **Quality Monitoring**: Track agent decision patterns for any degradation
- **Staged Implementation**: Implement changes incrementally and test each step

---

*This approach completely eliminates the token waste issues by removing inefficient patterns entirely and replacing them with optimized behavior.*