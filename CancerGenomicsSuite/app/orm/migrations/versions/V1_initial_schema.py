"""Initial database schema

Revision ID: V1_initial_schema
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'V1_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=120), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=True),
        sa.Column('first_name', sa.String(length=50), nullable=True),
        sa.Column('last_name', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_admin', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    
    # Create analysis_jobs table
    op.create_table('analysis_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.String(length=100), nullable=False),
        sa.Column('job_type', sa.String(length=50), nullable=False),
        sa.Column('job_name', sa.String(length=200), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('input_data', sa.Text(), nullable=True),
        sa.Column('results', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('progress', sa.Float(), nullable=True),
        sa.Column('estimated_completion', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('parameters', sa.Text(), nullable=True),
        sa.Column('output_format', sa.String(length=50), nullable=True),
        sa.Column('notification_email', sa.String(length=255), nullable=True),
        sa.Column('cpu_time', sa.Float(), nullable=True),
        sa.Column('memory_usage', sa.Float(), nullable=True),
        sa.Column('disk_usage', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id')
    )
    
    # Create data_files table
    op.create_table('data_files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('file_extension', sa.String(length=10), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('checksum', sa.String(length=64), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('upload_date', sa.DateTime(), nullable=True),
        sa.Column('is_processed', sa.Boolean(), nullable=True),
        sa.Column('processing_status', sa.String(length=50), nullable=True),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.Column('is_valid', sa.Boolean(), nullable=True),
        sa.Column('validation_errors', sa.Text(), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('record_count', sa.Integer(), nullable=True),
        sa.Column('sample_count', sa.Integer(), nullable=True),
        sa.Column('gene_count', sa.Integer(), nullable=True),
        sa.Column('processing_started_at', sa.DateTime(), nullable=True),
        sa.Column('processing_completed_at', sa.DateTime(), nullable=True),
        sa.Column('processing_duration', sa.Float(), nullable=True),
        sa.Column('project_id', sa.String(length=100), nullable=True),
        sa.Column('dataset_id', sa.String(length=100), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create projects table
    op.create_table('projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('project_id', sa.String(length=100), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('is_public', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('settings', sa.Text(), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id')
    )
    
    # Create datasets table
    op.create_table('datasets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('dataset_id', sa.String(length=100), nullable=False),
        sa.Column('project_id', sa.String(length=100), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('is_public', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dataset_id')
    )
    
    # Create gene_expression table
    op.create_table('gene_expression',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('gene_symbol', sa.String(length=50), nullable=False),
        sa.Column('gene_id', sa.String(length=50), nullable=True),
        sa.Column('sample_id', sa.String(length=100), nullable=False),
        sa.Column('expression_value', sa.Float(), nullable=False),
        sa.Column('expression_unit', sa.String(length=20), nullable=True),
        sa.Column('condition', sa.String(length=100), nullable=True),
        sa.Column('tissue_type', sa.String(length=100), nullable=True),
        sa.Column('cell_line', sa.String(length=100), nullable=True),
        sa.Column('treatment', sa.String(length=100), nullable=True),
        sa.Column('time_point', sa.String(length=50), nullable=True),
        sa.Column('replicate', sa.Integer(), nullable=True),
        sa.Column('batch_id', sa.String(length=50), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('is_normalized', sa.Boolean(), nullable=True),
        sa.Column('normalization_method', sa.String(length=50), nullable=True),
        sa.Column('data_file_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['data_file_id'], ['data_files.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create mutation_records table
    op.create_table('mutation_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('gene', sa.String(length=100), nullable=False),
        sa.Column('gene_id', sa.String(length=50), nullable=True),
        sa.Column('variant', sa.String(length=100), nullable=False),
        sa.Column('variant_type', sa.String(length=50), nullable=True),
        sa.Column('chromosome', sa.String(length=10), nullable=True),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('ref_allele', sa.String(length=10), nullable=True),
        sa.Column('alt_allele', sa.String(length=10), nullable=True),
        sa.Column('sample_id', sa.String(length=100), nullable=False),
        sa.Column('effect', sa.String(length=255), nullable=True),
        sa.Column('effect_prediction', sa.String(length=100), nullable=True),
        sa.Column('clinical_significance', sa.String(length=100), nullable=True),
        sa.Column('pathogenicity', sa.String(length=50), nullable=True),
        sa.Column('allele_frequency', sa.Float(), nullable=True),
        sa.Column('read_depth', sa.Integer(), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('source_id', sa.String(length=100), nullable=True),
        sa.Column('cancer_type', sa.String(length=100), nullable=True),
        sa.Column('tissue_type', sa.String(length=100), nullable=True),
        sa.Column('cell_line', sa.String(length=100), nullable=True),
        sa.Column('treatment_response', sa.String(length=100), nullable=True),
        sa.Column('drug_sensitivity', sa.String(length=100), nullable=True),
        sa.Column('functional_impact', sa.String(length=100), nullable=True),
        sa.Column('protein_domain', sa.String(length=100), nullable=True),
        sa.Column('data_file_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['data_file_id'], ['data_files.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create analysis_results table
    op.create_table('analysis_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('result_type', sa.String(length=50), nullable=False),
        sa.Column('result_name', sa.String(length=200), nullable=True),
        sa.Column('result_data', sa.Text(), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('version', sa.String(length=20), nullable=True),
        sa.Column('is_valid', sa.Boolean(), nullable=True),
        sa.Column('validation_errors', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['analysis_jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better performance
    # Users indexes
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_is_active', 'users', ['is_active'])
    
    # Analysis jobs indexes
    op.create_index('idx_analysis_jobs_job_id', 'analysis_jobs', ['job_id'])
    op.create_index('idx_analysis_jobs_job_type', 'analysis_jobs', ['job_type'])
    op.create_index('idx_analysis_jobs_status', 'analysis_jobs', ['status'])
    op.create_index('idx_analysis_jobs_user_id', 'analysis_jobs', ['user_id'])
    op.create_index('idx_analysis_jobs_created_at', 'analysis_jobs', ['created_at'])
    op.create_index('idx_job_type_status', 'analysis_jobs', ['job_type', 'status'])
    op.create_index('idx_user_status', 'analysis_jobs', ['user_id', 'status'])
    op.create_index('idx_created_at_status', 'analysis_jobs', ['created_at', 'status'])
    
    # Data files indexes
    op.create_index('idx_data_files_filename', 'data_files', ['filename'])
    op.create_index('idx_data_files_file_type', 'data_files', ['file_type'])
    op.create_index('idx_data_files_user_id', 'data_files', ['user_id'])
    op.create_index('idx_data_files_upload_date', 'data_files', ['upload_date'])
    op.create_index('idx_data_files_is_processed', 'data_files', ['is_processed'])
    op.create_index('idx_file_type_status', 'data_files', ['file_type', 'processing_status'])
    op.create_index('idx_user_upload_date', 'data_files', ['user_id', 'upload_date'])
    op.create_index('idx_project_dataset', 'data_files', ['project_id', 'dataset_id'])
    
    # Projects indexes
    op.create_index('idx_projects_name', 'projects', ['name'])
    op.create_index('idx_projects_project_id', 'projects', ['project_id'])
    op.create_index('idx_projects_owner_id', 'projects', ['owner_id'])
    
    # Datasets indexes
    op.create_index('idx_datasets_name', 'datasets', ['name'])
    op.create_index('idx_datasets_dataset_id', 'datasets', ['dataset_id'])
    op.create_index('idx_datasets_project_id', 'datasets', ['project_id'])
    op.create_index('idx_datasets_owner_id', 'datasets', ['owner_id'])
    
    # Gene expression indexes
    op.create_index('idx_gene_expression_gene_symbol', 'gene_expression', ['gene_symbol'])
    op.create_index('idx_gene_expression_sample_id', 'gene_expression', ['sample_id'])
    op.create_index('idx_gene_expression_condition', 'gene_expression', ['condition'])
    op.create_index('idx_gene_sample', 'gene_expression', ['gene_symbol', 'sample_id'])
    op.create_index('idx_gene_condition', 'gene_expression', ['gene_symbol', 'condition'])
    op.create_index('idx_sample_condition', 'gene_expression', ['sample_id', 'condition'])
    
    # Mutation records indexes
    op.create_index('idx_mutation_records_gene', 'mutation_records', ['gene'])
    op.create_index('idx_mutation_records_variant', 'mutation_records', ['variant'])
    op.create_index('idx_mutation_records_sample_id', 'mutation_records', ['sample_id'])
    op.create_index('idx_mutation_records_clinical_significance', 'mutation_records', ['clinical_significance'])
    op.create_index('idx_mutation_records_source', 'mutation_records', ['source'])
    op.create_index('idx_mutation_records_cancer_type', 'mutation_records', ['cancer_type'])
    op.create_index('idx_gene_variant', 'mutation_records', ['gene', 'variant'])
    op.create_index('idx_sample_gene', 'mutation_records', ['sample_id', 'gene'])
    op.create_index('idx_chromosome_position', 'mutation_records', ['chromosome', 'position'])
    op.create_index('idx_clinical_significance', 'mutation_records', ['clinical_significance', 'pathogenicity'])
    
    # Analysis results indexes
    op.create_index('idx_analysis_results_job_id', 'analysis_results', ['job_id'])
    op.create_index('idx_analysis_results_result_type', 'analysis_results', ['result_type'])
    op.create_index('idx_analysis_results_created_at', 'analysis_results', ['created_at'])
    op.create_index('idx_job_result_type', 'analysis_results', ['job_id', 'result_type'])
    op.create_index('idx_result_type_created', 'analysis_results', ['result_type', 'created_at'])
    op.create_index('idx_is_public_created', 'analysis_results', ['is_public', 'created_at'])
    
    # Create NGS Platform Support Tables
    op.create_table('ngs_samples',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sample_id', sa.String(length=100), nullable=False),
        sa.Column('sample_name', sa.String(length=200), nullable=False),
        sa.Column('sample_type', sa.String(length=50), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('sequencing_type', sa.String(length=50), nullable=False),
        sa.Column('library_prep', sa.String(length=100), nullable=True),
        sa.Column('read_length', sa.Integer(), nullable=True),
        sa.Column('paired_end', sa.Boolean(), nullable=True),
        sa.Column('project_id', sa.String(length=100), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sample_id')
    )
    
    op.create_table('ngs_files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_id', sa.String(length=100), nullable=False),
        sa.Column('sample_id', sa.String(length=100), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('checksum', sa.String(length=64), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('read_count', sa.BigInteger(), nullable=True),
        sa.Column('base_count', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['sample_id'], ['ngs_samples.sample_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_id')
    )
    
    op.create_table('ngs_pipelines',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pipeline_id', sa.String(length=100), nullable=False),
        sa.Column('pipeline_name', sa.String(length=200), nullable=False),
        sa.Column('pipeline_version', sa.String(length=50), nullable=False),
        sa.Column('pipeline_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('docker_image', sa.String(length=200), nullable=True),
        sa.Column('parameters', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('pipeline_id')
    )
    
    op.create_table('ngs_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.String(length=100), nullable=False),
        sa.Column('pipeline_id', sa.String(length=100), nullable=False),
        sa.Column('sample_id', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('input_files', sa.Text(), nullable=True),
        sa.Column('output_files', sa.Text(), nullable=True),
        sa.Column('parameters', sa.Text(), nullable=True),
        sa.Column('docker_container_id', sa.String(length=100), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('logs', sa.Text(), nullable=True),
        sa.Column('resource_usage', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['pipeline_id'], ['ngs_pipelines.pipeline_id'], ),
        sa.ForeignKeyConstraint(['sample_id'], ['ngs_samples.sample_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id')
    )
    
    # Create Docker and Container Management Tables
    op.create_table('docker_images',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('image_name', sa.String(length=200), nullable=False),
        sa.Column('image_tag', sa.String(length=100), nullable=False),
        sa.Column('image_id', sa.String(length=100), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('image_id'),
        sa.UniqueConstraint('image_name', 'image_tag')
    )
    
    op.create_table('docker_containers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('container_id', sa.String(length=100), nullable=False),
        sa.Column('container_name', sa.String(length=200), nullable=True),
        sa.Column('image_id', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('command', sa.Text(), nullable=True),
        sa.Column('environment', sa.Text(), nullable=True),
        sa.Column('volumes', sa.Text(), nullable=True),
        sa.Column('ports', sa.Text(), nullable=True),
        sa.Column('resource_limits', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('stopped_at', sa.DateTime(), nullable=True),
        sa.Column('exit_code', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['image_id'], ['docker_images.image_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('container_id')
    )
    
    # Create Job Queue Management Tables
    op.create_table('job_queues',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('queue_name', sa.String(length=100), nullable=False),
        sa.Column('queue_type', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('max_retries', sa.Integer(), nullable=True),
        sa.Column('timeout_seconds', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('queue_name')
    )
    
    op.create_table('queue_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.String(length=100), nullable=False),
        sa.Column('queue_name', sa.String(length=100), nullable=False),
        sa.Column('job_type', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('max_retries', sa.Integer(), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['queue_name'], ['job_queues.queue_name'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id')
    )
    
    # Create Alert and Notification Tables
    op.create_table('alert_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_name', sa.String(length=200), nullable=False),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('conditions', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('alert_instances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_id', sa.Integer(), nullable=False),
        sa.Column('alert_id', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('acknowledged_by', sa.Integer(), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['acknowledged_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['rule_id'], ['alert_rules.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('alert_id')
    )
    
    op.create_table('notification_channels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('channel_name', sa.String(length=100), nullable=False),
        sa.Column('channel_type', sa.String(length=50), nullable=False),
        sa.Column('configuration', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('channel_name')
    )
    
    op.create_table('alert_notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_id', sa.String(length=100), nullable=False),
        sa.Column('channel_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['alert_id'], ['alert_instances.alert_id'], ),
        sa.ForeignKeyConstraint(['channel_id'], ['notification_channels.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create Email Integration Tables
    op.create_table('email_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_name', sa.String(length=100), nullable=False),
        sa.Column('template_type', sa.String(length=50), nullable=False),
        sa.Column('subject_template', sa.Text(), nullable=False),
        sa.Column('body_template', sa.Text(), nullable=False),
        sa.Column('is_html', sa.Boolean(), nullable=True),
        sa.Column('variables', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('template_name')
    )
    
    op.create_table('email_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email_id', sa.String(length=100), nullable=False),
        sa.Column('recipient_email', sa.String(length=200), nullable=False),
        sa.Column('recipient_name', sa.String(length=200), nullable=True),
        sa.Column('subject', sa.String(length=500), nullable=False),
        sa.Column('template_name', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['template_name'], ['email_templates.template_name'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email_id')
    )
    
    # Create System Monitoring Tables
    op.create_table('system_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('metric_type', sa.String(length=50), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('labels', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('health_checks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('check_name', sa.String(length=100), nullable=False),
        sa.Column('check_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.Column('checked_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create Audit and Compliance Tables
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.String(length=100), nullable=True),
        sa.Column('old_values', sa.Text(), nullable=True),
        sa.Column('new_values', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('data_lineage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.String(length=100), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('target_id', sa.String(length=100), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=False),
        sa.Column('transformation_type', sa.String(length=100), nullable=True),
        sa.Column('transformation_details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create additional indexes for new tables
    op.create_index('idx_ngs_samples_sample_id', 'ngs_samples', ['sample_id'])
    op.create_index('idx_ngs_samples_project_id', 'ngs_samples', ['project_id'])
    op.create_index('idx_ngs_samples_user_id', 'ngs_samples', ['user_id'])
    op.create_index('idx_ngs_samples_platform', 'ngs_samples', ['platform'])
    op.create_index('idx_ngs_samples_sequencing_type', 'ngs_samples', ['sequencing_type'])
    
    op.create_index('idx_ngs_files_file_id', 'ngs_files', ['file_id'])
    op.create_index('idx_ngs_files_sample_id', 'ngs_files', ['sample_id'])
    op.create_index('idx_ngs_files_file_type', 'ngs_files', ['file_type'])
    
    op.create_index('idx_ngs_pipelines_pipeline_id', 'ngs_pipelines', ['pipeline_id'])
    op.create_index('idx_ngs_pipelines_pipeline_type', 'ngs_pipelines', ['pipeline_type'])
    op.create_index('idx_ngs_pipelines_is_active', 'ngs_pipelines', ['is_active'])
    
    op.create_index('idx_ngs_jobs_job_id', 'ngs_jobs', ['job_id'])
    op.create_index('idx_ngs_jobs_pipeline_id', 'ngs_jobs', ['pipeline_id'])
    op.create_index('idx_ngs_jobs_sample_id', 'ngs_jobs', ['sample_id'])
    op.create_index('idx_ngs_jobs_status', 'ngs_jobs', ['status'])
    op.create_index('idx_ngs_jobs_user_id', 'ngs_jobs', ['user_id'])
    op.create_index('idx_ngs_jobs_priority', 'ngs_jobs', ['priority'])
    
    op.create_index('idx_docker_images_image_name', 'docker_images', ['image_name'])
    op.create_index('idx_docker_images_image_tag', 'docker_images', ['image_tag'])
    op.create_index('idx_docker_images_is_active', 'docker_images', ['is_active'])
    
    op.create_index('idx_docker_containers_container_id', 'docker_containers', ['container_id'])
    op.create_index('idx_docker_containers_image_id', 'docker_containers', ['image_id'])
    op.create_index('idx_docker_containers_status', 'docker_containers', ['status'])
    
    op.create_index('idx_job_queues_queue_name', 'job_queues', ['queue_name'])
    op.create_index('idx_job_queues_queue_type', 'job_queues', ['queue_type'])
    op.create_index('idx_job_queues_is_active', 'job_queues', ['is_active'])
    
    op.create_index('idx_queue_jobs_job_id', 'queue_jobs', ['job_id'])
    op.create_index('idx_queue_jobs_queue_name', 'queue_jobs', ['queue_name'])
    op.create_index('idx_queue_jobs_status', 'queue_jobs', ['status'])
    op.create_index('idx_queue_jobs_priority', 'queue_jobs', ['priority'])
    op.create_index('idx_queue_jobs_user_id', 'queue_jobs', ['user_id'])
    op.create_index('idx_queue_jobs_scheduled_at', 'queue_jobs', ['scheduled_at'])
    
    op.create_index('idx_alert_rules_rule_name', 'alert_rules', ['rule_name'])
    op.create_index('idx_alert_rules_rule_type', 'alert_rules', ['rule_type'])
    op.create_index('idx_alert_rules_severity', 'alert_rules', ['severity'])
    op.create_index('idx_alert_rules_is_active', 'alert_rules', ['is_active'])
    
    op.create_index('idx_alert_instances_alert_id', 'alert_instances', ['alert_id'])
    op.create_index('idx_alert_instances_rule_id', 'alert_instances', ['rule_id'])
    op.create_index('idx_alert_instances_severity', 'alert_instances', ['severity'])
    op.create_index('idx_alert_instances_status', 'alert_instances', ['status'])
    op.create_index('idx_alert_instances_created_at', 'alert_instances', ['created_at'])
    
    op.create_index('idx_notification_channels_channel_name', 'notification_channels', ['channel_name'])
    op.create_index('idx_notification_channels_channel_type', 'notification_channels', ['channel_type'])
    op.create_index('idx_notification_channels_is_active', 'notification_channels', ['is_active'])
    
    op.create_index('idx_alert_notifications_alert_id', 'alert_notifications', ['alert_id'])
    op.create_index('idx_alert_notifications_channel_id', 'alert_notifications', ['channel_id'])
    op.create_index('idx_alert_notifications_status', 'alert_notifications', ['status'])
    
    op.create_index('idx_email_templates_template_name', 'email_templates', ['template_name'])
    op.create_index('idx_email_templates_template_type', 'email_templates', ['template_type'])
    op.create_index('idx_email_templates_is_active', 'email_templates', ['is_active'])
    
    op.create_index('idx_email_logs_email_id', 'email_logs', ['email_id'])
    op.create_index('idx_email_logs_recipient_email', 'email_logs', ['recipient_email'])
    op.create_index('idx_email_logs_status', 'email_logs', ['status'])
    op.create_index('idx_email_logs_sent_at', 'email_logs', ['sent_at'])
    
    op.create_index('idx_system_metrics_metric_name_time', 'system_metrics', ['metric_name', 'timestamp'])
    op.create_index('idx_system_metrics_metric_type_time', 'system_metrics', ['metric_type', 'timestamp'])
    
    op.create_index('idx_health_checks_check_name_time', 'health_checks', ['check_name', 'checked_at'])
    op.create_index('idx_health_checks_check_type_time', 'health_checks', ['check_type', 'checked_at'])
    
    op.create_index('idx_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_logs_resource_type', 'audit_logs', ['resource_type'])
    op.create_index('idx_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('idx_audit_logs_user_action_time', 'audit_logs', ['user_id', 'action', 'timestamp'])
    op.create_index('idx_audit_logs_resource_time', 'audit_logs', ['resource_type', 'resource_id', 'timestamp'])
    
    op.create_index('idx_data_lineage_source', 'data_lineage', ['source_id', 'source_type'])
    op.create_index('idx_data_lineage_target', 'data_lineage', ['target_id', 'target_type'])
    op.create_index('idx_data_lineage_created_at', 'data_lineage', ['created_at'])
    
    # Create check constraints
    op.create_check_constraint('check_positive_expression', 'gene_expression', 'expression_value >= 0')
    op.create_check_constraint('check_allele_frequency', 'mutation_records', 'allele_frequency >= 0 AND allele_frequency <= 1')
    op.create_check_constraint('check_positive_read_depth', 'mutation_records', 'read_depth >= 0')
    op.create_check_constraint('check_progress_range', 'analysis_jobs', 'progress >= 0 AND progress <= 100')
    op.create_check_constraint('check_priority_range', 'analysis_jobs', 'priority >= 1 AND priority <= 10')
    op.create_check_constraint('check_positive_file_size', 'data_files', 'file_size >= 0')
    op.create_check_constraint('check_quality_score_range', 'data_files', 'quality_score >= 0 AND quality_score <= 1')
    op.create_check_constraint('check_ngs_priority_range', 'ngs_jobs', 'priority >= 1 AND priority <= 10')
    op.create_check_constraint('check_queue_priority_range', 'queue_jobs', 'priority >= 1 AND priority <= 10')
    op.create_check_constraint('check_positive_metric_value', 'system_metrics', 'value >= 0')
    op.create_check_constraint('check_positive_response_time', 'health_checks', 'response_time_ms >= 0')


def downgrade() -> None:
    # Drop check constraints
    op.drop_constraint('check_positive_response_time', 'health_checks', type_='check')
    op.drop_constraint('check_positive_metric_value', 'system_metrics', type_='check')
    op.drop_constraint('check_queue_priority_range', 'queue_jobs', type_='check')
    op.drop_constraint('check_ngs_priority_range', 'ngs_jobs', type_='check')
    op.drop_constraint('check_quality_score_range', 'data_files', type_='check')
    op.drop_constraint('check_positive_file_size', 'data_files', type_='check')
    op.drop_constraint('check_priority_range', 'analysis_jobs', type_='check')
    op.drop_constraint('check_progress_range', 'analysis_jobs', type_='check')
    op.drop_constraint('check_positive_read_depth', 'mutation_records', type_='check')
    op.drop_constraint('check_allele_frequency', 'mutation_records', type_='check')
    op.drop_constraint('check_positive_expression', 'gene_expression', type_='check')
    
    # Drop indexes for new tables
    op.drop_index('idx_data_lineage_created_at', 'data_lineage')
    op.drop_index('idx_data_lineage_target', 'data_lineage')
    op.drop_index('idx_data_lineage_source', 'data_lineage')
    op.drop_index('idx_audit_logs_resource_time', 'audit_logs')
    op.drop_index('idx_audit_logs_user_action_time', 'audit_logs')
    op.drop_index('idx_audit_logs_timestamp', 'audit_logs')
    op.drop_index('idx_audit_logs_resource_type', 'audit_logs')
    op.drop_index('idx_audit_logs_action', 'audit_logs')
    op.drop_index('idx_audit_logs_user_id', 'audit_logs')
    op.drop_index('idx_health_checks_check_type_time', 'health_checks')
    op.drop_index('idx_health_checks_check_name_time', 'health_checks')
    op.drop_index('idx_system_metrics_metric_type_time', 'system_metrics')
    op.drop_index('idx_system_metrics_metric_name_time', 'system_metrics')
    op.drop_index('idx_email_logs_sent_at', 'email_logs')
    op.drop_index('idx_email_logs_status', 'email_logs')
    op.drop_index('idx_email_logs_recipient_email', 'email_logs')
    op.drop_index('idx_email_logs_email_id', 'email_logs')
    op.drop_index('idx_email_templates_is_active', 'email_templates')
    op.drop_index('idx_email_templates_template_type', 'email_templates')
    op.drop_index('idx_email_templates_template_name', 'email_templates')
    op.drop_index('idx_alert_notifications_status', 'alert_notifications')
    op.drop_index('idx_alert_notifications_channel_id', 'alert_notifications')
    op.drop_index('idx_alert_notifications_alert_id', 'alert_notifications')
    op.drop_index('idx_notification_channels_is_active', 'notification_channels')
    op.drop_index('idx_notification_channels_channel_type', 'notification_channels')
    op.drop_index('idx_notification_channels_channel_name', 'notification_channels')
    op.drop_index('idx_alert_instances_created_at', 'alert_instances')
    op.drop_index('idx_alert_instances_status', 'alert_instances')
    op.drop_index('idx_alert_instances_severity', 'alert_instances')
    op.drop_index('idx_alert_instances_rule_id', 'alert_instances')
    op.drop_index('idx_alert_instances_alert_id', 'alert_instances')
    op.drop_index('idx_alert_rules_is_active', 'alert_rules')
    op.drop_index('idx_alert_rules_severity', 'alert_rules')
    op.drop_index('idx_alert_rules_rule_type', 'alert_rules')
    op.drop_index('idx_alert_rules_rule_name', 'alert_rules')
    op.drop_index('idx_queue_jobs_scheduled_at', 'queue_jobs')
    op.drop_index('idx_queue_jobs_user_id', 'queue_jobs')
    op.drop_index('idx_queue_jobs_priority', 'queue_jobs')
    op.drop_index('idx_queue_jobs_status', 'queue_jobs')
    op.drop_index('idx_queue_jobs_queue_name', 'queue_jobs')
    op.drop_index('idx_queue_jobs_job_id', 'queue_jobs')
    op.drop_index('idx_job_queues_is_active', 'job_queues')
    op.drop_index('idx_job_queues_queue_type', 'job_queues')
    op.drop_index('idx_job_queues_queue_name', 'job_queues')
    op.drop_index('idx_docker_containers_status', 'docker_containers')
    op.drop_index('idx_docker_containers_image_id', 'docker_containers')
    op.drop_index('idx_docker_containers_container_id', 'docker_containers')
    op.drop_index('idx_docker_images_is_active', 'docker_images')
    op.drop_index('idx_docker_images_image_tag', 'docker_images')
    op.drop_index('idx_docker_images_image_name', 'docker_images')
    op.drop_index('idx_ngs_jobs_priority', 'ngs_jobs')
    op.drop_index('idx_ngs_jobs_user_id', 'ngs_jobs')
    op.drop_index('idx_ngs_jobs_status', 'ngs_jobs')
    op.drop_index('idx_ngs_jobs_sample_id', 'ngs_jobs')
    op.drop_index('idx_ngs_jobs_pipeline_id', 'ngs_jobs')
    op.drop_index('idx_ngs_jobs_job_id', 'ngs_jobs')
    op.drop_index('idx_ngs_pipelines_is_active', 'ngs_pipelines')
    op.drop_index('idx_ngs_pipelines_pipeline_type', 'ngs_pipelines')
    op.drop_index('idx_ngs_pipelines_pipeline_id', 'ngs_pipelines')
    op.drop_index('idx_ngs_files_file_type', 'ngs_files')
    op.drop_index('idx_ngs_files_sample_id', 'ngs_files')
    op.drop_index('idx_ngs_files_file_id', 'ngs_files')
    op.drop_index('idx_ngs_samples_sequencing_type', 'ngs_samples')
    op.drop_index('idx_ngs_samples_platform', 'ngs_samples')
    op.drop_index('idx_ngs_samples_user_id', 'ngs_samples')
    op.drop_index('idx_ngs_samples_project_id', 'ngs_samples')
    op.drop_index('idx_ngs_samples_sample_id', 'ngs_samples')
    
    # Drop indexes for original tables
    op.drop_index('idx_is_public_created', 'analysis_results')
    op.drop_index('idx_result_type_created', 'analysis_results')
    op.drop_index('idx_job_result_type', 'analysis_results')
    op.drop_index('idx_analysis_results_created_at', 'analysis_results')
    op.drop_index('idx_analysis_results_result_type', 'analysis_results')
    op.drop_index('idx_analysis_results_job_id', 'analysis_results')
    op.drop_index('idx_clinical_significance', 'mutation_records')
    op.drop_index('idx_chromosome_position', 'mutation_records')
    op.drop_index('idx_sample_gene', 'mutation_records')
    op.drop_index('idx_gene_variant', 'mutation_records')
    op.drop_index('idx_mutation_records_cancer_type', 'mutation_records')
    op.drop_index('idx_mutation_records_source', 'mutation_records')
    op.drop_index('idx_mutation_records_clinical_significance', 'mutation_records')
    op.drop_index('idx_mutation_records_sample_id', 'mutation_records')
    op.drop_index('idx_mutation_records_variant', 'mutation_records')
    op.drop_index('idx_mutation_records_gene', 'mutation_records')
    op.drop_index('idx_sample_condition', 'gene_expression')
    op.drop_index('idx_gene_condition', 'gene_expression')
    op.drop_index('idx_gene_sample', 'gene_expression')
    op.drop_index('idx_gene_expression_condition', 'gene_expression')
    op.drop_index('idx_gene_expression_sample_id', 'gene_expression')
    op.drop_index('idx_gene_expression_gene_symbol', 'gene_expression')
    op.drop_index('idx_datasets_owner_id', 'datasets')
    op.drop_index('idx_datasets_project_id', 'datasets')
    op.drop_index('idx_datasets_dataset_id', 'datasets')
    op.drop_index('idx_datasets_name', 'datasets')
    op.drop_index('idx_projects_owner_id', 'projects')
    op.drop_index('idx_projects_project_id', 'projects')
    op.drop_index('idx_projects_name', 'projects')
    op.drop_index('idx_project_dataset', 'data_files')
    op.drop_index('idx_user_upload_date', 'data_files')
    op.drop_index('idx_file_type_status', 'data_files')
    op.drop_index('idx_data_files_is_processed', 'data_files')
    op.drop_index('idx_data_files_upload_date', 'data_files')
    op.drop_index('idx_data_files_user_id', 'data_files')
    op.drop_index('idx_data_files_file_type', 'data_files')
    op.drop_index('idx_data_files_filename', 'data_files')
    op.drop_index('idx_created_at_status', 'analysis_jobs')
    op.drop_index('idx_user_status', 'analysis_jobs')
    op.drop_index('idx_job_type_status', 'analysis_jobs')
    op.drop_index('idx_analysis_jobs_created_at', 'analysis_jobs')
    op.drop_index('idx_analysis_jobs_user_id', 'analysis_jobs')
    op.drop_index('idx_analysis_jobs_status', 'analysis_jobs')
    op.drop_index('idx_analysis_jobs_job_type', 'analysis_jobs')
    op.drop_index('idx_analysis_jobs_job_id', 'analysis_jobs')
    op.drop_index('idx_users_is_active', 'users')
    op.drop_index('idx_users_email', 'users')
    op.drop_index('idx_users_username', 'users')
    
    # Drop tables in reverse order
    op.drop_table('data_lineage')
    op.drop_table('audit_logs')
    op.drop_table('health_checks')
    op.drop_table('system_metrics')
    op.drop_table('email_logs')
    op.drop_table('email_templates')
    op.drop_table('alert_notifications')
    op.drop_table('notification_channels')
    op.drop_table('alert_instances')
    op.drop_table('alert_rules')
    op.drop_table('queue_jobs')
    op.drop_table('job_queues')
    op.drop_table('docker_containers')
    op.drop_table('docker_images')
    op.drop_table('ngs_jobs')
    op.drop_table('ngs_pipelines')
    op.drop_table('ngs_files')
    op.drop_table('ngs_samples')
    op.drop_table('analysis_results')
    op.drop_table('mutation_records')
    op.drop_table('gene_expression')
    op.drop_table('datasets')
    op.drop_table('projects')
    op.drop_table('data_files')
    op.drop_table('analysis_jobs')
    op.drop_table('users')
