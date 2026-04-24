#!/usr/bin/env python3
"""
Cancer Genomics Analysis Suite - Configuration Settings

This module provides comprehensive configuration management for the cancer
genomics analysis suite. It supports both advanced Pydantic-based configuration
and a simple fallback configuration for basic functionality.

Features:
- Environment variable loading from .env files
- Pydantic-based validation and type safety
- Fallback configuration when dependencies are missing
- Support for development, production, and testing environments
- Comprehensive API and service configuration
"""

import os
import logging
import tempfile
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
from dotenv import load_dotenv
import secrets

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Try to import Pydantic for advanced configuration
# Support both Pydantic v1 and v2
try:
    try:
        # Try Pydantic v2 first (pydantic_settings)
        from pydantic_settings import BaseSettings
        from pydantic import Field, field_validator, model_validator, ConfigDict
        PYDANTIC_VERSION = 2
        PYDANTIC_AVAILABLE = True
        validator = field_validator  # Alias for compatibility
        root_validator = model_validator  # Alias for compatibility
    except ImportError:
        # Fallback to Pydantic v1
        from pydantic import BaseSettings, Field, validator, root_validator
        PYDANTIC_VERSION = 1
        PYDANTIC_AVAILABLE = True
        ConfigDict = None  # Not available in v1
except ImportError:
    PYDANTIC_AVAILABLE = False
    PYDANTIC_VERSION = None
    logger.warning("Pydantic not available, using simple configuration fallback")
    # Create dummy classes for fallback
    class BaseSettings:
        pass
    class Field:
        def __init__(self, default=None, env=None, description=None, default_factory=None):
            self.default = default
            self.env = env
            self.description = description
            self.default_factory = default_factory
    def validator(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def root_validator(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    ConfigDict = None


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    url: str = Field(default="sqlite:///cancer_genomics.db", env="DATABASE_URL", description="Primary database URL")
    pool_size: int = Field(default=10, env="DB_POOL_SIZE", description="Database connection pool size")
    max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW", description="Maximum overflow connections")
    pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT", description="Pool timeout in seconds")
    pool_recycle: int = Field(default=3600, env="DB_POOL_RECYCLE", description="Pool recycle time in seconds")
    
    # Backup settings
    backup_enabled: bool = Field(default=True, env="DB_BACKUP_ENABLED")
    backup_schedule: str = Field(default="0 2 * * *", env="DB_BACKUP_SCHEDULE")
    backup_retention_days: int = Field(default=30, env="DB_BACKUP_RETENTION_DAYS")
    
    # Test database
    test_url: Optional[str] = Field(default=None, env="TEST_DATABASE_URL")


class RedisSettings(BaseSettings):
    """Redis configuration settings."""
    
    enabled: bool = Field(default=False, env="ENABLE_REDIS")
    url: Optional[str] = Field(default=None, env="REDIS_URL")
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    db: int = Field(default=0, env="REDIS_DB")
    max_connections: int = Field(default=20, env="REDIS_MAX_CONNECTIONS")
    socket_timeout: int = Field(default=5, env="REDIS_SOCKET_TIMEOUT")
    socket_connect_timeout: int = Field(default=5, env="REDIS_SOCKET_CONNECT_TIMEOUT")
    
    # Cache settings
    cache_default_timeout: int = Field(default=3600, env="CACHE_DEFAULT_TIMEOUT")
    cache_key_prefix: str = Field(default="cancer_genomics:", env="CACHE_KEY_PREFIX")
    
    # Test Redis
    test_url: Optional[str] = Field(default=None, env="TEST_REDIS_URL")


class CelerySettings(BaseSettings):
    """Celery configuration settings."""
    
    broker_url: str = Field(default="redis://localhost:6379/0", env="CELERY_BROKER_URL")
    result_backend: str = Field(default="redis://localhost:6379/0", env="CELERY_RESULT_BACKEND")
    task_serializer: str = Field(default="json", env="CELERY_TASK_SERIALIZER")
    accept_content: List[str] = Field(default=["json"], env="CELERY_ACCEPT_CONTENT")
    result_serializer: str = Field(default="json", env="CELERY_RESULT_SERIALIZER")
    timezone: str = Field(default="UTC", env="CELERY_TIMEZONE")
    enable_utc: bool = Field(default=True, env="CELERY_ENABLE_UTC")
    
    # Worker settings
    worker_concurrency: int = Field(default=4, env="CELERY_WORKER_CONCURRENCY")
    worker_prefetch_multiplier: int = Field(default=1, env="CELERY_WORKER_PREFETCH_MULTIPLIER")
    task_acks_late: bool = Field(default=True, env="CELERY_TASK_ACKS_LATE")
    worker_max_tasks_per_child: int = Field(default=1000, env="CELERY_WORKER_MAX_TASKS_PER_CHILD")
    
    # Task time limits
    task_soft_time_limit: int = Field(default=3600, env="CELERY_TASK_SOFT_TIME_LIMIT")
    task_time_limit: int = Field(default=7200, env="CELERY_TASK_TIME_LIMIT")


class EmailSettings(BaseSettings):
    """Email configuration settings."""
    
    enabled: bool = Field(default=True, env="ENABLE_EMAIL")
    server: Optional[str] = Field(default=None, env="MAIL_SERVER")
    port: Optional[int] = Field(default=587, env="MAIL_PORT")
    use_tls: bool = Field(default=True, env="MAIL_USE_TLS")
    use_ssl: bool = Field(default=False, env="MAIL_USE_SSL")
    username: Optional[str] = Field(default=None, env="MAIL_USERNAME")
    password: Optional[str] = Field(default=None, env="MAIL_PASSWORD")
    default_sender: Optional[str] = Field(default=None, env="MAIL_DEFAULT_SENDER")
    max_emails: int = Field(default=100, env="MAIL_MAX_EMAILS")
    suppress_send: bool = Field(default=False, env="MAIL_SUPPRESS_SEND")
    
    # Email templates
    template_dir: str = Field(default="templates/email", env="EMAIL_TEMPLATE_DIR")
    from_name: str = Field(default="Cancer Genomics Analysis Suite", env="EMAIL_FROM_NAME")


class FileStorageSettings(BaseSettings):
    """File storage configuration settings."""
    
    upload_folder: str = Field(default="uploads", env="UPLOAD_FOLDER")
    max_content_length: int = Field(default=1073741824, env="MAX_CONTENT_LENGTH")  # 1GB
    allowed_extensions: List[str] = Field(
        default=["csv", "txt", "vcf", "fastq", "fasta", "bam", "sam", "bed", "gtf", "gff"],
        env="ALLOWED_EXTENSIONS"
    )
    
    # Cloud storage
    enable_cloud_storage: bool = Field(default=False, env="ENABLE_CLOUD_STORAGE")
    aws_access_key_id: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    aws_s3_bucket: Optional[str] = Field(default=None, env="AWS_S3_BUCKET")
    aws_s3_region: Optional[str] = Field(default=None, env="AWS_S3_REGION")
    aws_s3_endpoint_url: Optional[str] = Field(default=None, env="AWS_S3_ENDPOINT_URL")


class SecuritySettings(BaseSettings):
    """Security configuration settings."""
    
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32), env="SECRET_KEY")
    enable_authentication: bool = Field(default=True, env="ENABLE_AUTHENTICATION")
    session_cookie_secure: bool = Field(default=False, env="SESSION_COOKIE_SECURE")
    session_cookie_httponly: bool = Field(default=True, env="SESSION_COOKIE_HTTPONLY")
    session_cookie_samesite: str = Field(default="Lax", env="SESSION_COOKIE_SAMESITE")
    permanent_session_lifetime: int = Field(default=86400, env="PERMANENT_SESSION_LIFETIME")  # 24 hours
    
    # API security
    api_rate_limit: int = Field(default=1000, env="API_RATE_LIMIT")
    api_rate_limit_window: int = Field(default=3600, env="API_RATE_LIMIT_WINDOW")  # 1 hour
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    
    # CORS settings
    cors_origins: Union[str, List[str]] = Field(default="*", env="CORS_ORIGINS")
    cors_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        env="CORS_METHODS"
    )
    cors_headers: List[str] = Field(
        default=["Content-Type", "Authorization", "X-API-Key"],
        env="CORS_HEADERS"
    )


