from datetime import datetime

from models import (
    ExperimentResults,
    Phase1Results,
    Phase2Results,
    GroupDiscussionResult,
    PrincipleRanking,
    RankedPrinciple,
    JusticePrinciple,
    CertaintyLevel,
    PrincipleChoice,
)
from utils.logging.result_summary import build_experiment_summary


def _make_principle_ranking(primary: JusticePrinciple) -> PrincipleRanking:
    ordering = [
        primary,
        JusticePrinciple.MAXIMIZING_AVERAGE,
        JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
        JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
    ]
    ranked = [
        RankedPrinciple(principle=principle, rank=index + 1)
        for index, principle in enumerate(ordering)
    ]
    return PrincipleRanking(rankings=ranked, certainty=CertaintyLevel.SURE)


def _make_phase1_result(name: str, earnings: float) -> Phase1Results:
    return Phase1Results(
        participant_name=name,
        initial_ranking=_make_principle_ranking(JusticePrinciple.MAXIMIZING_FLOOR),
        post_explanation_ranking=_make_principle_ranking(JusticePrinciple.MAXIMIZING_FLOOR),
        application_results=[],
        final_ranking=_make_principle_ranking(JusticePrinciple.MAXIMIZING_FLOOR),
        total_earnings=earnings,
        final_memory_state="Learned about justice principles",
    )


def test_summary_builder_outputs_expected_shape():
    participants = [
        _make_phase1_result("Alice", 10.5),
        _make_phase1_result("Bob", 9.25),
    ]

    discussion = GroupDiscussionResult(
        consensus_reached=True,
        agreed_principle=PrincipleChoice.create_for_parsing(
            JusticePrinciple.MAXIMIZING_FLOOR,
            certainty=CertaintyLevel.SURE,
        ),
        final_round=3,
        discussion_history="Alice and Bob discussed fairness",
        vote_history=[],
    )

    phase2 = Phase2Results(
        discussion_result=discussion,
        payoff_results={"Alice": 4.0, "Bob": 5.0},
        final_rankings={
            "Alice": _make_principle_ranking(JusticePrinciple.MAXIMIZING_FLOOR),
            "Bob": _make_principle_ranking(JusticePrinciple.MAXIMIZING_FLOOR),
        },
    )

    experiment_results = ExperimentResults(
        experiment_id="test-exp",
        timestamp=datetime.utcnow(),
        total_runtime=12.34,
        phase1_results=participants,
        phase2_results=phase2,
        seed_used=42,
        seed_source="explicit",
    )

    summary = build_experiment_summary(experiment_results, config_path="config/default_config.yaml")

    assert summary["experiment_id"] == "test-exp"
    assert summary["seed"]["value"] == 42
    assert summary["phase1"]["participant_count"] == 2
    assert summary["phase2"]["consensus_reached"] is True
    participant_names = {entry["name"] for entry in summary["participants"]}
    assert participant_names == {"Alice", "Bob"}
    alice_summary = next(entry for entry in summary["participants"] if entry["name"] == "Alice")
    assert alice_summary["total_earnings"] == round(10.5 + 4.0, 4)
