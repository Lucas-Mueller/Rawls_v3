Cultural Adaptation & Multilingual Support
===========================================

The Frohlich Experiment provides comprehensive cultural adaptation utilities to ensure consistent and culturally appropriate behavior across different languages and cultural contexts. This documentation covers multilingual number formatting, language formality levels, and cultural context handling.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
--------

The cultural adaptation system ensures that experiments maintain consistency and appropriateness across different cultural and linguistic contexts. This is particularly important for economic experiments where number formatting, formality levels, and cultural references must be handled correctly.

.. code-block:: text

   Cultural Adaptation System
   ├── Language Support
   │   ├── English (primary)
   │   ├── Spanish (full support)
   │   └── Mandarin (full support)
   │
   ├── Amount Formatting
   │   ├── Currency symbols by culture
   │   ├── Number formatting conventions
   │   └── Thousand separators and decimals
   │
   ├── Formality Levels
   │   ├── Formal register
   │   ├── Neutral register
   │   └── Informal register
   │
   └── Cultural Context
       ├── Language-specific prompts
       ├── Culturally appropriate examples
       └── Context-aware translations

Supported Languages
-------------------

The system provides full experimental support for three languages:

**English (Primary Language)**
   - Default language for system operations
   - US English conventions for numbers and currency
   - Neutral formality level as baseline

**Spanish (Full Support)**
   - Complete Spanish translations for all prompts
   - Spanish number formatting conventions
   - Culturally appropriate examples and context
   - Support for both European and Latin American Spanish variants

**Mandarin (Full Support)**
   - Complete Mandarin Chinese translations
   - Chinese number formatting conventions
   - Culturally appropriate economic examples
   - Support for simplified characters

Amount Formatting
-----------------

The AmountFormattingManager handles culture-specific number and currency formatting:

.. code-block:: python

   from utils.cultural_adaptation import AmountFormattingManager, SupportedLanguage

   # Initialize formatter
   formatter = AmountFormattingManager()

   # Format amounts by language
   english_amount = formatter.format_amount(15000, SupportedLanguage.ENGLISH)
   # Returns: "$15,000"

   spanish_amount = formatter.format_amount(15000, SupportedLanguage.SPANISH)
   # Returns: "$15.000" (Spanish convention uses periods for thousands)

   mandarin_amount = formatter.format_amount(15000, SupportedLanguage.MANDARIN)
   # Returns: "$15,000" (Western convention maintained for clarity)

**Formatting Rules by Language:**

- **English**: "$15,000.00" (comma separators, period decimals)
- **Spanish**: "$15.000,00" (period separators, comma decimals)
- **Mandarin**: "$15,000.00" (Western format for experimental consistency)

**Key Features:**

- Automatic thousand separators according to cultural conventions
- Consistent decimal handling across languages
- Currency symbol standardization ($ for all languages in experiments)
- Error handling for invalid amounts

Number Parsing
--------------

The system can parse numbers in multiple cultural formats:

.. code-block:: python

   # Parse various number formats
   parsed_english = formatter.parse_amount("$15,000.50")     # 15000.50
   parsed_spanish = formatter.parse_amount("$15.000,50")     # 15000.50
   parsed_mandarin = formatter.parse_amount("$15,000.50")    # 15000.50

   # Handle different thousand separators
   flexible_parse = formatter.parse_flexible_amount("15000.50")  # 15000.50
   flexible_parse = formatter.parse_flexible_amount("15,000.50") # 15000.50
   flexible_parse = formatter.parse_flexible_amount("15.000,50") # 15000.50

**Parsing Capabilities:**

- Multiple thousand separator formats (comma, period, space)
- Various decimal separator formats (period, comma)
- Currency symbol recognition and removal
- Flexible whitespace handling
- Error recovery for malformed inputs

Formality Levels
----------------

The system supports different language formality levels for appropriate agent communication:

.. code-block:: python

   from utils.cultural_adaptation import FormalityLevel, FormalityManager

   formality_manager = FormalityManager()

   # Adjust formality based on context
   formal_text = formality_manager.adjust_formality(
       "Please provide your answer",
       FormalityLevel.FORMAL,
       SupportedLanguage.ENGLISH
   )

   neutral_text = formality_manager.adjust_formality(
       "Please provide your answer",
       FormalityLevel.NEUTRAL,
       SupportedLanguage.ENGLISH
   )

   informal_text = formality_manager.adjust_formality(
       "Please provide your answer",
       FormalityLevel.INFORMAL,
       SupportedLanguage.ENGLISH
   )

**Formality Levels:**

- **Formal**: Respectful, professional language ("Please provide your response")
- **Neutral**: Standard, balanced communication (default)
- **Informal**: Casual, conversational tone ("Give me your answer")

Language Register Adaptation
-----------------------------

The cultural adaptation system adjusts language register based on experimental context:

.. code-block:: python

   # Economic context adaptation
   economic_formal = formality_manager.adapt_for_context(
       "economic_decision",
       FormalityLevel.FORMAL,
       SupportedLanguage.SPANISH
   )

   # Discussion context adaptation
   discussion_neutral = formality_manager.adapt_for_context(
       "group_discussion",
       FormalityLevel.NEUTRAL,
       SupportedLanguage.MANDARIN
   )

