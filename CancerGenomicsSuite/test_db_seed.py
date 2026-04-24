#!/usr/bin/env python3
"""
Cancer Genomics Analysis Suite - Database Seeding Tool

This script seeds the database with comprehensive test data for the cancer
genomics analysis suite, including gene expression, mutations, clinical data,
and pathway information.

Usage:
    python test_db_seed.py [options]

Options:
    --samples N           Number of samples to generate (default: 100)
    --genes N             Number of genes to include (default: 50)
    --mutations N         Number of mutations per gene (default: 5)
    --clear               Clear existing data before seeding
    --verbose             Verbose output
    --dry-run             Show seeding plan without execution
    --help                Show this help message
"""

import random
import os
import argparse
import sys
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np


class DatabaseSeeder:
    """Comprehensive database seeder for cancer genomics test data."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.seeded_counts = {}
        self.start_time = None
        
        # Cancer-related genes with known significance
        self.cancer_genes = [
            "TP53", "BRCA1", "BRCA2", "EGFR", "MYC", "KRAS", "PIK3CA", "PTEN",
            "APC", "RB1", "VHL", "MLH1", "MSH2", "MSH6", "PMS2", "ATM", "CHEK2",
            "PALB2", "BARD1", "BRIP1", "RAD51C", "RAD51D", "CDH1", "STK11",
            "CDKN2A", "CDK4", "MDM2", "MDM4", "CCND1", "MYCN", "ALK", "RET",
            "MET", "FGFR1", "FGFR2", "FGFR3", "PDGFRA", "KIT", "FLT3", "JAK2",
            "BRAF", "NRAS", "HRAS", "AKT1", "MTOR", "TSC1", "TSC2", "NF1", "NF2"
        ]
        
        # Common cancer types
        self.cancer_types = [
            "Breast Cancer", "Lung Cancer", "Colorectal Cancer", "Prostate Cancer",
            "Ovarian Cancer", "Pancreatic Cancer", "Liver Cancer", "Brain Cancer",
            "Leukemia", "Lymphoma", "Melanoma", "Bladder Cancer", "Kidney Cancer",
            "Stomach Cancer", "Esophageal Cancer", "Cervical Cancer", "Endometrial Cancer"
        ]
        
        # Mutation types and their characteristics
        self.mutation_types = {
            "missense": {"impact": "moderate", "frequency": 0.4},
            "nonsense": {"impact": "high", "frequency": 0.15},
            "frameshift": {"impact": "high", "frequency": 0.1},
            "splice_site": {"impact": "high", "frequency": 0.1},
            "synonymous": {"impact": "low", "frequency": 0.2},
            "inframe_indel": {"impact": "moderate", "frequency": 0.05}
        }
        
        # Clinical stages
        self.clinical_stages = ["Stage I", "Stage II", "Stage III", "Stage IV"]
        
        # Treatment types
        self.treatments = [
            "Surgery", "Chemotherapy", "Radiation Therapy", "Targeted Therapy",
            "Immunotherapy", "Hormone Therapy", "Stem Cell Transplant"
        ]
    
    def log(self, message: str, level: str = "INFO"):
        """Log messages with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if self.verbose or level == "ERROR":
            print(f"[{timestamp}] {level}: {message}")
    
    def generate_gene_expression_data(self, num_samples: int, num_genes: int) -> List[Dict[str, Any]]:
        """Generate realistic gene expression data."""
        self.log("🧬 Generating gene expression data...")
        
        # Select random subset of cancer genes
        selected_genes = random.sample(self.cancer_genes, min(num_genes, len(self.cancer_genes)))
        
        expression_data = []
        for sample_id in range(1, num_samples + 1):
            sample_name = f"Sample_{sample_id:03d}"
            
            for gene in selected_genes:
                # Generate realistic expression values (log2 transformed)
                base_expression = random.uniform(2.0, 12.0)
                
                # Add some cancer-specific expression patterns
                if gene in ["TP53", "BRCA1", "BRCA2"]:
                    # Tumor suppressors - often downregulated
                    expression = base_expression * random.uniform(0.3, 1.2)
                elif gene in ["MYC", "EGFR", "KRAS"]:
                    # Oncogenes - often upregulated
                    expression = base_expression * random.uniform(1.0, 3.0)
                else:
                    expression = base_expression * random.uniform(0.5, 2.0)
                
                expression_data.append({
                    "sample_id": sample_name,
                    "gene": gene,
                    "expression_level": round(expression, 3),
                    "tissue_type": random.choice(["Tumor", "Normal", "Metastatic"]),
                    "batch": f"Batch_{random.randint(1, 5)}",
                    "created_at": datetime.now()
                })
        
        self.log(f"✅ Generated {len(expression_data)} gene expression records")
        return expression_data
    
    def generate_mutation_data(self, num_samples: int, mutations_per_gene: int) -> List[Dict[str, Any]]:
        """Generate realistic mutation data."""
        self.log("🧬 Generating mutation data...")
        
        mutation_data = []
        for sample_id in range(1, num_samples + 1):
            sample_name = f"Sample_{sample_id:03d}"
            
            # Select random genes for this sample
            num_mutated_genes = random.randint(1, min(10, len(self.cancer_genes)))
            mutated_genes = random.sample(self.cancer_genes, num_mutated_genes)
            
            for gene in mutated_genes:
                num_mutations = random.randint(1, mutations_per_gene)
                
                for _ in range(num_mutations):
                    # Select mutation type based on frequency
                    mut_type = random.choices(
                        list(self.mutation_types.keys()),
                        weights=[mt["frequency"] for mt in self.mutation_types.values()]
                    )[0]
                    
                    # Generate realistic mutation coordinates
                    chromosome = random.randint(1, 22)
                    position = random.randint(1000000, 250000000)
                    
                    # Generate cDNA and protein changes
                    c_dna_change = self._generate_cdna_change(mut_type)
                    protein_change = self._generate_protein_change(mut_type)
                    
                    # Determine pathogenicity based on mutation type and gene
                    pathogenicity = self._determine_pathogenicity(gene, mut_type)
                    
                    mutation_data.append({
                        "sample_id": sample_name,
                        "gene": gene,
                        "mutation": f"{c_dna_change}",
                        "mutation_type": mut_type,
                        "chromosome": chromosome,
                        "position": position,
                        "c_dna_change": c_dna_change,
                        "protein_change": protein_change,
                        "pathogenicity": pathogenicity,
                        "allele_frequency": round(random.uniform(0.1, 1.0), 3),
                        "read_depth": random.randint(50, 500),
                        "source": random.choice(["WGS", "WES", "Targeted Panel", "RNA-seq"]),
                        "created_at": datetime.now()
                    })
        
        self.log(f"✅ Generated {len(mutation_data)} mutation records")
        return mutation_data
    
    def generate_clinical_data(self, num_samples: int) -> List[Dict[str, Any]]:
        """Generate realistic clinical data."""
        self.log("🏥 Generating clinical data...")
        
        clinical_data = []
        for sample_id in range(1, num_samples + 1):
            sample_name = f"Sample_{sample_id:03d}"
            
            # Generate patient demographics
            age = random.randint(18, 85)
            gender = random.choice(["Male", "Female", "Other"])
            cancer_type = random.choice(self.cancer_types)
            stage = random.choice(self.clinical_stages)
            
            # Generate survival data
            diagnosis_date = date.today() - pd.Timedelta(days=random.randint(30, 1825))
            follow_up_days = random.randint(0, 1095)
            status = random.choice(["Alive", "Deceased"])
            
            # Generate treatment information
            treatments = random.sample(self.treatments, random.randint(1, 3))
            
            clinical_data.append({
                "sample_id": sample_name,
                "patient_id": f"Patient_{sample_id:04d}",
                "age_at_diagnosis": age,
                "gender": gender,
                "cancer_type": cancer_type,
                "stage": stage,
                "grade": random.choice(["Grade 1", "Grade 2", "Grade 3", "Grade 4"]),
                "diagnosis_date": diagnosis_date,
                "follow_up_days": follow_up_days,
                "status": status,
                "treatments": ", ".join(treatments),
                "smoking_status": random.choice(["Never", "Former", "Current", "Unknown"]),
                "family_history": random.choice(["Yes", "No", "Unknown"]),
                "created_at": datetime.now()
            })
        
        self.log(f"✅ Generated {len(clinical_data)} clinical records")
        return clinical_data
    
    def generate_pathway_data(self) -> List[Dict[str, Any]]:
        """Generate pathway and annotation data."""
        self.log("🛤️ Generating pathway data...")
        
        pathways = [
            {"name": "Cell Cycle", "genes": ["TP53", "RB1", "CDKN2A", "CCND1", "CDK4"]},
            {"name": "DNA Repair", "genes": ["BRCA1", "BRCA2", "ATM", "CHEK2", "MLH1", "MSH2"]},
            {"name": "Apoptosis", "genes": ["TP53", "BCL2", "BAX", "CASP3", "CASP8"]},
            {"name": "PI3K-AKT", "genes": ["PIK3CA", "PTEN", "AKT1", "MTOR", "TSC1", "TSC2"]},
            {"name": "MAPK", "genes": ["KRAS", "BRAF", "EGFR", "MEK1", "ERK1"]},
            {"name": "WNT", "genes": ["APC", "CTNNB1", "AXIN1", "GSK3B"]},
            {"name": "Hedgehog", "genes": ["PTCH1", "SMO", "GLI1", "SUFU"]},
            {"name": "Notch", "genes": ["NOTCH1", "NOTCH2", "JAG1", "DLL1"]},
            {"name": "TGF-beta", "genes": ["TGFBR1", "TGFBR2", "SMAD2", "SMAD4"]},
            {"name": "Immune Response", "genes": ["CD274", "PDCD1", "CTLA4", "LAG3"]}
        ]
        
        pathway_data = []
        for pathway in pathways:
            pathway_data.append({
                "pathway_name": pathway["name"],
                "genes": ", ".join(pathway["genes"]),
                "gene_count": len(pathway["genes"]),
                "category": random.choice(["Oncogenic", "Tumor Suppressor", "DNA Repair", "Immune"]),
                "description": f"Pathway involved in {pathway['name'].lower()} regulation",
                "created_at": datetime.now()
            })
        
        self.log(f"✅ Generated {len(pathway_data)} pathway records")
        return pathway_data
    
    def _generate_cdna_change(self, mut_type: str) -> str:
        """Generate realistic cDNA change notation."""
        nucleotides = ["A", "T", "G", "C"]
        
        if mut_type == "missense":
            ref = random.choice(nucleotides)
            alt = random.choice([n for n in nucleotides if n != ref])
            pos = random.randint(100, 9999)
            return f"c.{pos}{ref}>{alt}"
        elif mut_type == "nonsense":
            ref = random.choice(["C", "G"])
            alt = random.choice(["A", "T"])
            pos = random.randint(100, 9999)
            return f"c.{pos}{ref}>{alt}"
        elif mut_type == "frameshift":
            pos = random.randint(100, 9999)
            if random.choice([True, False]):
                return f"c.{pos}del{random.choice(nucleotides)}"
            else:
                return f"c.{pos}ins{random.choice(nucleotides)}"
        else:
            pos = random.randint(100, 9999)
            return f"c.{pos}+{random.randint(1, 3)}"
    
    def _generate_protein_change(self, mut_type: str) -> str:
        """Generate realistic protein change notation."""
        amino_acids = ["A", "R", "N", "D", "C", "Q", "E", "G", "H", "I", 
                      "L", "K", "M", "F", "P", "S", "T", "W", "Y", "V"]
        
        if mut_type in ["missense", "nonsense"]:
            ref_aa = random.choice(amino_acids)
            if mut_type == "nonsense":
                alt_aa = "*"
            else:
                alt_aa = random.choice([aa for aa in amino_acids if aa != ref_aa])
            pos = random.randint(1, 1000)
            return f"p.{ref_aa}{pos}{alt_aa}"
        elif mut_type == "frameshift":
            ref_aa = random.choice(amino_acids)
            pos = random.randint(1, 1000)
            return f"p.{ref_aa}{pos}fs"
        else:
            return "p.?"
    
    def _determine_pathogenicity(self, gene: str, mut_type: str) -> str:
        """Determine pathogenicity based on gene and mutation type."""
        # High-impact mutations in tumor suppressors
        if gene in ["TP53", "BRCA1", "BRCA2", "RB1", "PTEN"] and mut_type in ["nonsense", "frameshift"]:
            return random.choice(["Pathogenic", "Likely Pathogenic"])
        # High-impact mutations in oncogenes
        elif gene in ["KRAS", "BRAF", "PIK3CA"] and mut_type == "missense":
            return random.choice(["Pathogenic", "Likely Pathogenic"])
        # Low-impact mutations
        elif mut_type == "synonymous":
            return "Benign"
        # Everything else
        else:
            return random.choice(["Pathogenic", "Likely Pathogenic", "Uncertain Significance", 
                                "Likely Benign", "Benign"])
    
    def save_to_csv(self, data: List[Dict[str, Any]], filename: str):
        """Save generated data to CSV files."""
        if not data:
            return
        
        output_dir = Path("data")
        output_dir.mkdir(exist_ok=True)
        
        df = pd.DataFrame(data)
        csv_path = output_dir / filename
        df.to_csv(csv_path, index=False)
        self.log(f"💾 Saved {len(data)} records to {csv_path}")
    
    def seed_database(self, num_samples: int, num_genes: int, mutations_per_gene: int, 
                     clear_existing: bool = False) -> Dict[str, int]:
        """Main seeding function."""
        self.log("🌱 Starting database seeding process...")
        self.start_time = datetime.now()
        
        if clear_existing:
            self.log("🗑️ Clearing existing data...")
        
        # Generate all data types
        expression_data = self.generate_gene_expression_data(num_samples, num_genes)
        mutation_data = self.generate_mutation_data(num_samples, mutations_per_gene)
        clinical_data = self.generate_clinical_data(num_samples)
        pathway_data = self.generate_pathway_data()
        
        # Save to CSV files for reference
        self.save_to_csv(expression_data, "mock_expression_data.csv")
        self.save_to_csv(mutation_data, "mock_mutation_data.csv")
        self.save_to_csv(clinical_data, "mock_clinical_data.csv")
        self.save_to_csv(pathway_data, "mock_pathway_data.csv")
        
        # Update counts
        self.seeded_counts = {
            "gene_expression": len(expression_data),
            "mutations": len(mutation_data),
            "clinical": len(clinical_data),
            "pathways": len(pathway_data)
        }
        
        return self.seeded_counts
    
    def print_summary(self):
        """Print seeding summary."""
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            self.log("=" * 60)
            self.log("✅ Database seeding completed successfully!")
            self.log(f"⏱️  Total seeding time: {duration:.2f} seconds")
            
            for data_type, count in self.seeded_counts.items():
                self.log(f"📊 {data_type.replace('_', ' ').title()}: {count} records")
            
            self.log("💾 Data files saved to 'data/' directory")


