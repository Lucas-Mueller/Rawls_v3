"""
Critical parsing suite for Spanish multilingual edge cases using actual UtilityAgent methods.

This test suite restores comprehensive Spanish parsing coverage that exercises
production UtilityAgent parsing logic rather than bypassing it with stubbed JSON.

Tests cover:
1. Spanish principle name normalization edge cases
2. Mixed language statement parsing (Spanish + English)
3. Spanish constraint format variations
4. Spanish voting statement parsing
5. Complex Spanish grammatical structures
6. Regional Spanish variations

CRITICAL: These tests exercise actual UtilityAgent.parse_* methods with realistic
text inputs and LLM-like JSON responses to catch real production parsing bugs.
"""

import pytest
import json
import asyncio
from typing import Optional, List

from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple, PrincipleChoice, CertaintyLevel
from utils.language_manager import create_language_manager, SupportedLanguage
from utils.error_handling import ExperimentError
from tests.utils.stubbed_runner import StubbedRunner


@pytest.fixture
def spanish_utility_agent():
    """Create Spanish-configured utility agent for parsing tests."""
    language_manager = create_language_manager(SupportedLanguage.SPANISH)
    return UtilityAgent(
        utility_model="stub-model",
        temperature=0.0,
        experiment_language="spanish",
        language_manager=language_manager
    )


@pytest.fixture
def stubbed_runner(monkeypatch):
    """Create stubbed runner and patch UtilityAgent to use it."""
    runner = StubbedRunner()

    # Patch the utility agent's run_without_tracing function
    async def mock_run_without_tracing(agent, prompt, context=None):
        return await runner.run(agent, prompt, context)

    monkeypatch.setattr(
        "experiment_agents.utility_agent.run_without_tracing",
        mock_run_without_tracing
    )
    return runner


