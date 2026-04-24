#!/usr/bin/env python3
"""
Comprehensive Omics Analysis Runner

This script demonstrates the complete omics analysis pipeline with all implemented
omics fields. It can be used as a standalone application or imported as a module.

Usage:
    python run_omics_analysis.py --demo                    # Run demonstration
    python run_omics_analysis.py --dashboard              # Launch dashboard
    python run_omics_analysis.py --validate <file>        # Validate data file
    python run_omics_analysis.py --integrate <files>      # Integrate multiple files
    python run_omics_analysis.py --help                   # Show help
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
import numpy as np

# Import omics modules
from .omics_registry import get_omics_registry
from .omics_processor import get_omics_processor_factory
from .omics_metadata import get_omics_metadata_manager
from .omics_integration import get_omics_integration_engine
from .omics_validation import get_omics_validation_pipeline
from .omics_dashboard import create_comprehensive_omics_dashboard
from .omics_example import ComprehensiveOmicsExample

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OmicsAnalysisRunner:
    """Main runner for comprehensive omics analysis."""
    
    def __init__(self):
        """Initialize the omics analysis runner."""
        self.registry = get_omics_registry()
        self.processor_factory = get_omics_processor_factory()
        self.metadata_manager = get_omics_metadata_manager()
        self.integration_engine = get_omics_integration_engine()
        self.validation_pipeline = get_omics_validation_pipeline()
        
        logger.info("Omics Analysis Runner initialized")
        logger.info(f"Available omics fields: {len(self.registry.get_all_fields())}")
    
    def run_demonstration(self) -> Dict[str, Any]:
        """Run the comprehensive demonstration."""
        logger.info("Running comprehensive omics demonstration...")
        
        example = ComprehensiveOmicsExample()
        results = example.run_complete_demonstration()
        
        # Print summary
        self._print_demonstration_summary(results)
        
        return results
    
    def launch_dashboard(self, port: int = 8050, debug: bool = True):
        """Launch the interactive dashboard."""
        logger.info(f"Launching omics dashboard on port {port}...")
        
        dashboard = create_comprehensive_omics_dashboard()
        dashboard.run(debug=debug, port=port)
    
    def validate_data_file(self, file_path: str, omics_type: str) -> Dict[str, Any]:
        """Validate a single data file."""
        logger.info(f"Validating {file_path} as {omics_type} data...")
        
        try:
            # Load data
            data = pd.read_csv(file_path, index_col=0)
            
            # Create metadata
            metadata = {
                'samples': list(data.columns),
                'features': list(data.index),
                'data_type': omics_type,
                'file_path': file_path
            }
            
            # Run validation
            result = self.validation_pipeline.run_validation_pipeline(
                data, omics_type, metadata
            )
            
            # Print results
            self._print_validation_results(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating file: {e}")
            return {'error': str(e)}
    
    def integrate_data_files(self, file_paths: List[str], omics_types: List[str], 
                           integration_method: str = 'concatenation') -> Dict[str, Any]:
        """Integrate multiple data files."""
        logger.info(f"Integrating {len(file_paths)} data files...")
        
        try:
            # Load all data files
            omics_data = {}
            for file_path, omics_type in zip(file_paths, omics_types):
                logger.info(f"Loading {file_path} as {omics_type}...")
                data = pd.read_csv(file_path, index_col=0)
                omics_data[omics_type] = data
            
            # Perform integration
            result = self.integration_engine.integrate_omics_data(
                omics_data, method=integration_method
            )
            
            # Perform additional analyses
            if result.integrated_data is not None:
                # Clustering
                clusters = self.integration_engine.perform_clustering(
                    result.integrated_data, method='kmeans', n_clusters=3
                )
                result.sample_clusters = clusters
                
                # Dimensionality reduction
                reduced_data = self.integration_engine.perform_dimensionality_reduction(
                    result.integrated_data, method='pca', n_components=2
                )
                result.reduced_data = reduced_data
            
            # Print results
            self._print_integration_results(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error integrating files: {e}")
            return {'error': str(e)}
    
    def process_data_file(self, file_path: str, omics_type: str, 
                         output_path: str = None) -> Dict[str, Any]:
        """Process a single data file."""
        logger.info(f"Processing {file_path} as {omics_type} data...")
        
        try:
            # Get processor
            processor = self.processor_factory.create_processor(omics_type)
            
            # Load data
            load_result = processor.load_data(file_path)
            
            if not load_result.success:
                logger.error(f"Failed to load data: {load_result.error_message}")
                return {'error': load_result.error_message}
            
            # Preprocess data
            preprocess_result = processor.preprocess_data(load_result.data)
            
            if not preprocess_result.success:
                logger.error(f"Failed to preprocess data: {preprocess_result.error_message}")
                return {'error': preprocess_result.error_message}
            
            # Normalize data
            field_def = self.registry.get_field(omics_type)
            if field_def.normalization_methods:
                norm_method = field_def.normalization_methods[0]
                norm_result = processor.normalize_data(preprocess_result.data, norm_method)
                
                if norm_result.success:
                    processed_data = norm_result.data
                else:
                    logger.warning(f"Normalization failed: {norm_result.error_message}")
                    processed_data = preprocess_result.data
            else:
                processed_data = preprocess_result.data
            
            # Save processed data
            if output_path:
                processed_data.to_csv(output_path)
                logger.info(f"Processed data saved to {output_path}")
            
            # Print results
            self._print_processing_results(load_result, preprocess_result, processed_data)
            
            return {
                'success': True,
                'processed_data': processed_data,
                'quality_metrics': load_result.quality_metrics
            }
            
        except Exception as e:
            logger.error(f"Error processing file: {e}")
            return {'error': str(e)}
    
    def list_omics_fields(self):
        """List all available omics fields."""
        logger.info("Available omics fields:")
        
        categories = self.registry.get_categories()
        for category in categories:
            fields = self.registry.get_fields_by_category(category)
            print(f"\n{category}:")
            for field in fields:
                print(f"  - {field.full_name} ({field.name}): {field.description}")
    
    def get_omics_field_info(self, omics_type: str):
        """Get detailed information about a specific omics field."""
        field = self.registry.get_field(omics_type)
        
        if not field:
            print(f"Omics field '{omics_type}' not found")
            return
        
        print(f"\n{field.full_name} ({field.name})")
        print("=" * 50)
        print(f"Description: {field.description}")
        print(f"Category: {field.category}")
        print(f"Data Type: {field.data_type.value}")
        print(f"Complexity: {field.complexity_level}")
        print(f"Maturity: {field.maturity_level}")
        print(f"Clinical Relevance: {field.clinical_relevance}")
        
        print(f"\nPrimary Entities: {', '.join(field.primary_entities)}")
        print(f"Measurement Units: {', '.join(field.measurement_units)}")
        print(f"Data Formats: {', '.join(field.data_formats)}")
        
        print(f"\nPreprocessing Steps: {', '.join(field.preprocessing_steps)}")
        print(f"Normalization Methods: {', '.join(field.normalization_methods)}")
        print(f"Quality Control Metrics: {', '.join(field.quality_control_metrics)}")
        
        print(f"\nSupported Analyses: {', '.join(field.supported_analyses)}")
        print(f"Integration Methods: {', '.join(field.integration_methods)}")
        print(f"Visualization Types: {', '.join(field.visualization_types)}")
        
        print(f"\nRequired Tools: {', '.join(field.required_tools)}")
        print(f"Data Sources: {', '.join(field.data_sources)}")
    
    def _print_demonstration_summary(self, results: Dict[str, Any]):
        """Print demonstration summary."""
        print("\n" + "="*80)
        print("COMPREHENSIVE OMICS DEMONSTRATION SUMMARY")
        print("="*80)
        
        if 'example_data' in results:
            print(f"Generated data for {len(results['example_data'])} omics types")
        
        if 'processing' in results:
            successful = sum(1 for r in results['processing'].values() if r.get('status') == 'success')
            print(f"Successfully processed {successful} omics types")
        
        if 'validation' in results:
            passed = sum(1 for r in results['validation'].values() if r.get('overall_status') == 'PASSED')
            print(f"Validation passed for {passed} omics types")
        
        if 'integration' in results:
            print(f"Tested {len(results['integration'])} integration methods")
        
        if 'metadata' in results and 'summary' in results['metadata']:
            summary = results['metadata']['summary']
            print(f"Metadata: {summary['sample_metadata_count']} samples, {summary['feature_metadata_count']} features")
        
        print("\nTo launch the interactive dashboard, run:")
        print("python run_omics_analysis.py --dashboard")
    
    def _print_validation_results(self, result: Dict[str, Any]):
        """Print validation results."""
        print("\n" + "="*50)
        print("VALIDATION RESULTS")
        print("="*50)
        
        print(f"Overall Status: {result['overall_status']}")
        print(f"Overall Score: {result['overall_score']:.3f}")
        
        if 'validation_result' in result:
            val_result = result['validation_result']
            print(f"Validation Score: {val_result.validation_score:.3f}")
            print(f"Errors: {len(val_result.errors)}")
            print(f"Warnings: {len(val_result.warnings)}")
            print(f"Recommendations: {len(val_result.recommendations)}")
        
        if 'qc_result' in result:
            qc_result = result['qc_result']
            print(f"QC Score: {qc_result.qc_score:.3f}")
            print(f"QC Status: {'PASSED' if qc_result.passed_qc else 'FAILED'}")
            print(f"Failed Samples: {len(qc_result.failed_samples)}")
            print(f"Failed Features: {len(qc_result.failed_features)}")
    
    def _print_integration_results(self, result: Any):
        """Print integration results."""
        print("\n" + "="*50)
        print("INTEGRATION RESULTS")
        print("="*50)
        
        if hasattr(result, 'integrated_data') and result.integrated_data is not None:
            print(f"Integration Method: {result.integration_method}")
            print(f"Integrated Features: {result.integrated_data.shape[0]}")
            print(f"Samples: {result.integrated_data.shape[1]}")
            
            if hasattr(result, 'quality_metrics'):
                print("Quality Metrics:")
                for metric, value in result.quality_metrics.items():
                    if isinstance(value, (int, float)):
                        print(f"  {metric}: {value:.3f}")
            
            if hasattr(result, 'sample_clusters') and result.sample_clusters is not None:
                print(f"Clusters: {len(result.sample_clusters.unique())}")
                print(f"Cluster Distribution: {result.sample_clusters.value_counts().to_dict()}")
        else:
            print("Integration failed or no integrated data available")
    
    def _print_processing_results(self, load_result: Any, preprocess_result: Any, processed_data: pd.DataFrame):
        """Print processing results."""
        print("\n" + "="*50)
        print("PROCESSING RESULTS")
        print("="*50)
        
        print(f"Data Loading: {'SUCCESS' if load_result.success else 'FAILED'}")
        if load_result.success:
            print(f"Original Shape: {load_result.data.shape}")
        
        print(f"Preprocessing: {'SUCCESS' if preprocess_result.success else 'FAILED'}")
        if preprocess_result.success:
            print(f"Processed Shape: {preprocess_result.data.shape}")
        
        print(f"Final Shape: {processed_data.shape}")
        print(f"Missing Values: {processed_data.isnull().sum().sum()}")
        print(f"Data Range: [{processed_data.min().min():.3f}, {processed_data.max().max():.3f}]")


def main():
    """Main function for command-line interface."""
    parser = argparse.ArgumentParser(
        description="Comprehensive Omics Analysis Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_omics_analysis.py --demo                    # Run demonstration
  python run_omics_analysis.py --dashboard              # Launch dashboard
  python run_omics_analysis.py --list-fields            # List all omics fields
  python run_omics_analysis.py --field-info genomics    # Get field information
  python run_omics_analysis.py --validate data.csv --type transcriptomics
  python run_omics_analysis.py --integrate file1.csv file2.csv --types transcriptomics proteomics
  python run_omics_analysis.py --process data.csv --type metabolomics --output processed.csv
        """
    )
    
    # Main actions
    parser.add_argument('--demo', action='store_true', 
                       help='Run comprehensive demonstration')
    parser.add_argument('--dashboard', action='store_true',
                       help='Launch interactive dashboard')
    parser.add_argument('--list-fields', action='store_true',
                       help='List all available omics fields')
    parser.add_argument('--field-info', type=str, metavar='OMICS_TYPE',
                       help='Get detailed information about a specific omics field')
    
    # Data processing
    parser.add_argument('--validate', type=str, metavar='FILE',
                       help='Validate a data file')
    parser.add_argument('--type', type=str, metavar='OMICS_TYPE',
                       help='Specify omics type for data processing')
    parser.add_argument('--process', type=str, metavar='FILE',
                       help='Process a data file')
    parser.add_argument('--output', type=str, metavar='FILE',
                       help='Output file for processed data')
    
    # Integration
    parser.add_argument('--integrate', nargs='+', metavar='FILE',
                       help='Integrate multiple data files')
    parser.add_argument('--types', nargs='+', metavar='OMICS_TYPE',
                       help='Specify omics types for integration')
    parser.add_argument('--method', type=str, default='concatenation',
                       choices=['concatenation', 'pca', 'ica', 'cca', 'pls', 'network'],
                       help='Integration method (default: concatenation)')
    
    # Dashboard options
    parser.add_argument('--port', type=int, default=8050,
                       help='Port for dashboard (default: 8050)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode for dashboard')
    
    args = parser.parse_args()
    
    # Initialize runner
    runner = OmicsAnalysisRunner()
    
    # Execute actions
    if args.demo:
        runner.run_demonstration()
    
    elif args.dashboard:
        runner.launch_dashboard(port=args.port, debug=args.debug)
    
    elif args.list_fields:
        runner.list_omics_fields()
    
    elif args.field_info:
        runner.get_omics_field_info(args.field_info)
    
    elif args.validate:
        if not args.type:
            print("Error: --type is required for validation")
            sys.exit(1)
        runner.validate_data_file(args.validate, args.type)
    
    elif args.process:
        if not args.type:
            print("Error: --type is required for processing")
            sys.exit(1)
        runner.process_data_file(args.process, args.type, args.output)
    
    elif args.integrate:
        if not args.types:
            print("Error: --types is required for integration")
            sys.exit(1)
        if len(args.integrate) != len(args.types):
            print("Error: Number of files must match number of types")
            sys.exit(1)
        runner.integrate_data_files(args.integrate, args.types, args.method)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
