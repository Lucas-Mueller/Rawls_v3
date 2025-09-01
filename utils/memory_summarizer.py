"""
Memory summarization utilities for optimizing token usage in agent contexts.
"""
import re
import logging
from typing import List, Optional, Dict
from enum import Enum

logger = logging.getLogger(__name__)


class SummaryContext(Enum):
    """Context types for memory summaries."""
    GENERAL = "general"
    VOTING = "voting"
    DISCUSSION = "discussion"
    APPLICATION = "application"


class MemorySummarizer:
    """Handles memory summarization to reduce context token usage while preserving key insights."""
    
    @staticmethod
    def create_summary(
        full_memory: str, 
        context_type: SummaryContext = SummaryContext.GENERAL,
        max_lines: int = 4
    ) -> str:
        """
        Create a 3-4 line memory summary preserving key insights.
        
        Args:
            full_memory: Complete memory content to summarize
            context_type: Type of context for tailored summaries
            max_lines: Maximum number of lines in summary
            
        Returns:
            Condensed memory summary
        """
        if not full_memory or not full_memory.strip():
            return ""
        
        # Extract key insights first
        insights = MemorySummarizer.extract_key_insights(full_memory)
        
        # Get context-specific information
        if context_type == SummaryContext.VOTING:
            summary = MemorySummarizer._create_voting_summary(full_memory, insights, max_lines)
        elif context_type == SummaryContext.DISCUSSION:
            summary = MemorySummarizer._create_discussion_summary(full_memory, insights, max_lines)
        elif context_type == SummaryContext.APPLICATION:
            summary = MemorySummarizer._create_application_summary(full_memory, insights, max_lines)
        else:
            summary = MemorySummarizer._create_general_summary(full_memory, insights, max_lines)
        
        return summary.strip()
    
    @staticmethod
    def extract_key_insights(full_memory: str) -> List[str]:
        """
        Extract 2-3 most important strategic insights from memory.
        
        Args:
            full_memory: Complete memory content
            
        Returns:
            List of key insights
        """
        if not full_memory:
            return []
        
        insights = []
        
        # Look for Phase 1 learnings about principle effectiveness
        phase1_patterns = [
            r"(?:floor|average|range)\s+(?:principle|constraint).*?(?:earned|effective|performed|best|worst)",
            r"(?:earned|made|got)\s+\$[\d,]+\.?\d*",
            r"(?:best|worst|most|least)\s+(?:effective|successful|profitable)",
            r"(?:learned|discovered|found|realized).*?(?:principle|constraint|floor|average)"
        ]
        
        for pattern in phase1_patterns:
            matches = re.findall(pattern, full_memory, re.IGNORECASE)
            for match in matches[:2]:  # Limit to 2 matches per pattern
                if len(match) > 10:  # Skip very short matches
                    insights.append(match.strip())
        
        # Look for Phase 2 strategic insights
        phase2_patterns = [
            r"(?:consensus|agreement|group).*?(?:reached|building|forming)",
            r"(?:Alice|Bob|Charlie|others?).*?(?:support|agree|prefer|want)",
            r"(?:voted|voting|ballot).*?(?:principle|constraint|\$\d+)",
            r"(?:moderate|extreme|reasonable).*?(?:constraint|amount|floor)"
        ]
        
        for pattern in phase2_patterns:
            matches = re.findall(pattern, full_memory, re.IGNORECASE)
            for match in matches[:1]:  # Limit to 1 match per pattern
                if len(match) > 10:
                    insights.append(match.strip())
        
        # Look for preference evolution
        preference_patterns = [
            r"(?:initially|originally|first).*?(?:preferred|chose|wanted).*?(?:now|currently|changed)",
            r"(?:shifted|changed|moved).*?(?:from|to).*?(?:principle|preference)",
            r"(?:principle \d+|floor|average|range).*?(?:to|→|then).*?(?:principle \d+|floor|average|range)"
        ]
        
        for pattern in preference_patterns:
            matches = re.findall(pattern, full_memory, re.IGNORECASE)
            for match in matches[:1]:
                if len(match) > 15:
                    insights.append(match.strip())
        
        # Remove duplicates and limit to top 3 insights
        unique_insights = []
        for insight in insights:
            if insight not in unique_insights and len(unique_insights) < 3:
                unique_insights.append(insight)
        
        return unique_insights
    
    @staticmethod
    def _create_voting_summary(full_memory: str, insights: List[str], max_lines: int) -> str:
        """Create voting-focused summary emphasizing Phase 1 experience and voting history."""
        lines = []
        
        # Phase 1 earnings summary
        earnings_match = re.search(r"total.*?earnings?.*?\$?([\d,]+\.?\d*)", full_memory, re.IGNORECASE)
        if earnings_match:
            lines.append(f"Phase 1: Earned ${earnings_match.group(1)} total across principle applications.")
        
        # Best performing principle
        best_principle = MemorySummarizer._extract_best_principle(full_memory)
        if best_principle:
            lines.append(f"Best performing: {best_principle}.")
        
        # Current voting status/preference
        voting_info = MemorySummarizer._extract_voting_status(full_memory)
        if voting_info:
            lines.append(voting_info)
        
        # Key insight if space allows
        if len(lines) < max_lines and insights:
            lines.append(f"Key insight: {insights[0]}")
        
        return " ".join(lines[:max_lines])
    
    @staticmethod
    def _create_discussion_summary(full_memory: str, insights: List[str], max_lines: int) -> str:
        """Create discussion-focused summary emphasizing strategic insights and group dynamics."""
        lines = []
        
        # Current position/preference
        current_preference = MemorySummarizer._extract_current_preference(full_memory)
        if current_preference:
            lines.append(f"Position: {current_preference}.")
        
        # Group dynamics
        group_dynamics = MemorySummarizer._extract_group_dynamics(full_memory)
        if group_dynamics:
            lines.append(group_dynamics)
        
        # Strategic insights
        for insight in insights[:2]:  # Up to 2 insights
            if len(lines) < max_lines:
                lines.append(f"Insight: {insight}")
        
        return " ".join(lines[:max_lines])
    
    @staticmethod
    def _create_application_summary(full_memory: str, insights: List[str], max_lines: int) -> str:
        """Create application-focused summary emphasizing principle performance learnings."""
        lines = []
        
        # Principle performance summary
        performance = MemorySummarizer._extract_principle_performance(full_memory)
        if performance:
            lines.extend(performance[:2])  # Up to 2 performance lines
        
        # Learning insights
        for insight in insights:
            if len(lines) < max_lines and "learn" in insight.lower():
                lines.append(f"Learned: {insight}")
        
        return " ".join(lines[:max_lines])
    
    @staticmethod
    def _create_general_summary(full_memory: str, insights: List[str], max_lines: int) -> str:
        """Create general summary balancing Phase 1 experience and Phase 2 progress."""
        lines = []
        
        # Phase 1 overview
        phase1_summary = MemorySummarizer._extract_phase1_overview(full_memory)
        if phase1_summary:
            lines.append(phase1_summary)
        
        # Phase 2 progress (if applicable)
        phase2_progress = MemorySummarizer._extract_phase2_progress(full_memory)
        if phase2_progress:
            lines.append(phase2_progress)
        
        # Key insights
        for insight in insights:
            if len(lines) < max_lines:
                lines.append(f"Key insight: {insight}")
        
        return " ".join(lines[:max_lines])
    
    @staticmethod
    def _extract_best_principle(memory: str) -> Optional[str]:
        """Extract the best performing principle from memory."""
        patterns = [
            r"(?:best|highest|most effective).*?(floor|average|range).*?(?:principle|income)",
            r"(principle \d+).*?(?:best|highest|most effective|earned most)",
            r"(?:floor|average|range).*?(?:performed best|highest earnings|most profitable)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, memory, re.IGNORECASE)
            if match:
                return match.group(1) if match.group(1) else match.group(0)
        
        return None
    
    @staticmethod
    def _extract_voting_status(memory: str) -> Optional[str]:
        """Extract current voting status or preference."""
        patterns = [
            r"(?:voted|voting|ballot).*?(principle \d+).*?\$?([\d,]+)",
            r"(?:support|prefer|want).*?(floor|average|range).*?constraint.*?\$?([\d,]+)",
            r"consensus.*?(reached|building|forming).*?(\$?[\d,]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, memory, re.IGNORECASE)
            if match:
                return f"Voting: {match.group(0)[:50]}"  # Truncate if too long
        
        return None
    
    @staticmethod
    def _extract_current_preference(memory: str) -> Optional[str]:
        """Extract current principle preference."""
        patterns = [
            r"(?:current|now|currently).*?(?:prefer|support|want).*?(floor|average|range)",
            r"(?:support|prefer).*?(principle \d+)",
            r"(?:my position|I believe).*?(floor|average|range|principle)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, memory, re.IGNORECASE)
            if match:
                return match.group(0)[:40]  # Truncate if too long
        
        return None
    
    @staticmethod
    def _extract_group_dynamics(memory: str) -> Optional[str]:
        """Extract group dynamics information."""
        patterns = [
            r"(Alice|Bob|Charlie).*?(?:agree|support|oppose|prefer).*?(floor|average|principle)",
            r"(?:group|consensus|agreement).*?(?:reached|forming|building)",
            r"(?:allied|opposed|divided).*?(?:Alice|Bob|Charlie|group)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, memory, re.IGNORECASE)
            if match:
                return f"Group: {match.group(0)[:50]}"
        
        return None
    
    @staticmethod
    def _extract_principle_performance(memory: str) -> List[str]:
        """Extract principle performance information."""
        performance = []
        patterns = [
            r"(floor|average|range).*?(?:earned|made|performed).*?\$?([\d,]+\.?\d*)",
            r"(principle \d+).*?(?:earned|made|performed).*?\$?([\d,]+\.?\d*)",
            r"(?:best|worst|highest|lowest).*?(floor|average|range|principle \d+)"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, memory, re.IGNORECASE)
            for match in matches[:2]:  # Limit to 2 per pattern
                if isinstance(match, tuple):
                    performance.append(f"{match[0]} earned ${match[1]}" if len(match) > 1 else match[0])
                else:
                    performance.append(match[:40])
        
        return performance[:2]  # Return max 2 performance items
    
    @staticmethod
    def _extract_phase1_overview(memory: str) -> Optional[str]:
        """Extract Phase 1 overview."""
        earnings_match = re.search(r"(?:total|earned).*?\$?([\d,]+\.?\d*)", memory, re.IGNORECASE)
        preference_match = re.search(r"(?:prefer|chose|selected).*?(floor|average|range|principle \d+)", memory, re.IGNORECASE)
        
        if earnings_match and preference_match:
            return f"Phase 1: {preference_match.group(1)} preference, earned ${earnings_match.group(1)} total."
        elif earnings_match:
            return f"Phase 1: Earned ${earnings_match.group(1)} total across applications."
        elif preference_match:
            return f"Phase 1: {preference_match.group(1)} preference developed."
        
        return None
    
    @staticmethod
    def _extract_phase2_progress(memory: str) -> Optional[str]:
        """Extract Phase 2 progress."""
        patterns = [
            r"(?:round \d+|discussion).*?(?:voted|voting|consensus|agreement)",
            r"(?:Phase 2|discussion).*?(?:round \d+).*?(?:support|prefer|oppose)",
            r"(?:consensus|voting).*?(?:reached|initiated|building)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, memory, re.IGNORECASE)
            if match:
                return f"Phase 2: {match.group(0)[:60]}"
        
        return None