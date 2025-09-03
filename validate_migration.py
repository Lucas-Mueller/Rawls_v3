#!/usr/bin/env python3
"""
Migration Validation Script - Phase 6.3

Validates that the LiteLLM → Direct OpenRouter migration was successful by testing
both OpenAI and OpenRouter model functionality using the updated provider system.

This script tests:
1. OpenAI model creation and basic functionality
2. OpenRouter model creation and basic functionality  
3. Temperature detection for both providers
4. Model configuration creation for both providers
5. Error handling and meaningful failure messages

Usage:
    python validate_migration.py
"""

import asyncio
import logging
import sys
import os
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the updated model provider functions
from utils.model_provider import (
    detect_model_provider,
    create_model_config,
    get_model_provider_info,
    create_model_config_with_temperature_detection,
    create_model_settings
)
from utils.dynamic_model_capabilities import (
    test_temperature_support,
    TemperatureCache
)
from utils.openrouter_client import get_openrouter_client
from agents import Agent, Runner
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel


class MigrationValidator:
    """Validates the LiteLLM → Direct OpenRouter migration."""
    
    def __init__(self):
        self.results = []
        self.cache = TemperatureCache()
        
    def log_test_result(self, test_name: str, success: bool, details: str, error: Optional[Exception] = None):
        """Log and store test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
        logger.info(f"   Details: {details}")
        if error:
            logger.error(f"   Error: {error}")
        
        self.results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "error": str(error) if error else None,
            "timestamp": datetime.now().isoformat()
        })
        
    async def validate_environment(self) -> bool:
        """Validate that required environment variables are present."""
        logger.info("=== Environment Validation ===")
        
        openai_key = os.getenv("OPENAI_API_KEY")
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        
        if not openai_key:
            self.log_test_result(
                "OpenAI API Key", 
                False, 
                "OPENAI_API_KEY environment variable not set"
            )
            return False
        else:
            self.log_test_result(
                "OpenAI API Key", 
                True, 
                f"OPENAI_API_KEY present (length: {len(openai_key)})"
            )
        
        if not openrouter_key:
            self.log_test_result(
                "OpenRouter API Key", 
                False, 
                "OPENROUTER_API_KEY environment variable not set"
            )
            return False
        else:
            self.log_test_result(
                "OpenRouter API Key", 
                True, 
                f"OPENROUTER_API_KEY present (length: {len(openrouter_key)})"
            )
        
        return True

    async def test_model_provider_detection(self) -> bool:
        """Test model provider detection logic."""
        logger.info("=== Model Provider Detection ===")
        
        test_cases = [
            ("gpt-4", False, "OpenAI"),
            ("gpt-4o-mini", False, "OpenAI"),
            ("anthropic/claude-3-sonnet", True, "OpenRouter"),
            ("google/gemini-2.0-flash-exp", True, "OpenRouter"),
            ("meta-llama/llama-3.3-70b-instruct", True, "OpenRouter"),
        ]
        
        all_passed = True
        
        for model_string, expected_is_openrouter, expected_provider in test_cases:
            try:
                detected_model, is_openrouter = detect_model_provider(model_string)
                
                if detected_model == model_string and is_openrouter == expected_is_openrouter:
                    self.log_test_result(
                        f"Detect {model_string}",
                        True,
                        f"Correctly identified as {expected_provider} model"
                    )
                else:
                    self.log_test_result(
                        f"Detect {model_string}",
                        False,
                        f"Expected ({model_string}, {expected_is_openrouter}), got ({detected_model}, {is_openrouter})"
                    )
                    all_passed = False
                    
            except Exception as e:
                self.log_test_result(
                    f"Detect {model_string}",
                    False,
                    f"Exception during detection: {e}",
                    e
                )
                all_passed = False
        
        return all_passed

    async def test_model_config_creation(self) -> bool:
        """Test model configuration creation for both providers."""
        logger.info("=== Model Configuration Creation ===")
        
        test_cases = [
            ("gpt-4", "OpenAI", str),
            ("anthropic/claude-3-sonnet", "OpenRouter", OpenAIChatCompletionsModel),
        ]
        
        all_passed = True
        
        for model_string, provider_name, expected_type in test_cases:
            try:
                config = create_model_config(model_string, temperature=0.7)
                
                if isinstance(config, expected_type):
                    self.log_test_result(
                        f"Create {provider_name} config ({model_string})",
                        True,
                        f"Successfully created {type(config).__name__} instance"
                    )
                else:
                    self.log_test_result(
                        f"Create {provider_name} config ({model_string})",
                        False,
                        f"Expected {expected_type.__name__}, got {type(config).__name__}"
                    )
                    all_passed = False
                    
            except Exception as e:
                self.log_test_result(
                    f"Create {provider_name} config ({model_string})",
                    False,
                    f"Exception during creation: {e}",
                    e
                )
                all_passed = False
        
        return all_passed

    async def test_provider_info(self) -> bool:
        """Test provider information retrieval."""
        logger.info("=== Provider Information ===")
        
        test_cases = [
            ("gpt-4", {
                "provider": "OpenAI",
                "is_openrouter": False,
                "requires_env_var": "OPENAI_API_KEY"
            }),
            ("anthropic/claude-3-sonnet", {
                "provider": "OpenRouter", 
                "is_openrouter": True,
                "requires_env_var": "OPENROUTER_API_KEY"
            }),
        ]
        
        all_passed = True
        
        for model_string, expected_fields in test_cases:
            try:
                info = get_model_provider_info(model_string)
                
                success = True
                for key, expected_value in expected_fields.items():
                    if info.get(key) != expected_value:
                        success = False
                        break
                
                if success:
                    self.log_test_result(
                        f"Provider info ({model_string})",
                        True,
                        f"Correct provider info: {info['provider']}"
                    )
                else:
                    self.log_test_result(
                        f"Provider info ({model_string})",
                        False,
                        f"Incorrect provider info. Expected fields: {expected_fields}, got: {info}"
                    )
                    all_passed = False
                    
            except Exception as e:
                self.log_test_result(
                    f"Provider info ({model_string})",
                    False,
                    f"Exception getting provider info: {e}",
                    e
                )
                all_passed = False
        
        return all_passed

    async def test_openrouter_client(self) -> bool:
        """Test OpenRouter client creation."""
        logger.info("=== OpenRouter Client ===")
        
        try:
            client = get_openrouter_client()
            
            # Check that client has expected properties
            if hasattr(client, 'base_url') and hasattr(client, 'api_key'):
                expected_base_url = "https://openrouter.ai/api/v1"
                if client.base_url == expected_base_url:
                    self.log_test_result(
                        "OpenRouter Client Creation",
                        True,
                        f"Client created with correct base_url: {client.base_url}"
                    )
                    return True
                else:
                    self.log_test_result(
                        "OpenRouter Client Creation",
                        False,
                        f"Expected base_url {expected_base_url}, got {client.base_url}"
                    )
                    return False
            else:
                self.log_test_result(
                    "OpenRouter Client Creation",
                    False,
                    "Client missing expected attributes (base_url, api_key)"
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "OpenRouter Client Creation",
                False,
                f"Exception creating client: {e}",
                e
            )
            return False

    async def test_temperature_detection(self) -> bool:
        """Test temperature support detection for both providers."""
        logger.info("=== Temperature Detection ===")
        
        test_models = [
            ("gpt-4", "OpenAI"),
            ("anthropic/claude-3-sonnet", "OpenRouter"),
        ]
        
        all_passed = True
        
        for model_string, provider_name in test_models:
            try:
                logger.info(f"Testing temperature support for {model_string} ({provider_name})...")
                
                # Test temperature support detection
                supports_temp, reason, exception = await test_temperature_support(model_string, self.cache)
                
                self.log_test_result(
                    f"Temperature detection ({provider_name})",
                    True,  # Success if no exception was raised
                    f"Result: {supports_temp}, Reason: {reason}"
                )
                
                # Test advanced model config creation with temperature detection
                model_config, temp_info = await create_model_config_with_temperature_detection(
                    model_string, 
                    temperature=0.8, 
                    temperature_cache=self.cache
                )
                
                if temp_info.get("detection_method"):
                    self.log_test_result(
                        f"Advanced temperature config ({provider_name})",
                        True,
                        f"Detection method: {temp_info['detection_method']}, supports: {temp_info['supports_temperature']}"
                    )
                else:
                    self.log_test_result(
                        f"Advanced temperature config ({provider_name})",
                        False,
                        f"Missing detection_method in temp_info: {temp_info}"
                    )
                    all_passed = False
                    
            except Exception as e:
                self.log_test_result(
                    f"Temperature detection ({provider_name})",
                    False,
                    f"Exception during temperature testing: {e}",
                    e
                )
                all_passed = False
        
        return all_passed

    async def test_basic_agent_functionality(self) -> bool:
        """Test basic agent creation and functionality with both providers."""
        logger.info("=== Basic Agent Functionality ===")
        
        test_cases = [
            ("gpt-4", "OpenAI"),
            ("anthropic/claude-3-sonnet", "OpenRouter"),
        ]
        
        all_passed = True
        
        for model_string, provider_name in test_cases:
            try:
                logger.info(f"Testing basic agent functionality for {model_string} ({provider_name})...")
                
                # Create model config
                model_config = create_model_config(model_string)
                
                # Create agent
                agent = Agent(
                    name=f"test_agent_{provider_name.lower()}",
                    instructions="You are a test agent. Respond concisely with just 'Hello, world!' and nothing else.",
                    model=model_config
                )
                
                # Test basic functionality with timeout
                response = await asyncio.wait_for(
                    Runner.run(agent, "Say hello"),
                    timeout=30  # 30 second timeout
                )
                
                if response and hasattr(response, 'messages') and len(response.messages) > 0:
                    response_text = response.messages[-1].content
                    self.log_test_result(
                        f"Basic agent functionality ({provider_name})",
                        True,
                        f"Agent responded: '{response_text[:100]}...'" if len(response_text) > 100 else f"Agent responded: '{response_text}'"
                    )
                else:
                    self.log_test_result(
                        f"Basic agent functionality ({provider_name})",
                        False,
                        f"Invalid response format: {response}"
                    )
                    all_passed = False
                    
            except asyncio.TimeoutError:
                self.log_test_result(
                    f"Basic agent functionality ({provider_name})",
                    False,
                    "Agent test timed out after 30 seconds"
                )
                all_passed = False
            except Exception as e:
                self.log_test_result(
                    f"Basic agent functionality ({provider_name})",
                    False,
                    f"Exception during agent testing: {e}",
                    e
                )
                all_passed = False
        
        return all_passed

    async def run_all_tests(self) -> bool:
        """Run all validation tests."""
        logger.info("🚀 Starting Migration Validation Tests")
        logger.info("=" * 50)
        
        test_functions = [
            self.validate_environment,
            self.test_model_provider_detection,
            self.test_model_config_creation,
            self.test_provider_info,
            self.test_openrouter_client,
            self.test_temperature_detection,
            self.test_basic_agent_functionality,
        ]
        
        all_passed = True
        
        for test_func in test_functions:
            try:
                passed = await test_func()
                all_passed = all_passed and passed
                logger.info("")  # Add spacing between test groups
            except Exception as e:
                logger.error(f"Unexpected error in {test_func.__name__}: {e}")
                all_passed = False
        
        return all_passed
    
    def print_summary(self, overall_success: bool):
        """Print test summary."""
        logger.info("=" * 50)
        logger.info("🏁 MIGRATION VALIDATION SUMMARY")
        logger.info("=" * 50)
        
        passed_tests = sum(1 for result in self.results if result["success"])
        total_tests = len(self.results)
        
        logger.info(f"Total tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {total_tests - passed_tests}")
        
        if overall_success:
            logger.info("🎉 MIGRATION VALIDATION: SUCCESS")
            logger.info("The LiteLLM → Direct OpenRouter migration is working correctly!")
        else:
            logger.error("💥 MIGRATION VALIDATION: FAILED")
            logger.error("Some tests failed. Please review the errors above.")
            
        logger.info("=" * 50)
        
        # Print failed tests details
        failed_tests = [result for result in self.results if not result["success"]]
        if failed_tests:
            logger.info("FAILED TESTS DETAILS:")
            for test in failed_tests:
                logger.error(f"❌ {test['test']}: {test['details']}")
                if test['error']:
                    logger.error(f"   Error: {test['error']}")


async def main():
    """Main validation function."""
    validator = MigrationValidator()
    
    try:
        overall_success = await validator.run_all_tests()
        validator.print_summary(overall_success)
        
        # Exit with appropriate code
        sys.exit(0 if overall_success else 1)
        
    except KeyboardInterrupt:
        logger.warning("Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during validation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())