"""
Unit tests for UtilityAgent feedback generation capabilities.

This module tests the intelligent feedback generation system for parsing failures,
including multilingual support, contextual feedback, and retry mechanism integration.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional, Callable, Awaitable

from experiment_agents.utility_agent import UtilityAgent
from utils.parsing_errors import ParsingFailureType, ParsingError, create_parsing_error
from utils.error_handling import ExperimentError, ErrorSeverity, ExperimentErrorCategory
from models import PrincipleRanking, RankedPrinciple, JusticePrinciple, CertaintyLevel


class TestUtilityAgentFeedbackGeneration:
    """Test the feedback generation system in UtilityAgent."""

    def create_mock_language_manager(self, language: str = "english") -> Mock:
        """Create mock language manager with realistic feedback templates."""
        mock_lm = Mock()

        # Mock multilingual feedback templates based on actual translation files
        feedback_templates = {
            "english": {
                "parsing_feedback.choice_format_confusion.explanation": "You provided a choice statement (\"I choose X\") instead of a ranking format.",
                "parsing_feedback.choice_format_confusion.instruction": "Please provide a numbered ranking of all 4 principles from 1 (best) to 4 (worst).",
                "parsing_feedback.choice_format_confusion.example": "1. Maximizing floor income\\n2. Maximizing average income\\n3. Maximizing average with floor constraint\\n4. Maximizing average with range constraint",

                "parsing_feedback.incomplete_ranking.explanation": "Your ranking is incomplete - some principles are missing.",
                "parsing_feedback.incomplete_ranking.instruction": "Please rank ALL 4 justice principles from 1 to 4.",
                "parsing_feedback.incomplete_ranking.example": "Make sure to include:\\n1. [First choice]\\n2. [Second choice]\\n3. [Third choice]\\n4. [Fourth choice]",

                "parsing_feedback.no_numbered_list.explanation": "You provided a natural language response instead of a numbered list.",
                "parsing_feedback.no_numbered_list.instruction": "Please use a numbered format to rank the principles.",
                "parsing_feedback.no_numbered_list.example": "Format: 1. [principle name], 2. [principle name], etc.",

                "parsing_feedback.empty_response.explanation": "Your response was empty or too short to parse.",
                "parsing_feedback.empty_response.instruction": "Please provide a complete response ranking the justice principles.",
                "parsing_feedback.empty_response.example": "Example: 1. Your top choice, 2. Second choice, 3. Third choice, 4. Last choice"
            },
            "spanish": {
                "parsing_feedback.choice_format_confusion.explanation": "Proporcionaste una declaración de elección (\"Elijo X\") en lugar de un formato de clasificación.",
                "parsing_feedback.choice_format_confusion.instruction": "Por favor proporciona una clasificación numerada de todos los 4 principios del 1 (mejor) al 4 (peor).",
                "parsing_feedback.choice_format_confusion.example": "1. Maximizar ingresos mínimos\\n2. Maximizar ingresos promedio\\n3. Maximizar promedio con restricción de piso\\n4. Maximizar promedio with restricción de rango",

                "parsing_feedback.incomplete_ranking.explanation": "Tu clasificación está incompleta - faltan algunos principios.",
                "parsing_feedback.incomplete_ranking.instruction": "Por favor clasifica TODOS los 4 principios de justicia del 1 al 4.",
                "parsing_feedback.incomplete_ranking.example": "Asegúrate de incluir:\\n1. [Primera opción]\\n2. [Segunda opción]\\n3. [Tercera opción]\\n4. [Cuarta opción]",

                "parsing_feedback.no_numbered_list.explanation": "Proporcionaste una respuesta en lenguaje natural en lugar de una lista numerada.",
                "parsing_feedback.no_numbered_list.instruction": "Por favor usa un formato numerado para clasificar los principios.",
                "parsing_feedback.no_numbered_list.example": "Formato: 1. [nombre del principio], 2. [nombre del principio], etc.",

                "parsing_feedback.empty_response.explanation": "Tu respuesta estaba vacía o era demasiado corta para analizar.",
                "parsing_feedback.empty_response.instruction": "Por favor proporciona una respuesta completa clasificando los principios de justicia.",
                "parsing_feedback.empty_response.example": "Ejemplo: 1. Tu primera opción, 2. Segunda opción, 3. Tercera opción, 4. Última opción"
            },
            "mandarin": {
                "parsing_feedback.choice_format_confusion.explanation": "您提供了选择声明（\"我选择X\"）而不是排名格式。",
                "parsing_feedback.choice_format_confusion.instruction": "请提供所有4个原则的编号排名，从1（最好）到4（最差）。",
                "parsing_feedback.choice_format_confusion.example": "1. 最大化最低收入\\n2. 最大化平均收入\\n3. 在最低收入约束条件下最大化平均收入\\n4. 在范围约束条件下最大化平均收入",

                "parsing_feedback.incomplete_ranking.explanation": "您的排名不完整 - 缺少一些原则。",
                "parsing_feedback.incomplete_ranking.instruction": "请对所有4个正义原则从1到4进行排名。",
                "parsing_feedback.incomplete_ranking.example": "确保包含：\\n1. [第一选择]\\n2. [第二选择]\\n3. [第三选择]\\n4. [第四选择]",

                "parsing_feedback.no_numbered_list.explanation": "您提供了自然语言响应而不是编号列表。",
                "parsing_feedback.no_numbered_list.instruction": "请使用编号格式对原则进行排名。",
                "parsing_feedback.no_numbered_list.example": "格式：1. [原则名称]，2. [原则名称]，等等。",

                "parsing_feedback.empty_response.explanation": "您的响应为空或太短无法解析。",
                "parsing_feedback.empty_response.instruction": "请提供对正义原则进行排名的完整响应。",
                "parsing_feedback.empty_response.example": "示例：1. 您的首选，2. 第二选择，3. 第三选择，4. 最后选择"
            }
        }

        def mock_get(key: str, **kwargs) -> str:
            """Mock the language manager get method."""
            lang_templates = feedback_templates.get(language, feedback_templates["english"])
            template = lang_templates.get(key, f"[MISSING: {key}]")
            return template.replace("\\n", "\n")  # Unescape newlines

        mock_lm.get.side_effect = mock_get
        return mock_lm

    @pytest.mark.parametrize("language,failure_type,expected_phrases", [
        # English feedback
        ("english", ParsingFailureType.CHOICE_FORMAT_CONFUSION, [
            "Parsing Issue", "You provided a choice statement", "numbered ranking",
            "1. Maximizing floor income", "Your response"
        ]),
        ("english", ParsingFailureType.INCOMPLETE_RANKING, [
            "Parsing Issue", "ranking is incomplete", "ALL 4 justice principles",
            "Make sure to include"
        ]),
        ("english", ParsingFailureType.NO_NUMBERED_LIST, [
            "Parsing Issue", "natural language response", "numbered format",
            "Format: 1. [principle name]"
        ]),
        ("english", ParsingFailureType.EMPTY_RESPONSE, [
            "Parsing Issue", "empty or too short", "complete response",
            "Example: 1. Your top choice"
        ]),

        # Spanish feedback
        ("spanish", ParsingFailureType.CHOICE_FORMAT_CONFUSION, [
            "Problema de Análisis", "declaración de elección", "clasificación numerada"
        ]),
        ("spanish", ParsingFailureType.INCOMPLETE_RANKING, [
            "Problema de Análisis", "clasificación está incompleta", "TODOS los 4 principios"
        ]),

        # Mandarin feedback
        ("mandarin", ParsingFailureType.CHOICE_FORMAT_CONFUSION, [
            "解析问题", "选择声明", "编号排名"
        ]),
        ("mandarin", ParsingFailureType.INCOMPLETE_RANKING, [
            "解析问题", "排名不完整", "所有4个正义原则"
        ]),
    ])
    def test_generate_parsing_feedback_multilingual(
        self,
        language: str,
        failure_type: ParsingFailureType,
        expected_phrases: list
    ):
        """Test multilingual feedback generation for different failure types."""
        # Create utility agent with mock language manager
        language_manager = self.create_mock_language_manager(language)
        agent = UtilityAgent(experiment_language=language, language_manager=language_manager)

        original_response = "I choose maximizing floor income"
        attempt_number = 1

        # Generate feedback
        feedback = agent.generate_parsing_feedback(
            original_response=original_response,
            failure_type=failure_type,
            attempt_number=attempt_number,
            expected_format="ranking"
        )

        # Check that feedback contains expected phrases
        for phrase in expected_phrases:
            assert phrase in feedback, f"Expected phrase '{phrase}' not found in feedback: {feedback}"

        # Check structural elements
        assert f"⚠️" in feedback  # Warning emoji
        assert f"📝" in feedback  # Example emoji
        assert f"🔍" in feedback  # Response preview emoji

        # Check attempt number formatting
        if language == "english":
            assert f"Attempt {attempt_number}" in feedback
        elif language == "spanish":
            assert f"Intento {attempt_number}" in feedback
        elif language == "mandarin":
            assert f"第{attempt_number}次尝试" in feedback

    def test_generate_parsing_feedback_response_preview(self):
        """Test response preview inclusion and truncation in feedback."""
        language_manager = self.create_mock_language_manager("english")
        agent = UtilityAgent(experiment_language="english", language_manager=language_manager)

        # Test with short response
        short_response = "I choose option A"
        feedback = agent.generate_parsing_feedback(
            original_response=short_response,
            failure_type=ParsingFailureType.CHOICE_FORMAT_CONFUSION,
            attempt_number=1
        )

        assert short_response in feedback
        assert "🔍 Your response:" in feedback

        # Test with long response (should be truncated)
        long_response = "I choose " + "x" * 200 + " option with detailed explanation"
        feedback = agent.generate_parsing_feedback(
            original_response=long_response,
            failure_type=ParsingFailureType.CHOICE_FORMAT_CONFUSION,
            attempt_number=2
        )

        assert "🔍 Your response:" in feedback
        assert "..." in feedback  # Should contain truncation indicator
        assert len([line for line in feedback.split("\n") if "🔍" in line][0]) < 150  # Preview line should be reasonable length

    def test_generate_parsing_feedback_empty_response_handling(self):
        """Test feedback generation when original response is empty."""
        language_manager = self.create_mock_language_manager("english")
        agent = UtilityAgent(experiment_language="english", language_manager=language_manager)

        # Test with empty response
        feedback = agent.generate_parsing_feedback(
            original_response="",
            failure_type=ParsingFailureType.EMPTY_RESPONSE,
            attempt_number=1
        )

        # Should not include response preview section
        assert "🔍" not in feedback
        assert "Your response:" not in feedback

        # Should still include other elements
        assert "⚠️ Parsing Issue" in feedback
        assert "📝" in feedback

    def test_generate_parsing_feedback_fallback_on_missing_template(self):
        """Test fallback behavior when language templates are missing."""
        # Create mock language manager that throws exceptions
        mock_lm = Mock()
        mock_lm.get.side_effect = KeyError("Missing template")

        agent = UtilityAgent(experiment_language="english", language_manager=mock_lm)

        # Should fall back to hardcoded English templates
        feedback = agent.generate_parsing_feedback(
            original_response="test response",
            failure_type=ParsingFailureType.CHOICE_FORMAT_CONFUSION,
            attempt_number=1
        )

        # Check that fallback templates are used
        assert "Your response could not be parsed correctly" in feedback
        assert "Please provide a complete response ranking" in feedback
        assert "Example: 1. Your top choice" in feedback

    @pytest.mark.parametrize("attempt_number,expected_format", [
        (1, "Attempt 1"),
        (2, "Attempt 2"),
        (5, "Attempt 5"),
    ])
    def test_generate_parsing_feedback_attempt_numbering(self, attempt_number: int, expected_format: str):
        """Test attempt number formatting in feedback."""
        language_manager = self.create_mock_language_manager("english")
        agent = UtilityAgent(experiment_language="english", language_manager=language_manager)

        feedback = agent.generate_parsing_feedback(
            original_response="test response",
            failure_type=ParsingFailureType.NO_NUMBERED_LIST,
            attempt_number=attempt_number
        )

        assert expected_format in feedback

    def test_generate_parsing_feedback_all_failure_types(self):
        """Test that feedback generation works for all failure types."""
        language_manager = self.create_mock_language_manager("english")
        agent = UtilityAgent(experiment_language="english", language_manager=language_manager)

        failure_types = [
            ParsingFailureType.CHOICE_FORMAT_CONFUSION,
            ParsingFailureType.INCOMPLETE_RANKING,
            ParsingFailureType.NO_NUMBERED_LIST,
            ParsingFailureType.EMPTY_RESPONSE
        ]

        for failure_type in failure_types:
            feedback = agent.generate_parsing_feedback(
                original_response="test response",
                failure_type=failure_type,
                attempt_number=1,
                expected_format="ranking"
            )

            # Each feedback should have basic structure
            assert "⚠️" in feedback
            assert "📝" in feedback
            assert "Parsing Issue" in feedback
            assert len(feedback.split("\n")) >= 5  # Should have multiple lines


class TestUtilityAgentFeedbackIntegration:
    """Test integration of feedback generation with enhanced parsing methods."""

    def create_mock_utility_agent(self, language: str = "english") -> UtilityAgent:
        """Create mock utility agent for testing."""
        language_manager = Mock()
        language_manager.get.return_value = "Mock template"

        agent = UtilityAgent(experiment_language=language, language_manager=language_manager)
        agent._initialization_complete = True  # Skip async_init
        return agent

    @pytest.mark.asyncio
    async def test_parse_principle_ranking_enhanced_with_feedback_success(self):
        """Test successful parsing with feedback capability."""
        agent = self.create_mock_utility_agent("english")

        # Mock the underlying parse method to succeed
        mock_ranking = PrincipleRanking(
            rankings=[
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=1),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=2),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=3),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4)
            ],
            certainty=CertaintyLevel.SURE
        )

        with patch.object(agent, 'parse_principle_ranking_enhanced', AsyncMock(return_value=mock_ranking)):
            result = await agent.parse_principle_ranking_enhanced_with_feedback(
                response="1. Maximizing floor\n2. Maximizing average\n3. Floor constraint\n4. Range constraint",
                max_retries=3
            )

            assert result == mock_ranking

    @pytest.mark.asyncio
    async def test_parse_principle_ranking_enhanced_with_feedback_retry_success(self):
        """Test parsing that succeeds after retry with feedback."""
        agent = self.create_mock_utility_agent("english")

        # Mock successful ranking for second attempt
        mock_ranking = PrincipleRanking(
            rankings=[
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=1),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=2),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=3),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4)
            ],
            certainty=CertaintyLevel.SURE
        )

        # Mock retry callback
        retry_callback = AsyncMock(return_value="1. Floor\n2. Average\n3. Floor constraint\n4. Range constraint")

        with patch.object(agent, 'parse_principle_ranking_enhanced') as mock_parse:
            # First attempt fails, second succeeds
            mock_parse.side_effect = [
                ExperimentError("Parse failed", ExperimentErrorCategory.VALIDATION_ERROR, ErrorSeverity.RECOVERABLE),
                mock_ranking
            ]

            with patch.object(agent, 'generate_parsing_feedback', return_value="Mock feedback"):
                result = await agent.parse_principle_ranking_enhanced_with_feedback(
                    response="I choose maximizing floor",  # Invalid format
                    max_retries=2,
                    participant_retry_callback=retry_callback
                )

                assert result == mock_ranking
                retry_callback.assert_called_once_with("Mock feedback")

    @pytest.mark.asyncio
    async def test_parse_principle_ranking_enhanced_with_feedback_all_retries_fail(self):
        """Test parsing that fails all retry attempts."""
        agent = self.create_mock_utility_agent("english")

        # Mock retry callback
        retry_callback = AsyncMock(return_value="Still invalid response")

        with patch.object(agent, 'parse_principle_ranking_enhanced') as mock_parse:
            # All attempts fail
            mock_parse.side_effect = ExperimentError(
                "Parse failed",
                ExperimentErrorCategory.VALIDATION_ERROR,
                ErrorSeverity.RECOVERABLE
            )

            with patch.object(agent, 'generate_parsing_feedback', return_value="Mock feedback"):
                with pytest.raises(ParsingError) as exc_info:
                    await agent.parse_principle_ranking_enhanced_with_feedback(
                        response="Invalid response",
                        max_retries=2,
                        participant_retry_callback=retry_callback
                    )

                # Check that the error has proper context
                error = exc_info.value
                assert isinstance(error, ParsingError)
                assert error.retry_count == 1  # One retry increment from manual tracking
                assert "parsing_attempts" in error.parsing_context
                assert error.parsing_context["total_attempts"] == 2

    @pytest.mark.asyncio
    async def test_parse_principle_ranking_enhanced_with_feedback_callback_failure(self):
        """Test handling of callback failures during retry."""
        agent = self.create_mock_utility_agent("english")

        # Mock failing retry callback
        retry_callback = AsyncMock(side_effect=Exception("Callback failed"))

        with patch.object(agent, 'parse_principle_ranking_enhanced') as mock_parse:
            # All parsing attempts fail
            mock_parse.side_effect = ExperimentError(
                "Parse failed",
                ExperimentErrorCategory.VALIDATION_ERROR,
                ErrorSeverity.RECOVERABLE
            )

            with patch.object(agent, 'generate_parsing_feedback', return_value="Mock feedback"):
                with pytest.raises(ParsingError):
                    await agent.parse_principle_ranking_enhanced_with_feedback(
                        response="Invalid response",
                        max_retries=2,
                        participant_retry_callback=retry_callback
                    )

                # Should still attempt callback despite failure
                retry_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_principle_ranking_enhanced_with_feedback_no_callback(self):
        """Test parsing with feedback but no retry callback."""
        agent = self.create_mock_utility_agent("english")

        with patch.object(agent, 'parse_principle_ranking_enhanced') as mock_parse:
            # All attempts fail
            mock_parse.side_effect = ExperimentError(
                "Parse failed",
                ExperimentErrorCategory.VALIDATION_ERROR,
                ErrorSeverity.RECOVERABLE
            )

            with pytest.raises(ParsingError) as exc_info:
                await agent.parse_principle_ranking_enhanced_with_feedback(
                    response="Invalid response",
                    max_retries=3,
                    participant_retry_callback=None  # No callback
                )

            # Should still create error with proper context
            error = exc_info.value
            assert isinstance(error, ParsingError)
            assert "parsing_attempts" in error.parsing_context

    @pytest.mark.asyncio
    async def test_parse_principle_ranking_enhanced_with_feedback_empty_retry_response(self):
        """Test handling of empty retry responses from callback."""
        agent = self.create_mock_utility_agent("english")

        # Mock callback returning empty response
        retry_callback = AsyncMock(return_value="")

        with patch.object(agent, 'parse_principle_ranking_enhanced') as mock_parse:
            mock_parse.side_effect = ExperimentError(
                "Parse failed",
                ExperimentErrorCategory.VALIDATION_ERROR,
                ErrorSeverity.RECOVERABLE
            )

            with patch.object(agent, 'generate_parsing_feedback', return_value="Mock feedback"):
                with pytest.raises(ParsingError):
                    await agent.parse_principle_ranking_enhanced_with_feedback(
                        response="Invalid response",
                        max_retries=2,
                        participant_retry_callback=retry_callback
                    )

                # Callback should be called but parsing continues with original response
                retry_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_principle_ranking_enhanced_with_feedback_context_preservation(self):
        """Test that parsing context is properly preserved across retries."""
        agent = self.create_mock_utility_agent("mandarin")

        retry_callback = AsyncMock(return_value="New response")

        with patch.object(agent, 'parse_principle_ranking_enhanced') as mock_parse:
            mock_parse.side_effect = [
                ExperimentError("First failure", ExperimentErrorCategory.VALIDATION_ERROR, ErrorSeverity.RECOVERABLE),
                ExperimentError("Second failure", ExperimentErrorCategory.VALIDATION_ERROR, ErrorSeverity.RECOVERABLE)
            ]

            with patch.object(agent, 'generate_parsing_feedback', return_value="Mock feedback") as mock_feedback:
                with pytest.raises(ParsingError) as exc_info:
                    await agent.parse_principle_ranking_enhanced_with_feedback(
                        response="Original invalid response",
                        max_retries=2,
                        participant_retry_callback=retry_callback
                    )

                # Check that error context includes all attempts
                error = exc_info.value
                assert error.parsing_context["experiment_language"] == "mandarin"
                assert error.parsing_context["total_attempts"] == 2
                assert len(error.parsing_context["parsing_attempts"]) == 2

                # Check that feedback was generated with correct parameters
                mock_feedback.assert_called_once_with(
                    original_response="Original invalid response",
                    failure_type=ParsingFailureType.NO_NUMBERED_LIST,  # Default classification
                    attempt_number=1,
                    expected_format="ranking"
                )

    def test_feedback_generation_language_consistency(self):
        """Test that feedback generation respects agent language settings."""
        languages = ["english", "spanish", "mandarin"]

        for language in languages:
            agent = self.create_mock_utility_agent(language)

            # Generate feedback for each language
            feedback = agent.generate_parsing_feedback(
                original_response="test response",
                failure_type=ParsingFailureType.CHOICE_FORMAT_CONFUSION,
                attempt_number=1
            )

            # Should contain language-specific attempt formatting
            if language == "spanish":
                assert "Intento 1" in feedback
            elif language == "mandarin":
                assert "第1次尝试" in feedback
            else:  # English
                assert "Attempt 1" in feedback


class TestUtilityAgentFeedbackConfiguration:
    """Test configuration and integration aspects of feedback generation."""

    def test_feedback_generation_with_different_expected_formats(self):
        """Test feedback generation with different expected format types."""
        language_manager = Mock()
        language_manager.get.return_value = "Mock template"
        agent = UtilityAgent(experiment_language="english", language_manager=language_manager)

        formats = ["ranking", "choice", "agreement"]

        for format_type in formats:
            feedback = agent.generate_parsing_feedback(
                original_response="test response",
                failure_type=ParsingFailureType.INCOMPLETE_RANKING,
                attempt_number=1,
                expected_format=format_type
            )

            # Should contain format-specific feedback elements
            assert "Parsing Issue" in feedback
            assert f"expected_format" not in feedback  # Internal detail not exposed to user

    def test_feedback_generation_template_key_mapping(self):
        """Test that failure types correctly map to template keys."""
        language_manager = Mock()
        language_manager.get.return_value = "Mock template"
        agent = UtilityAgent(experiment_language="english", language_manager=language_manager)

        # Test each failure type maps to correct template key
        test_cases = [
            (ParsingFailureType.CHOICE_FORMAT_CONFUSION, "parsing_feedback.choice_format_confusion"),
            (ParsingFailureType.INCOMPLETE_RANKING, "parsing_feedback.incomplete_ranking"),
            (ParsingFailureType.NO_NUMBERED_LIST, "parsing_feedback.no_numbered_list"),
            (ParsingFailureType.EMPTY_RESPONSE, "parsing_feedback.empty_response")
        ]

        for failure_type, expected_key_prefix in test_cases:
            agent.generate_parsing_feedback(
                original_response="test",
                failure_type=failure_type,
                attempt_number=1
            )

            # Check that language manager was called with expected keys
            expected_calls = [
                f"{expected_key_prefix}.explanation",
                f"{expected_key_prefix}.instruction",
                f"{expected_key_prefix}.example"
            ]

            for expected_call in expected_calls:
                assert any(
                    call[0][0] == expected_call
                    for call in language_manager.get.call_args_list
                ), f"Expected call to '{expected_call}' not found"

            language_manager.reset_mock()

    def test_feedback_generation_robustness(self):
        """Test feedback generation robustness with various edge cases."""
        # Test with None language manager - should gracefully fall back
        agent = UtilityAgent(experiment_language="english", language_manager=None)

        # Should handle None language manager gracefully with fallback
        feedback = agent.generate_parsing_feedback(
            original_response="test",
            failure_type=ParsingFailureType.EMPTY_RESPONSE,
            attempt_number=1
        )

        # Should fall back to hardcoded templates
        assert "response could not be parsed correctly" in feedback

        # Test with mock that returns None - should handle gracefully with fallbacks
        mock_lm = Mock()
        mock_lm.get.return_value = None
        agent = UtilityAgent(experiment_language="english", language_manager=mock_lm)

        # Should handle None returns gracefully with fallback defaults
        feedback = agent.generate_parsing_feedback(
            original_response="test",
            failure_type=ParsingFailureType.EMPTY_RESPONSE,
            attempt_number=1
        )

        # Should use fallback text when language manager returns None
        assert "response could not be parsed correctly" in feedback
        assert "provide a complete response" in feedback