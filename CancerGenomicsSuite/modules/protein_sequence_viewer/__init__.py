"""
Protein Sequence Viewer Module

This module provides comprehensive protein sequence analysis and visualization
capabilities for the Cancer Genomics Analysis Suite, including sequence
validation, statistics, motif analysis, domain prediction, and interactive
visualization tools.

Components:
- ProteinViewer: Main analysis engine for protein sequences
- ProteinDashboard: Interactive dashboard for protein analysis
- ProteinUtils: Utility functions for protein manipulation and analysis
"""

from .viewer import ProteinViewer
from .protein_dash import ProteinDashboard

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite Team"

__all__ = [
    "ProteinViewer",
    "ProteinDashboard"
]
