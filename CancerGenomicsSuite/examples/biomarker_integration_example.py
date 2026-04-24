#!/usr/bin/env python3
"""
Example script demonstrating the integrated biomarker analysis system.

This script shows how to use the unified interface to perform biomarker
analysis using both CGAS and biomarker_identifier services.
"""

import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from integrations import (
    UnifiedBiomarkerInterface, 
    BiomarkerAnalysisOptions,
    discover_biomarkers_compatible,
    get_compatibility_manager
)


def create_sample_data(n_samples=100, n_features=50):
    """Create sample data for demonstration."""
    np.random.seed(42)
    
    # Create random gene expression data
    data = np.random.randn(n_samples, n_features)
    
    # Create feature names
    feature_names = [f"Gene_{i:03d}" for i in range(n_features)]
    
    # Create sample names
    sample_names = [f"Sample_{i:03d}" for i in range(n_samples)]
    
    # Create DataFrame
    df = pd.DataFrame(data, index=sample_names, columns=feature_names)
    
    # Create binary labels (disease vs control)
    labels = np.random.choice([0, 1], size=n_samples, p=[0.6, 0.4])
    
    return df, labels


def example_basic_usage():
    """Example of basic biomarker discovery."""
    print("🔬 Basic Biomarker Discovery Example")
    print("=" * 50)
    
    # Create sample data
    data, labels = create_sample_data(100, 50)
    print(f"Created dataset: {data.shape[0]} samples, {data.shape[1]} features")
    
    # Use the compatibility function for easy discovery
    try:
        biomarkers = discover_biomarkers_compatible(data, labels)
        print(f"✅ Discovered {len(biomarkers)} biomarkers")
        
        # Show top 5 biomarkers
        if biomarkers:
            print("\nTop 5 biomarkers:")
            for i, biomarker in enumerate(biomarkers[:5]):
                print(f"  {i+1}. {biomarker.get('name', 'Unknown')} "
                      f"(p-value: {biomarker.get('p_value', 'N/A'):.4f}, "
                      f"AUC: {biomarker.get('auc_score', 'N/A'):.3f})")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def example_unified_interface():
    """Example using the unified interface."""
    print("\n🔬 Unified Interface Example")
    print("=" * 50)
    
    # Create sample data
    data, labels = create_sample_data(150, 75)
    print(f"Created dataset: {data.shape[0]} samples, {data.shape[1]} features")
    
    # Create interface
    interface = UnifiedBiomarkerInterface()
    
    # Check service status
    status = interface.get_service_status()
    print(f"\nService Status:")
    for service, info in status['gateway_status'].items():
        available = "✅" if info['available'] else "❌"
        print(f"  {available} {service}: {info.get('response_time', 0):.3f}s")
    
    # Configure analysis options
    options = BiomarkerAnalysisOptions(
        p_value_threshold=0.01,
        effect_size_threshold=0.3,
        auc_threshold=0.75,
        prefer_service=None  # Auto-select
    )
    
    try:
        # Perform analysis
        results = interface.discover_biomarkers(data, labels, options)
        
        print(f"\n✅ Analysis completed using {results['metadata']['service_used']}")
        print(f"Processing time: {results['metadata']['processing_time']:.2f}s")
        print(f"Quality score: {results['metadata'].get('quality_score', 'N/A')}")
        
        # Show summary
        summary = results['summary']
        print(f"\nSummary:")
        print(f"  Total biomarkers: {summary['total_biomarkers']}")
        print(f"  Significant (p<0.05): {summary['significant_biomarkers']}")
        print(f"  High effect size: {summary['high_effect_biomarkers']}")
        print(f"  High AUC (>0.8): {summary['high_auc_biomarkers']}")
        
        # Show top biomarkers
        if results['biomarkers']:
            print(f"\nTop 3 biomarkers:")
            for i, biomarker in enumerate(results['biomarkers'][:3]):
                print(f"  {i+1}. {biomarker.get('name', 'Unknown')}")
                print(f"     p-value: {biomarker.get('p_value', 'N/A'):.6f}")
                print(f"     effect size: {biomarker.get('effect_size', 'N/A'):.3f}")
                print(f"     AUC: {biomarker.get('auc_score', 'N/A'):.3f}")
                print(f"     service: {biomarker.get('source_service', 'unknown')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def example_service_comparison():
    """Example comparing different services."""
    print("\n🔬 Service Comparison Example")
    print("=" * 50)
    
    # Create sample data
    data, labels = create_sample_data(200, 100)
    print(f"Created dataset: {data.shape[0]} samples, {data.shape[1]} features")
    
    # Create interface
    interface = UnifiedBiomarkerInterface()
    
    try:
        # Compare services
        comparison = interface.compare_services(data, labels)
        
        print(f"\n✅ Service comparison completed")
        
        # Show results from each service
        service_results = comparison['service_results']
        for service, result in service_results.items():
            biomarkers = result.get('biomarkers', [])
            print(f"\n{service.upper()} Results:")
            print(f"  Biomarkers found: {len(biomarkers)}")
            if biomarkers:
                avg_pvalue = np.mean([b.get('p_value', 1.0) for b in biomarkers])
                avg_auc = np.mean([b.get('auc_score', 0.5) for b in biomarkers])
                print(f"  Average p-value: {avg_pvalue:.6f}")
                print(f"  Average AUC: {avg_auc:.3f}")
        
        # Show comparison analysis
        comp_analysis = comparison['comparison']
        print(f"\nComparison Analysis:")
        print(f"  Services compared: {comp_analysis['services_compared']}")
        print(f"  Overlapping biomarkers: {comp_analysis['overlapping_biomarkers']}")
        print(f"  Unique biomarkers per service:")
        for service, count in comp_analysis['unique_biomarkers'].items():
            print(f"    {service}: {count}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def example_compatibility_manager():
    """Example using the compatibility manager directly."""
    print("\n🔬 Compatibility Manager Example")
    print("=" * 50)
    
    # Get compatibility manager
    manager = get_compatibility_manager()
    
    # Check available services
    available_services = manager.get_available_services()
    print(f"Available services: {available_services}")
    
    if not available_services:
        print("❌ No services available")
        return
    
    # Create sample data
    data, labels = create_sample_data(80, 40)
    print(f"Created dataset: {data.shape[0]} samples, {data.shape[1]} features")
    
    # Try each available service
    for service in available_services:
        try:
            print(f"\nTesting {service} service:")
            biomarkers = manager.discover_biomarkers(data, labels, service=service)
            print(f"  ✅ Found {len(biomarkers)} biomarkers")
            
            if biomarkers:
                best_biomarker = min(biomarkers, key=lambda x: x.get('p_value', 1.0))
                print(f"  Best biomarker: {best_biomarker.get('name', 'Unknown')} "
                      f"(p-value: {best_biomarker.get('p_value', 'N/A'):.6f})")
        
        except Exception as e:
            print(f"  ❌ Error with {service}: {e}")


def main():
    """Main function to run all examples."""
    print("🧬 Integrated Biomarker Analysis Examples")
    print("=" * 60)
    
    try:
        # Run examples
        example_basic_usage()
        example_unified_interface()
        example_service_comparison()
        example_compatibility_manager()
        
        print("\n✅ All examples completed!")
        print("\nTo use the integrated system in your own code:")
        print("1. Import: from integrations import UnifiedBiomarkerInterface")
        print("2. Create interface: interface = UnifiedBiomarkerInterface()")
        print("3. Analyze: results = interface.discover_biomarkers(data, labels)")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
