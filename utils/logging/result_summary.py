"""Utilities for building structured experiment summary payloads."""
from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Dict, List, Optional

from models import ExperimentResults


def build_experiment_summary(results: ExperimentResults, config_path: Optional[str] = None) -> Dict[str, object]:
    """Create a structured summary dictionary from experiment results."""
    phase1_stats = _summarize_phase1(results)
    phase2_stats = _summarize_phase2(results)
    participants = _summarize_participants(results)

    return {
        "experiment_id": results.experiment_id,
        "timestamp": results.timestamp.isoformat() if isinstance(results.timestamp, _dt.datetime) else str(results.timestamp),
        "total_runtime_seconds": round(results.total_runtime, 4),
        "config_file": Path(config_path).name if config_path else None,
        "seed": {
            "value": results.seed_used,
            "source": results.seed_source,
        },
        "phase1": phase1_stats,
        "phase2": phase2_stats,
        "participants": participants,
    }


def _summarize_phase1(results: ExperimentResults) -> Dict[str, object]:
    participant_results = results.phase1_results
    total_earnings = sum(r.total_earnings for r in participant_results)

    return {
        "participant_count": len(participant_results),
        "average_earnings": round(total_earnings / len(participant_results), 4) if participant_results else 0.0,
    }


def _summarize_phase2(results: ExperimentResults) -> Dict[str, object]:
    discussion = results.phase2_results.discussion_result
    agreed_principle = None
    if discussion.agreed_principle:
        agreed_principle = {
            "name": discussion.agreed_principle.principle.value,
            "constraint": discussion.agreed_principle.constraint_amount,
        }

    return {
        "consensus_reached": discussion.consensus_reached,
        "agreed_principle": agreed_principle,
        "final_round": discussion.final_round,
    }


def _summarize_participants(results: ExperimentResults) -> List[Dict[str, object]]:
    payoffs = results.phase2_results.payoff_results
    participant_rows: List[Dict[str, object]] = []

    for phase1 in results.phase1_results:
        phase1_earnings = round(phase1.total_earnings, 4)
        phase2_earnings = round(payoffs.get(phase1.participant_name, 0.0), 4)
        participant_rows.append(
            {
                "name": phase1.participant_name,
                "phase1_earnings": phase1_earnings,
                "phase2_earnings": phase2_earnings,
                "total_earnings": round(phase1_earnings + phase2_earnings, 4),
            }
        )

    # Include participants that only appear in Phase 2 (defensive)
    for name, phase2_earnings in payoffs.items():
        if any(row["name"] == name for row in participant_rows):
            continue
        participant_rows.append(
            {
                "name": name,
                "phase1_earnings": 0.0,
                "phase2_earnings": round(phase2_earnings, 4),
                "total_earnings": round(phase2_earnings, 4),
            }
        )

    return sorted(participant_rows, key=lambda row: row["name"].lower())
