"""
Performance comparison report generator for multilingual Frohlich Experiment system.

This module creates comprehensive performance comparison reports between languages,
including:
- Performance metric comparisons across languages
- Visualizations and charts
- Trend analysis over time  
- Actionable recommendations
- Export to multiple formats
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import asyncio

# Optional dependencies for enhanced reporting
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAS_PLOTTING = True
except ImportError:
    HAS_PLOTTING = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


@dataclass
class LanguagePerformanceData:
    """Performance data for a single language."""
    language: str
    parsing_time_avg: float
    parsing_time_p95: float
    memory_usage_avg: float
    memory_growth_rate: float
    cache_hit_rate: float
    error_rate: float
    throughput_rate: float
    cpu_usage_avg: float
    test_timestamp: str
    
    
@dataclass
class PerformanceComparison:
    """Comparison between two languages."""
    baseline_language: str
    comparison_language: str
    metric_name: str
    baseline_value: float
    comparison_value: float
    difference_absolute: float
    difference_percentage: float
    winner: str  # Which language performs better
    significance: str  # 'negligible', 'minor', 'moderate', 'major'


@dataclass
class PerformanceRecommendation:
    """Performance improvement recommendation."""
    language: str
    category: str
    priority: str  # 'low', 'medium', 'high', 'critical'
    title: str
    description: str
    expected_improvement: str
    implementation_effort: str


class PerformanceReportGenerator:
    """Generates comprehensive performance comparison reports."""
    
    def __init__(self, output_dir: str = "tests/performance/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Performance thresholds for significance classification
        self.significance_thresholds = {
            "negligible": 0.05,    # 5%
            "minor": 0.15,         # 15%
            "moderate": 0.30,      # 30%
            "major": 0.50          # 50%
        }
        
    def generate_comprehensive_report(self, 
                                    language_data: Dict[str, LanguagePerformanceData],
                                    report_name: str = None) -> str:
        """Generate a comprehensive performance comparison report."""
        
        if report_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_name = f"performance_report_{timestamp}"
        
        print(f"Generating comprehensive performance report: {report_name}")
        
        # Generate all report sections
        report_sections = {
            "executive_summary": self._generate_executive_summary(language_data),
            "detailed_comparisons": self._generate_detailed_comparisons(language_data),
            "performance_rankings": self._generate_performance_rankings(language_data),
            "trend_analysis": self._generate_trend_analysis(language_data),
            "recommendations": self._generate_recommendations(language_data),
            "raw_data": self._generate_raw_data_section(language_data)
        }
        
        # Create full report
        full_report = self._create_full_report(report_sections, report_name)
        
        # Save report to file
        report_path = self.output_dir / f"{report_name}.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(full_report)
        
        # Generate additional formats if dependencies available
        if HAS_PANDAS:
            self._generate_csv_report(language_data, report_name)
        
        if HAS_PLOTTING:
            self._generate_visual_report(language_data, report_name)
        
        print(f"Report generated: {report_path}")
        return str(report_path)
    
    def _generate_executive_summary(self, language_data: Dict[str, LanguagePerformanceData]) -> str:
        """Generate executive summary section."""
        languages = list(language_data.keys())
        
        # Find best and worst performing languages for key metrics
        parsing_best = min(language_data.items(), key=lambda x: x[1].parsing_time_avg)
        memory_best = min(language_data.items(), key=lambda x: x[1].memory_usage_avg)
        cache_best = max(language_data.items(), key=lambda x: x[1].cache_hit_rate)
        
        parsing_worst = max(language_data.items(), key=lambda x: x[1].parsing_time_avg)
        memory_worst = max(language_data.items(), key=lambda x: x[1].memory_usage_avg)
        cache_worst = min(language_data.items(), key=lambda x: x[1].cache_hit_rate)
        
        # Calculate overall performance differences
        all_parsing_times = [data.parsing_time_avg for data in language_data.values()]
        parsing_spread = max(all_parsing_times) - min(all_parsing_times)
        parsing_variation = (parsing_spread / min(all_parsing_times)) * 100 if min(all_parsing_times) > 0 else 0
        
        summary = f"""# Executive Summary

## Key Findings

**Overall Performance**: The multilingual system shows {'significant' if parsing_variation > 30 else 'moderate' if parsing_variation > 15 else 'minimal'} variation in performance across languages ({parsing_variation:.1f}% parsing time variation).

**Best Performing Language**: **{parsing_best[0]}** demonstrates the best overall parsing performance at {parsing_best[1].parsing_time_avg:.3f}s average.

