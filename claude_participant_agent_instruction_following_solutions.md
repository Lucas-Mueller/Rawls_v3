# Solving Participant Agent Instruction-Following Failures
*A Comprehensive Solution Framework*

## 🎯 **Problem Statement**

**Core Issue**: Participant agents consistently confuse ranking tasks with choice tasks, causing 64% experiment failure rate.

**Specific Manifestation**:
- **Expected Response** (Ranking): `"1. maximizing_floor\n2. maximizing_average\n3. maximizing_average_floor_constraint\n4. maximizing_average_range_constraint"`
- **Actual Response** (Choice): `"I choose maximizing average with floor constraint with a constraint of $10,000. I am very sure about this choice."`

**Impact**: 15 out of 18 parsing failures occur because participant agents provide single choices when complete rankings are required.

---

## 🧠 **Solution Categories**

### **Category 1: Prompt Engineering Solutions**

#### **1.1 Enhanced Format Examples**
```json
{
  "approach": "Explicit Format Coaching",
  "implementation": {
    "add_examples": {
      "good_example": "✅ CORRECT FORMAT:\n1. maximizing_floor\n2. maximizing_average\n3. maximizing_average_floor_constraint\n4. maximizing_average_range_constraint",
      "bad_example": "❌ WRONG FORMAT:\n'I choose maximizing_floor. I am sure about this choice.'"
    },
    "format_emphasis": "🚨 CRITICAL: Your response must contain exactly 4 numbered lines, one for each principle."
  },
  "pros": ["Simple to implement", "Addresses root cause", "Low technical complexity"],
  "cons": ["May not work with all model types", "Increases prompt length"],
  "effort": "Low",
  "impact": "High"
}
```

#### **1.2 Visual Prompt Differentiation**
```yaml
ranking_prompt_header: |
  ═══════════════════════════════════════════════
  🏆 RANKING TASK (Not a choice task!)
  ═══════════════════════════════════════════════
  You must rank ALL 4 principles from best to worst.

choice_prompt_header: |
  ┌─────────────────────────────────────────────┐
  │ 🎯 CHOICE TASK (Pick exactly one principle) │
  └─────────────────────────────────────────────┘
  You must choose ONE principle to apply.
```

#### **1.3 Step-by-Step Instruction Breakdown**
```markdown
**RANKING INSTRUCTIONS:**
Step 1: Read all 4 principles below
Step 2: Decide which is your BEST choice (this becomes #1)
Step 3: Decide which is your WORST choice (this becomes #4)
Step 4: Rank the remaining two as #2 and #3
Step 5: Write your response as exactly 4 numbered lines:
        1. [principle name]
        2. [principle name]
        3. [principle name]
        4. [principle name]
```

### **Category 2: Technical Validation Solutions**

#### **2.1 Immediate Response Validation**
```python
class ResponseValidator:
    def validate_ranking_format(self, response: str) -> tuple[bool, str]:
        """Validate ranking response format before utility agent parsing."""
        lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
        numbered_lines = [line for line in lines if re.match(r'^\d+\.', line)]

        if len(numbered_lines) < 4:
            return False, f"Found {len(numbered_lines)} numbered items, need exactly 4"

        # Check for choice-format patterns that indicate confusion
        choice_patterns = [r'I choose', r'My choice is', r'I select']
        if any(re.search(pattern, response, re.IGNORECASE) for pattern in choice_patterns):
            return False, "Response appears to be choice format, not ranking format"

        return True, "Valid ranking format"
```

#### **2.2 Multi-Stage Prompting with Validation**
```python
async def ranking_with_validation(self, participant: ParticipantAgent, prompt: str, max_attempts: int = 3):
    """Multi-stage prompting with format validation and correction."""

    for attempt in range(max_attempts):
        # Stage 1: Initial prompt
        result = await Runner.run(participant.agent, prompt)
        response = result.final_output

        # Stage 2: Format validation
        is_valid, error_msg = self.validate_ranking_format(response)

        if is_valid:
            return response

        # Stage 3: Corrective prompt
        correction_prompt = f"""
        Your previous response was not in the correct format: {error_msg}

        Original task: {prompt}

        Your previous response: "{response}"

        Please provide exactly 4 numbered lines ranking all principles:
        1. [your best principle]
        2. [your second choice]
        3. [your third choice]
        4. [your worst principle]
        """

    raise ExperimentError(f"Failed to get valid ranking after {max_attempts} attempts")
```

