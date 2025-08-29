# AI Agent Prompts vs Original Human Instructions: Comprehensive Comparison Report

## Executive Summary

This report provides a detailed comparison between the AI agent prompts used in "complex" mode for English and the original human experiment instructions from Frohlich & Oppenheimer's 1992 baseline experiment. The analysis reveals both faithful adaptations and several important deviations that may introduce unintended bias or alter experimental outcomes.

**Key Findings:**
- Justice principle definitions need alignment with original handbook wording
- Phase 1 procedures maintain experimental integrity with minor adjustments needed
- Phase 2 shows intentional adaptations for AI implementation (by design)
- AI-specific features like memory management and enhanced stakes emphasis are intentional design choices
- Current voting and discussion systems are kept as implemented

---

## 1. Justice Principle Definitions Comparison

### 1.1 Maximizing the Floor Income

**Original Handbook:** 
> "The most just distribution of income is that which maximizes the floor (or lowest) income in the society. This principle considers only the welfare of the worst-off individual in society. In judging among income distributions, the distribution which ensures the poorest person the highest income is the most just. No person's income can go up unless it increases the income of the people at the very bottom."

**AI Agent Prompt (Current):**
> "Maximizing the floor income: Choose the distribution that maximizes the lowest income in society"

**Recommended Update:**
> "The most just distribution of income is that which maximizes the floor (or lowest) income in the society. This principle considers only the welfare of the worst-off individual in society. In judging among income distributions, the distribution which ensures the poorest person the highest income is the most just. No person's income can go up unless it increases the income of the people at the very bottom."

**Analysis:** 📝 **TO BE UPDATED** - Replace current simplified version with complete original handbook wording for maximum fidelity.

### 1.2 Maximizing the Average Income

**Original Handbook:**
> "The most just distribution of income is that which maximizes the average income in the society. For any society maximizing the average income maximizes the total income in the society."

**AI Agent Prompt (Current):**
> "Maximizing the average income: Choose the distribution that maximizes the average income"

**Recommended Update:**
> "The most just distribution of income is that which maximizes the average income in the society. For any society maximizing the average income maximizes the total income in the society."

**Analysis:** 📝 **TO BE UPDATED** - Replace current version with complete original handbook wording including the explanation about total income.

### 1.3 Maximizing the Average with Floor Constraint

**Original Handbook:**
> "The most just distribution of income is that which maximizes the average income only after a certain specified minimum income is guaranteed to everyone. Such a principle ensures that the attempt to maximize the average is constrained so as to ensure that individuals 'at the bottom' receive a specified minimum. To choose this principle one must specify the value of the floor (lowest income)."

**AI Agent Prompt (Current):**
> "Maximizing the average income with a floor constraint: Maximize average income while ensuring everyone gets at least a specified minimum"

**Recommended Update:**
> "The most just distribution of income is that which maximizes the average income only after a certain specified minimum income is guaranteed to everyone. Such a principle ensures that the attempt to maximize the average is constrained so as to ensure that individuals 'at the bottom' receive a specified minimum. To choose this principle one must specify the value of the floor (lowest income)."

**Analysis:** 📝 **TO BE UPDATED** - Replace with complete original wording that better explains the constraint mechanism.

### 1.4 Maximizing the Average with Range Constraint

**Original Handbook:**
> "The most just distribution of income is that which attempts to maximize the average income only after guaranteeing that the difference between the poorest and the richest individuals (i.e., the range of income) in the society is not greater than a specified amount. Such a principle ensures that the attempt to maximize the average does not allow income differences between rich and poor to exceed a specified amount. To choose this principle one must specify the dollar difference between the high and low incomes."

**AI Agent Prompt (Current):**
> "Maximizing the average income with a range constraint: Maximize average income while keeping the gap between richest and poorest within a specified limit"

**Recommended Update:**
> "The most just distribution of income is that which attempts to maximize the average income only after guaranteeing that the difference between the poorest and the richest individuals (i.e., the range of income) in the society is not greater than a specified amount. Such a principle ensures that the attempt to maximize the average does not allow income differences between rich and poor to exceed a specified amount. To choose this principle one must specify the dollar difference between the high and low incomes."

**Analysis:** 📝 **TO BE UPDATED** - Replace with complete original wording that explicitly defines "range of income" and constraint specification requirements.

---

## 2. Phase 1 Comparison

### 2.1 Initial Principle Ranking

**Original Handbook:**
> "Rank order, according to your preferences, the following 4 principles of distributive justice by placing the letters (a), (b), (c), (d), signifying the principles, in the blanks below. Indicate ties by placing the tied principles in the same space."
> 
> Certainty scale: "very unsure, unsure, no opinion, sure, very sure"

