"""
Comprehensive Testing Suite for Data Collectors

This module provides comprehensive testing capabilities for all data collectors
in the system. It includes unit tests, integration tests, and validation tests
for each collector.
"""

import json
import logging
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, MagicMock

from .base_collector import DataCollectorBase
from .master_orchestrator import MasterDataOrchestrator
from .run_data_collection import ComprehensiveDataCollector


class TestDataCollectorBase(unittest.TestCase):
    """Test cases for the base data collector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            "sample_limit": 10,
            "min_request_interval": 0.1,
            "max_retries": 2
        }
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test collector initialization."""
        collector = DataCollectorBase(
            output_dir=self.temp_dir,
            config=self.config
        )
        
        self.assertEqual(collector.output_dir, Path(self.temp_dir))
        self.assertEqual(collector.config, self.config)
        self.assertIsNotNone(collector.logger)
        self.assertEqual(collector.max_retries, 2)
        self.assertEqual(collector.min_request_interval, 0.1)
    
    def test_filename_generation(self):
        """Test filename generation."""
        collector = DataCollectorBase(output_dir=self.temp_dir)
        
        filename = collector.generate_filename(
            "gene_expression",
            "BRCA",
            100,
            timestamp=False
        )
        
        expected = "datacollectorbase_gene_expression_BRCA_100_samples"
        self.assertEqual(filename, expected)
    
    def test_data_validation(self):
        """Test data validation."""
        collector = DataCollectorBase(output_dir=self.temp_dir)
        
        # Test with valid DataFrame
        import pandas as pd
        valid_df = pd.DataFrame({
            'gene': ['GENE1', 'GENE2'],
            'expression': [1.5, 2.3]
        })
        
        validation = collector.validate_data(valid_df)
        self.assertTrue(validation['is_valid'])
        self.assertEqual(validation['statistics']['rows'], 2)
        self.assertEqual(validation['statistics']['columns'], 2)
        
        # Test with empty DataFrame
        empty_df = pd.DataFrame()
        validation = collector.validate_data(empty_df)
        self.assertFalse(validation['is_valid'])
        self.assertIn("DataFrame is empty", validation['issues'])
    
    @patch('requests.request')
    def test_make_request(self, mock_request):
        """Test HTTP request functionality."""
        collector = DataCollectorBase(output_dir=self.temp_dir)
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"data": "test"}'
        mock_request.return_value = mock_response
        
        response = collector.make_request("http://test.com")
        
        self.assertEqual(response.status_code, 200)
        mock_request.assert_called_once()
    
    @patch('requests.request')
    def test_make_request_retry(self, mock_request):
        """Test HTTP request retry logic."""
        collector = DataCollectorBase(
            output_dir=self.temp_dir,
            config={"max_retries": 2, "retry_delay": 0.1}
        )
        
        # Mock failed then successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"data": "test"}'
        
        mock_request.side_effect = [
            Exception("Network error"),
            Exception("Network error"),
            mock_response
        ]
        
        response = collector.make_request("http://test.com")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_request.call_count, 3)


class TestMasterOrchestrator(unittest.TestCase):
    """Test cases for the master orchestrator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.json"
        
        # Create test configuration
        test_config = {
            "global": {
                "output_dir": self.temp_dir,
                "max_workers": 2
            },
            "tcga": {
                "sample_limit": 10,
                "cancer_types": ["BRCA"],
                "data_types": ["gene_expression"]
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(test_config, f)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test orchestrator initialization."""
        orchestrator = MasterDataOrchestrator(
            config_file=str(self.config_file),
            output_dir=self.temp_dir,
            max_workers=2
        )
        
        self.assertEqual(orchestrator.max_workers, 2)
        self.assertEqual(orchestrator.output_dir, Path(self.temp_dir))
        self.assertIsNotNone(orchestrator.config)
        self.assertIn("tcga", orchestrator.collectors_registry)
    
    def test_get_available_sources(self):
        """Test getting available sources."""
        orchestrator = MasterDataOrchestrator(
            config_file=str(self.config_file),
            output_dir=self.temp_dir
        )
        
        sources = orchestrator.get_available_sources()
        
        self.assertIsInstance(sources, list)
        self.assertGreater(len(sources), 0)
        
        # Check structure of source information
        for source in sources:
            self.assertIn("id", source)
            self.assertIn("name", source)
            self.assertIn("description", source)
            self.assertIn("status", source)
    
    @patch('data_collection.master_orchestrator.MasterDataOrchestrator._get_collector_class')
    def test_collect_from_single_source(self, mock_get_collector):
        """Test single source collection."""
        orchestrator = MasterDataOrchestrator(
            config_file=str(self.config_file),
            output_dir=self.temp_dir
        )
        
        # Mock collector class
        mock_collector_class = Mock()
        mock_collector = Mock()
        mock_collector.collect_data.return_value = {"samples_collected": 5}
        mock_collector.get_collection_summary.return_value = {
            "files_created": 1,
            "samples_collected": 5
        }
        mock_collector_class.return_value = mock_collector
        mock_get_collector.return_value = mock_collector_class
        
        # Test collection
        result = orchestrator.collect_from_single_source("tcga", "gene_expression")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["source"], "tcga")
        self.assertEqual(result["summary"]["samples_collected"], 5)
    
    def test_collect_from_unknown_source(self):
        """Test collection from unknown source."""
        orchestrator = MasterDataOrchestrator(
            config_file=str(self.config_file),
            output_dir=self.temp_dir
        )
        
        result = orchestrator.collect_from_single_source("unknown_source")
        
        self.assertFalse(result["success"])
        self.assertIn("Unknown data source", result["error"])


