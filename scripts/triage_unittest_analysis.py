#!/usr/bin/env python3
"""
Test Triage Analysis Script

Analyzes unittest.TestCase files to categorize them as:
- DELETE: Obsolete, duplicate, or wrong testing approach
- MIGRATE: Core behavior worth preserving
- REPLACE: Needs complete rewriting with scenario-driven approaches

Focus on services-first architecture alignment and avoiding "overfitted golden tests"
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from enum import Enum

class TriageCategory(Enum):
    DELETE = "DELETE"
    MIGRATE = "MIGRATE"
    REPLACE = "REPLACE"

@dataclass
class TestAnalysis:
    file_path: str
    category: TriageCategory
    reasons: List[str]
    test_methods: List[str]
    dependencies: List[str]
    lines_of_code: int
    has_golden_tests: bool
    tests_services: bool
    tests_core_behavior: bool
    has_duplicates: bool

class UnittestTriageAnalyzer:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.unittest_files = []
        self.pytest_files = []
        self.services_files = []

        # Load existing test files for comparison
        self._discover_test_files()

        # Common patterns indicating problematic tests
        self.golden_test_patterns = [
            r'assert.*==.*""".*"""',  # Multi-line string assertions
            r'expected.*=.*"""',       # Expected output strings
            r'\.strip\(\).*==',       # String stripping comparisons
            r'json\.loads.*expected', # JSON string comparisons
        ]

        # Patterns indicating valuable core behavior tests
        self.core_behavior_patterns = [
            r'test.*reproducib',
            r'test.*consistent',
            r'test.*validation',
            r'test.*error.*handling',
            r'test.*edge.*case',
        ]

        # Services-first architecture components
        self.services_components = {
            'SpeakingOrderService', 'DiscussionService', 'VotingService',
            'MemoryService', 'CounterfactualsService', 'Phase2Manager'
        }

    def _discover_test_files(self):
        """Find all test files to understand the testing landscape"""
        tests_dir = self.project_root / "tests"

        for file_path in tests_dir.rglob("*.py"):
            if file_path.name.startswith("test_"):
                content = file_path.read_text(encoding='utf-8', errors='ignore')

                if "unittest.TestCase" in content or "import unittest" in content:
                    self.unittest_files.append(file_path)
                elif "def test_" in content or "import pytest" in content:
                    self.pytest_files.append(file_path)

        # Find services files for architecture alignment checks
        services_dir = self.project_root / "core" / "services"
        if services_dir.exists():
            self.services_files = list(services_dir.glob("*.py"))

    def analyze_file(self, file_path: Path) -> TestAnalysis:
        """Analyze a single unittest file"""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            tree = ast.parse(content)
        except:
            return TestAnalysis(
                file_path=str(file_path),
                category=TriageCategory.DELETE,
                reasons=["Cannot parse file"],
                test_methods=[],
                dependencies=[],
                lines_of_code=0,
                has_golden_tests=False,
                tests_services=False,
                tests_core_behavior=False,
                has_duplicates=False
            )

        # Extract test methods and analyze patterns
        test_methods = self._extract_test_methods(tree)
        dependencies = self._extract_dependencies(tree, content)

        # Analyze testing patterns
        has_golden_tests = self._has_golden_test_patterns(content)
        tests_services = self._tests_services_architecture(content)
        tests_core_behavior = self._tests_core_behavior(content)
        has_duplicates = self._check_for_duplicates(file_path, test_methods)

        lines_of_code = len(content.splitlines())

        # Determine category and reasons
        category, reasons = self._categorize_test_file(
            file_path, content, test_methods, has_golden_tests,
            tests_services, tests_core_behavior, has_duplicates
        )

        return TestAnalysis(
            file_path=str(file_path),
            category=category,
            reasons=reasons,
            test_methods=test_methods,
            dependencies=dependencies,
            lines_of_code=lines_of_code,
            has_golden_tests=has_golden_tests,
            tests_services=tests_services,
            tests_core_behavior=tests_core_behavior,
            has_duplicates=has_duplicates
        )

    def _extract_test_methods(self, tree: ast.AST) -> List[str]:
        """Extract test method names from AST"""
        test_methods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                test_methods.append(node.name)
        return test_methods

    def _extract_dependencies(self, tree: ast.AST, content: str) -> List[str]:
        """Extract imported modules and dependencies"""
        dependencies = []

        # Extract imports from AST
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    dependencies.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    dependencies.append(node.module)

        # Look for component usage in content
        for component in self.services_components:
            if component in content:
                dependencies.append(component)

        return list(set(dependencies))

    def _has_golden_test_patterns(self, content: str) -> bool:
        """Check if file contains golden test patterns"""
        for pattern in self.golden_test_patterns:
            if re.search(pattern, content, re.MULTILINE | re.DOTALL):
                return True
        return False

    def _tests_services_architecture(self, content: str) -> bool:
        """Check if tests target services-first architecture"""
        for service in self.services_components:
            if service in content:
                return True
        return False

    def _tests_core_behavior(self, content: str) -> bool:
        """Check if tests validate core system behavior"""
        for pattern in self.core_behavior_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True

        # Check for validation, error handling, edge cases
        core_indicators = [
            'reproducibility', 'consistency', 'validation',
            'error_handling', 'edge_case', 'boundary'
        ]

        content_lower = content.lower()
        return any(indicator in content_lower for indicator in core_indicators)

    def _check_for_duplicates(self, file_path: Path, test_methods: List[str]) -> bool:
        """Check if similar tests exist in pytest files"""
        file_name_base = file_path.stem.replace('test_', '')

        # Look for similar pytest files
        for pytest_file in self.pytest_files:
            if file_name_base in pytest_file.stem:
                return True

        # Check for similar test method names
        for pytest_file in self.pytest_files:
            try:
                pytest_content = pytest_file.read_text(encoding='utf-8', errors='ignore')
                for method in test_methods:
                    method_base = method.replace('test_', '')
                    if method_base in pytest_content:
                        return True
            except:
                continue

        return False

    def _categorize_test_file(self, file_path: Path, content: str, test_methods: List[str],
                            has_golden_tests: bool, tests_services: bool,
                            tests_core_behavior: bool, has_duplicates: bool) -> Tuple[TriageCategory, List[str]]:
        """Determine the appropriate category for the test file"""
        reasons = []
        file_name = file_path.name

        # Strong DELETE indicators
        if has_golden_tests and not tests_core_behavior:
            reasons.append("Contains golden tests without core behavior validation")

        if has_duplicates and not tests_core_behavior:
            reasons.append("Duplicate coverage exists in pytest and no unique core behavior")

        if not test_methods:
            reasons.append("No test methods found")

        # Check for obsolete testing patterns
        obsolete_patterns = [
            'test.*string.*format',
            'test.*parsing.*exact',
            'test.*output.*match',
            'assert.*in.*expected',
        ]

        for pattern in obsolete_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                reasons.append(f"Uses obsolete testing pattern: {pattern}")

        # Services architecture misalignment
        if not tests_services and 'phase2' in file_name.lower():
            reasons.append("Phase2 test doesn't align with services-first architecture")

        # Strong MIGRATE indicators
        migrate_indicators = []
        if tests_core_behavior and not has_duplicates:
            migrate_indicators.append("Tests core behavior without duplication")

        if 'reproducibility' in file_name or 'models' in file_name:
            migrate_indicators.append("Tests fundamental system behavior")

        if tests_services and tests_core_behavior:
            migrate_indicators.append("Aligns with services architecture and tests core behavior")

        # Strong REPLACE indicators
        replace_indicators = []
        if has_golden_tests and tests_core_behavior:
            replace_indicators.append("Has valuable behavior tests but uses golden test approach")

        if not tests_services and 'phase2' in file_name.lower():
            replace_indicators.append("Phase2 functionality needs scenario-driven replacement")

        # Decision logic
        if len(reasons) >= 2:  # Multiple negative indicators
            return TriageCategory.DELETE, reasons
        elif migrate_indicators and not reasons:
            return TriageCategory.MIGRATE, migrate_indicators
        elif replace_indicators or (has_golden_tests and tests_core_behavior):
            return TriageCategory.REPLACE, replace_indicators + reasons
        elif reasons:
            return TriageCategory.DELETE, reasons
        else:
            # Default case - need manual review
            return TriageCategory.MIGRATE, ["Requires manual review - unclear categorization"]

    def analyze_all_files(self) -> Dict[TriageCategory, List[TestAnalysis]]:
        """Analyze all unittest files and categorize them"""
        results = {category: [] for category in TriageCategory}

        for file_path in self.unittest_files:
            analysis = self.analyze_file(file_path)
            results[analysis.category].append(analysis)

        return results

    def generate_report(self, results: Dict[TriageCategory, List[TestAnalysis]]) -> str:
        """Generate a detailed triage report"""
        report = []
        report.append("# Unittest Triage Analysis Report")
        report.append(f"Generated for: {self.project_root}")
        report.append(f"Total unittest files analyzed: {sum(len(analyses) for analyses in results.values())}")
        report.append(f"Total pytest files found: {len(self.pytest_files)}")
        report.append("")

        # Summary
        report.append("## Summary")
        for category in TriageCategory:
            count = len(results[category])
            report.append(f"- **{category.value}**: {count} files")
        report.append("")

        # Detailed analysis by category
        for category in TriageCategory:
            analyses = results[category]
            if not analyses:
                continue

            report.append(f"## {category.value} - {len(analyses)} files")
            report.append("")

            for analysis in sorted(analyses, key=lambda x: x.file_path):
                report.append(f"### {Path(analysis.file_path).name}")
                report.append(f"**Path**: `{analysis.file_path}`")
                report.append(f"**Lines of Code**: {analysis.lines_of_code}")
                report.append(f"**Test Methods**: {len(analysis.test_methods)}")

                if analysis.reasons:
                    report.append("**Reasons**:")
                    for reason in analysis.reasons:
                        report.append(f"- {reason}")

                report.append("**Analysis**:")
                report.append(f"- Golden tests: {'Yes' if analysis.has_golden_tests else 'No'}")
                report.append(f"- Tests services: {'Yes' if analysis.tests_services else 'No'}")
                report.append(f"- Tests core behavior: {'Yes' if analysis.tests_core_behavior else 'No'}")
                report.append(f"- Has duplicates: {'Yes' if analysis.has_duplicates else 'No'}")

                if analysis.test_methods:
                    report.append("**Test Methods**:")
                    for method in analysis.test_methods[:5]:  # Show first 5
                        report.append(f"- {method}")
                    if len(analysis.test_methods) > 5:
                        report.append(f"- ... and {len(analysis.test_methods) - 5} more")

                report.append("")

        # Recommendations
        report.append("## Recommendations")
        report.append("")

        delete_count = len(results[TriageCategory.DELETE])
        migrate_count = len(results[TriageCategory.MIGRATE])
        replace_count = len(results[TriageCategory.REPLACE])

        if delete_count > 0:
            report.append(f"1. **Delete {delete_count} files** - These are obsolete or duplicate existing coverage")

        if migrate_count > 0:
            report.append(f"2. **Migrate {migrate_count} files** - Convert these to pytest with minimal changes")

        if replace_count > 0:
            report.append(f"3. **Replace {replace_count} files** - Rewrite these with scenario-driven approaches")

        report.append("")
        report.append("## Next Steps")
        report.append("1. Review DELETE recommendations and remove obsolete tests")
        report.append("2. Quick migration of MIGRATE files to pytest")
        report.append("3. Design scenario-driven replacements for REPLACE files")
        report.append("4. Focus on services-first architecture alignment")

        return "\n".join(report)

def main():
    """Run the triage analysis"""
    project_root = "/Users/lucasmuller/Desktop/Githubg/Rawls_v3"

    analyzer = UnittestTriageAnalyzer(project_root)
    print(f"Found {len(analyzer.unittest_files)} unittest files")
    print(f"Found {len(analyzer.pytest_files)} pytest files")

    results = analyzer.analyze_all_files()
    report = analyzer.generate_report(results)

    # Save report
    report_path = Path(project_root) / "unittest_triage_report.md"
    report_path.write_text(report)

    print(f"\nTriage report saved to: {report_path}")

    # Print summary
    print("\n=== TRIAGE SUMMARY ===")
    for category in TriageCategory:
        count = len(results[category])
        print(f"{category.value}: {count} files")

if __name__ == "__main__":
    main()