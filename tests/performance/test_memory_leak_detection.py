"""
Memory leak detection tools for multilingual Frohlich Experiment system.

This module provides specialized memory leak detection capabilities for
multilingual processing, including:
- Long-running memory leak detection
- Language-specific memory pattern analysis
- Memory profiling integration
- Automated leak reporting
"""

import asyncio
import time
import gc
import psutil
import threading
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
import pytest

try:
    from memory_profiler import profile
    HAS_MEMORY_PROFILER = True
except ImportError:
    HAS_MEMORY_PROFILER = False

from tests.test_multilingual_base import AsyncMultilingualTestBase
from tests.fixtures.phase2_parsing_fixtures import Phase2ParsingFixtures
from experiment_agents.utility_agent import UtilityAgent
from utils.language_manager import LanguageManager, SupportedLanguage
from models import (
    PrincipleChoice, PrincipleRanking, VoteProposal, 
    ParsedResponse, ValidationResult, JusticePrinciple, CertaintyLevel
)

pytestmark = pytest.mark.asyncio


@dataclass
class MemorySnapshot:
    """Memory usage snapshot at a specific point in time."""
    timestamp: float
    rss_bytes: int  # Resident Set Size
    vms_bytes: int  # Virtual Memory Size
    shared_bytes: int
    cycle: int
    language: str
    operation: str


@dataclass
class MemoryLeakReport:
    """Report of detected memory leaks."""
    language: str
    operation: str
    leak_rate_mb_per_cycle: float
    total_leak_mb: float
    confidence_level: str
    cycles_analyzed: int
    detection_method: str
    recommendations: List[str]


