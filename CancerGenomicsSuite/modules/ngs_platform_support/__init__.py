"""
NGS Platform Support Module

This module provides comprehensive support for various Next-Generation Sequencing (NGS) platforms,
including Illumina, Ion Torrent, PacBio, and Oxford Nanopore. It includes platform-specific
pipelines, common preprocessing utilities, and workflow orchestration capabilities.

Supported Platforms:
- Illumina: Short-read sequencing with high throughput
- Ion Torrent: Semiconductor-based sequencing
- PacBio: Long-read sequencing with high accuracy
- Oxford Nanopore: Real-time long-read sequencing

Components:
- illumina_pipeline: Illumina-specific sequencing and analysis pipeline
- ion_torrent_pipeline: Ion Torrent platform support and analysis
- pacbio_pipeline: PacBio long-read sequencing pipeline
- nanopore_pipeline: Oxford Nanopore sequencing support
- common_preprocessing: Shared preprocessing utilities across platforms
- workflow_dispatcher: Workflow orchestration and job management
"""

from .illumina_pipeline import (
    IlluminaPipeline,
    IlluminaQualityControl,
    IlluminaAlignment,
    IlluminaVariantCalling,
    IlluminaExpressionAnalysis
)

from .ion_torrent_pipeline import (
    IonTorrentPipeline,
    IonTorrentQualityControl,
    IonTorrentAlignment,
    IonTorrentVariantCalling,
    IonTorrentExpressionAnalysis
)

from .pacbio_pipeline import (
    PacBioPipeline,
    PacBioQualityControl,
    PacBioAlignment,
    PacBioVariantCalling,
    PacBioAssembly,
    PacBioIsoformAnalysis
)

from .nanopore_pipeline import (
    NanoporePipeline,
    NanoporeQualityControl,
    NanoporeAlignment,
    NanoporeVariantCalling,
    NanoporeAssembly,
    NanoporeBasecalling
)

from .common_preprocessing import (
    FastqProcessor,
    QualityTrimmer,
    AdapterRemover,
    ContaminantFilter,
    ReadDeduplicator,
    QualityMetrics,
    PreprocessingPipeline
)

from .workflow_dispatcher import (
    WorkflowDispatcher,
    JobManager,
    ResourceMonitor,
    WorkflowScheduler,
    PlatformDetector,
    WorkflowValidator,
    DockerManager,
    CeleryJobManager,
    DockerConfig,
    QueueConfig,
    Job,
    JobStatus,
    PlatformType
)

from .ngs_pipeline_integration import (
    NGSPipelineManager,
    PipelineStepExecutor,
    PipelineValidator,
    EnhancedWorkflowDispatcher,
    PipelineDefinition,
    PipelineStep,
    PipelineExecution,
    PipelineStatus,
    PipelineType
)

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite"

__all__ = [
    # Illumina components
    "IlluminaPipeline",
    "IlluminaQualityControl",
    "IlluminaAlignment", 
    "IlluminaVariantCalling",
    "IlluminaExpressionAnalysis",
    
    # Ion Torrent components
    "IonTorrentPipeline",
    "IonTorrentQualityControl",
    "IonTorrentAlignment",
    "IonTorrentVariantCalling", 
    "IonTorrentExpressionAnalysis",
    
    # PacBio components
    "PacBioPipeline",
    "PacBioQualityControl",
    "PacBioAlignment",
    "PacBioVariantCalling",
    "PacBioAssembly",
    "PacBioIsoformAnalysis",
    
    # Nanopore components
    "NanoporePipeline",
    "NanoporeQualityControl",
    "NanoporeAlignment",
    "NanoporeVariantCalling",
    "NanoporeAssembly",
    "NanoporeBasecalling",
    
    # Common preprocessing components
    "FastqProcessor",
    "QualityTrimmer",
    "AdapterRemover",
    "ContaminantFilter",
    "ReadDeduplicator",
    "QualityMetrics",
    "PreprocessingPipeline",
    
    # Workflow management components
    "WorkflowDispatcher",
    "JobManager",
    "ResourceMonitor",
    "WorkflowScheduler",
    "PlatformDetector",
    "WorkflowValidator",
    
    # Docker and job queue components
    "DockerManager",
    "CeleryJobManager",
    "DockerConfig",
    "QueueConfig",
    "Job",
    "JobStatus",
    "PlatformType",
    
    # NGS Pipeline integration components
    "NGSPipelineManager",
    "PipelineStepExecutor",
    "PipelineValidator",
    "EnhancedWorkflowDispatcher",
    "PipelineDefinition",
    "PipelineStep",
    "PipelineExecution",
    "PipelineStatus",
    "PipelineType"
]
