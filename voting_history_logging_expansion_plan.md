# Voting History Logging Expansion Plan

## Overview

This plan expands the existing agent-centric logging system to include **Voting History** as a third category alongside General Information and Per-Agent Information. The voting history will capture complete details of all voting events during Phase 2, including both formal votes (complex mode) and the assessment of agent responses by the system.

## Current Logging Structure Analysis

### Existing Categories
1. **General Information** (`GeneralExperimentInfo`)
   - Consensus status, final vote results summary
   - Config file, seed info, probabilities
   - Located in `models/logging_types.py:182-207`

2. **Per-Agent Information** (`AgentExperimentLog`)
   - Individual agent journeys through Phase 1 and Phase 2
   - Contains discussion rounds with basic vote intention detection
   - Located in `models/logging_types.py:104-180`

### Current Vote-Related Logging
- **Simple Vote Detection**: `MemoryStateCapture.extract_vote_intention()` in agent logs
- **Complex Vote Storage**: `discussion_state.vote_history` contains `VoteResult` objects
- **Final Vote Summary**: `final_vote_results` dict in general information

## Proposed Voting History Category

### New Data Structure: `VotingHistoryLog`

```python
class VoteRoundDetails(BaseModel):
    """Details of a single voting round."""
    round_number: int = Field(..., description="Phase 2 round when vote was triggered")
    vote_type: str = Field(..., description="Type of vote: 'formal_vote' or 'preference_consensus'")
    trigger_participant: Optional[str] = Field(None, description="Agent who triggered the vote")
    trigger_statement: Optional[str] = Field(None, description="Statement that triggered the vote")
    
    # Vote participation details
    participant_votes: List[Dict[str, Any]] = Field(..., description="Individual vote details")
    # Each participant_vote contains:
    # - participant_name: str
    # - raw_response: str (exact agent output)
    # - assessed_choice: str (system's interpretation)
    # - constraint_amount: Optional[float]
    # - vote_timestamp: str
    # - parsing_success: bool
    
    # Vote outcome
    consensus_reached: bool = Field(..., description="Whether consensus was achieved")
    agreed_principle: Optional[str] = Field(None, description="Principle if consensus reached")
    agreed_constraint: Optional[float] = Field(None, description="Constraint amount if applicable")
    vote_counts: Dict[str, int] = Field(default_factory=dict, description="Vote distribution")
    
    # Process details
    confirmation_phase_occurred: bool = Field(False, description="Whether confirmation phase occurred")
    confirmation_results: Optional[List[Dict[str, Any]]] = Field(None, description="Confirmation responses if complex mode")
    warnings: List[str] = Field(default_factory=list, description="System warnings during vote processing")


class VotingHistoryLog(BaseModel):
    """Complete voting history for the experiment."""
    voting_detection_mode: str = Field(..., description="Mode used: 'simple' or 'complex'")
    total_vote_attempts: int = Field(..., description="Total number of vote attempts")
    successful_votes: int = Field(..., description="Number of votes that reached consensus")
    
    vote_rounds: List[VoteRoundDetails] = Field(default_factory=list, description="Details of each vote round")
    
    # Summary statistics
    vote_statistics: Dict[str, Any] = Field(default_factory=dict, description="Voting statistics")
    # Contains:
    # - preference_detections_per_round: Dict[int, int]
    # - failed_parsing_attempts: int
    # - fallback_statements_during_votes: int
    # - average_consensus_round: Optional[float]
```

### Integration Points

#### 1. Enhanced `AgentCentricLogger`