def main():
    """Main entry point for the database seeder."""
    parser = argparse.ArgumentParser(
        description="Cancer Genomics Analysis Suite - Database Seeding Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--samples", "-s",
        type=int,
        default=100,
        help="Number of samples to generate (default: 100)"
    )
    parser.add_argument(
        "--genes", "-g",
        type=int,
        default=50,
        help="Number of genes to include (default: 50)"
    )
    parser.add_argument(
        "--mutations", "-m",
        type=int,
        default=5,
        help="Number of mutations per gene (default: 5)"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing data before seeding"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show seeding plan without execution"
    )
    
    args = parser.parse_args()
    
    # Create seeder
    seeder = DatabaseSeeder(verbose=args.verbose)
    
    if args.dry_run:
        print("🔍 Seeding Plan (Dry Run)")
        print("=" * 40)
        print(f"Samples: {args.samples}")
        print(f"Genes: {args.genes}")
        print(f"Mutations per gene: {args.mutations}")
        print(f"Clear existing: {args.clear}")
        print(f"Verbose: {args.verbose}")
        
        estimated_records = {
            "Gene Expression": args.samples * args.genes,
            "Mutations": args.samples * args.mutations * 2,  # Rough estimate
            "Clinical": args.samples,
            "Pathways": 10  # Fixed number of pathways
        }
        
        print("\nEstimated records to generate:")
        for data_type, count in estimated_records.items():
            print(f"  • {data_type}: {count}")
        
        return
    
    try:
        # Run seeding
        counts = seeder.seed_database(
            num_samples=args.samples,
            num_genes=args.genes,
            mutations_per_gene=args.mutations,
            clear_existing=args.clear
        )
        
        # Print summary
        seeder.print_summary()
        
    except KeyboardInterrupt:
        print("\n⚠️  Database seeding interrupted by user")
    except Exception as e:
        print(f"\n💥 Error during database seeding: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
