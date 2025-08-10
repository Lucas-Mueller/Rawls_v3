# Phase 2 Voting Mechanism Fix - Implementation Plan

**Date**: August 10, 2025  
**Priority**: Critical  
**Status**: Ready for Implementation  
**Estimated Time**: 4-6 hours

## Overview

This plan addresses the critical failure in the Phase 2 voting mechanism where agents cannot trigger votes despite clear consensus. The issue stems from broken vote detection logic that prevents the consensus mechanism from functioning.

## Problem Statement

- **Current Issue**: Vote detection system fails to recognize natural language vote proposals
- **Impact**: 100% failure rate for Phase 2 consensus mechanism
- **Root Cause**: Overly rigid pattern matching expecting exact "VOTE_PROPOSAL:" format
- **Evidence**: All agents agreed on principle and amount but system recorded "consensus_reached": false

## Implementation Strategy

### Phase 1: Immediate Fix (Critical Priority)
**Timeline: 1-2 hours**

#### 1.1 Fix Vote Detection Logic Using Utility Agent Pattern
**File**: `experiment_agents/utility_agent.py`

Replace the current rigid pattern matching with utility agent-based detection (consistent with existing system patterns):

```python
async def extract_vote_from_statement(self, statement: str) -> Optional[VoteProposal]:
    """Detect if participant is proposing a vote using utility agent analysis."""
    
    # Use the same pattern as other parsing methods in this class
    detection_prompt = self.language_manager.get_vote_detection_prompt(statement)
    
    try:
        result = await Runner.run(self.parser_agent, detection_prompt)
        response_text = result.final_output.strip()
        
        # Parse the utility agent's structured response
        if response_text.startswith("VOTE_PROPOSAL:"):
            proposal_text = response_text[len("VOTE_PROPOSAL:"):].strip()
            return VoteProposal(
                proposed_by="participant",
                proposal_text=proposal_text
            )
        elif response_text.startswith("NO_VOTE"):
            return None
        else:
            # Fallback: if format is unexpected, try keyword detection
            return self._fallback_keyword_detection(statement)
            
    except Exception as e:
        logger.error(f"Error in vote detection: {e}")
        return self._fallback_keyword_detection(statement)

def _fallback_keyword_detection(self, statement: str) -> Optional[VoteProposal]:
    """Fallback keyword-based detection if utility agent fails."""
    vote_keywords = [
        "propose a vote", "propose we vote", "call for a vote", 
        "ready to vote", "let's vote", "should vote", "vote on",
        "move to vote", "conduct a vote", "proceed with vote"
    ]
    
    statement_lower = statement.lower()
    for keyword in vote_keywords:
        if keyword in statement_lower:
            return VoteProposal(
                proposed_by="participant",
                proposal_text=f"Vote detected via keyword '{keyword}': {statement[:100]}..."
            )
    return None
```

**File**: `utils/language_manager.py`

Add the vote detection prompt (following existing pattern):

```python
def get_vote_detection_prompt(self, statement: str) -> str:
    """Generate prompt for vote detection analysis."""
    return f"""You are analyzing a participant's statement to detect if they are proposing a vote.

Participant Statement: "{statement}"

Your task is to determine if this participant is:
1. Explicitly proposing to conduct a vote
2. Suggesting the group should vote now
3. Indicating readiness to vote on a specific principle
4. Calling for consensus through voting

Look for phrases like:
- "I propose we vote"
- "Let's vote on"
- "Ready to vote"
- "Call for a vote"
- "Should we vote"
- "Time to vote"
- "Proceed with a vote"

If the participant IS proposing a vote, respond with:
VOTE_PROPOSAL: [brief description of what they want to vote on]

If the participant is NOT proposing a vote, respond with:
NO_VOTE

Be generous in detection - if there's reasonable indication they want to vote, detect it."""
```

#### 1.2 Add Comprehensive Logging
**File**: `core/phase2_manager.py`

Add detailed logging around vote detection:

```python
# In _get_participant_statement_enhanced method, after statement extraction
vote_proposal = await self.utility_agent.extract_vote_from_statement(statement)

# Add logging
import logging
logger = logging.getLogger(__name__)

if vote_proposal:
    logger.info(f"VOTE PROPOSAL DETECTED from {participant.name}: {vote_proposal.proposal_text}")
else:
    logger.debug(f"No vote proposal detected in statement from {participant.name}: {statement[:100]}...")
```

#### 1.3 Emergency Test Case
**File**: `test_vote_detection_fix.py` (new)

Create immediate test to verify the fix:

```python
#!/usr/bin/env python3
"""Test the vote detection fix with real agent statements."""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('OPENAI_API_KEY', 'test-key')

from experiment_agents.utility_agent import UtilityAgent

# Real statements from the failed experiment
TEST_STATEMENTS = [
    "I propose we vote on maximizing the average income with a floor constraint of $12,000.",
    "Since we have reached agreement on both the principle and floor amount, I propose that we vote.",
    "I am ready to call for a vote. The group has repeatedly converged on the same principle.",
    "Let's move forward with a vote on this principle now.",
    "I think we should conduct a vote on maximizing average income with floor constraint.",
    "This is just discussion, no voting mentioned here.",  # Should NOT detect
]

async def test_vote_detection_fix():
    """Test that the vote detection fix works."""
    print("Testing Vote Detection Fix")
    print("=" * 40)
    
    utility_agent = UtilityAgent()
    
    for i, statement in enumerate(TEST_STATEMENTS):
        print(f"\nTest {i+1}: {statement[:50]}...")
        
        try:
            vote_proposal = await utility_agent.extract_vote_from_statement(statement)
            
            if vote_proposal:
                print(f"✅ VOTE DETECTED: {vote_proposal.proposal_text}")
            else:
                print("❌ NO VOTE DETECTED")
                if i < 5:  # First 5 should detect votes
                    print("   ⚠️  THIS IS A FAILURE - VOTE SHOULD HAVE BEEN DETECTED")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    print("\n" + "=" * 40)
    print("Fix validation complete!")

if __name__ == "__main__":
    asyncio.run(test_vote_detection_fix())
```

### Phase 2: Robustness Improvements (High Priority)
**Timeline: 2-3 hours**

#### 2.1 Enhanced Vote Proposal Detection
**File**: `models/response_types.py`

Add structured vote proposal types:

```python
class VoteProposal(BaseModel):
    """Represents a vote proposal from a participant."""
    proposed_by: str
    proposal_text: str
    confidence: float = Field(default=1.0, description="Confidence in vote detection (0-1)")
    detection_method: str = Field(default="keyword", description="Method used to detect vote")
```

#### 2.2 Multi-Method Detection System
**File**: `experiment_agents/utility_agent.py`

Implement multiple detection approaches:

```python
async def extract_vote_from_statement(self, statement: str) -> Optional[VoteProposal]:
    """Enhanced vote detection using multiple methods."""
    
    # Method 1: High-confidence keywords
    high_confidence_patterns = [
        r"i propose (?:a |we |to )?vote",
        r"let'?s (?:have a |conduct a |)?vote",
        r"call for (?:a )?vote",
        r"ready to vote",
        r"time to vote",
        r"move(?:ing)? to (?:a )?vote"
    ]
    
    # Method 2: Medium-confidence patterns  
    medium_confidence_patterns = [
        r"should vote",
        r"vote (?:on|for)",
        r"proceed with (?:a )?vote",
        r"consensus.*vote",
        r"agreement.*vote"
    ]
    
    # Method 3: Semantic analysis for complex cases
    # ... (implement semantic understanding)
    
    # Return proposal with confidence and method info
```

#### 2.3 Voting State Management
**File**: `models/experiment_types.py`

Add vote tracking:

```python
class GroupDiscussionState(BaseModel):
    """Enhanced state tracking for group discussions."""
    vote_proposals_detected: List[VoteProposal] = Field(default_factory=list)
    vote_detection_log: List[str] = Field(default_factory=list)
    failed_vote_attempts: int = 0
```

### Phase 3: System Resilience (Medium Priority)
**Timeline: 1-2 hours**

#### 3.1 Utility Agent-Based Consensus Detection
**File**: `experiment_agents/utility_agent.py`

Add new utility agent methods for agreement analysis:

```python
async def detect_group_consensus(
    self, 
    recent_statements: List[str], 
    participant_names: List[str]
) -> Optional[PrincipleChoice]:
    """Use utility agent to detect if group has reached implicit consensus."""
    
    statements_text = "\n".join([f"{name}: {stmt}" for name, stmt in zip(participant_names, recent_statements)])
    
    consensus_prompt = self.language_manager.get_consensus_detection_prompt(statements_text)
    
    try:
        result = await Runner.run(self.parser_agent, consensus_prompt)
        response_text = result.final_output.strip()
        
        if response_text.startswith("CONSENSUS_DETECTED:"):
            principle_text = response_text[len("CONSENSUS_DETECTED:"):].strip()
            return await self._parse_consensus_principle(principle_text)
        elif response_text.startswith("NO_CONSENSUS"):
            return None
            
    except Exception as e:
        logger.error(f"Error in consensus detection: {e}")
        return None

async def analyze_agreement_level(
    self, 
    statements: List[str], 
    participant_names: List[str]
) -> Dict[str, Any]:
    """Analyze how close the group is to agreement."""
    
    analysis_prompt = self.language_manager.get_agreement_analysis_prompt(statements, participant_names)
    
    result = await Runner.run(self.parser_agent, analysis_prompt)
    response_text = result.final_output.strip()
    
    # Parse structured response for agreement level, common principles, etc.
    return self._parse_agreement_analysis(response_text)
```

