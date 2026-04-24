#!/usr/bin/env python3
"""
Cancer Genomics Analysis Suite - Celery Worker Runner

This script provides a simple way to run Celery workers for the cancer
genomics analysis suite. It supports different worker types and configurations.

Usage:
    python run_celery_worker.py worker          # Run a general worker
    python run_celery_worker.py beat            # Run the beat scheduler
    python run_celery_worker.py flower          # Run Flower monitoring
    python run_celery_worker.py multi           # Run multiple workers
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import settings

def run_worker(concurrency=None, queues=None, loglevel='info'):
    """Run a Celery worker."""
    cmd = [
        'celery', '-A', 'celery_worker', 'worker',
        '--loglevel', loglevel,
        '--without-gossip',
        '--without-mingle',
        '--without-heartbeat'
    ]
    
    if concurrency:
        cmd.extend(['--concurrency', str(concurrency)])
    
    if queues:
        cmd.extend(['--queues', queues])
    
    print(f"Starting Celery worker with command: {' '.join(cmd)}")
    subprocess.run(cmd)

def run_beat():
    """Run the Celery beat scheduler."""
    cmd = [
        'celery', '-A', 'celery_worker', 'beat',
        '--loglevel', 'info',
        '--scheduler', 'celery.beat:PersistentScheduler'
    ]
    
    print(f"Starting Celery beat with command: {' '.join(cmd)}")
    subprocess.run(cmd)

def run_flower():
    """Run Flower monitoring interface."""
    cmd = [
        'celery', '-A', 'celery_worker', 'flower',
        '--port', '5555',
        '--broker', settings.celery.broker_url
    ]
    
    print(f"Starting Flower with command: {' '.join(cmd)}")
    print("Flower will be available at: http://localhost:5555")
    subprocess.run(cmd)

def run_multi():
    """Run multiple specialized workers."""
    workers = [
        {
            'name': 'data_processing',
            'queues': 'data_processing,default',
            'concurrency': 2
        },
        {
            'name': 'expression_analysis',
            'queues': 'expression_analysis',
            'concurrency': 1
        },
        {
            'name': 'mutation_analysis',
            'queues': 'mutation_analysis',
            'concurrency': 1
        },
        {
            'name': 'ml_prediction',
            'queues': 'ml_prediction',
            'concurrency': 1
        },
        {
            'name': 'reporting',
            'queues': 'reporting,integration',
            'concurrency': 1
        }
    ]
    
    print("Starting multiple Celery workers...")
    
    for worker in workers:
        cmd = [
            'celery', '-A', 'celery_worker', 'worker',
            '--loglevel', 'info',
            '--hostname', f"{worker['name']}@%h",
            '--queues', worker['queues'],
            '--concurrency', str(worker['concurrency']),
            '--without-gossip',
            '--without-mingle',
            '--without-heartbeat'
        ]
        
        print(f"Starting {worker['name']} worker: {' '.join(cmd)}")
        # In a real implementation, you would run these in separate processes
        # For now, we'll just show the command
        print(f"Command for {worker['name']}: {' '.join(cmd)}")

def check_redis_connection():
    """Check if Redis is available."""
    try:
        import redis
        r = redis.from_url(settings.celery.broker_url)
        r.ping()
        print("✅ Redis connection successful")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("Please ensure Redis is running and accessible")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Run Celery workers for Cancer Genomics Analysis Suite')
    parser.add_argument('command', choices=['worker', 'beat', 'flower', 'multi', 'check'],
                       help='Command to run')
    parser.add_argument('--concurrency', type=int, help='Number of worker processes')
    parser.add_argument('--queues', help='Comma-separated list of queues to consume')
    parser.add_argument('--loglevel', default='info', choices=['debug', 'info', 'warning', 'error'],
                       help='Log level')
    
    args = parser.parse_args()
    
    print(f"Cancer Genomics Analysis Suite - Celery Worker")
    print(f"Environment: {settings.flask_env}")
    print(f"Broker: {settings.celery.broker_url}")
    print(f"Result Backend: {settings.celery.result_backend}")
    print("-" * 50)
    
    if args.command == 'check':
        check_redis_connection()
        return
    
    if not check_redis_connection():
        print("Cannot start workers without Redis connection")
        sys.exit(1)
    
    if args.command == 'worker':
        run_worker(args.concurrency, args.queues, args.loglevel)
    elif args.command == 'beat':
        run_beat()
    elif args.command == 'flower':
        run_flower()
    elif args.command == 'multi':
        run_multi()

if __name__ == "__main__":
    main()
