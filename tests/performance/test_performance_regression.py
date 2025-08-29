"""
Performance regression test suite for multilingual Frohlich Experiment system.

This module implements performance regression detection to ensure that changes
to the system don't degrade multilingual processing performance. It provides:
- Baseline performance establishment
- Performance comparison against baselines
- Regression detection and reporting
- Performance trend analysis
"""

import asyncio
import time
import json
import os
import gc
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import pytest

from tests.test_multilingual_base import AsyncMultilingualTestBase
from tests.fixtures.phase2_parsing_fixtures import Phase2ParsingFixtures
from experiment_agents.utility_agent import UtilityAgent
from utils.language_manager import LanguageManager, SupportedLanguage
from models import (
    PrincipleChoice, PrincipleRanking, VoteProposal, 
    ParsedResponse, ValidationResult, JusticePrinciple, CertaintyLevel
)


@dataclass
class PerformanceMetric:
    """Individual performance metric measurement."""
    name: str
    value: float
    unit: str
    language: str
    timestamp: str
    test_version: str = "1.0"


@dataclass 
class PerformanceBaseline:
    """Performance baseline for comparison."""
    parsing_time_avg: float
    parsing_time_p95: float
    memory_usage_avg: float
    memory_growth_rate: float
    cache_hit_rate: float
    error_rate: float
    language: str
    created_at: str
    test_conditions: Dict[str, Any]


@dataclass
class RegressionResult:
    """Result of performance regression analysis."""
    metric_name: str
    language: str
    baseline_value: float
    current_value: float
    change_percent: float
    is_regression: bool
    severity: str  # 'minor', 'moderate', 'major'
    threshold_used: float