#### **2.3 Smart Fallback Parsing**
```python
class HybridUtilityAgent(UtilityAgent):
    async def parse_ranking_with_fallback(self, response: str) -> PrincipleRanking:
        """Attempt ranking parse, fall back to choice-to-ranking conversion."""

        try:
            # Primary: Standard ranking parsing
            return await self.parse_principle_ranking_enhanced(response)
        except ValueError as e:
            if "Invalid ranking structure" in str(e):
                # Fallback: Check if it's a single choice that can be converted
                choice = await self.try_parse_as_single_choice(response)
                if choice:
                    # Convert single choice to ranking with placeholders
                    return self.convert_choice_to_ranking(choice)
            raise e

    def convert_choice_to_ranking(self, choice: PrincipleChoice) -> PrincipleRanking:
        """Convert single principle choice to ranking with reasonable defaults."""
        all_principles = [
            "maximizing_floor",
            "maximizing_average",
            "maximizing_average_floor_constraint",
            "maximizing_average_range_constraint"
        ]

        chosen = choice.principle.value
        others = [p for p in all_principles if p != chosen]
        random.shuffle(others)  # Random ranking for non-chosen principles

        rankings = [
            RankedPrinciple(principle=JusticePrinciple(chosen), rank=1),
            RankedPrinciple(principle=JusticePrinciple(others[0]), rank=2),
            RankedPrinciple(principle=JusticePrinciple(others[1]), rank=3),
            RankedPrinciple(principle=JusticePrinciple(others[2]), rank=4)
        ]

        return PrincipleRanking(rankings=rankings, certainty=choice.certainty)
```

### **Category 3: Architectural Solutions**

#### **3.1 Task Type Separation**
```python
class Phase1ManagerV2:
    """Redesigned Phase 1 with clear task separation."""

    async def collect_principle_preferences(self, participant: ParticipantAgent):
        """Separate preference collection from ranking."""

        # Step 1: Collect individual principle ratings (not ranking)
        principle_ratings = {}
        for principle in all_principles:
            rating_prompt = f"Rate '{principle}' from 1-10 (10=strongly prefer): "
            rating = await self.collect_numeric_rating(participant, rating_prompt)
            principle_ratings[principle] = rating

        # Step 2: Generate ranking from ratings automatically
        sorted_principles = sorted(principle_ratings.items(), key=lambda x: x[1], reverse=True)
        ranking = [RankedPrinciple(principle=JusticePrinciple(p), rank=i+1)
                  for i, (p, _) in enumerate(sorted_principles)]

        return PrincipleRanking(rankings=ranking, certainty=CertaintyLevel.SURE)
```

#### **3.2 Guided Interactive Collection**
```python
class InteractiveRankingCollector:
    """Step-by-step interactive ranking collection."""

    async def collect_ranking_interactively(self, participant: ParticipantAgent) -> PrincipleRanking:
        principles = list(all_principles)
        ranking = []

        # Step 1: Best choice
        best_prompt = f"Which principle is your FIRST choice (best)?\nOptions: {principles}"
        best = await self.collect_single_choice(participant, best_prompt, principles)
        ranking.append(RankedPrinciple(principle=JusticePrinciple(best), rank=1))
        principles.remove(best)

        # Step 2: Worst choice
        worst_prompt = f"Which of the remaining is your LAST choice (worst)?\nOptions: {principles}"
        worst = await self.collect_single_choice(participant, worst_prompt, principles)
        principles.remove(worst)

        # Step 3: Rank remaining two
        second_prompt = f"Which is better between {principles[0]} and {principles[1]}?"
        second = await self.collect_single_choice(participant, second_prompt, principles)
        third = principles[1] if second == principles[0] else principles[0]

        ranking.append(RankedPrinciple(principle=JusticePrinciple(second), rank=2))
        ranking.append(RankedPrinciple(principle=JusticePrinciple(third), rank=3))
        ranking.append(RankedPrinciple(principle=JusticePrinciple(worst), rank=4))

        return PrincipleRanking(rankings=ranking, certainty=CertaintyLevel.SURE)
```

