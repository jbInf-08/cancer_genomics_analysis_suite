"""
Main Data Collection Runner

This module provides the main interface for running comprehensive data collection
from all available biomedical data sources. It includes both programmatic and
command-line interfaces.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

from .master_orchestrator import MasterDataOrchestrator


class ComprehensiveDataCollector:
    """
    Main interface for comprehensive data collection.
    
    This class provides a high-level interface for collecting data from
    all available biomedical data sources with various configuration options.
    """
    
    def __init__(self, 
                 output_dir: str = "data/external_sources",
                 config_file: str = "data_collection/config.json",
                 max_workers: int = 4,
                 log_level: str = "INFO"):
        """
        Initialize the comprehensive data collector.
        
        Args:
            output_dir: Directory for collected data
            config_file: Path to configuration file
            max_workers: Maximum number of parallel workers
            log_level: Logging level
        """
        self.output_dir = output_dir
        self.config_file = config_file
        self.max_workers = max_workers
        
        # Set up logging
        self.logger = self._setup_logger(log_level)
        
        # Initialize orchestrator
        self.orchestrator = MasterDataOrchestrator(
            config_file=config_file,
            output_dir=output_dir,
            max_workers=max_workers,
            logger=self.logger
        )
    
    def _setup_logger(self, log_level: str) -> logging.Logger:
        """Set up logger for the comprehensive collector."""
        logger = logging.getLogger("ComprehensiveDataCollector")
        logger.setLevel(getattr(logging, log_level.upper()))
        
        if not logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
            
            # File handler
            log_dir = Path(self.output_dir) / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_dir / "data_collection.log")
            file_handler.setFormatter(console_formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    def get_available_sources(self) -> List[Dict[str, Any]]:
        """
        Get list of all available data sources.
        
        Returns:
            List of dictionaries containing source information
        """
        return self.orchestrator.get_available_sources()
    
    def run_comprehensive_collection(self, 
                                   sources: Optional[List[str]] = None,
                                   data_types: Optional[List[str]] = None,
                                   cancer_types: Optional[List[str]] = None,
                                   **kwargs) -> Dict[str, Any]:
        """
        Run comprehensive data collection from all or selected sources.
        
        Args:
            sources: List of source IDs to collect from (None for all)
            data_types: List of data types to collect (None for all)
            cancer_types: List of cancer types to focus on (None for all)
            **kwargs: Additional parameters for collection
            
        Returns:
            Dictionary containing comprehensive collection results
        """
        self.logger.info("Starting comprehensive data collection")
        
        try:
            results = self.orchestrator.run_comprehensive_collection(
                sources=sources,
                data_types=data_types,
                cancer_types=cancer_types
            )
            
            self.logger.info("Completed comprehensive data collection")
            return results
            
        except Exception as e:
            self.logger.error(f"Comprehensive data collection failed: {e}")
            raise
    
    def collect_from_specific_sources(self, 
                                    collection_plan: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Collect data from specific sources with custom parameters.
        
        Args:
            collection_plan: Dictionary mapping source IDs to collection parameters
            
        Returns:
            Dictionary containing collection results
        """
        self.logger.info(f"Starting collection from {len(collection_plan)} specific sources")
        
        try:
            results = self.orchestrator.collect_from_multiple_sources(collection_plan)
            
            self.logger.info("Completed collection from specific sources")
            return results
            
        except Exception as e:
            self.logger.error(f"Collection from specific sources failed: {e}")
            raise
    
    def collect_from_single_source(self, 
                                 source_id: str,
                                 data_type: Optional[str] = None,
                                 **kwargs) -> Dict[str, Any]:
        """
        Collect data from a single source.
        
        Args:
            source_id: Identifier for the data source
            data_type: Specific data type to collect
            **kwargs: Additional parameters for collection
            
        Returns:
            Dictionary containing collection results
        """
        self.logger.info(f"Starting collection from single source: {source_id}")
        
        try:
            results = self.orchestrator.collect_from_single_source(
                source_id=source_id,
                data_type=data_type,
                **kwargs
            )
            
            self.logger.info(f"Completed collection from {source_id}")
            return results
            
        except Exception as e:
            self.logger.error(f"Collection from {source_id} failed: {e}")
            raise
    
    def get_collection_status(self) -> Dict[str, Any]:
        """Get current collection status."""
        return self.orchestrator.get_collection_status()
    
    def print_collection_summary(self, results: Dict[str, Any]):
        """Print a summary of collection results."""
        print("\n" + "="*60)
        print("COMPREHENSIVE DATA COLLECTION SUMMARY")
        print("="*60)
        
        if "start_time" in results and "end_time" in results:
            print(f"Collection Period: {results['start_time']} to {results['end_time']}")
        
        print(f"Total Sources: {results.get('total_sources', 0)}")
        print(f"Successful Sources: {results.get('successful_sources', 0)}")
        print(f"Failed Sources: {results.get('failed_sources', 0)}")
        print(f"Total Files Created: {results.get('total_files_created', 0)}")
        print(f"Total Samples Collected: {results.get('total_samples_collected', 0)}")
        
        if results.get('errors'):
            print(f"\nErrors ({len(results['errors'])}):")
            for error in results['errors'][:5]:  # Show first 5 errors
                print(f"  - {error.get('source', 'Unknown')}: {error.get('error', 'Unknown error')}")
            if len(results['errors']) > 5:
                print(f"  ... and {len(results['errors']) - 5} more errors")
        
        if results.get('warnings'):
            print(f"\nWarnings ({len(results['warnings'])}):")
            for warning in results['warnings'][:5]:  # Show first 5 warnings
                print(f"  - {warning}")
            if len(results['warnings']) > 5:
                print(f"  ... and {len(results['warnings']) - 5} more warnings")
        
        print("\nSource Results:")
        for source_id, source_result in results.get('source_results', {}).items():
            status = "✓" if source_result.get('success', False) else "✗"
            files = source_result.get('summary', {}).get('files_created', 0)
            samples = source_result.get('summary', {}).get('samples_collected', 0)
            print(f"  {status} {source_id}: {files} files, {samples} samples")
        
        print("="*60)