**Performance Leaders by Category**:
- **Parsing Speed**: {parsing_best[0]} ({parsing_best[1].parsing_time_avg:.3f}s avg)
- **Memory Efficiency**: {memory_best[0]} ({memory_best[1].memory_usage_avg / 1024 / 1024:.1f}MB avg)
- **Cache Effectiveness**: {cache_best[0]} ({cache_best[1].cache_hit_rate:.1%} hit rate)

**Areas for Improvement**:
- {parsing_worst[0]} shows {((parsing_worst[1].parsing_time_avg - parsing_best[1].parsing_time_avg) / parsing_best[1].parsing_time_avg * 100):.1f}% slower parsing than best performer
- {memory_worst[0]} uses {((memory_worst[1].memory_usage_avg - memory_best[1].memory_usage_avg) / 1024 / 1024):.1f}MB more memory on average
- {cache_worst[0]} has {((cache_best[1].cache_hit_rate - cache_worst[1].cache_hit_rate) * 100):.1f}% lower cache hit rate

## Recommendations Priority
1. **High**: Optimize {parsing_worst[0]} parsing algorithms
2. **Medium**: Improve {cache_worst[0]} caching mechanisms  
3. **Low**: Monitor {memory_worst[0]} memory usage patterns

"""
        return summary
    
    def _generate_detailed_comparisons(self, language_data: Dict[str, LanguagePerformanceData]) -> str:
        """Generate detailed performance comparisons."""
        languages = list(language_data.keys())
        comparisons = []
        
        # Generate all pairwise comparisons
        for i, lang1 in enumerate(languages):
            for lang2 in languages[i+1:]:
                lang_comparisons = self._compare_languages(
                    language_data[lang1], language_data[lang2]
                )
                comparisons.extend(lang_comparisons)
        
        # Organize comparisons by metric
        metrics = {}
        for comp in comparisons:
            if comp.metric_name not in metrics:
                metrics[comp.metric_name] = []
            metrics[comp.metric_name].append(comp)
        
        detailed_section = "# Detailed Performance Comparisons\n\n"
        
        for metric_name, metric_comparisons in metrics.items():
            detailed_section += f"## {metric_name.replace('_', ' ').title()}\n\n"
            
            for comp in metric_comparisons:
                significance_icon = {
                    'negligible': '✅',
                    'minor': '⚠️',
                    'moderate': '🔶', 
                    'major': '🔴'
                }.get(comp.significance, '❓')
                
                detailed_section += f"### {comp.baseline_language} vs {comp.comparison_language} {significance_icon}\n\n"
                detailed_section += f"- **{comp.baseline_language}**: {comp.baseline_value:.4f}\n"
                detailed_section += f"- **{comp.comparison_language}**: {comp.comparison_value:.4f}\n"
                detailed_section += f"- **Difference**: {comp.difference_absolute:.4f} ({comp.difference_percentage:+.1f}%)\n"
                detailed_section += f"- **Winner**: **{comp.winner}**\n"
                detailed_section += f"- **Significance**: {comp.significance.title()}\n\n"
        
        return detailed_section
    
    def _generate_performance_rankings(self, language_data: Dict[str, LanguagePerformanceData]) -> str:
        """Generate performance rankings for each metric."""
        languages = list(language_data.keys())
        
        rankings = {
            "parsing_time_avg": sorted(languages, key=lambda l: language_data[l].parsing_time_avg),
            "memory_usage_avg": sorted(languages, key=lambda l: language_data[l].memory_usage_avg),
            "cache_hit_rate": sorted(languages, key=lambda l: language_data[l].cache_hit_rate, reverse=True),
            "error_rate": sorted(languages, key=lambda l: language_data[l].error_rate),
            "throughput_rate": sorted(languages, key=lambda l: language_data[l].throughput_rate, reverse=True),
            "cpu_usage_avg": sorted(languages, key=lambda l: language_data[l].cpu_usage_avg)
        }
        
        rankings_section = "# Performance Rankings\n\n"
        
        for metric_name, ranked_languages in rankings.items():
            rankings_section += f"## {metric_name.replace('_', ' ').title()}\n\n"
            
            for rank, language in enumerate(ranked_languages, 1):
                value = getattr(language_data[language], metric_name)
                
                if metric_name in ["parsing_time_avg", "memory_usage_avg"]:
                    formatted_value = f"{value:.4f}" if value < 1 else f"{value / 1024 / 1024:.1f}MB" if "memory" in metric_name else f"{value:.3f}s"
                elif metric_name in ["cache_hit_rate"]:
                    formatted_value = f"{value:.1%}"
                elif metric_name in ["error_rate"]:
                    formatted_value = f"{value:.2%}"
                else:
                    formatted_value = f"{value:.2f}"
                
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")
                rankings_section += f"{medal} **{language}**: {formatted_value}\n"
            
            rankings_section += "\n"
        
        return rankings_section
    
    def _generate_trend_analysis(self, language_data: Dict[str, LanguagePerformanceData]) -> str:
        """Generate trend analysis section."""
        # This would analyze historical data if available
        # For now, provide structure for future implementation
        
        trend_section = """# Trend Analysis

