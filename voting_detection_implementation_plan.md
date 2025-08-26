# Voting Detection Implementation Plan

## 1. Current System Analysis

### Current "Simple" Voting Detection System

The current system implements automatic consensus detection through **preference statements** rather than explicit voting. Here's how it works:

#### Current Flow (Phase 2 Manager: `phase2_manager.py:365-444`)
1. **Preference Detection**: After each participant statement, the system uses `utility_agent.detect_preference_statement()` to identify preference statements
2. **Preference Collection**: When all participants have stated preferences in a round, the system checks for consensus using `utility_agent.check_preference_consensus()`
3. **Automatic Consensus**: If all preferences match (including constraint amounts), consensus is automatically reached and Phase 2 ends

#### Current Detection Mechanism (`utility_agent.py`)
- **Pattern Matching**: Uses regex patterns to identify preference statements like "My preference is [principle]", "I prefer [principle]", etc.
- **LLM Fallback**: If pattern matching fails, uses LLM-based semantic analysis with the prompt `utility_preference_detection`
- **Constraint Validation**: Automatically validates constraint amounts for principles c and d

#### Configuration
- **No explicit voting configuration** exists in the current system
- The current system is effectively the "simple" mode mentioned in your request
- Configuration is handled through `ExperimentConfiguration` in `config/models.py`

## 2. Requested "Complex" Voting Detection System

### Requirements Analysis
Based on your request, the new "complex" system should:

1. **Dynamic Voting Intention Detection**: Agents can casually or explicitly express desire to vote
2. **Two-Step Voting Process**:
   - **Step A**: Public confirmation phase where all agents confirm/deny voting willingness
   - **Step B**: Secret ballot if unanimous agreement from Step A
3. **Termination Conditions**:
   - If unanimous agreement in secret ballot → group discussion ends
   - If agent lacks constraint specification → correction loop with memory update
4. **Semantic Understanding**: Use Utility Agent with appropriate prompts for intention detection

### Key Differences from Current System
| Aspect | Current (Simple) | Proposed (Complex) |
|--------|------------------|-------------------|
| Trigger | Automatic preference detection | Agent expresses voting desire |
| Detection Method | Pattern matching + LLM fallback | Semantic LLM analysis |
| Process | Single-step consensus check | Two-step voting process |
| Publicity | All preferences public | Step A public, Step B secret |
| Confirmation | Automatic | Explicit confirmation required |

## 3. Implementation Action Plan

### Phase 1: Configuration System Updates

#### 3.1 Add Voting Detection Configuration
**File**: `config/models.py`
**Location**: `ExperimentConfiguration` class

```python
# Add new field to ExperimentConfiguration
voting_detection_mode: str = Field("simple", description="Voting detection mode: 'simple' or 'complex'")

# Add validator
@field_validator('voting_detection_mode')
@classmethod
def validate_voting_detection_mode(cls, v):
    valid_modes = ["simple", "complex"]
    if v not in valid_modes:
        raise ValueError(f"Invalid voting detection mode: {v}. Must be one of {valid_modes}")
    return v
```

#### 3.2 Update Default Configuration
**File**: `config/default_config.yaml`

```yaml
# Add voting detection configuration
voting_detection_mode: "simple"  # Default to current behavior
```

### Phase 2: Data Models Extension

#### 2.1 Add Voting Intention Models
**File**: `models/experiment_types.py`

```python
class VotingIntention(BaseModel):
    """Represents a detected voting intention from an agent."""
    participant_name: str
    statement: str
    intention_detected: bool
    confidence_score: float = Field(ge=0.0, le=1.0)
    round_number: int

class VotingConfirmation(BaseModel):
    """Represents an agent's confirmation to participate in voting."""
    participant_name: str
    wants_to_vote: bool
    statement: str

class SecretBallot(BaseModel):
    """Represents a secret ballot cast by an agent."""
    participant_name: str
    principle_choice: PrincipleChoice
    is_anonymous: bool = True

class VotingSession(BaseModel):
    """Complete voting session state."""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    initiated_by: str
    initiation_statement: str
    confirmation_phase: List[VotingConfirmation] = Field(default_factory=list)
    secret_ballots: List[SecretBallot] = Field(default_factory=list)
    session_complete: bool = False
    consensus_reached: bool = False
    agreed_principle: Optional[PrincipleChoice] = None
```

#### 2.2 Update Group Discussion State
**File**: `models/experiment_types.py`

