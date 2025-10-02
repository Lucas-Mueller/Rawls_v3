# Voting Confirmation Error Handling - Solution Proposals

## Overview

This document presents solution architectures for fixing the voting confirmation error handling issue identified in `voting_confirmation_error_handling_diagnosis.md`.

---

## Solution Architecture Options

### Option 1: Minimal Retry Logic (RECOMMENDED FOR QUICK FIX)

**Approach:** Add simple retry loop matching the vote initiation pattern

**Changes Required:**
1. Add retry loop around `Runner.run()` call in `conduct_confirmation_phase()`
2. Use existing `max_retries=3` pattern from `prompt_for_vote_initiation()`
3. Add `asyncio.sleep()` backoff between retries
4. Keep default to "Declined" only after all retries exhausted

**Implementation Complexity:** LOW
**Testing Effort:** LOW
**Risk:** LOW (mirrors existing proven pattern)

**Pseudocode:**
```python
async def conduct_confirmation_phase(...):
    max_retries = 3

    for participant in non_initiating_participants:
        for attempt in range(max_retries):
            try:
                result = await asyncio.wait_for(
                    Runner.run(participant.agent, confirmation_prompt, context=context),
                    timeout=confirmation_timeout
                )
                # Process successful response
                break  # Success, exit retry loop

            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))  # Linear backoff
                    continue
                else:
                    # Final timeout - record as declined

            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
                else:
                    # Final error - record as declined
```

**Pros:**
- ✅ Quick to implement
- ✅ Mirrors existing vote initiation logic
- ✅ Low risk of breaking existing behavior
- ✅ Solves most transient error cases

**Cons:**
- ❌ No error classification (retries all errors equally)
- ❌ Fixed retry count (not configurable)
- ❌ Linear backoff may be suboptimal

---

### Option 2: Configurable Retry with Error Classification (RECOMMENDED FOR PRODUCTION)

**Approach:** Add intelligent retry logic with error classification and configuration

**Changes Required:**
1. Add `max_confirmation_retries` to `Phase2Settings`
2. Classify errors as transient vs permanent
3. Only retry transient errors (API rate limits, network issues, timeouts)
4. Use exponential backoff with `retry_backoff_factor`
5. Log error types for debugging

**Implementation Complexity:** MEDIUM
**Testing Effort:** MEDIUM
**Risk:** MEDIUM (requires error classification logic)

**New Phase2Settings Fields:**
```python
class Phase2Settings(BaseModel):
    # ... existing fields ...

    max_confirmation_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for confirmation responses"
    )

    confirmation_retry_backoff_seconds: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Initial backoff delay for confirmation retries"
    )
```

**Error Classification:**
```python
def is_transient_error(exception: Exception) -> bool:
    """Classify errors as transient (retriable) vs permanent."""
    transient_indicators = [
        "rate limit",
        "timeout",
        "connection",
        "temporarily unavailable",
        "503",
        "429",
        "network"
    ]
    error_str = str(exception).lower()
    return any(indicator in error_str for indicator in transient_indicators)
```

**Enhanced Implementation:**
```python
async def conduct_confirmation_phase(...):
    max_retries = self.settings.max_confirmation_retries
    base_backoff = self.settings.confirmation_retry_backoff_seconds
    backoff_factor = self.settings.retry_backoff_factor

    for participant in non_initiating_participants:
        for attempt in range(max_retries):
            try:
                result = await asyncio.wait_for(
                    Runner.run(participant.agent, confirmation_prompt, context=context),
                    timeout=confirmation_timeout
                )
                # Success
                break

            except asyncio.TimeoutError as e:
                self._log_warning(f"Timeout on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    backoff = base_backoff * (backoff_factor ** attempt)
                    await asyncio.sleep(backoff)
                    continue
                else:
                    # Record as declined after all retries

            except Exception as e:
                # Classify error
                is_transient = self._is_transient_error(e)
                self._log_warning(
                    f"Error on attempt {attempt + 1}/{max_retries}: {str(e)[:100]} "
                    f"(transient={is_transient})"
                )

                if is_transient and attempt < max_retries - 1:
                    backoff = base_backoff * (backoff_factor ** attempt)
                    await asyncio.sleep(backoff)
                    continue
                else:
                    # Record as declined (permanent error or retries exhausted)
```

**Pros:**
- ✅ Intelligent error handling
- ✅ Configurable behavior
- ✅ Exponential backoff for API friendliness
- ✅ Clear logging for debugging
- ✅ Matches Phase2Settings pattern