class TestComprehensiveDataCollector(unittest.TestCase):
    """Test cases for the comprehensive data collector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.json"
        
        # Create test configuration
        test_config = {
            "global": {
                "output_dir": self.temp_dir,
                "max_workers": 2
            },
            "tcga": {
                "sample_limit": 10,
                "cancer_types": ["BRCA"],
                "data_types": ["gene_expression"]
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(test_config, f)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test comprehensive collector initialization."""
        collector = ComprehensiveDataCollector(
            output_dir=self.temp_dir,
            config_file=str(self.config_file),
            max_workers=2,
            log_level="INFO"
        )
        
        self.assertEqual(collector.output_dir, self.temp_dir)
        self.assertEqual(collector.max_workers, 2)
        self.assertIsNotNone(collector.orchestrator)
        self.assertIsNotNone(collector.logger)
    
    def test_get_available_sources(self):
        """Test getting available sources."""
        collector = ComprehensiveDataCollector(
            output_dir=self.temp_dir,
            config_file=str(self.config_file)
        )
        
        sources = collector.get_available_sources()
        
        self.assertIsInstance(sources, list)
        self.assertGreater(len(sources), 0)


def test_collector(collector_path: Path) -> Dict[str, Any]:
    """
    Test a specific collector module.
    
    Args:
        collector_path: Path to the collector module
        
    Returns:
        Dictionary containing test results
    """
    test_results = {
        "collector": collector_path.name,
        "status": "unknown",
        "errors": [],
        "warnings": [],
        "tests_passed": 0,
        "tests_failed": 0
    }
    
    try:
        # Import the collector module
        import importlib.util
        spec = importlib.util.spec_from_file_location("collector", collector_path)
        collector_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(collector_module)
        
        # Get the collector class
        collector_class = None
        for attr_name in dir(collector_module):
            attr = getattr(collector_module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, DataCollectorBase) and 
                attr != DataCollectorBase):
                collector_class = attr
                break
        
        if not collector_class:
            test_results["status"] = "failed"
            test_results["errors"].append("No collector class found")
            return test_results
        
        # Test collector initialization
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                collector = collector_class(output_dir=temp_dir)
                test_results["tests_passed"] += 1
        except Exception as e:
            test_results["tests_failed"] += 1
            test_results["errors"].append(f"Initialization failed: {e}")
        
        # Test get_available_datasets method
        try:
            datasets = collector.get_available_datasets()
            if isinstance(datasets, list):
                test_results["tests_passed"] += 1
            else:
                test_results["tests_failed"] += 1
                test_results["errors"].append("get_available_datasets should return a list")
        except Exception as e:
            test_results["tests_failed"] += 1
            test_results["errors"].append(f"get_available_datasets failed: {e}")
        
        # Test collect_data method (with mock data)
        try:
            with patch.object(collector, 'make_request') as mock_request:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.text = '{"data": "test"}'
                mock_response.json.return_value = {"data": "test"}
                mock_request.return_value = mock_response
                
                # Try to collect data with minimal parameters
                result = collector.collect_data()
                
                if isinstance(result, dict):
                    test_results["tests_passed"] += 1
                else:
                    test_results["tests_failed"] += 1
                    test_results["errors"].append("collect_data should return a dictionary")
        except Exception as e:
            test_results["tests_failed"] += 1
            test_results["errors"].append(f"collect_data failed: {e}")
        
        # Determine overall status
        if test_results["tests_failed"] == 0:
            test_results["status"] = "passed"
        else:
            test_results["status"] = "failed"
    
    except Exception as e:
        test_results["status"] = "error"
        test_results["errors"].append(f"Module import failed: {e}")
    
    return test_results


