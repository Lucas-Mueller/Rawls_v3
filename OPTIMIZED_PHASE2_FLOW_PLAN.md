# Optimized Phase 2 Flow Implementation Plan

## Executive Summary

This plan implements **memory update optimization** while maintaining the current **end-of-round voting timing** for fairness. The key insight is distinguishing between factual updates (simple insertion) and complex reasoning (agent-mediated) while ensuring agents have access to their recent statements to maintain consistency.

## Core Principles

### 1. **Consistency Preservation** 🎯
**Critical Requirement**: Agents must have access to their latest statements when making voting decisions to prevent cognitive inconsistency.

**Bad Example:**
```
Agent A Round 3: "I think we've discussed enough. Let's move to voting now."
[Agent doesn't remember their own statement]
System: "Do you want to initiate voting?"
Agent A: "0" (No, continue discussion)
```

**Good Example (with this plan):**
```
Agent A Round 3: "I think we've discussed enough. Let's move to voting now."
[Agent's memory updated with their statement]
System: "Do you want to initiate voting?" + context includes recent statement
Agent A: "1" (Yes - consistent with their statement)
```

### 2. **Memory Update Efficiency** ⚡
- **Simple Insertion**: Factual decisions (33% fewer agent calls)
- **Agent-Mediated**: Complex reasoning and analysis
- **Multi-language Support**: All memory updates work in Spanish, Mandarin, English

### 3. **Straightforward Prompts** 🗣️
- Clear, direct language
- Numerical responses (1/0) for consistency
- No ambiguous phrasing

---

## Complete Flow Specification

### Phase 2 Round Structure (UNCHANGED TIMING)

```
Round N:
┌─ Agent A: Internal Reasoning (if enabled) → Statement → Memory Update
├─ Agent B: Internal Reasoning (if enabled) → Statement → Memory Update  
├─ Agent C: Internal Reasoning (if enabled) → Statement → Memory Update
└─ END OF ROUND VOTING PROMPTS
   ├─ Agent A: Vote Initiation Prompt (HAS ACCESS TO OWN STATEMENT)
   ├─ Agent B: Vote Initiation Prompt (HAS ACCESS TO OWN STATEMENT)
   └─ Agent C: Vote Initiation Prompt (HAS ACCESS TO OWN STATEMENT)

If Voting Initiated:
├─ Voting Initiation Memory Updates (Simple Insertion)
├─ Confirmation Phase (Simple Insertion Memory Updates)  
└─ Secret Ballot Phase (Mixed Memory Strategy)
```

## Detailed Implementation Plan

### Step 1: Enhanced Vote Initiation Prompts

**Current Issue**: Agents don't have access to their recent statement when deciding whether to vote.

**Solution**: Include agent's own statement in vote prompt context.

#### Multi-Language Vote Prompts

**English:**
```
"You just made this statement to the group:
'{agent_recent_statement}'

Based on your recent statement and the discussion so far, do you want to initiate formal voting on the justice principles now?

Please respond with:
- 1 if you want to initiate voting now
- 0 if you want to continue the discussion

Your response (1 or 0):"
```

**Spanish:**
```
"Acabas de hacer esta declaración al grupo:
'{agent_recent_statement}'

Basándote en tu declaración reciente y la discusión hasta ahora, ¿quieres iniciar la votación formal sobre los principios de justicia ahora?

Por favor responde con:
- 1 si quieres iniciar la votación ahora
- 0 si quieres continuar la discusión

Tu respuesta (1 o 0):"
```

**Mandarin:**
```
"你刚刚向小组发表了这个声明：
'{agent_recent_statement}'

根据你最近的声明和到目前为止的讨论，你想现在就正义原则开始正式投票吗？

请回答：
- 1 如果你想现在开始投票
- 0 如果你想继续讨论

你的回答（1或0）："
```

### Step 2: Memory Update Strategy Implementation

#### Strategy Matrix

| Update Type | Method | Justification | Multi-Language |
|-------------|--------|---------------|----------------|
| **Internal Reasoning** | None | Ephemeral thinking | N/A |
| **Discussion Statement** | Agent-Mediated | Complex reasoning about justice | ✅ Full support |
| **Vote Initiation Decision** | Simple Insertion | Factual choice | ✅ Template-based |
| **Confirmation Response** | Simple Insertion | Binary agreement | ✅ Template-based |
| **Secret Ballot Choice** | Simple Insertion | Vote selection | ✅ Template-based |
| **Final Results** | Agent-Mediated | Complex earnings analysis | ✅ Full support |

#### Simple Insertion Templates

**Vote Initiation Decision:**

*English:* `"Round {round_num}: I chose to {initiate_voting/continue_discussion}."`

*Spanish:* `"Ronda {round_num}: Elegí {iniciar_votación/continuar_discusión}."`

*Mandarin:* `"第{round_num}轮：我选择了{开始投票/继续讨论}。"`

**Confirmation Response:**

*English:* `"Voting confirmation: I {agreed_to/declined_to} participate in formal voting."`

*Spanish:* `"Confirmación de votación: {Acepté/Rechacé} participar en la votación formal."`

*Mandarin:* `"投票确认：我{同意了/拒绝了}参加正式投票。"`

**Secret Ballot Choice:**

*English:* `"Secret ballot: I voted for {principle_name}."`

*Spanish:* `"Voto secreto: Voté por {principle_name}."`

*Mandarin:* `"秘密投票：我投票支持{principle_name}。"`

