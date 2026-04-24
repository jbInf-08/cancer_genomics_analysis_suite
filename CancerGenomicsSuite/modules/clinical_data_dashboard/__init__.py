"""
Clinical Data Dashboard Module

This module provides comprehensive functionality for analyzing and visualizing
clinical data in cancer genomics research.

Main Components:
- ClinicalDataAnalyzer: Core clinical data analysis class
- Survival analysis and Kaplan-Meier curves
- Clinical correlations and associations
- Predictive modeling for clinical outcomes
- Interactive visualizations and dashboards
"""

from .dashboard import (
    ClinicalDataAnalyzer,
    create_mock_clinical_data,
    create_mock_survival_data
)
from .clinical_dash import create_clinical_dashboard

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite"

__all__ = [
    'ClinicalDataAnalyzer',
    'create_mock_clinical_data',
    'create_mock_survival_data',
    'create_clinical_dashboard'
]

# Module metadata
MODULE_INFO = {
    'name': 'Clinical Data Dashboard',
    'version': __version__,
    'description': 'Comprehensive clinical data analysis and visualization for cancer genomics',
    'features': [
        'Clinical data loading and preprocessing',
        'Survival analysis with Kaplan-Meier curves',
        'Cox proportional hazards regression',
        'Clinical correlations and associations',
        'Predictive modeling for clinical outcomes',
        'Statistical tests (Chi-square, ANOVA, etc.)',
        'Interactive visualizations and dashboards',
        'Export capabilities for results'
    ],
    'supported_analyses': [
        'Survival analysis',
        'Kaplan-Meier estimation',
        'Cox regression',
        'Log-rank tests',
        'Clinical correlations',
        'Association tests',
        'Predictive modeling',
        'Feature importance analysis'
    ],
    'dependencies': [
        'pandas',
        'numpy',
        'plotly',
        'seaborn',
        'matplotlib',
        'scikit-learn',
        'lifelines',
        'scipy'
    ]
}
