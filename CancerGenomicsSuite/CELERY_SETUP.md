# Celery Configuration Setup

This document describes the Celery configuration and setup for the Cancer Genomics Analysis Suite.

## Overview

The Celery configuration is centralized in `app/celery_config.py` and provides:

- **Comprehensive Configuration**: All Celery settings in one place
- **Queue Management**: Specialized queues for different task types
- **Monitoring**: Health checks and task statistics
- **Error Handling**: Retry policies and error recovery
- **Security**: Connection retry and authentication
- **Performance**: Task compression and optimization

## Configuration Files

### `app/celery_config.py`

The main Celery configuration file that includes:

- **Broker Configuration**: Redis/RabbitMQ settings
- **Task Routing**: Queue assignment for different task types
- **Worker Settings**: Concurrency, time limits, and optimization
- **Monitoring**: Health checks and statistics
- **Error Handling**: Retry policies and error recovery

### `celery_worker.py`

The worker entry point that imports the configured Celery app and provides:

- **Task Decorators**: Priority-based task decorators
- **Debug Tasks**: Testing and monitoring tasks
- **Configuration Validation**: Startup checks

## Queue Configuration

The system uses specialized queues for different types of tasks:

- **`default`**: General tasks
- **`data_processing`**: File processing and data manipulation
- **`expression_analysis`**: Gene expression analysis tasks
- **`mutation_analysis`**: Mutation analysis and annotation
- **`ml_prediction`**: Machine learning and prediction tasks
- **`integration`**: External API integration tasks
- **`reporting`**: Report generation and export
- **`high_priority`**: Urgent tasks
- **`low_priority`**: Background cleanup tasks

## Task Types

### Data Processing Tasks
- File upload and validation
- Data format conversion
- Quality control checks
- Database operations

### Analysis Tasks
- Gene expression analysis
- Mutation analysis
- Pathway enrichment
- Statistical analysis

### Machine Learning Tasks
- Model training
- Prediction generation
- Feature selection
- Cross-validation

### Integration Tasks
- External API calls
- Data synchronization
- Third-party service integration

### Reporting Tasks
- Report generation
- Data export
- Visualization creation
- Summary statistics

## Running Celery

### Basic Worker

```bash
# Run a general worker
python run_celery_worker.py worker

# Run with specific concurrency
python run_celery_worker.py worker --concurrency 4

# Run specific queues
python run_celery_worker.py worker --queues data_processing,ml_prediction
```

### Beat Scheduler

```bash
# Run the beat scheduler for periodic tasks
python run_celery_worker.py beat
```

### Flower Monitoring

```bash
# Run Flower web interface
python run_celery_worker.py flower
```

Access Flower at: http://localhost:5555

### Multiple Workers

```bash
# Run multiple specialized workers
python run_celery_worker.py multi
```

### Direct Celery Commands

```bash
# General worker
celery -A celery_worker worker --loglevel=info

# Beat scheduler
celery -A celery_worker beat --loglevel=info

# Flower monitoring
celery -A celery_worker flower --port=5555

# Multi-worker setup
celery -A celery_worker multi start worker1 worker2 worker3
```

## Configuration Options

### Environment Variables

Key environment variables for Celery configuration:

```bash
# Broker and Backend
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Worker Settings
CELERY_WORKER_CONCURRENCY=4
CELERY_WORKER_PREFETCH_MULTIPLIER=1
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000

# Task Settings
CELERY_TASK_SOFT_TIME_LIMIT=3600
CELERY_TASK_TIME_LIMIT=7200
CELERY_TASK_ACKS_LATE=True
```

### Settings Integration

The Celery configuration automatically uses settings from `config/settings.py`:

```python
from config.settings import settings

celery_app.conf.update(
    broker_url=settings.celery.broker_url,
    result_backend=settings.celery.result_backend,
    worker_concurrency=settings.celery.worker_concurrency,
    # ... other settings
)
```

## Monitoring and Health Checks

### Health Check Task

