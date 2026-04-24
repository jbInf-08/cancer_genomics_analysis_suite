"""
Drug Discovery and Analysis Module for Cancer Genomics Analysis Suite

This module provides comprehensive drug discovery and analysis capabilities including:
- Drug target identification and validation
- Drug repurposing and repositioning analysis
- Drug mechanism of action analysis
- Drug-drug interaction analysis
- Drug response prediction and modeling
- Clinical trial matching and analysis
- Drug safety and toxicity assessment
"""

from .drug_analyzer import (
    DrugAnalyzer,
    DrugTargetIdentifier,
    DrugRepurposingAnalyzer,
    DrugMechanismAnalyzer
)

from .clinical_trials import (
    ClinicalTrialMatcher,
    TrialAnalyzer,
    DrugTrialIntegrator
)

from .drug_dashboard import (
    DrugDiscoveryDashboard,
    DrugVisualizationEngine
)

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite Team"

__all__ = [
    # Core Analysis
    "DrugAnalyzer",
    "DrugTargetIdentifier",
    "DrugRepurposingAnalyzer", 
    "DrugMechanismAnalyzer",
    
    # Clinical Trials
    "ClinicalTrialMatcher",
    "TrialAnalyzer",
    "DrugTrialIntegrator",
    
    # Dashboard
    "DrugDiscoveryDashboard",
    "DrugVisualizationEngine"
]
