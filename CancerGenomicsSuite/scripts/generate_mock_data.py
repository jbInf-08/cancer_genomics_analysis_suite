#!/usr/bin/env python3
"""
Mock Data Auto-Generation Script

This script automatically generates comprehensive mock data for the Cancer Genomics Analysis Suite.
It creates realistic synthetic datasets including:
- Clinical data
- Gene expression data
- Mutation data
- Variant annotations
- Protein structures
- Pathway data
- NGS data

Usage:
    python generate_mock_data.py [options]

Author: Cancer Genomics Analysis Suite
"""

import os
import sys
import argparse
import logging
import json
import random
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import uuid
from dataclasses import dataclass, asdict
import gzip
import csv

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class MockDataConfig:
    """Configuration for mock data generation."""
    num_patients: int = 1000
    num_samples: int = 1200
    num_genes: int = 20000
    num_mutations: int = 5000
    num_pathways: int = 200
    output_dir: str = "data"
    seed: int = 42
    cancer_types: List[str] = None
    gene_list: List[str] = None
    
    def __post_init__(self):
        if self.cancer_types is None:
            self.cancer_types = [
                "BRCA", "NSCLC", "COAD", "PRAD", "STAD", "LIHC", "THCA",
                "BLCA", "HNSC", "KIRC", "LUSC", "UCEC", "CESC", "SARC",
                "DLBC", "LGG", "GBM", "OV", "SKCM", "PAAD"
            ]
        
        if self.gene_list is None:
            self.gene_list = [
                "TP53", "BRCA1", "BRCA2", "EGFR", "KRAS", "MYC", "PIK3CA",
                "PTEN", "APC", "RB1", "VHL", "CDKN2A", "MLH1", "MSH2",
                "ATM", "CHEK2", "PALB2", "BARD1", "RAD51C", "RAD51D",
                "BRAF", "ALK", "RET", "MET", "FGFR1", "FGFR2", "FGFR3",
                "PDGFRA", "KIT", "ABL1", "BCR", "JAK2", "FLT3", "NPM1",
                "MLL", "NF1", "NF2", "TSC1", "TSC2", "STK11", "SMAD4"
            ]


