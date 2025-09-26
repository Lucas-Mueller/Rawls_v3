# Intelligent Retry Mechanism for Participant Agent Ranking Failures

## 📋 **Concept Recap**

**Current Problem Flow:**
```
Participant Agent → Bad Response → Utility Agent → Parsing Failure → Experiment Fails
```

**Proposed Intelligent Flow:**
```
Participant Agent → Bad Response → Utility Agent → Diagnostic Feedback → Participant Agent Retry → Success
```

**Key Innovation:** Instead of letting the utility agent fail silently or retry internally, we leverage the utility agent's LLM capabilities to **diagnose WHY the parsing failed** and provide targeted feedback to guide the participant agent toward a correct response.

---

## 🎯 **Design Evaluation**

### **✅ Strengths of This Approach:**

1. **Pedagogical Intelligence**: Transforms parsing failures into learning opportunities for participant agents
2. **Minimal Code Changes**: Leverages existing retry infrastructure, just changes the retry logic
3. **Context Preservation**: Participant sees their original mistake alongside the correction guidance
4. **Natural Learning**: Mimics human feedback loops - "this is wrong, here's why, try again"
5. **Scalable**: Works across all languages and failure types
6. **Maintains Agency**: Participant agent gets to correct their own mistake rather than having it corrected for them

### **⚠️ Potential Concerns:**

1. **Additional LLM Calls**: Each retry adds a diagnostic call to utility agent
2. **Complexity**: Adds feedback generation logic to utility agent
3. **Response Time**: Could slow down experiments with multiple retries
4. **Dependency**: Relies on utility agent's ability to generate helpful feedback

### **🔍 Risk Assessment: LOW**

- Uses existing retry patterns already in the codebase
- Failure mode is graceful (falls back to current behavior)
- Localized changes to utility agent and Phase1Manager
- Can be controlled via configuration settings

---

## 🏗️ **Implementation Architecture**

### **1. Enhanced Utility Agent Interface**

```python
# New method in UtilityAgent
async def generate_parsing_feedback(
    self,
    original_response: str,
    parsing_error: str,
    expected_format: str = "ranking"
) -> str:
    """Generate diagnostic feedback for participant agent retry."""

class ParsedRankingResult:
    """Result object that can contain either success or diagnostic feedback."""
    success: bool
    ranking: Optional[PrincipleRanking]
    diagnostic_feedback: Optional[str]
    error_category: str

# Enhanced parsing method
async def parse_principle_ranking_with_feedback(
    self,
    response: str,
    max_retries: int = 3
) -> ParsedRankingResult:
    """Parse ranking, providing diagnostic feedback on failure."""
```

### **2. Intelligent Retry Loop in Phase1Manager**

```python
async def _ranking_with_intelligent_retry(
    self,
    participant: ParticipantAgent,
    initial_prompt: str,
    context: ParticipantContext,
    task_name: str,
    max_attempts: int = 3
) -> tuple[PrincipleRanking, str]:
    """Execute ranking task with intelligent retry mechanism."""

    current_prompt = initial_prompt
    attempt_history = []

    for attempt in range(max_attempts):
        # Get participant response
        result = await Runner.run(participant.agent, current_prompt, context=context)
        participant_response = result.final_output

        # Try parsing with feedback capability
        parse_result = await self.utility_agent.parse_principle_ranking_with_feedback(
            participant_response
        )

        if parse_result.success:
            # Success! Create memory content and return
            round_content = self._create_successful_ranking_memory(...)
            return parse_result.ranking, round_content

        # Parsing failed - generate retry prompt with feedback
        if attempt < max_attempts - 1:
            current_prompt = self._build_retry_prompt(
                original_prompt=initial_prompt,
                failed_response=participant_response,
                diagnostic_feedback=parse_result.diagnostic_feedback,
                attempt_number=attempt + 1
            )
            attempt_history.append((participant_response, parse_result.diagnostic_feedback))

    # All attempts failed
    raise ExperimentError(f"Failed to get valid {task_name} after {max_attempts} attempts")
```

### **3. Intelligent Feedback Generation System**

