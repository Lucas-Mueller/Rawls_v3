# FROHLICH EXPERIMENT: MULTI-PHASE IMPLEMENTATION PLAN

Based on my analysis of the agents_sdk documentation and your requirements, here's a comprehensive implementation plan for the multi-agent justice principles experiment system.

## **PHASE 1: CORE FOUNDATION & DATA MODELS**

### **1.1 Project Structure & Dependencies**
```
frohlich_experiment/
├── main.py                    # Single entry point file
├── config/
│   ├── __init__.py
│   ├── models.py             # Pydantic configuration models
│   └── default_config.yaml   # Test configuration
├── core/
│   ├── __init__.py
│   ├── experiment_manager.py # Main experiment orchestrator
│   ├── phase1_manager.py     # Phase 1 execution logic
│   ├── phase2_manager.py     # Phase 2 execution logic
│   └── distribution_generator.py # Dynamic distribution creation
├── agents/
│   ├── __init__.py
│   ├── participant_agent.py  # Main experiment participant
│   ├── utility_agent.py      # Response parsing/validation
│   └── agent_factory.py      # Agent creation utilities
├── models/
│   ├── __init__.py
│   ├── experiment_types.py   # Core experiment data structures
│   ├── principle_types.py    # Justice principle models
│   └── response_types.py     # Agent response schemas
└── utils/
    ├── __init__.py
    ├── memory_manager.py     # Agent memory handling
    ├── logging_utils.py      # JSON logging system
    └── validation_utils.py   # Response validation helpers
```

### **1.2 Core Data Models (Pydantic)**
```python
# models/principle_types.py
class JusticePrinciple(str, Enum):
    MAXIMIZING_FLOOR = "maximizing_floor"
    MAXIMIZING_AVERAGE = "maximizing_average" 
    MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT = "maximizing_average_floor_constraint"
    MAXIMIZING_AVERAGE_RANGE_CONSTRAINT = "maximizing_average_range_constraint"

class PrincipleChoice(BaseModel):
    principle: JusticePrinciple
    constraint_amount: Optional[int] = None  # Required for constraint principles
    certainty: CertaintyLevel
    reasoning: Optional[str] = None

class PrincipleRanking(BaseModel):
    rankings: List[RankedPrinciple]  # Ordered list, best to worst
    certainty_scores: Dict[JusticePrinciple, CertaintyLevel]

# models/experiment_types.py  
class IncomeDistribution(BaseModel):
    high: int
    medium_high: int  
    medium: int
    medium_low: int
    low: int
    
class DistributionSet(BaseModel):
    distributions: List[IncomeDistribution]  # Always 4 distributions
    multiplier: float  # Applied to base distribution

class ParticipantContext(BaseModel):
    name: str
    role_description: str
    bank_balance: float
    memory: str  # CRITICAL: Continuous across Phase 1 and Phase 2
    round_number: int
    phase: ExperimentPhase
    max_memory_length: int = 5000
```

### **1.3 Configuration System**
```python
# config/models.py
class AgentConfiguration(BaseModel):
    name: str
    personality: str
    model: str = "o3-mini"
    temperature: float = 0.7
    reasoning_enabled: bool = True
    memory_length: int = 5000

class ExperimentConfiguration(BaseModel):
    agents: List[AgentConfiguration]
    phase2_rounds: int = 10
    distribution_range_phase1: Tuple[float, float] = (0.5, 2.0)
    distribution_range_phase2: Tuple[float, float] = (0.5, 2.0)
    
    @classmethod
    def from_yaml(cls, path: str) -> 'ExperimentConfiguration':
        # YAML loading implementation
```

**Deliverable:** Complete data model foundation with type safety and validation

---

## **PHASE 2: UTILITY AGENT & VALIDATION SYSTEM**

