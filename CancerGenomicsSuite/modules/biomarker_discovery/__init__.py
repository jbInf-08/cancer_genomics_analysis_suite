"""
Biomarker Discovery Module for Cancer Genomics Analysis Suite

This module provides comprehensive biomarker discovery capabilities including:
- Statistical biomarker identification and validation
- Machine learning-based biomarker discovery
- Multi-omics biomarker integration
- Clinical biomarker validation and assessment
- Biomarker-disease association analysis
- Biomarker performance evaluation and metrics
"""

from .biomarker_analyzer import (
    BiomarkerAnalyzer,
    StatisticalBiomarkerDiscovery,
    MLBiomarkerDiscovery,
    BiomarkerValidator
)

from .biomarker_dashboard import (
    BiomarkerDiscoveryDashboard,
    BiomarkerVisualizationEngine
)

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite Team"

__all__ = [
    # Core Analysis
    "BiomarkerAnalyzer",
    "StatisticalBiomarkerDiscovery", 
    "MLBiomarkerDiscovery",
    "BiomarkerValidator",
    
    # Dashboard
    "BiomarkerDiscoveryDashboard",
    "BiomarkerVisualizationEngine"
]
