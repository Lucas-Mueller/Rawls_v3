# Implementation Plan: Making Agent Reasoning Available During Voting Decisions

## Issue Summary

Currently, agents do NOT have access to their current round's internal reasoning when making vote initiation decisions. They only see their recent public statement, accumulated memory, and discussion history. This creates an inconsistency where agents have reasoning available for statement generation but not for the crucial voting decision that follows.

**Current Flow:**
1. Agent generates reasoning → public statement (reasoning available)
2. Agent asked about vote initiation (reasoning NOT available) ← **NEEDS TO CHANGE**

## Root Cause Analysis

The issue stems from the services-first architecture where:

1. **DiscussionService** generates and uses reasoning for statement creation via `get_participant_statement_with_retry()` method
2. **VotingService** prompts for vote initiation via `prompt_for_vote_initiation()` method without any reasoning context
3. **No reasoning flow** between the two services - reasoning is generated, used for statements, but not passed to voting

The reasoning is "lost" between statement generation and voting because:
- `Phase2Manager._process_participant_statement()` receives `internal_reasoning` from DiscussionService
- `Phase2Manager._attempt_end_of_round_voting()` calls VotingService without passing reasoning
- VotingService has no access to the reasoning that was just generated

## Affected Components

### Core Files to Modify:
1. **`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/services/voting_service.py`** - Add reasoning parameter to vote prompts
2. **`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/phase2_manager.py`** - Pass reasoning from statement to voting flow
3. **`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/english_prompts.json`** - Add new prompt template
4. **`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/spanish_prompts.json`** - Add new prompt template
5. **`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/mandarin_prompts.json`** - Add new prompt template

### Components to Understand (No Changes):
- **`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/services/discussion_service.py`** - How reasoning is currently generated
- **`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/config/phase2_settings.py`** - Existing reasoning settings

## Implementation Strategy

### Step 1: Enhance VotingService to Accept Reasoning

**File:** `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/services/voting_service.py`

**Changes to `prompt_for_vote_initiation()` method (lines 94-204):**

1. **Add reasoning parameter:**
   ```python
   async def prompt_for_vote_initiation(
       self,
       participant: ParticipantAgent,
       context: ParticipantContext,
       agent_recent_statement: Optional[str] = None,
       internal_reasoning: Optional[str] = None,  # NEW PARAMETER
       max_retries: int = 3
   ) -> bool:
   ```

2. **Modify prompt selection logic (lines 115-122):**
   ```python
   # Use enhanced prompt with reasoning and statement context if available
   if internal_reasoning and internal_reasoning.strip():
       if agent_recent_statement and agent_recent_statement.strip():
           vote_prompt = language_manager.get(
               "prompts.vote_initiation_with_reasoning_and_statement_prompt",
               agent_recent_statement=agent_recent_statement,
               internal_reasoning=internal_reasoning
           )
       else:
           vote_prompt = language_manager.get(
               "prompts.vote_initiation_with_reasoning_prompt",
               internal_reasoning=internal_reasoning
           )
   elif agent_recent_statement and agent_recent_statement.strip():
       vote_prompt = language_manager.get(
           "prompts.vote_initiation_with_statement_prompt",
           agent_recent_statement=agent_recent_statement
       )
   else:
       vote_prompt = language_manager.get("prompts.vote_initiation_prompt")
   ```

**Changes to `conduct_voting_process()` method (lines 476-544):**

3. **Add reasoning parameter:**
   ```python
   async def conduct_voting_process(
       self,
       participants: List[ParticipantAgent],
       initiating_participant: ParticipantAgent,
       contexts: List[ParticipantContext],
       discussion_state: GroupDiscussionState,
       agent_recent_statement: Optional[str],
       internal_reasoning: Optional[str],  # NEW PARAMETER
       error_handler,
       utility_agent
   ) -> bool:
   ```

4. **Pass reasoning to vote initiation (lines 512-517):**
   ```python
   wants_to_vote = await self.prompt_for_vote_initiation(
       participant=initiating_participant,
       context=initiating_context,
       agent_recent_statement=agent_recent_statement,
       internal_reasoning=internal_reasoning  # NEW ARGUMENT
   )
   ```

### Step 2: Update Phase2Manager to Pass Reasoning

**File:** `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/phase2_manager.py`

**Changes to `_attempt_end_of_round_voting()` method (lines 359-434):**

1. **Add reasoning parameter:**
   ```python
   async def _attempt_end_of_round_voting(
       self, round_num, contexts, participant_recent_statements, 
       participant_recent_reasoning,  # NEW PARAMETER
       discussion_state, process_logger
   ):
   ```