### **2.1 Utility Agent Implementation**
```python
# agents/utility_agent.py
class UtilityAgent:
    def __init__(self):
        self.parser_agent = Agent(
            name="Response Parser",
            instructions=self._get_parser_instructions(),
            output_type=ParsedResponse
        )
        
        self.validator_agent = Agent(
            name="Response Validator", 
            instructions=self._get_validator_instructions(),
            output_type=ValidationResult
        )
    
    async def parse_principle_choice(self, response: str) -> PrincipleChoice:
        """Parse principle choice from participant response"""
        
    async def parse_principle_ranking(self, response: str) -> PrincipleRanking:
        """Parse principle ranking from participant response"""
        
    async def validate_constraint_specification(self, choice: PrincipleChoice) -> bool:
        """Validate constraint principles have required amounts"""
        
    async def extract_vote_from_statement(self, statement: str) -> Optional[VoteProposal]:
        """Detect if participant is proposing a vote"""
```

### **2.2 Distribution Generation System**
```python
# core/distribution_generator.py
class DistributionGenerator:
    BASE_DISTRIBUTION = IncomeDistribution(
        high=32000, medium_high=27000, medium=24000,
        medium_low=13000, low=12000
    )
    
    @staticmethod
    def generate_dynamic_distribution(multiplier_range: Tuple[float, float]) -> DistributionSet:
        """Generate 4 distributions with random multiplier"""
        
    @staticmethod  
    def apply_principle_to_distributions(
        distributions: List[IncomeDistribution],
        principle: PrincipleChoice
    ) -> Tuple[IncomeDistribution, str]:
        """Apply justice principle logic and return chosen distribution + explanation"""
```

**Deliverable:** Robust response parsing and validation system with dynamic distribution generation

---

## **PHASE 3: PARTICIPANT AGENT SYSTEM**

### **3.1 Memory Management**
```python
# utils/memory_manager.py
class MemoryManager:
    @staticmethod
    def update_memory(
        current_memory: str, 
        new_info: str, 
        max_length: int
    ) -> str:
        """Intelligent memory truncation maintaining important information"""
        
    @staticmethod
    def format_memory_prompt(memory: str, phase: ExperimentPhase) -> str:
        """Format memory for agent consumption"""
```

### **3.2 Participant Agent Implementation**
```python
# agents/participant_agent.py
def create_participant_agent(config: AgentConfiguration) -> Agent[ParticipantContext]:
    return Agent[ParticipantContext](
        name=config.name,
        instructions=lambda ctx, agent: _generate_dynamic_instructions(ctx, agent, config),
        model=config.model,
        model_settings=ModelSettings(temperature=config.temperature),
        output_type=ParticipantResponse  # Changes based on experiment step
    )

def _generate_dynamic_instructions(
    ctx: RunContextWrapper[ParticipantContext], 
    agent: Agent, 
    config: AgentConfiguration
) -> str:
    """Generate context-aware instructions including memory, bank balance, etc."""
    
    return f"""
    Name: {ctx.context.name}
    Role Description: {ctx.context.role_description}
    Bank Balance: ${ctx.context.bank_balance}
    Current Phase: {ctx.context.phase}
    Memory: {ctx.context.memory}
    
    {BROAD_EXPERIMENT_EXPLANATION}
    
    Personality: {config.personality}
    
    [Phase-specific instructions based on current step]
    """
```

### **3.3 Broad Experiment Explanation**
```python
BROAD_EXPERIMENT_EXPLANATION = """
You are participating in an experiment studying principles of justice and income distribution.

The experiment has two main phases:
Phase 1: You will individually learn about and apply four different principles of justice to income distributions. You will be asked to rank these principles by preference and apply them to specific scenarios. Your choices will affect your earnings.

Phase 2: You will join a group discussion to reach consensus on which principle of justice the group should adopt. The group's chosen principle will then be applied to determine everyone's final earnings.

Throughout the experiment, maintain your assigned personality while engaging thoughtfully with the principles and other participants.
"""
```

**Deliverable:** Complete participant agent system with dynamic instructions and memory management

---

