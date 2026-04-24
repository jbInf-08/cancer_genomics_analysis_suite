-- Cancer Genomics Analysis Suite Database Schema
-- This file provides a reference for the database schema used by the application

-- Users table (from auth package)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(120) UNIQUE,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    is_active BOOLEAN DEFAULT 1,
    is_admin BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME
);

-- Analysis Jobs table
CREATE TABLE IF NOT EXISTS analysis_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(100) UNIQUE NOT NULL,
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    user_id INTEGER,
    input_data TEXT,
    results TEXT,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Data Files table
CREATE TABLE IF NOT EXISTS data_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size INTEGER NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    user_id INTEGER,
    upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_processed BOOLEAN DEFAULT 0,
    metadata TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Gene Expression table
CREATE TABLE IF NOT EXISTS gene_expression (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gene_symbol VARCHAR(50) NOT NULL,
    gene_id VARCHAR(50),
    sample_id VARCHAR(100) NOT NULL,
    expression_value REAL NOT NULL,
    expression_unit VARCHAR(20) DEFAULT 'FPKM',
    condition VARCHAR(100),
    tissue_type VARCHAR(100),
    cell_line VARCHAR(100),
    treatment VARCHAR(100),
    time_point VARCHAR(50),
    replicate INTEGER,
    batch_id VARCHAR(50),
    quality_score REAL,
    is_normalized BOOLEAN DEFAULT 0,
    normalization_method VARCHAR(50),
    data_file_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (data_file_id) REFERENCES data_files (id),
    CHECK (expression_value >= 0)
);

-- Mutation Records table
CREATE TABLE IF NOT EXISTS mutation_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gene VARCHAR(100) NOT NULL,
    gene_id VARCHAR(50),
    variant VARCHAR(100) NOT NULL,
    variant_type VARCHAR(50),
    chromosome VARCHAR(10),
    position INTEGER,
    ref_allele VARCHAR(10),
    alt_allele VARCHAR(10),
    sample_id VARCHAR(100) NOT NULL,
    effect VARCHAR(255),
    effect_prediction VARCHAR(100),
    clinical_significance VARCHAR(100),
    pathogenicity VARCHAR(50),
    allele_frequency REAL,
    read_depth INTEGER,
    quality_score REAL,
    source VARCHAR(50),
    source_id VARCHAR(100),
    cancer_type VARCHAR(100),
    tissue_type VARCHAR(100),
    cell_line VARCHAR(100),
    treatment_response VARCHAR(100),
    drug_sensitivity VARCHAR(100),
    functional_impact VARCHAR(100),
    protein_domain VARCHAR(100),
    data_file_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (data_file_id) REFERENCES data_files (id),
    CHECK (allele_frequency >= 0 AND allele_frequency <= 1),
    CHECK (read_depth >= 0)
);

-- Analysis Results table
CREATE TABLE IF NOT EXISTS analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    result_type VARCHAR(50) NOT NULL,
    result_name VARCHAR(200),
    result_data TEXT NOT NULL,
    file_path VARCHAR(500),
    file_size INTEGER,
    mime_type VARCHAR(100),
    is_public BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    tags TEXT,
    version VARCHAR(20) DEFAULT '1.0',
    is_valid BOOLEAN DEFAULT 1,
    validation_errors TEXT,
    FOREIGN KEY (job_id) REFERENCES analysis_jobs (id)
);

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    project_id VARCHAR(100) UNIQUE NOT NULL,
    owner_id INTEGER NOT NULL,
    is_public BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    settings TEXT,
    tags TEXT,
    FOREIGN KEY (owner_id) REFERENCES users (id)
);

