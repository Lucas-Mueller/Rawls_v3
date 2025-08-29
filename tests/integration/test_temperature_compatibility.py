#!/usr/bin/env python3
"""
Integration tests for dynamic temperature compatibility detection.

Tests the dynamic temperature detection system with different models,
including models that don't support temperature parameters.
"""

import asyncio
import pytest
import logging
from typing import List

from utils.dynamic_model_capabilities import (
    test_temperature_support, 
    batch_test_model_temperatures,
    get_temperature_cache_info,
    clear_temperature_cache
)
from utils.model_provider import create_model_config_with_temperature_detection
from config import AgentConfiguration
from experiment_agents.participant_agent import ParticipantAgent, create_participant_agents_with_dynamic_temperature
from experiment_agents.utility_agent import UtilityAgent


@pytest.mark.integration
@pytest.mark.asyncio
class TestTemperatureCompatibility:
    """Integration tests for temperature compatibility detection."""
    
    def setup_method(self):
        """Clear temperature cache before each test."""
        clear_temperature_cache()
    
    async def test_individual_model_temperature_detection(self):
        """Test individual model temperature detection."""
        test_models = [
            "gpt-4.1-mini",  # Should support temperature  
            "gpt-4.1-nano",  # Does NOT support temperature (from config)
        ]
        
        results = {}
        for model in test_models:
            try:
                supports_temp, reason, exception = await test_temperature_support(model)
                results[model] = {
                    'supports_temperature': supports_temp,
                    'reason': reason,
                    'exception': str(exception) if exception else None
                }
            except Exception as e:
                results[model] = {
                    'supports_temperature': False,
                    'reason': f"Test failed: {str(e)}",
                    'exception': str(e)
                }
        
        # Verify we got results for all models
        assert len(results) == len(test_models), "Should have results for all test models"
        
        # Verify results structure
        for model, result in results.items():
            assert 'supports_temperature' in result, f"Result for {model} should include supports_temperature"
            assert 'reason' in result, f"Result for {model} should include reason"
            assert isinstance(result['supports_temperature'], bool), f"supports_temperature should be bool for {model}"

    async def test_batch_temperature_detection(self):
        """Test batch model temperature detection."""
        models = [
            "gpt-4.1-mini", 
            "gpt-4.1-nano"
        ]
        
        results = await batch_test_model_temperatures(models)
        
        # Verify batch results
        assert len(results) == len(models), "Should have results for all models in batch"
        
        for model in models:
            assert model in results, f"Should have result for {model}"
            result = results[model]
            assert 'supports_temperature' in result, f"Batch result for {model} should include supports_temperature"
            assert 'test_reason' in result, f"Batch result for {model} should include test_reason"
            assert 'detection_method' in result, f"Batch result for {model} should include detection_method"

    async def test_agent_creation_with_temperature_detection(self):
        """Test agent creation with temperature detection."""
        configs = [
            AgentConfiguration(
                name="TempSupportedAgent",
                personality="Test agent with temperature support",
                model="gpt-4.1-mini",
                temperature=0.5,
                memory_character_limit=1000,
                reasoning_enabled=True
            ),
        ]
        
        agents = []
        for config in configs:
            agent = ParticipantAgent(config)
            agents.append(agent)
            
            # Verify temperature info is available
            temp_info = agent.temperature_info
            assert 'supports_temperature' in temp_info, f"Agent {config.name} should have temperature support info"
            assert 'requested_temperature' in temp_info, f"Agent {config.name} should have requested temperature info"
            assert 'detection_method' in temp_info, f"Agent {config.name} should have detection method info"
        
        assert len(agents) == len(configs), "Should create all requested agents"

    async def test_batch_agent_creation_optimization(self):
        """Test batch agent creation with pre-testing optimization."""
        configs = [
            AgentConfiguration(
                name="Agent1",
                personality="First test agent",
                model="gpt-4.1-mini",
                temperature=0.3,
                memory_character_limit=1000,
                reasoning_enabled=True
            ),
            AgentConfiguration(
                name="Agent2",
                personality="Second test agent", 
                model="gpt-4.1-mini",  # Same model - should use cached result
                temperature=0.7,
                memory_character_limit=1000,
                reasoning_enabled=True
            )
        ]
        
        agents = await create_participant_agents_with_dynamic_temperature(configs)
        
        assert len(agents) == len(configs), "Should create all agents with batch testing"
        
        # Verify all agents have temperature info
        for agent in agents:
            temp_info = agent.temperature_info
            assert 'supports_temperature' in temp_info, f"Agent {agent.config.name} should have temperature info"
            assert 'detection_method' in temp_info, f"Agent {agent.config.name} should have detection method"

    async def test_utility_agent_temperature_detection(self):
        """Test utility agent creation with temperature detection."""
        models_to_test = [
            "gpt-4.1-mini",  # Should support temperature
        ]
        
        for model in models_to_test:
            utility_agent = UtilityAgent(utility_model=model)
            temp_info = utility_agent.temperature_info
            
            # Verify temperature info structure
            assert 'supports_temperature' in temp_info, f"Utility agent with {model} should have temperature support info"
            assert 'detection_method' in temp_info, f"Utility agent with {model} should have detection method"
            assert isinstance(temp_info['supports_temperature'], bool), f"supports_temperature should be bool for {model}"

    def test_temperature_cache_functionality(self):
        """Test temperature cache information and management."""
        # Start with clear cache
        clear_temperature_cache()
        
        cache_info = get_temperature_cache_info()
        assert cache_info['cached_models'] == 0, "Cache should be empty after clear"
        assert len(cache_info['supported_models']) == 0, "No supported models should be cached initially"
        assert len(cache_info['unsupported_models']) == 0, "No unsupported models should be cached initially"

    @pytest.mark.slow
    async def test_end_to_end_temperature_workflow(self):
        """Test complete temperature detection workflow."""
        # Clear cache for clean test
        clear_temperature_cache()
        
        # Create agent config
        config = AgentConfiguration(
            name="EndToEndTestAgent",
            personality="Test agent for full workflow",
            model="gpt-4.1-mini",
            temperature=0.5,
            memory_character_limit=1000,
            reasoning_enabled=True
        )
        
        # Create agent (should trigger temperature detection)
        agent = ParticipantAgent(config)
        
        # Verify agent creation succeeded
        assert agent is not None, "Agent should be created successfully"
        assert hasattr(agent, 'temperature_info'), "Agent should have temperature info"
        
        # Verify temperature info is populated
        temp_info = agent.temperature_info
        assert temp_info['requested_temperature'] == 0.5, "Should preserve requested temperature"
        assert 'supports_temperature' in temp_info, "Should determine temperature support"
        assert 'test_reason' in temp_info, "Should provide test reason"
        
        # Verify cache is populated
        cache_info = get_temperature_cache_info()
        assert cache_info['cached_models'] > 0, "Cache should contain at least one model after agent creation"


if __name__ == "__main__":
    # Allow direct execution for debugging
    async def main():
        """Run tests directly for debugging."""
        test_instance = TestTemperatureCompatibility()
        
        print("Running Temperature Compatibility Integration Tests...")
        
        try:
            test_instance.setup_method()
            
            await test_instance.test_individual_model_temperature_detection()
            print("✅ Individual model detection test passed")
            
            await test_instance.test_batch_temperature_detection()
            print("✅ Batch temperature detection test passed")
            
            await test_instance.test_agent_creation_with_temperature_detection()
            print("✅ Agent creation test passed")
            
            await test_instance.test_batch_agent_creation_optimization()
            print("✅ Batch agent creation test passed")
            
            await test_instance.test_utility_agent_temperature_detection()
            print("✅ Utility agent test passed")
            
            test_instance.test_temperature_cache_functionality()
            print("✅ Cache functionality test passed")
            
            await test_instance.test_end_to_end_temperature_workflow()
            print("✅ End-to-end workflow test passed")
            
            print("\n🎉 All temperature compatibility tests passed!")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise
    
    asyncio.run(main())