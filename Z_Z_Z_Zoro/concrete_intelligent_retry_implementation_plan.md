# Concrete Intelligent Retry Implementation Plan

**Document Version:** 1.0
**Date:** September 24, 2025
**Based on:** intelligent_retry_mechanism_implementation_plan.md
**Status:** Developer-Ready Implementation Guide

---

## Executive Summary

This document provides a concrete, step-by-step implementation plan for the intelligent retry mechanism that transforms the 64% failure rate in Phase 1 ranking tasks into an 85%+ success rate. The plan is based on deep analysis of the existing codebase and provides specific file paths, method signatures, and code implementations.

**Key Integration Points Identified:**
- **UtilityAgent** (`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/experiment_agents/utility_agent.py`): Lines 391-499 contain existing parsing logic
- **Phase1Manager** (`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/phase1_manager.py`): Lines 251-531 contain the three ranking methods to enhance
- **ExperimentConfiguration** (`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/config/models.py`): Lines 71-248 for configuration integration

---

## Phase 1: Foundation Implementation (32 hours)

### Task 1.1: Error Classification System (8 hours)

**Objective:** Create streamlined error taxonomy for parsing failures

**Implementation:**

#### Create `utils/parsing_errors.py`
```python
"""
Parsing error classification for intelligent retry mechanism.
"""
from enum import Enum
from typing import Optional, Dict, Any
from utils.error_handling import ExperimentError, ExperimentErrorCategory, ErrorSeverity


class ParsingFailureType(Enum):
    """Specific types of parsing failures for targeted feedback."""
    CHOICE_FORMAT_CONFUSION = "choice_format_confusion"      # "I choose X" responses
    INCOMPLETE_RANKING = "incomplete_ranking"                # Missing 1-3 ranking items
    NO_NUMBERED_LIST = "no_numbered_list"                   # Natural language, no structure
    EMPTY_RESPONSE = "empty_response"                       # Empty or very short responses


class ParsingError(ExperimentError):
    """Parsing-specific error with failure type classification."""

    def __init__(
        self,
        message: str,
        failure_type: ParsingFailureType,
        original_response: str,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message,
            ExperimentErrorCategory.VALIDATION_ERROR,
            ErrorSeverity.RECOVERABLE,  # All parsing failures are recoverable with retry
            context
        )
        self.failure_type = failure_type
        self.original_response = original_response


def classify_parsing_failure(response: str, parsing_exception: Exception) -> ParsingFailureType:
    """
    Classify parsing failure based on response content and exception.

    Args:
        response: Original participant response text
        parsing_exception: Exception that occurred during parsing

    Returns:
        ParsingFailureType indicating the specific failure pattern
    """
    response_lower = response.lower().strip()

    # Check for empty or very short responses
    if len(response.strip()) < 10:
        return ParsingFailureType.EMPTY_RESPONSE

    # Check for choice format confusion (single choice instead of ranking)
    choice_indicators = [
        "i choose", "my choice is", "i prefer", "i select",
        "elijo", "mi elección es", "prefiero", "selecciono",
        "我选择", "我的选择是", "我偏好", "我选择的是"
    ]

    if any(indicator in response_lower for indicator in choice_indicators):
        return ParsingFailureType.CHOICE_FORMAT_CONFUSION

    # Check for numbered list structure
    import re
    numbered_items = re.findall(r'^\s*[1-4]\.?\s+', response, re.MULTILINE)

    if len(numbered_items) == 0:
        return ParsingFailureType.NO_NUMBERED_LIST
    elif len(numbered_items) < 4:
        return ParsingFailureType.INCOMPLETE_RANKING

    # Default to choice format confusion if no specific pattern detected
    return ParsingFailureType.CHOICE_FORMAT_CONFUSION
```

**Deliverables:**
- [ ] `utils/parsing_errors.py` - Complete error classification system
- [ ] Unit tests: `tests/unit/test_parsing_errors.py`
- [ ] Integration test with existing error handling system

---

### Task 1.2: UtilityAgent Feedback Generation (16 hours)

**Objective:** Add diagnostic feedback capability to UtilityAgent

**Implementation:**

#### Modify `experiment_agents/utility_agent.py`

**Add new method after line 553 (end of class):**