-- Datasets table
CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    dataset_id VARCHAR(100) UNIQUE NOT NULL,
    project_id VARCHAR(100),
    owner_id INTEGER NOT NULL,
    is_public BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,
    tags TEXT,
    FOREIGN KEY (project_id) REFERENCES projects (project_id),
    FOREIGN KEY (owner_id) REFERENCES users (id)
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_gene_expression_gene_symbol ON gene_expression (gene_symbol);
CREATE INDEX IF NOT EXISTS idx_gene_expression_sample_id ON gene_expression (sample_id);
CREATE INDEX IF NOT EXISTS idx_gene_expression_condition ON gene_expression (condition);
CREATE INDEX IF NOT EXISTS idx_gene_sample ON gene_expression (gene_symbol, sample_id);
CREATE INDEX IF NOT EXISTS idx_gene_condition ON gene_expression (gene_symbol, condition);
CREATE INDEX IF NOT EXISTS idx_sample_condition ON gene_expression (sample_id, condition);

CREATE INDEX IF NOT EXISTS idx_mutation_records_gene ON mutation_records (gene);
CREATE INDEX IF NOT EXISTS idx_mutation_records_variant ON mutation_records (variant);
CREATE INDEX IF NOT EXISTS idx_mutation_records_sample_id ON mutation_records (sample_id);
CREATE INDEX IF NOT EXISTS idx_mutation_records_clinical_significance ON mutation_records (clinical_significance);
CREATE INDEX IF NOT EXISTS idx_mutation_records_source ON mutation_records (source);
CREATE INDEX IF NOT EXISTS idx_mutation_records_cancer_type ON mutation_records (cancer_type);
CREATE INDEX IF NOT EXISTS idx_gene_variant ON mutation_records (gene, variant);
CREATE INDEX IF NOT EXISTS idx_sample_gene ON mutation_records (sample_id, gene);
CREATE INDEX IF NOT EXISTS idx_chromosome_position ON mutation_records (chromosome, position);
CREATE INDEX IF NOT EXISTS idx_clinical_significance ON mutation_records (clinical_significance, pathogenicity);

CREATE INDEX IF NOT EXISTS idx_analysis_jobs_job_id ON analysis_jobs (job_id);
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_job_type ON analysis_jobs (job_type);
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_status ON analysis_jobs (status);
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_user_id ON analysis_jobs (user_id);
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_created_at ON analysis_jobs (created_at);
CREATE INDEX IF NOT EXISTS idx_job_type_status ON analysis_jobs (job_type, status);
CREATE INDEX IF NOT EXISTS idx_user_status ON analysis_jobs (user_id, status);
CREATE INDEX IF NOT EXISTS idx_created_at_status ON analysis_jobs (created_at, status);

CREATE INDEX IF NOT EXISTS idx_data_files_filename ON data_files (filename);
CREATE INDEX IF NOT EXISTS idx_data_files_file_type ON data_files (file_type);
CREATE INDEX IF NOT EXISTS idx_data_files_user_id ON data_files (user_id);
CREATE INDEX IF NOT EXISTS idx_data_files_upload_date ON data_files (upload_date);
CREATE INDEX IF NOT EXISTS idx_data_files_is_processed ON data_files (is_processed);
CREATE INDEX IF NOT EXISTS idx_file_type_status ON data_files (file_type, processing_status);
CREATE INDEX IF NOT EXISTS idx_user_upload_date ON data_files (user_id, upload_date);
CREATE INDEX IF NOT EXISTS idx_project_dataset ON data_files (project_id, dataset_id);

CREATE INDEX IF NOT EXISTS idx_analysis_results_job_id ON analysis_results (job_id);
CREATE INDEX IF NOT EXISTS idx_analysis_results_result_type ON analysis_results (result_type);
CREATE INDEX IF NOT EXISTS idx_analysis_results_created_at ON analysis_results (created_at);
CREATE INDEX IF NOT EXISTS idx_job_result_type ON analysis_results (job_id, result_type);
CREATE INDEX IF NOT EXISTS idx_result_type_created ON analysis_results (result_type, created_at);
CREATE INDEX IF NOT EXISTS idx_is_public_created ON analysis_results (is_public, created_at);

