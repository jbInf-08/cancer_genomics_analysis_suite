"""
Comprehensive Omics Example

This module demonstrates the complete omics analysis pipeline with all implemented
omics fields, from data loading and validation to integration and visualization.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path
import json

from .omics_registry import get_omics_registry, OmicsFieldRegistry
from .omics_processor import get_omics_processor_factory, OmicsProcessorFactory
from .omics_metadata import get_omics_metadata_manager, OmicsMetadataManager
from .omics_integration import get_omics_integration_engine, OmicsIntegrationEngine
from .omics_validation import get_omics_validation_pipeline, OmicsValidationPipeline
from .omics_dashboard import create_comprehensive_omics_dashboard

logger = logging.getLogger(__name__)


class ComprehensiveOmicsExample:
    """Comprehensive example demonstrating all omics functionality."""
    
    def __init__(self):
        """Initialize the comprehensive omics example."""
        self.registry = get_omics_registry()
        self.processor_factory = get_omics_processor_factory()
        self.metadata_manager = get_omics_metadata_manager()
        self.integration_engine = get_omics_integration_engine()
        self.validation_pipeline = get_omics_validation_pipeline()
        
        # Example data storage
        self.example_data: Dict[str, pd.DataFrame] = {}
        self.processed_data: Dict[str, pd.DataFrame] = {}
        self.integration_results: Dict[str, Any] = {}
        self.validation_results: Dict[str, Any] = {}
    
    def generate_example_data(self) -> Dict[str, pd.DataFrame]:
        """Generate example data for all omics types."""
        logger.info("Generating example data for all omics types...")
        
        # Common samples
        samples = [f"sample_{i:03d}" for i in range(50)]
        
        # Generate data for each omics type
        for omics_type, field_def in self.registry.get_all_fields().items():
            logger.info(f"Generating example data for {omics_type}...")
            
            if field_def.data_type.value == 'sequence':
                # Generate sequence-like data (e.g., coverage, quality scores)
                n_features = 1000
                features = [f"{omics_type}_feature_{i:04d}" for i in range(n_features)]
                data = np.random.poisson(50, (n_features, len(samples)))
                
            elif field_def.data_type.value == 'expression':
                # Generate expression-like data
                n_features = 2000
                features = [f"{omics_type}_gene_{i:04d}" for i in range(n_features)]
                # Log-normal distribution for expression data
                data = np.random.lognormal(mean=5, sigma=1, size=(n_features, len(samples)))
                
            elif field_def.data_type.value == 'abundance':
                # Generate abundance-like data
                n_features = 500
                features = [f"{omics_type}_protein_{i:04d}" for i in range(n_features)]
                # Normal distribution for abundance data
                data = np.random.normal(1000, 200, size=(n_features, len(samples)))
                data = np.abs(data)  # Ensure positive values
                
            elif field_def.data_type.value == 'metabolite':
                # Generate metabolite-like data
                n_features = 200
                features = [f"{omics_type}_metabolite_{i:04d}" for i in range(n_features)]
                # Log-normal distribution for metabolite data
                data = np.random.lognormal(mean=3, sigma=1, size=(n_features, len(samples)))
                
            elif field_def.data_type.value == 'modification':
                # Generate modification-like data (e.g., methylation)
                n_features = 10000
                features = [f"{omics_type}_site_{i:05d}" for i in range(n_features)]
                # Beta distribution for modification data
                data = np.random.beta(2, 2, size=(n_features, len(samples)))
                
            elif field_def.data_type.value == 'interaction':
                # Generate interaction-like data
                n_features = 100
                features = [f"{omics_type}_interaction_{i:03d}" for i in range(n_features)]
                # Binary interaction data
                data = np.random.binomial(1, 0.3, size=(n_features, len(samples)))
                
            elif field_def.data_type.value == 'network':
                # Generate network-like data
                n_features = 50
                features = [f"{omics_type}_node_{i:03d}" for i in range(n_features)]
                # Network connectivity data
                data = np.random.exponential(1, size=(n_features, len(samples)))
                
            elif field_def.data_type.value == 'phenotype':
                # Generate phenotype-like data
                n_features = 100
                features = [f"{omics_type}_trait_{i:03d}" for i in range(n_features)]
                # Normal distribution for phenotype data
                data = np.random.normal(0, 1, size=(n_features, len(samples)))
                
            elif field_def.data_type.value == 'exposure':
                # Generate exposure-like data
                n_features = 50
                features = [f"{omics_type}_exposure_{i:03d}" for i in range(n_features)]
                # Log-normal distribution for exposure data
                data = np.random.lognormal(mean=2, sigma=1, size=(n_features, len(samples)))
                
            elif field_def.data_type.value == 'flux':
                # Generate flux-like data
                n_features = 100
                features = [f"{omics_type}_flux_{i:03d}" for i in range(n_features)]
                # Normal distribution for flux data
                data = np.random.normal(0, 1, size=(n_features, len(samples)))
                
            elif field_def.data_type.value == 'kinetic':
                # Generate kinetic-like data
                n_features = 50
                features = [f"{omics_type}_kinetic_{i:03d}" for i in range(n_features)]
                # Exponential distribution for kinetic data
                data = np.random.exponential(1, size=(n_features, len(samples)))
                
            else:
                # Default: generate random data
                n_features = 100
                features = [f"{omics_type}_feature_{i:03d}" for i in range(n_features)]
                data = np.random.normal(0, 1, size=(n_features, len(samples)))
            
            # Create DataFrame
            df = pd.DataFrame(data, index=features, columns=samples)
            
            # Add some missing values
            missing_indices = np.random.choice(df.size, size=int(df.size * 0.05), replace=False)
            df.values.flat[missing_indices] = np.nan
            
            self.example_data[omics_type] = df
        
        logger.info(f"Generated example data for {len(self.example_data)} omics types")
        return self.example_data
    
    def demonstrate_data_processing(self) -> Dict[str, Any]:
        """Demonstrate data processing for all omics types."""
        logger.info("Demonstrating data processing...")
        
        processing_results = {}
        
        for omics_type, data in self.example_data.items():
            logger.info(f"Processing {omics_type} data...")
            
            try:
                # Get processor
                processor = self.processor_factory.create_processor(omics_type)
                
                # Load data (simulate file loading)
                load_result = processor.load_data(f"{omics_type}_data.csv", data=data)
                
                if load_result.success:
                    # Preprocess data
                    preprocess_result = processor.preprocess_data(load_result.data)
                    
                    if preprocess_result.success:
                        # Normalize data
                        field_def = self.registry.get_field(omics_type)
                        if field_def.normalization_methods:
                            norm_method = field_def.normalization_methods[0]
                            norm_result = processor.normalize_data(preprocess_result.data, norm_method)
                            
                            if norm_result.success:
                                self.processed_data[omics_type] = norm_result.data
                                processing_results[omics_type] = {
                                    'status': 'success',
                                    'original_shape': data.shape,
                                    'processed_shape': norm_result.data.shape,
                                    'quality_metrics': norm_result.quality_metrics
                                }
                            else:
                                processing_results[omics_type] = {
                                    'status': 'normalization_failed',
                                    'error': norm_result.error_message
                                }
                        else:
                            self.processed_data[omics_type] = preprocess_result.data
                            processing_results[omics_type] = {
                                'status': 'success',
                                'original_shape': data.shape,
                                'processed_shape': preprocess_result.data.shape,
                                'quality_metrics': preprocess_result.quality_metrics
                            }
                    else:
                        processing_results[omics_type] = {
                            'status': 'preprocessing_failed',
                            'error': preprocess_result.error_message
                        }
                else:
                    processing_results[omics_type] = {
                        'status': 'loading_failed',
                        'error': load_result.error_message
                    }
                    
            except Exception as e:
                logger.error(f"Error processing {omics_type}: {e}")
                processing_results[omics_type] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        logger.info(f"Processing completed for {len(processing_results)} omics types")
        return processing_results
    
    def demonstrate_validation(self) -> Dict[str, Any]:
        """Demonstrate validation pipeline for all omics types."""
        logger.info("Demonstrating validation pipeline...")
        
        validation_results = {}
        
        for omics_type, data in self.example_data.items():
            logger.info(f"Validating {omics_type} data...")
            
            try:
                # Create sample metadata
                sample_metadata = {
                    'samples': list(data.columns),
                    'features': list(data.index),
                    'data_type': omics_type,
                    'platform': f"{omics_type}_platform",
                    'protocol': f"{omics_type}_protocol"
                }
                
                # Run validation pipeline
                result = self.validation_pipeline.run_validation_pipeline(
                    data, omics_type, sample_metadata
                )
                
                validation_results[omics_type] = result
                
            except Exception as e:
                logger.error(f"Error validating {omics_type}: {e}")
                validation_results[omics_type] = {
                    'overall_status': 'ERROR',
                    'overall_score': 0.0,
                    'error': str(e)
                }
        
        logger.info(f"Validation completed for {len(validation_results)} omics types")
        return validation_results
    
    def demonstrate_integration(self) -> Dict[str, Any]:
        """Demonstrate multi-omics integration."""
        logger.info("Demonstrating multi-omics integration...")
        
        integration_results = {}
        
        # Select a subset of omics types for integration
        core_omics = ['genomics', 'transcriptomics', 'proteomics', 'metabolomics', 'epigenomics']
        available_omics = [omics for omics in core_omics if omics in self.processed_data]
        
        if len(available_omics) < 2:
            logger.warning("Insufficient processed data for integration")
            return integration_results
        
        # Test different integration methods
        integration_methods = ['concatenation', 'pca', 'ica']
        
        for method in integration_methods:
            logger.info(f"Testing {method} integration...")
            
            try:
                # Prepare data for integration
                integration_data = {omics: self.processed_data[omics] for omics in available_omics}
                
                # Perform integration
                result = self.integration_engine.integrate_omics_data(
                    integration_data, method=method
                )
                
                integration_results[method] = result
                
                # Perform clustering
                if result.integrated_data is not None:
                    clusters = self.integration_engine.perform_clustering(
                        result.integrated_data, method='kmeans', n_clusters=3
                    )
                    result.sample_clusters = clusters
                    
                    # Perform dimensionality reduction
                    reduced_data = self.integration_engine.perform_dimensionality_reduction(
                        result.integrated_data, method='pca', n_components=2
                    )
                    result.reduced_data = reduced_data
                
            except Exception as e:
                logger.error(f"Error in {method} integration: {e}")
                integration_results[method] = {
                    'error': str(e),
                    'success': False
                }
        
        logger.info(f"Integration completed with {len(integration_results)} methods")
        return integration_results
    
    def demonstrate_metadata_management(self) -> Dict[str, Any]:
        """Demonstrate metadata management."""
        logger.info("Demonstrating metadata management...")
        
        metadata_results = {}
        
        # Create sample metadata
        sample_metadata_df = pd.DataFrame({
            'sample_id': [f"sample_{i:03d}" for i in range(50)],
            'sample_type': np.random.choice(['tumor', 'normal'], 50),
            'patient_id': [f"patient_{i:03d}" for i in range(50)],
            'age': np.random.normal(60, 15, 50),
            'sex': np.random.choice(['M', 'F'], 50),
            'disease_status': np.random.choice(['cancer', 'control'], 50),
            'batch_id': np.random.choice(['batch_1', 'batch_2', 'batch_3'], 50)
        })
        
        sample_metadata = self.metadata_manager.create_sample_metadata_from_dataframe(sample_metadata_df)
        
        for sample_id, metadata in sample_metadata.items():
            self.metadata_manager.add_sample_metadata(metadata)
        
        metadata_results['sample_metadata'] = {
            'count': len(sample_metadata),
            'samples': list(sample_metadata.keys())[:5]  # Show first 5
        }
        
        # Create feature metadata for each omics type
        for omics_type, data in self.example_data.items():
            feature_metadata_df = pd.DataFrame({
                'feature_id': list(data.index),
                'feature_name': [f"{omics_type}_{i}" for i in range(len(data.index))],
                'feature_type': omics_type,
                'chromosome': np.random.choice(['chr1', 'chr2', 'chr3', 'chrX', 'chrY'], len(data.index)),
                'start_position': np.random.randint(1, 1000000, len(data.index)),
                'end_position': np.random.randint(1000000, 2000000, len(data.index)),
                'expression_level': data.mean(axis=1),
                'expression_variance': data.var(axis=1)
            })
            
            feature_metadata = self.metadata_manager.create_feature_metadata_from_dataframe(
                feature_metadata_df, omics_type
            )
            
            for feature_id, metadata in feature_metadata.items():
                self.metadata_manager.add_feature_metadata(omics_type, metadata)
            
            metadata_results[f'{omics_type}_feature_metadata'] = {
                'count': len(feature_metadata),
                'features': list(feature_metadata.keys())[:5]  # Show first 5
            }
        
        # Create experiment metadata
        experiment_metadata_df = pd.DataFrame({
            'experiment_id': ['exp_001'],
            'experiment_name': ['Comprehensive Omics Analysis'],
            'experiment_description': ['Multi-omics analysis demonstration'],
            'experiment_type': ['multi_omics'],
            'study_id': ['study_001'],
            'study_name': ['Cancer Genomics Study'],
            'data_types': [list(self.example_data.keys())],
            'sample_count': [50],
            'feature_count': [sum(data.shape[0] for data in self.example_data.values())]
        })
        
        experiment_metadata = self.metadata_manager.create_experiment_metadata_from_dataframe(experiment_metadata_df)
        
        for exp_id, metadata in experiment_metadata.items():
            self.metadata_manager.add_experiment_metadata(metadata)
        
        metadata_results['experiment_metadata'] = {
            'count': len(experiment_metadata),
            'experiments': list(experiment_metadata.keys())
        }
        
        # Get metadata summary
        metadata_summary = self.metadata_manager.get_metadata_summary()
        metadata_results['summary'] = metadata_summary
        
        logger.info("Metadata management demonstration completed")
        return metadata_results
    
    def generate_comprehensive_report(self) -> str:
        """Generate a comprehensive report of all demonstrations."""
        report = f"""
