"""Transcript logging utilities for participant agent interactions."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

from agents import Runner
from pydantic import BaseModel, Field

from config.models import TranscriptLoggingConfig
from models import ParticipantContext

if TYPE_CHECKING:
    from experiment_agents.participant_agent import ParticipantAgent


class TranscriptInteraction(BaseModel):
    """Single captured interaction for a participant."""

    phase: str
    round: Optional[int] = None
    interaction_type: str
    timestamp: str
    instructions: Optional[str] = None
    input_prompt: Optional[str] = None
    output_response: Optional[str] = None


class AgentTranscript(BaseModel):
    """Collection of interactions for a single agent."""

    interactions: Dict[str, TranscriptInteraction] = Field(default_factory=dict)


class ExperimentTranscript(BaseModel):
    """Complete transcript payload for an experiment run."""

    experiment_metadata: Dict[str, Any]
    transcripts: Dict[str, AgentTranscript] = Field(default_factory=dict)


class TranscriptLogger:
    """Record participant prompts for later analysis."""

    def __init__(
        self,
        config: TranscriptLoggingConfig,
        experiment_id: str,
        config_path: Optional[str] = None
    ) -> None:
        self.config = config
        self.experiment_id = experiment_id
        self._call_counters: Dict[str, int] = {}
        created_at = datetime.now(timezone.utc).isoformat()
        metadata: Dict[str, Any] = {
            "experiment_id": experiment_id,
            "created_at": created_at,
            "config_file": config_path,
        }
        self._experiment_transcript = ExperimentTranscript(
            experiment_metadata=metadata,
            transcripts={}
        )
        self._logger = logging.getLogger(__name__)

    @property
    def transcript(self) -> ExperimentTranscript:
        """Expose the in-memory transcript (primarily for testing)."""
        return self._experiment_transcript

    def is_enabled(self) -> bool:
        """Return whether transcript logging is active."""
        return bool(self.config.enabled)

    def get_next_call_number(self, agent_name: str) -> int:
        """Return the next sequential call number for an agent."""
        current = self._call_counters.get(agent_name, 0) + 1
        self._call_counters[agent_name] = current
        return current

    def record_interaction(
        self,
        agent_name: str,
        phase: str,
        round_number: int,
        interaction_type: str,
        instructions: Optional[str],
        input_prompt: Optional[str],
        output_response: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> None:
        """Record a single interaction for the given agent."""
        if not self.is_enabled():
            return

        call_number = self.get_next_call_number(agent_name)
        interaction_timestamp = (timestamp or datetime.now(timezone.utc)).isoformat()
        interaction = TranscriptInteraction(
            phase=phase,
            round=round_number,
            interaction_type=interaction_type,
            timestamp=interaction_timestamp,
            instructions=instructions,
            input_prompt=input_prompt,
            output_response=output_response
        )

        agent_transcript = self._experiment_transcript.transcripts.get(agent_name)
        if agent_transcript is None:
            agent_transcript = AgentTranscript()
            self._experiment_transcript.transcripts[agent_name] = agent_transcript

        agent_transcript.interactions[f"call_{call_number}"] = interaction
        self._experiment_transcript.experiment_metadata["last_updated"] = interaction_timestamp

    def save_transcript(self, output_path: Optional[str] = None) -> str:
        """Persist the transcript to disk and return the file path."""
        if not self.is_enabled():
            raise RuntimeError("Transcript logging is disabled.")

        chosen_path = output_path or self.config.output_path
        if not chosen_path:
            chosen_path = f"transcript_{self.experiment_id}.json"

        path = Path(chosen_path)
        if not path.is_absolute():
            path = Path.cwd() / path

        path.parent.mkdir(parents=True, exist_ok=True)
        self._experiment_transcript.experiment_metadata["saved_at"] = datetime.now(timezone.utc).isoformat()

        payload = self._experiment_transcript.model_dump(mode="json")
        with path.open('w', encoding='utf-8') as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

        return str(path)


async def run_with_transcript_logging(
    participant: "ParticipantAgent",
    prompt: str,
    context: ParticipantContext,
    transcript_logger: Optional[TranscriptLogger],
    interaction_type: str
):
    """Wrapper around Runner.run that injects transcript logging."""
    instructions: Optional[str] = None
    if transcript_logger and transcript_logger.is_enabled() and transcript_logger.config.include_instructions:
        try:
            instructions = participant.get_instructions_for_context(context)
        except Exception as exc:  # pragma: no cover - defensive resilience
            transcript_logger._logger.warning(
                "Failed to capture instructions for %s: %s", participant.name, exc
            )
            instructions = None

    result = await Runner.run(participant.agent, prompt, context=context)

    if transcript_logger and transcript_logger.is_enabled():
        input_prompt = prompt if transcript_logger.config.include_input_prompts else None
        agent_response: Optional[str] = None
        if (
            transcript_logger.config.include_agent_responses
            and getattr(result, "final_output", None) is not None
        ):
            agent_response = str(result.final_output)
        try:
            phase_value = context.phase.value if getattr(context, "phase", None) else "unknown"
            round_value = getattr(context, "round_number", None)
            transcript_logger.record_interaction(
                agent_name=participant.name,
                phase=phase_value,
                round_number=round_value,
                interaction_type=interaction_type,
                instructions=instructions,
                input_prompt=input_prompt,
                output_response=agent_response
            )
        except Exception as exc:  # pragma: no cover - defensive resilience
            transcript_logger._logger.warning(
                "Failed to record transcript interaction for %s: %s", participant.name, exc
            )

    return result


__all__ = [
    "TranscriptInteraction",
    "AgentTranscript",
    "ExperimentTranscript",
    "TranscriptLogger",
    "run_with_transcript_logging",
]