CREATE INDEX IF NOT EXISTS idx_projects_name ON projects (name);
CREATE INDEX IF NOT EXISTS idx_projects_project_id ON projects (project_id);
CREATE INDEX IF NOT EXISTS idx_projects_owner_id ON projects (owner_id);

CREATE INDEX IF NOT EXISTS idx_datasets_name ON datasets (name);
CREATE INDEX IF NOT EXISTS idx_datasets_dataset_id ON datasets (dataset_id);
CREATE INDEX IF NOT EXISTS idx_datasets_project_id ON datasets (project_id);
CREATE INDEX IF NOT EXISTS idx_datasets_owner_id ON datasets (owner_id);

CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users (is_active);

-- NGS Platform Support Tables
CREATE TABLE IF NOT EXISTS ngs_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id VARCHAR(100) UNIQUE NOT NULL,
    sample_name VARCHAR(200) NOT NULL,
    sample_type VARCHAR(50) NOT NULL, -- 'tumor', 'normal', 'cell_line', etc.
    platform VARCHAR(50) NOT NULL, -- 'illumina', 'pacbio', 'nanopore'
    sequencing_type VARCHAR(50) NOT NULL, -- 'WGS', 'WES', 'RNA-seq', 'ChIP-seq'
    library_prep VARCHAR(100),
    read_length INTEGER,
    paired_end BOOLEAN DEFAULT 1,
    project_id VARCHAR(100),
    user_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,
    FOREIGN KEY (project_id) REFERENCES projects (project_id),
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS ngs_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id VARCHAR(100) UNIQUE NOT NULL,
    sample_id VARCHAR(100) NOT NULL,
    file_type VARCHAR(50) NOT NULL, -- 'fastq', 'bam', 'vcf', 'bcf'
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    checksum VARCHAR(64),
    quality_score REAL,
    read_count BIGINT,
    base_count BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sample_id) REFERENCES ngs_samples (sample_id)
);

CREATE TABLE IF NOT EXISTS ngs_pipelines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_id VARCHAR(100) UNIQUE NOT NULL,
    pipeline_name VARCHAR(200) NOT NULL,
    pipeline_version VARCHAR(50) NOT NULL,
    pipeline_type VARCHAR(50) NOT NULL, -- 'variant_calling', 'expression', 'methylation'
    description TEXT,
    docker_image VARCHAR(200),
    parameters TEXT, -- JSON parameters
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ngs_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(100) UNIQUE NOT NULL,
    pipeline_id VARCHAR(100) NOT NULL,
    sample_id VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    priority INTEGER DEFAULT 5,
    user_id INTEGER NOT NULL,
    input_files TEXT, -- JSON array of input files
    output_files TEXT, -- JSON array of output files
    parameters TEXT, -- JSON parameters
    docker_container_id VARCHAR(100),
    started_at DATETIME,
    completed_at DATETIME,
    error_message TEXT,
    logs TEXT,
    resource_usage TEXT, -- JSON with CPU, memory, disk usage
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pipeline_id) REFERENCES ngs_pipelines (pipeline_id),
    FOREIGN KEY (sample_id) REFERENCES ngs_samples (sample_id),
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Docker and Container Management Tables
CREATE TABLE IF NOT EXISTS docker_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_name VARCHAR(200) NOT NULL,
    image_tag VARCHAR(100) NOT NULL,
    image_id VARCHAR(100) UNIQUE NOT NULL,
    size_bytes BIGINT,
    created_at DATETIME,
    last_used DATETIME,
    is_active BOOLEAN DEFAULT 1,
    metadata TEXT,
    UNIQUE(image_name, image_tag)
);

