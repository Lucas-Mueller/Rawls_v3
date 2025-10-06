"""
Language Manager for Multi-Language Support in Frohlich Experiment

This module handles loading and retrieving translated prompts and messages
based on the configured language setting.
"""

import json
import os
import logging
import random
import re
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class SupportedLanguage(Enum):
    """Supported languages for the experiment."""
    ENGLISH = "English"
    SPANISH = "Spanish"  
    MANDARIN = "Mandarin"


class LanguageManager:
    """Manages loading and retrieval of translated experiment content."""
    
    def __init__(self, translations_dir: str = "translations", seed: Optional[int] = None):
        """
        Initialize the language manager.
        
        Args:
            translations_dir: Directory containing translation JSON files
            seed: Random seed for deterministic example generation (optional)
        """
        self.translations_dir = translations_dir
        self.translations_cache: Dict[str, Dict[str, Any]] = {}
        self.current_language = SupportedLanguage.ENGLISH
        self.seed = seed
        
        # Language file mappings
        self.language_files = {
            SupportedLanguage.ENGLISH: "english_prompts.json",
            SupportedLanguage.SPANISH: "spanish_prompts.json", 
            SupportedLanguage.MANDARIN: "mandarin_prompts.json"
        }
    
    def set_language(self, language: SupportedLanguage) -> None:
        """
        Set the current language for the experiment.
        
        Args:
            language: The language to use for all prompts and messages
        """
        if not isinstance(language, SupportedLanguage):
            raise ValueError(f"Unsupported language: {language}")
        
        self.current_language = language
        logger.info(f"Language set to: {language.value}")
    
    def load_language(self, language: SupportedLanguage) -> Dict[str, Any]:
        """
        Load translations for a specific language.
        
        Args:
            language: Language to load
            
        Returns:
            Dictionary containing all translations for the language
            
        Raises:
            FileNotFoundError: If translation file doesn't exist
            json.JSONDecodeError: If translation file is invalid
        """
        if language in self.translations_cache:
            return self.translations_cache[language]
        
        filename = self.language_files[language]
        filepath = os.path.join(self.translations_dir, filename)
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"Translation file not found: {filepath}. "
                f"Run translate_prompts.py to generate translation files."
            )
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                translations = json.load(f)
            
            self.translations_cache[language] = translations
            logger.info(f"Loaded translations for {language.value}")
            return translations
            
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in translation file {filepath}: {e}",
                e.doc, e.pos
            )
    
    def get_current_translations(self) -> Dict[str, Any]:
        """
        Get translations for the current language.
        
        Returns:
            Dictionary containing all translations for current language
        """
        return self.load_language(self.current_language)
    
    def get(self, path: str, **format_kwargs) -> str:
        """
        Get a translated string using dot notation path.
        
        Args:
            path: Dot-separated path to the translation (e.g., "common.principle_names.maximizing_floor")
            **format_kwargs: Format arguments for template strings
            
        Returns:
            Translated and formatted string
            
        Raises:
            KeyError: If path doesn't exist
            ValueError: If formatting fails
        """
        try:
            translations = self.get_current_translations()
            
            # Navigate the path
            parts = path.split('.')
            current = translations
            
            for part in parts:
                if not isinstance(current, dict):
                    raise KeyError(f"Cannot navigate further in path '{path}' at '{part}'")
                current = current[part]
            
            # Ensure we have a string result
            if isinstance(current, dict):
                raise ValueError(
                    f"Path '{path}' points to a dictionary, not a string. "
                    f"Available keys: {list(current.keys())}"
                )
            
            # Check for principle list template substitution
            if isinstance(current, str):
                # Handle principle list templates
                if "{principle_list_detailed}" in current:
                    format_kwargs["principle_list_detailed"] = self.get_principle_list_formatted("detailed")
                if "{principle_list_simple}" in current:
                    format_kwargs["principle_list_simple"] = self.get_principle_list_formatted("simple")  
                # DEPRECATED - principle_list_letters template is deprecated, use names_only
                if "{principle_list_letters}" in current:
                    format_kwargs["principle_list_letters"] = self.get_principle_list_formatted("names_only")
                # Handle master principle descriptions template (uses master descriptions from translations)
                if "{master_principle_descriptions}" in current:
                    format_kwargs["master_principle_descriptions"] = self._get_master_principle_descriptions()
                # Handle individual principle name templates for detailed explanations
                if "{principle_name_floor}" in current:
                    format_kwargs["principle_name_floor"] = self.get("common.principle_names.maximizing_floor")
                if "{principle_name_average}" in current:
                    format_kwargs["principle_name_average"] = self.get("common.principle_names.maximizing_average")
                if "{principle_name_floor_constraint}" in current:
                    format_kwargs["principle_name_floor_constraint"] = self.get("common.principle_names.maximizing_average_floor_constraint")
                if "{principle_name_range_constraint}" in current:
                    format_kwargs["principle_name_range_constraint"] = self.get("common.principle_names.maximizing_average_range_constraint")
            
            # Format template if kwargs provided or if templates were substituted
            if format_kwargs:
                formatted_result = current.format(**format_kwargs)
            else:
                formatted_result = current
            
            return formatted_result
                
        except KeyError as e:
            raise KeyError(
                f"Translation path not found: '{path}' in {self.current_language.value}"
            )
        except (ValueError, KeyError) as e:
            raise ValueError(
                f"Failed to format translation at '{path}': {e}"
            )

    def get_prompt(self, category: str, prompt_key: str, **format_kwargs) -> str:
        """
        Get a translated prompt for the current language.
        
        Args:
            category: Category of prompt (e.g., 'phase1_instructions', 'system_messages')
            prompt_key: Specific prompt key within category
            **format_kwargs: Format arguments for template strings
            
        Returns:
            Translated and formatted prompt string
            
        Raises:
            KeyError: If category or prompt_key doesn't exist
            ValueError: If formatting fails
        """
        # Use the new dot notation API internally
        return self.get(f"{category}.{prompt_key}", **format_kwargs)
    
    def get_message(self, category: str, message_group: str, message_key: str, **format_kwargs) -> str:
        """
        Get a translated message from a message group (like error_messages).
        
        Args:
            category: Category containing the message group
            message_group: Group of messages (e.g., 'error_messages')  
            message_key: Specific message key within group
            **format_kwargs: Format arguments for template strings
            
        Returns:
            Translated and formatted message string
        """
        # Use the new dot notation API internally
        return self.get(f"{category}.{message_group}.{message_key}", **format_kwargs)
    
    def get_experiment_explanation(self) -> str:
        """Get the main experiment explanation."""
        return self.get("prompts.experiment_explanation")

    def get_initial_experiment_explanation(self) -> str:
        """Get the initial/detailed experiment explanation shown before first memory update."""
        return self.get("prompts.initial_experiment_explanation")

    def _generate_randomized_example(self) -> str:
        """
        Generate a randomized ranking example using the configured seed.
        
        Returns:
            Formatted example with randomly ordered principles
        """
        if self.seed is None:
            # Fallback to fixed order if no seed provided
            principles = [
                self.get("common.principle_names.maximizing_average_floor_constraint"),
                self.get("common.principle_names.maximizing_floor"), 
                self.get("common.principle_names.maximizing_average"),
                self.get("common.principle_names.maximizing_average_range_constraint")
            ]
        else:
            # Create deterministic random order based on seed
            principles = [
                self.get("common.principle_names.maximizing_floor"),
                self.get("common.principle_names.maximizing_average"),
                self.get("common.principle_names.maximizing_average_floor_constraint"), 
                self.get("common.principle_names.maximizing_average_range_constraint")
            ]
            
            # Use seed-based randomization for consistent results
            rng = random.Random(self.seed)
            rng.shuffle(principles)
        
        # Format as numbered example
        example_lines = []
        for i, principle in enumerate(principles, 1):
            example_lines.append(f"{i}. {principle}")
        
        return "\n".join(example_lines)
    
    def _get_master_principle_descriptions(self) -> str:
        """
        Get formatted master principle descriptions from translation file.
        Uses the master_principle_descriptions section for detailed explanations.
        
        Returns:
            Formatted list of master principle descriptions
        """
        try:
            # Get the master descriptions from the translation file
            floor_desc = self.get("master_principle_descriptions.maximizing_floor")
            avg_desc = self.get("master_principle_descriptions.maximizing_average")
            floor_c_desc = self.get("master_principle_descriptions.maximizing_average_floor_constraint")
            range_c_desc = self.get("master_principle_descriptions.maximizing_average_range_constraint")
            
            return f"""1. {floor_desc}

2. {avg_desc}

3. {floor_c_desc}

4. {range_c_desc}"""
            
        except KeyError:
            # Fallback to principle_list_detailed if master descriptions not available
            return self.get_principle_list_formatted("detailed")
    
    def get_phase1_instructions(self, round_number: int) -> str:
        """
        Get Phase 1 instructions for a specific round.
        
        Args:
            round_number: Round number (0, -1, 1-4, 5)
            
        Returns:
            Translated instructions for the round
        """
        if round_number == 0:
            return self.get("prompts.phase1_round0_initial_ranking")
        elif round_number == -1:
            return self.get("prompts.phase1_round_neg1_detailed_explanation")  
        elif 1 <= round_number <= 4:
            return self.get("prompts.phase1_rounds1_4_principle_application", 
                          round_number=round_number)
        elif round_number == 5:
            return self.get("prompts.phase1_round5_final_ranking")
        else:
            return self.get("prompts.fallback_default_phase_instructions")
    
    def get_phase2_instructions(self, round_number: int, max_rounds: int = 5) -> str:
        """
        Get Phase 2 instructions for group discussion (always uses complex voting).
        
        Args:
            round_number: Discussion round number
            max_rounds: Total number of discussion rounds
            
        Returns:
            Translated instructions for group discussion
        """
        # Always use unified prompt (previously complex voting prompt)
        return self.get("prompts.phase2_discussion_prompt", 
                       round_number=round_number,
                       max_rounds=max_rounds,
                       discussion_history="",
                       group_participants="")
    
    def get_parser_instructions(self) -> str:
        """Get utility agent parser instructions."""
        return self.get("prompts.utility_parser_instructions")
    
    def get_validator_instructions(self) -> str:
        """Get utility agent validator instructions."""
        return self.get("prompts.utility_validator_instructions")
    
    def get_principle_choice_parsing_prompt(self, response: str) -> str:
        """Get prompt for parsing principle choices."""
        return self.get("prompts.utility_parse_principle_choice", 
                       response=response)
    
    def get_principle_ranking_parsing_prompt(self, response: str) -> str:
        """Get prompt for parsing principle rankings."""
        return self.get("prompts.utility_parse_principle_ranking",
                       response=response)
    
    
    def get_constraint_re_prompt(self, participant_name: str, principle_name: str, constraint_type: str) -> str:
        """Get re-prompt for missing constraint specification."""
        return self.get("prompts.utility_constraint_re_prompt",
                       participant_name=participant_name,
                       principle_name=principle_name, 
                       constraint_type=constraint_type)
    
    def get_format_improvement_prompt(self, response: str, parse_type: str) -> str:
        """Get format improvement prompt."""
        if parse_type == 'principle_choice':
            return self.get("prompts.utility_format_improvement_choice",
                           response=response)
        elif parse_type == 'principle_ranking':
            return self.get("prompts.utility_format_improvement_ranking", 
                           response=response)
        else:
            raise ValueError(f"Unknown parse_type: {parse_type}")
    
    def get_validation_message(self, validation_key: str, **format_kwargs) -> str:
        """Get a translated validation message."""
        return self.get(f"prompts.validation_{validation_key}", **format_kwargs)
    
    def get_error_message(self, error_key: str, **format_kwargs) -> str:
        """Get a translated error message."""
        return self.get(f"prompts.system_error_messages_{error_key}", **format_kwargs)
    
    def get_success_message(self, success_key: str, **format_kwargs) -> str:
        """Get a translated success message."""
        return self.get(f"prompts.system_success_messages_{success_key}", **format_kwargs)
    
    def get_status_message(self, status_key: str, **format_kwargs) -> str:
        """Get a translated status message."""
        return self.get(f"prompts.system_status_messages_{status_key}", **format_kwargs)
    
    def get_justice_principle_name(self, principle_key: str) -> str:
        """Get translated name for a justice principle (for agent-facing content)."""
        return self.get(f"common.principle_names.{principle_key}")
    
    def get_justice_principle_name_english(self, principle_key: str) -> str:
        """Get English name for a justice principle (for system logs and developer messages)."""
        # Always use English for system logging regardless of current language
        original_lang = self.current_language
        try:
            self.set_language(SupportedLanguage.ENGLISH)
            return self.get(f"common.principle_names.{principle_key}")
        finally:
            self.set_language(original_lang)
    
    def get_certainty_level_name(self, certainty_key: str) -> str:
        """Get translated name for a certainty level (for agent-facing content)."""
        return self.get(f"common.certainty_levels.{certainty_key}")
    
    def get_certainty_level_name_english(self, certainty_key: str) -> str:
        """Get English name for a certainty level (for system logs and developer messages)."""
        # Always use English for system logging regardless of current language
        original_lang = self.current_language
        try:
            self.set_language(SupportedLanguage.ENGLISH)
            return self.get(f"common.certainty_levels.{certainty_key}")
        finally:
            self.set_language(original_lang)
    
    def get_phase_name(self, phase_key: str) -> str:
        """Get translated name for a phase."""
        return self.get(f"common.phase_names.{phase_key}")
    
    def get_context_stage_instruction(
        self,
        stage_key: str,
        round_number: int | None = None,
        max_rounds: int | None = None,
        **format_kwargs: Any
    ) -> str:
        """Get localized instruction text for a specific experiment stage."""
        if 'round_number' not in format_kwargs:
            format_kwargs['round_number'] = round_number if round_number is not None else ""
        if 'max_rounds' not in format_kwargs:
            format_kwargs['max_rounds'] = max_rounds if max_rounds is not None else ""
        try:
            instruction = self.get(
                f"prompts.context_stage_prompts.{stage_key}",
                **format_kwargs
            )
        except KeyError:
            # Fallback to a simple English string if translation missing
            instruction = stage_key.replace('_', ' ').title()
        if stage_key == "application" and round_number is not None and round_number > 0:
            instruction = f"{instruction} (Round {round_number})"
        if stage_key == "discussion" and round_number is not None and max_rounds is not None:
            instruction = f"{instruction} (Round {round_number} of {max_rounds})"
        return instruction
    
    def format_context_info(self, name: str, role_description: str, bank_balance: float,
                           phase: str, round_number: int, formatted_memory: str,
                           personality: str, phase_instructions: str, experiment_config=None,
                           internal_reasoning: str = "",
                           stage: Optional[Any] = None,
                           max_rounds: Optional[int] = None,
                           participant_names: Optional[List[str]] = None,
                           stage_header: str = "",
                           interaction_type: Optional[str] = None) -> str:
        """
        Format the main context information display.

        Args:
            name: Participant name
            role_description: Role description
            bank_balance: Current bank balance
            phase: Current phase
            round_number: Current round number
            formatted_memory: Formatted memory content
            personality: Participant personality
            phase_instructions: Phase-specific instructions
            experiment_config: Optional experiment configuration
            internal_reasoning: Optional internal reasoning content
            stage: Optional ExperimentStage for conditional formatting
            max_rounds: Optional maximum rounds for discussion header
            participant_names: Optional participant names for discussion header
            stage_header: Optional localized stage status line displayed ahead of instructions

        Returns:
            Formatted context information string
        """
        
        # Track first turn per phase for experiment explanation gating
        if not hasattr(self, '_first_turn_tracker'):
            self._first_turn_tracker = {}
        
        phase_key = f"{phase}_{name}"  # Track per participant and phase
        is_first_turn = phase_key not in self._first_turn_tracker
        if is_first_turn:
            self._first_turn_tracker[phase_key] = True
            
        # Determine whether to include experiment explanation
        include_explanation = True  # Default behavior
        if experiment_config:
            # First check the master switch - if disabled, skip explanation entirely
            if hasattr(experiment_config, 'include_experiment_explanation'):
                if not experiment_config.include_experiment_explanation:
                    include_explanation = False

            # If master switch allows, check per-turn settings
            if include_explanation and hasattr(experiment_config, 'include_experiment_explanation_each_turn'):
                # If config says always include, use the explanation
                # If config says don't include each turn, only include on first turn per phase
                include_explanation = (experiment_config.include_experiment_explanation_each_turn or is_first_turn)

        # Special handling for Phase 1 memory updates: detailed explanation only on first, then nothing
        # For all other interactions: keep existing behavior (detailed on first, brief thereafter)
        is_phase1_memory_update = (role_description == "MemoryUpdate" and phase == "Phase 1")

        if is_phase1_memory_update:
            # Phase 1 memory updates: long explanation on first, short reminder afterwards
            if include_explanation:
                if is_first_turn:
                    experiment_explanation = self.get_initial_experiment_explanation()
                else:
                    experiment_explanation = self.get_experiment_explanation()
            else:
                experiment_explanation = ""
        else:
            # All other interactions: existing behavior
            if include_explanation:
                if is_first_turn:
                    experiment_explanation = self.get_initial_experiment_explanation()
                else:
                    experiment_explanation = self.get_experiment_explanation()
            else:
                experiment_explanation = ""
        language_instruction = self.get("prompts.language_instruction")

        # Localize common phase names when possible (e.g., "Phase 1" → localized)
        localized_phase = phase
        try:
            phase_map = {
                "Phase 1": self.get("common.phase_names.phase1"),
                "Phase 2": self.get("common.phase_names.phase2"),
            }
            if phase in phase_map:
                localized_phase = phase_map[phase]
        except Exception:
            # If translation keys missing, keep original
            localized_phase = phase
        
        # Format internal reasoning section if available
        internal_reasoning_section = ""
        if internal_reasoning and internal_reasoning.strip():
            sanitized_reasoning = self._strip_markdown_emphasis(internal_reasoning)
            internal_reasoning_section = self.get("prompts.internal_reasoning_context_format",
                                                 internal_reasoning=sanitized_reasoning)

        # Format discussion or voting header section based on context
        discussion_header_section = ""
        if stage and max_rounds and participant_names:
            # Import ExperimentStage dynamically to avoid circular imports
            from models.experiment_types import ExperimentStage

            # Check if we're in a voting interaction (vote_prompt, vote_confirmation, ballot)
            is_voting = interaction_type in ("vote_prompt", "vote_confirmation", "ballot")

            if stage == ExperimentStage.DISCUSSION or is_voting:
                # Format participant list using language-aware method
                participant_list = self.format_participant_list(participant_names)

                # Only add header if we have valid data
                if participant_list and round_number:
                    # Use voting header for voting interactions, discussion header otherwise
                    header_key = "context_voting_header_section" if is_voting else "context_discussion_header_section"
                    discussion_header_section = self.get(
                        header_key,
                        round_number=round_number,
                        max_rounds=max_rounds,
                        participants=participant_list
                    )

        return self.get("prompts.context_context_info_format",
                       name=name,
                       role_description=role_description,
                       bank_balance=bank_balance,
                       phase=localized_phase,
                       round_number=round_number,
                       discussion_header_section=discussion_header_section,
                       formatted_memory=formatted_memory,
                       internal_reasoning_section=internal_reasoning_section,
                       experiment_explanation=experiment_explanation,
                       personality=personality,
                       phase_instructions=phase_instructions,
                       language_instruction=language_instruction,
                       stage_header=stage_header)
    
    def format_memory_context(self, name: str, bank_balance: float, personality: str,
                             role_description: str = None, phase=None, round_number: int = 0,
                             stage: Optional[Any] = None,
                             experiment_config=None) -> str:
        """Format minimal context for memory updates only."""
        # Convert phase enum to string if needed
        if hasattr(phase, 'value'):
            phase_str = phase.value.replace('_', ' ').title()  # "phase_1" → "Phase 1"
        else:
            phase_str = str(phase) if phase else "Phase 1"

        # Use provided role_description or fall back to personality
        actual_role = role_description if role_description is not None else personality

        # Format discussion header section if in discussion stage
        discussion_header_section = ""
        if stage and experiment_config:
            # Import ExperimentStage dynamically to avoid circular imports
            from models.experiment_types import ExperimentStage

            if stage == ExperimentStage.DISCUSSION:
                # Extract max rounds and participant names from experiment_config
                max_rounds = experiment_config.phase2_rounds if experiment_config else 5
                participant_names = []
                try:
                    if experiment_config and getattr(experiment_config, 'agents', None):
                        participant_names = [getattr(a, 'name', '') for a in experiment_config.agents if getattr(a, 'name', '')]
                except Exception:
                    participant_names = []

                # Format participant list using language-aware method
                if participant_names and round_number:
                    participant_list = self.format_participant_list(participant_names)

                    # Only add header if we have valid data
                    if participant_list:
                        discussion_header_section = self.get(
                            "context_discussion_header_section",
                            round_number=round_number,
                            max_rounds=max_rounds,
                            participants=participant_list
                        )

        return self.get("prompts.context_memory_update_format",
                       name=name,
                       role_description=actual_role,
                       bank_balance=bank_balance,
                       phase=phase_str,
                       round_number=round_number,
                       personality=personality,
                       discussion_header_section=discussion_header_section)

    def format_participant_list(self, participant_names: List[str]) -> str:
        """
        Format participant list with language-appropriate conjunctions.

        Args:
            participant_names: List of participant names

        Returns:
            Formatted participant list string

        Examples:
            ["Alice"] → "Alice"
            ["Alice", "Bob"] → "Alice and Bob"
            ["Alice", "Bob", "Carol"] → "Alice, Bob, and Carol"
        """
        if not participant_names:
            return ""

        if len(participant_names) == 1:
            return participant_names[0]

        if len(participant_names) == 2:
            return self.get("common.list_formatting.two_items",
                           first=participant_names[0],
                           second=participant_names[1])

        # Three or more participants
        items_list = ", ".join(participant_names[:-1])
        return self.get("common.list_formatting.three_plus_items",
                       items=items_list,
                       last=participant_names[-1])

    @staticmethod
    def _strip_markdown_emphasis(text: str) -> str:
        """Remove Markdown bold/italic markers to ensure plain text rendering."""
        if not text:
            return text

        pattern = re.compile(r"(\*\*|__)(.+?)(\1)", flags=re.DOTALL)
        return pattern.sub(r"\2", text)

    def format_memory_section(self, memory: str, display_mode: str = "full", context_type: str = "general") -> str:
        """
        Format the memory section display.

        Args:
            memory: The memory content to format
            display_mode: Display mode ("full", "compact", "adaptive")
            context_type: Context type for summary ("general", "voting", "discussion", "application")
            
        Returns:
            Formatted memory section
        """
        if not memory or not memory.strip():
            # Handle empty memory case
            if display_mode == "compact":
                empty_placeholder = self.get("prompts.context_memory_summary_empty_placeholder")
                return self.get("prompts.context_memory_summary_format", 
                               memory_summary=empty_placeholder)
            else:
                empty_placeholder = self.get("prompts.context_memory_empty_placeholder")
                return self.get("prompts.context_memory_section_format", 
                               memory=empty_placeholder)
        
        if display_mode == "compact":
            # Use memory summarization
            from utils.memory_summarizer import MemorySummarizer, SummaryContext
            
            # Convert context_type to SummaryContext enum
            context_map = {
                "voting": SummaryContext.VOTING,
                "discussion": SummaryContext.DISCUSSION,
                "application": SummaryContext.APPLICATION,
                "general": SummaryContext.GENERAL
            }
            summary_context = context_map.get(context_type, SummaryContext.GENERAL)
            
            try:
                memory_summary = MemorySummarizer.create_summary(
                    memory, 
                    context_type=summary_context, 
                    max_lines=4
                )
                
                # If summary is empty or too short, fallback to full memory
                if not memory_summary or len(memory_summary.strip()) < 20:
                    return self.get("prompts.context_memory_section_format", 
                                   memory=memory)
                
                return self.get("prompts.context_memory_summary_format", 
                               memory_summary=memory_summary)
            except Exception as e:
                # Fallback to full memory display if summarization fails
                logger.warning(f"Memory summarization failed: {e}, falling back to full display")
                return self.get("prompts.context_memory_section_format", 
                               memory=memory)
        else:
            # Full display mode
            return self.get("prompts.context_memory_section_format", 
                           memory=memory)

    def format_phase2_discussion_instructions(
        self,
        round_number: int,
        max_rounds: int,
        participant_names: Optional[List[str]],
        discussion_history: str,
        agent_recent_statement: Optional[str] = None
    ) -> str:
        """Format the Phase 2 discussion history section only.

        The header and participant composition are now handled by discussion_header_section
        in format_context_info to avoid duplication. This method only formats the
        discussion transcript.

        Note: DEFENSIVE stripping applied here even though stripping happens at source,
        to protect against edge cases, old data, or direct assignments to public_history.
        """
        # Transcript section only - header is added separately by discussion_header_section
        transcript = discussion_history if (discussion_history and discussion_history.strip()) else self.get("no_previous_discussion_placeholder")
        # DEFENSIVE: Strip markdown even though it should be clean
        transcript = self._strip_markdown_emphasis(transcript)

        # Format with template (blank line before closing delimiter prevents bold rendering)
        history_section = self.get(
            "context_discussion_history_section_format",
            discussion_history=transcript
        )

        # Append agent's recent statement if provided
        if agent_recent_statement and agent_recent_statement.strip():
            history_section += f"\n\nYour most recent statement:\n\"{agent_recent_statement}\""

        return history_section
    
    def get_principle_list_formatted(self, list_type: str = "detailed") -> str:
        """
        Get formatted list of justice principles.
        
        Args:
            list_type: Type of list formatting ("detailed", "simple", "names_only", "letters_only" [deprecated])
            
        Returns:
            Formatted list of justice principles
        """
        if list_type == "detailed":
            # For detailed explanations in prompts (use fully localized descriptions)
            name_floor = self.get("common.principle_names.maximizing_floor")
            name_avg = self.get("common.principle_names.maximizing_average")
            name_floor_c = self.get("common.principle_names.maximizing_average_floor_constraint")
            name_range_c = self.get("common.principle_names.maximizing_average_range_constraint")

            desc_floor = self.get("common.principle_descriptions.maximizing_floor")
            desc_avg = self.get("common.principle_descriptions.maximizing_average")
            desc_floor_c = self.get("common.principle_descriptions.maximizing_average_floor_constraint")
            desc_range_c = self.get("common.principle_descriptions.maximizing_average_range_constraint")

            return f"""1. **{name_floor}**: {desc_floor}
2. **{name_avg}**: {desc_avg}  
3. **{name_floor_c}**: {desc_floor_c}
4. **{name_range_c}**: {desc_range_c}"""
            
        elif list_type == "simple":
            # For application choices - NO LETTERS (localized descriptions + localized notes for constrained)
            name_floor = self.get("common.principle_names.maximizing_floor")
            name_avg = self.get("common.principle_names.maximizing_average")
            name_floor_c = self.get("common.principle_names.maximizing_average_floor_constraint")
            name_range_c = self.get("common.principle_names.maximizing_average_range_constraint")

            desc_floor = self.get("common.principle_descriptions.maximizing_floor")
            desc_avg = self.get("common.principle_descriptions.maximizing_average")
            desc_floor_c = self.get("common.principle_descriptions.maximizing_average_floor_constraint")
            desc_range_c = self.get("common.principle_descriptions.maximizing_average_range_constraint")

            # Localized notes for constrained principles (optional)
            try:
                note_floor_c = self.get("common.principle_notes.floor_constraint")
            except Exception:
                note_floor_c = ""
            try:
                note_range_c = self.get("common.principle_notes.range_constraint")
            except Exception:
                note_range_c = ""

            return f"""**{name_floor}**: {desc_floor}
**{name_avg}**: {desc_avg}  
**{name_floor_c}**: {desc_floor_c}{note_floor_c}
**{name_range_c}**: {desc_range_c}{note_range_c}"""
            
        elif list_type == "letters_only":
            # DEPRECATED - For backward compatibility only, use names_only instead
            return self.get_principle_list_formatted("names_only")
            
        elif list_type == "names_only":
            # For voting prompts - just names, no letters
            return f"""{self.get("common.principle_names.maximizing_floor")}
{self.get("common.principle_names.maximizing_average")}  
{self.get("common.principle_names.maximizing_average_floor_constraint")}
{self.get("common.principle_names.maximizing_average_range_constraint")}"""
            
        else:
            raise ValueError(f"Unknown list_type: {list_type}")
    
    # Two-Stage Voting Support Methods
    
    def get_two_stage_principle_selection_prompt(self, round_number: int, max_rounds: int) -> str:
        """Get the principle selection prompt for two-stage voting."""
        return self.get("prompts.two_stage_principle_selection",
                       round_number=round_number,
                       max_rounds=max_rounds)
    
    def get_two_stage_amount_specification_prompt(self, principle_name: str) -> str:
        """
        Get the amount specification prompt for two-stage voting.
        
        Args:
            principle_name: Name of the selected principle requiring constraint
            
        Returns:
            Formatted amount specification prompt
        """
        return self.get("prompts.two_stage_amount_specification", principle_name=principle_name)
    
    def get_two_stage_error_message(self, error_type: str, attempt: int, max_attempts: int) -> str:
        """
        Get a two-stage voting error message.
        
        Args:
            error_type: Type of error (e.g., "respond_with_number_only", "invalid_amount_format")
            attempt: Current attempt number
            max_attempts: Maximum allowed attempts
            
        Returns:
            Formatted error message
        """
        try:
            return self.get(f"errors.two_stage_{error_type}", 
                          attempt=attempt, max_attempts=max_attempts)
        except KeyError:
            # Fallback error messages
            fallback_messages = {
                "respond_with_number_only": f"Invalid response (attempt {attempt}/{max_attempts}). You must respond with exactly one number: 1, 2, 3, or 4.",
                "invalid_amount_format": f"Invalid amount format (attempt {attempt}/{max_attempts}). You must respond with a positive whole dollar amount.",
                "amount_too_low": f"Amount too low (attempt {attempt}/{max_attempts}). Please provide a realistic dollar amount.",
                "amount_too_high": f"Amount too high (attempt {attempt}/{max_attempts}). Please provide a realistic dollar amount.",
                "amount_must_be_positive": f"Invalid amount (attempt {attempt}/{max_attempts}). Amount must be positive.",
                "no_text_in_amount": f"Invalid format (attempt {attempt}/{max_attempts}). Please provide only a number.",
                "empty_amount_response": f"Empty response (attempt {attempt}/{max_attempts}). Please provide a dollar amount."
            }
            return fallback_messages.get(error_type, 
                f"Invalid response (attempt {attempt}/{max_attempts}). Please try again.")
    
    def format_amount_display(self, amount: int) -> str:
        """
        Format amounts in dollars consistently across all languages.
        
        Args:
            amount: Dollar amount to format
            
        Returns:
            Formatted amount string (e.g., "$25,000")
        """
        # Import here to avoid circular imports
        try:
            from utils.cultural_adaptation import get_amount_formatter, SupportedLanguage as CulturalLanguage
            
            formatter = get_amount_formatter()
            
            # Map current language to cultural language enum
            language_mapping = {
                SupportedLanguage.ENGLISH: CulturalLanguage.ENGLISH,
                SupportedLanguage.SPANISH: CulturalLanguage.SPANISH, 
                SupportedLanguage.MANDARIN: CulturalLanguage.MANDARIN
            }
            
            cultural_lang = language_mapping.get(self.current_language, CulturalLanguage.ENGLISH)
            return formatter.format_amount(amount, cultural_lang)
            
        except ImportError:
            # Fallback formatting if cultural adaptation not available
            return f"${amount:,}"
    
    def get_two_stage_timeout_message(self) -> str:
        """Get timeout message for two-stage voting."""
        try:
            return self.get("errors.timeout_retry")
        except KeyError:
            # Language-specific fallback messages
            fallbacks = {
                SupportedLanguage.ENGLISH: "Response timed out. Please try again.",
                SupportedLanguage.SPANISH: "Tiempo de espera agotado. Por favor, inténtalo de nuevo.",
                SupportedLanguage.MANDARIN: "响应超时。请重试。"
            }
            return fallbacks.get(self.current_language, "Response timed out. Please try again.")
    
    def validate_two_stage_translations(self) -> Dict[str, bool]:
        """
        Validate that all required two-stage voting translations exist.
        
        Returns:
            Dictionary with validation results for each language
        """
        results = {}
        required_keys = [
            "prompts.two_stage_principle_selection",
            "prompts.two_stage_amount_specification", 
            "errors.two_stage_respond_with_number_only",
            "errors.two_stage_invalid_amount_format",
            "errors.two_stage_amount_too_low", 
            "errors.two_stage_amount_too_high"
        ]
        
        original_language = self.current_language
        
        try:
            for language in SupportedLanguage:
                self.set_language(language)
                language_valid = True
                
                for key in required_keys:
                    try:
                        self.get(key)
                    except KeyError:
                        logger.warning(f"Missing translation key '{key}' for {language.value}")
                        language_valid = False
                
                results[language.value] = language_valid
        
        finally:
            # Restore original language
            self.set_language(original_language)
        
        return results