class ExternalAPISettings(BaseSettings):
    """External API configuration settings."""
    
    # Ensembl API
    ensembl_api_url: str = Field(default="https://rest.ensembl.org", env="ENSEMBL_API_URL")
    ensembl_api_timeout: int = Field(default=30, env="ENSEMBL_API_TIMEOUT")
    ensembl_api_rate_limit: int = Field(default=15, env="ENSEMBL_API_RATE_LIMIT")
    
    # UniProt API
    uniprot_api_url: str = Field(default="https://www.uniprot.org", env="UNIPROT_API_URL")
    uniprot_api_timeout: int = Field(default=30, env="UNIPROT_API_TIMEOUT")
    uniprot_api_rate_limit: int = Field(default=10, env="UNIPROT_API_RATE_LIMIT")
    
    # PubMed API
    pubmed_api_url: str = Field(default="https://eutils.ncbi.nlm.nih.gov/entrez/eutils", env="PUBMED_API_URL")
    pubmed_api_timeout: int = Field(default=30, env="PUBMED_API_TIMEOUT")
    pubmed_api_rate_limit: int = Field(default=3, env="PUBMED_API_RATE_LIMIT")
    
    # ClinVar API
    clinvar_api_url: str = Field(default="https://eutils.ncbi.nlm.nih.gov/entrez/eutils", env="CLINVAR_API_URL")
    clinvar_api_timeout: int = Field(default=30, env="CLINVAR_API_TIMEOUT")
    
    # COSMIC API
    cosmic_api_url: str = Field(default="https://cancer.sanger.ac.uk/cosmic", env="COSMIC_API_URL")
    cosmic_api_timeout: int = Field(default=30, env="COSMIC_API_TIMEOUT")
    cosmic_api_key: Optional[str] = Field(default=None, env="COSMIC_API_KEY")
    cosmic_api_token: Optional[str] = Field(default=None, env="COSMIC_API_TOKEN")
    
    # Scopus API
    scopus_api_url: str = Field(default="https://api.elsevier.com/content/search/scopus", env="SCOPUS_API_URL")
    scopus_api_key: Optional[str] = Field(default=None, env="SCOPUS_API_KEY")
    scopus_api_timeout: int = Field(default=30, env="SCOPUS_API_TIMEOUT")
    scopus_api_rate_limit: int = Field(default=20, env="SCOPUS_API_RATE_LIMIT")
    
    # ENCODE API
    encode_api_base: str = Field(default="https://www.encodeproject.org", env="ENCODE_API_BASE")
    encode_api_url: str = Field(default="https://www.encodeproject.org", env="ENCODE_API_URL")
    encode_api_timeout: int = Field(default=30, env="ENCODE_API_TIMEOUT")
    encode_api_rate_limit: int = Field(default=10, env="ENCODE_API_RATE_LIMIT")
    
    # NCBI API
    ncbi_api_url: str = Field(default="https://eutils.ncbi.nlm.nih.gov/entrez/eutils", env="NCBI_API_URL")
    ncbi_api_key: Optional[str] = Field(default=None, env="NCBI_API_KEY")
    ncbi_api_timeout: int = Field(default=30, env="NCBI_API_TIMEOUT")
    ncbi_api_rate_limit: int = Field(default=3, env="NCBI_API_RATE_LIMIT")
    
    # KEGG API
    kegg_api_url: str = Field(default="https://rest.kegg.jp", env="KEGG_API_URL")
    kegg_api_timeout: int = Field(default=30, env="KEGG_API_TIMEOUT")
    kegg_api_rate_limit: int = Field(default=10, env="KEGG_API_RATE_LIMIT")
    
    # Reactome API
    reactome_api_url: str = Field(default="https://reactome.org/ContentService", env="REACTOME_API_URL")
    reactome_api_timeout: int = Field(default=30, env="REACTOME_API_TIMEOUT")
    reactome_api_rate_limit: int = Field(default=10, env="REACTOME_API_RATE_LIMIT")
    
    # GO (Gene Ontology) API
    go_api_url: str = Field(default="https://api.geneontology.org", env="GO_API_URL")
    go_api_timeout: int = Field(default=30, env="GO_API_TIMEOUT")
    go_api_rate_limit: int = Field(default=10, env="GO_API_RATE_LIMIT")