CREATE TABLE IF NOT EXISTS docker_containers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    container_id VARCHAR(100) UNIQUE NOT NULL,
    container_name VARCHAR(200),
    image_id VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL, -- 'running', 'stopped', 'exited', 'paused'
    command TEXT,
    environment TEXT, -- JSON environment variables
    volumes TEXT, -- JSON volume mounts
    ports TEXT, -- JSON port mappings
    resource_limits TEXT, -- JSON resource limits
    started_at DATETIME,
    stopped_at DATETIME,
    exit_code INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (image_id) REFERENCES docker_images (image_id)
);

-- Job Queue Management Tables
CREATE TABLE IF NOT EXISTS job_queues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    queue_name VARCHAR(100) UNIQUE NOT NULL,
    queue_type VARCHAR(50) NOT NULL, -- 'redis', 'rabbitmq', 'sqs'
    priority INTEGER DEFAULT 5,
    max_retries INTEGER DEFAULT 3,
    timeout_seconds INTEGER DEFAULT 3600,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS queue_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(100) UNIQUE NOT NULL,
    queue_name VARCHAR(100) NOT NULL,
    job_type VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed', 'retry'
    priority INTEGER DEFAULT 5,
    user_id INTEGER,
    payload TEXT NOT NULL, -- JSON job data
    result TEXT, -- JSON result data
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    scheduled_at DATETIME,
    started_at DATETIME,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (queue_name) REFERENCES job_queues (queue_name),
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Alert and Notification Tables
CREATE TABLE IF NOT EXISTS alert_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_name VARCHAR(200) NOT NULL,
    rule_type VARCHAR(50) NOT NULL, -- 'threshold', 'pattern', 'anomaly'
    description TEXT,
    conditions TEXT NOT NULL, -- JSON conditions
    severity VARCHAR(20) NOT NULL, -- 'info', 'warning', 'critical'
    is_active BOOLEAN DEFAULT 1,
    created_by INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS alert_instances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id INTEGER NOT NULL,
    alert_id VARCHAR(100) UNIQUE NOT NULL,
    severity VARCHAR(20) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'acknowledged', 'resolved'
    acknowledged_by INTEGER,
    acknowledged_at DATETIME,
    resolved_at DATETIME,
    metadata TEXT, -- JSON additional data
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rule_id) REFERENCES alert_rules (id),
    FOREIGN KEY (acknowledged_by) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS notification_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_name VARCHAR(100) UNIQUE NOT NULL,
    channel_type VARCHAR(50) NOT NULL, -- 'email', 'slack', 'teams', 'webhook'
    configuration TEXT NOT NULL, -- JSON configuration
    is_active BOOLEAN DEFAULT 1,
    created_by INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS alert_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id VARCHAR(100) NOT NULL,
    channel_id INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'sent', 'failed'
    sent_at DATETIME,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (alert_id) REFERENCES alert_instances (alert_id),
    FOREIGN KEY (channel_id) REFERENCES notification_channels (id)
);

-- Email Integration Tables
CREATE TABLE IF NOT EXISTS email_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_name VARCHAR(100) UNIQUE NOT NULL,
    template_type VARCHAR(50) NOT NULL, -- 'alert', 'notification', 'report'
    subject_template TEXT NOT NULL,
    body_template TEXT NOT NULL,
    is_html BOOLEAN DEFAULT 1,
    variables TEXT, -- JSON template variables
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS email_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id VARCHAR(100) UNIQUE NOT NULL,
    recipient_email VARCHAR(200) NOT NULL,
    recipient_name VARCHAR(200),
    subject VARCHAR(500) NOT NULL,
    template_name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'sent', 'failed', 'bounced'
    sent_at DATETIME,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    metadata TEXT, -- JSON additional data
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (template_name) REFERENCES email_templates (template_name)
);

-- System Monitoring Tables
CREATE TABLE IF NOT EXISTS system_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name VARCHAR(100) NOT NULL,
    metric_type VARCHAR(50) NOT NULL, -- 'counter', 'gauge', 'histogram'
    value REAL NOT NULL,
    labels TEXT, -- JSON labels
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_metric_name_time (metric_name, timestamp),
    INDEX idx_metric_type_time (metric_type, timestamp)
);

