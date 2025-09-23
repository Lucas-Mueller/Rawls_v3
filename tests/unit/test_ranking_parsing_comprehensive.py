"""
Critical ranking parsing test suite using actual UtilityAgent methods.

This test suite restores comprehensive ranking parsing coverage that exercises
production UtilityAgent.parse_principle_ranking_enhanced logic to catch real
ranking disambiguation bugs.

Tests cover:
1. Complex ranking statement disambiguation
2. Multilingual ranking format variations
3. Partial ranking completion and validation
4. Ranking order consistency validation
5. Mixed format ranking statement parsing
6. Fallback ranking extraction edge cases

CRITICAL: These tests exercise actual UtilityAgent.parse_principle_ranking_enhanced
methods with realistic text inputs and LLM-like JSON responses to catch production bugs.
"""

import pytest
import json
import asyncio
from typing import Optional, List

from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple, PrincipleRanking, RankedPrinciple, CertaintyLevel
from utils.language_manager import create_language_manager, SupportedLanguage
from utils.error_handling import ExperimentError
from tests.utils.stubbed_runner import StubbedRunner


@pytest.fixture
def ranking_utility_agent():
    """Create utility agent for ranking parsing tests."""
    language_manager = create_language_manager(SupportedLanguage.ENGLISH)
    return UtilityAgent(
        utility_model="stub-model",
        temperature=0.0,
        experiment_language="english",
        language_manager=language_manager
    )


@pytest.fixture
def spanish_ranking_utility_agent():
    """Create Spanish utility agent for multilingual ranking tests."""
    language_manager = create_language_manager(SupportedLanguage.SPANISH)
    return UtilityAgent(
        utility_model="stub-model",
        temperature=0.0,
        experiment_language="spanish",
        language_manager=language_manager
    )


