"""
Sequence Search Tool Module

This module provides comprehensive sequence search and alignment capabilities
for the Cancer Genomics Analysis Suite, including local and global alignment,
BLAST-like searches, pattern matching, and interactive visualization tools.

Components:
- SequenceAligner: Main alignment engine for sequence searches
- SearchDashboard: Interactive dashboard for sequence search operations
- SearchUtils: Utility functions for sequence manipulation and analysis
"""

from .aligner import SequenceAligner
from .search_dash import SearchDashboard

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite Team"

__all__ = [
    "SequenceAligner",
    "SearchDashboard"
]