## **PHASE 4: PHASE 1 IMPLEMENTATION**  

### **4.1 Phase 1 Manager**
```python
# core/phase1_manager.py
class Phase1Manager:
    def __init__(self, participants: List[Agent], utility_agent: UtilityAgent):
        self.participants = participants
        self.utility_agent = utility_agent
        
    async def run_phase1(self, config: ExperimentConfiguration) -> List[Phase1Results]:
        """Execute complete Phase 1 for all participants in parallel"""
        
        tasks = []
        for participant in self.participants:
            context = self._create_participant_context(participant)
            task = asyncio.create_task(
                self._run_single_participant_phase1(participant, context, config)
            )
            tasks.append(task)
            
        return await asyncio.gather(*tasks)
    
    async def _run_single_participant_phase1(
        self, 
        participant: Agent, 
        context: ParticipantContext,
        config: ExperimentConfiguration
    ) -> Phase1Results:
        """Run complete Phase 1 for single participant"""
        
        # 1.1 Initial Principle Ranking
        initial_ranking = await self._step_1_1_initial_ranking(participant, context)
        context = self._update_context_memory(context, "initial_ranking", initial_ranking)
        
        # 1.2 Detailed Explanation (informational only)
        await self._step_1_2_detailed_explanation(participant, context)
        context = self._update_context_memory(context, "detailed_explanation", "completed")
        
        # 1.3 Repeated Application (4 rounds)
        application_results = []
        for round_num in range(1, 5):
            context.round_number = round_num
            distribution_set = DistributionGenerator.generate_dynamic_distribution(
                config.distribution_range_phase1
            )
            
            result = await self._step_1_3_principle_application(
                participant, context, distribution_set, round_num
            )
            application_results.append(result)
            
            # Update context with earnings and feedback
            context = self._update_context_with_earnings(context, result)
            
        # 1.4 Final Ranking
        final_ranking = await self._step_1_4_final_ranking(participant, context)
        
        return Phase1Results(
            participant_name=participant.name,
            initial_ranking=initial_ranking,
            application_results=application_results,
            final_ranking=final_ranking,
            total_earnings=context.bank_balance,
            final_memory_state=context.memory  # CRITICAL: Preserve memory for Phase 2
        )
```

### **4.2 Individual Phase 1 Steps**
```python
async def _step_1_1_initial_ranking(
    self, participant: Agent, context: ParticipantContext
) -> PrincipleRanking:
    """Step 1.1: Initial principle ranking with certainty"""
    
    ranking_prompt = self._build_ranking_prompt()
    
    result = await Runner.run(
        participant.clone(output_type=PrincipleRankingResponse),
        ranking_prompt,
        context=context
    )
    
    # Parse and validate response using utility agent
    parsed_ranking = await self.utility_agent.parse_principle_ranking(
        result.final_output
    )
    
    return parsed_ranking

async def _step_1_3_principle_application(
    self, 
    participant: Agent, 
    context: ParticipantContext,
    distribution_set: DistributionSet,
    round_num: int
) -> ApplicationResult:
    """Step 1.3: Single round of principle application"""
    
    application_prompt = self._build_application_prompt(distribution_set, round_num)
    
    result = await Runner.run(
        participant.clone(output_type=PrincipleChoiceResponse),
        application_prompt,
        context=context
    )
    
    # Parse and validate choice
    parsed_choice = await self.utility_agent.parse_principle_choice(result.final_output)
    
    # Validate constraint specification
    if not await self.utility_agent.validate_constraint_specification(parsed_choice):
        # Re-prompt for valid constraint
        parsed_choice = await self._re_prompt_for_valid_constraint(
            participant, context, parsed_choice
        )
    
    # Apply principle to distributions
    chosen_distribution, explanation = DistributionGenerator.apply_principle_to_distributions(
        distribution_set.distributions, parsed_choice
    )
    
    # Calculate payoff and income class assignment
    assigned_class, earnings = self._calculate_payoff(chosen_distribution)
    
    return ApplicationResult(
        round_number=round_num,
        principle_choice=parsed_choice,
        chosen_distribution=chosen_distribution,
        assigned_income_class=assigned_class,
        earnings=earnings,
        alternative_earnings=self._calculate_alternative_earnings(distribution_set.distributions)
    )
```