```python
class GroupDiscussionState(BaseModel):
    # ... existing fields ...
    
    # Add complex voting fields
    active_voting_session: Optional[VotingSession] = None
    voting_history: List[VotingSession] = Field(default_factory=list)
    pending_voting_intentions: List[VotingIntention] = Field(default_factory=list)
```

### Phase 3: Utility Agent Enhancements

#### 3.1 Add Voting Intention Detection
**File**: `experiment_agents/utility_agent.py`

```python
async def detect_voting_intention(self, statement: str, participant_name: str) -> Optional[VotingIntention]:
    """
    Semantically detect if participant expresses desire to vote.
    Uses LLM to understand casual or explicit voting intentions.
    """
    await self.async_init()
    
    language_manager = get_language_manager()
    detection_prompt = language_manager.get(
        "prompts.complex_voting_intention_detection",
        statement=statement,
        participant_name=participant_name
    )
    
    result = await Runner.run(self.parser_agent, detection_prompt)
    response = result.final_output.strip()
    
    # Parse LLM response for intention and confidence
    intention_detected = "VOTING_INTENTION_DETECTED" in response.upper()
    confidence_match = re.search(r'CONFIDENCE:\s*(\d*\.?\d+)', response, re.IGNORECASE)
    confidence_score = float(confidence_match.group(1)) if confidence_match else 0.5
    
    if intention_detected:
        return VotingIntention(
            participant_name=participant_name,
            statement=statement,
            intention_detected=True,
            confidence_score=confidence_score,
            round_number=0  # Will be set by phase2_manager
        )
    
    return None

async def conduct_voting_confirmation(self, participants: List[str], voting_context: str) -> List[VotingConfirmation]:
    """
    Conduct confirmation phase where all agents confirm voting willingness.
    """
    confirmations = []
    
    for participant_name in participants:
        confirmation_prompt = language_manager.get(
            "prompts.voting_confirmation_request",
            participant_name=participant_name,
            voting_context=voting_context
        )
        
        # This would need to be called by phase2_manager with actual participant agent
        # Return structure for phase2_manager to execute
        confirmations.append({
            'participant_name': participant_name,
            'prompt': confirmation_prompt
        })
    
    return confirmations

async def conduct_secret_ballot(self, participants: List[str]) -> List[SecretBallot]:
    """
    Conduct secret ballot phase.
    """
    ballots = []
    
    for participant_name in participants:
        ballot_prompt = language_manager.get(
            "prompts.secret_ballot_request",
            participant_name=participant_name
        )
        
        # Return structure for phase2_manager to execute
        ballots.append({
            'participant_name': participant_name,
            'prompt': ballot_prompt
        })
    
    return ballots

def check_voting_consensus(self, ballots: List[SecretBallot]) -> tuple[bool, Optional[PrincipleChoice], List[str]]:
    """
    Check if secret ballots reached consensus.
    Returns (consensus_reached, agreed_principle, warnings)
    """
    if not ballots:
        return False, None, ["No ballots received"]
    
    # Group ballots by principle and constraint amount
    ballot_groups = {}
    warnings = []
    
    for ballot in ballots:
        choice = ballot.principle_choice
        key = (choice.principle.value, choice.constraint_amount)
        
        if key not in ballot_groups:
            ballot_groups[key] = []
        ballot_groups[key].append(ballot)
        
        # Check for missing constraint amounts
        if (choice.constraint_amount is None and 
            choice.principle in [JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                               JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT]):
            warnings.append(f"Ballot from {ballot.participant_name} missing constraint amount")
    
    # Check for consensus (all ballots in same group)
    if len(ballot_groups) == 1:
        agreed_choice = list(ballot_groups.values())[0][0].principle_choice
        return True, agreed_choice, warnings
    
    return False, None, warnings
```

#### 3.2 Add Language Manager Prompts
**File**: `translations/english_prompts.json`

```json
{
  "complex_voting_intention_detection": "Analyze this statement to detect if the participant wants to initiate a voting session.\n\nStatement: \"{statement}\"\nParticipant: {participant_name}\n\nLook for expressions of voting desire such as:\n- \"I want to vote\"\n- \"Let's vote on this\"\n- \"I think we should vote\"\n- \"Ready to vote\"\n- \"Time to vote\"\n- Casual expressions like \"shall we vote?\" or \"vote time?\"\n\nProvide assessment:\nVOTING_INTENTION_DETECTED or NO_VOTING_INTENTION\nCONFIDENCE: [0.0-1.0]\n\nExplanation: [brief reasoning]",
  
  "voting_confirmation_request": "A group member has expressed desire to vote. Do you agree to participate in a voting session?\n\nContext: {voting_context}\n\nPlease respond with one of:\n- \"Yes, I agree to vote\"\n- \"No, I prefer more discussion\"\n- \"Yes, I'm ready to vote\"\n- \"No, not yet\"\n\nYour response will be public to all participants.",
  
  "secret_ballot_request": "VOTING SESSION - SECRET BALLOT\n\nPlease cast your secret ballot by clearly stating your principle preference.\n\nRemember the four principles:\n(a) Maximizing the floor income\n(b) Maximizing the average income  \n(c) Maximizing the average income with a floor constraint\n(d) Maximizing the average income with a range constraint\n\nFor constraint principles (c or d), you MUST specify the constraint amount.\n\nYour ballot is secret and will not be revealed to other participants.\n\nMy secret ballot choice is: [your principle preference]"
}
```

