"""
Utility agent for parsing and validating participant responses.
"""
import asyncio
from typing import Optional
from agents import Agent, Runner, AgentOutputSchema

from models import (
    PrincipleChoice, PrincipleRanking, VoteProposal, JusticePrinciple,
    ParsedResponse, ValidationResult, CertaintyLevel, RankedPrinciple
)


class UtilityAgent:
    """Specialized agent for parsing and validating participant responses."""
    
    def __init__(self):
        self.parser_agent = Agent(
            name="Response Parser",
            instructions=self._get_parser_instructions()
        )
        
        self.validator_agent = Agent(
            name="Response Validator", 
            instructions=self._get_validator_instructions()
        )
    
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
    
    async def parse_principle_choice(self, response: str) -> PrincipleChoice:
        """Parse principle choice from participant response."""
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
        
        result = await Runner.run(self.parser_agent, parse_prompt)
        parsed_result = result.final_output
        
        if not parsed_result.success:
            raise ValueError(f"Failed to parse principle choice: {parsed_result.error_message}")
        
        data = parsed_result.parsed_data
        return PrincipleChoice(
            principle=JusticePrinciple(data['principle']),
            constraint_amount=data.get('constraint_amount'),
            certainty=CertaintyLevel(data['certainty']),
            reasoning=data.get('reasoning')
        )
    
    async def parse_principle_ranking(self, response: str) -> PrincipleRanking:
        """Parse principle ranking from participant response."""
        parse_prompt = f"""
        Parse the following participant response to extract their complete ranking of justice principles:
        
        Response: "{response}"
        
        Extract a complete ranking of all 4 principles from best (rank 1) to worst (rank 4).
        Also extract certainty levels for each principle.
        
        Return the parsed data as a dictionary with:
        - rankings: list of {{principle, rank, certainty}} objects
        """
        
        result = await Runner.run(self.parser_agent, parse_prompt)
        parsed_result = result.final_output
        
        if not parsed_result.success:
            raise ValueError(f"Failed to parse principle ranking: {parsed_result.error_message}")
        
        data = parsed_result.parsed_data
        rankings = []
        for ranking_data in data['rankings']:
            rankings.append(RankedPrinciple(
                principle=JusticePrinciple(ranking_data['principle']),
                rank=ranking_data['rank'],
                certainty=CertaintyLevel(ranking_data['certainty'])
            ))
        
        return PrincipleRanking(rankings=rankings)
    
    async def validate_constraint_specification(self, choice: PrincipleChoice) -> bool:
        """Validate constraint principles have required amounts."""
        constraint_principles = [
            JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
        ]
        
        if choice.principle in constraint_principles:
            return choice.constraint_amount is not None and choice.constraint_amount > 0
        
        return True
    
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