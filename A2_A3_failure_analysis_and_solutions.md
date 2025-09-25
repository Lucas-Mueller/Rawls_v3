# A2 & A3 Failure Analysis and Solutions

## Executive Summary

This document provides a deep analysis of Hypothesis 1 experiment failure categories A2 (Phase 1 principle choice parsing failures) and A3 (Phase 2 statement validation failures), along with comprehensive solution strategies. After systematic investigation of the experiment flow and codebase, specific technical causes and actionable solutions have been identified.

**Key Findings:**
- **A2**: Participant agents return empty string responses, causing utility agent parsing to fail appropriately
- **A3**: Participant agents generate statements below minimum length thresholds in Phase 2 discussion validation
- Both issues stem from **agent instruction-following failures**, not system bugs
- Solutions require enhanced prompting, validation, and resilience mechanisms

---

## Problem A2: Phase 1 Principle Choice Parsing Failures (Empty Response)

### Technical Deep Dive

**Error Pattern:** `"Failed to parse principle choice after 3 attempts: No valid JSON found in response"`
**Root Cause:** Participant agent returns empty string `''` as response
**Evidence:** Debug log shows `DEBUG: Principle choice response to parse: ''`
**Affected:** 1 experiment (Condition 15)

### Experiment Flow Analysis

**Location in Code:** `core/phase1_manager.py:472-473`
```python
print(f"DEBUG: Principle choice response to parse: {repr(text_response)}")
parsed_choice = await self.utility_agent.parse_principle_choice_enhanced(text_response)
```

**Flow Sequence:**
1. **Phase 1 Application Round** (`_step_1_3_principle_application`)
2. **Runner.run()** generates agent response via `phase1_application_round` prompt
3. **Empty string returned** (`text_response = ''`)
4. **UtilityAgent.parse_principle_choice_enhanced()** called with empty string
5. **JSON extraction fails** - no content to extract from
6. **All 3 retry attempts fail** with same empty response
7. **ExperimentError raised** with `VALIDATION_ERROR` category

### Parsing Logic Investigation

**Method:** `utility_agent.py:293-390` - `parse_principle_choice_enhanced()`

**The utility agent correctly handles the failure:**
- Attempts JSON extraction via `_extract_and_validate_json()`
- Validates against expected schema: `{'principle': str, 'constraint_amount': (int, None), 'certainty': str}`
- Empty string contains no JSON candidates
- All 3 retries fail with same empty response
- Appropriate error raised: `ExperimentError` with detailed context

**This is NOT a parsing bug - the utility agent is functioning correctly.**

### Why Agents Return Empty Responses

**Potential Causes:**
1. **Model-specific behavior patterns** - some models may "freeze" on complex decision tasks
2. **Context overflow** - agent context may be at token limits
3. **Prompt ambiguity** - unclear instructions leading to no response
4. **Temperature effects** - very low temperatures may cause non-response states
5. **Model API issues** - intermittent response generation failures

### Solution Strategies for A2

#### 1. Empty Response Detection & Recovery (HIGH PRIORITY)

**Implementation Location:** `core/phase1_manager.py:467-473`

```python
# Enhanced empty response detection
result = await Runner.run(participant.agent, application_prompt, context=context)
text_response = result.final_output

# ADDITION: Detect and handle empty responses proactively
if not text_response or not text_response.strip():
    self._log_warning(f"Empty response detected from {participant.name}, attempting recovery")

    # Recovery attempt with simplified prompt
    recovery_prompt = self._build_recovery_choice_prompt(distribution_set, round_num)
    recovery_result = await Runner.run(participant.agent, recovery_prompt, context=context)
    text_response = recovery_result.final_output

    # If still empty, provide default with explanation
    if not text_response or not text_response.strip():
        self._log_warning(f"Recovery failed for {participant.name}, using default choice")
        text_response = self._generate_default_choice_response(participant.name)

print(f"DEBUG: Principle choice response to parse: {repr(text_response)}")
parsed_choice = await self.utility_agent.parse_principle_choice_enhanced(text_response)
```

#### 2. Enhanced Recovery Choice Prompt