### Phase 4: Phase 2 Manager Integration

#### 4.1 Add Complex Voting Logic
**File**: `core/phase2_manager.py`

```python
async def _handle_complex_voting_detection(
    self,
    participant: ParticipantAgent,
    statement: str,
    discussion_state: GroupDiscussionState,
    contexts: List[ParticipantContext]
) -> bool:
    """
    Handle complex voting detection and initiate voting session if needed.
    Returns True if voting session was initiated, False otherwise.
    """
    
    # Check if voting intention is detected
    voting_intention = await self.utility_agent.detect_voting_intention(
        statement, participant.name
    )
    
    if not voting_intention:
        return False
    
    # Log voting intention detection
    self._log_info(f"Voting intention detected from {participant.name}")
    
    # Initiate voting session
    voting_session = VotingSession(
        initiated_by=participant.name,
        initiation_statement=statement
    )
    
    discussion_state.active_voting_session = voting_session
    
    # Step A: Confirmation Phase
    confirmation_success = await self._conduct_confirmation_phase(
        voting_session, contexts, discussion_state
    )
    
    if not confirmation_success:
        self._log_info("Voting confirmation failed - returning to discussion")
        discussion_state.active_voting_session = None
        return False
    
    # Step B: Secret Ballot Phase
    consensus_reached = await self._conduct_secret_ballot_phase(
        voting_session, contexts, discussion_state
    )
    
    # Complete voting session
    voting_session.session_complete = True
    discussion_state.voting_history.append(voting_session)
    discussion_state.active_voting_session = None
    
    return consensus_reached

async def _conduct_confirmation_phase(
    self,
    voting_session: VotingSession,
    contexts: List[ParticipantContext],
    discussion_state: GroupDiscussionState
) -> bool:
    """
    Conduct public confirmation phase.
    Returns True if all participants agree to vote.
    """
    
    self._log_info("=== VOTING CONFIRMATION PHASE ===")
    
    for i, context in enumerate(contexts):
        participant = self.participants[i]
        
        confirmation_prompt = f"""
A group member ({voting_session.initiated_by}) has expressed desire to vote.

Statement: "{voting_session.initiation_statement}"

Do you agree to participate in a voting session?

Please respond with:
- "Yes, I agree to vote" 
- "No, I prefer more discussion"

Your response will be public to all participants.
        """
        
        # Get confirmation from participant
        result = await Runner.run(participant.agent, confirmation_prompt, context=context)
        confirmation_response = result.final_output
        
        # Parse confirmation
        wants_to_vote = self._parse_voting_confirmation(confirmation_response)
        
        confirmation = VotingConfirmation(
            participant_name=participant.name,
            wants_to_vote=wants_to_vote,
            statement=confirmation_response
        )
        
        voting_session.confirmation_phase.append(confirmation)
        
        # Add to public history
        discussion_state.public_history += f"\n[VOTING CONFIRMATION] {participant.name}: {confirmation_response}"
        
        # If anyone disagrees, confirmation phase fails
        if not wants_to_vote:
            self._log_info(f"{participant.name} declined voting - confirmation failed")
            return False
    
    self._log_info("All participants agreed to vote - proceeding to secret ballot")
    return True

async def _conduct_secret_ballot_phase(
    self,
    voting_session: VotingSession,
    contexts: List[ParticipantContext],
    discussion_state: GroupDiscussionState
) -> bool:
    """
    Conduct secret ballot phase.
    Returns True if consensus is reached.
    """
    
    self._log_info("=== SECRET BALLOT PHASE ===")
    
    for i, context in enumerate(contexts):
        participant = self.participants[i]
        
        ballot_prompt = """
VOTING SESSION - SECRET BALLOT

Please cast your secret ballot by clearly stating your principle preference.

The four principles:
(a) Maximizing the floor income
(b) Maximizing the average income  
(c) Maximizing the average income with a floor constraint
(d) Maximizing the average income with a range constraint

For constraint principles (c or d), you MUST specify the constraint amount.

Your ballot is secret and will not be revealed to other participants.

My secret ballot choice is:
        """
        
        # Get secret ballot from participant
        result = await Runner.run(participant.agent, ballot_prompt, context=context)
        ballot_response = result.final_output
        
        # Parse ballot using existing utility agent methods
        try:
            principle_choice = await self.utility_agent.parse_principle_choice_enhanced(ballot_response)
            
            ballot = SecretBallot(
                participant_name=participant.name,
                principle_choice=principle_choice
            )
            
            voting_session.secret_ballots.append(ballot)
            self._log_info(f"Secret ballot received from {participant.name}")
            
        except Exception as e:
            self._log_warning(f"Failed to parse ballot from {participant.name}: {e}")
            # Could implement re-prompt logic here
            return False
    
    # Check for consensus
    consensus_reached, agreed_principle, warnings = self.utility_agent.check_voting_consensus(
        voting_session.secret_ballots
    )
    
    # Handle missing constraint amounts
    if not consensus_reached and warnings:
        await self._handle_constraint_corrections(voting_session, contexts, warnings)
        # Re-check consensus after corrections
        consensus_reached, agreed_principle, _ = self.utility_agent.check_voting_consensus(
            voting_session.secret_ballots
        )
    
    if consensus_reached:
        voting_session.consensus_reached = True
        voting_session.agreed_principle = agreed_principle
        self._log_info(f"Consensus reached: {agreed_principle.principle.value}")
        
        # Add consensus to public history (without revealing individual ballots)
        discussion_state.public_history += f"\n[VOTING RESULT] Consensus reached: {agreed_principle.principle.value}"
        if agreed_principle.constraint_amount:
            discussion_state.public_history += f" (${agreed_principle.constraint_amount:,})"
    else:
        self._log_info("No consensus reached in secret ballot")
        discussion_state.public_history += "\n[VOTING RESULT] No consensus reached - discussion continues"
    
    return consensus_reached

def _parse_voting_confirmation(self, response: str) -> bool:
    """Parse voting confirmation response."""
    response_lower = response.lower().strip()
    
    # Positive indicators
    positive_patterns = [
        r'\byes\b', r'\bagree\b', r'\bready\b', r'\bvote\b'
    ]
    
    # Negative indicators  
    negative_patterns = [
        r'\bno\b', r'\bdecline\b', r'\bprefer.*discussion\b', r'\bnot yet\b'
    ]
    
    # Check negative first (more specific)
    for pattern in negative_patterns:
        if re.search(pattern, response_lower):
            return False
    
    # Check positive
    for pattern in positive_patterns:
        if re.search(pattern, response_lower):
            return True
    
    # Default to no if unclear
    return False
```