```python
async def generate_parsing_feedback(
    self,
    original_response: str,
    failure_type: 'ParsingFailureType',  # Import from utils.parsing_errors
    attempt_number: int
) -> str:
    """
    Generate contextual feedback for parsing failures.

    Args:
        original_response: Original participant response that failed parsing
        failure_type: Specific type of parsing failure detected
        attempt_number: Which retry attempt this is (1, 2, 3...)

    Returns:
        Localized feedback message for the participant
    """
    await self.async_init()

    # Import here to avoid circular dependency
    from utils.parsing_errors import ParsingFailureType

    # Get base feedback template based on failure type and language
    template_key = f"parsing_feedback.{failure_type.value}"

    try:
        base_feedback = self.language_manager.get(template_key)
    except KeyError:
        # Fallback to English if translation missing
        fallback_messages = {
            ParsingFailureType.CHOICE_FORMAT_CONFUSION:
                "I noticed you provided a single choice, but I need you to rank ALL 4 justice principles in order from best (1) to worst (4). Please provide a complete ranking.",
            ParsingFailureType.INCOMPLETE_RANKING:
                "You provided some rankings, but I need all 4 principles ranked. Please provide a complete ranking from 1 to 4.",
            ParsingFailureType.NO_NUMBERED_LIST:
                "Please format your response as a numbered list (1., 2., 3., 4.) with each principle ranked in order.",
            ParsingFailureType.EMPTY_RESPONSE:
                "Please provide a complete response ranking all 4 justice principles from best to worst."
        }
        base_feedback = fallback_messages.get(failure_type, "Please provide a complete ranking of all 4 principles.")

    # Add progressive guidance for multiple attempts
    if attempt_number > 1:
        try:
            progressive_key = f"parsing_feedback.progressive_guidance.attempt_{attempt_number}"
            additional_guidance = self.language_manager.get(progressive_key)
            base_feedback += f"\n\n{additional_guidance}"
        except KeyError:
            # Fallback progressive guidance
            progressive_messages = {
                2: "This is your second attempt. Please be extra careful to format your response as requested.",
                3: "This is your final attempt. Please provide exactly what is requested: a numbered list ranking all 4 principles."
            }
            if attempt_number in progressive_messages:
                base_feedback += f"\n\n{progressive_messages[attempt_number]}"

    return base_feedback


async def parse_principle_ranking_enhanced_with_retry(
    self,
    response: str,
    max_retries: int = 3,
    participant_retry_callback: Optional[Callable[[str], Awaitable[str]]] = None
) -> 'PrincipleRanking':
    """
    Enhanced parsing with participant feedback capability.

    Args:
        response: Initial participant response to parse
        max_retries: Maximum number of retry attempts (includes initial attempt)
        participant_retry_callback: Async function to get retry response from participant

    Returns:
        Successfully parsed PrincipleRanking

    Raises:
        ParsingError: If all retry attempts fail
    """
    from utils.parsing_errors import ParsingError, ParsingFailureType, classify_parsing_failure

    current_response = response

    for attempt in range(max_retries):
        try:
            # Use existing parsing logic
            return await self.parse_principle_ranking_enhanced(current_response)

        except Exception as parsing_exception:
            # Classify the failure type
            failure_type = classify_parsing_failure(current_response, parsing_exception)

            # If this is the last attempt or no retry callback, raise error
            if attempt >= max_retries - 1 or not participant_retry_callback:
                raise ParsingError(
                    f"Failed to parse principle ranking after {attempt + 1} attempts: {str(parsing_exception)}",
                    failure_type,
                    current_response,
                    {
                        "attempt_number": attempt + 1,
                        "max_attempts": max_retries,
                        "original_exception": str(parsing_exception)
                    }
                )

            # Generate feedback and get retry response
            feedback = await self.generate_parsing_feedback(
                original_response=response,  # Always reference original response
                failure_type=failure_type,
                attempt_number=attempt + 1
            )

            # Get participant's retry response
            current_response = await participant_retry_callback(feedback)
```

**Add import at top of file (after line 22):**
```python
from typing import Optional, List, Callable, Awaitable  # Add Callable, Awaitable
```

**Deliverables:**
- [ ] Enhanced UtilityAgent with feedback generation
- [ ] New method signatures integrated with existing parsing
- [ ] Unit tests: `tests/unit/test_utility_agent_feedback.py`
- [ ] Integration tests with existing parsing methods

---

### Task 1.3: Translation Updates (8 hours)

**Objective:** Add multilingual feedback templates to translation files

**Implementation:**

#### Update `translations/english_prompts.json`

**Add after line 50 (inside the main JSON object):**

```json
"parsing_feedback": {
  "choice_format_confusion": "I noticed you provided a single choice, but I need you to rank ALL 4 justice principles in order from best (1) to worst (4). Please provide a numbered list like:\n\n1. [First choice principle]\n2. [Second choice principle]\n3. [Third choice principle]\n4. [Fourth choice principle]",
  "incomplete_ranking": "You provided some rankings, but I need all 4 principles ranked. Please provide a complete ranking from 1 to 4, making sure to include:\n- Maximizing Floor Income\n- Maximizing Average Income\n- Maximizing Average with Floor Constraint\n- Maximizing Average with Range Constraint",
  "no_numbered_list": "Please format your response as a numbered list (1., 2., 3., 4.) with each principle ranked in order. For example:\n\n1. Maximizing Floor Income\n2. Maximizing Average Income\n3. Maximizing Average with Floor Constraint\n4. Maximizing Average with Range Constraint",
  "empty_response": "Please provide a complete response ranking all 4 justice principles from best (1) to worst (4). I need your full ranking to continue.",
  "progressive_guidance": {
    "attempt_2": "This is your second attempt. Please be extra careful to format your response as a numbered list with all 4 principles.",
    "attempt_3": "This is your final attempt. Please provide exactly what is requested: a numbered list ranking all 4 principles from 1 to 4."
  }
}
```

#### Update `translations/spanish_prompts.json`

**Add Spanish translations after the corresponding section:**

```json
"parsing_feedback": {
  "choice_format_confusion": "Noté que proporcionaste una sola opción, pero necesito que clasifiques TODOS los 4 principios de justicia en orden del mejor (1) al peor (4). Por favor proporciona una lista numerada como:\n\n1. [Principio de primera opción]\n2. [Principio de segunda opción]\n3. [Principio de tercera opción]\n4. [Principio de cuarta opción]",
  "incomplete_ranking": "Proporcionaste algunas clasificaciones, pero necesito que los 4 principios estén clasificados. Por favor proporciona una clasificación completa del 1 al 4, asegurándote de incluir:\n- Maximizar los ingresos mínimos\n- Maximizar los ingresos promedio\n- Maximizar los ingresos promedio con restricción de ingreso mínimo\n- Maximizar los ingresos promedio con restricción de rango",
  "no_numbered_list": "Por favor formatea tu respuesta como una lista numerada (1., 2., 3., 4.) con cada principio clasificado en orden. Por ejemplo:\n\n1. Maximizar los ingresos mínimos\n2. Maximizar los ingresos promedio\n3. Maximizar los ingresos promedio con restricción de ingreso mínimo\n4. Maximizar los ingresos promedio con restricción de rango",
  "empty_response": "Por favor proporciona una respuesta completa clasificando los 4 principios de justicia del mejor (1) al peor (4). Necesito tu clasificación completa para continuar.",
  "progressive_guidance": {
    "attempt_2": "Este es tu segundo intento. Por favor ten extra cuidado de formatear tu respuesta como una lista numerada con los 4 principios.",
    "attempt_3": "Este es tu intento final. Por favor proporciona exactamente lo que se solicita: una lista numerada clasificando los 4 principios del 1 al 4."
  }
}
```