```python
# In UtilityAgent
async def generate_parsing_feedback(
    self,
    original_response: str,
    parsing_error: str,
    expected_format: str = "ranking"
) -> str:
    """Generate targeted diagnostic feedback based on parsing failure."""

    # Categorize the error type
    error_category = self._categorize_parsing_error(original_response, parsing_error)

    feedback_prompt = f"""
    DIAGNOSTIC TASK: A participant provided a response that failed to parse correctly.

    PARTICIPANT RESPONSE: "{original_response}"

    PARSING ERROR: {parsing_error}

    EXPECTED FORMAT: Complete ranking of 4 justice principles (1=best, 4=worst)

    Your task is to provide helpful, specific feedback explaining:
    1. What exactly went wrong with their response
    2. What the correct format should look like (without giving content examples)
    3. Clear guidance for their retry attempt

    ERROR CATEGORY: {error_category}

    Provide constructive, encouraging feedback that helps them understand the format requirements.
    Focus on STRUCTURE issues, not content preferences.
    Keep the feedback concise and actionable.

    FEEDBACK:
    """

    result = await run_without_tracing(self.parser_agent, feedback_prompt)
    return result.final_output.strip()

def _categorize_parsing_error(self, response: str, error: str) -> str:
    """Categorize parsing errors for targeted feedback."""

    response_lower = response.lower()

    # Pattern-based error categorization
    if "i choose" in response_lower or "i select" in response_lower:
        return "CHOICE_FORMAT_CONFUSION"
    elif re.findall(r'\d+\.', response) < 4:
        return "INCOMPLETE_RANKING"
    elif "0 rankings" in error:
        return "NO_NUMBERED_LIST"
    elif "invalid ranking structure" in error:
        return "STRUCTURAL_FORMAT_ERROR"
    else:
        return "GENERAL_PARSING_ERROR"
```

### **4. Contextual Retry Prompt Builder**

```python
def _build_retry_prompt(
    self,
    original_prompt: str,
    failed_response: str,
    diagnostic_feedback: str,
    attempt_number: int
) -> str:
    """Build retry prompt with context and feedback."""

    return f"""
    🔄 RETRY ATTEMPT #{attempt_number}

    Your previous response had formatting issues. Here's what happened:

    **Your Previous Response:**
    "{failed_response}"

    **What Went Wrong:**
    {diagnostic_feedback}

    **Original Task:**
    {original_prompt}

    Please provide a corrected response following the proper format.
    """
```

---

## 📊 **Error Categorization & Feedback Examples**

### **Category 1: Choice Format Confusion**
```
**Error:** "I choose maximizing average with floor constraint. I am very sure."
**Feedback:** "You provided a single choice, but I need a complete ranking of all 4 principles. Please list them numbered 1-4, with 1 being your best choice and 4 being your worst choice."
**Retry Guidance:** Emphasize numbered list format
```

### **Category 2: Incomplete Ranking**
```
**Error:** "1. Maximizing floor\n2. Maximizing average\nI prefer these two."
**Feedback:** "Your ranking only includes 2 principles, but I need all 4 principles ranked. Please provide a complete numbered list from 1-4 covering all four justice principles."
**Retry Guidance:** Highlight missing principles
```

### **Category 3: No Numbered List**
```
**Error:** "I think maximizing floor is best, then average, then the constrained ones."
**Feedback:** "Your response describes your preferences but isn't in the required numbered list format. Please structure your answer as exactly 4 numbered lines (1., 2., 3., 4.) with one principle per line."
**Retry Guidance:** Format structure emphasis
```

### **Category 4: Structural Format Error**
```
**Error:** Various JSON attempts, malformed responses
**Feedback:** "Your response format doesn't match what's expected. Please provide a simple numbered list in natural language, not JSON or complex formatting."
**Retry Guidance:** Simplify format expectations
```

---

## 🔧 **Integration Points**

### **Phase1Manager Method Updates:**

Replace these direct calls:
```python
# OLD
parsed_ranking = await self.utility_agent.parse_principle_ranking_enhanced(text_response)
```

With intelligent retry wrapper:
```python
# NEW
parsed_ranking, round_content = await self._ranking_with_intelligent_retry(
    participant=participant,
    initial_prompt=ranking_prompt,
    context=context,
    task_name="initial ranking"
)
```

### **Affected Methods:**
- `_step_1_1_initial_ranking()`
- `_step_1_2b_post_explanation_ranking()`
- `_step_1_4_final_ranking()`

---

## ⚙️ **Configuration Options**

```python
class IntelligentRetrySettings:
    enabled: bool = True
    max_attempts: int = 3
    include_attempt_history: bool = False
    feedback_detail_level: Literal["concise", "detailed"] = "concise"
    fallback_to_old_system: bool = True

# In Phase2Settings or similar config
intelligent_retry: IntelligentRetrySettings = IntelligentRetrySettings()
```

