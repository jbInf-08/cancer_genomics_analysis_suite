#!/usr/bin/env python3
"""
Celery Configuration for Cancer Genomics Analysis Suite

This module provides comprehensive Celery configuration for background task
processing in the cancer genomics analysis suite. It integrates with the
application settings and provides robust task management capabilities.

Features:
- Integration with application settings
- Task discovery and auto-registration
- Monitoring and health checks
- Error handling and retry policies
- Result backend configuration
- Worker and task optimization
- Security and authentication
"""

import os
import logging
from celery import Celery
from celery.signals import worker_ready, worker_shutdown, task_prerun, task_postrun
from kombu import Queue, Exchange
from kombu.common import Broadcast

# Import settings
from CancerGenomicsSuite.config.settings import settings

# Configure logging
logger = logging.getLogger(__name__)

# Create Celery application
celery_app = Celery("cancer_genomics_suite")

# Basic Configuration
celery_app.conf.update(
    # Broker and Result Backend
    broker_url=settings.celery.broker_url,
    result_backend=settings.celery.result_backend,
    
    # Serialization
    task_serializer=settings.celery.task_serializer,
    result_serializer=settings.celery.result_serializer,
    accept_content=settings.celery.accept_content,
    
    # Timezone
    timezone=settings.celery.timezone,
    enable_utc=settings.celery.enable_utc,
    
    # Task Execution
    task_acks_late=settings.celery.task_acks_late,
    worker_prefetch_multiplier=settings.celery.worker_prefetch_multiplier,
    worker_max_tasks_per_child=settings.celery.worker_max_tasks_per_child,
    
    # Time Limits
    task_soft_time_limit=settings.celery.task_soft_time_limit,
    task_time_limit=settings.celery.task_time_limit,
    
    # Result Backend Settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,
    
    # Task Routing
    task_default_queue='default',
    task_routes={
        'celery_worker.tasks.data_processing.*': {'queue': 'data_processing'},
        'celery_worker.tasks.expression_analysis.*': {'queue': 'expression_analysis'},
        'celery_worker.tasks.mutation_analysis.*': {'queue': 'mutation_analysis'},
        'celery_worker.tasks.ml_prediction.*': {'queue': 'ml_prediction'},
        'celery_worker.tasks.integration_tasks.*': {'queue': 'integration'},
        'celery_worker.tasks.reporting.*': {'queue': 'reporting'},
    },
    
    # Queue Configuration
    task_create_missing_queues=True,
    task_queues=(
        Queue('default', Exchange('default'), routing_key='default'),
        Queue('data_processing', Exchange('data_processing'), routing_key='data_processing'),
        Queue('expression_analysis', Exchange('expression_analysis'), routing_key='expression_analysis'),
        Queue('mutation_analysis', Exchange('mutation_analysis'), routing_key='mutation_analysis'),
        Queue('ml_prediction', Exchange('ml_prediction'), routing_key='ml_prediction'),
        Queue('integration', Exchange('integration'), routing_key='integration'),
        Queue('reporting', Exchange('reporting'), routing_key='reporting'),
        Queue('high_priority', Exchange('high_priority'), routing_key='high_priority'),
        Queue('low_priority', Exchange('low_priority'), routing_key='low_priority'),
        Broadcast('broadcast_tasks'),
    ),
    
    # Worker Configuration
    worker_concurrency=settings.celery.worker_concurrency,
    worker_disable_rate_limits=False,
    worker_hijack_root_logger=False,
    worker_log_color=False,
    
    # Task Discovery
    include=[
        'celery_worker.tasks.data_processing',
        'celery_worker.tasks.expression_analysis',
        'celery_worker.tasks.mutation_analysis',
        'celery_worker.tasks.ml_prediction',
        'celery_worker.tasks.integration_tasks',
        'celery_worker.tasks.reporting',
    ],
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Security
    worker_direct=True,
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    
    # Task Compression
    task_compression='gzip',
    result_compression='gzip',
    
    # Task Tracking
    task_track_started=True,
    task_ignore_result=False,
    
    # Beat Schedule (for periodic tasks)
    beat_schedule={
        'cleanup-temp-files': {
            'task': 'celery_worker.tasks.data_processing.cleanup_temp_files',
            'schedule': 3600.0,  # Run every hour
        },
        'health-check': {
            'task': 'celery_worker.tasks.reporting.system_health_check',
            'schedule': 300.0,  # Run every 5 minutes
        },
        'backup-database': {
            'task': 'celery_worker.tasks.data_processing.backup_database',
            'schedule': 86400.0,  # Run daily
        },
    },
    beat_schedule_filename='celerybeat-schedule',
    
    # Task Retry Configuration
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Result Backend Optimization
    result_backend_transport_options={
        'master_name': 'mymaster',
        'visibility_timeout': 3600,
    },
    
    # Task Annotation (for monitoring and debugging)
    task_annotations={
        '*': {
            'rate_limit': '100/m',  # 100 tasks per minute
        },
        'celery_worker.tasks.ml_prediction.*': {
            'rate_limit': '10/m',  # ML tasks are more resource intensive
            'time_limit': 7200,    # 2 hours max
            'soft_time_limit': 3600,  # 1 hour soft limit
        },
        'celery_worker.tasks.data_processing.*': {
            'rate_limit': '50/m',
            'time_limit': 3600,    # 1 hour max
        },
    },
)

