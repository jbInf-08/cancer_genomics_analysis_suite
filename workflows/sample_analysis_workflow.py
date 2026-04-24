#!/usr/bin/env python3
"""
Cancer Genomics Analysis Suite - Sample Analysis Workflow

This module demonstrates a complete workflow:
1. Data Collection - Gather data from multiple sources
2. Data Preprocessing - Clean and standardize data
3. Statistical Analysis - Run differential analysis with R
4. Visualization - Generate plots and reports

Usage:
    python workflows/sample_analysis_workflow.py
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class CancerGenomicsWorkflow:
    """
    End-to-end workflow for cancer genomics analysis.
    
    Workflow Steps:
    1. collect_data() - Gather data from APIs
    2. preprocess_data() - Clean and standardize
    3. analyze_data() - Statistical analysis with R
    4. visualize_results() - Generate plots
    5. generate_report() - Create summary report
    """
    
    def __init__(self, 
                 output_dir: str = "data/workflow_output",
                 cancer_type: str = "BRCA"):
        """
        Initialize workflow.
        
        Args:
            output_dir: Directory for output files
            cancer_type: Cancer type to analyze (e.g., BRCA, LUAD)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cancer_type = cancer_type
        self.workflow_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Track workflow state
        self.state = {
            "workflow_id": self.workflow_id,
            "cancer_type": cancer_type,
            "started_at": datetime.now().isoformat(),
            "steps_completed": [],
            "data": {},
            "results": {}
        }
        
        print(f"Workflow initialized: {self.workflow_id}")
        print(f"Cancer type: {cancer_type}")
        print(f"Output directory: {self.output_dir}")
    
    def collect_data(self, sources: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Step 1: Collect data from multiple sources.
        
        Args:
            sources: List of sources to collect from
            
        Returns:
            Collection summary
        """
        print("\n" + "="*60)
        print("STEP 1: DATA COLLECTION")
        print("="*60)
        
        if sources is None:
            sources = ["ensembl", "clinvar", "tcga"]
        
        collection_results = {}
        
        # Collect from Ensembl
        if "ensembl" in sources:
            try:
                from data_collection.ensembl_collector import EnsemblCollector
                
                collector = EnsemblCollector(
                    output_dir=str(self.output_dir / "raw" / "ensembl")
                )
                
                # Collect gene information for cancer-related genes
                result = collector.collect_data(
                    data_type="genes",
                    genes=['TP53', 'BRCA1', 'BRCA2', 'EGFR', 'KRAS', 'BRAF', 
                           'PIK3CA', 'PTEN', 'RB1', 'MYC']
                )
                
                collection_results["ensembl"] = {
                    "status": "success",
                    "genes_collected": result.get("samples_collected", 0),
                    "files": result.get("files_created", [])
                }
                print(f"[OK] Ensembl: {result.get('samples_collected', 0)} genes")
                
            except Exception as e:
                collection_results["ensembl"] = {"status": "failed", "error": str(e)}
                print(f"[FAIL] Ensembl: {e}")
        
        # Collect from ClinVar
        if "clinvar" in sources:
            try:
                from data_collection.clinvar_collector import ClinvarCollector
                
                collector = ClinvarCollector(
                    output_dir=str(self.output_dir / "raw" / "clinvar")
                )
                
                result = collector.collect_data(
                    data_type="variants",
                    cancer_type=self.cancer_type,
                    max_results=50
                )
                
                collection_results["clinvar"] = {
                    "status": "success",
                    "variants_collected": result.get("samples_collected", 0),
                    "files": result.get("files_created", [])
                }
                print(f"[OK] ClinVar: {result.get('samples_collected', 0)} variants")
                
            except Exception as e:
                collection_results["clinvar"] = {"status": "failed", "error": str(e)}
                print(f"[FAIL] ClinVar: {e}")
        
        # Collect from TCGA
        if "tcga" in sources:
            try:
                from data_collection.tcga_collector import TCGACollector
                
                collector = TCGACollector(
                    output_dir=str(self.output_dir / "raw" / "tcga")
                )
                
                # Collect cases
                result_cases = collector.collect_data(
                    data_type="cases",
                    cancer_type=self.cancer_type,
                    sample_limit=50
                )
                
                # Collect mutations
                result_mutations = collector.collect_data(
                    data_type="mutations",
                    cancer_type=self.cancer_type,
                    sample_limit=100
                )
                
                collection_results["tcga"] = {
                    "status": "success",
                    "cases_collected": result_cases.get("samples_collected", 0),
                    "mutations_collected": result_mutations.get("mutations_collected", 0),
                    "files": result_cases.get("files_created", []) + result_mutations.get("files_created", [])
                }
                print(f"[OK] TCGA: {result_cases.get('samples_collected', 0)} cases, "
                      f"{result_mutations.get('mutations_collected', 0)} mutations")
                
            except Exception as e:
                collection_results["tcga"] = {"status": "failed", "error": str(e)}
                print(f"[FAIL] TCGA: {e}")
        
        self.state["steps_completed"].append("collect_data")
        self.state["data"]["collection"] = collection_results
        
        return collection_results
    
    def preprocess_data(self) -> Dict[str, Any]:
        """
        Step 2: Preprocess and clean collected data.
        
        Returns:
            Preprocessing summary
        """
        print("\n" + "="*60)
        print("STEP 2: DATA PREPROCESSING")
        print("="*60)
        
        preprocessing_results = {}
        
        try:
            from data_collection.data_preprocessing import (
                DataPreprocessor, 
                preprocess_mutation_data
            )
            
            preprocessor = DataPreprocessor()
            
            # Load and preprocess TCGA mutations if available
            tcga_mutation_files = list(
                (self.output_dir / "raw" / "tcga").glob("tcga_mutations_*.csv")
            )
            
            if tcga_mutation_files:
                df = pd.read_csv(tcga_mutation_files[0])
                
                # Standardize gene names
                if 'gene_symbol' in df.columns:
                    df = preprocessor.standardize_gene_names(df, 'gene_symbol')
                
                # Calculate quality metrics
                quality = preprocessor.calculate_quality_metrics(df)
                
                # Save preprocessed data
                processed_dir = self.output_dir / "processed"
                processed_dir.mkdir(exist_ok=True)
                
                output_file = processed_dir / f"mutations_processed_{self.cancer_type}.csv"
                df.to_csv(output_file, index=False)
                
                preprocessing_results["mutations"] = {
                    "status": "success",
                    "rows": len(df),
                    "columns": list(df.columns),
                    "quality_metrics": quality,
                    "output_file": str(output_file)
                }
                print(f"[OK] Processed mutations: {len(df)} rows")
            
            # Load and preprocess ClinVar variants if available
            clinvar_files = list(
                (self.output_dir / "raw" / "clinvar").glob("clinvar_*.csv")
            )
            
            if clinvar_files:
                df = pd.read_csv(clinvar_files[0])
                
                # Basic cleaning
                df = preprocessor.clean_dataframe(df)
                
                output_file = processed_dir / f"clinvar_processed_{self.cancer_type}.csv"
                df.to_csv(output_file, index=False)
                
                preprocessing_results["clinvar"] = {
                    "status": "success",
                    "rows": len(df),
                    "output_file": str(output_file)
                }
                print(f"[OK] Processed ClinVar: {len(df)} variants")
                
        except Exception as e:
            preprocessing_results["error"] = str(e)
            print(f"[FAIL] Preprocessing error: {e}")
        
        self.state["steps_completed"].append("preprocess_data")
        self.state["data"]["preprocessing"] = preprocessing_results
        
        return preprocessing_results
    
    def analyze_data(self, use_r: bool = True) -> Dict[str, Any]:
        """
        Step 3: Statistical analysis.
        
        Args:
            use_r: Whether to use R for analysis
            
        Returns:
            Analysis results
        """
        print("\n" + "="*60)
        print("STEP 3: STATISTICAL ANALYSIS")
        print("="*60)
        
        analysis_results = {}
        
        # Python-based analysis
        try:
            # Load processed mutations
            processed_dir = self.output_dir / "processed"
            mutation_files = list(processed_dir.glob("mutations_processed_*.csv"))
            
            if mutation_files:
                df = pd.read_csv(mutation_files[0])
                
                # Mutation frequency analysis
                if 'gene_symbol' in df.columns:
                    gene_counts = df['gene_symbol'].value_counts().head(20)
                    
                    analysis_results["mutation_frequency"] = {
                        "top_genes": gene_counts.to_dict(),
                        "total_mutations": len(df),
                        "unique_genes": df['gene_symbol'].nunique()
                    }
                    print(f"[OK] Mutation frequency: {df['gene_symbol'].nunique()} unique genes")
                
                # Consequence type distribution
                if 'consequence_type' in df.columns:
                    consequence_counts = df['consequence_type'].value_counts().to_dict()
                    analysis_results["consequence_distribution"] = consequence_counts
                    print(f"[OK] Consequence types: {len(consequence_counts)} types")
                    
        except Exception as e:
            analysis_results["python_analysis_error"] = str(e)
            print(f"[FAIL] Python analysis: {e}")
        
        # R-based analysis
        if use_r:
            try:
                from CancerGenomicsSuite.modules.r_integration.r_client import RClient
                
                r_client = RClient()
                status = r_client.get_r_status()
                
                if status.get("rpy2_available"):
                    # Test R calculation
                    result = r_client.execute_r_script("cat(mean(1:100))")
                    
                    analysis_results["r_integration"] = {
                        "status": "available",
                        "r_version": status.get("r_version"),
                        "test_result": result.get("stdout", "").strip()
                    }
                    print(f"[OK] R integration: {status.get('r_version', 'Unknown')}")
                    
                    # Check for DESeq2
                    if r_client.check_package_installed("DESeq2"):
                        analysis_results["deseq2_available"] = True
                        print("[OK] DESeq2: Available for differential expression")
                    
                    if r_client.check_package_installed("limma"):
                        analysis_results["limma_available"] = True
                        print("[OK] limma: Available for microarray analysis")
                else:
                    analysis_results["r_integration"] = {
                        "status": "subprocess_only",
                        "r_version": status.get("r_version")
                    }
                    print(f"[OK] R available via subprocess: {status.get('r_version', 'Unknown')}")
                    
            except Exception as e:
                analysis_results["r_error"] = str(e)
                print(f"[WARN] R integration: {e}")
        
        self.state["steps_completed"].append("analyze_data")
        self.state["results"]["analysis"] = analysis_results
        
        return analysis_results
    
    def visualize_results(self) -> Dict[str, Any]:
        """
        Step 4: Generate visualizations.
        
        Returns:
            Visualization summary
        """
        print("\n" + "="*60)
        print("STEP 4: VISUALIZATION")
        print("="*60)
        
        viz_results = {}
        plots_dir = self.output_dir / "plots"
        plots_dir.mkdir(exist_ok=True)
        
        try:
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            import matplotlib.pyplot as plt
            
            analysis = self.state.get("results", {}).get("analysis", {})
            
            # Plot 1: Mutation frequency bar chart
            if "mutation_frequency" in analysis:
                top_genes = analysis["mutation_frequency"].get("top_genes", {})
                
                if top_genes:
                    fig, ax = plt.subplots(figsize=(12, 6))
                    genes = list(top_genes.keys())[:15]
                    counts = [top_genes[g] for g in genes]
                    
                    ax.barh(genes, counts, color='steelblue')
                    ax.set_xlabel('Number of Mutations')
                    ax.set_ylabel('Gene')
                    ax.set_title(f'Top Mutated Genes in {self.cancer_type}')
                    ax.invert_yaxis()
                    
                    plt.tight_layout()
                    plot_file = plots_dir / f"mutation_frequency_{self.cancer_type}.png"
                    plt.savefig(plot_file, dpi=150)
                    plt.close()
                    
                    viz_results["mutation_frequency_plot"] = str(plot_file)
                    print(f"[OK] Created: {plot_file.name}")
            
            # Plot 2: Consequence type pie chart
            if "consequence_distribution" in analysis:
                conseq = analysis["consequence_distribution"]
                
                if conseq:
                    fig, ax = plt.subplots(figsize=(10, 10))
                    
                    # Take top 8 types
                    sorted_conseq = sorted(conseq.items(), key=lambda x: x[1], reverse=True)[:8]
                    labels = [c[0] for c in sorted_conseq]
                    sizes = [c[1] for c in sorted_conseq]
                    
                    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
                    ax.set_title(f'Mutation Consequence Types in {self.cancer_type}')
                    
                    plt.tight_layout()
                    plot_file = plots_dir / f"consequence_types_{self.cancer_type}.png"
                    plt.savefig(plot_file, dpi=150)
                    plt.close()
                    
                    viz_results["consequence_plot"] = str(plot_file)
                    print(f"[OK] Created: {plot_file.name}")
            
        except Exception as e:
            viz_results["error"] = str(e)
            print(f"[FAIL] Visualization: {e}")
        
        self.state["steps_completed"].append("visualize_results")
        self.state["results"]["visualization"] = viz_results
        
        return viz_results
    
    def generate_report(self) -> str:
        """
        Step 5: Generate final workflow report.
        
        Returns:
            Path to report file
        """
        print("\n" + "="*60)
        print("STEP 5: REPORT GENERATION")
        print("="*60)
        
        self.state["completed_at"] = datetime.now().isoformat()
        
        # Save JSON report
        report_file = self.output_dir / f"workflow_report_{self.workflow_id}.json"
        with open(report_file, 'w') as f:
            json.dump(self.state, f, indent=2, default=str)
        
        print(f"[OK] JSON report: {report_file}")
        
        # Generate markdown summary
        md_report = self._generate_markdown_report()
        md_file = self.output_dir / f"workflow_summary_{self.workflow_id}.md"
        with open(md_file, 'w') as f:
            f.write(md_report)
        
        print(f"[OK] Markdown report: {md_file}")
        
        self.state["steps_completed"].append("generate_report")
        
        return str(report_file)
    
    def _generate_markdown_report(self) -> str:
        """Generate markdown summary report."""
        
        analysis = self.state.get("results", {}).get("analysis", {})
        collection = self.state.get("data", {}).get("collection", {})
        
        report = f"""# Cancer Genomics Analysis Workflow Report

## Workflow Information
- **ID**: {self.workflow_id}
- **Cancer Type**: {self.cancer_type}
- **Started**: {self.state.get('started_at', 'N/A')}
- **Completed**: {self.state.get('completed_at', 'N/A')}

## Data Collection Summary

| Source | Status | Records |
|--------|--------|---------|
"""
        
        for source, data in collection.items():
            status = data.get("status", "unknown")
            if status == "success":
                records = (data.get("genes_collected", 0) or 
                          data.get("variants_collected", 0) or
                          data.get("cases_collected", 0) or
                          data.get("mutations_collected", 0))
                report += f"| {source.upper()} | {status} | {records} |\n"
            else:
                report += f"| {source.upper()} | {status} | - |\n"
        
        if "mutation_frequency" in analysis:
            mf = analysis["mutation_frequency"]
            report += f"""
## Mutation Analysis

- **Total Mutations**: {mf.get('total_mutations', 'N/A')}
- **Unique Genes**: {mf.get('unique_genes', 'N/A')}

### Top Mutated Genes
"""
            for gene, count in list(mf.get('top_genes', {}).items())[:10]:
                report += f"- {gene}: {count} mutations\n"
        
        report += f"""
## R Integration

- **Status**: {analysis.get('r_integration', {}).get('status', 'N/A')}
- **R Version**: {analysis.get('r_integration', {}).get('r_version', 'N/A')}
- **DESeq2**: {'Available' if analysis.get('deseq2_available') else 'Not checked'}
- **limma**: {'Available' if analysis.get('limma_available') else 'Not checked'}

## Output Files

Generated files are located in: `{self.output_dir}`

---
*Report generated by Cancer Genomics Analysis Suite*
"""
        return report
    
    def run_full_workflow(self, sources: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run the complete workflow end-to-end.
        
        Args:
            sources: Data sources to collect from
            
        Returns:
            Complete workflow results
        """
        print("\n" + "#"*60)
        print("# CANCER GENOMICS ANALYSIS WORKFLOW")
        print("#"*60)
        print(f"# Cancer Type: {self.cancer_type}")
        print(f"# Workflow ID: {self.workflow_id}")
        print("#"*60)
        
        # Execute workflow steps
        self.collect_data(sources)
        self.preprocess_data()
        self.analyze_data()
        self.visualize_results()
        report_path = self.generate_report()
        
        print("\n" + "#"*60)
        print("# WORKFLOW COMPLETE")
        print("#"*60)
        print(f"# Report: {report_path}")
        print("#"*60)
        
        return self.state


def main():
    """Run sample workflow."""
    workflow = CancerGenomicsWorkflow(
        output_dir="data/workflow_output",
        cancer_type="BRCA"
    )
    
    results = workflow.run_full_workflow(
        sources=["ensembl", "clinvar", "tcga"]
    )
    
    return results


if __name__ == "__main__":
    main()
