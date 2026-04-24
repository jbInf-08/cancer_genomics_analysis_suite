"""
NGS Pipeline Integration Module

This module provides comprehensive integration for Next-Generation Sequencing (NGS) pipelines,
including pipeline management, execution, monitoring, and integration with the workflow dispatcher.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import yaml
import subprocess
import time
from datetime import datetime, timedelta

from .workflow_dispatcher import WorkflowDispatcher, DockerManager, CeleryJobManager
from ..config.settings import settings

logger = logging.getLogger(__name__)

class PipelineStatus(Enum):
    """Pipeline execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class PipelineType(Enum):
    """Types of NGS pipelines"""
    QUALITY_CONTROL = "quality_control"
    ALIGNMENT = "alignment"
    VARIANT_CALLING = "variant_calling"
    EXPRESSION_ANALYSIS = "expression_analysis"
    CHIP_SEQ = "chip_seq"
    ATAC_SEQ = "atac_seq"
    SINGLE_CELL = "single_cell"
    METAGENOMICS = "metagenomics"
    CUSTOM = "custom"

@dataclass
class PipelineStep:
    """Individual step in an NGS pipeline"""
    name: str
    command: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    timeout: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    status: PipelineStatus = PipelineStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None

@dataclass
class PipelineDefinition:
    """Complete pipeline definition"""
    name: str
    version: str
    description: str
    pipeline_type: PipelineType
    steps: List[PipelineStep]
    inputs: Dict[str, str] = field(default_factory=dict)
    outputs: Dict[str, str] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    requirements: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PipelineExecution:
    """Pipeline execution instance"""
    execution_id: str
    pipeline_definition: PipelineDefinition
    status: PipelineStatus = PipelineStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    current_step: Optional[str] = None
    progress: float = 0.0
    error_message: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