# Configure Redis-specific settings if using Redis
if 'redis' in settings.celery.broker_url.lower():
    celery_app.conf.update(
        broker_transport_options={
            'visibility_timeout': 3600,
            'fanout_prefix': True,
            'fanout_patterns': True,
        },
        result_backend_transport_options={
            'visibility_timeout': 3600,
        },
    )

# Configure RabbitMQ-specific settings if using RabbitMQ
if 'amqp' in settings.celery.broker_url.lower() or 'rabbitmq' in settings.celery.broker_url.lower():
    celery_app.conf.update(
        broker_transport_options={
            'visibility_timeout': 3600,
            'fanout_prefix': True,
            'fanout_patterns': True,
        },
    )


# Signal Handlers for Monitoring and Logging
@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handle worker ready signal."""
    logger.info(f"Celery worker {sender} is ready and accepting tasks")


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Handle worker shutdown signal."""
    logger.info(f"Celery worker {sender} is shutting down")


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handle task prerun signal."""
    logger.info(f"Task {task.name}[{task_id}] starting with args={args}, kwargs={kwargs}")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Handle task postrun signal."""
    logger.info(f"Task {task.name}[{task_id}] finished with state={state}")


# Task Error Handling
@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def error_handler_task(self, exc, task_id, args, kwargs, einfo):
    """Global error handler for failed tasks."""
    logger.error(f"Task {task_id} failed: {exc}")
    logger.error(f"Exception info: {einfo}")


# Health Check Task
@celery_app.task
def health_check():
    """Health check task for monitoring."""
    try:
        # Test broker connection
        celery_app.control.inspect().stats()
        
        # Test result backend
        test_result = celery_app.send_task('celery_worker.tasks.reporting.test_task')
        test_result.get(timeout=10)
        
        return {
            'status': 'healthy',
            'broker': 'connected',
            'result_backend': 'connected',
            'worker_count': len(celery_app.control.inspect().active())
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


# Utility Functions
def get_task_status(task_id):
    """Get the status of a specific task."""
    try:
        result = celery_app.AsyncResult(task_id)
        return {
            'task_id': task_id,
            'status': result.status,
            'result': result.result if result.ready() else None,
            'info': result.info
        }
    except Exception as e:
        logger.error(f"Error getting task status for {task_id}: {e}")
        return {
            'task_id': task_id,
            'status': 'UNKNOWN',
            'error': str(e)
        }


def get_worker_stats():
    """Get statistics about active workers."""
    try:
        inspect = celery_app.control.inspect()
        return {
            'active': inspect.active(),
            'scheduled': inspect.scheduled(),
            'reserved': inspect.reserved(),
            'stats': inspect.stats(),
            'registered': inspect.registered()
        }
    except Exception as e:
        logger.error(f"Error getting worker stats: {e}")
        return {'error': str(e)}


def purge_all_queues():
    """Purge all task queues (use with caution)."""
    try:
        for queue_name in ['default', 'data_processing', 'expression_analysis', 
                          'mutation_analysis', 'ml_prediction', 'integration', 'reporting']:
            celery_app.control.purge()
        logger.info("All queues purged successfully")
        return True
    except Exception as e:
        logger.error(f"Error purging queues: {e}")
        return False


def get_queue_lengths():
    """Get the length of all task queues."""
    try:
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        scheduled_tasks = inspect.scheduled()
        reserved_tasks = inspect.reserved()
        
        queue_lengths = {}
        for worker, tasks in active_tasks.items():
            for task in tasks:
                queue = task.get('delivery_info', {}).get('routing_key', 'default')
                queue_lengths[queue] = queue_lengths.get(queue, 0) + 1
        
        return queue_lengths
    except Exception as e:
        logger.error(f"Error getting queue lengths: {e}")
        return {'error': str(e)}


# Configuration Validation
def validate_celery_config():
    """Validate Celery configuration."""
    try:
        # Test broker connection
        celery_app.control.inspect().stats()
        logger.info("Celery configuration validation successful")
        return True
    except Exception as e:
        logger.error(f"Celery configuration validation failed: {e}")
        return False


# Export the celery app and utility functions
__all__ = [
    'celery_app',
    'health_check',
    'get_task_status',
    'get_worker_stats',
    'purge_all_queues',
    'get_queue_lengths',
    'validate_celery_config'
]