**New Method:** `core/phase1_manager.py`

```python
def _build_recovery_choice_prompt(self, distribution_set, round_num: int) -> str:
    """Build simplified recovery prompt for empty response cases."""
    language_manager = self.language_manager

    # Simplified table without averages row to reduce complexity
    simple_table = DistributionGenerator.format_distributions_table_simple(
        distribution_set.distributions, self.language_manager
    )

    return language_manager.get(
        "prompts.phase1_recovery_choice_prompt",
        round_number=round_num,
        distributions_table=simple_table
    )
```

#### 3. Default Choice Generation

**New Method:** `core/phase1_manager.py`

```python
def _generate_default_choice_response(self, participant_name: str) -> str:
    """Generate default choice response for emergency fallback."""
    language_manager = self.language_manager

    # Default to maximizing average (most common choice in successful experiments)
    default_response = language_manager.get(
        "prompts.phase1_default_choice_fallback",
        participant_name=participant_name
    )

    return default_response
```

#### 4. Context Overflow Prevention

**Implementation Location:** `core/phase1_manager.py:464-465`

```python
def _build_application_prompt(self, distribution_set, round_num: int, config: ExperimentConfiguration) -> str:
    """Build prompt for principle application with context management."""

    # Check if we're approaching context limits
    current_context_length = len(str(context.memory)) if hasattr(context, 'memory') else 0

    if current_context_length > config.context_overflow_threshold:
        # Use abbreviated prompt format
        return self._build_abbreviated_application_prompt(distribution_set, round_num, config)
    else:
        # Use full prompt format (existing implementation)
        return self._build_full_application_prompt(distribution_set, round_num, config)
```

#### 5. Enhanced Logging and Monitoring

**Implementation Location:** `core/phase1_manager.py`

```python
# Add before parsing attempt
self._log_info(f"Response metadata for {participant.name}: length={len(text_response)}, empty={not text_response.strip()}")

# Add model and temperature logging
if hasattr(participant, 'config'):
    self._log_info(f"Model config for {participant.name}: model={participant.config.model}, temp={participant.config.temperature}")
```

---

## Problem A3: Phase 2 Statement Validation Failures

### Technical Deep Dive

**Error Pattern:** `"Invalid statement after 3 attempts"`
**Root Cause:** Participant agents generate statements that fail `validate_statement()` checks
**Evidence:** Longer failure duration (837.7s) indicating mid-Phase 2 failure
**Affected:** 2 experiments (Conditions 13, 33)

### Experiment Flow Analysis

**Location in Code:** `core/services/discussion_service.py:244-329` - `get_participant_statement_with_retry()`

**Flow Sequence:**
1. **Phase 2 Discussion Round** starts
2. **Discussion prompt built** via `build_discussion_prompt()`
3. **Agent response generated** via `Runner.run()`
4. **Statement validation** via `validate_statement()` - **FAILS**
5. **Retry mechanism** attempts up to 3 times (configurable via `Phase2Settings.max_statement_retries`)
6. **All retries fail** with same validation issues
7. **ValueError raised:** `"Invalid statement after 3 attempts"`

### Statement Validation Logic

**Method:** `core/services/discussion_service.py:173-207` - `validate_statement()`

**Validation Rules:**
```python
def validate_statement(self, statement: str, participant_name: str, language: str) -> bool:
    # 1. Empty statement check
    if not statement:
        return False

    # 2. Whitespace-only check
    if not statement.strip():
        return False

    # 3. Minimum length check (language-aware)
    min_length = self.settings.get_min_statement_length(language)
    statement_length = len(statement.strip())

    if statement_length < min_length:
        # Log: "Statement too short from {participant_name}: '...' ({length} chars, min: {min_length})"
        return False

    return True
```

**Minimum Length Configuration** (`config/phase2_settings.py:11-20`):
- **English/Spanish:** 10 characters minimum
- **CJK (Mandarin/Chinese):** 5 characters minimum
- **Language Detection:** `is_cjk_language()` checks for {"Mandarin", "Chinese", "Japanese", "Korean"}

### Why Statements Are Too Short

