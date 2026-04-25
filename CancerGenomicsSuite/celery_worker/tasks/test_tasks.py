#!/usr/bin/env python3
"""
Test Tasks for Cancer Genomics Analysis Suite

This module provides simple test tasks to verify Celery configuration
and worker functionality.
"""

import time
import logging
from datetime import datetime

# Import the celery app from the main configuration
from CancerGenomicsSuite.app.celery_config import celery_app

logger = logging.getLogger(__name__)

@celery_app.task
def test_task():
    """Simple test task to verify Celery is working."""
    logger.info("Test task started")
    time.sleep(1)  # Simulate some work
    result = {
        'message': 'Test task completed successfully',
        'timestamp': datetime.utcnow().isoformat(),
        'status': 'success'
    }
    logger.info(f"Test task completed: {result}")
    return result

@celery_app.task
def test_task_with_args(arg1, arg2, **kwargs):
    """Test task that accepts arguments."""
    logger.info(f"Test task with args started: {arg1}, {arg2}, {kwargs}")
    time.sleep(2)  # Simulate some work
    result = {
        'message': 'Test task with args completed',
        'arg1': arg1,
        'arg2': arg2,
        'kwargs': kwargs,
        'timestamp': datetime.utcnow().isoformat(),
        'status': 'success'
    }
    logger.info(f"Test task with args completed: {result}")
    return result

@celery_app.task(bind=True)
def test_task_with_retry(self, fail_count=0):
    """Test task that can fail and retry."""
    logger.info(f"Test retry task started, fail_count: {fail_count}")
    
    if fail_count > 0:
        logger.warning(f"Task failing intentionally (attempt {self.request.retries + 1})")
        raise Exception(f"Intentional failure (attempt {self.request.retries + 1})")
    
    result = {
        'message': 'Test retry task completed successfully',
        'attempts': self.request.retries + 1,
        'timestamp': datetime.utcnow().isoformat(),
        'status': 'success'
    }
    logger.info(f"Test retry task completed: {result}")
    return result

@celery_app.task
def test_long_running_task(duration=10):
    """Test task that runs for a specified duration."""
    logger.info(f"Long running test task started, duration: {duration} seconds")
    
    start_time = time.time()
    for i in range(duration):
        time.sleep(1)
        logger.info(f"Long running task progress: {i+1}/{duration}")
    
    end_time = time.time()
    result = {
        'message': 'Long running test task completed',
        'duration': end_time - start_time,
        'timestamp': datetime.utcnow().isoformat(),
        'status': 'success'
    }
    logger.info(f"Long running test task completed: {result}")
    return result

@celery_app.task
def test_task_with_error():
    """Test task that always fails."""
    logger.error("Test error task started")
    raise Exception("This is a test error task")

@celery_app.task
def test_chain_task():
    """Test task for chaining."""
    logger.info("Chain test task started")
    time.sleep(1)
    result = {
        'message': 'Chain test task completed',
        'timestamp': datetime.utcnow().isoformat(),
        'status': 'success'
    }
    logger.info(f"Chain test task completed: {result}")
    return result

# Export tasks
__all__ = [
    'test_task',
    'test_task_with_args', 
    'test_task_with_retry',
    'test_long_running_task',
    'test_task_with_error',
    'test_chain_task'
]