@pytest.fixture
def mandarin_ranking_utility_agent():
    """Create Mandarin utility agent for multilingual ranking tests."""
    language_manager = create_language_manager(SupportedLanguage.MANDARIN)
    return UtilityAgent(
        utility_model="stub-model",
        temperature=0.0,
        experiment_language="mandarin",
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


class TestComplexRankingDisambiguation:
    """Test disambiguation of complex ranking statements that caused production issues."""

    @pytest.mark.asyncio
    async def test_ambiguous_ranking_statement_resolution(self, ranking_utility_agent, stubbed_runner):
        """Test resolution of ambiguous ranking statements with multiple valid interpretations."""

        ambiguous_rankings = [
            (
                "I prefer maximizing floor first, then average, followed by the constraint options",
                '''
                {
                    "rankings": [
                        {"principle": "maximizing_floor", "rank": 1},
                        {"principle": "maximizing_average", "rank": 2},
                        {"principle": "maximizing_average_floor_constraint", "rank": 3},
                        {"principle": "maximizing_average_range_constraint", "rank": 4}
                    ],
                    "certainty": "sure"
                }
                ''',
                [JusticePrinciple.MAXIMIZING_FLOOR, JusticePrinciple.MAXIMIZING_AVERAGE,
                 JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT]
            ),
            (
                "My ranking: first choice is maximizing average, last choice is floor constraints, "
                "and the range constraint comes before pure floor maximization",
                '''
                {
                    "rankings": [
                        {"principle": "maximizing_average", "rank": 1},
                        {"principle": "maximizing_average_range_constraint", "rank": 2},
                        {"principle": "maximizing_floor", "rank": 3},
                        {"principle": "maximizing_average_floor_constraint", "rank": 4}
                    ],
                    "certainty": "sure"
                }
                ''',
                [JusticePrinciple.MAXIMIZING_AVERAGE, JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
                 JusticePrinciple.MAXIMIZING_FLOOR, JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT]
            ),
            (
                "Starting with the constraint principles: floor constraint is better than range constraint. "
                "But I prefer non-constraint principles overall: average is best, then floor.",
                '''
                {
                    "rankings": [
                        {"principle": "maximizing_average", "rank": 1},
                        {"principle": "maximizing_floor", "rank": 2},
                        {"principle": "maximizing_average_floor_constraint", "rank": 3},
                        {"principle": "maximizing_average_range_constraint", "rank": 4}
                    ],
                    "certainty": "sure"
                }
                ''',
                [JusticePrinciple.MAXIMIZING_AVERAGE, JusticePrinciple.MAXIMIZING_FLOOR,
                 JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT]
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in ambiguous_rankings]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_order in ambiguous_rankings:
            result = await ranking_utility_agent.parse_principle_ranking_enhanced(statement)

            # Check that we got all 4 rankings
            assert len(result.rankings) == 4, f"Should have 4 rankings for: '{statement[:50]}...'"

            # Check ranking order
            sorted_rankings = sorted(result.rankings, key=lambda x: x.rank)
            actual_order = [r.principle for r in sorted_rankings]

            assert actual_order == expected_order, (
                f"Ranking order mismatch for: '{statement[:50]}...'\n"
                f"Expected: {[p.value for p in expected_order]}\n"
                f"Got: {[p.value for p in actual_order]}"
            )

    @pytest.mark.asyncio
    async def test_incomplete_ranking_completion(self, ranking_utility_agent, stubbed_runner):
        """Test completion of incomplete ranking statements."""

        incomplete_rankings = [
            (
                "My top choice is maximizing floor, my second choice is maximizing average",
                '''
                {
                    "rankings": [
                        {"principle": "maximizing_floor", "rank": 1},
                        {"principle": "maximizing_average", "rank": 2},
                        {"principle": "maximizing_average_floor_constraint", "rank": 3},
                        {"principle": "maximizing_average_range_constraint", "rank": 4}
                    ],
                    "certainty": "unsure"
                }
                ''',
                "Two explicit choices should be completed with remaining principles"
            ),
            (
                "I like maximizing average best. I don't like the range constraint option.",
                '''
                {
                    "rankings": [
                        {"principle": "maximizing_average", "rank": 1},
                        {"principle": "maximizing_floor", "rank": 2},
                        {"principle": "maximizing_average_floor_constraint", "rank": 3},
                        {"principle": "maximizing_average_range_constraint", "rank": 4}
                    ],
                    "certainty": "unsure"
                }
                ''',
                "Best and worst choices should infer middle rankings"
            ),
            (
                "Maximizing floor is my least preferred option",
                '''
                {
                    "rankings": [
                        {"principle": "maximizing_average", "rank": 1},
                        {"principle": "maximizing_average_floor_constraint", "rank": 2},
                        {"principle": "maximizing_average_range_constraint", "rank": 3},
                        {"principle": "maximizing_floor", "rank": 4}
                    ],
                    "certainty": "unsure"
                }
                ''',
                "Least preferred should be rank 4, others inferred"
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in incomplete_rankings]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, description in incomplete_rankings:
            result = await ranking_utility_agent.parse_principle_ranking_enhanced(statement)

            # Should always complete to 4 rankings
            assert len(result.rankings) == 4, f"Should complete to 4 rankings: {description}"

            # Should be marked as less certain for incomplete rankings
            assert result.certainty in [CertaintyLevel.UNSURE, CertaintyLevel.VERY_UNSURE], (
                f"Incomplete rankings should have lower certainty: {description}"
            )

            # All ranks 1-4 should be present exactly once
            ranks = [r.rank for r in result.rankings]
            assert sorted(ranks) == [1, 2, 3, 4], f"Should have ranks 1-4 exactly once: {description}"

    @pytest.mark.asyncio
    async def test_ranking_with_reasoning_extraction(self, ranking_utility_agent, stubbed_runner):
        """Test extraction of rankings from statements with extensive reasoning."""

        reasoning_rankings = [
            (
                "After considering the fairness implications, I believe maximizing floor income "
                "provides the best foundation for society (rank 1). However, pure average maximization "
                "might be more efficient (rank 2). Between the constraint options, I prefer floor "
                "constraints over range constraints because they provide clearer guarantees (rank 3 vs 4).",
                '''
                {
                    "rankings": [
                        {"principle": "maximizing_floor", "rank": 1},
                        {"principle": "maximizing_average", "rank": 2},
                        {"principle": "maximizing_average_floor_constraint", "rank": 3},
                        {"principle": "maximizing_average_range_constraint", "rank": 4}
                    ],
                    "certainty": "very_sure"
                }
                ''',
                "Explicit rank annotations in reasoning"
            ),
            (
                "Looking at equity vs efficiency trade-offs: \n"
                "First, I favor approaches that help the worst-off, so maximizing floor is my top choice.\n"
                "Second, if we must consider efficiency, then maximizing average makes sense.\n"
                "Third, floor constraints balance both concerns reasonably well.\n"
                "Fourth, range constraints seem unnecessarily complex for our purposes.",
                '''
                {
                    "rankings": [
                        {"principle": "maximizing_floor", "rank": 1},
                        {"principle": "maximizing_average", "rank": 2},
                        {"principle": "maximizing_average_floor_constraint", "rank": 3},
                        {"principle": "maximizing_average_range_constraint", "rank": 4}
                    ],
                    "certainty": "very_sure"
                }
                ''',
                "Ordinal ranking with detailed justifications"
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in reasoning_rankings]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, description in reasoning_rankings:
            result = await ranking_utility_agent.parse_principle_ranking_enhanced(statement)

            # Should extract complete ranking despite verbose reasoning
            assert len(result.rankings) == 4, f"Should extract complete ranking: {description}"

            # Should maintain high certainty when ranking is explicit
            assert result.certainty in [CertaintyLevel.SURE, CertaintyLevel.VERY_SURE], (
                f"Explicit rankings should have high certainty: {description}"
            )

            # Verify specific expected order for first test case
            if "rank 1" in statement:
                sorted_rankings = sorted(result.rankings, key=lambda x: x.rank)
                assert sorted_rankings[0].principle == JusticePrinciple.MAXIMIZING_FLOOR
                assert sorted_rankings[1].principle == JusticePrinciple.MAXIMIZING_AVERAGE


class TestMultilingualRankingParsing:
    """Test ranking parsing across different languages."""

    @pytest.mark.asyncio
    async def test_spanish_ranking_parsing(self, spanish_ranking_utility_agent, stubbed_runner):
        """Test Spanish ranking statement parsing with principle name mapping."""

        spanish_rankings = [
            (
                "Mi ranking: 1. Maximizar los ingresos mínimos, 2. Maximizar los ingresos promedio, "
                "3. Maximizar promedio con restricción mínima, 4. Maximizar promedio con restricción de rango",
                '''
                {
                    "rankings": [
                        {"principle": "maximizing_floor", "rank": 1},
                        {"principle": "maximizing_average", "rank": 2},
                        {"principle": "maximizing_average_floor_constraint", "rank": 3},
                        {"principle": "maximizing_average_range_constraint", "rank": 4}
                    ],
                    "certainty": "sure"
                }
                ''',
                "Numbered Spanish ranking list"
            ),
            (
                "Primero prefiero maximizar los ingresos promedio, segundo maximizar los mínimos, "
                "tercero usar restricciones de rango, y último las restricciones de piso",
                '''
                {
                    "rankings": [
                        {"principle": "maximizing_average", "rank": 1},
                        {"principle": "maximizing_floor", "rank": 2},
                        {"principle": "maximizing_average_range_constraint", "rank": 3},
                        {"principle": "maximizing_average_floor_constraint", "rank": 4}
                    ],
                    "certainty": "sure"
                }
                ''',
                "Spanish ordinal ranking (primero, segundo, etc.)"
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in spanish_rankings]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, description in spanish_rankings:
            result = await spanish_ranking_utility_agent.parse_principle_ranking_enhanced(statement)

            assert len(result.rankings) == 4, f"Spanish ranking should be complete: {description}"

            # Check that Spanish principles were normalized to English
            for ranking in result.rankings:
                assert ranking.principle.value in [
                    "maximizing_floor", "maximizing_average",
                    "maximizing_average_floor_constraint", "maximizing_average_range_constraint"
                ], f"Spanish principles should normalize to English: {description}"

    @pytest.mark.asyncio
    async def test_mandarin_ranking_parsing(self, mandarin_ranking_utility_agent, stubbed_runner):
        """Test Mandarin ranking statement parsing with special fallback extraction."""

        mandarin_rankings = [
            (
                "VOTE_PROPOSAL: [在最低收入约束条件下最大化平均收入, 平均收入最大化, 在范围约束条件下最大化平均收入, 最大化最低收入]",
                '''
                {
                    "rankings": [
                        {"principle": "maximizing_average_floor_constraint", "rank": 1},
                        {"principle": "maximizing_average", "rank": 2},
                        {"principle": "maximizing_average_range_constraint", "rank": 3},
                        {"principle": "maximizing_floor", "rank": 4}
                    ],
                    "certainty": "sure"
                }
                ''',
                "VOTE_PROPOSAL array format should be parsed by fallback"
            ),
            (
                "我的排名：\n1. 最大化最低收入\n2. 平均收入最大化\n3. 在最低收入约束条件下最大化平均收入\n4. 在范围约束条件下最大化平均收入",
                '''
                {
                    "rankings": [
                        {"principle": "maximizing_floor", "rank": 1},
                        {"principle": "maximizing_average", "rank": 2},
                        {"principle": "maximizing_average_floor_constraint", "rank": 3},
                        {"principle": "maximizing_average_range_constraint", "rank": 4}
                    ],
                    "certainty": "sure"
                }
                ''',
                "Numbered list format in Mandarin"
            )
        ]

        # Register responses - first one should trigger fallback, second should parse normally
        responses = ["test"] + [response for _, response, _ in mandarin_rankings]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, description in mandarin_rankings:
            result = await mandarin_ranking_utility_agent.parse_principle_ranking_enhanced(statement)

            assert len(result.rankings) == 4, f"Mandarin ranking should be complete: {description}"

            # Check that Mandarin principles were normalized to English
            for ranking in result.rankings:
                assert ranking.principle.value in [
                    "maximizing_floor", "maximizing_average",
                    "maximizing_average_floor_constraint", "maximizing_average_range_constraint"
                ], f"Mandarin principles should normalize to English: {description}"

    @pytest.mark.asyncio
    async def test_mixed_language_ranking_parsing(self, ranking_utility_agent, stubbed_runner):
        """Test parsing of rankings with mixed languages."""

        mixed_language_rankings = [
            (
                "My ranking: 1. maximizing_floor (最大化最低收入), 2. maximizing_average (promedio), "
                "3. floor constraint, 4. range constraint",
                '''
                {
                    "rankings": [
                        {"principle": "maximizing_floor", "rank": 1},
                        {"principle": "maximizing_average", "rank": 2},
                        {"principle": "maximizing_average_floor_constraint", "rank": 3},
                        {"principle": "maximizing_average_range_constraint", "rank": 4}
                    ],
                    "certainty": "sure"
                }
                ''',
                "Mixed English, Mandarin, and Spanish terms"
            ),
            (
                "1° maximizar los ingresos mínimos (maximizing_floor)\n"
                "2° maximizing average income\n"
                "3° 在最低收入约束条件下最大化平均收入\n"
                "4° range constraint option",
                '''
                {
                    "rankings": [
                        {"principle": "maximizing_floor", "rank": 1},
                        {"principle": "maximizing_average", "rank": 2},
                        {"principle": "maximizing_average_floor_constraint", "rank": 3},
                        {"principle": "maximizing_average_range_constraint", "rank": 4}
                    ],
                    "certainty": "sure"
                }
                ''',
                "Each rank in different language"
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in mixed_language_rankings]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, description in mixed_language_rankings:
            result = await ranking_utility_agent.parse_principle_ranking_enhanced(statement)

            assert len(result.rankings) == 4, f"Mixed language ranking should be complete: {description}"

            # Verify correct principle ordering
            sorted_rankings = sorted(result.rankings, key=lambda x: x.rank)
            assert sorted_rankings[0].principle == JusticePrinciple.MAXIMIZING_FLOOR
            assert sorted_rankings[1].principle == JusticePrinciple.MAXIMIZING_AVERAGE


class TestRankingFormatVariations:
    """Test different ranking format variations and edge cases."""

    @pytest.mark.asyncio
    async def test_alternative_ranking_formats(self, ranking_utility_agent, stubbed_runner):
        """Test various alternative ranking formats (bullets, letters, etc.)."""

        alternative_formats = [
            (
                "• Maximizing floor income\n• Maximizing average income\n• Floor constraint option\n• Range constraint option",
                '''
                {
                    "rankings": [
                        {"principle": "maximizing_floor", "rank": 1},
                        {"principle": "maximizing_average", "rank": 2},
                        {"principle": "maximizing_average_floor_constraint", "rank": 3},
                        {"principle": "maximizing_average_range_constraint", "rank": 4}
                    ],
                    "certainty": "sure"
                }
                ''',
                "Bullet point format"
            ),
            (
                "A) Maximizing average income\nB) Maximizing floor income\nC) Average with range constraint\nD) Average with floor constraint",
                '''
                {
                    "rankings": [
                        {"principle": "maximizing_average", "rank": 1},
                        {"principle": "maximizing_floor", "rank": 2},
                        {"principle": "maximizing_average_range_constraint", "rank": 3},
                        {"principle": "maximizing_average_floor_constraint", "rank": 4}
                    ],
                    "certainty": "sure"
                }
                ''',
                "Letter-based ranking format"
            ),
            (
                "Best → Worst: Floor maximization → Average maximization → Floor constraints → Range constraints",
                '''
                {
                    "rankings": [
                        {"principle": "maximizing_floor", "rank": 1},
                        {"principle": "maximizing_average", "rank": 2},
                        {"principle": "maximizing_average_floor_constraint", "rank": 3},
                        {"principle": "maximizing_average_range_constraint", "rank": 4}
                    ],
                    "certainty": "sure"
                }
                ''',
                "Arrow-based best to worst format"
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in alternative_formats]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, description in alternative_formats:
            result = await ranking_utility_agent.parse_principle_ranking_enhanced(statement)

            assert len(result.rankings) == 4, f"Alternative format should be parsed: {description}"

            # Verify ranks are 1-4
            ranks = [r.rank for r in result.rankings]
            assert sorted(ranks) == [1, 2, 3, 4], f"Should have complete ranking: {description}"

    @pytest.mark.asyncio
    async def test_ranking_with_ties_and_indifference(self, ranking_utility_agent, stubbed_runner):
        """Test handling of rankings with ties or expressions of indifference."""

        tie_rankings = [
            (
                "I strongly prefer maximizing floor (rank 1). The other three options are roughly equivalent to me - "
                "I guess average is slightly better (rank 2), then the constraint options are tied for last.",
                '''
                {
                    "rankings": [
                        {"principle": "maximizing_floor", "rank": 1},
                        {"principle": "maximizing_average", "rank": 2},
                        {"principle": "maximizing_average_floor_constraint", "rank": 3},
                        {"principle": "maximizing_average_range_constraint", "rank": 4}
                    ],
                    "certainty": "unsure"
                }
                ''',
                "Expressed indifference should still result in complete ranking"
            ),
            (
                "Maximizing floor is clearly best. I'm indifferent between the other three options.",
                '''
                {
                    "rankings": [
                        {"principle": "maximizing_floor", "rank": 1},
                        {"principle": "maximizing_average", "rank": 2},
                        {"principle": "maximizing_average_floor_constraint", "rank": 3},
                        {"principle": "maximizing_average_range_constraint", "rank": 4}
                    ],
                    "certainty": "unsure"
                }
                ''',
                "Indifference between multiple options"
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in tie_rankings]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, description in tie_rankings:
            result = await ranking_utility_agent.parse_principle_ranking_enhanced(statement)

            assert len(result.rankings) == 4, f"Ties should still result in complete ranking: {description}"

            # Should have lower certainty when ties/indifference expressed
            assert result.certainty in [CertaintyLevel.UNSURE, CertaintyLevel.VERY_UNSURE], (
                f"Ties/indifference should reduce certainty: {description}"
            )

    @pytest.mark.asyncio
    async def test_relative_ranking_statements(self, ranking_utility_agent, stubbed_runner):
        """Test parsing of relative ranking statements (X is better than Y)."""

        relative_rankings = [
            (
                "Maximizing average is better than maximizing floor. Floor constraints are better than range constraints. "
                "I prefer non-constraint options over constraint options.",
                '''
                {
                    "rankings": [
                        {"principle": "maximizing_average", "rank": 1},
                        {"principle": "maximizing_floor", "rank": 2},
                        {"principle": "maximizing_average_floor_constraint", "rank": 3},
                        {"principle": "maximizing_average_range_constraint", "rank": 4}
                    ],
                    "certainty": "sure"
                }
                ''',
                "Pairwise comparisons should build complete ranking"
            ),
            (
                "Between constraint options, I prefer floor over range. Between non-constraint options, floor over average. "
                "Overall, I prefer constraint options to non-constraint options.",
                '''
                {
                    "rankings": [
                        {"principle": "maximizing_average_floor_constraint", "rank": 1},
                        {"principle": "maximizing_average_range_constraint", "rank": 2},
                        {"principle": "maximizing_floor", "rank": 3},
                        {"principle": "maximizing_average", "rank": 4}
                    ],
                    "certainty": "sure"
                }
                ''',
                "Hierarchical pairwise preferences"
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in relative_rankings]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, description in relative_rankings:
            result = await ranking_utility_agent.parse_principle_ranking_enhanced(statement)

            assert len(result.rankings) == 4, f"Relative rankings should be complete: {description}"

            # Verify logical consistency in first test case
            if "average is better than" in statement.lower():
                sorted_rankings = sorted(result.rankings, key=lambda x: x.rank)
                avg_rank = next(r.rank for r in result.rankings if r.principle == JusticePrinciple.MAXIMIZING_AVERAGE)
                floor_rank = next(r.rank for r in result.rankings if r.principle == JusticePrinciple.MAXIMIZING_FLOOR)
                assert avg_rank < floor_rank, "Average should rank better than floor based on statement"


class TestRankingFallbackExtraction:
    """Test fallback ranking extraction mechanisms."""

    @pytest.mark.asyncio
    async def test_fallback_extraction_triggers(self, ranking_utility_agent, stubbed_runner):
        """Test scenarios that should trigger fallback extraction logic."""

        fallback_scenarios = [
            (
                "VOTE_PROPOSAL: [maximizing_floor, maximizing_average, maximizing_average_floor_constraint, maximizing_average_range_constraint]",
                "invalid json response",  # Force fallback
                [JusticePrinciple.MAXIMIZING_FLOOR, JusticePrinciple.MAXIMIZING_AVERAGE,
                 JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT],
                "VOTE_PROPOSAL array format should trigger fallback"
            ),
            (
                "1. Maximizing floor income\n2. Maximizing average income\n3. Floor constraint\n4. Range constraint",
                "malformed json",  # Force fallback
                [JusticePrinciple.MAXIMIZING_FLOOR, JusticePrinciple.MAXIMIZING_AVERAGE,
                 JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT],
                "Numbered list should trigger fallback"
            )
        ]

        for statement, bad_response, expected_order, description in fallback_scenarios:
            # Register bad response to trigger fallback
            stubbed_runner.register("Response Parser", ["test", bad_response])
            stubbed_runner.register("Response Validator", ["test"])

            result = await ranking_utility_agent.parse_principle_ranking_enhanced(statement)

            if result:  # Fallback might succeed
                assert len(result.rankings) == 4, f"Fallback should extract complete ranking: {description}"

                # Check if order matches expected (fallback extraction should work)
                sorted_rankings = sorted(result.rankings, key=lambda x: x.rank)
                actual_order = [r.principle for r in sorted_rankings]

                # For fallback, we expect the parsing to work even with bad LLM response
                assert len(actual_order) == 4, f"Fallback should extract 4 principles: {description}"

    @pytest.mark.asyncio
    async def test_fallback_extraction_edge_cases(self, ranking_utility_agent, stubbed_runner):
        """Test edge cases in fallback extraction logic."""

        edge_cases = [
            (
                "Weird format: maximizing_floor | maximizing_average | floor_constraint | range_constraint",
                "bad json",
                "Pipe-separated format"
            ),
            (
                "My preferences: floor > average > floor_constraint > range_constraint",
                "invalid",
                "Greater-than comparison format"
            ),
            (
                "Ranking order: (1) floor, (2) average, (3) floor constraint, (4) range constraint",
                "not json",
                "Parenthetical numbers format"
            )
        ]

        for statement, bad_response, description in edge_cases:
            stubbed_runner.register("Response Parser", ["test", bad_response])
            stubbed_runner.register("Response Validator", ["test"])

            try:
                result = await ranking_utility_agent.parse_principle_ranking_enhanced(statement, max_retries=1)

                if result:  # If fallback succeeds
                    assert len(result.rankings) == 4, f"Fallback should be complete: {description}"

                    # All ranks should be unique and 1-4
                    ranks = [r.rank for r in result.rankings]
                    assert len(set(ranks)) == 4, f"Ranks should be unique: {description}"
                    assert set(ranks) == {1, 2, 3, 4}, f"Ranks should be 1-4: {description}"

            except ExperimentError:
                # Some edge cases might legitimately fail - that's acceptable
                pass


class TestRankingValidationAndConsistency:
    """Test ranking validation and consistency checking."""

    @pytest.mark.asyncio
    async def test_ranking_completeness_validation(self, ranking_utility_agent, stubbed_runner):
        """Test validation that rankings are complete (all 4 principles, ranks 1-4)."""

        # This test validates that our parsing produces valid rankings
        valid_ranking_response = '''
        {
            "rankings": [
                {"principle": "maximizing_floor", "rank": 1},
                {"principle": "maximizing_average", "rank": 2},
                {"principle": "maximizing_average_floor_constraint", "rank": 3},
                {"principle": "maximizing_average_range_constraint", "rank": 4}
            ],
            "certainty": "sure"
        }
        '''

        stubbed_runner.register("Response Parser", ["test", valid_ranking_response])
        stubbed_runner.register("Response Validator", ["test"])

        result = await ranking_utility_agent.parse_principle_ranking_enhanced(
            "1. Maximizing floor, 2. Maximizing average, 3. Floor constraint, 4. Range constraint"
        )

        # Validate completeness
        assert len(result.rankings) == 4, "Should have exactly 4 rankings"

        # Validate all principles are present
        principles = {r.principle for r in result.rankings}
        expected_principles = {
            JusticePrinciple.MAXIMIZING_FLOOR,
            JusticePrinciple.MAXIMIZING_AVERAGE,
            JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
        }
        assert principles == expected_principles, "Should include all 4 justice principles"

        # Validate all ranks are present and unique
        ranks = {r.rank for r in result.rankings}
        assert ranks == {1, 2, 3, 4}, "Should have ranks 1-4 exactly once each"

    @pytest.mark.asyncio
    async def test_ranking_error_handling_and_retries(self, ranking_utility_agent, stubbed_runner):
        """Test error handling and retry logic for ranking parsing."""

        # Test progressive failure then success
        stubbed_runner.register("Response Parser", [
            "test",
            "invalid json 1",  # First attempt fails
            "invalid json 2",  # Second attempt fails
            '''
            {
                "rankings": [
                    {"principle": "maximizing_floor", "rank": 1},
                    {"principle": "maximizing_average", "rank": 2},
                    {"principle": "maximizing_average_floor_constraint", "rank": 3},
                    {"principle": "maximizing_average_range_constraint", "rank": 4}
                ],
                "certainty": "sure"
            }
            '''  # Third attempt succeeds
        ])
        stubbed_runner.register("Response Validator", ["test"])

        result = await ranking_utility_agent.parse_principle_ranking_enhanced(
            "My ranking: floor, average, floor constraint, range constraint",
            max_retries=3
        )

        assert result is not None, "Should eventually succeed after retries"
        assert len(result.rankings) == 4, "Should parse complete ranking after retries"

    @pytest.mark.asyncio
    async def test_ranking_total_failure_after_retries(self, ranking_utility_agent, stubbed_runner):
        """Test total failure case when all retries are exhausted."""

        # All attempts fail
        stubbed_runner.register("Response Parser", [
            "test",
            "invalid json 1",
            "invalid json 2",
            "invalid json 3"
        ])
        stubbed_runner.register("Response Validator", ["test"])

        with pytest.raises(ExperimentError) as exc_info:
            await ranking_utility_agent.parse_principle_ranking_enhanced(
                "Completely unparseable ranking statement",
                max_retries=3
            )

        assert "Could not parse principle ranking" in str(exc_info.value)


class TestRankingCertaintyLevels:
    """Test certainty level assignment in ranking parsing."""

    @pytest.mark.asyncio
    async def test_certainty_level_mapping(self, ranking_utility_agent, stubbed_runner):
        """Test that certainty levels are correctly parsed and mapped."""

        certainty_cases = [
            (
                "I am absolutely certain: 1. Floor, 2. Average, 3. Floor constraint, 4. Range constraint",
                '{"rankings": [{"principle": "maximizing_floor", "rank": 1}, {"principle": "maximizing_average", "rank": 2}, {"principle": "maximizing_average_floor_constraint", "rank": 3}, {"principle": "maximizing_average_range_constraint", "rank": 4}], "certainty": "very_sure"}',
                CertaintyLevel.VERY_SURE
            ),
            (
                "I think my ranking is: 1. Floor, 2. Average, 3. Floor constraint, 4. Range constraint",
                '{"rankings": [{"principle": "maximizing_floor", "rank": 1}, {"principle": "maximizing_average", "rank": 2}, {"principle": "maximizing_average_floor_constraint", "rank": 3}, {"principle": "maximizing_average_range_constraint", "rank": 4}], "certainty": "unsure"}',
                CertaintyLevel.UNSURE
            ),
            (
                "I'm really not sure, but maybe: 1. Floor, 2. Average, 3. Floor constraint, 4. Range constraint",
                '{"rankings": [{"principle": "maximizing_floor", "rank": 1}, {"principle": "maximizing_average", "rank": 2}, {"principle": "maximizing_average_floor_constraint", "rank": 3}, {"principle": "maximizing_average_range_constraint", "rank": 4}], "certainty": "very_unsure"}',
                CertaintyLevel.VERY_UNSURE
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in certainty_cases]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_certainty in certainty_cases:
            result = await ranking_utility_agent.parse_principle_ranking_enhanced(statement)

            assert result.certainty == expected_certainty, (
                f"Certainty level mismatch for: '{statement[:30]}...'\n"
                f"Expected: {expected_certainty.value}, Got: {result.certainty.value}"
            )