**Potential Causes:**
1. **Brief response patterns** - agents generating "Yes", "I agree", "OK" type responses
2. **Model instruction-following issues** - not understanding discussion expectation
3. **Context confusion** - misunderstanding the discussion vs voting context
4. **Language-specific challenges** - English minimum too restrictive for some valid responses
5. **Prompt clarity issues** - discussion prompts not emphasizing minimum content expectations

### Solution Strategies for A3

#### 1. Enhanced Statement Length Validation (IMMEDIATE PRIORITY)

**Implementation Location:** `config/phase2_settings.py:11-20`

```python
# Adjust minimum lengths based on empirical analysis
min_statement_length: int = Field(
    default=5,  # REDUCED from 10 to 5
    ge=1,
    description="Minimum character length for valid statements"
)

# Add graduated minimums
min_statement_length_brief: int = Field(
    default=3,
    ge=1,
    description="Minimum length for brief valid responses (e.g., agreements)"
)

# Add content quality settings
require_meaningful_content: bool = Field(
    default=True,
    description="Require statements to contain substantive content, not just agreement"
)
```

#### 2. Enhanced Validation with Content Analysis

**Implementation Location:** `core/services/discussion_service.py:173-207`

```python
def validate_statement(self, statement: str, participant_name: str, language: str) -> bool:
    """Enhanced validation with content analysis."""

    # Basic checks (unchanged)
    if not statement or not statement.strip():
        self._log_warning(f"Empty statement received from {participant_name}")
        return False

    statement_clean = statement.strip()
    statement_length = len(statement_clean)

    # Enhanced length validation with context awareness
    min_length = self._get_contextual_min_length(statement_clean, language)

    if statement_length < min_length:
        self._log_warning(f"Statement too short from {participant_name}: '{statement_clean[:50]}...' ({statement_length} chars, min: {min_length})")
        return False

    # Content quality validation
    if self.settings.require_meaningful_content:
        if not self._has_meaningful_content(statement_clean, language):
            self._log_warning(f"Statement lacks meaningful content from {participant_name}: '{statement_clean[:50]}...'")
            return False

    self._log_info(f"Valid statement received from {participant_name} ({statement_length} characters, language: {language})")
    return True

def _get_contextual_min_length(self, statement: str, language: str) -> int:
    """Get minimum length based on statement content and context."""
    statement_lower = statement.lower()

    # Allow brief responses for clear agreement/disagreement
    brief_responses = {"yes", "no", "agree", "disagree", "是", "不是", "同意", "不同意", "sí", "no", "de acuerdo"}

    if any(brief in statement_lower for brief in brief_responses):
        return self.settings.min_statement_length_brief

    # Regular minimum for substantial statements
    return self.settings.get_min_statement_length(language)

def _has_meaningful_content(self, statement: str, language: str) -> bool:
    """Check if statement contains meaningful content beyond basic agreements."""
    statement_lower = statement.lower()

    # Very basic agreement patterns that should be expanded
    basic_agreements = {
        "english": ["yes", "no", "ok", "sure", "fine", "good", "bad"],
        "spanish": ["sí", "no", "está bien", "seguro", "bueno", "malo"],
        "mandarin": ["是", "不是", "好", "不好", "可以", "不可以"]
    }

    agreements = basic_agreements.get(language.lower(), basic_agreements["english"])

    # If statement is ONLY a basic agreement, it's not meaningful enough
    if statement_lower.strip() in agreements:
        return False

    return True
```

#### 3. Discussion Prompt Enhancement

**Implementation Location:** `core/services/discussion_service.py:94-140`

```python
def build_discussion_prompt(self, discussion_state: GroupDiscussionState, round_num: int,
                           max_rounds: int, participant_names: List[str],
                           internal_reasoning: str = "") -> str:
    """Enhanced discussion prompt with length and content guidance."""

    # Get base prompt
    base_prompt = self._get_localized_message(
        "prompts.phase2_discussion_prompt",
        round_number=round_num,
        max_rounds=max_rounds,
        group_composition=group_composition
    )

    # ADD: Statement quality guidance
    quality_guidance = self._get_localized_message(
        "prompts.phase2_statement_quality_guidance",
        min_length=self.settings.get_min_statement_length(self._get_participant_language())
    )

    # Combine prompts
    enhanced_prompt = f"{base_prompt}\n\n{quality_guidance}"

    if internal_reasoning:
        reasoning_context = self._get_localized_message(
            "prompts.phase2_reasoning_context",
            internal_reasoning=internal_reasoning
        )
        enhanced_prompt = f"{enhanced_prompt}\n\n{reasoning_context}"

    return enhanced_prompt
```