# Comprehensive Omics Analysis Report
Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview
This report demonstrates the comprehensive omics analysis capabilities of the Cancer Genomics Analysis Suite,
including support for {len(self.registry.get_all_fields())} different omics fields.

## Omics Fields Supported
"""
        
        # Add omics fields by category
        categories = self.registry.get_categories()
        for category in categories:
            fields = self.registry.get_fields_by_category(category)
            report += f"\n### {category}\n"
            for field in fields:
                report += f"- **{field.full_name}** ({field.name}): {field.description}\n"
        
        report += f"""
## Data Generation Results
- Generated example data for {len(self.example_data)} omics types
- Total features: {sum(data.shape[0] for data in self.example_data.values())}
- Total samples: {len(list(self.example_data.values())[0].columns) if self.example_data else 0}

## Data Processing Results
"""
        
        if hasattr(self, 'processed_data'):
            report += f"- Successfully processed {len(self.processed_data)} omics types\n"
            for omics_type, data in self.processed_data.items():
                report += f"  - {omics_type}: {data.shape[0]} features, {data.shape[1]} samples\n"
        
        report += f"""
## Validation Results
"""
        
        if hasattr(self, 'validation_results'):
            passed_count = sum(1 for result in self.validation_results.values() 
                             if result.get('overall_status') == 'PASSED')
            report += f"- Validation passed for {passed_count}/{len(self.validation_results)} omics types\n"
        
        report += f"""
