#!/usr/bin/env python3
"""
Unified Pipeline Orchestrator for Cancer Genomics Analysis

This module provides a comprehensive pipeline orchestration system that
integrates Argo Workflows, Snakemake, Nextflow, and real-time processing
for cancer genomics analysis workflows.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import yaml
import pandas as pd
import numpy as np
from pathlib import Path
import subprocess
import tempfile
import shutil
import uuid
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# Import our custom modules
from .workflow_executor import WorkflowExecutor
from .nextflow_manager import NextflowManager
from .snakemake_manager import SnakemakeManager
from ..real_time_processing.kafka_stream_processor import KafkaStreamProcessor, StreamEvent, StreamEventType
from ..graph_analytics.neo4j_integration import Neo4jGenomicsGraph

logger = logging.getLogger(__name__)


class PipelineType(Enum):
    """Enumeration of pipeline types."""
    ARGO_WORKFLOW = "argo_workflow"
    SNAKEMAKE = "snakemake"
    NEXTFLOW = "nextflow"
    CUSTOM = "custom"
    HYBRID = "hybrid"


class PipelineStatus(Enum):
    """Enumeration of pipeline statuses."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    PAUSED = "paused"


class ResourceType(Enum):
    """Enumeration of resource types."""
    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    GPU = "gpu"
    NETWORK = "network"


@dataclass
class PipelineResource:
    """Represents pipeline resource requirements."""
    resource_type: ResourceType
    amount: float
    unit: str = "cores"  # cores, Gi, Ti, etc.
    min_amount: float = None
    max_amount: float = None
    
    def __post_init__(self):
        if self.min_amount is None:
            self.min_amount = self.amount
        if self.max_amount is None:
            self.max_amount = self.amount


@dataclass
class PipelineDefinition:
    """Represents a pipeline definition."""
    pipeline_id: str
    name: str
    description: str
    pipeline_type: PipelineType
    version: str
    author: str
    created_at: datetime
    updated_at: datetime
    tags: List[str] = None
    parameters: Dict[str, Any] = None
    resources: List[PipelineResource] = None
    dependencies: List[str] = None
    outputs: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.parameters is None:
            self.parameters = {}
        if self.resources is None:
            self.resources = []
        if self.dependencies is None:
            self.dependencies = []
        if self.outputs is None:
            self.outputs = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PipelineExecution:
    """Represents a pipeline execution."""
    execution_id: str
    pipeline_id: str
    status: PipelineStatus
    started_at: datetime
    completed_at: datetime = None
    parameters: Dict[str, Any] = None
    inputs: Dict[str, Any] = None
    outputs: Dict[str, Any] = None
    logs: List[str] = None
    error_message: str = None
    resource_usage: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        if self.inputs is None:
            self.inputs = {}
        if self.outputs is None:
            self.outputs = {}
        if self.logs is None:
            self.logs = []
        if self.resource_usage is None:
            self.resource_usage = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class WorkflowStep:
    """Represents a workflow step."""
    step_id: str
    name: str
    description: str
    pipeline_id: str
    parameters: Dict[str, Any] = None
    dependencies: List[str] = None
    condition: str = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 3600  # seconds
    resources: List[PipelineResource] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        if self.dependencies is None:
            self.dependencies = []
        if self.resources is None:
            self.resources = []


@dataclass
class WorkflowDefinition:
    """Represents a workflow definition."""
    workflow_id: str
    name: str
    description: str
    version: str
    author: str
    created_at: datetime
    updated_at: datetime
    steps: List[WorkflowStep] = None
    parameters: Dict[str, Any] = None
    global_resources: List[PipelineResource] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.steps is None:
            self.steps = []
        if self.parameters is None:
            self.parameters = {}
        if self.global_resources is None:
            self.global_resources = []
        if self.metadata is None:
            self.metadata = {}


