"""
Phylogenetic Tree Viewer Module

This module provides comprehensive phylogenetic tree construction and visualization
capabilities for the Cancer Genomics Analysis Suite, including multiple sequence
alignment, tree building algorithms, evolutionary analysis, and interactive
tree visualization tools.

Components:
- PhylogeneticTreeBuilder: Main tree construction engine
- TreeDashboard: Interactive dashboard for phylogenetic analysis
- TreeUtils: Utility functions for tree manipulation and analysis
"""

from .tree_builder import PhylogeneticTreeBuilder
from .tree_dash import TreeDashboard

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite Team"

__all__ = [
    "PhylogeneticTreeBuilder",
    "TreeDashboard"
]