**Deliverable:** Complete Phase 1 implementation with parallel execution and comprehensive validation

---

## **PHASE 5: PHASE 2 IMPLEMENTATION**

### **5.1 Group Discussion State Management**
```python
# models/experiment_types.py
class GroupDiscussionState(BaseModel):
    round_number: int = 0
    statements: List[DiscussionStatement] = []
    vote_history: List[VoteResult] = []
    public_history: str = ""
    
    def add_statement(self, participant_name: str, statement: str):
        """Add statement to public history"""
        
    def add_vote_result(self, vote_result: VoteResult):
        """Add vote result to public history"""

class DiscussionStatement(BaseModel):
    participant_name: str
    statement: str
    round_number: int
    timestamp: datetime
    contains_vote_proposal: bool = False
```

### **5.2 Phase 2 Manager Implementation**
```python
# core/phase2_manager.py
class Phase2Manager:
    def __init__(self, participants: List[Agent], utility_agent: UtilityAgent):
        self.participants = participants
        self.utility_agent = utility_agent
        
    async def run_phase2(
        self, 
        config: ExperimentConfiguration,
        phase1_results: List[Phase1Results]
    ) -> Phase2Results:
        """Execute complete Phase 2 group discussion"""
        
        # CRITICAL: Initialize participants with CONTINUOUS memory from Phase 1
        # Memory must include all Phase 1 experiences, earnings, and learnings
        participant_contexts = self._initialize_phase2_contexts(phase1_results)
        
        # Group discussion
        discussion_result = await self._run_group_discussion(
            config, participant_contexts
        )
        
        # Apply chosen principle and calculate payoffs
        payoff_results = await self._apply_group_principle_and_calculate_payoffs(
            discussion_result, config
        )
        
        # Final individual rankings
        final_rankings = await self._collect_final_rankings(
            participant_contexts, discussion_result, payoff_results
        )
        
        return Phase2Results(
            discussion_result=discussion_result,
            payoff_results=payoff_results, 
            final_rankings=final_rankings
        )
    
    async def _run_group_discussion(
        self,
        config: ExperimentConfiguration,
        contexts: List[ParticipantContext]
    ) -> GroupDiscussionResult:
        """Run sequential group discussion with voting"""
        
        discussion_state = GroupDiscussionState()
        
        for round_num in range(1, config.phase2_rounds + 1):
            discussion_state.round_number = round_num
            
            # Generate speaking order (avoid same participant starting consecutive rounds)
            speaking_order = self._generate_speaking_order(round_num, contexts)
            
            for participant_idx in speaking_order:
                participant = self.participants[participant_idx]
                context = contexts[participant_idx]
                
                # Get participant statement (with internal reasoning if enabled)
                statement = await self._get_participant_statement(
                    participant, context, discussion_state, config
                )
                
                discussion_state.add_statement(participant.name, statement)
                
                # Check for vote proposal
                vote_proposal = await self.utility_agent.extract_vote_from_statement(statement)
                
                if vote_proposal:
                    # Check if all participants agree to vote
                    if await self._check_unanimous_vote_agreement(
                        discussion_state, contexts, config
                    ):
                        vote_result = await self._conduct_group_vote(contexts, config)
                        discussion_state.add_vote_result(vote_result)
                        
                        if vote_result.consensus_reached:
                            return GroupDiscussionResult(
                                consensus_reached=True,
                                agreed_principle=vote_result.agreed_principle,
                                final_round=round_num,
                                discussion_history=discussion_state.public_history,
                                vote_history=discussion_state.vote_history
                            )
        
        # No consensus reached
        return GroupDiscussionResult(
            consensus_reached=False,
            final_round=config.phase2_rounds,
            discussion_history=discussion_state.public_history,
            vote_history=discussion_state.vote_history
        )
```