CREATE TABLE IF NOT EXISTS health_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_name VARCHAR(100) NOT NULL,
    check_type VARCHAR(50) NOT NULL, -- 'database', 'redis', 'api', 'disk', 'memory'
    status VARCHAR(20) NOT NULL, -- 'healthy', 'unhealthy', 'degraded'
    response_time_ms INTEGER,
    error_message TEXT,
    metadata TEXT, -- JSON additional data
    checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_check_name_time (check_name, checked_at),
    INDEX idx_check_type_time (check_type, checked_at)
);

-- Audit and Compliance Tables
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(100),
    old_values TEXT, -- JSON old values
    new_values TEXT, -- JSON new values
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    INDEX idx_user_action_time (user_id, action, timestamp),
    INDEX idx_resource_time (resource_type, resource_id, timestamp)
);

CREATE TABLE IF NOT EXISTS data_lineage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id VARCHAR(100) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    target_id VARCHAR(100) NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    transformation_type VARCHAR(100),
    transformation_details TEXT, -- JSON transformation details
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_source (source_id, source_type),
    INDEX idx_target (target_id, target_type)
);

-- Additional Indexes for New Tables
CREATE INDEX IF NOT EXISTS idx_ngs_samples_sample_id ON ngs_samples (sample_id);
CREATE INDEX IF NOT EXISTS idx_ngs_samples_project_id ON ngs_samples (project_id);
CREATE INDEX IF NOT EXISTS idx_ngs_samples_user_id ON ngs_samples (user_id);
CREATE INDEX IF NOT EXISTS idx_ngs_samples_platform ON ngs_samples (platform);
CREATE INDEX IF NOT EXISTS idx_ngs_samples_sequencing_type ON ngs_samples (sequencing_type);

CREATE INDEX IF NOT EXISTS idx_ngs_files_file_id ON ngs_files (file_id);
CREATE INDEX IF NOT EXISTS idx_ngs_files_sample_id ON ngs_files (sample_id);
CREATE INDEX IF NOT EXISTS idx_ngs_files_file_type ON ngs_files (file_type);

CREATE INDEX IF NOT EXISTS idx_ngs_pipelines_pipeline_id ON ngs_pipelines (pipeline_id);
CREATE INDEX IF NOT EXISTS idx_ngs_pipelines_pipeline_type ON ngs_pipelines (pipeline_type);
CREATE INDEX IF NOT EXISTS idx_ngs_pipelines_is_active ON ngs_pipelines (is_active);

CREATE INDEX IF NOT EXISTS idx_ngs_jobs_job_id ON ngs_jobs (job_id);
CREATE INDEX IF NOT EXISTS idx_ngs_jobs_pipeline_id ON ngs_jobs (pipeline_id);
CREATE INDEX IF NOT EXISTS idx_ngs_jobs_sample_id ON ngs_jobs (sample_id);
CREATE INDEX IF NOT EXISTS idx_ngs_jobs_status ON ngs_jobs (status);
CREATE INDEX IF NOT EXISTS idx_ngs_jobs_user_id ON ngs_jobs (user_id);
CREATE INDEX IF NOT EXISTS idx_ngs_jobs_priority ON ngs_jobs (priority);

CREATE INDEX IF NOT EXISTS idx_docker_images_image_name ON docker_images (image_name);
CREATE INDEX IF NOT EXISTS idx_docker_images_image_tag ON docker_images (image_tag);
CREATE INDEX IF NOT EXISTS idx_docker_images_is_active ON docker_images (is_active);

CREATE INDEX IF NOT EXISTS idx_docker_containers_container_id ON docker_containers (container_id);
CREATE INDEX IF NOT EXISTS idx_docker_containers_image_id ON docker_containers (image_id);
CREATE INDEX IF NOT EXISTS idx_docker_containers_status ON docker_containers (status);

