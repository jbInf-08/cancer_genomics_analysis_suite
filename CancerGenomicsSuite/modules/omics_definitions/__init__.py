"""
Comprehensive Omics Definitions Module

This module provides comprehensive definitions, metadata, and utilities for all omics fields
in cancer genomics analysis. It serves as the central registry for all omics types and their
associated data structures, processing methods, and analysis pipelines.

Main Components:
- OmicsFieldRegistry: Central registry for all omics field definitions
- OmicsDataProcessor: Standardized data processing for all omics types
- OmicsMetadataManager: Metadata management for omics datasets
- OmicsIntegrationEngine: Advanced integration algorithms for multi-omics analysis
"""

from .omics_registry import (
    OmicsFieldRegistry,
    OmicsFieldDefinition,
    OmicsDataType,
    OmicsAnalysisType
)
from .omics_processor import (
    OmicsDataProcessor,
    OmicsDataValidator,
    OmicsQualityControl
)
from .omics_metadata import (
    OmicsMetadataManager,
    OmicsSampleMetadata,
    OmicsFeatureMetadata
)
from .omics_integration import (
    OmicsIntegrationEngine,
    OmicsCorrelationAnalyzer,
    OmicsNetworkBuilder
)

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite"

__all__ = [
    'OmicsFieldRegistry',
    'OmicsFieldDefinition', 
    'OmicsDataType',
    'OmicsAnalysisType',
    'OmicsDataProcessor',
    'OmicsDataValidator',
    'OmicsQualityControl',
    'OmicsMetadataManager',
    'OmicsSampleMetadata',
    'OmicsFeatureMetadata',
    'OmicsIntegrationEngine',
    'OmicsCorrelationAnalyzer',
    'OmicsNetworkBuilder'
]

# Module metadata
MODULE_INFO = {
    'name': 'Comprehensive Omics Definitions',
    'version': __version__,
    'description': 'Complete omics field definitions and processing framework for cancer genomics',
    'features': [
        'Comprehensive omics field registry (50+ omics types)',
        'Standardized data processing pipelines',
        'Advanced multi-omics integration algorithms',
        'Quality control and validation frameworks',
        'Metadata management and annotation',
        'Network analysis and correlation tools',
        'Interactive visualization components'
    ],
    'supported_omics_types': [
        # Core Genomics-Related Omics
        'genomics', 'transcriptomics', 'proteomics', 'metabolomics', 'epigenomics',
        # Structural and Functional Omics  
        'connectomics', 'interactomics', 'secretomics', 'degradomics', 'glycomics', 'lipidomics',
        # Specialized Omics
        'pharmacogenomics', 'nutrigenomics', 'toxicogenomics', 'immunogenomics', 
        'neurogenomics', 'pharmacoproteomics',
        # Microbiome and Environmental Omics
        'metagenomics', 'microbiomics', 'exposomics',
        # Emerging and Specialized Fields
        'fluxomics', 'phenomics', 'kinomics', 'phosphoproteomics', 'ubiquitomics', 
        'chromatomics', 'acetylomics', 'allergomics', 'bibliomics', 'cytomics',
        'editomics', 'foodomics', 'hologenomics', 'ionomics', 'membranomics',
        'metallomics', 'methylomics', 'obesomics', 'organomics', 'parvomics',
        'physiomics', 'regulomics', 'speechomics', 'synaptomics', 'synthetomics',
        'toponomics', 'toxomics', 'antibodyomics', 'embryomics', 'interferomics',
        'mechanomics', 'researchomics', 'trialomics', 'dynomics'
    ],
    'dependencies': [
        'pandas', 'numpy', 'scipy', 'scikit-learn', 'plotly', 'dash',
        'networkx', 'matplotlib', 'seaborn', 'biopython', 'pybedtools',
        'pysam', 'h5py', 'zarr', 'anndata', 'scanpy', 'leidenalg'
    ]
}