class AnalysisSettings(BaseSettings):
    """Analysis configuration settings."""
    
    # Gene expression analysis
    expression_normalization_method: str = Field(default="quantile", env="EXPRESSION_NORMALIZATION_METHOD")
    expression_qc_threshold: float = Field(default=0.1, env="EXPRESSION_QC_THRESHOLD")
    expression_batch_correction: bool = Field(default=True, env="EXPRESSION_BATCH_CORRECTION")
    
    # Mutation analysis
    mutation_quality_threshold: float = Field(default=20, env="MUTATION_QUALITY_THRESHOLD")
    mutation_read_depth_threshold: int = Field(default=10, env="MUTATION_READ_DEPTH_THRESHOLD")
    mutation_allele_frequency_threshold: float = Field(default=0.05, env="MUTATION_ALLELE_FREQUENCY_THRESHOLD")
    
    # Machine learning
    ml_cross_validation_folds: int = Field(default=5, env="ML_CROSS_VALIDATION_FOLDS")
    ml_random_state: int = Field(default=42, env="ML_RANDOM_STATE")
    ml_test_size: float = Field(default=0.2, env="ML_TEST_SIZE")
    ml_feature_selection_method: str = Field(default="mutual_info", env="ML_FEATURE_SELECTION_METHOD")
    
    # Pathway analysis
    pathway_database: str = Field(default="kegg", env="PATHWAY_DATABASE")
    pathway_p_value_threshold: float = Field(default=0.05, env="PATHWAY_P_VALUE_THRESHOLD")
    pathway_fdr_threshold: float = Field(default=0.1, env="PATHWAY_FDR_THRESHOLD")


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""
    
    level: str = Field(default="INFO", env="LOG_LEVEL")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    file: Optional[str] = Field(default=None, env="LOG_FILE")
    max_size: int = Field(default=10485760, env="LOG_MAX_SIZE")  # 10MB
    backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")


class MonitoringSettings(BaseSettings):
    """Monitoring configuration settings."""
    
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    health_check_interval: int = Field(default=300, env="HEALTH_CHECK_INTERVAL")  # 5 minutes
    
    # Performance monitoring
    enable_profiling: bool = Field(default=False, env="ENABLE_PROFILING")
    profiling_sample_rate: float = Field(default=0.1, env="PROFILING_SAMPLE_RATE")


class FeatureFlags(BaseSettings):
    """Feature flags configuration."""
    
    # Core analysis features
    enable_gene_expression_analysis: bool = Field(default=True, env="ENABLE_GENE_EXPRESSION_ANALYSIS")
    enable_mutation_analysis: bool = Field(default=True, env="ENABLE_MUTATION_ANALYSIS")
    enable_machine_learning: bool = Field(default=True, env="ENABLE_MACHINE_LEARNING")
    enable_pathway_analysis: bool = Field(default=True, env="ENABLE_PATHWAY_ANALYSIS")
    enable_protein_structure_analysis: bool = Field(default=True, env="ENABLE_PROTEIN_STRUCTURE_ANALYSIS")
    enable_pharmacogenomics: bool = Field(default=True, env="ENABLE_PHARMACOGENOMICS")
    enable_clinical_data_integration: bool = Field(default=True, env="ENABLE_CLINICAL_DATA_INTEGRATION")
    enable_multi_omics_integration: bool = Field(default=True, env="ENABLE_MULTI_OMICS_INTEGRATION")
    
    # Advanced features
    enable_real_time_analysis: bool = Field(default=False, env="ENABLE_REAL_TIME_ANALYSIS")
    enable_distributed_computing: bool = Field(default=True, env="ENABLE_DISTRIBUTED_COMPUTING")
    enable_gpu_acceleration: bool = Field(default=False, env="ENABLE_GPU_ACCELERATION")
    enable_cloud_integration: bool = Field(default=False, env="ENABLE_CLOUD_INTEGRATION")
    
    # New advanced technologies
    enable_pipeline_orchestration: bool = Field(default=True, env="ENABLE_PIPELINE_ORCHESTRATION")
    enable_graph_analytics: bool = Field(default=True, env="ENABLE_GRAPH_ANALYTICS")
    enable_kafka_streaming: bool = Field(default=False, env="ENABLE_KAFKA_STREAMING")
    enable_oauth2_auth: bool = Field(default=True, env="ENABLE_OAUTH2_AUTH")


class DataProcessingSettings(BaseSettings):
    """Data processing configuration settings."""
    
    # File processing
    max_file_size_mb: int = Field(default=1024, env="MAX_FILE_SIZE_MB")
    supported_file_formats: List[str] = Field(
        default=["csv", "txt", "vcf", "fastq", "fasta", "bam", "sam", "bed", "gtf", "gff"],
        env="SUPPORTED_FILE_FORMATS"
    )
    auto_detect_file_format: bool = Field(default=True, env="AUTO_DETECT_FILE_FORMAT")
    
    # Data validation
    enable_data_validation: bool = Field(default=True, env="ENABLE_DATA_VALIDATION")
    strict_data_validation: bool = Field(default=False, env="STRICT_DATA_VALIDATION")
    data_quality_threshold: float = Field(default=0.8, env="DATA_QUALITY_THRESHOLD")
    
    # Data retention
    data_retention_days: int = Field(default=365, env="DATA_RETENTION_DAYS")
    temp_file_cleanup_hours: int = Field(default=24, env="TEMP_FILE_CLEANUP_HOURS")
    backup_retention_days: int = Field(default=90, env="BACKUP_RETENTION_DAYS")


