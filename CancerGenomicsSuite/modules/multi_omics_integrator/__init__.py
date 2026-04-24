"""
Multi-Omics Integrator Module

This module provides comprehensive functionality for integrating and analyzing
multiple omics data types in cancer genomics research.

Main Components:
- MultiOmicsIntegrator: Core multi-omics integration and analysis class
- Data loading, normalization, and integration tools
- Dimensionality reduction and clustering methods
- Interactive visualizations and dashboards
"""

from .integrator import (
    MultiOmicsIntegrator,
    create_mock_omics_data
)
from .multiomics_dash import create_multiomics_dashboard

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite"

__all__ = [
    'MultiOmicsIntegrator',
    'create_mock_omics_data',
    'create_multiomics_dashboard'
]

# Module metadata
MODULE_INFO = {
    'name': 'Multi-Omics Integrator',
    'version': __version__,
    'description': 'Comprehensive multi-omics data integration and analysis for cancer genomics',
    'features': [
        'Multi-omics data loading and preprocessing',
        'Data normalization and quality control',
        'Multiple integration methods (concatenation, PCA, ICA)',
        'Dimensionality reduction (PCA, t-SNE, UMAP)',
        'Clustering analysis (K-means, DBSCAN, hierarchical)',
        'Interactive visualizations and dashboards',
        'Correlation analysis between omics types',
        'Export capabilities for results'
    ],
    'supported_data_types': [
        'Gene expression',
        'DNA methylation',
        'Protein expression',
        'Copy number variation',
        'Mutation data',
        'MicroRNA expression',
        'Metabolomics data'
    ],
    'dependencies': [
        'pandas',
        'numpy',
        'plotly',
        'seaborn',
        'matplotlib',
        'scikit-learn',
        'scipy'
    ]
}
