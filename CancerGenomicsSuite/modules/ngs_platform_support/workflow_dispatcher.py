"""
Workflow Dispatcher for NGS Platform Support

This module provides workflow orchestration, job management, resource monitoring,
and scheduling capabilities for NGS sequencing pipelines across different platforms.
"""

import os
import subprocess
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
from pathlib import Path
import json
import time
import threading
import queue
from datetime import datetime, timedelta
import psutil
import warnings
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from enum import Enum
import docker
import redis
from celery import Celery
from celery.result import AsyncResult
import uuid

# Import platform-specific pipelines
from .illumina_pipeline import IlluminaPipeline
from .ion_torrent_pipeline import IonTorrentPipeline
from .pacbio_pipeline import PacBioPipeline
from .nanopore_pipeline import NanoporePipeline
from .common_preprocessing import PreprocessingPipeline

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    QUEUED = "queued"


class PlatformType(Enum):
    """Platform type enumeration."""
    ILLUMINA = "illumina"
    ION_TORRENT = "ion_torrent"
    PACBIO = "pacbio"
    NANOPORE = "nanopore"


@dataclass
class Job:
    """Job data class."""
    job_id: str
    sample_id: str
    platform: PlatformType
    input_files: Dict[str, str]
    config: Dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    priority: int = 0
    resources: Dict[str, Any] = None
    results: Dict[str, Any] = None
    error: Optional[str] = None
    docker_container_id: Optional[str] = None
    celery_task_id: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.resources is None:
            self.resources = {}


@dataclass
class DockerConfig:
    """Docker configuration data class."""
    image_name: str
    image_tag: str = "latest"
    registry: str = "localhost:5000"
    network: str = "cancer-genomics-network"
    volume_prefix: str = "cancer-genomics-data"
    memory_limit: str = "4g"
    cpu_limit: str = "2"
    environment: Dict[str, str] = None
    volumes: Dict[str, str] = None
    ports: Dict[str, str] = None
    
    def __post_init__(self):
        if self.environment is None:
            self.environment = {}
        if self.volumes is None:
            self.volumes = {}
        if self.ports is None:
            self.ports = {}


@dataclass
class QueueConfig:
    """Job queue configuration data class."""
    queue_type: str = "redis"
    broker_url: str = "redis://localhost:6379/1"
    result_backend: str = "redis://localhost:6379/2"
    max_retries: int = 3
    retry_delay: int = 60
    timeout: int = 3600
    concurrency: int = 4
    enable_priority_queues: bool = True
    enable_dead_letter_queue: bool = True


