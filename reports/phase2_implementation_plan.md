# Phase 2 Implementation Plan: Critical Fixes Based on Review

**Date**: 2025-08-20  
**Based on**: Lucas's review of phase2_prompt_design_review.md  

## Executive Summary

This plan addresses the critical issues identified in Phase 2, focusing on Lucas's approved suggestions and removing the items he rejected. The core theme is **using utility agents for complex decision-making** while ensuring **clean multilingual integration**.

## Priority 1: Utility Agent Integration for Decision Making

### 1. Vote Detection via Utility Agent
**Lucas's Suggestion**: "Lets use an utility agent to determine whether the participant agent wants to trigger a vote --> if we do that we have to integrate it cleanly with our multiple languages"

#### Current Problem:
```python
# Overly permissive pattern matching in prompts
vote_proposal = await self.utility_agent.extract_vote_from_statement(statement)
```

#### Proposed Solution:
```python
async def determine_vote_intention(self, statement: str, language: str) -> VoteIntention:
    """Use utility agent to determine if participant wants to vote."""
    
    # Language-aware vote detection prompt
    detection_prompt = self.language_manager.get("utility.vote_intention_analysis", 
                                                language=language,
                                                statement=statement)
    
    result = await Runner.run(self.utility_agent, detection_prompt)
    
    return VoteIntention(
        wants_to_vote=result.wants_to_vote,
        confidence=result.confidence,
        proposed_principle=result.proposed_principle,
        reasoning=result.reasoning
    )
```

### 2. Agreement Detection via Utility Agent
**Lucas's Suggestion**: Same approach for unanimous agreement detection

#### Current Problem:
```python
agreements = [("YES" in response.final_output.upper()) for response in responses]
```

#### Proposed Solution:
```python
async def analyze_agreement_response(self, response: str, language: str) -> AgreementAnalysis:
    """Use utility agent to analyze agreement to vote."""
    
    analysis_prompt = self.language_manager.get("utility.agreement_analysis",
                                               language=language,
                                               response=response)
    
    result = await Runner.run(self.utility_agent, analysis_prompt)
    
    return AgreementAnalysis(
        agrees_to_vote=result.agrees_to_vote,
        has_reservations=result.has_reservations,
        wants_more_discussion=result.wants_more_discussion,
        confidence=result.confidence
    )
```

### 3. Consensus Detection via Utility Agent  
**Lucas's Suggestion**: "Lets use an utility agent to determine whether agreement has been reached and which it is --> if we do that we have to integrate it cleanly with our multiple languages"

#### Current Problem:
```python
# Brittle exact matching and questionable semantic tolerance
if exact_consensus_failed():
    tolerance = max(1000, int(avg_amount * 0.1))  # Lucas: "unacceptable"
```

#### Proposed Solution:
```python
async def analyze_group_consensus(self, votes: List[PrincipleChoice], language: str) -> ConsensusAnalysis:
    """Use utility agent to determine if consensus exists."""
    
    consensus_prompt = self.language_manager.get("utility.consensus_analysis",
                                                language=language,
                                                votes=self._format_votes_for_analysis(votes))
    
    result = await Runner.run(self.utility_agent, consensus_prompt)
    
    return ConsensusAnalysis(
        has_consensus=result.has_consensus,
        agreed_principle=result.agreed_principle if result.has_consensus else None,
        constraint_amount=result.constraint_amount if result.has_consensus else None,
        analysis_reasoning=result.reasoning
    )
```

## Priority 2: Configuration Flexibility

### 4. Optional Randomized Speaking Order
**Lucas's Suggestion**: "Lets make randomized speaking order an optional parameter"

#### Implementation:
```python
class ExperimentConfiguration:
    # Add new field
    randomize_speaking_order: bool = True  # Default maintains current behavior
    speaking_order_strategy: str = "random"  # "random", "fixed", "conversational"

def _generate_speaking_order(self, round_num: int, contexts, last_round_starter=None):
    """Generate speaking order based on configuration."""
    
    if not self.config.randomize_speaking_order:
        # Fixed order: same sequence every round
        return list(range(len(contexts)))
    
    # Default: current random behavior
    participant_indices = list(range(len(contexts)))
    random.shuffle(participant_indices)
    
    if last_round_starter is not None and participant_indices[0] == last_round_starter:
        if len(participant_indices) > 1:
            participant_indices[0], participant_indices[1] = participant_indices[1], participant_indices[0]
    
    return participant_indices
```

## Priority 3: Remove Failed Semantic Consensus Logic

### 5. Remove Semantic Consensus Tolerance
**Lucas's Comments**: 
- "Tolerance calculation unacceptable and should be removed"

**Note**: Constraint validation already exists and works correctly in `utility_agent.py:validate_constraint_specification()` - it checks for `constraint_amount is not None and constraint_amount > 0` for constraint principles.

#### Implementation:
```python
# Remove the entire _check_semantic_consensus method and its tolerance logic
# Replace semantic consensus entirely with utility agent consensus detection

def _check_consensus(self, votes: List[PrincipleChoice]) -> PrincipleChoice:
    """Only check exact consensus - no tolerance."""
    if not votes:
        return None
    
    first_vote = votes[0]
    for vote in votes[1:]:
        if (vote.principle != first_vote.principle or 
            vote.constraint_amount != first_vote.constraint_amount):
            return None
    
    return first_vote
```

## Priority 4: Multilingual Integration Framework

### 6. Clean Language Integration for Utility Agents
**Recurring Theme**: "integrate it cleanly with our multiple languages"

#### New Translation Structure:
```json
{
  "utility": {
    "vote_intention_analysis": "Analyze if this statement indicates the participant wants to vote: '{statement}'\n\nConsider cultural context...",
    "agreement_analysis": "Analyze if this response indicates agreement to vote: '{response}'\n\nConsider linguistic patterns...",
    "consensus_analysis": "Analyze these votes for consensus:\n{votes}\n\nDetermine if there is exact agreement..."
  }
}
```

## Implementation Timeline

### Phase 1 (Week 1): Core Utility Agent Integration
- [ ] Implement vote intention detection via utility agent
- [ ] Implement agreement analysis via utility agent  
- [ ] Add multilingual prompt templates for utility operations
- [ ] Remove semantic consensus tolerance logic

### Phase 2 (Week 2): Configuration and Validation
- [ ] Add speaking order configuration options
- [ ] Implement utility agent consensus detection
- [ ] Add proper constraint validation bounds
- [ ] Remove old pattern-matching systems

### Phase 3 (Week 3): Testing and Integration
- [ ] Test multilingual utility agent performance
- [ ] Validate constraint bounds with realistic scenarios
- [ ] Test speaking order options
- [ ] Integration testing and optimization

## Key Design Principles

1. **Utility Agent Consistency**: All complex decisions use utility agents
2. **Clean Multilingual Integration**: Single templates with language context
3. **Configuration Flexibility**: Make behaviors configurable
4. **Realistic Constraints**: Validation reflects experimental scenarios
5. **Remove Failed Approaches**: Eliminate semantic tolerance entirely

## Expected Outcomes

1. More reliable vote detection through utility agent analysis
2. Better multilingual consistency across all languages
3. Configurable speaking order for different experimental needs
4. Realistic constraint validation within reasonable bounds
5. Cleaner architecture with consistent utility agent approach