#### 4.2 Integrate with Main Discussion Loop
**File**: `core/phase2_manager.py`

Modify the main discussion loop to check voting detection mode:

```python
async def _run_group_discussion(self, config, contexts, logger) -> GroupDiscussionResult:
    # ... existing code ...
    
    for speaking_order_position, participant_idx in enumerate(speaking_order):
        # ... get statement ...
        
        # Check voting detection mode
        if config.voting_detection_mode == "complex":
            # Try complex voting detection
            voting_initiated = await self._handle_complex_voting_detection(
                participant, statement, discussion_state, contexts
            )
            
            if voting_initiated:
                # Voting session completed - check if consensus was reached
                if discussion_state.voting_history[-1].consensus_reached:
                    agreed_principle = discussion_state.voting_history[-1].agreed_principle
                    return GroupDiscussionResult(
                        consensus_reached=True,
                        agreed_principle=agreed_principle,
                        final_round=round_num,
                        discussion_history=discussion_state.public_history,
                        vote_history=[]  # Complex voting uses different structure
                    )
                # If no consensus, continue discussion
                continue
        
        else:  # Simple mode (current behavior)
            # ... existing preference detection code ...
```

### Phase 5: Error Handling and Edge Cases

#### 5.1 Constraint Correction Loop
**File**: `core/phase2_manager.py`