```python
class AgentCentricLogger:
    def __init__(self):
        # ... existing code ...
        self.voting_history: Optional[VotingHistoryLog] = None
        self.current_vote_round: Optional[VoteRoundDetails] = None
    
    def initialize_voting_history(self, voting_detection_mode: str):
        """Initialize voting history tracking."""
        self.voting_history = VotingHistoryLog(
            voting_detection_mode=voting_detection_mode,
            total_vote_attempts=0,
            successful_votes=0
        )
    
    def start_vote_round(
        self, 
        round_number: int, 
        vote_type: str,
        trigger_participant: Optional[str] = None,
        trigger_statement: Optional[str] = None
    ):
        """Start tracking a new vote round."""
        if not self.voting_history:
            raise ValueError("Voting history not initialized")
        
        self.current_vote_round = VoteRoundDetails(
            round_number=round_number,
            vote_type=vote_type,
            trigger_participant=trigger_participant,
            trigger_statement=trigger_statement,
            participant_votes=[],
            consensus_reached=False
        )
        self.voting_history.total_vote_attempts += 1
    
    def log_vote_response(
        self,
        participant_name: str,
        raw_response: str,
        assessed_choice: str,
        constraint_amount: Optional[float] = None,
        parsing_success: bool = True,
        vote_timestamp: Optional[str] = None
    ):
        """Log individual participant vote response."""
        if not self.current_vote_round:
            raise ValueError("No active vote round")
        
        vote_detail = {
            "participant_name": participant_name,
            "raw_response": raw_response,
            "assessed_choice": assessed_choice,
            "constraint_amount": constraint_amount,
            "vote_timestamp": vote_timestamp or datetime.now().isoformat(),
            "parsing_success": parsing_success
        }
        
        self.current_vote_round.participant_votes.append(vote_detail)
    
    def log_confirmation_phase(
        self,
        confirmation_results: List[Dict[str, Any]]
    ):
        """Log confirmation phase results."""
        if not self.current_vote_round:
            raise ValueError("No active vote round")
        
        self.current_vote_round.confirmation_phase_occurred = True
        self.current_vote_round.confirmation_results = confirmation_results
    
    def complete_vote_round(
        self,
        consensus_reached: bool,
        agreed_principle: Optional[str] = None,
        agreed_constraint: Optional[float] = None,
        vote_counts: Optional[Dict[str, int]] = None,
        warnings: Optional[List[str]] = None
    ):
        """Complete and store the current vote round."""
        if not self.current_vote_round or not self.voting_history:
            raise ValueError("No active vote round or voting history")
        
        self.current_vote_round.consensus_reached = consensus_reached
        self.current_vote_round.agreed_principle = agreed_principle
        self.current_vote_round.agreed_constraint = agreed_constraint
        self.current_vote_round.vote_counts = vote_counts or {}
        self.current_vote_round.warnings = warnings or []
        
        if consensus_reached:
            self.voting_history.successful_votes += 1
        
        self.voting_history.vote_rounds.append(self.current_vote_round)
        self.current_vote_round = None
```

#### 2. Updated `TargetStateStructure`

```python
class TargetStateStructure(BaseModel):
    """Complete target state structure with voting history."""
    general_information: GeneralExperimentInfo
    agents: List[Dict[str, Any]]  # Agent logs in target format
    voting_history: Optional[VotingHistoryLog] = None  # NEW: Third category
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "general_information": {
                # ... existing general info fields ...
            },
            "agents": self.agents
        }
        
        # Add voting history if present
        if self.voting_history:
            result["voting_history"] = {
                "voting_detection_mode": self.voting_history.voting_detection_mode,
                "total_vote_attempts": self.voting_history.total_vote_attempts,
                "successful_votes": self.voting_history.successful_votes,
                "vote_rounds": [
                    {
                        "round_number": vote_round.round_number,
                        "vote_type": vote_round.vote_type,
                        "trigger_participant": vote_round.trigger_participant,
                        "trigger_statement": vote_round.trigger_statement,
                        "participant_votes": vote_round.participant_votes,
                        "consensus_reached": vote_round.consensus_reached,
                        "agreed_principle": vote_round.agreed_principle,
                        "agreed_constraint": vote_round.agreed_constraint,
                        "vote_counts": vote_round.vote_counts,
                        "confirmation_phase_occurred": vote_round.confirmation_phase_occurred,
                        "confirmation_results": vote_round.confirmation_results,
                        "warnings": vote_round.warnings
                    }
                    for vote_round in self.voting_history.vote_rounds
                ],
                "vote_statistics": self.voting_history.vote_statistics
            }
        
        return result
```

## Implementation Changes by Component

### 1. `models/logging_types.py`

**Changes:**
- Add `VoteRoundDetails` and `VotingHistoryLog` classes
- Update `TargetStateStructure` to include `voting_history` field
- Modify `to_dict()` method to serialize voting history

### 2. `utils/agent_centric_logger.py`

**Changes:**
- Add voting history initialization and tracking methods
- Integrate with existing Phase 2 logging workflow
- Update `generate_target_state()` to include voting history
- Modify `save_to_file()` to handle voting history serialization

### 3. `core/phase2_manager.py`