#### Update `translations/mandarin_prompts.json`

**Add Mandarin translations:**

```json
"parsing_feedback": {
  "choice_format_confusion": "我注意到您提供了单一选择，但我需要您对所有4个公正原则进行从最好(1)到最差(4)的排序。请提供如下数字列表：\n\n1. [第一选择原则]\n2. [第二选择原则]\n3. [第三选择原则]\n4. [第四选择原则]",
  "incomplete_ranking": "您提供了一些排序，但我需要对所有4个原则进行排序。请提供从1到4的完整排序，确保包括：\n- 最低收入最大化\n- 平均收入最大化\n- 在最低收入约束条件下最大化平均收入\n- 在范围约束条件下最大化平均收入",
  "no_numbered_list": "请将您的回答格式化为数字列表(1., 2., 3., 4.)，按顺序对每个原则进行排序。例如：\n\n1. 最低收入最大化\n2. 平均收入最大化\n3. 在最低收入约束条件下最大化平均收入\n4. 在范围约束条件下最大化平均收入",
  "empty_response": "请提供完整的回答，对所有4个公正原则从最好(1)到最差(4)进行排序。我需要您的完整排序来继续。",
  "progressive_guidance": {
    "attempt_2": "这是您的第二次尝试。请格外小心地将您的回答格式化为包含所有4个原则的数字列表。",
    "attempt_3": "这是您的最后一次尝试。请提供确切要求的内容：一个数字列表，将所有4个原则从1到4进行排序。"
  }
}
```

**Deliverables:**
- [ ] Updated `translations/english_prompts.json`
- [ ] Updated `translations/spanish_prompts.json`
- [ ] Updated `translations/mandarin_prompts.json`
- [ ] Translation consistency validation tests

---

## Phase 2: Core Implementation (36 hours)

### Task 2.1: Configuration Integration (8 hours)

**Objective:** Add retry settings to existing ExperimentConfiguration

**Implementation:**

#### Modify `config/models.py`

**Add after line 103 (in ExperimentConfiguration class):**

```python
# Intelligent Retry Configuration
enable_intelligent_retries: bool = Field(
    True, description="Enable intelligent retry mechanism for parsing failures"
)
max_participant_retries: int = Field(
    2, ge=0, le=5, description="Maximum retry attempts for ranking failures (0 = disabled)"
)
enable_progressive_guidance: bool = Field(
    True, description="Provide more specific guidance on subsequent retry attempts"
)
memory_update_on_retry: bool = Field(
    True, description="Update agent memory with retry experiences and corrections"
)
retry_feedback_detail: str = Field(
    "detailed", description="Level of detail in retry feedback messages: 'concise' or 'detailed'"
)

@field_validator('retry_feedback_detail')
@classmethod
def validate_retry_feedback_detail(cls, v):
    """Validate retry feedback detail level is supported."""
    valid_levels = ["concise", "detailed"]
    if v not in valid_levels:
        raise ValueError(f"Invalid retry feedback detail: {v}. Must be one of {valid_levels}")
    return v
```

**Deliverables:**
- [ ] Updated `config/models.py` with retry configuration
- [ ] Configuration validation for new fields
- [ ] Unit tests: `tests/unit/test_experiment_configuration_retry.py`
- [ ] Documentation updates for new configuration options

---

### Task 2.2: Phase1Manager Retry Integration (20 hours)

**Objective:** Implement intelligent retry loops in existing ranking methods

**Implementation:**

#### Modify `core/phase1_manager.py`

**Add import after line 18:**
```python
from utils.parsing_errors import ParsingError, ParsingFailureType
```

**Add helper method after line 531 (end of class methods):**