### **5.3 Voting System Implementation**
```python
async def _conduct_group_vote(
    self, 
    contexts: List[ParticipantContext],
    config: ExperimentConfiguration
) -> VoteResult:
    """Conduct secret ballot voting"""
    
    voting_tasks = []
    for i, participant in enumerate(self.participants):
        context = contexts[i]
        task = asyncio.create_task(
            self._get_participant_vote(participant, context)
        )
        voting_tasks.append(task)
    
    votes = await asyncio.gather(*voting_tasks)
    
    # Validate votes and check for consensus
    valid_votes = []
    for vote in votes:
        if await self.utility_agent.validate_constraint_specification(vote):
            valid_votes.append(vote)
        else:
            # Re-prompt for valid vote
            corrected_vote = await self._re_prompt_for_valid_vote(vote)
            valid_votes.append(corrected_vote)
    
    # Check for exact consensus (including constraint amounts)
    consensus_principle = self._check_exact_consensus(valid_votes)
    
    return VoteResult(
        votes=valid_votes,
        consensus_reached=consensus_principle is not None,
        agreed_principle=consensus_principle,
        vote_counts=self._count_votes(valid_votes)
    )

def _check_exact_consensus(self, votes: List[PrincipleChoice]) -> Optional[PrincipleChoice]:
    """Check if all votes are exactly identical (including constraint amounts)"""
    if not votes:
        return None
        
    first_vote = votes[0]
    for vote in votes[1:]:
        if (vote.principle != first_vote.principle or 
            vote.constraint_amount != first_vote.constraint_amount):
            return None
    
    return first_vote
```

**Deliverable:** Complete Phase 2 implementation with group discussion, voting, and consensus detection

---

## **PHASE 6: EXPERIMENT ORCHESTRATION & LOGGING**

### **6.1 Main Experiment Manager**
```python
# core/experiment_manager.py
class FrohlichExperimentManager:
    def __init__(self, config: ExperimentConfiguration):
        self.config = config
        self.experiment_id = str(uuid.uuid4())
        self.participants = self._create_participants()
        self.utility_agent = UtilityAgent()
        self.phase1_manager = Phase1Manager(self.participants, self.utility_agent)
        self.phase2_manager = Phase2Manager(self.participants, self.utility_agent)
        
    async def run_complete_experiment(self) -> ExperimentResults:
        """Run complete two-phase experiment with tracing"""
        
        with trace(
            "Frohlich Experiment",
            trace_id=self.experiment_id,
            group_id="frohlich_experiments",
            trace_metadata={
                "experiment_type": "justice_principles",
                "num_participants": len(self.participants),
                "phase2_rounds": self.config.phase2_rounds
            }
        ) as experiment_trace:
            
            # Phase 1: Individual familiarization (parallel)
            logger.info(f"Starting Phase 1 for experiment {self.experiment_id}")
            phase1_results = await self.phase1_manager.run_phase1(self.config)
            
            # Phase 2: Group discussion (sequential)  
            logger.info(f"Starting Phase 2 for experiment {self.experiment_id}")
            phase2_results = await self.phase2_manager.run_phase2(
                self.config, phase1_results
            )
            
            # Compile final results
            results = ExperimentResults(
                experiment_id=self.experiment_id,
                config=self.config,
                phase1_results=phase1_results,
                phase2_results=phase2_results,
                timestamp=datetime.now(),
                total_runtime=time.time() - start_time
            )
            
            return results
            
    def _create_participants(self) -> List[Agent[ParticipantContext]]:
        """Create participant agents from configuration"""
        return [
            create_participant_agent(agent_config) 
            for agent_config in self.config.agents
        ]
    
    def _transfer_phase1_memory_to_phase2(
        self, 
        phase1_results: List[Phase1Results]
    ) -> List[ParticipantContext]:
        """
        CRITICAL: Transfer complete Phase 1 memory to Phase 2 contexts
        This ensures continuous memory across experimental phases
        """
        phase2_contexts = []
        for i, (participant, phase1_result) in enumerate(zip(self.participants, phase1_results)):
            # Extract final memory state from Phase 1
            final_phase1_memory = phase1_result.final_memory_state
            
            # Create Phase 2 context with continuous memory
            phase2_context = ParticipantContext(
                name=participant.name,
                role_description=self.config.agents[i].personality,
                bank_balance=phase1_result.total_earnings,  # Carry forward earnings
                memory=final_phase1_memory,  # CONTINUOUS MEMORY FROM PHASE 1
                round_number=0,  # Reset for Phase 2
                phase=ExperimentPhase.PHASE_2,
                max_memory_length=self.config.agents[i].memory_length
            )
            
            # Add Phase 2 transition information to memory
            transition_info = f"""
            TRANSITION TO PHASE 2:
            - Total Phase 1 earnings: ${phase1_result.total_earnings}
            - Now entering group discussion phase
            - Your task: Work with other participants to reach consensus on justice principle
            """
            phase2_context.memory = MemoryManager.update_memory(
                phase2_context.memory, 
                transition_info, 
                phase2_context.max_memory_length
            )
            
            phase2_contexts.append(phase2_context)
            
        return phase2_contexts
```