**File**: `utils/language_manager.py`

Add consensus detection prompts:

```python
def get_consensus_detection_prompt(self, statements_text: str) -> str:
    """Generate prompt for detecting group consensus."""
    return f"""You are analyzing a group discussion to detect if participants have reached consensus on a justice principle.

Recent Statements:
{statements_text}

Analyze these statements to determine if ALL participants are expressing support for the SAME justice principle with the SAME constraint amount (if applicable).

Look for indicators of consensus:
- All participants mention the same principle
- All participants agree on the same constraint amount ($X,XXX)
- Participants acknowledge agreement with each other
- Statements like "I agree with [name]", "we all support", "consensus on"

The four justice principles are:
1. Maximizing the floor income
2. Maximizing the average income  
3. Maximizing the average income with a floor constraint
4. Maximizing the average income with a range constraint

If you detect clear consensus, respond with:
CONSENSUS_DETECTED: [principle name] [with constraint amount if applicable]

If there is no clear consensus, respond with:
NO_CONSENSUS

Be conservative - only detect consensus if it's very clear all participants agree."""

def get_agreement_analysis_prompt(self, statements: List[str], names: List[str]) -> str:
    """Generate prompt for analyzing agreement level."""
    statements_text = "\n".join([f"{name}: {stmt}" for name, stmt in zip(names, statements)])
    
    return f"""Analyze the level of agreement in this group discussion.

Statements:
{statements_text}

Provide analysis in this format:
AGREEMENT_LEVEL: [HIGH/MEDIUM/LOW]
COMMON_PRINCIPLE: [principle if any agreement exists]
DISAGREEMENTS: [list any points of disagreement]
READY_FOR_VOTE: [YES/NO based on whether group seems ready]

Focus on justice principle preferences and constraint amounts."""
```

**File**: `core/phase2_manager.py`

Use utility agent for consensus detection:

```python
async def _check_implicit_consensus(
    self, 
    contexts: List[ParticipantContext], 
    discussion_state: GroupDiscussionState
) -> Optional[PrincipleChoice]:
    """Check if agents have reached implicit consensus using utility agent analysis."""
    
    # Get recent statements from each participant
    recent_statements = []
    participant_names = []
    
    # Collect last statement from each participant (last 1-2 rounds)
    for i, context in enumerate(contexts):
        recent_statement = self._get_last_statement_from_participant(discussion_state, context.name)
        if recent_statement:
            recent_statements.append(recent_statement)
            participant_names.append(context.name)
    
    if len(recent_statements) >= len(contexts):
        # Use utility agent to detect consensus
        consensus = await self.utility_agent.detect_group_consensus(recent_statements, participant_names)
        
        if consensus:
            logger.info(f"Implicit consensus detected by utility agent: {consensus}")
            return consensus
    
    return None

async def _analyze_group_readiness_for_vote(
    self, 
    contexts: List[ParticipantContext], 
    discussion_state: GroupDiscussionState
) -> bool:
    """Use utility agent to analyze if group is ready for voting."""
    
    recent_statements = []
    participant_names = []
    
    # Get last 2 statements from each participant
    for context in contexts:
        statements = self._get_recent_statements_from_participant(discussion_state, context.name, count=2)
        recent_statements.extend(statements)
        participant_names.extend([context.name] * len(statements))
    
    analysis = await self.utility_agent.analyze_agreement_level(recent_statements, participant_names)
    
    return analysis.get('ready_for_vote', False) or analysis.get('agreement_level') == 'HIGH'
```

#### 3.2 Fallback Voting Trigger
**File**: `core/phase2_manager.py`

Add emergency vote trigger:

```python
async def _emergency_vote_check(
    self, 
    round_num: int, 
    max_rounds: int, 
    contexts: List[ParticipantContext], 
    config: ExperimentConfiguration
) -> bool:
    """Trigger emergency vote if near end of rounds with apparent consensus."""
    
    # If we're in last 25% of rounds and no vote has been attempted
    if round_num >= (max_rounds * 0.75) and not hasattr(self, '_emergency_vote_attempted'):
        
        # Check for implicit consensus
        implicit_consensus = await self._check_implicit_consensus(contexts, discussion_state)
        
        if implicit_consensus:
            logger.warning(f"Emergency vote trigger: Detected implicit consensus on {implicit_consensus}")
            self._emergency_vote_attempted = True
            return True
    
    return False
```

### Phase 4: Testing & Validation (High Priority)
**Timeline: 1 hour**

#### 4.1 Comprehensive Test Suite
**File**: `tests/integration/test_phase2_voting.py`

```python
class TestPhase2Voting:
    """Comprehensive tests for Phase 2 voting mechanism."""
    
    async def test_vote_detection_real_scenarios(self):
        """Test with real agent statements from failed experiments."""
        
    async def test_consensus_with_vote_detection(self):
        """End-to-end test: agents reach consensus and vote is triggered."""
        
    async def test_unanimous_agreement_flow(self):
        """Test the full unanimous agreement -> vote -> consensus flow."""
        
    async def test_emergency_consensus_detection(self):
        """Test fallback mechanisms when vote detection fails."""
```

#### 4.2 Regression Testing
**File**: `test_experiment_scenarios.py`

Test with the exact failed scenario:
- 3 agents (Alice, Bob, Donald)
- Same personalities and preferences  
- Same principle agreement ($12,000 floor constraint)
- Verify consensus is reached

## Implementation Checklist

### Critical Path (Must Complete First)
- [ ] **Fix vote detection logic** in `utility_agent.py`
- [ ] **Add logging** to track vote detection attempts  
- [ ] **Create emergency test** to validate fix
- [ ] **Test with failed experiment scenario**

### High Priority (Complete Same Day)
- [ ] **Multi-method detection** for robustness
- [ ] **Enhanced vote proposal types** with confidence
- [ ] **Implicit consensus detection** as backup
- [ ] **Emergency vote trigger** for late-round consensus

### Medium Priority (Complete Within 2 Days)
- [ ] **Comprehensive test suite** for voting mechanism
- [ ] **Integration tests** with real experiment scenarios
- [ ] **Performance monitoring** for vote detection
- [ ] **Documentation updates** for voting mechanism

## Validation Criteria

### Must Pass Before Deployment
1. **Vote Detection**: 95%+ accuracy on real agent statements
2. **End-to-End**: Failed experiment scenario now reaches consensus
3. **No Regressions**: Existing functionality remains intact
4. **Performance**: Vote detection adds <100ms per round

### Success Metrics
- **Primary**: experiment_results_*.json shows `"consensus_reached": true` for agreed scenarios  
- **Secondary**: Agents successfully complete voting process within reasonable rounds
- **Tertiary**: System logs show clear vote detection and unanimous agreement flows

## Risk Assessment

### Low Risk
- **Keyword detection**: Simple and reliable for explicit vote statements
- **Additional logging**: Cannot break existing functionality

### Medium Risk  
- **Semantic analysis**: May have edge cases with complex statements
- **Emergency triggers**: Could activate inappropriately

### High Risk
- **Changing core voting logic**: Could introduce new failure modes

### Mitigation Strategies
- **Gradual rollout**: Test keyword detection first, then add semantic analysis
- **Extensive logging**: Track all vote detection attempts for debugging
- **Rollback plan**: Keep original code commented for quick reversion

## Success Definition

**The fix is successful when:**
1. Agents who explicitly propose votes have their proposals detected
2. The failed experiment scenario (`experiment_results_20250810_111811.json`) would now reach consensus
3. No existing functionality is broken
4. Vote detection works reliably across different agent personalities and statement styles

## Post-Implementation

### Monitoring
- **Log Analysis**: Review vote detection rates in subsequent experiments
- **Agent Feedback**: Monitor agent statements for vote-related frustration
- **Consensus Rates**: Track improvement in Phase 2 consensus achievement

### Future Improvements
- **Machine Learning**: Train models on agent voting patterns
- **Natural Language Understanding**: Implement more sophisticated semantic analysis  
- **User Interface**: Add debugging tools for real-time vote detection monitoring

## Contact & Escalation

**Implementation Lead**: Claude Code  
**Review Required**: Before modifying core voting logic  
**Testing Required**: Before deployment to production experiments

This plan provides a structured approach to fixing the critical voting mechanism failure while maintaining system stability and enabling future improvements.