2. **Pass reasoning to VotingService (lines 394-402):**
   ```python
   consensus_reached = await self.voting_service.conduct_voting_process(
       participants=self.participants,
       initiating_participant=participant,
       contexts=contexts,
       discussion_state=discussion_state,
       agent_recent_statement=recent_statement,
       internal_reasoning=participant_recent_reasoning.get(participant.name, ""),  # NEW ARGUMENT
       error_handler=self.error_handler,
       utility_agent=self.utility_agent
   )
   ```

**Changes to `_run_group_discussion()` method (lines 436-556):**

3. **Track reasoning alongside statements:**
   ```python
   # Track recent statements and reasoning for vote consistency
   participant_recent_statements = {}
   participant_recent_reasoning = {}  # NEW TRACKING
   ```

4. **Store reasoning after statement processing (around line 492):**
   ```python
   # Store for vote consistency and track logging
   participant_recent_statements[participant.name] = statement
   participant_recent_reasoning[participant.name] = internal_reasoning  # NEW STORAGE
   ```

5. **Pass reasoning to voting attempt (around line 536):**
   ```python
   consensus_result = await self._attempt_end_of_round_voting(
       round_num, contexts, participant_recent_statements, 
       participant_recent_reasoning,  # NEW ARGUMENT
       discussion_state, process_logger
   )
   ```

### Step 3: Add New Translation Keys

**Files:** All translation files in `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/`

**New keys to add to prompts section:**

**English (`english_prompts.json`):**
```json
"vote_initiation_with_reasoning_prompt": "=== YOUR INTERNAL REASONING ===\n{internal_reasoning}\n================================\n\nBased on your internal reasoning above and the discussion so far, do you want to initiate formal voting on the justice principles now?\n\nPlease respond with:\n- 1 if you want to initiate voting now\n- 0 if you dont want to vote now\n\nYour response (1 or 0):",

"vote_initiation_with_reasoning_and_statement_prompt": "You just made this statement to the group:\n\"{agent_recent_statement}\"\n\n=== YOUR INTERNAL REASONING ===\n{internal_reasoning}\n================================\n\nBased on your internal reasoning and recent statement, do you want to initiate formal voting on the justice principles now?\n\nPlease respond with:\n- 1 if you want to initiate voting now\n- 0 if you dont want to vote now\n\nYour response (1 or 0):"
```

**Spanish (`spanish_prompts.json`):**
```json
"vote_initiation_with_reasoning_prompt": "=== SU RAZONAMIENTO INTERNO ===\n{internal_reasoning}\n================================\n\nBasándote en tu razonamiento interno arriba y la discusión hasta ahora, ¿quieres iniciar la votación formal sobre los principios de justicia ahora?\n\nPor favor responde con:\n- 1 si quieres iniciar la votación ahora\n- 0 si no quieres votar ahora\n\nTu respuesta (1 o 0):",

"vote_initiation_with_reasoning_and_statement_prompt": "Acabas de hacer esta declaración al grupo:\n\"{agent_recent_statement}\"\n\n=== SU RAZONAMIENTO INTERNO ===\n{internal_reasoning}\n================================\n\nBasándote en tu razonamiento interno y declaración reciente, ¿quieres iniciar la votación formal sobre los principios de justicia ahora?\n\nPor favor responde con:\n- 1 si quieres iniciar la votación ahora\n- 0 si no quieres votar ahora\n\nTu respuesta (1 o 0):"
```

**Mandarin (`mandarin_prompts.json`):**
```json
"vote_initiation_with_reasoning_prompt": "=== 您的内部推理 ===\n{internal_reasoning}\n================================\n\n根据您上述的内部推理和到目前为止的讨论，您想现在就正义原则开始正式投票吗？\n\n请回答：\n- 1 如果您想现在开始投票\n- 0 如果您现在不想投票\n\n您的回答（1或0）：",

"vote_initiation_with_reasoning_and_statement_prompt": "您刚刚向小组发表了这个声明：\n\"{agent_recent_statement}\"\n\n=== 您的内部推理 ===\n{internal_reasoning}\n================================\n\n根据您的内部推理和最近的声明，您想现在就正义原则开始正式投票吗？\n\n请回答：\n- 1 如果您想现在开始投票\n- 0 如果您现在不想投票\n\n您的回答（1或0）："
```

## Technical Considerations

### Reasoning vs Memory Distinction
- **Memory**: Accumulated long-term context across rounds (includes past reasoning if configured)
- **Current Reasoning**: Fresh reasoning generated specifically for the current round
- **Placement**: Reasoning should be inserted after memory but before the voting question, following the same pattern as statement prompts

### Prompt Structure Design
The new prompts follow the established pattern from `build_discussion_prompt()` in DiscussionService:
1. Context (recent statement if available)
2. Reasoning section (clearly marked with dividers)
3. Action prompt (voting decision)
4. Response format (numerical 1/0)

