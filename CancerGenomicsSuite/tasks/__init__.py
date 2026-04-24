"""
Tasks Module

This module provides comprehensive task management and pipeline execution capabilities
for the Cancer Genomics Analysis Suite. It includes queue management, various analysis
pipelines, and automated reporting workflows.

Components:
- QueueManager: Manages task queues and execution scheduling
- BlastPipeline: Handles BLAST sequence analysis workflows
- MLPredictorPipeline: Manages machine learning prediction tasks
- AnnotationPipeline: Processes genomic annotation workflows
- ReportingPipeline: Handles automated report generation tasks
"""

from .queue_manager import QueueManager
from .blast_pipeline import BlastPipeline
from .ml_predictor_pipeline import MLPredictorPipeline
from .annotation_pipeline import AnnotationPipeline
from .reporting_pipeline import ReportingPipeline

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite Team"

__all__ = [
    "QueueManager",
    "BlastPipeline",
    "MLPredictorPipeline",
    "AnnotationPipeline",
    "ReportingPipeline"
]
