"""
Reporting Module

This module provides comprehensive reporting capabilities for the Cancer Genomics Analysis Suite.
It includes report generation, dashboard creation, and automated reporting workflows.

Components:
- ReportBuilder: Handles report generation and formatting
- ReportDashboard: Creates interactive reporting dashboards
"""

from .report_builder import ReportBuilder, ReportType, ReportFormat, ReportSection
from .report_dash import ReportDashboard, ReportWidget, ReportFilter

__all__ = [
    'ReportBuilder',
    'ReportType',
    'ReportFormat',
    'ReportSection',
    'ReportDashboard',
    'ReportWidget',
    'ReportFilter'
]

__version__ = '1.0.0'
__author__ = 'Cancer Genomics Analysis Suite'