### Step 3: Implementation Sequence

#### Phase 3.1: Vote Prompt Enhancement (High Priority)

**File**: `core/phase2_manager.py`

**Method**: `_prompt_for_vote_initiation()`

**Changes**:
1. Modify prompt to include agent's recent statement
2. Add multi-language template support
3. Ensure statement is available in context

```python
async def _prompt_for_vote_initiation_enhanced(
    self,
    participant: 'ParticipantAgent',
    context: ParticipantContext,
    agent_recent_statement: str,  # NEW PARAMETER
    max_retries: int = 3
) -> bool:
    """Enhanced vote initiation with statement context."""
    
    language_manager = self.language_manager
    
    # NEW: Include recent statement in prompt
    vote_prompt = language_manager.get(
        "prompts.vote_initiation_with_statement_prompt",
        agent_recent_statement=agent_recent_statement
    )
    
    # Rest of implementation remains the same...
```

#### Phase 3.2: Simple Memory Insertion System

**File**: `utils/simple_memory_manager.py` (NEW)

**Purpose**: Handle simple factual memory insertions without agent calls.

```python
class SimpleMemoryManager:
    """Handles simple factual memory insertions."""
    
    @staticmethod
    def insert_vote_initiation_decision(
        context: ParticipantContext,
        round_num: int,
        wants_vote: bool,
        language_manager
    ) -> None:
        """Insert vote initiation decision into memory."""
        
        template_key = "memory_insertions.vote_initiation_decision"
        decision_text = "initiate_voting" if wants_vote else "continue_discussion"
        
        memory_addition = language_manager.get(
            template_key,
            round_num=round_num,
            decision=language_manager.get(f"memory_insertions.{decision_text}")
        )
        
        context.memory += f"\n{memory_addition}"
    
    # Similar methods for confirmation and ballot choices...
```

#### Phase 3.3: Multi-Language Template Addition

**Files**: 
- `translations/english_prompts.json`
- `translations/spanish_prompts.json` 
- `translations/mandarin_prompts.json`

**New Entries**:

```json
{
  "prompts": {
    "vote_initiation_with_statement_prompt": "[language-specific template from above]"
  },
  "memory_insertions": {
    "vote_initiation_decision": "[language-specific template from above]",
    "confirmation_response": "[language-specific template from above]",
    "secret_ballot_choice": "[language-specific template from above]",
    "initiate_voting": "[initiate voting/iniciar votación/开始投票]",
    "continue_discussion": "[continue discussion/continuar discusión/继续讨论]",
    "agreed_to": "[agreed to/acepté/同意了]",
    "declined_to": "[declined to/rechacé/拒绝了]"
  }
}
```

### Step 4: Integration Points

#### In `_run_group_discussion()`:

```python
# After agent makes statement
statement, internal_reasoning, tool_call_info = await self._get_participant_statement_enhanced(...)

# Store recent statement for vote prompting
participant_recent_statements[participant.name] = statement

# Update memory (agent-mediated - KEEP CURRENT)
context.memory = await MemoryManager.prompt_agent_for_memory_update(...)

# End-of-round voting with statement access
for participant_idx, participant in enumerate(self.participants):
    recent_statement = participant_recent_statements[participant.name]
    wants_vote = await self._prompt_for_vote_initiation_enhanced(
        participant, contexts[participant_idx], recent_statement
    )
    
    # Simple memory insertion (NEW)
    SimpleMemoryManager.insert_vote_initiation_decision(
        contexts[participant_idx], round_num, wants_vote, self.language_manager
    )
```

#### In Confirmation Phase:

```python
# Replace current agent-mediated memory update:
context.memory = await MemoryManager.prompt_agent_for_memory_update(
    participant, context, confirmation_content, ...
)

# With simple insertion:
SimpleMemoryManager.insert_confirmation_response(
    context, agrees_to_vote, self.language_manager
)
```

## Expected Benefits

### Performance Improvements
- **33% reduction** in memory-related agent calls
- **Faster execution** for voting sequences
- **Reduced API costs** for simple decisions

### Quality Improvements  
- **Consistency prevention**: Agents can't contradict their recent statements
- **Better decision context**: Vote decisions made with full statement awareness
- **Maintained reasoning quality**: Complex analysis still uses agent-mediated updates

### Multi-Language Support
- **Template-based consistency** across languages
- **Cultural appropriateness** in prompt formulation
- **Numerical response consistency** (1/0 works in all languages)

## Risk Mitigation

### Consistency Validation
- **Unit tests** to ensure agents remember their statements during vote prompts
- **Integration tests** for multi-language template rendering
- **Validation** that simple insertions maintain memory coherence

### Rollback Plan
- **Gradual implementation**: Start with vote initiation prompts only
- **A/B comparison**: Run parallel experiments to validate performance
- **Easy reversion**: Keep current system intact until fully validated

## Success Metrics

1. **Consistency Score**: % of agents whose vote decisions align with their recent statements
2. **Performance Gain**: Reduction in total agent calls per experiment
3. **Memory Coherence**: Agent memory quality maintained across languages
4. **Experimental Validity**: No reduction in research data quality

---

## Implementation Timeline

**Week 1**: Vote prompt enhancement + multi-language templates
**Week 2**: Simple memory insertion system + integration
**Week 3**: Testing and validation across all languages
**Week 4**: Performance measurement and optimization

**Target**: 33% reduction in memory-related agent calls with improved decision consistency.