**Changes:**
- Initialize voting history at start of Phase 2
- Integrate vote round tracking for both simple and complex modes
- Log vote responses and outcomes through the logger

#### Simple Mode Integration (Preference Consensus)

```python
async def _run_group_discussion(self, config: ExperimentConfiguration, contexts: List[ParticipantContext], logger: AgentCentricLogger = None) -> GroupDiscussionResult:
    # ... existing code ...
    
    # Initialize voting history tracking
    if logger:
        logger.initialize_voting_history(config.voting_detection_mode)
    
    for round_num in range(1, config.phase2_rounds + 1):
        # ... participant statements ...
        
        # If all participants have stated preferences, check for consensus
        if num_participants_with_preferences == total_participants:
            # Start vote round tracking for preference consensus
            if logger:
                logger.start_vote_round(
                    round_number=round_num,
                    vote_type="preference_consensus"
                )
                
                # Log each participant's preference as a "vote"
                for participant_name, preference in discussion_state.current_round_preferences.items():
                    logger.log_vote_response(
                        participant_name=participant_name,
                        raw_response=f"Preference: {preference.principle.value}",
                        assessed_choice=preference.principle.value,
                        constraint_amount=preference.constraint_amount,
                        parsing_success=True
                    )
            
            preferences_list = list(discussion_state.current_round_preferences.values())
            consensus_reached, agreed_preference, warnings = self.utility_agent.check_preference_consensus(preferences_list)
            
            # Complete vote round
            if logger:
                vote_counts = {}
                for pref in preferences_list:
                    key = pref.principle.value
                    if pref.constraint_amount:
                        key += f" (${pref.constraint_amount:,})"
                    vote_counts[key] = vote_counts.get(key, 0) + 1
                
                logger.complete_vote_round(
                    consensus_reached=consensus_reached,
                    agreed_principle=agreed_preference.principle.value if agreed_preference else None,
                    agreed_constraint=agreed_preference.constraint_amount if agreed_preference else None,
                    vote_counts=vote_counts,
                    warnings=warnings
                )
```

#### Complex Mode Integration (Formal Voting)

```python
async def _handle_complex_voting_mode(self, participant: 'ParticipantAgent', statement: str, discussion_state: GroupDiscussionState, contexts: List[ParticipantContext]) -> bool:
    # ... existing code ...
    
    if vote_detection_result is None:
        return False
    
    # Start vote round tracking
    if self.logger:
        self.logger.start_vote_round(
            round_number=discussion_state.round_number,
            vote_type="formal_vote",
            trigger_participant=participant.name,
            trigger_statement=statement
        )
    
    # Confirmation phase
    confirmation_success = await self._conduct_confirmation_phase(
        participant.name, statement, contexts, discussion_state
    )
    
    # Log confirmation results
    if self.logger and hasattr(self, '_last_confirmation_results'):
        self.logger.log_confirmation_phase(self._last_confirmation_results)
    
    if not confirmation_success:
        # Complete failed vote round
        if self.logger:
            self.logger.complete_vote_round(
                consensus_reached=False,
                warnings=["Confirmation phase failed"]
            )
        return False
    
    # Secret ballot phase
    consensus_reached = await self._conduct_secret_ballot_phase(contexts, discussion_state)
    
    # Complete vote round with results
    if self.logger and discussion_state.last_vote_result:
        vote_result = discussion_state.last_vote_result
        self.logger.complete_vote_round(
            consensus_reached=vote_result.consensus_reached,
            agreed_principle=vote_result.agreed_principle.principle.value if vote_result.agreed_principle else None,
            agreed_constraint=vote_result.agreed_principle.constraint_amount if vote_result.agreed_principle else None,
            vote_counts=vote_result.vote_counts
        )
    
    return consensus_reached
```

#### Enhanced Secret Ballot Logging

