"""
Batch Processing Module

This module provides comprehensive batch processing capabilities for the Cancer Genomics Analysis Suite.
It includes batch job management, processing dashboards, and data export functionality.

Components:
- BatchDashboard: Interactive dashboard for batch processing management
- DataExporter: Handles data export in various formats
"""

from .batch_dash import BatchDashboard, BatchJob, JobStatus, JobType, BatchQueue
from .exporter import DataExporter, ExportFormat, ExportConfig, ExportJob

__all__ = [
    'BatchDashboard',
    'BatchJob',
    'JobStatus',
    'JobType',
    'BatchQueue',
    'DataExporter',
    'ExportFormat',
    'ExportConfig',
    'ExportJob'
]

__version__ = '1.0.0'
__author__ = 'Cancer Genomics Analysis Suite'
