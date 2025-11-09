# TECHNICAL README: Frohlich Experiment Framework

## Executive Summary

This document provides a comprehensive technical analysis of the **Frohlich Experiment** framework—a sophisticated Python system for conducting computational experiments on distributive justice. The framework orchestrates AI agents in a two-phase experiment grounded in **Rawlsian philosophy** and inspired by economist Norman Frohlich's empirical work on justice principles.

**Core Thesis**: Under a computationally-simulated "veil of ignorance," agents autonomously reason about and reach consensus on principles of distributive justice through formal voting mechanisms and memory-augmented discussion.

**Scale**: ~10,452 lines of production code across 60+ modules implementing:
- Two-phase experiment orchestration with 6 specialized Phase 2 services
- Deterministic two-stage voting system with multilingual support
- Sophisticated memory management with content truncation
- Reproducible experiments via seeding and configuration
- Multi-provider LLM support (OpenAI, Google Gemini, OpenRouter, Ollama)

---

## 1. Core Experimental Model

### 1.1 The Veil of Ignorance Scenario

The experiment implements a computational variant of **John Rawls' veil of ignorance** thought experiment:

1. **Information Asymmetry**: Agents are randomly assigned to one of 5 income classes (high, medium_high, medium, medium_low, low)
2. **Uncertainty**: Agents know the 4 justice principles but not which class they'll occupy
3. **Deliberation**: Agents participate in structured discussion and reach consensus on a principle
4. **Payoff Realization**: After consensus, agents' actual income class is revealed, determining their final earnings

### 1.2 Four Justice Principles

The framework operationalizes four distinct principles (implemented in `models/principle_types.py`):

```
Principle 1: MAXIMIZING_FLOOR
  - Maximize the lowest income in the distribution
  - Rawlsian "difference principle": prioritize the worst-off
  - No constraint parameters required

Principle 2: MAXIMIZING_AVERAGE
  - Maximize average income across all classes
  - Utilitarian: total welfare maximization
  - No constraint parameters required

Principle 3: MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
  - Maximize average income with a minimum floor constraint
  - Example: "maximize average but no class earns < $15,000"
  - Requires positive integer constraint_amount

Principle 4: MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
  - Maximize average income with range limitation
  - Example: "maximize average but income spread ≤ $10,000"
  - Requires positive integer constraint_amount
```

Each principle produces different income distributions and payoffs for different agent classes, creating meaningful trade-offs in the bargaining process.

### 1.3 Income Distribution System

**Distribution Generator** (`core/distribution_generator.py`) provides four income distributions per round:

```python
BASE_DISTRIBUTION = IncomeDistribution(
    high=32000,           # Class 1 (richest)
    medium_high=27000,    # Class 2
    medium=24000,         # Class 3 (most likely)
    medium_low=13000,     # Class 4
    low=12000            # Class 5 (poorest)
)
```

**Two distribution generation modes**:

1. **Dynamic Mode**: Applies random multiplier (e.g., 0.8-1.2) to base distribution
   ```python
   multiplier = random_gen.uniform(0.8, 1.2)  # Seeded for reproducibility
   scaled_distribution = {income * multiplier for each class}
   ```

