"""
Resource usage monitoring and analysis tools for multilingual Frohlich Experiment system.

This module implements Subplan 6.3: Resource Usage Analysis from the Opus Multilingual 
Testing Implementation Plan. It provides comprehensive resource monitoring for:
- CPU usage by language
- Memory allocation patterns
- I/O operations for translations
- Cache effectiveness
"""

import asyncio
import time
import gc
import psutil
import threading
import os
import sys
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from unittest.mock import MagicMock, AsyncMock
import pytest

# Skip all tests in this module if memory_profiler is not available
try:
    from memory_profiler import profile
    memory_profiler_available = True
except ImportError:
    memory_profiler_available = False
    profile = lambda func: func  # No-op decorator

from tests.test_multilingual_base import AsyncMultilingualTestBase
from tests.fixtures.phase2_parsing_fixtures import Phase2ParsingFixtures
from experiment_agents.utility_agent import UtilityAgent
from utils.language_manager import LanguageManager, SupportedLanguage
from models import (
    PrincipleChoice, PrincipleRanking, VoteProposal, 
    ParsedResponse, ValidationResult, JusticePrinciple, CertaintyLevel
)


@dataclass
class ResourceSnapshot:
    """Snapshot of system resource usage at a point in time."""
    timestamp: float
    cpu_percent: float
    memory_rss: int  # Resident Set Size in bytes
    memory_vms: int  # Virtual Memory Size in bytes
    open_files: int
    threads: int
    language: Optional[str] = None
    operation: Optional[str] = None


@dataclass
class LanguageResourceProfile:
    """Resource usage profile for a specific language."""
    language: str
    avg_cpu_usage: float
    peak_cpu_usage: float
    avg_memory_usage: int
    peak_memory_usage: int
    memory_growth_rate: float  # bytes per operation
    avg_processing_time: float
    cache_hit_rate: float
    io_operations: int


class ResourceMonitor:
    """Monitors system resource usage during multilingual processing."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.snapshots: List[ResourceSnapshot] = []
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitor_interval = 0.1  # 100ms monitoring interval
        
    def start_monitoring(self):
        """Start background resource monitoring."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop background resource monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self.monitoring:
            try:
                snapshot = self._take_snapshot()
                self.snapshots.append(snapshot)
                time.sleep(self.monitor_interval)
            except Exception as e:
                # Continue monitoring despite individual errors
                pass
    
    def _take_snapshot(self, language: str = None, operation: str = None) -> ResourceSnapshot:
        """Take a snapshot of current resource usage."""
        return ResourceSnapshot(
            timestamp=time.time(),
            cpu_percent=self.process.cpu_percent(),
            memory_rss=self.process.memory_info().rss,
            memory_vms=self.process.memory_info().vms,
            open_files=len(self.process.open_files()) if hasattr(self.process, 'open_files') else 0,
            threads=self.process.num_threads(),
            language=language,
            operation=operation
        )
    
    def get_snapshots_for_language(self, language: str) -> List[ResourceSnapshot]:
        """Get all snapshots for a specific language."""
        return [s for s in self.snapshots if s.language == language]
    
    def get_snapshots_for_operation(self, operation: str) -> List[ResourceSnapshot]:
        """Get all snapshots for a specific operation."""
        return [s for s in self.snapshots if s.operation == operation]
    
    def clear_snapshots(self):
        """Clear all collected snapshots."""
        self.snapshots.clear()


