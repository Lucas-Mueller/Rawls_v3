"""
Utilities for async testing patterns in the Frohlich Experiment.
Provides helpers for timeouts, mock agents, delays, and error injection.
"""
import asyncio
import random
from typing import List, Dict, Any, Optional, Callable
from unittest.mock import AsyncMock, Mock
from contextlib import asynccontextmanager

from experiment_agents import ParticipantAgent
from utils.error_handling import ExperimentError, ExperimentErrorCategory, ErrorSeverity


class AsyncTestUtils:
    """Utilities for async testing patterns."""
    
    @staticmethod
    async def run_with_timeout(coro, timeout: float = 30.0):
        """Run coroutine with timeout for hanging tests."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise AssertionError(f"Operation timed out after {timeout} seconds")
    
    @staticmethod
    def mock_agent_responses(agent_name: str, responses: List[str]) -> AsyncMock:
        """Create mock agent that returns predetermined responses."""
        response_iter = iter(responses)
        
        async def mock_response(*args, **kwargs):
            try:
                response = next(response_iter)
                mock_result = Mock()
                mock_result.final_output = response
                return mock_result
            except StopIteration:
                # Return default response if we run out
                mock_result = Mock()
                mock_result.final_output = f"Default response from {agent_name}"
                return mock_result
        
        return AsyncMock(side_effect=mock_response)
    
    @staticmethod
    async def simulate_agent_delay(min_delay: float = 0.1, max_delay: float = 0.5):
        """Simulate realistic agent response delays."""
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
    
    @staticmethod
    def create_error_injecting_mock(
        error_type: type, 
        error_frequency: float = 0.3,
        success_responses: Optional[List[str]] = None
    ) -> AsyncMock:
        """Create mock that intermittently raises errors."""
        if success_responses is None:
            success_responses = ["Success response"]
        
        response_iter = iter(success_responses * 100)  # Repeat responses
        
        async def mock_with_errors(*args, **kwargs):
            if random.random() < error_frequency:
                raise error_type("Simulated error")
            
            try:
                response = next(response_iter)
                mock_result = Mock()
                mock_result.final_output = response
                return mock_result
            except StopIteration:
                mock_result = Mock()
                mock_result.final_output = "Default success response"
                return mock_result
        
        return AsyncMock(side_effect=mock_with_errors)
    
    @staticmethod
    @asynccontextmanager
    async def parallel_context():
        """Context manager for running multiple async operations in parallel."""
        tasks = []
        
        class ParallelRunner:
            def add_task(self, coro):
                task = asyncio.create_task(coro)
                tasks.append(task)
                return task
            
            async def wait_all(self):
                return await asyncio.gather(*tasks, return_exceptions=True)
        
        runner = ParallelRunner()
        try:
            yield runner
        finally:
            # Cleanup any remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
    
    @staticmethod
    def create_mock_participant_agent(
        name: str, 
        responses: Optional[List[str]] = None,
        memory_responses: Optional[List[str]] = None,
        error_injection: Optional[Dict[str, Any]] = None
    ) -> ParticipantAgent:
        """Create comprehensive mock participant agent."""
        mock_agent = Mock(spec=ParticipantAgent)
        mock_agent.name = name
        
        # Set up config
        from config import AgentConfiguration
        mock_agent.config = AgentConfiguration(
            name=name,
            personality="Test personality",
            model="o3-mini",
            temperature=0.7,
            memory_character_limit=50000,
            reasoning_enabled=True
        )
        
        # Set up responses
        if responses is None:
            responses = [f"Default response from {name}"]
        
        if memory_responses is None:
            memory_responses = [f"Updated memory from {name}"]
        
        # Create response mocks
        if error_injection:
            mock_agent.agent = AsyncTestUtils.create_error_injecting_mock(
                error_injection.get("error_type", Exception),
                error_injection.get("frequency", 0.1),
                responses
            )
            mock_agent.update_memory = AsyncTestUtils.create_error_injecting_mock(
                error_injection.get("memory_error_type", Exception),
                error_injection.get("memory_frequency", 0.1),
                memory_responses
            )
        else:
            mock_agent.agent = AsyncTestUtils.mock_agent_responses(name, responses)
            mock_agent.update_memory = AsyncTestUtils.mock_agent_responses(name, memory_responses)
        
        return mock_agent
    
    @staticmethod
    async def wait_for_condition(
        condition: Callable[[], bool], 
        timeout: float = 5.0, 
        check_interval: float = 0.1
    ) -> bool:
        """Wait for a condition to become true with timeout."""
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            if condition():
                return True
            await asyncio.sleep(check_interval)
        
        return False
    
    @staticmethod
    def create_controlled_experiment_runner(
        agent_responses: Dict[str, List[str]],
        error_scenarios: Optional[Dict[str, Dict[str, Any]]] = None
    ):
        """Create a controlled experiment runner with predetermined responses and errors."""
        
        class ControlledRunner:
            def __init__(self):
                self.agent_responses = agent_responses
                self.error_scenarios = error_scenarios or {}
                self.call_counts = {agent: 0 for agent in agent_responses.keys()}
            
            async def run_agent_interaction(self, agent_name: str, prompt: str) -> str:
                """Simulate agent interaction with controlled responses."""
                call_count = self.call_counts[agent_name]
                responses = self.agent_responses.get(agent_name, ["Default response"])
                
                # Check for error injection
                if agent_name in self.error_scenarios:
                    error_config = self.error_scenarios[agent_name]
                    if call_count in error_config.get("error_on_calls", []):
                        error_type = error_config.get("error_type", Exception)
                        raise error_type(f"Injected error for {agent_name} on call {call_count}")
                
                # Simulate delay
                await AsyncTestUtils.simulate_agent_delay()
                
                # Return predetermined response
                if call_count < len(responses):
                    response = responses[call_count]
                else:
                    response = responses[-1] if responses else "Default response"
                
                self.call_counts[agent_name] += 1
                return response
        
        return ControlledRunner()


class ErrorInjectionUtils:
    """Utilities for error injection testing."""
    
    @staticmethod
    def create_memory_error_scenario() -> Dict[str, Any]:
        """Create scenario that triggers memory limit errors."""
        return {
            "error_type": MemoryError,
            "frequency": 0.8,
            "error_on_calls": [1, 3],  # Fail on specific calls
            "memory_error_type": MemoryError,
            "memory_frequency": 0.5
        }
    
    @staticmethod
    def create_communication_error_scenario() -> Dict[str, Any]:
        """Create scenario that triggers agent communication errors."""
        return {
            "error_type": ConnectionError,
            "frequency": 0.4,
            "error_on_calls": [2, 4, 6],
            "memory_error_type": TimeoutError,
            "memory_frequency": 0.2
        }
    
    @staticmethod
    def create_validation_error_scenario() -> Dict[str, Any]:
        """Create scenario that triggers validation errors."""
        return {
            "error_type": ValueError,
            "frequency": 0.6,
            "error_on_calls": [1, 5],
            "memory_error_type": ValueError,
            "memory_frequency": 0.3
        }
    
    @staticmethod
    def create_intermittent_api_failure() -> Dict[str, Any]:
        """Create scenario simulating intermittent API failures."""
        return {
            "error_type": ConnectionError,
            "frequency": 0.25,  # 25% failure rate
            "error_on_calls": [],  # Random failures, not specific calls
            "recovery_after": 3  # Recover after 3 attempts
        }


class TestDataGenerators:
    """Generate test data for various scenarios."""
    
    @staticmethod
    def generate_ranking_responses(agent_name: str, consistency_level: str = "high") -> List[str]:
        """Generate ranking responses with varying consistency."""
        base_rankings = {
            "high": [
                "1. Maximizing the floor income, 2. Maximizing average with floor constraint, 3. Maximizing average income, 4. Maximizing average with range constraint. Overall certainty: very_sure",
                "1. Maximizing the floor income, 2. Maximizing average with floor constraint, 3. Maximizing average income, 4. Maximizing average with range constraint. Overall certainty: very_sure",
                "1. Maximizing the floor income, 2. Maximizing average with floor constraint, 3. Maximizing average income, 4. Maximizing average with range constraint. Overall certainty: very_sure"
            ],
            "medium": [
                "1. Maximizing the floor income, 2. Maximizing average with floor constraint, 3. Maximizing average income, 4. Maximizing average with range constraint. Overall certainty: sure",
                "1. Maximizing the floor income, 2. Maximizing average income, 3. Maximizing average with floor constraint, 4. Maximizing average with range constraint. Overall certainty: sure",
                "1. Maximizing average with floor constraint, 2. Maximizing the floor income, 3. Maximizing average income, 4. Maximizing average with range constraint. Overall certainty: unsure"
            ],
            "low": [
                "1. Maximizing the floor income, 2. Maximizing average income, 3. Maximizing average with range constraint, 4. Maximizing average with floor constraint. Overall certainty: unsure",
                "1. Maximizing average income, 2. Maximizing the floor income, 3. Maximizing average with floor constraint, 4. Maximizing average with range constraint. Overall certainty: no_opinion",
                "1. Maximizing average with range constraint, 2. Maximizing average income, 3. Maximizing the floor income, 4. Maximizing average with floor constraint. Overall certainty: very_unsure"
            ]
        }
        
        return base_rankings.get(consistency_level, base_rankings["medium"])
    
    @staticmethod
    def generate_principle_choice_responses(agent_name: str, preference: str = "floor") -> List[str]:
        """Generate principle choice responses based on preference."""
        preferences = {
            "floor": [
                "I choose principle a (maximizing the floor). I am sure about this choice.",
                "I choose principle a (maximizing the floor). I am very sure about this choice.",
                "I choose principle c (maximizing average with floor constraint) with a constraint of $15,000. I am sure about this choice.",
                "I choose principle a (maximizing the floor). I am very sure about this choice."
            ],
            "average": [
                "I choose principle b (maximizing the average). I am sure about this choice.",
                "I choose principle b (maximizing the average). I am very sure about this choice.",
                "I choose principle d (maximizing average with range constraint) with a constraint of $20,000. I am sure about this choice.",
                "I choose principle b (maximizing the average). I am very sure about this choice."
            ],
            "mixed": [
                "I choose principle a (maximizing the floor). I am sure about this choice.",
                "I choose principle b (maximizing the average). I am sure about this choice.",
                "I choose principle c (maximizing average with floor constraint) with a constraint of $16,000. I am unsure about this choice.",
                "I choose principle d (maximizing average with range constraint) with a constraint of $18,000. I am sure about this choice."
            ]
        }
        
        return preferences.get(preference, preferences["mixed"])
    
    @staticmethod
    def generate_discussion_responses(agent_name: str, stance: str = "cooperative") -> List[str]:
        """Generate discussion responses based on stance."""
        stances = {
            "cooperative": [
                f"I believe we should work together to find the best principle. My experience in Phase 1 showed that {agent_name.lower()} values are important.",
                f"I'm willing to listen to others' perspectives and find common ground.",
                f"Based on our discussion, I think we can reach consensus. I propose we vote on the principle we've been discussing."
            ],
            "competitive": [
                f"My analysis clearly shows that my preferred principle is superior. The data supports this conclusion.",
                f"While I understand others have different views, I maintain that my approach is most logical.",
                f"I'm willing to vote, but I believe my principle choice is clearly the best option."
            ],
            "flexible": [
                f"I see merit in multiple approaches. Perhaps we can find a compromise that incorporates the best aspects.",
                f"After hearing the discussion, I'm willing to adjust my position for the group's benefit.",
                f"I think we're close to agreement. Let's vote on the compromise principle we've discussed."
            ]
        }
        
        return stances.get(stance, stances["cooperative"])