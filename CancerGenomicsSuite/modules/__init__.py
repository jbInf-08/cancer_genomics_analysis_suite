"""
Cancer Genomics Analysis Suite - Modules Package

This package contains all the analysis modules for the Cancer Genomics Analysis Suite,
including biomarker discovery, drug analysis, and integration capabilities.
"""

# Import biomarker discovery modules
try:
    from .biomarker_discovery import (
        BiomarkerAnalyzer,
        StatisticalBiomarkerDiscovery,
        MLBiomarkerDiscovery,
        BiomarkerValidator,
        BiomarkerDiscoveryDashboard,
        BiomarkerVisualizationEngine
    )
    _BIOMARKER_DISCOVERY_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Biomarker discovery modules not available: {e}")
    _BIOMARKER_DISCOVERY_AVAILABLE = False
    # Set dummy classes
    BiomarkerAnalyzer = None
    StatisticalBiomarkerDiscovery = None
    MLBiomarkerDiscovery = None
    BiomarkerValidator = None
    BiomarkerDiscoveryDashboard = None
    BiomarkerVisualizationEngine = None

# Import drug discovery modules
try:
    from .drug_discovery import (
        DrugAnalyzer,
        DrugTargetIdentifier,
        DrugRepurposingAnalyzer,
        DrugMechanismAnalyzer,
        ClinicalTrialMatcher,
        TrialAnalyzer,
        DrugTrialIntegrator,
        DrugDiscoveryDashboard,
        DrugVisualizationEngine
    )
    _DRUG_DISCOVERY_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Drug discovery modules not available: {e}")
    _DRUG_DISCOVERY_AVAILABLE = False
    # Set dummy classes
    DrugAnalyzer = None
    DrugTargetIdentifier = None
    DrugRepurposingAnalyzer = None
    DrugMechanismAnalyzer = None
    ClinicalTrialMatcher = None
    TrialAnalyzer = None
    DrugTrialIntegrator = None
    DrugDiscoveryDashboard = None
    DrugVisualizationEngine = None

# Import drug-biomarker integration modules
try:
    from .drug_biomarker_integration import (
        DrugBiomarkerAnalyzer,
        PharmacogenomicsIntegrator,
        PersonalizedMedicineEngine,
        DrugResponsePredictor as IntegratedDrugResponsePredictor,
        BiomarkerBasedPredictor,
        MultiOmicsPredictor
    )
    _DRUG_BIOMARKER_INTEGRATION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Drug-biomarker integration modules not available: {e}")
    _DRUG_BIOMARKER_INTEGRATION_AVAILABLE = False
    # Set dummy classes
    DrugBiomarkerAnalyzer = None
    PharmacogenomicsIntegrator = None
    PersonalizedMedicineEngine = None
    IntegratedDrugResponsePredictor = None
    BiomarkerBasedPredictor = None
    MultiOmicsPredictor = None

# Import API modules
try:
    from .biomarker_drug_api import (
        create_biomarker_api,
        create_drug_api,
        create_integration_api,
        create_clinical_api
    )
    _API_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: API modules not available: {e}")
    _API_MODULES_AVAILABLE = False
    # Set dummy functions
    create_biomarker_api = None
    create_drug_api = None
    create_integration_api = None
    create_clinical_api = None

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite Team"

# Build __all__ dynamically based on available modules
__all__ = []

# Add biomarker discovery modules if available
if _BIOMARKER_DISCOVERY_AVAILABLE:
    __all__.extend([
        "BiomarkerAnalyzer",
        "StatisticalBiomarkerDiscovery",
        "MLBiomarkerDiscovery",
        "BiomarkerValidator",
        "BiomarkerDiscoveryDashboard",
        "BiomarkerVisualizationEngine"
    ])

# Add drug discovery modules if available
if _DRUG_DISCOVERY_AVAILABLE:
    __all__.extend([
        "DrugAnalyzer",
        "DrugTargetIdentifier",
        "DrugRepurposingAnalyzer",
        "DrugMechanismAnalyzer",
        "ClinicalTrialMatcher",
        "TrialAnalyzer",
        "DrugTrialIntegrator",
        "DrugDiscoveryDashboard",
        "DrugVisualizationEngine"
    ])

# Add drug-biomarker integration modules if available
if _DRUG_BIOMARKER_INTEGRATION_AVAILABLE:
    __all__.extend([
        "DrugBiomarkerAnalyzer",
        "PharmacogenomicsIntegrator",
        "PersonalizedMedicineEngine",
        "IntegratedDrugResponsePredictor",
        "BiomarkerBasedPredictor",
        "MultiOmicsPredictor"
    ])

# Add API modules if available
if _API_MODULES_AVAILABLE:
    __all__.extend([
        "create_biomarker_api",
        "create_drug_api",
        "create_integration_api",
        "create_clinical_api"
    ])