def main():
    """Main entry point for command-line interface."""
    parser = argparse.ArgumentParser(
        description="Comprehensive Data Collection System for Cancer Genomics Analysis Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all available sources
  python -m data_collection.run_data_collection --list-sources
  
  # Run collection from specific sources
  python -m data_collection.run_data_collection --sources TCGA GEO COSMIC
  
  # Run with custom configuration
  python -m data_collection.run_data_collection --config custom_config.json
  
  # Run with specific data types
  python -m data_collection.run_data_collection --data-types clinical expression mutation
  
  # Run with specific cancer types
  python -m data_collection.run_data_collection --cancer-types BRCA LUAD COAD
  
  # Run comprehensive collection (all sources)
  python -m data_collection.run_data_collection --comprehensive
        """
    )
    
    # Main options
    parser.add_argument(
        "--list-sources",
        action="store_true",
        help="List all available data sources"
    )
    
    parser.add_argument(
        "--comprehensive",
        action="store_true",
        help="Run comprehensive collection from all sources"
    )
    
    # Collection options
    parser.add_argument(
        "--sources",
        nargs="+",
        help="List of source IDs to collect from"
    )
    
    parser.add_argument(
        "--data-types",
        nargs="+",
        help="List of data types to collect"
    )
    
    parser.add_argument(
        "--cancer-types",
        nargs="+",
        help="List of cancer types to focus on"
    )
    
    # Configuration options
    parser.add_argument(
        "--config",
        default="data_collection/config.json",
        help="Path to configuration file (default: data_collection/config.json)"
    )
    
    parser.add_argument(
        "--output-dir",
        default="data/external_sources",
        help="Output directory for collected data (default: data/external_sources)"
    )
    
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Maximum number of parallel workers (default: 4)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    # Single source collection
    parser.add_argument(
        "--single-source",
        help="Collect from a single source"
    )
    
    parser.add_argument(
        "--single-data-type",
        help="Data type for single source collection"
    )
    
    args = parser.parse_args()
    
    # Initialize collector
    try:
        collector = ComprehensiveDataCollector(
            output_dir=args.output_dir,
            config_file=args.config,
            max_workers=args.max_workers,
            log_level=args.log_level
        )
    except Exception as e:
        print(f"Failed to initialize data collector: {e}")
        sys.exit(1)
    
    # Handle different modes
    if args.list_sources:
        # List available sources
        sources = collector.get_available_sources()
        print("\nAvailable Data Sources:")
        print("="*50)
        
        for source in sources:
            print(f"\n{source['id'].upper()}")
            print(f"  Name: {source['name']}")
            print(f"  Description: {source['description']}")
            print(f"  Data Types: {', '.join(source.get('data_types', []))}")
            print(f"  Cancer Types: {', '.join(source.get('cancer_types', []))}")
            print(f"  Sample Limit: {source.get('sample_limit', 'N/A')}")
            print(f"  Status: {source.get('status', 'Unknown')}")
        
        print(f"\nTotal Sources: {len(sources)}")
        
    elif args.single_source:
        # Single source collection
        try:
            results = collector.collect_from_single_source(
                source_id=args.single_source,
                data_type=args.single_data_type
            )
            
            if results.get('success', False):
                print(f"\n✓ Successfully collected data from {args.single_source}")
                summary = results.get('summary', {})
                print(f"  Files created: {summary.get('files_created', 0)}")
                print(f"  Samples collected: {summary.get('samples_collected', 0)}")
            else:
                print(f"\n✗ Failed to collect data from {args.single_source}")
                print(f"  Error: {results.get('error', 'Unknown error')}")
                sys.exit(1)
                
        except Exception as e:
            print(f"Collection from {args.single_source} failed: {e}")
            sys.exit(1)
    
    elif args.comprehensive or args.sources:
        # Comprehensive or multi-source collection
        try:
            if args.comprehensive:
                print("Running comprehensive data collection from all sources...")
                results = collector.run_comprehensive_collection()
            else:
                print(f"Running data collection from {len(args.sources)} sources...")
                results = collector.run_comprehensive_collection(
                    sources=args.sources,
                    data_types=args.data_types,
                    cancer_types=args.cancer_types
                )
            
            # Print summary
            collector.print_collection_summary(results)
            
            # Check for failures
            if results.get('failed_sources', 0) > 0:
                print(f"\nWarning: {results['failed_sources']} sources failed to collect data")
                sys.exit(1)
            else:
                print("\n✓ All sources completed successfully!")
                
        except Exception as e:
            print(f"Data collection failed: {e}")
            sys.exit(1)
    
    else:
        # No action specified
        parser.print_help()


if __name__ == "__main__":
    main()