```python
from CancerGenomicsSuite.app.celery_config import health_check

# Run health check
result = health_check.delay()
status = result.get()
```

### Task Status

```python
from CancerGenomicsSuite.app.celery_config import get_task_status

# Get task status
status = get_task_status('task-id-here')
```

### Worker Statistics

```python
from CancerGenomicsSuite.app.celery_config import get_worker_stats

# Get worker statistics
stats = get_worker_stats()
```

### Queue Lengths

```python
from CancerGenomicsSuite.app.celery_config import get_queue_lengths

# Get queue lengths
lengths = get_queue_lengths()
```

## Error Handling

### Retry Policies

Tasks automatically retry on failure with exponential backoff:

```python
@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def my_task(self):
    # Task implementation
    pass
```

### Error Monitoring

All task failures are logged and can be monitored through:

- Celery logs
- Flower interface
- Custom error handlers

## Testing

### Test Tasks

Use the test tasks in `celery_worker/tasks/test_tasks.py`:

```python
from celery_worker.tasks.test_tasks import test_task, test_task_with_args

# Simple test
result = test_task.delay()

# Test with arguments
result = test_task_with_args.delay('arg1', 'arg2', key='value')
```

### Configuration Validation

```bash
# Check Redis connection
python run_celery_worker.py check
```

## Production Deployment

### Docker Deployment

```dockerfile
# Celery worker
FROM python:3.9
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["celery", "-A", "celery_worker", "worker", "--loglevel=info"]
```

### Systemd Service

```ini
[Unit]
Description=Celery Worker
After=network.target

[Service]
Type=forking
User=celery
Group=celery
EnvironmentFile=/etc/celery/celery.conf
WorkingDirectory=/opt/celery
ExecStart=/opt/celery/venv/bin/celery -A celery_worker worker --loglevel=info --detach
ExecStop=/bin/kill -s TERM $MAINPID
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Load Balancing

For high-throughput scenarios:

```bash
# Multiple workers on different machines
celery -A celery_worker worker --hostname=worker1@%h
celery -A celery_worker worker --hostname=worker2@%h
celery -A celery_worker worker --hostname=worker3@%h
```

## Troubleshooting

### Common Issues

1. **Redis Connection Error**
   - Check Redis is running: `redis-cli ping`
   - Verify connection URL in settings

2. **Task Not Executing**
   - Check worker is running: `celery -A celery_worker inspect active`
   - Verify task is registered: `celery -A celery_worker inspect registered`

3. **Memory Issues**
   - Reduce worker concurrency
   - Increase `worker_max_tasks_per_child`
   - Monitor memory usage

4. **Task Timeouts**
   - Increase `task_time_limit`
   - Optimize task implementation
   - Use task chunks for large datasets

### Debugging

```bash
# Check worker status
celery -A celery_worker inspect active

# Check registered tasks
celery -A celery_worker inspect registered

# Check worker statistics
celery -A celery_worker inspect stats

# Purge all queues (use with caution)
celery -A celery_worker purge
```

### Logging

Configure logging in your application:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## Performance Optimization

### Worker Optimization

- **Concurrency**: Match CPU cores (usually 2-4x CPU cores)
- **Prefetch**: Set to 1 for CPU-bound tasks, higher for I/O-bound
- **Memory**: Monitor and restart workers periodically

### Task Optimization

- **Chunking**: Break large tasks into smaller chunks
- **Compression**: Enable task compression for large payloads
- **Caching**: Cache frequently used data
- **Database**: Use connection pooling

### Queue Optimization

- **Priority Queues**: Use different queues for different priorities
- **Routing**: Route tasks to appropriate workers
- **Load Balancing**: Distribute load across multiple workers

## Security Considerations

- **Network Security**: Use TLS for broker connections
- **Authentication**: Configure broker authentication
- **Access Control**: Limit worker access to necessary resources
- **Data Privacy**: Ensure sensitive data is handled securely
- **Audit Logging**: Log all task executions and results
