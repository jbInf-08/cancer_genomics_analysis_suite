"""
DNA Sequence Analyzer Module

This module provides comprehensive DNA sequence analysis capabilities for the
Cancer Genomics Analysis Suite, including sequence validation, statistics,
translation, ORF finding, and visualization tools.

Components:
- DNAAnalyzer: Main analysis engine for DNA sequences
- DNADashboard: Interactive dashboard for sequence analysis
- DNAUtils: Utility functions for sequence manipulation and analysis
"""

from .analyzer import DNAAnalyzer
from .dna_dash import DNADashboard
from .utils import DNAUtils

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite Team"

__all__ = [
    "DNAAnalyzer",
    "DNADashboard", 
    "DNAUtils"
]