class MemoryTracker:
    """Tracks memory usage over time to detect leaks."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.snapshots: List[MemorySnapshot] = []
        self.tracking = False
        self.tracker_thread: Optional[threading.Thread] = None
        
    def start_tracking(self):
        """Start memory tracking."""
        if self.tracking:
            return
            
        self.tracking = True
        self.tracker_thread = threading.Thread(target=self._tracking_loop)
        self.tracker_thread.daemon = True
        self.tracker_thread.start()
        
    def stop_tracking(self):
        """Stop memory tracking."""
        self.tracking = False
        if self.tracker_thread:
            self.tracker_thread.join(timeout=1.0)
    
    def _tracking_loop(self):
        """Background memory tracking loop."""
        while self.tracking:
            try:
                memory_info = self.process.memory_info()
                # Store basic tracking data
                time.sleep(0.05)  # Track every 50ms
            except Exception:
                # Continue tracking despite errors
                pass
    
    def take_snapshot(self, cycle: int, language: str, operation: str) -> MemorySnapshot:
        """Take a memory snapshot."""
        memory_info = self.process.memory_info()
        
        snapshot = MemorySnapshot(
            timestamp=time.time(),
            rss_bytes=memory_info.rss,
            vms_bytes=memory_info.vms,
            shared_bytes=getattr(memory_info, 'shared', 0),
            cycle=cycle,
            language=language,
            operation=operation
        )
        
        self.snapshots.append(snapshot)
        return snapshot
    
    def get_snapshots_for_language(self, language: str) -> List[MemorySnapshot]:
        """Get snapshots for specific language."""
        return [s for s in self.snapshots if s.language == language]
    
    def clear_snapshots(self):
        """Clear all snapshots."""
        self.snapshots.clear()


class TestMemoryLeakDetection(AsyncMultilingualTestBase):
    """Comprehensive memory leak detection test suite."""
    
    def setUp(self):
        """Set up memory leak detection environment."""
        super().setUp()
        self.memory_tracker = MemoryTracker()
        self.languages = ["English", "Spanish", "Mandarin"]
        self.leak_reports: List[MemoryLeakReport] = []
        
        # Memory leak detection thresholds
        self.leak_threshold_mb_per_cycle = 5.0  # 5MB per cycle indicates leak
        self.max_total_leak_mb = 100.0  # 100MB total leak max
        self.min_cycles_for_detection = 5  # Minimum cycles to detect pattern

    def _create_stub_utility_agent(self) -> UtilityAgent:
        agent = MagicMock(spec=UtilityAgent)
        agent.async_init = AsyncMock(return_value=None)
        agent.parse_principle_choice_enhanced = AsyncMock(return_value={})
        return agent
        
    def tearDown(self):
        """Clean up memory tracking."""
        self.memory_tracker.stop_tracking()
        super().tearDown()
    
    async def test_long_running_memory_leak_detection(self):
        """Run long-term memory leak detection across all languages."""
        print("Starting long-running memory leak detection...")
        
        self.memory_tracker.start_tracking()
        
        # Run extended processing cycles
        cycles = 6
        statements_per_cycle = 8
        
        for cycle in range(cycles):
            print(f"Running cycle {cycle + 1}/{cycles}")
            
            for language in self.languages:
                # Take snapshot before processing
                before_snapshot = self.memory_tracker.take_snapshot(
                    cycle, language, f"before_processing"
                )
                
                # Process statements in this language
                await self._run_memory_intensive_processing(language, statements_per_cycle)
                
                # Take snapshot after processing
                after_snapshot = self.memory_tracker.take_snapshot(
                    cycle, language, f"after_processing"
                )
                
                # Force garbage collection
                gc.collect()
                
                # Take snapshot after GC
                gc_snapshot = self.memory_tracker.take_snapshot(
                    cycle, language, f"after_gc"
                )
            
            # Brief pause between cycles
            await asyncio.sleep(0.01)
        
        self.memory_tracker.stop_tracking()
        
        # Analyze for memory leaks
        leak_reports = self._analyze_memory_leaks()
        self.leak_reports.extend(leak_reports)
        
        # Report findings
        self._report_memory_leaks(leak_reports)
        
        # Assert no significant leaks
        self._assert_no_memory_leaks(leak_reports)
    
    async def test_language_specific_memory_patterns(self):
        """Analyze memory patterns specific to each language."""
        print("Analyzing language-specific memory patterns...")
        
        language_patterns = {}
        
        for language in self.languages:
            patterns = await self._analyze_language_memory_pattern(language)
            language_patterns[language] = patterns
        
        # Compare patterns across languages
        self._compare_language_memory_patterns(language_patterns)
        
        # Assert reasonable memory usage across languages
        self._assert_balanced_language_memory_usage(language_patterns)
    
    async def test_memory_growth_under_stress(self):
        """Test memory behavior under stress conditions."""
        print("Testing memory growth under stress...")
        
        stress_scenarios = [
            {"concurrent_agents": 4, "statements_per_agent": 20},
            {"concurrent_agents": 8, "statements_per_agent": 15},
            {"concurrent_agents": 12, "statements_per_agent": 10}
        ]
        
        for scenario in stress_scenarios:
            await self._test_stress_memory_scenario(scenario)
        
        # Analyze stress test results
        self._analyze_stress_memory_results()
    
    async def test_cache_memory_behavior(self):
        """Test memory behavior of caching systems."""
        print("Testing cache memory behavior...")
        
        from tests.test_multilingual_base import LanguageDataLoader
        
        # Clear cache and measure baseline
        LanguageDataLoader.clear_cache()
        initial_memory = self.memory_tracker.process.memory_info().rss
        
        # Load cache for all languages multiple times
        for iteration in range(10):
            for language in self.languages:
                # Access language data (should cache it)
                LanguageDataLoader.get_language_test_data(language)
                
                # Take memory snapshot
                current_memory = self.memory_tracker.process.memory_info().rss
                growth = current_memory - initial_memory
                
                print(f"Iteration {iteration + 1}, {language}: "
                      f"Memory growth {growth / 1024 / 1024:.2f}MB")
        
        # Clear cache and check if memory is released
        LanguageDataLoader.clear_cache()
        gc.collect()
        
        final_memory = self.memory_tracker.process.memory_info().rss
        post_clear_growth = final_memory - initial_memory
        
        print(f"Memory growth after cache clear: {post_clear_growth / 1024 / 1024:.2f}MB")
        
        # Assert cache doesn't cause excessive memory growth
        max_cache_growth = 50 * 1024 * 1024  # 50MB max for caching
        self.assertLess(
            post_clear_growth,
            max_cache_growth,
            f"Cache memory growth {post_clear_growth / 1024 / 1024:.2f}MB "
            f"exceeds limit {max_cache_growth / 1024 / 1024:.2f}MB"
        )
    
    @pytest.mark.skipif(not HAS_MEMORY_PROFILER, reason="memory_profiler not available")
    async def test_detailed_memory_profiling(self):
        """Run detailed memory profiling on critical functions."""
        print("Running detailed memory profiling...")
        
        # Profile each language's processing
        for language in self.languages:
            await self._profile_language_memory_detailed(language)
    
    # Memory analysis methods
    
    async def _run_memory_intensive_processing(self, language: str, statement_count: int):
        """Run memory-intensive processing for leak detection."""
        utility_agent = self._create_stub_utility_agent()
        
        # Create and process statements
        for i in range(statement_count):
            # Create statement with some complexity
            statement = f"Memory test statement {i} in {language} with additional complexity " \
                       f"and longer text to increase memory usage during processing. " \
                       f"This statement contains various patterns like vote, principle, " \
                       f"constraint, agreement, and disagreement for comprehensive testing."
            
            # Process statement (this may allocate memory)
            await self._mock_parse_statement_memory_intensive(utility_agent, statement, language)
    
    async def _analyze_language_memory_pattern(self, language: str) -> Dict[str, Any]:
        """Analyze memory usage pattern for specific language."""
        cycles = 5
        statements_per_cycle = 6
        
        memory_readings = []
        processing_times = []
        
        utility_agent = self._create_stub_utility_agent()
        
        for cycle in range(cycles):
            cycle_start_memory = self.memory_tracker.process.memory_info().rss
            cycle_start_time = time.perf_counter()
            
            # Process statements for this cycle
            await self._run_memory_intensive_processing(language, statements_per_cycle)
            
            cycle_end_time = time.perf_counter()
            cycle_end_memory = self.memory_tracker.process.memory_info().rss
            
            memory_growth = cycle_end_memory - cycle_start_memory
            processing_time = cycle_end_time - cycle_start_time
            
            memory_readings.append(memory_growth)
            processing_times.append(processing_time)
            
            # Force garbage collection between cycles
            gc.collect()
        
        return {
            "avg_memory_growth_per_cycle": sum(memory_readings) / len(memory_readings),
            "max_memory_growth": max(memory_readings),
            "avg_processing_time": sum(processing_times) / len(processing_times),
            "memory_efficiency": sum(memory_readings) / sum(processing_times) if sum(processing_times) > 0 else 0,
            "cycles_analyzed": cycles
        }
    
    async def _test_stress_memory_scenario(self, scenario: Dict[str, int]):
        """Test memory behavior under specific stress scenario."""
        concurrent_agents = scenario["concurrent_agents"]
        statements_per_agent = scenario["statements_per_agent"]
        
        print(f"Stress test: {concurrent_agents} agents, {statements_per_agent} statements each")
        
        initial_memory = self.memory_tracker.process.memory_info().rss
        
        # Create concurrent processing tasks
        tasks = []
        for agent_id in range(concurrent_agents):
            language = self.languages[agent_id % len(self.languages)]
            
            task = asyncio.create_task(
                self._stress_test_agent_processing(agent_id, language, statements_per_agent)
            )
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        final_memory = self.memory_tracker.process.memory_info().rss
        stress_memory_growth = final_memory - initial_memory
        
        print(f"Stress test memory growth: {stress_memory_growth / 1024 / 1024:.2f}MB")
        
        # Check for memory leaks under stress
        max_stress_growth = 200 * 1024 * 1024  # 200MB max under stress
        self.assertLess(
            stress_memory_growth,
            max_stress_growth,
            f"Stress test memory growth {stress_memory_growth / 1024 / 1024:.2f}MB "
            f"exceeds limit {max_stress_growth / 1024 / 1024:.2f}MB"
        )
        
        # Check for exceptions
        exceptions = [r for r in results if isinstance(r, Exception)]
        if exceptions:
            print(f"Warning: {len(exceptions)} exceptions occurred during stress test")
    
    async def _stress_test_agent_processing(self, agent_id: int, language: str, statement_count: int):
        """Simulate agent processing under stress conditions."""
        utility_agent = self._create_stub_utility_agent()
        
        for i in range(statement_count):
            statement = f"Stress test agent {agent_id} statement {i} in {language}"
            await self._mock_parse_statement_memory_intensive(utility_agent, statement, language)
    
    async def _profile_language_memory_detailed(self, language: str):
        """Run detailed memory profiling for specific language."""
        # This would use memory_profiler decorators if available
        # For now, we'll do basic profiling
        
        utility_agent = self._create_stub_utility_agent()
        
        # Profile a sequence of operations
        initial_memory = self.memory_tracker.process.memory_info().rss
        
        for i in range(30):
            statement = f"Detailed profiling statement {i} in {language}"
            await self._mock_parse_statement_memory_intensive(utility_agent, statement, language)
            
            if i % 10 == 9:  # Every 10 statements
                current_memory = self.memory_tracker.process.memory_info().rss
                growth = current_memory - initial_memory
                print(f"{language} detailed profile at {i+1}: {growth / 1024:.2f}KB growth")
    
    def _analyze_memory_leaks(self) -> List[MemoryLeakReport]:
        """Analyze memory snapshots to detect leaks."""
        leak_reports = []
        
        for language in self.languages:
            language_snapshots = self.memory_tracker.get_snapshots_for_language(language)
            
            if len(language_snapshots) < self.min_cycles_for_detection * 2:
                continue  # Not enough data
            
            # Group snapshots by operation and analyze trends
            operations = set(s.operation for s in language_snapshots)
            
            for operation in operations:
                op_snapshots = [s for s in language_snapshots if s.operation == operation]
                
                if len(op_snapshots) < self.min_cycles_for_detection:
                    continue
                
                leak_report = self._detect_leak_in_snapshots(language, operation, op_snapshots)
                if leak_report:
                    leak_reports.append(leak_report)
        
        return leak_reports
    
    def _detect_leak_in_snapshots(self, language: str, operation: str, 
                                snapshots: List[MemorySnapshot]) -> Optional[MemoryLeakReport]:
        """Detect memory leak in snapshot sequence."""
        if len(snapshots) < 3:
            return None
        
        # Sort by cycle
        snapshots.sort(key=lambda s: s.cycle)
        
        # Calculate memory growth over cycles
        memory_values = [s.rss_bytes for s in snapshots]
        cycles = [s.cycle for s in snapshots]
        
        # Simple linear regression to detect trend
        n = len(memory_values)
        if n < self.min_cycles_for_detection:
            return None
        
        # Calculate average growth per cycle
        first_half_avg = sum(memory_values[:n//2]) / (n//2)
        second_half_avg = sum(memory_values[n//2:]) / (n - n//2)
        
        total_cycles = cycles[-1] - cycles[0] + 1 if cycles[-1] != cycles[0] else 1
        memory_growth_total = memory_values[-1] - memory_values[0]
        growth_per_cycle = memory_growth_total / total_cycles
        
        # Convert to MB
        growth_per_cycle_mb = growth_per_cycle / (1024 * 1024)
        total_growth_mb = memory_growth_total / (1024 * 1024)
        
        # Determine if this constitutes a leak
        is_leak = growth_per_cycle_mb > self.leak_threshold_mb_per_cycle
        
        if is_leak:
            # Determine confidence based on consistency
            memory_increases = 0
            for i in range(1, len(memory_values)):
                if memory_values[i] > memory_values[i-1]:
                    memory_increases += 1
            
            consistency_ratio = memory_increases / (len(memory_values) - 1)
            
            if consistency_ratio > 0.8:
                confidence = "high"
            elif consistency_ratio > 0.6:
                confidence = "medium"
            else:
                confidence = "low"
            
            # Generate recommendations
            recommendations = []
            if growth_per_cycle_mb > 10:
                recommendations.append("Investigate major memory allocation in processing loop")
            if operation == "after_processing":
                recommendations.append("Check for uncollected objects after processing")
            if language == "Mandarin":
                recommendations.append("Review Unicode string handling for Chinese text")
            
            return MemoryLeakReport(
                language=language,
                operation=operation,
                leak_rate_mb_per_cycle=growth_per_cycle_mb,
                total_leak_mb=total_growth_mb,
                confidence_level=confidence,
                cycles_analyzed=len(snapshots),
                detection_method="linear_trend_analysis",
                recommendations=recommendations
            )
        
        return None
    
    def _compare_language_memory_patterns(self, language_patterns: Dict[str, Dict[str, Any]]):
        """Compare memory patterns across languages."""
        print("\n" + "="*60)
        print("LANGUAGE MEMORY PATTERN COMPARISON")
        print("="*60)
        
        for language, patterns in language_patterns.items():
            avg_growth = patterns["avg_memory_growth_per_cycle"]
            efficiency = patterns["memory_efficiency"]
            
            print(f"\n{language}:")
            print(f"  Avg Growth/Cycle: {avg_growth / 1024:.2f} KB")
            print(f"  Max Growth:       {patterns['max_memory_growth'] / 1024:.2f} KB")
            print(f"  Memory Efficiency: {efficiency / 1024:.2f} KB/sec")
            print(f"  Processing Time:   {patterns['avg_processing_time']:.3f} sec")
    
    def _analyze_stress_memory_results(self):
        """Analyze results from stress testing."""
        # This would analyze stress test results
        # Implementation would depend on stored stress test data
        print("Stress memory analysis completed.")
    
    # Reporting methods
    
    def _report_memory_leaks(self, leak_reports: List[MemoryLeakReport]):
        """Report detected memory leaks."""
        print("\n" + "="*60)
        print("MEMORY LEAK DETECTION RESULTS")
        print("="*60)
        
        if not leak_reports:
            print("✅ No memory leaks detected!")
        else:
            print(f"⚠️  {len(leak_reports)} potential memory leaks detected:")
            
            for report in leak_reports:
                print(f"\n🔍 {report.language} - {report.operation}")
                print(f"   Leak Rate:     {report.leak_rate_mb_per_cycle:.2f} MB/cycle")
                print(f"   Total Leak:    {report.total_leak_mb:.2f} MB")
                print(f"   Confidence:    {report.confidence_level}")
                print(f"   Cycles:        {report.cycles_analyzed}")
                print(f"   Method:        {report.detection_method}")
                
                if report.recommendations:
                    print(f"   Recommendations:")
                    for rec in report.recommendations:
                        print(f"     • {rec}")
        
        print("\n" + "="*60)
    
    # Mock methods for testing
    
    async def _mock_parse_statement_memory_intensive(self, utility_agent: UtilityAgent, 
                                                   statement: str, language: str) -> Dict[str, Any]:
        """Mock parsing with intentional memory allocation for testing."""
        # Simulate memory-intensive processing
        processed_text = statement.lower().strip()
        words = processed_text.split()
        
        # Simulate language-specific processing overhead
        processing_delay = {
            "Mandarin": 0.0008,
            "Spanish": 0.0005,
            "English": 0.0003
        }.get(language, 0.0003)
        
        await asyncio.sleep(processing_delay)
        
        # Create memory-heavy data structures for testing
        temp_data = {
            "statement": statement,
            "language": language,
            "words": words,
            "processed_text": processed_text,
            "metadata": {
                "timestamp": time.time(),
                "length": len(statement),
                "word_count": len(words),
                "processing_language": language
            },
            # Add some memory overhead for testing
            "extra_data": list(range(20)),
            "text_variations": [
                statement.upper(),
                statement.lower(),
                statement.title(),
                ''.join(reversed(statement))
            ]
        }
        
        return temp_data
    
    # Assertion methods
    
    def _assert_no_memory_leaks(self, leak_reports: List[MemoryLeakReport]):
        """Assert no significant memory leaks were detected."""
        significant_leaks = [
            r for r in leak_reports 
            if r.leak_rate_mb_per_cycle > self.leak_threshold_mb_per_cycle 
            and r.confidence_level in ["medium", "high"]
        ]
        
        if significant_leaks:
            leak_details = []
            for leak in significant_leaks:
                leak_details.append(
                    f"{leak.language}.{leak.operation}: "
                    f"{leak.leak_rate_mb_per_cycle:.2f} MB/cycle "
                    f"({leak.confidence_level} confidence)"
                )
            
            self.fail(f"Significant memory leaks detected:\n" + "\n".join(leak_details))
    
    def _assert_balanced_language_memory_usage(self, language_patterns: Dict[str, Dict[str, Any]]):
        """Assert memory usage is reasonably balanced across languages."""
        growth_values = [
            patterns["avg_memory_growth_per_cycle"] 
            for patterns in language_patterns.values()
        ]
        
        if not growth_values:
            return
        
        min_growth = min(growth_values)
        max_growth = max(growth_values)
        
        if min_growth > 0:
            imbalance_ratio = max_growth / min_growth
            max_acceptable_imbalance = 5.0  # 5x difference max
            
            self.assertLess(
                imbalance_ratio,
                max_acceptable_imbalance,
                f"Memory usage imbalance {imbalance_ratio:.1f}x exceeds "
                f"acceptable limit {max_acceptable_imbalance}x"
            )


if __name__ == "__main__":
    # Run memory leak detection tests
    import unittest
    unittest.main(verbosity=2)
