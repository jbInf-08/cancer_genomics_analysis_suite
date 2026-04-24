"""
Omics Processors Package

This package contains specialized processors for different omics fields,
providing field-specific data processing, analysis, and visualization capabilities.
"""

# Core Genomics-Related Omics
from .genomics_processor import GenomicsProcessor
from .transcriptomics_processor import TranscriptomicsProcessor
from .proteomics_processor import ProteomicsProcessor
from .metabolomics_processor import MetabolomicsProcessor
from .epigenomics_processor import EpigenomicsProcessor

# Structural and Functional Omics
from .structural_functional_omics import (
    ConnectomicsProcessor, InteractomicsProcessor, SecretomicsProcessor,
    DegradomicsProcessor, GlycomicsProcessor, LipidomicsProcessor
)

# Specialized Omics
from .specialized_omics import (
    PharmacogenomicsProcessor, NutrigenomicsProcessor, ToxicogenomicsProcessor,
    ImmunogenomicsProcessor, NeurogenomicsProcessor, PharmacoproteomicsProcessor
)

# Microbiome and Environmental Omics
from .microbiome_environmental_omics import (
    MetagenomicsProcessor, MicrobiomicsProcessor, ExposomicsProcessor
)

# Emerging and Specialized Fields
from .emerging_specialized_omics import (
    FluxomicsProcessor, PhenomicsProcessor, KinomicsProcessor,
    PhosphoproteomicsProcessor, UbiquitomicsProcessor, ChromatomicsProcessor
)

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite"

__all__ = [
    # Core Genomics-Related Omics
    'GenomicsProcessor',
    'TranscriptomicsProcessor', 
    'ProteomicsProcessor',
    'MetabolomicsProcessor',
    'EpigenomicsProcessor',
    
    # Structural and Functional Omics
    'ConnectomicsProcessor',
    'InteractomicsProcessor',
    'SecretomicsProcessor',
    'DegradomicsProcessor',
    'GlycomicsProcessor',
    'LipidomicsProcessor',
    
    # Specialized Omics
    'PharmacogenomicsProcessor',
    'NutrigenomicsProcessor',
    'ToxicogenomicsProcessor',
    'ImmunogenomicsProcessor',
    'NeurogenomicsProcessor',
    'PharmacoproteomicsProcessor',
    
    # Microbiome and Environmental Omics
    'MetagenomicsProcessor',
    'MicrobiomicsProcessor',
    'ExposomicsProcessor',
    
    # Emerging and Specialized Fields
    'FluxomicsProcessor',
    'PhenomicsProcessor',
    'KinomicsProcessor',
    'PhosphoproteomicsProcessor',
    'UbiquitomicsProcessor',
    'ChromatomicsProcessor'
]

# Module metadata
MODULE_INFO = {
    'name': 'Omics Processors',
    'version': __version__,
    'description': 'Comprehensive specialized processors for all omics fields',
    'features': [
        # Core Genomics-Related Omics
        'Genomics data processing and analysis',
        'Transcriptomics expression analysis',
        'Proteomics protein analysis',
        'Metabolomics metabolite analysis',
        'Epigenomics modification analysis',
        
        # Structural and Functional Omics
        'Connectomics neural connectivity analysis',
        'Interactomics protein interaction analysis',
        'Secretomics secreted protein analysis',
        'Degradomics protein degradation analysis',
        'Glycomics glycan analysis',
        'Lipidomics lipid analysis',
        
        # Specialized Omics
        'Pharmacogenomics drug response analysis',
        'Nutrigenomics nutrition-gene interaction analysis',
        'Toxicogenomics toxicity analysis',
        'Immunogenomics immune response analysis',
        'Neurogenomics neural analysis',
        'Pharmacoproteomics drug-protein interaction analysis',
        
        # Microbiome and Environmental Omics
        'Metagenomics taxonomic analysis',
        'Microbiomics microbiome analysis',
        'Exposomics exposure analysis',
        
        # Emerging and Specialized Fields
        'Fluxomics metabolic flux analysis',
        'Phenomics phenotype analysis',
        'Kinomics kinase activity analysis',
        'Phosphoproteomics phosphorylation analysis',
        'Ubiquitomics ubiquitination analysis',
        'Chromatomics chromatin analysis'
    ],
    'supported_omics_types': [
        # Core Genomics-Related Omics
        'genomics', 'transcriptomics', 'proteomics', 'metabolomics', 'epigenomics',
        
        # Structural and Functional Omics
        'connectomics', 'interactomics', 'secretomics', 'degradomics', 'glycomics', 'lipidomics',
        
        # Specialized Omics
        'pharmacogenomics', 'nutrigenomics', 'toxicogenomics', 'immunogenomics', 'neurogenomics', 'pharmacoproteomics',
        
        # Microbiome and Environmental Omics
        'metagenomics', 'microbiomics', 'exposomics',
        
        # Emerging and Specialized Fields
        'fluxomics', 'phenomics', 'kinomics', 'phosphoproteomics', 'ubiquitomics', 'chromatomics'
    ],
    'dependencies': [
        'pandas', 'numpy', 'scipy', 'scikit-learn', 'plotly', 'dash',
        'biopython', 'pybedtools', 'pysam', 'h5py', 'zarr', 'networkx'
    ]
}