def run_all_tests() -> Dict[str, Any]:
    """
    Run tests for all collectors in the system.
    
    Returns:
        Dictionary containing test results for all collectors
    """
    test_results = {
        "start_time": None,
        "end_time": None,
        "total_collectors": 0,
        "passed_collectors": 0,
        "failed_collectors": 0,
        "collector_results": {},
        "summary": {}
    }
    
    import datetime
    test_results["start_time"] = datetime.datetime.now().isoformat()
    
    # Find all collector modules
    data_collection_dir = Path(__file__).parent
    collector_files = list(data_collection_dir.glob("*_collector.py"))
    
    test_results["total_collectors"] = len(collector_files)
    
    # Test each collector
    for collector_file in collector_files:
        print(f"Testing {collector_file.name}...")
        result = test_collector(collector_file)
        test_results["collector_results"][collector_file.name] = result
        
        if result["status"] == "passed":
            test_results["passed_collectors"] += 1
        else:
            test_results["failed_collectors"] += 1
    
    test_results["end_time"] = datetime.datetime.now().isoformat()
    
    # Generate summary
    test_results["summary"] = {
        "total_tests": sum(r["tests_passed"] + r["tests_failed"] for r in test_results["collector_results"].values()),
        "passed_tests": sum(r["tests_passed"] for r in test_results["collector_results"].values()),
        "failed_tests": sum(r["tests_failed"] for r in test_results["collector_results"].values()),
        "success_rate": (test_results["passed_collectors"] / test_results["total_collectors"] * 100) if test_results["total_collectors"] > 0 else 0
    }
    
    return test_results


def print_test_results(results: Dict[str, Any]):
    """Print test results in a formatted way."""
    print("\n" + "="*60)
    print("DATA COLLECTOR TEST RESULTS")
    print("="*60)
    
    print(f"Test Period: {results['start_time']} to {results['end_time']}")
    print(f"Total Collectors: {results['total_collectors']}")
    print(f"Passed: {results['passed_collectors']}")
    print(f"Failed: {results['failed_collectors']}")
    print(f"Success Rate: {results['summary']['success_rate']:.1f}%")
    
    print(f"\nTest Summary:")
    print(f"  Total Tests: {results['summary']['total_tests']}")
    print(f"  Passed Tests: {results['summary']['passed_tests']}")
    print(f"  Failed Tests: {results['summary']['failed_tests']}")
    
    print(f"\nCollector Results:")
    for collector_name, result in results["collector_results"].items():
        status_icon = "✓" if result["status"] == "passed" else "✗"
        print(f"  {status_icon} {collector_name}: {result['status']}")
        if result["errors"]:
            for error in result["errors"]:
                print(f"    Error: {error}")
    
    print("="*60)


def main():
    """Main entry point for running tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test all data collectors")
    parser.add_argument(
        "--collector",
        help="Test a specific collector (e.g., tcga_collector.py)"
    )
    parser.add_argument(
        "--output",
        help="Output file for test results (JSON format)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    if args.collector:
        # Test specific collector
        collector_path = Path(args.collector)
        if not collector_path.exists():
            print(f"Collector file not found: {collector_path}")
            return 1
        
        result = test_collector(collector_path)
        print(f"\nTest Results for {collector_path.name}:")
        print(f"Status: {result['status']}")
        print(f"Tests Passed: {result['tests_passed']}")
        print(f"Tests Failed: {result['tests_failed']}")
        
        if result["errors"]:
            print("Errors:")
            for error in result["errors"]:
                print(f"  - {error}")
        
        return 0 if result["status"] == "passed" else 1
    
    else:
        # Test all collectors
        results = run_all_tests()
        print_test_results(results)
        
        # Save results if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\nTest results saved to {args.output}")
        
        return 0 if results["failed_collectors"] == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
