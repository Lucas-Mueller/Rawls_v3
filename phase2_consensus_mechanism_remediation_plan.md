# Phase 2 Consensus Mechanism Remediation Plan

## Executive Summary

This document provides a comprehensive remediation plan to address the critical failures identified in the Phase 2 consensus mechanism (Steps 3-6). The plan is structured in three phases with specific priorities, implementation steps, testing strategies, and success criteria.

**Status**: Phase 2 consensus mechanism is currently non-functional and should not be used for experiments until critical fixes are implemented.

**Estimated Timeline**: 2-3 weeks for critical fixes, 4-6 weeks for complete remediation

## Phase 1: Critical System Stabilization (Week 1-2)

### Priority: CRITICAL - System Breaking Issues

#### 1.1 Fix Prompt Response Format Mismatches

**Issue**: System asks participants "YES"/"NO" but expects "AGREES"/"DISAGREES"

**Files to Modify**:
- `translations/english_prompts.json`
- `translations/spanish_prompts.json` 
- `translations/mandarin_prompts.json`

**Implementation Steps**:
1. **Update Agreement Detection Prompt** (`prompts.utility_agreement_detection_enhanced`):
   ```json
   "utility_agreement_detection_enhanced": "Analyze this response to determine if the participant clearly agrees to conduct a vote NOW.\n\nResponse: \"{response}\"\n\nLook for clear agreement indicators:\n✅ \"Yes\" / \"YES\" / \"Si\" / \"Oui\" / \"是的\"\n✅ \"I agree\" / \"Agreed\" / \"Let's vote\"\n✅ \"Ready to vote\" / \"I'm ready\"\n✅ \"Let's proceed\" / \"Let's do it\"\n\nIgnore responses with hesitation or conditions:\n❌ \"Yes, but...\" / \"I agree, however...\"\n❌ \"Maybe\" / \"Perhaps\" / \"Not sure\"\n❌ \"Need more discussion\" / \"Not ready\"\n\nRespond EXACTLY:\n- \"AGREES\" if clear immediate willingness\n- \"DISAGREES\" if any hesitation or conditions"
   ```

2. **Update Vote Agreement Prompt** (`prompts.phase2_vote_agreement`):
   ```json
   "phase2_vote_agreement": "A vote has been proposed. Do you agree to conduct a vote now?\n\nIf you are ready to vote immediately, respond: \"Yes\"\nIf you need more discussion, respond: \"No\"\n\nWhat is your response?"
   ```

3. **Add Input Validation** in `UtilityAgent.detect_agreement_multilingual()`:
   ```python
   async def detect_agreement_multilingual(self, response: str) -> bool:
       # Normalize response for robust matching
       normalized = response.strip().upper()
       
       # Direct agreement patterns (more robust than exact matching)
       agreement_patterns = [
           "YES", "SI", "SÍ", "OUI", "是的", "AGREES", 
           "I AGREE", "AGREED", "LET'S VOTE", "READY TO VOTE",
           "LET'S PROCEED", "LET'S DO IT"
       ]
       
       # Check for direct matches or contains patterns
       for pattern in agreement_patterns:
           if pattern in normalized:
               # Additional check: ensure no negation words
               negation_words = ["BUT", "HOWEVER", "NOT", "NO"]
               if not any(neg in normalized for neg in negation_words):
                   return True
       
       # Fallback to LLM analysis for complex cases
       detection_prompt = language_manager.get(
           "prompts.utility_agreement_detection_enhanced",
           response=response
       )
       result = await Runner.run(self.parser_agent, detection_prompt)
       return result.final_output.strip().upper() == "AGREES"
   ```

**Success Criteria**:
- All prompt formats aligned with expected responses
- 95%+ accuracy in agreement detection tests
- No format mismatch errors in logs

#### 1.2 Replace Brittle String Matching for Vote Detection

**Issue**: Exact string matching for "VOTE_DETECTED" fails with LLM output variations

**Files to Modify**:
- `experiment_agents/utility_agent.py:337-353`

**Implementation Steps**:
1. **Replace Exact String Matching**:
   ```python
   async def detect_vote_intention_enhanced(self, statement: str) -> Optional[str]:
       """Enhanced vote detection with robust pattern matching."""
       await self.async_init()
       
       # First: Direct pattern matching for common vote phrases
       vote_indicators = [
           r"i propose we vote",
           r"let'?s vote",
           r"call for a vote",
           r"time to vote",
           r"ready to vote",
           r"we should vote",
           r"proceed with.*vote",
           r"move to.*vot",
           r"conduct.*vote"
       ]
       
       statement_lower = statement.lower()
       for pattern in vote_indicators:
           if re.search(pattern, statement_lower):
               return statement  # Direct pattern match found
       
       # Fallback: LLM-based semantic analysis
       detection_prompt = self.language_manager.get(
           "prompts.utility_vote_detection_enhanced",
           statement=statement
       )
       
       result = await Runner.run(self.parser_agent, detection_prompt)
       response = result.final_output.strip().upper()
       
       # Robust response parsing (not exact string matching)
       if any(indicator in response for indicator in ["VOTE_DETECTED", "VOTE DETECTED", "VOTING", "YES"]):
           return statement
       
       return None
   ```

