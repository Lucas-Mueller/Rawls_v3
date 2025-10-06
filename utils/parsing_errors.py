"""
Error classification system for parsing failures in the Frohlich Experiment.

This module provides intelligent error categorization for parsing failures, enabling
targeted retry strategies and improved experiment reliability. The classification
system identifies common parsing failure patterns and supports the intelligent
retry mechanism.

The error types are designed based on analysis of real parsing failures and
support multilingual experiments with targeted retry strategies.
"""

import re
from enum import Enum
from typing import Optional, Dict, Any, List, Pattern
from utils.error_handling import ExperimentError, ErrorSeverity, ExperimentErrorCategory


# Pre-compiled regex patterns for performance optimization
_COMPILED_CHOICE_PATTERNS = [
    re.compile(r'\b(?:i\s+choose|my\s+choice\s+is|i\s+select|i\s+prefer|i\s+support)\b', re.IGNORECASE),
    re.compile(r'(?:我选择|我選擇|我的选择|我的選擇|我倾向|我傾向|我支持)'),  # Removed \b for Chinese
    re.compile(r'\b(?:elijo|mi\s+elección\s+es|prefiero|apoyo)\b', re.IGNORECASE),
]

_COMPILED_NUMBERED_PATTERNS = [
    re.compile(r'^\s*\d+\.\s', re.MULTILINE),
    re.compile(r'^\s*\d+\)\s', re.MULTILINE),
    re.compile(r'^\s*\d+\s*-\s', re.MULTILINE),
    re.compile(r'^\s*\d+\s*:\s', re.MULTILINE),
    re.compile(r'^\s*\(\d+\)\s', re.MULTILINE),
]


class ParsingFailureType(Enum):
    """
    Classification of parsing failure types for intelligent retry strategies.

    Each type represents a distinct category of parsing failure that can be
    addressed with specific retry approaches and prompt modifications.
    """

    CHOICE_FORMAT_CONFUSION = "choice_format_confusion"
    """
    Agent responds with choice statements ("I choose X") instead of rankings.
    Common in experiments where agents misunderstand the ranking requirement.
    Retry strategy: Emphasize numbered ranking format in prompts.
    """

    INCOMPLETE_RANKING = "incomplete_ranking"
    """
    Agent provides partial rankings, missing 1-3 ranking items.
    Often occurs when agents get distracted or forget items.
    Retry strategy: Remind about complete ranking requirement.
    """

    NO_NUMBERED_LIST = "no_numbered_list"
    """
    Agent responds with natural language without numbered structure.
    Common when agents provide essay-style responses instead of lists.
    Retry strategy: Explicitly request numbered format.
    """

    EMPTY_RESPONSE = "empty_response"
    """
    Agent provides empty or very short responses (< 10 meaningful characters).
    May indicate technical issues or misunderstood prompts.
    Retry strategy: Simplify prompt and check for technical issues.
    """