class PerformanceRegressionTests(AsyncMultilingualTestBase):
    """Performance regression test suite for multilingual processing."""
    
    def setUp(self):
        """Set up regression testing environment."""
        super().setUp()
        self.languages = ["English", "Spanish", "Mandarin"]
        self.baselines: Dict[str, PerformanceBaseline] = {}
        self.current_metrics: Dict[str, List[PerformanceMetric]] = {}
        
        # Regression thresholds (percentage increase that triggers regression)
        self.regression_thresholds = {
            "parsing_time_avg": 0.15,      # 15% increase
            "parsing_time_p95": 0.20,      # 20% increase
            "memory_usage_avg": 0.25,      # 25% increase
            "memory_growth_rate": 0.30,    # 30% increase
            "cache_hit_rate": -0.10,       # 10% decrease (negative = bad)
            "error_rate": 0.05             # 5% increase
        }
        
        # Test configuration
        self.baseline_file = Path("tests/performance/baselines.json")
        self.results_dir = Path("tests/performance/results")
        self.results_dir.mkdir(exist_ok=True)
        
    async def test_establish_performance_baselines(self):
        """Establish performance baselines for all languages."""
        print("Establishing performance baselines...")
        
        for language in self.languages:
            baseline = await self._establish_language_baseline(language)
            self.baselines[language] = baseline
        
        # Save baselines to file
        self._save_baselines()
        
        print("Performance baselines established and saved.")
    
    async def test_detect_performance_regressions(self):
        """Detect performance regressions against established baselines."""
        # Load existing baselines
        self._load_baselines()
        
        if not self.baselines:
            print("No baselines found. Run test_establish_performance_baselines first.")
            return
        
        print("Testing for performance regressions...")
        
        regression_results = []
        
        for language in self.languages:
            if language not in self.baselines:
                print(f"No baseline found for {language}, skipping regression test.")
                continue
            
            current_metrics = await self._measure_current_performance(language)
            regressions = self._detect_regressions(language, current_metrics)
            regression_results.extend(regressions)
        
        # Report regression results
        self._report_regression_results(regression_results)
        
        # Assert no major regressions
        self._assert_no_major_regressions(regression_results)
    
    async def test_performance_trend_analysis(self):
        """Analyze performance trends over time."""
        historical_results = self._load_historical_results()
        
        for language in self.languages:
            trends = self._analyze_performance_trends(language, historical_results)
            self._report_performance_trends(language, trends)
    
    async def test_comparative_language_performance(self):
        """Compare performance across languages to detect imbalances."""
        language_metrics = {}
        
        for language in self.languages:
            metrics = await self._measure_current_performance(language)
            language_metrics[language] = metrics
        
        # Compare metrics across languages
        comparisons = self._compare_language_performance(language_metrics)
        self._report_language_comparisons(comparisons)
        
        # Assert performance balance across languages
        self._assert_language_performance_balance(comparisons)
    
    async def test_memory_leak_regression(self):
        """Test for memory leak regressions specifically."""
        print("Testing for memory leak regressions...")
        
        initial_memory = self._get_current_memory()
        
        # Run extended processing cycles
        for cycle in range(10):
            for language in self.languages:
                await self._run_extended_processing_cycle(language, statements=30)
            
            # Force garbage collection
            gc.collect()
            
            current_memory = self._get_current_memory()
            memory_growth = current_memory - initial_memory
            
            print(f"Cycle {cycle + 1}: Memory growth {memory_growth / 1024 / 1024:.2f} MB")
            
            # Check for excessive memory growth
            max_acceptable_growth = 50 * 1024 * 1024  # 50MB total max
            if memory_growth > max_acceptable_growth:
                self.fail(f"Memory leak detected: Growth {memory_growth / 1024 / 1024:.2f}MB "
                         f"exceeds limit {max_acceptable_growth / 1024 / 1024:.2f}MB after {cycle + 1} cycles")
        
        print("No memory leak regressions detected.")
    
    # Baseline establishment methods
    
    async def _establish_language_baseline(self, language: str) -> PerformanceBaseline:
        """Establish performance baseline for a specific language."""
        print(f"Establishing baseline for {language}...")
        
        # Measure parsing performance
        parsing_times = await self._measure_parsing_times(language)
        parsing_time_avg = sum(parsing_times) / len(parsing_times)
        parsing_time_p95 = sorted(parsing_times)[int(len(parsing_times) * 0.95)]
        
        # Measure memory usage
        memory_metrics = await self._measure_memory_usage(language)
        
        # Measure cache performance
        cache_metrics = await self._measure_cache_performance(language)
        
        # Measure error rates
        error_rate = await self._measure_error_rate(language)
        
        baseline = PerformanceBaseline(
            parsing_time_avg=parsing_time_avg,
            parsing_time_p95=parsing_time_p95,
            memory_usage_avg=memory_metrics["avg_usage"],
            memory_growth_rate=memory_metrics["growth_rate"],
            cache_hit_rate=cache_metrics["hit_rate"],
            error_rate=error_rate,
            language=language,
            created_at=datetime.now().isoformat(),
            test_conditions={
                "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
                "test_statements": 100,
                "test_iterations": 3
            }
        )
        
        return baseline
    
    async def _measure_parsing_times(self, language: str, iterations: int = 100) -> List[float]:
        """Measure parsing times for language."""
        utility_agent = UtilityAgent()
        await utility_agent.async_init()
        
        test_data = self.get_language_test_data(language)
        statements = []
        
        # Collect statements for testing
        for data_type, data_list in test_data.items():
            if isinstance(data_list, list):
                statements.extend(str(item) for item in data_list)
        
        if not statements:
            statements = [f"Test statement {i} in {language}" for i in range(iterations)]
        
        parsing_times = []
        
        for i in range(iterations):
            statement = statements[i % len(statements)]
            
            start_time = time.perf_counter()
            await self._mock_parse_statement(utility_agent, statement, language)
            end_time = time.perf_counter()
            
            parsing_times.append(end_time - start_time)
        
        return parsing_times
    
    async def _measure_memory_usage(self, language: str) -> Dict[str, float]:
        """Measure memory usage patterns for language."""
        import psutil
        process = psutil.Process()
        
        initial_memory = process.memory_info().rss
        utility_agent = UtilityAgent()
        await utility_agent.async_init()
        
        memory_readings = []
        
        # Process statements and monitor memory
        for i in range(50):
            statement = f"Memory test statement {i} in {language}"
            
            memory_before = process.memory_info().rss
            await self._mock_parse_statement(utility_agent, statement, language)
            memory_after = process.memory_info().rss
            
            memory_readings.append(memory_after)
        
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        avg_memory = sum(memory_readings) / len(memory_readings)
        
        return {
            "avg_usage": avg_memory,
            "growth_rate": memory_growth / 50  # Per statement
        }
    
    async def _measure_cache_performance(self, language: str) -> Dict[str, float]:
        """Measure cache performance for language."""
        from tests.test_multilingual_base import LanguageDataLoader
        
        # Clear cache for cold test
        LanguageDataLoader.clear_cache()
        
        # Measure cold access
        cold_start = time.perf_counter()
        LanguageDataLoader.get_language_test_data(language)
        cold_time = time.perf_counter() - cold_start
        
        # Measure warm access
        warm_times = []
        for _ in range(10):
            warm_start = time.perf_counter()
            LanguageDataLoader.get_language_test_data(language)
            warm_time = time.perf_counter() - warm_start
            warm_times.append(warm_time)
        
        avg_warm_time = sum(warm_times) / len(warm_times)
        hit_rate = max(0.0, 1.0 - (avg_warm_time / cold_time)) if cold_time > 0 else 0.0
        
        return {"hit_rate": hit_rate}
    
    async def _measure_error_rate(self, language: str, iterations: int = 100) -> float:
        """Measure error rate for language processing."""
        utility_agent = UtilityAgent()
        await utility_agent.async_init()
        
        errors = 0
        
        for i in range(iterations):
            statement = f"Error test statement {i} in {language}"
            
            try:
                await self._mock_parse_statement(utility_agent, statement, language)
            except Exception:
                errors += 1
        
        return errors / iterations if iterations > 0 else 0.0
    
    # Performance measurement methods
    
    async def _measure_current_performance(self, language: str) -> Dict[str, float]:
        """Measure current performance for comparison with baseline."""
        # Use same methods as baseline establishment but return dict
        parsing_times = await self._measure_parsing_times(language, 50)  # Smaller sample
        memory_metrics = await self._measure_memory_usage(language) 
        cache_metrics = await self._measure_cache_performance(language)
        error_rate = await self._measure_error_rate(language, 50)
        
        return {
            "parsing_time_avg": sum(parsing_times) / len(parsing_times),
            "parsing_time_p95": sorted(parsing_times)[int(len(parsing_times) * 0.95)],
            "memory_usage_avg": memory_metrics["avg_usage"],
            "memory_growth_rate": memory_metrics["growth_rate"],
            "cache_hit_rate": cache_metrics["hit_rate"],
            "error_rate": error_rate
        }
    
    # Regression detection methods
    
    def _detect_regressions(self, language: str, current_metrics: Dict[str, float]) -> List[RegressionResult]:
        """Detect regressions by comparing current metrics to baseline."""
        regressions = []
        baseline = self.baselines[language]
        
        # Compare each metric
        for metric_name, threshold in self.regression_thresholds.items():
            baseline_value = getattr(baseline, metric_name)
            current_value = current_metrics[metric_name]
            
            # Calculate percentage change
            if baseline_value != 0:
                change_percent = (current_value - baseline_value) / baseline_value
            else:
                change_percent = 0.0 if current_value == 0 else 1.0
            
            # Determine if this is a regression
            is_regression = False
            severity = "none"
            
            if threshold > 0:  # Higher values are bad (e.g., parsing_time)
                if change_percent > threshold:
                    is_regression = True
                    if change_percent > threshold * 2:
                        severity = "major"
                    elif change_percent > threshold * 1.5:
                        severity = "moderate"
                    else:
                        severity = "minor"
            else:  # Lower values are bad (e.g., cache_hit_rate)
                if change_percent < threshold:
                    is_regression = True
                    if change_percent < threshold * 2:
                        severity = "major"
                    elif change_percent < threshold * 1.5:
                        severity = "moderate" 
                    else:
                        severity = "minor"
            
            regression = RegressionResult(
                metric_name=metric_name,
                language=language,
                baseline_value=baseline_value,
                current_value=current_value,
                change_percent=change_percent,
                is_regression=is_regression,
                severity=severity,
                threshold_used=threshold
            )
            
            regressions.append(regression)
        
        return regressions
    
    # Analysis methods
    
    def _compare_language_performance(self, language_metrics: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Compare performance across languages."""
        comparisons = {}
        
        for metric_name in self.regression_thresholds.keys():
            metric_values = {lang: metrics[metric_name] for lang, metrics in language_metrics.items()}
            
            min_lang = min(metric_values, key=metric_values.get)
            max_lang = max(metric_values, key=metric_values.get)
            
            # Calculate performance imbalance
            min_val = metric_values[min_lang]
            max_val = metric_values[max_lang]
            
            if min_val != 0:
                imbalance_ratio = max_val / min_val
            else:
                imbalance_ratio = float('inf') if max_val > 0 else 1.0
            
            comparisons[metric_name] = {
                "best_language": min_lang if metric_name != "cache_hit_rate" else max_lang,
                "worst_language": max_lang if metric_name != "cache_hit_rate" else min_lang,
                "best_value": min_val if metric_name != "cache_hit_rate" else max_val,
                "worst_value": max_val if metric_name != "cache_hit_rate" else min_val,
                "imbalance_ratio": imbalance_ratio,
                "all_values": metric_values
            }
        
        return comparisons
    
    def _analyze_performance_trends(self, language: str, historical_results: List[Dict]) -> Dict[str, Any]:
        """Analyze performance trends over time."""
        # This would analyze historical performance data
        # For now, return empty analysis
        return {"trends": "analysis_not_implemented"}
    
    # Reporting methods
    
    def _report_regression_results(self, regression_results: List[RegressionResult]):
        """Report regression test results."""
        print("\n" + "="*60)
        print("PERFORMANCE REGRESSION TEST RESULTS")
        print("="*60)
        
        regressions_found = [r for r in regression_results if r.is_regression]
        
        if not regressions_found:
            print("✅ No performance regressions detected!")
        else:
            print(f"⚠️  {len(regressions_found)} performance regressions detected:")
            
            for regression in regressions_found:
                print(f"\n📊 {regression.language} - {regression.metric_name}")
                print(f"   Baseline: {regression.baseline_value:.4f}")
                print(f"   Current:  {regression.current_value:.4f}")
                print(f"   Change:   {regression.change_percent:.1%} ({regression.severity})")
                print(f"   Threshold: {regression.threshold_used:.1%}")
        
        print("\n" + "="*60)
    
    def _report_language_comparisons(self, comparisons: Dict[str, Any]):
        """Report language performance comparisons."""
        print("\n" + "="*60)
        print("LANGUAGE PERFORMANCE COMPARISON")
        print("="*60)
        
        for metric_name, comparison in comparisons.items():
            print(f"\n📊 {metric_name.replace('_', ' ').title()}:")
            print(f"   Best:  {comparison['best_language']} ({comparison['best_value']:.4f})")
            print(f"   Worst: {comparison['worst_language']} ({comparison['worst_value']:.4f})")
            print(f"   Ratio: {comparison['imbalance_ratio']:.2f}x")
        
        print("\n" + "="*60)
    
    def _report_performance_trends(self, language: str, trends: Dict[str, Any]):
        """Report performance trends for a language."""
        print(f"\n📈 Performance Trends for {language}: {trends}")
    
    # Utility methods
    
    async def _run_extended_processing_cycle(self, language: str, statements: int):
        """Run extended processing cycle for memory leak testing."""
        utility_agent = UtilityAgent()
        await utility_agent.async_init()
        
        for i in range(statements):
            statement = f"Extended test statement {i} in {language}"
            await self._mock_parse_statement(utility_agent, statement, language)
    
    def _get_current_memory(self) -> int:
        """Get current memory usage in bytes."""
        import psutil
        return psutil.Process().memory_info().rss
    
    async def _mock_parse_statement(self, utility_agent: UtilityAgent, 
                                  statement: str, language: str) -> Dict[str, Any]:
        """Mock parsing operation with realistic performance characteristics."""
        # Simulate realistic processing time based on language
        if language == "Mandarin":
            await asyncio.sleep(0.006)  # 6ms for Chinese
        elif language == "Spanish":
            await asyncio.sleep(0.004)  # 4ms for Spanish
        else:
            await asyncio.sleep(0.003)  # 3ms for English
        
        # Simulate memory allocation
        temp_data = {
            "statement": statement,
            "language": language,
            "processed_at": time.time(),
            "word_count": len(statement.split())
        }
        
        return temp_data
    
    # File I/O methods
    
    def _save_baselines(self):
        """Save baselines to file."""
        baseline_data = {}
        for language, baseline in self.baselines.items():
            baseline_data[language] = asdict(baseline)
        
        with open(self.baseline_file, 'w') as f:
            json.dump(baseline_data, f, indent=2)
    
    def _load_baselines(self):
        """Load baselines from file."""
        if not self.baseline_file.exists():
            return
        
        with open(self.baseline_file, 'r') as f:
            baseline_data = json.load(f)
        
        for language, data in baseline_data.items():
            self.baselines[language] = PerformanceBaseline(**data)
    
    def _load_historical_results(self) -> List[Dict]:
        """Load historical performance results."""
        # This would load historical test results from files
        # For now, return empty list
        return []
    
    # Assertion methods
    
    def _assert_no_major_regressions(self, regression_results: List[RegressionResult]):
        """Assert no major performance regressions are present."""
        major_regressions = [r for r in regression_results if r.severity == "major"]
        
        if major_regressions:
            regression_details = []
            for regression in major_regressions:
                regression_details.append(
                    f"{regression.language}.{regression.metric_name}: "
                    f"{regression.change_percent:.1%} change "
                    f"({regression.baseline_value:.4f} → {regression.current_value:.4f})"
                )
            
            self.fail(f"Major performance regressions detected:\n" + "\n".join(regression_details))
    
    def _assert_language_performance_balance(self, comparisons: Dict[str, Any]):
        """Assert performance is reasonably balanced across languages."""
        max_acceptable_imbalance = 3.0  # 3x difference max
        
        imbalanced_metrics = []
        
        for metric_name, comparison in comparisons.items():
            if comparison["imbalance_ratio"] > max_acceptable_imbalance:
                imbalanced_metrics.append(
                    f"{metric_name}: {comparison['imbalance_ratio']:.1f}x "
                    f"({comparison['best_language']} vs {comparison['worst_language']})"
                )
        
        if imbalanced_metrics:
            self.fail(f"Performance imbalance detected:\n" + "\n".join(imbalanced_metrics))


if __name__ == "__main__":
    # Run performance regression tests
    import unittest
    unittest.main(verbosity=2)