2. **Update Vote Detection Prompt** for clearer responses:
   ```json
   "utility_vote_detection_enhanced": "Analyze this statement for voting intentions.\n\nStatement: \"{statement}\"\n\nDetect if participant wants to:\n1. Propose/call for a vote\n2. Express readiness to vote\n3. Move to decision/voting phase\n\nBe generous - detect intent even with informal language.\n\nRespond with:\n- \"VOTING_INTENT_DETECTED\" if they want to vote\n- \"NO_VOTING_INTENT\" otherwise"
   ```

**Success Criteria**:
- Vote detection accuracy increases to 90%+
- No missed vote proposals in test scenarios
- Robust handling of various phrasings and languages

#### 1.3 Remove Pydantic Validation Bypass Hack

**Issue**: Temporary constraint amounts violate data integrity

**Files to Modify**:
- `experiment_agents/utility_agent.py:725-737`
- `models/principle_types.py:26-54`

**Implementation Steps**:
1. **Modify PrincipleChoice Model** to allow None constraints temporarily:
   ```python
   class PrincipleChoice(BaseModel):
       principle: JusticePrinciple
       constraint_amount: Optional[int] = Field(None, description="Required for constraint principles")
       certainty: CertaintyLevel
       reasoning: Optional[str] = Field(None, description="Participant's reasoning")
       _is_constraint_validated: bool = False  # Internal validation flag
       
       @model_validator(mode='after')
       def validate_constraint_amount(self):
           """Validate constraint amounts only when explicitly requested."""
           # Skip validation during parsing, enforce during voting
           if hasattr(self, '_skip_constraint_validation') and self._skip_constraint_validation:
               return self
               
           if self.principle in [
               JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
               JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
           ]:
               if self.constraint_amount is None:
                   raise ValueError(f"Constraint amount required for principle {self.principle}")
               if self.constraint_amount <= 0:
                   raise ValueError("Constraint amount must be positive")
               self._is_constraint_validated = True
           return self
       
       def is_valid_constraint(self) -> bool:
           """Check if constraint amount is valid for voting."""
           if self.principle in [
               JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
               JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
           ]:
               return self.constraint_amount is not None and self.constraint_amount > 0
           return True  # Non-constraint principles are always valid
       
       def validate_for_voting(self) -> 'PrincipleChoice':
           """Validate constraint amounts for voting - returns validated copy."""
           if not self.is_valid_constraint():
               raise ValueError(f"Invalid constraint for voting: {self.constraint_amount}")
           # Create validated copy
           validated = self.model_copy()
           validated._is_constraint_validated = True
           return validated
   ```

2. **Remove Validation Bypass** in UtilityAgent:
   ```python
   def _create_principle_choice(self, data: Dict[str, Any]) -> PrincipleChoice:
       """Create PrincipleChoice object with proper validation."""
       principle = JusticePrinciple(data['principle'])
       constraint_amount = data.get('constraint_amount')
       
       # Allow creation without constraint for parsing, but mark as unvalidated
       choice = PrincipleChoice(
           principle=principle,
           constraint_amount=constraint_amount,
           certainty=CertaintyLevel(data['certainty']),
           reasoning=data.get('reasoning', '')
       )
       choice._skip_constraint_validation = True  # Skip during parsing
       return choice
   ```

3. **Update Voting Validation** in Phase2Manager:
   ```python
   async def _conduct_group_vote(self, contexts, config) -> VoteResult:
       """Conduct voting with proper validation."""
       # ... existing code ...
       
       # Validate and prepare votes
       validated_votes = []
       for i, vote in enumerate(votes):
           participant_name = self.participants[i].name
           
           try:
               # Attempt to validate for voting
               validated_vote = vote.validate_for_voting()
               validated_votes.append(validated_vote)
               self._log_info(f"Valid vote from {participant_name}: {validated_vote.principle.value}")
               
           except ValueError as e:
               # Re-prompt for missing constraint
               self._log_info(f"Invalid vote from {participant_name}: {str(e)}")
               corrected_vote = await self._re_prompt_for_valid_vote(
                   self.participants[i], contexts[i], vote, config.agents[i]
               )
               
               # Validate corrected vote before adding
               try:
                   validated_corrected = corrected_vote.validate_for_voting()
                   validated_votes.append(validated_corrected)
               except ValueError as e2:
                   # Final fallback - use default constraint
                   self._log_warning(f"Repeated validation failure for {participant_name}, using default")
                   default_constraint = 10000 if 'floor' in vote.principle.value else 20000
                   fallback_vote = PrincipleChoice(
                       principle=vote.principle,
                       constraint_amount=default_constraint,
                       certainty=CertaintyLevel.UNSURE,
                       reasoning=f"Default constraint applied due to validation failure: {str(e2)}"
                   )
                   validated_votes.append(fallback_vote.validate_for_voting())
       
       # Proceed with consensus check using validated votes
       consensus_principle = self._check_exact_consensus(validated_votes)
       # ... rest of method
   ```