```python
async def _execute_ranking_with_retry(
    self,
    participant: ParticipantAgent,
    context: ParticipantContext,
    agent_config: AgentConfiguration,
    ranking_prompt: str,
    task_name: str,
    config: 'ExperimentConfiguration'
) -> tuple['PrincipleRanking', str]:
    """
    Core retry logic for ranking tasks with intelligent feedback.

    Args:
        participant: The participant agent
        context: Current participant context
        agent_config: Agent-specific configuration
        ranking_prompt: The ranking prompt to present
        task_name: Descriptive name for logging (e.g., "initial_ranking")
        config: Experiment configuration with retry settings

    Returns:
        Tuple of (parsed_ranking, round_content_for_memory)

    Raises:
        ExperimentError: If all retry attempts fail
    """
    from agents import Runner

    # Initial attempt
    result = await Runner.run(participant.agent, ranking_prompt, context=context)
    original_response = result.final_output

    # Create retry callback for participant interaction
    async def retry_callback(feedback_message: str) -> str:
        nonlocal context

        # Build retry prompt with feedback
        retry_prompt = self._build_retry_prompt(
            ranking_prompt,
            original_response,
            feedback_message,
            task_name
        )

        # Get participant retry response
        retry_result = await Runner.run(
            participant.agent, retry_prompt, context=context
        )

        # Update memory with retry experience if configured
        if config.memory_update_on_retry:
            retry_memory_content = self._build_retry_memory_content(
                feedback_message,
                retry_result.final_output
            )
            context.memory = await self._update_memory_with_retry(
                participant, context, retry_memory_content, config
            )

        return retry_result.final_output

    # Parse with retry capability
    try:
        parsed_ranking = await self.utility_agent.parse_principle_ranking_enhanced_with_retry(
            original_response,
            max_retries=config.max_participant_retries + 1,  # +1 for initial attempt
            participant_retry_callback=retry_callback if config.enable_intelligent_retries else None
        )
    except ParsingError as e:
        # All retries exhausted - provide detailed error context
        raise ExperimentError(
            f"Failed to parse principle ranking in {task_name} after {config.max_participant_retries + 1} attempts",
            ExperimentErrorCategory.VALIDATION_ERROR,
            ErrorSeverity.FATAL,
            context={
                "participant": participant.name,
                "task": task_name,
                "original_response": original_response,
                "failure_type": e.failure_type.value,
                "retry_attempts": config.max_participant_retries,
                "final_error": str(e)
            }
        )

    # Build complete round content for memory
    round_content = self._build_ranking_round_content(
        ranking_prompt, parsed_ranking, original_response, task_name
    )

    return parsed_ranking, round_content


def _build_retry_prompt(
    self,
    original_prompt: str,
    original_response: str,
    feedback_message: str,
    task_name: str
) -> str:
    """Build prompt for retry attempt with feedback."""
    language_manager = self.language_manager

    try:
        # Try to get localized retry prompt template
        retry_template = language_manager.get("prompts.retry_prompt_template")
        return retry_template.format(
            original_prompt=original_prompt,
            your_response=original_response,
            feedback=feedback_message,
            task_name=task_name
        )
    except KeyError:
        # Fallback English template
        return f"""You previously provided this response to the ranking task:

"{original_response}"

However, there was an issue with your response format:

{feedback_message}

Please provide your ranking again with the correct format:

{original_prompt}"""


def _build_retry_memory_content(
    self,
    feedback_message: str,
    retry_response: str
) -> str:
    """Build memory content for retry experience."""
    language_manager = self.language_manager

    try:
        template = language_manager.get("memory_field_labels.retry_experience")
        return template.format(
            feedback=feedback_message,
            corrected_response=retry_response
        )
    except KeyError:
        # Fallback format
        return f"""Instruction clarification received: {feedback_message}
My corrected response: {retry_response}"""


async def _update_memory_with_retry(
    self,
    participant: ParticipantAgent,
    context: ParticipantContext,
    retry_content: str,
    config: 'ExperimentConfiguration'
) -> str:
    """Update participant memory with retry experience."""
    from utils.memory_manager import MemoryManager

    # Use same memory guidance style as main experiment
    memory_guidance_style = getattr(config, 'memory_guidance_style', 'structured')

    try:
        return await MemoryManager.prompt_agent_for_memory_update(
            participant,
            context,
            retry_content,
            memory_guidance_style=memory_guidance_style,
            language_manager=self.language_manager,
            error_handler=self.error_handler,
            utility_agent=self.utility_agent
        )
    except Exception as e:
        # Log warning but don't fail the retry attempt
        self._log_warning(f"Failed to update memory during retry for {participant.name}: {e}")
        return context.memory  # Return unchanged memory


def _build_ranking_round_content(
    self,
    prompt: str,
    ranking: 'PrincipleRanking',
    original_response: str,
    task_name: str
) -> str:
    """Build round content for memory with retry context."""
    language_manager = self.language_manager

    base_content = f"""{language_manager.get('memory_field_labels.prompt')} {prompt}
{language_manager.get('memory_field_labels.your_response')} {original_response}
{language_manager.get('memory_field_labels.outcome')} {language_manager.get(f'memory_outcomes.completed_{task_name}')}"""

    return base_content
```

**Modify existing ranking methods to use retry logic:**

**Replace lines 251-274 (_step_1_1_initial_ranking):**
```python
async def _step_1_1_initial_ranking(
    self,
    participant: ParticipantAgent,
    context: ParticipantContext,
    agent_config: AgentConfiguration,
    config: 'ExperimentConfiguration' = None
) -> tuple['PrincipleRanking', str]:
    """Step 1.1: Initial principle ranking with intelligent retry."""

    ranking_prompt = self._build_ranking_prompt()

    # Use retry logic if enabled
    if config and config.enable_intelligent_retries:
        return await self._execute_ranking_with_retry(
            participant, context, agent_config, ranking_prompt,
            "initial_ranking", config
        )
    else:
        # Legacy behavior for backward compatibility
        result = await Runner.run(participant.agent, ranking_prompt, context=context)
        text_response = result.final_output

        parsed_ranking = await self.utility_agent.parse_principle_ranking_enhanced(text_response)

        language_manager = self.language_manager
        round_content = f"""{language_manager.get('memory_field_labels.prompt')} {ranking_prompt}
{language_manager.get('memory_field_labels.your_response')} {text_response}
{language_manager.get('memory_field_labels.outcome')} {language_manager.get('memory_outcomes.completed_initial_ranking')}"""

        return parsed_ranking, round_content
```

**Update method calls in _run_single_participant_phase1:**

**Replace line 88:**
```python
initial_ranking, ranking_content = await self._step_1_1_initial_ranking(participant, context, agent_config, config)
```

**Similarly update other ranking method calls (lines 134-136 and 522).**

**Deliverables:**
- [ ] Enhanced Phase1Manager with retry capability
- [ ] Updated method signatures to accept config parameter
- [ ] Backward compatibility with existing behavior
- [ ] Integration tests: `tests/integration/test_phase1_retry_integration.py`
- [ ] Memory consistency validation during retries

---

### Task 2.3: Memory Management Integration (8 hours)

**Objective:** Ensure retry experiences are captured in agent memory

**Implementation:**

#### Update Translation Templates

**Add to `translations/english_prompts.json`:**

```json
"memory_field_labels": {
  "retry_experience": "Instruction clarification received: {feedback}\nMy corrected response: {corrected_response}",
  "retry_attempt": "Retry attempt {attempt_number}"
},
"memory_outcomes": {
  "completed_initial_ranking": "Successfully completed initial principle ranking",
  "completed_post_explanation_ranking": "Successfully completed post-explanation principle ranking",
  "completed_final_ranking": "Successfully completed final principle ranking"
},
"prompts": {
  "retry_prompt_template": "You previously provided this response to the {task_name} task:\n\n\"{your_response}\"\n\nHowever, there was an issue with your response format:\n\n{feedback}\n\nPlease provide your ranking again with the correct format:\n\n{original_prompt}"
}
```

