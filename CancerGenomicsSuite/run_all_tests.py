#!/usr/bin/env python3
"""
Cancer Genomics Analysis Suite - Test Runner

This script provides comprehensive testing capabilities for the cancer genomics
analysis suite, including unit tests, integration tests, and coverage reporting.

Usage:
    python run_all_tests.py [options]

Options:
    --unit          Run only unit tests
    --integration   Run only integration tests
    --coverage      Generate coverage report
    --verbose       Verbose output
    --parallel      Run tests in parallel
    --html-report   Generate HTML coverage report
    --xml-report    Generate XML test report
    --help          Show this help message
"""

import pytest
import sys
import os
import argparse
import subprocess
from pathlib import Path
from typing import List, Optional


class TestRunner:
    """Comprehensive test runner for the Cancer Genomics Analysis Suite."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.tests_dir = self.project_root / "tests"
        self.coverage_dir = self.project_root / "coverage_reports"
        self.reports_dir = self.project_root / "test_reports"
        
        # Ensure directories exist
        self.coverage_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
    
    def run_unit_tests(self, verbose: bool = False) -> int:
        """Run unit tests only."""
        print("🧬 Running unit tests for Cancer Genomics Analysis Suite...")
        
        args = [
            "pytest",
            str(self.tests_dir),
            "-v" if verbose else "-q",
            "--tb=short",
            "--strict-markers",
            "-m", "not integration and not slow"
        ]
        
        return subprocess.call(args)
    
    def run_integration_tests(self, verbose: bool = False) -> int:
        """Run integration tests only."""
        print("🔬 Running integration tests for Cancer Genomics Analysis Suite...")
        
        args = [
            "pytest",
            str(self.tests_dir),
            "-v" if verbose else "-q",
            "--tb=short",
            "--strict-markers",
            "-m", "integration"
        ]
        
        return subprocess.call(args)
    
    def run_all_tests(self, verbose: bool = False, parallel: bool = False) -> int:
        """Run all tests (unit and integration)."""
        print("🧪 Running all tests for Cancer Genomics Analysis Suite...")
        
        args = [
            "pytest",
            str(self.tests_dir),
            "-v" if verbose else "-q",
            "--tb=short",
            "--strict-markers"
        ]
        
        if parallel:
            args.extend(["-n", "auto"])
        
        return subprocess.call(args)
    
    def run_with_coverage(self, verbose: bool = False, html_report: bool = False) -> int:
        """Run tests with coverage reporting."""
        print("📊 Running tests with coverage analysis...")
        
        args = [
            "pytest",
            str(self.tests_dir),
            "-v" if verbose else "-q",
            "--tb=short",
            "--cov=.",
            "--cov-report=term-missing",
            "--cov-report=term:skip-covered",
            "--cov-fail-under=80"
        ]
        
        if html_report:
            args.extend([
                "--cov-report=html:{}".format(self.coverage_dir / "html"),
                "--cov-report=xml:{}".format(self.coverage_dir / "coverage.xml")
            ])
        
        return subprocess.call(args)
    
    def generate_xml_report(self, verbose: bool = False) -> int:
        """Run tests and generate XML report."""
        print("📋 Generating XML test report...")
        
        args = [
            "pytest",
            str(self.tests_dir),
            "-v" if verbose else "-q",
            "--tb=short",
            "--junitxml={}".format(self.reports_dir / "test_results.xml")
        ]
        
        return subprocess.call(args)
    
    def run_specific_module(self, module_name: str, verbose: bool = False) -> int:
        """Run tests for a specific module."""
        print(f"🎯 Running tests for module: {module_name}")
        
        test_file = self.tests_dir / f"test_{module_name}.py"
        if not test_file.exists():
            print(f"❌ Test file not found: {test_file}")
            return 1
        
        args = [
            "pytest",
            str(test_file),
            "-v" if verbose else "-q",
            "--tb=short"
        ]
        
        return subprocess.call(args)
    
    def check_test_environment(self) -> bool:
        """Check if the test environment is properly set up."""
        print("🔍 Checking test environment...")
        
        # Check if pytest is available
        try:
            import pytest
            print("✅ pytest is available")
        except ImportError:
            print("❌ pytest is not installed")
            return False
        
        # Check if test directory exists
        if not self.tests_dir.exists():
            print("❌ Tests directory not found")
            return False
        print("✅ Tests directory found")
        
        # Check for test files
        test_files = list(self.tests_dir.glob("test_*.py"))
        if not test_files:
            print("⚠️  No test files found in tests directory")
        else:
            print(f"✅ Found {len(test_files)} test files")
        
        return True
    
    def print_test_summary(self):
        """Print a summary of available tests."""
        print("\n📚 Available Test Modules:")
        print("=" * 50)
        
        test_files = list(self.tests_dir.glob("test_*.py"))
        for test_file in sorted(test_files):
            module_name = test_file.stem.replace("test_", "")
            print(f"  • {module_name}")
        
        print(f"\nTotal test modules: {len(test_files)}")


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="Cancer Genomics Analysis Suite Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--unit", 
        action="store_true", 
        help="Run only unit tests"
    )
    parser.add_argument(
        "--integration", 
        action="store_true", 
        help="Run only integration tests"
    )
    parser.add_argument(
        "--coverage", 
        action="store_true", 
        help="Generate coverage report"
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Verbose output"
    )
    parser.add_argument(
        "--parallel", "-p", 
        action="store_true", 
        help="Run tests in parallel"
    )
    parser.add_argument(
        "--html-report", 
        action="store_true", 
        help="Generate HTML coverage report"
    )
    parser.add_argument(
        "--xml-report", 
        action="store_true", 
        help="Generate XML test report"
    )
    parser.add_argument(
        "--module", "-m", 
        type=str, 
        help="Run tests for specific module"
    )
    parser.add_argument(
        "--check-env", 
        action="store_true", 
        help="Check test environment"
    )
    parser.add_argument(
        "--list", "-l", 
        action="store_true", 
        help="List available test modules"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    # Handle special commands
    if args.check_env:
        success = runner.check_test_environment()
        sys.exit(0 if success else 1)
    
    if args.list:
        runner.print_test_summary()
        sys.exit(0)
    
    # Run tests based on arguments
    exit_code = 0
    
    try:
        if args.module:
            exit_code = runner.run_specific_module(args.module, args.verbose)
        elif args.unit:
            exit_code = runner.run_unit_tests(args.verbose)
        elif args.integration:
            exit_code = runner.run_integration_tests(args.verbose)
        elif args.coverage:
            exit_code = runner.run_with_coverage(args.verbose, args.html_report)
        elif args.xml_report:
            exit_code = runner.generate_xml_report(args.verbose)
        else:
            # Default: run all tests with coverage
            exit_code = runner.run_with_coverage(args.verbose, args.html_report)
        
        # Print summary
        if exit_code == 0:
            print("\n🎉 All tests completed successfully!")
        else:
            print("\n❌ Some tests failed. Check the output above for details.")
        
    except KeyboardInterrupt:
        print("\n⚠️  Test run interrupted by user")
        exit_code = 130
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        exit_code = 1
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