**AI Agent Prompt (Current):**
> "You will be asked to rank these four justice principles from best (1) to worst (4) based on your preference. For each principle, also indicate your certainty level (very unsure, unsure, no opinion, sure, very sure). Explain your reasoning clearly."

**Recommended Update:**
> "You will be asked to rank these four justice principles from best (1) to worst (4) based on your preference. For each principle, also indicate your certainty level (very unsure, unsure, no opinion, sure, very sure)."

**Analysis:** 📝 **TO BE UPDATED** - Remove "Explain your reasoning clearly" to match the original's approach of not explicitly requiring reasoning explanations.

### 2.2 Application Rounds Instructions

**Original Handbook:**
> "You are to make a choice from among the four principles of justice which are mentioned above: (a) maximizing the floor, (b) maximizing the average, (c) maximizing the average with a floor constraint, and (d) maximizing the average with a range constraint. If you choose (c) or (d), you will have to tell us what that floor or range constraint is before you can be said to have made a well-defined choice."

**AI Agent Prompt:**
> "You are to make a choice from among the four principles of justice which are mentioned above: (a) maximizing the floor, (b) maximizing the average, (c) maximizing the average with a floor constraint, and (d) maximizing the average with a range constraint. If you choose (c) or (d), you will have to tell us what that floor or range constraint is before you can be said to have made a well-defined choice."

**Analysis:** ✅ **IDENTICAL** - This is exactly the same wording as the original experiment.

### 2.3 Payoff Structure

**Original Handbook:**
> "You will then receive one dollar for each $10,000 received by a member of the income class you have been assigned to."

**AI Agent Prompt:**
> "Your earnings will be $1 for every $10,000 of income you receive."

**Analysis:** ✅ **FAITHFUL** - Same payoff structure with slight rewording for clarity.

---

## 3. Phase 2 (Group Discussion) Comparison

### 3.1 Stakes Explanation

**Original Handbook:** 
> "Your payoffs in this section of the experiment will conform to the principle which you, as a group, adopt. If you, as a group, do not adopt any principle, then we will select one of the income distributions at random for you as a group. That choice of income distribution will conform to no particular characteristics."

**AI Agent Prompt (Current):**
> "**IMPORTANT: The stakes are much higher in this phase than in Phase 1.** This group decision will determine everyone's final earnings and has far greater consequences than your individual Phase 1 choices."

**Recommended Combined Wording:**
> "**IMPORTANT: The stakes are much higher in this phase than in Phase 1.** Your payoffs in this section of the experiment will conform to the principle which you, as a group, adopt. This group decision will determine everyone's final earnings and has far greater consequences than your individual Phase 1 choices. If you, as a group, do not adopt any principle, then we will select one of the income distributions at random for you as a group. That choice of income distribution will conform to no particular characteristics."

**Analysis:** ✅ **INTENTIONAL DESIGN** - Combine both versions to maintain original information while emphasizing the importance of Phase 2 for AI agents. The emphasis on higher stakes is needed and by design.

### 3.2 Voting Procedures

**Original Handbook:**
> "The group will adopt a principle if, and only if, that principle is able to secure the unanimous support of the group against all other principles... The principles are to be voted upon, two at a time. Only that principle which gets unanimous support in two-way contests against all other principles is actually adopted by the group."

**AI Agent Prompt (Complex Mode):**
> "COMPLEX VOTING SYSTEM: - Discuss your reasoning and thoughts about the principles - When you feel ready to vote, express your desire: 'I think we should vote' or 'Let's vote on this' or 'Ready to vote' - If voting is initiated, all participants must confirm agreement to proceed - Secret ballots will be cast if everyone agrees to vote - Consensus requires unanimous agreement in the secret ballot"

**Analysis:** ✅ **INTENTIONAL ADAPTATION** - The AI system uses a different but functionally equivalent voting mechanism:
- **Original:** Pairwise comparisons with unanimous support required
- **AI:** Single secret ballot with unanimous agreement required

This procedural change is intentionally designed for AI implementation efficiency while maintaining the core requirement of unanimous agreement.

### 3.3 Discussion Rules

**Original Handbook:**
> "You are not restricted, in any way, to the four principles of justice mentioned above. Thus, you can discuss (and later adopt) other principles. Any one of you can introduce and begin discussion of any principle."

**AI Agent Prompt:** 
> No equivalent provision found in the AI prompts.

**Analysis:** ✅ **INTENTIONAL SCOPE** - The AI system focuses on the four original principles, which maintains experimental consistency and avoids complications that alternative principle proposals might introduce in an AI context.

---

## 4. Potential Bias and Nudging Analysis

### 4.1 Emphasis on Stakes and Consequences

