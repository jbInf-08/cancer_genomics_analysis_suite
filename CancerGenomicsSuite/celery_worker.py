#!/usr/bin/env python3
"""
Cancer Genomics Analysis Suite - Celery Worker Configuration

This module configures Celery for distributed task processing in the cancer
genomics analysis suite, including background jobs for data processing,
analysis, and reporting.

Usage:
    celery -A celery_worker worker --loglevel=info
    celery -A celery_worker flower  # For monitoring
    celery -A celery_worker beat    # For scheduled tasks
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the configured Celery app
from app.celery_config import celery_app as celery

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Celery configuration is now handled in app/celery_config.py
# The celery instance is imported from there with all necessary configuration

# Task decorators for different priority levels
def high_priority_task(*args, **kwargs):
    """Decorator for high priority tasks."""
    kwargs.setdefault("queue", "high_priority")
    kwargs.setdefault("priority", 9)
    return celery.task(*args, **kwargs)

def low_priority_task(*args, **kwargs):
    """Decorator for low priority tasks."""
    kwargs.setdefault("queue", "low_priority")
    kwargs.setdefault("priority", 1)
    return celery.task(*args, **kwargs)

def long_running_task(*args, **kwargs):
    """Decorator for long-running tasks."""
    kwargs.setdefault("time_limit", 14400)  # 4 hours
    kwargs.setdefault("soft_time_limit", 10800)  # 3 hours
    return celery.task(*args, **kwargs)

# Import task modules
try:
    from celery_worker.tasks import (
        expression_analysis,
        mutation_analysis,
        ml_prediction,
        reporting,
        data_processing,
        integration_tasks,
        md_workflow_tasks,
        test_tasks
    )
    logger.info("✅ All task modules imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ Some task modules could not be imported: {e}")

# Task registration and monitoring
@celery.task(bind=True)
def debug_task(self):
    """Debug task for testing worker connectivity."""
    logger.info(f"Request: {self.request!r}")
    return "Debug task completed successfully"

@celery.task(bind=True)
def health_check(self):
    """Health check task for monitoring worker status."""
    import psutil
    import time
    
    health_info = {
        "worker_id": self.request.hostname,
        "task_id": self.request.id,
        "timestamp": time.time(),
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
        "status": "healthy"
    }
    
    logger.info(f"Health check completed: {health_info}")
    return health_info

# Error handling
@celery.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def retry_task(self, task_name, *args, **kwargs):
    """Generic retry task wrapper."""
    try:
        # This would be replaced with actual task execution
        logger.info(f"Executing retry task: {task_name}")
        return f"Task {task_name} completed successfully"
    except Exception as exc:
        logger.error(f"Task {task_name} failed: {exc}")
        raise self.retry(exc=exc)

# Task monitoring and statistics
@celery.task
def get_task_statistics():
    """Get current task statistics."""
    from celery import current_app
    
    inspect = current_app.control.inspect()
    
    stats = {
        "active_tasks": inspect.active(),
        "scheduled_tasks": inspect.scheduled(),
        "reserved_tasks": inspect.reserved(),
        "worker_stats": inspect.stats(),
    }
    
    return stats

# Configuration validation
def validate_configuration():
    """Validate Celery configuration."""
    try:
        # Test broker connection
        celery.control.inspect().ping()
        logger.info("✅ Broker connection successful")
        
        # Test result backend
        test_result = debug_task.delay()
        result = test_result.get(timeout=10)
        logger.info(f"✅ Result backend test: {result}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Configuration validation failed: {e}")
        return False

# Worker startup hook
@celery.task
def worker_startup():
    """Task to run on worker startup."""
    logger.info("🚀 Cancer Genomics Analysis Suite Worker Starting")
    logger.info(f"📊 Broker: {celery.conf.broker_url}")
    logger.info(f"💾 Backend: {celery.conf.result_backend}")
    logger.info(f"⏰ Timezone: {celery.conf.timezone}")
    
    # Validate configuration
    if validate_configuration():
        logger.info("✅ Worker configuration validated successfully")
    else:
        logger.error("❌ Worker configuration validation failed")

# Graceful shutdown hook
@celery.task
def worker_shutdown():
    """Task to run on worker shutdown."""
    logger.info("🛑 Cancer Genomics Analysis Suite Worker Shutting Down")
    logger.info("📊 Final task statistics:")
    
    try:
        stats = get_task_statistics()
        logger.info(f"Active tasks: {len(stats.get('active_tasks', {}))}")
        logger.info(f"Scheduled tasks: {len(stats.get('scheduled_tasks', {}))}")
    except Exception as e:
        logger.error(f"Error getting final statistics: {e}")

# Export celery instance
__all__ = ["celery", "high_priority_task", "low_priority_task", "long_running_task"]

if __name__ == "__main__":
    # Run worker startup
    worker_startup()