**Success Criteria**:
- No validation bypass hacks in codebase
- All votes entering consensus are properly validated
- Clear error handling for invalid votes
- Type safety maintained throughout

#### 1.4 Add Re-validation of Corrected Votes

**Issue**: Re-prompted votes are added without validation

**Files to Modify**:
- `core/phase2_manager.py:635-649`

**Implementation Steps**:
1. **Add Validation Loop** (already included in 1.3 above)
2. **Add Recursion Limits**:
   ```python
   async def _re_prompt_for_valid_vote(
       self,
       participant: ParticipantAgent,
       context: ParticipantContext,
       invalid_vote: PrincipleChoice,
       agent_config: AgentConfiguration,
       max_retries: int = 3,
       current_retry: int = 0
   ) -> PrincipleChoice:
       """Re-prompt with recursion limits."""
       
       if current_retry >= max_retries:
           self._log_warning(f"Maximum retries ({max_retries}) exceeded for {participant.name}")
           # Return vote with default constraint
           default_constraint = 10000 if 'floor' in invalid_vote.principle.value else 20000
           return PrincipleChoice(
               principle=invalid_vote.principle,
               constraint_amount=default_constraint,
               certainty=CertaintyLevel.UNSURE,
               reasoning=f"Default constraint applied after {max_retries} failed attempts"
           )
       
       retry_prompt = await self.utility_agent.re_prompt_for_constraint(
           participant.name, invalid_vote
       )
       
       result = await Runner.run(participant.agent, retry_prompt, context=context)
       retry_text = result.final_output
       
       # Parse and validate immediately
       parsed_vote = await self.utility_agent.parse_principle_choice_enhanced(retry_text)
       
       if parsed_vote.is_valid_constraint():
           return parsed_vote
       else:
           # Recursive retry with incremented counter
           self._log_info(f"Retry {current_retry + 1} failed for {participant.name}, retrying...")
           return await self._re_prompt_for_valid_vote(
               participant, context, parsed_vote, agent_config, 
               max_retries, current_retry + 1
           )
   ```

**Success Criteria**:
- All corrected votes are re-validated before acceptance
- Recursion limits prevent infinite loops
- Graceful degradation to default constraints when retries exhausted

## Phase 2: Enhanced Reliability and Validation (Week 3-4)

### Priority: HIGH - Functionality Breaking Issues

#### 2.1 Implement Unified Validation Framework

**Goal**: Create single validation system used consistently across all components

**Files to Create**:
- `utils/validation_framework.py`