class UnifiedPipelineOrchestrator:
    """
    Unified pipeline orchestrator for cancer genomics analysis.
    
    Provides functionality to:
    - Manage pipeline definitions and executions
    - Orchestrate complex workflows
    - Integrate with Argo Workflows, Snakemake, and Nextflow
    - Handle real-time processing and notifications
    - Manage resources and dependencies
    """
    
    def __init__(
        self,
        kafka_processor: Optional[KafkaStreamProcessor] = None,
        neo4j_graph: Optional[Neo4jGenomicsGraph] = None,
        kubernetes_config: Optional[str] = None
    ):
        """
        Initialize unified pipeline orchestrator.
        
        Args:
            kafka_processor: Optional Kafka stream processor
            neo4j_graph: Optional Neo4j graph database
            kubernetes_config: Optional Kubernetes configuration path
        """
        self.kafka_processor = kafka_processor
        self.neo4j_graph = neo4j_graph
        
        # Pipeline managers
        self.workflow_executor = WorkflowExecutor()
        self.nextflow_manager = NextflowManager()
        self.snakemake_manager = SnakemakeManager()
        
        # Kubernetes client
        self.k8s_client = None
        if kubernetes_config:
            self._initialize_kubernetes_client(kubernetes_config)
        
        # Pipeline registry
        self.pipeline_registry: Dict[str, PipelineDefinition] = {}
        self.workflow_registry: Dict[str, WorkflowDefinition] = {}
        self.execution_registry: Dict[str, PipelineExecution] = {}
        
        # Execution state
        self.is_running = False
        self.execution_threads = []
        self.resource_monitor = ResourceMonitor()
        
        # Metrics
        self.metrics = {
            "pipelines_executed": 0,
            "pipelines_failed": 0,
            "workflows_executed": 0,
            "workflows_failed": 0,
            "total_execution_time": 0.0,
            "average_execution_time": 0.0
        }
        
        # Initialize default pipelines
        self._initialize_default_pipelines()
    
    def _initialize_kubernetes_client(self, config_path: str):
        """Initialize Kubernetes client."""
        try:
            if config_path:
                config.load_kube_config(config_file=config_path)
            else:
                config.load_incluster_config()
            
            self.k8s_client = client.ApiClient()
            logger.info("Kubernetes client initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            self.k8s_client = None
    
    def _initialize_default_pipelines(self):
        """Initialize default pipeline definitions."""
        # Variant calling pipeline
        variant_calling_pipeline = PipelineDefinition(
            pipeline_id="variant_calling_v1",
            name="Variant Calling Pipeline",
            description="Comprehensive variant calling pipeline for cancer genomics",
            pipeline_type=PipelineType.ARGO_WORKFLOW,
            version="1.0.0",
            author="Cancer Genomics Team",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=["variant_calling", "cancer", "genomics"],
            parameters={
                "input_fastq": {"type": "string", "required": True, "description": "Input FASTQ files"},
                "reference_genome": {"type": "string", "required": True, "description": "Reference genome"},
                "sample_id": {"type": "string", "required": True, "description": "Sample identifier"},
                "output_dir": {"type": "string", "required": True, "description": "Output directory"}
            },
            resources=[
                PipelineResource(ResourceType.CPU, 8, "cores"),
                PipelineResource(ResourceType.MEMORY, 32, "Gi"),
                PipelineResource(ResourceType.STORAGE, 100, "Gi")
            ],
            outputs=["variants.vcf", "quality_metrics.txt", "coverage_stats.txt"]
        )
        
        # Expression analysis pipeline
        expression_pipeline = PipelineDefinition(
            pipeline_id="expression_analysis_v1",
            name="Expression Analysis Pipeline",
            description="RNA-seq expression analysis pipeline",
            pipeline_type=PipelineType.NEXTFLOW,
            version="1.0.0",
            author="Cancer Genomics Team",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=["expression", "rna_seq", "genomics"],
            parameters={
                "input_fastq": {"type": "string", "required": True, "description": "Input FASTQ files"},
                "reference_genome": {"type": "string", "required": True, "description": "Reference genome"},
                "gtf_file": {"type": "string", "required": True, "description": "GTF annotation file"},
                "sample_id": {"type": "string", "required": True, "description": "Sample identifier"}
            },
            resources=[
                PipelineResource(ResourceType.CPU, 16, "cores"),
                PipelineResource(ResourceType.MEMORY, 64, "Gi"),
                PipelineResource(ResourceType.STORAGE, 200, "Gi")
            ],
            outputs=["expression_matrix.txt", "differential_genes.txt", "pathway_analysis.txt"]
        )
        
        # Multi-omics integration pipeline
        multi_omics_pipeline = PipelineDefinition(
            pipeline_id="multi_omics_v1",
            name="Multi-Omics Integration Pipeline",
            description="Multi-omics data integration and analysis",
            pipeline_type=PipelineType.SNAKEMAKE,
            version="1.0.0",
            author="Cancer Genomics Team",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=["multi_omics", "integration", "genomics"],
            parameters={
                "genomics_data": {"type": "string", "required": True, "description": "Genomics data path"},
                "transcriptomics_data": {"type": "string", "required": True, "description": "Transcriptomics data path"},
                "epigenomics_data": {"type": "string", "required": True, "description": "Epigenomics data path"},
                "clinical_data": {"type": "string", "required": True, "description": "Clinical data path"}
            },
            resources=[
                PipelineResource(ResourceType.CPU, 32, "cores"),
                PipelineResource(ResourceType.MEMORY, 128, "Gi"),
                PipelineResource(ResourceType.STORAGE, 500, "Gi")
            ],
            outputs=["integrated_data.csv", "pathway_analysis.txt", "biomarker_analysis.txt"]
        )
        
        # Register pipelines
        self.register_pipeline(variant_calling_pipeline)
        self.register_pipeline(expression_pipeline)
        self.register_pipeline(multi_omics_pipeline)
        
        logger.info("Default pipelines initialized")
    
    def register_pipeline(self, pipeline: PipelineDefinition) -> bool:
        """
        Register a pipeline definition.
        
        Args:
            pipeline: Pipeline definition to register
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.pipeline_registry[pipeline.pipeline_id] = pipeline
            logger.info(f"Registered pipeline: {pipeline.pipeline_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register pipeline {pipeline.pipeline_id}: {e}")
            return False
    
    def unregister_pipeline(self, pipeline_id: str) -> bool:
        """
        Unregister a pipeline definition.
        
        Args:
            pipeline_id: Pipeline identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if pipeline_id in self.pipeline_registry:
                del self.pipeline_registry[pipeline_id]
                logger.info(f"Unregistered pipeline: {pipeline_id}")
                return True
            else:
                logger.warning(f"Pipeline {pipeline_id} not found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to unregister pipeline {pipeline_id}: {e}")
            return False
    
    def get_pipeline(self, pipeline_id: str) -> Optional[PipelineDefinition]:
        """
        Get a pipeline definition.
        
        Args:
            pipeline_id: Pipeline identifier
            
        Returns:
            Pipeline definition or None if not found
        """
        return self.pipeline_registry.get(pipeline_id)
    
    def list_pipelines(self, tags: List[str] = None) -> List[PipelineDefinition]:
        """
        List pipeline definitions.
        
        Args:
            tags: Optional list of tags to filter by
            
        Returns:
            List of pipeline definitions
        """
        pipelines = list(self.pipeline_registry.values())
        
        if tags:
            filtered_pipelines = []
            for pipeline in pipelines:
                if any(tag in pipeline.tags for tag in tags):
                    filtered_pipelines.append(pipeline)
            return filtered_pipelines
        
        return pipelines
    
    def register_workflow(self, workflow: WorkflowDefinition) -> bool:
        """
        Register a workflow definition.
        
        Args:
            workflow: Workflow definition to register
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate workflow
            if not self._validate_workflow(workflow):
                raise ValueError("Invalid workflow definition")
            
            self.workflow_registry[workflow.workflow_id] = workflow
            logger.info(f"Registered workflow: {workflow.workflow_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register workflow {workflow.workflow_id}: {e}")
            return False
    
    def _validate_workflow(self, workflow: WorkflowDefinition) -> bool:
        """
        Validate a workflow definition.
        
        Args:
            workflow: Workflow definition to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check if all referenced pipelines exist
            for step in workflow.steps:
                if step.pipeline_id not in self.pipeline_registry:
                    logger.error(f"Pipeline {step.pipeline_id} not found for step {step.step_id}")
                    return False
            
            # Check for circular dependencies
            if self._has_circular_dependencies(workflow):
                logger.error(f"Circular dependencies detected in workflow {workflow.workflow_id}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating workflow: {e}")
            return False
    
    def _has_circular_dependencies(self, workflow: WorkflowDefinition) -> bool:
        """
        Check for circular dependencies in workflow.
        
        Args:
            workflow: Workflow definition to check
            
        Returns:
            True if circular dependencies exist, False otherwise
        """
        try:
            # Build dependency graph
            graph = {}
            for step in workflow.steps:
                graph[step.step_id] = step.dependencies
            
            # Check for cycles using DFS
            visited = set()
            rec_stack = set()
            
            def has_cycle(node):
                visited.add(node)
                rec_stack.add(node)
                
                for neighbor in graph.get(node, []):
                    if neighbor not in visited:
                        if has_cycle(neighbor):
                            return True
                    elif neighbor in rec_stack:
                        return True
                
                rec_stack.remove(node)
                return False
            
            for node in graph:
                if node not in visited:
                    if has_cycle(node):
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking circular dependencies: {e}")
            return True
    
    def execute_pipeline(
        self,
        pipeline_id: str,
        parameters: Dict[str, Any],
        inputs: Dict[str, Any] = None,
        execution_id: str = None
    ) -> str:
        """
        Execute a pipeline.
        
        Args:
            pipeline_id: Pipeline identifier
            parameters: Pipeline parameters
            inputs: Pipeline inputs
            execution_id: Optional execution identifier
            
        Returns:
            Execution identifier
        """
        try:
            # Get pipeline definition
            pipeline = self.get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline {pipeline_id} not found")
            
            # Generate execution ID if not provided
            if not execution_id:
                execution_id = f"{pipeline_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            # Create execution record
            execution = PipelineExecution(
                execution_id=execution_id,
                pipeline_id=pipeline_id,
                status=PipelineStatus.PENDING,
                started_at=datetime.now(),
                parameters=parameters,
                inputs=inputs or {}
            )
            
            # Register execution
            self.execution_registry[execution_id] = execution
            
            # Check resource availability
            if not self.resource_monitor.check_resources(pipeline.resources):
                execution.status = PipelineStatus.QUEUED
                logger.info(f"Pipeline {pipeline_id} queued due to resource constraints")
                return execution_id
            
            # Execute pipeline
            self._execute_pipeline_async(execution)
            
            return execution_id
            
        except Exception as e:
            logger.error(f"Failed to execute pipeline {pipeline_id}: {e}")
            if execution_id and execution_id in self.execution_registry:
                self.execution_registry[execution_id].status = PipelineStatus.FAILED
                self.execution_registry[execution_id].error_message = str(e)
            raise
    
    def _execute_pipeline_async(self, execution: PipelineExecution):
        """Execute pipeline asynchronously."""
        def run_pipeline():
            try:
                # Update status
                execution.status = PipelineStatus.RUNNING
                
                # Get pipeline definition
                pipeline = self.get_pipeline(execution.pipeline_id)
                
                # Allocate resources
                self.resource_monitor.allocate_resources(pipeline.resources)
                
                # Execute based on pipeline type
                if pipeline.pipeline_type == PipelineType.ARGO_WORKFLOW:
                    result = self._execute_argo_workflow(execution, pipeline)
                elif pipeline.pipeline_type == PipelineType.NEXTFLOW:
                    result = self._execute_nextflow_pipeline(execution, pipeline)
                elif pipeline.pipeline_type == PipelineType.SNAKEMAKE:
                    result = self._execute_snakemake_pipeline(execution, pipeline)
                else:
                    raise ValueError(f"Unsupported pipeline type: {pipeline.pipeline_type}")
                
                # Update execution
                execution.status = PipelineStatus.COMPLETED
                execution.completed_at = datetime.now()
                execution.outputs = result
                
                # Update metrics
                self.metrics["pipelines_executed"] += 1
                execution_time = (execution.completed_at - execution.started_at).total_seconds()
                self.metrics["total_execution_time"] += execution_time
                self.metrics["average_execution_time"] = (
                    self.metrics["total_execution_time"] / self.metrics["pipelines_executed"]
                )
                
                # Send notification
                if self.kafka_processor:
                    self._send_execution_notification(execution, "completed")
                
                logger.info(f"Pipeline execution {execution.execution_id} completed successfully")
                
            except Exception as e:
                # Update execution
                execution.status = PipelineStatus.FAILED
                execution.completed_at = datetime.now()
                execution.error_message = str(e)
                
                # Update metrics
                self.metrics["pipelines_failed"] += 1
                
                # Send notification
                if self.kafka_processor:
                    self._send_execution_notification(execution, "failed")
                
                logger.error(f"Pipeline execution {execution.execution_id} failed: {e}")
                
            finally:
                # Release resources
                pipeline = self.get_pipeline(execution.pipeline_id)
                if pipeline:
                    self.resource_monitor.release_resources(pipeline.resources)
        
        # Start execution thread
        thread = threading.Thread(target=run_pipeline, daemon=True)
        thread.start()
        self.execution_threads.append(thread)
    
    def _execute_argo_workflow(self, execution: PipelineExecution, pipeline: PipelineDefinition) -> Dict[str, Any]:
        """Execute Argo workflow."""
        try:
            # Create workflow template
            workflow_template = self._create_argo_workflow_template(pipeline, execution.parameters)
            
            # Submit workflow
            result = self.workflow_executor.submit_workflow(workflow_template)
            
            # Wait for completion
            status = self.workflow_executor.wait_for_completion(result["workflow_id"])
            
            if status == "Succeeded":
                # Get outputs
                outputs = self.workflow_executor.get_workflow_outputs(result["workflow_id"])
                return outputs
            else:
                raise Exception(f"Workflow failed with status: {status}")
                
        except Exception as e:
            logger.error(f"Error executing Argo workflow: {e}")
            raise
    
    def _execute_nextflow_pipeline(self, execution: PipelineExecution, pipeline: PipelineDefinition) -> Dict[str, Any]:
        """Execute Nextflow pipeline."""
        try:
            # Create pipeline script
            pipeline_script = self._create_nextflow_pipeline_script(pipeline, execution.parameters)
            
            # Execute pipeline
            result = self.nextflow_manager.execute_pipeline(
                pipeline_script=pipeline_script,
                params=execution.parameters,
                pipeline_name=execution.execution_id
            )
            
            if result["status"] == "completed":
                # Get outputs
                outputs = self.nextflow_manager.get_pipeline_outputs(execution.execution_id)
                return outputs
            else:
                raise Exception(f"Nextflow pipeline failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error executing Nextflow pipeline: {e}")
            raise
    
    def _execute_snakemake_pipeline(self, execution: PipelineExecution, pipeline: PipelineDefinition) -> Dict[str, Any]:
        """Execute Snakemake pipeline."""
        try:
            # Create Snakefile
            snakefile = self._create_snakemake_snakefile(pipeline, execution.parameters)
            
            # Execute pipeline
            result = self.snakemake_manager.execute_pipeline(
                snakefile=snakefile,
                params=execution.parameters,
                pipeline_name=execution.execution_id
            )
            
            if result["status"] == "completed":
                # Get outputs
                outputs = self.snakemake_manager.get_pipeline_outputs(execution.execution_id)
                return outputs
            else:
                raise Exception(f"Snakemake pipeline failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error executing Snakemake pipeline: {e}")
            raise
    
    def _create_argo_workflow_template(self, pipeline: PipelineDefinition, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Create Argo workflow template."""
        # This would create the actual Argo workflow YAML
        # For now, return a placeholder
        return {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Workflow",
            "metadata": {
                "name": f"{pipeline.pipeline_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "namespace": "argo"
            },
            "spec": {
                "entrypoint": "main",
                "templates": [
                    {
                        "name": "main",
                        "container": {
                            "image": "genomics-pipeline:latest",
                            "command": ["python", "pipeline.py"],
                            "args": [json.dumps(parameters)]
                        }
                    }
                ]
            }
        }
    
    def _create_nextflow_pipeline_script(self, pipeline: PipelineDefinition, parameters: Dict[str, Any]) -> str:
        """Create Nextflow pipeline script."""
        # This would create the actual Nextflow script
        # For now, return a placeholder
        return f"""
        #!/usr/bin/env nextflow
        
        params.input = "{parameters.get('input_fastq', '')}"
        params.output = "{parameters.get('output_dir', '')}"
        
        workflow {{
            // Pipeline steps would go here
        }}
        """
    
    def _create_snakemake_snakefile(self, pipeline: PipelineDefinition, parameters: Dict[str, Any]) -> str:
        """Create Snakemake Snakefile."""
        # This would create the actual Snakefile
        # For now, return a placeholder
        return f"""
        # Snakemake pipeline for {pipeline.name}
        
        rule all:
            input: "{parameters.get('output_dir', '')}/results.txt"
        
        rule process_data:
            input: "{parameters.get('input_fastq', '')}"
            output: "{parameters.get('output_dir', '')}/results.txt"
            shell: "echo 'Processing data' > {{output}}"
        """
    
    def execute_workflow(
        self,
        workflow_id: str,
        parameters: Dict[str, Any],
        inputs: Dict[str, Any] = None
    ) -> str:
        """
        Execute a workflow.
        
        Args:
            workflow_id: Workflow identifier
            parameters: Workflow parameters
            inputs: Workflow inputs
            
        Returns:
            Execution identifier
        """
        try:
            # Get workflow definition
            workflow = self.workflow_registry.get(workflow_id)
            if not workflow:
                raise ValueError(f"Workflow {workflow_id} not found")
            
            # Generate execution ID
            execution_id = f"{workflow_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            # Execute workflow
            self._execute_workflow_async(workflow, execution_id, parameters, inputs or {})
            
            return execution_id
            
        except Exception as e:
            logger.error(f"Failed to execute workflow {workflow_id}: {e}")
            raise
    
    def _execute_workflow_async(self, workflow: WorkflowDefinition, execution_id: str, parameters: Dict[str, Any], inputs: Dict[str, Any]):
        """Execute workflow asynchronously."""
        def run_workflow():
            try:
                # Create execution context
                context = {
                    "execution_id": execution_id,
                    "workflow_id": workflow.workflow_id,
                    "parameters": parameters,
                    "inputs": inputs,
                    "step_results": {},
                    "step_statuses": {}
                }
                
                # Execute workflow steps
                self._execute_workflow_steps(workflow, context)
                
                # Update metrics
                self.metrics["workflows_executed"] += 1
                
                # Send notification
                if self.kafka_processor:
                    self._send_workflow_notification(workflow, execution_id, "completed")
                
                logger.info(f"Workflow execution {execution_id} completed successfully")
                
            except Exception as e:
                # Update metrics
                self.metrics["workflows_failed"] += 1
                
                # Send notification
                if self.kafka_processor:
                    self._send_workflow_notification(workflow, execution_id, "failed")
                
                logger.error(f"Workflow execution {execution_id} failed: {e}")
        
        # Start execution thread
        thread = threading.Thread(target=run_workflow, daemon=True)
        thread.start()
        self.execution_threads.append(thread)
    
    def _execute_workflow_steps(self, workflow: WorkflowDefinition, context: Dict[str, Any]):
        """Execute workflow steps in dependency order."""
        # Build execution order
        execution_order = self._build_execution_order(workflow.steps)
        
        # Execute steps in order
        for step_group in execution_order:
            # Execute steps in parallel within each group
            with ThreadPoolExecutor(max_workers=len(step_group)) as executor:
                futures = []
                for step in step_group:
                    future = executor.submit(self._execute_workflow_step, step, context)
                    futures.append(future)
                
                # Wait for all steps in group to complete
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if not result:
                            raise Exception("Step execution failed")
                    except Exception as e:
                        logger.error(f"Error executing workflow step: {e}")
                        raise
    
    def _build_execution_order(self, steps: List[WorkflowStep]) -> List[List[WorkflowStep]]:
        """Build execution order for workflow steps."""
        # This is a simplified topological sort
        # In practice, you'd want a more robust implementation
        
        execution_order = []
        remaining_steps = steps.copy()
        completed_steps = set()
        
        while remaining_steps:
            # Find steps with no pending dependencies
            ready_steps = []
            for step in remaining_steps:
                if all(dep in completed_steps for dep in step.dependencies):
                    ready_steps.append(step)
            
            if not ready_steps:
                raise Exception("Circular dependency detected in workflow")
            
            # Add ready steps to execution order
            execution_order.append(ready_steps)
            
            # Update state
            for step in ready_steps:
                completed_steps.add(step.step_id)
                remaining_steps.remove(step)
        
        return execution_order
    
    def _execute_workflow_step(self, step: WorkflowStep, context: Dict[str, Any]) -> bool:
        """Execute a single workflow step."""
        try:
            # Get pipeline definition
            pipeline = self.get_pipeline(step.pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline {step.pipeline_id} not found")
            
            # Prepare step parameters
            step_parameters = context["parameters"].copy()
            step_parameters.update(step.parameters)
            
            # Execute pipeline
            execution_id = self.execute_pipeline(
                pipeline_id=step.pipeline_id,
                parameters=step_parameters,
                inputs=context["inputs"]
            )
            
            # Wait for completion
            while True:
                execution = self.execution_registry.get(execution_id)
                if not execution:
                    raise Exception("Execution not found")
                
                if execution.status == PipelineStatus.COMPLETED:
                    # Store result
                    context["step_results"][step.step_id] = execution.outputs
                    context["step_statuses"][step.step_id] = "completed"
                    return True
                elif execution.status == PipelineStatus.FAILED:
                    # Handle failure
                    if step.retry_count < step.max_retries:
                        step.retry_count += 1
                        logger.info(f"Retrying step {step.step_id} (attempt {step.retry_count})")
                        return self._execute_workflow_step(step, context)
                    else:
                        context["step_statuses"][step.step_id] = "failed"
                        raise Exception(f"Step {step.step_id} failed after {step.max_retries} retries")
                
                # Wait before checking again
                time.sleep(5)
                
        except Exception as e:
            logger.error(f"Error executing workflow step {step.step_id}: {e}")
            context["step_statuses"][step.step_id] = "failed"
            return False
    
    def get_execution_status(self, execution_id: str) -> Optional[PipelineExecution]:
        """
        Get execution status.
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            Pipeline execution or None if not found
        """
        return self.execution_registry.get(execution_id)
    
    def cancel_execution(self, execution_id: str) -> bool:
        """
        Cancel a pipeline execution.
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            execution = self.execution_registry.get(execution_id)
            if not execution:
                logger.warning(f"Execution {execution_id} not found")
                return False
            
            if execution.status in [PipelineStatus.COMPLETED, PipelineStatus.FAILED, PipelineStatus.CANCELLED]:
                logger.warning(f"Execution {execution_id} is already {execution.status.value}")
                return False
            
            # Cancel execution
            execution.status = PipelineStatus.CANCELLED
            execution.completed_at = datetime.now()
            
            # Release resources
            pipeline = self.get_pipeline(execution.pipeline_id)
            if pipeline:
                self.resource_monitor.release_resources(pipeline.resources)
            
            # Send notification
            if self.kafka_processor:
                self._send_execution_notification(execution, "cancelled")
            
            logger.info(f"Execution {execution_id} cancelled")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel execution {execution_id}: {e}")
            return False
    
    def _send_execution_notification(self, execution: PipelineExecution, status: str):
        """Send execution notification."""
        try:
            if not self.kafka_processor:
                return
            
            event = StreamEvent(
                event_id=str(uuid.uuid4()),
                event_type=StreamEventType.WORKFLOW_EVENT,
                timestamp=datetime.now(),
                source="pipeline_orchestrator",
                data={
                    "execution_id": execution.execution_id,
                    "pipeline_id": execution.pipeline_id,
                    "status": status,
                    "execution_status": execution.status.value,
                    "started_at": execution.started_at.isoformat(),
                    "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                    "error_message": execution.error_message
                }
            )
            
            self.kafka_processor.produce_event("workflow-events", event)
            
        except Exception as e:
            logger.error(f"Error sending execution notification: {e}")
    
    def _send_workflow_notification(self, workflow: WorkflowDefinition, execution_id: str, status: str):
        """Send workflow notification."""
        try:
            if not self.kafka_processor:
                return
            
            event = StreamEvent(
                event_id=str(uuid.uuid4()),
                event_type=StreamEventType.WORKFLOW_EVENT,
                timestamp=datetime.now(),
                source="pipeline_orchestrator",
                data={
                    "execution_id": execution_id,
                    "workflow_id": workflow.workflow_id,
                    "status": status,
                    "workflow_name": workflow.name
                }
            )
            
            self.kafka_processor.produce_event("workflow-events", event)
            
        except Exception as e:
            logger.error(f"Error sending workflow notification: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get orchestrator metrics.
        
        Returns:
            Dictionary with metrics
        """
        metrics = self.metrics.copy()
        
        # Add current state
        metrics["active_executions"] = len([
            e for e in self.execution_registry.values()
            if e.status in [PipelineStatus.RUNNING, PipelineStatus.PENDING, PipelineStatus.QUEUED]
        ])
        
        metrics["total_executions"] = len(self.execution_registry)
        metrics["registered_pipelines"] = len(self.pipeline_registry)
        metrics["registered_workflows"] = len(self.workflow_registry)
        
        return metrics
    
    def cleanup_old_executions(self, days_old: int = 7):
        """
        Clean up old execution records.
        
        Args:
            days_old: Number of days old to clean up
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            old_executions = [
                execution_id for execution_id, execution in self.execution_registry.items()
                if execution.completed_at and execution.completed_at < cutoff_date
            ]
            
            for execution_id in old_executions:
                del self.execution_registry[execution_id]
            
            logger.info(f"Cleaned up {len(old_executions)} old execution records")
            
        except Exception as e:
            logger.error(f"Error cleaning up old executions: {e}")


class ResourceMonitor:
    """
    Resource monitor for pipeline orchestration.
    
    Tracks and manages resource allocation for pipeline executions.
    """
    
    def __init__(self):
        """Initialize resource monitor."""
        self.allocated_resources: Dict[str, List[PipelineResource]] = {}
        self.total_resources: Dict[ResourceType, float] = {
            ResourceType.CPU: 100.0,  # Total CPU cores
            ResourceType.MEMORY: 1000.0,  # Total memory in Gi
            ResourceType.STORAGE: 10000.0,  # Total storage in Gi
            ResourceType.GPU: 10.0,  # Total GPUs
            ResourceType.NETWORK: 1000.0  # Total network bandwidth in Mbps
        }
    
    def check_resources(self, required_resources: List[PipelineResource]) -> bool:
        """
        Check if required resources are available.
        
        Args:
            required_resources: List of required resources
            
        Returns:
            True if resources are available, False otherwise
        """
        try:
            # Calculate available resources
            available_resources = self._calculate_available_resources()
            
            # Check each required resource
            for resource in required_resources:
                available = available_resources.get(resource.resource_type, 0.0)
                if available < resource.amount:
                    logger.warning(f"Insufficient {resource.resource_type.value}: required {resource.amount}, available {available}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking resources: {e}")
            return False
    
    def allocate_resources(self, resources: List[PipelineResource]) -> bool:
        """
        Allocate resources for pipeline execution.
        
        Args:
            resources: List of resources to allocate
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if resources are available
            if not self.check_resources(resources):
                return False
            
            # Allocate resources
            allocation_id = str(uuid.uuid4())
            self.allocated_resources[allocation_id] = resources.copy()
            
            logger.info(f"Allocated resources: {allocation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error allocating resources: {e}")
            return False
    
    def release_resources(self, resources: List[PipelineResource]) -> bool:
        """
        Release allocated resources.
        
        Args:
            resources: List of resources to release
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find and remove matching allocation
            for allocation_id, allocated_resources in self.allocated_resources.items():
                if self._resources_match(resources, allocated_resources):
                    del self.allocated_resources[allocation_id]
                    logger.info(f"Released resources: {allocation_id}")
                    return True
            
            logger.warning("No matching resource allocation found")
            return False
            
        except Exception as e:
            logger.error(f"Error releasing resources: {e}")
            return False
    
    def _calculate_available_resources(self) -> Dict[ResourceType, float]:
        """Calculate currently available resources."""
        available = self.total_resources.copy()
        
        for allocated_resources in self.allocated_resources.values():
            for resource in allocated_resources:
                available[resource.resource_type] -= resource.amount
        
        return available
    
    def _resources_match(self, resources1: List[PipelineResource], resources2: List[PipelineResource]) -> bool:
        """Check if two resource lists match."""
        if len(resources1) != len(resources2):
            return False
        
        # Sort by resource type for comparison
        sorted1 = sorted(resources1, key=lambda r: r.resource_type.value)
        sorted2 = sorted(resources2, key=lambda r: r.resource_type.value)
        
        for r1, r2 in zip(sorted1, sorted2):
            if (r1.resource_type != r2.resource_type or 
                r1.amount != r2.amount or 
                r1.unit != r2.unit):
                return False
        
        return True
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """
        Get current resource usage.
        
        Returns:
            Dictionary with resource usage information
        """
        try:
            available = self._calculate_available_resources()
            usage = {}
            
            for resource_type, total in self.total_resources.items():
                available_amount = available[resource_type]
                used_amount = total - available_amount
                usage[resource_type.value] = {
                    "total": total,
                    "used": used_amount,
                    "available": available_amount,
                    "usage_percentage": (used_amount / total) * 100 if total > 0 else 0
                }
            
            return usage
            
        except Exception as e:
            logger.error(f"Error getting resource usage: {e}")
            return {}


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Create orchestrator
    orchestrator = UnifiedPipelineOrchestrator()
    
    try:
        # List available pipelines
        pipelines = orchestrator.list_pipelines()
        print(f"Available pipelines: {len(pipelines)}")
        
        # Execute a pipeline
        if pipelines:
            pipeline = pipelines[0]
            execution_id = orchestrator.execute_pipeline(
                pipeline_id=pipeline.pipeline_id,
                parameters={
                    "input_fastq": "/data/sample.fastq",
                    "reference_genome": "/data/hg38.fa",
                    "sample_id": "SAMPLE001",
                    "output_dir": "/data/output"
                }
            )
            print(f"Started execution: {execution_id}")
            
            # Monitor execution
            while True:
                execution = orchestrator.get_execution_status(execution_id)
                if execution:
                    print(f"Execution status: {execution.status.value}")
                    if execution.status in [PipelineStatus.COMPLETED, PipelineStatus.FAILED]:
                        break
                time.sleep(5)
        
        # Get metrics
        metrics = orchestrator.get_metrics()
        print(f"Orchestrator metrics: {json.dumps(metrics, indent=2)}")
        
    except Exception as e:
        logger.error(f"Error in example: {e}")
    finally:
        # Cleanup
        orchestrator.cleanup_old_executions()