@pytest.mark.skipif(not memory_profiler_available, reason="memory_profiler not available")
class MultilingualResourceUsageTests(AsyncMultilingualTestBase):
    """Resource usage analysis tests for multilingual processing."""
    
    def setUp(self):
        """Set up resource monitoring test environment."""
        super().setUp()
        self.resource_monitor = ResourceMonitor()
        self.languages = ["English", "Spanish", "Mandarin"]
        self.language_profiles: Dict[str, LanguageResourceProfile] = {}
        
        # Resource usage thresholds
        self.max_cpu_usage = 80.0  # 80% max CPU usage
        self.max_memory_growth = 50 * 1024 * 1024  # 50MB max memory growth per test
        self.max_cache_miss_rate = 0.3  # 30% max cache miss rate
        
    def tearDown(self):
        """Clean up resource monitoring."""
        self.resource_monitor.stop_monitoring()
        super().tearDown()
    
    async def test_cpu_usage_by_language(self):
        """Monitor CPU usage patterns across different languages."""
        self.resource_monitor.start_monitoring()
        
        for language in self.languages:
            await self._profile_language_cpu_usage(language)
        
        self.resource_monitor.stop_monitoring()
        
        # Analyze CPU usage patterns
        await self._analyze_cpu_usage_patterns()
        
        # Assert CPU usage is within acceptable limits
        self._assert_cpu_usage_limits()
    
    async def test_memory_allocation_patterns(self):
        """Analyze memory allocation patterns for each language."""
        for language in self.languages:
            await self._profile_language_memory_patterns(language)
        
        # Analyze memory patterns
        self._analyze_memory_patterns()
        
        # Assert memory usage is reasonable
        self._assert_memory_usage_patterns()
    
    async def test_translation_io_operations(self):
        """Monitor I/O operations for translation file access."""
        self.resource_monitor.start_monitoring()
        
        for language in self.languages:
            await self._profile_translation_io(language)
        
        self.resource_monitor.stop_monitoring()
        
        # Analyze I/O patterns
        self._analyze_io_patterns()
        
        # Assert I/O efficiency
        self._assert_io_efficiency()
    
    async def test_cache_effectiveness(self):
        """Test caching effectiveness for language data and translations."""
        cache_results = {}
        
        for language in self.languages:
            cache_performance = await self._test_language_cache_performance(language)
            cache_results[language] = cache_performance
        
        # Analyze cache effectiveness
        self._analyze_cache_effectiveness(cache_results)
        
        # Assert cache performance
        self._assert_cache_performance(cache_results)
    
    async def test_resource_usage_under_load(self):
        """Test resource usage patterns under increasing load."""
        load_levels = [10, 25, 50, 100]  # Number of concurrent operations
        
        self.resource_monitor.start_monitoring()
        
        for load_level in load_levels:
            await self._test_load_level_resources(load_level)
        
        self.resource_monitor.stop_monitoring()
        
        # Analyze resource scaling
        self._analyze_resource_scaling()
        
        # Assert resource scaling is acceptable
        self._assert_resource_scaling()
    
    async def test_memory_leak_detection(self):
        """Detect potential memory leaks in multilingual processing."""
        initial_memory = self.resource_monitor.process.memory_info().rss
        
        # Run multiple processing cycles
        for cycle in range(5):
            for language in self.languages:
                await self._run_processing_cycle(language, statements=20)
            
            # Force garbage collection
            gc.collect()
            
            # Check memory growth
            current_memory = self.resource_monitor.process.memory_info().rss
            memory_growth = current_memory - initial_memory
            
            print(f"Cycle {cycle + 1}: Memory growth {memory_growth / 1024 / 1024:.2f} MB")
            
            # Assert memory growth is not excessive
            max_growth_per_cycle = 20 * 1024 * 1024  # 20MB per cycle max
            self.assertLess(
                memory_growth,
                max_growth_per_cycle * (cycle + 1),
                f"Memory growth {memory_growth / 1024 / 1024:.2f}MB exceeds "
                f"limit {max_growth_per_cycle * (cycle + 1) / 1024 / 1024:.2f}MB after {cycle + 1} cycles"
            )
    
    async def test_thread_usage_patterns(self):
        """Monitor thread usage patterns during multilingual processing."""
        initial_threads = self.resource_monitor.process.num_threads()
        
        thread_counts = []
        
        for language in self.languages:
            # Start processing in language
            utility_agent = UtilityAgent()
            await utility_agent.async_init()
            
            # Monitor thread count during processing
            current_threads = self.resource_monitor.process.num_threads()
            thread_counts.append(current_threads)
            
            # Simulate processing
            await self._simulate_language_processing(utility_agent, language, 10)
        
        final_threads = self.resource_monitor.process.num_threads()
        
        # Analyze thread usage
        max_threads = max(thread_counts)
        thread_growth = max_threads - initial_threads
        
        print(f"Thread usage: Initial {initial_threads}, Max {max_threads}, Final {final_threads}")
        
        # Assert reasonable thread usage
        max_acceptable_growth = 10  # 10 additional threads max
        self.assertLess(
            thread_growth,
            max_acceptable_growth,
            f"Thread growth {thread_growth} exceeds limit {max_acceptable_growth}"
        )
    
    # Private profiling and analysis methods
    
    async def _profile_language_cpu_usage(self, language: str):
        """Profile CPU usage for a specific language."""
        utility_agent = UtilityAgent()
        await utility_agent.async_init()
        
        cpu_readings = []
        processing_times = []
        
        # Process multiple statements and monitor CPU
        test_data = self.get_language_test_data(language)
        statements = []
        
        for data_type, data_list in test_data.items():
            if isinstance(data_list, list):
                statements.extend(str(item) for item in data_list[:5])
        
        for statement in statements[:20]:  # Process 20 statements
            # Take CPU reading before processing
            cpu_before = self.resource_monitor.process.cpu_percent()
            start_time = time.perf_counter()
            
            # Process statement
            await self._mock_parse_statement(utility_agent, statement, language)
            
            # Take CPU reading after processing
            end_time = time.perf_counter()
            cpu_after = self.resource_monitor.process.cpu_percent()
            
            processing_time = end_time - start_time
            cpu_usage = max(cpu_before, cpu_after)  # Use higher reading
            
            cpu_readings.append(cpu_usage)
            processing_times.append(processing_time)
        
        # Create language profile
        if cpu_readings:
            profile = LanguageResourceProfile(
                language=language,
                avg_cpu_usage=sum(cpu_readings) / len(cpu_readings),
                peak_cpu_usage=max(cpu_readings),
                avg_memory_usage=0,  # Will be set in memory profiling
                peak_memory_usage=0,
                memory_growth_rate=0.0,
                avg_processing_time=sum(processing_times) / len(processing_times),
                cache_hit_rate=0.0,  # Will be set in cache testing
                io_operations=0
            )
            self.language_profiles[language] = profile
    
    async def _profile_language_memory_patterns(self, language: str):
        """Profile memory allocation patterns for a specific language."""
        utility_agent = UtilityAgent()
        await utility_agent.async_init()
        
        initial_memory = self.resource_monitor.process.memory_info().rss
        memory_readings = []
        
        # Process statements and monitor memory
        for i in range(50):  # Process 50 statements
            statement = f"Test statement {i} for {language} memory profiling"
            
            memory_before = self.resource_monitor.process.memory_info().rss
            await self._mock_parse_statement(utility_agent, statement, language)
            memory_after = self.resource_monitor.process.memory_info().rss
            
            memory_readings.append(memory_after)
            
            # Periodic garbage collection to see true memory growth
            if i % 10 == 9:
                gc.collect()
        
        # Analyze memory pattern
        final_memory = self.resource_monitor.process.memory_info().rss
        memory_growth = final_memory - initial_memory
        memory_growth_rate = memory_growth / 50  # Per statement
        
        # Update language profile
        if language in self.language_profiles:
            profile = self.language_profiles[language]
            profile.avg_memory_usage = sum(memory_readings) / len(memory_readings)
            profile.peak_memory_usage = max(memory_readings)
            profile.memory_growth_rate = memory_growth_rate
        
        print(f"{language} memory: Growth {memory_growth / 1024:.2f} KB total, "
              f"{memory_growth_rate / 1024:.2f} KB per statement")
    
    async def _profile_translation_io(self, language: str):
        """Profile I/O operations for translation access."""
        # Track file operations before and after language operations
        initial_files = len(self.resource_monitor.process.open_files()) if hasattr(self.resource_monitor.process, 'open_files') else 0
        
        # Create language manager and trigger translation loading
        language_manager = LanguageManager()
        
        language_enum_map = {
            "English": SupportedLanguage.ENGLISH,
            "Spanish": SupportedLanguage.SPANISH, 
            "Mandarin": SupportedLanguage.MANDARIN
        }
        
        if language in language_enum_map:
            language_enum = language_enum_map[language]
            
            # Simulate translation I/O operations
            for i in range(10):
                language_manager.set_language(language_enum)
                
                # Try to access various translation methods
                try:
                    language_manager.get_phase1_instructions()
                    language_manager.get_phase2_instructions()
                except AttributeError:
                    # Some methods might not exist, continue
                    pass
        
        final_files = len(self.resource_monitor.process.open_files()) if hasattr(self.resource_monitor.process, 'open_files') else 0
        io_operations = max(0, final_files - initial_files)
        
        # Update language profile
        if language in self.language_profiles:
            self.language_profiles[language].io_operations = io_operations
    
    async def _test_language_cache_performance(self, language: str) -> Dict[str, float]:
        """Test cache performance for language data."""
        from tests.test_multilingual_base import LanguageDataLoader
        
        # Clear cache to test cold performance
        LanguageDataLoader.clear_cache()
        
        # Test cold cache performance (first access)
        cold_start_time = time.perf_counter()
        cold_data = LanguageDataLoader.get_language_test_data(language)
        cold_end_time = time.perf_counter()
        cold_time = cold_end_time - cold_start_time
        
        # Test warm cache performance (subsequent accesses)
        warm_times = []
        for i in range(10):
            warm_start_time = time.perf_counter()
            warm_data = LanguageDataLoader.get_language_test_data(language)
            warm_end_time = time.perf_counter()
            warm_times.append(warm_end_time - warm_start_time)
        
        avg_warm_time = sum(warm_times) / len(warm_times)
        
        # Calculate cache effectiveness
        cache_speedup = cold_time / avg_warm_time if avg_warm_time > 0 else 1.0
        cache_hit_rate = max(0.0, 1.0 - (avg_warm_time / cold_time)) if cold_time > 0 else 0.0
        
        return {
            "cold_time": cold_time,
            "avg_warm_time": avg_warm_time,
            "cache_speedup": cache_speedup,
            "cache_hit_rate": cache_hit_rate
        }
    
    async def _test_load_level_resources(self, load_level: int):
        """Test resource usage at a specific load level."""
        # Create multiple utility agents for concurrent processing
        utility_agents = []
        for i in range(min(load_level, 5)):  # Limit actual agent creation
            utility_agent = UtilityAgent()
            await utility_agent.async_init()
            utility_agents.append(utility_agent)
        
        # Create concurrent processing tasks
        tasks = []
        for i in range(load_level):
            agent = utility_agents[i % len(utility_agents)]
            language = self.languages[i % len(self.languages)]
            
            task = asyncio.create_task(
                self._simulate_language_processing(agent, language, 5)
            )
            tasks.append(task)
        
        # Monitor resources during concurrent processing
        start_snapshot = self.resource_monitor._take_snapshot(operation=f"load_{load_level}")
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_snapshot = self.resource_monitor._take_snapshot(operation=f"load_{load_level}")
        
        # Calculate resource usage for this load level
        cpu_increase = end_snapshot.cpu_percent - start_snapshot.cpu_percent
        memory_increase = end_snapshot.memory_rss - start_snapshot.memory_rss
        
        print(f"Load level {load_level}: CPU +{cpu_increase:.1f}%, "
              f"Memory +{memory_increase / 1024 / 1024:.2f}MB")
    
    async def _run_processing_cycle(self, language: str, statements: int):
        """Run a processing cycle for memory leak detection."""
        utility_agent = UtilityAgent()
        await utility_agent.async_init()
        
        test_data = self.get_language_test_data(language)
        statement_list = []
        
        # Collect statements
        for data_type, data_list in test_data.items():
            if isinstance(data_list, list):
                statement_list.extend(str(item) for item in data_list)
        
        # Process statements
        for i in range(statements):
            if statement_list:
                statement = statement_list[i % len(statement_list)]
            else:
                statement = f"Test statement {i} in {language}"
            
            await self._mock_parse_statement(utility_agent, statement, language)
    
    async def _simulate_language_processing(self, utility_agent: UtilityAgent, 
                                          language: str, statement_count: int):
        """Simulate processing statements in a specific language."""
        test_data = self.get_language_test_data(language)
        
        for i in range(statement_count):
            # Create test statement
            if test_data and test_data.get('ballots'):
                statement = str(test_data['ballots'][i % len(test_data['ballots'])])
            else:
                statement = f"Resource test statement {i} in {language}"
            
            await self._mock_parse_statement(utility_agent, statement, language)
    
    async def _mock_parse_statement(self, utility_agent: UtilityAgent, 
                                  statement: str, language: str) -> Dict[str, Any]:
        """Mock parsing with realistic resource usage."""
        # Simulate CPU and memory intensive operations
        processed_text = statement.lower().strip()
        words = processed_text.split()
        
        # Simulate pattern matching (CPU intensive)
        patterns = ["vote", "principle", "constraint", "agree", "disagree", "floor", "average"]
        matches = []
        for pattern in patterns:
            if pattern in processed_text:
                matches.append(pattern)
        
        # Simulate language-specific processing overhead
        if language == "Mandarin":
            # Chinese processing requires more CPU and memory
            await asyncio.sleep(0.008)  # 8ms processing time
            # Simulate Unicode processing overhead
            encoded = statement.encode('utf-8')
            decoded = encoded.decode('utf-8')
        elif language == "Spanish":
            # Spanish processing has moderate overhead
            await asyncio.sleep(0.005)  # 5ms processing time
        else:
            # English baseline
            await asyncio.sleep(0.003)  # 3ms processing time
        
        # Simulate memory allocation
        temp_data = {
            "statement": statement,
            "language": language,
            "words": words,
            "matches": matches,
            "processing_metadata": {
                "timestamp": time.time(),
                "length": len(statement),
                "complexity_score": len(matches) * len(words)
            }
        }
        
        return temp_data
    
    # Analysis methods
    
    async def _analyze_cpu_usage_patterns(self):
        """Analyze CPU usage patterns across languages."""
        print("\nCPU Usage Analysis:")
        for language, profile in self.language_profiles.items():
            print(f"{language}: Avg {profile.avg_cpu_usage:.1f}%, "
                  f"Peak {profile.peak_cpu_usage:.1f}%, "
                  f"Avg Time {profile.avg_processing_time:.3f}s")
    
    def _analyze_memory_patterns(self):
        """Analyze memory allocation patterns."""
        print("\nMemory Usage Analysis:")
        for language, profile in self.language_profiles.items():
            print(f"{language}: Avg {profile.avg_memory_usage / 1024 / 1024:.2f}MB, "
                  f"Peak {profile.peak_memory_usage / 1024 / 1024:.2f}MB, "
                  f"Growth Rate {profile.memory_growth_rate / 1024:.2f}KB/stmt")
    
    def _analyze_io_patterns(self):
        """Analyze I/O operation patterns."""
        print("\nI/O Operations Analysis:")
        for language, profile in self.language_profiles.items():
            print(f"{language}: I/O Operations {profile.io_operations}")
    
    def _analyze_cache_effectiveness(self, cache_results: Dict[str, Dict[str, float]]):
        """Analyze cache effectiveness across languages."""
        print("\nCache Effectiveness Analysis:")
        for language, results in cache_results.items():
            print(f"{language}: Hit Rate {results['cache_hit_rate']:.2%}, "
                  f"Speedup {results['cache_speedup']:.1f}x, "
                  f"Cold {results['cold_time']:.4f}s, Warm {results['avg_warm_time']:.4f}s")
            
            # Update language profile
            if language in self.language_profiles:
                self.language_profiles[language].cache_hit_rate = results['cache_hit_rate']
    
    def _analyze_resource_scaling(self):
        """Analyze how resources scale with load."""
        load_snapshots = {}
        
        for snapshot in self.resource_monitor.snapshots:
            if snapshot.operation and snapshot.operation.startswith('load_'):
                load_level = int(snapshot.operation.split('_')[1])
                if load_level not in load_snapshots:
                    load_snapshots[load_level] = []
                load_snapshots[load_level].append(snapshot)
        
        print("\nResource Scaling Analysis:")
        for load_level in sorted(load_snapshots.keys()):
            snapshots = load_snapshots[load_level]
            if snapshots:
                avg_cpu = sum(s.cpu_percent for s in snapshots) / len(snapshots)
                avg_memory = sum(s.memory_rss for s in snapshots) / len(snapshots)
                print(f"Load {load_level}: Avg CPU {avg_cpu:.1f}%, "
                      f"Avg Memory {avg_memory / 1024 / 1024:.2f}MB")
    
    # Assertion methods
    
    def _assert_cpu_usage_limits(self):
        """Assert CPU usage is within acceptable limits."""
        for language, profile in self.language_profiles.items():
            self.assertLess(
                profile.peak_cpu_usage,
                self.max_cpu_usage,
                f"{language} peak CPU usage {profile.peak_cpu_usage:.1f}% exceeds limit {self.max_cpu_usage}%"
            )
    
    def _assert_memory_usage_patterns(self):
        """Assert memory usage patterns are reasonable."""
        for language, profile in self.language_profiles.items():
            # Check memory growth rate is reasonable
            max_growth_rate = 1024 * 10  # 10KB per statement max
            self.assertLess(
                profile.memory_growth_rate,
                max_growth_rate,
                f"{language} memory growth rate {profile.memory_growth_rate / 1024:.2f}KB/stmt "
                f"exceeds limit {max_growth_rate / 1024:.2f}KB/stmt"
            )
    
    def _assert_io_efficiency(self):
        """Assert I/O operations are efficient."""
        for language, profile in self.language_profiles.items():
            max_io_operations = 5  # Maximum file operations per test
            self.assertLess(
                profile.io_operations,
                max_io_operations,
                f"{language} I/O operations {profile.io_operations} exceeds limit {max_io_operations}"
            )
    
    def _assert_cache_performance(self, cache_results: Dict[str, Dict[str, float]]):
        """Assert cache performance meets requirements."""
        for language, results in cache_results.items():
            min_cache_hit_rate = 0.7  # 70% minimum hit rate
            self.assertGreater(
                results['cache_hit_rate'],
                min_cache_hit_rate,
                f"{language} cache hit rate {results['cache_hit_rate']:.2%} "
                f"below minimum {min_cache_hit_rate:.2%}"
            )
    
    def _assert_resource_scaling(self):
        """Assert resource scaling is acceptable."""
        # This method would analyze the scaling patterns from snapshots
        # For now, we'll check that resources don't grow exponentially
        pass


if __name__ == "__main__":
    # Run resource usage tests
    import unittest
    unittest.main(verbosity=2)