### Backward Compatibility
- All new parameters are optional with default values
- Existing behavior preserved when no reasoning is provided
- Configuration-driven: respects existing `reasoning_enabled` setting

### Memory Efficiency
- Reasoning is only passed to voting when it exists and is non-empty
- No additional memory storage - reasoning is ephemeral for the voting decision only
- Existing memory limits and character restrictions remain unchanged

## Risk Assessment

### Low Risk Areas:
- **Isolated Changes**: Modifications are contained within well-defined service boundaries
- **Optional Parameters**: All changes use optional parameters with safe defaults
- **Existing Patterns**: Following established prompting patterns from DiscussionService
- **Configuration Respect**: Honors existing `reasoning_enabled` settings

### Potential Complications:
1. **Translation Consistency**: New prompt keys must be added to all language files
2. **Prompt Length**: Combined reasoning + statement prompts might be longer
3. **Timeout Considerations**: Vote prompts with reasoning might need longer timeouts

### Mitigation Strategies:
1. **Comprehensive Translation**: Add keys to all three language files simultaneously
2. **Length Monitoring**: Log prompt lengths to ensure they stay within reasonable bounds
3. **Timeout Configuration**: Use existing `vote_prompt_timeout` configuration
4. **Graceful Fallback**: If reasoning is empty/invalid, fall back to existing prompts

## Testing Strategy

### Unit Tests
1. **VotingService Tests**: 
   - Test `prompt_for_vote_initiation()` with reasoning parameter
   - Verify correct prompt selection logic for all combinations
   - Test reasoning parameter propagation through `conduct_voting_process()`

2. **Phase2Manager Tests**:
   - Test reasoning tracking in `_run_group_discussion()`
   - Verify reasoning passed to `_attempt_end_of_round_voting()`
   - Test reasoning flow from statement generation to voting

### Integration Tests
1. **End-to-End Reasoning Flow**:
   - Generate reasoning → statement → voting with reasoning available
   - Verify agents can access their reasoning during voting decisions
   - Test across all three languages (English, Spanish, Mandarin)

2. **Configuration Testing**:
   - Test with `reasoning_enabled=True` (reasoning should be available)
   - Test with `reasoning_enabled=False` (should fall back to existing behavior)
   - Test mixed configurations across participants

### Validation Tests
1. **Prompt Structure Validation**:
   - Verify reasoning is inserted after memory in vote prompts
   - Confirm reasoning section uses proper formatting/dividers
   - Test prompt rendering with various reasoning content lengths

2. **Translation Validation**:
   - Verify all new keys exist in all language files
   - Test prompt generation in each language
   - Confirm proper character encoding for CJK languages

### Manual Testing
1. **Behavioral Validation**:
   - Run experiments and verify agents reference their reasoning in voting decisions
   - Compare voting behavior with/without reasoning access
   - Ensure reasoning content matches what was generated for statements

## Timeline Estimation

### Phase 1: Core Implementation (2-3 hours)
- [ ] Modify VotingService methods (1 hour)
- [ ] Update Phase2Manager reasoning flow (1 hour)
- [ ] Add translation keys to all language files (30 minutes)

### Phase 2: Testing & Validation (1-2 hours)
- [ ] Write unit tests for VotingService changes (30 minutes)
- [ ] Write integration tests for reasoning flow (30 minutes)
- [ ] Manual testing with sample experiments (30-60 minutes)

### Phase 3: Documentation & Cleanup (30 minutes)
- [ ] Update code comments and docstrings
- [ ] Verify all TODO items addressed
- [ ] Final review and testing

**Total Estimated Time: 3.5-5.5 hours**

## Dependencies

### Prerequisites:
- Understanding of existing reasoning generation in DiscussionService
- Familiarity with VotingService prompt selection logic
- Access to all translation files for multilingual support

### No Blocking Dependencies:
- Changes are self-contained within the voting system
- No database or configuration schema changes required
- No breaking changes to existing APIs

## Success Criteria

### Implementation Success:
1. **Reasoning Available**: Agents have access to their internal reasoning when making voting decisions
2. **Consistent Flow**: Reasoning flows seamlessly from statement generation to voting
3. **Multilingual Support**: All languages properly display reasoning in vote prompts
4. **Backward Compatibility**: Existing configurations and experiments work unchanged

### Behavioral Success:
1. **Agent Decision Quality**: Agents can reference their reasoning when deciding to vote
2. **Consistency**: Voting decisions align better with stated reasoning and positions
3. **No Regression**: All existing voting functionality remains intact
4. **Configuration Respect**: Reasoning integration respects existing settings

This implementation provides a clean, maintainable solution that enhances agent decision-making while preserving the existing services-first architecture and maintaining full backward compatibility.