class NGSPipelineManager:
    """Manages NGS pipeline definitions, executions, and monitoring"""
    
    def __init__(self, workflow_dispatcher: WorkflowDispatcher):
        self.workflow_dispatcher = workflow_dispatcher
        self.docker_manager = workflow_dispatcher.docker_manager
        self.celery_manager = workflow_dispatcher.celery_manager
        self.pipelines: Dict[str, PipelineDefinition] = {}
        self.executions: Dict[str, PipelineExecution] = {}
        self.pipeline_dir = Path(settings.ngs_platform.pipeline_directory)
        self.pipeline_dir.mkdir(parents=True, exist_ok=True)
        
    async def load_pipeline_definition(self, pipeline_path: Union[str, Path]) -> PipelineDefinition:
        """Load pipeline definition from YAML or JSON file"""
        try:
            pipeline_path = Path(pipeline_path)
            if not pipeline_path.exists():
                raise FileNotFoundError(f"Pipeline definition not found: {pipeline_path}")
            
            with open(pipeline_path, 'r') as f:
                if pipeline_path.suffix.lower() in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            # Parse pipeline steps
            steps = []
            for step_data in data.get('steps', []):
                step = PipelineStep(
                    name=step_data['name'],
                    command=step_data['command'],
                    inputs=step_data.get('inputs', []),
                    outputs=step_data.get('outputs', []),
                    parameters=step_data.get('parameters', {}),
                    dependencies=step_data.get('dependencies', []),
                    timeout=step_data.get('timeout'),
                    max_retries=step_data.get('max_retries', 3)
                )
                steps.append(step)
            
            pipeline = PipelineDefinition(
                name=data['name'],
                version=data['version'],
                description=data.get('description', ''),
                pipeline_type=PipelineType(data.get('type', 'custom')),
                steps=steps,
                inputs=data.get('inputs', {}),
                outputs=data.get('outputs', {}),
                parameters=data.get('parameters', {}),
                requirements=data.get('requirements', {}),
                metadata=data.get('metadata', {})
            )
            
            self.pipelines[pipeline.name] = pipeline
            logger.info(f"Loaded pipeline definition: {pipeline.name} v{pipeline.version}")
            return pipeline
            
        except Exception as e:
            logger.error(f"Failed to load pipeline definition from {pipeline_path}: {e}")
            raise
    
    async def save_pipeline_definition(self, pipeline: PipelineDefinition, 
                                     output_path: Optional[Union[str, Path]] = None) -> Path:
        """Save pipeline definition to file"""
        try:
            if output_path is None:
                output_path = self.pipeline_dir / f"{pipeline.name}_v{pipeline.version}.yaml"
            
            output_path = Path(output_path)
            
            # Convert pipeline to dictionary
            data = {
                'name': pipeline.name,
                'version': pipeline.version,
                'description': pipeline.description,
                'type': pipeline.pipeline_type.value,
                'steps': [
                    {
                        'name': step.name,
                        'command': step.command,
                        'inputs': step.inputs,
                        'outputs': step.outputs,
                        'parameters': step.parameters,
                        'dependencies': step.dependencies,
                        'timeout': step.timeout,
                        'max_retries': step.max_retries
                    }
                    for step in pipeline.steps
                ],
                'inputs': pipeline.inputs,
                'outputs': pipeline.outputs,
                'parameters': pipeline.parameters,
                'requirements': pipeline.requirements,
                'metadata': pipeline.metadata
            }
            
            with open(output_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, indent=2)
            
            logger.info(f"Saved pipeline definition to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to save pipeline definition: {e}")
            raise
    
    async def execute_pipeline(self, pipeline_name: str, inputs: Dict[str, Any], 
                             parameters: Optional[Dict[str, Any]] = None,
                             execution_id: Optional[str] = None) -> str:
        """Execute a pipeline with given inputs and parameters"""
        try:
            if pipeline_name not in self.pipelines:
                raise ValueError(f"Pipeline not found: {pipeline_name}")
            
            pipeline = self.pipelines[pipeline_name]
            
            if execution_id is None:
                execution_id = f"{pipeline_name}_{int(time.time())}"
            
            # Create execution instance
            execution = PipelineExecution(
                execution_id=execution_id,
                pipeline_definition=pipeline
            )
            
            self.executions[execution_id] = execution
            
            # Submit to Celery for execution
            task = self.celery_manager.submit_job(
                job_type="pipeline_execution",
                parameters={
                    'execution_id': execution_id,
                    'pipeline_name': pipeline_name,
                    'inputs': inputs,
                    'parameters': parameters or {}
                }
            )
            
            execution.status = PipelineStatus.RUNNING
            execution.start_time = datetime.now()
            
            logger.info(f"Started pipeline execution: {execution_id}")
            return execution_id
            
        except Exception as e:
            logger.error(f"Failed to execute pipeline {pipeline_name}: {e}")
            raise
    
    async def get_execution_status(self, execution_id: str) -> PipelineExecution:
        """Get status of a pipeline execution"""
        if execution_id not in self.executions:
            raise ValueError(f"Execution not found: {execution_id}")
        
        execution = self.executions[execution_id]
        
        # Update status from Celery if running
        if execution.status == PipelineStatus.RUNNING:
            task_status = self.celery_manager.get_task_status(execution_id)
            if task_status:
                execution.status = PipelineStatus(task_status)
                if execution.status in [PipelineStatus.COMPLETED, PipelineStatus.FAILED]:
                    execution.end_time = datetime.now()
        
        return execution
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running pipeline execution"""
        try:
            if execution_id not in self.executions:
                raise ValueError(f"Execution not found: {execution_id}")
            
            execution = self.executions[execution_id]
            
            if execution.status == PipelineStatus.RUNNING:
                # Cancel Celery task
                success = self.celery_manager.cancel_task(execution_id)
                if success:
                    execution.status = PipelineStatus.CANCELLED
                    execution.end_time = datetime.now()
                    logger.info(f"Cancelled pipeline execution: {execution_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to cancel execution {execution_id}: {e}")
            return False
    
    async def get_pipeline_logs(self, execution_id: str) -> List[str]:
        """Get logs for a pipeline execution"""
        if execution_id not in self.executions:
            raise ValueError(f"Execution not found: {execution_id}")
        
        execution = self.executions[execution_id]
        return execution.logs
    
    async def list_pipelines(self) -> List[PipelineDefinition]:
        """List all available pipeline definitions"""
        return list(self.pipelines.values())
    
    async def list_executions(self, status_filter: Optional[PipelineStatus] = None) -> List[PipelineExecution]:
        """List all pipeline executions, optionally filtered by status"""
        executions = list(self.executions.values())
        
        if status_filter:
            executions = [e for e in executions if e.status == status_filter]
        
        return executions
    
    async def cleanup_old_executions(self, days_old: int = 30) -> int:
        """Clean up old completed/failed executions"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        cleaned_count = 0
        
        for execution_id, execution in list(self.executions.items()):
            if (execution.status in [PipelineStatus.COMPLETED, PipelineStatus.FAILED, PipelineStatus.CANCELLED] 
                and execution.end_time and execution.end_time < cutoff_date):
                del self.executions[execution_id]
                cleaned_count += 1
        
        logger.info(f"Cleaned up {cleaned_count} old executions")
        return cleaned_count

