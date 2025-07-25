"""
Memory management utilities for agent memory handling.
"""
from typing import List
from models import ExperimentPhase


class MemoryManager:
    """Manages agent memory with intelligent truncation and formatting."""
    
    @staticmethod
    def update_memory(
        current_memory: str, 
        new_info: str, 
        max_length: int,
        priority_sections: List[str] = None
    ) -> str:
        """
        Intelligent memory truncation maintaining important information.
        
        Args:
            current_memory: Current memory content
            new_info: New information to add
            max_length: Maximum memory length in characters
            priority_sections: Sections to preserve during truncation
        """
        # Add new information
        updated_memory = current_memory + "\n" + new_info
        
        # If within limits, return as-is
        if len(updated_memory) <= max_length:
            return updated_memory
        
        # Need to truncate - preserve priority sections and recent information
        return MemoryManager._intelligent_truncate(
            updated_memory, max_length, priority_sections or []
        )
    
    @staticmethod
    def _intelligent_truncate(
        memory: str, 
        max_length: int, 
        priority_sections: List[str]
    ) -> str:
        """
        Perform intelligent truncation preserving important information.
        
        Strategy:
        1. Always preserve priority sections
        2. Keep recent information (last 30% of max_length)
        3. Preserve key experiment milestones
        4. Remove middle content if necessary
        """
        lines = memory.split('\n')
        
        # Calculate space allocation
        recent_space = int(max_length * 0.3)  # 30% for recent info
        priority_space = int(max_length * 0.4)  # 40% for priority sections
        buffer_space = max_length - recent_space - priority_space  # 30% buffer
        
        # Extract priority content
        priority_content = []
        remaining_lines = []
        
        for line in lines:
            is_priority = any(section in line for section in priority_sections)
            if is_priority:
                priority_content.append(line)
            else:
                remaining_lines.append(line)
        
        # Build priority section
        priority_text = '\n'.join(priority_content)
        if len(priority_text) > priority_space:
            # Truncate priority content if too long
            priority_text = priority_text[:priority_space]
        
        # Get recent content
        recent_text = '\n'.join(remaining_lines[-10:])  # Last 10 lines
        if len(recent_text) > recent_space:
            recent_text = recent_text[-recent_space:]
        
        # Fill buffer with middle content if space allows
        remaining_space = max_length - len(priority_text) - len(recent_text) - 20  # 20 for separators
        
        if remaining_space > 0 and len(remaining_lines) > 10:
            # Take some middle content
            middle_lines = remaining_lines[:-10]  # Exclude recent lines
            middle_text = '\n'.join(middle_lines)
            
            if len(middle_text) <= remaining_space:
                # All middle content fits
                final_memory = priority_text + "\n\n" + middle_text + "\n\n" + recent_text
            else:
                # Take first part of middle content
                middle_text = middle_text[:remaining_space]
                final_memory = priority_text + "\n\n" + middle_text + "\n...[TRUNCATED]...\n" + recent_text
        else:
            # Only priority and recent content
            final_memory = priority_text + "\n\n...[MEMORY TRUNCATED]...\n\n" + recent_text
        
        return final_memory.strip()
    
    @staticmethod
    def format_memory_prompt(memory: str, phase: ExperimentPhase) -> str:
        """Format memory for agent consumption based on current phase."""
        if not memory.strip():
            return "No previous memories."
        
        if phase == ExperimentPhase.PHASE_1:
            header = "=== YOUR MEMORY (Phase 1 - Individual Learning) ==="
        else:
            header = "=== YOUR MEMORY (Including Phase 1 + Phase 2 Group Discussion) ==="
        
        return f"{header}\n{memory}\n{'='*50}"
    
    @staticmethod
    def add_memory_entry(
        current_memory: str,
        entry_type: str,
        content: str,
        round_number: int = None
    ) -> str:
        """Add a structured memory entry."""
        timestamp_info = f" (Round {round_number})" if round_number else ""
        entry = f"\n[{entry_type.upper()}{timestamp_info}] {content}"
        return current_memory + entry
    
    @staticmethod
    def extract_key_learnings(memory: str) -> List[str]:
        """Extract key learnings from memory for summarization."""
        key_learnings = []
        lines = memory.split('\n')
        
        # Look for specific patterns that indicate important learnings
        learning_indicators = [
            "learned that",
            "discovered that", 
            "realized that",
            "found that",
            "concluded that",
            "earned $",
            "chose principle",
            "ranking:"
        ]
        
        for line in lines:
            line_lower = line.lower()
            if any(indicator in line_lower for indicator in learning_indicators):
                key_learnings.append(line.strip())
        
        return key_learnings[:10]  # Return top 10 key learnings
    
    @staticmethod
    def create_phase_transition_summary(phase1_memory: str) -> str:
        """Create a summary for transitioning from Phase 1 to Phase 2."""
        key_learnings = MemoryManager.extract_key_learnings(phase1_memory)
        
        summary = "=== PHASE 1 SUMMARY ===\n"
        summary += "Key experiences and learnings:\n"
        
        if key_learnings:
            for i, learning in enumerate(key_learnings, 1):
                summary += f"{i}. {learning}\n"
        else:
            summary += "No specific key learnings extracted.\n"
        
        summary += "\n=== TRANSITIONING TO PHASE 2 ===\n"
        summary += "You will now participate in group discussion to reach consensus on a justice principle.\n"
        summary += "Your Phase 1 experiences should inform your contributions to the group discussion.\n"
        
        return summary