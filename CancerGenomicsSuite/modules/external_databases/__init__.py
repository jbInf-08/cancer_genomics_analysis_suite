"""
External Database Integration Module for Cancer Genomics Analysis Suite

This module provides integration with external drug and biomarker databases including:
- DrugBank integration for drug information
- ChEMBL integration for chemical and biological data
- PubChem integration for chemical structures and properties
- Biomarker databases integration
- Clinical trial databases integration
- Literature databases integration
"""

from .drug_databases import (
    ChEMBLClient,
    DrugBankClient,
    DrugDatabaseIntegrator,
    PubChemClient,
)

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite Team"

__all__ = [
    "DrugBankClient",
    "ChEMBLClient",
    "PubChemClient",
    "DrugDatabaseIntegrator",
]

try:
    from .biomarker_databases import (
        BiomarkerDatabaseClient,
        ClinicalBiomarkerIntegrator,
        LiteratureBiomarkerClient,
    )

    __all__.extend(
        [
            "BiomarkerDatabaseClient",
            "ClinicalBiomarkerIntegrator",
            "LiteratureBiomarkerClient",
        ]
    )
except ImportError:
    pass

try:
    from .clinical_databases import (
        ClinicalTrialsClient,
        EMAApprovalClient,
        FDAApprovalClient,
    )

    __all__.extend(
        [
            "ClinicalTrialsClient",
            "FDAApprovalClient",
            "EMAApprovalClient",
        ]
    )
except ImportError:
    pass

try:
    from .database_manager import CacheManager, DatabaseManager, DataSynchronizer

    __all__.extend(["DatabaseManager", "DataSynchronizer", "CacheManager"])
except ImportError:
    pass