class ParsingError(ExperimentError):
    """
    Specialized exception for parsing failures with intelligent classification.

    Extends the existing ExperimentError framework to provide parsing-specific
    error handling with failure type classification and context preservation.

    Attributes:
        failure_type: The classified type of parsing failure
        original_response: The raw response that failed to parse
        parsing_context: Additional context about the parsing attempt
        retry_count: Number of retry attempts for this specific failure
    """

    def __init__(
        self,
        message: str,
        failure_type: ParsingFailureType,
        severity: ErrorSeverity = ErrorSeverity.RECOVERABLE,
        original_response: Optional[str] = None,
        parsing_context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        operation: Optional[str] = None
    ):
        """
        Initialize parsing error with failure classification.

        Args:
            message: Human-readable error description
            failure_type: Classification of the parsing failure type
            severity: Error severity level (default: RECOVERABLE)
            original_response: The raw response that failed to parse
            parsing_context: Additional parsing context and metadata
            cause: Original exception that triggered this error (if any)
            operation: Name of the parsing operation that failed
        """
        # Build comprehensive context including parsing-specific information
        context = parsing_context or {}
        context.update({
            "failure_type": failure_type.value,
            "original_response_length": len(original_response) if original_response else 0,
            "has_original_response": original_response is not None,
            "parsing_operation": operation
        })

        # Add truncated response for debugging (limit to prevent log overflow)
        if original_response:
            context["original_response_preview"] = original_response[:200] + "..." if len(original_response) > 200 else original_response

        super().__init__(
            message=message,
            category=ExperimentErrorCategory.VALIDATION_ERROR,  # Parsing is a validation operation
            severity=severity,
            context=context,
            cause=cause,
            operation=operation
        )

        # Parsing-specific attributes
        self.failure_type = failure_type
        self.original_response = original_response
        self.parsing_context = parsing_context or {}
        self.retry_count = 0

    def increment_retry(self) -> None:
        """Increment the retry counter for this parsing failure."""
        self.retry_count += 1
        self.context["retry_count"] = self.retry_count

    def get_suggested_retry_strategy(self) -> Dict[str, Any]:
        """
        Get suggested retry strategy based on failure type.

        Returns:
            Dictionary containing retry strategy recommendations including
            prompt modifications, timeout adjustments, and retry limits.
        """
        strategies = {
            ParsingFailureType.CHOICE_FORMAT_CONFUSION: {
                "prompt_emphasis": "numbered ranking format",
                "example_format": "1. First choice\n2. Second choice\n3. Third choice\n4. Fourth choice",
                "max_retries": 2,
                "timeout_multiplier": 1.0,
                "prompt_prefix": "Please provide your response as a numbered list ranking from 1-4:"
            },

            ParsingFailureType.INCOMPLETE_RANKING: {
                "prompt_emphasis": "complete ranking requirement",
                "example_format": "You must rank all 4 principles",
                "max_retries": 3,
                "timeout_multiplier": 1.2,
                "prompt_prefix": "Please ensure you rank ALL FOUR principles from 1-4:"
            },

            ParsingFailureType.NO_NUMBERED_LIST: {
                "prompt_emphasis": "numbered format requirement",
                "example_format": "Use numbers: 1., 2., 3., 4.",
                "max_retries": 2,
                "timeout_multiplier": 1.0,
                "prompt_prefix": "Please respond using ONLY a numbered list format:"
            },

            ParsingFailureType.EMPTY_RESPONSE: {
                "prompt_emphasis": "response requirement",
                "example_format": "Please provide a complete response",
                "max_retries": 1,
                "timeout_multiplier": 1.5,
                "prompt_prefix": "Please provide a complete response to the question:"
            }
        }

        base_strategy = strategies.get(self.failure_type, strategies[ParsingFailureType.EMPTY_RESPONSE])
        base_strategy["current_retry_count"] = self.retry_count
        return base_strategy


def detect_parsing_failure_type(response: str, expected_format: str = "ranking") -> Optional[ParsingFailureType]:
    """
    Detect the type of parsing failure from a response that failed to parse.

    This function analyzes the raw response to classify the parsing failure,
    enabling intelligent retry strategies. It uses pattern matching and
    heuristics to identify common failure modes.

    Args:
        response: The raw response text that failed to parse
        expected_format: The expected format type ('ranking', 'choice', 'agreement', etc.)

    Returns:
        The detected failure type, or None if the failure cannot be classified

    Examples:
        >>> detect_parsing_failure_type("I choose maximizing floor income", "ranking")
        ParsingFailureType.CHOICE_FORMAT_CONFUSION

        >>> detect_parsing_failure_type("1. First choice\n2. Second choice", "ranking")
        ParsingFailureType.INCOMPLETE_RANKING

        >>> detect_parsing_failure_type("", "ranking")
        ParsingFailureType.EMPTY_RESPONSE
    """
    if not response or not isinstance(response, str):
        return ParsingFailureType.EMPTY_RESPONSE

    # Clean the response for analysis
    cleaned_response = response.strip()

    # Empty or very short response detection
    if len(cleaned_response) < 10 or not any(c.isalnum() for c in cleaned_response):
        return ParsingFailureType.EMPTY_RESPONSE

    # For ranking format detection
    if expected_format == "ranking":
        return _detect_ranking_failure_type(cleaned_response)

    # For other formats, return generic classification based on length and structure
    if len(cleaned_response) < 20:
        return ParsingFailureType.EMPTY_RESPONSE

    # If we can't classify specifically, return None for now
    return None


def _detect_ranking_failure_type(response: str) -> Optional[ParsingFailureType]:
    """
    Detect failure type specifically for ranking responses.

    Args:
        response: Cleaned response text

    Returns:
        Detected failure type for ranking-specific parsing
    """
    # Use pre-compiled patterns for better performance
    choice_pattern_found = any(
        pattern.search(response) for pattern in _COMPILED_CHOICE_PATTERNS
    )

    if choice_pattern_found:
        return ParsingFailureType.CHOICE_FORMAT_CONFUSION

    # Numbered list detection
    numbered_items = _count_numbered_items(response)

    # No numbered structure at all
    if numbered_items == 0:
        return ParsingFailureType.NO_NUMBERED_LIST

    # Incomplete ranking (expecting 4 items for justice principles)
    if 1 <= numbered_items <= 3:
        return ParsingFailureType.INCOMPLETE_RANKING

    # If we have 4+ numbered items, the parsing failure might be due to content issues
    # rather than format issues, so we don't classify it
    return None


