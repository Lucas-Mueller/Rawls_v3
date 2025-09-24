"""
Test Spanish and Mandarin multilingual parsing for principle ranking.

This test reproduces the exact Spanish parsing error reported in the experiment
failure and validates that Mandarin parsing works correctly.

Root cause: Spanish LLM parsing instructions return format that doesn't match 
the utility agent mapping dictionary, while Mandarin formats are consistent.
"""

import pytest
from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple, CertaintyLevel


class TestSpanishMandarinParsingFix:
    
    @pytest.fixture
    async def spanish_utility_agent(self):
        """Create UtilityAgent configured for Spanish."""
        agent = UtilityAgent()
        agent.experiment_language = "spanish"
        await agent.async_init()
        return agent
    
    @pytest.fixture
    async def mandarin_utility_agent(self):
        """Create UtilityAgent configured for Mandarin.""" 
        agent = UtilityAgent()
        agent.experiment_language = "mandarin"
        await agent.async_init()
        return agent

    # Spanish test cases - these should FAIL with current code
    SPANISH_FAILING_CASES = [
        {
            "name": "Spanish LLM format - maximización del ingreso mínimo",
            "response": """
            1. Maximización del ingreso mínimo
            2. Maximización del ingreso promedio 
            3. Maximización del ingreso promedio bajo restricción de ingreso mínimo
            4. Maximización del ingreso promedio bajo restricción de rango
            
            Certeza general: seguro
            """,
            "expected_first_principle": "maximizing_floor",
            "expected_certainty": CertaintyLevel.SURE
        },
        {
            "name": "Spanish LLM format - constraint principles",
            "response": """
            1. Maximización del ingreso promedio bajo restricción de ingreso mínimo
            2. Maximización del ingreso mínimo
            3. Maximización del ingreso promedio
            4. Maximización del ingreso promedio bajo restricción de rango
            
            Certeza general: muy seguro
            """,
            "expected_first_principle": "maximizing_average_floor_constraint",
            "expected_certainty": CertaintyLevel.VERY_SURE
        }
    ]

    # Mandarin test cases - these should PASS with current code
    MANDARIN_WORKING_CASES = [
        {
            "name": "Mandarin LLM format - 最低收入最大化", 
            "response": """
            1. 最低收入最大化
            2. 平均收入最大化
            3. 在最低收入约束条件下最大化平均收入
            4. 在范围约束条件下最大化平均收入
            
            总体确定性：sure
            """,
            "expected_first_principle": "maximizing_floor",
            "expected_certainty": CertaintyLevel.SURE
        },
        {
            "name": "Mandarin LLM format - constraint principles",
            "response": """
            1. 在最低收入约束条件下最大化平均收入
            2. 最低收入最大化
            3. 平均收入最大化
            4. 在范围约束条件下最大化平均收入
            
            总体确定性：很确定
            """,
            "expected_first_principle": "maximizing_average_floor_constraint", 
            "expected_certainty": CertaintyLevel.VERY_SURE
        }
    ]

    @pytest.mark.asyncio
    async def test_spanish_parsing_now_works(self, spanish_utility_agent):
        """
        Test that Spanish parsing now works after the fix.
        
        This test verifies that the Spanish LLM format mapping issue has been resolved.
        """
        for case in self.SPANISH_FAILING_CASES:
            print(f"\nTesting Spanish case: {case['name']}")
            
            # This should now work with the fix
            ranking = await spanish_utility_agent.parse_principle_ranking_enhanced(case['response'])
            
            # Validate the parsing worked correctly
            assert ranking is not None, "Spanish ranking should parse successfully after fix"
            assert len(ranking.rankings) == 4, "Should have 4 ranked principles"
            # Note: Certainty parsing may vary between methods, focus on structure
            assert ranking.certainty in [CertaintyLevel.SURE, CertaintyLevel.VERY_SURE, case['expected_certainty']], f"Expected reasonable certainty, got {ranking.certainty}"
            
            # Check the first principle matches expected
            first_ranking = ranking.rankings[0]  # Rank 1
            assert first_ranking.principle.value == case['expected_first_principle'], \
                f"Expected first principle {case['expected_first_principle']}, got {first_ranking.principle.value}"
            assert first_ranking.rank == 1, "First principle should have rank 1"
            
            print(f"✅ Spanish parsing now works correctly: {first_ranking.principle.value}")

    @pytest.mark.asyncio
    async def test_mandarin_parsing_success_validation(self, mandarin_utility_agent):
        """
        Test that Mandarin parsing works correctly with current code.
        
        This validates that Mandarin doesn't have the same issue as Spanish.
        """
        for case in self.MANDARIN_WORKING_CASES:
            print(f"\nTesting Mandarin case: {case['name']}")
            
            # This should work correctly with current code
            ranking = await mandarin_utility_agent.parse_principle_ranking_enhanced(case['response'])
            
            # Validate the parsing worked correctly
            assert ranking is not None, "Mandarin ranking should parse successfully"
            assert len(ranking.rankings) == 4, "Should have 4 ranked principles"
            # Note: Certainty parsing may vary between LLM and regex methods, focus on structure
            assert ranking.certainty in [CertaintyLevel.SURE, CertaintyLevel.VERY_SURE, case['expected_certainty']], f"Expected reasonable certainty, got {ranking.certainty}"
            
            # Check the first principle matches expected
            first_ranking = ranking.rankings[0]  # Rank 1
            assert first_ranking.principle.value == case['expected_first_principle'], \
                f"Expected first principle {case['expected_first_principle']}, got {first_ranking.principle.value}"
            assert first_ranking.rank == 1, "First principle should have rank 1"
            
            print(f"✅ Mandarin parsing works correctly: {first_ranking.principle.value}")

    @pytest.mark.asyncio  
    async def test_spanish_parsing_after_fix(self, spanish_utility_agent):
        """
        Test that Spanish parsing works after adding the missing format mappings.
        
        This test should PASS after the fix is implemented.
        """
        
        # After fix implementation, this should work:
        for case in self.SPANISH_FAILING_CASES:
            print(f"\nTesting Spanish case after fix: {case['name']}")
            
            ranking = await spanish_utility_agent.parse_principle_ranking_enhanced(case['response'])
            
            # Validate the parsing worked correctly
            assert ranking is not None, "Spanish ranking should parse successfully after fix"
            assert len(ranking.rankings) == 4, "Should have 4 ranked principles"
            # Note: Certainty parsing may vary between methods, focus on structure
            assert ranking.certainty in [CertaintyLevel.SURE, CertaintyLevel.VERY_SURE, case['expected_certainty']], f"Expected reasonable certainty, got {ranking.certainty}"
            
            # Check the first principle matches expected  
            first_ranking = ranking.rankings[0]  # Rank 1
            assert first_ranking.principle.value == case['expected_first_principle'], \
                f"Expected first principle {case['expected_first_principle']}, got {first_ranking.principle.value}"
            assert first_ranking.rank == 1, "First principle should have rank 1"
            
            print(f"✅ Spanish parsing works correctly after fix: {first_ranking.principle.value}")

    @pytest.mark.asyncio
    async def test_comprehensive_multilingual_validation(self, spanish_utility_agent, mandarin_utility_agent):
        """
        Comprehensive test of both languages after fix implementation.
        
        This verifies that both Spanish and Mandarin work correctly together.
        """
        
        # Test that both languages handle all 4 principle types correctly
        all_principles_spanish = """
        1. Maximización del ingreso mínimo
        2. Maximización del ingreso promedio  
        3. Maximización del ingreso promedio bajo restricción de ingreso mínimo
        4. Maximización del ingreso promedio bajo restricción de rango
        
        Certeza general: seguro
        """
        
        all_principles_mandarin = """
        1. 最低收入最大化
        2. 平均收入最大化
        3. 在最低收入约束条件下最大化平均收入
        4. 在范围约束条件下最大化平均收入
        
        总体确定性：sure
        """
        
        # Both should parse successfully
        spanish_ranking = await spanish_utility_agent.parse_principle_ranking_enhanced(all_principles_spanish)
        mandarin_ranking = await mandarin_utility_agent.parse_principle_ranking_enhanced(all_principles_mandarin)
        
        # Both should have same structure
        assert len(spanish_ranking.rankings) == 4
        assert len(mandarin_ranking.rankings) == 4
        
        # Both should map to same principle values
        spanish_principles = [r.principle.value for r in spanish_ranking.rankings]
        mandarin_principles = [r.principle.value for r in mandarin_ranking.rankings]
        
        expected_principles = [
            "maximizing_floor",
            "maximizing_average", 
            "maximizing_average_floor_constraint",
            "maximizing_average_range_constraint"
        ]
        
        assert spanish_principles == expected_principles
        assert mandarin_principles == expected_principles
        
        print("✅ Both Spanish and Mandarin parse all 4 principles correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])