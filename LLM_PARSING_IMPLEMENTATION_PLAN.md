# LLM-Based Parsing Implementation Plan

## Executive Summary

Replace the current lookup-based parsing system (2,105 lines of complex logic) with a simple, robust LLM-based approach that uses structured prompts to extract principle rankings, choices, and discussion statements from participant responses.

## Current System Analysis

### Parsing Points Requiring Replacement
1. **Phase 1 Manager** (`core/phase1_manager.py`)
   - Line 245: `parse_principle_ranking_enhanced()` - Initial ranking
   - Line 294: `parse_principle_choice_enhanced()` - Principle application choice  
   - Line 323: `parse_principle_ranking_enhanced()` - Demonstration round ranking
   - Line 452: `parse_principle_ranking_enhanced()` - Post-explanation ranking
   - Line 477: `parse_principle_ranking_enhanced()` - Final ranking

2. **Phase 2 Manager** (`core/phase2_manager.py`)
   - Line 816: `parse_discussion_statement_enhanced()` - Discussion statement parsing
   - Line 1196: `parse_internal_reasoning_enhanced()` - Internal reasoning parsing

### Current Problems
- Brittle regex patterns failing on format variations
- 58+ hardcoded principle mappings across languages
- Complex text cleaning logic with edge cases
- Inconsistent results across different AI models
- Difficult debugging and maintenance

## New Architecture Design

### Core Principle: **Simple, Focused LLM Instructions**

```
Participant Response → Language-Specific Parsing Prompt → Utility Agent → Structured Output → Validated Result
```

### Key Components

1. **Parsing Prompt Templates** - Language-specific, task-specific prompts
2. **Structured Output Parser** - Simple regex to extract structured responses  
3. **Validation Layer** - Ensure parsed results meet requirements
4. **Retry Logic** - Handle parsing failures gracefully

## Implementation Plan

### Phase 1: Core Infrastructure (Days 1-2)

#### 1.1 Create Parsing Prompt Templates
**File**: `experiment_agents/llm_parsing_prompts.py`

```python
class LLMParsingPrompts:
    """Language and task-specific parsing prompts."""
    
    RANKING_PROMPTS = {
        'english': """Extract the ranking of justice principles from this response.

Justice Principles:
ID1: Maximizing the floor income
ID2: Maximizing the average income
ID3: Maximizing the average income with a floor constraint  
ID4: Maximizing the average income with a range constraint

Certainty Levels: very_unsure, unsure, no_opinion, sure, very_sure

Return ONLY in this format:
RANKING: [ID3,ID1,ID4,ID2]
CERTAINTY: sure""",
        
        'spanish': """Extrae la clasificación de principios de justicia de esta respuesta.

Principios de Justicia:
ID1: Maximización del ingreso mínimo
ID2: Maximización del ingreso promedio
ID3: Maximización del ingreso promedio con restricción de ingreso mínimo
ID4: Maximización del ingreso promedio con restricción de rango

Niveles de Certeza: muy_inseguro, inseguro, sin_opinion, seguro, muy_seguro

Devuelve SOLO en este formato:
RANKING: [ID3,ID1,ID4,ID2]  
CERTAINTY: seguro""",
        
        'mandarin': """从这个回应中提取正义原则的排名。

正义原则：
ID1: 最大化最低收入
ID2: 最大化平均收入  
ID3: 在最低收入约束条件下最大化平均收入
ID4: 在范围约束条件下最大化平均收入

确定性级别：非常不确定，不确定，无意见，确定，非常确定

仅返回此格式：
RANKING: [ID3,ID1,ID4,ID2]
CERTAINTY: 确定"""
    }
    
    CHOICE_PROMPTS = {
        'english': """Extract the principle choice from this response.

Justice Principles:
ID1: Maximizing the floor income
ID2: Maximizing the average income
ID3: Maximizing the average income with a floor constraint
ID4: Maximizing the average income with a range constraint

Certainty Levels: very_unsure, unsure, no_opinion, sure, very_sure

If the principle requires a constraint amount (ID3 or ID4), extract the dollar amount.

Return ONLY in this format:
CHOICE: ID3
CONSTRAINT: 15000
CERTAINTY: sure"""
    }
```

#### 1.2 Create Structured Output Parser
**File**: `experiment_agents/llm_output_parser.py`