class WorkflowDispatcher:
    """
    Main workflow dispatcher for orchestrating NGS pipelines.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize workflow dispatcher.
        
        Args:
            config: Dispatcher configuration
        """
        self.config = config or self._get_default_config()
        self.job_manager = JobManager(self.config)
        self.resource_monitor = ResourceMonitor(self.config)
        self.scheduler = WorkflowScheduler(self.config)
        self.platform_detector = PlatformDetector()
        self.validator = WorkflowValidator()
        
        # Job queue and execution
        self.job_queue = queue.PriorityQueue()
        self.running_jobs = {}
        self.completed_jobs = {}
        self.failed_jobs = {}
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=self.config.get("max_workers", 4))
        self.dispatcher_thread = None
        self.is_running = False
        
        # Platform pipelines
        self.pipelines = {
            PlatformType.ILLUMINA: IlluminaPipeline,
            PlatformType.ION_TORRENT: IonTorrentPipeline,
            PlatformType.PACBIO: PacBioPipeline,
            PlatformType.NANOPORE: NanoporePipeline
        }
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default dispatcher configuration."""
        return {
            "max_workers": 4,
            "max_memory_gb": 32,
            "max_cpu_percent": 80,
            "job_timeout_hours": 24,
            "retry_failed_jobs": True,
            "max_retries": 3,
            "output_dir": "./workflow_output",
            "log_dir": "./workflow_logs",
            "temp_dir": "./workflow_temp",
            "cleanup_temp_files": True,
            "resource_check_interval": 30,  # seconds
            "job_check_interval": 10  # seconds
        }
    
    def start_dispatcher(self):
        """Start the workflow dispatcher."""
        if self.is_running:
            logger.warning("Dispatcher is already running")
            return
        
        self.is_running = True
        self.dispatcher_thread = threading.Thread(target=self._dispatcher_loop, daemon=True)
        self.dispatcher_thread.start()
        logger.info("Workflow dispatcher started")
    
    def stop_dispatcher(self):
        """Stop the workflow dispatcher."""
        self.is_running = False
        if self.dispatcher_thread:
            self.dispatcher_thread.join(timeout=30)
        logger.info("Workflow dispatcher stopped")
    
    def submit_job(self, sample_id: str, input_files: Dict[str, str], 
                   platform: Optional[PlatformType] = None,
                   config: Optional[Dict[str, Any]] = None,
                   priority: int = 0) -> str:
        """
        Submit a job to the workflow dispatcher.
        
        Args:
            sample_id: Sample identifier
            input_files: Input file paths
            platform: Platform type (auto-detected if None)
            config: Job configuration
            priority: Job priority (higher = more priority)
            
        Returns:
            Job ID
        """
        try:
            # Auto-detect platform if not specified
            if platform is None:
                platform = self.platform_detector.detect_platform(input_files)
            
            # Validate job
            validation_result = self.validator.validate_job(sample_id, input_files, platform, config)
            if not validation_result["valid"]:
                raise ValueError(f"Job validation failed: {validation_result['errors']}")
            
            # Create job
            job_id = f"{sample_id}_{platform.value}_{int(time.time())}"
            job = Job(
                job_id=job_id,
                sample_id=sample_id,
                platform=platform,
                input_files=input_files,
                config=config or {},
                priority=priority
            )
            
            # Add to queue
            self.job_queue.put((priority, job))
            logger.info(f"Job {job_id} submitted for sample {sample_id}")
            
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to submit job: {str(e)}")
            raise
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status."""
        # Check running jobs
        if job_id in self.running_jobs:
            job = self.running_jobs[job_id]
            return {
                "job_id": job_id,
                "status": job.status.value,
                "progress": self._get_job_progress(job),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "resources": job.resources
            }
        
        # Check completed jobs
        if job_id in self.completed_jobs:
            job = self.completed_jobs[job_id]
            return {
                "job_id": job_id,
                "status": job.status.value,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "results": job.results
            }
        
        # Check failed jobs
        if job_id in self.failed_jobs:
            job = self.failed_jobs[job_id]
            return {
                "job_id": job_id,
                "status": job.status.value,
                "failed_at": job.completed_at.isoformat() if job.completed_at else None,
                "error": job.error
            }
        
        return {"job_id": job_id, "status": "not_found"}
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        if job_id in self.running_jobs:
            job = self.running_jobs[job_id]
            job.status = JobStatus.CANCELLED
            # Note: Actual cancellation would require more complex implementation
            logger.info(f"Job {job_id} cancelled")
            return True
        
        return False
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status."""
        return {
            "queue_size": self.job_queue.qsize(),
            "running_jobs": len(self.running_jobs),
            "completed_jobs": len(self.completed_jobs),
            "failed_jobs": len(self.failed_jobs),
            "resource_usage": self.resource_monitor.get_current_usage()
        }
    
    def _dispatcher_loop(self):
        """Main dispatcher loop."""
        while self.is_running:
            try:
                # Check resource availability
                if not self.resource_monitor.has_available_resources():
                    time.sleep(self.config["resource_check_interval"])
                    continue
                
                # Get next job from queue
                try:
                    priority, job = self.job_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                # Check if we can start the job
                if self._can_start_job(job):
                    self._start_job(job)
                else:
                    # Put job back in queue
                    self.job_queue.put((priority, job))
                    time.sleep(self.config["job_check_interval"])
                
            except Exception as e:
                logger.error(f"Error in dispatcher loop: {str(e)}")
                time.sleep(5)
    
    def _can_start_job(self, job: Job) -> bool:
        """Check if a job can be started."""
        # Check resource availability
        if not self.resource_monitor.has_available_resources():
            return False
        
        # Check if we have capacity for more jobs
        if len(self.running_jobs) >= self.config["max_workers"]:
            return False
        
        return True
    
    def _start_job(self, job: Job):
        """Start a job."""
        try:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now()
            self.running_jobs[job.job_id] = job
            
            # Submit to executor
            future = self.executor.submit(self._execute_job, job)
            future.add_done_callback(lambda f: self._job_completed(job.job_id, f))
            
            logger.info(f"Job {job.job_id} started")
            
        except Exception as e:
            logger.error(f"Failed to start job {job.job_id}: {str(e)}")
            job.status = JobStatus.FAILED
            job.error = str(e)
            self.failed_jobs[job.job_id] = job
    
    def _execute_job(self, job: Job) -> Dict[str, Any]:
        """Execute a job."""
        try:
            logger.info(f"Executing job {job.job_id} for platform {job.platform.value}")
            
            # Get platform pipeline
            pipeline_class = self.pipelines.get(job.platform)
            if not pipeline_class:
                raise ValueError(f"Unsupported platform: {job.platform}")
            
            # Create pipeline instance
            pipeline = pipeline_class(job.config)
            
            # Execute pipeline
            results = pipeline.run_full_pipeline(job.input_files, job.sample_id)
            
            return results
            
        except Exception as e:
            logger.error(f"Job {job.job_id} failed: {str(e)}")
            raise
    
    def _job_completed(self, job_id: str, future):
        """Handle job completion."""
        job = self.running_jobs.pop(job_id, None)
        if not job:
            return
        
        try:
            if future.exception():
                job.status = JobStatus.FAILED
                job.error = str(future.exception())
                job.completed_at = datetime.now()
                self.failed_jobs[job_id] = job
                logger.error(f"Job {job_id} failed: {job.error}")
            else:
                job.status = JobStatus.COMPLETED
                job.results = future.result()
                job.completed_at = datetime.now()
                self.completed_jobs[job_id] = job
                logger.info(f"Job {job_id} completed successfully")
                
        except Exception as e:
            logger.error(f"Error handling job completion for {job_id}: {str(e)}")
    
    def _get_job_progress(self, job: Job) -> Dict[str, Any]:
        """Get job progress information."""
        # This would need to be implemented based on the specific pipeline
        # For now, return basic information
        return {
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "elapsed_time": str(datetime.now() - job.started_at) if job.started_at else None,
            "current_step": "running"  # Would be updated by pipeline
        }


class JobManager:
    """
    Job management utilities.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.jobs_db = {}  # In-memory job database
    
    def create_job(self, job_data: Dict[str, Any]) -> str:
        """Create a new job."""
        job_id = job_data.get("job_id", f"job_{int(time.time())}")
        self.jobs_db[job_id] = job_data
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID."""
        return self.jobs_db.get(job_id)
    
    def update_job(self, job_id: str, updates: Dict[str, Any]) -> bool:
        """Update job data."""
        if job_id in self.jobs_db:
            self.jobs_db[job_id].update(updates)
            return True
        return False
    
    def delete_job(self, job_id: str) -> bool:
        """Delete job."""
        if job_id in self.jobs_db:
            del self.jobs_db[job_id]
            return True
        return False
    
    def list_jobs(self, status: Optional[JobStatus] = None) -> List[Dict[str, Any]]:
        """List jobs, optionally filtered by status."""
        jobs = list(self.jobs_db.values())
        if status:
            jobs = [job for job in jobs if job.get("status") == status.value]
        return jobs


class ResourceMonitor:
    """
    System resource monitoring utilities.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_memory_gb = config.get("max_memory_gb", 32)
        self.max_cpu_percent = config.get("max_cpu_percent", 80)
    
    def get_current_usage(self) -> Dict[str, Any]:
        """Get current system resource usage."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_gb = memory.used / (1024**3)
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_gb = disk.used / (1024**3)
            disk_percent = (disk.used / disk.total) * 100
            
            return {
                "cpu_percent": cpu_percent,
                "memory_gb": memory_gb,
                "memory_percent": memory_percent,
                "disk_gb": disk_gb,
                "disk_percent": disk_percent,
                "available_memory_gb": (memory.total - memory.used) / (1024**3),
                "available_disk_gb": (disk.total - disk.used) / (1024**3)
            }
            
        except Exception as e:
            logger.error(f"Error getting resource usage: {str(e)}")
            return {}
    
    def has_available_resources(self) -> bool:
        """Check if system has available resources for new jobs."""
        usage = self.get_current_usage()
        
        # Check memory
        if usage.get("memory_gb", 0) > self.max_memory_gb:
            return False
        
        # Check CPU
        if usage.get("cpu_percent", 0) > self.max_cpu_percent:
            return False
        
        return True
    
    def get_resource_recommendations(self) -> List[str]:
        """Get resource usage recommendations."""
        usage = self.get_current_usage()
        recommendations = []
        
        if usage.get("memory_percent", 0) > 90:
            recommendations.append("High memory usage detected. Consider reducing concurrent jobs.")
        
        if usage.get("cpu_percent", 0) > 90:
            recommendations.append("High CPU usage detected. Consider reducing concurrent jobs.")
        
        if usage.get("disk_percent", 0) > 90:
            recommendations.append("High disk usage detected. Consider cleaning up temporary files.")
        
        return recommendations


class WorkflowScheduler:
    """
    Workflow scheduling utilities.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.scheduled_jobs = {}
    
    def schedule_job(self, job_id: str, schedule_time: datetime, 
                    job_data: Dict[str, Any]) -> bool:
        """Schedule a job for future execution."""
        try:
            self.scheduled_jobs[job_id] = {
                "schedule_time": schedule_time,
                "job_data": job_data,
                "status": "scheduled"
            }
            return True
        except Exception as e:
            logger.error(f"Failed to schedule job {job_id}: {str(e)}")
            return False
    
    def get_due_jobs(self) -> List[Dict[str, Any]]:
        """Get jobs that are due for execution."""
        due_jobs = []
        current_time = datetime.now()
        
        for job_id, job_info in self.scheduled_jobs.items():
            if job_info["schedule_time"] <= current_time and job_info["status"] == "scheduled":
                due_jobs.append({
                    "job_id": job_id,
                    "job_data": job_info["job_data"]
                })
                job_info["status"] = "due"
        
        return due_jobs
    
    def cancel_scheduled_job(self, job_id: str) -> bool:
        """Cancel a scheduled job."""
        if job_id in self.scheduled_jobs:
            del self.scheduled_jobs[job_id]
            return True
        return False


