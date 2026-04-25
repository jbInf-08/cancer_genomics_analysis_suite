# Cancer Genomics Analysis Suite - Integration Updates

This document outlines the comprehensive updates made to the Cancer Genomics Analysis Suite, including enhanced configuration management, database schema updates, NGS pipeline integration, and advanced alerting capabilities.

## Overview of Updates

### 1. Configuration Management Enhancements

#### Updated Files:
- `config/__init__.py` - Enhanced configuration package structure
- `config/settings.py` - Comprehensive Pydantic-based configuration
- `environment.template` - Extended environment variables template

#### Key Features:
- **Pydantic Integration**: Robust configuration validation and type checking
- **Nested Settings**: Organized configuration into logical groups (Database, Redis, Email, etc.)
- **Environment Detection**: Automatic detection of development, production, and testing environments
- **Configuration Validation**: Comprehensive validation of configuration parameters
- **Fallback Support**: SimpleConfig fallback for environments without Pydantic

#### New Configuration Sections:
- NGS Platform Configuration
- Docker Configuration
- Job Queue Configuration
- Monitoring and Alerts
- Enhanced Email Integration
- Redis Support
- Security Settings
- Compliance Settings

### 2. Database Schema Updates

#### Updated Files:
- `app/orm/schema.sql` - Comprehensive database schema
- `migrations/V1_initial_schema.py` - Alembic migration script

#### New Tables:
- **NGS Platform Support**:
  - `ngs_samples` - NGS sample information
  - `ngs_files` - NGS file metadata
  - `ngs_pipelines` - Pipeline definitions
  - `ngs_jobs` - Pipeline execution jobs

- **Docker and Container Management**:
  - `docker_images` - Docker image registry
  - `docker_containers` - Container instances

- **Job Queue Management**:
  - `job_queues` - Queue definitions
  - `queue_jobs` - Job queue entries

- **Alert and Notification Systems**:
  - `alert_rules` - Alert rule definitions
  - `alert_instances` - Alert instances
  - `notification_channels` - Notification channel configuration
  - `alert_notifications` - Notification history

- **Email Integration**:
  - `email_templates` - Email template definitions
  - `email_logs` - Email delivery logs

- **System Monitoring**:
  - `system_metrics` - System performance metrics
  - `health_checks` - Health check results

- **Audit and Compliance**:
  - `audit_logs` - System audit trail
  - `data_lineage` - Data lineage tracking

### 3. NGS Platform Support Enhancements

#### Updated Files:
- `modules/ngs_platform_support/workflow_dispatcher.py` - Added Docker and Celery support
- `modules/ngs_platform_support/ngs_pipeline_integration.py` - New comprehensive pipeline integration
- `modules/ngs_platform_support/__init__.py` - Updated exports

#### New Components:

##### DockerManager
- Docker image management (pull, push, list)
- Container lifecycle management (create, start, stop, remove)
- Container logging and monitoring
- Volume and network management

##### CeleryJobManager
- Distributed task queue management
- Job submission and monitoring
- Task status tracking
- Queue configuration and management

##### NGSPipelineManager
- Pipeline definition management (load, save, validate)
- Pipeline execution orchestration
- Execution monitoring and status tracking
- Pipeline cleanup and maintenance

##### PipelineStepExecutor
- Individual step execution
- Docker and local execution support
- Command parameter substitution
- Error handling and retry logic

##### PipelineValidator
- Pipeline definition validation
- Input validation for executions
- Dependency checking
- Type and format validation

##### EnhancedWorkflowDispatcher
- Integrated pipeline management
- Enhanced job orchestration
- Comprehensive monitoring
- Resource management

### 4. Advanced Alerting and Notifications

#### Updated Files:
- `modules/notifications/alert_monitor.py` - Enhanced with webhook support

#### New Features:

##### Webhook Notifications
- **Slack Integration**: Rich Slack message formatting with attachments
- **Microsoft Teams Integration**: Teams message cards with color coding
- **Email Fallback**: Comprehensive email notifications with SMTP support

##### Notification Classes:
- `WebhookNotifier` - Base webhook notification class
- `SlackNotifier` - Slack-specific formatting and delivery
- `TeamsNotifier` - Teams-specific message card formatting
- `EmailNotifier` - SMTP-based email notifications

##### Enhanced Alert Monitor:
- Multi-channel notification support
- Retry logic with configurable attempts
- Notification channel management
- Fallback mechanisms

### 5. Example Files and Documentation

#### New Files:
- `examples/example_ngs_pipeline.yaml` - Complete RNA-seq pipeline example
- `examples/ngs_pipeline_usage_example.py` - Comprehensive usage examples
- `INTEGRATION_UPDATES.md` - This documentation file

## Usage Examples

### 1. Basic Pipeline Execution