class MockDataGenerator:
    """Generates comprehensive mock data for cancer genomics analysis."""
    
    def __init__(self, config: MockDataConfig):
        """
        Initialize the mock data generator.
        
        Args:
            config (MockDataConfig): Configuration for data generation
        """
        self.config = config
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.output_dir / 'mock_data_generation.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Set random seed for reproducibility
        random.seed(config.seed)
        np.random.seed(config.seed)
        
        # Initialize data structures
        self.patients = []
        self.samples = []
        self.genes = []
        self.mutations = []
        self.expressions = []
        self.pathways = []
        
        # Cancer type specific configurations
        self.cancer_configs = {
            "BRCA": {"stages": ["Stage I", "Stage IIA", "Stage IIB", "Stage IIIA", "Stage IIIB", "Stage IIIC", "Stage IV"],
                    "grades": ["Grade 1", "Grade 2", "Grade 3"],
                    "histologies": ["Invasive Ductal Carcinoma", "Invasive Lobular Carcinoma", "Triple Negative"]},
            "NSCLC": {"stages": ["Stage IA", "Stage IB", "Stage IIA", "Stage IIB", "Stage IIIA", "Stage IIIB", "Stage IV"],
                     "grades": ["Grade 1", "Grade 2", "Grade 3"],
                     "histologies": ["Adenocarcinoma", "Squamous Cell Carcinoma", "Large Cell Carcinoma"]},
            "COAD": {"stages": ["Stage I", "Stage IIA", "Stage IIB", "Stage IIIA", "Stage IIIB", "Stage IIIC", "Stage IV"],
                    "grades": ["Grade 1", "Grade 2", "Grade 3"],
                    "histologies": ["Adenocarcinoma", "Mucinous Adenocarcinoma", "Signet Ring Cell Carcinoma"]},
            "PRAD": {"stages": ["Stage I", "Stage IIA", "Stage IIB", "Stage IIIA", "Stage IIIB", "Stage IIIC", "Stage IV"],
                    "grades": ["Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5"],
                    "histologies": ["Adenocarcinoma", "Ductal Adenocarcinoma", "Acinar Adenocarcinoma"]},
            "STAD": {"stages": ["Stage I", "Stage IIA", "Stage IIB", "Stage IIIA", "Stage IIIB", "Stage IIIC", "Stage IV"],
                    "grades": ["Grade 1", "Grade 2", "Grade 3"],
                    "histologies": ["Adenocarcinoma", "Signet Ring Cell Carcinoma", "Mucinous Adenocarcinoma"]},
            "LIHC": {"stages": ["Stage I", "Stage II", "Stage IIIA", "Stage IIIB", "Stage IIIC", "Stage IV"],
                    "grades": ["Grade 1", "Grade 2", "Grade 3"],
                    "histologies": ["Hepatocellular Carcinoma", "Cholangiocarcinoma", "Mixed Hepatocellular-Cholangiocarcinoma"]},
            "THCA": {"stages": ["Stage I", "Stage II", "Stage III", "Stage IVA", "Stage IVB", "Stage IVC"],
                    "grades": ["Grade 1", "Grade 2", "Grade 3"],
                    "histologies": ["Papillary Thyroid Carcinoma", "Follicular Thyroid Carcinoma", "Medullary Thyroid Carcinoma"]},
            "BLCA": {"stages": ["Stage 0a", "Stage 0is", "Stage I", "Stage II", "Stage III", "Stage IV"],
                    "grades": ["Low Grade", "High Grade"],
                    "histologies": ["Urothelial Carcinoma", "Squamous Cell Carcinoma", "Adenocarcinoma"]},
            "HNSC": {"stages": ["Stage I", "Stage II", "Stage III", "Stage IVA", "Stage IVB", "Stage IVC"],
                    "grades": ["Grade 1", "Grade 2", "Grade 3"],
                    "histologies": ["Squamous Cell Carcinoma", "Adenocarcinoma", "Adenoid Cystic Carcinoma"]},
            "KIRC": {"stages": ["Stage I", "Stage II", "Stage III", "Stage IV"],
                    "grades": ["Grade 1", "Grade 2", "Grade 3", "Grade 4"],
                    "histologies": ["Clear Cell Renal Cell Carcinoma", "Papillary Renal Cell Carcinoma", "Chromophobe Renal Cell Carcinoma"]}
        }
        
        # Treatment options
        self.treatments = {
            "chemotherapy": ["Cisplatin", "Carboplatin", "Paclitaxel", "Docetaxel", "Gemcitabine", "5-FU", "Oxaliplatin"],
            "targeted_therapy": ["Trastuzumab", "Bevacizumab", "Cetuximab", "Erlotinib", "Gefitinib", "Imatinib", "Sunitinib"],
            "immunotherapy": ["Pembrolizumab", "Nivolumab", "Atezolizumab", "Durvalumab", "Ipilimumab"],
            "radiation_therapy": ["External Beam Radiation", "Brachytherapy", "Stereotactic Radiosurgery", "Proton Therapy"]
        }
        
        # Response categories
        self.responses = ["Complete Response", "Partial Response", "Stable Disease", "Progressive Disease"]
        
        # Comorbidities
        self.comorbidities = [
            "Diabetes", "Hypertension", "COPD", "Heart Disease", "Obesity", 
            "Hepatitis B", "Hepatitis C", "HIV", "Stroke", "Kidney Disease"
        ]
        
        # Generate base data
        self._generate_base_data()
    
    def _generate_base_data(self):
        """Generate base patient and sample data."""
        self.logger.info("Generating base patient and sample data...")
        
        # Generate patients
        for i in range(self.config.num_patients):
            patient_id = f"P{str(i+1).zfill(3)}"
            age = random.randint(18, 90)
            gender = random.choice(["Male", "Female"])
            race = random.choice(["White", "Black", "Asian", "Hispanic", "Other"])
            ethnicity = random.choice(["Hispanic", "Non-Hispanic"])
            
            # Cancer type specific data
            cancer_type = random.choice(self.config.cancer_types)
            cancer_config = self.cancer_configs.get(cancer_type, self.cancer_configs["BRCA"])
            
            primary_diagnosis = random.choice(cancer_config["histologies"])
            cancer_stage = random.choice(cancer_config["stages"])
            tumor_grade = random.choice(cancer_config["grades"])
            
            # Treatment and outcome data
            treatment_status = random.choice(["Active", "Completed", "Discontinued"])
            response = random.choice(self.responses)
            
            # Survival data
            overall_survival = random.randint(30, 2000)
            progression_free_survival = random.randint(20, min(overall_survival, 1500))
            
            # Additional clinical data
            metastasis_status = random.choice(["Yes", "No"])
            recurrence_status = random.choice(["Yes", "No"])
            comorbidities = random.sample(self.comorbidities, random.randint(0, 3))
            smoking_status = random.choice(["Never", "Former", "Current"])
            alcohol_consumption = random.choice(["None", "Light", "Moderate", "Heavy"])
            family_history = random.choice(["Yes", "No"])
            
            patient = {
                "patient_id": patient_id,
                "age": age,
                "gender": gender,
                "race": race,
                "ethnicity": ethnicity,
                "primary_diagnosis": primary_diagnosis,
                "cancer_stage": cancer_stage,
                "tumor_grade": tumor_grade,
                "treatment_status": treatment_status,
                "response_to_treatment": response,
                "overall_survival_days": overall_survival,
                "progression_free_survival_days": progression_free_survival,
                "metastasis_status": metastasis_status,
                "recurrence_status": recurrence_status,
                "comorbidities": "; ".join(comorbidities) if comorbidities else "None",
                "smoking_status": smoking_status,
                "alcohol_consumption": alcohol_consumption,
                "family_history": family_history
            }
            
            self.patients.append(patient)
        
        # Generate samples
        for i in range(self.config.num_samples):
            sample_id = f"S{str(i+1).zfill(3)}"
            patient = random.choice(self.patients)
            patient_id = patient["patient_id"]
            
            # Sample type and platform data
            sample_type = random.choice(["tumor", "normal", "cell_line", "metastasis"])
            platform = random.choice(["illumina", "pacbio", "nanopore"])
            sequencing_type = random.choice(["WGS", "WES", "RNA-seq", "ChIP-seq"])
            library_prep = random.choice(["TruSeq", "Nextera", "KAPA", "Swift"])
            read_length = random.choice([75, 100, 150, 250, 300])
            paired_end = random.choice([True, False])
            
            sample = {
                "sample_id": sample_id,
                "patient_id": patient_id,
                "sample_name": f"{patient_id}_{sample_type}_{i+1}",
                "sample_type": sample_type,
                "platform": platform,
                "sequencing_type": sequencing_type,
                "library_prep": library_prep,
                "read_length": read_length,
                "paired_end": paired_end,
                "project_id": f"PROJ_{random.randint(1, 10)}",
                "user_id": random.randint(1, 10),
                "created_at": datetime.now() - timedelta(days=random.randint(1, 365)),
                "updated_at": datetime.now() - timedelta(days=random.randint(1, 30)),
                "metadata": json.dumps({
                    "tissue_source": random.choice(["primary", "metastasis", "normal"]),
                    "collection_date": (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat(),
                    "storage_conditions": random.choice(["frozen", "FFPE", "fresh"])
                })
            }
            
            self.samples.append(sample)
        
        self.logger.info(f"Generated {len(self.patients)} patients and {len(self.samples)} samples")
    
    def generate_clinical_data(self) -> str:
        """Generate clinical data CSV file."""
        self.logger.info("Generating clinical data...")
        
        # Add treatment details to clinical data
        clinical_data = []
        for patient in self.patients:
            clinical_record = patient.copy()
            
            # Add treatment details
            clinical_record["chemotherapy"] = random.choice(["Yes", "No"])
            clinical_record["radiation_therapy"] = random.choice(["Yes", "No"])
            clinical_record["targeted_therapy"] = random.choice(["Yes", "No"])
            clinical_record["immunotherapy"] = random.choice(["Yes", "No"])
            clinical_record["surgery"] = random.choice(["Yes", "No"])
            
            # Add sample information
            patient_samples = [s for s in self.samples if s["patient_id"] == patient["patient_id"]]
            if patient_samples:
                sample = random.choice(patient_samples)
                clinical_record["sample_id"] = sample["sample_id"]
            else:
                clinical_record["sample_id"] = f"S{str(random.randint(1, 1000)).zfill(3)}"
            
            clinical_data.append(clinical_record)
        
        # Save to CSV
        output_file = self.output_dir / "mock_clinical_data.csv"
        df = pd.DataFrame(clinical_data)
        df.to_csv(output_file, index=False)
        
        self.logger.info(f"Clinical data saved to: {output_file}")
        return str(output_file)
    
    def generate_expression_data(self) -> str:
        """Generate gene expression data."""
        self.logger.info("Generating gene expression data...")
        
        expression_data = []
        
        # Generate expression for each sample
        for sample in self.samples:
            # Get patient info for cancer type
            patient = next((p for p in self.patients if p["patient_id"] == sample["patient_id"]), None)
            if not patient:
                continue
            
            # Determine cancer type from diagnosis
            cancer_type = self._get_cancer_type_from_diagnosis(patient["primary_diagnosis"])
            tissue_type = sample["sample_type"]
            
            # Generate expression for subset of genes
            num_genes = random.randint(50, 200)
            selected_genes = random.sample(self.config.gene_list, min(num_genes, len(self.config.gene_list)))
            
            for gene in selected_genes:
                # Generate realistic expression values
                base_expression = np.random.lognormal(mean=6, sigma=1.5)
                
                # Add cancer-specific expression patterns
                if gene in ["TP53", "BRCA1", "BRCA2"] and cancer_type in ["BRCA"]:
                    base_expression *= random.uniform(0.5, 2.0)
                elif gene in ["EGFR", "KRAS"] and cancer_type in ["NSCLC", "COAD"]:
                    base_expression *= random.uniform(0.8, 3.0)
                
                # Calculate log2 fold change
                log2_fc = np.random.normal(0, 1.5)
                
                # Generate p-values
                p_value = random.uniform(0.001, 0.1)
                adjusted_p_value = p_value * random.uniform(1.5, 5.0)
                
                expression_record = {
                    "sample_id": sample["sample_id"],
                    "gene_symbol": gene,
                    "expression_value": round(base_expression, 2),
                    "log2_fold_change": round(log2_fc, 2),
                    "p_value": round(p_value, 4),
                    "adjusted_p_value": round(adjusted_p_value, 4),
                    "tissue_type": tissue_type,
                    "cancer_type": cancer_type
                }
                
                expression_data.append(expression_record)
        
        # Save to CSV
        output_file = self.output_dir / "mock_expression_data.csv"
        df = pd.DataFrame(expression_data)
        df.to_csv(output_file, index=False)
        
        self.logger.info(f"Expression data saved to: {output_file}")
        return str(output_file)
    
    def generate_mutation_data(self) -> str:
        """Generate mutation data."""
        self.logger.info("Generating mutation data...")
        
        mutation_data = []
        
        # Common cancer mutations
        cancer_mutations = {
            "TP53": [("17", 7574003, "G", "A", "p.R175H"), ("17", 7577120, "C", "T", "p.R248Q")],
            "BRCA1": [("17", 43094695, "G", "C", "p.R1699W"), ("17", 43094695, "G", "T", "p.R1699L")],
            "BRCA2": [("13", 32316467, "G", "A", "p.N372H"), ("13", 32316467, "G", "T", "p.N372Y")],
            "EGFR": [("7", 55241707, "G", "T", "p.G719S"), ("7", 55241707, "G", "A", "p.G719A")],
            "KRAS": [("12", 25245350, "G", "A", "p.G12D"), ("12", 25245350, "G", "T", "p.G12V")],
            "MYC": [("8", 128748315, "G", "A", "p.P44L"), ("8", 128748315, "G", "T", "p.P44S")],
            "PIK3CA": [("3", 178916876, "G", "A", "p.H1047R"), ("3", 178916876, "G", "T", "p.H1047L")],
            "PTEN": [("10", 89692905, "G", "A", "p.R130Q"), ("10", 89692905, "G", "T", "p.R130L")],
            "APC": [("5", 112175779, "G", "A", "p.R1450Q"), ("5", 112175779, "G", "T", "p.R1450L")],
            "RB1": [("13", 48877883, "G", "A", "p.R661Q"), ("13", 48877883, "G", "T", "p.R661L")]
        }
        
        # Generate mutations for samples
        for sample in self.samples:
            # Get patient info
            patient = next((p for p in self.patients if p["patient_id"] == sample["patient_id"]), None)
            if not patient:
                continue
            
            # Number of mutations per sample
            num_mutations = random.randint(1, 20)
            
            for _ in range(num_mutations):
                # Select random gene
                gene = random.choice(self.config.gene_list)
                
                # Get mutation info
                if gene in cancer_mutations:
                    chrom, pos, ref, alt, protein_change = random.choice(cancer_mutations[gene])
                else:
                    # Generate random mutation
                    chrom = str(random.randint(1, 22))
                    pos = random.randint(1000000, 200000000)
                    ref = random.choice(["A", "T", "G", "C"])
                    alt = random.choice([b for b in ["A", "T", "G", "C"] if b != ref])
                    protein_change = f"p.{random.choice(['A', 'R', 'N', 'D', 'C', 'Q', 'E', 'G', 'H', 'I', 'L', 'K', 'M', 'F', 'P', 'S', 'T', 'W', 'Y', 'V'])}{random.randint(1, 500)}{random.choice(['A', 'R', 'N', 'D', 'C', 'Q', 'E', 'G', 'H', 'I', 'L', 'K', 'M', 'F', 'P', 'S', 'T', 'W', 'Y', 'V'])}"
                
                # Generate additional mutation data
                transcript_id = f"ENST{random.randint(10000000000, 99999999999)}"
                consequence_type = random.choice([
                    "missense_variant", "nonsense_variant", "synonymous_variant",
                    "frameshift_variant", "splice_acceptor_variant", "splice_donor_variant"
                ])
                clinical_significance = random.choice([
                    "Pathogenic", "Likely_pathogenic", "Uncertain_significance",
                    "Likely_benign", "Benign"
                ])
                cosmic_id = random.randint(10000, 99999)
                allele_frequency = random.uniform(0.1, 0.9)
                read_depth = random.randint(50, 200)
                variant_quality = random.uniform(95, 100)
                
                mutation_record = {
                    "sample_id": sample["sample_id"],
                    "chromosome": chrom,
                    "start_position": pos,
                    "end_position": pos,
                    "reference_allele": ref,
                    "alternate_allele": alt,
                    "gene_symbol": gene,
                    "transcript_id": transcript_id,
                    "protein_change": protein_change,
                    "consequence_type": consequence_type,
                    "clinical_significance": clinical_significance,
                    "cosmic_id": cosmic_id,
                    "allele_frequency": round(allele_frequency, 2),
                    "read_depth": read_depth,
                    "variant_quality": round(variant_quality, 1)
                }
                
                mutation_data.append(mutation_record)
        
        # Save to CSV
        output_file = self.output_dir / "mock_mutation_data.csv"
        df = pd.DataFrame(mutation_data)
        df.to_csv(output_file, index=False)
        
        self.logger.info(f"Mutation data saved to: {output_file}")
        return str(output_file)
    
    def generate_variant_annotations(self) -> str:
        """Generate variant annotation data."""
        self.logger.info("Generating variant annotations...")
        
        # Create variant annotations directory
        variant_dir = self.output_dir / "mock_variant_annotations"
        variant_dir.mkdir(exist_ok=True)
        
        annotations = []
        
        # Generate annotations for mutations
        mutation_file = self.output_dir / "mock_mutation_data.csv"
        if mutation_file.exists():
            df_mutations = pd.read_csv(mutation_file)
            
            for _, mutation in df_mutations.iterrows():
                # Generate functional predictions
                sift_score = random.uniform(0, 1)
                sift_prediction = "deleterious" if sift_score < 0.05 else "tolerated"
                
                polyphen2_score = random.uniform(0, 1)
                polyphen2_prediction = "probably_damaging" if polyphen2_score > 0.8 else "possibly_damaging" if polyphen2_score > 0.5 else "benign"
                
                cadd_score = random.uniform(0, 50)
                cadd_prediction = "deleterious" if cadd_score > 15 else "tolerated"
                
                # Generate conservation scores
                phastcons_score = random.uniform(0, 1)
                phylop_score = random.uniform(-10, 10)
                
                # Generate population frequencies
                gnomad_af = random.uniform(0, 0.1)
                exac_af = random.uniform(0, 0.1)
                thousand_genomes_af = random.uniform(0, 0.1)
                
                annotation = {
                    "variant_id": f"{mutation['chromosome']}:{mutation['start_position']}:{mutation['reference_allele']}>{mutation['alternate_allele']}",
                    "gene_symbol": mutation["gene_symbol"],
                    "transcript_id": mutation["transcript_id"],
                    "protein_change": mutation["protein_change"],
                    "consequence_type": mutation["consequence_type"],
                    "clinical_significance": mutation["clinical_significance"],
                    "cosmic_id": mutation["cosmic_id"],
                    "allele_frequency": mutation["allele_frequency"],
                    "read_depth": mutation["read_depth"],
                    "variant_quality": mutation["variant_quality"],
                    "functional_predictions": {
                        "sift_score": round(sift_score, 3),
                        "sift_prediction": sift_prediction,
                        "polyphen2_score": round(polyphen2_score, 3),
                        "polyphen2_prediction": polyphen2_prediction,
                        "cadd_score": round(cadd_score, 1),
                        "cadd_prediction": cadd_prediction
                    },
                    "conservation_scores": {
                        "phastcons_score": round(phastcons_score, 3),
                        "phylop_score": round(phylop_score, 3)
                    },
                    "population_frequencies": {
                        "gnomad_af": round(gnomad_af, 6),
                        "exac_af": round(exac_af, 6),
                        "thousand_genomes_af": round(thousand_genomes_af, 6)
                    },
                    "clinical_evidence": {
                        "clinvar_id": f"CV{random.randint(100000, 999999)}",
                        "hgmd_id": f"CM{random.randint(100000, 999999)}",
                        "disease_associations": random.sample([
                            "Breast cancer", "Ovarian cancer", "Lung cancer", "Colorectal cancer",
                            "Prostate cancer", "Pancreatic cancer", "Liver cancer", "Thyroid cancer"
                        ], random.randint(1, 3))
                    }
                }
                
                annotations.append(annotation)
        
        # Save to JSON
        output_file = variant_dir / "annotated_mutations.json"
        with open(output_file, 'w') as f:
            json.dump({"annotations": annotations}, f, indent=2)
        
        self.logger.info(f"Variant annotations saved to: {output_file}")
        return str(output_file)
    
    def generate_pathway_data(self) -> str:
        """Generate pathway data."""
        self.logger.info("Generating pathway data...")
        
        # Common cancer pathways
        pathways = [
            "Cell Cycle", "DNA Repair", "Apoptosis", "PI3K/AKT/mTOR",
            "RAS/MAPK", "WNT/beta-catenin", "Hedgehog", "Notch",
            "TGF-beta", "JAK/STAT", "NF-kappaB", "p53", "RB", "MYC",
            "Hypoxia", "Angiogenesis", "Epithelial-Mesenchymal Transition",
            "Immune Response", "Metabolism", "Oxidative Stress"
        ]
        
        pathway_data = []
        
        for pathway in pathways:
            # Generate genes for each pathway
            num_genes = random.randint(5, 50)
            pathway_genes = random.sample(self.config.gene_list, min(num_genes, len(self.config.gene_list)))
            
            pathway_record = {
                "pathway_name": pathway,
                "pathway_id": f"PATH_{random.randint(1000, 9999)}",
                "description": f"{pathway} signaling pathway involved in cancer development",
                "genes": pathway_genes,
                "gene_count": len(pathway_genes),
                "category": random.choice(["Oncogenic", "Tumor Suppressor", "DNA Repair", "Metabolic", "Immune"]),
                "source": random.choice(["KEGG", "Reactome", "GO", "MSigDB"]),
                "confidence": random.choice(["High", "Medium", "Low"])
            }
            
            pathway_data.append(pathway_record)
        
        # Save to JSON
        output_file = self.output_dir / "mock_pathway_data.json"
        with open(output_file, 'w') as f:
            json.dump({"pathways": pathway_data}, f, indent=2)
        
        # Also save as simple text list
        pathway_list_file = self.output_dir / "mock_pathway_list.txt"
        with open(pathway_list_file, 'w') as f:
            for pathway in pathways:
                f.write(f"{pathway}\n")
        
        self.logger.info(f"Pathway data saved to: {output_file}")
        return str(output_file)
    
    def generate_protein_structures(self) -> str:
        """Generate mock protein structure data."""
        self.logger.info("Generating protein structure data...")
        
        # Create protein structures directory
        structure_dir = self.output_dir / "mock_protein_structures"
        structure_dir.mkdir(exist_ok=True)
        
        # Common cancer proteins with known structures
        protein_structures = [
            {"name": "TP53", "pdb_id": "1TUP", "description": "Tumor protein p53"},
            {"name": "BRCA1", "pdb_id": "1JM7", "description": "Breast cancer type 1 susceptibility protein"},
            {"name": "EGFR", "pdb_id": "1M17", "description": "Epidermal growth factor receptor"},
            {"name": "KRAS", "pdb_id": "4OBE", "description": "K-Ras protein"},
            {"name": "MYC", "pdb_id": "1NKP", "description": "Myc proto-oncogene protein"},
            {"name": "PIK3CA", "pdb_id": "2RD0", "description": "Phosphatidylinositol-4,5-bisphosphate 3-kinase"},
            {"name": "PTEN", "pdb_id": "1D5R", "description": "Phosphatase and tensin homolog"},
            {"name": "APC", "pdb_id": "1DEW", "description": "Adenomatous polyposis coli protein"},
            {"name": "RB1", "pdb_id": "1AD6", "description": "Retinoblastoma protein"},
            {"name": "VHL", "pdb_id": "1LM8", "description": "Von Hippel-Lindau tumor suppressor"}
        ]
        
        for protein in protein_structures:
            # Generate mock PDB content
            pdb_content = self._generate_mock_pdb(protein["name"], protein["pdb_id"])
            
            # Save PDB file
            pdb_file = structure_dir / f"{protein['name']}.pdb"
            with open(pdb_file, 'w') as f:
                f.write(pdb_content)
        
        self.logger.info(f"Protein structures saved to: {structure_dir}")
        return str(structure_dir)
    
    def _generate_mock_pdb(self, protein_name: str, pdb_id: str) -> str:
        """Generate mock PDB file content."""
        pdb_lines = [
            f"HEADER    CANCER PROTEIN                           {pdb_id}   {datetime.now().strftime('%d-%b-%y')}   {pdb_id}",
            f"TITLE     MOCK STRUCTURE FOR {protein_name}",
            f"COMPND    MOL_ID: 1;",
            f"COMPND   2 MOLECULE: {protein_name};",
            f"COMPND   3 CHAIN: A;",
            f"SOURCE    MOL_ID: 1;",
            f"SOURCE   2 ORGANISM_SCIENTIFIC: HOMO SAPIENS;",
            f"SOURCE   3 ORGANISM_COMMON: HUMAN;",
            f"KEYWDS    CANCER, ONCOGENE, TUMOR SUPPRESSOR",
            f"REMARK   1 MOCK STRUCTURE FOR TESTING PURPOSES",
            f"REMARK   2 GENERATED BY MOCK DATA GENERATOR",
            f"SEQRES   1 A   {random.randint(100, 500)}  ALA ARG ASN ASP CYS GLN GLU GLY HIS ILE LEU LYS MET PHE PRO SER THR TRP TYR VAL",
            f"ATOM      1  N   ALA A   1      20.123  15.456  10.789  1.00 20.00           N",
            f"ATOM      2  CA  ALA A   1      21.234  16.567  11.890  1.00 20.00           C",
            f"ATOM      3  C   ALA A   1      22.345  17.678  12.901  1.00 20.00           C",
            f"ATOM      4  O   ALA A   1      23.456  18.789  13.012  1.00 20.00           O",
            f"END"
        ]
        
        return "\n".join(pdb_lines)
    
    def generate_ngs_data(self) -> str:
        """Generate NGS pipeline data."""
        self.logger.info("Generating NGS data...")
        
        ngs_data = []
        
        for sample in self.samples:
            # Generate NGS file information
            file_types = ["fastq", "bam", "vcf", "bcf"]
            
            for file_type in file_types:
                file_id = f"{sample['sample_id']}_{file_type}_{random.randint(1, 1000)}"
                file_path = f"/data/ngs/{sample['sample_id']}/{file_id}.{file_type}"
                file_size = random.randint(1000000, 10000000000)  # 1MB to 10GB
                checksum = f"md5:{''.join(random.choices('0123456789abcdef', k=32))}"
                
                if file_type == "fastq":
                    read_count = random.randint(1000000, 100000000)
                    base_count = read_count * sample["read_length"]
                    quality_score = random.uniform(20, 40)
                else:
                    read_count = None
                    base_count = None
                    quality_score = None
                
                ngs_record = {
                    "file_id": file_id,
                    "sample_id": sample["sample_id"],
                    "file_type": file_type,
                    "file_path": file_path,
                    "file_size": file_size,
                    "checksum": checksum,
                    "quality_score": quality_score,
                    "read_count": read_count,
                    "base_count": base_count,
                    "created_at": sample["created_at"],
                    "updated_at": sample["updated_at"]
                }
                
                ngs_data.append(ngs_record)
        
        # Save to CSV
        output_file = self.output_dir / "mock_ngs_data.csv"
        df = pd.DataFrame(ngs_data)
        df.to_csv(output_file, index=False)
        
        self.logger.info(f"NGS data saved to: {output_file}")
        return str(output_file)
    
    def _get_cancer_type_from_diagnosis(self, diagnosis: str) -> str:
        """Map diagnosis to cancer type."""
        diagnosis_lower = diagnosis.lower()
        
        if "breast" in diagnosis_lower or "ductal" in diagnosis_lower or "lobular" in diagnosis_lower:
            return "BRCA"
        elif "lung" in diagnosis_lower or "adenocarcinoma" in diagnosis_lower or "squamous" in diagnosis_lower:
            return "NSCLC"
        elif "colon" in diagnosis_lower or "colorectal" in diagnosis_lower:
            return "COAD"
        elif "prostate" in diagnosis_lower:
            return "PRAD"
        elif "stomach" in diagnosis_lower or "gastric" in diagnosis_lower:
            return "STAD"
        elif "liver" in diagnosis_lower or "hepatocellular" in diagnosis_lower:
            return "LIHC"
        elif "thyroid" in diagnosis_lower:
            return "THCA"
        elif "bladder" in diagnosis_lower or "urothelial" in diagnosis_lower:
            return "BLCA"
        elif "head" in diagnosis_lower or "neck" in diagnosis_lower:
            return "HNSC"
        elif "kidney" in diagnosis_lower or "renal" in diagnosis_lower:
            return "KIRC"
        else:
            return random.choice(self.config.cancer_types)
    
    def generate_all_data(self) -> Dict[str, str]:
        """Generate all mock data files."""
        self.logger.info("Starting comprehensive mock data generation...")
        
        generated_files = {}
        
        # Generate all data types
        generated_files["clinical"] = self.generate_clinical_data()
        generated_files["expression"] = self.generate_expression_data()
        generated_files["mutations"] = self.generate_mutation_data()
        generated_files["variant_annotations"] = self.generate_variant_annotations()
        generated_files["pathways"] = self.generate_pathway_data()
        generated_files["protein_structures"] = self.generate_protein_structures()
        generated_files["ngs_data"] = self.generate_ngs_data()
        
        # Generate summary report
        self.generate_summary_report(generated_files)
        
        self.logger.info("Mock data generation completed successfully!")
        return generated_files
    
    def generate_summary_report(self, generated_files: Dict[str, str]) -> str:
        """Generate a summary report of created data files."""
        report_file = self.output_dir / "mock_data_generation_summary.txt"
        
        with open(report_file, 'w') as f:
            f.write("Mock Data Generation Summary\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Output directory: {self.output_dir}\n")
            f.write(f"Random seed: {self.config.seed}\n\n")
            
            f.write("Configuration:\n")
            f.write(f"  Number of patients: {self.config.num_patients}\n")
            f.write(f"  Number of samples: {self.config.num_samples}\n")
            f.write(f"  Number of genes: {self.config.num_genes}\n")
            f.write(f"  Number of mutations: {self.config.num_mutations}\n")
            f.write(f"  Cancer types: {', '.join(self.config.cancer_types)}\n\n")
            
            f.write("Generated Files:\n")
            f.write("-" * 20 + "\n")
            for data_type, file_path in generated_files.items():
                f.write(f"{data_type}: {file_path}\n")
            
            f.write(f"\nTotal files generated: {len(generated_files)}\n")
            
            f.write("\nUsage Instructions:\n")
            f.write("-" * 20 + "\n")
            f.write("These mock data files can be used for:\n")
            f.write("- Testing the Cancer Genomics Analysis Suite\n")
            f.write("- Development and debugging\n")
            f.write("- Training and education\n")
            f.write("- Performance testing\n")
            f.write("- Integration testing\n\n")
            
            f.write("Data Integration:\n")
            f.write("- Clinical data links patients to samples\n")
            f.write("- Expression data contains gene expression values\n")
            f.write("- Mutation data includes variant information\n")
            f.write("- Variant annotations provide functional predictions\n")
            f.write("- Pathway data contains gene sets\n")
            f.write("- Protein structures are in PDB format\n")
            f.write("- NGS data includes file metadata\n")
        
        self.logger.info(f"Summary report saved to: {report_file}")
        return str(report_file)


def main():
    """Main function to run the mock data generator."""
    parser = argparse.ArgumentParser(
        description="Auto-generate comprehensive mock data for cancer genomics analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all mock data with default settings
  python generate_mock_data.py
  
  # Generate data with custom parameters
  python generate_mock_data.py --num-patients 500 --num-samples 600 --output-dir custom_data
  
  # Generate only specific data types
  python generate_mock_data.py --clinical-only
  
  # Generate data with specific cancer types
  python generate_mock_data.py --cancer-types BRCA NSCLC COAD
        """
    )
    
    parser.add_argument(
        "--num-patients",
        type=int,
        default=1000,
        help="Number of patients to generate (default: 1000)"
    )
    
    parser.add_argument(
        "--num-samples",
        type=int,
        default=1200,
        help="Number of samples to generate (default: 1200)"
    )
    
    parser.add_argument(
        "--num-genes",
        type=int,
        default=20000,
        help="Number of genes to include (default: 20000)"
    )
    
    parser.add_argument(
        "--num-mutations",
        type=int,
        default=5000,
        help="Number of mutations to generate (default: 5000)"
    )
    
    parser.add_argument(
        "--output-dir",
        default="data",
        help="Output directory for generated data (default: data)"
    )
    
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)"
    )
    
    parser.add_argument(
        "--cancer-types",
        nargs="+",
        help="Specific cancer types to include"
    )
    
    parser.add_argument(
        "--clinical-only",
        action="store_true",
        help="Generate only clinical data"
    )
    
    parser.add_argument(
        "--expression-only",
        action="store_true",
        help="Generate only expression data"
    )
    
    parser.add_argument(
        "--mutations-only",
        action="store_true",
        help="Generate only mutation data"
    )
    
    args = parser.parse_args()
    
    # Create configuration
    config = MockDataConfig(
        num_patients=args.num_patients,
        num_samples=args.num_samples,
        num_genes=args.num_genes,
        num_mutations=args.num_mutations,
        output_dir=args.output_dir,
        seed=args.seed,
        cancer_types=args.cancer_types
    )
    
    # Initialize generator
    generator = MockDataGenerator(config)
    
    # Generate data based on options
    if args.clinical_only:
        generator.logger.info("Generating clinical data only...")
        generator.generate_clinical_data()
    elif args.expression_only:
        generator.logger.info("Generating expression data only...")
        generator.generate_expression_data()
    elif args.mutations_only:
        generator.logger.info("Generating mutation data only...")
        generator.generate_mutation_data()
    else:
        # Generate all data
        generated_files = generator.generate_all_data()
        generator.logger.info(f"Generated {len(generated_files)} data files")


if __name__ == "__main__":
    main()