**Context Types:**

- **economic_decision**: Formal, precise language for financial decisions
- **group_discussion**: Balanced formality for collaborative dialogue
- **principle_explanation**: Educational, explanatory tone
- **voting_procedure**: Clear, procedural language

Cultural Context Integration
-----------------------------

Integration with the language manager for comprehensive cultural adaptation:

.. code-block:: python

   from utils.language_manager import get_language_manager

   # Get language manager with cultural adaptation
   lang_manager = get_language_manager("spanish")

   # Format culturally appropriate economic examples
   economic_example = lang_manager.get_cultural_example(
       "income_distribution",
       amount=25000,
       formality=FormalityLevel.NEUTRAL
   )

   # Returns Spanish-appropriate example with correct formatting

**Cultural Integration Features:**

- Language-specific economic examples
- Culturally appropriate metaphors and analogies
- Context-aware terminology selection
- Regional variant handling (e.g., European vs Latin American Spanish)

Two-Stage Voting Integration
-----------------------------

The cultural adaptation system integrates with the two-stage voting system:

.. code-block:: python

   from core.two_stage_voting_manager import TwoStageVotingManager

   # Voting manager with cultural adaptation
   voting_manager = TwoStageVotingManager(
       language_manager=lang_manager,
       amount_formatter=formatter
   )

   # Parse culturally diverse voting responses
   english_vote = voting_manager.parse_vote("I choose principle 3 with $25,000 floor", "english")
   spanish_vote = voting_manager.parse_vote("Elijo el principio 3 con $25.000 piso", "spanish")

   # Both parsed correctly despite different formatting

**Voting Integration Benefits:**

- Multilingual number recognition in voting
- Culture-specific amount parsing
- Consistent validation across languages
- Error recovery for cultural formatting differences

Configuration Examples
----------------------

**Basic Cultural Configuration:**

.. code-block:: yaml

   # Experiment configuration with cultural adaptation
   language: "spanish"

   agents:
     - name: "Agente_Analítico"
       personality: "Eres analítico y metódico en español"
       model: "gpt-4.1-mini"
       language: "spanish"

   # Cultural adaptation settings
   cultural_adaptation:
     formality_level: "neutral"
     amount_formatting: true
     cultural_context: true

**Advanced Multilingual Experiment:**

.. code-block:: yaml

   # Multi-language experiment with full cultural adaptation
   language: "english"  # Base language

   agents:
     - name: "English_Agent"
       language: "english"
       formality_level: "neutral"

     - name: "Spanish_Agent"
       language: "spanish"
       formality_level: "formal"

     - name: "Mandarin_Agent"
       language: "mandarin"
       formality_level: "neutral"

   # Enable full cultural adaptation
   enable_cultural_adaptation: true
   adapt_formality_by_context: true
   format_amounts_culturally: true

Best Practices
--------------

**Language Consistency:**
- Use consistent formality levels within single experiments
- Maintain base language for system operations and results
- Validate translations for economic terminology accuracy

**Cultural Sensitivity:**
- Test examples with native speakers when possible
- Consider regional variations within languages
- Ensure economic concepts translate appropriately

**Performance Considerations:**
- Cultural adaptation adds minimal computational overhead
- Formatting operations are highly optimized
- Caching prevents repeated adaptation operations

**Testing Cultural Adaptation:**

.. code-block:: python

   # Test cultural adaptation functionality
   def test_cultural_adaptation():
       formatter = AmountFormattingManager()

       # Test amount formatting across languages
       assert formatter.format_amount(15000, SupportedLanguage.ENGLISH) == "$15,000"
       assert formatter.format_amount(15000, SupportedLanguage.SPANISH) == "$15.000"

       # Test parsing flexibility
       assert formatter.parse_flexible_amount("$15,000") == 15000
       assert formatter.parse_flexible_amount("$15.000") == 15000

       print("✅ Cultural adaptation tests passed")

Troubleshooting
---------------

**Common Issues:**

1. **Number Parsing Failures:**
   - Check for mixed separator conventions
   - Verify currency symbol placement
   - Ensure consistent decimal handling

2. **Language Register Mismatches:**
   - Validate formality level appropriateness
   - Check context-specific adaptations
   - Review cultural context accuracy

3. **Translation Inconsistencies:**
   - Cross-reference with native speakers
   - Validate economic terminology
   - Test with diverse cultural examples

**Debug Information:**

.. code-block:: python

   # Enable debug logging for cultural adaptation
   import logging
   logging.getLogger('utils.cultural_adaptation').setLevel(logging.DEBUG)

   # Test specific formatting
   formatter = AmountFormattingManager()
   result = formatter.format_amount(12345.67, SupportedLanguage.SPANISH)
   print(f"Formatted: {result}")  # Debug output shows formatting steps

This cultural adaptation system ensures that the Frohlich Experiment maintains scientific validity and cultural appropriateness across all supported languages and contexts.

See Also
--------

- :doc:`getting-started/installation` - Installation with language support
- :doc:`user-guide/running-experiments` - Running multilingual experiments
- :doc:`user-guide/designing-experiments` - Designing culturally appropriate experiments
- ``translations/`` - Translation files for all supported languages
- :doc:`phase2-settings` - Phase 2 configuration for multilingual support