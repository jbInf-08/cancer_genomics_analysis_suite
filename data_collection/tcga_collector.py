"""
TCGA Data Collector via GDC API

This module provides data collection capabilities for The Cancer Genome Atlas (TCGA)
through the Genomic Data Commons (GDC) REST API.

API Documentation: https://docs.gdc.cancer.gov/API/Users_Guide/Getting_Started/
Rate Limits: No strict rate limit, but please be considerate.
Authentication: Not required for public data.
"""

import pandas as pd
import requests
import json
import time
from typing import Dict, List, Any, Optional
from .base_collector import DataCollectorBase


class TCGACollector(DataCollectorBase):
    """
    Data collector for The Cancer Genome Atlas (TCGA) via GDC API.
    
    TCGA provides:
    - Gene expression data (RNA-seq)
    - Somatic mutations (WES, WGS)
    - Copy number alterations
    - DNA methylation
    - Clinical data
    - Protein expression
    
    Data is accessed through the NCI Genomic Data Commons (GDC) portal.
    No authentication required for public data.
    """
    
    # TCGA project IDs for common cancer types
    CANCER_PROJECT_IDS = {
        'BRCA': 'TCGA-BRCA',   # Breast invasive carcinoma
        'LUAD': 'TCGA-LUAD',   # Lung adenocarcinoma
        'LUSC': 'TCGA-LUSC',   # Lung squamous cell carcinoma
        'COAD': 'TCGA-COAD',   # Colon adenocarcinoma
        'PRAD': 'TCGA-PRAD',   # Prostate adenocarcinoma
        'STAD': 'TCGA-STAD',   # Stomach adenocarcinoma
        'OV': 'TCGA-OV',       # Ovarian serous cystadenocarcinoma
        'GBM': 'TCGA-GBM',     # Glioblastoma multiforme
        'HNSC': 'TCGA-HNSC',   # Head and neck squamous cell carcinoma
        'KIRC': 'TCGA-KIRC',   # Kidney renal clear cell carcinoma
        'LIHC': 'TCGA-LIHC',   # Liver hepatocellular carcinoma
        'THCA': 'TCGA-THCA',   # Thyroid carcinoma
        'BLCA': 'TCGA-BLCA',   # Bladder urothelial carcinoma
        'SKCM': 'TCGA-SKCM',   # Skin cutaneous melanoma
        'PAAD': 'TCGA-PAAD',   # Pancreatic adenocarcinoma
    }
    
    def __init__(self, output_dir: str = "data/external_sources/tcga", **kwargs):
        """Initialize TCGA collector."""
        super().__init__(output_dir, **kwargs)
        self.base_url = self.config.get("base_url", "https://api.gdc.cancer.gov")
        self.sample_limit = self.config.get("sample_limit", 100)
        self.cancer_types = self.config.get("cancer_types", ["BRCA", "LUAD", "COAD", "PRAD"])
        self.data_types = self.config.get("data_types", ["cases", "mutations", "clinical"])
        
        # GDC API requires slower requests
        self.min_request_interval = 0.2
    
    def _build_filter(self, field: str, value: Any, op: str = "=") -> Dict:
        """Build a GDC filter object."""
        return {
            "op": op,
            "content": {
                "field": field,
                "value": value
            }
        }
    
    def _make_gdc_request(self, endpoint: str, filters: Optional[Dict] = None,
                          fields: Optional[List[str]] = None, 
                          size: int = 100, from_: int = 0) -> Dict:
        """
        Make a request to the GDC API.
        
        Args:
            endpoint: API endpoint (e.g., 'cases', 'files', 'projects')
            filters: Filter dictionary
            fields: List of fields to return
            size: Number of results
            from_: Starting index
            
        Returns:
            API response as dictionary
        """
        url = f"{self.base_url}/{endpoint}"
        
        params = {
            "size": size,
            "from": from_,
            "pretty": "false"
        }
        
        if filters:
            params["filters"] = json.dumps(filters)
        
        if fields:
            params["fields"] = ",".join(fields)
        
        response = self.make_request(url, params=params, auth_type='none')
        
        if response.status_code == 200:
            return response.json()
        else:
            self.logger.error(f"GDC API error: {response.status_code} - {response.text[:200]}")
            return {"data": {"hits": []}, "pagination": {"total": 0}}
    
    def collect_data(self, 
                    data_type: str = "cases",
                    cancer_type: str = "BRCA",
                    sample_limit: Optional[int] = None,
                    **kwargs) -> Dict[str, Any]:
        """
        Collect data from TCGA via GDC API.
        
        Args:
            data_type: Type of data ('cases', 'mutations', 'clinical', 'files')
            cancer_type: Cancer type abbreviation (e.g., 'BRCA', 'LUAD')
            sample_limit: Maximum number of samples
            
        Returns:
            Dictionary containing collection results
        """
        if sample_limit is None:
            sample_limit = self.sample_limit
        
        self.logger.info(f"Collecting {data_type} data for {cancer_type} from TCGA/GDC")
        
        try:
            if data_type == "cases":
                return self._collect_cases(cancer_type, sample_limit)
            elif data_type == "mutations":
                return self._collect_ssm_mutations(cancer_type, sample_limit)
            elif data_type == "clinical":
                return self._collect_clinical_data(cancer_type, sample_limit)
            elif data_type == "files":
                return self._collect_file_metadata(cancer_type, sample_limit)
            elif data_type == "genes":
                return self._collect_genes(cancer_type, sample_limit)
            else:
                raise ValueError(f"Unsupported data type: {data_type}")
                
        except Exception as e:
            self.logger.error(f"Failed to collect {data_type} data: {e}")
            raise
    
    def _collect_cases(self, cancer_type: str, sample_limit: int) -> Dict[str, Any]:
        """
        Collect case/sample information for a cancer type.
        
        Args:
            cancer_type: Cancer type abbreviation
            sample_limit: Maximum samples to collect
            
        Returns:
            Collection results
        """
        project_id = self.CANCER_PROJECT_IDS.get(cancer_type, f"TCGA-{cancer_type}")
        
        filters = {
            "op": "=",
            "content": {
                "field": "project.project_id",
                "value": project_id
            }
        }
        
        fields = [
            "submitter_id",
            "case_id",
            "primary_site",
            "disease_type",
            "project.project_id",
            "project.name",
            "demographic.gender",
            "demographic.race",
            "demographic.ethnicity",
            "demographic.vital_status",
            "demographic.days_to_death",
            "demographic.age_at_index",
            "diagnoses.primary_diagnosis",
            "diagnoses.tumor_stage",
            "diagnoses.tumor_grade",
            "diagnoses.age_at_diagnosis",
            "diagnoses.days_to_last_follow_up",
            "diagnoses.vital_status"
        ]
        
        result = self._make_gdc_request(
            "cases",
            filters=filters,
            fields=fields,
            size=sample_limit
        )
        
        hits = result.get("data", {}).get("hits", [])
        
        if not hits:
            self.logger.warning(f"No cases found for {cancer_type}")
            return {"samples_collected": 0, "files_created": []}
        
        # Parse case data
        cases_data = []
        for case in hits:
            demo = case.get("demographic", {}) or {}
            diag = case.get("diagnoses", [{}])[0] if case.get("diagnoses") else {}
            proj = case.get("project", {}) or {}
            
            cases_data.append({
                "case_id": case.get("case_id", ""),
                "submitter_id": case.get("submitter_id", ""),
                "project_id": proj.get("project_id", ""),
                "project_name": proj.get("name", ""),
                "primary_site": case.get("primary_site", ""),
                "disease_type": case.get("disease_type", ""),
                "gender": demo.get("gender", ""),
                "race": demo.get("race", ""),
                "ethnicity": demo.get("ethnicity", ""),
                "vital_status": demo.get("vital_status", ""),
                "days_to_death": demo.get("days_to_death", ""),
                "age_at_index": demo.get("age_at_index", ""),
                "primary_diagnosis": diag.get("primary_diagnosis", ""),
                "tumor_stage": diag.get("tumor_stage", ""),
                "tumor_grade": diag.get("tumor_grade", ""),
                "age_at_diagnosis": diag.get("age_at_diagnosis", ""),
                "days_to_last_follow_up": diag.get("days_to_last_follow_up", ""),
            })
        
        df = pd.DataFrame(cases_data)
        
        filename = self.generate_filename("cases", cancer_type, len(df))
        filepath = self.save_data(df, filename, "csv")
        json_path = self.save_data(cases_data, filename.replace('.csv', ''), "json")
        
        return {
            "samples_collected": len(df),
            "data_type": "cases",
            "cancer_type": cancer_type,
            "files_created": [filepath, json_path]
        }
    
    def _collect_ssm_mutations(self, cancer_type: str, sample_limit: int) -> Dict[str, Any]:
        """
        Collect Simple Somatic Mutations (SSM) from GDC.
        
        Args:
            cancer_type: Cancer type abbreviation
            sample_limit: Maximum mutations to collect
            
        Returns:
            Collection results
        """
        project_id = self.CANCER_PROJECT_IDS.get(cancer_type, f"TCGA-{cancer_type}")
        
        filters = {
            "op": "=",
            "content": {
                "field": "cases.project.project_id",
                "value": project_id
            }
        }
        
        fields = [
            "ssm_id",
            "genomic_dna_change",
            "chromosome",
            "start_position",
            "end_position",
            "reference_allele",
            "tumor_allele",
            "consequence.transcript.gene.symbol",
            "consequence.transcript.consequence_type",
            "consequence.transcript.aa_change",
            "ncbi_build"
        ]
        
        result = self._make_gdc_request(
            "ssms",
            filters=filters,
            fields=fields,
            size=sample_limit
        )
        
        hits = result.get("data", {}).get("hits", [])
        
        if not hits:
            self.logger.warning(f"No mutations found for {cancer_type}")
            return {"samples_collected": 0, "files_created": []}
        
        # Parse mutation data
        mutations_data = []
        for mut in hits:
            conseqs = mut.get("consequence", [])
            for conseq in conseqs[:1]:  # Take first consequence
                transcript = conseq.get("transcript", {}) or {}
                gene = transcript.get("gene", {}) or {}
                
                mutations_data.append({
                    "ssm_id": mut.get("ssm_id", ""),
                    "genomic_dna_change": mut.get("genomic_dna_change", ""),
                    "chromosome": mut.get("chromosome", ""),
                    "start_position": mut.get("start_position", ""),
                    "end_position": mut.get("end_position", ""),
                    "reference_allele": mut.get("reference_allele", ""),
                    "tumor_allele": mut.get("tumor_allele", ""),
                    "gene_symbol": gene.get("symbol", ""),
                    "consequence_type": transcript.get("consequence_type", ""),
                    "aa_change": transcript.get("aa_change", ""),
                    "ncbi_build": mut.get("ncbi_build", ""),
                })
        
        df = pd.DataFrame(mutations_data)
        
        filename = self.generate_filename("mutations", cancer_type, len(df))
        filepath = self.save_data(df, filename, "csv")
        json_path = self.save_data(mutations_data, filename.replace('.csv', ''), "json")
        
        return {
            "mutations_collected": len(df),
            "unique_genes": len(df['gene_symbol'].unique()) if 'gene_symbol' in df.columns else 0,
            "data_type": "mutations",
            "cancer_type": cancer_type,
            "files_created": [filepath, json_path]
        }
    
    def _collect_clinical_data(self, cancer_type: str, sample_limit: int) -> Dict[str, Any]:
        """
        Collect clinical data (same as cases but focused on clinical fields).
        """
        return self._collect_cases(cancer_type, sample_limit)
    
    def _collect_file_metadata(self, cancer_type: str, sample_limit: int) -> Dict[str, Any]:
        """
        Collect metadata about available files for a cancer type.
        
        Args:
            cancer_type: Cancer type abbreviation
            sample_limit: Maximum files to list
            
        Returns:
            Collection results
        """
        project_id = self.CANCER_PROJECT_IDS.get(cancer_type, f"TCGA-{cancer_type}")
        
        filters = {
            "op": "=",
            "content": {
                "field": "cases.project.project_id",
                "value": project_id
            }
        }
        
        fields = [
            "file_id",
            "file_name",
            "file_size",
            "data_type",
            "data_category",
            "data_format",
            "experimental_strategy",
            "platform",
            "access",
            "state"
        ]
        
        result = self._make_gdc_request(
            "files",
            filters=filters,
            fields=fields,
            size=sample_limit
        )
        
        hits = result.get("data", {}).get("hits", [])
        total = result.get("data", {}).get("pagination", {}).get("total", 0)
        
        if not hits:
            self.logger.warning(f"No files found for {cancer_type}")
            return {"samples_collected": 0, "files_created": []}
        
        # Parse file metadata
        files_data = []
        for f in hits:
            files_data.append({
                "file_id": f.get("file_id", ""),
                "file_name": f.get("file_name", ""),
                "file_size_bytes": f.get("file_size", 0),
                "data_type": f.get("data_type", ""),
                "data_category": f.get("data_category", ""),
                "data_format": f.get("data_format", ""),
                "experimental_strategy": f.get("experimental_strategy", ""),
                "platform": f.get("platform", ""),
                "access": f.get("access", ""),
                "state": f.get("state", ""),
            })
        
        df = pd.DataFrame(files_data)
        
        filename = self.generate_filename("files_metadata", cancer_type, len(df))
        filepath = self.save_data(df, filename, "csv")
        
        # Summarize by data type
        if len(df) > 0:
            summary = df.groupby('data_type').size().to_dict()
            self.logger.info(f"Files by data type: {summary}")
        
        return {
            "files_listed": len(df),
            "total_files_available": total,
            "data_type": "files_metadata",
            "cancer_type": cancer_type,
            "files_created": [filepath]
        }
    
    def _collect_genes(self, cancer_type: str, sample_limit: int) -> Dict[str, Any]:
        """
        Collect gene information for genes mutated in a cancer type.
        
        Args:
            cancer_type: Cancer type abbreviation
            sample_limit: Maximum genes to collect
            
        Returns:
            Collection results
        """
        project_id = self.CANCER_PROJECT_IDS.get(cancer_type, f"TCGA-{cancer_type}")
        
        filters = {
            "op": "=",
            "content": {
                "field": "cases.project.project_id",
                "value": project_id
            }
        }
        
        fields = [
            "gene_id",
            "symbol",
            "name",
            "biotype",
            "gene_chromosome",
            "gene_start",
            "gene_end",
            "gene_strand",
            "is_cancer_gene_census"
        ]
        
        result = self._make_gdc_request(
            "genes",
            filters=filters,
            fields=fields,
            size=sample_limit
        )
        
        hits = result.get("data", {}).get("hits", [])
        
        if not hits:
            self.logger.warning(f"No gene data found for {cancer_type}")
            return {"samples_collected": 0, "files_created": []}
        
        # Parse gene data
        genes_data = []
        for gene in hits:
            genes_data.append({
                "gene_id": gene.get("gene_id", ""),
                "symbol": gene.get("symbol", ""),
                "name": gene.get("name", ""),
                "biotype": gene.get("biotype", ""),
                "chromosome": gene.get("gene_chromosome", ""),
                "start": gene.get("gene_start", ""),
                "end": gene.get("gene_end", ""),
                "strand": gene.get("gene_strand", ""),
                "is_cancer_gene_census": gene.get("is_cancer_gene_census", False),
            })
        
        df = pd.DataFrame(genes_data)
        
        filename = self.generate_filename("genes", cancer_type, len(df))
        filepath = self.save_data(df, filename, "csv")
        json_path = self.save_data(genes_data, filename.replace('.csv', ''), "json")
        
        return {
            "genes_collected": len(df),
            "cancer_gene_census_count": df['is_cancer_gene_census'].sum() if 'is_cancer_gene_census' in df.columns else 0,
            "data_type": "genes",
            "cancer_type": cancer_type,
            "files_created": [filepath, json_path]
        }
    
    def get_available_datasets(self) -> List[Dict[str, Any]]:
        """Get list of available datasets from TCGA/GDC."""
        datasets = []
        
        for cancer_type, project_id in self.CANCER_PROJECT_IDS.items():
            for data_type in ['cases', 'mutations', 'genes', 'files']:
                datasets.append({
                    "data_type": data_type,
                    "cancer_type": cancer_type,
                    "project_id": project_id,
                    "description": f"TCGA {data_type} for {cancer_type}",
                    "source": "GDC API",
                    "requires_auth": False
                })
        
        return datasets
    
    def get_project_summary(self, cancer_type: str) -> Dict[str, Any]:
        """
        Get summary statistics for a TCGA project.
        
        Args:
            cancer_type: Cancer type abbreviation
            
        Returns:
            Project summary statistics
        """
        project_id = self.CANCER_PROJECT_IDS.get(cancer_type, f"TCGA-{cancer_type}")
        
        url = f"{self.base_url}/projects/{project_id}"
        
        try:
            response = self.make_request(url, auth_type='none')
            
            if response.status_code == 200:
                data = response.json().get("data", {})
                return {
                    "project_id": project_id,
                    "name": data.get("name", ""),
                    "primary_site": data.get("primary_site", []),
                    "disease_type": data.get("disease_type", []),
                    "dbgap_accession_number": data.get("dbgap_accession_number", ""),
                    "summary": data.get("summary", {})
                }
            else:
                return {"error": f"API returned {response.status_code}"}
                
        except Exception as e:
            return {"error": str(e)}