### **6.2 JSON Logging System**
```python
# utils/logging_utils.py
class ExperimentLogger:
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.log_data = {}
        
    def log_experiment_results(self, results: ExperimentResults):
        """Save complete experiment results as JSON"""
        
        log_structure = {
            "experiment_metadata": {
                "experiment_id": results.experiment_id,
                "timestamp": results.timestamp.isoformat(),
                "total_runtime_seconds": results.total_runtime,
                "configuration": results.config.dict()
            },
            "phase1_results": self._format_phase1_results(results.phase1_results),
            "phase2_results": self._format_phase2_results(results.phase2_results),
            "agent_interactions": self._extract_agent_interactions(results),
            "final_summary": self._generate_experiment_summary(results)
        }
        
        with open(self.output_path, 'w') as f:
            json.dump(log_structure, f, indent=2, default=self._json_serializer)
    
    def _extract_agent_interactions(self, results: ExperimentResults) -> Dict:
        """Extract all agent inputs/outputs in chronological order"""
        # Implementation to extract all agent interactions from results
        
    @staticmethod
    def _json_serializer(obj):
        """Handle datetime and other non-serializable objects"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Enum):
            return obj.value
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
```

### **6.3 Main Entry Point**
```python
# main.py
import asyncio
import logging
from pathlib import Path
from datetime import datetime

from config.models import ExperimentConfiguration
from core.experiment_manager import FrohlichExperimentManager
from utils.logging_utils import ExperimentLogger

async def main():
    """Main entry point for Frohlich Experiment"""
    
    # Load configuration
    config_path = Path("config/default_config.yaml")
    config = ExperimentConfiguration.from_yaml(config_path)
    
    # Set up logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = f"experiment_results_{timestamp}.json"
    logger = ExperimentLogger(log_path)
    
    # Initialize and run experiment
    experiment_manager = FrohlichExperimentManager(config)
    
    try:
        print(f"Starting Frohlich Experiment with {len(config.agents)} participants...")
        results = await experiment_manager.run_complete_experiment()
        
        # Save results
        logger.log_experiment_results(results)
        print(f"Experiment completed successfully. Results saved to: {log_path}")
        
        # Print summary
        print(f"\nExperiment Summary:")
        print(f"- Phase 1 completed for {len(results.phase1_results)} participants")
        print(f"- Phase 2 consensus: {'Reached' if results.phase2_results.discussion_result.consensus_reached else 'Not reached'}")
        if results.phase2_results.discussion_result.consensus_reached:
            print(f"- Agreed principle: {results.phase2_results.discussion_result.agreed_principle}")
        
    except Exception as e:
        logging.error(f"Experiment failed: {e}")
        raise

if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.INFO)
    
    # Run experiment
    asyncio.run(main())
```

