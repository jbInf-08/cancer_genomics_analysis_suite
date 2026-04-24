"""
Demo Usage Script for Comprehensive Data Collection System

This script demonstrates how to use the comprehensive data collection system
to gather data from multiple biomedical sources.
"""

import json
from pathlib import Path
from data_collection.run_data_collection import ComprehensiveDataCollector


def demo_basic_usage():
    """Demonstrate basic usage of the data collection system."""
    print("="*60)
    print("COMPREHENSIVE DATA COLLECTION SYSTEM - DEMO")
    print("="*60)
    
    # Initialize the comprehensive data collector
    collector = ComprehensiveDataCollector(
        output_dir="data/external_sources",
        config_file="data_collection/config.json",
        max_workers=2,
        log_level="INFO"
    )
    
    print("\n1. Available Data Sources:")
    print("-" * 30)
    sources = collector.get_available_sources()
    print(f"Total sources available: {len(sources)}")
    
    # Show first 5 sources
    for i, source in enumerate(sources[:5]):
        print(f"  {i+1}. {source['id'].upper()}: {source['description']}")
    
    if len(sources) > 5:
        print(f"  ... and {len(sources) - 5} more sources")
    
    return collector


def demo_single_source_collection(collector):
    """Demonstrate single source data collection."""
    print("\n2. Single Source Collection Demo:")
    print("-" * 40)
    
    # Collect from PubMed
    print("Collecting literature data from PubMed...")
    try:
        results = collector.collect_from_single_source(
            source_id="pubmed",
            data_type="publications",
            search_term="cancer biomarkers",
            max_results=5
        )
        
        if results.get('success', False):
            print("✓ PubMed collection successful!")
            summary = results.get('summary', {})
            print(f"  - Files created: {summary.get('files_created', 0)}")
            print(f"  - Articles collected: {summary.get('samples_collected', 0)}")
        else:
            print("✗ PubMed collection failed")
            print(f"  Error: {results.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"✗ PubMed collection failed with exception: {e}")
    
    # Collect from Kaggle
    print("\nCollecting cancer datasets from Kaggle...")
    try:
        results = collector.collect_from_single_source(
            source_id="kaggle",
            data_type="cancer",
            max_datasets=3
        )
        
        if results.get('success', False):
            print("✓ Kaggle collection successful!")
            summary = results.get('summary', {})
            print(f"  - Files created: {summary.get('files_created', 0)}")
            print(f"  - Datasets collected: {summary.get('samples_collected', 0)}")
        else:
            print("✗ Kaggle collection failed")
            print(f"  Error: {results.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"✗ Kaggle collection failed with exception: {e}")


def demo_multi_source_collection(collector):
    """Demonstrate multi-source data collection."""
    print("\n3. Multi-Source Collection Demo:")
    print("-" * 40)
    
    # Define collection plan
    collection_plan = {
        "cosmic": {
            "data_type": "mutations",
            "gene_list": ["TP53", "BRCA1", "EGFR"],
            "cancer_type": "breast"
        },
        "geo": {
            "search_term": "breast cancer",
            "data_type": "expression",
            "max_datasets": 2
        }
    }
    
    print("Collecting from multiple sources...")
    print("Sources: COSMIC (mutations), GEO (expression)")
    
    try:
        results = collector.collect_from_specific_sources(collection_plan)
        
        print(f"\n✓ Multi-source collection completed!")
        print(f"  - Total sources: {results.get('total_sources', 0)}")
        print(f"  - Successful: {results.get('successful_sources', 0)}")
        print(f"  - Failed: {results.get('failed_sources', 0)}")
        print(f"  - Total files created: {results.get('total_files_created', 0)}")
        print(f"  - Total samples collected: {results.get('total_samples_collected', 0)}")
        
        # Show individual source results
        print("\nIndividual source results:")
        for source_id, source_result in results.get('source_results', {}).items():
            status = "✓" if source_result.get('success', False) else "✗"
            files = source_result.get('summary', {}).get('files_created', 0)
            samples = source_result.get('summary', {}).get('samples_collected', 0)
            print(f"  {status} {source_id}: {files} files, {samples} samples")
    
    except Exception as e:
        print(f"✗ Multi-source collection failed: {e}")


def demo_comprehensive_collection(collector):
    """Demonstrate comprehensive collection from all sources."""
    print("\n4. Comprehensive Collection Demo:")
    print("-" * 40)
    
    # Note: This would collect from ALL sources, which might take a long time
    # For demo purposes, we'll limit to a few sources
    print("Note: Comprehensive collection from all sources would take a long time.")
    print("For demo purposes, we'll show how to run it with limited sources.")
    
    # Example of how to run comprehensive collection with specific sources
    try:
        results = collector.run_comprehensive_collection(
            sources=["tcga", "cosmic", "pubmed"],  # Limit to 3 sources for demo
            data_types=["gene_expression", "mutations", "publications"],
            cancer_types=["BRCA", "LUAD"]
        )
        
        print("✓ Comprehensive collection completed!")
        collector.print_collection_summary(results)
    
    except Exception as e:
        print(f"✗ Comprehensive collection failed: {e}")


def demo_data_exploration():
    """Demonstrate exploring collected data."""
    print("\n5. Data Exploration Demo:")
    print("-" * 30)
    
    data_dir = Path("data/external_sources")
    
    if not data_dir.exists():
        print("No data directory found. Run collection first.")
        return
    
    print("Exploring collected data...")
    
    # Find all CSV files
    csv_files = list(data_dir.rglob("*.csv"))
    print(f"Found {len(csv_files)} CSV files:")
    
    for csv_file in csv_files[:5]:  # Show first 5 files
        file_size = csv_file.stat().st_size
        print(f"  - {csv_file.name} ({file_size} bytes)")
    
    if len(csv_files) > 5:
        print(f"  ... and {len(csv_files) - 5} more files")
    
    # Find metadata files
    metadata_files = list(data_dir.rglob("*metadata.json"))
    print(f"\nFound {len(metadata_files)} metadata files:")
    
    for metadata_file in metadata_files:
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            collector_name = metadata.get('collector_name', 'Unknown')
            files_created = len(metadata.get('files_created', []))
            samples_collected = metadata.get('samples_collected', 0)
            
            print(f"  - {collector_name}: {files_created} files, {samples_collected} samples")
        
        except Exception as e:
            print(f"  - {metadata_file.name}: Error reading metadata")


def main():
    """Main demo function."""
    try:
        # Initialize collector
        collector = demo_basic_usage()
        
        # Run demos
        demo_single_source_collection(collector)
        demo_multi_source_collection(collector)
        demo_comprehensive_collection(collector)
        demo_data_exploration()
        
        print("\n" + "="*60)
        print("DEMO COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\nNext steps:")
        print("1. Check the 'data/external_sources' directory for collected data")
        print("2. Review the logs in 'data/external_sources/logs' for detailed information")
        print("3. Customize the configuration in 'data_collection/config.json'")
        print("4. Run comprehensive collection with: python -m data_collection.run_data_collection --comprehensive")
        print("5. Test individual collectors with: python -m data_collection.test_all_collectors")
        
    except Exception as e:
        print(f"\n✗ Demo failed with error: {e}")
        print("Please check your configuration and try again.")


if __name__ == "__main__":
    main()