**Add corresponding Spanish and Mandarin translations.**

**Deliverables:**
- [ ] Memory integration for retry experiences
- [ ] Translation templates for retry memory content
- [ ] Memory consistency tests during retry scenarios
- [ ] Documentation for memory management during retries

---

## Phase 3: Testing & Validation (32 hours)

### Task 3.1: Unit Testing (12 hours)

**Objective:** Comprehensive unit tests for all new components

**Test Files to Create:**

#### `tests/unit/test_parsing_errors.py`
```python
"""
Unit tests for parsing error classification system.
"""
import pytest
from utils.parsing_errors import ParsingFailureType, ParsingError, classify_parsing_failure


class TestParsingFailureClassification:
    """Test parsing failure classification logic."""

    def test_empty_response_detection(self):
        """Test detection of empty/very short responses."""
        assert classify_parsing_failure("", Exception()) == ParsingFailureType.EMPTY_RESPONSE
        assert classify_parsing_failure("yes", Exception()) == ParsingFailureType.EMPTY_RESPONSE

    def test_choice_format_confusion_english(self):
        """Test detection of choice format in English."""
        response = "I choose maximizing floor income because it helps the poor."
        assert classify_parsing_failure(response, Exception()) == ParsingFailureType.CHOICE_FORMAT_CONFUSION

    def test_choice_format_confusion_spanish(self):
        """Test detection of choice format in Spanish."""
        response = "Elijo maximizar los ingresos mínimos."
        assert classify_parsing_failure(response, Exception()) == ParsingFailureType.CHOICE_FORMAT_CONFUSION

    def test_choice_format_confusion_mandarin(self):
        """Test detection of choice format in Mandarin."""
        response = "我选择最低收入最大化"
        assert classify_parsing_failure(response, Exception()) == ParsingFailureType.CHOICE_FORMAT_CONFUSION

    def test_incomplete_ranking_detection(self):
        """Test detection of incomplete rankings."""
        response = """1. Maximizing floor income
        2. Maximizing average income"""
        assert classify_parsing_failure(response, Exception()) == ParsingFailureType.INCOMPLETE_RANKING

    def test_no_numbered_list_detection(self):
        """Test detection of responses without numbered structure."""
        response = "I think maximizing floor income is best, then average income is second best."
        assert classify_parsing_failure(response, Exception()) == ParsingFailureType.NO_NUMBERED_LIST

    def test_parsing_error_creation(self):
        """Test ParsingError creation and attributes."""
        error = ParsingError(
            "Test error",
            ParsingFailureType.CHOICE_FORMAT_CONFUSION,
            "I choose maximizing floor"
        )

        assert error.failure_type == ParsingFailureType.CHOICE_FORMAT_CONFUSION
        assert error.original_response == "I choose maximizing floor"
        assert error.severity.value == "recoverable"
```

#### `tests/unit/test_utility_agent_feedback.py`
```python
"""
Unit tests for UtilityAgent feedback generation.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from experiment_agents.utility_agent import UtilityAgent
from utils.parsing_errors import ParsingFailureType


@pytest.mark.asyncio
class TestUtilityAgentFeedback:
    """Test UtilityAgent feedback generation functionality."""

    async def test_feedback_generation_english(self):
        """Test feedback generation in English."""
        # Setup
        language_manager = Mock()
        language_manager.get.return_value = "Please provide a numbered list ranking all 4 principles."

        utility_agent = UtilityAgent(language_manager=language_manager)
        utility_agent._initialization_complete = True  # Skip async_init

        # Test
        feedback = await utility_agent.generate_parsing_feedback(
            "I choose maximizing floor",
            ParsingFailureType.CHOICE_FORMAT_CONFUSION,
            1
        )

        assert "numbered list" in feedback.lower()
        assert "4 principles" in feedback.lower()

    async def test_progressive_guidance(self):
        """Test progressive guidance on multiple attempts."""
        # Setup
        language_manager = Mock()
        language_manager.get.side_effect = [
            "Please provide a numbered list",
            "This is your second attempt"
        ]

        utility_agent = UtilityAgent(language_manager=language_manager)
        utility_agent._initialization_complete = True

        # Test second attempt
        feedback = await utility_agent.generate_parsing_feedback(
            "I choose maximizing floor",
            ParsingFailureType.CHOICE_FORMAT_CONFUSION,
            2
        )

        assert "second attempt" in feedback.lower()

    async def test_parse_with_retry_success_on_retry(self):
        """Test successful parsing after retry."""
        # Setup
        utility_agent = UtilityAgent()
        utility_agent._initialization_complete = True
        utility_agent.parse_principle_ranking_enhanced = AsyncMock()

        # First call fails, second succeeds
        utility_agent.parse_principle_ranking_enhanced.side_effect = [
            Exception("Parse failed"),
            Mock()  # Success
        ]

        callback = AsyncMock(return_value="1. Floor\n2. Average\n3. Floor constraint\n4. Range constraint")

        # Test
        result = await utility_agent.parse_principle_ranking_enhanced_with_retry(
            "I choose floor",
            max_retries=2,
            participant_retry_callback=callback
        )

        # Verify retry callback was called
        callback.assert_called_once()
        assert utility_agent.parse_principle_ranking_enhanced.call_count == 2
```

**Additional unit test files:**
- [ ] `tests/unit/test_phase1_manager_retry.py`
- [ ] `tests/unit/test_configuration_retry_validation.py`
- [ ] `tests/unit/test_translation_feedback.py`

**Deliverables:**
- [ ] Complete unit test suite for all new components
- [ ] Test coverage > 90% for new code
- [ ] CI/CD integration tests
- [ ] Mock-based tests for external dependencies

