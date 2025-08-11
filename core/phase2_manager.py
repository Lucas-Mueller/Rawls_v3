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
from experiment_agents import update_participant_context, UtilityAgent, ParticipantAgent
from core.distribution_generator import DistributionGenerator
from utils.memory_manager import MemoryManager
from utils.agent_centric_logger import AgentCentricLogger, MemoryStateCapture
from utils.language_manager import get_language_manager


class Phase2Manager:
    """Manages Phase 2 group discussion and consensus building."""
    
    def __init__(self, participants: List[ParticipantAgent], utility_agent: UtilityAgent):
        self.participants = participants
        self.utility_agent = utility_agent
        self.logger = None  # Will be set in run_phase2
    
    def _log_info(self, message: str):
        """Safe logging helper."""
        if self.logger and hasattr(self.logger, 'debug_logger'):
            self.logger.debug_logger.info(message)
    
    def _log_warning(self, message: str):
        """Safe logging helper."""
        if self.logger and hasattr(self.logger, 'debug_logger'):
            self.logger.debug_logger.warning(message)
    
    async def run_phase2(
        self, 
        config: ExperimentConfiguration,
        phase1_results: List[Phase1Results],
        logger: AgentCentricLogger = None
    ) -> Phase2Results:
        """Execute complete Phase 2 group discussion."""
        
        # Store logger for use in consensus methods
        self.logger = logger
        
        # CRITICAL: Initialize participants with CONTINUOUS memory from Phase 1
        participant_contexts = self._initialize_phase2_contexts(phase1_results, config)
        
        # Group discussion
        discussion_result = await self._run_group_discussion(
            config, participant_contexts, logger
        )
        
        # Apply chosen principle and calculate payoffs
        payoff_results, assigned_classes = await self._apply_group_principle_and_calculate_payoffs(
            discussion_result, config
        )
        
        # Final individual rankings
        final_rankings = await self._collect_final_rankings(
            participant_contexts, discussion_result, payoff_results, assigned_classes, config, logger
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
        contexts: List[ParticipantContext],
        logger: AgentCentricLogger = None
    ) -> GroupDiscussionResult:
        """Run sequential group discussion with voting."""
        
        discussion_state = GroupDiscussionState()
        last_round_starter = None
        
        for round_num in range(1, config.phase2_rounds + 1):
            discussion_state.round_number = round_num
            
            # Generate speaking order (avoid same participant starting consecutive rounds)
            speaking_order = self._generate_speaking_order(round_num, contexts, last_round_starter)
            last_round_starter = speaking_order[0]
            
            for speaking_order_position, participant_idx in enumerate(speaking_order):
                participant = self.participants[participant_idx]
                context = contexts[participant_idx]
                agent_config = config.agents[participant_idx]
                
                # Update context with current round
                context.round_number = round_num
                
                # Capture pre-statement state
                memory_before = context.memory
                balance_before = context.bank_balance
                
                # Get participant statement (with internal reasoning if enabled)
                statement, statement_content, internal_reasoning = await self._get_participant_statement_enhanced(
                    participant, context, discussion_state, agent_config
                )
                
                discussion_state.add_statement(participant.name, statement)
                
                # Log discussion round
                if logger:
                    vote_intention = MemoryStateCapture.extract_vote_intention(statement)
                    favored_principle = self._extract_favored_principle(statement)
                    
                    logger.log_discussion_round(
                        participant.name,
                        round_num,
                        speaking_order_position + 1,  # 1-indexed speaking order
                        internal_reasoning,
                        statement,
                        vote_intention,
                        favored_principle,
                        memory_before,
                        balance_before
                    )
                
                # Update participant memory with agent
                context.memory = await MemoryManager.prompt_agent_for_memory_update(
                    participant, context, statement_content
                )
                contexts[participant_idx] = update_participant_context(
                    context, new_round=round_num
                )
                
                # Check for vote proposal
                vote_proposal = await self.utility_agent.extract_vote_from_statement(statement)
                
                # ADD VOTE DETECTION DEBUG LOGGING
                import logging
                debug_logger = logging.getLogger(__name__)
                
                debug_logger.info(f"=== VOTE DETECTION DEBUG ===")
                debug_logger.info(f"Agent: {participant.name}")
                debug_logger.info(f"Statement: {statement}")
                debug_logger.info(f"Vote proposal detected: {vote_proposal is not None}")
                if vote_proposal:
                    debug_logger.info(f"Vote proposal text: {vote_proposal.proposal_text}")
                else:
                    debug_logger.info(f"No vote proposal detected")
                
                if vote_proposal:
                    debug_logger.info(f"Checking unanimous agreement...")
                    # Check if all participants agree to vote
                    unanimous_agreement = await self._check_unanimous_vote_agreement(
                        discussion_state, contexts, config
                    )
                    debug_logger.info(f"Unanimous agreement result: {unanimous_agreement}")
                    
                    if unanimous_agreement:
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
        
        # Always use text responses, no structured output needed for statements
        result = await Runner.run(participant.agent, discussion_prompt, context=context)
        statement = result.final_output
        
        # Create round content for memory
        round_content = f"""Prompt: {discussion_prompt}
Your Statement: {statement}
Outcome: Made statement in Round {context.round_number} of group discussion."""
        
        return statement, round_content

    async def _get_participant_statement_enhanced(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        discussion_state: GroupDiscussionState,
        agent_config: AgentConfiguration
    ) -> tuple[str, str, str]:
        """Get participant's statement with separated internal reasoning."""
        
        # If reasoning is enabled, ask for internal reasoning first
        internal_reasoning = ""
        if agent_config.reasoning_enabled:
            reasoning_prompt = self._build_internal_reasoning_prompt(discussion_state, context.round_number)
            reasoning_result = await Runner.run(participant.agent, reasoning_prompt, context=context)
            internal_reasoning = reasoning_result.final_output
        
        # Get public statement
        discussion_prompt = self._build_discussion_prompt(discussion_state, context.round_number)
        result = await Runner.run(participant.agent, discussion_prompt, context=context)
        statement = result.final_output
        
        # Create round content for memory
        round_content = f"""Prompt: {discussion_prompt}
Internal Reasoning: {internal_reasoning}
Your Public Statement: {statement}
Outcome: Made statement in Round {context.round_number} of group discussion."""
        
        return statement, round_content, internal_reasoning
    
    def _extract_favored_principle(self, statement: str) -> str:
        """Extract favored principle from participant statement."""
        statement_lower = statement.lower()
        
        if any(phrase in statement_lower for phrase in ["principle a", "maximizing floor", "floor income"]):
            return "Principle A"
        elif any(phrase in statement_lower for phrase in ["principle b", "maximizing average", "average income"]):
            return "Principle B"
        elif any(phrase in statement_lower for phrase in ["principle c", "floor constraint", "average with floor"]):
            return "Principle C"
        elif any(phrase in statement_lower for phrase in ["principle d", "range constraint", "average with range"]):
            return "Principle D"
        else:
            language_manager = get_language_manager()
            return language_manager.get("prompts.phase2_default_constraint_specification")
    
    def _determine_assigned_class(self, earnings: float) -> str:
        """Determine income class based on earnings amount."""
        language_manager = get_language_manager()
        # Get income class names using the new API
        income_class_names = {
            "high": language_manager.get("common.income_classes.high"),
            "medium_high": language_manager.get("common.income_classes.medium_high"),
            "medium": language_manager.get("common.income_classes.medium"),
            "medium_low": language_manager.get("common.income_classes.medium_low"),
            "low": language_manager.get("common.income_classes.low")
        }
        
        # Simple mapping based on typical earnings ranges
        if earnings >= 30:
            return income_class_names["high"]
        elif earnings >= 25:
            return income_class_names["medium_high"]
        elif earnings >= 20:
            return income_class_names["medium"]
        elif earnings >= 15:
            return income_class_names["medium_low"]
        else:
            return income_class_names["low"]
    
    async def _check_unanimous_vote_agreement(
        self,
        discussion_state: GroupDiscussionState,
        contexts: List[ParticipantContext],
        config: ExperimentConfiguration
    ) -> bool:
        """Check if all participants agree to conduct a vote."""
        
        vote_agreement_prompt = """
        A vote has been proposed. Do you agree to conduct a vote now?
        
        Respond with either "YES" or "NO".
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
        
        # ADD UNANIMOUS AGREEMENT DEBUG LOGGING
        import logging
        debug_logger = logging.getLogger(__name__)
        
        debug_logger.info(f"=== UNANIMOUS AGREEMENT DEBUG ===")
        for i, response in enumerate(responses):
            participant_name = self.participants[i].name
            response_text = response.final_output
            contains_yes = "YES" in response_text.upper()
            debug_logger.info(f"{participant_name} response: '{response_text}' -> Contains YES: {contains_yes}")
        
        # Check if all responses contain "YES"
        agreements = [("YES" in response.final_output.upper()) for response in responses]
        debug_logger.info(f"All agreements: {agreements}")
        debug_logger.info(f"Unanimous result: {all(agreements)}")
        
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
        
        # Check for consensus (try exact first, then semantic matching)
        consensus_principle = self._check_exact_consensus(valid_votes)
        if consensus_principle is None:
            self._log_info("Exact consensus failed, trying semantic matching...")
            consensus_principle = self._check_semantic_consensus(valid_votes)
        
        # Additional logging for vote result
        self._log_info("=== VOTE RESULT SUMMARY ===")
        self._log_info(f"Consensus reached: {consensus_principle is not None}")
        self._log_info(f"Vote counts: {self._count_votes(valid_votes)}")
        if consensus_principle:
            self._log_info(f"Agreed principle: {consensus_principle.principle.value} with constraint: {consensus_principle.constraint_amount}")
        
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
        
        # Always use text responses, parse with enhanced utility agent
        result = await Runner.run(participant.agent, voting_prompt, context=context)
        text_response = result.final_output
        
        # Parse using enhanced utility agent with retry logic
        vote_choice = await self.utility_agent.parse_principle_choice_enhanced(text_response)
        
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
        
        # Always use text responses, parse with enhanced utility agent
        result = await Runner.run(participant.agent, retry_prompt, context=context)
        retry_text = result.final_output
        
        # Parse using enhanced utility agent with retry logic
        return await self.utility_agent.parse_principle_choice_enhanced(retry_text)
    
    def _check_exact_consensus(self, votes: List[PrincipleChoice]) -> PrincipleChoice:
        """Check if all votes are exactly identical (including constraint amounts)."""
        
        if not votes:
            self._log_warning("No votes provided for consensus check")
            return None
        
        # Log all votes for comparison
        self._log_info("=== VOTE COMPARISON ANALYSIS ===")
        self._log_info(f"Total votes: {len(votes)}")
        
        for i, vote in enumerate(votes):
            self._log_info(f"Vote {i+1}: principle={vote.principle.value}, constraint_amount={vote.constraint_amount}, certainty={vote.certainty}")
            if vote.reasoning:
                self._log_info(f"Vote {i+1} reasoning excerpt: {vote.reasoning[:100]}...")
        
        first_vote = votes[0]
        self._log_info(f"Reference vote (first): principle={first_vote.principle.value}, constraint_amount={first_vote.constraint_amount}")
        
        # Check each vote against the first
        consensus_failed = False
        for i, vote in enumerate(votes[1:], 1):
            principle_match = vote.principle == first_vote.principle
            constraint_match = vote.constraint_amount == first_vote.constraint_amount
            
            self._log_info(f"Vote {i+1} vs Reference: principle_match={principle_match}, constraint_match={constraint_match}")
            
            if not principle_match:
                self._log_warning(f"CONSENSUS FAILURE: Vote {i+1} principle mismatch - '{vote.principle.value}' != '{first_vote.principle.value}'")
                consensus_failed = True
            
            if not constraint_match:
                self._log_warning(f"CONSENSUS FAILURE: Vote {i+1} constraint mismatch - {vote.constraint_amount} != {first_vote.constraint_amount}")
                consensus_failed = True
        
        if consensus_failed:
            self._log_info("=== CONSENSUS RESULT: FAILED ===")
            return None
        else:
            self._log_info("=== CONSENSUS RESULT: SUCCESS ===")
            self._log_info(f"Agreed principle: {first_vote.principle.value} with constraint: {first_vote.constraint_amount}")
            return first_vote
    
    def _check_semantic_consensus(self, votes: List[PrincipleChoice]) -> PrincipleChoice:
        """Check for semantic consensus with fuzzy matching for constraint amounts."""
        
        if not votes:
            return None
        
        self._log_info("=== SEMANTIC CONSENSUS ANALYSIS ===")
        
        # Group votes by principle first
        principle_groups = {}
        for vote in votes:
            principle_key = vote.principle.value
            if principle_key not in principle_groups:
                principle_groups[principle_key] = []
            principle_groups[principle_key].append(vote)
        
        self._log_info(f"Principle groups: {[(k, len(v)) for k, v in principle_groups.items()]}")
        
        # Check if all votes are for the same principle
        if len(principle_groups) != 1:
            self._log_info("Multiple principles chosen - no semantic consensus possible")
            return None
        
        # All votes are for the same principle, now check constraint amounts
        principle = list(principle_groups.keys())[0]
        votes_for_principle = principle_groups[principle]
        
        self._log_info(f"All votes are for: {principle}")
        
        # If it's not a constraint principle, we have consensus
        if 'constraint' not in principle.lower():
            self._log_info("Non-constraint principle - semantic consensus achieved")
            return votes_for_principle[0]
        
        # For constraint principles, check if amounts are semantically similar
        constraint_amounts = [v.constraint_amount for v in votes_for_principle if v.constraint_amount is not None]
        
        self._log_info(f"Constraint amounts: {constraint_amounts}")
        
        if not constraint_amounts:
            self._log_warning("Constraint principle but no constraint amounts found")
            return None
        
        # Check if constraint amounts are within semantic tolerance
        semantic_consensus = self._check_constraint_semantic_similarity(constraint_amounts)
        
        if semantic_consensus:
            # Use the most common constraint amount (or first if tied)
            from collections import Counter
            amount_counts = Counter(constraint_amounts)
            most_common_amount = amount_counts.most_common(1)[0][0]
            
            self._log_info(f"Semantic consensus achieved with constraint amount: {most_common_amount}")
            
            # Return a vote with the consensus principle and amount
            return PrincipleChoice(
                principle=votes_for_principle[0].principle,
                constraint_amount=most_common_amount,
                certainty=votes_for_principle[0].certainty,
                reasoning="Semantic consensus from group votes"
            )
        else:
            self._log_info("Constraint amounts too different for semantic consensus")
            return None
    
    def _check_constraint_semantic_similarity(self, amounts: List[int]) -> bool:
        """Check if constraint amounts are semantically similar (within tolerance)."""
        
        if len(set(amounts)) == 1:
            self._log_info("All constraint amounts identical")
            return True
        
        # Calculate tolerance (10% of the average or minimum $1000)
        avg_amount = sum(amounts) / len(amounts)
        tolerance = max(1000, int(avg_amount * 0.1))
        
        self._log_info(f"Average amount: {avg_amount}, tolerance: ±{tolerance}")
        
        # Check if all amounts are within tolerance of each other
        min_amount = min(amounts)
        max_amount = max(amounts)
        
        if max_amount - min_amount <= tolerance:
            self._log_info(f"Amounts within tolerance: {min_amount} to {max_amount} (range: {max_amount - min_amount})")
            return True
        else:
            self._log_info(f"Amounts outside tolerance: {min_amount} to {max_amount} (range: {max_amount - min_amount})")
            return False
    
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
    ) -> tuple[Dict[str, float], Dict[str, str]]:
        """Apply chosen principle or random assignment if no consensus.
        
        Returns:
            tuple: (payoffs dict, assigned_classes dict)
        """
        
        # Generate new distribution set for Phase 2 payoffs
        distribution_set = DistributionGenerator.generate_dynamic_distribution(
            config.distribution_range_phase2
        )
        
        payoffs = {}
        assigned_classes = {}
        
        if discussion_result.consensus_reached and discussion_result.agreed_principle:
            # Apply agreed principle
            chosen_distribution, explanation = DistributionGenerator.apply_principle_to_distributions(
                distribution_set.distributions, discussion_result.agreed_principle
            )
            
            # Assign each participant to income class and calculate payoff
            for participant in self.participants:
                assigned_class, earnings = DistributionGenerator.calculate_payoff(chosen_distribution)
                payoffs[participant.name] = earnings
                assigned_classes[participant.name] = assigned_class
        else:
            # Random assignment - each participant gets random income class from random distribution
            for participant in self.participants:
                random_distribution = random.choice(distribution_set.distributions)
                assigned_class, earnings = DistributionGenerator.calculate_payoff(random_distribution)
                payoffs[participant.name] = earnings
                assigned_classes[participant.name] = assigned_class
        
        return payoffs, assigned_classes
    
    async def _collect_final_rankings(
        self,
        contexts: List[ParticipantContext],
        discussion_result: GroupDiscussionResult,
        payoff_results: Dict[str, float],
        assigned_classes: Dict[str, str],
        config: ExperimentConfiguration,
        logger: AgentCentricLogger = None
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
            assigned_class = assigned_classes[participant.name]
            final_ranking_tasks.append((task, participant.name, assigned_class, final_earnings, context.memory, updated_context.bank_balance))
        
        # Gather just the tasks for asyncio
        tasks = [task_info[0] for task_info in final_ranking_tasks]
        rankings = await asyncio.gather(*tasks)
        
        # Log post-discussion state with final rankings and return dictionary
        final_rankings = {}
        for i, ranking in enumerate(rankings):
            task_info = final_ranking_tasks[i]
            participant_name = task_info[1]
            assigned_class = task_info[2]
            final_earnings = task_info[3]
            memory_state = task_info[4]
            bank_balance = task_info[5]
            
            # Log post-discussion state with actual ranking
            if logger:
                logger.log_post_discussion(
                    participant_name,
                    assigned_class,
                    final_earnings,
                    ranking,
                    memory_state,
                    bank_balance
                )
            
            final_rankings[participant_name] = ranking
        
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
        
        # Always use text responses, parse with enhanced utility agent
        result = await Runner.run(participant.agent, final_ranking_prompt, context=context)
        text_response = result.final_output
        
        # Parse using enhanced utility agent with retry logic
        return await self.utility_agent.parse_principle_ranking_enhanced(text_response)
    
    def _build_internal_reasoning_prompt(self, discussion_state: GroupDiscussionState, round_num: int) -> str:
        """Build prompt for internal reasoning before public statement."""
        
        return f"""
        GROUP DISCUSSION - Round {round_num} (Internal Reasoning)
        
        Discussion History:
        {discussion_state.public_history or "No previous discussion."}
        
        Before making your public statement, consider internally:
        - What is your current position on which justice principle the group should adopt?
        - How has the discussion so far influenced your thinking?
        - What arguments do you want to make in your public statement?
        - Are you ready to call for a vote, or do you need more discussion?
        
        Provide your internal reasoning (this will not be shared with other participants).
        """
    
    def _build_discussion_prompt(self, discussion_state: GroupDiscussionState, round_num: int) -> str:
        """Build prompt for group discussion round."""
        
        return f"""
        GROUP DISCUSSION - Round {round_num}
        
        Discussion History:
        {discussion_state.public_history or "No previous discussion."}
        
        Your task is to work with other participants to reach consensus on which justice principle 
        the group should adopt. The group's chosen principle will determine everyone's final earnings.
        
        Guidelines:
        - You may propose a vote when you think the group is ready
        - All participants must agree to vote before voting begins
        - Consensus requires everyone to choose the EXACT same principle (including constraint amounts)
        
        If no consensus is reached, final earnings will be randomly determined.
        
        What is your statement to the group for this round?
        """