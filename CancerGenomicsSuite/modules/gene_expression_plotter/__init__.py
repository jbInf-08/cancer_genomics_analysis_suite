"""
Gene Expression Plotter Module

This module provides comprehensive gene expression analysis and visualization
capabilities for the Cancer Genomics Analysis Suite, including expression
data processing, statistical analysis, clustering, differential expression
analysis, and interactive plotting tools.

Components:
- GeneExpressionPlotter: Main analysis engine for gene expression data
- ExpressionDashboard: Interactive dashboard for expression analysis
- ExpressionUtils: Utility functions for expression data manipulation
"""

from .plotter import GeneExpressionPlotter
from .expression_dash import ExpressionDashboard

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite Team"

__all__ = [
    "GeneExpressionPlotter",
    "ExpressionDashboard"
]
