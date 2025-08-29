#!/usr/bin/env python3
"""
Integration test script for Phase 1 critical fixes.
Tests the core workflow functionality to ensure the fixes are working in the full system context.
"""

import asyncio
import unittest
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.principle_types import PrincipleChoice, JusticePrinciple, CertaintyLevel
from experiment_agents.utility_agent import UtilityAgent


class TestPhase1Workflow(unittest.TestCase):
    """Integration test suite for Phase 1 workflow and critical fixes."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_results = []
        self.passed = 0
        self.failed = 0
        self.utility_agent = None
    
    async def async_setUp(self):
        """Async setup for utility agent."""
        if not self.utility_agent:
            self.utility_agent = UtilityAgent()
            await self.utility_agent.async_init()
    
    def test_result(self, test_name: str, passed: bool, message: str = ""):
        """Record test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append(f"{status}: {test_name}")
        if message:
            self.test_results.append(f"    {message}")
        
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def test_pydantic_validation_workflow(self):
        """Test Pydantic validation workflow with constraint principles."""
        try:
            # Test 1: Valid constraint principle workflow
            valid_choice = PrincipleChoice.create_for_parsing(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                constraint_amount=15000,
                certainty=CertaintyLevel.SURE,
                reasoning="Test reasoning"
            )
            
            # Should be able to validate for voting
            validated = valid_choice.validate_for_voting()
            self.test_result(
                "Valid constraint principle workflow", 
                validated.constraint_amount == 15000,
                f"Constraint amount: {validated.constraint_amount}"
            )
            
            # Test 2: Invalid constraint principle workflow
            invalid_choice = PrincipleChoice.create_for_parsing(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                constraint_amount=None,
                certainty=CertaintyLevel.SURE,
                reasoning="Test reasoning"
            )
            
            # First verify it can be created in parsing mode
            self.test_result(
                "Invalid constraint created in parsing mode",
                invalid_choice.constraint_amount is None,
                "Should allow None constraint in parsing mode"
            )
            
            # Then verify validation for voting fails
            validation_failed = False
            try:
                invalid_choice.validate_for_voting()
            except ValueError:
                validation_failed = True
            
            self.test_result(
                "Invalid constraint principle validation failure", 
                validation_failed,
                "Should raise ValueError for None constraint"
            )
            
            # Test 3: Non-constraint principle workflow
            non_constraint = PrincipleChoice.create_for_parsing(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE,
                constraint_amount=None,
                certainty=CertaintyLevel.SURE,
                reasoning="Test reasoning"
            )
            
            validated_non_constraint = non_constraint.validate_for_voting()
            self.test_result(
                "Non-constraint principle workflow", 
                validated_non_constraint.principle == JusticePrinciple.MAXIMIZING_AVERAGE,
                f"Principle: {validated_non_constraint.principle.value}"
            )
            
        except Exception as e:
            self.test_result("Pydantic validation workflow", False, f"Exception: {str(e)}")
    
    async def test_agreement_detection_workflow(self):
        """Test agreement detection workflow with various formats."""
        await self.async_setUp()
        
        try:
            # Test cases: (response, expected_agreement)
            test_cases = [
                ("Yes", True),
                ("YES", True), 
                ("yes", True),
                ("I agree", True),
                ("Let's vote", True),
                ("Ready to vote", True),
                ("No", False),
                ("NO", False),
                ("Not ready", False),
                ("Yes, but I have concerns", False),  # Should detect negation
                ("Need more discussion", False),
                ("Si", True),  # Spanish
                ("是的", True),  # Mandarin
            ]
            
            correct_detections = 0
            total_tests = len(test_cases)
            
            for response, expected in test_cases:
                try:
                    result = await self.utility_agent.detect_agreement_multilingual(response)
                    if result == expected:
                        correct_detections += 1
                except Exception:
                    pass  # Count as incorrect
            
            accuracy = correct_detections / total_tests
            self.test_result(
                "Agreement detection workflow accuracy",
                accuracy >= 0.8,  # 80% accuracy threshold
                f"Accuracy: {accuracy:.1%} ({correct_detections}/{total_tests})"
            )
            
        except Exception as e:
            self.test_result("Agreement detection workflow", False, f"Exception: {str(e)}")
    
    async def test_vote_detection_workflow(self):
        """Test vote detection workflow with various formats."""
        await self.async_setUp()
        
        try:
            # Test cases: (statement, should_detect_vote)
            test_cases = [
                ("I propose we vote on principle A", True),
                ("Let's vote now", True),
                ("Ready to vote", True),
                ("Time to vote", True),
                ("We should proceed with a vote", True),
                ("Let's finalize this with a vote", True),
                ("I think we need more discussion", False),
                ("What do you think about this principle?", False),
                ("I'm not sure yet", False),
                ("VOTE: I formally propose principle C", True),
                ("Let me think about this more", False),
            ]
            
            correct_detections = 0
            total_tests = len(test_cases)
            
            for statement, should_detect in test_cases:
                try:
                    result = await self.utility_agent.detect_vote_intention_enhanced(statement)
                    detected = result is not None
                    
                    if detected == should_detect:
                        correct_detections += 1
                except Exception:
                    pass  # Count as incorrect
            
            accuracy = correct_detections / total_tests
            self.test_result(
                "Vote detection workflow accuracy",
                accuracy >= 0.8,  # 80% accuracy threshold
                f"Accuracy: {accuracy:.1%} ({correct_detections}/{total_tests})"
            )
            
        except Exception as e:
            self.test_result("Vote detection workflow", False, f"Exception: {str(e)}")
    
    def test_constraint_validation_workflow(self):
        """Test constraint validation workflow."""
        try:
            # Test valid constraint amounts
            valid_amounts = [1000, 5000, 10000, 25000, 50000]
            
            for amount in valid_amounts:
                choice = PrincipleChoice.create_for_parsing(
                    principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                    constraint_amount=amount,
                    certainty=CertaintyLevel.SURE
                )
                
                is_valid = choice.is_valid_constraint()
                self.test_result(
                    f"Valid constraint amount {amount}",
                    is_valid,
                    f"Amount: ${amount}"
                )
            
            # Test invalid constraint amounts  
            invalid_amounts = [0, -1000, None]
            
            for amount in invalid_amounts:
                choice = PrincipleChoice.create_for_parsing(
                    principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                    constraint_amount=amount,
                    certainty=CertaintyLevel.SURE
                )
                
                is_valid = choice.is_valid_constraint()
                self.test_result(
                    f"Invalid constraint amount {amount}",
                    not is_valid,
                    f"Amount: {amount} (should be invalid)"
                )
            
        except Exception as e:
            self.test_result("Constraint validation workflow", False, f"Exception: {str(e)}")
    
    async def test_end_to_end_parsing_workflow(self):
        """Test end-to-end parsing workflow with realistic scenarios."""
        await self.async_setUp()
        
        try:
            # Realistic parsing scenarios
            scenarios = [
                {
                    "input": "I think we should choose maximizing the floor income",
                    "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                    "expected_constraint": None
                },
                {
                    "input": "My choice is maximizing average income with a floor constraint of $20000",
                    "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                    "expected_constraint": 20000
                },
                {
                    "input": "I prefer maximizing average income without constraints",
                    "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE,
                    "expected_constraint": None
                }
            ]
            
            successful_parses = 0
            
            for i, scenario in enumerate(scenarios):
                try:
                    result = await self.utility_agent.parse_principle_choice_enhanced(scenario["input"])
                    
                    if result and result.principle == scenario["expected_principle"]:
                        # Check constraint if expected
                        if scenario["expected_constraint"] is not None:
                            if result.constraint_amount == scenario["expected_constraint"]:
                                successful_parses += 1
                        else:
                            if result.constraint_amount is None:
                                successful_parses += 1
                except Exception:
                    pass  # Count as failed parse
            
            success_rate = successful_parses / len(scenarios)
            self.test_result(
                "End-to-end parsing workflow",
                success_rate >= 0.7,  # 70% success threshold
                f"Success rate: {success_rate:.1%} ({successful_parses}/{len(scenarios)})"
            )
            
        except Exception as e:
            self.test_result("End-to-end parsing workflow", False, f"Exception: {str(e)}")
    
    async def test_error_recovery_workflow(self):
        """Test error recovery in workflow scenarios."""
        await self.async_setUp()
        
        try:
            # Test various error conditions that should be handled gracefully
            error_cases = [
                "",  # Empty input
                "This is not a valid principle choice",  # Invalid input
                "I choose principle z",  # Invalid principle
                "My choice is unclear and contradictory",  # Ambiguous input
            ]
            
            handled_gracefully = 0
            
            for error_case in error_cases:
                try:
                    result = await self.utility_agent.parse_principle_choice_enhanced(error_case)
                    # Should either return None or a valid result without throwing
                    handled_gracefully += 1
                except Exception:
                    # Exception indicates poor error handling
                    pass
            
            recovery_rate = handled_gracefully / len(error_cases)
            self.test_result(
                "Error recovery workflow",
                recovery_rate == 1.0,  # Should handle all error cases gracefully
                f"Recovery rate: {recovery_rate:.1%} ({handled_gracefully}/{len(error_cases)})"
            )
            
        except Exception as e:
            self.test_result("Error recovery workflow", False, f"Exception: {str(e)}")
    
    async def run_all_workflow_tests(self):
        """Run all Phase 1 workflow tests."""
        # Run tests
        self.test_pydantic_validation_workflow()
        await self.test_agreement_detection_workflow()
        await self.test_vote_detection_workflow()
        self.test_constraint_validation_workflow()
        await self.test_end_to_end_parsing_workflow()
        await self.test_error_recovery_workflow()
        
        # Calculate results
        total_tests = self.passed + self.failed
        success_rate = self.passed / total_tests if total_tests > 0 else 0
        
        return success_rate >= 0.8  # 80% overall success threshold
    
    def print_results(self):
        """Print test results."""
        print("\n" + "=" * 50)
        print("📊 PHASE 1 WORKFLOW TEST RESULTS")
        print("=" * 50)
        
        for result in self.test_results:
            print(result)
        
        total_tests = self.passed + self.failed
        success_rate = self.passed / total_tests if total_tests > 0 else 0
        
        print(f"\n📈 SUMMARY: {self.passed} passed, {self.failed} failed")
        print(f"📈 SUCCESS RATE: {success_rate:.1%}")
        
        if self.failed == 0:
            print("🎉 All workflow tests passed! Phase 1 fixes are working correctly.")
        else:
            print(f"⚠️  {self.failed} workflow test(s) failed. Review the implementation.")


class AsyncTestRunner:
    """Helper class to run async workflow tests."""
    
    def run_async_tests(self):
        """Run all async workflow tests."""
        test_instance = TestPhase1Workflow()
        
        async def run_all_async():
            success = await test_instance.run_all_workflow_tests()
            test_instance.print_results()
            return success
        
        return asyncio.run(run_all_async())


if __name__ == "__main__":
    # For direct execution, run custom async test runner
    runner = AsyncTestRunner()
    try:
        success = runner.run_async_tests()
        if success:
            print("\n✅ Phase 1 workflow tests validated successfully!")
            print("🚀 Ready to proceed with Phase 2 implementation.")
        else:
            print("\n❌ Some workflow tests failed. Please review and fix issues.")
            print("🛠️  Check the implementation and run tests again.")
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        raise