## Historical Performance Trends

*Note: This section requires historical performance data for trend analysis.*

### Parsing Performance Trends
- Long-term parsing speed improvements
- Language-specific performance evolution
- Impact of system optimizations

### Memory Usage Trends  
- Memory efficiency improvements over time
- Memory leak prevention success
- Cache optimization effectiveness

### Error Rate Trends
- Error rate reduction over time
- Language-specific error patterns
- System reliability improvements

## Predictive Analysis

Based on current performance patterns:

1. **Performance Convergence**: Languages showing similar performance patterns
2. **Optimization Opportunities**: Areas with highest improvement potential
3. **Stability Indicators**: Metrics showing consistent performance

"""
        return trend_section
    
    def _generate_recommendations(self, language_data: Dict[str, LanguagePerformanceData]) -> List[PerformanceRecommendation]:
        """Generate performance recommendations."""
        recommendations = []
        languages = list(language_data.keys())
        
        # Analyze each language for improvement opportunities
        for language, data in language_data.items():
            # Parse performance recommendations
            if data.parsing_time_avg > 0.005:  # > 5ms is slow
                priority = "high" if data.parsing_time_avg > 0.010 else "medium"
                recommendations.append(PerformanceRecommendation(
                    language=language,
                    category="Parsing Performance",
                    priority=priority,
                    title="Optimize parsing algorithms",
                    description=f"Parsing time of {data.parsing_time_avg:.3f}s is above optimal threshold. "
                               f"Consider optimizing regular expressions, caching parsed patterns, or "
                               f"implementing more efficient parsing strategies.",
                    expected_improvement="20-40% parsing time reduction",
                    implementation_effort="Medium"
                ))
            
            # Memory usage recommendations
            if data.memory_usage_avg > 50 * 1024 * 1024:  # > 50MB
                recommendations.append(PerformanceRecommendation(
                    language=language,
                    category="Memory Usage",
                    priority="medium",
                    title="Reduce memory consumption",
                    description=f"Average memory usage of {data.memory_usage_avg / 1024 / 1024:.1f}MB "
                               f"suggests opportunities for optimization. Review object lifecycle, "
                               f"implement lazy loading, and optimize data structures.",
                    expected_improvement="15-30% memory reduction",
                    implementation_effort="Medium to High"
                ))
            
            # Cache performance recommendations
            if data.cache_hit_rate < 0.8:  # < 80% hit rate
                recommendations.append(PerformanceRecommendation(
                    language=language,
                    category="Cache Performance",
                    priority="medium",
                    title="Improve caching strategy",
                    description=f"Cache hit rate of {data.cache_hit_rate:.1%} indicates suboptimal "
                               f"caching. Consider implementing smarter cache eviction policies, "
                               f"increasing cache size, or improving cache key strategies.",
                    expected_improvement="10-25% performance improvement",
                    implementation_effort="Low to Medium"
                ))
            
            # Error rate recommendations
            if data.error_rate > 0.02:  # > 2% error rate
                priority = "critical" if data.error_rate > 0.05 else "high"
                recommendations.append(PerformanceRecommendation(
                    language=language,
                    category="Error Handling",
                    priority=priority,
                    title="Reduce error rate",
                    description=f"Error rate of {data.error_rate:.1%} is above acceptable threshold. "
                               f"Review error patterns, improve input validation, and enhance "
                               f"error recovery mechanisms.",
                    expected_improvement="Improved reliability and user experience",
                    implementation_effort="Medium"
                ))
        
        return recommendations
    
    def _generate_recommendations_section(self, recommendations: List[PerformanceRecommendation]) -> str:
        """Generate recommendations section text."""
        if not recommendations:
            return "# Recommendations\n\n✅ No performance issues detected. System is performing optimally.\n\n"
        
        # Group by priority
        by_priority = {}
        for rec in recommendations:
            if rec.priority not in by_priority:
                by_priority[rec.priority] = []
            by_priority[rec.priority].append(rec)
        
        rec_section = "# Performance Recommendations\n\n"
        
        priority_order = ["critical", "high", "medium", "low"]
        priority_icons = {
            "critical": "🚨",
            "high": "🔴", 
            "medium": "🟡",
            "low": "🟢"
        }
        
        for priority in priority_order:
            if priority not in by_priority:
                continue
                
            rec_section += f"## {priority_icons[priority]} {priority.title()} Priority\n\n"
            
            for rec in by_priority[priority]:
                rec_section += f"### {rec.language} - {rec.title}\n\n"
                rec_section += f"**Category**: {rec.category}\n\n"
                rec_section += f"**Description**: {rec.description}\n\n"
                rec_section += f"**Expected Improvement**: {rec.expected_improvement}\n\n"
                rec_section += f"**Implementation Effort**: {rec.implementation_effort}\n\n"
                rec_section += "---\n\n"
        
        return rec_section
    
    def _generate_raw_data_section(self, language_data: Dict[str, LanguagePerformanceData]) -> str:
        """Generate raw data section."""
        raw_section = "# Raw Performance Data\n\n"
        
        for language, data in language_data.items():
            raw_section += f"## {language}\n\n"
            raw_section += "```json\n"
            raw_section += json.dumps(asdict(data), indent=2)
            raw_section += "\n```\n\n"
        
        return raw_section
    
    def _create_full_report(self, sections: Dict[str, Any], report_name: str) -> str:
        """Create the full report from all sections."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Generate recommendations section from recommendations data
        if isinstance(sections["recommendations"], list):
            sections["recommendations"] = self._generate_recommendations_section(sections["recommendations"])
        
        full_report = f"""# Multilingual Performance Analysis Report

**Report Name**: {report_name}  
**Generated**: {timestamp}  
**System**: Frohlich Experiment Multilingual Processing

---

{sections["executive_summary"]}

---

{sections["detailed_comparisons"]}

---

{sections["performance_rankings"]}

---

{sections["trend_analysis"]}

---

{sections["recommendations"]}

---

{sections["raw_data"]}

---

*Report generated by Frohlich Experiment Performance Analysis System*
"""
        
        return full_report
    
    def _compare_languages(self, lang1_data: LanguagePerformanceData, 
                          lang2_data: LanguagePerformanceData) -> List[PerformanceComparison]:
        """Compare two languages across all metrics."""
        comparisons = []
        
        metrics = [
            "parsing_time_avg", "parsing_time_p95", "memory_usage_avg",
            "memory_growth_rate", "cache_hit_rate", "error_rate",
            "throughput_rate", "cpu_usage_avg"
        ]
        
        for metric in metrics:
            val1 = getattr(lang1_data, metric)
            val2 = getattr(lang2_data, metric)
            
            diff_abs = val2 - val1
            diff_pct = (diff_abs / val1 * 100) if val1 != 0 else 0
            
            # Determine winner (lower is better for most metrics except cache_hit_rate and throughput_rate)
            if metric in ["cache_hit_rate", "throughput_rate"]:
                winner = lang2_data.language if val2 > val1 else lang1_data.language
            else:
                winner = lang2_data.language if val2 < val1 else lang1_data.language
            
            # Determine significance
            abs_diff_pct = abs(diff_pct)
            if abs_diff_pct >= self.significance_thresholds["major"]:
                significance = "major"
            elif abs_diff_pct >= self.significance_thresholds["moderate"]:
                significance = "moderate"
            elif abs_diff_pct >= self.significance_thresholds["minor"]:
                significance = "minor"
            else:
                significance = "negligible"
            
            comparison = PerformanceComparison(
                baseline_language=lang1_data.language,
                comparison_language=lang2_data.language,
                metric_name=metric,
                baseline_value=val1,
                comparison_value=val2,
                difference_absolute=diff_abs,
                difference_percentage=diff_pct,
                winner=winner,
                significance=significance
            )
            
            comparisons.append(comparison)
        
        return comparisons
    
    def _generate_csv_report(self, language_data: Dict[str, LanguagePerformanceData], report_name: str):
        """Generate CSV report if pandas is available."""
        if not HAS_PANDAS:
            return
        
        # Convert data to DataFrame
        data_rows = []
        for language, data in language_data.items():
            data_dict = asdict(data)
            data_rows.append(data_dict)
        
        df = pd.DataFrame(data_rows)
        
        # Save to CSV
        csv_path = self.output_dir / f"{report_name}.csv"
        df.to_csv(csv_path, index=False)
        print(f"CSV report generated: {csv_path}")
    
    def _generate_visual_report(self, language_data: Dict[str, LanguagePerformanceData], report_name: str):
        """Generate visual report with charts if matplotlib is available."""
        if not HAS_PLOTTING:
            return
        
        # Set up the plotting style
        plt.style.use('seaborn-v0_8' if hasattr(plt.style, 'seaborn-v0_8') else 'default')
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Multilingual Performance Analysis', fontsize=16)
        
        languages = list(language_data.keys())
        
        # Parsing time comparison
        parsing_times = [language_data[lang].parsing_time_avg for lang in languages]
        axes[0, 0].bar(languages, parsing_times, color=['#1f77b4', '#ff7f0e', '#2ca02c'][:len(languages)])
        axes[0, 0].set_title('Average Parsing Time')
        axes[0, 0].set_ylabel('Time (seconds)')
        axes[0, 0].tick_params(axis='x', rotation=45)
        
        # Memory usage comparison  
        memory_usage = [language_data[lang].memory_usage_avg / 1024 / 1024 for lang in languages]
        axes[0, 1].bar(languages, memory_usage, color=['#d62728', '#9467bd', '#8c564b'][:len(languages)])
        axes[0, 1].set_title('Average Memory Usage')
        axes[0, 1].set_ylabel('Memory (MB)')
        axes[0, 1].tick_params(axis='x', rotation=45)
        
        # Cache hit rate comparison
        cache_rates = [language_data[lang].cache_hit_rate * 100 for lang in languages]
        axes[1, 0].bar(languages, cache_rates, color=['#e377c2', '#7f7f7f', '#bcbd22'][:len(languages)])
        axes[1, 0].set_title('Cache Hit Rate')
        axes[1, 0].set_ylabel('Hit Rate (%)')
        axes[1, 0].tick_params(axis='x', rotation=45)
        
        # Error rate comparison
        error_rates = [language_data[lang].error_rate * 100 for lang in languages]
        axes[1, 1].bar(languages, error_rates, color=['#17becf', '#ff9896', '#ffbb78'][:len(languages)])
        axes[1, 1].set_title('Error Rate')
        axes[1, 1].set_ylabel('Error Rate (%)')
        axes[1, 1].tick_params(axis='x', rotation=45)
        
        # Adjust layout and save
        plt.tight_layout()
        
        # Save the plot
        plot_path = self.output_dir / f"{report_name}_charts.png"
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Visual report generated: {plot_path}")