```python
class LLMOutputParser:
    """Parse structured output from LLM parsing responses."""
    
    def parse_ranking(self, llm_response: str) -> PrincipleRanking:
        """Parse ranking from structured LLM output."""
        ranking_match = re.search(r'RANKING:\s*\[([^\]]+)\]', llm_response)
        certainty_match = re.search(r'CERTAINTY:\s*(\w+)', llm_response)
        
        if not ranking_match:
            raise ParseError("No RANKING found in response")
            
        # Convert ID format to actual principles
        id_list = [id.strip() for id in ranking_match.group(1).split(',')]
        rankings = self._convert_ids_to_principles(id_list)
        certainty = self._parse_certainty(certainty_match.group(1) if certainty_match else 'sure')
        
        return PrincipleRanking(rankings=rankings, certainty=certainty)
    
    def parse_choice(self, llm_response: str) -> PrincipleChoice:
        """Parse principle choice from structured LLM output."""
        # Similar implementation for choice parsing
```

#### 1.3 Integrate with Existing UtilityAgent
**Modify**: `experiment_agents/utility_agent.py`

```python
class UtilityAgent:
    def __init__(self, model_name: str):
        self.parsing_prompts = LLMParsingPrompts()
        self.output_parser = LLMOutputParser()
        # ... existing initialization
    
    async def parse_principle_ranking_enhanced(self, response: str, max_retries: int = 3) -> PrincipleRanking:
        """New LLM-based ranking parser."""
        language = self.language_manager.current_language.lower()
        
        for attempt in range(max_retries):
            try:
                prompt = self._build_ranking_prompt(response, language)
                result = await run_without_tracing(self.parser_agent, prompt)
                return self.output_parser.parse_ranking(result.final_output)
            except ParseError as e:
                if attempt == max_retries - 1:
                    raise ExperimentError(f"Failed to parse ranking after {max_retries} attempts: {e}")
                # Log attempt and retry with clarified prompt
```

### Phase 2: Method Replacement (Days 3-4)

#### 2.1 Replace Ranking Parser Methods
- `parse_principle_ranking_enhanced()`
- Remove old `_extract_numbered_list()`, `_fuzzy_match_principle()` methods
- Remove 58+ principle mapping dictionaries
- Simplify to single LLM-based approach

#### 2.2 Replace Choice Parser Methods  
- `parse_principle_choice_enhanced()`
- Handle constraint amount extraction via LLM
- Remove complex constraint detection logic

#### 2.3 Replace Discussion Statement Parser
- `parse_discussion_statement_enhanced()` 
- Adapt prompt for discussion statement parsing
- Handle voting proposal detection

### Phase 3: Error Handling & Validation (Day 5)

#### 3.1 Robust Error Handling
```python
class ParseError(Exception):
    """Specific exception for LLM parsing failures."""
    pass

class LLMParsingValidator:
    """Validate parsed results meet experiment requirements."""
    
    def validate_ranking(self, ranking: PrincipleRanking) -> bool:
        """Ensure ranking has 4 unique principles with valid ranks."""
        if len(ranking.rankings) != 4:
            return False
        
        ranks = [r.rank for r in ranking.rankings]
        principles = [r.principle for r in ranking.rankings]
        
        return (len(set(ranks)) == 4 and 
                set(ranks) == {1, 2, 3, 4} and
                len(set(principles)) == 4)
```

#### 3.2 Retry Strategy
- Attempt 1: Standard prompt
- Attempt 2: Clarified prompt with examples
- Attempt 3: Simplified prompt asking for core information only
- Final: Detailed error logging for debugging

### Phase 4: Testing & Validation (Days 6-7)

#### 4.1 Unit Tests
**File**: `tests/unit/test_llm_parsing.py`

```python
class TestLLMParsing:
    @pytest.mark.asyncio
    async def test_ranking_parsing_english(self):
        """Test ranking parsing with various English formats."""
        test_cases = [
            # Markdown bold format
            "1. **Maximizing the average with a floor constraint** – explanation",
            # Plain text format  
            "1. Maximizing floor income\n2. Maximizing average income",
            # Natural language format
            "I prefer the approach focusing on the poorest first"
        ]
        
        agent = UtilityAgent('gpt-4o-mini')
        for case in test_cases:
            result = await agent.parse_principle_ranking_enhanced(case)
            assert len(result.rankings) == 4
            assert all(1 <= r.rank <= 4 for r in result.rankings)
```

