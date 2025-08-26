#!/usr/bin/env python3
"""
Test script for Phase 1 critical fixes.
Tests the core functionality to ensure the fixes are working.
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.principle_types import PrincipleChoice, JusticePrinciple, CertaintyLevel
from experiment_agents.utility_agent import UtilityAgent


class Phase1FixesTest:
    """Test suite for Phase 1 critical fixes."""
    
    def __init__(self):
        self.test_results = []
        self.passed = 0
        self.failed = 0
    
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
    
    def test_pydantic_validation_bypass_removal(self):
        """Test 1.3: Verify Pydantic validation bypass is removed."""
        print("🧪 Testing Pydantic validation bypass removal...")
        
        try:
            # Test 1: Valid constraint principle should work
            valid_choice = PrincipleChoice.create_for_parsing(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                constraint_amount=15000,
                certainty=CertaintyLevel.SURE,
                reasoning="Test reasoning"
            )
            
            # Should be able to validate for voting
            validated = valid_choice.validate_for_voting()
            self.test_result(
                "Valid constraint principle validation", 
                validated.constraint_amount == 15000,
                f"Constraint amount: {validated.constraint_amount}"
            )
            
            # Test 2: Invalid constraint principle should fail validation
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
            
            # Test 3: Non-constraint principle should work without constraint
            non_constraint = PrincipleChoice.create_for_parsing(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE,
                constraint_amount=None,
                certainty=CertaintyLevel.SURE,
                reasoning="Test reasoning"
            )
            
            validated_non_constraint = non_constraint.validate_for_voting()
            self.test_result(
                "Non-constraint principle validation", 
                validated_non_constraint.principle == JusticePrinciple.MAXIMIZING_AVERAGE,
                f"Principle: {validated_non_constraint.principle.value}"
            )
            
        except Exception as e:
            self.test_result("Pydantic validation bypass removal", False, f"Exception: {str(e)}")
    
    async def test_agreement_detection_robustness(self):
        """Test 1.1: Verify agreement detection handles various formats."""
        print("🧪 Testing agreement detection robustness...")
        
        try:
            utility_agent = UtilityAgent()
            await utility_agent.async_init()
            
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
                    result = await utility_agent.detect_agreement_multilingual(response)
                    if result == expected:
                        correct_detections += 1
                        print(f"  ✅ '{response}' -> {result} (expected {expected})")
                    else:
                        print(f"  ❌ '{response}' -> {result} (expected {expected})")
                except Exception as e:
                    print(f"  ❌ '{response}' -> Exception: {str(e)}")
            
            accuracy = correct_detections / total_tests
            self.test_result(
                "Agreement detection accuracy",
                accuracy >= 0.8,  # 80% accuracy threshold
                f"Accuracy: {accuracy:.1%} ({correct_detections}/{total_tests})"
            )
            
        except Exception as e:
            self.test_result("Agreement detection robustness", False, f"Exception: {str(e)}")
    
    async def test_vote_detection_robustness(self):
        """Test 1.2: Verify vote detection handles various formats."""
        print("🧪 Testing vote detection robustness...")
        
        try:
            utility_agent = UtilityAgent()
            await utility_agent.async_init()
            
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
                    result = await utility_agent.detect_vote_intention_enhanced(statement)
                    detected = result is not None
                    
                    if detected == should_detect:
                        correct_detections += 1
                        print(f"  ✅ '{statement[:30]}...' -> {detected} (expected {should_detect})")
                    else:
                        print(f"  ❌ '{statement[:30]}...' -> {detected} (expected {should_detect})")
                except Exception as e:
                    print(f"  ❌ '{statement[:30]}...' -> Exception: {str(e)}")
            
            accuracy = correct_detections / total_tests
            self.test_result(
                "Vote detection accuracy",
                accuracy >= 0.8,  # 80% accuracy threshold
                f"Accuracy: {accuracy:.1%} ({correct_detections}/{total_tests})"
            )
            
        except Exception as e:
            self.test_result("Vote detection robustness", False, f"Exception: {str(e)}")
    
    def test_constraint_validation(self):
        """Test 1.4: Verify constraint validation works properly."""
        print("🧪 Testing constraint validation...")
        
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
            self.test_result("Constraint validation", False, f"Exception: {str(e)}")
    
    async def run_all_tests(self):
        """Run all Phase 1 fix tests."""
        print("🚀 Running Phase 1 Critical Fixes Test Suite")
        print("=" * 50)
        
        # Run tests
        self.test_pydantic_validation_bypass_removal()
        await self.test_agreement_detection_robustness()
        await self.test_vote_detection_robustness()
        self.test_constraint_validation()
        
        # Print results
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS")
        print("=" * 50)
        
        for result in self.test_results:
            print(result)
        
        print(f"\n📈 SUMMARY: {self.passed} passed, {self.failed} failed")
        
        if self.failed == 0:
            print("🎉 All tests passed! Phase 1 fixes are working correctly.")
            return True
        else:
            print(f"⚠️  {self.failed} test(s) failed. Review the fixes.")
            return False


async def main():
    """Main test runner."""
    test_suite = Phase1FixesTest()
    success = await test_suite.run_all_tests()
    
    if success:
        print("\n✅ Phase 1 critical fixes validated successfully!")
        print("🚀 Ready to proceed with Phase 2 implementation.")
    else:
        print("\n❌ Some tests failed. Please review and fix issues.")
        print("🛠️  Check the implementation and run tests again.")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)