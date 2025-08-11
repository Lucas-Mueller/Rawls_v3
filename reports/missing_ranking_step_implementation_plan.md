# Missing Ranking Step Implementation Plan

## Issue Identified

The current Phase 1 implementation is missing a critical ranking step that should occur after the detailed explanation (step 1.2) but before the repeated applications (step 1.3).

## Current Phase 1 Flow (Incorrect)
1. **Step 1.1**: Initial principle ranking
2. **Step 1.2**: Detailed explanation of principles applied to distributions  
3. **Step 1.3**: Repeated application (4 rounds) ← **Missing ranking step here**
4. **Step 1.4**: Final ranking

## Required Phase 1 Flow (Per Master Plan)
1. **Step 1.1**: Initial principle ranking
2. **Step 1.2**: Detailed explanation of principles applied to distributions
3. **Step 1.2b**: **Post-explanation ranking** ← **MISSING STEP**
4. **Step 1.3**: Repeated application (4 rounds)
5. **Step 1.4**: Final ranking

## Implementation Plan

### 1. Add New Step Method
Add `_step_1_2b_post_explanation_ranking()` method to `Phase1Manager` class in `/core/phase1_manager.py`:

```python
async def _step_1_2b_post_explanation_ranking(
    self,
    participant: ParticipantAgent,
    context: ParticipantContext,
    agent_config: AgentConfiguration
) -> tuple[PrincipleRanking, str]:
    """Step 1.2b: Post-explanation principle ranking."""
    
    post_explanation_prompt = self._build_post_explanation_ranking_prompt()
    
    # Always use text responses, parse with enhanced utility agent
    result = await Runner.run(participant.agent, post_explanation_prompt, context=context)
    text_response = result.final_output
    
    # Parse using enhanced utility agent with retry logic
    parsed_ranking = await self.utility_agent.parse_principle_ranking_enhanced(text_response)
    
    # Create round content for memory
    round_content = f"""Prompt: {post_explanation_prompt}
Your Response: {text_response}
Your Post-Explanation Rankings: {parsed_ranking.dict() if hasattr(parsed_ranking, 'dict') else str(parsed_ranking)}
Outcome: Completed ranking after learning how principles apply to distributions."""
    
    return parsed_ranking, round_content
```

### 2. Add Prompt Builder Method
Add `_build_post_explanation_ranking_prompt()` method:

```python
def _build_post_explanation_ranking_prompt(self) -> str:
    """Build prompt for post-explanation ranking."""
    return """
After learning how each justice principle is applied to income distributions, please rank the four principles again from best (1) to worst (4):

1. **Maximizing the floor income**: Choose the distribution that maximizes the lowest income
2. **Maximizing the average income**: Choose the distribution that maximizes the average income  
3. **Maximizing the average income with a floor constraint**: Maximize average while ensuring minimum income
4. **Maximizing the average income with a range constraint**: Maximize average while limiting income gap

Consider:
- How each principle works in practice based on the examples you just studied
- Whether the detailed explanations changed your understanding
- Your preference for how income should be distributed

Indicate your overall certainty level for the entire ranking: very_unsure, unsure, no_opinion, sure, or very_sure.

Provide your ranking with reasoning, noting any changes from your initial ranking and why.
"""
```

### 3. Update Main Phase 1 Flow
Modify `_run_single_participant_phase1()` method to include the new step:

```python
# After step 1.2 detailed explanation:
context.memory = await MemoryManager.prompt_agent_for_memory_update(
    participant, context, explanation_content
)
context = update_participant_context(context, new_round=context.round_number)

# NEW STEP 1.2b: Post-explanation ranking
context.round_number = 0  # Reset to 0 for second ranking
post_explanation_ranking, post_ranking_content = await self._step_1_2b_post_explanation_ranking(
    participant, context, agent_config
)

# Update memory with agent
context.memory = await MemoryManager.prompt_agent_for_memory_update(
    participant, context, post_ranking_content
)
context = update_participant_context(context, new_round=context.round_number)

# Continue with step 1.3...
```

### 4. Update Data Models
Update `Phase1Results` in `/models/experiment_types.py` to include the new ranking:

```python
@dataclass
class Phase1Results:
    participant_name: str
    initial_ranking: PrincipleRanking
    post_explanation_ranking: PrincipleRanking  # NEW FIELD
    application_results: List[ApplicationResult]
    final_ranking: PrincipleRanking
    total_earnings: float
    final_memory_state: str
```

### 5. Update Return Statement
Modify the return statement in `_run_single_participant_phase1()`:

```python
return Phase1Results(
    participant_name=participant.name,
    initial_ranking=initial_ranking,
    post_explanation_ranking=post_explanation_ranking,  # NEW FIELD
    application_results=application_results,
    final_ranking=final_ranking,
    total_earnings=context.bank_balance,
    final_memory_state=context.memory
)
```

### 6. Round Numbering Strategy
- **Round -1**: Detailed explanation (learning step)
- **Round 0**: Both initial ranking (1.1) and post-explanation ranking (1.2b)
- **Rounds 1-4**: Repeated applications (1.3)
- **Round 5**: Final ranking (1.4)

### 7. Memory Management
- Agent memory will be updated after the post-explanation ranking
- Memory update should capture the ranking change and reasoning
- Full context preservation for subsequent Phase 1 steps

## Benefits of This Implementation

1. **Compliance**: Matches the master plan specification exactly
2. **Insight Generation**: Captures how detailed examples influence agent preferences
3. **Data Richness**: Provides three ranking points for analysis (initial, post-explanation, final)
4. **Memory Continuity**: Maintains agent memory consistency throughout Phase 1
5. **Minimal Disruption**: Clean integration with existing code structure

## Testing Requirements

1. Verify new ranking step executes in correct sequence
2. Confirm memory updates work properly
3. Test data model changes don't break existing functionality
4. Validate round numbering consistency
5. Ensure JSON output includes new ranking data

## Files to Modify

1. `/core/phase1_manager.py` - Add new step method and update flow
2. `/models/experiment_types.py` - Update Phase1Results dataclass
3. `/tests/unit/test_phase1_manager.py` - Add tests for new step
4. `/tests/integration/test_experiment_flow.py` - Update integration tests