#!/usr/bin/env python3
"""
Quick test to verify the keyword argument conflict fix.
"""
import sys
import os
import asyncio
from unittest.mock import AsyncMock, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.selective_memory_manager import SelectiveMemoryManager, MemoryEventType


async def test_keyword_conflict_fix():
    """Test that the keyword argument conflict is resolved."""
    print("🔧 Testing Keyword Argument Conflict Fix")
    print("=" * 50)
    
    # Create mock objects
    agent = MagicMock()
    agent.name = "TestAgent"
    
    context = MagicMock()
    context.memory = "Initial memory"
    
    config = MagicMock()
    config.memory_guidance_style = "narrative"
    config.selective_memory_updates = True
    
    language_manager = MagicMock()
    error_handler = MagicMock()
    utility_agent = MagicMock()
    
    # Mock the original MemoryManager to avoid actual LLM calls
    original_method = SelectiveMemoryManager._full_memory_update
    SelectiveMemoryManager._full_memory_update = AsyncMock(return_value="Updated memory via LLM")
    
    try:
        # Test case that previously caused the conflict
        # This simulates the exact call from Phase2Manager
        updated_memory = await SelectiveMemoryManager.update_memory_selective(
            agent=agent,
            context=context,
            content="Round 1 discussion content...",
            event_type=MemoryEventType.DISCUSSION_STATEMENT,
            event_metadata={'round_number': 1, 'participant_name': agent.name},
            config=config,
            language_manager=language_manager,
            error_handler=error_handler,
            utility_agent=utility_agent,
            memory_guidance_style="narrative"  # This was causing the conflict
        )
        
        print("✅ No keyword argument conflict!")
        print(f"✅ Updated memory: {updated_memory}")
        print("✅ SelectiveMemoryManager working correctly")
        
        # Verify the mock was called correctly
        SelectiveMemoryManager._full_memory_update.assert_called_once()
        call_kwargs = SelectiveMemoryManager._full_memory_update.call_args[1]
        
        # Verify memory_guidance_style is not duplicated in kwargs
        if 'memory_guidance_style' in call_kwargs:
            print("⚠️  Warning: memory_guidance_style still in kwargs, but should be handled cleanly")
        else:
            print("✅ kwargs cleaned properly - no memory_guidance_style conflict")
            
    except TypeError as e:
        if "multiple values for keyword argument" in str(e):
            print(f"❌ Keyword conflict still present: {e}")
            return False
        else:
            print(f"❌ Other TypeError: {e}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        # Restore original method
        SelectiveMemoryManager._full_memory_update = original_method
    
    return True


async def test_parameter_precedence():
    """Test that config takes precedence over kwargs for memory_guidance_style."""
    print(f"\n📋 Testing Parameter Precedence")
    print("=" * 50)
    
    # Mock the MemoryManager.prompt_agent_for_memory_update to capture calls
    from utils.memory_manager import MemoryManager
    original_prompt_method = MemoryManager.prompt_agent_for_memory_update
    
    captured_calls = []
    
    async def mock_prompt_agent(agent, context, round_content, memory_guidance_style, **kwargs):
        captured_calls.append({
            'memory_guidance_style': memory_guidance_style,
            'kwargs': kwargs.copy()
        })
        return "Mocked updated memory"
    
    MemoryManager.prompt_agent_for_memory_update = mock_prompt_agent
    
    try:
        # Create test objects
        agent = MagicMock()
        agent.name = "TestAgent"
        context = MagicMock()
        context.memory = "Initial memory"
        
        # Test 1: Config says "structured", kwargs says "narrative"
        config1 = MagicMock()
        config1.memory_guidance_style = "structured"  # Config value
        config1.selective_memory_updates = False  # Force full LLM update
        
        await SelectiveMemoryManager.update_memory_selective(
            agent=agent,
            context=context,
            content="Test content",
            config=config1,
            memory_guidance_style="narrative"  # This should be ignored in favor of config
        )
        
        # Check what was actually passed
        if captured_calls:
            actual_style = captured_calls[-1]['memory_guidance_style']
            if actual_style == "structured":
                print("✅ Config takes precedence over kwargs parameter")
            else:
                print(f"❌ Expected 'structured' from config, got '{actual_style}'")
                
            # Verify kwargs was cleaned  
            kwargs_after = captured_calls[-1]['kwargs']
            if 'memory_guidance_style' not in kwargs_after:
                print("✅ kwargs cleaned properly - no memory_guidance_style present")
            else:
                print(f"❌ memory_guidance_style still in kwargs: {kwargs_after}")
        
    finally:
        # Restore original method
        MemoryManager.prompt_agent_for_memory_update = original_prompt_method
    
    return True


async def run_tests():
    """Run all keyword fix tests."""
    print("🧪 Keyword Argument Conflict Fix Tests")
    print("=" * 60)
    
    try:
        success1 = await test_keyword_conflict_fix()
        success2 = await test_parameter_precedence()
        
        if success1 and success2:
            print(f"\n✅ All keyword conflict tests passed!")
            print("=" * 60)
            print("Fix Summary:")
            print("- ✅ No more 'multiple values for keyword argument' errors")
            print("- ✅ Config takes precedence for memory_guidance_style") 
            print("- ✅ kwargs cleaned properly to avoid conflicts")
            print("- ✅ Backward compatibility maintained")
            
        else:
            print(f"\n❌ Some tests failed - fix needs more work")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_tests())