class PlatformDetector:
    """
    Platform detection utilities.
    """
    
    def __init__(self):
        self.platform_indicators = {
            PlatformType.ILLUMINA: [
                "R1", "R2", "_1", "_2", "fastq.gz", "fq.gz",
                "illumina", "hiseq", "miseq", "novaseq", "nextseq"
            ],
            PlatformType.ION_TORRENT: [
                "ion", "torrent", "pgm", "proton", "s5", "genexus"
            ],
            PlatformType.PACBIO: [
                "pacbio", "ccs", "subreads", "hifi", "sequel", "rs"
            ],
            PlatformType.NANOPORE: [
                "nanopore", "minion", "gridion", "promethion", "flongle",
                "fast5", "ont"
            ]
        }
    
    def detect_platform(self, input_files: Dict[str, str]) -> PlatformType:
        """
        Detect platform from input files.
        
        Args:
            input_files: Dictionary of input file paths
            
        Returns:
            Detected platform type
        """
        file_paths = list(input_files.values())
        platform_scores = {platform: 0 for platform in PlatformType}
        
        for file_path in file_paths:
            file_path_lower = file_path.lower()
            
            for platform, indicators in self.platform_indicators.items():
                for indicator in indicators:
                    if indicator.lower() in file_path_lower:
                        platform_scores[platform] += 1
        
        # Return platform with highest score, default to Illumina
        if any(score > 0 for score in platform_scores.values()):
            return max(platform_scores, key=platform_scores.get)
        else:
            return PlatformType.ILLUMINA  # Default platform
    
    def get_platform_info(self, platform: PlatformType) -> Dict[str, Any]:
        """Get information about a platform."""
        platform_info = {
            PlatformType.ILLUMINA: {
                "name": "Illumina",
                "description": "Short-read sequencing platform",
                "typical_read_length": "50-300 bp",
                "error_rate": "0.1%",
                "throughput": "High"
            },
            PlatformType.ION_TORRENT: {
                "name": "Ion Torrent",
                "description": "Semiconductor-based sequencing",
                "typical_read_length": "100-600 bp",
                "error_rate": "1-2%",
                "throughput": "Medium"
            },
            PlatformType.PACBIO: {
                "name": "PacBio",
                "description": "Long-read sequencing platform",
                "typical_read_length": "1-50 kb",
                "error_rate": "0.1-0.5%",
                "throughput": "Medium"
            },
            PlatformType.NANOPORE: {
                "name": "Oxford Nanopore",
                "description": "Real-time long-read sequencing",
                "typical_read_length": "1-100 kb",
                "error_rate": "5-15%",
                "throughput": "Variable"
            }
        }
        
        return platform_info.get(platform, {})