**Cons:**
- ❌ More complex implementation
- ❌ Requires thorough testing of error classification
- ❌ Potential for false positive/negative classification

---

### Option 3: Circuit Breaker Pattern (ADVANCED)

**Approach:** Add circuit breaker to detect systemic failures and fail fast

**Use Case:** When API is completely down, avoid wasting time on retries

**Implementation Complexity:** HIGH
**Testing Effort:** HIGH
**Risk:** MEDIUM-HIGH

**Not recommended for initial fix** - adds significant complexity for edge cases. Consider for future enhancement if systemic failures become frequent.

---

## Recommended Implementation Strategy

### Phase 1: Quick Fix (Option 1)
**Timeline:** 1-2 hours implementation + 1 hour testing

1. Add retry loop to `conduct_confirmation_phase()` matching `prompt_for_vote_initiation()` pattern
2. Use hardcoded `max_retries=3`
3. Linear backoff with `asyncio.sleep(1.0 * (attempt + 1))`
4. Add logging for retry attempts
5. Test with mock errors and timeouts

**Success Criteria:**
- ✅ Transient errors trigger retries (up to 3 attempts)
- ✅ Only defaults to "Declined" after retries exhausted
- ✅ Existing tests still pass
- ✅ Logging shows retry attempts clearly

### Phase 2: Production Hardening (Option 2)
**Timeline:** 3-4 hours implementation + 2-3 hours testing

1. Add `max_confirmation_retries` and `confirmation_retry_backoff_seconds` to `Phase2Settings`
2. Implement error classification logic
3. Replace hardcoded retries with configurable settings
4. Add exponential backoff using `retry_backoff_factor`
5. Enhance logging with error type information
6. Add comprehensive tests for:
   - Transient errors (retried)
   - Permanent errors (not retried)
   - Retry exhaustion
   - Backoff timing
   - Configuration variations

**Success Criteria:**
- ✅ Error classification accurately identifies transient errors
- ✅ Retries respect configuration settings
- ✅ Exponential backoff prevents API hammering
- ✅ Logging provides clear error diagnostics
- ✅ All edge cases covered by tests

---

## Implementation Details

### Code Changes Required

**File:** `core/services/voting_service.py`
**Method:** `conduct_confirmation_phase()` (lines 212-351)

**Modification Location:** Lines 269-319 (the participant confirmation loop)

**Current Code (Problematic):**
```python
try:
    result = await asyncio.wait_for(
        Runner.run(participant.agent, confirmation_prompt, context=context),
        timeout=confirmation_timeout
    )
    # ... process response ...

except asyncio.TimeoutError:
    # PROBLEM: No retry, immediate decline
    confirmations.append({'agrees': False})

except Exception as e:
    # PROBLEM: No retry, immediate decline
    confirmations.append({'agrees': False})
```

**Proposed Code (Phase 1 - Minimal Fix):**
```python
max_retries = 3  # TODO: Make configurable in Phase 2
confirmation_recorded = False

for attempt in range(max_retries):
    try:
        if attempt > 0:
            self._log_info(f"Confirmation retry {attempt + 1}/{max_retries} for {participant.name}")
            # Add retry instruction to prompt for subsequent attempts
            retry_instruction = self._get_localized_message('voting_prompts.confirmation_retry_instruction')
            retry_prompt = f"{confirmation_prompt}\n\n{retry_instruction}"
        else:
            retry_prompt = confirmation_prompt

        result = await asyncio.wait_for(
            Runner.run(participant.agent, retry_prompt, context=context),
            timeout=confirmation_timeout
        )
        response = result.final_output.strip()

        # Process response (existing code)
        agrees_to_vote, parse_error = self.utility_agent.detect_numerical_agreement(response)

        if parse_error is not None:
            self._log_warning(f"Invalid confirmation response from {participant.name}: {parse_error}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1.0 * (attempt + 1))  # Linear backoff
                continue
            else:
                # Retries exhausted - default to decline
                agrees_to_vote = False

        # Success - record confirmation
        confirmations.append({
            'participant': participant.name,
            'response': response,
            'agrees': agrees_to_vote
        })
        confirmation_recorded = True
        break  # Exit retry loop

    except asyncio.TimeoutError:
        self._log_warning(
            f"Confirmation timeout for {participant.name} "
            f"(attempt {attempt + 1}/{max_retries}, {confirmation_timeout}s timeout)"
        )
        if attempt < max_retries - 1:
            await asyncio.sleep(1.0 * (attempt + 1))
            continue
        else:
            # Final timeout - record as declined
            confirmations.append({
                'participant': participant.name,
                'response': "(timeout - declined after retries)",
                'agrees': False
            })
            confirmation_recorded = True

    except Exception as e:
        self._log_warning(
            f"Error during confirmation from {participant.name} "
            f"(attempt {attempt + 1}/{max_retries}): {str(e)}"
        )
        if attempt < max_retries - 1:
            await asyncio.sleep(1.0 * (attempt + 1))
            continue
        else:
            # Final error - record as declined
            confirmations.append({
                'participant': participant.name,
                'response': f"(error after retries: {str(e)[:50]})",
                'agrees': False
            })
            confirmation_recorded = True

if not confirmation_recorded:
    # Safety fallback (should never reach here)
    self._log_warning(f"No confirmation recorded for {participant.name} - defaulting to decline")
    confirmations.append({
        'participant': participant.name,
        'response': "(no response - declined)",
        'agrees': False
    })
```

