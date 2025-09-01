# Simplified Memory System Optimization

## The Real Problems

**Current Issues:**
- **23+ expensive LLM calls per agent** for memory updates (5 in Phase 1, 18+ in Phase 2)
- **Full 2000+ character memory** shown in every agent context (competing with discussion history)
- **Verbose, repetitive agent memory** ("In round 1 I said..., In round 2 I said..., In round 3...")
- **Unnecessary updates** for simple factual events (vote confirmations, ballot choices)

**Agent Memory Examples - Current Problems:**
```
Current Verbose Memory:
"In my initial ranking, I placed maximizing floor income first because I believe in protecting the worst-off. Then I learned about how the principles actually work through examples. In round 1 of applications, I chose maximizing average because the numbers looked good, and I was assigned to medium class and earned $2.40. In round 2, I chose maximizing floor because I wanted to help the poor, and I was assigned to medium class again and earned $1.80. In round 3, I chose maximizing average with floor constraint with a constraint of $15,000 because I wanted to balance both goals, and I was assigned to high class and earned $3.20. In round 4..."

[This continues for 2000+ characters with similar repetitive patterns]
```

## Simple Solution: **Smart Memory Management**

### 1. **Memory Display Optimization** 
**Instead of:** Showing full 2000+ char memory in every context  
**Do:** Show condensed memory summary, full memory available when needed

**Current Context Display:**
```
=== YOUR MEMORY ===
[2000+ characters of verbose memory competing with prompt]
====================
```

**New Smart Display:**
```
=== MEMORY SUMMARY ===
Phase 1: Floor preference → Average+floor ($15k). Earned $9.60 total. Best: floor principle.
Phase 2 (Round 3): Supporting $18k floor constraint. Alice+Bob agree. Consensus building.
Key Insights: Moderate constraints work. Floor principle most reliable.
=== 

[Full memory available when specifically referenced or requested]
```

### 2. **Selective Memory Updates**
**Instead of:** 23+ memory updates per agent  
**Do:** Strategic updates for meaningful events only

**Skip Memory Updates For:**
- Vote initiation responses (1/0 choices) → Simple insertion: "Round 3: Chose to initiate voting"
- Ballot confirmations (1/0 choices) → Simple insertion: "Agreed to vote" 
- Simple ballot choices (1-4 selections) → Simple insertion: "Voted: Principle 3, $18k"

**Keep Full Memory Updates For:**
- Phase 1 principle applications (complex reasoning about choices and outcomes)
- Phase 2 discussion statements (strategic thinking about group dynamics)
- Phase changes (transition between phases with major context shifts)
- Final results (comprehensive outcome processing)

**Expected Reduction:** 23+ calls → 12-15 calls per agent (45% reduction)

### 3. **Better Memory Prompts**
**Instead of:** Generic "update your memory" prompts  
**Do:** Context-specific guidance that encourages concise, structured thinking

**Current Memory Prompt:**
```
Return your complete updated memory incorporating insights from recent activity. 
Include both important information from your previous memory and new learnings.

Your Previous Memory: [2000+ chars]
Recent Activity: [Round content]
```

**New Guided Memory Prompts:**

**For Phase 1 Applications:**
```
Update your memory with key insights from this principle application round.

Focus on:
- What did you learn about this principle's effectiveness?
- How did the outcome compare to your expectations?
- What would you do differently next time?

Keep your previous Phase 1 insights and add this round's learnings concisely.

Previous Memory: [memory]
This Round: [round content]

Return: Updated memory emphasizing insights over chronology.
```

**For Phase 2 Discussion:**
```
Update your memory with insights from this discussion round.

Focus on:
- How has the group dynamic evolved?
- What new information or arguments emerged?
- How is your position developing?

Maintain key Phase 1 learnings and group discussion insights.

Previous Memory: [memory]  
This Round: [round content]

Return: Updated memory focusing on strategic insights and group progress.
```

### 4. **Smart Memory Compression** 
**Instead of:** Emergency compression when hitting limits  
**Do:** Proactive, intelligent compression that preserves key insights

**Enhanced Compression Prompt:**
```
Your memory has grown long. Condense it while preserving essential insights.

Preserve:
✓ Key Phase 1 learnings about principle effectiveness  
✓ Your principle preference evolution and reasons
✓ Important group dynamics and consensus-building insights
✓ Strategic insights about constraint amounts and negotiation

Reduce:
- Redundant round-by-round chronology
- Repetitive statements about the same insights
- Excessive detail about routine events

Target: ~60% of current length while keeping all important insights.

Current Memory: [memory]
Return: Condensed memory preserving key insights
```

### 5. **Context-Aware Memory Display**

**Voting Context:**
```
=== MEMORY (VOTING FOCUS) ===
Phase 1 Best: Floor principle (earned most). Tried constraints: $15k, $20k floor.
Discussion: Group favors floor protection. Alice+Bob support $18k floor.
Voting History: Initiated voting in Round 2 (failed). Ready for consensus.
===
```

**Discussion Context:**
```
=== MEMORY (DISCUSSION FOCUS) ===  
Position: Support floor protection, flexible on amount ($15-20k range).
Group Status: Alice+Bob allied, Charlie prefers pure average. Building consensus.
Strategy: Moderate constraints more successful than extreme positions.
===
```

## Implementation Plan