class ComplianceSettings(BaseSettings):
    """Compliance and privacy configuration settings."""
    
    # Data privacy
    enable_data_anonymization: bool = Field(default=True, env="ENABLE_DATA_ANONYMIZATION")
    anonymization_method: str = Field(default="hash", env="ANONYMIZATION_METHOD")
    pii_detection: bool = Field(default=True, env="PII_DETECTION")
    
    # Compliance
    enable_audit_logging: bool = Field(default=True, env="ENABLE_AUDIT_LOGGING")
    audit_log_retention_days: int = Field(default=2555, env="AUDIT_LOG_RETENTION_DAYS")  # 7 years
    enable_access_control: bool = Field(default=True, env="ENABLE_ACCESS_CONTROL")
    
    # Data governance
    data_classification: str = Field(default="confidential", env="DATA_CLASSIFICATION")
    data_retention_policy: str = Field(default="standard", env="DATA_RETENTION_POLICY")
    enable_data_lineage: bool = Field(default=True, env="ENABLE_DATA_LINEAGE")


class NGSPlatformSettings(BaseSettings):
    """NGS Platform configuration settings."""
    
    # NGS platform settings
    platform: str = Field(default="illumina", env="NGS_PLATFORM")
    quality_threshold: int = Field(default=20, env="NGS_QUALITY_THRESHOLD")
    min_read_length: int = Field(default=50, env="NGS_MIN_READ_LENGTH")
    max_read_length: int = Field(default=150, env="NGS_MAX_READ_LENGTH")
    adapter_sequences: List[str] = Field(
        default=["AGATCGGAAGAGCACACGTCTGAACTCCAGTCA", "AGATCGGAAGAGCGTCGTGTAGGGAAAGAGTGT"],
        env="NGS_ADAPTER_SEQUENCES"
    )
    
    # Pipeline settings
    enable_quality_control: bool = Field(default=True, env="NGS_ENABLE_QC")
    enable_adapter_trimming: bool = Field(default=True, env="NGS_ENABLE_ADAPTER_TRIMMING")
    enable_duplicate_removal: bool = Field(default=True, env="NGS_ENABLE_DUPLICATE_REMOVAL")
    enable_alignment: bool = Field(default=True, env="NGS_ENABLE_ALIGNMENT")
    enable_variant_calling: bool = Field(default=True, env="NGS_ENABLE_VARIANT_CALLING")


class DockerSettings(BaseSettings):
    """Docker configuration settings."""
    
    # Docker registry and image settings
    registry: str = Field(default="localhost:5000", env="DOCKER_REGISTRY")
    image_prefix: str = Field(default="cancer-genomics", env="DOCKER_IMAGE_PREFIX")
    network: str = Field(default="cancer-genomics-network", env="DOCKER_NETWORK")
    volume_prefix: str = Field(default="cancer-genomics-data", env="DOCKER_VOLUME_PREFIX")
    
    # Container settings
    default_memory_limit: str = Field(default="4g", env="DOCKER_MEMORY_LIMIT")
    default_cpu_limit: str = Field(default="2", env="DOCKER_CPU_LIMIT")
    default_timeout: int = Field(default=3600, env="DOCKER_TIMEOUT")
    
    # Security settings
    enable_privileged_mode: bool = Field(default=False, env="DOCKER_PRIVILEGED_MODE")
    enable_network_isolation: bool = Field(default=True, env="DOCKER_NETWORK_ISOLATION")
    enable_resource_limits: bool = Field(default=True, env="DOCKER_RESOURCE_LIMITS")


class JobQueueSettings(BaseSettings):
    """Job queue configuration settings."""
    
    # Queue type and backend
    queue_type: str = Field(default="redis", env="JOB_QUEUE_TYPE")
    max_retries: int = Field(default=3, env="JOB_QUEUE_MAX_RETRIES")
    retry_delay: int = Field(default=60, env="JOB_QUEUE_RETRY_DELAY")
    timeout: int = Field(default=3600, env="JOB_QUEUE_TIMEOUT")
    concurrency: int = Field(default=4, env="JOB_QUEUE_CONCURRENCY")
    
    # Queue management
    enable_priority_queues: bool = Field(default=True, env="JOB_QUEUE_ENABLE_PRIORITY")
    enable_dead_letter_queue: bool = Field(default=True, env="JOB_QUEUE_ENABLE_DLQ")
    enable_monitoring: bool = Field(default=True, env="JOB_QUEUE_ENABLE_MONITORING")
    
    # Job persistence
    enable_job_persistence: bool = Field(default=True, env="JOB_QUEUE_ENABLE_PERSISTENCE")
    job_retention_hours: int = Field(default=168, env="JOB_QUEUE_RETENTION_HOURS")  # 7 days


class AlertSettings(BaseSettings):
    """Alert and notification configuration settings."""
    
    # Email alerts
    email_enabled: bool = Field(default=True, env="ALERT_EMAIL_ENABLED")
    email_retry_attempts: int = Field(default=3, env="ALERT_EMAIL_RETRY_ATTEMPTS")
    email_retry_delay: int = Field(default=30, env="ALERT_EMAIL_RETRY_DELAY")
    
    # Slack alerts
    slack_enabled: bool = Field(default=True, env="ALERT_SLACK_ENABLED")
    slack_webhook_url: Optional[str] = Field(default=None, env="SLACK_WEBHOOK_URL")
    slack_channel: str = Field(default="#alerts", env="SLACK_ALERT_CHANNEL")
    slack_username: str = Field(default="Cancer Genomics Bot", env="SLACK_BOT_USERNAME")
    slack_icon_emoji: str = Field(default=":dna:", env="SLACK_BOT_ICON")
    
    # Teams alerts
    teams_enabled: bool = Field(default=True, env="ALERT_TEAMS_ENABLED")
    teams_webhook_url: Optional[str] = Field(default=None, env="TEAMS_WEBHOOK_URL")
    teams_title: str = Field(default="Cancer Genomics Alert", env="TEAMS_ALERT_TITLE")
    
    # General alert settings
    retry_attempts: int = Field(default=3, env="ALERT_RETRY_ATTEMPTS")
    retry_delay: int = Field(default=30, env="ALERT_RETRY_DELAY")
    enable_alert_aggregation: bool = Field(default=True, env="ALERT_ENABLE_AGGREGATION")
    alert_aggregation_window: int = Field(default=300, env="ALERT_AGGREGATION_WINDOW")  # 5 minutes
    
    # Alert severity levels
    critical_alerts_enabled: bool = Field(default=True, env="ALERT_CRITICAL_ENABLED")
    warning_alerts_enabled: bool = Field(default=True, env="ALERT_WARNING_ENABLED")
    info_alerts_enabled: bool = Field(default=False, env="ALERT_INFO_ENABLED")


