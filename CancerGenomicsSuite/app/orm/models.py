#!/usr/bin/env python3
"""
Database Models for Cancer Genomics Analysis Suite

This module defines comprehensive database models for storing genomic data,
analysis results, and application state. It includes models for gene expression,
mutations, analysis jobs, data files, and results.

Features:
- Gene expression data storage and management
- Mutation record tracking with clinical significance
- Analysis job management and status tracking
- Data file upload and processing tracking
- Analysis result storage and retrieval
- Comprehensive relationships and constraints
- Data validation and serialization methods

Models:
- GeneExpression: Gene expression data with sample and condition information
- MutationRecord: Mutation data with clinical significance and source tracking
- AnalysisJob: Job management for various analysis types
- DataFile: File upload and processing management
- AnalysisResult: Analysis output storage and retrieval
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy import Index, CheckConstraint
from sqlalchemy.exc import SQLAlchemyError

# Import db from the main app module
from .. import db

# Configure logging
logger = logging.getLogger(__name__)


class GeneExpression(db.Model):
    """
    Model for storing gene expression data.
    
    This model stores gene expression values for different samples and conditions,
    supporting various types of expression analysis including RNA-seq, microarray,
    and qPCR data.
    """
    
    __tablename__ = 'gene_expression'
    
    id = db.Column(db.Integer, primary_key=True)
    gene_symbol = db.Column(db.String(50), nullable=False, index=True)
    gene_id = db.Column(db.String(50), nullable=True, index=True)  # Ensembl ID, etc.
    sample_id = db.Column(db.String(100), nullable=False, index=True)
    expression_value = db.Column(db.Float, nullable=False)
    expression_unit = db.Column(db.String(20), default='FPKM')  # FPKM, TPM, counts, etc.
    condition = db.Column(db.String(100), nullable=True, index=True)
    tissue_type = db.Column(db.String(100), nullable=True)
    cell_line = db.Column(db.String(100), nullable=True)
    treatment = db.Column(db.String(100), nullable=True)
    time_point = db.Column(db.String(50), nullable=True)
    replicate = db.Column(db.Integer, nullable=True)
    batch_id = db.Column(db.String(50), nullable=True)
    quality_score = db.Column(db.Float, nullable=True)
    is_normalized = db.Column(db.Boolean, default=False)
    normalization_method = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    data_file_id = db.Column(db.Integer, db.ForeignKey('data_files.id'), nullable=True)
    data_file = db.relationship('DataFile', backref=db.backref('gene_expression_data', lazy=True))
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_gene_sample', 'gene_symbol', 'sample_id'),
        Index('idx_gene_condition', 'gene_symbol', 'condition'),
        Index('idx_sample_condition', 'sample_id', 'condition'),
        CheckConstraint('expression_value >= 0', name='check_positive_expression'),
    )
    
    def __repr__(self):
        return f'<GeneExpression {self.gene_symbol}:{self.sample_id}={self.expression_value}>'
    
    def to_dict(self):
        """Convert gene expression record to dictionary."""
        return {
            'id': self.id,
            'gene_symbol': self.gene_symbol,
            'gene_id': self.gene_id,
            'sample_id': self.sample_id,
            'expression_value': self.expression_value,
            'expression_unit': self.expression_unit,
            'condition': self.condition,
            'tissue_type': self.tissue_type,
            'cell_line': self.cell_line,
            'treatment': self.treatment,
            'time_point': self.time_point,
            'replicate': self.replicate,
            'batch_id': self.batch_id,
            'quality_score': self.quality_score,
            'is_normalized': self.is_normalized,
            'normalization_method': self.normalization_method,
            'data_file_id': self.data_file_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_by_gene(cls, gene_symbol: str, condition: Optional[str] = None):
        """Get all expression data for a specific gene."""
        query = cls.query.filter_by(gene_symbol=gene_symbol)
        if condition:
            query = query.filter_by(condition=condition)
        return query.all()
    
    @classmethod
    def get_by_sample(cls, sample_id: str):
        """Get all expression data for a specific sample."""
        return cls.query.filter_by(sample_id=sample_id).all()
    
    @classmethod
    def get_expression_summary(cls, gene_symbol: str):
        """Get expression summary statistics for a gene."""
        from sqlalchemy import func
        
        result = db.session.query(
            func.count(cls.id).label('count'),
            func.avg(cls.expression_value).label('mean'),
            func.stddev(cls.expression_value).label('std'),
            func.min(cls.expression_value).label('min'),
            func.max(cls.expression_value).label('max')
        ).filter_by(gene_symbol=gene_symbol).first()
        
        return {
            'gene_symbol': gene_symbol,
            'count': result.count,
            'mean': float(result.mean) if result.mean else 0,
            'std': float(result.std) if result.std else 0,
            'min': float(result.min) if result.min else 0,
            'max': float(result.max) if result.max else 0
        }


class MutationRecord(db.Model):
    """
    Model for storing mutation records with clinical significance.
    
    This model stores mutation data from various sources including COSMIC,
    ClinVar, and custom annotations, with comprehensive clinical information.
    """
    
    __tablename__ = 'mutation_records'
    
    id = db.Column(db.Integer, primary_key=True)
    gene = db.Column(db.String(100), nullable=False, index=True)
    gene_id = db.Column(db.String(50), nullable=True, index=True)  # Ensembl ID
    variant = db.Column(db.String(100), nullable=False, index=True)
    variant_type = db.Column(db.String(50), nullable=True)  # SNV, indel, CNV, etc.
    chromosome = db.Column(db.String(10), nullable=True)
    position = db.Column(db.Integer, nullable=True)
    ref_allele = db.Column(db.String(10), nullable=True)
    alt_allele = db.Column(db.String(10), nullable=True)
    sample_id = db.Column(db.String(100), nullable=False, index=True)
    effect = db.Column(db.String(255), nullable=True)
    effect_prediction = db.Column(db.String(100), nullable=True)  # SIFT, PolyPhen, etc.
    clinical_significance = db.Column(db.String(100), nullable=True, index=True)
    pathogenicity = db.Column(db.String(50), nullable=True)  # pathogenic, benign, VUS
    allele_frequency = db.Column(db.Float, nullable=True)
    read_depth = db.Column(db.Integer, nullable=True)
    quality_score = db.Column(db.Float, nullable=True)
    source = db.Column(db.String(50), nullable=True, index=True)  # COSMIC, ClinVar, custom
    source_id = db.Column(db.String(100), nullable=True)  # ID in source database
    cancer_type = db.Column(db.String(100), nullable=True, index=True)
    tissue_type = db.Column(db.String(100), nullable=True)
    cell_line = db.Column(db.String(100), nullable=True)
    treatment_response = db.Column(db.String(100), nullable=True)
    drug_sensitivity = db.Column(db.String(100), nullable=True)
    functional_impact = db.Column(db.String(100), nullable=True)
    protein_domain = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    data_file_id = db.Column(db.Integer, db.ForeignKey('data_files.id'), nullable=True)
    data_file = db.relationship('DataFile', backref=db.backref('mutation_data', lazy=True))
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_gene_variant', 'gene', 'variant'),
        Index('idx_sample_gene', 'sample_id', 'gene'),
        Index('idx_chromosome_position', 'chromosome', 'position'),
        Index('idx_clinical_significance', 'clinical_significance', 'pathogenicity'),
        CheckConstraint('allele_frequency >= 0 AND allele_frequency <= 1', name='check_allele_frequency'),
        CheckConstraint('read_depth >= 0', name='check_positive_read_depth'),
    )
    
    def __repr__(self):
        return f'<MutationRecord {self.gene}:{self.variant} in {self.sample_id}>'
    
    def to_dict(self):
        """Convert mutation record to dictionary."""
        return {
            'id': self.id,
            'gene': self.gene,
            'gene_id': self.gene_id,
            'variant': self.variant,
            'variant_type': self.variant_type,
            'chromosome': self.chromosome,
            'position': self.position,
            'ref_allele': self.ref_allele,
            'alt_allele': self.alt_allele,
            'sample_id': self.sample_id,
            'effect': self.effect,
            'effect_prediction': self.effect_prediction,
            'clinical_significance': self.clinical_significance,
            'pathogenicity': self.pathogenicity,
            'allele_frequency': self.allele_frequency,
            'read_depth': self.read_depth,
            'quality_score': self.quality_score,
            'source': self.source,
            'source_id': self.source_id,
            'cancer_type': self.cancer_type,
            'tissue_type': self.tissue_type,
            'cell_line': self.cell_line,
            'treatment_response': self.treatment_response,
            'drug_sensitivity': self.drug_sensitivity,
            'functional_impact': self.functional_impact,
            'protein_domain': self.protein_domain,
            'data_file_id': self.data_file_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_by_gene(cls, gene: str, pathogenicity: Optional[str] = None):
        """Get all mutations for a specific gene."""
        query = cls.query.filter_by(gene=gene)
        if pathogenicity:
            query = query.filter_by(pathogenicity=pathogenicity)
        return query.all()
    
    @classmethod
    def get_by_sample(cls, sample_id: str):
        """Get all mutations for a specific sample."""
        return cls.query.filter_by(sample_id=sample_id).all()
    
    @classmethod
    def get_pathogenic_mutations(cls, cancer_type: Optional[str] = None):
        """Get all pathogenic mutations, optionally filtered by cancer type."""
        query = cls.query.filter_by(pathogenicity='pathogenic')
        if cancer_type:
            query = query.filter_by(cancer_type=cancer_type)
        return query.all()
    
    @classmethod
    def get_mutation_summary(cls, gene: str):
        """Get mutation summary statistics for a gene."""
        from sqlalchemy import func
        
        result = db.session.query(
            func.count(cls.id).label('total_mutations'),
            func.count(func.distinct(cls.sample_id)).label('affected_samples'),
            func.count(func.distinct(cls.cancer_type)).label('cancer_types'),
            func.avg(cls.allele_frequency).label('avg_allele_frequency')
        ).filter_by(gene=gene).first()
        
        pathogenic_count = cls.query.filter_by(gene=gene, pathogenicity='pathogenic').count()
        
        return {
            'gene': gene,
            'total_mutations': result.total_mutations,
            'affected_samples': result.affected_samples,
            'cancer_types': result.cancer_types,
            'pathogenic_mutations': pathogenic_count,
            'avg_allele_frequency': float(result.avg_allele_frequency) if result.avg_allele_frequency else 0
        }


class AnalysisJob(db.Model):
    """
    Model for tracking analysis jobs and their execution status.
    
    This model manages the lifecycle of various analysis jobs including
    gene expression analysis, mutation analysis, pathway analysis, and
    machine learning predictions.
    """
    
    __tablename__ = 'analysis_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    job_type = db.Column(db.String(50), nullable=False, index=True)  # gene_expression, mutation, pathway, ml
    job_name = db.Column(db.String(200), nullable=True)  # Human-readable job name
    status = db.Column(db.String(20), default='pending', index=True)  # pending, running, completed, failed, cancelled
    priority = db.Column(db.Integer, default=5)  # 1-10, higher number = higher priority
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    input_data = db.Column(db.Text, nullable=True)  # JSON string of input parameters
    results = db.Column(db.Text, nullable=True)  # JSON string of results
    error_message = db.Column(db.Text, nullable=True)
    progress = db.Column(db.Float, default=0.0)  # Progress percentage (0-100)
    estimated_completion = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Job configuration
    parameters = db.Column(db.Text, nullable=True)  # JSON string of job parameters
    output_format = db.Column(db.String(50), default='json')  # json, csv, pdf, html
    notification_email = db.Column(db.String(255), nullable=True)
    
    # Resource usage tracking
    cpu_time = db.Column(db.Float, nullable=True)  # CPU time in seconds
    memory_usage = db.Column(db.Float, nullable=True)  # Memory usage in MB
    disk_usage = db.Column(db.Float, nullable=True)  # Disk usage in MB
    
    # Relationships
    results_rel = db.relationship('AnalysisResult', backref='job', lazy=True, cascade='all, delete-orphan')
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_job_type_status', 'job_type', 'status'),
        Index('idx_user_status', 'user_id', 'status'),
        Index('idx_created_at_status', 'created_at', 'status'),
        CheckConstraint('progress >= 0 AND progress <= 100', name='check_progress_range'),
        CheckConstraint('priority >= 1 AND priority <= 10', name='check_priority_range'),
    )
    
    def __repr__(self):
        return f'<AnalysisJob {self.job_id}:{self.job_type} [{self.status}]>'
    
    def to_dict(self):
        """Convert job to dictionary."""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'job_type': self.job_type,
            'job_name': self.job_name,
            'status': self.status,
            'priority': self.priority,
            'user_id': self.user_id,
            'input_data': json.loads(self.input_data) if self.input_data else None,
            'results': json.loads(self.results) if self.results else None,
            'error_message': self.error_message,
            'progress': self.progress,
            'estimated_completion': self.estimated_completion.isoformat() if self.estimated_completion else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'parameters': json.loads(self.parameters) if self.parameters else None,
            'output_format': self.output_format,
            'notification_email': self.notification_email,
            'cpu_time': self.cpu_time,
            'memory_usage': self.memory_usage,
            'disk_usage': self.disk_usage
        }
    
    def update_status(self, status: str, progress: Optional[float] = None, error_message: Optional[str] = None):
        """Update job status and progress."""
        self.status = status
        if progress is not None:
            self.progress = progress
        if error_message:
            self.error_message = error_message
        
        if status == 'running' and not self.started_at:
            self.started_at = datetime.utcnow()
        elif status in ['completed', 'failed', 'cancelled']:
            self.completed_at = datetime.utcnow()
            self.progress = 100.0 if status == 'completed' else self.progress
        
        self.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            logger.info(f"Job {self.job_id} status updated to {status}")
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to update job status: {e}")
            raise
    
    def set_progress(self, progress: float, estimated_completion: Optional[datetime] = None):
        """Update job progress."""
        self.progress = max(0.0, min(100.0, progress))
        if estimated_completion:
            self.estimated_completion = estimated_completion
        self.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to update job progress: {e}")
            raise
    
    def add_result(self, result_type: str, result_data: Dict[str, Any], file_path: Optional[str] = None):
        """Add a result to this job."""
        result = AnalysisResult(
            job_id=self.id,
            result_type=result_type,
            result_data=json.dumps(result_data),
            file_path=file_path
        )
        
        try:
            db.session.add(result)
            db.session.commit()
            logger.info(f"Added result {result_type} to job {self.job_id}")
            return result
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to add result to job: {e}")
            raise
    
    @classmethod
    def get_by_status(cls, status: str):
        """Get all jobs with a specific status."""
        return cls.query.filter_by(status=status).order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_by_user(cls, user_id: int, status: Optional[str] = None):
        """Get all jobs for a specific user."""
        query = cls.query.filter_by(user_id=user_id)
        if status:
            query = query.filter_by(status=status)
        return query.order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_running_jobs(cls):
        """Get all currently running jobs."""
        return cls.query.filter_by(status='running').order_by(cls.priority.desc(), cls.created_at.asc()).all()
    
    @classmethod
    def get_job_statistics(cls):
        """Get job statistics."""
        from sqlalchemy import func
        
        stats = db.session.query(
            cls.status,
            func.count(cls.id).label('count'),
            func.avg(cls.progress).label('avg_progress')
        ).group_by(cls.status).all()
        
        return {
            'by_status': {stat.status: {'count': stat.count, 'avg_progress': float(stat.avg_progress or 0)} for stat in stats},
            'total_jobs': sum(stat.count for stat in stats)
        }
    
    @property
    def duration(self) -> Optional[float]:
        """Get job duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.utcnow() - self.started_at).total_seconds()
        return None
    
    @property
    def is_completed(self) -> bool:
        """Check if job is completed."""
        return self.status == 'completed'
    
    @property
    def is_failed(self) -> bool:
        """Check if job failed."""
        return self.status == 'failed'
    
    @property
    def is_running(self) -> bool:
        """Check if job is running."""
        return self.status == 'running'

