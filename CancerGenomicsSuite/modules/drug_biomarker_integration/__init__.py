"""
Drug-Biomarker Integration Module for Cancer Genomics Analysis Suite

This module provides comprehensive integration between drug discovery and biomarker analysis including:
- Drug-biomarker interaction analysis
- Pharmacogenomics integration
- Drug response prediction based on biomarkers
- Biomarker-guided drug selection
- Personalized medicine recommendations
- Clinical decision support systems
"""

from .drug_biomarker_analyzer import (
    DrugBiomarkerAnalyzer,
    PharmacogenomicsIntegrator,
    PersonalizedMedicineEngine
)

from .drug_response_prediction import (
    DrugResponsePredictor,
    BiomarkerBasedPredictor,
    MultiOmicsPredictor
)

# Import optional modules if they exist
try:
    from .clinical_decision_support import (
        ClinicalDecisionSupport,
        TreatmentRecommendationEngine,
        RiskAssessmentEngine
    )
    _CLINICAL_DECISION_AVAILABLE = True
except ImportError:
    _CLINICAL_DECISION_AVAILABLE = False
    ClinicalDecisionSupport = None
    TreatmentRecommendationEngine = None
    RiskAssessmentEngine = None

try:
    from .integration_dashboard import (
        DrugBiomarkerDashboard,
        IntegrationVisualizationEngine
    )
    _DASHBOARD_AVAILABLE = True
except ImportError:
    _DASHBOARD_AVAILABLE = False
    DrugBiomarkerDashboard = None
    IntegrationVisualizationEngine = None

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite Team"

__all__ = [
    # Core Integration
    "DrugBiomarkerAnalyzer",
    "PharmacogenomicsIntegrator",
    "PersonalizedMedicineEngine",
    
    # Drug Response Prediction
    "DrugResponsePredictor",
    "BiomarkerBasedPredictor",
    "MultiOmicsPredictor"
]

# Add optional modules to __all__ if they're available
if _CLINICAL_DECISION_AVAILABLE:
    __all__.extend([
        "ClinicalDecisionSupport",
        "TreatmentRecommendationEngine",
        "RiskAssessmentEngine"
    ])

if _DASHBOARD_AVAILABLE:
    __all__.extend([
        "DrugBiomarkerDashboard",
        "IntegrationVisualizationEngine"
    ])