class PipelineStepExecutor:
    """Executes individual pipeline steps"""
    
    def __init__(self, docker_manager: DockerManager):
        self.docker_manager = docker_manager
    
    async def execute_step(self, step: PipelineStep, inputs: Dict[str, Any], 
                          parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single pipeline step"""
        try:
            step.status = PipelineStatus.RUNNING
            step.start_time = datetime.now()
            
            # Prepare command with parameters
            command = self._prepare_command(step, inputs, parameters)
            
            # Execute in Docker container if specified
            if 'docker_image' in step.parameters:
                result = await self._execute_in_docker(step, command)
            else:
                result = await self._execute_locally(step, command)
            
            step.status = PipelineStatus.COMPLETED
            step.end_time = datetime.now()
            
            return result
            
        except Exception as e:
            step.status = PipelineStatus.FAILED
            step.error_message = str(e)
            step.end_time = datetime.now()
            logger.error(f"Step {step.name} failed: {e}")
            raise
    
    def _prepare_command(self, step: PipelineStep, inputs: Dict[str, Any], 
                        parameters: Dict[str, Any]) -> str:
        """Prepare command string with inputs and parameters"""
        command = step.command
        
        # Replace input placeholders
        for input_name, input_value in inputs.items():
            placeholder = f"{{{input_name}}}"
            command = command.replace(placeholder, str(input_value))
        
        # Replace parameter placeholders
        for param_name, param_value in parameters.items():
            placeholder = f"{{{param_name}}}"
            command = command.replace(placeholder, str(param_value))
        
        return command
    
    async def _execute_in_docker(self, step: PipelineStep, command: str) -> Dict[str, Any]:
        """Execute command in Docker container"""
        docker_image = step.parameters['docker_image']
        container_name = f"pipeline_step_{step.name}_{int(time.time())}"
        
        # Pull image if needed
        await self.docker_manager.pull_image(docker_image)
        
        # Create and start container
        container_id = await self.docker_manager.create_container(
            image=docker_image,
            command=command,
            name=container_name,
            environment=step.parameters.get('environment', {}),
            volumes=step.parameters.get('volumes', {})
        )
        
        await self.docker_manager.start_container(container_id)
        
        # Wait for completion
        exit_code = await self.docker_manager.wait_for_container(container_id)
        
        # Get logs
        logs = await self.docker_manager.get_container_logs(container_id)
        
        # Clean up container
        await self.docker_manager.remove_container(container_id)
        
        if exit_code != 0:
            raise RuntimeError(f"Container execution failed with exit code {exit_code}")
        
        return {
            'exit_code': exit_code,
            'logs': logs,
            'container_id': container_id
        }
    
    async def _execute_locally(self, step: PipelineStep, command: str) -> Dict[str, Any]:
        """Execute command locally"""
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"Command failed with exit code {process.returncode}: {stderr.decode()}")
        
        return {
            'exit_code': process.returncode,
            'stdout': stdout.decode(),
            'stderr': stderr.decode()
        }

class PipelineValidator:
    """Validates pipeline definitions and executions"""
    
    @staticmethod
    def validate_pipeline_definition(pipeline: PipelineDefinition) -> List[str]:
        """Validate a pipeline definition"""
        errors = []
        
        # Check required fields
        if not pipeline.name:
            errors.append("Pipeline name is required")
        
        if not pipeline.version:
            errors.append("Pipeline version is required")
        
        if not pipeline.steps:
            errors.append("Pipeline must have at least one step")
        
        # Validate steps
        step_names = set()
        for i, step in enumerate(pipeline.steps):
            if not step.name:
                errors.append(f"Step {i+1}: name is required")
            elif step.name in step_names:
                errors.append(f"Step {i+1}: duplicate step name '{step.name}'")
            else:
                step_names.add(step.name)
            
            if not step.command:
                errors.append(f"Step {i+1}: command is required")
            
            # Check dependencies
            for dep in step.dependencies:
                if dep not in step_names:
                    errors.append(f"Step {i+1}: dependency '{dep}' not found")
        
        return errors
    
    @staticmethod
    def validate_execution_inputs(pipeline: PipelineDefinition, inputs: Dict[str, Any]) -> List[str]:
        """Validate inputs for pipeline execution"""
        errors = []
        
        # Check required inputs
        for input_name, input_spec in pipeline.inputs.items():
            if input_name not in inputs:
                errors.append(f"Required input '{input_name}' not provided")
            else:
                # Validate input type if specified
                if 'type' in input_spec:
                    expected_type = input_spec['type']
                    actual_value = inputs[input_name]
                    
                    if expected_type == 'file' and not Path(actual_value).exists():
                        errors.append(f"Input '{input_name}': file not found")
                    elif expected_type == 'directory' and not Path(actual_value).is_dir():
                        errors.append(f"Input '{input_name}': directory not found")
        
        return errors

# Integration with WorkflowDispatcher
class EnhancedWorkflowDispatcher(WorkflowDispatcher):
    """Enhanced workflow dispatcher with NGS pipeline integration"""
    
    def __init__(self):
        super().__init__()
        self.pipeline_manager = NGSPipelineManager(self)
        self.step_executor = PipelineStepExecutor(self.docker_manager)
        self.validator = PipelineValidator()
    
    async def load_pipeline(self, pipeline_path: Union[str, Path]) -> PipelineDefinition:
        """Load and validate a pipeline definition"""
        pipeline = await self.pipeline_manager.load_pipeline_definition(pipeline_path)
        
        # Validate pipeline
        errors = self.validator.validate_pipeline_definition(pipeline)
        if errors:
            raise ValueError(f"Pipeline validation failed: {'; '.join(errors)}")
        
        return pipeline
    
    async def execute_pipeline(self, pipeline_name: str, inputs: Dict[str, Any], 
                             parameters: Optional[Dict[str, Any]] = None) -> str:
        """Execute a pipeline with validation"""
        # Validate inputs
        if pipeline_name not in self.pipeline_manager.pipelines:
            raise ValueError(f"Pipeline not found: {pipeline_name}")
        
        pipeline = self.pipeline_manager.pipelines[pipeline_name]
        errors = self.validator.validate_execution_inputs(pipeline, inputs)
        if errors:
            raise ValueError(f"Input validation failed: {'; '.join(errors)}")
        
        return await self.pipeline_manager.execute_pipeline(pipeline_name, inputs, parameters)
    
    async def get_pipeline_status(self, execution_id: str) -> PipelineExecution:
        """Get pipeline execution status"""
        return await self.pipeline_manager.get_execution_status(execution_id)
    
    async def cancel_pipeline(self, execution_id: str) -> bool:
        """Cancel a running pipeline"""
        return await self.pipeline_manager.cancel_execution(execution_id)
    
    async def list_available_pipelines(self) -> List[PipelineDefinition]:
        """List all available pipelines"""
        return await self.pipeline_manager.list_pipelines()
    
    async def cleanup_pipeline_executions(self, days_old: int = 30) -> int:
        """Clean up old pipeline executions"""
        return await self.pipeline_manager.cleanup_old_executions(days_old)