CREATE INDEX IF NOT EXISTS idx_job_queues_queue_name ON job_queues (queue_name);
CREATE INDEX IF NOT EXISTS idx_job_queues_queue_type ON job_queues (queue_type);
CREATE INDEX IF NOT EXISTS idx_job_queues_is_active ON job_queues (is_active);

CREATE INDEX IF NOT EXISTS idx_queue_jobs_job_id ON queue_jobs (job_id);
CREATE INDEX IF NOT EXISTS idx_queue_jobs_queue_name ON queue_jobs (queue_name);
CREATE INDEX IF NOT EXISTS idx_queue_jobs_status ON queue_jobs (status);
CREATE INDEX IF NOT EXISTS idx_queue_jobs_priority ON queue_jobs (priority);
CREATE INDEX IF NOT EXISTS idx_queue_jobs_user_id ON queue_jobs (user_id);
CREATE INDEX IF NOT EXISTS idx_queue_jobs_scheduled_at ON queue_jobs (scheduled_at);

CREATE INDEX IF NOT EXISTS idx_alert_rules_rule_name ON alert_rules (rule_name);
CREATE INDEX IF NOT EXISTS idx_alert_rules_rule_type ON alert_rules (rule_type);
CREATE INDEX IF NOT EXISTS idx_alert_rules_severity ON alert_rules (severity);
CREATE INDEX IF NOT EXISTS idx_alert_rules_is_active ON alert_rules (is_active);

CREATE INDEX IF NOT EXISTS idx_alert_instances_alert_id ON alert_instances (alert_id);
CREATE INDEX IF NOT EXISTS idx_alert_instances_rule_id ON alert_instances (rule_id);
CREATE INDEX IF NOT EXISTS idx_alert_instances_severity ON alert_instances (severity);
CREATE INDEX IF NOT EXISTS idx_alert_instances_status ON alert_instances (status);
CREATE INDEX IF NOT EXISTS idx_alert_instances_created_at ON alert_instances (created_at);

CREATE INDEX IF NOT EXISTS idx_notification_channels_channel_name ON notification_channels (channel_name);
CREATE INDEX IF NOT EXISTS idx_notification_channels_channel_type ON notification_channels (channel_type);
CREATE INDEX IF NOT EXISTS idx_notification_channels_is_active ON notification_channels (is_active);

CREATE INDEX IF NOT EXISTS idx_alert_notifications_alert_id ON alert_notifications (alert_id);
CREATE INDEX IF NOT EXISTS idx_alert_notifications_channel_id ON alert_notifications (channel_id);
CREATE INDEX IF NOT EXISTS idx_alert_notifications_status ON alert_notifications (status);

CREATE INDEX IF NOT EXISTS idx_email_templates_template_name ON email_templates (template_name);
CREATE INDEX IF NOT EXISTS idx_email_templates_template_type ON email_templates (template_type);
CREATE INDEX IF NOT EXISTS idx_email_templates_is_active ON email_templates (is_active);

CREATE INDEX IF NOT EXISTS idx_email_logs_email_id ON email_logs (email_id);
CREATE INDEX IF NOT EXISTS idx_email_logs_recipient_email ON email_logs (recipient_email);
CREATE INDEX IF NOT EXISTS idx_email_logs_status ON email_logs (status);
CREATE INDEX IF NOT EXISTS idx_email_logs_sent_at ON email_logs (sent_at);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs (action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource_type ON audit_logs (resource_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs (timestamp);

CREATE INDEX IF NOT EXISTS idx_data_lineage_source ON data_lineage (source_id, source_type);
CREATE INDEX IF NOT EXISTS idx_data_lineage_target ON data_lineage (target_id, target_type);
CREATE INDEX IF NOT EXISTS idx_data_lineage_created_at ON data_lineage (created_at);