class WorkflowValidator:
    """
    Workflow validation utilities.
    """
    
    def __init__(self):
        self.required_file_extensions = [".fastq", ".fq", ".fastq.gz", ".fq.gz", ".fast5", ".bam"]
    
    def validate_job(self, sample_id: str, input_files: Dict[str, str], 
                    platform: PlatformType, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate a job before submission.
        
        Args:
            sample_id: Sample identifier
            input_files: Input file paths
            platform: Platform type
            config: Job configuration
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        
        # Validate sample ID
        if not sample_id or not isinstance(sample_id, str):
            errors.append("Invalid sample ID")
        
        # Validate input files
        if not input_files:
            errors.append("No input files provided")
        else:
            for file_type, file_path in input_files.items():
                if not file_path:
                    errors.append(f"Empty file path for {file_type}")
                elif not os.path.exists(file_path):
                    errors.append(f"File does not exist: {file_path}")
                elif not self._is_valid_file_extension(file_path):
                    warnings.append(f"Unusual file extension: {file_path}")
        
        # Validate platform-specific requirements
        platform_errors = self._validate_platform_requirements(platform, input_files)
        errors.extend(platform_errors)
        
        # Validate configuration
        if config:
            config_errors = self._validate_configuration(config)
            errors.extend(config_errors)
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _is_valid_file_extension(self, file_path: str) -> bool:
        """Check if file has a valid extension."""
        return any(file_path.lower().endswith(ext) for ext in self.required_file_extensions)
    
    def _validate_platform_requirements(self, platform: PlatformType, 
                                      input_files: Dict[str, str]) -> List[str]:
        """Validate platform-specific requirements."""
        errors = []
        
        if platform == PlatformType.ILLUMINA:
            # Illumina typically has R1/R2 files
            if not any("r1" in key.lower() or "r2" in key.lower() for key in input_files.keys()):
                errors.append("Illumina platform typically requires R1/R2 file pairs")
        
        elif platform == PlatformType.PACBIO:
            # PacBio can have subreads or CCS files
            if not any("subreads" in key.lower() or "ccs" in key.lower() for key in input_files.keys()):
                errors.append("PacBio platform typically requires subreads or CCS files")
        
        elif platform == PlatformType.NANOPORE:
            # Nanopore can have FAST5 or FASTQ files
            if not any("fast5" in key.lower() or "fastq" in key.lower() for key in input_files.keys()):
                errors.append("Nanopore platform typically requires FAST5 or FASTQ files")
        
        return errors
    
    def _validate_configuration(self, config: Dict[str, Any]) -> List[str]:
        """Validate job configuration."""
        errors = []
        
        # Check for required configuration parameters
        required_params = ["output_dir"]
        for param in required_params:
            if param not in config:
                errors.append(f"Missing required configuration parameter: {param}")
        
        # Validate parameter values
        if "threads" in config:
            if not isinstance(config["threads"], int) or config["threads"] < 1:
                errors.append("Threads must be a positive integer")
        
        if "memory" in config:
            if not isinstance(config["memory"], str) or not config["memory"].endswith("G"):
                errors.append("Memory must be specified as a string ending with 'G' (e.g., '8G')")
        
        return errors
    
    def validate_workflow_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate workflow configuration."""
        errors = []
        warnings = []
        
        # Check required parameters
        required_params = ["max_workers", "output_dir"]
        for param in required_params:
            if param not in config:
                errors.append(f"Missing required workflow parameter: {param}")
        
        # Validate parameter values
        if "max_workers" in config:
            if not isinstance(config["max_workers"], int) or config["max_workers"] < 1:
                errors.append("max_workers must be a positive integer")
        
        if "max_memory_gb" in config:
            if not isinstance(config["max_memory_gb"], (int, float)) or config["max_memory_gb"] <= 0:
                errors.append("max_memory_gb must be a positive number")
        
        if "max_cpu_percent" in config:
            if not isinstance(config["max_cpu_percent"], (int, float)) or not (0 < config["max_cpu_percent"] <= 100):
                errors.append("max_cpu_percent must be between 0 and 100")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }


class DockerManager:
    """
    Docker container management for NGS pipelines.
    """
    
    def __init__(self, config: DockerConfig):
        self.config = config
        try:
            self.client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.client = None
    
    def pull_image(self, image_name: str, tag: str = "latest") -> bool:
        """Pull Docker image."""
        try:
            if not self.client:
                return False
            
            full_image_name = f"{self.config.registry}/{image_name}:{tag}"
            logger.info(f"Pulling Docker image: {full_image_name}")
            self.client.images.pull(full_image_name)
            return True
        except Exception as e:
            logger.error(f"Failed to pull image {image_name}:{tag}: {e}")
            return False
    
    def create_container(self, job: Job, pipeline_config: Dict[str, Any]) -> Optional[str]:
        """Create Docker container for job execution."""
        try:
            if not self.client:
                return None
            
            # Prepare container configuration
            image_name = f"{self.config.registry}/{self.config.image_name}:{self.config.image_tag}"
            
            # Set up volumes
            volumes = {}
            for host_path, container_path in self.config.volumes.items():
                volumes[host_path] = {"bind": container_path, "mode": "rw"}
            
            # Add job-specific volumes
            for file_type, file_path in job.input_files.items():
                host_dir = os.path.dirname(file_path)
                container_dir = f"/data/input/{file_type}"
                volumes[host_dir] = {"bind": container_dir, "mode": "ro"}
            
            # Set up environment variables
            environment = self.config.environment.copy()
            environment.update({
                "JOB_ID": job.job_id,
                "SAMPLE_ID": job.sample_id,
                "PLATFORM": job.platform.value,
                "CONFIG": json.dumps(pipeline_config)
            })
            
            # Create container
            container = self.client.containers.create(
                image=image_name,
                command=["python", "/app/run_pipeline.py"],
                environment=environment,
                volumes=volumes,
                network=self.config.network,
                mem_limit=self.config.memory_limit,
                cpu_quota=int(self.config.cpu_limit) * 100000,
                detach=True,
                name=f"ngs-job-{job.job_id}"
            )
            
            logger.info(f"Created Docker container {container.id} for job {job.job_id}")
            return container.id
            
        except Exception as e:
            logger.error(f"Failed to create container for job {job.job_id}: {e}")
            return None
    
    def start_container(self, container_id: str) -> bool:
        """Start Docker container."""
        try:
            if not self.client:
                return False
            
            container = self.client.containers.get(container_id)
            container.start()
            logger.info(f"Started Docker container {container_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start container {container_id}: {e}")
            return False
    
    def stop_container(self, container_id: str) -> bool:
        """Stop Docker container."""
        try:
            if not self.client:
                return False
            
            container = self.client.containers.get(container_id)
            container.stop(timeout=30)
            logger.info(f"Stopped Docker container {container_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop container {container_id}: {e}")
            return False
    
    def remove_container(self, container_id: str) -> bool:
        """Remove Docker container."""
        try:
            if not self.client:
                return False
            
            container = self.client.containers.get(container_id)
            container.remove(force=True)
            logger.info(f"Removed Docker container {container_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove container {container_id}: {e}")
            return False
    
    def get_container_logs(self, container_id: str) -> str:
        """Get container logs."""
        try:
            if not self.client:
                return ""
            
            container = self.client.containers.get(container_id)
            return container.logs().decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to get logs for container {container_id}: {e}")
            return ""
    
    def get_container_status(self, container_id: str) -> str:
        """Get container status."""
        try:
            if not self.client:
                return "unknown"
            
            container = self.client.containers.get(container_id)
            return container.status
            
        except Exception as e:
            logger.error(f"Failed to get status for container {container_id}: {e}")
            return "unknown"


class CeleryJobManager:
    """
    Celery-based job queue management for NGS pipelines.
    """
    
    def __init__(self, config: QueueConfig):
        self.config = config
        self.celery_app = self._create_celery_app()
        self.redis_client = self._create_redis_client()
    
    def _create_celery_app(self) -> Celery:
        """Create Celery application."""
        celery_app = Celery('ngs_pipeline')
        celery_app.conf.update(
            broker_url=self.config.broker_url,
            result_backend=self.config.result_backend,
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='UTC',
            enable_utc=True,
            task_track_started=True,
            task_time_limit=self.config.timeout,
            task_soft_time_limit=self.config.timeout - 300,
            worker_prefetch_multiplier=1,
            task_acks_late=True,
            worker_max_tasks_per_child=1000
        )
        
        # Register tasks
        self._register_tasks(celery_app)
        
        return celery_app
    
    def _create_redis_client(self) -> Optional[redis.Redis]:
        """Create Redis client."""
        try:
            return redis.from_url(self.config.broker_url)
        except Exception as e:
            logger.error(f"Failed to create Redis client: {e}")
            return None
    
    def _register_tasks(self, celery_app: Celery):
        """Register Celery tasks."""
        
        @celery_app.task(bind=True, name='ngs_pipeline.run_pipeline')
        def run_pipeline_task(self, job_data: Dict[str, Any]):
            """Celery task for running NGS pipeline."""
            try:
                job_id = job_data['job_id']
                sample_id = job_data['sample_id']
                platform = job_data['platform']
                input_files = job_data['input_files']
                config = job_data['config']
                
                logger.info(f"Starting Celery task for job {job_id}")
                
                # Import platform-specific pipeline
                if platform == 'illumina':
                    from .illumina_pipeline import IlluminaPipeline
                    pipeline = IlluminaPipeline(config)
                elif platform == 'ion_torrent':
                    from .ion_torrent_pipeline import IonTorrentPipeline
                    pipeline = IonTorrentPipeline(config)
                elif platform == 'pacbio':
                    from .pacbio_pipeline import PacBioPipeline
                    pipeline = PacBioPipeline(config)
                elif platform == 'nanopore':
                    from .nanopore_pipeline import NanoporePipeline
                    pipeline = NanoporePipeline(config)
                else:
                    raise ValueError(f"Unsupported platform: {platform}")
                
                # Run pipeline
                results = pipeline.run_full_pipeline(input_files, sample_id)
                
                logger.info(f"Completed Celery task for job {job_id}")
                return results
                
            except Exception as e:
                logger.error(f"Celery task failed for job {job_data.get('job_id', 'unknown')}: {e}")
                raise
    
    def submit_job(self, job: Job) -> Optional[str]:
        """Submit job to Celery queue."""
        try:
            job_data = {
                'job_id': job.job_id,
                'sample_id': job.sample_id,
                'platform': job.platform.value,
                'input_files': job.input_files,
                'config': job.config
            }
            
            # Submit to Celery
            task = self.celery_app.send_task(
                'ngs_pipeline.run_pipeline',
                args=[job_data],
                queue='ngs_pipeline_queue',
                priority=job.priority
            )
            
            logger.info(f"Submitted job {job.job_id} to Celery with task ID {task.id}")
            return task.id
            
        except Exception as e:
            logger.error(f"Failed to submit job {job.job_id} to Celery: {e}")
            return None
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get Celery task status."""
        try:
            result = AsyncResult(task_id, app=self.celery_app)
            
            return {
                'task_id': task_id,
                'status': result.status,
                'result': result.result if result.successful() else None,
                'error': str(result.result) if result.failed() else None,
                'progress': result.info.get('progress', 0) if result.info else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get status for task {task_id}: {e}")
            return {'task_id': task_id, 'status': 'UNKNOWN', 'error': str(e)}
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel Celery task."""
        try:
            self.celery_app.control.revoke(task_id, terminate=True)
            logger.info(f"Cancelled Celery task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False
    
    def get_queue_info(self) -> Dict[str, Any]:
        """Get queue information."""
        try:
            if not self.redis_client:
                return {}
            
            # Get queue length
            queue_length = self.redis_client.llen('celery')
            
            # Get active tasks
            inspect = self.celery_app.control.inspect()
            active_tasks = inspect.active()
            scheduled_tasks = inspect.scheduled()
            
            return {
                'queue_length': queue_length,
                'active_tasks': len(active_tasks.get('celery@worker', [])) if active_tasks else 0,
                'scheduled_tasks': len(scheduled_tasks.get('celery@worker', [])) if scheduled_tasks else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue info: {e}")
            return {}
