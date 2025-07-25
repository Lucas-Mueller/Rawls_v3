"""
Phase 2 manager for group discussion and consensus building.
"""
import asyncio
import random
from typing import List, Dict
from agents import Agent, Runner

from models import (
    ParticipantContext, Phase2Results, GroupDiscussionResult, GroupDiscussionState,
    ExperimentPhase, VoteResult, PrincipleChoice, GroupStatementResponse,
    VotingResponse, Phase1Results, PrincipleRanking, PrincipleRankingResponse
)
from config import ExperimentConfiguration, AgentConfiguration
from experiment_agents import create_agent_with_output_type, update_participant_context, UtilityAgent, ParticipantAgent
from core.distribution_generator import DistributionGenerator
from utils.memory_manager import MemoryManager


class Phase2Manager:
    """Manages Phase 2 group discussion and consensus building."""
    
    def __init__(self, participants: List[ParticipantAgent], utility_agent: UtilityAgent):
        self.participants = participants
        self.utility_agent = utility_agent
    
    async def run_phase2(
        self, 
        config: ExperimentConfiguration,
        phase1_results: List[Phase1Results]
    ) -> Phase2Results:
        """Execute complete Phase 2 group discussion."""
        
        # CRITICAL: Initialize participants with CONTINUOUS memory from Phase 1
        participant_contexts = self._initialize_phase2_contexts(phase1_results, config)
        
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
            participant_contexts, discussion_result, payoff_results, config
        )
        
        return Phase2Results(
            discussion_result=discussion_result,
            payoff_results=payoff_results, 
            final_rankings=final_rankings
        )
    
    def _initialize_phase2_contexts(
        self, 
        phase1_results: List[Phase1Results],
        config: ExperimentConfiguration
    ) -> List[ParticipantContext]:
        """
        CRITICAL: Transfer complete Phase 1 memory to Phase 2 contexts
        This ensures continuous memory across experimental phases
        """
        phase2_contexts = []
        
        for i, phase1_result in enumerate(phase1_results):
            agent_config = config.agents[i]
            
            # Create Phase 2 context with continuous memory - no automatic transition
            phase2_context = ParticipantContext(
                name=phase1_result.participant_name,
                role_description=agent_config.personality,
                bank_balance=phase1_result.total_earnings,  # Carry forward earnings
                memory=phase1_result.final_memory_state,  # CONTINUOUS MEMORY FROM PHASE 1
                round_number=0,  # Reset for Phase 2
                phase=ExperimentPhase.PHASE_2,
                memory_character_limit=agent_config.memory_character_limit
            )
            
            phase2_contexts.append(phase2_context)
            
        return phase2_contexts
    
    async def _run_group_discussion(
        self,
        config: ExperimentConfiguration,
        contexts: List[ParticipantContext]
    ) -> GroupDiscussionResult:
        """Run sequential group discussion with voting."""
        
        discussion_state = GroupDiscussionState()
        last_round_starter = None
        
        for round_num in range(1, config.phase2_rounds + 1):
            discussion_state.round_number = round_num
            
            # Generate speaking order (avoid same participant starting consecutive rounds)
            speaking_order = self._generate_speaking_order(round_num, contexts, last_round_starter)
            last_round_starter = speaking_order[0]
            
            for participant_idx in speaking_order:
                participant = self.participants[participant_idx]
                context = contexts[participant_idx]
                agent_config = config.agents[participant_idx]
                
                # Update context with current round
                context.round_number = round_num
                
                # Get participant statement (with internal reasoning if enabled)
                statement, statement_content = await self._get_participant_statement(
                    participant, context, discussion_state, agent_config
                )
                
                discussion_state.add_statement(participant.name, statement)
                
                # Update participant memory with agent
                context.memory = await MemoryManager.prompt_agent_for_memory_update(
                    participant, context, statement_content
                )
                contexts[participant_idx] = update_participant_context(
                    context, new_round=round_num
                )
                
                # Check for vote proposal
                vote_proposal = await self.utility_agent.extract_vote_from_statement(statement)
                
                if vote_proposal:
                    # Check if all participants agree to vote
                    if await self._check_unanimous_vote_agreement(
                        discussion_state, contexts, config
                    ):
                        vote_result = await self._conduct_group_vote(contexts, config)
                        discussion_state.add_vote_result(vote_result)
                        
                        # Update all participants' memory with vote result
                        vote_content = f"VOTE CONDUCTED: {vote_result.consensus_reached and 'Consensus reached' or 'No consensus'}"
                        if vote_result.consensus_reached and vote_result.agreed_principle:
                            vote_content += f" on {vote_result.agreed_principle.principle.value}"
                        
                        # Update each participant's memory with the vote outcome
                        for i in range(len(contexts)):
                            participant = self.participants[i]
                            contexts[i].memory = await MemoryManager.prompt_agent_for_memory_update(
                                participant, contexts[i], 
                                f"Vote Outcome: {vote_content}"
                            )
                        
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
    
    def _generate_speaking_order(
        self, 
        round_num: int, 
        contexts: List[ParticipantContext],
        last_round_starter: int = None
    ) -> List[int]:
        """Generate speaking order avoiding same participant starting consecutive rounds."""
        participant_indices = list(range(len(contexts)))
        random.shuffle(participant_indices)
        
        # If this isn't the first round, ensure different starter
        if last_round_starter is not None and participant_indices[0] == last_round_starter:
            # Swap first and second elements
            if len(participant_indices) > 1:
                participant_indices[0], participant_indices[1] = participant_indices[1], participant_indices[0]
        
        return participant_indices
    
    async def _get_participant_statement(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        discussion_state: GroupDiscussionState,
        agent_config: AgentConfiguration
    ) -> tuple[str, str]:
        """Get participant's statement for the current round."""
        
        discussion_prompt = self._build_discussion_prompt(discussion_state, context.round_number)
        
        # Create agent with structured output if reasoning is enabled
        if agent_config.reasoning_enabled:
            statement_agent = create_agent_with_output_type(agent_config, GroupStatementResponse)
            result = await Runner.run(statement_agent, discussion_prompt, context=context)
            statement = result.final_output.public_statement
            
            # Create round content for memory
            round_content = f"""Prompt: {discussion_prompt}
Your Internal Reasoning: {result.final_output.internal_reasoning if hasattr(result.final_output, 'internal_reasoning') else 'N/A'}
Your Public Statement: {statement}
Outcome: Made statement in Round {context.round_number} of group discussion."""
        else:
            # Direct statement without structured reasoning
            result = await Runner.run(participant.agent, discussion_prompt, context=context)
            statement = result.final_output
            
            # Create round content for memory
            round_content = f"""Prompt: {discussion_prompt}
Your Statement: {statement}
Outcome: Made statement in Round {context.round_number} of group discussion."""
        
        return statement, round_content
    
    async def _check_unanimous_vote_agreement(
        self,
        discussion_state: GroupDiscussionState,
        contexts: List[ParticipantContext],
        config: ExperimentConfiguration
    ) -> bool:
        """Check if all participants agree to conduct a vote."""
        
        vote_agreement_prompt = """
        A vote has been proposed. Do you agree to conduct a vote now?
        
        Respond with either "YES" or "NO" and briefly explain your reasoning.
        If you think more discussion is needed, respond "NO".
        If you think the group is ready to vote, respond "YES".
        """
        
        agreement_tasks = []
        for i, participant in enumerate(self.participants):
            context = contexts[i]
            task = asyncio.create_task(
                Runner.run(participant.agent, vote_agreement_prompt, context=context)
            )
            agreement_tasks.append(task)
        
        responses = await asyncio.gather(*agreement_tasks)
        
        # Check if all responses contain "YES"
        agreements = [("YES" in response.final_output.upper()) for response in responses]
        return all(agreements)
    
    async def _conduct_group_vote(
        self, 
        contexts: List[ParticipantContext],
        config: ExperimentConfiguration
    ) -> VoteResult:
        """Conduct secret ballot voting."""
        
        voting_tasks = []
        for i, participant in enumerate(self.participants):
            context = contexts[i]
            agent_config = config.agents[i]
            task = asyncio.create_task(
                self._get_participant_vote(participant, context, agent_config)
            )
            voting_tasks.append(task)
        
        votes = await asyncio.gather(*voting_tasks)
        
        # Validate votes and check for consensus
        valid_votes = []
        for i, vote in enumerate(votes):
            if await self.utility_agent.validate_constraint_specification(vote):
                valid_votes.append(vote)
            else:
                # Re-prompt for valid vote
                corrected_vote = await self._re_prompt_for_valid_vote(
                    self.participants[i], contexts[i], vote, config.agents[i]
                )
                valid_votes.append(corrected_vote)
        
        # Check for exact consensus (including constraint amounts)
        consensus_principle = self._check_exact_consensus(valid_votes)
        
        return VoteResult(
            votes=valid_votes,
            consensus_reached=consensus_principle is not None,
            agreed_principle=consensus_principle,
            vote_counts=self._count_votes(valid_votes)
        )
    
    async def _get_participant_vote(
        self,
        participant: ParticipantAgent, 
        context: ParticipantContext,
        agent_config: AgentConfiguration
    ) -> PrincipleChoice:
        """Get a participant's vote in secret ballot."""
        
        voting_prompt = """
        SECRET BALLOT VOTE
        
        Choose ONE of the four justice principles for the group to adopt:
        (a) maximizing the floor
        (b) maximizing the average  
        (c) maximizing the average with a floor constraint
        (d) maximizing the average with a range constraint
        
        **IMPORTANT**: If you choose (c) or (d), you MUST specify the exact constraint amount in dollars.
        
        This is your final vote. The group needs unanimous agreement (everyone choosing the exact same principle with the exact same constraint amount) to reach consensus.
        
        What is your vote?
        """
        
        voting_agent = create_agent_with_output_type(agent_config, VotingResponse)
        result = await Runner.run(voting_agent, voting_prompt, context=context)
        
        # Parse the vote
        try:
            parsed_vote = await self.utility_agent.parse_principle_choice(
                result.final_output.vote_reasoning + " " + str(result.final_output.vote_choice.dict())
            )
            vote_choice = parsed_vote
        except Exception:
            # Fallback to structured response
            vote_choice = result.final_output.vote_choice
        
        # Validate the constraint amount if needed
        if not vote_choice.is_valid_constraint():
            # Re-prompt for valid constraint amount
            vote_choice = await self._re_prompt_for_valid_vote(
                participant, context, vote_choice, agent_config
            )
        
        return vote_choice
    
    async def _re_prompt_for_valid_vote(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext, 
        invalid_vote: PrincipleChoice,
        agent_config: AgentConfiguration
    ) -> PrincipleChoice:
        """Re-prompt participant for valid vote with constraint amount."""
        
        retry_prompt = await self.utility_agent.re_prompt_for_constraint(
            participant.name, invalid_vote
        )
        
        voting_agent = create_agent_with_output_type(agent_config, VotingResponse)
        result = await Runner.run(voting_agent, retry_prompt, context=context)
        
        try:
            parsed_vote = await self.utility_agent.parse_principle_choice(
                result.final_output.vote_reasoning + " " + str(result.final_output.vote_choice.dict())
            )
            return parsed_vote
        except Exception:
            return result.final_output.vote_choice
    
    def _check_exact_consensus(self, votes: List[PrincipleChoice]) -> PrincipleChoice:
        """Check if all votes are exactly identical (including constraint amounts)."""
        if not votes:
            return None
            
        first_vote = votes[0]
        for vote in votes[1:]:
            if (vote.principle != first_vote.principle or 
                vote.constraint_amount != first_vote.constraint_amount):
                return None
        
        return first_vote
    
    def _count_votes(self, votes: List[PrincipleChoice]) -> Dict[str, int]:
        """Count votes by principle (including constraint amounts)."""
        vote_counts = {}
        for vote in votes:
            key = vote.principle.value
            if vote.constraint_amount:
                key += f"_${vote.constraint_amount}"
            vote_counts[key] = vote_counts.get(key, 0) + 1
        return vote_counts
    
    async def _apply_group_principle_and_calculate_payoffs(
        self,
        discussion_result: GroupDiscussionResult,
        config: ExperimentConfiguration
    ) -> Dict[str, float]:
        """Apply chosen principle or random assignment if no consensus."""
        
        # Generate new distribution set for Phase 2 payoffs
        distribution_set = DistributionGenerator.generate_dynamic_distribution(
            config.distribution_range_phase2
        )
        
        payoffs = {}
        
        if discussion_result.consensus_reached and discussion_result.agreed_principle:
            # Apply agreed principle
            chosen_distribution, explanation = DistributionGenerator.apply_principle_to_distributions(
                distribution_set.distributions, discussion_result.agreed_principle
            )
            
            # Assign each participant to income class and calculate payoff
            for participant in self.participants:
                assigned_class, earnings = DistributionGenerator.calculate_payoff(chosen_distribution)
                payoffs[participant.name] = earnings
        else:
            # Random assignment - each participant gets random income class from random distribution
            for participant in self.participants:
                random_distribution = random.choice(distribution_set.distributions)
                assigned_class, earnings = DistributionGenerator.calculate_payoff(random_distribution)
                payoffs[participant.name] = earnings
        
        return payoffs
    
    async def _collect_final_rankings(
        self,
        contexts: List[ParticipantContext],
        discussion_result: GroupDiscussionResult,
        payoff_results: Dict[str, float],
        config: ExperimentConfiguration
    ) -> Dict[str, PrincipleRanking]:
        """Collect final principle rankings from all participants."""
        
        final_ranking_tasks = []
        
        for i, participant in enumerate(self.participants):
            context = contexts[i]
            agent_config = config.agents[i]
            
            # Update context with final results using agent-managed memory
            final_earnings = payoff_results[participant.name]
            result_content = f"FINAL RESULTS: Phase 2 earnings: ${final_earnings:.2f}. "
            
            if discussion_result.consensus_reached:
                result_content += f"Group reached consensus on {discussion_result.agreed_principle.principle.value}."
            else:
                result_content += "Group did not reach consensus. Earnings were randomly assigned."
            
            # Update memory with agent
            context.memory = await MemoryManager.prompt_agent_for_memory_update(
                participant, context, f"Final Phase 2 Results: {result_content}"
            )
            
            updated_context = update_participant_context(
                context, balance_change=final_earnings
            )
            
            task = asyncio.create_task(
                self._get_final_ranking(participant, updated_context, agent_config)
            )
            final_ranking_tasks.append(task)
        
        rankings = await asyncio.gather(*final_ranking_tasks)
        
        # Return as dictionary mapping participant name to ranking
        final_rankings = {}
        for i, ranking in enumerate(rankings):
            final_rankings[self.participants[i].name] = ranking
        
        return final_rankings
    
    async def _get_final_ranking(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        agent_config: AgentConfiguration
    ) -> PrincipleRanking:
        """Get participant's final principle ranking after Phase 2."""
        
        final_ranking_prompt = """
        After participating in both Phase 1 (individual experience) and Phase 2 (group discussion), 
        please provide your final ranking of the four justice principles from best (1) to worst (4).
        
        Reflect on:
        - Your Phase 1 experiences with applying the principles
        - The group discussion and different perspectives you heard
        - The final outcome and your earnings
        - How your understanding of the principles has evolved
        
        Provide your final ranking with an overall certainty level for the entire ranking and explain how the complete experiment 
        influenced your final preferences.
        """
        
        ranking_agent = create_agent_with_output_type(agent_config, PrincipleRankingResponse)
        result = await Runner.run(ranking_agent, final_ranking_prompt, context=context)
        
        try:
            # Parse the ranking using utility agent
            parsed_ranking = await self.utility_agent.parse_principle_ranking(result.final_output.ranking_explanation)
            return parsed_ranking
        except Exception:
            # Fallback to the structured response
            return result.final_output.principle_rankings
    
    def _build_discussion_prompt(self, discussion_state: GroupDiscussionState, round_num: int) -> str:
        """Build prompt for group discussion round."""
        
        return f"""
        GROUP DISCUSSION - Round {round_num}
        
        Discussion History:
        {discussion_state.public_history or "No previous discussion."}
        
        Your task is to work with other participants to reach consensus on which justice principle 
        the group should adopt. The group's chosen principle will determine everyone's final earnings.
        
        Guidelines:
        - Share your perspective based on your Phase 1 experiences
        - Listen to and consider others' viewpoints
        - You may propose a vote when you think the group is ready
        - All participants must agree to vote before voting begins
        - Consensus requires everyone to choose the EXACT same principle (including constraint amounts)
        
        If no consensus is reached, final earnings will be randomly determined.
        
        What is your statement to the group for this round?
        """