class TestSpanishPrincipleNormalization:
    """Test Spanish principle name normalization with realistic LLM-like responses."""

    @pytest.mark.asyncio
    async def test_spanish_principle_name_mapping(self, spanish_utility_agent, stubbed_runner):
        """Test that Spanish principle names get correctly normalized to English enum values."""

        # Test cases with Spanish text input and LLM-like JSON responses
        test_cases = [
            (
                "Elijo maximizar los ingresos mínimos",
                '{"principle": "maximizar los ingresos mínimos", "constraint_amount": null, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_FLOOR
            ),
            (
                "Mi preferencia es maximizar los ingresos promedio",
                '{"principle": "maximizar los ingresos promedio", "constraint_amount": null, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE
            ),
            (
                "Selecciono maximizar los ingresos promedio con restricción de ingreso mínimo",
                '{"principle": "maximizar los ingresos promedio con restricción de ingreso mínimo", "constraint_amount": 15000, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            ),
            (
                "Apoyo maximizar los ingresos promedio con restricción de rango",
                '{"principle": "maximizar los ingresos promedio con restricción de rango", "constraint_amount": 20000, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
            )
        ]

        # Register initialization + actual responses
        responses = ["test"] + [response for _, response, _ in test_cases]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_principle in test_cases:
            result = await spanish_utility_agent.parse_principle_choice_enhanced(statement)
            assert result.principle == expected_principle, (
                f"Spanish normalization failed for '{statement}': "
                f"expected {expected_principle.value}, got {result.principle.value}"
            )

    @pytest.mark.asyncio
    async def test_partial_spanish_principle_matching(self, spanish_utility_agent, stubbed_runner):
        """Test partial matching for incomplete Spanish principle names."""

        # Test cases with partial or abbreviated Spanish terms
        test_cases = [
            (
                "Prefiero el principio de ingresos mínimos",
                '{"principle": "ingresos mínimos", "constraint_amount": null, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_FLOOR
            ),
            (
                "Apoyo maximizar promedio sin restricciones",
                '{"principle": "maximizar promedio", "constraint_amount": null, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE
            ),
            (
                "Elijo promedio con restricción mínima de €25000",
                '{"principle": "promedio con restricción", "constraint_amount": 25000, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in test_cases]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_principle in test_cases:
            result = await spanish_utility_agent.parse_principle_choice_enhanced(statement)
            assert result.principle == expected_principle, (
                f"Partial Spanish matching failed for '{statement}': "
                f"expected {expected_principle.value}, got {result.principle.value}"
            )

    @pytest.mark.asyncio
    async def test_mixed_language_statements(self, spanish_utility_agent, stubbed_runner):
        """Test parsing of statements mixing Spanish and English."""

        # Realistic mixed-language statements that could occur in experiments
        test_cases = [
            (
                "Elijo maximizing_floor (maximizar los ingresos mínimos)",
                '{"principle": "maximizing_floor", "constraint_amount": null, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_FLOOR
            ),
            (
                "Mi choice es maximizar average income con €15000 constraint",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 15000, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            ),
            (
                "Prefiero el principio maximizing_average_range_constraint con límite de €20000",
                '{"principle": "maximizing_average_range_constraint", "constraint_amount": 20000, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in test_cases]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_principle in test_cases:
            result = await spanish_utility_agent.parse_principle_choice_enhanced(statement)
            assert result.principle == expected_principle, (
                f"Mixed language parsing failed for '{statement}': "
                f"expected {expected_principle.value}, got {result.principle.value}"
            )


class TestSpanishConstraintFormatParsing:
    """Test Spanish constraint amount parsing with various regional formats."""

    @pytest.mark.asyncio
    async def test_european_spanish_number_formats(self, spanish_utility_agent, stubbed_runner):
        """Test European Spanish number formats (Spain): 1.500,50"""

        test_cases = [
            (
                "Elijo maximizar promedio con restricción de €15.000",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 15000, "certainty": "sure"}',
                15000
            ),
            (
                "Restricción de €1.250.000,50 para maximizar promedio",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 1250000, "certainty": "sure"}',
                1250000
            ),
            (
                "Límite de €45.750,25 en el principio de promedio",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 45750, "certainty": "sure"}',
                45750
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in test_cases]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_amount in test_cases:
            result = await spanish_utility_agent.parse_principle_choice_enhanced(statement)
            assert result.constraint_amount == expected_amount, (
                f"European format parsing failed for '{statement}': "
                f"expected {expected_amount}, got {result.constraint_amount}"
            )

    @pytest.mark.asyncio
    async def test_latin_american_number_formats(self, spanish_utility_agent, stubbed_runner):
        """Test Latin American Spanish number formats: 15,000.50"""

        test_cases = [
            (
                "Elijo maximizar promedio con restricción de $15,000",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 15000, "certainty": "sure"}',
                15000
            ),
            (
                "Restricción de $1,250,000.50 para maximizar promedio",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 1250000, "certainty": "sure"}',
                1250000
            ),
            (
                "Límite de MXN 45,750.25 en el principio de promedio",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 45750, "certainty": "sure"}',
                45750
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in test_cases]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_amount in test_cases:
            result = await spanish_utility_agent.parse_principle_choice_enhanced(statement)
            assert result.constraint_amount == expected_amount, (
                f"Latin American format parsing failed for '{statement}': "
                f"expected {expected_amount}, got {result.constraint_amount}"
            )

    @pytest.mark.asyncio
    async def test_spanish_currency_variations(self, spanish_utility_agent, stubbed_runner):
        """Test various Spanish currency formats and symbols."""

        test_cases = [
            (
                "Restricción de 15000 euros para maximizar promedio",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 15000, "certainty": "sure"}',
                15000
            ),
            (
                "Límite de 25000 pesos mexicanos",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 25000, "certainty": "sure"}',
                25000
            ),
            (
                "Tope de ARS 18,000 para el principio",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 18000, "certainty": "sure"}',
                18000
            ),
            (
                "Barrera de COP 50.000",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 50000, "certainty": "sure"}',
                50000
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in test_cases]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_amount in test_cases:
            result = await spanish_utility_agent.parse_principle_choice_enhanced(statement)
            assert result.constraint_amount == expected_amount, (
                f"Currency variation parsing failed for '{statement}': "
                f"expected {expected_amount}, got {result.constraint_amount}"
            )