**Key Improvements:**
1. ✅ Retry loop with up to 3 attempts
2. ✅ Linear backoff between retries (1s, 2s, 3s)
3. ✅ Enhanced logging showing attempt numbers
4. ✅ Retry instruction added to prompt for clarity
5. ✅ Only defaults to "Declined" after all retries exhausted
6. ✅ Safety fallback to prevent unhandled cases

---

### Configuration Changes (Phase 2)

**File:** `config/phase2_settings.py`

**Add New Fields:**
```python
class Phase2Settings(BaseModel):
    # ... existing fields ...

    # Confirmation retry settings
    max_confirmation_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for voting confirmation responses"
    )

    confirmation_retry_backoff_seconds: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Initial backoff delay for confirmation retries (exponential scaling)"
    )

    # Error classification settings
    retry_transient_errors_only: bool = Field(
        default=True,
        description="Only retry transient errors (API rate limits, network issues); fail fast on permanent errors"
    )
```

---

### Translation Updates

**File:** `translations/english_prompts.json`

**Add New Key:**
```json
{
  "voting_prompts": {
    "confirmation_retry_instruction": "Please respond clearly with 1 (to confirm) or 0 (to decline). Your previous response could not be processed."
  }
}
```

**Repeat for:** `translations/spanish_prompts.json`, `translations/mandarin_prompts.json`

---

## Testing Strategy

### Unit Tests (New)

**File:** `tests/unit/test_voting_service_confirmation_retries.py`

**Test Cases:**
1. `test_confirmation_succeeds_first_attempt` - No retries needed
2. `test_confirmation_succeeds_after_retry` - Transient error, then success
3. `test_confirmation_timeout_with_retry` - Timeout, then success
4. `test_confirmation_exhausts_retries` - All retries fail, records as declined
5. `test_confirmation_retry_backoff_timing` - Verifies backoff delays
6. `test_confirmation_retry_logging` - Verifies retry attempt logging
7. `test_confirmation_invalid_response_retry` - Parse error triggers retry

### Component Tests (Enhanced)

**File:** `tests/component/test_voting_service_live.py`

**Test Cases:**
1. `test_confirmation_with_transient_api_errors` - Mock API rate limit, verify retry
2. `test_confirmation_with_network_errors` - Mock connection errors, verify retry
3. `test_confirmation_with_timeout_errors` - Mock timeout, verify retry

### Integration Tests (Enhanced)

**File:** `tests/integration/test_phase2_voting_flows.py`

**Test Cases:**
1. `test_full_voting_with_confirmation_retries` - End-to-end voting with retries
2. `test_voting_blocked_by_exhausted_retries` - Voting fails after all retries

---

## Backwards Compatibility

### Configuration Compatibility

**Default Values:** Choose defaults that match current behavior:
- `max_confirmation_retries=3` (new capability, safe default)
- `confirmation_retry_backoff_seconds=1.0` (conservative, API-friendly)
- `retry_transient_errors_only=True` (intelligent, avoids wasted retries)

**Existing Configs:** No changes required to existing YAML files - defaults apply

### Behavioral Changes

**Before Fix:**
- First error/timeout → Immediate "Declined"
- No retries
- High failure rate on transient errors

**After Fix (Phase 1):**
- First error/timeout → Retry (up to 3 attempts)
- Linear backoff
- "Declined" only after retries exhausted
- **More voting attempts succeed** (desired change)

**Impact Assessment:**
- ✅ Positive: More fair to agents, better experimental validity
- ✅ Positive: Reduces false negatives from transient errors
- ⚠️ Neutral: Slightly longer execution time due to retries (acceptable tradeoff)
- ✅ Positive: Better alignment with vote initiation behavior

