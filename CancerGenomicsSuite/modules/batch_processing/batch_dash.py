"""
Batch Processing Dashboard Module

Provides interactive dashboard functionality for batch processing management in the Cancer Genomics Analysis Suite.
Supports job queuing, monitoring, and real-time status updates.
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path
import json
import uuid
from datetime import datetime, timedelta
import threading
import time
import queue
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Batch job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class JobType(Enum):
    """Types of batch jobs."""
    DATA_PROCESSING = "data_processing"
    ANALYSIS = "analysis"
    EXPORT = "export"
    QUALITY_CONTROL = "quality_control"
    VISUALIZATION = "visualization"
    REPORT_GENERATION = "report_generation"
    CUSTOM = "custom"


@dataclass
class BatchJob:
    """Represents a batch processing job."""
    id: str
    name: str
    job_type: JobType
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    priority: int = 0  # Higher number = higher priority
    progress: float = 0.0  # 0.0 to 1.0
    parameters: Dict[str, Any] = field(default_factory=dict)
    input_files: List[str] = field(default_factory=list)
    output_files: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    worker_id: Optional[str] = None
    estimated_duration: Optional[timedelta] = None
    actual_duration: Optional[timedelta] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'job_type': self.job_type.value,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'priority': self.priority,
            'progress': self.progress,
            'parameters': self.parameters,
            'input_files': self.input_files,
            'output_files': self.output_files,
            'error_message': self.error_message,
            'worker_id': self.worker_id,
            'estimated_duration': str(self.estimated_duration) if self.estimated_duration else None,
            'actual_duration': str(self.actual_duration) if self.actual_duration else None,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchJob':
        """Create job from dictionary."""
        data['job_type'] = JobType(data['job_type'])
        data['status'] = JobStatus(data['status'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('started_at'):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        if data.get('estimated_duration'):
            data['estimated_duration'] = timedelta(seconds=int(data['estimated_duration'].split(':')[-1]))
        if data.get('actual_duration'):
            data['actual_duration'] = timedelta(seconds=int(data['actual_duration'].split(':')[-1]))
        return cls(**data)


class BatchQueue:
    """
    Manages batch job queue and execution.
    
    Features:
    - Priority-based job queuing
    - Worker pool management
    - Job status tracking
    - Progress monitoring
    - Error handling and retry logic
    """
    
    def __init__(self, max_workers: int = 4, db_path: str = None):
        """
        Initialize batch queue.
        
        Args:
            max_workers: Maximum number of worker threads
            db_path: Path to SQLite database for job persistence
        """
        self.max_workers = max_workers
        self.db_path = db_path or str(Path(__file__).parent / 'batch_jobs.db')
        self.jobs = {}
        self.job_queue = queue.PriorityQueue()
        self.workers = {}
        self.is_running = False
        self.executor = None
        
        # Initialize database
        self._init_database()
        
        # Load existing jobs
        self._load_jobs()
    
    def _init_database(self):
        """Initialize SQLite database for job persistence."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    priority INTEGER DEFAULT 0,
                    progress REAL DEFAULT 0.0,
                    parameters TEXT,
                    input_files TEXT,
                    output_files TEXT,
                    error_message TEXT,
                    worker_id TEXT,
                    estimated_duration TEXT,
                    actual_duration TEXT,
                    metadata TEXT
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_status_priority 
                ON jobs(status, priority DESC, created_at)
            ''')
    
    def _load_jobs(self):
        """Load existing jobs from database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('SELECT * FROM jobs')
            
            for row in cursor:
                job_data = dict(row)
                job_data['parameters'] = json.loads(job_data['parameters'] or '{}')
                job_data['input_files'] = json.loads(job_data['input_files'] or '[]')
                job_data['output_files'] = json.loads(job_data['output_files'] or '[]')
                job_data['metadata'] = json.loads(job_data['metadata'] or '{}')
                
                job = BatchJob.from_dict(job_data)
                self.jobs[job.id] = job
    
    def _save_job(self, job: BatchJob):
        """Save job to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO jobs (
                    id, name, job_type, status, created_at, started_at, completed_at,
                    priority, progress, parameters, input_files, output_files,
                    error_message, worker_id, estimated_duration, actual_duration, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job.id, job.name, job.job_type.value, job.status.value,
                job.created_at.isoformat(),
                job.started_at.isoformat() if job.started_at else None,
                job.completed_at.isoformat() if job.completed_at else None,
                job.priority, job.progress,
                json.dumps(job.parameters),
                json.dumps(job.input_files),
                json.dumps(job.output_files),
                job.error_message, job.worker_id,
                str(job.estimated_duration) if job.estimated_duration else None,
                str(job.actual_duration) if job.actual_duration else None,
                json.dumps(job.metadata)
            ))
    
    def add_job(self, job: BatchJob) -> str:
        """
        Add a job to the queue.
        
        Args:
            job: Job to add
            
        Returns:
            str: Job ID
        """
        self.jobs[job.id] = job
        self._save_job(job)
        
        # Add to priority queue (negative priority for max-heap behavior)
        self.job_queue.put((-job.priority, job.created_at, job))
        
        logger.info(f"Added job {job.name} to queue")
        return job.id
    
    def start_processing(self):
        """Start the batch processing workers."""
        if self.is_running:
            return
        
        self.is_running = True
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Start worker threads
        for i in range(self.max_workers):
            worker_id = f"worker-{i}"
            self.workers[worker_id] = {
                'id': worker_id,
                'status': 'idle',
                'current_job': None,
                'thread': None
            }
        
        logger.info(f"Started batch processing with {self.max_workers} workers")
    
    def stop_processing(self):
        """Stop the batch processing workers."""
        self.is_running = False
        
        if self.executor:
            self.executor.shutdown(wait=True)
        
        logger.info("Stopped batch processing")
    
    def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """Get status of a specific job."""
        job = self.jobs.get(job_id)
        return job.status if job else None
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        status_counts = {}
        for status in JobStatus:
            status_counts[status.value] = sum(1 for job in self.jobs.values() if job.status == status)
        
        active_workers = sum(1 for worker in self.workers.values() if worker['status'] == 'running')
        
        return {
            'total_jobs': len(self.jobs),
            'status_counts': status_counts,
            'queue_size': self.job_queue.qsize(),
            'active_workers': active_workers,
            'max_workers': self.max_workers,
            'is_running': self.is_running
        }
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            if job.status in [JobStatus.PENDING, JobStatus.RUNNING]:
                job.status = JobStatus.CANCELLED
                job.completed_at = datetime.now()
                self._save_job(job)
                logger.info(f"Cancelled job {job.name}")
                return True
        return False
    
    def retry_job(self, job_id: str) -> bool:
        """Retry a failed job."""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            if job.status == JobStatus.FAILED:
                job.status = JobStatus.PENDING
                job.progress = 0.0
                job.error_message = None
                job.started_at = None
                job.completed_at = None
                self._save_job(job)
                
                # Re-add to queue
                self.job_queue.put((-job.priority, job.created_at, job))
                logger.info(f"Retrying job {job.name}")
                return True
        return False


class BatchDashboard:
    """
    Interactive dashboard for batch processing management.
    
    Features:
    - Real-time job monitoring
    - Queue management
    - Progress tracking
    - Job creation and configuration
    - Performance metrics
    - Error handling and retry
    """
    
    def __init__(self, app_name: str = "BatchProcessingDashboard", batch_queue: BatchQueue = None):
        """
        Initialize BatchDashboard.
        
        Args:
            app_name: Name of the Dash application
            batch_queue: BatchQueue instance to manage
        """
        self.app_name = app_name
        self.app = dash.Dash(__name__)
        self.batch_queue = batch_queue or BatchQueue()
        self.callbacks_registered = set()
        
        # Configure app
        self.app.config.suppress_callback_exceptions = True
        
        # Set up default layout
        self._setup_default_layout()
    
    def _setup_default_layout(self):
        """Set up default dashboard layout."""
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1("Batch Processing Dashboard", className="dashboard-title"),
                html.Div([
                    html.Button("Start Processing", id="start-processing-btn", className="btn btn-success"),
                    html.Button("Stop Processing", id="stop-processing-btn", className="btn btn-danger"),
                    html.Button("Add Job", id="add-job-btn", className="btn btn-primary"),
                    dcc.Interval(id="refresh-interval", interval=2000, n_intervals=0)
                ], className="header-buttons")
            ], className="dashboard-header"),
            
            # Status overview
            html.Div(id="status-overview", className="status-overview"),
            
            # Main content tabs
            dcc.Tabs([
                dcc.Tab(label="Queue Status", children=[
                    html.Div(id="queue-status-content", className="tab-content")
                ]),
                dcc.Tab(label="Job Management", children=[
                    html.Div(id="job-management-content", className="tab-content")
                ]),
                dcc.Tab(label="Performance Metrics", children=[
                    html.Div(id="performance-content", className="tab-content")
                ]),
                dcc.Tab(label="Job Creation", children=[
                    html.Div(id="job-creation-content", className="tab-content")
                ])
            ], className="dashboard-tabs"),
            
            # Hidden divs for callbacks
            html.Div(id="hidden-div", style={"display": "none"}),
            dcc.Store(id="job-store", data={}),
            dcc.Store(id="queue-store", data={})
        ], className="dashboard-container")
        
        # Register default callbacks
        self._register_default_callbacks()
    
    def _register_default_callbacks(self):
        """Register default dashboard callbacks."""
        @self.app.callback(
            [Output("status-overview", "children"),
             Output("queue-status-content", "children"),
             Output("job-management-content", "children"),
             Output("performance-content", "children"),
             Output("job-creation-content", "children")],
            [Input("refresh-interval", "n_intervals"),
             Input("start-processing-btn", "n_clicks"),
             Input("stop-processing-btn", "n_clicks")],
            prevent_initial_call=False
        )
        def update_dashboard(n_intervals, start_clicks, stop_clicks):
            """Update dashboard components."""
            ctx = callback_context
            if ctx.triggered:
                trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
                if trigger_id == "start-processing-btn":
                    self.batch_queue.start_processing()
                elif trigger_id == "stop-processing-btn":
                    self.batch_queue.stop_processing()
            
            # Get current status
            queue_status = self.batch_queue.get_queue_status()
            
            # Status overview
            status_overview = self._create_status_overview(queue_status)
            
            # Queue status content
            queue_content = self._create_queue_status_content()
            
            # Job management content
            job_content = self._create_job_management_content()
            
            # Performance content
            performance_content = self._create_performance_content()
            
            # Job creation content
            creation_content = self._create_job_creation_content()
            
            return status_overview, queue_content, job_content, performance_content, creation_content
    
    def _create_status_overview(self, queue_status: Dict[str, Any]) -> html.Div:
        """Create status overview section."""
        status_cards = []
        
        for status, count in queue_status['status_counts'].items():
            color = {
                'pending': 'warning',
                'running': 'info',
                'completed': 'success',
                'failed': 'danger',
                'cancelled': 'secondary',
                'paused': 'secondary'
            }.get(status, 'secondary')
            
            status_cards.append(
                html.Div([
                    html.H3(str(count), className=f"status-count text-{color}"),
                    html.P(status.title(), className="status-label")
                ], className="status-card")
            )
        
        return html.Div([
            html.H2("Queue Status Overview", className="section-title"),
            html.Div(status_cards, className="status-cards-grid"),
            html.Div([
                html.P(f"Total Jobs: {queue_status['total_jobs']}", className="status-info"),
                html.P(f"Queue Size: {queue_status['queue_size']}", className="status-info"),
                html.P(f"Active Workers: {queue_status['active_workers']}/{queue_status['max_workers']}", className="status-info"),
                html.P(f"Processing: {'Running' if queue_status['is_running'] else 'Stopped'}", className="status-info")
            ], className="status-details")
        ], className="status-overview")
    
    def _create_queue_status_content(self) -> html.Div:
        """Create queue status content."""
        jobs = list(self.batch_queue.jobs.values())
        jobs_df = pd.DataFrame([job.to_dict() for job in jobs])
        
        if jobs_df.empty:
            return html.Div("No jobs in queue", className="no-data")
        
        # Create jobs table
        table_data = []
        for _, job in jobs_df.iterrows():
            table_data.append([
                job['name'],
                job['job_type'],
                job['status'],
                f"{job['progress']:.1%}",
                job['created_at'][:19] if job['created_at'] else 'N/A',
                job['priority']
            ])
        
        return html.Div([
            html.H3("Current Jobs", className="section-title"),
            html.Table([
                html.Thead([
                    html.Tr([
                        html.Th("Job Name"),
                        html.Th("Type"),
                        html.Th("Status"),
                        html.Th("Progress"),
                        html.Th("Created"),
                        html.Th("Priority")
                    ])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td(cell) for cell in row
                    ]) for row in table_data
                ])
            ], className="jobs-table")
        ])
    
    def _create_job_management_content(self) -> html.Div:
        """Create job management content."""
        jobs = list(self.batch_queue.jobs.values())
        
        job_cards = []
        for job in jobs:
            status_color = {
                'pending': 'warning',
                'running': 'info',
                'completed': 'success',
                'failed': 'danger',
                'cancelled': 'secondary',
                'paused': 'secondary'
            }.get(job.status.value, 'secondary')
            
            actions = []
            if job.status == JobStatus.PENDING:
                actions.append(html.Button("Cancel", className="btn btn-sm btn-danger", 
                                         id=f"cancel-{job.id}"))
            elif job.status == JobStatus.FAILED:
                actions.append(html.Button("Retry", className="btn btn-sm btn-warning",
                                         id=f"retry-{job.id}"))
            
            job_cards.append(
                html.Div([
                    html.H4(job.name, className="job-title"),
                    html.P(f"Type: {job.job_type.value}", className="job-info"),
                    html.P(f"Status: {job.status.value}", className=f"job-status text-{status_color}"),
                    html.P(f"Progress: {job.progress:.1%}", className="job-progress"),
                    html.Div([
                        dcc.Progress(value=job.progress * 100, className="progress-bar")
                    ], className="progress-container"),
                    html.Div(actions, className="job-actions")
                ], className="job-card")
            )
        
        return html.Div([
            html.H3("Job Management", className="section-title"),
            html.Div(job_cards, className="job-cards-grid")
        ])
    
    def _create_performance_content(self) -> html.Div:
        """Create performance metrics content."""
        jobs = list(self.batch_queue.jobs.values())
        
        if not jobs:
            return html.Div("No performance data available", className="no-data")
        
        # Calculate metrics
        completed_jobs = [job for job in jobs if job.status == JobStatus.COMPLETED]
        failed_jobs = [job for job in jobs if job.status == JobStatus.FAILED]
        
        success_rate = len(completed_jobs) / len(jobs) * 100 if jobs else 0
        
        # Average processing time
        avg_time = 0
        if completed_jobs:
            durations = [job.actual_duration.total_seconds() for job in completed_jobs if job.actual_duration]
            avg_time = sum(durations) / len(durations) if durations else 0
        
        # Create performance chart
        status_counts = {}
        for status in JobStatus:
            status_counts[status.value] = sum(1 for job in jobs if job.status == status)
        
        fig = px.pie(
            values=list(status_counts.values()),
            names=list(status_counts.keys()),
            title="Job Status Distribution"
        )
        
        return html.Div([
            html.H3("Performance Metrics", className="section-title"),
            html.Div([
                html.Div([
                    html.H4(f"{success_rate:.1f}%", className="metric-value"),
                    html.P("Success Rate", className="metric-label")
                ], className="metric-card"),
                html.Div([
                    html.H4(f"{avg_time:.1f}s", className="metric-value"),
                    html.P("Avg Processing Time", className="metric-label")
                ], className="metric-card"),
                html.Div([
                    html.H4(str(len(jobs)), className="metric-value"),
                    html.P("Total Jobs", className="metric-label")
                ], className="metric-card")
            ], className="metrics-grid"),
            dcc.Graph(figure=fig, className="performance-chart")
        ])
    
    def _create_job_creation_content(self) -> html.Div:
        """Create job creation content."""
        return html.Div([
            html.H3("Create New Job", className="section-title"),
            html.Div([
                html.Div([
                    html.Label("Job Name", className="form-label"),
                    dcc.Input(id="job-name-input", type="text", placeholder="Enter job name", className="form-control")
                ], className="form-group"),
                html.Div([
                    html.Label("Job Type", className="form-label"),
                    dcc.Dropdown(
                        id="job-type-dropdown",
                        options=[{'label': job_type.value.replace('_', ' ').title(), 'value': job_type.value} 
                                for job_type in JobType],
                        placeholder="Select job type",
                        className="form-control"
                    )
                ], className="form-group"),
                html.Div([
                    html.Label("Priority", className="form-label"),
                    dcc.Slider(
                        id="job-priority-slider",
                        min=0,
                        max=10,
                        step=1,
                        value=5,
                        marks={i: str(i) for i in range(0, 11)},
                        className="form-control"
                    )
                ], className="form-group"),
                html.Div([
                    html.Label("Input Files", className="form-label"),
                    dcc.Upload(
                        id="input-files-upload",
                        children=html.Div(['Drag and Drop or ', html.A('Select Files')]),
                        multiple=True,
                        className="upload-area"
                    )
                ], className="form-group"),
                html.Div([
                    html.Label("Parameters (JSON)", className="form-label"),
                    dcc.Textarea(
                        id="job-parameters-textarea",
                        placeholder='{"param1": "value1", "param2": "value2"}',
                        className="form-control",
                        rows=4
                    )
                ], className="form-group"),
                html.Button("Create Job", id="create-job-btn", className="btn btn-primary")
            ], className="job-creation-form")
        ])
    
    def create_job(self, name: str, job_type: JobType, priority: int = 5,
                   input_files: List[str] = None, parameters: Dict[str, Any] = None) -> str:
        """
        Create a new batch job.
        
        Args:
            name: Job name
            job_type: Type of job
            priority: Job priority (0-10)
            input_files: List of input file paths
            parameters: Job parameters
            
        Returns:
            str: Job ID
        """
        job = BatchJob(
            id=str(uuid.uuid4()),
            name=name,
            job_type=job_type,
            status=JobStatus.PENDING,
            created_at=datetime.now(),
            priority=priority,
            input_files=input_files or [],
            parameters=parameters or {}
        )
        
        return self.batch_queue.add_job(job)
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics."""
        queue_status = self.batch_queue.get_queue_status()
        return {
            'queue_status': queue_status,
            'total_jobs': len(self.batch_queue.jobs),
            'active_workers': queue_status['active_workers'],
            'is_processing': queue_status['is_running']
        }
    
    def run_dashboard(self, host: str = "127.0.0.1", port: int = 8052, debug: bool = False):
        """
        Run the dashboard application.
        
        Args:
            host: Host to run on
            port: Port to run on
            debug: Enable debug mode
        """
        logger.info(f"Starting batch processing dashboard on {host}:{port}")
        self.app.run_server(host=host, port=port, debug=debug)
