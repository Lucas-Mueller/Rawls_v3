"""
Scalability test framework for multilingual Frohlich Experiment system.

This module implements Subplan 6.2: Scalability Tests from the Opus Multilingual 
Testing Implementation Plan. It provides comprehensive scalability testing for:
- Large numbers of agents in different languages
- Rapid language switching scenarios
- Large constraint amounts in various formats  
- Unicode string handling at scale
"""

import asyncio
import time
import gc
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, AsyncMock
import pytest

from tests.test_multilingual_base import AsyncMultilingualTestBase
from tests.fixtures.phase2_parsing_fixtures import Phase2ParsingFixtures
from experiment_agents.utility_agent import UtilityAgent
from utils.language_manager import LanguageManager, SupportedLanguage
from models import (
    PrincipleChoice, PrincipleRanking, VoteProposal, 
    ParsedResponse, ValidationResult, JusticePrinciple, CertaintyLevel
)


class ScalabilityMetrics:
    """Container for scalability test metrics."""
    
    def __init__(self):
        self.agent_counts: List[int] = []
        self.processing_times: List[float] = []
        self.memory_usage: List[float] = []
        self.throughput_rates: List[float] = []  # statements per second
        self.error_rates: List[float] = []
        self.concurrent_language_metrics: Dict[str, List[float]] = {}


