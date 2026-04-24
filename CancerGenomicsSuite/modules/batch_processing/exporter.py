"""
Data Exporter Module

Provides comprehensive data export capabilities for the Cancer Genomics Analysis Suite.
Supports multiple export formats, batch processing, and automated export workflows.
"""

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
import zipfile
import tarfile
import gzip
import shutil
import sqlite3
import h5py
import pickle
import csv
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import queue
import time

logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    """Supported export formats."""
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"
    PARQUET = "parquet"
    HDF5 = "hdf5"
    PICKLE = "pickle"
    XML = "xml"
    TSV = "tsv"
    ZIP = "zip"
    TAR = "tar"
    GZIP = "gzip"


class ExportStatus(Enum):
    """Export job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExportConfig:
    """Configuration for data export."""
    format: ExportFormat
    output_path: str
    include_metadata: bool = True
    compress: bool = False
    chunk_size: int = 10000
    encoding: str = "utf-8"
    delimiter: str = ","
    sheet_name: str = "Sheet1"
    index: bool = False
    header: bool = True
    custom_options: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            'format': self.format.value,
            'output_path': self.output_path,
            'include_metadata': self.include_metadata,
            'compress': self.compress,
            'chunk_size': self.chunk_size,
            'encoding': self.encoding,
            'delimiter': self.delimiter,
            'sheet_name': self.sheet_name,
            'index': self.index,
            'header': self.header,
            'custom_options': self.custom_options
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExportConfig':
        """Create config from dictionary."""
        data['format'] = ExportFormat(data['format'])
        return cls(**data)


@dataclass
class ExportJob:
    """Represents an export job."""
    id: str
    name: str
    data_source: str
    config: ExportConfig
    status: ExportStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    file_size: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'data_source': self.data_source,
            'config': self.config.to_dict(),
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'progress': self.progress,
            'file_size': self.file_size,
            'error_message': self.error_message,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExportJob':
        """Create job from dictionary."""
        data['config'] = ExportConfig.from_dict(data['config'])
        data['status'] = ExportStatus(data['status'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('started_at'):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        return cls(**data)


class DataExporter:
    """
    Handles data export in various formats with batch processing capabilities.
    
    Features:
    - Multiple export formats (CSV, Excel, JSON, Parquet, HDF5, etc.)
    - Batch processing and queuing
    - Progress tracking
    - Compression support
    - Metadata inclusion
    - Error handling and retry
    - Custom export options
    """
    
    def __init__(self, output_dir: str = None, max_workers: int = 4):
        """
        Initialize DataExporter.
        
        Args:
            output_dir: Default output directory
            max_workers: Maximum number of worker threads
        """
        self.output_dir = Path(output_dir) if output_dir else Path("outputs/exports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_workers = max_workers
        self.export_jobs = {}
        self.job_queue = queue.Queue()
        self.workers = {}
        self.is_running = False
        self.executor = None
        
        # Export handlers
        self.export_handlers = {
            ExportFormat.CSV: self._export_csv,
            ExportFormat.EXCEL: self._export_excel,
            ExportFormat.JSON: self._export_json,
            ExportFormat.PARQUET: self._export_parquet,
            ExportFormat.HDF5: self._export_hdf5,
            ExportFormat.PICKLE: self._export_pickle,
            ExportFormat.XML: self._export_xml,
            ExportFormat.TSV: self._export_tsv
        }
    
    def create_export_job(self, name: str, data_source: str, config: ExportConfig) -> str:
        """
        Create a new export job.
        
        Args:
            name: Job name
            data_source: Data source identifier
            config: Export configuration
            
        Returns:
            str: Job ID
        """
        job = ExportJob(
            id=str(uuid.uuid4()),
            name=name,
            data_source=data_source,
            config=config,
            status=ExportStatus.PENDING,
            created_at=datetime.now()
        )
        
        self.export_jobs[job.id] = job
        self.job_queue.put(job)
        
        logger.info(f"Created export job: {name}")
        return job.id
    
    def start_export_workers(self):
        """Start export worker threads."""
        if self.is_running:
            return
        
        self.is_running = True
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Start worker threads
        for i in range(self.max_workers):
            worker_id = f"export-worker-{i}"
            self.workers[worker_id] = {
                'id': worker_id,
                'status': 'idle',
                'current_job': None
            }
            
            # Submit worker task
            self.executor.submit(self._export_worker, worker_id)
        
        logger.info(f"Started {self.max_workers} export workers")
    
    def stop_export_workers(self):
        """Stop export worker threads."""
        self.is_running = False
        
        if self.executor:
            self.executor.shutdown(wait=True)
        
        logger.info("Stopped export workers")
    
    def _export_worker(self, worker_id: str):
        """Export worker thread."""
        while self.is_running:
            try:
                # Get job from queue
                job = self.job_queue.get(timeout=1)
                
                self.workers[worker_id]['status'] = 'running'
                self.workers[worker_id]['current_job'] = job.id
                
                # Process export job
                self._process_export_job(job)
                
                self.workers[worker_id]['status'] = 'idle'
                self.workers[worker_id]['current_job'] = None
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Export worker {worker_id} error: {str(e)}")
                self.workers[worker_id]['status'] = 'error'
    
    def _process_export_job(self, job: ExportJob):
        """Process an export job."""
        try:
            job.status = ExportStatus.RUNNING
            job.started_at = datetime.now()
            
            # Get data (this would be implemented based on your data source)
            data = self._get_data_from_source(job.data_source)
            
            if data is None:
                raise ValueError(f"Data source {job.data_source} not found")
            
            # Export data
            output_path = self._export_data(data, job.config)
            
            # Update job status
            job.status = ExportStatus.COMPLETED
            job.completed_at = datetime.now()
            job.progress = 1.0
            job.file_size = Path(output_path).stat().st_size if Path(output_path).exists() else 0
            
            logger.info(f"Completed export job: {job.name}")
            
        except Exception as e:
            job.status = ExportStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
            logger.error(f"Failed export job {job.name}: {str(e)}")
    
    def _get_data_from_source(self, data_source: str) -> Any:
        """Get data from source (placeholder implementation)."""
        # This would be implemented based on your data source system
        # For now, return a sample DataFrame
        return pd.DataFrame({
            'sample_id': [f'sample_{i}' for i in range(100)],
            'gene_expression': np.random.normal(10, 2, 100),
            'mutation_count': np.random.poisson(5, 100),
            'clinical_status': np.random.choice(['normal', 'tumor'], 100)
        })
    
    def _export_data(self, data: Any, config: ExportConfig) -> str:
        """Export data using the specified configuration."""
        # Ensure output directory exists
        output_path = Path(config.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get export handler
        handler = self.export_handlers.get(config.format)
        if not handler:
            raise ValueError(f"Unsupported export format: {config.format}")
        
        # Export data
        result_path = handler(data, config)
        
        # Apply compression if requested
        if config.compress:
            result_path = self._compress_file(result_path, config.format)
        
        return result_path
    
    def _export_csv(self, data: pd.DataFrame, config: ExportConfig) -> str:
        """Export data as CSV."""
        if isinstance(data, pd.DataFrame):
            data.to_csv(
                config.output_path,
                index=config.index,
                header=config.header,
                encoding=config.encoding,
                sep=config.delimiter,
                chunksize=config.chunk_size if config.chunk_size > 0 else None
            )
        else:
            # Handle other data types
            with open(config.output_path, 'w', encoding=config.encoding, newline='') as f:
                writer = csv.writer(f, delimiter=config.delimiter)
                if config.header and hasattr(data, 'columns'):
                    writer.writerow(data.columns)
                for row in data:
                    writer.writerow(row)
        
        return config.output_path
    
    def _export_excel(self, data: pd.DataFrame, config: ExportConfig) -> str:
        """Export data as Excel."""
        if isinstance(data, pd.DataFrame):
            with pd.ExcelWriter(config.output_path, engine='openpyxl') as writer:
                data.to_excel(
                    writer,
                    sheet_name=config.sheet_name,
                    index=config.index,
                    header=config.header
                )
                
                # Add metadata sheet if requested
                if config.include_metadata:
                    metadata_df = pd.DataFrame({
                        'Property': ['Export Date', 'Data Shape', 'Columns'],
                        'Value': [
                            datetime.now().isoformat(),
                            str(data.shape),
                            ', '.join(data.columns.tolist())
                        ]
                    })
                    metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
        else:
            raise ValueError("Excel export only supports DataFrame data")
        
        return config.output_path
    
    def _export_json(self, data: Any, config: ExportConfig) -> str:
        """Export data as JSON."""
        if isinstance(data, pd.DataFrame):
            # Convert DataFrame to records
            export_data = {
                'data': data.to_dict('records'),
                'columns': data.columns.tolist(),
                'shape': data.shape
            }
            
            if config.include_metadata:
                export_data['metadata'] = {
                    'export_date': datetime.now().isoformat(),
                    'data_types': data.dtypes.to_dict(),
                    'missing_values': data.isnull().sum().to_dict()
                }
        else:
            export_data = data
        
        with open(config.output_path, 'w', encoding=config.encoding) as f:
            json.dump(export_data, f, indent=2, default=str)
        
        return config.output_path
    
    def _export_parquet(self, data: pd.DataFrame, config: ExportConfig) -> str:
        """Export data as Parquet."""
        if isinstance(data, pd.DataFrame):
            data.to_parquet(
                config.output_path,
                index=config.index,
                compression='snappy'
            )
        else:
            raise ValueError("Parquet export only supports DataFrame data")
        
        return config.output_path
    
    def _export_hdf5(self, data: pd.DataFrame, config: ExportConfig) -> str:
        """Export data as HDF5."""
        if isinstance(data, pd.DataFrame):
            with h5py.File(config.output_path, 'w') as f:
                # Store data
                f.create_dataset('data', data=data.values)
                f.create_dataset('columns', data=[col.encode() for col in data.columns])
                f.create_dataset('index', data=[str(idx).encode() for idx in data.index])
                
                # Store metadata if requested
                if config.include_metadata:
                    metadata_group = f.create_group('metadata')
                    metadata_group.attrs['export_date'] = datetime.now().isoformat()
                    metadata_group.attrs['shape'] = data.shape
                    metadata_group.attrs['dtypes'] = json.dumps(data.dtypes.to_dict())
        else:
            raise ValueError("HDF5 export only supports DataFrame data")
        
        return config.output_path
    
    def _export_pickle(self, data: Any, config: ExportConfig) -> str:
        """Export data as Pickle."""
        with open(config.output_path, 'wb') as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        return config.output_path
    
    def _export_xml(self, data: pd.DataFrame, config: ExportConfig) -> str:
        """Export data as XML."""
        if isinstance(data, pd.DataFrame):
            root = ET.Element("data")
            
            # Add metadata if requested
            if config.include_metadata:
                metadata = ET.SubElement(root, "metadata")
                ET.SubElement(metadata, "export_date").text = datetime.now().isoformat()
                ET.SubElement(metadata, "shape").text = str(data.shape)
                ET.SubElement(metadata, "columns").text = ', '.join(data.columns.tolist())
            
            # Add data
            records = ET.SubElement(root, "records")
            for _, row in data.iterrows():
                record = ET.SubElement(records, "record")
                for col, value in row.items():
                    field = ET.SubElement(record, col)
                    field.text = str(value) if pd.notna(value) else ""
            
            # Write to file
            tree = ET.ElementTree(root)
            tree.write(config.output_path, encoding=config.encoding, xml_declaration=True)
        else:
            raise ValueError("XML export only supports DataFrame data")
        
        return config.output_path
    
    def _export_tsv(self, data: pd.DataFrame, config: ExportConfig) -> str:
        """Export data as TSV (Tab-Separated Values)."""
        config.delimiter = '\t'
        return self._export_csv(data, config)
    
    def _compress_file(self, file_path: str, original_format: ExportFormat) -> str:
        """Compress a file."""
        compressed_path = f"{file_path}.gz"
        
        with open(file_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove original file
        Path(file_path).unlink()
        
        return compressed_path
    
    def create_export_package(self, job_ids: List[str], package_name: str = None) -> str:
        """
        Create a package containing multiple export files.
        
        Args:
            job_ids: List of export job IDs to include
            package_name: Name of the package file
            
        Returns:
            str: Path to the package file
        """
        if package_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            package_name = f"export_package_{timestamp}.zip"
        
        package_path = self.output_dir / package_name
        
        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for job_id in job_ids:
                job = self.export_jobs.get(job_id)
                if job and job.status == ExportStatus.COMPLETED:
                    output_path = Path(job.config.output_path)
                    if output_path.exists():
                        zipf.write(output_path, output_path.name)
                        
                        # Add metadata file
                        metadata = {
                            'job_id': job.id,
                            'job_name': job.name,
                            'export_format': job.config.format.value,
                            'created_at': job.created_at.isoformat(),
                            'completed_at': job.completed_at.isoformat(),
                            'file_size': job.file_size
                        }
                        
                        metadata_path = f"{output_path.stem}_metadata.json"
                        zipf.writestr(metadata_path, json.dumps(metadata, indent=2))
        
        logger.info(f"Created export package: {package_path}")
        return str(package_path)
    
    def get_export_status(self, job_id: str) -> Optional[ExportStatus]:
        """Get status of an export job."""
        job = self.export_jobs.get(job_id)
        return job.status if job else None
    
    def get_export_jobs(self, status: ExportStatus = None) -> List[ExportJob]:
        """Get export jobs, optionally filtered by status."""
        jobs = list(self.export_jobs.values())
        if status:
            jobs = [job for job in jobs if job.status == status]
        return jobs
    
    def cancel_export_job(self, job_id: str) -> bool:
        """Cancel an export job."""
        job = self.export_jobs.get(job_id)
        if job and job.status in [ExportStatus.PENDING, ExportStatus.RUNNING]:
            job.status = ExportStatus.CANCELLED
            job.completed_at = datetime.now()
            logger.info(f"Cancelled export job: {job.name}")
            return True
        return False
    
    def retry_export_job(self, job_id: str) -> bool:
        """Retry a failed export job."""
        job = self.export_jobs.get(job_id)
        if job and job.status == ExportStatus.FAILED:
            job.status = ExportStatus.PENDING
            job.progress = 0.0
            job.error_message = None
            job.started_at = None
            job.completed_at = None
            
            # Re-add to queue
            self.job_queue.put(job)
            logger.info(f"Retrying export job: {job.name}")
            return True
        return False
    
    def get_export_statistics(self) -> Dict[str, Any]:
        """Get export statistics."""
        jobs = list(self.export_jobs.values())
        
        status_counts = {}
        for status in ExportStatus:
            status_counts[status.value] = sum(1 for job in jobs if job.status == status)
        
        total_size = sum(job.file_size or 0 for job in jobs if job.status == ExportStatus.COMPLETED)
        
        return {
            'total_jobs': len(jobs),
            'status_counts': status_counts,
            'queue_size': self.job_queue.qsize(),
            'active_workers': sum(1 for worker in self.workers.values() if worker['status'] == 'running'),
            'total_exported_size': total_size,
            'is_running': self.is_running
        }
    
    def cleanup_old_exports(self, days_old: int = 30) -> int:
        """
        Clean up old export files.
        
        Args:
            days_old: Remove files older than this many days
            
        Returns:
            int: Number of files removed
        """
        cutoff_date = datetime.now() - timedelta(days=days_old)
        removed_count = 0
        
        for job in self.export_jobs.values():
            if (job.status == ExportStatus.COMPLETED and 
                job.completed_at and 
                job.completed_at < cutoff_date):
                
                output_path = Path(job.config.output_path)
                if output_path.exists():
                    output_path.unlink()
                    removed_count += 1
        
        logger.info(f"Cleaned up {removed_count} old export files")
        return removed_count