---

### Task 3.2: Integration Testing (12 hours)

**Objective:** End-to-end testing of retry mechanism

#### `tests/integration/test_intelligent_retry_integration.py`
```python
"""
Integration tests for intelligent retry mechanism.
"""
import pytest
from unittest.mock import Mock, patch
from config import ExperimentConfiguration
from core.phase1_manager import Phase1Manager
from experiment_agents import UtilityAgent, ParticipantAgent
from utils.parsing_errors import ParsingFailureType


@pytest.mark.asyncio
class TestIntelligentRetryIntegration:
    """Integration tests for complete retry workflow."""

    async def test_retry_mechanism_success_after_feedback(self):
        """Test successful ranking after retry with feedback."""
        # Create test configuration with retry enabled
        config = ExperimentConfiguration(
            language="English",
            agents=[Mock()],  # Simplified for test
            enable_intelligent_retries=True,
            max_participant_retries=2
        )

        # Mock participant agent that fails first, succeeds second
        participant = Mock()
        participant.agent = Mock()
        participant.name = "Test Participant"

        # Mock language manager
        language_manager = Mock()
        language_manager.get.return_value = "Please provide a numbered list"

        # Mock utility agent
        utility_agent = Mock()
        utility_agent.parse_principle_ranking_enhanced_with_retry = AsyncMock()

        # Setup Phase1Manager
        phase1_manager = Phase1Manager(
            participants=[participant],
            utility_agent=utility_agent,
            language_manager=language_manager
        )

        # Mock the retry method to simulate successful retry
        expected_ranking = Mock()
        utility_agent.parse_principle_ranking_enhanced_with_retry.return_value = expected_ranking

        # Test
        result, content = await phase1_manager._execute_ranking_with_retry(
            participant,
            Mock(),  # context
            Mock(),  # agent_config
            "Rank the principles",
            "test_ranking",
            config
        )

        assert result == expected_ranking
        assert "Rank the principles" in content

    async def test_retry_mechanism_failure_after_max_attempts(self):
        """Test failure after exceeding max retry attempts."""
        from utils.error_handling import ExperimentError
        from utils.parsing_errors import ParsingError

        # Setup similar to success test but with persistent failures
        config = ExperimentConfiguration(
            language="English",
            agents=[Mock()],
            enable_intelligent_retries=True,
            max_participant_retries=1  # Only 1 retry
        )

        participant = Mock()
        utility_agent = Mock()
        phase1_manager = Phase1Manager([participant], utility_agent, Mock())

        # Mock persistent parsing failure
        parsing_error = ParsingError(
            "Parse failed",
            ParsingFailureType.CHOICE_FORMAT_CONFUSION,
            "I choose floor"
        )
        utility_agent.parse_principle_ranking_enhanced_with_retry = AsyncMock(
            side_effect=parsing_error
        )

        # Test - should raise ExperimentError after retries exhausted
        with pytest.raises(ExperimentError) as exc_info:
            await phase1_manager._execute_ranking_with_retry(
                participant, Mock(), Mock(), "Rank", "test", config
            )

        assert "after 2 attempts" in str(exc_info.value)
        assert exc_info.value.context["failure_type"] == "choice_format_confusion"

    async def test_multilingual_feedback_generation(self):
        """Test feedback generation across all supported languages."""
        languages = ["english", "spanish", "mandarin"]

        for language in languages:
            language_manager = Mock()
            language_manager.get.return_value = f"Feedback in {language}"

            utility_agent = UtilityAgent(
                experiment_language=language,
                language_manager=language_manager
            )
            utility_agent._initialization_complete = True

            feedback = await utility_agent.generate_parsing_feedback(
                "I choose floor",
                ParsingFailureType.CHOICE_FORMAT_CONFUSION,
                1
            )

            assert feedback == f"Feedback in {language}"
            language_manager.get.assert_called_with("parsing_feedback.choice_format_confusion")

    async def test_memory_update_during_retry(self):
        """Test memory updates during retry process."""
        # Setup with memory updates enabled
        config = ExperimentConfiguration(
            language="English",
            agents=[Mock()],
            enable_intelligent_retries=True,
            memory_update_on_retry=True
        )

        participant = Mock()
        context = Mock()
        context.memory = "Initial memory"

        phase1_manager = Phase1Manager([participant], Mock(), Mock())

        # Mock memory update
        with patch.object(phase1_manager, '_update_memory_with_retry') as mock_update:
            mock_update.return_value = "Updated memory with retry"

            updated_memory = await phase1_manager._update_memory_with_retry(
                participant, context, "Retry content", config
            )

            assert updated_memory == "Updated memory with retry"
            mock_update.assert_called_once()
```

**Deliverables:**
- [ ] Complete integration test suite
- [ ] End-to-end workflow validation
- [ ] Multilingual integration testing
- [ ] Performance impact measurement tests
- [ ] Memory consistency validation tests

---

### Task 3.3: Experimental Validation (8 hours)

**Objective:** Validate retry mechanism effectiveness with real data