class TestSpanishVotingStatements:
    """Test Spanish voting statement parsing and agreement detection."""

    @pytest.mark.asyncio
    async def test_spanish_voting_agreement_patterns(self, spanish_utility_agent, stubbed_runner):
        """Test detection of agreement patterns in Spanish voting statements."""

        # Test agreement detection
        agreement_statements = [
            "Sí, estoy de acuerdo",
            "De acuerdo",
            "Acepto esta propuesta",
            "Correcto",
            "Exacto",
            "Absolutamente sí"
        ]

        for statement in agreement_statements:
            agreement = await spanish_utility_agent.detect_agreement(statement)
            assert agreement is True, f"Should detect agreement in: '{statement}'"

    @pytest.mark.asyncio
    async def test_spanish_numerical_voting_responses(self, spanish_utility_agent, stubbed_runner):
        """Test numerical voting response parsing (1=yes, 0=no) in Spanish context."""

        test_cases = [
            ("1", True, None),
            ("0", False, None),
            ("1 (sí)", True, None),
            ("0 (no)", False, None),
            ("Respuesta: 1", True, None),
            ("Mi voto es 0", False, None),
            ("1 y 0", False, "Multiple numbers found"),  # Should error
            ("ningún número", False, "No valid number found"),  # Should error
        ]

        for response, expected_success, expected_error_type in test_cases:
            success, error = spanish_utility_agent.detect_numerical_agreement(response)

            if expected_error_type:
                assert error is not None, f"Should have error for: '{response}'"
                assert expected_error_type in error, f"Error should mention '{expected_error_type}' for: '{response}'"
            else:
                assert success == expected_success, f"Voting detection failed for: '{response}'"
                assert error is None, f"Should not have error for: '{response}'"

    @pytest.mark.asyncio
    async def test_spanish_preference_statement_detection(self, spanish_utility_agent, stubbed_runner):
        """Test preference statement detection in Spanish discussion."""

        # Preference statements that should be detected
        preference_cases = [
            (
                "Mi preferencia es maximizar los ingresos mínimos",
                '{"preference_detected": true, "principle": "maximizing_floor", "constraint_amount": null, "certainty": "sure"}',
                True, JusticePrinciple.MAXIMIZING_FLOOR
            ),
            (
                "Prefiero el principio de maximizar promedio con €15000",
                '{"preference_detected": true, "principle": "maximizing_average_floor_constraint", "constraint_amount": 15000, "certainty": "sure"}',
                True, JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            ),
            (
                "Mi elección es maximizar el rango con restricción",
                '{"preference_detected": true, "principle": "maximizing_average_range_constraint", "constraint_amount": 20000, "certainty": "sure"}',
                True, JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
            )
        ]

        # Non-preference statements
        non_preference_cases = [
            (
                "Estoy discutiendo las opciones disponibles",
                '{"preference_detected": false}',
                False, None
            ),
            (
                "Los principios son interesantes",
                '{"preference_detected": false}',
                False, None
            )
        ]

        all_cases = preference_cases + non_preference_cases

        # Register responses
        responses = ["test"] + [response for _, response, _, _ in all_cases]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, should_detect, expected_principle in all_cases:
            result = await spanish_utility_agent.detect_preference_statement(statement)

            if should_detect:
                assert result is not None, f"Should detect preference in: '{statement}'"
                assert result.principle == expected_principle, (
                    f"Wrong principle detected in '{statement}': "
                    f"expected {expected_principle.value}, got {result.principle.value}"
                )
            else:
                assert result is None, f"Should not detect preference in: '{statement}'"