2. **Original Values Mode**: Uses predefined historical distributions (Frohlich's original data)
   - Round 1 → Situation A
   - Round 2 → Situation B
   - Round 3 → Situation C
   - Round 4 → Situation D

**Income Class Probabilities**: Each round specifies how likely each class is
```python
default_probabilities = {
    high: 0.05,           # 5% chance of high income
    medium_high: 0.10,    # 10% chance
    medium: 0.50,         # 50% chance (modal class)
    medium_low: 0.25,     # 25% chance
    low: 0.10             # 10% chance
}
```

When calculating payoffs, the framework uses **weighted expected value** calculations:
```
expected_payoff = Σ(income_class[i] * probability[i])
```

---

## 2. Two-Phase Experiment Architecture

### 2.1 Phase 1: Individual Familiarization (Parallel Execution)

**Purpose**: Agents independently learn about justice principles and reason about their preferences without group influence.

**Flow** (`core/phase1_manager.py`):

```
For each participant (executed in parallel asyncio tasks):
  1. Initial Ranking
     - Agent ranks 4 justice principles 1-4 (best to worst)
     - No prior knowledge of distributions

  2. Principle Explanation
     - Agent receives detailed explanation of each principle
     - Explanation includes empirical payoff examples

  3. Post-Explanation Ranking
     - Agent re-ranks principles after understanding implications
     - Tests learning and preference stability

  4. Application Tasks (4 rounds)
     For each round:
       a. Agent receives 4 income distributions
       b. Agent selects which distribution to apply chosen principle to
       c. System calculates participant's expected payoff
       d. Participant provides reasoning for choices
```

**Key Implementation Details**:

- **Deterministic RNGs**: Each participant gets seeded random.Random instance
  ```python
  self._participant_rngs[agent_name] = random.Random(seed=base_seed + agent_index)
  ```
  This ensures reproducibility across experiment runs

- **Memory Management**: Integrated SelectiveMemoryManager for context truncation
  - Prevents context overflow for long discussions
  - Truncates old statements (≤300 characters each)
  - Limits accumulated internal reasoning (≤200 characters)

- **Output**: Phase1Results containing:
  ```python
  {
    initial_ranking: PrincipleRanking,
    post_explanation_ranking: PrincipleRanking,
    application_results: [ApplicationResult × 4 rounds],
    participant_name: str,
    completion_status: str
  }
  ```

### 2.2 Phase 2: Group Discussion and Consensus (Sequential with Services)

**Purpose**: Agents engage in structured group discussion to reach collective consensus on a justice principle via formal voting.

**Architecture**: Services-first design with 6 specialized services orchestrated by Phase2Manager:

```
Phase2Manager (orchestrator)
├── SpeakingOrderService        → Manages turn allocation with finisher restrictions
├── DiscussionService           → Generates discussion prompts, validates statements
├── VotingService               → Coordinates voting process (initiation + confirmation + ballot)
├── MemoryService               → Updates agent memories with event summaries
├── CounterfactualsService      → Calculates payoffs and prepares results
└── ManipulatorService          → Optional experimental manipulation
```

**Full Phase 2 Flow**:

```python
async def run_phase2(phase1_results: List[Phase1Results]) -> Phase2Results:
    """
    Executes group discussion with formal consensus building.
    """

    # Initialize speaking order with finisher restrictions
    speaking_order = speaking_order_service.determine_speaking_order(
        participants=participants,
        randomize_finisher=(settings.finisher_restrictions_active)
    )

    # Begin rounds of discussion and potential voting
    for round_num in range(1, config.phase2_rounds + 1):

        # 1. DISCUSSION: Sequential agent statements with memory context
        for participant in speaking_order[round_num]:

            # Get contextual discussion prompt
            discussion_prompt = discussion_service.build_discussion_prompt(
                participant=participant,
                phase1_results=phase1_results[participant],
                discussion_history=group_state.public_history,
                current_round=round_num,
                consensus_status=group_state.consensus_reached
            )

            # Agent generates statement
            statement = await participant.think(discussion_prompt)

            # Validate statement (>= min_length, retries up to 3 times)
            validated_statement = discussion_service.validate_statement(
                statement=statement,
                min_length=settings.statement_min_length,
                max_retries=settings.statement_validation_retries
            )

            # Update public history and agent-specific memories
            group_state.public_history.append({
                'round': round_num,
                'participant': participant.name,
                'statement': validated_statement,
                'timestamp': datetime.now()
            })

            memory_delta = memory_service.update_discussion_memory(
                agent=participant,
                context=participant.context,
                statement_summary=validated_statement[:300],  # Truncate to 300 chars
                round_number=round_num
            )

        # 2. VOTING: Check if any agent wants to initiate voting
        voting_initiation_prompt = discussion_service.build_voting_initiation_prompt(
            round_number=round_num,
            is_final_round=(round_num == config.phase2_rounds),
            consensus_reached=group_state.consensus_reached
        )

        voting_initiated = False
        for participant in participants:
            # Agent decision: initiate voting? (1=Yes, 0=No)
            initiation_response = await participant.think(voting_initiation_prompt)
            vote_yes, principle = utility_agent.detect_numerical_agreement(initiation_response)

            if vote_yes:
                voting_initiated = True
                break

        if voting_initiated or round_num == config.phase2_rounds:

            # 2a. CONFIRMATION PHASE
            confirmation_results = await voting_service.coordinate_voting_confirmation(
                participants=participants,
                discussion_state=group_state,
                current_round=round_num,
                timeout_seconds=settings.voting_confirmation_timeout
            )

            # All must agree (confirmation_results = 100% Yes) to proceed
            if confirmation_results.all_confirmed:

                # 2b. SECRET BALLOT (Two-Stage Voting)
                ballot_results = await voting_service.coordinate_secret_ballot(
                    participants=participants,
                    current_round=round_num,
                    timeout_seconds=settings.voting_secret_ballot_timeout
                )

                # STAGE 1: Principle Selection (deterministic numerical input: 1-4)
                for participant in participants:
                    ballot_prompt = voting_service.build_ballot_prompt(stage=1)
                    response = await participant.think(ballot_prompt)

                    # TwoStageVotingManager: Extract principle number (1-4) via regex
                    principle_num, success = two_stage_voting.extract_principle_number(
                        response=response,
                        max_retries=3
                    )

                    if success:
                        participant.principle_vote = principle_num
                    else:
                        # Fallback: keyword matching in participant's language
                        principle_num = principle_keyword_matcher.match_principle(
                            text=response,
                            detected_language=detect_language_from_response(response)
                        )

                # STAGE 2: Amount Specification (if principles 3 or 4 chosen)
                for participant in participants:
                    if participant.principle_vote in [3, 4]:  # Constraint principles
                        amount_prompt = voting_service.build_ballot_prompt(
                            stage=2,
                            principle_num=participant.principle_vote
                        )
                        response = await participant.think(amount_prompt)

                        # Extract positive integer via regex
                        constraint_amount, success = two_stage_voting.extract_constraint_amount(
                            response=response,
                            max_retries=3
                        )

                        if success:
                            participant.constraint_amount = constraint_amount

                # 2c. CONSENSUS DETECTION
                consensus = voting_service.detect_consensus(
                    votes=[(p.principle_vote, p.constraint_amount) for p in participants],
                    strict_mode=True  # All must vote identically
                )

                if consensus:
                    group_state.consensus_reached = True
                    group_state.consensus_principle = consensus.principle
                    group_state.consensus_constraint = consensus.constraint_amount
                    break  # Exit round loop
                else:
                    # Voting failed: continue discussion in next round
                    memory_service.update_voting_memory(
                        agents=participants,
                        event_type=MemoryEventType.VOTING_FAILED,
                        reason="No consensus reached"
                    )

    # 3. PAYOFF CALCULATION & RESULTS
    final_results = await counterfactuals_service.calculate_and_format_results(
        consensus_reached=group_state.consensus_reached,
        consensus_principle=group_state.consensus_principle if group_state.consensus_reached else None,
        participants=participants,
        phase1_results=phase1_results,
        current_round=round_num
    )

    # 4. FINAL RANKINGS
    for participant in participants:
        final_ranking_prompt = counterfactuals_service.build_final_ranking_prompt()
        ranking_response = await participant.think(final_ranking_prompt)
        final_ranking = utility_agent.parse_principle_ranking(ranking_response)
        final_results[participant.name].final_ranking = final_ranking

    return Phase2Results(
        consensus_reached=group_state.consensus_reached,
        final_principle=group_state.consensus_principle,
        final_constraint_amount=group_state.consensus_constraint,
        discussion_transcript=group_state.public_history,
        participant_results=final_results,
        rounds_completed=round_num
    )
```

---

## 3. Service-Based Architecture (Phase 2 Core)

The framework employs a **services-first architecture** for Phase 2, replacing monolithic logic with focused, testable services using **Protocol-based dependency injection**.

### 3.1 SpeakingOrderService

**File**: `core/services/speaking_order_service.py`

**Responsibility**: Manage turn allocation with optional finisher restrictions.

**Key Methods**:

```python
def determine_speaking_order(
    self,
    participants: List[ParticipantAgent],
    randomize_finisher: bool = False
) -> Dict[int, List[ParticipantAgent]]:
    """
    Determine speaking order for each round with finisher restrictions.

    Algorithm:
    1. Randomly shuffle participant order using seeded RNG
    2. If randomize_finisher: ensure last speaker differs from previous rounds
    3. Return dict mapping round_number → [ordered_participants]

    Finisher Restriction: The agent speaking last must not have spoken last
    in any previous round (encourages new perspectives at round conclusion).
    """

def apply_finisher_restrictions(
    self,
    order: List[ParticipantAgent],
    previous_finishers: Set[str]
) -> List[ParticipantAgent]:
    """Reorder to ensure new finisher if restriction enabled."""
```

**Configuration**:
```yaml
phase2_settings:
  finisher_restrictions_active: true  # Enable finisher reordering
  use_fixed_speaking_order: false     # Or specify fixed order
```

### 3.2 DiscussionService

**File**: `core/services/discussion_service.py`

**Responsibility**: Generate contextual discussion prompts, validate statements, manage discussion history.

**Key Methods**:

```python
def build_discussion_prompt(
    self,
    participant: ParticipantAgent,
    phase1_results: Phase1Results,
    discussion_history: List[Dict],
    current_round: int,
    consensus_status: bool
) -> str:
    """
    Build contextual discussion prompt with:
    - Agent's Phase 1 rankings and application results
    - Summary of previous statements (with truncation)
    - Current round context
    - System instructions for tone/length

    Returns: Localized prompt template with agent-specific context
    """

def validate_statement(
    self,
    statement: str,
    min_length: int = 50,
    max_retries: int = 3
) -> str:
    """
    Validate that statement meets minimum length.
    Retry up to max_retries times if validation fails.

    Raises: ValidationError if max_retries exceeded
    """

def manage_discussion_history_length(
    self,
    history: List[Dict],
    max_length_chars: int
) -> List[Dict]:
    """
    Truncate discussion history intelligently:
    1. Remove oldest entries first (chronological ordering)
    2. Keep enough context for decision-making
    3. Preserve critical principle discussion

    Uses Phase2Settings.public_history_max_length (default: 100,000 chars)
    """
```

**Multilingual Support**:
```python
# Translation keys for discussion prompts
DISCUSSION_ROUND_START = "discussion_round_{round}_start"
DISCUSSION_VOTING_INITIATION = "discussion_voting_initiation"
DISCUSSION_FINAL_ROUND = "discussion_final_round"

# Language manager retrieves localized versions (en/es/zh)
prompt = language_manager.get("discussion_round_{round}_start",
                               round=current_round)
```

### 3.3 VotingService

**File**: `core/services/voting_service.py`

**Responsibility**: Coordinate complete voting process (initiation → confirmation → secret ballot).

**Key Methods**:

```python
async def initiate_voting(
    self,
    participants: List[ParticipantAgent],
    discussion_state: GroupDiscussionState,
    current_round: int,
    timeout_seconds: Optional[float] = None
) -> VotingInitiationResult:
    """
    Determine if voting should be initiated.

    Process:
    1. Generate initiation prompt asking "Do you want to initiate voting?"
    2. For each participant: get response and detect numerical answer (1=Yes, 0=No)
    3. Return: (should_initiate, initiating_participant)

    Returns after first Yes response or all participants checked.
    """

async def coordinate_voting_confirmation(
    self,
    participants: List[ParticipantAgent],
    discussion_state: GroupDiscussionState,
    current_round: int,
    timeout_seconds: Optional[float] = None
) -> ConfirmationResult:
    """
    Confirmation Phase: All agents must agree to participate in voting.

    Process:
    1. Send confirmation prompt: "Do you agree to participate in voting? (1=Yes, 0=No)"
    2. Collect responses from all participants
    3. Validate 100% agreement (all_confirmed = all agents said Yes)

    Returns:
        all_confirmed: bool
        confirmation_votes: Dict[participant_name -> (vote, confidence)]
    """

async def coordinate_secret_ballot(
    self,
    participants: List[ParticipantAgent],
    current_round: int,
    timeout_seconds: Optional[float] = None
) -> SecretBallotResult:
    """
    Execute two-stage secret ballot process.

    STAGE 1: Principle Selection (1-4)
    STAGE 2: Amount Specification (for principles 3 & 4)

    Handled by TwoStageVotingManager with deterministic numerical validation.
    """

def detect_consensus(
    self,
    votes: List[Tuple[int, Optional[int]]],
    strict_mode: bool = True
) -> Optional[ConsensusResult]:
    """
    Detect unanimous agreement on principle and constraint.

    If strict_mode=True: All agents must vote identically
    If strict_mode=False: Majority rule (not used in current implementation)

    Returns: ConsensusResult or None if no consensus
    """
```

**Error Handling**:
```python
# Automatic retry with exponential backoff
async def _invoke_voting_interaction(
    self,
    participant: ParticipantAgent,
    context: ParticipantContext,
    prompt: str,
    timeout_seconds: Optional[float] = None
):
    """Execute interaction with timeout and automatic retry."""
    try:
        return await asyncio.wait_for(
            coroutine=participant.think(prompt),
            timeout=timeout_seconds or self.settings.voting_confirmation_timeout
        )
    except asyncio.TimeoutError:
        # Retry up to settings.voting_retry_limit times with exponential backoff
        ...
```

### 3.4 TwoStageVotingManager

**File**: `core/two_stage_voting_manager.py`

**Responsibility**: Deterministic two-stage voting with multilingual validation.

**Stage 1: Principle Selection** (Deterministic Numerical Input)

```python
async def conduct_principle_selection(
    self,
    participants: List[ParticipantAgent],
    round_number: int,
    timeout_seconds: Optional[float] = None
) -> Dict[str, int]:  # participant_name -> principle_number (1-4)
    """
    STAGE 1: Select principle (1-4).

    Algorithm:
    1. Send prompt: "Which principle do you choose? (1=Floor, 2=Average, 3=Avg+Floor, 4=Avg+Range)"
    2. For each participant:
       a. Get response
       b. Use regex to extract first digit 1-4
       c. On parse failure: Use keyword fallback in participant's language
       d. On continued failure: Retry up to max_retries

    Returns: Dict mapping participant_name -> principle_number

    Key Design:
    - Replaces complex LLM-based principle detection with regex validation
    - Keyword fallback supports multilingual responses
    - Deterministic: no interpretation variance
    """

    principle_mapping = {}
    for participant in participants:
        principle_prompt = self.language_manager.get(
            "voting_principle_selection_prompt"
        )

        response = await participant.think(principle_prompt)

        # Try regex extraction first (deterministic)
        principle_num = self._extract_principle_number(response)

        if principle_num is None:
            # Fallback: keyword matching in participant's language
            detected_lang = detect_language_from_response(response)
            principle_num = principle_keyword_matcher.match_principle(
                text=response,
                language=detected_lang
            )

        principle_mapping[participant.name] = principle_num

    return principle_mapping

def _extract_principle_number(self, response: str) -> Optional[int]:
    """Extract first digit 1-4 from response using regex."""
    match = re.search(r'([1-4])', response)
    return int(match.group(1)) if match else None
```

**Stage 2: Amount Specification** (For Constraint Principles)

```python
async def conduct_amount_specification(
    self,
    participants: List[ParticipantAgent],
    principle_mapping: Dict[str, int],  # From Stage 1
    round_number: int,
    timeout_seconds: Optional[float] = None
) -> Dict[str, Optional[int]]:  # participant_name -> constraint_amount
    """
    STAGE 2: Specify constraint amount (for principles 3 & 4).

    Algorithm:
    1. Filter participants who voted for principle 3 or 4
    2. For each such participant:
       a. Send prompt: "What is your constraint amount? Please specify a number."
       b. Use regex to extract first positive integer
       c. On parse failure: Retry with cultural adaptation (number format parsing)
       d. Return int or None if failed after retries

    Returns: Dict mapping participant_name -> constraint_amount (or None)

    Multilingual Number Parsing:
    - English: 1000, 1,000 (comma), 1.000 (period)
    - Spanish: 1.000 (period), 1,000 (comma)
    - Mandarin: 1000, with cultural context for large numbers

    Uses get_amount_formatter() from cultural_adaptation.py
    """

    amount_mapping = {}
    for participant in participants:
        if principle_mapping[participant.name] not in [3, 4]:
            amount_mapping[participant.name] = None
            continue

        amount_prompt = self.language_manager.get(
            "voting_amount_specification_prompt",
            principle_num=principle_mapping[participant.name]
        )

        response = await participant.think(amount_prompt)

        # Extract amount using regex + cultural adaptation
        amount = self._extract_constraint_amount(response)

        if amount is None:
            # Try cultural adaptation (multilingual number formats)
            formatter = get_amount_formatter(
                language=detect_language_from_response(response)
            )
            amount = formatter.parse_amount_from_text(response)

        amount_mapping[participant.name] = amount

    return amount_mapping

def _extract_constraint_amount(self, response: str) -> Optional[int]:
    """Extract first positive integer from response."""
    match = re.search(r'(\d+)', response)
    return int(match.group(1)) if match else None
```

**Key Design Rationale**:
- **Deterministic**: Replaces complex LLM parsing ("Does the agent want principle 3?") with simple regex
- **Multilingual**: Keyword fallback and cultural number formatting
- **Auditable**: Each vote extractable from raw response with clear validation rules
- **Testable**: Stateless validation functions for unit testing

### 3.5 MemoryService

**File**: `core/services/memory_service.py`

**Responsibility**: Unified memory management with intelligent routing and content truncation.

**Architecture**:

```
SelectiveMemoryManager (lower-level)
    ↓ (wrapped by)
MemoryService (public API)
    ├── Routes events by type (discussion, voting, results)
    ├── Applies truncation rules (≤300 char statements, ≤200 char reasoning)
    ├── Delegates to SelectiveMemoryManager for implementation
    └── Provides consistent guidance style application
```

**Key Methods**:

```python
async def update_discussion_memory(
    self,
    agent: ParticipantAgent,
    context: ParticipantContext,
    statement_summary: str,  # Participant's statement
    round_number: int,
    include_reasoning: bool = False
) -> str:
    """
    Update agent memory with discussion statement.

    Process:
    1. Truncate statement to 300 characters
    2. Format with memory guidance style (narrative or structured)
    3. Delegate to SelectiveMemoryManager for insertion
    4. Return memory update result

    Routing: Routes to update_memory_simple() for direct insertion
    """

async def update_voting_memory(
    self,
    agent: ParticipantAgent,
    context: ParticipantContext,
    event_type: MemoryEventType,  # VOTING_INITIATED, VOTING_CONFIRMED, BALLOT_COMPLETED
    round_number: int,
    vote_choice: Optional[PrincipleChoice] = None,
    consensus_reached: bool = False
) -> str:
    """
    Update agent memory with voting event.

    Three sub-events:
    1. VOTING_INITIATED: Group is considering voting
    2. VOTING_CONFIRMED: All agents agreed to participate
    3. BALLOT_COMPLETED: Secret ballot results (with consensus if reached)

    Routing: Routes to update_memory_complex() if consensus reached,
             simple insertion if just status update
    """

async def update_final_results_memory(
    self,
    agent: ParticipantAgent,
    context: ParticipantContext,
    result_content: str,
    final_earnings: float,
    consensus_reached: bool
) -> str:
    """
    Update agent memory with final Phase 2 results.

    Content:
    - Consensus principle and constraint (if reached)
    - Agent's assigned income class
    - Final earnings (actual payoff)
    - Counterfactual earnings under other principles

    Routing: Always uses update_memory_complex() for detailed analysis
    """

def _truncate_content(
    self,
    content: str,
    content_type: str  # 'statement', 'reasoning', 'result'
) -> str:
    """
    Apply truncation rules based on Phase2Settings:
    - statement: ≤ 300 characters
    - reasoning: ≤ 200 characters
    - result: No truncation (full results preserved)
    """

def _apply_guidance_style(
    self,
    content: str,
    guidance_style: str  # 'narrative' or 'structured'
) -> str:
    """
    Format memory content with guidance style:

    narrative: "Agent Alice discussed the importance of fairness..."
    structured: "Topic: Fairness; Agent: Alice; Key Points: ..."
    """
```

**Configuration**:
```yaml
phase2_settings:
  memory_management:
    guidance_style: "narrative"  # or "structured"
    public_history_max_length: 100000  # characters
    statement_max_length: 300
    reasoning_max_length: 200
    enable_truncation: true
```

### 3.6 CounterfactualsService

**File**: `core/services/counterfactuals_service.py`

**Responsibility**: Calculate payoffs, generate counterfactual analyses, format detailed results.

**Payoff Calculation Algorithm**:

```python
async def calculate_payoffs(
    self,
    distribution_set: DistributionSet,
    consensus_principle: Optional[JusticePrinciple],
    participants: List[ParticipantAgent],
    income_probabilities: IncomeClassProbabilities
) -> Dict[str, float]:  # participant_name -> final_earnings
    """
    Calculate final payoffs based on consensus principle.

    Two scenarios:

    SCENARIO 1: Consensus Reached
        Apply the consensus principle to the distribution
        principle_mapping = apply_principle(consensus_principle, distribution)

        For each participant:
            1. Randomly assign income class using seeded RNG (respects probabilities)
            2. Look up income for assigned class in mapped distribution
            3. earnings[participant] = income

    SCENARIO 2: No Consensus
        Assign principle randomly from 4 principles
        random_principle = random.choice([Principle1, Principle2, Principle3, Principle4])

        Then apply same process as Scenario 1

    Returns: Dict mapping participant names to final earnings
    """

def _apply_principle_to_distribution(
    self,
    principle: JusticePrinciple,
    original_distribution: IncomeDistribution,
    constraint_amount: Optional[int] = None
) -> Dict[IncomeClass, int]:
    """
    Apply principle to original distribution, return optimized mapping.

    Principle 1: MAXIMIZING_FLOOR
        Objective: Maximize lowest income
        Algorithm: For each income class, optimize to maximize floor()
        Result: Modified distribution where floor is highest possible

    Principle 2: MAXIMIZING_AVERAGE
        Objective: Maximize average income
        Algorithm: Scale entire distribution uniformly (already optimal)
        Result: Original distribution (no change needed)

    Principle 3: MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
        Objective: Maximize average with floor constraint
        Algorithm:
            1. Set all incomes ≥ constraint_amount
            2. Remaining budget → maximize average

        Example:
            Original: high=32k, med=24k, med_low=13k, low=12k, avg=20.2k
            Constraint: 15k floor
            Result: high=38k, med=30k, med_low=15k, low=15k, avg=21.6k
                    (redistributed to satisfy floor while maximizing avg)

    Principle 4: MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
        Objective: Maximize average with range constraint
        Algorithm:
            1. Calculate range: high - low ≤ constraint_amount
            2. Maximize average subject to range constraint

        Example:
            Original: high=32k, low=12k, range=20k, avg=20.2k
            Constraint: 10k range max
            Result: high=22k, low=12k, range=10k, avg=17.2k
                    (compressed to satisfy range limit)
    """

async def format_detailed_results(
    self,
    participants: List[ParticipantAgent],
    final_payoffs: Dict[str, float],
    consensus_reached: bool,
    consensus_principle: Optional[JusticePrinciple],
    distribution_set: DistributionSet
) -> Dict[str, DetailedResult]:
    """
    Generate transparent results showing:

    For each participant:
        1. Final principle (consensus or random)
        2. Assigned income class
        3. Final earnings
        4. COUNTERFACTUAL earnings under each of 4 principles
            (with same income class assignment)
        5. Counterfactual earnings under each of 4 distributions
            (with same principle assignment)

    Returns: Dict[participant_name -> {
        assigned_income_class: IncomeClass,
        final_earnings: float,
        counterfactual_by_principle: Dict[principle -> earnings],
        counterfactual_by_distribution: Dict[distribution_idx -> earnings]
    }]

    Purpose: Transparency and post-hoc analysis
    "Here's what you earned. Here's what you would have earned under other principles."
    """

async def collect_final_rankings(
    self,
    participants: List[ParticipantAgent],
    results: Dict[str, DetailedResult]
) -> Dict[str, PrincipleRanking]:
    """
    Ask participants to re-rank principles after seeing results.

    Process:
    1. Generate final ranking prompt with counterfactual results
    2. Each participant ranks 4 principles 1-4 (best to worst)
    3. Parse ranking using utility_agent.parse_principle_ranking()
    4. Validate ranking completeness

    Returns: Dict[participant_name -> PrincipleRanking]

    Purpose: Measure shift in preferences after payoff revelation
    """
```

**Counterfactual Generation Example**:

```
Participant: Alice
Final Principle: MAXIMIZING_FLOOR (voted unanimously)
Distribution Set Round 4:
  - Dist 1: high=32k, med=24k, low=12k
  - Dist 2: high=28k, med=20k, low=13k
  - Dist 3: high=31k, med=21k, low=14k
  - Dist 4: high=21k, med=19k, low=15k

Alice's Assigned Income Class: medium (50% probability)

ACTUAL RESULT:
  Distribution Used: Dist 1 (application-chosen)
  Principle Used: MAXIMIZING_FLOOR
  Alice's Earnings: 24000

COUNTERFACTUALS (same income class):

By Principle (Dist 1):
  If Maximizing_Floor → 24000 (actual)
  If Maximizing_Average → 24000 (different mapping, potentially different income)
  If Avg+Floor(15k) → 25000
  If Avg+Range(10k) → 23000

By Distribution (Maximizing_Floor principle):
  If Dist 1 → 24000 (actual)
  If Dist 2 → 20000 (lower incomes)
  If Dist 3 → 21000
  If Dist 4 → 19000
```

---

## 4. Voting System: Deep Dive

### 4.1 Voting Architecture

The voting system orchestrates three phases:

```
VOTING FLOW:
├── Phase 1: VOTING INITIATION
│   └── Any agent can trigger: "Do you want to initiate voting?" (1=Yes/0=No)
│
├── Phase 2: VOTING CONFIRMATION
│   └── All must agree: "Do you confirm to participate in voting?" (1=Yes/0=No)
│       Requires 100% unanimous agreement
│
└── Phase 3: SECRET BALLOT (TwoStageVotingManager)
    ├── Stage 1: Principle Selection (1-4)
    │   └── Extract numerical response: "Which principle? (1/2/3/4)"
    │
    └── Stage 2: Amount Specification (principles 3 & 4)
        └── Extract amount: "What is your constraint? (positive integer)"
```

### 4.2 Consensus Definition

**Strict Unanimity**: All participants must vote:
- **Same principle** (1, 2, 3, or 4)
- **Same constraint amount** (if principle 3 or 4)

```python
def detect_consensus(votes: List[Tuple[int, Optional[int]]]) -> bool:
    """
    Example:
    votes = [
        (1, None),  # Alice: Floor, no constraint
        (1, None),  # Bob: Floor, no constraint
        (1, None),  # Carol: Floor, no constraint
    ]
    → consensus = True (all agree on principle 1)

    votes = [
        (3, 15000),  # Alice: Avg+Floor, floor=15k
        (3, 15000),  # Bob: Avg+Floor, floor=15k
        (3, 15000),  # Carol: Avg+Floor, floor=15k
    ]
    → consensus = True (all agree on principle 3 with 15k floor)

    votes = [
        (1, None),   # Alice: Floor
        (2, None),   # Bob: Average ← Different!
        (1, None),   # Carol: Floor
    ]
    → consensus = False (no unanimous agreement)
    """
    if not votes:
        return False

    first_vote = votes[0]
    return all(vote == first_vote for vote in votes)
```

### 4.3 Timeout and Retry Mechanisms

**Configuration**:
```yaml
phase2_settings:
  voting_initiation_timeout: 30  # seconds
  voting_confirmation_timeout: 30
  voting_secret_ballot_timeout: 45
  voting_retry_limit: 3
  voting_retry_backoff_factor: 1.5  # exponential backoff
```

**Retry Algorithm**:
```python
async def _invoke_with_retry(
    prompt: str,
    max_retries: int = 3,
    base_timeout: float = 30
) -> str:
    """
    Execute with exponential backoff retry:

    Attempt 1: timeout = 30s
    Attempt 2: timeout = 45s (30 × 1.5)
    Attempt 3: timeout = 67.5s (45 × 1.5)

    Stops on:
    - Successful response
    - Max retries exceeded
    """
    for attempt in range(max_retries):
        timeout = base_timeout * (1.5 ** attempt)
        try:
            return await asyncio.wait_for(
                participant.think(prompt),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            if attempt < max_retries - 1:
                await asyncio.sleep(1)  # Brief pause before retry
            else:
                raise
```

---

## 5. Configuration System

### 5.1 YAML-Driven Configuration

**File**: `config/models.py` with Pydantic validation

**Structure**:
```yaml
# Main experiment config
experiment_name: "baseline_v1"
phase2_rounds: 10
distribution_mode: "dynamic"  # or "original_values"

# Phase 2 settings
phase2_settings:
  finisher_restrictions_active: true
  statement_min_length: 50
  statement_validation_retries: 3
  public_history_max_length: 100000

  memory_management:
    guidance_style: "narrative"  # or "structured"
    enable_truncation: true

  voting:
    voting_confirmation_timeout: 30
    voting_secret_ballot_timeout: 45
    voting_retry_limit: 3

# Agents (8 participants for standard setup)
agents:
  - name: "Alice"
    model: "gpt-4o"
    language: "en"
    temperature: 0.7

  - name: "Bob"
    model: "gpt-4o"
    language: "en"
    temperature: 0.7

  # ... 6 more agents

# Income distribution
income_class_probabilities:
  high: 0.05
  medium_high: 0.10
  medium: 0.50
  medium_low: 0.25
  low: 0.10

# Reproducibility
seed: 42  # Global seed for all RNGs
```

### 5.2 Multi-Provider Model Support

**Intelligent Model Provider Detection**:

```python
# In experiment_agents/participant_agent.py
class ModelProvider(Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"

def detect_model_provider(model_str: str) -> ModelProvider:
    """
    Auto-detect provider from model string:

    - "gpt-4o" → OpenAI
    - "o1-mini" → OpenAI
    - "gemini-2.0-flash" → Google Gemini
    - "provider/model" → OpenRouter (e.g., "anthropic/claude-3.5-sonnet")
    - "ollama/gemma2:7b" → Ollama
    """
```

**Provider-Specific Implementation**:
```python
if provider == ModelProvider.OPENAI:
    # Native OpenAI Agents SDK
    client = Agents(api_key=os.getenv("OPENAI_API_KEY"))

elif provider == ModelProvider.GEMINI:
    # Google Gemini (if GEMINI_API_KEY set)
    client = anthropic.Anthropic(
        api_key=os.getenv("GEMINI_API_KEY"),
        base_url="https://generativelanguage.googleapis.com/openai/"
    )

elif provider == ModelProvider.OPENROUTER:
    # OpenRouter proxy (any model via provider/model format)
    client = anthropic.Anthropic(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1"
    )

elif provider == ModelProvider.OLLAMA:
    # Local Ollama instance
    client = anthropic.Anthropic(
        api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    )
```

---

## 6. Multilingual Support

### 6.1 Translation Architecture

**File**: `utils/language_manager.py`

```python
class SupportedLanguage(Enum):
    ENGLISH = "en"
    SPANISH = "es"
    MANDARIN = "zh"

class LanguageManager:
    """
    Centralized translation management.

    Loads translations from JSON files:
    - translations/en.json
    - translations/es.json
    - translations/zh.json
    """

    def get(self, key: str, **kwargs) -> str:
        """
        Retrieve localized string with substitutions.

        Example:
            message = lang_manager.get(
                "discussion_round_X_start",
                round=3,
                agent_name="Alice"
            )
            # Returns: "Round 3: Alice, please share your thoughts..."
        """
```

### 6.2 Multilingual Voting

**Number Format Parsing** (`utils/cultural_adaptation.py`):

```python
def get_amount_formatter(language: SupportedLanguage):
    """
    Multilingual number format parsing:

    English:
        "1000", "1,000" → 1000

    Spanish:
        "1.000" (period=thousands), "1,000" (comma) → 1000

    Mandarin:
        "1000", "1千" (thousand), "1万" (ten thousand) → culturally aware
    """
```

**Keyword Fallback** (`core/principle_keywords.py`):

```python
def match_principle_from_text(text: str, language: SupportedLanguage) -> Optional[int]:
    """
    Fallback principle detection via keywords when numerical extraction fails.

    Example responses:

    English:
        "I choose the maximizing average principle" → 2
        "Floor constraint sounds best" → 3

    Spanish:
        "Prefiero maximizar el piso" → 1
        "El promedio me parece bien" → 2

    Mandarin:
        "最大化平均收入" → 2
        "保证最低收入" → 1
    """
```

---

## 7. Memory Management Deep Dive

### 7.1 Three-Tier Memory System

```
TIER 1: CONTEXT WINDOW (ParticipantAgent.context)
├── Current memories (truncated to fit context)
├── Updated by MemoryService after each event
└── Sent to LLM in every prompt

TIER 2: AGENT MEMORY STORAGE (MemoryManager)
├── Persistent memory across rounds
├── Accumulated discussion statements
├── Voting events and results
└── Truncated intelligently to prevent overflow

TIER 3: DISCUSSION HISTORY (GroupDiscussionState.public_history)
├── Shared among all agents
├── All statements (truncated versions)
└── Used for context window building
```

### 7.2 Truncation Rules

**Applied by MemoryService**:

```python
TRUNCATION_RULES = {
    "statement": {
        "max_chars": 300,
        "strategy": "truncate_end_with_ellipsis"
    },
    "reasoning": {
        "max_chars": 200,
        "strategy": "truncate_end_with_ellipsis"
    },
    "result": {
        "max_chars": None,  # No truncation
        "strategy": "preserve_full"
    }
}

# Example:
original_statement = "I believe in maximizing the floor because fairness requires we protect the worst-off members of society..."
truncated = original_statement[:300] + "..."
# Result: "I believe in maximizing the floor because fairness requires we protect the worst-off members of society..."
```

**History Truncation**:

```python
def manage_discussion_history_length(
    self,
    history: List[Dict],
    max_length_chars: int = 100000
) -> List[Dict]:
    """
    If total history exceeds max_length_chars:
    1. Remove oldest statement first
    2. Recalculate total length
    3. Repeat until under limit

    Ensures recent context preserved while old statements pruned.
    """
```

### 7.3 Selective Memory Manager

**File**: `utils/selective_memory_manager.py`

**Two Update Strategies**:

```python
async def update_memory_simple(
    agent: ParticipantAgent,
    context: ParticipantContext,
    summary: str
) -> str:
    """
    Direct Memory Insertion (fast, ~1 second):

    Directly append summary to agent.context.memory
    No LLM involvement
    Used for: Discussion statements, status updates
    """

async def update_memory_complex(
    agent: ParticipantAgent,
    context: ParticipantContext,
    new_information: str,
    internal_reasoning: str = ""
) -> str:
    """
    LLM-Mediated Memory Integration (slow, ~10 seconds):

    Ask agent's LLM to integrate new information:
    "Here's what happened: {new_information}
    Current memory: {existing_memory}

    Integrate the new information into memory, updating beliefs..."

    Returns: Agent's synthesized memory update
    Used for: Complex results, voting outcomes with reasoning
    """

# Routing in MemoryService:
if event_type in [VOTING_INITIATED, DISCUSSION_STATEMENT]:
    await selective_memory_manager.update_memory_simple(...)
elif event_type in [VOTING_COMPLETE, FINAL_RESULTS]:
    await selective_memory_manager.update_memory_complex(...)
```

---

## 8. Reproducibility and Seeding

### 8.1 Seed Management

**File**: `utils/seed_manager.py`

```python
class SeedManager:
    """
    Centralized seeding for reproducible experiments.

    Three levels of seeding:
    """

    def __init__(self, global_seed: int = 42):
        self.global_seed = global_seed
        self.random = random.Random(global_seed)  # Global RNG
        self.seeds_by_component = {}  # Per-component seeds

    def get_seed_for(self, component_name: str) -> int:
        """
        Get deterministic seed for a component:

        Example:
            phase1_seed = seed_manager.get_seed_for("phase1")
            participant_1_seed = seed_manager.get_seed_for("participant_1")
            voting_seed = seed_manager.get_seed_for("voting")

        Deterministic: Same global_seed → Same component seeds
        """

    def _build_participant_rngs(self, config: ExperimentConfiguration):
        """
        Create deterministic RNG for each participant:

        for i, agent in enumerate(agents):
            seed = global_seed + i  # e.g., 42, 43, 44, 45...
            agent_rng = random.Random(seed)

        Result: Each participant's randomization is independent but seeded
        """
```

### 8.2 Reproducibility Guarantees

**With configuration + seed, experiment is fully reproducible**:

```python
# Run 1
config = ExperimentConfiguration.from_yaml("config.yaml")
config.seed = 42
results_1 = await FrohlichExperimentManager(config).run_complete_experiment()

# Run 2 (identical to Run 1)
config = ExperimentConfiguration.from_yaml("config.yaml")
config.seed = 42
results_2 = await FrohlichExperimentManager(config).run_complete_experiment()

# results_1 == results_2 (exactly, not probabilistically)
# Same distributions, same agent decisions, same payoffs, same consensus
```

**What's Seeded**:
- Distribution generation (multiplier)
- Participant income class assignment
- Speaking order randomization
- Finisher restriction randomization

**What's NOT Seeded** (LLM-dependent):
- Agent reasoning and statement generation (stochastic by nature)
- Agent's voting choices (depends on LLM temperature and model state)

---

## 9. Data Model Reference

### 9.1 Core Type Hierarchy

```python
# Justice principles (models/principle_types.py)
class JusticePrinciple(str, Enum):
    MAXIMIZING_FLOOR = "maximizing_floor"  # Principle 1
    MAXIMIZING_AVERAGE = "maximizing_average"  # Principle 2
    MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT = "maximizing_average_floor_constraint"  # Principle 3
    MAXIMIZING_AVERAGE_RANGE_CONSTRAINT = "maximizing_average_range_constraint"  # Principle 4

class PrincipleChoice(BaseModel):
    principle: JusticePrinciple
    constraint_amount: Optional[int] = None  # For principles 3 & 4
    certainty: CertaintyLevel  # VERY_UNSURE, UNSURE, NO_OPINION, SURE, VERY_SURE
    reasoning: Optional[str] = None

class PrincipleRanking(BaseModel):
    rankings: List[RankedPrinciple]  # 4 items, ranks 1-4
    certainty: CertaintyLevel

# Income distribution
class IncomeClass(str, Enum):
    HIGH = "high"
    MEDIUM_HIGH = "medium_high"
    MEDIUM = "medium"
    MEDIUM_LOW = "medium_low"
    LOW = "low"

class IncomeDistribution(BaseModel):
    high: int
    medium_high: int
    medium: int
    medium_low: int
    low: int

    # Methods:
    # - get_floor_income() → int
    # - get_average_income(probabilities) → float
    # - get_range() → int

class DistributionSet(BaseModel):
    distributions: List[IncomeDistribution]  # Always 4
    multiplier: float  # Applied to base

# Results
class Phase1Results(BaseModel):
    participant_name: str
    initial_ranking: PrincipleRanking
    post_explanation_ranking: PrincipleRanking
    application_results: List[ApplicationResult]  # 4 rounds
    completion_status: str

class Phase2Results(BaseModel):
    consensus_reached: bool
    final_principle: Optional[JusticePrinciple]
    final_constraint_amount: Optional[int]
    discussion_transcript: List[Dict]
    participant_results: Dict[str, DetailedResult]
    rounds_completed: int

class ExperimentResults(BaseModel):
    phase1_results: List[Phase1Results]
    phase2_results: Phase2Results
    metadata: Dict[str, Any]  # timestamps, seed, config file path, etc.
```

### 9.2 Context Objects

```python
class ParticipantContext(BaseModel):
    """
    Agent's working context updated throughout experiment.
    Sent in every prompt to the LLM.
    """
    participant_name: str
    current_phase: ExperimentPhase
    current_stage: ExperimentStage
    current_round: int
    memory: str  # Accumulated memory from MemoryService
    assigned_income_class: Optional[IncomeClass] = None
    interaction_type: Optional[str] = None  # "discussion", "voting", "ranking"

    # Phase 1 specific
    income_distributions: Optional[DistributionSet] = None
    principle_explanations: Optional[Dict] = None

    # Phase 2 specific
    public_discussion_history: Optional[str] = None
    current_principle_choice: Optional[PrincipleChoice] = None

class GroupDiscussionState(BaseModel):
    """
    Shared state for Phase 2 discussion.
    """
    public_history: List[Dict]  # All statements so far
    consensus_reached: bool
    consensus_principle: Optional[JusticePrinciple] = None
    consensus_constraint: Optional[int] = None
    current_round: int
    voting_in_progress: bool
```

---

## 10. Error Handling and Recovery

### 10.1 Error Type Hierarchy

**File**: `utils/error_handling.py`

```python
class ExperimentError(Exception):
    """Base for all experiment errors."""
    pass

class ExperimentLogicError(ExperimentError):
    """Logic errors in experiment flow."""
    pass

class AgentCommunicationError(ExperimentError):
    """Communication failures with agents."""
    pass

class ValidationError(ExperimentError):
    """Data validation errors."""
    pass

# Error handler with automatic retry
class ExperimentErrorHandler:
    async def handle_with_retry(
        self,
        coroutine,
        max_retries: int = 3,
        base_delay: float = 1.0
    ):
        """Execute with exponential backoff retry."""
```

### 10.2 Parsing Error Recovery

**File**: `utils/parsing_errors.py`

```python
class ParsingError(Enum):
    """Classification of parsing failures."""
    EXTRACTION_FAILED = "extraction_failed"  # Regex found nothing
    INVALID_FORMAT = "invalid_format"  # Found text but wrong format
    OUT_OF_RANGE = "out_of_range"  # Value outside expected range
    LANGUAGE_MISMATCH = "language_mismatch"  # Language doesn't match expected

def detect_parsing_failure_type(response: str, context: str) -> ParsingError:
    """Classify why parsing failed."""

def handle_parsing_error(error: ParsingError, response: str):
    """Route to appropriate recovery strategy."""
```

---

## 11. Experiment Flow Diagram

```
START: FrohlichExperimentManager
│
├─→ Load Configuration (ExperimentConfiguration.from_yaml)
│   └─→ Validate with Pydantic models
│
├─→ Create Agents
│   ├─→ 8 ParticipantAgents (with model provider detection)
│   └─→ 1 UtilityAgent (for parsing)
│
├─→ PHASE 1 EXECUTION (Parallel)
│   │
│   └─→ For each participant (asyncio.create_task):
│       ├─→ Initial Ranking (rank 4 principles)
│       ├─→ Principle Explanation (receive explanation)
│       ├─→ Post-Explanation Ranking (re-rank)
│       └─→ Application Tasks (4 rounds):
│           ├─→ Generate distribution set
│           ├─→ Agent selects distribution
│           ├─→ Calculate payoff
│           └─→ Update memory
│
├─→ PHASE 2 EXECUTION (Sequential)
│   │
│   ├─→ Initialize Services
│   │   ├─→ SpeakingOrderService
│   │   ├─→ DiscussionService
│   │   ├─→ VotingService
│   │   ├─→ MemoryService
│   │   ├─→ CounterfactualsService
│   │   └─→ ManipulatorService (optional)
│   │
│   ├─→ For each round (1 to phase2_rounds):
│   │   │
│   │   ├─→ Determine Speaking Order
│   │   │
│   │   ├─→ DISCUSSION STAGE:
│   │   │   └─→ For each speaker:
│   │   │       ├─→ Build discussion prompt
│   │   │       ├─→ Agent generates statement
│   │   │       ├─→ Validate (length check, retries)
│   │   │       ├─→ Update public history
│   │   │       └─→ Update agent memories
│   │   │
│   │   ├─→ VOTING CHECK:
│   │   │   ├─→ Any agent initiate voting? (1=Yes/0=No)
│   │   │   └─→ Is final round?
│   │   │
│   │   └─→ IF VOTING INITIATED OR FINAL ROUND:
│   │       │
│   │       ├─→ VOTING CONFIRMATION PHASE:
│   │       │   └─→ All agents confirm participation (1=Yes/0=No)
│   │       │       Requires 100% agreement
│   │       │
│   │       ├─→ IF ALL CONFIRMED:
│   │       │   │
│   │       │   ├─→ STAGE 1: Principle Selection (TwoStageVotingManager)
│   │       │   │   └─→ Extract principle number 1-4 via regex
│   │       │   │       (with keyword fallback)
│   │       │   │
│   │       │   ├─→ STAGE 2: Amount Specification (if principle 3 or 4)
│   │       │   │   └─→ Extract constraint amount via regex
│   │       │   │       (with cultural adaptation for number formats)
│   │       │   │
│   │       │   └─→ DETECT CONSENSUS:
│   │       │       └─→ All votes identical?
│   │       │           ├─→ YES: Set consensus_reached=True, exit rounds
│   │       │           └─→ NO: Update voting failure memory, continue
│   │       │
│   │       └─→ IF NOT ALL CONFIRMED:
│   │           └─→ Update confirmation failure memory, continue
│   │
│   └─→ [End of round loop - either consensus reached or max rounds]
│
├─→ PAYOFF CALCULATION (CounterfactualsService)
│   │
│   ├─→ Apply consensus principle (or random if no consensus)
│   ├─→ Randomly assign income classes (seeded, respects probabilities)
│   ├─→ Calculate final earnings for each agent
│   └─→ Calculate counterfactuals (earnings under all 4 principles)
│
├─→ FINAL RANKING COLLECTION
│   │
│   └─→ For each agent:
│       ├─→ Present results with counterfactuals
│       ├─→ Ask to re-rank principles
│       └─→ Parse ranking
│
└─→ COMPILE RESULTS & EXPORT
    ├─→ ExperimentResults (phase1 + phase2 + metadata)
    └─→ Save to JSON

END
```

---

## 12. Performance Characteristics

### 12.1 Phase 1 Timing

- **Per participant**: ~30-60 seconds
- **Total (8 participants parallel)**: ~60 seconds
- **Breakdown**:
  - Initial ranking: 5-10 seconds
  - Explanations: 10-15 seconds
  - 4 application rounds: 15-30 seconds
  - Memory updates: 5-10 seconds

### 12.2 Phase 2 Timing

- **Per round**: 2-4 minutes (depends on agent count)
- **Typical experiment** (10 rounds): 20-40 minutes
- **Breakdown per round**:
  - Discussion (8 agents × 20-30s each): 2-4 minutes
  - Voting check: 30 seconds
  - If voting initiated:
    - Confirmation phase: 1-2 minutes
    - Secret ballot (stage 1 + 2): 2-3 minutes
    - Consensus detection: instant

### 12.3 Token Usage (GPT-4o)

- **Phase 1**: ~50,000 tokens (8 agents)
- **Phase 2 (10 rounds)**: ~200,000 tokens
- **Total per experiment**: ~250,000 tokens (~$10-15 at current pricing)

---

## 13. Testing Strategy

### 13.1 Test Layers

```
ULTRA-FAST TESTS (< 1 second)
├── Unit tests for services (protocol-based mocking)
├── Voting validation tests
└── Data model validation tests
    └── Run with: pytest --mode=ultra_fast

DEVELOPMENT TESTS (< 5 minutes)
├── Component tests (with API calls, but small payloads)
├── Multilingual response parsing
└── Memory service behavior
    └── Run with: pytest --mode=dev

CI/CD TESTS (< 15 minutes)
├── Integration tests (full Phase 1 + Phase 2)
├── Live endpoint testing (requires API key)
└── Multilingual coverage validation (EN, ES, ZH)
    └── Run with: pytest --mode=ci

FULL TESTS (30-45 minutes)
├── End-to-end experiment runs
├── All language combinations
└── All configuration combinations
    └── Run with: pytest --mode=full
```

### 13.2 Key Test Files

```
tests/
├── unit/
│   ├── test_fast_response_parsing.py       # Multilingual voting parsing
│   ├── test_fast_data_flows.py             # Service integration (mocked)
│   └── test_fast_*.py                      # 40+ fast tests (~0.04s)
│
├── component/
│   ├── test_voting_service.py              # Voting service integration
│   ├── test_memory_service.py              # Memory management
│   └── test_distribution_generator.py      # Payoff calculations
│
├── integration/
│   ├── test_phase1_execution.py            # Full Phase 1 flow
│   └── test_phase2_execution.py            # Full Phase 2 with services
│
└── snapshots/
    └── test_golden_results.py              # Baseline result validation
```


### 15.2 Debug Logging

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check specific logger
logger = logging.getLogger("core.phase2_manager")
logger.setLevel(logging.DEBUG)

# Key log locations
# - core/phase2_manager.py: Overall flow
# - core/services/voting_service.py: Voting process
# - core/two_stage_voting_manager.py: Vote extraction
# - utils/selective_memory_manager.py: Memory updates
```

### 15.2 Transcript Logging

**Enable in config**:
```yaml
transcript_logging:
  enabled: true
  output_path: "transcripts/"
  include_instructions: true  # Expensive (adds ~5%)
  include_agent_responses: true  # Default, includes full responses
```

**Transcript contains**:
```json
{
  "experiment_id": "uuid",
  "timestamp": "2025-01-01T00:00:00",
  "interactions": [
    {
      "interaction_type": "phase1_discussion",
      "participant": "Alice",
      "prompt": "[Full prompt sent]",
      "response": "[Full response from agent]",
      "duration_seconds": 5.2
    },
    ...
  ]
}
```

---

## 16. Reference Implementation

**Quick Start**:
```bash
# Install dependencies
pip install -r requirements.txt

# Set API keys
export OPENAI_API_KEY="sk-..."
export OPENROUTER_API_KEY="sk-..."  # Optional

# Run quick test
python main.py config/fast.yaml results/test.json

# Run with custom config
python main.py config/my_experiment.yaml results/my_output.json

# Run tests
pytest --mode=ultra_fast  # 7 seconds
pytest --mode=dev        # 5 minutes
pytest --mode=ci         # 15 minutes
pytest --mode=full       # 30-45 minutes
```


