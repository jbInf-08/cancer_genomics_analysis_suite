#!/usr/bin/env python3
"""
Data Pipeline

This module provides data pipeline management capabilities for real-time
cancer genomics data processing.
"""

import logging
import json
import time
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import numpy as np

from .kafka_manager import KafkaManager
from .stream_processor import StreamProcessor

logger = logging.getLogger(__name__)


class DataPipeline:
    """
    Data pipeline manager for cancer genomics real-time processing.
    
    Provides functionality to:
    - Manage end-to-end data pipelines
    - Coordinate multiple processing stages
    - Handle data flow between components
    - Monitor pipeline health and performance
    - Manage pipeline dependencies
    """
    
    def __init__(
        self,
        kafka_manager: KafkaManager,
        stream_processor: StreamProcessor,
        pipeline_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize data pipeline manager.
        
        Args:
            kafka_manager: Kafka manager instance
            stream_processor: Stream processor instance
            pipeline_config: Pipeline configuration
        """
        self.kafka_manager = kafka_manager
        self.stream_processor = stream_processor
        self.pipeline_config = pipeline_config or {}
        
        # Pipeline management
        self.pipelines = {}
        self.pipeline_dependencies = {}
        self.pipeline_status = {}
        
        # Monitoring
        self.monitoring_enabled = self.pipeline_config.get("monitoring_enabled", True)
        self.health_check_interval = self.pipeline_config.get("health_check_interval", 30)
        self.monitoring_thread = None
        
        # Performance tracking
        self.performance_metrics = {
            "throughput": {},
            "latency": {},
            "error_rates": {},
            "resource_usage": {}
        }
        
        # Start monitoring if enabled
        if self.monitoring_enabled:
            self.start_monitoring()
    
    def create_cancer_genomics_pipeline(
        self,
        pipeline_name: str,
        data_sources: List[Dict[str, Any]],
        processing_stages: List[Dict[str, Any]],
        output_destinations: List[Dict[str, Any]]
    ) -> bool:
        """
        Create a cancer genomics data pipeline.
        
        Args:
            pipeline_name: Name of the pipeline
            data_sources: List of data source configurations
            processing_stages: List of processing stage configurations
            output_destinations: List of output destination configurations
            
        Returns:
            True if pipeline was created successfully
        """
        try:
            # Create topics for data flow
            topics = self._create_pipeline_topics(pipeline_name, data_sources, processing_stages, output_destinations)
            
            # Create processing stages
            processing_pipelines = self._create_processing_stages(pipeline_name, processing_stages, topics)
            
            # Store pipeline configuration
            pipeline_config = {
                "name": pipeline_name,
                "data_sources": data_sources,
                "processing_stages": processing_stages,
                "output_destinations": output_destinations,
                "topics": topics,
                "processing_pipelines": processing_pipelines,
                "created_at": datetime.now().isoformat(),
                "status": "created"
            }
            
            self.pipelines[pipeline_name] = pipeline_config
            self.pipeline_status[pipeline_name] = {
                "status": "created",
                "health": "unknown",
                "last_check": None,
                "errors": []
            }
            
            logger.info(f"Created cancer genomics pipeline: {pipeline_name}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to create pipeline {pipeline_name}: {e}")
            return False
    
    def _create_pipeline_topics(
        self,
        pipeline_name: str,
        data_sources: List[Dict[str, Any]],
        processing_stages: List[Dict[str, Any]],
        output_destinations: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Create Kafka topics for pipeline data flow."""
        topics = {}
        
        # Create input topics for data sources
        for i, data_source in enumerate(data_sources):
            topic_name = f"{pipeline_name}_input_{i}"
            self.kafka_manager.create_topic(
                topic_name=topic_name,
                num_partitions=data_source.get("partitions", 3),
                replication_factor=data_source.get("replication_factor", 1)
            )
            topics[f"input_{i}"] = topic_name
        
        # Create intermediate topics for processing stages
        for i, stage in enumerate(processing_stages):
            if i < len(processing_stages) - 1:  # Not the last stage
                topic_name = f"{pipeline_name}_stage_{i}"
                self.kafka_manager.create_topic(
                    topic_name=topic_name,
                    num_partitions=stage.get("partitions", 3),
                    replication_factor=stage.get("replication_factor", 1)
                )
                topics[f"stage_{i}"] = topic_name
        
        # Create output topics for destinations
        for i, destination in enumerate(output_destinations):
            topic_name = f"{pipeline_name}_output_{i}"
            self.kafka_manager.create_topic(
                topic_name=topic_name,
                num_partitions=destination.get("partitions", 3),
                replication_factor=destination.get("replication_factor", 1)
            )
            topics[f"output_{i}"] = topic_name
        
        return topics
    
    def _create_processing_stages(
        self,
        pipeline_name: str,
        processing_stages: List[Dict[str, Any]],
        topics: Dict[str, str]
    ) -> List[str]:
        """Create processing stages for the pipeline."""
        processing_pipelines = []
        
        for i, stage in enumerate(processing_stages):
            stage_name = f"{pipeline_name}_stage_{i}"
            
            # Determine input and output topics
            if i == 0:
                input_topics = [topics["input_0"]]  # First stage uses input topic
            else:
                input_topics = [topics[f"stage_{i-1}"]]
            
            if i == len(processing_stages) - 1:
                output_topics = [topics["output_0"]]  # Last stage uses output topic
            else:
                output_topics = [topics[f"stage_{i}"]]
            
            # Create processing steps
            processing_steps = self._create_processing_steps(stage)
            
            # Create stream processor pipeline
            success = self.stream_processor.create_processing_pipeline(
                pipeline_name=stage_name,
                input_topics=input_topics,
                output_topics=output_topics,
                processing_steps=processing_steps
            )
            
            if success:
                processing_pipelines.append(stage_name)
            
        return processing_pipelines
    
    def _create_processing_steps(self, stage_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create processing steps for a stage."""
        steps = []
        
        # Data validation step
        if stage_config.get("enable_validation", True):
            steps.append({
                "type": "quality_check",
                "config": {
                    "checks": [
                        {
                            "type": "completeness",
                            "required_fields": stage_config.get("required_fields", []),
                            "min_completeness": stage_config.get("min_completeness", 0.8)
                        },
                        {
                            "type": "validity",
                            "field_rules": stage_config.get("field_rules", {})
                        }
                    ]
                }
            })
        
        # Data transformation steps
        transformations = stage_config.get("transformations", [])
        for transform in transformations:
            steps.append({
                "type": "transform",
                "config": transform
            })
        
        # Data filtering steps
        filters = stage_config.get("filters", [])
        for filter_config in filters:
            steps.append({
                "type": "filter",
                "config": filter_config
            })
        
        # Data aggregation steps
        aggregations = stage_config.get("aggregations", [])
        for aggregation in aggregations:
            steps.append({
                "type": "aggregate",
                "config": aggregation
            })
        
        return steps
    
    def start_pipeline(self, pipeline_name: str) -> bool:
        """
        Start a data pipeline.
        
        Args:
            pipeline_name: Name of the pipeline to start
            
        Returns:
            True if pipeline was started successfully
        """
        if pipeline_name not in self.pipelines:
            logger.error(f"Pipeline {pipeline_name} not found")
            return False
        
        try:
            pipeline_config = self.pipelines[pipeline_name]
            processing_pipelines = pipeline_config["processing_pipelines"]
            
            # Start all processing stages
            for stage_name in processing_pipelines:
                success = self.stream_processor.start_pipeline(stage_name)
                if not success:
                    logger.error(f"Failed to start processing stage: {stage_name}")
                    return False
            
            # Update pipeline status
            self.pipelines[pipeline_name]["status"] = "running"
            self.pipelines[pipeline_name]["started_at"] = datetime.now().isoformat()
            self.pipeline_status[pipeline_name]["status"] = "running"
            
            logger.info(f"Started data pipeline: {pipeline_name}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to start pipeline {pipeline_name}: {e}")
            return False
    
    def stop_pipeline(self, pipeline_name: str) -> bool:
        """
        Stop a data pipeline.
        
        Args:
            pipeline_name: Name of the pipeline to stop
            
        Returns:
            True if pipeline was stopped successfully
        """
        if pipeline_name not in self.pipelines:
            logger.error(f"Pipeline {pipeline_name} not found")
            return False
        
        try:
            pipeline_config = self.pipelines[pipeline_name]
            processing_pipelines = pipeline_config["processing_pipelines"]
            
            # Stop all processing stages
            for stage_name in processing_pipelines:
                self.stream_processor.stop_pipeline(stage_name)
            
            # Update pipeline status
            self.pipelines[pipeline_name]["status"] = "stopped"
            self.pipelines[pipeline_name]["stopped_at"] = datetime.now().isoformat()
            self.pipeline_status[pipeline_name]["status"] = "stopped"
            
            logger.info(f"Stopped data pipeline: {pipeline_name}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to stop pipeline {pipeline_name}: {e}")
            return False
    
    def create_variant_calling_pipeline(self, pipeline_name: str = "variant_calling") -> bool:
        """
        Create a pre-configured variant calling pipeline.
        
        Args:
            pipeline_name: Name of the pipeline
            
        Returns:
            True if pipeline was created successfully
        """
        data_sources = [
            {
                "type": "fastq_files",
                "partitions": 6,
                "replication_factor": 1,
                "description": "Raw sequencing data"
            }
        ]
        
        processing_stages = [
            {
                "name": "quality_control",
                "partitions": 4,
                "replication_factor": 1,
                "enable_validation": True,
                "required_fields": ["sample_id", "read1_path", "read2_path"],
                "transformations": [
                    {
                        "transform_type": "extract_features",
                        "features": [
                            {
                                "name": "file_size",
                                "type": "sum",
                                "source_fields": ["read1_size", "read2_size"]
                            }
                        ]
                    }
                ],
                "filters": [
                    {
                        "filter_type": "range",
                        "field": "file_size",
                        "min": 1000000  # Minimum 1MB
                    }
                ]
            },
            {
                "name": "alignment",
                "partitions": 8,
                "replication_factor": 1,
                "enable_validation": True,
                "required_fields": ["sample_id", "reference_genome"],
                "transformations": [
                    {
                        "transform_type": "normalize",
                        "fields": ["mapping_quality"],
                        "method": "min_max",
                        "min": 0,
                        "max": 60
                    }
                ],
                "filters": [
                    {
                        "filter_type": "range",
                        "field": "mapping_quality",
                        "min": 20
                    }
                ]
            },
            {
                "name": "variant_calling",
                "partitions": 6,
                "replication_factor": 1,
                "enable_validation": True,
                "required_fields": ["sample_id", "bam_file"],
                "transformations": [
                    {
                        "transform_type": "extract_features",
                        "features": [
                            {
                                "name": "variant_quality_score",
                                "type": "mean",
                                "source_fields": ["qual", "dp", "gq"]
                            }
                        ]
                    }
                ],
                "filters": [
                    {
                        "filter_type": "range",
                        "field": "variant_quality_score",
                        "min": 30
                    }
                ]
            },
            {
                "name": "annotation",
                "partitions": 4,
                "replication_factor": 1,
                "enable_validation": True,
                "required_fields": ["variant_id", "chromosome", "position"],
                "aggregations": [
                    {
                        "aggregation_type": "window",
                        "buffer_name": "annotation_buffer",
                        "window_size": 100,
                        "aggregation_fields": ["impact_score"],
                        "aggregation_method": "mean"
                    }
                ]
            }
        ]
        
        output_destinations = [
            {
                "type": "annotated_variants",
                "partitions": 3,
                "replication_factor": 1,
                "description": "Annotated variant calls"
            }
        ]
        
        return self.create_cancer_genomics_pipeline(
            pipeline_name=pipeline_name,
            data_sources=data_sources,
            processing_stages=processing_stages,
            output_destinations=output_destinations
        )
    
    def create_expression_analysis_pipeline(self, pipeline_name: str = "expression_analysis") -> bool:
        """
        Create a pre-configured expression analysis pipeline.
        
        Args:
            pipeline_name: Name of the pipeline
            
        Returns:
            True if pipeline was created successfully
        """
        data_sources = [
            {
                "type": "rna_seq_data",
                "partitions": 4,
                "replication_factor": 1,
                "description": "RNA-seq expression data"
            }
        ]
        
        processing_stages = [
            {
                "name": "quality_control",
                "partitions": 3,
                "replication_factor": 1,
                "enable_validation": True,
                "required_fields": ["sample_id", "expression_matrix"],
                "transformations": [
                    {
                        "transform_type": "normalize",
                        "fields": ["expression_values"],
                        "method": "log"
                    }
                ],
                "filters": [
                    {
                        "filter_type": "range",
                        "field": "expression_values",
                        "min": 0
                    }
                ]
            },
            {
                "name": "normalization",
                "partitions": 4,
                "replication_factor": 1,
                "enable_validation": True,
                "transformations": [
                    {
                        "transform_type": "normalize",
                        "fields": ["expression_values"],
                        "method": "quantile"
                    }
                ]
            },
            {
                "name": "differential_expression",
                "partitions": 6,
                "replication_factor": 1,
                "enable_validation": True,
                "required_fields": ["gene_id", "condition"],
                "aggregations": [
                    {
                        "aggregation_type": "batch",
                        "buffer_name": "de_buffer",
                        "batch_size": 1000,
                        "aggregation_fields": ["log2fc", "p_value"],
                        "aggregation_method": "mean"
                    }
                ]
            }
        ]
        
        output_destinations = [
            {
                "type": "differential_expression_results",
                "partitions": 3,
                "replication_factor": 1,
                "description": "Differential expression analysis results"
            }
        ]
        
        return self.create_cancer_genomics_pipeline(
            pipeline_name=pipeline_name,
            data_sources=data_sources,
            processing_stages=processing_stages,
            output_destinations=output_destinations
        )
    
    def create_multi_omics_pipeline(self, pipeline_name: str = "multi_omics") -> bool:
        """
        Create a pre-configured multi-omics integration pipeline.
        
        Args:
            pipeline_name: Name of the pipeline
            
        Returns:
            True if pipeline was created successfully
        """
        data_sources = [
            {
                "type": "genomics_data",
                "partitions": 4,
                "replication_factor": 1,
                "description": "Genomic variant data"
            },
            {
                "type": "transcriptomics_data",
                "partitions": 4,
                "replication_factor": 1,
                "description": "Gene expression data"
            },
            {
                "type": "epigenomics_data",
                "partitions": 3,
                "replication_factor": 1,
                "description": "Epigenomic data"
            }
        ]
        
        processing_stages = [
            {
                "name": "data_preprocessing",
                "partitions": 6,
                "replication_factor": 1,
                "enable_validation": True,
                "required_fields": ["sample_id", "data_type"],
                "transformations": [
                    {
                        "transform_type": "normalize",
                        "fields": ["data_values"],
                        "method": "z_score"
                    }
                ]
            },
            {
                "name": "data_integration",
                "partitions": 8,
                "replication_factor": 1,
                "enable_validation": True,
                "required_fields": ["sample_id", "gene_id"],
                "aggregations": [
                    {
                        "aggregation_type": "window",
                        "buffer_name": "integration_buffer",
                        "window_size": 50,
                        "aggregation_fields": ["correlation_score"],
                        "aggregation_method": "mean"
                    }
                ]
            },
            {
                "name": "pathway_analysis",
                "partitions": 4,
                "replication_factor": 1,
                "enable_validation": True,
                "required_fields": ["pathway_id", "enrichment_score"],
                "filters": [
                    {
                        "filter_type": "range",
                        "field": "enrichment_score",
                        "min": 1.5
                    }
                ]
            }
        ]
        
        output_destinations = [
            {
                "type": "integrated_omics_results",
                "partitions": 3,
                "replication_factor": 1,
                "description": "Integrated multi-omics analysis results"
            }
        ]
        
        return self.create_cancer_genomics_pipeline(
            pipeline_name=pipeline_name,
            data_sources=data_sources,
            processing_stages=processing_stages,
            output_destinations=output_destinations
        )
    
    def start_monitoring(self):
        """Start pipeline monitoring."""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
        
        def monitoring_worker():
            while self.monitoring_enabled:
                try:
                    self._perform_health_checks()
                    self._update_performance_metrics()
                    time.sleep(self.health_check_interval)
                except Exception as e:
                    logger.error(f"Error in monitoring thread: {e}")
                    time.sleep(self.health_check_interval)
        
        self.monitoring_thread = threading.Thread(target=monitoring_worker, daemon=True)
        self.monitoring_thread.start()
        logger.info("Started pipeline monitoring")
    
    def stop_monitoring(self):
        """Stop pipeline monitoring."""
        self.monitoring_enabled = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Stopped pipeline monitoring")
    
    def _perform_health_checks(self):
        """Perform health checks on all pipelines."""
        for pipeline_name in self.pipelines.keys():
            try:
                # Check pipeline status
                pipeline_config = self.pipelines[pipeline_name]
                processing_pipelines = pipeline_config["processing_pipelines"]
                
                # Check if all processing stages are running
                all_running = True
                for stage_name in processing_pipelines:
                    stage_status = self.stream_processor.get_pipeline_status(stage_name)
                    if stage_status.get("status") != "running":
                        all_running = False
                        break
                
                # Update health status
                if all_running:
                    self.pipeline_status[pipeline_name]["health"] = "healthy"
                else:
                    self.pipeline_status[pipeline_name]["health"] = "unhealthy"
                
                self.pipeline_status[pipeline_name]["last_check"] = datetime.now().isoformat()
                
            except Exception as e:
                logger.error(f"Health check failed for pipeline {pipeline_name}: {e}")
                self.pipeline_status[pipeline_name]["health"] = "error"
                self.pipeline_status[pipeline_name]["errors"].append(str(e))
    
    def _update_performance_metrics(self):
        """Update performance metrics for all pipelines."""
        try:
            # Get stream processor statistics
            stream_stats = self.stream_processor.get_processing_statistics()
            
            # Update throughput metrics
            self.performance_metrics["throughput"]["messages_per_second"] = stream_stats.get("messages_per_second", 0)
            self.performance_metrics["throughput"]["total_messages"] = stream_stats.get("messages_processed", 0)
            
            # Update latency metrics
            self.performance_metrics["latency"]["avg_processing_time"] = stream_stats.get("avg_processing_time", 0)
            
            # Update error rates
            total_messages = stream_stats.get("messages_processed", 0) + stream_stats.get("messages_failed", 0)
            if total_messages > 0:
                error_rate = stream_stats.get("messages_failed", 0) / total_messages
                self.performance_metrics["error_rates"]["overall"] = error_rate
            
        except Exception as e:
            logger.error(f"Failed to update performance metrics: {e}")
    
    def get_pipeline_status(self, pipeline_name: str) -> Dict[str, Any]:
        """
        Get status of a specific pipeline.
        
        Args:
            pipeline_name: Name of the pipeline
            
        Returns:
            Dictionary with pipeline status
        """
        if pipeline_name not in self.pipelines:
            return {}
        
        status = self.pipeline_status.get(pipeline_name, {})
        pipeline_config = self.pipelines[pipeline_name]
        
        return {
            "name": pipeline_name,
            "status": pipeline_config["status"],
            "health": status.get("health", "unknown"),
            "last_check": status.get("last_check"),
            "errors": status.get("errors", []),
            "created_at": pipeline_config["created_at"],
            "started_at": pipeline_config.get("started_at"),
            "stopped_at": pipeline_config.get("stopped_at"),
            "processing_stages": len(pipeline_config["processing_pipelines"])
        }
    
    def get_all_pipeline_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all pipelines.
        
        Returns:
            Dictionary with status of all pipelines
        """
        return {
            pipeline_name: self.get_pipeline_status(pipeline_name)
            for pipeline_name in self.pipelines.keys()
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics.
        
        Returns:
            Dictionary with performance metrics
        """
        return self.performance_metrics.copy()
    
    def delete_pipeline(self, pipeline_name: str) -> bool:
        """
        Delete a pipeline.
        
        Args:
            pipeline_name: Name of the pipeline to delete
            
        Returns:
            True if pipeline was deleted successfully
        """
        if pipeline_name not in self.pipelines:
            logger.error(f"Pipeline {pipeline_name} not found")
            return False
        
        try:
            # Stop pipeline if running
            if self.pipelines[pipeline_name]["status"] == "running":
                self.stop_pipeline(pipeline_name)
            
            # Delete topics
            pipeline_config = self.pipelines[pipeline_name]
            for topic_name in pipeline_config["topics"].values():
                self.kafka_manager.delete_topic(topic_name)
            
            # Remove from tracking
            del self.pipelines[pipeline_name]
            if pipeline_name in self.pipeline_status:
                del self.pipeline_status[pipeline_name]
            
            logger.info(f"Deleted pipeline: {pipeline_name}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete pipeline {pipeline_name}: {e}")
            return False
    
    def list_pipelines(self) -> List[Dict[str, Any]]:
        """
        List all pipelines.
        
        Returns:
            List of pipeline information
        """
        return [
            {
                "name": name,
                "status": config["status"],
                "created_at": config["created_at"],
                "processing_stages": len(config["processing_pipelines"]),
                "topics": len(config["topics"])
            }
            for name, config in self.pipelines.items()
        ]
