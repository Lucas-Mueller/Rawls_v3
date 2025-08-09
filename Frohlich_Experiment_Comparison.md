# Frohlich-Oppenheimer Experiment: Original vs. Current AI Implementation

This document provides a detailed comparison between the original Frohlich-Oppenheimer experiment and its current multi-agent AI implementation. Each section follows the format: Original Procedure → Current Implementation → Analysis.

## Overview

### Original Frohlich-Oppenheimer Experiment
The original experiment was conducted with groups of five university students in physical rooms across Canada, Poland, and the United States. The study examined how individuals choose principles of distributive justice when faced with uncertainty about their own position in the resulting income distribution.

### Current AI Implementation  
The current system simulates this experiment using AI agents that can be configured with different personalities, models, and parameters. The experiment maintains the same two-phase structure but adapts the methodology for multi-agent AI systems.

**MAJOR DEVIATION**: The original was designed for human psychology and decision-making under uncertainty, while the current version simulates human-like reasoning in AI agents without the same psychological drivers.

---

## Phase 1: Individual Familiarization

### 1.1 Orientation and Comprehension

#### Original Procedure
- Participants read a two-page printed overview
- Strict ranking of four principles (no ties allowed)
- Comprehension gate with second version if failed
- Targeted clarification of specific misunderstandings

#### Current Implementation
- Agents receive principle definitions in prompts
- Initial ranking with certainty scale (1-5: very unsure to very sure)
- No comprehension gate - assumes agents understand immediately
- Utility agent processes rankings for validation

#### Analysis
**ASSUMPTION**: Current system assumes AI agents will understand principles perfectly without comprehension checking.
**DEVIATION**: No formal comprehension validation or retry mechanism for understanding failures.

### 1.2 Sample Task Illustration

#### Original Procedure
- Sample task illustrated how chosen rules select unique five-class distributions
- Explained why constrained rules need numeric specifications
- Used specific example table for walkthrough

#### Current Implementation
- Agents shown example table with four income distributions
- Explained how each principle would select from examples
- Same example distributions as original (maintaining comparability)

#### Analysis
**FAITHFUL IMPLEMENTATION**: This step closely matches the original design.

### 1.3 Incentivized Individual Choices (4 Rounds)

#### Original Procedure
- Four independent choice situations
- Opaque draw bags with assignment chits for income class assignment
- Physical chit drawing in view of participant
- Cash conversion: $1 for every $10,000 household income
- Chits kept by participants for later reflection
- Draws made with replacement to prevent frequency learning

#### Current Implementation
- Four rounds of principle applications
- Random assignment to income classes (simulated)
- Same cash conversion rate ($1 per $10,000)
- Dynamic distributions with configurable multiplier (0.5-2.0 default)
- Agents told what they would have received under other principles

#### Analysis
**MAJOR PROBLEM**: **Physical uncertainty mechanism lost** - Original used physical chit draws that participants could see and feel, creating real uncertainty about class assignment. Current system uses computational randomization without the same psychological impact.

**DEVIATION**: No physical artifacts for agents to "keep" and reflect upon during group phase.

**ASSUMPTION**: AI agents will respond to monetary incentives similarly to humans despite not experiencing financial pressure.

### 1.4 Assignment Mechanism

#### Original Procedure
- Chit composition undisclosed and non-inferrable
- Independence across draws maintained
- Opacity and non-informative appearance required

#### Current Implementation
- Pure random assignment to income classes
- No mechanism to prevent inference of assignment probabilities
- Computational rather than physical randomization

#### Analysis
**MAJOR PROBLEM**: **Loss of true uncertainty** - Original's physical opacity created genuine uncertainty that influenced decision-making. Current system's computational randomization lacks this psychological element.

---

## Phase 2: Group Deliberation

### 2.1 Collective Deliberation Process

#### Original Procedure
- Minimum 5 minutes discussion required
- Could not close without unanimous consent via secret ballot
- Any participant could restart discussion
- Open agenda allowing novel formulations
- Unanimous support required to proceed to payment
- Higher stakes explicitly mentioned before group phase

