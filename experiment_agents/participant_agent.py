"""
Participant agent system for the Frohlich Experiment.
"""
from agents import Agent, RunContextWrapper, ModelSettings, Runner

from config import AgentConfiguration
from models import ParticipantContext, ExperimentPhase
from utils.model_provider import create_model_config_with_temperature_detection, create_model_settings, create_model_config_sync
from utils.dynamic_model_capabilities import create_agent_with_temperature_retry
from utils.language_manager import get_language_manager
import asyncio
import logging
from typing import List


# This will be replaced by dynamic language manager calls


class ParticipantAgent:
    """Wrapper for participant agent with memory management capabilities and dynamic temperature detection."""
    
    def __init__(self, config: AgentConfiguration):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # We'll initialize the agent asynchronously in async_init
        self.agent = None
        self.temperature_info = None
        self._initialization_complete = False

    async def async_init(self):
        """Asynchronously initialize the agent with dynamic temperature detection."""
        if self._initialization_complete:
            return
        
        # Prepare base agent kwargs (without model and model_settings)
        base_kwargs = {
            "name": self.config.name,
            "instructions": lambda ctx, agent: _generate_dynamic_instructions(ctx, agent, self.config),
        }
        
        # Use dynamic temperature retry system
        try:
            self.logger.info(f"Creating agent {self.config.name} with dynamic temperature detection")
            
            self.agent, self.temperature_info = await create_agent_with_temperature_retry(
                agent_class=Agent[ParticipantContext],
                model_string=self.config.model,
                temperature=self.config.temperature,
                agent_kwargs=base_kwargs
            )
            
            # Log temperature status
            self._log_temperature_status()
            
            self._initialization_complete = True
            self.logger.info(f"✅ Successfully initialized agent {self.config.name}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize agent {self.config.name}: {e}")
            raise e
    
    def _log_temperature_status(self):
        """Log temperature detection status."""
        if not self.temperature_info:
            return
            
        temp_info = self.temperature_info
        detection_method = temp_info.get('detection_method', 'unknown')
        
        if temp_info.get("supports_temperature", False):
            # Temperature supported
            effective_temp = temp_info.get('effective_temperature')
            if effective_temp is not None:
                self.logger.info(
                    f"✅ {self.config.name}: Temperature {effective_temp} active "
                    f"(method: {detection_method})"
                )
            else:
                self.logger.info(
                    f"✅ {self.config.name}: Temperature support confirmed, none requested "
                    f"(method: {detection_method})"
                )
        else:
            # Temperature not supported
            requested = temp_info.get('requested_temperature')
            was_retried = temp_info.get('was_retried', False)
            
            if was_retried:
                self.logger.warning(
                    f"🔄 {self.config.name}: Temperature {requested} not supported, "
                    f"automatically retried without temperature (method: {detection_method})"
                )
            else:
                self.logger.warning(
                    f"❌ {self.config.name}: Temperature {requested} not supported, "
                    f"using default behavior (method: {detection_method})"
                )
    
    @property
    def name(self) -> str:
        if self.agent is None:
            return self.config.name
        return self.agent.name
    
    async def update_memory(self, prompt: str, current_bank_balance: float = 0.0) -> str:
        """Agent updates their own memory based on prompt."""
        # Ensure agent is initialized
        await self.async_init()
        
        # Create a temporary context just for memory update
        temp_context = ParticipantContext(
            name=self.config.name,
            role_description="Memory update",
            bank_balance=current_bank_balance,
            memory="",
            round_number=0,
            phase=ExperimentPhase.PHASE_1,
            memory_character_limit=self.config.memory_character_limit
        )
        
        result = await Runner.run(self.agent, prompt, context=temp_context)
        return result.final_output
    
    def clone(self, **kwargs):
        """Clone the underlying agent with modifications."""
        if self.agent is None:
            raise RuntimeError("Agent not initialized. Call async_init() first.")
        return self.agent.clone(**kwargs)


async def create_participant_agent(config: AgentConfiguration) -> ParticipantAgent:
    """Create a participant agent with the given configuration."""
    agent = ParticipantAgent(config)
    await agent.async_init()
    return agent


async def create_participant_agents_with_dynamic_temperature(
    configs: List[AgentConfiguration]
) -> List[ParticipantAgent]:
    """
    Create multiple participant agents with dynamic temperature detection and retry.
    """
    if not configs:
        return []
    
    logger = logging.getLogger(__name__)
    logger.info(f"Creating {len(configs)} participant agents with dynamic temperature detection...")
    
    # Create agents with dynamic temperature detection
    agents = []
    for config in configs:
        try:
            logger.info(f"Creating agent: {config.name} (model: {config.model}, temp: {config.temperature})")
            agent = ParticipantAgent(config)
            await agent.async_init()
            agents.append(agent)
        except Exception as e:
            logger.error(f"Failed to create agent {config.name}: {e}")
            raise e
    
    logger.info(f"✅ Successfully created {len(agents)} participant agents")
    return agents


def _generate_dynamic_instructions(
    ctx: RunContextWrapper[ParticipantContext], 
    agent: Agent, 
    config: AgentConfiguration
) -> str:
    """Generate context-aware instructions including memory, bank balance, etc."""
    
    language_manager = get_language_manager()
    context = ctx.context
    
    # Format memory for display using language manager
    memory_content = context.memory if context.memory.strip() else None
    formatted_memory = language_manager.format_memory_section(memory_content or "")
    
    # Get phase-specific instructions using language manager
    phase_instructions = _get_phase_specific_instructions_translated(
        context.phase, context.round_number, language_manager
    )
    
    # Format everything using language manager
    return language_manager.format_context_info(
        name=context.name,
        role_description=context.role_description,
        bank_balance=context.bank_balance,
        phase=context.phase.value.replace('_', ' ').title(),
        round_number=context.round_number,
        formatted_memory=formatted_memory,
        personality=config.personality,
        phase_instructions=phase_instructions
    )


def _get_phase_specific_instructions_translated(phase: ExperimentPhase, round_number: int, language_manager) -> str:
    """Get instructions specific to the current phase and round using language manager."""
    
    if phase == ExperimentPhase.PHASE_1:
        return language_manager.get_phase1_instructions(round_number)
    elif phase == ExperimentPhase.PHASE_2:
        return language_manager.get_phase2_instructions(round_number)
    else:
        return language_manager.get_prompt("fallback", "default_phase_instructions")


# Old hardcoded function replaced by _get_phase_specific_instructions_translated()




def update_participant_context(
    context: ParticipantContext,
    balance_change: float = 0.0,
    new_round: int = None,
    new_phase: ExperimentPhase = None
) -> ParticipantContext:
    """Update participant context with new information (memory handled separately)."""
    
    # Create updated context
    updated_context = ParticipantContext(
        name=context.name,
        role_description=context.role_description,
        bank_balance=context.bank_balance + balance_change,
        memory=context.memory,  # Memory updated separately by agent
        round_number=new_round if new_round is not None else context.round_number,
        phase=new_phase if new_phase is not None else context.phase,
        memory_character_limit=context.memory_character_limit
    )
    
    return updated_context