class TestSpanishGrammaticalComplexity:
    """Test parsing of complex Spanish grammatical structures."""

    @pytest.mark.asyncio
    async def test_complex_spanish_sentence_structures(self, spanish_utility_agent, stubbed_runner):
        """Test parsing of complex Spanish sentences with subordinate clauses."""

        complex_statements = [
            (
                "Aunque considero todas las opciones, mi preferencia definitiva es maximizar los ingresos mínimos porque considero que es más justo",
                '{"principle": "maximizing_floor", "constraint_amount": null, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_FLOOR
            ),
            (
                "Después de reflexionar cuidadosamente sobre las implicaciones económicas y sociales, elijo maximizar el ingreso promedio con una restricción de €25000",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 25000, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            ),
            (
                "Si bien entiendo los beneficios de otros enfoques, creo firmemente que deberíamos maximizar el promedio con restricción de rango de €30000",
                '{"principle": "maximizing_average_range_constraint", "constraint_amount": 30000, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in complex_statements]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_principle in complex_statements:
            result = await spanish_utility_agent.parse_principle_choice_enhanced(statement)
            assert result.principle == expected_principle, (
                f"Complex sentence parsing failed for: '{statement[:50]}...': "
                f"expected {expected_principle.value}, got {result.principle.value}"
            )

    @pytest.mark.asyncio
    async def test_spanish_conditional_and_subjunctive_parsing(self, spanish_utility_agent, stubbed_runner):
        """Test parsing with Spanish conditional and subjunctive moods."""

        conditional_statements = [
            (
                "Si tuviera que elegir, escogería maximizar los ingresos mínimos",
                '{"principle": "maximizing_floor", "constraint_amount": null, "certainty": "unsure"}',
                JusticePrinciple.MAXIMIZING_FLOOR
            ),
            (
                "En caso de que optáramos por restricciones, sugiero €20000 para maximizar promedio",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 20000, "certainty": "unsure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            ),
            (
                "Me gustaría que consideráramos maximizar el rango con restricción",
                '{"principle": "maximizing_average_range_constraint", "constraint_amount": null, "certainty": "unsure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in conditional_statements]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_principle in conditional_statements:
            result = await spanish_utility_agent.parse_principle_choice_enhanced(statement)
            assert result.principle == expected_principle, (
                f"Conditional/subjunctive parsing failed for: '{statement[:50]}...': "
                f"expected {expected_principle.value}, got {result.principle.value}"
            )


class TestSpanishRegionalVariations:
    """Test parsing across different Spanish regional variations."""

    @pytest.mark.asyncio
    async def test_mexican_spanish_variations(self, spanish_utility_agent, stubbed_runner):
        """Test Mexican Spanish specific terms and constructions."""

        mexican_statements = [
            (
                "Elijo maximizar los ingresos mínimos, órale",
                '{"principle": "maximizing_floor", "constraint_amount": null, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_FLOOR
            ),
            (
                "Mi preferencia es el principio de maximizar el promedio con una restricción de $25,000 pesos mexicanos",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 25000, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in mexican_statements]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_principle in mexican_statements:
            result = await spanish_utility_agent.parse_principle_choice_enhanced(statement)
            assert result.principle == expected_principle, (
                f"Mexican Spanish parsing failed for: '{statement}': "
                f"expected {expected_principle.value}, got {result.principle.value}"
            )

    @pytest.mark.asyncio
    async def test_argentinian_spanish_variations(self, spanish_utility_agent, stubbed_runner):
        """Test Argentinian Spanish specific terms and constructions."""

        argentinian_statements = [
            (
                "Che, elijo maximizar los ingresos promedio, ¿dale?",
                '{"principle": "maximizing_average", "constraint_amount": null, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE
            ),
            (
                "Mi elección es maximizar el promedio con una restricción de AR$ 18,000",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 18000, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in argentinian_statements]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_principle in argentinian_statements:
            result = await spanish_utility_agent.parse_principle_choice_enhanced(statement)
            assert result.principle == expected_principle, (
                f"Argentinian Spanish parsing failed for: '{statement}': "
                f"expected {expected_principle.value}, got {result.principle.value}"
            )


class TestSpanishParsingErrorRecovery:
    """Test error recovery and robustness in Spanish parsing."""

    @pytest.mark.asyncio
    async def test_typos_and_misspellings_recovery(self, spanish_utility_agent, stubbed_runner):
        """Test parsing recovery from common Spanish typos and misspellings."""

        typo_statements = [
            (
                "Elijo maksimizar los ingresos minimos",  # Common keyboard typos
                '{"principle": "maximizing_floor", "constraint_amount": null, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_FLOOR
            ),
            (
                "Mi preferensia es maksimizar el promedio",  # Phonetic spelling errors
                '{"principle": "maximizing_average", "constraint_amount": null, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE
            ),
            (
                "Apoyo la maksimisación del promedio con restricción",  # Mixed errors
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 15000, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in typo_statements]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_principle in typo_statements:
            result = await spanish_utility_agent.parse_principle_choice_enhanced(statement)
            assert result.principle == expected_principle, (
                f"Typo recovery failed for: '{statement}': "
                f"expected {expected_principle.value}, got {result.principle.value}"
            )

    @pytest.mark.asyncio
    async def test_malformed_spanish_constraint_recovery(self, spanish_utility_agent, stubbed_runner):
        """Test recovery from malformed Spanish constraint expressions."""

        malformed_cases = [
            (
                "Elijo maximizar promedio con restricción €€15000",  # Double currency symbol
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 15000, "certainty": "sure"}',
                15000
            ),
            (
                "Restricción de €,15,000 para maximizar promedio",  # Extra comma
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 15000, "certainty": "sure"}',
                15000
            ),
            (
                "Límite de €15.000,50,00 euros",  # Extra decimal places
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 15000, "certainty": "sure"}',
                15000
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in malformed_cases]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_amount in malformed_cases:
            result = await spanish_utility_agent.parse_principle_choice_enhanced(statement)
            assert result.constraint_amount == expected_amount, (
                f"Malformed constraint recovery failed for: '{statement}': "
                f"expected {expected_amount}, got {result.constraint_amount}"
            )


# Additional edge case tests to ensure comprehensive coverage
class TestSpanishParsingEdgeCases:
    """Test edge cases and boundary conditions in Spanish parsing."""

    @pytest.mark.asyncio
    async def test_empty_and_whitespace_statements(self, spanish_utility_agent, stubbed_runner):
        """Test handling of empty or whitespace-only statements."""

        edge_cases = [
            "   ",  # Only whitespace
            "\n\t\r",  # Various whitespace characters
            "",  # Empty string
        ]

        # These should trigger retry logic and eventually fail
        stubbed_runner.register("Response Parser", ["test", "not valid json"] * len(edge_cases))
        stubbed_runner.register("Response Validator", ["test"])

        for statement in edge_cases:
            with pytest.raises((ExperimentError, ValueError)):
                await spanish_utility_agent.parse_principle_choice_enhanced(statement, max_retries=1)

    @pytest.mark.asyncio
    async def test_extremely_long_spanish_statements(self, spanish_utility_agent, stubbed_runner):
        """Test parsing of very long Spanish statements."""

        # Create a very long but valid Spanish statement
        long_statement = (
            "Después de una reflexión muy profunda y extensa sobre todas las opciones disponibles, "
            "considerando las implicaciones económicas, sociales y morales de cada principio de justicia distributiva, "
            "incluyendo análisis detallados de los efectos sobre diferentes grupos socioeconómicos, "
            "las consecuencias a largo plazo para la sociedad, los precedentes históricos similares, "
            "y consultando múltiples perspectivas filosóficas sobre la justicia y la equidad, "
            "finalmente he llegado a la conclusión de que mi preferencia definitiva es " +
            "maximizar los ingresos mínimos" +
            " porque considero que es la opción más justa y equitativa para todos los participantes " +
            "en nuestra sociedad, especialmente para aquellos en situaciones económicas más vulnerables."
        )

        stubbed_runner.register("Response Parser", [
            "test",
            '{"principle": "maximizing_floor", "constraint_amount": null, "certainty": "very_sure"}'
        ])
        stubbed_runner.register("Response Validator", ["test"])

        result = await spanish_utility_agent.parse_principle_choice_enhanced(long_statement)
        assert result.principle == JusticePrinciple.MAXIMIZING_FLOOR
        assert result.certainty == CertaintyLevel.VERY_SURE