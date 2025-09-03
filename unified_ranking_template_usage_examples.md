# Unified Ranking Prompt Template Usage Examples

This document demonstrates how the new `unified_ranking_prompt_template` can replace all existing ranking prompt templates across different languages and scenarios.

## Template Parameters

The unified template accepts two parameters:
- `{context_description}`: Describes the context of the ranking (initial, post-explanation, final, etc.)
- `{additional_instructions}`: Optional additional context-specific instructions

## Usage Examples

### 1. Phase 1 Initial Ranking (replacing `phase1_initial_ranking_prompt_template`)

**Context Description:**
```
This is your first time ranking these four justice principles based on your initial understanding.
```

**Additional Instructions:**
```
(empty or basic instructions)
```

### 2. Phase 1 Post-Explanation Ranking (replacing `phase1_post_explanation_ranking_prompt`)

**Context Description:**
```
After learning how each justice principle is applied to income distributions, please rank the four principles again.
```

**Additional Instructions:**
```
(empty or basic instructions)
```

### 3. Phase 1 Final Ranking (replacing `phase1_final_ranking_after_experience`)

**Context Description:**
```
After experiencing the four rounds of principle application, rank these principles again from best (1) to worst (4).
Reflect on what you learned from applying these principles and how it may have changed your preferences.
```

**Additional Instructions:**
```
Then explain how your experience in the four application rounds influenced your ranking.
```

### 4. Phase 2 Final Ranking (replacing `phase2_final_ranking_prompt`)

**Context Description:**
```
You will be asked to rank these four justice principles based on your experience in the group discussion phase.
```

**Additional Instructions:**
```
(empty or basic instructions)
```

## Template Benefits

1. **Consistency**: All ranking prompts now use identical principle descriptions and response formats
2. **Maintainability**: Changes to principle descriptions only need to be made in one place per language
3. **Flexibility**: Context-specific instructions can be added without duplicating core content
4. **Internationalization**: Each language has its own unified template with proper translations
5. **Reduced Complexity**: From 4+ different ranking templates down to 1 unified template

## Implementation Notes

- The template includes complete principle descriptions in each language
- Response format is standardized across all ranking scenarios
- Examples are provided to guide consistent formatting
- Template parameters allow for context-specific customization
- All existing ranking scenarios can be handled with appropriate parameter values