```python
async def _conduct_secret_ballot_phase(self, contexts: List[ParticipantContext], discussion_state: GroupDiscussionState) -> bool:
    # ... existing code ...
    
    ballots = []
    
    for i, context in enumerate(contexts):
        participant = self.participants[i]
        
        # Get secret ballot from participant
        result = await Runner.run(participant.agent, ballot_prompt, context=context)
        ballot_response = result.final_output
        
        # Parse ballot using existing utility agent methods
        try:
            principle_choice = await self.utility_agent.parse_principle_choice_enhanced(ballot_response)
            ballots.append(principle_choice)
            
            # Log the vote response
            if self.logger:
                self.logger.log_vote_response(
                    participant_name=participant.name,
                    raw_response=ballot_response,
                    assessed_choice=principle_choice.principle.value,
                    constraint_amount=principle_choice.constraint_amount,
                    parsing_success=True
                )
            
        except Exception as e:
            # Log failed parsing
            if self.logger:
                self.logger.log_vote_response(
                    participant_name=participant.name,
                    raw_response=ballot_response,
                    assessed_choice="PARSING_FAILED",
                    parsing_success=False
                )
            
            return False
    
    # ... rest of consensus checking ...
```

### 4. Output Format Changes

The JSON output structure will now include a third top-level category:

```json
{
  "general_information": {
    "consensus_reached": true,
    "consensus_principle": "Maximizing average income",
    "final_vote_results": {
      "Agent_1": "Maximizing average income",
      "Agent_2": "Maximizing average income"
    }
    // ... other general fields
  },
  "agents": [
    {
      "name": "Agent_1",
      "phase_1": { /* Phase 1 logs */ },
      "phase_2": { /* Phase 2 logs including basic vote intention */ }
    }
    // ... other agents
  ],
  "voting_history": {
    "voting_detection_mode": "complex",
    "total_vote_attempts": 2,
    "successful_votes": 1,
    "vote_rounds": [
      {
        "round_number": 3,
        "vote_type": "formal_vote",
        "trigger_participant": "Agent_1",
        "trigger_statement": "I think we should vote on this principle.",
        "participant_votes": [
          {
            "participant_name": "Agent_1",
            "raw_response": "I vote for Maximizing average income principle.",
            "assessed_choice": "Maximizing average income",
            "constraint_amount": null,
            "vote_timestamp": "2024-08-26T14:30:15.123456",
            "parsing_success": true
          },
          {
            "participant_name": "Agent_2", 
            "raw_response": "I also choose the average income maximization approach.",
            "assessed_choice": "Maximizing average income",
            "constraint_amount": null,
            "vote_timestamp": "2024-08-26T14:30:16.789012",
            "parsing_success": true
          }
        ],
        "consensus_reached": true,
        "agreed_principle": "Maximizing average income",
        "agreed_constraint": null,
        "vote_counts": {
          "Maximizing average income": 2
        },
        "confirmation_phase_occurred": true,
        "confirmation_results": [
          {
            "participant": "Agent_1",
            "response": "Yes, I agree to vote",
            "agrees": true
          },
          {
            "participant": "Agent_2",
            "response": "I'm ready to vote", 
            "agrees": true
          }
        ],
        "warnings": []
      }
    ],
    "vote_statistics": {
      "preference_detections_per_round": {
        "1": 0,
        "2": 2,
        "3": 2
      },
      "failed_parsing_attempts": 0,
      "fallback_statements_during_votes": 0,
      "average_consensus_round": 3.0
    }
  }
}
```

## Testing Strategy

### 1. Unit Tests

- Test `VotingHistoryLog` data structures
- Test logger voting history methods
- Test serialization/deserialization

### 2. Integration Tests

- Test simple mode preference consensus logging
- Test complex mode formal vote logging
- Test mixed scenarios with failed votes
- Test backward compatibility with existing logs

### 3. Validation Tests

- Ensure existing log structure remains unchanged
- Verify voting history is optional and doesn't break old experiments
- Test edge cases (no votes, parsing failures, agent failures)

## Backward Compatibility

- Voting history is optional - existing experiments continue to work
- General information and agent logs remain unchanged
- Only new field added to output structure is `voting_history`
- Existing analysis scripts can ignore the new category

## Benefits

1. **Complete Vote Transparency**: Full visibility into all voting attempts and outcomes
2. **System Assessment Tracking**: Shows how the system interpreted agent responses
3. **Debugging Support**: Raw responses help debug parsing issues
4. **Research Value**: Detailed voting patterns for analysis
5. **Separate Concerns**: Voting details don't clutter agent or general logs
6. **Extensible**: Easy to add new voting-related metrics in the future

## Implementation Priority

1. **High Priority**: Data structures and basic logging integration
2. **Medium Priority**: Complex mode integration and confirmation phase logging
3. **Low Priority**: Advanced statistics and analysis features

This plan provides a comprehensive expansion of the logging system while maintaining the existing structure and ensuring backward compatibility.