**Implementation Steps**:
1. **Create Validation Framework**:
   ```python
   from typing import List, Dict, Any, Optional, Tuple
   from enum import Enum
   from dataclasses import dataclass
   
   class ValidationSeverity(str, Enum):
       ERROR = "error"
       WARNING = "warning"
       INFO = "info"
   
   @dataclass
   class ValidationResult:
       is_valid: bool
       severity: ValidationSeverity
       message: str
       context: Optional[Dict[str, Any]] = None
       suggested_fix: Optional[str] = None
   
   class ValidationFramework:
       """Unified validation system for consensus mechanism."""
       
       @staticmethod
       def validate_vote_proposal_text(statement: str) -> ValidationResult:
           """Validate vote proposal statement."""
           if not statement or len(statement.strip()) < 10:
               return ValidationResult(
                   is_valid=False,
                   severity=ValidationSeverity.ERROR,
                   message="Vote proposal statement too short or empty",
                   suggested_fix="Provide meaningful vote proposal statement"
               )
           
           # Check for vote indicators
           vote_patterns = [
               r"vote", r"ballot", r"decide", r"choose", r"consensus", r"finalize"
           ]
           
           if not any(re.search(pattern, statement.lower()) for pattern in vote_patterns):
               return ValidationResult(
                   is_valid=False,
                   severity=ValidationSeverity.WARNING,
                   message="Statement may not contain clear vote intention",
                   context={"statement_preview": statement[:100]}
               )
           
           return ValidationResult(is_valid=True, severity=ValidationSeverity.INFO, message="Valid vote proposal")
       
       @staticmethod
       def validate_principle_choice(choice: PrincipleChoice, for_voting: bool = False) -> ValidationResult:
           """Validate principle choice with context-aware rules."""
           
           # Basic validation
           if not choice.principle:
               return ValidationResult(
                   is_valid=False, severity=ValidationSeverity.ERROR,
                   message="Missing principle selection"
               )
           
           # Constraint validation for voting
           if for_voting and choice.principle in [
               JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
               JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
           ]:
               if choice.constraint_amount is None:
                   return ValidationResult(
                       is_valid=False, severity=ValidationSeverity.ERROR,
                       message=f"Constraint amount required for {choice.principle.value}",
                       suggested_fix="Specify constraint amount in dollars (e.g., $15,000)"
                   )
               
               if choice.constraint_amount <= 0:
                   return ValidationResult(
                       is_valid=False, severity=ValidationSeverity.ERROR,
                       message=f"Constraint amount must be positive: {choice.constraint_amount}",
                       suggested_fix="Use positive dollar amount (e.g., $10,000)"
                   )
               
               # Range validation
               if choice.constraint_amount < 1000 or choice.constraint_amount > 100000:
                   return ValidationResult(
                       is_valid=False, severity=ValidationSeverity.WARNING,
                       message=f"Constraint amount may be unrealistic: ${choice.constraint_amount}",
                       context={"suggested_range": "1,000 - 100,000"}
                   )
           
           return ValidationResult(is_valid=True, severity=ValidationSeverity.INFO, message="Valid principle choice")
       
       @staticmethod
       def validate_consensus_votes(votes: List[PrincipleChoice]) -> Tuple[ValidationResult, Optional[PrincipleChoice]]:
           """Validate votes for consensus determination."""
           
           if not votes:
               return ValidationResult(
                   is_valid=False, severity=ValidationSeverity.ERROR,
                   message="No votes provided for consensus"
               ), None
           
           # Validate each vote for voting
           invalid_votes = []
           for i, vote in enumerate(votes):
               result = ValidationFramework.validate_principle_choice(vote, for_voting=True)
               if not result.is_valid:
                   invalid_votes.append((i, result.message))
           
           if invalid_votes:
               return ValidationResult(
                   is_valid=False, severity=ValidationSeverity.ERROR,
                   message=f"Invalid votes detected: {len(invalid_votes)}",
                   context={"invalid_votes": invalid_votes}
               ), None
           
           # Check consensus
           first_vote = votes[0]
           consensus_achieved = True
           mismatched_votes = []
           
           for i, vote in enumerate(votes[1:], 1):
               if (vote.principle != first_vote.principle or 
                   vote.constraint_amount != first_vote.constraint_amount):
                   consensus_achieved = False
                   mismatched_votes.append({
                       "vote_index": i,
                       "principle": vote.principle.value,
                       "constraint": vote.constraint_amount
                   })
           
           if consensus_achieved:
               return ValidationResult(
                   is_valid=True, severity=ValidationSeverity.INFO,
                   message="Consensus achieved"
               ), first_vote
           else:
               return ValidationResult(
                   is_valid=False, severity=ValidationSeverity.INFO,
                   message="No consensus - votes differ",
                   context={
                       "reference_vote": {
                           "principle": first_vote.principle.value,
                           "constraint": first_vote.constraint_amount
                       },
                       "mismatched_votes": mismatched_votes
                   }
               ), None
   ```

2. **Integrate Framework** into existing components:
   ```python
   # In Phase2Manager._conduct_group_vote()
   from utils.validation_framework import ValidationFramework
   
   # Validate votes using framework
   validation_result, consensus_choice = ValidationFramework.validate_consensus_votes(votes)
   
   self._log_info(f"Vote validation: {validation_result.message}")
   if validation_result.context:
       self._log_info(f"Validation context: {validation_result.context}")
   
   return VoteResult(
       votes=votes,
       consensus_reached=validation_result.is_valid and consensus_choice is not None,
       agreed_principle=consensus_choice,
       vote_counts=self._count_votes(votes)
   )
   ```

**Success Criteria**:
- Single validation system used across all components
- Consistent validation logic and error messages
- Clear validation context and suggested fixes

#### 2.2 Implement Semantic Response Analysis

**Goal**: Replace string matching with semantic understanding

**Files to Modify**:
- `experiment_agents/utility_agent.py`