async def generate_sample_report():
    """Generate a sample performance report for testing."""
    # Create sample data
    sample_data = {
        "English": LanguagePerformanceData(
            language="English",
            parsing_time_avg=0.003,
            parsing_time_p95=0.008,
            memory_usage_avg=45 * 1024 * 1024,
            memory_growth_rate=1024,
            cache_hit_rate=0.85,
            error_rate=0.01,
            throughput_rate=333.33,
            cpu_usage_avg=15.5,
            test_timestamp=datetime.now().isoformat()
        ),
        "Spanish": LanguagePerformanceData(
            language="Spanish",
            parsing_time_avg=0.004,
            parsing_time_p95=0.009,
            memory_usage_avg=48 * 1024 * 1024,
            memory_growth_rate=1200,
            cache_hit_rate=0.82,
            error_rate=0.015,
            throughput_rate=250.0,
            cpu_usage_avg=18.2,
            test_timestamp=datetime.now().isoformat()
        ),
        "Mandarin": LanguagePerformanceData(
            language="Mandarin",
            parsing_time_avg=0.006,
            parsing_time_p95=0.012,
            memory_usage_avg=52 * 1024 * 1024,
            memory_growth_rate=1500,
            cache_hit_rate=0.78,
            error_rate=0.02,
            throughput_rate=166.67,
            cpu_usage_avg=22.8,
            test_timestamp=datetime.now().isoformat()
        )
    }
    
    # Generate report
    generator = PerformanceReportGenerator()
    report_path = generator.generate_comprehensive_report(sample_data, "sample_multilingual_performance")
    
    print(f"Sample report generated at: {report_path}")
    return report_path


if __name__ == "__main__":
    # Generate a sample report for demonstration
    asyncio.run(generate_sample_report())