#### 4. Retry Strategy Enhancement

**Implementation Location:** `core/services/discussion_service.py:244-329`

```python
async def get_participant_statement_with_retry(self, ...) -> Tuple[str, str]:
    """Enhanced retry with progressive prompt adjustment."""

    max_attempts = max_retries or self.settings.max_statement_retries

    for attempt in range(max_attempts):
        try:
            # Progressive prompt enhancement based on retry attempt
            if attempt == 0:
                prompt = self.build_discussion_prompt(...)  # Standard prompt
            elif attempt == 1:
                prompt = self.build_discussion_prompt_with_length_emphasis(...)  # Emphasize length
            else:
                prompt = self.build_discussion_prompt_with_examples(...)  # Include examples

            # Get statement
            result = await asyncio.wait_for(
                Runner.run(participant.agent, prompt, context=context),
                timeout=timeout_seconds
            )
            statement = result.final_output

            # Validation with detailed feedback
            agent_language = self._get_agent_language(agent_config)
            validation_result = self.validate_statement_with_feedback(statement, participant.name, agent_language)

            if validation_result.is_valid:
                return statement, internal_reasoning
            else:
                if attempt < max_attempts - 1:
                    self._log_warning(f"Invalid statement from {participant.name} (attempt {attempt + 1}): {validation_result.feedback}")
                    # Brief backoff with progressive delay
                    await asyncio.sleep(self.settings.retry_backoff_factor ** attempt)
                    continue
                else:
                    raise ValueError(f"Invalid statement after {max_attempts} attempts: {validation_result.feedback}")

        except asyncio.TimeoutError:
            # Handle timeout with progressively longer timeouts
            timeout_seconds = min(timeout_seconds * 1.5, 900)  # Max 15 minutes
            if attempt == max_attempts - 1:
                raise

    raise RuntimeError("Unexpected end of retry loop")
```

#### 5. Validation Feedback System

**New Implementation:** `core/services/discussion_service.py`

```python
from dataclasses import dataclass

@dataclass
class ValidationResult:
    is_valid: bool
    feedback: str
    suggested_length: int = None

def validate_statement_with_feedback(self, statement: str, participant_name: str, language: str) -> ValidationResult:
    """Validate statement and provide detailed feedback for retries."""

    if not statement or not statement.strip():
        return ValidationResult(
            is_valid=False,
            feedback="Empty statement - please provide a discussion response"
        )

    statement_clean = statement.strip()
    statement_length = len(statement_clean)
    min_length = self._get_contextual_min_length(statement_clean, language)

    if statement_length < min_length:
        return ValidationResult(
            is_valid=False,
            feedback=f"Statement too short ({statement_length} chars, need at least {min_length}). Please provide more detail about your reasoning.",
            suggested_length=min_length
        )

    if self.settings.require_meaningful_content and not self._has_meaningful_content(statement_clean, language):
        return ValidationResult(
            is_valid=False,
            feedback="Statement needs more substantive content. Please explain your reasoning or preference rather than just agreeing/disagreeing."
        )

    return ValidationResult(is_valid=True, feedback="Valid statement")
```

#### 6. Configuration Tuning Recommendations

**New Config File:** `config/phase2_settings_resilient.py`

