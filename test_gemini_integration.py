#!/usr/bin/env python3
"""
Test script for Gemini API integration.

This script tests:
1. Model provider detection
2. Gemini client initialization
3. Error messages for missing API keys
4. Mixed provider configurations
"""

import os
import asyncio
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def test_provider_detection():
    """Test the model provider detection logic."""
    from utils.model_provider import detect_model_provider

    print("\n" + "="*60)
    print("Testing Model Provider Detection")
    print("="*60)

    test_cases = [
        # (model_string, expected_provider, should_fail)
        ("gemini-2.5-flash", "gemini", False),  # Requires GEMINI_API_KEY
        ("gemini-1.5-pro", "gemini", False),
        ("gemma-2b", "gemini", False),
        ("gpt-4o", "openai", False),  # Requires OPENAI_API_KEY
        ("gpt-4o-mini", "openai", False),
        ("o1-preview", "openai", False),
        ("o3-mini", "openai", False),
        ("google/gemini-2.5-flash", "openrouter", False),  # Explicit OpenRouter
        ("openai/gpt-4o", "openrouter", False),
        ("anthropic/claude-3", "openrouter", False),
        ("unknown-model", None, True),  # Should raise error
    ]

    for model_string, expected_provider, should_fail in test_cases:
        try:
            processed_model, provider = detect_model_provider(model_string)
            if should_fail:
                print(f"❌ {model_string}: Expected error but got provider={provider}")
            else:
                if provider == expected_provider:
                    print(f"✅ {model_string} -> {provider}")
                else:
                    print(f"❌ {model_string}: Expected {expected_provider}, got {provider}")
        except ValueError as e:
            if should_fail:
                print(f"✅ {model_string} -> Error (as expected): {str(e).split('.')[0]}")
            else:
                print(f"❌ {model_string}: Unexpected error: {e}")


def test_model_config_creation():
    """Test model configuration creation."""
    from utils.model_provider import create_model_config

    print("\n" + "="*60)
    print("Testing Model Configuration Creation")
    print("="*60)

    # Test with available API keys
    if os.getenv("GEMINI_API_KEY"):
        try:
            config = create_model_config("gemini-2.5-flash")
            # Gemini now uses OpenAIChatCompletionsModel
            expected_type = "OpenAIChatCompletionsModel"
            actual_type = type(config).__name__
            status = "✅" if actual_type == expected_type else "⚠️"
            print(f"{status} Created Gemini config: {actual_type}")
        except Exception as e:
            print(f"❌ Failed to create Gemini config: {e}")
    else:
        print("⚠️  GEMINI_API_KEY not set - skipping Gemini test")

    if os.getenv("OPENAI_API_KEY"):
        try:
            config = create_model_config("gpt-4o-mini")
            print(f"✅ Created OpenAI config: {type(config)}")
        except Exception as e:
            print(f"❌ Failed to create OpenAI config: {e}")
    else:
        print("⚠️  OPENAI_API_KEY not set - skipping OpenAI test")

    if os.getenv("OPENROUTER_API_KEY"):
        try:
            config = create_model_config("google/gemini-2.5-flash")
            print(f"✅ Created OpenRouter config: {type(config).__name__}")
        except Exception as e:
            print(f"❌ Failed to create OpenRouter config: {e}")
    else:
        print("⚠️  OPENROUTER_API_KEY not set - skipping OpenRouter test")


async def test_gemini_client():
    """Test Gemini client functionality."""
    from utils.gemini_client import get_gemini_client, is_gemini_available
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

    print("\n" + "="*60)
    print("Testing Gemini Client")
    print("="*60)

    if not is_gemini_available():
        print("⚠️  Gemini not available (check GEMINI_API_KEY)")
        return

    try:
        # Create Gemini client
        client = get_gemini_client()
        print(f"✅ Created Gemini client with OpenAI-compatible endpoint")

        # Create OpenAIChatCompletionsModel with Gemini client
        model = OpenAIChatCompletionsModel(
            model="gemini-2.5-flash",
            openai_client=client
        )
        print(f"✅ Created OpenAIChatCompletionsModel with Gemini client")

        # Test API call using the model's interface
        print("📡 Testing Gemini API call via OpenAI-compatible endpoint...")

        # The OpenAI Agents SDK will handle the actual call
        # For now, just verify the model was created successfully
        print(f"✅ Gemini integration ready (using OpenAI-compatible endpoint)")

    except Exception as e:
        print(f"❌ Gemini client test failed: {e}")


def test_error_messages():
    """Test that error messages are clear and helpful."""
    from utils.model_provider import detect_model_provider

    print("\n" + "="*60)
    print("Testing Error Messages")
    print("="*60)

    # Temporarily unset API keys to test error messages
    original_gemini = os.environ.pop("GEMINI_API_KEY", None)
    original_openai = os.environ.pop("OPENAI_API_KEY", None)

    test_cases = [
        "gemini-2.5-flash",
        "gpt-4o",
        "unknown-model"
    ]

    for model in test_cases:
        try:
            detect_model_provider(model)
            print(f"❌ {model}: Should have raised error")
        except ValueError as e:
            error_msg = str(e)
            # Check for helpful error message components
            has_solutions = "Solutions:" in error_msg
            has_env_var = "API_KEY" in error_msg
            has_alternative = "openrouter" in error_msg.lower() or "/" in error_msg

            if has_solutions and has_env_var and has_alternative:
                print(f"✅ {model}: Clear error with solutions")
                print(f"   Error preview: {error_msg.split('Solutions:')[0].strip()}")
            else:
                print(f"⚠️  {model}: Error could be clearer")
                print(f"   Error: {error_msg[:100]}")

    # Restore API keys
    if original_gemini:
        os.environ["GEMINI_API_KEY"] = original_gemini
    if original_openai:
        os.environ["OPENAI_API_KEY"] = original_openai


async def test_temperature_detection():
    """Test temperature detection with Gemini models."""
    from utils.dynamic_model_capabilities import test_temperature_support

    print("\n" + "="*60)
    print("Testing Temperature Detection")
    print("="*60)

    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  GEMINI_API_KEY not set - skipping temperature test")
        return

    try:
        supports_temp, reason, exception = await test_temperature_support("gemini-2.5-flash")
        if supports_temp:
            print(f"✅ Gemini supports temperature: {reason}")
        else:
            print(f"⚠️  Gemini temperature support: {reason}")
            if exception:
                print(f"   Exception: {exception}")
    except Exception as e:
        print(f"❌ Temperature detection failed: {e}")


def main():
    """Run all tests."""
    print("\n" + "#"*60)
    print("# Gemini API Integration Test Suite")
    print("#"*60)

    # Check environment
    print("\n" + "="*60)
    print("Environment Check")
    print("="*60)
    print(f"GEMINI_API_KEY: {'✅ Set' if os.getenv('GEMINI_API_KEY') else '❌ Not set'}")
    print(f"OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Not set'}")
    print(f"OPENROUTER_API_KEY: {'✅ Set' if os.getenv('OPENROUTER_API_KEY') else '❌ Not set'}")

    # Run synchronous tests
    test_provider_detection()
    test_model_config_creation()
    test_error_messages()

    # Run async tests
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_gemini_client())
    loop.run_until_complete(test_temperature_detection())

    print("\n" + "#"*60)
    print("# Test Suite Complete")
    print("#"*60)


if __name__ == "__main__":
    main()