def create_language_manager(language: SupportedLanguage, seed: Optional[int] = None) -> LanguageManager:
    """
    Create a new language manager instance with specified language and seed.
    
    Args:
        language: Language to set for this instance
        seed: Random seed for deterministic example generation (optional)
        
    Returns:
        New LanguageManager instance configured with the specified language and seed
    """
    manager = LanguageManager(seed=seed)
    manager.set_language(language)
    return manager


def get_english_principle_name(principle_key: str, language_manager: LanguageManager) -> str:
    """
    Get English principle name for system logging (always English).
    
    Args:
        principle_key: The principle key (e.g., "maximizing_floor")
        language_manager: Language manager instance to use
        
    Returns:
        English principle name for logging
    """
    return language_manager.get_justice_principle_name_english(principle_key)


def get_english_certainty_name(certainty_key: str, language_manager: LanguageManager) -> str:
    """
    Get English certainty level name for system logging (always English).
    
    Args:
        certainty_key: The certainty key (e.g., "very_sure")
        language_manager: Language manager instance to use
        
    Returns:
        English certainty name for logging
    """
    return language_manager.get_certainty_level_name_english(certainty_key)


def validate_translation_files(translations_dir: str = "translations") -> bool:
    """
    Validate that all required translation files exist and are valid.
    
    Args:
        translations_dir: Directory containing translation files
        
    Returns:
        True if all files are valid, False otherwise
    """
    manager = LanguageManager(translations_dir)
    
    try:
        for language in SupportedLanguage:
            logger.info(f"Validating {language.value} translations...")
            translations = manager.load_language(language)
            
            # Basic validation - check that required top-level sections exist
            required_sections = ["common", "prompts"]
            
            for section in required_sections:
                if section not in translations:
                    logger.error(f"Missing section '{section}' in {language.value}")
                    return False
            
            # Check common subsections
            common_subsections = ["principle_names", "income_classes", "certainty_levels"]
            for subsection in common_subsections:
                if subsection not in translations["common"]:
                    logger.error(f"Missing common.{subsection} in {language.value}")
                    return False
        
        logger.info("All translation files validated successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Translation validation failed: {e}")
        return False