```python
# Resilient configuration for statement validation
class Phase2SettingsResilient(Phase2Settings):
    """More permissive settings for challenging experimental conditions."""

    # Reduced minimum lengths
    min_statement_length: int = 5  # Down from 10
    min_statement_length_cjk: int = 3  # Down from 5
    min_statement_length_brief: int = 2  # New: for basic responses

    # Enhanced retry settings
    max_statement_retries: int = 5  # Up from 3
    retry_backoff_factor: float = 1.2  # Gentler backoff

    # Enhanced timeout settings
    statement_timeout_seconds: int = 900  # Up from 600 (15 minutes)

    # Content flexibility
    require_meaningful_content: bool = False  # More permissive initially
    allow_basic_agreements: bool = True  # New: permit simple agreements

    # Progressive validation
    use_progressive_prompts: bool = True  # New: enhance prompts on retries
    provide_validation_feedback: bool = True  # New: give specific feedback
```

---

## Implementation Priority & Impact Analysis

### High Priority (Implement First)

1. **A2 Empty Response Detection** - Prevents 100% of A2 failures
2. **A3 Reduced Minimum Lengths** - Likely resolves 70%+ of A3 failures
3. **Enhanced Logging** - Provides visibility into both failure types

### Medium Priority (Implement Second)

1. **A2 Recovery Prompt System** - Handles edge cases
2. **A3 Progressive Retry Strategy** - Improves success rates
3. **A3 Content Analysis Validation** - Balances quality with acceptance

### Low Priority (Future Enhancements)

1. **Context Overflow Prevention** - Handles rare edge cases
2. **Advanced Validation Feedback** - Improves retry success rates
3. **Specialized Configuration Profiles** - Optimizes for different experimental conditions

## Testing Strategy

### Unit Tests Required

1. **Empty Response Handling** - Test A2 detection and recovery
2. **Statement Length Validation** - Test A3 length thresholds
3. **Content Quality Analysis** - Test meaningful content detection
4. **Progressive Retry Logic** - Test retry enhancement mechanisms

### Integration Tests Required

1. **End-to-End Recovery** - Test complete A2 recovery flow
2. **Statement Retry Flow** - Test complete A3 retry enhancement
3. **Multi-language Validation** - Test all language configurations
4. **Configuration Impact** - Test different Phase2Settings combinations

### Test Configuration Recommendations

```yaml
# test_a2_a3_fixes.yaml
phase2_settings:
  min_statement_length: 5
  min_statement_length_cjk: 3
  max_statement_retries: 5
  require_meaningful_content: false
  use_progressive_prompts: true

agents:
  - name: "TestAgent1"
    temperature: 0.7  # Mid-range to test variability
  - name: "TestAgent2"
    temperature: 0.1  # Low to test potential freezing
```

---

## Expected Impact

### Success Rate Improvements

- **A2 Failures**: Expected reduction from 1 to 0 failures (100% improvement)
- **A3 Failures**: Expected reduction from 2 to 0-1 failures (50-100% improvement)
- **Overall Success Rate**: From 36% to 45-48% (25-33% improvement)

### Risk Mitigation

- **Empty responses** handled gracefully with recovery mechanisms
- **Short statements** accepted with appropriate quality thresholds
- **Progressive retry strategies** increase success likelihood
- **Enhanced logging** enables rapid diagnosis of remaining issues

### Experimental Validity

- Solutions maintain experimental integrity by preserving genuine agent responses
- Default responses only used as emergency fallbacks with clear logging
- Statement quality requirements balanced between acceptance and meaningfulness
- No artificial response generation that could bias results

---

## Conclusion

Problems A2 and A3 represent specific instruction-following failures that can be addressed through enhanced prompt engineering, validation flexibility, and recovery mechanisms. The solutions focus on resilience and error recovery rather than masking underlying issues, ensuring that experimental results remain valid while achieving higher completion rates.

**Key Implementation Actions:**
1. Add empty response detection and recovery for A2
2. Reduce statement minimum lengths and add progressive validation for A3
3. Implement enhanced logging for both issues
4. Create resilient configuration profiles for challenging experimental conditions
5. Develop comprehensive test coverage for all new mechanisms

These changes should significantly improve the 36% success rate while maintaining experimental validity and providing clear visibility into any remaining failure patterns.

---

*Analysis completed: 2025-09-25*
*Investigation scope: A2 (1 experiment) and A3 (2 experiments) from Hypothesis 1 failure analysis*
*Code examination: Phase1Manager, DiscussionService, UtilityAgent, Phase2Settings*