class PipelineOrchestrationSettings(BaseSettings):
    """Pipeline orchestration configuration settings."""
    
    # Nextflow settings
    nextflow_enabled: bool = Field(default=True, env="NEXTFLOW_ENABLED")
    nextflow_executable: str = Field(default="nextflow", env="NEXTFLOW_EXECUTABLE")
    nextflow_work_dir: str = Field(default="nextflow_work", env="NEXTFLOW_WORK_DIR")
    nextflow_cache_dir: str = Field(default="nextflow_cache", env="NEXTFLOW_CACHE_DIR")
    nextflow_config_file: Optional[str] = Field(default=None, env="NEXTFLOW_CONFIG_FILE")
    
    # Snakemake settings
    snakemake_enabled: bool = Field(default=True, env="SNAKEMAKE_ENABLED")
    snakemake_executable: str = Field(default="snakemake", env="SNAKEMAKE_EXECUTABLE")
    snakemake_work_dir: str = Field(default="snakemake_work", env="SNAKEMAKE_WORK_DIR")
    snakemake_config_file: Optional[str] = Field(default=None, env="SNAKEMAKE_CONFIG_FILE")
    
    # Pipeline execution settings
    max_concurrent_pipelines: int = Field(default=5, env="MAX_CONCURRENT_PIPELINES")
    pipeline_timeout: int = Field(default=7200, env="PIPELINE_TIMEOUT")  # 2 hours
    enable_pipeline_monitoring: bool = Field(default=True, env="ENABLE_PIPELINE_MONITORING")
    
    # Resource management
    default_memory_limit: str = Field(default="8GB", env="DEFAULT_MEMORY_LIMIT")
    default_cpu_limit: int = Field(default=4, env="DEFAULT_CPU_LIMIT")
    enable_resource_tracking: bool = Field(default=True, env="ENABLE_RESOURCE_TRACKING")


class GraphAnalyticsSettings(BaseSettings):
    """Graph analytics configuration settings."""
    
    # Neo4j settings
    neo4j_enabled: bool = Field(default=True, env="NEO4J_ENABLED")
    neo4j_uri: str = Field(default="bolt://localhost:7687", env="NEO4J_URI")
    neo4j_username: str = Field(default="neo4j", env="NEO4J_USERNAME")
    neo4j_password: str = Field(default="password", env="NEO4J_PASSWORD")
    neo4j_database: str = Field(default="neo4j", env="NEO4J_DATABASE")
    
    # NetworkX settings
    networkx_enabled: bool = Field(default=True, env="NETWORKX_ENABLED")
    networkx_cache_size: int = Field(default=1000, env="NETWORKX_CACHE_SIZE")
    networkx_parallel_processing: bool = Field(default=True, env="NETWORKX_PARALLEL_PROCESSING")
    
    # Graph visualization settings
    enable_interactive_visualization: bool = Field(default=True, env="ENABLE_INTERACTIVE_VISUALIZATION")
    max_nodes_for_visualization: int = Field(default=10000, env="MAX_NODES_FOR_VISUALIZATION")
    visualization_export_formats: List[str] = Field(default=["png", "svg", "html"], env="VISUALIZATION_EXPORT_FORMATS")
    
    # Graph analysis settings
    enable_centrality_analysis: bool = Field(default=True, env="ENABLE_CENTRALITY_ANALYSIS")
    enable_community_detection: bool = Field(default=True, env="ENABLE_COMMUNITY_DETECTION")
    enable_pathway_analysis: bool = Field(default=True, env="ENABLE_PATHWAY_ANALYSIS")


class KafkaSettings(BaseSettings):
    """Apache Kafka configuration settings."""
    
    # Kafka connection settings
    kafka_enabled: bool = Field(default=False, env="KAFKA_ENABLED")
    kafka_bootstrap_servers: List[str] = Field(default=["localhost:9092"], env="KAFKA_BOOTSTRAP_SERVERS")
    kafka_client_id: str = Field(default="cancer_genomics_kafka", env="KAFKA_CLIENT_ID")
    kafka_security_protocol: str = Field(default="PLAINTEXT", env="KAFKA_SECURITY_PROTOCOL")
    
    # Kafka producer settings
    kafka_producer_acks: str = Field(default="all", env="KAFKA_PRODUCER_ACKS")
    kafka_producer_retries: int = Field(default=3, env="KAFKA_PRODUCER_RETRIES")
    kafka_producer_batch_size: int = Field(default=16384, env="KAFKA_PRODUCER_BATCH_SIZE")
    kafka_producer_linger_ms: int = Field(default=10, env="KAFKA_PRODUCER_LINGER_MS")
    
    # Kafka consumer settings
    kafka_consumer_group_id: str = Field(default="cancer_genomics_group", env="KAFKA_CONSUMER_GROUP_ID")
    kafka_consumer_auto_offset_reset: str = Field(default="earliest", env="KAFKA_CONSUMER_AUTO_OFFSET_RESET")
    kafka_consumer_enable_auto_commit: bool = Field(default=True, env="KAFKA_CONSUMER_ENABLE_AUTO_COMMIT")
    kafka_consumer_max_poll_records: int = Field(default=500, env="KAFKA_CONSUMER_MAX_POLL_RECORDS")
    
    # Kafka topics
    kafka_data_topic: str = Field(default="genomics_data", env="KAFKA_DATA_TOPIC")
    kafka_results_topic: str = Field(default="analysis_results", env="KAFKA_RESULTS_TOPIC")
    kafka_alerts_topic: str = Field(default="alerts", env="KAFKA_ALERTS_TOPIC")
    
    # Kafka streaming settings
    enable_stream_processing: bool = Field(default=True, env="ENABLE_STREAM_PROCESSING")
    stream_processing_parallelism: int = Field(default=4, env="STREAM_PROCESSING_PARALLELISM")
    stream_processing_timeout: int = Field(default=300, env="STREAM_PROCESSING_TIMEOUT")