**Design Features:**
1. **Repeated emphasis on "higher stakes"** in Phase 2 helps AI agents understand importance 
2. **Bold formatting and capitalization** ("**IMPORTANT**") ensures attention
3. **Explicit comparison** between Phase 1 and Phase 2 consequences clarifies structure

**Rationale:** This emphasis is intentionally designed to ensure AI agents appropriately weight the importance of Phase 2 group decisions, compensating for their different risk perception compared to human participants.

### 4.2 Reasoning Requirements

**Current Implementation:**
1. **"Explain your reasoning clearly"** in ranking tasks - TO BE REMOVED
2. **Structured response formats** - KEEP AS IS
3. **Internal reasoning prompts** in complex mode - KEEP AS IS

**Rationale:** Remove explicit reasoning requirements from rankings to match original spontaneity, but maintain structured formats and internal reasoning prompts as they are essential for AI agent functionality and response parsing.

### 4.3 Personality Instructions

**Current Implementation:**
1. **"Stay true to your personality"** instructions throughout - TO BE REMOVED
2. **Personality descriptions** influence responses - KEEP AS IS
3. **"Maintain your assigned personality"** reminders - TO BE REMOVED

**Rationale:** Keep personality descriptions as they provide necessary behavioral context for AI agents, but remove explicit personality maintenance reminders to reduce artificial constraints.

### 4.4 Memory Management

**Design Features:**
1. **Explicit memory update instructions**
2. **"Include important information from previous memory"**
3. **Memory compression guidance**

**Rationale:** Memory management is essential for AI agent functionality and maintaining continuity across the experiment phases. This is an intentional design choice to ensure proper AI agent operation.

---

## 5. Structural Changes in Implementation

### 5.1 Voting Detection Mode

**Original:** Clear procedural rules for when votes occur
**AI:** Relies on natural language processing to detect voting intentions

**Rationale:** Natural language processing for voting detection is necessary for AI implementation and is designed with appropriate safeguards.

### 5.2 Response Parsing

**Original:** Human-interpreted responses
**AI:** Automated parsing with specific format requirements

**Rationale:** Automated parsing with format requirements is necessary for AI implementation while maintaining experimental validity.

### 5.3 Error Handling

**Original:** Moderator intervention for errors
**AI:** Automated re-prompting and format correction

**Rationale:** Automated error handling ensures consistent experimental administration and prevents experiment failures.

---



---

## 7. Implementation Actions Required

### 7.1 Critical Updates to Implement

1. **Update all four justice principle definitions** to use complete original handbook wording
2. **Remove "Explain your reasoning clearly"** from ranking prompts
3. **Combine Phase 2 stakes explanation** using both original and AI emphasis wording
4. **Remove explicit personality maintenance reminders** while keeping personality descriptions

### 7.2 Current Implementation to Maintain

1. **Complex voting system with secret ballots** - intentionally designed for AI implementation
2. **Memory management instructions** - essential for AI agent functionality
3. **Structured response formats** - necessary for automated parsing
4. **Internal reasoning prompts** - important for AI decision-making transparency
5. **Enhanced stakes emphasis** - needed to ensure AI agents understand Phase 2 importance
6. **Focus on four original principles** - maintains experimental consistency

### 7.3 Design Rationale Confirmed

1. **Automated error handling** - prevents experiment failures
2. **Natural language voting detection** - enables flexible AI interaction
3. **Response parsing requirements** - ensures data validity
4. **Memory capabilities** - provides necessary continuity for AI agents

---

## 8. Conclusion

The AI implementation successfully adapts the core experimental design from the original human experiment while making intentional modifications necessary for AI agent functionality. Most structural changes are deliberate design choices rather than deviations requiring correction.

**Key Actions Required:**
1. **Update justice principle definitions** to use complete original handbook wording for maximum fidelity
2. **Remove explicit reasoning requirements** from ranking tasks to match original spontaneity
3. **Refine personality instruction approach** by removing maintenance reminders while keeping descriptions
4. **Implement combined stakes explanation** that includes both original content and AI-specific emphasis

**Intentional Design Choices to Maintain:**
1. **Enhanced stakes emphasis** - ensures AI agents appropriately weight Phase 2 importance
2. **Secret ballot voting system** - functionally equivalent to original while suited for AI implementation
3. **Memory management capabilities** - essential for AI agent continuity and functionality
4. **Structured response formats** - necessary for automated data processing and validation

**Overall Assessment:** The implementation maintains experimental integrity while making appropriate adaptations for AI agents. The identified changes will enhance fidelity to the original while preserving the technical functionality essential for successful AI-based replication.

---

*Report generated on August 27, 2025*
*Analysis covers AI prompts in "complex" mode for English language*