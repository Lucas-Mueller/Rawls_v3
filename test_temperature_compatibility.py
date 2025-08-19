#!/usr/bin/env python3
"""
Test script for dynamic temperature compatibility detection.

This script tests the new dynamic temperature detection system with different models,
including the gpt-5-nano-2025-08-07 model that doesn't support temperature.
"""

import asyncio
import logging
import sys
from typing import List

# Setup logging to see the dynamic detection in action
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from utils.dynamic_model_capabilities import (
    test_temperature_support, 
    batch_test_model_temperatures,
    get_temperature_cache_info,
    clear_temperature_cache
)
from utils.model_provider import create_model_config_with_temperature_detection
from config import AgentConfiguration
from experiment_agents.participant_agent import ParticipantAgent, create_participant_agents_with_batch_testing
from experiment_agents.utility_agent import UtilityAgent

async def test_individual_model_detection():
    """Test individual model temperature detection."""
    print("\n=== Individual Model Temperature Detection Tests ===")
    
    # Test models with different temperature support characteristics
    test_models = [
        "gpt-4.1",  # Should support temperature
        "gpt-4.1-mini",  # Should support temperature  
        "gpt-5-nano-2025-08-07",  # Does NOT support temperature (new test model)
        "gpt-4.1-nano",  # Does NOT support temperature (from config)
    ]
    
    for model in test_models:
        print(f"\n🧪 Testing model: {model}")
        try:
            supports_temp, reason, exception = await test_temperature_support(model)
            status = "✅ SUPPORTS" if supports_temp else "❌ NO SUPPORT"
            print(f"   {status}: {reason}")
            if exception:
                print(f"   Exception: {exception}")
        except Exception as e:
            print(f"   💥 TEST FAILED: {e}")

async def test_batch_detection():
    """Test batch model temperature detection."""
    print("\n=== Batch Model Temperature Detection Test ===")
    
    models = [
        "gpt-4.1",
        "gpt-4.1-mini", 
        "gpt-5-nano-2025-08-07",
        "gpt-4.1-nano"
    ]
    
    print(f"🚀 Batch testing {len(models)} models...")
    results = await batch_test_model_temperatures(models)
    
    print("\n📊 Batch Test Results:")
    for model, info in results.items():
        status = "✅ SUPPORTS" if info["supports_temperature"] else "❌ NO SUPPORT" 
        print(f"   {model}: {status}")
        print(f"      Reason: {info['test_reason']}")
        print(f"      Method: {info['detection_method']}")

async def test_agent_creation():
    """Test agent creation with temperature detection."""
    print("\n=== Agent Creation with Temperature Detection ===")
    
    # Test agent configurations
    configs = [
        AgentConfiguration(
            name="TempSupportedAgent",
            personality="Test agent with temperature support",
            model="gpt-4.1-mini",
            temperature=0.5,
            memory_character_limit=1000,
            reasoning_enabled=True
        ),
        AgentConfiguration(
            name="NoTempSupportAgent", 
            personality="Test agent without temperature support",
            model="gpt-5-nano-2025-08-07",
            temperature=0.8,  # This should trigger a warning
            memory_character_limit=1000,
            reasoning_enabled=True
        )
    ]
    
    print("🏗️  Creating individual agents...")
    agents = []
    for config in configs:
        print(f"   Creating agent: {config.name} (model: {config.model})")
        try:
            agent = ParticipantAgent(config)
            agents.append(agent)
            
            # Check temperature info
            temp_info = agent.temperature_info
            temp_status = "✅ ACTIVE" if temp_info["supports_temperature"] else "❌ N/A"
            print(f"      Temperature: {temp_status} (requested: {temp_info['requested_temperature']})")
            print(f"      Detection: {temp_info['detection_method']} - {temp_info['test_reason']}")
            
        except Exception as e:
            print(f"      💥 FAILED: {e}")
    
    print(f"\n✅ Successfully created {len(agents)} agents")

async def test_batch_agent_creation():
    """Test batch agent creation with pre-testing."""
    print("\n=== Batch Agent Creation Test ===")
    
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
            model="gpt-5-nano-2025-08-07", 
            temperature=0.7,
            memory_character_limit=1000,
            reasoning_enabled=True
        ),
        AgentConfiguration(
            name="Agent3",
            personality="Third test agent",
            model="gpt-4.1-mini",  # Same model as Agent1 - should use cached result
            temperature=0.9,
            memory_character_limit=1000,
            reasoning_enabled=True
        )
    ]
    
    print("🚀 Creating agents with batch temperature testing...")
    try:
        agents = await create_participant_agents_with_batch_testing(configs)
        print(f"✅ Successfully created {len(agents)} agents with batch testing")
        
        for agent in agents:
            temp_info = agent.temperature_info
            temp_status = "✅ ACTIVE" if temp_info["supports_temperature"] else "❌ N/A"
            print(f"   {agent.config.name}: Temperature {temp_status} (detection: {temp_info['detection_method']})")
            
    except Exception as e:
        print(f"💥 Batch agent creation failed: {e}")

async def test_utility_agent():
    """Test utility agent creation with temperature detection."""
    print("\n=== Utility Agent Temperature Detection ===")
    
    models_to_test = [
        "gpt-4.1-mini",  # Should support temperature
        "gpt-5-nano-2025-08-07",  # Should NOT support temperature
    ]
    
    for model in models_to_test:
        print(f"\n🔧 Testing utility agent with model: {model}")
        try:
            utility_agent = UtilityAgent(utility_model=model)
            temp_info = utility_agent.temperature_info
            temp_status = "✅ ACTIVE" if temp_info["supports_temperature"] else "❌ N/A"
            print(f"   Temperature: {temp_status}")
            print(f"   Detection: {temp_info['detection_method']} - {temp_info['test_reason']}")
        except Exception as e:
            print(f"   💥 FAILED: {e}")

def show_cache_info():
    """Show temperature cache information."""
    print("\n=== Temperature Cache Information ===")
    cache_info = get_temperature_cache_info()
    
    print(f"📊 Cached models: {cache_info['cached_models']}")
    print("✅ Models supporting temperature:")
    for model in cache_info['supported_models']:
        print(f"   - {model}")
    print("❌ Models NOT supporting temperature:")
    for model in cache_info['unsupported_models']:
        print(f"   - {model}")

async def main():
    """Run all temperature compatibility tests."""
    print("🧪 Dynamic Temperature Compatibility Detection Tests")
    print("=" * 60)
    
    # Clear cache to start fresh
    clear_temperature_cache()
    
    try:
        # Run individual tests
        await test_individual_model_detection()
        await test_batch_detection()
        
        # Show cache after batch testing
        show_cache_info()
        
        # Test agent creation
        await test_agent_creation()
        await test_batch_agent_creation()
        await test_utility_agent()
        
        # Final cache info
        show_cache_info()
        
        print("\n🎉 All tests completed successfully!")
        print("✨ Dynamic temperature detection is working correctly!")
        
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())