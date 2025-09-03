# Complete Principle Information Redundancy Analysis

## Problem Statement

Agents are receiving principle information **3 times total** (not just 2), creating excessive redundancy and context bloat. The user's requirement is: "if we just give them this in the input prompt... Its enough"

## Current Sources of Principle Information

### 1. **SYSTEM CONTEXT - Phase Instructions** ⚠️ MAJOR SOURCE
Located in translation files, specifically in these phase instruction prompts:

#### Phase 1 Round 0 (`phase1_round0_initial_ranking`)
```
The Four Justice Principles:
{principle_list_detailed}
```
- Uses `{principle_list_detailed}` template
- Called via `get_phase1_instructions(0)` → `language_manager.get("prompts.phase1_round0_initial_ranking")`
- Injected through `utils/language_manager.py` lines 147-153 where `{principle_list_detailed}` gets replaced with full principle descriptions

#### Phase 1 Application Rounds (`phase1_rounds1_4_principle_application`)
```
Choose from these four justice principles:
{principle_list_simple}
```
- Uses `{principle_list_simple}` template  
- Called for rounds 1-4 via `get_phase1_instructions(1-4)`

#### Phase 1 Final Ranking (`phase1_round5_final_ranking`)
- Contains **hardcoded** full principle descriptions with detailed explanations
- No template substitution - directly embedded in translation file
- This is the most verbose principle information source

#### Phase 2 Discussion (`phase2_discussion_prompt`)
```
The Four Justice Principles:
**Maximizing the floor income**: [detailed description]
**Maximizing the average income**: [detailed description]
**Maximizing the average income with a floor constraint**: [detailed description]  
**Maximizing the average income with a range constraint**: [detailed description]
```
- Contains **hardcoded** full principle descriptions
- Called via `get_phase2_instructions()` → `language_manager.get("prompts.phase2_discussion_prompt")`

### 2. **INPUT PROMPTS** ⚠️ RECENTLY ADDED
Through the new `unified_ranking_prompt_template` in CounterfactualsService:
- Contains detailed principle descriptions
- Added as part of the recent ranking optimization
- This is what the user intended to be the ONLY source

### 3. **LEGACY SOURCES** (May still exist)
- Memory content with principle information from previous rounds
- Any remaining template substitutions in other prompt locations

## Technical Implementation Details

### Template Substitution Mechanism
In `utils/language_manager.py` lines 147-153:
```python
if "{principle_list_detailed}" in current:
    format_kwargs["principle_list_detailed"] = self.get_principle_list_formatted("detailed")
if "{principle_list_simple}" in current:
    format_kwargs["principle_list_simple"] = self.get_principle_list_formatted("simple")
if "{principle_list_letters}" in current:
    format_kwargs["principle_list_letters"] = self.get_principle_list_formatted("names_only")
```

### System Context Construction Flow
1. `participant_agent.py` → `_generate_dynamic_instructions()`
2. → `_get_phase_specific_instructions_translated()`  
3. → `language_manager.get_phase1_instructions()` or `get_phase2_instructions()`
4. → `language_manager.get()` with template substitution
5. → Template replacement via lines 147-153
6. → Final system context via `format_context_info()`

## Files Requiring Modification

### High Priority - Remove Principle Information
1. **`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/english_prompts.json`**
   - Remove `{principle_list_detailed}` from `phase1_round0_initial_ranking`
   - Remove `{principle_list_simple}` from `phase1_rounds1_4_principle_application`  
   - Remove hardcoded principles from `phase1_round5_final_ranking`
   - Remove hardcoded principles from `phase2_discussion_prompt`

2. **`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/spanish_prompts.json`**
   - Same changes for Spanish translations

3. **`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/mandarin_prompts.json`**
   - Same changes for Mandarin translations

### Medium Priority - Cleanup Template System
4. **`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/utils/language_manager.py`**
   - Lines 147-153: Remove template substitution logic (or make conditional)
   - `get_principle_list_formatted()` method can remain for input prompts
   - Consider feature flag for gradual rollout

## Recommended Implementation Strategy

### Phase 1: Remove System Context Sources
1. **Update Phase 1 Round 0** - Remove principle list entirely
   - Change from learning + ranking to pure ranking
   - Agents will learn principles through input prompts only

2. **Update Phase 1 Application Rounds** - Remove principle list
   - Instructions focus on task mechanics only
   - Principle information comes via input prompts

3. **Update Phase 1 Final Ranking** - Remove hardcoded principles
   - Generic "rank the principles" instruction
   - Principles provided in input prompt

4. **Update Phase 2 Discussion** - Remove hardcoded principles  
   - Focus on discussion mechanics and voting process
   - Principle information comes via input prompts

### Phase 2: Validation
1. Test that agents still receive principle information via input prompts
2. Verify no functionality breaks
3. Confirm ranking prompts work correctly
4. Test across all languages (English, Spanish, Mandarin)

## Expected Outcome

After implementation:
- **System Context**: No principle information (clean context focused on mechanics)
- **Input Prompts**: Complete principle information (single source of truth)
- **Memory**: Principle information from prior rounds only (not system-injected)

This achieves the user's goal: "if we just give them this in the input prompt... Its enough"

## Risk Assessment

### Low Risk
- Phase instructions contain mostly task mechanics
- Core functionality preserved through input prompts
- Gradual rollout possible via feature flags

### Mitigation Strategies
- Keep backup of original translation files
- Implement feature flag for rollback capability
- Test thoroughly with sample conversations
- Validate across all language variants

## Implementation Priority

1. **Critical**: English translation file updates
2. **High**: Spanish and Mandarin translation file updates  
3. **Medium**: Template substitution cleanup in language_manager.py
4. **Low**: Remove unused `get_principle_list_formatted()` calls if any remain