#### Current Implementation
- Maximum number of rounds set in configuration (not minimum time)
- Randomized speaking order with restrictions (same agent can't end/start consecutive rounds)
- Agent reasoning step (optional, enabled by default)
- Vote proposal requires all agents' agreement to trigger voting
- Unanimous agreement required for consensus

#### Analysis
**MAJOR PROBLEM**: **Time-based vs Round-based deliberation** - Original used minimum time requirements allowing for natural conversation flow. Current uses fixed round limits that may cut off important deliberation.

**DEVIATION**: Original's "any participant can restart" vs current's structured turn-taking system fundamentally changes group dynamics.

**ASSUMPTION**: AI agents will engage in meaningful deliberation within structured turn-taking rather than free-flowing discussion.

### 2.2 Voting Mechanism

#### Original Procedure
- Secret ballots among items on fixed agenda
- If no unanimous winner, discussion resumed
- Only consensus guaranteed distributional properties group endorsed

#### Current Implementation
- Secret ballot system maintained
- Invalid ballots (missing constraint amounts) handled by utility agent
- Agent can re-vote if ballot invalid
- Same consensus requirement for principle adoption

#### Analysis
**FAITHFUL IMPLEMENTATION**: Voting mechanism closely matches original design.

### 2.3 Payment Implementation

#### Original Procedure
- Hidden set of five-class payoff vectors filtered by chosen rule
- Random vector drawn from filtered set
- Random class assignment within chosen vector
- If no unanimity, draw from unfiltered set (making consensus valuable)

#### Current Implementation
- New distribution set generated with multiplier
- Same random assignment mechanism
- Same incentive structure for reaching consensus
- Agents told what they would have received under competing distributions

#### Analysis
**FAITHFUL IMPLEMENTATION**: Payment mechanism maintains original incentive structure.

---

## Additional Original Features Not Implemented

### Production Extension
#### Original Procedure
- Separate series with earned income from proofreading task
- Explicit tax/transfer schedules shown
- Three rounds of production work
- Increasing marginal returns for productivity

#### Current Implementation
- **NOT IMPLEMENTED**

#### Analysis
**MAJOR PROBLEM**: **Missing production variant** - This was a significant part of the original experiment testing how principles work under earned (vs assigned) income.

### Framing Manipulations
#### Original Procedure  
- Higher-variance tables to make worst outcomes more salient
- Loss frame (starting with $40 credit, showing reductions)
- Neutral language variant removing "justice" terminology

#### Current Implementation
- **NOT IMPLEMENTED** (though configurable distributions exist)

#### Analysis
**DEVIATION**: Missing important experimental controls for testing robustness of choices across different framings.

### Decision Rule Treatments
#### Original Procedure
- Unanimity with discussion
- Simple majority voting
- Imposed policy without discussion

#### Current Implementation
- Only unanimity requirement implemented

#### Analysis  
**DEVIATION**: Missing comparative treatments that were part of original experimental design.

---

## Technical Implementation Differences

### Physical vs Digital Environment
#### Original
- Separate desks in quiet room
- Printed materials and physical ballots
- Opaque draw bags with tactile chits
- Face-to-face group discussion

#### Current
- Digital multi-agent system
- Text-based interactions
- Computational randomization
- Structured turn-taking in "virtual room"

#### Analysis
**MAJOR PROBLEM**: **Loss of embodied experience** - Physical environment created psychological realism that may be crucial for decision-making under uncertainty.

### Participant Pool
#### Original
- University students (human subjects)
- 98 sessions across 3 countries
- Natural variation in personalities and backgrounds

#### Current
- AI agents with configured personalities
- Unlimited sessions possible
- Artificial personality variation through prompts

#### Analysis
**MAJOR PROBLEM**: **Artificial vs natural personality variation** - Current system simulates personality differences rather than capturing genuine human diversity in values and reasoning.

### Memory and Learning
#### Original
- Natural human memory with physical chits for reference
- Organic learning through experience
- Emotional responses to outcomes

#### Current
- Agent-managed digital memory (50,000 character limit)
- Structured memory updates after each step
- No emotional responses to monetary outcomes

#### Analysis
**ASSUMPTION**: AI agents' structured memory management will substitute for human memory and emotional learning processes.

---

## Language and Cultural Adaptations

### Original
- Conducted in multiple countries (Canada, Poland, US)
- Translation issues noted (Polish version had timing problems)
- Natural cultural variation in participants

### Current
- Multi-language support (English, Spanish, Mandarin)
- Translated prompts and agent instructions
- Configurable language settings

#### Analysis
**IMPROVEMENT**: Current system provides better language standardization and broader accessibility than original.

---

## Summary of Major Issues

### MAJOR PROBLEMS Identified:

1. **Physical uncertainty mechanism lost** - The tangible, opaque chit-drawing process created genuine uncertainty that computational randomization cannot replicate.

2. **Time-based vs Round-based deliberation** - Original's minimum time requirements vs current's maximum round limits fundamentally change discussion dynamics.

3. **Missing production variant** - A significant component testing earned vs assigned income principles is not implemented.

4. **Loss of embodied experience** - Physical environment and face-to-face interaction may be psychologically crucial for the experiment's validity.

5. **Artificial vs natural personality variation** - Simulated personalities may not capture genuine human diversity in moral reasoning.

### Key Assumptions Made:
- AI agents respond to monetary incentives like humans
- Structured turn-taking substitutes for free-flowing discussion  
- Digital memory management replaces human memory and learning
- Computational randomization creates equivalent uncertainty to physical processes
- Simulated personalities capture relevant human variation

### Faithful Implementations:
- Basic two-phase structure maintained
- Justice principle definitions preserved
- Voting and consensus mechanisms accurate
- Payment incentive structure maintained
- Multi-language support enhanced

The current implementation captures the formal structure of the Frohlich-Oppenheimer experiment well, but may miss crucial psychological and social elements that made the original experiment meaningful for understanding human decision-making under uncertainty.