class DataFile(db.Model):
    """
    Model for tracking uploaded data files and their processing status.
    
    This model manages file uploads, metadata, and processing status for
    various genomic data file types including VCF, FASTQ, CSV, and others.
    """
    
    __tablename__ = 'data_files'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False, index=True)  # csv, vcf, fastq, bam, etc.
    file_extension = db.Column(db.String(10), nullable=True)
    file_size = db.Column(db.BigInteger, nullable=False)  # Use BigInteger for large files
    file_path = db.Column(db.String(500), nullable=False)
    checksum = db.Column(db.String(64), nullable=True)  # MD5 or SHA256 checksum
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    is_processed = db.Column(db.Boolean, default=False, index=True)
    processing_status = db.Column(db.String(50), default='pending')  # pending, processing, completed, failed
    processing_error = db.Column(db.Text, nullable=True)
    file_metadata = db.Column(db.Text, nullable=True)  # JSON string of file metadata
    
    # File validation and quality
    is_valid = db.Column(db.Boolean, default=True)
    validation_errors = db.Column(db.Text, nullable=True)  # JSON string of validation errors
    quality_score = db.Column(db.Float, nullable=True)  # 0-1 quality score
    
    # Data statistics
    record_count = db.Column(db.Integer, nullable=True)  # Number of records in file
    sample_count = db.Column(db.Integer, nullable=True)  # Number of samples
    gene_count = db.Column(db.Integer, nullable=True)  # Number of genes
    
    # Processing information
    processing_started_at = db.Column(db.DateTime, nullable=True)
    processing_completed_at = db.Column(db.DateTime, nullable=True)
    processing_duration = db.Column(db.Float, nullable=True)  # Duration in seconds
    
    # File organization
    project_id = db.Column(db.String(100), nullable=True, index=True)
    dataset_id = db.Column(db.String(100), nullable=True, index=True)
    tags = db.Column(db.Text, nullable=True)  # JSON array of tags
    
    # Relationships
    gene_expression_data = db.relationship('GeneExpression', backref='data_file', lazy=True)
    mutation_data = db.relationship('MutationRecord', backref='data_file', lazy=True)
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_file_type_status', 'file_type', 'processing_status'),
        Index('idx_user_upload_date', 'user_id', 'upload_date'),
        Index('idx_project_dataset', 'project_id', 'dataset_id'),
        CheckConstraint('file_size >= 0', name='check_positive_file_size'),
        CheckConstraint('quality_score >= 0 AND quality_score <= 1', name='check_quality_score_range'),
    )
    
    def __repr__(self):
        return f'<DataFile {self.filename} ({self.file_type})>'
    
    def to_dict(self):
        """Convert file to dictionary."""
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_type': self.file_type,
            'file_extension': self.file_extension,
            'file_size': self.file_size,
            'file_path': self.file_path,
            'checksum': self.checksum,
            'user_id': self.user_id,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'is_processed': self.is_processed,
            'processing_status': self.processing_status,
            'processing_error': self.processing_error,
            'metadata': json.loads(self.file_metadata) if self.file_metadata else None,
            'is_valid': self.is_valid,
            'validation_errors': json.loads(self.validation_errors) if self.validation_errors else None,
            'quality_score': self.quality_score,
            'record_count': self.record_count,
            'sample_count': self.sample_count,
            'gene_count': self.gene_count,
            'processing_started_at': self.processing_started_at.isoformat() if self.processing_started_at else None,
            'processing_completed_at': self.processing_completed_at.isoformat() if self.processing_completed_at else None,
            'processing_duration': self.processing_duration,
            'project_id': self.project_id,
            'dataset_id': self.dataset_id,
            'tags': json.loads(self.tags) if self.tags else None
        }
    
    def update_processing_status(self, status: str, error_message: Optional[str] = None):
        """Update file processing status."""
        self.processing_status = status
        
        if status == 'processing' and not self.processing_started_at:
            self.processing_started_at = datetime.utcnow()
        elif status in ['completed', 'failed']:
            self.processing_completed_at = datetime.utcnow()
            if self.processing_started_at:
                self.processing_duration = (self.processing_completed_at - self.processing_started_at).total_seconds()
            self.is_processed = (status == 'completed')
        
        if error_message:
            self.processing_error = error_message
        
        try:
            db.session.commit()
            logger.info(f"File {self.filename} processing status updated to {status}")
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to update file processing status: {e}")
            raise
    
    def add_validation_error(self, error_type: str, error_message: str):
        """Add a validation error to the file."""
        errors = json.loads(self.validation_errors) if self.validation_errors else []
        errors.append({
            'type': error_type,
            'message': error_message,
            'timestamp': datetime.utcnow().isoformat()
        })
        self.validation_errors = json.dumps(errors)
        self.is_valid = False
        
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to add validation error: {e}")
            raise
    
    def set_metadata(self, metadata: Dict[str, Any]):
        """Set file metadata."""
        self.file_metadata = json.dumps(metadata)
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to set file metadata: {e}")
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get file metadata as dictionary."""
        return json.loads(self.file_metadata) if self.file_metadata else {}
    
    @classmethod
    def get_by_type(cls, file_type: str, processed_only: bool = False):
        """Get files by type."""
        query = cls.query.filter_by(file_type=file_type)
        if processed_only:
            query = query.filter_by(is_processed=True)
        return query.order_by(cls.upload_date.desc()).all()
    
    @classmethod
    def get_by_user(cls, user_id: int, file_type: Optional[str] = None):
        """Get files by user."""
        query = cls.query.filter_by(user_id=user_id)
        if file_type:
            query = query.filter_by(file_type=file_type)
        return query.order_by(cls.upload_date.desc()).all()
    
    @classmethod
    def get_pending_processing(cls):
        """Get files pending processing."""
        return cls.query.filter_by(processing_status='pending').order_by(cls.upload_date.asc()).all()
    
    @classmethod
    def get_file_statistics(cls):
        """Get file statistics."""
        from sqlalchemy import func
        
        stats = db.session.query(
            cls.file_type,
            func.count(cls.id).label('count'),
            func.sum(cls.file_size).label('total_size'),
            func.avg(cls.file_size).label('avg_size')
        ).group_by(cls.file_type).all()
        
        return {
            'by_type': {
                stat.file_type: {
                    'count': stat.count,
                    'total_size': stat.total_size or 0,
                    'avg_size': float(stat.avg_size or 0)
                }
                for stat in stats
            },
            'total_files': sum(stat.count for stat in stats),
            'total_size': sum(stat.total_size or 0 for stat in stats)
        }
    
    @property
    def file_size_mb(self) -> float:
        """Get file size in MB."""
        return self.file_size / (1024 * 1024) if self.file_size else 0
    
    @property
    def file_size_gb(self) -> float:
        """Get file size in GB."""
        return self.file_size / (1024 * 1024 * 1024) if self.file_size else 0
    
    @property
    def is_large_file(self) -> bool:
        """Check if file is considered large (>100MB)."""
        return self.file_size > 100 * 1024 * 1024 if self.file_size else False

class AnalysisResult(db.Model):
    """
    Model for storing analysis results and outputs.
    
    This model stores various types of analysis results including plots,
    tables, summaries, and generated files from different analysis jobs.
    """
    
    __tablename__ = 'analysis_results'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('analysis_jobs.id'), nullable=False, index=True)
    result_type = db.Column(db.String(50), nullable=False, index=True)  # plot, table, summary, report, etc.
    result_name = db.Column(db.String(200), nullable=True)  # Human-readable result name
    result_data = db.Column(db.Text, nullable=False)  # JSON string of result data
    file_path = db.Column(db.String(500), nullable=True)  # Path to generated files
    file_size = db.Column(db.BigInteger, nullable=True)  # Size of result file
    mime_type = db.Column(db.String(100), nullable=True)  # MIME type of result
    is_public = db.Column(db.Boolean, default=False)  # Whether result is publicly accessible
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Result metadata
    description = db.Column(db.Text, nullable=True)
    tags = db.Column(db.Text, nullable=True)  # JSON array of tags
    version = db.Column(db.String(20), default='1.0')
    
    # Result validation
    is_valid = db.Column(db.Boolean, default=True)
    validation_errors = db.Column(db.Text, nullable=True)  # JSON string of validation errors
    
    # Relationships
    job = db.relationship('AnalysisJob', backref=db.backref('results', lazy=True, cascade='all, delete-orphan'))
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_job_result_type', 'job_id', 'result_type'),
        Index('idx_result_type_created', 'result_type', 'created_at'),
        Index('idx_is_public_created', 'is_public', 'created_at'),
    )
    
    def __repr__(self):
        return f'<AnalysisResult {self.id}:{self.result_type}>'
    
    def to_dict(self):
        """Convert result to dictionary."""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'result_type': self.result_type,
            'result_name': self.result_name,
            'result_data': json.loads(self.result_data) if self.result_data else None,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'description': self.description,
            'tags': json.loads(self.tags) if self.tags else None,
            'version': self.version,
            'is_valid': self.is_valid,
            'validation_errors': json.loads(self.validation_errors) if self.validation_errors else None
        }
    
    def get_result_data(self) -> Dict[str, Any]:
        """Get result data as dictionary."""
        return json.loads(self.result_data) if self.result_data else {}
    
    def set_result_data(self, data: Dict[str, Any]):
        """Set result data from dictionary."""
        self.result_data = json.dumps(data)
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to set result data: {e}")
            raise
    
    def add_tag(self, tag: str):
        """Add a tag to the result."""
        tags = json.loads(self.tags) if self.tags else []
        if tag not in tags:
            tags.append(tag)
            self.tags = json.dumps(tags)
            try:
                db.session.commit()
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(f"Failed to add tag: {e}")
                raise
    
    def remove_tag(self, tag: str):
        """Remove a tag from the result."""
        tags = json.loads(self.tags) if self.tags else []
        if tag in tags:
            tags.remove(tag)
            self.tags = json.dumps(tags)
            try:
                db.session.commit()
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(f"Failed to remove tag: {e}")
                raise
    
    @classmethod
    def get_by_job(cls, job_id: int, result_type: Optional[str] = None):
        """Get results by job ID."""
        query = cls.query.filter_by(job_id=job_id)
        if result_type:
            query = query.filter_by(result_type=result_type)
        return query.order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_by_type(cls, result_type: str, public_only: bool = False):
        """Get results by type."""
        query = cls.query.filter_by(result_type=result_type)
        if public_only:
            query = query.filter_by(is_public=True)
        return query.order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_public_results(cls):
        """Get all public results."""
        return cls.query.filter_by(is_public=True).order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_result_statistics(cls):
        """Get result statistics."""
        from sqlalchemy import func
        
        stats = db.session.query(
            cls.result_type,
            func.count(cls.id).label('count'),
            func.sum(cls.file_size).label('total_size'),
            func.avg(cls.file_size).label('avg_size')
        ).group_by(cls.result_type).all()
        
        return {
            'by_type': {
                stat.result_type: {
                    'count': stat.count,
                    'total_size': stat.total_size or 0,
                    'avg_size': float(stat.avg_size or 0)
                }
                for stat in stats
            },
            'total_results': sum(stat.count for stat in stats),
            'total_size': sum(stat.total_size or 0 for stat in stats)
        }
    
    @property
    def file_size_mb(self) -> float:
        """Get file size in MB."""
        return self.file_size / (1024 * 1024) if self.file_size else 0
    
    @property
    def has_file(self) -> bool:
        """Check if result has an associated file."""
        return bool(self.file_path and self.file_path.strip())


# Additional utility models for enhanced functionality

class Project(db.Model):
    """
    Model for organizing analysis projects.
    
    This model allows users to organize their analyses into projects
    for better data management and collaboration.
    """
    
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    project_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Project settings
    settings = db.Column(db.Text, nullable=True)  # JSON string of project settings
    tags = db.Column(db.Text, nullable=True)  # JSON array of tags
    
    # Relationships
    owner = db.relationship('User', backref=db.backref('projects', lazy=True))
    
    def __repr__(self):
        return f'<Project {self.name} ({self.project_id})>'
    
    def to_dict(self):
        """Convert project to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'project_id': self.project_id,
            'owner_id': self.owner_id,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'settings': json.loads(self.settings) if self.settings else None,
            'tags': json.loads(self.tags) if self.tags else None
        }


