"""
Participant agent system for the Frohlich Experiment.
"""
from agents import Agent, RunContextWrapper, ModelSettings, Runner, function_tool

from config import AgentConfiguration
from models import ParticipantContext, ExperimentPhase
from utils.model_provider import create_model_config_with_temperature_detection, create_model_settings, create_model_config_sync
from utils.dynamic_model_capabilities import create_agent_with_temperature_retry
import asyncio
import logging
from typing import List, Optional, Any


# Tool factory function for creating localized voting tools with conditional logic
def create_voting_tool(language_manager, experiment_config):
    """Create a localized voting tool with built-in conditional logic."""
    
    @function_tool
    async def request_group_vote(ctx: RunContextWrapper[Any]) -> str:
        """Request that the group proceed to formal voting on justice principles."""
        
        # Log that the tool was called
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🗳️ VOTING TOOL CALLED by agent in phase {getattr(ctx.context, 'phase', 'unknown')} with role {getattr(ctx.context, 'role_description', 'unknown')}")
        
        # Get current context to determine if voting is allowed
        from models import ExperimentPhase
        current_context = ctx.context
        
        # Only allow during Phase 2 group discussion (not memory updates or Phase 1)
        if (current_context.phase != ExperimentPhase.PHASE_2):
            return "Voting is not available in this phase of the experiment."
        
        # Block during memory updates (role_description is "MemoryUpdate")
        if current_context.role_description == "MemoryUpdate":
            return "Voting is not available during memory updates."
        
        # Tool is being called during Phase 2 group discussion - proceed with voting
        return language_manager.get_voting_tool_confirmation()
    
    # Set localized tool description
    request_group_vote.__doc__ = language_manager.get_voting_tool_description()
    
    return request_group_vote


class ParticipantAgent:
    """Wrapper for participant agent with memory management capabilities and dynamic temperature detection."""
    
    def __init__(self, config: AgentConfiguration, experiment_config=None, language_manager=None):
        self.config = config
        self.experiment_config = experiment_config
        self.language_manager = language_manager
        self.logger = logging.getLogger(__name__)
        
        # We'll initialize the agent asynchronously in async_init
        self.agent = None
        self.temperature_info = None
        self._initialization_complete = False

    async def async_init(self):
        """Asynchronously initialize the agent with dynamic temperature detection."""
        if self._initialization_complete:
            return
        
        # Create tools statically if in complex mode
        tools = []
        if (self.experiment_config and 
            self.experiment_config.voting_detection_mode == "complex"):
            # Create the voting tool with built-in conditional logic
            voting_tool = create_voting_tool(self.language_manager, self.experiment_config)
            tools.append(voting_tool)
            self.logger.info(f"🗳️ VOTING TOOL REGISTERED for {self.config.name}: {voting_tool.__name__ if hasattr(voting_tool, '__name__') else 'voting_tool'}")
        else:
            self.logger.info(f"📋 No voting tools registered for {self.config.name} (mode: {getattr(self.experiment_config, 'voting_detection_mode', 'None') if self.experiment_config else 'None'})")
        
        # Prepare base agent kwargs (without model and model_settings) 
        base_kwargs = {
            "name": self.config.name,
            "instructions": lambda ctx, agent: _generate_dynamic_instructions(ctx, agent, self.config, self.experiment_config, self.language_manager),
            "tools": tools
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
        """Agent updates their own memory based on prompt using minimal context."""
        # Ensure agent is initialized
        await self.async_init()
        
        # Create a specialized memory update context that uses minimal formatting
        temp_context = ParticipantContext(
            name=self.config.name,
            role_description="MemoryUpdate",  # Special role for memory context detection
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


async def create_participant_agent(config: AgentConfiguration, language_manager=None) -> ParticipantAgent:
    """Create a participant agent with the given configuration."""
    agent = ParticipantAgent(config, language_manager=language_manager)
    await agent.async_init()
    return agent


async def create_participant_agents_with_dynamic_temperature(
    configs: List[AgentConfiguration],
    experiment_config=None,
    language_manager=None
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
            agent = ParticipantAgent(config, experiment_config, language_manager)
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
    config: AgentConfiguration,
    experiment_config=None,
    language_manager=None
) -> str:
    """Generate context-aware instructions including memory, bank balance, etc."""
    
    context = ctx.context
    
    # Check if this is a memory update context and use minimal formatting
    if context.role_description == "MemoryUpdate":
        return language_manager.format_memory_context(
            name=context.name,
            bank_balance=context.bank_balance,
            personality=config.personality
        )
    
    # Standard context formatting for regular operations
    # Format memory for display using language manager
    memory_content = context.memory if context.memory.strip() else None
    formatted_memory = language_manager.format_memory_section(memory_content or "")
    
    # Get phase-specific instructions using language manager
    phase_instructions = _get_phase_specific_instructions_translated(
        context.phase, context.round_number, language_manager, experiment_config
    )
    
    # Format everything using language manager with config-aware explanation inclusion
    return language_manager.format_context_info(
        name=context.name,
        role_description=context.role_description,
        bank_balance=context.bank_balance,
        phase=context.phase.value.replace('_', ' ').title(),
        round_number=context.round_number,
        formatted_memory=formatted_memory,
        personality=config.personality,
        phase_instructions=phase_instructions,
        experiment_config=experiment_config
    )


# Removed _get_conditional_tools - now using static tool registration with internal conditional logic


def _get_phase_specific_instructions_translated(phase: ExperimentPhase, round_number: int, language_manager, experiment_config=None) -> str:
    """Get instructions specific to the current phase and round using language manager."""
    
    if phase == ExperimentPhase.PHASE_1:
        return language_manager.get_phase1_instructions(round_number)
    elif phase == ExperimentPhase.PHASE_2:
        # Pass voting detection mode to language manager for Phase 2
        voting_mode = getattr(experiment_config, 'voting_detection_mode', 'simple') if experiment_config else 'simple'
        return language_manager.get_phase2_instructions(round_number, voting_mode)
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