### Phase 1: Memory Display Optimization (Week 1-2)

**1.1 Create Memory Summarizer**
```python
class MemorySummarizer:
    @staticmethod
    def create_summary(full_memory: str, context_type: str = "general") -> str:
        """Create 3-4 line memory summary preserving key insights"""
        
    @staticmethod  
    def extract_key_insights(full_memory: str) -> List[str]:
        """Extract 2-3 most important strategic insights"""
```

**1.2 Update Context Display**
- Modify `language_manager.format_memory_section()` to use summary by default
- Add configuration flag: `show_full_memory_in_context: false`
- Keep full memory available for specific prompts that need it

**1.3 Add Context-Aware Summaries**
- Voting context: Emphasize Phase 1 constraint experience, voting history
- Discussion context: Emphasize strategic insights, group dynamics
- Application context: Emphasize principle performance learnings

### Phase 2: Selective Memory Updates (Week 3-4)

**2.1 Identify Update-Skip Events**
```python
# Skip full memory updates for these - use simple insertion instead:
SIMPLE_MEMORY_EVENTS = [
    "vote_initiation_response",  # 1/0 choice
    "voting_confirmation",       # 1/0 choice  
    "ballot_selection",          # 1-4 choice
    "amount_specification"       # Dollar amount
]

# Keep full memory updates for:
COMPLEX_MEMORY_EVENTS = [
    "principle_application",     # Complex reasoning about choices
    "discussion_statement",      # Strategic group thinking
    "phase_transition",          # Major context changes
    "final_results"             # Comprehensive outcomes
]
```

**2.2 Implement Event Classification**
- Add event type detection in Phase2Manager
- Route to appropriate memory update method
- Track memory update frequency for optimization

### Phase 3: Enhanced Memory Prompts (Week 3-4)

**3.1 Context-Specific Prompts**
- Phase 1 application prompts: Focus on principle effectiveness learnings
- Phase 2 discussion prompts: Focus on strategic insights and group dynamics  
- Compression prompts: Better guidance on what to preserve vs. reduce

**3.2 Memory Guidance Integration**
- Enhance existing `memory_guidance_style` to include prompt specificity
- Add template system for different memory update contexts
- Maintain agent autonomy while providing better structure

### Phase 4: Smart Compression (Week 5-6)

**4.1 Proactive Compression Triggers**
- Trigger compression at 70% of limit instead of 80%
- Better compression prompts that preserve insights over chronology
- Validation that key information is preserved

**4.2 Compression Quality Measurement**
- Track compression effectiveness (tokens saved vs. information preserved)
- A/B test different compression strategies
- Rollback capability if compression degrades agent performance

## Expected Results

### Performance Improvements
- **45% reduction** in memory update LLM calls (23+ → 12-15 per agent)
- **60% reduction** in context token usage for memory display
- **30% reduction** in total memory-related API costs
- **Faster experiment execution** with fewer memory bottlenecks

### Quality Preservation  
- **Maintain full agent control** over memory content and insights
- **Preserve key Phase 1 learnings** about principle effectiveness 
- **Maintain understanding** of discussion history and group dynamics
- **Better focus** on strategic insights vs. chronological repetition

### Information Density Improvements
- **Higher insight-to-token ratio** in memory content
- **Context-appropriate information** shown when needed
- **Reduced redundancy** while preserving comprehensiveness
- **Better agent decision-making** with cleaner, focused memory

## Configuration Options

```yaml
memory_optimization:
  # Display settings
  show_memory_summary_in_context: true    # Use summary instead of full memory
  summary_length: "3-4 lines"             # Target summary length
  context_aware_summaries: true           # Different summaries for voting/discussion
  
  # Update frequency  
  selective_updates: true                  # Skip updates for simple events
  batch_simple_events: true               # Batch multiple simple events
  update_threshold: "meaningful_only"     # Only update for meaningful events
  
  # Compression settings
  proactive_compression_trigger: 0.7      # Compress at 70% of limit
  compression_target: 0.6                 # Target 60% of limit after compression
  preserve_insights_over_chronology: true # Prioritize insights in compression
  
  # Backwards compatibility
  fallback_to_full_memory: true          # Fallback if summary fails
  legacy_mode_available: true            # Option to use old system
```

## Risk Mitigation

**Information Loss Prevention:**
- Gradual rollout with A/B testing against current system
- Full memory always available, just not shown by default
- Rollback capability if agent performance degrades

**Agent Experience Protection:**
- Agents still control their memory content completely
- Enhanced prompts guide but don't constrain agent thinking
- Memory summaries preserve agent insights, just more concisely

**System Reliability:**
- Simple changes to existing system, not a complete rebuild
- Configuration flags to disable optimizations if needed  
- Extensive testing of memory summary accuracy before deployment

## Success Metrics

**Primary Goals:**
- 40-50% reduction in memory-related LLM calls
- 50-60% reduction in context token usage for memory
- Maintain agent decision quality (measured by experimental outcomes)
- Preserve agent understanding scores (measured by post-experiment surveys)

**Quality Validation:**
- Agent decisions remain consistent with full memory system
- Key Phase 1 insights preserved in Phase 2 decision-making
- Discussion quality maintained with summarized memory context
- No degradation in consensus-building or voting accuracy

This approach keeps agents in control of their memory while making the system much more efficient through smarter display and selective updates.