#### 4.2 Integration Tests
- Test all 7 parsing points with real experiment data
- Multi-language testing (English, Spanish, Mandarin)  
- Multi-model testing (GPT, Gemini, Claude variants)

#### 4.3 Regression Tests
- Ensure existing experiment configurations still work
- Verify Phase 2 consensus detection remains functional
- Check memory management compatibility

### Phase 5: Migration & Cleanup (Day 8)

#### 5.1 Code Cleanup
- Remove old parsing methods and imports
- Delete unused principle mapping dictionaries
- Clean up complex regex patterns
- Remove debugging code and temporary fixes

#### 5.2 Documentation Update
- Update CLAUDE.md with new parsing approach
- Document prompt templates and their purposes
- Update troubleshooting guide for parsing issues

## Implementation Details

### Prompt Design Principles

1. **Clear Task Definition**: Explicitly state what to extract
2. **Structured Format**: Use consistent output format across languages
3. **Minimal Context**: Only include essential information
4. **Examples When Needed**: Add examples for complex cases
5. **Language-Specific**: Respect cultural and linguistic conventions

### Error Recovery Strategy

```python
RETRY_PROMPTS = {
    'clarified': """The previous response wasn't clear. Please extract ONLY the ranking information.

    Focus on finding which principle the participant ranked 1st, 2nd, 3rd, and 4th.
    
    Return in exactly this format:
    RANKING: [ID1,ID3,ID2,ID4]
    CERTAINTY: sure""",
    
    'simplified': """What is the participant's order of preference for these 4 principles?
    
    Just give me the order from most preferred (1st) to least preferred (4th).
    
    Format: RANKING: [ID3,ID1,ID4,ID2]"""
}
```

### Performance Considerations

- **Latency**: Same as current system (already using utility agent LLM)
- **Cost**: Marginal increase, offset by fewer failed experiments
- **Reliability**: Much higher due to LLM robustness vs brittle regex

### Validation & Quality Assurance

```python
class ParsingQualityMetrics:
    """Track parsing success rates and failure modes."""
    
    def __init__(self):
        self.success_count = 0
        self.failure_count = 0
        self.failure_reasons = defaultdict(int)
    
    def record_success(self, parsing_type: str):
        self.success_count += 1
        logger.info(f"Parsing success: {parsing_type}")
    
    def record_failure(self, parsing_type: str, reason: str):
        self.failure_count += 1
        self.failure_reasons[reason] += 1
        logger.warning(f"Parsing failure: {parsing_type} - {reason}")
```

## Risk Mitigation

### Risk 1: LLM Inconsistency
**Mitigation**: Structured output format + validation + retry logic

### Risk 2: Language Prompt Quality  
**Mitigation**: Native speaker review of Spanish/Mandarin prompts

### Risk 3: Performance Regression
**Mitigation**: A/B testing with current system during transition

### Risk 4: Edge Case Handling
**Mitigation**: Comprehensive test suite with real experiment data

## Success Metrics

1. **Parsing Success Rate**: >95% across all 7 parsing points
2. **Multi-Language Support**: Equal performance across English/Spanish/Mandarin  
3. **Multi-Model Robustness**: Works with GPT, Gemini, Claude variants
4. **Code Simplicity**: <500 lines vs current 2,105 lines
5. **Maintainability**: Issues resolvable via prompt adjustment vs code changes

## Timeline Summary

- **Day 1-2**: Core infrastructure (prompts, parsers, integration)
- **Day 3-4**: Replace existing methods across all 7 parsing points  
- **Day 5**: Error handling, validation, retry logic
- **Day 6-7**: Comprehensive testing (unit, integration, regression)
- **Day 8**: Migration, cleanup, documentation

**Total Effort**: 8 development days for complete system transformation

## Conclusion

This LLM-based approach transforms a brittle, complex parsing system into a simple, robust, and maintainable solution. By leveraging the natural language understanding capabilities of LLMs, we eliminate the fundamental brittleness of regex-based parsing while supporting multi-language experiments seamlessly.

The implementation prioritizes simplicity, robustness, and maintainability - ensuring the Frohlich experiment can reliably parse participant responses regardless of format variations or AI model differences.