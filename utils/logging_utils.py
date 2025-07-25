"""
JSON logging system for experiment results.
"""
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from enum import Enum

from models import ExperimentResults


class ExperimentLogger:
    """Handles JSON logging of complete experiment results."""
    
    def __init__(self, output_path: str):
        self.output_path = Path(output_path)
        self.log_data = {}
        
    def log_experiment_results(self, results: ExperimentResults):
        """Save complete experiment results as JSON."""
        
        log_structure = {
            "experiment_metadata": {
                "experiment_id": results.experiment_id,
                "timestamp": results.timestamp.isoformat(),
                "total_runtime_seconds": results.total_runtime,
                "configuration": self._format_configuration(results)
            },
            "phase1_results": self._format_phase1_results(results.phase1_results),
            "phase2_results": self._format_phase2_results(results.phase2_results),
            "agent_interactions": self._extract_agent_interactions(results),
            "final_summary": self._generate_experiment_summary(results)
        }
        
        # Ensure parent directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.output_path, 'w') as f:
            json.dump(log_structure, f, indent=2, default=self._json_serializer)
    
    def _format_configuration(self, results: ExperimentResults) -> Dict[str, Any]:
        """Format configuration data for logging."""
        # Extract configuration from results if available
        # For now, create a basic structure
        return {
            "num_participants": len(results.phase1_results),
            "phase1_completed": True,
            "phase2_completed": results.phase2_results is not None
        }
    
    def _format_phase1_results(self, phase1_results) -> Dict[str, Any]:
        """Format Phase 1 results for logging."""
        formatted_results = {}
        
        for result in phase1_results:
            participant_data = {
                "initial_ranking": self._format_principle_ranking(result.initial_ranking),
                "final_ranking": self._format_principle_ranking(result.final_ranking),
                "application_rounds": [],
                "total_earnings": result.total_earnings,
                "memory_final_length": len(result.final_memory_state)
            }
            
            # Format application results
            for app_result in result.application_results:
                round_data = {
                    "round_number": app_result.round_number,
                    "principle_chosen": app_result.principle_choice.principle.value,
                    "constraint_amount": app_result.principle_choice.constraint_amount,
                    "certainty": app_result.principle_choice.certainty.value,
                    "assigned_income_class": app_result.assigned_income_class.value,
                    "earnings": app_result.earnings,
                    "alternative_earnings": app_result.alternative_earnings
                }
                participant_data["application_rounds"].append(round_data)
            
            formatted_results[result.participant_name] = participant_data
        
        return formatted_results
    
    def _format_phase2_results(self, phase2_results) -> Dict[str, Any]:
        """Format Phase 2 results for logging."""
        if not phase2_results:
            return {"completed": False}
        
        return {
            "completed": True,
            "consensus_reached": phase2_results.discussion_result.consensus_reached,
            "agreed_principle": (
                phase2_results.discussion_result.agreed_principle.principle.value 
                if phase2_results.discussion_result.agreed_principle 
                else None
            ),
            "constraint_amount": (
                phase2_results.discussion_result.agreed_principle.constraint_amount
                if phase2_results.discussion_result.agreed_principle
                else None
            ),
            "final_round": phase2_results.discussion_result.final_round,
            "num_votes_conducted": len(phase2_results.discussion_result.vote_history),
            "discussion_length": len(phase2_results.discussion_result.discussion_history),
            "payoffs": phase2_results.payoff_results,
            "vote_history": [
                {
                    "consensus_reached": vote.consensus_reached,
                    "num_votes": len(vote.votes),
                    "vote_counts": vote.vote_counts
                }
                for vote in phase2_results.discussion_result.vote_history
            ]
        }
    
    def _format_principle_ranking(self, ranking) -> Dict[str, Any]:
        """Format principle ranking for logging."""
        return {
            "rankings": [
                {
                    "principle": ranked_principle.principle.value,
                    "rank": ranked_principle.rank
                }
                for ranked_principle in ranking.rankings
            ],
            "overall_certainty": ranking.certainty.value
        }
    
    def _extract_agent_interactions(self, results: ExperimentResults) -> Dict[str, Any]:
        """Extract chronological agent interactions."""
        interactions = {
            "total_phase1_interactions": len(results.phase1_results) * 6,  # 6 major steps per participant
            "phase2_interactions": 0,
            "summary": "Detailed interaction logs would require instrumentation during execution"
        }
        
        if results.phase2_results:
            interactions["phase2_interactions"] = results.phase2_results.discussion_result.final_round
        
        return interactions
    
    def _generate_experiment_summary(self, results: ExperimentResults) -> Dict[str, Any]:
        """Generate high-level experiment summary."""
        summary = {
            "experiment_completed": True,
            "participants": [result.participant_name for result in results.phase1_results],
            "phase1_summary": {
                "all_participants_completed": len(results.phase1_results) > 0,
                "total_earnings_phase1": sum(r.total_earnings for r in results.phase1_results),
                "avg_earnings_phase1": sum(r.total_earnings for r in results.phase1_results) / len(results.phase1_results)
            }
        }
        
        if results.phase2_results:
            summary["phase2_summary"] = {
                "consensus_reached": results.phase2_results.discussion_result.consensus_reached,
                "total_discussion_rounds": results.phase2_results.discussion_result.final_round,
                "total_earnings_phase2": sum(results.phase2_results.payoff_results.values()),
                "avg_earnings_phase2": sum(results.phase2_results.payoff_results.values()) / len(results.phase2_results.payoff_results)
            }
            
            # Calculate total earnings
            total_earnings = {}
            for result in results.phase1_results:
                total_earnings[result.participant_name] = result.total_earnings
            
            for name, phase2_earnings in results.phase2_results.payoff_results.items():
                total_earnings[name] = total_earnings.get(name, 0) + phase2_earnings
            
            summary["total_earnings"] = total_earnings
            summary["winner"] = max(total_earnings.items(), key=lambda x: x[1])  # (name, earnings)
        
        return summary
    
    @staticmethod
    def _json_serializer(obj):
        """Handle datetime and other non-serializable objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Enum):
            return obj.value
        elif hasattr(obj, 'dict'):  # Pydantic models
            return obj.dict()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")