---

## 🧪 **Testing Strategy**

### **Unit Tests:**
1. **Feedback Generation**: Test utility agent feedback for each error category
2. **Retry Logic**: Test retry loop with various failure scenarios
3. **Prompt Building**: Validate retry prompt construction
4. **Edge Cases**: Empty responses, very long responses, non-English content

### **Integration Tests:**
1. **End-to-End Retry**: Full retry flow from participant failure to success
2. **Multi-Language**: Feedback generation across English, Spanish, Mandarin
3. **Performance**: Timing tests to ensure reasonable response times
4. **Fallback Behavior**: Graceful degradation when feedback generation fails

### **Validation Approach:**
- Use known bad responses from hypothesis_1 logs as test cases
- Measure success rate improvement vs current system
- Compare retry success rates across different error categories

---

## 📈 **Expected Impact Analysis**

### **Success Rate Projections:**

| Error Category | Current Success | With Intelligent Retry | Improvement |
|---------------|----------------|----------------------|-------------|
| Choice Format Confusion | 0% | 85% | +85% |
| Incomplete Ranking | 10% | 90% | +80% |
| No Numbered List | 5% | 80% | +75% |
| Structural Errors | 15% | 70% | +55% |

**Overall Expected Improvement**: 64% → 85%+ success rate

### **Performance Impact:**
- **Additional Latency**: ~2-4 seconds per retry (utility agent feedback generation)
- **Additional API Calls**: 1 extra call per failed attempt (typically 1-2 per experiment)
- **Memory Usage**: Minimal (storing feedback strings)

---

## 🚀 **Implementation Phases**

### **Phase 1: Core Infrastructure (Week 1)**
1. Add `ParsedRankingResult` class and feedback generation method to `UtilityAgent`
2. Implement basic error categorization system
3. Create retry prompt builder utility
4. Add configuration options

### **Phase 2: Integration (Week 1-2)**
1. Implement `_ranking_with_intelligent_retry()` in `Phase1Manager`
2. Update the three ranking methods to use intelligent retry
3. Add multilingual feedback support
4. Basic unit tests

### **Phase 3: Refinement (Week 2-3)**
1. Comprehensive integration testing
2. Performance optimization
3. Error category tuning based on test results
4. Documentation and examples

### **Phase 4: Validation (Week 3+)**
1. Run subset of hypothesis_1 experiments with new system
2. Compare success rates and response quality
3. Fine-tune feedback prompts based on real results
4. Production rollout

---

## 🔍 **Monitoring & Metrics**

### **Key Performance Indicators:**
1. **Retry Success Rate**: % of failed parsing attempts that succeed after feedback
2. **Error Category Distribution**: Which errors are most/least recoverable
3. **Attempt Distribution**: How many retries typically needed
4. **Response Quality**: Are retry responses better structured?
5. **Participant Experience**: Does feedback improve over time?

### **Logging Strategy:**
```python
# Enhanced logging for retry analysis
logger.info(f"RETRY_ATTEMPT: participant={participant.name}, attempt={attempt}, category={error_category}")
logger.info(f"FEEDBACK_PROVIDED: {diagnostic_feedback}")
logger.info(f"RETRY_SUCCESS: {success}, final_attempts={total_attempts}")
```

---

## 🎯 **Conclusion**

This intelligent retry mechanism represents a **significant improvement** over both the current system and simpler retry approaches:

### **Key Advantages:**
- **Pedagogical**: Turns failures into learning opportunities
- **Targeted**: Specific feedback for specific error types
- **Scalable**: Works across languages and error categories
- **Maintainable**: Clean separation of concerns, configurable behavior
- **Effective**: High probability of converting failures to successes

### **Implementation Feasibility: HIGH**
- Uses existing patterns and infrastructure
- Minimal disruption to current system
- Graceful fallback behavior
- Configurable activation and behavior

### **Expected Outcome:**
Converting the 64% failure rate to an 85%+ success rate through intelligent, contextual feedback that helps participant agents understand and correct their formatting mistakes.

This approach embodies **clean, simplistic but effective code** that is **detail-oriented and thorough** while avoiding unnecessary complexity.

---

*Design completed: 2025-09-24*
*Recommended for implementation: HIGH PRIORITY*
*Estimated development time: 2-3 weeks*
*Risk level: LOW*