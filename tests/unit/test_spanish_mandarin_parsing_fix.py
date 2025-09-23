"""Regression tests for Spanish and Mandarin ranking parsing using production code."""

from __future__ import annotations

import json
from typing import Iterable, List, Tuple

import pytest

from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import CertaintyLevel, JusticePrinciple
from tests.utils.stubbed_runner import StubbedRunner
from utils.language_manager import SupportedLanguage, create_language_manager


def _build_ranking_payload(rankings: Iterable[Tuple[str, int]], certainty: CertaintyLevel) -> str:
    """Serialize a multilingual ranking payload as produced by the parser agent."""

    payload = {
        "rankings": [{"principle": principle, "rank": rank} for principle, rank in rankings],
        "certainty": certainty.value,
    }
    return json.dumps(payload)


@pytest.fixture
async def utility_agent_factory(monkeypatch, stubbed_runner: StubbedRunner):
    """Create initialized utility agents with language-aware configuration and stubbed runner."""

    async def _create(language: SupportedLanguage) -> UtilityAgent:
        language_manager = create_language_manager(language)
        agent = UtilityAgent(
            utility_model="stub-model",
            temperature=0.0,
            experiment_language=language.value,
            language_manager=language_manager,
        )

        async def _mock_run(agent_obj, prompt: str, context=None):
            return await stubbed_runner.run(agent_obj, prompt, context)

        monkeypatch.setattr("experiment_agents.utility_agent.run_without_tracing", _mock_run)
        stubbed_runner.register("Response Parser", ["test", "test"])
        stubbed_runner.register("Response Validator", ["test", "test"])
        await agent.async_init()
        return agent

    return _create


SPANISH_CASES: List[dict] = [
    {
        "name": "Spanish ranking with floor principle first",
        "response": """
1. Maximización del ingreso mínimo
2. Maximización del ingreso promedio
3. Maximización del ingreso promedio bajo restricción de ingreso mínimo
4. Maximización del ingreso promedio bajo restricción de rango

Certeza general: seguro
""",
        "payload": _build_ranking_payload(
            [
                ("Maximizar los ingresos mínimos", 1),
                ("Maximizar los ingresos promedio", 2),
                ("Maximizar los ingresos promedio con restricción de ingreso mínimo", 3),
                ("Maximizar los ingresos promedio con restricción de rango", 4),
            ],
            CertaintyLevel.SURE,
        ),
        "expected": [
            JusticePrinciple.MAXIMIZING_FLOOR,
            JusticePrinciple.MAXIMIZING_AVERAGE,
            JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
        ],
        "certainty": CertaintyLevel.SURE,
    },
    {
        "name": "Spanish ranking with constraint principle first",
        "response": """
1. Maximización del ingreso promedio bajo restricción de ingreso mínimo
2. Maximización del ingreso mínimo
3. Maximización del ingreso promedio
4. Maximización del ingreso promedio bajo restricción de rango

Certeza general: muy seguro
""",
        "payload": _build_ranking_payload(
            [
                ("Maximizar los ingresos promedio con restricción de ingreso mínimo", 1),
                ("Maximizar los ingresos mínimos", 2),
                ("Maximizar los ingresos promedio", 3),
                ("Maximizar los ingresos promedio con restricción de rango", 4),
            ],
            CertaintyLevel.VERY_SURE,
        ),
        "expected": [
            JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            JusticePrinciple.MAXIMIZING_FLOOR,
            JusticePrinciple.MAXIMIZING_AVERAGE,
            JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
        ],
        "certainty": CertaintyLevel.VERY_SURE,
    },
]


MANDARIN_CASES: List[dict] = [
    {
        "name": "Mandarin ranking with floor first",
        "response": """
1. 最低收入最大化
2. 平均收入最大化
3. 在最低收入约束条件下最大化平均收入
4. 在范围约束条件下最大化平均收入

总体确定性：sure
""",
        "payload": _build_ranking_payload(
            [
                ("最低收入最大化", 1),
                ("平均收入最大化", 2),
                ("在最低收入约束条件下最大化平均收入", 3),
                ("在范围约束条件下最大化平均收入", 4),
            ],
            CertaintyLevel.SURE,
        ),
        "expected": [
            JusticePrinciple.MAXIMIZING_FLOOR,
            JusticePrinciple.MAXIMIZING_AVERAGE,
            JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
        ],
        "certainty": CertaintyLevel.SURE,
    },
    {
        "name": "Mandarin ranking with constraint first",
        "response": """
1. 在最低收入约束条件下最大化平均收入
2. 最低收入最大化
3. 平均收入最大化
4. 在范围约束条件下最大化平均收入

总体确定性：very_sure
""",
        "payload": _build_ranking_payload(
            [
                ("在最低收入约束条件下最大化平均收入", 1),
                ("最低收入最大化", 2),
                ("平均收入最大化", 3),
                ("在范围约束条件下最大化平均收入", 4),
            ],
            CertaintyLevel.VERY_SURE,
        ),
        "expected": [
            JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            JusticePrinciple.MAXIMIZING_FLOOR,
            JusticePrinciple.MAXIMIZING_AVERAGE,
            JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
        ],
        "certainty": CertaintyLevel.VERY_SURE,
    },
]


@pytest.mark.asyncio
async def test_spanish_parsing_with_multilingual_normalization(
    utility_agent_factory,
    stubbed_runner: StubbedRunner,
):
    agent = await utility_agent_factory(SupportedLanguage.SPANISH)

    for case in SPANISH_CASES:
        stubbed_runner.register("Response Parser", [case["payload"]] * 3)
        ranking = await agent.parse_principle_ranking_enhanced(case["response"])

        assert ranking.certainty == case["certainty"], case["name"]
        ordered = sorted(ranking.rankings, key=lambda item: item.rank)
        assert [item.principle for item in ordered] == case["expected"], case["name"]


@pytest.mark.asyncio
async def test_mandarin_parsing_with_multilingual_normalization(
    utility_agent_factory,
    stubbed_runner: StubbedRunner,
):
    agent = await utility_agent_factory(SupportedLanguage.MANDARIN)

    for case in MANDARIN_CASES:
        stubbed_runner.register("Response Parser", [case["payload"]] * 3)
        ranking = await agent.parse_principle_ranking_enhanced(case["response"])

        assert ranking.certainty == case["certainty"], case["name"]
        ordered = sorted(ranking.rankings, key=lambda item: item.rank)
        assert [item.principle for item in ordered] == case["expected"], case["name"]


if __name__ == "__main__":  # pragma: no cover - convenience guard
    pytest.main([__file__, "-v"])
