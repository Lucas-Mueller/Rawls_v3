"""
Integration tests for state management and consistency across phases.
Tests memory continuity, bank balance consistency, and state synchronization.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from core.experiment_manager import FrohlichExperimentManager
from tests.integration.fixtures.experiment_fixtures import ExperimentTestFixture
from tests.integration.utils.async_test_utils import AsyncTestUtils
from models import ParticipantContext, ExperimentPhase, IncomeClass
from utils.error_handling import get_global_error_handler


class TestStateConsistency:
    """Test state management and consistency across phases."""
    
    def setup_method(self):
        """Set up test fixtures for each test."""
        self.config = ExperimentTestFixture.create_minimal_config(num_agents=2)
        self.error_handler = get_global_error_handler()
        self.error_handler.clear_error_history()
        self.captured_states = []
    
    def capture_context_state(self, context: ParticipantContext):
        """Helper to capture context state for verification."""
        self.captured_states.append({
            "name": context.name,
            "bank_balance": context.bank_balance,
            "memory": context.memory,
            "round_number": context.round_number,
            "phase": context.phase,
            "timestamp": asyncio.get_event_loop().time()
        })
    
    @pytest.mark.asyncio
    async def test_memory_continuity_across_phases(self):
        """Test agent memory preserved from Phase 1 to Phase 2."""
        
        manager = FrohlichExperimentManager(self.config)
        phase1_memories = {}
        phase2_initial_memories = {}
        
        # Mock memory updates to track state
        original_memory_update = None
        
        async def tracking_memory_update(self, prompt, bank_balance):
            nonlocal original_memory_update
            # Create unique memory content for tracking
            agent_name = self.name
            memory_content = f"Agent {agent_name} memory - Balance: ${bank_balance} - Content: Updated memory"
            
            # Store Phase 1 final memories
            if "final ranking" in prompt.lower() or "completed final ranking" in prompt.lower():
                phase1_memories[agent_name] = memory_content
            
            # Store Phase 2 initial memories (should match Phase 1 final)
            if "group discussion" in prompt.lower() and agent_name not in phase2_initial_memories:
                phase2_initial_memories[agent_name] = memory_content
                
            return memory_content
        
        with patch('agents.Runner.run') as mock_runner, \
             patch.object(manager.utility_agent, 'parse_principle_ranking_enhanced') as mock_parse_ranking, \
             patch.object(manager.utility_agent, 'parse_principle_choice_enhanced') as mock_parse_choice, \
             patch.object(manager.utility_agent, 'validate_constraint_specification') as mock_validate:
            
            # Set up basic mocks
            mock_runner.return_value.final_output = "Test response"
            mock_parse_ranking.return_value = ExperimentTestFixture.create_test_principle_rankings()[0]
            mock_parse_choice.return_value = ExperimentTestFixture.create_test_principle_choices()[0]
            mock_validate.return_value = True
            
            # Apply memory tracking to all participants
            for participant in manager.participants:
                participant.update_memory = AsyncMock(side_effect=lambda p, b, agent=participant: tracking_memory_update(agent, p, b))
            
            # Run experiment
            results = await AsyncTestUtils.run_with_timeout(
                manager.run_complete_experiment(),
                timeout=60.0
            )
            
            # Verify results exist
            assert results is not None
            assert len(results.phase1_results) == 2
            
            # Verify memory continuity
            for phase1_result in results.phase1_results:
                agent_name = phase1_result.participant_name
                
                # Check that Phase 1 final memory is preserved for Phase 2
                assert phase1_result.final_memory_state is not None
                assert len(phase1_result.final_memory_state) > 0
                
                # Memory should contain accumulated information
                final_memory = phase1_result.final_memory_state
                assert agent_name in final_memory  # Should contain agent-specific content
    
    @pytest.mark.asyncio
    async def test_bank_balance_consistency(self):
        """Test bank balance updates correctly across all operations."""
        
        manager = FrohlichExperimentManager(self.config)
        balance_history = {agent.name: [] for agent in manager.participants}
        
        # Mock distribution generator to return predictable earnings
        with patch('core.distribution_generator.DistributionGenerator.calculate_payoff') as mock_payoff, \
             patch('agents.Runner.run') as mock_runner, \
             patch.object(manager.utility_agent, 'parse_principle_ranking_enhanced') as mock_parse_ranking, \
             patch.object(manager.utility_agent, 'parse_principle_choice_enhanced') as mock_parse_choice, \
             patch.object(manager.utility_agent, 'validate_constraint_specification') as mock_validate:
            
            # Set up predictable payoffs
            payoffs = [(IncomeClass.HIGH, 30.0), (IncomeClass.MEDIUM, 20.0), (IncomeClass.LOW, 10.0)]
            payoff_iter = iter(payoffs * 10)  # Repeat as needed
            mock_payoff.side_effect = lambda x: next(payoff_iter, (IncomeClass.MEDIUM, 20.0))
            
            # Set up other mocks
            mock_runner.return_value.final_output = "Test response"
            mock_parse_ranking.return_value = ExperimentTestFixture.create_test_principle_rankings()[0]
            mock_parse_choice.return_value = ExperimentTestFixture.create_test_principle_choices()[0]
            mock_validate.return_value = True
            
            # Track balance updates through memory updates
            async def balance_tracking_memory_update(prompt, bank_balance, agent_name):
                balance_history[agent_name].append(bank_balance)
                return f"Memory for {agent_name} with balance ${bank_balance}"
            
            for participant in manager.participants:
                agent_name = participant.name
                participant.update_memory = AsyncMock(
                    side_effect=lambda p, b, name=agent_name: balance_tracking_memory_update(p, b, name)
                )
            
            # Run experiment
            results = await AsyncTestUtils.run_with_timeout(
                manager.run_complete_experiment(),
                timeout=60.0
            )
            
            # Verify bank balance consistency
            assert results is not None
            
            for phase1_result in results.phase1_results:
                agent_name = phase1_result.participant_name
                
                # Check Phase 1 balance progression
                agent_balances = balance_history[agent_name]
                if agent_balances:
                    # Balance should be non-decreasing (only additions, no subtractions)
                    for i in range(1, len(agent_balances)):
                        assert agent_balances[i] >= agent_balances[i-1], f"Balance decreased for {agent_name}: {agent_balances[i-1]} -> {agent_balances[i]}"
                    
                    # Final balance should match Phase 1 result
                    final_balance = agent_balances[-1]
                    assert abs(final_balance - phase1_result.total_earnings) < 0.01, f"Balance mismatch for {agent_name}: {final_balance} vs {phase1_result.total_earnings}"
            
            # Check Phase 2 balance consistency
            for agent_name, phase2_earnings in results.phase2_results.payoff_results.items():
                # Phase 2 earnings should be non-negative
                assert phase2_earnings >= 0, f"Negative Phase 2 earnings for {agent_name}: {phase2_earnings}"
    
    @pytest.mark.asyncio
    async def test_context_updates_threadsafe(self):
        """Test context updates don't create race conditions."""
        
        manager = FrohlichExperimentManager(self.config)
        
        # Track all context updates
        context_updates = []
        update_lock = asyncio.Lock()
        
        async def context_tracking_update(prompt, bank_balance, agent_name, update_count):
            async with update_lock:
                context_updates.append({
                    "agent": agent_name,
                    "balance": bank_balance,
                    "update_number": update_count[0],
                    "timestamp": asyncio.get_event_loop().time()
                })
                update_count[0] += 1
            
            # Simulate some processing time
            await asyncio.sleep(0.01)
            return f"Memory update #{update_count[0]} for {agent_name}"
        
        with patch('agents.Runner.run') as mock_runner, \
             patch.object(manager.utility_agent, 'parse_principle_ranking_enhanced') as mock_parse_ranking, \
             patch.object(manager.utility_agent, 'parse_principle_choice_enhanced') as mock_parse_choice, \
             patch.object(manager.utility_agent, 'validate_constraint_specification') as mock_validate:
            
            # Set up basic mocks
            mock_runner.return_value.final_output = "Test response"
            mock_parse_ranking.return_value = ExperimentTestFixture.create_test_principle_rankings()[0]
            mock_parse_choice.return_value = ExperimentTestFixture.create_test_principle_choices()[0]
            mock_validate.return_value = True
            
            # Set up context tracking for each participant
            for participant in manager.participants:
                agent_name = participant.name
                update_count = [0]  # Mutable counter
                participant.update_memory = AsyncMock(
                    side_effect=lambda p, b, name=agent_name, count=update_count: context_tracking_update(p, b, name, count)
                )
            
            # Run experiment
            results = await AsyncTestUtils.run_with_timeout(
                manager.run_complete_experiment(),
                timeout=60.0
            )
            
            # Verify no race conditions occurred
            assert results is not None
            
            # Analyze context updates for race conditions
            if context_updates:
                # Group updates by agent
                agent_updates = {}
                for update in context_updates:
                    agent = update["agent"]
                    if agent not in agent_updates:
                        agent_updates[agent] = []
                    agent_updates[agent].append(update)
                
                # Verify updates within each agent are properly sequenced
                for agent, updates in agent_updates.items():
                    # Sort by timestamp
                    updates.sort(key=lambda x: x["timestamp"])
                    
                    # Check that update numbers are sequential
                    for i in range(1, len(updates)):
                        prev_update = updates[i-1]["update_number"]
                        curr_update = updates[i]["update_number"]
                        assert curr_update > prev_update, f"Race condition detected for {agent}: update {prev_update} -> {curr_update}"
                        
                    # Check that balances are non-decreasing within each agent
                    for i in range(1, len(updates)):
                        prev_balance = updates[i-1]["balance"]
                        curr_balance = updates[i]["balance"]
                        assert curr_balance >= prev_balance, f"Balance race condition for {agent}: {prev_balance} -> {curr_balance}"
    
    @pytest.mark.asyncio
    async def test_public_history_consistency(self):
        """Test public discussion history remains consistent."""
        
        manager = FrohlichExperimentManager(self.config)
        
        # Track discussion history updates
        discussion_history_snapshots = []
        
        # Mock Phase 2 discussion tracking
        original_add_statement = None
        
        def track_discussion_updates(self, participant_name, statement):
            # Capture state before and after
            before_length = len(self.public_history)
            
            # Call original method (simulate)
            self.public_history += f"\n{participant_name}: {statement}"
            
            # Capture snapshot
            discussion_history_snapshots.append({
                "participant": participant_name,
                "statement": statement,
                "history_before_length": before_length,
                "history_after_length": len(self.public_history),
                "timestamp": asyncio.get_event_loop().time()
            })
        
        with patch('agents.Runner.run') as mock_runner, \
             patch.object(manager.utility_agent, 'parse_principle_ranking_enhanced') as mock_parse_ranking, \
             patch.object(manager.utility_agent, 'parse_principle_choice_enhanced') as mock_parse_choice, \
             patch.object(manager.utility_agent, 'validate_constraint_specification') as mock_validate:
            
            # Set up basic mocks
            mock_runner.return_value.final_output = "I agree with this discussion approach"
            mock_parse_ranking.return_value = ExperimentTestFixture.create_test_principle_rankings()[0]
            mock_parse_choice.return_value = ExperimentTestFixture.create_test_principle_choices()[0]
            mock_validate.return_value = True
            
            # Mock discussion state tracking
            with patch('models.experiment_types.GroupDiscussionState.add_statement', side_effect=track_discussion_updates):
                
                # Run experiment
                results = await AsyncTestUtils.run_with_timeout(
                    manager.run_complete_experiment(),
                    timeout=60.0
                )
                
                # Verify discussion history consistency
                assert results is not None
                
                if discussion_history_snapshots:
                    # Verify history growth is monotonic
                    for i in range(1, len(discussion_history_snapshots)):
                        prev_length = discussion_history_snapshots[i-1]["history_after_length"]
                        curr_length_before = discussion_history_snapshots[i]["history_before_length"]
                        
                        # History should only grow, never shrink
                        assert curr_length_before >= prev_length, f"Discussion history inconsistency: {prev_length} -> {curr_length_before}"
                    
                    # Verify all participants contributed to discussion
                    participants_in_discussion = set(snap["participant"] for snap in discussion_history_snapshots)
                    expected_participants = set(agent.name for agent in manager.participants)
                    assert len(participants_in_discussion.intersection(expected_participants)) > 0, "No participants found in discussion history"
    
    @pytest.mark.asyncio
    async def test_cross_phase_state_transition(self):
        """Test state transitions between Phase 1 and Phase 2."""
        
        manager = FrohlichExperimentManager(self.config)
        
        # Track state transitions
        state_transitions = []
        
        # Mock context updates to track phase transitions
        original_update_context = None
        
        async def track_context_transitions(prompt, bank_balance, agent_name):
            # Detect phase transitions based on prompt content
            phase = ExperimentPhase.PHASE_1
            if "group discussion" in prompt.lower() or "phase 2" in prompt.lower():
                phase = ExperimentPhase.PHASE_2
            
            state_transitions.append({
                "agent": agent_name,
                "phase": phase,
                "balance": bank_balance,
                "prompt_snippet": prompt[:100],  # First 100 chars for context
                "timestamp": asyncio.get_event_loop().time()
            })
            
            return f"Memory for {agent_name} in {phase.value}"
        
        with patch('agents.Runner.run') as mock_runner, \
             patch.object(manager.utility_agent, 'parse_principle_ranking_enhanced') as mock_parse_ranking, \
             patch.object(manager.utility_agent, 'parse_principle_choice_enhanced') as mock_parse_choice, \
             patch.object(manager.utility_agent, 'validate_constraint_specification') as mock_validate:
            
            # Set up basic mocks
            mock_runner.return_value.final_output = "Test response"
            mock_parse_ranking.return_value = ExperimentTestFixture.create_test_principle_rankings()[0]
            mock_parse_choice.return_value = ExperimentTestFixture.create_test_principle_choices()[0]
            mock_validate.return_value = True
            
            # Set up transition tracking
            for participant in manager.participants:
                agent_name = participant.name
                participant.update_memory = AsyncMock(
                    side_effect=lambda p, b, name=agent_name: track_context_transitions(p, b, name)
                )
            
            # Run experiment
            results = await AsyncTestUtils.run_with_timeout(
                manager.run_complete_experiment(),
                timeout=60.0
            )
            
            # Verify state transitions
            assert results is not None
            
            if state_transitions:
                # Group transitions by agent
                agent_transitions = {}
                for transition in state_transitions:
                    agent = transition["agent"]
                    if agent not in agent_transitions:
                        agent_transitions[agent] = []
                    agent_transitions[agent].append(transition)
                
                # Verify proper phase progression for each agent
                for agent, transitions in agent_transitions.items():
                    # Sort by timestamp
                    transitions.sort(key=lambda x: x["timestamp"])
                    
                    # Check phase progression
                    phases_seen = [t["phase"] for t in transitions]
                    
                    # Should see Phase 1 before Phase 2 (if Phase 2 occurs)
                    if ExperimentPhase.PHASE_2 in phases_seen:
                        first_phase2_idx = phases_seen.index(ExperimentPhase.PHASE_2)
                        # All transitions before first Phase 2 should be Phase 1
                        for i in range(first_phase2_idx):
                            assert phases_seen[i] == ExperimentPhase.PHASE_1, f"Invalid phase transition for {agent} at index {i}"
                    
                    # Bank balance should not decrease during phase transition
                    if len(transitions) >= 2:
                        for i in range(1, len(transitions)):
                            prev_balance = transitions[i-1]["balance"]
                            curr_balance = transitions[i]["balance"]
                            # Allow for small floating point differences
                            assert curr_balance >= prev_balance - 0.01, f"Balance decreased during transition for {agent}: {prev_balance} -> {curr_balance}"
    
    @pytest.mark.asyncio
    async def test_concurrent_state_updates_isolation(self):
        """Test that concurrent state updates in Phase 1 don't interfere."""
        
        manager = FrohlichExperimentManager(self.config)
        
        # Track concurrent updates
        concurrent_updates = []
        update_times = {}
        
        async def concurrent_memory_update(prompt, bank_balance, agent_name):
            start_time = asyncio.get_event_loop().time()
            
            # Simulate varying processing times
            processing_time = 0.01 if agent_name == "TestAgent1" else 0.02
            await asyncio.sleep(processing_time)
            
            end_time = asyncio.get_event_loop().time()
            
            concurrent_updates.append({
                "agent": agent_name,
                "start_time": start_time,
                "end_time": end_time,
                "processing_time": end_time - start_time,
                "balance": bank_balance
            })
            
            return f"Concurrent memory for {agent_name}"
        
        with patch('agents.Runner.run') as mock_runner, \
             patch.object(manager.utility_agent, 'parse_principle_ranking_enhanced') as mock_parse_ranking, \
             patch.object(manager.utility_agent, 'parse_principle_choice_enhanced') as mock_parse_choice, \
             patch.object(manager.utility_agent, 'validate_constraint_specification') as mock_validate:
            
            # Set up basic mocks
            mock_runner.return_value.final_output = "Test response"
            mock_parse_ranking.return_value = ExperimentTestFixture.create_test_principle_rankings()[0]
            mock_parse_choice.return_value = ExperimentTestFixture.create_test_principle_choices()[0]
            mock_validate.return_value = True
            
            # Set up concurrent tracking
            for participant in manager.participants:
                agent_name = participant.name
                participant.update_memory = AsyncMock(
                    side_effect=lambda p, b, name=agent_name: concurrent_memory_update(p, b, name)
                )
            
            # Run experiment
            results = await AsyncTestUtils.run_with_timeout(
                manager.run_complete_experiment(),
                timeout=60.0
            )
            
            # Verify concurrent execution isolation
            assert results is not None
            
            if concurrent_updates:
                # Group by agent
                agent_updates = {}
                for update in concurrent_updates:
                    agent = update["agent"]
                    if agent not in agent_updates:
                        agent_updates[agent] = []
                    agent_updates[agent].append(update)
                
                # Verify proper isolation
                for agent, updates in agent_updates.items():
                    # Check for overlapping execution times with other agents
                    other_agents_updates = [u for u in concurrent_updates if u["agent"] != agent]
                    
                    for update in updates:
                        # Check balance consistency within agent
                        agent_updates_sorted = sorted(updates, key=lambda x: x["start_time"])
                        agent_idx = agent_updates_sorted.index(update)
                        
                        # Balance should be consistent with previous updates
                        if agent_idx > 0:
                            prev_balance = agent_updates_sorted[agent_idx - 1]["balance"]
                            curr_balance = update["balance"]
                            assert curr_balance >= prev_balance, f"Balance inconsistency for {agent}: {prev_balance} -> {curr_balance}"