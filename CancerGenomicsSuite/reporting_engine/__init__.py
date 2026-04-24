"""
Reporting Engine Module

This module provides comprehensive reporting capabilities for the Cancer Genomics Analysis Suite.
It includes PDF generation, HTML reporting, and template utilities for creating various
types of reports including analysis results, clinical data summaries, and research findings.

Components:
- PDFBuilder: Generates PDF reports with charts, tables, and formatted content
- HTMLReporter: Creates interactive HTML reports with embedded visualizations
- TemplateUtils: Provides template management and formatting utilities
"""

from .pdf_builder import PDFBuilder
from .html_reporter import HTMLReporter
from .template_utils import TemplateUtils

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite Team"

__all__ = [
    "PDFBuilder",
    "HTMLReporter", 
    "TemplateUtils"
]