**Implementation Steps**:
1. **Add Semantic Analysis Methods**:
   ```python
   async def analyze_response_semantically(
       self, 
       response: str, 
       expected_intent: str,
       confidence_threshold: float = 0.8
   ) -> Tuple[bool, float, str]:
       """
       Analyze response semantically instead of string matching.
       
       Returns: (matches_intent, confidence_score, explanation)
       """
       await self.async_init()
       
       analysis_prompt = f"""
       Analyze this response for semantic meaning:
       
       Response: "{response}"
       Expected Intent: {expected_intent}
       
       Does the response clearly express the expected intent?
       
       Provide analysis in this exact format:
       INTENT_MATCH: [YES/NO]
       CONFIDENCE: [0.0-1.0]
       EXPLANATION: [brief explanation of your analysis]
       
       Consider:
       - Semantic meaning, not exact words
       - Context and implied meaning
       - Language variations and informal expressions
       - Cultural communication patterns
       """
       
       result = await Runner.run(self.parser_agent, analysis_prompt)
       output = result.final_output
       
       # Parse structured response
       import re
       intent_match = re.search(r'INTENT_MATCH:\s*(YES|NO)', output, re.IGNORECASE)
       confidence_match = re.search(r'CONFIDENCE:\s*([\d.]+)', output)
       explanation_match = re.search(r'EXPLANATION:\s*(.+)', output, re.DOTALL)
       
       matches = intent_match and intent_match.group(1).upper() == "YES"
       confidence = float(confidence_match.group(1)) if confidence_match else 0.5
       explanation = explanation_match.group(1).strip() if explanation_match else "No explanation provided"
       
       return matches, confidence, explanation
   
   async def detect_vote_intention_semantic(self, statement: str) -> Tuple[Optional[str], float]:
       """Semantic vote intention detection with confidence scoring."""
       matches, confidence, explanation = await self.analyze_response_semantically(
           statement, 
           "expressing intention to initiate voting or move to voting phase"
       )
       
       self._log_info(f"Vote detection - Matches: {matches}, Confidence: {confidence:.2f}, Reason: {explanation}")
       
       if matches and confidence >= 0.7:
           return statement, confidence
       return None, confidence
   
   async def detect_agreement_semantic(self, response: str) -> Tuple[bool, float]:
       """Semantic agreement detection with confidence scoring."""
       matches, confidence, explanation = await self.analyze_response_semantically(
           response,
           "agreeing to conduct a vote immediately without conditions or hesitation"
       )
       
       self._log_info(f"Agreement detection - Matches: {matches}, Confidence: {confidence:.2f}, Reason: {explanation}")
       
       return matches and confidence >= 0.8, confidence
   ```

2. **Update Detection Methods** to use semantic analysis:
   ```python
   async def detect_vote_intention_enhanced(self, statement: str) -> Optional[str]:
       """Enhanced detection using semantic analysis as primary method."""
       
       # Primary: Semantic analysis
       vote_text, confidence = await self.detect_vote_intention_semantic(statement)
       if vote_text and confidence >= 0.7:
           return vote_text
       
       # Fallback: Pattern matching for high-confidence cases
       vote_indicators = [
           r"i propose we vote",
           r"let'?s vote",
           r"call for a vote",
           r"time to vote",
           r"ready to vote"
       ]
       
       statement_lower = statement.lower()
       for pattern in vote_indicators:
           if re.search(pattern, statement_lower):
               self._log_info(f"Vote detected via pattern matching: {pattern}")
               return statement
       
       return None
   ```

**Success Criteria**:
- Semantic analysis replaces brittle string matching
- Confidence scoring provides reliability metrics
- Fallback pattern matching for edge cases
- 95%+ accuracy in intent detection tests

#### 2.3 Standardize Constraint Amount Handling

**Goal**: Consistent constraint handling across all validation layers

**Files to Modify**:
- `experiment_agents/utility_agent.py:596-708`
- `core/phase2_manager.py:768-776`

**Implementation Steps**:
1. **Create Constraint Handler Class**:
   ```python
   class ConstraintAmountHandler:
       """Standardized constraint amount parsing and validation."""
       
       CONSTRAINT_RANGES = {
           JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT: (1000, 50000),
           JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT: (5000, 100000)
       }
       
       DEFAULT_CONSTRAINTS = {
           JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT: 10000,
           JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT: 20000
       }
       
       @classmethod
       def parse_constraint_amount(cls, text: str, principle: JusticePrinciple) -> Optional[int]:
           """Parse constraint amount from text with standardized logic."""
           
           # Direct numeric parsing
           import re
           
           # Pattern 1: Dollar amounts ($15,000 or $15000)
           dollar_pattern = r'\$\s*(\d{1,3}(?:,\d{3})*|\d+)'
           dollar_matches = re.findall(dollar_pattern, text)
           
           for match in dollar_matches:
               amount = int(match.replace(',', ''))
               if cls._is_valid_constraint_range(amount, principle):
                   return amount
           
           # Pattern 2: K format (15k, 20K)
           k_pattern = r'(\d+)\s*k'
           k_matches = re.findall(k_pattern, text, re.IGNORECASE)
           
           for match in k_matches:
               amount = int(match) * 1000
               if cls._is_valid_constraint_range(amount, principle):
                   return amount
           
           # Pattern 3: Contextual amounts (near constraint keywords)
           context_pattern = r'(?:constraint|floor|range|limit)[\s\w]*?(\d{1,3}(?:,\d{3})*|\d+)'
           context_matches = re.findall(context_pattern, text, re.IGNORECASE)
           
           for match in context_matches:
               amount = int(match.replace(',', ''))
               if cls._is_valid_constraint_range(amount, principle):
                   return amount
           
           # Pattern 4: Abstract descriptions
           return cls._parse_abstract_constraint(text, principle)
       
       @classmethod
       def _is_valid_constraint_range(cls, amount: int, principle: JusticePrinciple) -> bool:
           """Check if amount is in valid range for principle."""
           if principle not in cls.CONSTRAINT_RANGES:
               return True  # Non-constraint principles
           
           min_val, max_val = cls.CONSTRAINT_RANGES[principle]
           return min_val <= amount <= max_val
       
       @classmethod
       def _parse_abstract_constraint(cls, text: str, principle: JusticePrinciple) -> Optional[int]:
           """Parse abstract constraint descriptions."""
           text_lower = text.lower()
           
           # Reject negative indicators
           if any(neg in text_lower for neg in ['negative', 'minus', '-']):
               return None
           
           # Map abstract terms to amounts
           if any(term in text_lower for term in ['high', 'maximum', 'strong']):
               return cls._get_high_constraint(principle)
           elif any(term in text_lower for term in ['low', 'minimum', 'basic']):
               return cls._get_low_constraint(principle)
           elif any(term in text_lower for term in ['moderate', 'reasonable', 'balanced']):
               return cls.DEFAULT_CONSTRAINTS.get(principle)
           
           return None
       
       @classmethod
       def _get_high_constraint(cls, principle: JusticePrinciple) -> int:
           """Get high constraint amount for principle."""
           if principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT:
               return 25000
           elif principle == JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT:
               return 50000
           return 0
       
       @classmethod
       def _get_low_constraint(cls, principle: JusticePrinciple) -> int:
           """Get low constraint amount for principle."""
           if principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT:
               return 5000
           elif principle == JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT:
               return 10000
           return 0
       
       @classmethod
       def get_default_constraint(cls, principle: JusticePrinciple) -> int:
           """Get default constraint for principle."""
           return cls.DEFAULT_CONSTRAINTS.get(principle, 0)
       
       @classmethod
       def format_constraint_for_display(cls, amount: Optional[int]) -> str:
           """Format constraint amount for display."""
           if amount is None:
               return "Not specified"
           return f"${amount:,}"
   ```