```python
from modules.ngs_platform_support import EnhancedWorkflowDispatcher

# Initialize dispatcher
dispatcher = EnhancedWorkflowDispatcher()

# Load pipeline
pipeline = await dispatcher.load_pipeline("path/to/pipeline.yaml")

# Execute pipeline
execution_id = await dispatcher.execute_pipeline(
    pipeline_name="rna_seq_analysis",
    inputs={
        "fastq_files": "/path/to/sample_R1.fastq.gz,/path/to/sample_R2.fastq.gz",
        "reference_genome": "/path/to/reference.fa",
        "gtf_annotation": "/path/to/annotation.gtf"
    },
    parameters={
        "threads": 8,
        "memory": "32G"
    }
)

# Monitor execution
status = await dispatcher.get_pipeline_status(execution_id)
print(f"Status: {status.status.value}, Progress: {status.progress:.1f}%")
```

### 2. Alert Monitoring Setup

```python
from modules.notifications.alert_monitor import AlertMonitor

# Initialize monitor
monitor = AlertMonitor()

# Set up notifications
monitor.setup_slack_notification("https://hooks.slack.com/services/YOUR/WEBHOOK")
monitor.setup_teams_notification("https://your-org.webhook.office.com/webhookb2/YOUR-WEBHOOK")
monitor.setup_email_notification(
    smtp_server="smtp.gmail.com",
    smtp_port=587,
    username="your-email@gmail.com",
    password="your-app-password",
    from_email="your-email@gmail.com",
    to_emails=["admin@your-org.com"]
)

# Start monitoring
monitor.start_monitoring()
```

### 3. Configuration Usage

```python
from config import settings

# Access configuration
print(f"Database URL: {settings.get_database_url()}")
print(f"Redis URL: {settings.get_redis_url()}")
print(f"Environment: {settings.environment}")

# Check feature flags
if settings.get_feature_status("ngs_pipeline_integration"):
    print("NGS Pipeline integration is enabled")

# Access nested settings
print(f"Email server: {settings.email.server}")
print(f"Docker registry: {settings.docker.registry}")
```

## Environment Variables

The following new environment variables have been added:

### NGS Platform Configuration
- `NGS_PLATFORM` - Primary NGS platform (illumina, ion_torrent, pacbio, nanopore)
- `NGS_QUALITY_THRESHOLD` - Default quality threshold for reads
- `NGS_ADAPTER_SEQUENCES` - Common adapter sequences
- `NGS_ENABLE_QC` - Enable quality control by default

### Docker Configuration
- `DOCKER_REGISTRY` - Docker registry URL
- `DOCKER_IMAGE_PREFIX` - Image name prefix
- `DOCKER_MEMORY_LIMIT` - Default memory limit for containers
- `DOCKER_CPU_LIMIT` - Default CPU limit for containers

### Job Queue Configuration
- `JOB_QUEUE_TYPE` - Queue type (celery, redis, local)
- `JOB_QUEUE_MAX_RETRIES` - Maximum retry attempts
- `JOB_QUEUE_ENABLE_PRIORITY` - Enable priority queues

### Monitoring and Alerts
- `ALERT_EMAIL_ENABLED` - Enable email alerts
- `SLACK_WEBHOOK_URL` - Slack webhook URL
- `TEAMS_WEBHOOK_URL` - Teams webhook URL
- `ALERT_RETRY_COUNT` - Number of retry attempts for notifications

## Migration Instructions

### 1. Database Migration
```bash
# Run Alembic migration
alembic upgrade head
```

### 2. Environment Setup
```bash
# Copy environment template
cp environment.template .env

# Edit .env with your specific configuration
nano .env
```

### 3. Dependencies
Ensure the following Python packages are installed:
```bash
pip install pydantic redis celery docker requests aiohttp pyyaml
```

## Testing

Run the example script to test the integration:
```bash
python examples/ngs_pipeline_usage_example.py
```

## Troubleshooting

### Common Issues:

1. **Pydantic Import Error**: Ensure Pydantic is installed or the SimpleConfig fallback will be used
2. **Docker Connection Error**: Verify Docker daemon is running and accessible
3. **Redis Connection Error**: Check Redis server status and connection parameters
4. **Webhook Notification Failures**: Verify webhook URLs and network connectivity

### Logging

Enable debug logging for detailed troubleshooting:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

Planned future enhancements include:
- Kubernetes integration for container orchestration
- Advanced pipeline scheduling and resource optimization
- Machine learning-based quality control
- Enhanced visualization and reporting
- Integration with cloud storage providers
- Advanced security and compliance features

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the example files for usage patterns
3. Check the configuration validation messages
4. Enable debug logging for detailed error information

## Contributing

When contributing to the codebase:
1. Follow the existing code structure and patterns
2. Add comprehensive docstrings and type hints
3. Include unit tests for new functionality
4. Update this documentation for significant changes
5. Ensure backward compatibility where possible