**Breaking Changes:** NONE
- Existing experiments continue to work
- Results improve in quality (fewer false declines)
- No API contract changes

---

## Monitoring and Observability

### Logging Enhancements

**Add Structured Logging:**
```python
self._log_info(
    f"Confirmation attempt {attempt + 1}/{max_retries} for {participant.name}: "
    f"{'Success' if success else 'Failed'} "
    f"(retry_in={backoff}s)" if attempt < max_retries - 1 else ""
)
```

**Metrics to Track:**
- Total confirmation attempts
- Retry success rate (succeeded after N retries)
- Retry exhaustion rate (all retries failed)
- Error type distribution (timeout vs exception)
- Backoff delay effectiveness

### Debugging Support

**Enhanced Error Messages:**
```python
self._log_warning(
    f"Confirmation error for {participant.name}: "
    f"attempt={attempt + 1}/{max_retries}, "
    f"error_type={type(e).__name__}, "
    f"error_msg={str(e)[:200]}, "
    f"transient={is_transient if Phase2}, "
    f"will_retry={attempt < max_retries - 1}"
)
```

---

## Risk Assessment

### Phase 1 (Minimal Fix) Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Retries cause timeout cascades | Low | Medium | Use conservative backoff (1s, 2s, 3s) |
| Breaks existing tests | Low | High | Run full test suite before merge |
| Retry logic has bugs | Low | Medium | Mirror proven `prompt_for_vote_initiation()` pattern |
| Increases API costs | Low | Low | 3 retries max, only on errors (rare) |

**Overall Risk: LOW**

### Phase 2 (Production Hardening) Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Error classification false positives | Medium | Medium | Conservative classification (whitelist transient errors) |
| Configuration errors | Low | Medium | Validation in Phase2Settings with sensible defaults |
| Exponential backoff too aggressive | Low | Low | Configurable with reasonable defaults |
| Complexity introduces bugs | Medium | Medium | Comprehensive test coverage |

**Overall Risk: MEDIUM** (manageable with thorough testing)

---

## Rollout Plan

### Step 1: Implementation (Phase 1)
- [ ] Add retry loop to `conduct_confirmation_phase()`
- [ ] Add logging for retry attempts
- [ ] Add translation keys for retry instructions
- [ ] Update existing unit tests if needed
- [ ] Add new unit tests for retry behavior

### Step 2: Testing
- [ ] Run full unit test suite
- [ ] Run component tests with live API
- [ ] Run integration tests
- [ ] Manual testing with mock errors
- [ ] Verify logging output

### Step 3: Code Review
- [ ] Review retry logic correctness
- [ ] Review error handling completeness
- [ ] Review logging clarity
- [ ] Review test coverage
- [ ] Review backwards compatibility

### Step 4: Deployment
- [ ] Merge Phase 1 fix
- [ ] Monitor experiment results for improvements
- [ ] Collect retry metrics from logs
- [ ] Assess need for Phase 2 enhancements

### Step 5: Enhancement (Phase 2 - Optional)
- [ ] Add configuration fields to Phase2Settings
- [ ] Implement error classification
- [ ] Implement exponential backoff
- [ ] Add comprehensive tests
- [ ] Update documentation

---

## Success Metrics

### Immediate Success (Phase 1)
- ✅ Zero "Declined (error)" failures on first retry attempt for transient errors
- ✅ 90%+ reduction in false "Declined" recordings
- ✅ All existing tests pass
- ✅ No increase in experiment execution time for successful cases

### Long-term Success (Phase 2)
- ✅ Configurable retry behavior across different experimental setups
- ✅ Intelligent error classification reduces unnecessary retries
- ✅ Exponential backoff prevents API rate limit cascades
- ✅ Clear logging enables easy debugging of voting issues

### Experimental Validity Improvements
- ✅ Higher consensus rates in cooperative agent scenarios
- ✅ Fewer experiments terminated due to technical failures
- ✅ Results more accurately reflect agent preferences vs infrastructure issues

---

## Conclusion

**Recommended Approach:** Implement Phase 1 (Minimal Fix) immediately, then evaluate need for Phase 2 (Production Hardening) based on observed error patterns.

**Rationale:**
1. Phase 1 solves the immediate unfairness issue with minimal risk
2. Phase 1 can be implemented and tested quickly (2-3 hours)
3. Phase 2 adds nice-to-have features but isn't critical for basic functionality
4. Real-world usage data from Phase 1 will inform Phase 2 design decisions

**Expected Impact:**
- Immediate improvement in voting fairness
- Reduction in false "Declined" recordings
- Better experimental validity
- Foundation for future enhancements
