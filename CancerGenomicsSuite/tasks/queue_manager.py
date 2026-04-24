"""
Queue Manager Module

This module provides comprehensive task queue management capabilities for the
Cancer Genomics Analysis Suite, including task scheduling, priority management,
and distributed execution coordination.
"""

import asyncio
import queue
import threading
import time
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import uuid


class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """Task priority enumeration."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Task:
    """Task data structure."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    function: Optional[Callable] = None
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[int] = None
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class QueueManager:
    """
    A comprehensive task queue manager for cancer genomics analysis workflows.
    
    This class provides task scheduling, priority management, dependency handling,
    and distributed execution capabilities.
    """
    
    def __init__(self, max_workers: int = 4, queue_size: int = 1000):
        """
        Initialize the queue manager.
        
        Args:
            max_workers (int): Maximum number of worker threads
            queue_size (int): Maximum queue size
        """
        self.max_workers = max_workers
        self.queue_size = queue_size
        self.task_queue = queue.PriorityQueue(maxsize=queue_size)
        self.tasks: Dict[str, Task] = {}
        self.workers: List[threading.Thread] = []
        self.running = False
        self.logger = logging.getLogger(__name__)
        
        # Statistics
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'cancelled_tasks': 0,
            'start_time': None
        }
    
    def add_task(self, name: str, function: Callable, *args, 
                 priority: TaskPriority = TaskPriority.NORMAL,
                 timeout: Optional[int] = None,
                 max_retries: int = 3,
                 dependencies: Optional[List[str]] = None,
                 **kwargs) -> str:
        """
        Add a task to the queue.
        
        Args:
            name (str): Task name
            function (Callable): Function to execute
            *args: Function arguments
            priority (TaskPriority): Task priority
            timeout (int, optional): Task timeout in seconds
            max_retries (int): Maximum number of retries
            dependencies (List[str], optional): Task dependencies
            **kwargs: Function keyword arguments
            
        Returns:
            str: Task ID
        """
        task = Task(
            name=name,
            function=function,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout=timeout,
            max_retries=max_retries,
            dependencies=dependencies or []
        )
        
        self.tasks[task.id] = task
        self.stats['total_tasks'] += 1
        
        # Add to priority queue (lower priority value = higher priority)
        priority_value = 5 - priority.value  # Invert for queue ordering
        self.task_queue.put((priority_value, task.created_at, task.id))
        
        self.logger.info(f"Added task '{name}' with ID {task.id}")
        return task.id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.
        
        Args:
            task_id (str): Task ID
            
        Returns:
            Task: Task object or None if not found
        """
        return self.tasks.get(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        Get task status by ID.
        
        Args:
            task_id (str): Task ID
            
        Returns:
            TaskStatus: Task status or None if not found
        """
        task = self.get_task(task_id)
        return task.status if task else None
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task.
        
        Args:
            task_id (str): Task ID
            
        Returns:
            bool: True if task was cancelled, False otherwise
        """
        task = self.get_task(task_id)
        if task and task.status in [TaskStatus.PENDING, TaskStatus.RETRYING]:
            task.status = TaskStatus.CANCELLED
            self.stats['cancelled_tasks'] += 1
            self.logger.info(f"Cancelled task {task_id}")
            return True
        return False
    
    def get_ready_tasks(self) -> List[Task]:
        """
        Get tasks that are ready to run (no pending dependencies).
        
        Returns:
            List[Task]: List of ready tasks
        """
        ready_tasks = []
        
        for task in self.tasks.values():
            if task.status == TaskStatus.PENDING:
                # Check if all dependencies are completed
                dependencies_met = True
                for dep_id in task.dependencies:
                    dep_task = self.get_task(dep_id)
                    if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                        dependencies_met = False
                        break
                
                if dependencies_met:
                    ready_tasks.append(task)
        
        return ready_tasks
    
    def _execute_task(self, task: Task) -> Any:
        """
        Execute a single task.
        
        Args:
            task (Task): Task to execute
            
        Returns:
            Any: Task result
        """
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        try:
            self.logger.info(f"Executing task {task.id}: {task.name}")
            
            # Execute the function
            if task.timeout:
                # Use asyncio for timeout handling
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(
                                None, lambda: task.function(*task.args, **task.kwargs)
                            ),
                            timeout=task.timeout
                        )
                    )
                finally:
                    loop.close()
            else:
                result = task.function(*task.args, **task.kwargs)
            
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            self.stats['completed_tasks'] += 1
            
            self.logger.info(f"Completed task {task.id}: {task.name}")
            return result
            
        except Exception as e:
            task.error = str(e)
            task.retry_count += 1
            
            if task.retry_count <= task.max_retries:
                task.status = TaskStatus.RETRYING
                self.logger.warning(f"Task {task.id} failed, retrying ({task.retry_count}/{task.max_retries}): {e}")
                
                # Re-queue the task for retry
                priority_value = 5 - task.priority.value
                self.task_queue.put((priority_value, task.created_at, task.id))
            else:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()
                self.stats['failed_tasks'] += 1
                self.logger.error(f"Task {task.id} failed permanently: {e}")
            
            raise
    
    def _worker(self):
        """Worker thread function."""
        while self.running:
            try:
                # Get task from queue with timeout
                _, _, task_id = self.task_queue.get(timeout=1)
                task = self.get_task(task_id)
                
                if task and task.status == TaskStatus.PENDING:
                    self._execute_task(task)
                
                self.task_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Worker error: {e}")
    
    def start(self):
        """Start the queue manager and worker threads."""
        if self.running:
            return
        
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        # Start worker threads
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker, name=f"Worker-{i}")
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
        
        self.logger.info(f"Started queue manager with {self.max_workers} workers")
    
    def stop(self, wait: bool = True):
        """
        Stop the queue manager.
        
        Args:
            wait (bool): Whether to wait for running tasks to complete
        """
        if not self.running:
            return
        
        self.running = False
        
        if wait:
            # Wait for queue to empty
            self.task_queue.join()
            
            # Wait for workers to finish
            for worker in self.workers:
                worker.join(timeout=5)
        
        self.logger.info("Stopped queue manager")
    
    def wait_for_completion(self, timeout: Optional[int] = None) -> bool:
        """
        Wait for all tasks to complete.
        
        Args:
            timeout (int, optional): Maximum time to wait in seconds
            
        Returns:
            bool: True if all tasks completed, False if timeout
        """
        start_time = time.time()
        
        while True:
            # Check if all tasks are completed or failed
            pending_tasks = sum(1 for task in self.tasks.values() 
                              if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.RETRYING])
            
            if pending_tasks == 0:
                return True
            
            if timeout and (time.time() - start_time) > timeout:
                return False
            
            time.sleep(0.1)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get queue manager statistics.
        
        Returns:
            Dict[str, Any]: Statistics dictionary
        """
        current_time = datetime.now()
        uptime = None
        
        if self.stats['start_time']:
            uptime = (current_time - self.stats['start_time']).total_seconds()
        
        return {
            **self.stats,
            'uptime_seconds': uptime,
            'queue_size': self.task_queue.qsize(),
            'active_workers': len([w for w in self.workers if w.is_alive()]),
            'tasks_by_status': {
                status.value: sum(1 for task in self.tasks.values() if task.status == status)
                for status in TaskStatus
            }
        }
    
    def clear_completed_tasks(self):
        """Remove completed and failed tasks from memory."""
        to_remove = []
        
        for task_id, task in self.tasks.items():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.tasks[task_id]
        
        self.logger.info(f"Cleared {len(to_remove)} completed tasks")
    
    def export_tasks(self, filepath: str):
        """
        Export tasks to JSON file.
        
        Args:
            filepath (str): Path to export file
        """
        export_data = {
            'tasks': [],
            'statistics': self.get_statistics(),
            'export_time': datetime.now().isoformat()
        }
        
        for task in self.tasks.values():
            task_data = {
                'id': task.id,
                'name': task.name,
                'priority': task.priority.value,
                'status': task.status.value,
                'created_at': task.created_at.isoformat(),
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'retry_count': task.retry_count,
                'max_retries': task.max_retries,
                'timeout': task.timeout,
                'dependencies': task.dependencies,
                'metadata': task.metadata,
                'error': task.error
            }
            export_data['tasks'].append(task_data)
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        self.logger.info(f"Exported tasks to {filepath}")
    
    def import_tasks(self, filepath: str):
        """
        Import tasks from JSON file.
        
        Args:
            filepath (str): Path to import file
        """
        with open(filepath, 'r') as f:
            import_data = json.load(f)
        
        imported_count = 0
        
        for task_data in import_data.get('tasks', []):
            # Note: Function and args/kwargs are not restored for security reasons
            task = Task(
                id=task_data['id'],
                name=task_data['name'],
                priority=TaskPriority(task_data['priority']),
                status=TaskStatus(task_data['status']),
                created_at=datetime.fromisoformat(task_data['created_at']),
                started_at=datetime.fromisoformat(task_data['started_at']) if task_data['started_at'] else None,
                completed_at=datetime.fromisoformat(task_data['completed_at']) if task_data['completed_at'] else None,
                retry_count=task_data['retry_count'],
                max_retries=task_data['max_retries'],
                timeout=task_data['timeout'],
                dependencies=task_data['dependencies'],
                metadata=task_data['metadata'],
                error=task_data['error']
            )
            
            self.tasks[task.id] = task
            imported_count += 1
        
        self.logger.info(f"Imported {imported_count} tasks from {filepath}")
