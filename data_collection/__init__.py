"""
Comprehensive Data Collection System for Cancer Genomics Analysis Suite

This module provides a comprehensive data collection system for gathering
biomarker data from ALL major biomedical data sources including:

- Genomic & Expression Data (TCGA, GEO, ICGC, EGA, GDC, NCBI)
- Clinical & Registry Data (SEER, NCDB, CDC, NIH, NCI)
- Imaging & Radiomics Data (TCIA, MICCAI, Prostate-X, CAMELYON, etc.)
- Mutation & Variant Data (COSMIC, ClinVar, OncoKB)
- Drug & Cell Line Data (CCLE, GDSC, NCI-60)
- Literature & Research Data (PubMed, cBioPortal, FireCloud/Terra)
- Challenge & Competition Data (PathLAION, MIMIC, Kaggle)

The system includes:
- 40+ Individual Data Collectors
- Master Orchestrator for coordinated collection
- Comprehensive Testing Suite
- Configuration Management
- Error Handling & Logging
- Data Validation & Quality Control
"""

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite"

from .base_collector import DataCollectorBase
from .master_orchestrator import MasterDataOrchestrator
from .run_data_collection import ComprehensiveDataCollector

__all__ = [
    "DataCollectorBase",
    "MasterDataOrchestrator", 
    "ComprehensiveDataCollector"
]
