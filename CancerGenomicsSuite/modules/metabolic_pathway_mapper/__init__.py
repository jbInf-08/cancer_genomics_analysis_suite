"""
Metabolic Pathway Mapper Module

This module provides comprehensive functionality for mapping and analyzing
metabolic pathways in cancer genomics data.

Main Components:
- MetabolicPathwayMapper: Core pathway mapping and analysis class
- Pathway visualization and analysis tools
- KEGG pathway integration
- Interactive dashboard components
"""

from .mapper import (
    MetabolicPathwayMapper,
    create_mock_pathway_data
)
from .pathway_dash import create_pathway_dashboard
from .kegg_overlay import KEGGPathwayOverlay

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite"

__all__ = [
    'MetabolicPathwayMapper',
    'create_mock_pathway_data',
    'create_pathway_dashboard',
    'KEGGPathwayOverlay'
]

# Module metadata
MODULE_INFO = {
    'name': 'Metabolic Pathway Mapper',
    'version': __version__,
    'description': 'Comprehensive pathway mapping and analysis for cancer genomics',
    'features': [
        'Pathway network creation and analysis',
        'Gene expression pathway analysis',
        'Dysregulated pathway identification',
        'Interactive pathway visualizations',
        'KEGG pathway integration',
        'Export capabilities'
    ],
    'dependencies': [
        'pandas',
        'numpy',
        'networkx',
        'plotly',
        'requests'
    ]
}
