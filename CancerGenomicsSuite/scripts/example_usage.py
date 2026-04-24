#!/usr/bin/env python3
"""
Example Usage Script for Auto-Generation

This script demonstrates how to use the auto-generation scripts
programmatically and provides examples for common use cases.

Author: Cancer Genomics Analysis Suite
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.setup_auto_generation import AutoGenerationSetup
from scripts.generate_blast_databases import BlastDatabaseGenerator
from scripts.generate_mock_data import MockDataGenerator, MockDataConfig


def example_basic_setup():
    """Example: Basic setup and data generation."""
    print("=== Basic Setup Example ===")
    
    # Initialize setup manager
    setup = AutoGenerationSetup()
    
    # Check dependencies
    deps = setup.check_dependencies()
    print(f"Dependencies check: {deps}")
    
    # Run full setup
    success = setup.run_full_setup()
    print(f"Setup completed: {success}")


def example_custom_blast_databases():
    """Example: Generate custom BLAST databases."""
    print("=== Custom BLAST Databases Example ===")
    
    # Initialize generator
    generator = BlastDatabaseGenerator(output_dir="custom_blast_db")
    
    # Generate specific databases
    databases = generator.generate_all_databases(use_api=False, use_mock=True)
    print(f"Generated databases: {list(databases.keys())}")
    
    # Create custom database from FASTA file
    # custom_db = generator.create_custom_database(
    #     "my_sequences.fasta", 
    #     "custom_db", 
    #     "nucl", 
    #     "Custom gene sequences"
    # )


def example_custom_mock_data():
    """Example: Generate custom mock data."""
    print("=== Custom Mock Data Example ===")
    
    # Create custom configuration
    config = MockDataConfig(
        num_patients=100,
        num_samples=120,
        num_genes=1000,
        cancer_types=["BRCA", "NSCLC"],
        output_dir="custom_mock_data"
    )
    
    # Initialize generator
    generator = MockDataGenerator(config)
    
    # Generate specific data types
    clinical_file = generator.generate_clinical_data()
    expression_file = generator.generate_expression_data()
    mutation_file = generator.generate_mutation_data()
    
    print(f"Generated files:")
    print(f"  Clinical: {clinical_file}")
    print(f"  Expression: {expression_file}")
    print(f"  Mutations: {mutation_file}")


def example_integration_with_pipeline():
    """Example: Integration with existing BLAST pipeline."""
    print("=== Pipeline Integration Example ===")
    
    try:
        from tasks.blast_pipeline import BlastPipeline, BlastConfig
        
        # Configure BLAST pipeline
        config = BlastConfig(
            database_path="blast_databases/cancer_genes",
            program="blastn",
            evalue=1e-5,
            max_target_seqs=10
        )
        
        # Initialize pipeline
        pipeline = BlastPipeline(config)
        
        # Example query sequence
        query_sequence = "ATGCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG"
        
        # Run BLAST analysis
        output_file = pipeline.run_blast(query_sequence)
        print(f"BLAST results saved to: {output_file}")
        
        # Parse results
        results = pipeline.parse_blast_results(output_file)
        print(f"Found {len(results)} hits")
        
        # Get top hits
        top_hits = pipeline.get_top_hits(5)
        for i, hit in enumerate(top_hits, 1):
            print(f"  {i}. {hit.subject_id} (Score: {hit.bit_score:.2f})")
            
    except ImportError as e:
        print(f"Could not import BLAST pipeline: {e}")
        print("Make sure you're running from the correct directory")


def example_batch_processing():
    """Example: Batch processing with multiple configurations."""
    print("=== Batch Processing Example ===")
    
    # Different configurations for different scenarios
    configs = [
        {
            "name": "small_dataset",
            "num_patients": 50,
            "num_samples": 60,
            "cancer_types": ["BRCA"]
        },
        {
            "name": "medium_dataset", 
            "num_patients": 200,
            "num_samples": 240,
            "cancer_types": ["BRCA", "NSCLC"]
        },
        {
            "name": "large_dataset",
            "num_patients": 500,
            "num_samples": 600,
            "cancer_types": ["BRCA", "NSCLC", "COAD", "PRAD"]
        }
    ]
    
    for config_data in configs:
        print(f"\nGenerating {config_data['name']}...")
        
        # Create configuration
        config = MockDataConfig(
            num_patients=config_data["num_patients"],
            num_samples=config_data["num_samples"],
            cancer_types=config_data["cancer_types"],
            output_dir=f"data_{config_data['name']}"
        )
        
        # Generate data
        generator = MockDataGenerator(config)
        files = generator.generate_all_data()
        
        print(f"  Generated {len(files)} files for {config_data['name']}")


def example_data_validation():
    """Example: Validate generated data."""
    print("=== Data Validation Example ===")
    
    import pandas as pd
    import json
    
    # Check if data files exist
    data_dir = Path("data")
    if not data_dir.exists():
        print("Data directory not found. Run data generation first.")
        return
    
    # Validate clinical data
    clinical_file = data_dir / "mock_clinical_data.csv"
    if clinical_file.exists():
        df = pd.read_csv(clinical_file)
        print(f"Clinical data: {len(df)} patients")
        print(f"  Cancer types: {df['primary_diagnosis'].nunique()}")
        print(f"  Age range: {df['age'].min()}-{df['age'].max()}")
    
    # Validate expression data
    expression_file = data_dir / "mock_expression_data.csv"
    if expression_file.exists():
        df = pd.read_csv(expression_file)
        print(f"Expression data: {len(df)} records")
        print(f"  Genes: {df['gene_symbol'].nunique()}")
        print(f"  Samples: {df['sample_id'].nunique()}")
    
    # Validate mutation data
    mutation_file = data_dir / "mock_mutation_data.csv"
    if mutation_file.exists():
        df = pd.read_csv(mutation_file)
        print(f"Mutation data: {len(df)} mutations")
        print(f"  Genes: {df['gene_symbol'].nunique()}")
        print(f"  Consequence types: {df['consequence_type'].nunique()}")
    
    # Validate pathway data
    pathway_file = data_dir / "mock_pathway_data.json"
    if pathway_file.exists():
        with open(pathway_file, 'r') as f:
            data = json.load(f)
        print(f"Pathway data: {len(data['pathways'])} pathways")


def main():
    """Run all examples."""
    print("Auto-Generation Scripts - Example Usage")
    print("=" * 50)
    
    # Run examples
    try:
        example_basic_setup()
        print("\n")
        
        example_custom_blast_databases()
        print("\n")
        
        example_custom_mock_data()
        print("\n")
        
        example_integration_with_pipeline()
        print("\n")
        
        example_batch_processing()
        print("\n")
        
        example_data_validation()
        
    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