2. **Replace All Constraint Parsing** with standardized handler

**Success Criteria**:
- Single constraint parsing logic used everywhere
- Consistent validation ranges
- Standardized default values
- Clear formatting for display

## Phase 3: Performance and Maintainability (Week 5-6)

### Priority: MEDIUM - Performance and Code Quality

#### 3.1 Eliminate Duplicate Async Tasks

**Issue**: Wasteful double task creation in unanimous agreement

**Files to Modify**:
- `core/phase2_manager.py:553-592`

**Implementation**:
```python
async def _check_unanimous_vote_agreement(
    self,
    discussion_state: GroupDiscussionState,
    contexts: List[ParticipantContext],
    config: ExperimentConfiguration
) -> bool:
    """Streamlined unanimous agreement check."""
    
    language_manager = get_language_manager()
    vote_agreement_prompt = language_manager.get("prompts.phase2_vote_agreement")
    
    # Single task creation with immediate semantic analysis
    agreement_tasks = []
    for i, participant in enumerate(self.participants):
        context = contexts[i]
        
        async def check_single_agreement(p, ctx):
            # Get participant response
            response = await Runner.run(p.agent, vote_agreement_prompt, context=ctx)
            # Immediately analyze semantically
            agrees, confidence = await self.utility_agent.detect_agreement_semantic(
                response.final_output
            )
            return agrees, confidence, p.name
        
        task = asyncio.create_task(check_single_agreement(participant, context))
        agreement_tasks.append(task)
    
    # Gather all results
    results = await asyncio.gather(*agreement_tasks)
    
    # Log and evaluate
    self._log_info("=== UNANIMOUS AGREEMENT ANALYSIS ===")
    all_agree = True
    
    for agrees, confidence, participant_name in results:
        self._log_info(f"{participant_name}: Agrees={agrees}, Confidence={confidence:.2f}")
        if not agrees:
            all_agree = False
    
    self._log_info(f"Unanimous result: {all_agree}")
    return all_agree
```

#### 3.2 Unify Vote Counting Logic

**Issue**: Inconsistent logic between vote counting and consensus determination

**Files to Modify**:
- `core/phase2_manager.py:768-776`