```python
async def _handle_constraint_corrections(
    self,
    voting_session: VotingSession,
    contexts: List[ParticipantContext],
    warnings: List[str]
) -> None:
    """
    Handle missing constraint amounts by re-prompting participants.
    """
    
    for warning in warnings:
        # Extract participant name from warning
        participant_match = re.search(r'from (\w+)', warning)
        if not participant_match:
            continue
        
        participant_name = participant_match.group(1)
        participant_idx = next(
            i for i, p in enumerate(self.participants) 
            if p.name == participant_name
        )
        
        participant = self.participants[participant_idx]
        context = contexts[participant_idx]
        
        # Update memory with correction
        correction_content = f"Your previous ballot was missing a constraint amount. {warning}"
        context.memory = await MemoryManager.prompt_agent_for_memory_update(
            participant, context, correction_content
        )
        
        # Re-prompt for corrected ballot
        correction_prompt = f"""
Your previous ballot was incomplete. You selected a constraint principle but didn't specify the constraint amount.

Please provide a corrected ballot with the constraint amount:

For floor constraint (c): specify minimum income (e.g., "$15,000")
For range constraint (d): specify maximum gap (e.g., "$50,000")

My corrected ballot choice is:
        """
        
        result = await Runner.run(participant.agent, correction_prompt, context=context)
        corrected_response = result.final_output
        
        # Parse and update ballot
        try:
            corrected_choice = await self.utility_agent.parse_principle_choice_enhanced(
                corrected_response
            )
            
            # Update ballot in voting session
            for ballot in voting_session.secret_ballots:
                if ballot.participant_name == participant_name:
                    ballot.principle_choice = corrected_choice
                    break
                    
        except Exception as e:
            self._log_warning(f"Failed to parse corrected ballot from {participant_name}: {e}")
```

### Phase 6: Testing and Integration

#### 6.1 Unit Tests
**File**: `tests/unit/test_complex_voting_detection.py`

```python
import pytest
from experiment_agents.utility_agent import UtilityAgent
from models.experiment_types import VotingIntention, VotingConfirmation, SecretBallot

class TestComplexVotingDetection:
    
    @pytest.fixture
    async def utility_agent(self):
        agent = UtilityAgent()
        await agent.async_init()
        return agent
    
    @pytest.mark.asyncio
    async def test_voting_intention_detection_explicit(self, utility_agent):
        statement = "I think we should vote on this now."
        intention = await utility_agent.detect_voting_intention(statement, "Alice")
        
        assert intention is not None
        assert intention.intention_detected is True
        assert intention.participant_name == "Alice"
    
    @pytest.mark.asyncio
    async def test_voting_intention_detection_casual(self, utility_agent):
        statement = "Maybe it's time to vote?"
        intention = await utility_agent.detect_voting_intention(statement, "Bob")
        
        assert intention is not None
        assert intention.intention_detected is True
    
    @pytest.mark.asyncio
    async def test_no_voting_intention(self, utility_agent):
        statement = "I prefer principle A for these reasons..."
        intention = await utility_agent.detect_voting_intention(statement, "Charlie")
        
        assert intention is None
```

#### 6.2 Integration Tests
**File**: `tests/integration/test_complex_voting_flow.py`

```python
import pytest
from core.phase2_manager import Phase2Manager
from experiment_agents.utility_agent import UtilityAgent
from config.models import ExperimentConfiguration

class TestComplexVotingFlow:
    
    @pytest.mark.asyncio
    async def test_complete_complex_voting_flow(self):
        """Test full complex voting flow from intention to consensus."""
        # Setup test configuration with complex voting
        config = ExperimentConfiguration(
            voting_detection_mode="complex",
            # ... other config
        )
        
        # Test full flow...
        # This would require more extensive setup with mock agents
```

### Phase 7: Documentation Updates

#### 7.1 Update CLAUDE.md
**File**: `CLAUDE.md`

Add section about voting detection modes:

```markdown
### Voting Detection Modes

The system supports two voting detection modes:

#### Simple Mode (Default)
- Automatic consensus detection through preference statements
- No explicit voting process
- Consensus reached when all participants state matching preferences

#### Complex Mode  
- Agent-initiated voting through expressed intentions
- Two-phase voting process: confirmation + secret ballot
- Semantic intention detection using LLM analysis

Configure via YAML:
```yaml
voting_detection_mode: "complex"  # or "simple"
```
```

## Summary

This implementation plan provides:

1. **Backward Compatibility**: Default "simple" mode maintains current behavior
2. **Configurable System**: Easy switching between detection modes via configuration
3. **Robust Detection**: LLM-based semantic analysis for voting intentions
4. **Complete Flow**: Two-phase voting process with confirmation and secret ballots
5. **Error Handling**: Constraint correction loops and validation
6. **Comprehensive Testing**: Unit and integration test coverage
7. **Documentation**: Updated user guides and API documentation

The implementation follows the existing architectural patterns and integrates seamlessly with the current agent-managed memory system, language manager, and error handling frameworks.