## Integration Results
"""
        
        if hasattr(self, 'integration_results'):
            report += f"- Tested {len(self.integration_results)} integration methods\n"
            for method, result in self.integration_results.items():
                if hasattr(result, 'integrated_data') and result.integrated_data is not None:
                    report += f"  - {method}: {result.integrated_data.shape[0]} features, {result.integrated_data.shape[1]} samples\n"
        
        report += f"""
## Metadata Management Results
"""
        
        if hasattr(self, 'metadata_manager'):
            summary = self.metadata_manager.get_metadata_summary()
            report += f"- Sample metadata: {summary['sample_metadata_count']} records\n"
            report += f"- Feature metadata: {summary['feature_metadata_count']} records\n"
            report += f"- Experiment metadata: {summary['experiment_metadata_count']} records\n"
        
        report += f"""
## Technical Specifications
- Registry: {len(self.registry.get_all_fields())} omics fields defined
- Processors: {len(self.processor_factory.get_available_processors())} available processors
- Integration methods: 6 different methods supported
- Validation pipeline: Comprehensive validation and QC
- Dashboard: Interactive web-based interface

## Recommendations
1. Use the comprehensive dashboard for interactive analysis
2. Validate all data before processing
3. Choose appropriate integration methods based on data characteristics
4. Maintain comprehensive metadata for reproducibility
5. Use quality control metrics to assess data reliability