**Implementation**:
```python
def _analyze_vote_distribution(self, votes: List[PrincipleChoice]) -> Dict[str, Any]:
    """Unified vote analysis for both counting and consensus."""
    
    vote_groups = {}
    vote_details = []
    
    for i, vote in enumerate(votes):
        # Create standardized vote key
        vote_key = f"{vote.principle.value}"
        if vote.constraint_amount is not None:
            vote_key += f"_${vote.constraint_amount}"
        
        # Group votes
        if vote_key not in vote_groups:
            vote_groups[vote_key] = {
                'principle': vote.principle,
                'constraint_amount': vote.constraint_amount,
                'votes': [],
                'count': 0
            }
        
        vote_groups[vote_key]['votes'].append(i)
        vote_groups[vote_key]['count'] += 1
        
        vote_details.append({
            'index': i,
            'principle': vote.principle.value,
            'constraint_amount': vote.constraint_amount,
            'vote_key': vote_key
        })
    
    return {
        'vote_groups': vote_groups,
        'vote_details': vote_details,
        'total_votes': len(votes),
        'unique_positions': len(vote_groups)
    }

def _check_exact_consensus(self, votes: List[PrincipleChoice]) -> Optional[PrincipleChoice]:
    """Consensus check using unified vote analysis."""
    
    if not votes:
        return None
    
    analysis = self._analyze_vote_distribution(votes)
    
    self._log_info("=== UNIFIED VOTE ANALYSIS ===")
    self._log_info(f"Total votes: {analysis['total_votes']}")
    self._log_info(f"Unique positions: {analysis['unique_positions']}")
    
    # Log each position
    for vote_key, group in analysis['vote_groups'].items():
        self._log_info(f"Position '{vote_key}': {group['count']} votes")
    
    # Consensus requires exactly one position with all votes
    if analysis['unique_positions'] == 1:
        consensus_group = list(analysis['vote_groups'].values())[0]
        consensus_vote = votes[consensus_group['votes'][0]]
        self._log_info(f"CONSENSUS ACHIEVED: {consensus_vote.principle.value}")
        return consensus_vote
    else:
        self._log_info("NO CONSENSUS: Multiple positions detected")
        return None

def _count_votes(self, votes: List[PrincipleChoice]) -> Dict[str, int]:
    """Vote counting using unified analysis."""
    analysis = self._analyze_vote_distribution(votes)
    return {key: group['count'] for key, group in analysis['vote_groups'].items()}
```

#### 3.3 Add Comprehensive Error Handling

**Files to Modify**:
- `core/phase2_manager.py` (various methods)
- `experiment_agents/utility_agent.py` (various methods)

**Implementation Strategy**:
1. Add try-catch blocks around all async operations
2. Implement proper error recovery instead of fallback hacks
3. Add circuit breakers for repeated failures
4. Log detailed error context for debugging

## Testing Strategy

### Unit Tests

**Files to Create**:
- `tests/unit/test_vote_detection_fixes.py`
- `tests/unit/test_agreement_validation_fixes.py`
- `tests/unit/test_constraint_handling_fixes.py`
- `tests/unit/test_consensus_determination_fixes.py`

**Test Coverage**:
```python
# Example test structure
class TestVoteDetectionFixes:
    def test_semantic_vote_detection_various_phrasings(self):
        """Test vote detection with various phrasings."""
        test_cases = [
            ("I propose we vote on principle A", True),
            ("Let's vote now", True),
            ("Time to finalize this with a vote", True),
            ("I think we need more discussion", False),
            ("What do you think about voting?", False),
            ("VOTE: I formally propose principle C", True)
        ]
        
        for statement, expected in test_cases:
            result = detect_vote_intention_enhanced(statement)
            assert bool(result) == expected, f"Failed for: {statement}"
    
    def test_multilingual_vote_detection(self):
        """Test vote detection across languages."""
        test_cases = [
            ("Propongo que votemos por el principio A", True),
            ("我提议我们投票选择原则B", True),
            ("Je propose que nous votions", True)
        ]
        
        for statement, expected in test_cases:
            result = detect_vote_intention_enhanced(statement)
            assert bool(result) == expected

class TestAgreementValidationFixes:
    def test_agreement_detection_format_alignment(self):
        """Test that agreement detection matches prompt format."""
        test_cases = [
            ("Yes", True),
            ("NO", False),
            ("I agree", True),
            ("Yes, but I have concerns", False),
            ("Not ready yet", False)
        ]
        
        for response, expected in test_cases:
            result = detect_agreement_multilingual(response)
            assert result == expected

class TestConstraintHandlingFixes:
    def test_constraint_parsing_consistency(self):
        """Test standardized constraint parsing."""
        test_cases = [
            ("I choose principle C with $15,000", 15000),
            ("Principle C with 20k constraint", 20000),
            ("Maximum constraint for principle D", 25000),  # Abstract
            ("Negative constraint of -$5000", None),  # Invalid
        ]
        
        for text, expected in test_cases:
            result = ConstraintAmountHandler.parse_constraint_amount(
                text, JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            )
            assert result == expected

class TestConsensusIntegration:
    def test_end_to_end_consensus_flow(self):
        """Test complete consensus flow with fixed components."""
        # This would test the entire flow from vote detection 
        # through consensus determination
        pass
```

### Integration Tests

**Files to Create**:
- `tests/integration/test_consensus_mechanism_fixed.py`

**Test Scenarios**:
1. **Complete Consensus Flow**: Vote proposal → Unanimous agreement → Voting → Consensus
2. **Failed Consensus Scenarios**: Different vote outcomes
3. **Error Recovery**: Invalid votes, parsing failures, timeout scenarios
4. **Multilingual Scenarios**: Mixed language experiments
5. **Edge Cases**: Single participant, maximum participants, repeated voting