class OAuth2Settings(BaseSettings):
    """OAuth2 authentication configuration settings."""
    
    # OAuth2 general settings
    oauth2_enabled: bool = Field(default=True, env="OAUTH2_ENABLED")
    oauth2_base_url: str = Field(default="http://localhost:5000", env="OAUTH2_BASE_URL")
    oauth2_session_timeout: int = Field(default=3600, env="OAUTH2_SESSION_TIMEOUT")  # 1 hour
    oauth2_csrf_protection: bool = Field(default=True, env="OAUTH2_CSRF_PROTECTION")
    
    # Keycloak settings
    keycloak_enabled: bool = Field(default=False, env="KEYCLOAK_ENABLED")
    keycloak_server_url: str = Field(default="http://localhost:8080", env="KEYCLOAK_SERVER_URL")
    keycloak_realm: str = Field(default="cancer-genomics", env="KEYCLOAK_REALM")
    keycloak_client_id: str = Field(default="cancer-genomics-app", env="KEYCLOAK_CLIENT_ID")
    keycloak_client_secret: str = Field(default="", env="KEYCLOAK_CLIENT_SECRET")
    
    # Auth0 settings
    auth0_enabled: bool = Field(default=False, env="AUTH0_ENABLED")
    auth0_domain: str = Field(default="", env="AUTH0_DOMAIN")
    auth0_client_id: str = Field(default="", env="AUTH0_CLIENT_ID")
    auth0_client_secret: str = Field(default="", env="AUTH0_CLIENT_SECRET")
    
    # JWT token settings
    jwt_secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32), env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expiry: int = Field(default=3600, env="JWT_ACCESS_TOKEN_EXPIRY")  # 1 hour
    jwt_refresh_token_expiry: int = Field(default=604800, env="JWT_REFRESH_TOKEN_EXPIRY")  # 7 days
    
    # User management settings
    user_registration_enabled: bool = Field(default=True, env="USER_REGISTRATION_ENABLED")
    user_email_verification_required: bool = Field(default=False, env="USER_EMAIL_VERIFICATION_REQUIRED")
    max_tokens_per_user: int = Field(default=5, env="MAX_TOKENS_PER_USER")
    token_rotation_enabled: bool = Field(default=True, env="TOKEN_ROTATION_ENABLED")