#### Create `scripts/validate_retry_mechanism.py`
```python
"""
Experimental validation script for intelligent retry mechanism.
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from config import ExperimentConfiguration
from core.phase1_manager import Phase1Manager
from experiment_agents import UtilityAgent, ParticipantAgent
from utils.language_manager import LanguageManager


class RetryValidationRunner:
    """Run experimental validation of retry mechanism."""

    def __init__(self, config_path: str, output_dir: str):
        self.config = ExperimentConfiguration.from_yaml(config_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)

        # Results tracking
        self.results = {
            "experiment_metadata": {
                "start_time": datetime.now().isoformat(),
                "config_file": config_path,
                "retry_enabled": self.config.enable_intelligent_retries
            },
            "success_metrics": {
                "total_ranking_attempts": 0,
                "successful_rankings": 0,
                "failed_rankings": 0,
                "retry_usage": {
                    "tasks_requiring_retry": 0,
                    "total_retry_attempts": 0,
                    "success_after_retry": 0
                }
            },
            "failure_analysis": {
                "failure_types": {},
                "retry_effectiveness": {}
            },
            "performance_metrics": {
                "average_task_duration": 0,
                "retry_overhead": 0
            }
        }

    async def run_validation(self, num_trials: int = 10) -> Dict:
        """Run validation trials and collect metrics."""
        logging.info(f"Starting retry mechanism validation with {num_trials} trials")

        for trial in range(num_trials):
            logging.info(f"Running trial {trial + 1}/{num_trials}")
            await self._run_single_trial()

        # Calculate final metrics
        self._calculate_final_metrics()

        # Save results
        results_file = self.output_dir / f"retry_validation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        logging.info(f"Validation complete. Results saved to: {results_file}")
        return self.results

    async def _run_single_trial(self):
        """Run a single validation trial."""
        # Initialize components
        language_manager = LanguageManager(self.config.language)
        utility_agent = UtilityAgent(language_manager=language_manager)

        # Create test participants
        participants = []
        for agent_config in self.config.agents:
            participant = ParticipantAgent(agent_config, language_manager)
            participants.append(participant)

        # Initialize Phase1Manager
        phase1_manager = Phase1Manager(
            participants=participants,
            utility_agent=utility_agent,
            language_manager=language_manager
        )

        # Run Phase 1 ranking tasks
        for participant in participants:
            await self._test_participant_rankings(participant, phase1_manager)

    async def _test_participant_rankings(self, participant, phase1_manager):
        """Test all ranking tasks for a participant."""
        from models import ParticipantContext, ExperimentPhase

        # Create test context
        context = ParticipantContext(
            name=participant.name,
            role_description="Test participant",
            bank_balance=0.0,
            memory="",
            round_number=0,
            phase=ExperimentPhase.PHASE_1,
            memory_character_limit=50000
        )

        # Test each ranking method
        ranking_methods = [
            ("initial_ranking", phase1_manager._step_1_1_initial_ranking),
            ("post_explanation_ranking", phase1_manager._step_1_2b_post_explanation_ranking),
            ("final_ranking", phase1_manager._step_1_4_final_ranking)
        ]

        for method_name, method in ranking_methods:
            await self._test_ranking_method(participant, context, method, method_name)

    async def _test_ranking_method(self, participant, context, method, method_name):
        """Test a specific ranking method with metrics collection."""
        start_time = asyncio.get_event_loop().time()

        try:
            self.results["success_metrics"]["total_ranking_attempts"] += 1

            # Run ranking with retry capability
            ranking, content = await method(participant, context, Mock())

            # Success
            self.results["success_metrics"]["successful_rankings"] += 1

        except Exception as e:
            # Failure
            self.results["success_metrics"]["failed_rankings"] += 1

            # Analyze failure type if it's a parsing error
            if hasattr(e, 'failure_type'):
                failure_type = e.failure_type.value
                self.results["failure_analysis"]["failure_types"][failure_type] = \
                    self.results["failure_analysis"]["failure_types"].get(failure_type, 0) + 1

        # Record timing
        duration = asyncio.get_event_loop().time() - start_time
        # Update performance metrics...

    def _calculate_final_metrics(self):
        """Calculate final success rate and retry effectiveness."""
        total = self.results["success_metrics"]["total_ranking_attempts"]
        successful = self.results["success_metrics"]["successful_rankings"]

        if total > 0:
            success_rate = (successful / total) * 100
            self.results["success_metrics"]["success_rate_percent"] = success_rate

            logging.info(f"Final Success Rate: {success_rate:.1f}%")
            logging.info(f"Total Attempts: {total}")
            logging.info(f"Successful: {successful}")


async def main():
    """Main validation entry point."""
    logging.basicConfig(level=logging.INFO)

    # Test with and without retry mechanism
    configs = [
        ("config/default_config.yaml", "with_retry"),
        ("config/default_config_no_retry.yaml", "without_retry")  # Need to create
    ]

    results = {}

    for config_path, test_name in configs:
        runner = RetryValidationRunner(config_path, f"validation_results/{test_name}")
        results[test_name] = await runner.run_validation(num_trials=5)

    # Compare results
    print("\n=== VALIDATION RESULTS COMPARISON ===")
    for test_name, result in results.items():
        success_rate = result["success_metrics"].get("success_rate_percent", 0)
        print(f"{test_name}: {success_rate:.1f}% success rate")


if __name__ == "__main__":
    asyncio.run(main())
```

**Deliverables:**
- [ ] Experimental validation script
- [ ] A/B testing framework for retry vs non-retry
- [ ] Success rate improvement measurement
- [ ] Performance overhead analysis
- [ ] Validation report with recommendations

---

## Phase 4: Documentation & Deployment (20 hours)

### Task 4.1: Technical Documentation (8 hours)

**Create comprehensive documentation:**

#### `docs/intelligent_retry_system.md`
```markdown
# Intelligent Retry System

## Overview
The intelligent retry system provides automated error recovery for participant response parsing failures in Phase 1 ranking tasks.

## Architecture
- **Error Classification**: 4 specific failure types with targeted feedback
- **Retry Logic**: Configurable retry attempts with progressive guidance
- **Memory Integration**: Retry experiences captured in participant memory
- **Multilingual Support**: Feedback generation in English, Spanish, and Mandarin

## Configuration
```yaml
enable_intelligent_retries: true
max_participant_retries: 2
enable_progressive_guidance: true
memory_update_on_retry: true
retry_feedback_detail: "detailed"
```

## Integration Points
- UtilityAgent: `generate_parsing_feedback()` and `parse_principle_ranking_enhanced_with_retry()`
- Phase1Manager: Enhanced ranking methods with retry capability
- Translation System: Feedback templates in all supported languages

## Monitoring
- Success rate metrics
- Retry attempt frequency
- Failure type distribution
- Performance impact measurement
```

