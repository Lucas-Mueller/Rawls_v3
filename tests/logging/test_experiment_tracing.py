"""Trace metadata and integration coverage for the experiment manager."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from config import ExperimentConfiguration
from core.experiment_manager import FrohlichExperimentManager
from models import (
    Phase1Results,
    Phase2Results,
    GroupDiscussionResult,
    ApplicationResult,
)
from models.principle_types import (
    PrincipleRanking,
    RankedPrinciple,
    PrincipleChoice,
    JusticePrinciple,
    CertaintyLevel,
)
from models.experiment_types import IncomeDistribution, IncomeClass


class StubParticipant:
    def __init__(self, cfg):
        self.name = cfg.name
        self.config = cfg
        self.agent = SimpleNamespace(name=cfg.name)

    async def update_memory(self, *_args, **_kwargs):
        return "memory"


class StubUtilityAgent:
    def __init__(self, *args, **kwargs):
        pass

    async def async_init(self):  # pragma: no cover - behaviour verified via manager tests
        return None

    async def validate_consensus_against_discussion(self, *_args, **_kwargs):
        return True, []


class StubAgentLogger:
    def initialize_experiment(self, *_args, **_kwargs):
        return None

    def set_seed_info(self, *_args, **_kwargs):
        return None

    def initialize_voting_history(self):
        return None


class StubPhase1Manager:
    def __init__(self, participants, *_args, **_kwargs):
        self.participants = participants

    async def run_phase1(self, *_args, **_kwargs):
        ranking = PrincipleRanking(
            rankings=[
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=1),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=2),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=3),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4),
            ],
            certainty=CertaintyLevel.SURE,
        )

        application = ApplicationResult(
            round_number=1,
            principle_choice=PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE,
                constraint_amount=None,
                certainty=CertaintyLevel.SURE,
            ),
            chosen_distribution=IncomeDistribution(high=30_000, medium_high=25_000, medium=20_000, medium_low=15_000, low=10_000),
            assigned_income_class=IncomeClass.HIGH,
            earnings=12_000.0,
            alternative_earnings={},
            alternative_earnings_same_class={},
        )

        return [
            Phase1Results(
                participant_name=participant.name,
                initial_ranking=ranking,
                post_explanation_ranking=ranking,
                application_results=[application],
                final_ranking=ranking,
                total_earnings=12_000.0,
                final_memory_state="memory",
            )
            for participant in self.participants
        ]


class StubPhase2Manager:
    def __init__(self, participants, *_args, **_kwargs):
        self.participants = participants

    async def run_phase2(self, _config, phase1_results, *_args, **_kwargs):
        principle_choice = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE,
            constraint_amount=None,
            certainty=CertaintyLevel.SURE,
        )
        discussion = GroupDiscussionResult(
            consensus_reached=True,
            agreed_principle=principle_choice,
            final_round=1,
            discussion_history="generated",
            vote_history=[],
        )

        payoff_results = {result.participant_name: 15_000.0 for result in phase1_results}
        final_rankings = {result.participant_name: result.final_ranking for result in phase1_results}

        return Phase2Results(
            discussion_result=discussion,
            payoff_results=payoff_results,
            final_rankings=final_rankings,
        )


@pytest.mark.asyncio
async def test_experiment_trace_metadata(monkeypatch):
    config = ExperimentConfiguration.from_yaml("config/default_config.yaml")
    config.agents = config.agents[:2]
    config.language = "Spanish"

    participant_agents = [StubParticipant(cfg) for cfg in config.agents]

    async def fake_create_participants(self):
        return participant_agents

    monkeypatch.setattr(FrohlichExperimentManager, "_create_participants", fake_create_participants)
    monkeypatch.setattr("core.experiment_manager.UtilityAgent", StubUtilityAgent)
    monkeypatch.setattr("core.experiment_manager.Phase1Manager", StubPhase1Manager)
    monkeypatch.setattr("core.experiment_manager.Phase2Manager", StubPhase2Manager)
    monkeypatch.setattr("core.experiment_manager.build_experiment_summary", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        FrohlichExperimentManager,
        "_set_general_logging_info",
        lambda self, _results: None,
    )
    monkeypatch.setattr(
        FrohlichExperimentManager,
        "_set_fallback_general_info",
        lambda self, _results: None,
    )

    captured_trace = {}

    class DummyTrace:
        def __init__(self, name: str, metadata: dict) -> None:
            captured_trace["name"] = name
            captured_trace["metadata"] = metadata

        def __enter__(self):
            return SimpleNamespace(trace_id="trace-12345")

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("core.experiment_manager.trace", DummyTrace)

    language_manager = SimpleNamespace(
        get=lambda key, **kwargs: key,
        format_memory_section=lambda memory, **kwargs: memory,
        get_localized_principle_name=lambda principle, **kwargs: str(principle),
        get_localized_principle_description=lambda principle, **kwargs: f"Description for {principle}",
        format_number=lambda num, **kwargs: str(num),
        format_currency=lambda amount, **kwargs: f"${amount:,.2f}",
        get_phase1_instructions=lambda round_number, **kwargs: f"Phase 1 instructions for round {round_number}",
        get_phase2_instructions=lambda round_number, max_rounds=5, **kwargs: f"Phase 2 instructions for round {round_number} of {max_rounds}",
        get_parser_instructions=lambda **kwargs: "Parser instructions",
        get_validator_instructions=lambda **kwargs: "Validator instructions",
        get_experiment_explanation=lambda **kwargs: "Experiment explanation",
        get_prompt=lambda category, prompt_key, **kwargs: f"{category}_{prompt_key}",
        get_message=lambda category, message_group, message_key, **kwargs: f"{category}_{message_group}_{message_key}",
        format_context_info=lambda name, role_description, bank_balance, **kwargs: f"Context for {name}",
        format_memory_context=lambda name, bank_balance, personality, **kwargs: f"Memory context for {name}",
        format_phase2_discussion_instructions=lambda **kwargs: "Phase 2 discussion instructions",
        get_principle_list_formatted=lambda list_type="detailed", **kwargs: "Formatted principle list",
        get_two_stage_principle_selection_prompt=lambda **kwargs: "Two stage principle selection prompt",
        get_two_stage_amount_specification_prompt=lambda principle_name, **kwargs: f"Amount specification for {principle_name}",
        get_justice_principle_name=lambda principle_key, **kwargs: str(principle_key),
        get_certainty_level_name=lambda certainty_key, **kwargs: str(certainty_key),
        get_phase_name=lambda phase_key, **kwargs: str(phase_key),
        format_amount_display=lambda amount, **kwargs: f"${amount:,}",
        get_two_stage_timeout_message=lambda **kwargs: "Timeout message",
        get_validation_message=lambda validation_key, **kwargs: f"Validation: {validation_key}",
        get_error_message=lambda error_key, **kwargs: f"Error: {error_key}",
        get_success_message=lambda success_key, **kwargs: f"Success: {success_key}",
        get_status_message=lambda status_key, **kwargs: f"Status: {status_key}",
        get_principle_choice_parsing_prompt=lambda response, **kwargs: f"Parse choice from: {response}",
        get_principle_ranking_parsing_prompt=lambda response, **kwargs: f"Parse ranking from: {response}",
        get_constraint_re_prompt=lambda participant_name, principle_name, constraint_type, **kwargs: f"Constraint re-prompt for {participant_name}",
        get_format_improvement_prompt=lambda response, parse_type, **kwargs: f"Format improvement for {parse_type}",
        get_two_stage_error_message=lambda error_type, attempt, max_attempts, **kwargs: f"Error {error_type}, attempt {attempt}/{max_attempts}",
        get_justice_principle_name_english=lambda principle_key, **kwargs: str(principle_key),
        get_certainty_level_name_english=lambda certainty_key, **kwargs: str(certainty_key),
    )
    manager = FrohlichExperimentManager(config, "config/default_config.yaml", language_manager=language_manager)
    manager.agent_logger = StubAgentLogger()

    results = await manager.run_complete_experiment()

    metadata = captured_trace["metadata"]
    assert metadata["experiment_id"] == manager.experiment_id
    assert metadata["participant_count"] == str(len(config.agents))
    assert metadata["language"] == config.language
    expected_names = ", ".join(agent.name for agent in config.agents)
    assert metadata["participant_names"] == expected_names
    assert isinstance(results.phase1_results, list) and results.phase1_results
    assert results.phase2_results.discussion_result.consensus_reached is True