def _count_numbered_items(text: str) -> int:
    """
    Count the number of numbered list items in text.

    Detects various numbering patterns including:
    - "1.", "2.", etc.
    - "1)", "2)", etc.
    - "1 -", "2 -", etc.
    - Multilingual number formats

    Args:
        text: Text to analyze

    Returns:
        Number of detected numbered items
    """
    found_numbers = set()

    for line in text.split('\n'):
        for pattern in _COMPILED_NUMBERED_PATTERNS:
            match = pattern.search(line)
            if match:
                # Extract the number to avoid counting the same number multiple times
                number_text = re.search(r'\d+', match.group())
                if number_text:
                    found_numbers.add(int(number_text.group()))

    return len(found_numbers)


def create_parsing_error(
    response: str,
    parsing_operation: str,
    expected_format: str = "ranking",
    additional_context: Optional[Dict[str, Any]] = None,
    cause: Optional[Exception] = None
) -> ParsingError:
    """
    Create a classified parsing error from a failed parsing attempt.

    This function serves as the main entry point for creating parsing errors
    with automatic failure type detection and appropriate error messaging.

    Args:
        response: The raw response that failed to parse
        parsing_operation: Description of the parsing operation (e.g., "principle ranking")
        expected_format: The expected format type
        additional_context: Additional context for error tracking
        cause: Original exception if this error wraps another exception

    Returns:
        ParsingError instance with classified failure type and context

    Example:
        >>> error = create_parsing_error(
        ...     response="I choose the first option",
        ...     parsing_operation="principle ranking",
        ...     expected_format="ranking"
        ... )
        >>> error.failure_type
        ParsingFailureType.CHOICE_FORMAT_CONFUSION
    """
    failure_type = detect_parsing_failure_type(response, expected_format)

    if failure_type is None:
        # Default to generic classification based on response characteristics
        if len(response.strip()) < 10:
            failure_type = ParsingFailureType.EMPTY_RESPONSE
        else:
            failure_type = ParsingFailureType.NO_NUMBERED_LIST

    # Build context
    context = additional_context or {}
    context.update({
        "expected_format": expected_format,
        "response_length": len(response),
        "response_lines": len(response.split('\n')),
        "numbered_items_detected": _count_numbered_items(response)
    })

    # Generate appropriate error message based on failure type
    failure_messages = {
        ParsingFailureType.CHOICE_FORMAT_CONFUSION: f"Agent provided choice statement instead of {expected_format} format",
        ParsingFailureType.INCOMPLETE_RANKING: f"Agent provided incomplete {expected_format} (missing items)",
        ParsingFailureType.NO_NUMBERED_LIST: f"Agent provided natural language instead of numbered {expected_format}",
        ParsingFailureType.EMPTY_RESPONSE: f"Agent provided empty or minimal response for {expected_format}"
    }

    message = failure_messages.get(
        failure_type,
        f"Failed to parse {parsing_operation}: unknown failure type"
    )

    return ParsingError(
        message=message,
        failure_type=failure_type,
        severity=ErrorSeverity.RECOVERABLE,
        original_response=response,
        parsing_context=context,
        cause=cause,
        operation=parsing_operation
    )


def get_failure_type_statistics(errors: List[ParsingError]) -> Dict[str, Any]:
    """
    Generate statistics about parsing failure types for analysis and optimization.

    Args:
        errors: List of parsing errors to analyze

    Returns:
        Dictionary with failure type statistics and patterns
    """
    if not errors:
        return {"total_errors": 0}

    # Count by failure type
    failure_counts = {}
    for error in errors:
        failure_type = error.failure_type.value
        failure_counts[failure_type] = failure_counts.get(failure_type, 0) + 1

    # Calculate retry statistics
    total_retries = sum(error.retry_count for error in errors)
    avg_retries = total_retries / len(errors) if errors else 0

    # Most common failure type
    most_common = max(failure_counts.items(), key=lambda x: x[1]) if failure_counts else None

    return {
        "total_errors": len(errors),
        "failure_type_counts": failure_counts,
        "total_retries": total_retries,
        "average_retries_per_error": round(avg_retries, 2),
        "most_common_failure_type": most_common[0] if most_common else None,
        "most_common_failure_count": most_common[1] if most_common else 0,
        "failure_type_percentages": {
            failure_type: round(count / len(errors) * 100, 1)
            for failure_type, count in failure_counts.items()
        }
    }