class Dataset(db.Model):
    """
    Model for organizing data files into datasets.
    
    This model allows users to group related data files into datasets
    for easier management and analysis.
    """
    
    __tablename__ = 'datasets'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    dataset_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    project_id = db.Column(db.String(100), db.ForeignKey('projects.project_id'), nullable=True, index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Dataset metadata
    dataset_metadata = db.Column(db.Text, nullable=True)  # JSON string of dataset metadata
    tags = db.Column(db.Text, nullable=True)  # JSON array of tags
    
    # Relationships
    project = db.relationship('Project', backref=db.backref('datasets', lazy=True))
    owner = db.relationship('User', backref=db.backref('datasets', lazy=True))
    
    def __repr__(self):
        return f'<Dataset {self.name} ({self.dataset_id})>'
    
    def to_dict(self):
        """Convert dataset to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'dataset_id': self.dataset_id,
            'project_id': self.project_id,
            'owner_id': self.owner_id,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'metadata': json.loads(self.file_metadata) if self.file_metadata else None,
            'tags': json.loads(self.tags) if self.tags else None
        }


# Model utility functions and management

def get_all_models():
    """
    Get all model classes defined in this module.
    
    Returns:
        List of model classes
    """
    return [
        GeneExpression,
        MutationRecord,
        AnalysisJob,
        DataFile,
        AnalysisResult,
        Project,
        Dataset
    ]


def get_model_by_table_name(table_name: str):
    """
    Get a model class by its table name.
    
    Args:
        table_name: Name of the database table
        
    Returns:
        Model class or None if not found
    """
    models = {
        'gene_expression': GeneExpression,
        'mutation_records': MutationRecord,
        'analysis_jobs': AnalysisJob,
        'data_files': DataFile,
        'analysis_results': AnalysisResult,
        'projects': Project,
        'datasets': Dataset
    }
    
    return models.get(table_name)


def get_model_statistics():
    """
    Get statistics for all models.
    
    Returns:
        Dict containing model statistics
    """
    try:
        stats = {}
        
        for model in get_all_models():
            try:
                count = model.query.count()
                stats[model.__tablename__] = {
                    'count': count,
                    'model_name': model.__name__
                }
            except Exception as e:
                logger.warning(f"Failed to get count for {model.__name__}: {e}")
                stats[model.__tablename__] = {
                    'count': 'error',
                    'model_name': model.__name__,
                    'error': str(e)
                }
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get model statistics: {e}")
        return {'error': str(e)}


def validate_model_relationships():
    """
    Validate that all model relationships are properly defined.
    
    Returns:
        Dict with validation results
    """
    try:
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check foreign key relationships
        for model in get_all_models():
            for column in model.__table__.columns:
                if column.foreign_keys:
                    for fk in column.foreign_keys:
                        referenced_table = fk.column.table.name
                        referenced_model = get_model_by_table_name(referenced_table)
                        
                        if not referenced_model:
                            validation_results['errors'].append(
                                f"Model {model.__name__} references unknown table {referenced_table}"
                            )
                            validation_results['valid'] = False
        
        # Check relationship definitions
        for model in get_all_models():
            for attr_name in dir(model):
                attr = getattr(model, attr_name)
                if hasattr(attr, 'property') and hasattr(attr.property, 'mapper'):
                    # This is a relationship
                    related_model = attr.property.mapper.class_
                    if related_model not in get_all_models():
                        validation_results['warnings'].append(
                            f"Model {model.__name__} has relationship to unknown model {related_model.__name__}"
                        )
        
        return validation_results
        
    except Exception as e:
        logger.error(f"Model relationship validation failed: {e}")
        return {
            'valid': False,
            'errors': [f"Validation failed: {str(e)}"],
            'warnings': []
        }


def create_sample_data():
    """
    Create sample data for testing and development.
    
    Returns:
        Dict with creation results
    """
    try:
        results = {
            'created': {},
            'errors': []
        }
        
        # Create sample gene expression data
        try:
            sample_expression = GeneExpression(
                gene_symbol='BRCA1',
                gene_id='ENSG00000012048',
                sample_id='SAMPLE_001',
                expression_value=5.2,
                expression_unit='FPKM',
                condition='tumor',
                tissue_type='breast',
                quality_score=0.95
            )
            db.session.add(sample_expression)
            results['created']['gene_expression'] = 1
        except Exception as e:
            results['errors'].append(f"Failed to create sample gene expression: {e}")
        
        # Create sample mutation record
        try:
            sample_mutation = MutationRecord(
                gene='BRCA1',
                gene_id='ENSG00000012048',
                variant='c.5266dupC',
                variant_type='SNV',
                chromosome='17',
                position=43094691,
                ref_allele='C',
                alt_allele='CC',
                sample_id='SAMPLE_001',
                effect='frameshift',
                clinical_significance='pathogenic',
                pathogenicity='pathogenic',
                allele_frequency=0.5,
                source='ClinVar'
            )
            db.session.add(sample_mutation)
            results['created']['mutation_record'] = 1
        except Exception as e:
            results['errors'].append(f"Failed to create sample mutation: {e}")
        
        # Create sample analysis job
        try:
            sample_job = AnalysisJob(
                job_id='JOB_001',
                job_type='gene_expression',
                job_name='Sample Expression Analysis',
                status='completed',
                progress=100.0,
                input_data=json.dumps({'genes': ['BRCA1', 'TP53'], 'samples': ['SAMPLE_001']}),
                results=json.dumps({'summary': 'Analysis completed successfully'})
            )
            db.session.add(sample_job)
            results['created']['analysis_job'] = 1
        except Exception as e:
            results['errors'].append(f"Failed to create sample analysis job: {e}")
        
        db.session.commit()
        logger.info("Sample data created successfully")
        
        return results
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to create sample data: {e}")
        return {
            'created': {},
            'errors': [f"Sample data creation failed: {str(e)}"]
        }


def cleanup_sample_data():
    """
    Clean up sample data created for testing.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Delete sample data in reverse order of dependencies
        GeneExpression.query.filter(GeneExpression.gene_symbol == 'BRCA1').delete()
        MutationRecord.query.filter(MutationRecord.gene == 'BRCA1').delete()
        AnalysisJob.query.filter(AnalysisJob.job_id == 'JOB_001').delete()
        
        db.session.commit()
        logger.info("Sample data cleaned up successfully")
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to cleanup sample data: {e}")
        return False


# Export all models and utility functions
__all__ = [
    'GeneExpression',
    'MutationRecord', 
    'AnalysisJob',
    'DataFile',
    'AnalysisResult',
    'Project',
    'Dataset',
    'get_all_models',
    'get_model_by_table_name',
    'get_model_statistics',
    'validate_model_relationships',
    'create_sample_data',
    'cleanup_sample_data'
]