### Performance Tests

**Files to Create**:
- `tests/performance/test_consensus_performance.py`

**Metrics to Track**:
- Vote detection latency
- Agreement validation latency  
- Vote parsing and validation time
- Consensus determination time
- Memory usage during consensus operations
- API call efficiency (reduced duplicate calls)

## Risk Assessment and Mitigation

### High Risk Items

1. **Data Migration Risk**
   - **Risk**: Existing experiment data may be incompatible with new validation
   - **Mitigation**: Implement backward compatibility layer for existing data
   - **Timeline**: Add 2-3 days for migration utilities

2. **LLM Model Variability Risk**
   - **Risk**: Different LLM models may respond differently to semantic analysis
   - **Mitigation**: Test with multiple models (GPT-4, Claude, Llama) during development
   - **Timeline**: Add 1 week for cross-model testing

3. **Breaking Changes Risk**
   - **Risk**: Fixes may break existing working components
   - **Mitigation**: Comprehensive test suite with 95%+ coverage before deployment
   - **Timeline**: Add 1 week for thorough testing

### Medium Risk Items

1. **Performance Regression Risk**
   - **Risk**: Semantic analysis may be slower than string matching
   - **Mitigation**: Implement caching and fallback mechanisms
   - **Timeline**: Monitor performance, optimize if needed

2. **Prompt Engineering Risk**  
   - **Risk**: New prompts may not work as expected across all scenarios
   - **Mitigation**: A/B test prompts with historical data
   - **Timeline**: Add 3-4 days for prompt optimization

## Success Metrics

### Phase 1 Success Criteria
- [ ] Vote detection accuracy >90% (vs current ~30%)
- [ ] Agreement validation accuracy >95% (vs current ~0%)  
- [ ] Zero Pydantic validation bypasses in codebase
- [ ] All votes entering consensus are validated
- [ ] No infinite retry loops in testing

### Phase 2 Success Criteria
- [ ] Unified validation framework adopted across all components
- [ ] Semantic analysis replaces >80% of string matching
- [ ] Constraint handling standardized with consistent validation
- [ ] Performance maintained or improved vs current implementation

### Phase 3 Success Criteria
- [ ] Duplicate async tasks eliminated (performance gain)
- [ ] Vote counting and consensus logic unified
- [ ] Comprehensive error handling with graceful degradation
- [ ] 95%+ test coverage for consensus mechanism

### Overall Success Metrics
- [ ] End-to-end consensus success rate >85% (vs current ~5%)
- [ ] Zero false consensus detections
- [ ] Zero system crashes due to consensus mechanism
- [ ] Experiment data validity restored
- [ ] Participant experience significantly improved

## Timeline and Resource Requirements

### Week 1-2: Critical Fixes (Phase 1)
- **Developer Time**: 60-80 hours
- **Dependencies**: Access to test environments
- **Deliverables**: Working vote detection, agreement validation, constraint validation

### Week 3-4: Enhanced Reliability (Phase 2)
- **Developer Time**: 40-60 hours  
- **Dependencies**: Phase 1 completion, LLM API access for testing
- **Deliverables**: Semantic analysis, unified validation, standardized constraint handling

### Week 5-6: Performance and Quality (Phase 3)
- **Developer Time**: 30-40 hours
- **Dependencies**: Phase 2 completion
- **Deliverables**: Optimized performance, comprehensive testing, documentation

### Total Effort Estimate: 130-180 developer hours (3.25-4.5 weeks full-time)

## Deployment Strategy

### Phase 1 Deployment (Critical Fixes)
1. **Deploy to staging environment**
2. **Run comprehensive test suite** 
3. **Validate with historical failing cases**
4. **Limited production deployment** (single experiment type)
5. **Monitor for 48 hours** before full deployment

### Phase 2 Deployment (Enhanced Features)
1. **A/B test semantic analysis** vs pattern matching
2. **Gradual rollout** of unified validation framework
3. **Performance monitoring** and optimization

### Phase 3 Deployment (Optimizations)
1. **Performance baseline comparison**
2. **Full regression testing**
3. **Complete rollout** with monitoring

## Conclusion

This remediation plan addresses the systematic failures in the Phase 2 consensus mechanism through a structured approach prioritizing critical fixes first, followed by reliability improvements and performance optimizations.

The plan's success depends on:
1. **Immediate implementation** of critical fixes to restore basic functionality
2. **Comprehensive testing** to prevent regression and ensure reliability
3. **Gradual deployment** with careful monitoring at each phase

**Upon completion, the consensus mechanism will be transformed from a non-functional system into a robust, reliable component suitable for experimental research with AI agents.**

---
*Remediation Plan created by Claude Code on 2025-08-26*  
*Based on critical failure analysis of Phase 2 consensus mechanism*  
*Priority: IMMEDIATE - System currently non-functional for experimental use*