"""
Process Flow Logger for clear, user-friendly experiment progress tracking.

This logger focuses on providing clear, actionable progress information
rather than verbose technical details. It supports multiple verbosity levels
and structured visual output to help experimenters understand what's happening.
"""

import sys
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


class VerbosityLevel(Enum):
    """Logging verbosity levels."""
    MINIMAL = "minimal"      # Only essential progress and results
    STANDARD = "standard"    # Standard progress with key details
    DETAILED = "detailed"    # Detailed progress with timing info
    DEBUG = "debug"         # Full technical details (current behavior)


@dataclass
class AgentStatus:
    """Tracks individual agent status."""
    name: str
    status: str = "pending"  # pending, active, completed, error
    current_task: str = ""
    progress: float = 0.0    # 0.0 to 1.0


class ProcessFlowLogger:
    """
    Clean, user-focused experiment progress logger.
    
    Provides structured terminal output that emphasizes experiment flow
    over technical implementation details.
    """
    
    def __init__(self, verbosity: VerbosityLevel = VerbosityLevel.STANDARD, use_colors: bool = True):
        """
        Initialize ProcessFlowLogger.
        
        Args:
            verbosity: Logging detail level
            use_colors: Whether to use colored terminal output
        """
        self.verbosity = verbosity
        self.use_colors = use_colors and sys.stdout.isatty()
        self.start_time = None
        self.phase_start_time = None
        self.agent_statuses: Dict[str, AgentStatus] = {}
        
        # Color codes for terminal output
        self.colors = {
            'blue': '\033[94m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'red': '\033[91m',
            'bold': '\033[1m',
            'underline': '\033[4m',
            'reset': '\033[0m',
            'gray': '\033[90m'
        } if self.use_colors else {k: '' for k in ['blue', 'green', 'yellow', 'red', 'bold', 'underline', 'reset', 'gray']}
    
    def _colorize(self, text: str, color: str) -> str:
        """Apply color formatting to text."""
        return f"{self.colors.get(color, '')}{text}{self.colors['reset']}"
    
    def _should_log(self, level: VerbosityLevel) -> bool:
        """Check if current verbosity level should log this message."""
        level_order = [VerbosityLevel.MINIMAL, VerbosityLevel.STANDARD, VerbosityLevel.DETAILED, VerbosityLevel.DEBUG]
        return level_order.index(level) <= level_order.index(self.verbosity)
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def _get_elapsed_time(self) -> str:
        """Get formatted elapsed time since experiment start."""
        if self.start_time:
            elapsed = time.time() - self.start_time
            return self._format_duration(elapsed)
        return "0s"
    
    def _print_separator(self, char: str = "═", length: int = 60) -> None:
        """Print a visual separator line."""
        print(self._colorize(char * length, 'blue'), flush=True)
    
    def _print_progress_bar(self, progress: float, width: int = 40) -> str:
        """Generate a progress bar string."""
        filled = int(width * progress)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}] {progress * 100:.1f}%"
    
    # Experiment Lifecycle Methods
    
    def start_experiment(self, experiment_id: str, config: Dict[str, Any]) -> None:
        """Log experiment start with configuration summary."""
        self.start_time = time.time()
        
        if self._should_log(VerbosityLevel.MINIMAL):
            self._print_separator()
            print(self._colorize("🧪 FROHLICH EXPERIMENT STARTING", 'bold'), flush=True)
            self._print_separator()
            
        if self._should_log(VerbosityLevel.STANDARD):
            print(f"Experiment ID: {self._colorize(experiment_id[:8], 'blue')}", flush=True)
            print(f"Participants: {self._colorize(str(len(config.get('agents', []))), 'green')}", flush=True)
            print(f"Language: {self._colorize(config.get('language', 'English'), 'yellow')}", flush=True)
            print(f"Max Phase 2 rounds: {self._colorize(str(config.get('phase2_rounds', 'N/A')), 'yellow')}", flush=True)
            
        if self._should_log(VerbosityLevel.DETAILED):
            print(f"Configuration file: {config.get('config_file', 'N/A')}", flush=True)
            print(f"Started at: {datetime.now().strftime('%H:%M:%S')}", flush=True)
            
        print(flush=True)
    
    def initialize_agents(self, agent_configs: List[Dict[str, Any]]) -> None:
        """Log agent initialization phase."""
        if self._should_log(VerbosityLevel.STANDARD):
            print(self._colorize("🤖 Initializing Agents...", 'bold'), flush=True)
            
        # Initialize agent status tracking
        for config in agent_configs:
            self.agent_statuses[config.get('name', 'Unknown')] = AgentStatus(
                name=config.get('name', 'Unknown'),
                status="initializing"
            )
    
    def agent_initialized(self, agent_name: str, model: str, duration: float) -> None:
        """Log successful agent initialization."""
        if agent_name in self.agent_statuses:
            self.agent_statuses[agent_name].status = "ready"
            
        if self._should_log(VerbosityLevel.STANDARD):
            model_display = model.split('/')[-1] if '/' in model else model  # Shorten model name
            duration_str = f" [{self._format_duration(duration)}]" if self._should_log(VerbosityLevel.DETAILED) else ""
            print(f"  ✅ {self._colorize(agent_name, 'green')} ({model_display}){duration_str}", flush=True)
    
    def agents_ready(self, total_init_time: float) -> None:
        """Log completion of agent initialization."""
        if self._should_log(VerbosityLevel.STANDARD):
            duration_str = f" in {self._format_duration(total_init_time)}" if self._should_log(VerbosityLevel.DETAILED) else ""
            print(f"\n✨ All agents ready{duration_str}\n", flush=True)
    
    # Phase 1 Methods
    
    def start_phase1(self, participant_count: int) -> None:
        """Log Phase 1 start."""
        self.phase_start_time = time.time()
        
        if self._should_log(VerbosityLevel.MINIMAL):
            print(self._colorize("📖 PHASE 1: Individual Familiarization", 'bold'), flush=True)
            
        if self._should_log(VerbosityLevel.STANDARD):
            print(self._colorize("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", 'blue'), flush=True)
            print(f"Running parallel familiarization for {participant_count} participants...", flush=True)
            print(flush=True)
            
        # Update agent statuses
        for agent_status in self.agent_statuses.values():
            agent_status.status = "phase1_active"
            agent_status.current_task = "Familiarization"
            agent_status.progress = 0.0
    
    def phase1_agent_progress(self, agent_name: str, step: str, progress: float) -> None:
        """Log individual agent progress in Phase 1."""
        if agent_name in self.agent_statuses:
            self.agent_statuses[agent_name].current_task = step
            self.agent_statuses[agent_name].progress = progress
            
        if self._should_log(VerbosityLevel.DETAILED):
            progress_bar = self._print_progress_bar(progress, width=20)
            print(f"  {agent_name}: {step} {progress_bar}", flush=True)
    
    def phase1_completed(self, results_summary: List[Dict[str, Any]], duration: float) -> None:
        """Log Phase 1 completion."""
        if self._should_log(VerbosityLevel.STANDARD):
            print(f"\n🎯 {self._colorize('Phase 1 Complete', 'green')} - Duration: {self._format_duration(duration)}", flush=True)
            
        if self._should_log(VerbosityLevel.DETAILED):
            for result in results_summary:
                name = result.get('name', 'Unknown')
                earnings = result.get('earnings', 0.0)
                print(f"  {name}: ${earnings:.2f} earned", flush=True)
                
        print(flush=True)
        
        # Update agent statuses
        for agent_status in self.agent_statuses.values():
            agent_status.status = "phase1_complete"
            agent_status.current_task = "Ready for Phase 2"
            agent_status.progress = 1.0
    
    # Phase 2 Methods
    
    def start_phase2(self, max_rounds: int) -> None:
        """Log Phase 2 start."""
        self.phase_start_time = time.time()
        
        if self._should_log(VerbosityLevel.MINIMAL):
            print(self._colorize("💬 PHASE 2: Group Discussion", 'bold'), flush=True)
            
        if self._should_log(VerbosityLevel.STANDARD):
            print(self._colorize("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", 'blue'), flush=True)
            print(f"Beginning group discussion (max {max_rounds} rounds)...", flush=True)
            print(flush=True)
            
        # Update agent statuses
        for agent_status in self.agent_statuses.values():
            agent_status.status = "phase2_active"
            agent_status.current_task = "Waiting to speak"
            agent_status.progress = 0.0
    
    def phase2_round_start(self, round_num: int, max_rounds: int, speaking_order: List[str]) -> None:
        """Log start of discussion round."""
        if self._should_log(VerbosityLevel.STANDARD):
            progress = (round_num - 1) / max_rounds
            progress_indicator = f" ({round_num}/{max_rounds})" if self._should_log(VerbosityLevel.DETAILED) else ""
            
            print(f"🗣️  {self._colorize(f'Round {round_num}{progress_indicator}', 'bold')}", flush=True)
            
            if self._should_log(VerbosityLevel.DETAILED):
                speaking_list = " → ".join(speaking_order)
                print(f"   Speaking order: {speaking_list}", flush=True)
    
    def phase2_agent_speaking(self, agent_name: str, round_num: int) -> None:
        """Log when an agent is speaking."""
        if agent_name in self.agent_statuses:
            self.agent_statuses[agent_name].current_task = f"Speaking (Round {round_num})"
            
        if self._should_log(VerbosityLevel.DETAILED):
            print(f"   💭 {self._colorize(agent_name, 'yellow')} is thinking...", flush=True)
    
    def phase2_agent_response(self, agent_name: str, message_length: int, response_time: float) -> None:
        """Log agent response completion."""
        if self._should_log(VerbosityLevel.DETAILED):
            timing = f" [{self._format_duration(response_time)}]" if response_time > 0 else ""
            print(f"   ✅ {agent_name} responded ({message_length} chars){timing}", flush=True)
    
    def phase2_round_complete(self, round_num: int, duration: float) -> None:
        """Log completion of discussion round."""
        if self._should_log(VerbosityLevel.STANDARD):
            timing = f" - {self._format_duration(duration)}" if self._should_log(VerbosityLevel.DETAILED) else ""
            print(f"   ✅ Round {round_num} complete{timing}\n", flush=True)
    
    def phase2_voting_initiated(self, round_num: int) -> None:
        """Log voting initiation."""
        if self._should_log(VerbosityLevel.STANDARD):
            print(f"🗳️  {self._colorize('Voting initiated', 'bold')} (Round {round_num})", flush=True)
            
        # Update agent statuses
        for agent_status in self.agent_statuses.values():
            agent_status.current_task = "Voting"
    
    def phase2_voting_result(self, consensus_reached: bool, chosen_principle: Optional[str], 
                           constraint_amount: Optional[int], round_num: int) -> None:
        """Log voting results."""
        if consensus_reached:
            if self._should_log(VerbosityLevel.MINIMAL):
                principle_display = chosen_principle if chosen_principle else "Unknown"
                constraint_text = f" (constraint: ${constraint_amount})" if constraint_amount else ""
                print(f"🎉 {self._colorize('Consensus Reached!', 'green')} Principle: {principle_display}{constraint_text}", flush=True)
        else:
            if self._should_log(VerbosityLevel.STANDARD):
                print(f"⏳ No consensus yet - continuing discussion...", flush=True)
        print(flush=True)
    
    def phase2_completed(self, consensus_reached: bool, final_round: int, duration: float, 
                        payoff_summary: Optional[Dict[str, float]] = None) -> None:
        """Log Phase 2 completion."""
        if self._should_log(VerbosityLevel.STANDARD):
            status = "with consensus" if consensus_reached else "without consensus"
            print(f"🏁 {self._colorize(f'Phase 2 Complete {status}', 'green')} - Duration: {self._format_duration(duration)}", flush=True)
            print(f"   Rounds conducted: {final_round}", flush=True)
            
        if payoff_summary and self._should_log(VerbosityLevel.DETAILED):
            print("   Final earnings:", flush=True)
            for name, earnings in payoff_summary.items():
                print(f"     {name}: ${earnings:.2f}", flush=True)
                
        print(flush=True)
        
        # Update agent statuses
        for agent_status in self.agent_statuses.values():
            agent_status.status = "completed"
            agent_status.current_task = "Experiment complete"
            agent_status.progress = 1.0
    
    # Experiment Completion Methods
    
    def experiment_completed(self, experiment_summary: Dict[str, Any]) -> None:
        """Log experiment completion with summary."""
        total_duration = time.time() - self.start_time if self.start_time else 0
        
        if self._should_log(VerbosityLevel.MINIMAL):
            self._print_separator()
            print(self._colorize("✅ EXPERIMENT COMPLETED", 'bold'), flush=True)
            self._print_separator()
            
        if self._should_log(VerbosityLevel.STANDARD):
            print(f"Total Duration: {self._colorize(self._format_duration(total_duration), 'green')}", flush=True)
            
            consensus = experiment_summary.get('consensus_reached', False)
            if consensus:
                principle = experiment_summary.get('chosen_principle', 'Unknown')
                print(f"Consensus: {self._colorize('✅ ' + principle, 'green')}", flush=True)
            else:
                print(f"Consensus: {self._colorize('❌ Not reached', 'yellow')}", flush=True)

            transcript_file = experiment_summary.get('transcript_file')
            if transcript_file:
                print(f"Transcript saved: {transcript_file}", flush=True)
                
        if self._should_log(VerbosityLevel.DETAILED):
            errors = experiment_summary.get('total_errors', 0)
            if errors > 0:
                print(f"Errors: {errors} (all recovered)", flush=True)
            else:
                print("Errors: None", flush=True)
                
            results_file = experiment_summary.get('results_file')
            if results_file:
                print(f"Results saved: {results_file}", flush=True)
                
            trace_url = experiment_summary.get('trace_url')
            if trace_url:
                print(f"🔗 Trace: {trace_url}", flush=True)
        
        print(flush=True)
    
    # Error and Warning Methods
    
    def log_warning(self, message: str, context: Optional[str] = None) -> None:
        """Log a warning message."""
        if self._should_log(VerbosityLevel.STANDARD):
            context_str = f" ({context})" if context else ""
            print(f"⚠️  {self._colorize(message, 'yellow')}{context_str}", flush=True)
    
    def log_error(self, message: str, context: Optional[str] = None) -> None:
        """Log an error message."""
        if self._should_log(VerbosityLevel.MINIMAL):
            context_str = f" ({context})" if context else ""
            print(f"❌ {self._colorize(message, 'red')}{context_str}", flush=True)
    
    def log_recovery(self, message: str) -> None:
        """Log error recovery."""
        if self._should_log(VerbosityLevel.STANDARD):
            print(f"🔄 {self._colorize(message, 'blue')}", flush=True)
    
    # Debug and Technical Methods (for DEBUG verbosity level)
    
    def log_debug(self, message: str) -> None:
        """Log debug information (only in DEBUG mode)."""
        if self._should_log(VerbosityLevel.DEBUG):
            print(f"{self._colorize('[DEBUG]', 'gray')} {message}", flush=True)
    
    def log_technical(self, message: str) -> None:
        """Log technical details (only in DEBUG mode)."""
        if self._should_log(VerbosityLevel.DEBUG):
            print(f"{self._colorize('[TECH]', 'gray')} {message}", flush=True)


# Convenience function for easy integration
def create_process_logger(verbosity: str = "standard", use_colors: bool = True) -> ProcessFlowLogger:
    """
    Create a ProcessFlowLogger with specified verbosity level.
    
    Args:
        verbosity: One of "minimal", "standard", "detailed", "debug"
        use_colors: Whether to use colored output
        
    Returns:
        Configured ProcessFlowLogger instance
    """
    try:
        verbosity_level = VerbosityLevel(verbosity.lower())
    except ValueError:
        verbosity_level = VerbosityLevel.STANDARD
        
    return ProcessFlowLogger(verbosity_level, use_colors)
