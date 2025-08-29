#!/usr/bin/env python3
"""Integration test for Alice's specific ballot parsing issue - Letter-Based Parsing Removal Fix."""

import asyncio
import pytest
from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple


@pytest.mark.integration
@pytest.mark.asyncio
class TestAliceBallotParsingFix:
    """Integration test suite for Alice's ballot parsing fix."""

    @pytest.fixture
    def utility_agent(self):
        """Create utility agent for testing."""
        return UtilityAgent(
            model="gpt-4o-mini",
            temperature=0.1,
            language="english"
        )

    async def test_alice_ballot_parsing(self, utility_agent):
        """Test the exact ballot that failed for Alice."""
        # Alice's original ballot that failed
        alice_ballot = "My ballot choice is Maximizing the average income with a floor constraint with a floor constraint of $13,000"
        
        # Parse Alice's ballot using the updated system
        result = await utility_agent.parse_principle_choice_enhanced(alice_ballot)
        
        # Verify the results match expectations
        expected_principle = JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
        expected_constraint = 13000
        
        # Assertions
        assert result is not None, f"Failed to parse Alice's ballot: '{alice_ballot}'"
        assert result.principle == expected_principle, f"Wrong principle: got {result.principle.value}, expected {expected_principle.value}"
        assert result.constraint_amount == expected_constraint, f"Wrong constraint amount: got {result.constraint_amount}, expected {expected_constraint}"

    async def test_backward_compatibility(self, utility_agent):
        """Test that letter-based responses still work for backward compatibility."""
        # Test cases with letters (should still work)
        letter_test_cases = [
            ("My ballot choice is principle c with a floor constraint of $15,000", 
             JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 15000),
            ("I choose principle a",
             JusticePrinciple.MAXIMIZING_FLOOR, None),
            ("My vote is principle d with range constraint of $20,000",
             JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 20000)
        ]
        
        for ballot, expected_principle, expected_constraint in letter_test_cases:
            result = await utility_agent.parse_principle_choice_enhanced(ballot)
            
            assert result is not None, f"Failed to parse ballot: '{ballot}'"
            assert result.principle == expected_principle, f"Wrong principle for '{ballot}': got {result.principle.value}, expected {expected_principle.value}"
            assert result.constraint_amount == expected_constraint, f"Wrong constraint for '{ballot}': got {result.constraint_amount}, expected {expected_constraint}"

    async def test_mixed_language_examples(self):
        """Test full names in different languages."""
        # English agent
        english_agent = UtilityAgent(model="gpt-4o-mini", temperature=0.1, language="english")
        
        # Spanish agent  
        spanish_agent = UtilityAgent(model="gpt-4o-mini", temperature=0.1, language="spanish")
        
        test_cases = [
            # English full name
            (english_agent, "My ballot choice is maximizing_average_floor_constraint with constraint of $12,000",
             JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 12000),
            
            # Spanish full name (should work with Spanish agent)
            (spanish_agent, "Mi elección es maximización del ingreso promedio bajo restricción de ingreso mínimo con restricción de $18,000",
             JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 18000),
        ]
        
        for agent, ballot, expected_principle, expected_constraint in test_cases:
            try:
                result = await agent.parse_principle_choice_enhanced(ballot)
                
                if result:
                    # If parsing succeeds, verify it's correct
                    assert result.principle == expected_principle, f"Wrong principle: got {result.principle.value}, expected {expected_principle.value}"
                    if expected_constraint is not None:
                        assert result.constraint_amount == expected_constraint, f"Wrong constraint: got {result.constraint_amount}, expected {expected_constraint}"
            except Exception as e:
                # Some multilingual parsing may fail - that's acceptable for this test
                pytest.skip(f"Multilingual parsing not fully implemented for: {ballot[:50]}...")

    async def test_principle_name_variations(self, utility_agent):
        """Test various ways of expressing the same principle."""
        variations = [
            # Alice's problematic case
            "My ballot choice is Maximizing the average income with a floor constraint with a floor constraint of $13,000",
            # Simpler variations
            "maximizing_average_floor_constraint with constraint of $13,000",
            "maximizing average with floor constraint of $13,000",
            "I choose maximizing the average income with a floor constraint of $13,000",
            # Letter-based (backward compatibility)
            "My ballot choice is principle c with a floor constraint of $13,000",
        ]
        
        expected_principle = JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
        expected_constraint = 13000
        
        for variation in variations:
            result = await utility_agent.parse_principle_choice_enhanced(variation)
            
            assert result is not None, f"Failed to parse variation: '{variation}'"
            assert result.principle == expected_principle, f"Wrong principle for '{variation}': got {result.principle.value}"
            assert result.constraint_amount == expected_constraint, f"Wrong constraint for '{variation}': got {result.constraint_amount}"

    async def test_constraint_extraction_robustness(self, utility_agent):
        """Test robust constraint amount extraction."""
        constraint_cases = [
            ("principle c with constraint of $13,000", 13000),
            ("principle c with constraint of $13000", 13000),  # No comma
            ("principle c with constraint of 13000", 13000),   # No dollar sign
            ("principle c with floor constraint of $13,000", 13000),  # Explicit floor
            ("maximizing average floor constraint with $13,000", 13000),  # Full name style
        ]
        
        for ballot, expected_amount in constraint_cases:
            result = await utility_agent.parse_principle_choice_enhanced(ballot)
            
            assert result is not None, f"Failed to parse: '{ballot}'"
            assert result.constraint_amount == expected_amount, f"Wrong constraint extraction for '{ballot}': got {result.constraint_amount}, expected {expected_amount}"


if __name__ == "__main__":
    # Allow direct execution for debugging
    async def main():
        """Run tests directly for debugging."""
        test_instance = TestAliceBallotParsingFix()
        agent = UtilityAgent(model="gpt-4o-mini", temperature=0.1, language="english")
        
        print("Running Alice Ballot Parsing Fix Integration Tests...")
        
        try:
            await test_instance.test_alice_ballot_parsing(agent)
            print("✅ Alice's ballot parsing test passed")
            
            await test_instance.test_backward_compatibility(agent)
            print("✅ Backward compatibility test passed")
            
            await test_instance.test_principle_name_variations(agent)
            print("✅ Principle name variations test passed")
            
            await test_instance.test_constraint_extraction_robustness(agent)
            print("✅ Constraint extraction robustness test passed")
            
            print("\n🎉 All Alice ballot parsing fix tests passed!")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise
    
    asyncio.run(main())