#### **3.3 Structured Output Generation**
```python
# Use OpenAI's structured outputs or similar
class StructuredRankingAgent:
    def __init__(self):
        self.ranking_schema = {
            "type": "object",
            "properties": {
                "rankings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "principle": {"type": "string", "enum": all_principles},
                            "rank": {"type": "integer", "minimum": 1, "maximum": 4}
                        }
                    },
                    "minItems": 4,
                    "maxItems": 4
                },
                "certainty": {"type": "string", "enum": ["very_unsure", "unsure", "sure", "very_sure"]}
            }
        }

    async def collect_structured_ranking(self, participant: ParticipantAgent, prompt: str):
        """Force structured JSON output from participant agent."""
        structured_prompt = f"""
        {prompt}

        You MUST respond with valid JSON matching this exact format:
        {{
            "rankings": [
                {{"principle": "principle_name", "rank": 1}},
                {{"principle": "principle_name", "rank": 2}},
                {{"principle": "principle_name", "rank": 3}},
                {{"principle": "principle_name", "rank": 4}}
            ],
            "certainty": "sure"
        }}
        """

        # Use structured output mode if available
        if hasattr(participant.agent, 'generate_structured'):
            return await participant.agent.generate_structured(
                prompt=structured_prompt,
                schema=self.ranking_schema
            )
        else:
            # Fallback to regular parsing with strict validation
            return await self.parse_with_strict_validation(participant, structured_prompt)
```

### **Category 4: Model-Specific Solutions**

#### **4.1 Model Capability Matching**
```python
class ModelSpecificPromptManager:
    """Tailor prompts to specific model capabilities."""

    MODEL_CONFIGS = {
        "google/gemini-2.5-pro": {
            "instruction_following": "excellent",
            "format_preference": "structured",
            "example_count": 1,
            "prompt_style": "detailed"
        },
        "google/gemma-3-12b-it": {
            "instruction_following": "good",
            "format_preference": "simple",
            "example_count": 2,
            "prompt_style": "step_by_step"
        },
        "google/gemini-2.5-flash-lite": {
            "instruction_following": "moderate",
            "format_preference": "template",
            "example_count": 3,
            "prompt_style": "explicit"
        }
    }

    def get_optimized_ranking_prompt(self, model_name: str) -> str:
        config = self.MODEL_CONFIGS.get(model_name, self.MODEL_CONFIGS["google/gemini-2.5-pro"])

        if config["prompt_style"] == "step_by_step":
            return self.build_step_by_step_prompt(config)
        elif config["prompt_style"] == "explicit":
            return self.build_explicit_prompt(config)
        else:
            return self.build_detailed_prompt(config)
```

#### **4.2 Temperature Optimization for Instructions**
```python
class InstructionOptimizedAgent:
    """Use different temperatures for different task types."""

    async def create_ranking_agent(self, base_config: AgentConfiguration) -> Agent:
        """Create agent optimized for instruction-following."""
        ranking_config = base_config.copy()

        # Lower temperature for better instruction following
        ranking_config.temperature = min(0.3, base_config.temperature)

        # Add instruction-following system prompt
        ranking_config.instructions = f"""
        {base_config.instructions}

        CRITICAL INSTRUCTION FOLLOWING RULES:
        - When asked to rank items, provide exactly the number of ranked items requested
        - When asked to choose one item, provide exactly one choice
        - Follow response format instructions precisely
        - Never confuse ranking tasks with choice tasks
        """

        return await create_agent_with_temperature_retry(
            agent_class=Agent,
            model_string=ranking_config.model,
            temperature=ranking_config.temperature,
            agent_kwargs={"instructions": ranking_config.instructions}
        )
```

### **Category 5: Hybrid & Advanced Solutions**

#### **5.1 Progressive Disclosure System**
```python
class ProgressiveRankingSystem:
    """Break ranking into progressive steps with validation."""

    async def collect_ranking_progressively(self, participant: ParticipantAgent) -> PrincipleRanking:
        # Stage 1: Understanding check
        understanding = await self.verify_task_understanding(participant)
        if not understanding:
            await self.provide_task_clarification(participant)

        # Stage 2: Practice round with feedback
        practice_ranking = await self.practice_ranking_with_feedback(participant)

        # Stage 3: Actual ranking with confidence
        return await self.collect_final_ranking_with_validation(participant)

    async def verify_task_understanding(self, participant: ParticipantAgent) -> bool:
        check_prompt = """
        Before we begin, please confirm your understanding:

        I will ask you to RANK all 4 principles from best to worst.
        This means you need to provide 4 numbered lines, like:
        1. principle_a
        2. principle_b
        3. principle_c
        4. principle_d

        Do you understand this format? Respond with just "YES" or "NO".
        """

        response = await Runner.run(participant.agent, check_prompt)
        return "YES" in response.final_output.upper()
```