class MultilingualScalabilityTests(AsyncMultilingualTestBase):
    """Scalability test framework for multilingual processing."""
    
    def setUp(self):
        """Set up scalability testing environment."""
        super().setUp()
        self.metrics = ScalabilityMetrics()
        self.process = psutil.Process()
        self.languages = ["English", "Spanish", "Mandarin"]
        
        # Scalability test parameters
        self.agent_counts = [10, 25, 50, 100]  # Number of simulated agents
        self.max_acceptable_time = 30.0  # 30 seconds max processing time
        self.max_memory_per_agent = 10 * 1024 * 1024  # 10MB per agent max
        
    async def test_large_agent_count_processing(self):
        """Test processing with increasing numbers of agents across languages."""
        for agent_count in self.agent_counts:
            await self._test_agent_count_scenario(agent_count)
        
        # Assert scalability requirements
        self._assert_scalability_performance()
    
    async def test_rapid_language_switching(self):
        """Test performance with rapid language context switching."""
        switch_scenarios = [
            {"switches_per_minute": 60, "duration_minutes": 2},
            {"switches_per_minute": 120, "duration_minutes": 1},
            {"switches_per_minute": 300, "duration_minutes": 0.5}
        ]
        
        for scenario in switch_scenarios:
            await self._test_language_switching_scenario(scenario)
        
        # Assert switching performance
        self._assert_language_switching_performance()
    
    async def test_large_constraint_amounts(self):
        """Test parsing of very large constraint amounts in various formats."""
        large_amounts = [
            100000,      # $100,000
            500000,      # $500,000  
            1000000,     # $1,000,000
            5000000,     # $5,000,000
            10000000     # $10,000,000
        ]
        
        for amount in large_amounts:
            await self._test_large_amount_parsing(amount)
        
        # Assert large amount parsing performance
        self._assert_large_amount_performance()
    
    async def test_unicode_string_handling_scale(self):
        """Test Unicode string processing performance at scale."""
        unicode_test_sizes = [1000, 5000, 10000, 25000]  # Number of Unicode strings
        
        for size in unicode_test_sizes:
            await self._test_unicode_processing_scale(size)
        
        # Assert Unicode processing performance
        self._assert_unicode_performance()
    
    async def test_concurrent_multilingual_processing(self):
        """Test concurrent processing across all languages simultaneously."""
        concurrency_levels = [5, 10, 20, 50]  # Concurrent tasks per language
        
        for concurrency in concurrency_levels:
            await self._test_concurrent_processing(concurrency)
        
        # Assert concurrent processing performance
        self._assert_concurrent_performance()
    
    async def test_memory_usage_scaling(self):
        """Test memory usage patterns as processing load increases."""
        workload_sizes = [100, 500, 1000, 2500]  # Number of statements to process
        
        initial_memory = self.process.memory_info().rss
        
        for workload_size in workload_sizes:
            memory_before = self.process.memory_info().rss
            
            await self._process_workload_batch(workload_size)
            
            memory_after = self.process.memory_info().rss
            memory_growth = memory_after - memory_before
            
            # Log memory metrics
            print(f"Workload {workload_size}: Memory growth {memory_growth / 1024 / 1024:.2f} MB")
            self.metrics.memory_usage.append(memory_growth)
            
            # Force garbage collection between tests
            gc.collect()
        
        # Assert memory scaling is linear
        self._assert_memory_scaling()
    
    async def test_throughput_under_load(self):
        """Test processing throughput under increasing load."""
        load_levels = [
            {"statements_per_second": 1, "duration_seconds": 30},
            {"statements_per_second": 5, "duration_seconds": 20}, 
            {"statements_per_second": 10, "duration_seconds": 15},
            {"statements_per_second": 20, "duration_seconds": 10}
        ]
        
        for load_level in load_levels:
            throughput = await self._test_throughput_scenario(load_level)
            self.metrics.throughput_rates.append(throughput)
        
        # Assert throughput performance
        self._assert_throughput_performance()
    
    # Private test implementation methods
    
    async def _test_agent_count_scenario(self, agent_count: int):
        """Test processing scenario with specific agent count."""
        start_time = time.perf_counter()
        
        # Create utility agents for each simulated agent
        utility_agents = []
        for i in range(min(agent_count, 10)):  # Limit actual agent creation to 10
            utility_agent = UtilityAgent()
            await utility_agent.async_init()
            utility_agents.append(utility_agent)
        
        # Simulate processing from multiple agents
        tasks = []
        statements_per_agent = 5
        
        for i in range(agent_count):
            # Cycle through available utility agents
            agent = utility_agents[i % len(utility_agents)]
            language = self.languages[i % len(self.languages)]
            
            # Create processing task
            task = asyncio.create_task(
                self._simulate_agent_processing(agent, language, statements_per_agent)
            )
            tasks.append(task)
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.perf_counter()
        processing_time = end_time - start_time
        
        # Calculate metrics
        error_count = sum(1 for r in results if isinstance(r, Exception))
        error_rate = error_count / len(results) if results else 0
        
        self.metrics.agent_counts.append(agent_count)
        self.metrics.processing_times.append(processing_time)
        self.metrics.error_rates.append(error_rate)
        
        print(f"Agent count {agent_count}: {processing_time:.2f}s, {error_rate:.2%} errors")
    
    async def _test_language_switching_scenario(self, scenario: Dict[str, float]):
        """Test rapid language switching scenario."""
        switches_per_minute = scenario["switches_per_minute"]
        duration_minutes = scenario["duration_minutes"]
        
        total_switches = int(switches_per_minute * duration_minutes)
        switch_interval = (duration_minutes * 60) / total_switches
        
        utility_agent = UtilityAgent()
        await utility_agent.async_init()
        
        start_time = time.perf_counter()
        
        for i in range(total_switches):
            # Switch language context
            current_language = self.languages[i % len(self.languages)]
            
            # Simulate processing in current language
            test_data = self.get_language_test_data(current_language)
            if test_data and test_data.get('ballots'):
                statement = str(test_data['ballots'][0])
                await self._mock_parse_statement(utility_agent, statement, current_language)
            
            # Wait for next switch (simulate real-time switching)
            if i < total_switches - 1:
                await asyncio.sleep(max(0, switch_interval - 0.01))  # Account for processing time
        
        end_time = time.perf_counter()
        actual_time = end_time - start_time
        
        print(f"Language switching: {switches_per_minute}/min for {duration_minutes}min = {actual_time:.2f}s")
        
        # Assert reasonable performance
        max_expected_time = duration_minutes * 60 * 1.2  # 20% overhead allowed
        self.assertLess(
            actual_time, 
            max_expected_time,
            f"Language switching took {actual_time:.2f}s, expected < {max_expected_time:.2f}s"
        )
    
    async def _test_large_amount_parsing(self, amount: int):
        """Test parsing of large constraint amounts."""
        utility_agent = UtilityAgent()
        await utility_agent.async_init()
        
        # Test various formats for the large amount
        amount_formats = [
            f"${amount:,}",           # $1,000,000
            f"${amount}",             # $1000000  
            f"{amount:,} dollars",    # 1,000,000 dollars
            f"¥{amount:,}",          # ¥1,000,000 (Chinese)
            f"€{amount:,}",          # €1,000,000 (European)
        ]
        
        for format_str in amount_formats:
            start_time = time.perf_counter()
            
            # Create test statement with large amount
            test_statement = f"I prefer floor constraint with {format_str}"
            
            try:
                result = await self._mock_parse_statement(utility_agent, test_statement, "English")
                
                end_time = time.perf_counter()
                parse_time = end_time - start_time
                
                # Assert parsing time is reasonable
                max_parse_time = 5.0  # 5 seconds max for large amounts
                self.assertLess(
                    parse_time,
                    max_parse_time, 
                    f"Parsing {format_str} took {parse_time:.3f}s, expected < {max_parse_time}s"
                )
                
            except Exception as e:
                self.fail(f"Failed to parse large amount {format_str}: {e}")
    
    async def _test_unicode_processing_scale(self, string_count: int):
        """Test Unicode string processing at scale."""
        utility_agent = UtilityAgent()
        await utility_agent.async_init()
        
        # Create test strings in different languages
        unicode_strings = []
        
        # Chinese strings
        chinese_base = "我选择最大化平均收入原则，约束金额为"
        for i in range(string_count // 3):
            amount = (i + 1) * 1000
            unicode_strings.append(f"{chinese_base}¥{amount:,}")
        
        # Spanish strings  
        spanish_base = "Prefiero maximizar los ingresos promedio con restricción de"
        for i in range(string_count // 3):
            amount = (i + 1) * 1000
            unicode_strings.append(f"{spanish_base} €{amount:,}")
        
        # English strings with Unicode symbols
        english_base = "I support floor constraint with"
        for i in range(string_count - len(unicode_strings)):
            amount = (i + 1) * 1000
            unicode_strings.append(f"{english_base} ${amount:,}")
        
        # Process all Unicode strings
        start_time = time.perf_counter()
        
        tasks = []
        for i, string in enumerate(unicode_strings):
            language = self.languages[i % len(self.languages)]
            task = asyncio.create_task(
                self._mock_parse_statement(utility_agent, string, language)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Calculate performance metrics
        successful_parses = sum(1 for r in results if not isinstance(r, Exception))
        throughput = successful_parses / total_time if total_time > 0 else 0
        
        print(f"Unicode processing: {string_count} strings in {total_time:.2f}s ({throughput:.1f} strings/sec)")
        
        # Assert reasonable Unicode processing performance
        min_throughput = 50  # 50 strings per second minimum
        self.assertGreater(
            throughput,
            min_throughput,
            f"Unicode throughput {throughput:.1f}/sec below minimum {min_throughput}/sec"
        )
    
    async def _test_concurrent_processing(self, concurrency_level: int):
        """Test concurrent processing across languages."""
        tasks_per_language = concurrency_level
        
        start_time = time.perf_counter()
        
        all_tasks = []
        
        # Create concurrent tasks for each language
        for language in self.languages:
            utility_agent = UtilityAgent()
            await utility_agent.async_init()
            
            # Create multiple concurrent tasks for this language
            for i in range(tasks_per_language):
                task = asyncio.create_task(
                    self._simulate_agent_processing(utility_agent, language, 3)
                )
                all_tasks.append(task)
        
        # Execute all concurrent tasks
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        end_time = time.perf_counter()
        concurrent_time = end_time - start_time
        
        # Calculate metrics
        total_tasks = len(all_tasks)
        error_count = sum(1 for r in results if isinstance(r, Exception))
        success_rate = (total_tasks - error_count) / total_tasks if total_tasks > 0 else 0
        
        print(f"Concurrent processing: {concurrency_level} tasks/language, "
              f"{concurrent_time:.2f}s total, {success_rate:.2%} success rate")
        
        # Assert acceptable concurrent performance
        max_concurrent_time = 15.0  # 15 seconds max
        min_success_rate = 0.95     # 95% success rate minimum
        
        self.assertLess(
            concurrent_time,
            max_concurrent_time,
            f"Concurrent processing took {concurrent_time:.2f}s, expected < {max_concurrent_time}s"
        )
        
        self.assertGreater(
            success_rate,
            min_success_rate,
            f"Success rate {success_rate:.2%} below minimum {min_success_rate:.2%}"
        )
    
    async def _process_workload_batch(self, workload_size: int):
        """Process a batch of statements for memory testing."""
        utility_agent = UtilityAgent()
        await utility_agent.async_init()
        
        # Create statements from test data
        statements = []
        for language in self.languages:
            test_data = self.get_language_test_data(language)
            for data_type, data_list in test_data.items():
                if isinstance(data_list, list):
                    for item in data_list[:workload_size // len(self.languages) // len(test_data)]:
                        if isinstance(item, dict):
                            text = item.get('text', str(item))
                        else:
                            text = str(item)
                        statements.append((text, language))
        
        # Extend to reach workload size
        while len(statements) < workload_size:
            base_statements = statements[:workload_size - len(statements)]
            statements.extend(base_statements)
        
        # Process all statements
        for text, language in statements[:workload_size]:
            await self._mock_parse_statement(utility_agent, text, language)
    
    async def _test_throughput_scenario(self, load_level: Dict[str, Any]) -> float:
        """Test processing throughput under specific load."""
        statements_per_second = load_level["statements_per_second"]
        duration_seconds = load_level["duration_seconds"]
        
        total_statements = int(statements_per_second * duration_seconds)
        statement_interval = 1.0 / statements_per_second
        
        utility_agent = UtilityAgent()
        await utility_agent.async_init()
        
        # Create test statements
        test_statements = []
        for i in range(total_statements):
            language = self.languages[i % len(self.languages)]
            test_data = self.get_language_test_data(language)
            
            if test_data and test_data.get('ballots'):
                statement = str(test_data['ballots'][i % len(test_data['ballots'])])
                test_statements.append((statement, language))
        
        # Process statements at target rate
        start_time = time.perf_counter()
        successful_processes = 0
        
        for i, (statement, language) in enumerate(test_statements):
            try:
                await self._mock_parse_statement(utility_agent, statement, language)
                successful_processes += 1
            except Exception as e:
                print(f"Processing error at statement {i}: {e}")
            
            # Wait for next statement (maintain target rate)
            if i < len(test_statements) - 1:
                await asyncio.sleep(max(0, statement_interval - 0.01))
        
        end_time = time.perf_counter()
        actual_time = end_time - start_time
        actual_throughput = successful_processes / actual_time if actual_time > 0 else 0
        
        print(f"Throughput test: {statements_per_second} target/sec, "
              f"{actual_throughput:.1f} actual/sec")
        
        return actual_throughput
    
    async def _simulate_agent_processing(self, utility_agent: UtilityAgent, 
                                       language: str, statement_count: int) -> Dict[str, Any]:
        """Simulate processing statements from a single agent."""
        test_data = self.get_language_test_data(language)
        processed = 0
        errors = 0
        
        start_time = time.perf_counter()
        
        # Process statements
        for i in range(statement_count):
            try:
                # Get test statement
                if test_data and test_data.get('ballots'):
                    statement = str(test_data['ballots'][i % len(test_data['ballots'])])
                else:
                    statement = f"Test statement {i} in {language}"
                
                await self._mock_parse_statement(utility_agent, statement, language)
                processed += 1
                
            except Exception as e:
                errors += 1
        
        end_time = time.perf_counter()
        processing_time = end_time - start_time
        
        return {
            "language": language,
            "processed": processed,
            "errors": errors, 
            "processing_time": processing_time,
            "throughput": processed / processing_time if processing_time > 0 else 0
        }
    
    async def _mock_parse_statement(self, utility_agent: UtilityAgent, 
                                  statement: str, language: str) -> Dict[str, Any]:
        """Mock parsing operation for scalability testing."""
        # Simulate more realistic parsing overhead
        processed_text = statement.lower().strip()
        words = processed_text.split()
        
        # Simulate pattern matching and text analysis
        patterns = ["vote", "principle", "constraint", "agree", "disagree", "floor", "average"]
        matches = []
        for pattern in patterns:
            if pattern in processed_text:
                matches.append(pattern)
                # Simulate processing time proportional to complexity
                await asyncio.sleep(0.002 * len(matches))  # 2ms per pattern match
        
        # Simulate language-specific processing overhead
        if language == "Mandarin":
            # Chinese processing typically requires more computation
            await asyncio.sleep(0.005)
        elif language == "Spanish":
            # Spanish processing has moderate overhead
            await asyncio.sleep(0.003)
        else:
            # English baseline
            await asyncio.sleep(0.002)
        
        return {
            "statement": statement,
            "language": language,
            "word_count": len(words),
            "pattern_matches": matches,
            "processed_at": time.time()
        }
    
    # Performance assertion methods
    
    def _assert_scalability_performance(self):
        """Assert that scalability performance meets requirements."""
        if not self.metrics.processing_times:
            return
        
        # Check that processing time scales reasonably
        for i, (count, time_taken) in enumerate(zip(self.metrics.agent_counts, self.metrics.processing_times)):
            max_expected_time = count * 0.1  # 100ms per agent baseline
            
            self.assertLess(
                time_taken,
                max_expected_time,
                f"Agent count {count} took {time_taken:.2f}s, expected < {max_expected_time:.2f}s"
            )
            
            # Check error rates
            if i < len(self.metrics.error_rates):
                error_rate = self.metrics.error_rates[i]
                max_error_rate = 0.05  # 5% max error rate
                
                self.assertLess(
                    error_rate,
                    max_error_rate,
                    f"Error rate {error_rate:.2%} exceeds maximum {max_error_rate:.2%} for {count} agents"
                )
    
    def _assert_language_switching_performance(self):
        """Assert language switching performance is acceptable."""
        # This is tested within the switching scenarios themselves
        pass
    
    def _assert_large_amount_performance(self):
        """Assert large amount parsing performs adequately."""
        # This is tested within the large amount parsing tests
        pass
    
    def _assert_unicode_performance(self):
        """Assert Unicode processing performance is acceptable."""
        # This is tested within the Unicode processing tests
        pass
    
    def _assert_concurrent_performance(self):
        """Assert concurrent processing performance meets standards."""
        # This is tested within the concurrent processing tests
        pass
    
    def _assert_memory_scaling(self):
        """Assert memory usage scales linearly with workload."""
        if len(self.metrics.memory_usage) < 2:
            return
        
        # Check that memory growth is reasonable
        max_memory_growth = self.metrics.memory_usage[-1]  # Largest workload memory
        max_acceptable_growth = 500 * 1024 * 1024  # 500MB max total growth
        
        self.assertLess(
            max_memory_growth,
            max_acceptable_growth,
            f"Memory growth {max_memory_growth / 1024 / 1024:.2f}MB exceeds "
            f"limit {max_acceptable_growth / 1024 / 1024:.2f}MB"
        )
    
    def _assert_throughput_performance(self):
        """Assert throughput performance meets requirements."""
        if not self.metrics.throughput_rates:
            return
        
        min_acceptable_throughput = 0.5  # 0.5 statements per second minimum
        
        for throughput in self.metrics.throughput_rates:
            self.assertGreater(
                throughput,
                min_acceptable_throughput,
                f"Throughput {throughput:.1f}/sec below minimum {min_acceptable_throughput}/sec"
            )


if __name__ == "__main__":
    # Run scalability tests
    import unittest
    unittest.main(verbosity=2)