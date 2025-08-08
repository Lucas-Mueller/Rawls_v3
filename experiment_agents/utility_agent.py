"""
Utility agent for parsing and validating participant responses.
"""
import asyncio
import logging
import re
import os
from typing import Optional, Dict, Any, List
from agents import Agent, Runner, AgentOutputSchema

from models import (
    PrincipleChoice, PrincipleRanking, VoteProposal, JusticePrinciple,
    ParsedResponse, ValidationResult, CertaintyLevel, RankedPrinciple
)
from utils.error_handling import (
    ValidationError, AgentCommunicationError, ExperimentError,
    ErrorSeverity, ExperimentErrorCategory, get_global_error_handler,
    handle_experiment_errors
)
from utils.model_provider import create_model_config

logger = logging.getLogger(__name__)


class UtilityAgent:
    """Specialized agent for parsing and validating participant responses with enhanced text parsing."""
    
    def __init__(self, utility_model: str = None):
        # Use environment variable or default for utility agents
        if utility_model is None:
            utility_model = os.getenv("UTILITY_AGENT_MODEL", "gpt-4.1-mini")
        
        model_config = create_model_config(utility_model)
        
        # Both OpenAI and LiteLLM models use the same Agent pattern
        self.parser_agent = Agent(
            name="Response Parser",
            instructions=self._get_parser_instructions(),
            model=model_config
        )
        self.validator_agent = Agent(
            name="Response Validator", 
            instructions=self._get_validator_instructions(),
            model=model_config
        )
        
        # Enhanced parsing patterns
        self._principle_patterns = self._compile_principle_patterns()
        self._certainty_patterns = self._compile_certainty_patterns()
        self._ranking_patterns = self._compile_ranking_patterns()
    
    def _get_parser_instructions(self) -> str:
        """Instructions for the parser agent."""
        return """
        You are a specialized parser for the Frohlich Experiment.
        
        When analyzing text for vote proposals, respond with either:
        - "VOTE_PROPOSAL: [extracted proposal text]" if a vote is proposed
        - "NO_VOTE" if no vote is proposed
        
        Look for phrases like "I propose we vote", "Let's vote on", "Should we take a vote", etc.
        
        For other parsing tasks, extract the relevant information and respond clearly and concisely.
        """
    
    def _get_validator_instructions(self) -> str:
        """Instructions for the validator agent."""
        return """
        You are a validator agent for the Frohlich Experiment.
        
        Your task is to validate parsed responses for completeness and correctness:
        
        1. Constraint Validation: If a participant chooses a constraint principle 
           (maximizing_average_floor_constraint or maximizing_average_range_constraint),
           they MUST specify a constraint amount.
        
        2. Ranking Validation: Complete rankings must include all 4 principles with ranks 1-4.
        
        3. Data Integrity: All required fields must be present and valid.
        
        Return is_valid=True if validation passes, is_valid=False with specific errors if not.
        """
    
    @handle_experiment_errors(
        category=ExperimentErrorCategory.VALIDATION_ERROR,
        severity=ErrorSeverity.RECOVERABLE,
        operation_name="parse_principle_choice"
    )
    async def parse_principle_choice(self, response: str) -> PrincipleChoice:
        """Parse principle choice from participant response."""
        error_handler = get_global_error_handler()
        
        parse_prompt = f"""
        Parse the following participant response to extract their justice principle choice:
        
        Response: "{response}"
        
        Extract:
        - Which principle they chose
        - Constraint amount (if applicable)
        - Their certainty level
        - Their reasoning
        
        Return the parsed data as a dictionary with keys: principle, constraint_amount, certainty, reasoning
        """
        
        try:
            result = await Runner.run(self.parser_agent, parse_prompt)
            parsed_result = result.final_output
            
            if not parsed_result.success:
                raise ValidationError(
                    f"Failed to parse principle choice: {parsed_result.error_message}",
                    ErrorSeverity.RECOVERABLE,
                    {
                        "response_text": response,
                        "parse_error": parsed_result.error_message,
                        "operation": "principle_choice_parsing"
                    }
                )
            
            data = parsed_result.parsed_data
            return PrincipleChoice(
                principle=JusticePrinciple(data['principle']),
                constraint_amount=data.get('constraint_amount'),
                certainty=CertaintyLevel(data['certainty']),
                reasoning=data.get('reasoning')
            )
            
        except (ValueError, KeyError) as e:
            raise ValidationError(
                f"Invalid principle choice format: {str(e)}",
                ErrorSeverity.RECOVERABLE,
                {
                    "response_text": response,
                    "parsing_error": str(e),
                    "operation": "principle_choice_validation"
                },
                cause=e
            )
        except Exception as e:
            raise AgentCommunicationError(
                f"Agent communication failed during principle choice parsing: {str(e)}",
                ErrorSeverity.RECOVERABLE,
                {
                    "response_text": response,
                    "communication_error": str(e),
                    "operation": "principle_choice_agent_communication"
                },
                cause=e
            )
    
    @handle_experiment_errors(
        category=ExperimentErrorCategory.VALIDATION_ERROR,
        severity=ErrorSeverity.RECOVERABLE,
        operation_name="parse_principle_ranking"
    )
    async def parse_principle_ranking(self, response: str) -> PrincipleRanking:
        """Parse principle ranking from participant response."""
        parse_prompt = f"""
        Parse the following participant response to extract their complete ranking of justice principles:
        
        Response: "{response}"
        
        Extract a complete ranking of all 4 principles from best (rank 1) to worst (rank 4).
        Also extract the overall certainty level for the entire ranking.
        
        Return the parsed data as a dictionary with:
        - rankings: list of {{principle, rank}} objects (no individual certainty levels)
        - certainty: overall certainty level for the entire ranking
        """
        
        try:
            result = await Runner.run(self.parser_agent, parse_prompt)
            parsed_result = result.final_output
            
            if not parsed_result.success:
                raise ValidationError(
                    f"Failed to parse principle ranking: {parsed_result.error_message}",
                    ErrorSeverity.RECOVERABLE,
                    {
                        "response_text": response,
                        "parse_error": parsed_result.error_message,
                        "operation": "principle_ranking_parsing"
                    }
                )
            
            data = parsed_result.parsed_data
            rankings = []
            for ranking_data in data['rankings']:
                rankings.append(RankedPrinciple(
                    principle=JusticePrinciple(ranking_data['principle']),
                    rank=ranking_data['rank']
                ))
            
            # Extract overall certainty level for the entire ranking
            overall_certainty = CertaintyLevel(data.get('certainty', 'sure'))
            
            ranking = PrincipleRanking(rankings=rankings, certainty=overall_certainty)
            
            # Validate ranking completeness
            if not self._validate_ranking_completeness(ranking):
                raise ValidationError(
                    "Incomplete ranking - missing principles or invalid ranks",
                    ErrorSeverity.RECOVERABLE,
                    {
                        "response_text": response,
                        "parsed_rankings": [{"principle": r.principle.value, "rank": r.rank} for r in rankings],
                        "operation": "ranking_completeness_validation"
                    }
                )
            
            return ranking
            
        except (ValueError, KeyError) as e:
            raise ValidationError(
                f"Invalid principle ranking format: {str(e)}",
                ErrorSeverity.RECOVERABLE,
                {
                    "response_text": response,
                    "parsing_error": str(e),
                    "operation": "principle_ranking_validation"
                },
                cause=e
            )
        except Exception as e:
            raise AgentCommunicationError(
                f"Agent communication failed during principle ranking parsing: {str(e)}",
                ErrorSeverity.RECOVERABLE,
                {
                    "response_text": response,
                    "communication_error": str(e),
                    "operation": "principle_ranking_agent_communication"
                },
                cause=e
            )
    
    def _validate_ranking_completeness(self, ranking: PrincipleRanking) -> bool:
        """Validate that ranking includes all 4 principles with ranks 1-4."""
        if len(ranking.rankings) != 4:
            return False
        
        principles = {r.principle for r in ranking.rankings}
        expected_principles = set(JusticePrinciple)
        if principles != expected_principles:
            return False
        
        ranks = {r.rank for r in ranking.rankings}
        expected_ranks = {1, 2, 3, 4}
        if ranks != expected_ranks:
            return False
        
        return True
    
    @handle_experiment_errors(
        category=ExperimentErrorCategory.VALIDATION_ERROR,
        severity=ErrorSeverity.RECOVERABLE,
        operation_name="validate_constraint"
    )
    async def validate_constraint_specification(self, choice: PrincipleChoice) -> bool:
        """Validate constraint principles have required amounts."""
        try:
            constraint_principles = [
                JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
            ]
            
            if choice.principle in constraint_principles:
                is_valid = choice.constraint_amount is not None and choice.constraint_amount > 0
                if not is_valid:
                    logger.warning(
                        f"Constraint principle {choice.principle.value} missing valid constraint amount: {choice.constraint_amount}"
                    )
                return is_valid
            
            return True
            
        except Exception as e:
            raise ValidationError(
                f"Constraint validation failed: {str(e)}",
                ErrorSeverity.RECOVERABLE,
                {
                    "principle": choice.principle.value if choice.principle else "unknown",
                    "constraint_amount": choice.constraint_amount,
                    "validation_error": str(e)
                },
                cause=e
            )
    
    async def extract_vote_from_statement(self, statement: str) -> Optional[VoteProposal]:
        """Detect if participant is proposing a vote."""
        detection_prompt = f"""
        Analyze this group discussion statement to determine if the participant is proposing a vote:
        
        Statement: "{statement}"
        """
        
        result = await Runner.run(self.parser_agent, detection_prompt)
        response_text = result.final_output.strip()
        
        if response_text.startswith("VOTE_PROPOSAL:"):
            proposal_text = response_text[len("VOTE_PROPOSAL:"):].strip()
            return VoteProposal(
                proposed_by="participant",  # Will be set by caller
                proposal_text=proposal_text
            )
        
        return None
    
    async def re_prompt_for_constraint(self, participant_name: str, choice: PrincipleChoice) -> str:
        """Generate re-prompt message for missing constraint."""
        constraint_type = "floor" if choice.principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT else "range"
        
        return f"""
        {participant_name}, you chose the "{choice.principle.value}" principle, but you did not specify the {constraint_type} constraint amount.
        
        Please specify the dollar amount for your {constraint_type} constraint.
        
        For example:
        - Floor constraint: "I choose maximizing average with a floor constraint of $15,000"
        - Range constraint: "I choose maximizing average with a range constraint of $20,000"
        """
    
    def _compile_principle_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for principle detection."""
        return {
            'maximizing_floor': re.compile(
                r'(?:maximizing?.*?floor|floor.*?income|option\s*[(\[]?a[)\]]?)', 
                re.IGNORECASE
            ),
            'maximizing_average': re.compile(
                r'(?:maximizing?.*?average(?!\s+with)|average.*?income(?!\s+with)|option\s*[(\[]?b[)\]]?)', 
                re.IGNORECASE
            ),
            'maximizing_average_floor_constraint': re.compile(
                r'(?:maximizing?.*?average.*?floor|average.*?floor.*?constraint|floor.*?constraint|option\s*[(\[]?c[)\]]?)', 
                re.IGNORECASE
            ),
            'maximizing_average_range_constraint': re.compile(
                r'(?:maximizing?.*?average.*?range|average.*?range.*?constraint|range.*?constraint|option\s*[(\[]?d[)\]]?)', 
                re.IGNORECASE
            )
        }
    
    def _compile_certainty_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for certainty level detection."""
        return {
            'very_unsure': re.compile(r'very\s+unsure|extremely\s+uncertain|highly\s+uncertain', re.IGNORECASE),
            'unsure': re.compile(r'(?<!very\s)unsure|uncertain|not\s+confident', re.IGNORECASE),
            'no_opinion': re.compile(r'no\s+opinion|neutral|indifferent|no\s+preference', re.IGNORECASE),
            'sure': re.compile(r'(?<!very\s)sure|confident|certain', re.IGNORECASE),
            'very_sure': re.compile(r'very\s+sure|extremely\s+confident|highly\s+certain|completely\s+sure', re.IGNORECASE)
        }
    
    def _compile_ranking_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for ranking detection."""
        return {
            'ranking_line': re.compile(r'(\d+)\.?\s*(.*?)(?=\d+\.|$)', re.MULTILINE | re.DOTALL),
            'rank_number': re.compile(r'(?:rank|position|place)?\s*(\d+)', re.IGNORECASE),
            'constraint_amount': re.compile(r'\$?(\d{1,3}(?:,\d{3})*|\d+)(?:\s*(?:dollars?|k|thousand))?', re.IGNORECASE)
        }
    
    async def parse_principle_choice_enhanced(self, response: str, max_retries: int = 3) -> PrincipleChoice:
        """Enhanced parsing for principle choice with retry logic."""
        
        for attempt in range(max_retries):
            try:
                # First try direct pattern matching
                choice_data = self._extract_principle_choice_direct(response)
                if choice_data:
                    return self._create_principle_choice(choice_data)
                
                # Fallback to agent-based parsing
                return await self.parse_principle_choice(response)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    # Final attempt - use more permissive parsing
                    return await self._parse_with_fallback(response, 'principle_choice')
                
                # Add clarifying context for retry
                response = f"Original response: {response}\n\nPlease clearly state your principle choice."
    
    def _extract_principle_choice_direct(self, response: str) -> Optional[Dict[str, Any]]:
        """Direct pattern matching for principle choice."""
        
        # Find principle
        principle = None
        for principle_key, pattern in self._principle_patterns.items():
            if pattern.search(response):
                principle = principle_key
                break
        
        if not principle:
            return None
        
        # Find constraint amount if needed
        constraint_amount = None
        if 'constraint' in principle:
            amount_match = self._ranking_patterns['constraint_amount'].search(response)
            if amount_match:
                amount_str = amount_match.group(1).replace(',', '')
                try:
                    constraint_amount = float(amount_str)
                    # Handle k/thousand notation
                    if 'k' in response.lower() or 'thousand' in response.lower():
                        constraint_amount *= 1000
                except ValueError:
                    pass
        
        # Find certainty
        certainty = 'sure'  # default
        for certainty_key, pattern in self._certainty_patterns.items():
            if pattern.search(response):
                certainty = certainty_key
                break
        
        return {
            'principle': principle,
            'constraint_amount': constraint_amount,
            'certainty': certainty,
            'reasoning': response  # Full response as reasoning
        }
    
    def _create_principle_choice(self, data: Dict[str, Any]) -> PrincipleChoice:
        """Create PrincipleChoice object from extracted data."""
        return PrincipleChoice(
            principle=JusticePrinciple(data['principle']),
            constraint_amount=data.get('constraint_amount'),
            certainty=CertaintyLevel(data['certainty']),
            reasoning=data.get('reasoning', '')
        )
    
    async def parse_principle_ranking_enhanced(self, response: str, max_retries: int = 3) -> PrincipleRanking:
        """Enhanced parsing for principle ranking with retry logic."""
        
        for attempt in range(max_retries):
            try:
                # First try direct pattern matching
                ranking_data = self._extract_ranking_direct(response)
                if ranking_data and len(ranking_data['rankings']) == 4:
                    return self._create_principle_ranking(ranking_data)
                
                # Fallback to agent-based parsing
                return await self.parse_principle_ranking(response)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    # Final attempt - use more permissive parsing
                    return await self._parse_with_fallback(response, 'principle_ranking')
                
                # Add clarifying context for retry
                response = f"Original response: {response}\n\nPlease provide a complete ranking of all 4 principles from 1-4."
    
    def _extract_ranking_direct(self, response: str) -> Optional[Dict[str, Any]]:
        """Direct pattern matching for principle ranking."""
        
        rankings = []
        
        # Look for numbered list format
        ranking_matches = self._ranking_patterns['ranking_line'].findall(response)
        
        if len(ranking_matches) >= 4:
            for rank_num, rank_text in ranking_matches[:4]:
                principle = self._identify_principle_in_text(rank_text.strip())
                if principle:
                    rankings.append({
                        'principle': principle,
                        'rank': int(rank_num)
                    })
        
        # Find overall certainty
        certainty = 'sure'  # default
        for certainty_key, pattern in self._certainty_patterns.items():
            if pattern.search(response):
                certainty = certainty_key
                break
        
        if len(rankings) == 4:
            return {
                'rankings': rankings,
                'certainty': certainty
            }
        
        return None
    
    def _identify_principle_in_text(self, text: str) -> Optional[str]:
        """Identify which principle is mentioned in text."""
        for principle_key, pattern in self._principle_patterns.items():
            if pattern.search(text):
                return principle_key
        return None
    
    def _create_principle_ranking(self, data: Dict[str, Any]) -> PrincipleRanking:
        """Create PrincipleRanking object from extracted data."""
        rankings = []
        for ranking_data in data['rankings']:
            rankings.append(RankedPrinciple(
                principle=JusticePrinciple(ranking_data['principle']),
                rank=ranking_data['rank']
            ))
        
        return PrincipleRanking(
            rankings=rankings, 
            certainty=CertaintyLevel(data.get('certainty', 'sure'))
        )
    
    async def _parse_with_fallback(self, response: str, parse_type: str) -> Any:
        """Fallback parsing with more permissive approach."""
        
        if parse_type == 'principle_choice':
            # Create a basic choice if we can identify any principle
            for principle_key, pattern in self._principle_patterns.items():
                if pattern.search(response):
                    return PrincipleChoice(
                        principle=JusticePrinciple(principle_key),
                        constraint_amount=None,
                        certainty=CertaintyLevel.SURE,
                        reasoning=response
                    )
            
            # Ultimate fallback - default choice
            return PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE,
                constraint_amount=None,
                certainty=CertaintyLevel.UNSURE,
                reasoning=response
            )
        
        elif parse_type == 'principle_ranking':
            # Create default ranking if parsing fails
            principles = list(JusticePrinciple)
            rankings = []
            for i, principle in enumerate(principles[:4]):
                rankings.append(RankedPrinciple(
                    principle=principle,
                    rank=i + 1
                ))
            
            return PrincipleRanking(
                rankings=rankings,
                certainty=CertaintyLevel.UNSURE
            )
        
        raise ValueError(f"Unknown parse type: {parse_type}")
    
    async def validate_and_retry_parse(self, response: str, parse_type: str, max_retries: int = 3) -> Any:
        """Validate parsed response and retry if needed."""
        
        for attempt in range(max_retries):
            try:
                if parse_type == 'principle_choice':
                    parsed = await self.parse_principle_choice_enhanced(response)
                    if await self.validate_constraint_specification(parsed):
                        return parsed
                elif parse_type == 'principle_ranking':
                    parsed = await self.parse_principle_ranking_enhanced(response)
                    if len(parsed.rankings) == 4:
                        return parsed
                
                # If validation failed, improve the response text for retry
                if attempt < max_retries - 1:
                    response = await self._improve_response_format(response, parse_type)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
        
        raise ValueError(f"Failed to parse and validate {parse_type} after {max_retries} attempts")
    
    async def _improve_response_format(self, response: str, parse_type: str) -> str:
        """Use parser agent to improve response format."""
        
        format_prompt = self._get_format_improvement_prompt(response, parse_type)
        result = await Runner.run(self.parser_agent, format_prompt)
        
        return result.final_output
    
    def _get_format_improvement_prompt(self, response: str, parse_type: str) -> str:
        """Get prompt for improving response format."""
        
        if parse_type == 'principle_choice':
            return f"""
            The following response needs to be reformatted for clear principle choice extraction:
            
            Original response: "{response}"
            
            Please rewrite this to clearly state:
            1. Which principle they chose (a, b, c, or d)
            2. If they chose c or d, the specific constraint amount in dollars
            3. Their certainty level
            4. Their reasoning
            
            Format as: "I choose [principle] with [constraint if applicable]. I am [certainty level] about this choice because [reasoning]."
            """
        
        elif parse_type == 'principle_ranking':
            return f"""
            The following response needs to be reformatted for clear ranking extraction:
            
            Original response: "{response}"
            
            Please rewrite this as a numbered list ranking all 4 principles from best (1) to worst (4):
            
            1. [principle name]
            2. [principle name]  
            3. [principle name]
            4. [principle name]
            
            Overall certainty: [certainty level]
            """
        
        return response