**Deliverable:** Complete experiment orchestration with comprehensive JSON logging

---

## **PHASE 7: CONFIGURATION & TESTING**

### **7.1 Default Test Configuration**
```yaml
# config/default_config.yaml
agents:
  - name: "Alice"
    personality: "Analytical and methodical. Values fairness and systematic approaches to problem-solving."
    model: "o3-mini"
    temperature: 0.7
    reasoning_enabled: true
    memory_length: 5000
    
  - name: "Bob" 
    personality: "Pragmatic and results-oriented. Focuses on practical outcomes and efficiency."
    model: "o3-mini"
    temperature: 0.8
    reasoning_enabled: true
    memory_length: 5000
    
  - name: "Carol"
    personality: "Empathetic and community-focused. Prioritizes helping those in need and social welfare."
    model: "o3-mini" 
    temperature: 0.6
    reasoning_enabled: true
    memory_length: 5000

phase2_rounds: 8
distribution_range_phase1: [0.5, 2.0]
distribution_range_phase2: [0.5, 2.0]
```

### **7.2 Unit Testing Framework**
```python
# tests/unit/test_distribution_generator.py
class TestDistributionGenerator:
    def test_generate_dynamic_distribution(self):
        """Test dynamic distribution generation with multipliers"""
        
    def test_apply_principle_maximizing_floor(self):
        """Test principle application logic for maximizing floor"""
        
    def test_apply_principle_with_constraints(self):
        """Test constraint principle validation and application"""

# tests/unit/test_utility_agent.py  
class TestUtilityAgent:
    async def test_parse_principle_choice_valid(self):
        """Test parsing valid principle choices"""
        
    async def test_parse_principle_choice_missing_constraint(self):
        """Test handling of missing constraint amounts"""

# tests/integration/test_phase1_flow.py
class TestPhase1Integration:
    async def test_complete_phase1_single_participant(self):
        """Test complete Phase 1 flow for single participant"""
        
    async def test_phase1_parallel_execution(self):
        """Test parallel execution of multiple participants"""
```

**Deliverable:** Complete testing framework and default configuration for system validation

---

## **IMPLEMENTATION TIMELINE & DEPENDENCIES**

### **Critical Path Dependencies:**
1. **Phase 1** (Foundation) → **Phase 2** (Utility Agent) → **Phase 3** (Participant Agents)
2. **Phase 4** (Phase 1 Logic) ← **Phase 3** (Participant Agents) 
3. **Phase 5** (Phase 2 Logic) ← **Phase 3** (Participant Agents) + **Phase 2** (Utility Agent)
4. **Phase 6** (Orchestration) ← **Phase 4** + **Phase 5**
5. **Phase 7** (Testing) ← All previous phases

### **Parallel Implementation Opportunities:**
- Phase 2 (Utility Agent) and Phase 3 (Participant Agents) can be developed simultaneously
- Phase 4 and Phase 5 can be developed in parallel after Phase 3 is complete
- Unit tests can be written alongside each phase

### **Key Technical Decisions Made:**
1. **Single trace per experiment** for complete visibility
2. **Pydantic models throughout** for type safety and validation
3. **Manager-based architecture** for clear separation of concerns
4. **Parallel Phase 1, sequential Phase 2** following optimal patterns
5. **Context-based memory management** leveraging agents_sdk capabilities
6. **Utility agent for all parsing/validation** to ensure consistency
7. **CONTINUOUS MEMORY ACROSS PHASES** - Critical requirement for experimental integrity

This implementation plan provides a comprehensive roadmap for building the Frohlich Experiment system with proper separation of concerns, robust error handling, and optimal use of the agents_sdk framework capabilities.