## Conclusion
The Cancer Genomics Analysis Suite provides comprehensive support for all major omics fields,
enabling researchers to perform sophisticated multi-omics analyses with robust validation,
quality control, and integration capabilities.
"""
        
        return report
    
    def run_complete_demonstration(self) -> Dict[str, Any]:
        """Run the complete demonstration of all omics functionality."""
        logger.info("Starting comprehensive omics demonstration...")
        
        results = {}
        
        try:
            # Step 1: Generate example data
            logger.info("Step 1: Generating example data...")
            results['example_data'] = self.generate_example_data()
            
            # Step 2: Demonstrate data processing
            logger.info("Step 2: Demonstrating data processing...")
            results['processing'] = self.demonstrate_data_processing()
            
            # Step 3: Demonstrate validation
            logger.info("Step 3: Demonstrating validation...")
            results['validation'] = self.demonstrate_validation()
            
            # Step 4: Demonstrate metadata management
            logger.info("Step 4: Demonstrating metadata management...")
            results['metadata'] = self.demonstrate_metadata_management()
            
            # Step 5: Demonstrate integration
            logger.info("Step 5: Demonstrating integration...")
            results['integration'] = self.demonstrate_integration()
            
            # Step 6: Generate comprehensive report
            logger.info("Step 6: Generating comprehensive report...")
            results['report'] = self.generate_comprehensive_report()
            
            logger.info("Comprehensive omics demonstration completed successfully!")
            
        except Exception as e:
            logger.error(f"Error in comprehensive demonstration: {e}")
            results['error'] = str(e)
        
        return results


def run_omics_demonstration():
    """Run the complete omics demonstration."""
    example = ComprehensiveOmicsExample()
    return example.run_complete_demonstration()


def launch_omics_dashboard():
    """Launch the comprehensive omics dashboard."""
    dashboard = create_comprehensive_omics_dashboard()
    dashboard.run(debug=True, port=8050)


if __name__ == "__main__":
    # Run the demonstration
    print("Running comprehensive omics demonstration...")
    results = run_omics_demonstration()
    
    # Print summary
    print("\n" + "="*80)
    print("DEMONSTRATION SUMMARY")
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
    
    if 'report' in results:
        print("\nComprehensive report generated!")
        print("Report preview:")
        print(results['report'][:500] + "...")
    
    print("\nTo launch the interactive dashboard, run:")
    print("python -c 'from omics_example import launch_omics_dashboard; launch_omics_dashboard()'")