# Simple configuration class for fallback when Pydantic is not available
class SimpleConfig:
    """Simple configuration class for basic functionality."""
    
    def __init__(self):
        # General
        self.APP_NAME = os.getenv("APP_NAME", "Cancer Genomics Analysis Suite")
        self.DEBUG = os.getenv("DEBUG", "False").lower() == "true"
        self.ENV = os.getenv("ENV", "development")
        self.FLASK_ENV = os.getenv("FLASK_ENV", "development")
        self.DASH_DEBUG_MODE = os.getenv("DASH_DEBUG_MODE", "True").lower() == "true"
        self.HOST = os.getenv("HOST", "0.0.0.0")
        self.PORT = int(os.getenv("PORT", "8050"))
        self.APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
        
        # Database
        self.SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///cancer_genomics.db")
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        
        # Celery
        self.CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
        self.CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
        
        # Auth
        self.SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
        
        # External API Tokens
        self.COSMIC_API_TOKEN = os.getenv("COSMIC_API_TOKEN", "")
        self.COSMIC_API_KEY = os.getenv("COSMIC_API_KEY", "")
        self.SCOPUS_API_KEY = os.getenv("SCOPUS_API_KEY", "")
        self.ENCODE_API_BASE = os.getenv("ENCODE_API_BASE", "https://www.encodeproject.org")
        self.NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")
        
        # Feature flags
        self.ENABLE_GENE_EXPRESSION_ANALYSIS = os.getenv("ENABLE_GENE_EXPRESSION_ANALYSIS", "True").lower() == "true"
        self.ENABLE_MUTATION_ANALYSIS = os.getenv("ENABLE_MUTATION_ANALYSIS", "True").lower() == "true"
        self.ENABLE_MACHINE_LEARNING = os.getenv("ENABLE_MACHINE_LEARNING", "True").lower() == "true"
        self.ENABLE_PATHWAY_ANALYSIS = os.getenv("ENABLE_PATHWAY_ANALYSIS", "True").lower() == "true"
        self.ENABLE_MULTI_OMICS_INTEGRATION = os.getenv("ENABLE_MULTI_OMICS_INTEGRATION", "True").lower() == "true"
        
        # Testing
        self.TESTING = os.getenv("TESTING", "False").lower() == "true"
        
        # Create nested objects for compatibility
        self.database = type('Database', (), {
            'url': self.SQLALCHEMY_DATABASE_URI,
            'pool_size': int(os.getenv("DB_POOL_SIZE", "10")),
            'max_overflow': int(os.getenv("DB_MAX_OVERFLOW", "20")),
            'pool_timeout': int(os.getenv("DB_POOL_TIMEOUT", "30")),
            'pool_recycle': int(os.getenv("DB_POOL_RECYCLE", "3600"))
        })()
        
        self.security = type('Security', (), {
            'secret_key': self.SECRET_KEY,
            'enable_authentication': True,
            'session_cookie_secure': os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true",
            'session_cookie_httponly': os.getenv("SESSION_COOKIE_HTTPONLY", "True").lower() == "true",
            'session_cookie_samesite': os.getenv("SESSION_COOKIE_SAMESITE", "Lax"),
            'permanent_session_lifetime': int(os.getenv("PERMANENT_SESSION_LIFETIME", "86400")),
            'cors_origins': os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS") else ["*"],
            'cors_methods': os.getenv("CORS_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(","),
            'cors_headers': os.getenv("CORS_HEADERS", "Content-Type,Authorization").split(",")
        })()
        
        self.external_apis = type('ExternalAPIs', (), {
            'cosmic_api_key': self.COSMIC_API_KEY,
            'cosmic_api_token': self.COSMIC_API_TOKEN,
            'scopus_api_key': self.SCOPUS_API_KEY,
            'encode_api_base': self.ENCODE_API_BASE,
            'ncbi_api_key': self.NCBI_API_KEY
        })()
        
        self.features = type('Features', (), {
            'enable_gene_expression_analysis': self.ENABLE_GENE_EXPRESSION_ANALYSIS,
            'enable_mutation_analysis': self.ENABLE_MUTATION_ANALYSIS,
            'enable_machine_learning': self.ENABLE_MACHINE_LEARNING,
            'enable_pathway_analysis': self.ENABLE_PATHWAY_ANALYSIS,
            'enable_multi_omics_integration': self.ENABLE_MULTI_OMICS_INTEGRATION
        })()
        
        self.logging = type('Logging', (), {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file': None
        })()
        
        # File storage settings
        self.file_storage = type('FileStorage', (), {
            'upload_folder': os.getenv("UPLOAD_FOLDER", "uploads"),
            'max_content_length': int(os.getenv("MAX_CONTENT_LENGTH", "1073741824")),
            'enable_cloud_storage': os.getenv("ENABLE_CLOUD_STORAGE", "False").lower() == "true"
        })()
        
        # Redis settings
        self.redis = type('Redis', (), {
            'enabled': os.getenv("ENABLE_REDIS", "False").lower() == "true",
            'url': os.getenv("REDIS_URL", "redis://localhost:6379/0")
        })()
        
        # Celery settings
        self.celery = type('Celery', (), {
            'broker_url': self.CELERY_BROKER_URL,
            'result_backend': self.CELERY_RESULT_BACKEND,
            'task_serializer': os.getenv("CELERY_TASK_SERIALIZER", "json"),
            'accept_content': ["json"],
            'result_serializer': os.getenv("CELERY_RESULT_SERIALIZER", "json"),
            'timezone': os.getenv("CELERY_TIMEZONE", "UTC"),
            'enable_utc': os.getenv("CELERY_ENABLE_UTC", "True").lower() == "true",
            'worker_concurrency': int(os.getenv("CELERY_WORKER_CONCURRENCY", "4")),
            'worker_prefetch_multiplier': int(os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", "1")),
            'task_acks_late': os.getenv("CELERY_TASK_ACKS_LATE", "True").lower() == "true",
            'worker_max_tasks_per_child': int(os.getenv("CELERY_WORKER_MAX_TASKS_PER_CHILD", "1000")),
            'task_soft_time_limit': int(os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", "3600")),
            'task_time_limit': int(os.getenv("CELERY_TASK_TIME_LIMIT", "7200"))
        })()
    
    @property
    def app_name(self):
        return self.APP_NAME
    
    @property
    def app_version(self):
        return self.APP_VERSION
    
    @property
    def flask_env(self):
        return self.FLASK_ENV
    
    @property
    def dash_debug_mode(self):
        return self.DASH_DEBUG_MODE
    
    @property
    def host(self):
        return self.HOST
    
    @property
    def port(self):
        return self.PORT
    
    @property
    def testing(self):
        return self.TESTING
    
    def is_development(self):
        return self.FLASK_ENV.lower() == "development"
    
    def is_production(self):
        return self.FLASK_ENV.lower() == "production"
    
    def is_testing(self):
        return self.TESTING
    
    def get_database_url(self):
        return self.SQLALCHEMY_DATABASE_URI
    
    def get_redis_url(self):
        return None  # Simple config doesn't support Redis by default
    
    def get_feature_status(self, feature_name):
        return getattr(self.features, feature_name, False)


if PYDANTIC_AVAILABLE:
    class Settings(BaseSettings):
        """Main application settings with Pydantic validation."""
        
        # Application configuration
        flask_env: str = Field(default="development", env="FLASK_ENV")
        dash_debug_mode: bool = Field(default=True, env="DASH_DEBUG_MODE")
        host: str = Field(default="0.0.0.0", env="HOST")
        port: int = Field(default=8050, env="PORT")
        app_name: str = Field(default="Cancer Genomics Analysis Suite", env="APP_NAME")
        app_version: str = Field(default="1.0.0", env="APP_VERSION")
        
        # Development and testing
        testing: bool = Field(default=False, env="TESTING")
        flask_debug: bool = Field(default=True, env="FLASK_DEBUG")
        reloader_enabled: bool = Field(default=True, env="RELOADER_ENABLED")
        debug_toolbar_enabled: bool = Field(default=False, env="DEBUG_TOOLBAR_ENABLED")
        
        # Mock services for testing
        mock_external_apis: bool = Field(default=False, env="MOCK_EXTERNAL_APIS")
        mock_email_service: bool = Field(default=False, env="MOCK_EMAIL_SERVICE")
        
        # Sub-configurations
        database: DatabaseSettings = Field(default_factory=DatabaseSettings)
        redis: RedisSettings = Field(default_factory=RedisSettings)
        celery: CelerySettings = Field(default_factory=CelerySettings)
        email: EmailSettings = Field(default_factory=EmailSettings)
        file_storage: FileStorageSettings = Field(default_factory=FileStorageSettings)
        security: SecuritySettings = Field(default_factory=SecuritySettings)
        external_apis: ExternalAPISettings = Field(default_factory=ExternalAPISettings)
        analysis: AnalysisSettings = Field(default_factory=AnalysisSettings)
        logging: LoggingSettings = Field(default_factory=LoggingSettings)
        monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
        features: FeatureFlags = Field(default_factory=FeatureFlags)
        data_processing: DataProcessingSettings = Field(default_factory=DataProcessingSettings)
        compliance: ComplianceSettings = Field(default_factory=ComplianceSettings)
        ngs_platform: NGSPlatformSettings = Field(default_factory=NGSPlatformSettings)
        docker: DockerSettings = Field(default_factory=DockerSettings)
        job_queue: JobQueueSettings = Field(default_factory=JobQueueSettings)
        alerts: AlertSettings = Field(default_factory=AlertSettings)
        pipeline_orchestration: PipelineOrchestrationSettings = Field(default_factory=PipelineOrchestrationSettings)
        graph_analytics: GraphAnalyticsSettings = Field(default_factory=GraphAnalyticsSettings)
        kafka: KafkaSettings = Field(default_factory=KafkaSettings)
        oauth2: OAuth2Settings = Field(default_factory=OAuth2Settings)
        
        def get_database_url(self) -> str:
            """Get database URL for current environment."""
            if self.testing and self.database.test_url:
                return self.database.test_url
            return self.database.url
        
        def get_redis_url(self) -> Optional[str]:
            """Get Redis URL for current environment."""
            if not self.redis.enabled:
                return None
            
            if self.testing and self.redis.test_url:
                return self.redis.test_url
            return self.redis.url
        
        def is_development(self) -> bool:
            """Check if running in development mode."""
            return self.flask_env.lower() == "development"
        
        def is_production(self) -> bool:
            """Check if running in production mode."""
            return self.flask_env.lower() == "production"
        
        def is_testing(self) -> bool:
            """Check if running in testing mode."""
            return self.testing
        
        def get_feature_status(self, feature_name: str) -> bool:
            """Get status of a specific feature flag."""
            return getattr(self.features, feature_name, False)
        
        def to_dict(self) -> Dict[str, Any]:
            """Convert settings to dictionary."""
            return {
                "app_name": self.app_name,
                "app_version": self.app_version,
                "flask_env": self.flask_env,
                "host": self.host,
                "port": self.port,
                "testing": self.testing,
                "features": {
                    "gene_expression_analysis": self.features.enable_gene_expression_analysis,
                    "mutation_analysis": self.features.enable_mutation_analysis,
                    "machine_learning": self.features.enable_machine_learning,
                    "pathway_analysis": self.features.enable_pathway_analysis,
                    "multi_omics_integration": self.features.enable_multi_omics_integration,
                },
                "external_services": {
                    "redis_enabled": self.redis.enabled,
                    "email_enabled": self.email.enabled,
                    "cloud_storage_enabled": self.file_storage.enable_cloud_storage,
                }
            }
        
        if PYDANTIC_VERSION == 2 and ConfigDict is not None:
            # Pydantic v2 uses model_config
            model_config = ConfigDict(
                env_file=".env",
                env_file_encoding="utf-8",
                case_sensitive=False,
                validate_assignment=True,
                extra="ignore"  # Ignore extra environment variables (they're used by nested settings)
            )
        else:
            # Pydantic v1 uses nested Config class
            class Config:
                env_file = ".env"
                env_file_encoding = "utf-8"
                case_sensitive = False
                validate_assignment = True
                extra = "ignore"  # Ignore extra environment variables (they're used by nested settings)
else:
    # Use simple configuration when Pydantic is not available
    Settings = SimpleConfig


class TestConfig(SimpleConfig):
    """Test configuration with sensible defaults for testing."""
    
    def __init__(self):
        super().__init__()
        # Override with test-specific settings
        self.TESTING = True
        self.DEBUG = True
        self.ENV = "testing"
        self.FLASK_ENV = "testing"
        
        # Use in-memory SQLite for tests
        self.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        self.database.url = "sqlite:///:memory:"
        
        # Disable external services
        self.ENABLE_REDIS = False
        self.redis.enabled = False
        
        # Use test secret key
        self.SECRET_KEY = "test-secret-key-for-testing-only"
        
        # Disable email
        if hasattr(self, 'email'):
            self.email.enabled = False
        
        # Mock external APIs
        self.MOCK_EXTERNAL_APIS = True
        
        # Fast celery settings for testing
        self.celery.task_always_eager = True
        self.celery.task_eager_propagates = True

        # Flask app.config keys used by create_app (from_object reads uppercase attrs).
        # Under pytest, conftest sets CGAS_TEST_UPLOAD_FOLDER via tmp_path_factory (one dir per session).
        upload_override = os.environ.get("CGAS_TEST_UPLOAD_FOLDER")
        if upload_override:
            self.UPLOAD_FOLDER = str(Path(upload_override).resolve())
        else:
            self.UPLOAD_FOLDER = str(Path(tempfile.mkdtemp(prefix="cgas_test_upload_")).resolve())
        self.file_storage.upload_folder = self.UPLOAD_FOLDER
        self.MAX_CONTENT_LENGTH = self.file_storage.max_content_length


# Create global settings instance
try:
    settings = Settings()
except Exception as e:
    logger.error(f"Failed to create settings instance: {e}")
    # Fallback to simple configuration
    settings = SimpleConfig()

# Configure logging
def configure_logging():
    """Configure application logging based on settings."""
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": settings.logging.format,
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.logging.level,
                "formatter": "default",
                "stream": "ext://sys.stdout"
            }
        },
        "root": {
            "level": settings.logging.level,
            "handlers": ["console"]
        }
    }
    
    # Add file handler if log file is specified
    if settings.logging.file:
        log_config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": settings.logging.level,
            "formatter": "default",
            "filename": settings.logging.file,
            "maxBytes": settings.logging.max_size,
            "backupCount": settings.logging.backup_count
        }
        log_config["root"]["handlers"].append("file")
    
    import logging.config
    logging.config.dictConfig(log_config)
    
    logger.info(f"Logging configured for {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.flask_env}")
    logger.info(f"Debug mode: {settings.dash_debug_mode}")


# Initialize logging
configure_logging()

# Export settings instance
__all__ = ["settings", "configure_logging", "Settings", "SimpleConfig", "TestConfig"]