**Deliverables:**
- [ ] Complete technical documentation
- [ ] API documentation for new methods
- [ ] Configuration guide
- [ ] Troubleshooting guide
- [ ] Migration guide from existing system

---

### Task 4.2: Testing Documentation (4 hours)

**Create testing guides:**

#### `docs/testing_retry_system.md`
```markdown
# Testing the Intelligent Retry System

## Unit Testing
- `tests/unit/test_parsing_errors.py` - Error classification tests
- `tests/unit/test_utility_agent_feedback.py` - Feedback generation tests

## Integration Testing
- `tests/integration/test_intelligent_retry_integration.py` - End-to-end retry workflow

## Validation Testing
- `scripts/validate_retry_mechanism.py` - Experimental effectiveness validation

## Test Coverage Requirements
- Unit tests: >90% coverage for new code
- Integration tests: All retry workflows covered
- Validation tests: Success rate improvement demonstrated
```

**Deliverables:**
- [ ] Complete testing documentation
- [ ] Test execution guides
- [ ] Coverage requirements and measurement
- [ ] Continuous integration setup

---

### Task 4.3: Deployment Guide (8 hours)

**Create deployment documentation:**

#### `docs/retry_system_deployment.md`
```markdown
# Deploying the Intelligent Retry System

## Prerequisites
- Existing Frohlich Experiment framework v3.0+
- Python 3.9+ environment
- Updated translation files

## Deployment Steps

### 1. Code Deployment
```bash
# Apply all file changes from implementation plan
git apply intelligent_retry_implementation.patch

# Update dependencies
pip install -r requirements.txt

# Run migration tests
python -m pytest tests/unit/test_*retry* -v
```

### 2. Configuration Update
```yaml
# Add to your experiment configuration
enable_intelligent_retries: true
max_participant_retries: 2
memory_update_on_retry: true
```

### 3. Validation Testing
```bash
# Run validation script
python scripts/validate_retry_mechanism.py

# Expected results: >85% success rate improvement
```

## Rollback Procedure
If issues arise:
```bash
# Disable retry mechanism in config
enable_intelligent_retries: false

# Or revert to previous version
git revert <retry-commit-hash>
```

## Performance Monitoring
Monitor these metrics post-deployment:
- Phase 1 success rate (target: 85%+)
- Average retry attempts per task
- Memory update consistency
- Overall experiment duration impact
```

**Deliverables:**
- [ ] Complete deployment guide
- [ ] Rollback procedures
- [ ] Performance monitoring setup
- [ ] Production checklist
- [ ] Troubleshooting runbook

---

## Implementation Dependencies & Execution Sequence

### Critical Path Dependencies:
1. **Task 1.1** (Error Classification) → **Task 1.2** (Feedback Generation)
2. **Task 1.2** (Feedback Generation) → **Task 2.2** (Phase1Manager Integration)
3. **Task 2.1** (Configuration) → **Task 2.2** (Phase1Manager Integration)
4. **Task 1.3** (Translation Updates) → **All Testing Tasks**

### Parallel Execution Opportunities:
- **Task 1.1** and **Task 2.1** can be developed in parallel
- **Task 1.3** can be developed alongside **Task 1.2**
- All **Task 3.x** testing can run in parallel after core implementation

### Daily Execution Plan:

#### Week 1 (Foundation - 32 hours)
- **Days 1-2**: Tasks 1.1 + 2.1 (16 hours) - Error classification and configuration
- **Days 3-4**: Task 1.2 (16 hours) - UtilityAgent feedback generation
- **Day 5**: Task 1.3 (8 hours) - Translation updates

#### Week 2 (Core Implementation - 36 hours)
- **Days 1-3**: Task 2.2 (28 hours) - Phase1Manager retry integration
- **Days 4-5**: Task 2.3 (8 hours) - Memory management integration

#### Week 3 (Testing & Deployment - 32 hours)
- **Days 1-2**: Task 3.1 (20 hours) - Unit testing
- **Days 3-4**: Task 3.2 + 3.3 (12 hours) - Integration and validation testing
- **Day 5**: Tasks 4.1-4.3 (20 hours) - Documentation and deployment

---

## Success Validation Criteria

### Primary Success Metrics:
- **Phase 1 Success Rate**: From 36% to 85%+ (minimum 49 percentage point improvement)
- **Parsing Recovery Rate**: 90%+ of failures resolved within 2 retry attempts
- **System Stability**: No regression in successful experiments

### Secondary Success Metrics:
- **Average Retry Usage**: <1.5 attempts per ranking task
- **Performance Impact**: <25% increase in Phase 1 duration
- **Memory Consistency**: 100% consistency in retry vs non-retry memory states

### Validation Methods:
- A/B testing with retry enabled/disabled configurations
- Experimental validation with real participant data
- Performance benchmarking against baseline system
- Cross-language effectiveness validation

---

## Risk Mitigation Strategies

### High-Risk Mitigations:
1. **Phase1Manager Integration Risk**: Feature flag deployment with instant rollback capability
2. **Memory Management Risk**: Comprehensive memory state validation tests
3. **Performance Risk**: Timeout controls and asynchronous processing optimization

### Medium-Risk Mitigations:
1. **Translation Quality Risk**: Native speaker review of all feedback templates
2. **Configuration Complexity Risk**: Backward compatibility maintenance and validation

### Deployment Safety Measures:
- Gradual rollout with success rate monitoring
- Automated rollback triggers for performance degradation
- Comprehensive regression test suite execution

---

This concrete implementation plan provides developer-ready specifications with exact file paths, method signatures, and code implementations. Each task includes specific deliverables, validation criteria, and integration points with the existing codebase. The plan maintains backward compatibility while introducing the intelligent retry mechanism to achieve the target 85%+ success rate improvement.