#### **5.2 Error Detection & Recovery System**
```python
class ErrorRecoverySystem:
    """Detect common errors and provide targeted corrections."""

    ERROR_PATTERNS = {
        "choice_instead_of_ranking": {
            "pattern": r"I choose|I select|My choice is",
            "correction": "You provided a choice but I need a ranking. Please list all 4 principles numbered 1-4."
        },
        "incomplete_ranking": {
            "pattern": lambda resp: len(re.findall(r'^\d+\.', resp, re.MULTILINE)) < 4,
            "correction": "Your ranking is incomplete. Please provide exactly 4 numbered principles."
        },
        "duplicate_principles": {
            "pattern": lambda resp: self.has_duplicate_principles(resp),
            "correction": "You ranked the same principle multiple times. Each principle should appear exactly once."
        }
    }

    async def collect_with_error_recovery(self, participant: ParticipantAgent, prompt: str) -> str:
        max_attempts = 3

        for attempt in range(max_attempts):
            response = await Runner.run(participant.agent, prompt)
            text = response.final_output

            # Check for errors
            error_found = self.detect_errors(text)
            if not error_found:
                return text

            # Provide targeted correction
            correction_prompt = f"""
            {error_found['correction']}

            Original task: {prompt}

            Your previous response: "{text}"

            Please try again with the correct format.
            """
            prompt = correction_prompt  # Update prompt for next iteration

        raise ExperimentError(f"Could not collect valid ranking after {max_attempts} attempts")
```

#### **5.3 AI-Powered Format Coach**
```python
class FormatCoachingSystem:
    """Use a specialized AI coach to teach proper response formats."""

    def __init__(self):
        self.coach_agent = Agent(
            name="Format Coach",
            instructions="""You are a format coaching assistant. Your job is to help participants
            understand the difference between ranking tasks and choice tasks, and provide clear
            examples of correct response formats."""
        )

    async def provide_format_coaching(self, participant: ParticipantAgent, task_type: str,
                                    failed_response: str) -> str:
        coaching_prompt = f"""
        A participant in an experiment is struggling with response format for {task_type} tasks.

        Their incorrect response was: "{failed_response}"

        Please provide:
        1. Clear explanation of what they did wrong
        2. Exact format they should use
        3. A concrete example of a correct response
        4. Encouraging guidance to try again

        Be supportive but very specific about the format requirements.
        """

        coaching_result = await Runner.run(self.coach_agent, coaching_prompt)
        return coaching_result.final_output
```

---

## 🎯 **Recommended Implementation Strategy**

### **Phase 1: Quick Wins (Week 1)**
1. **Enhanced Format Examples** (Solution 1.1) - Add explicit good/bad examples to ranking prompts
2. **Visual Prompt Differentiation** (Solution 1.2) - Make ranking vs choice prompts visually distinct
3. **Immediate Response Validation** (Solution 2.1) - Add format validation before utility agent parsing

### **Phase 2: Robust Improvements (Week 2-3)**
4. **Multi-Stage Prompting** (Solution 2.2) - Implement validation and correction loops
5. **Smart Fallback Parsing** (Solution 2.3) - Handle edge cases gracefully
6. **Model-Specific Optimization** (Solution 4.1) - Tailor prompts to model capabilities

### **Phase 3: Advanced Features (Week 4+)**
7. **Interactive Collection** (Solution 3.2) - Step-by-step ranking collection for difficult cases
8. **Error Recovery System** (Solution 5.2) - Automated error detection and targeted corrections

---

## 📊 **Expected Impact Analysis**

| Solution | Implementation Effort | Expected Success Rate Improvement | Risk Level |
|----------|----------------------|-----------------------------------|------------|
| Enhanced Format Examples | Low | +40% (36% → 76%) | Very Low |
| Visual Differentiation | Low | +20% (additional) | Very Low |
| Response Validation | Medium | +15% (additional) | Low |
| Multi-Stage Prompting | Medium | +10% (additional) | Medium |
| Smart Fallback | High | +5% (additional) | Medium |

**Projected Total Success Rate**: 85-90% (from current 36%)

---

## ✅ **Success Metrics**

1. **Primary**: Experiment completion rate >85%
2. **Secondary**: Reduction in "Invalid ranking structure" errors >90%
3. **Tertiary**: Participant agent instruction-following accuracy >95%
4. **Quality**: Ranking responses contain meaningful preference ordering

---

*This solution framework provides multiple approaches from simple prompt engineering to sophisticated AI coaching systems, allowing for incremental improvement and fallback strategies.*