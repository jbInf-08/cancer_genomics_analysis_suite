"""
Delivery Queue Module

Manages message queuing and delivery for notifications in the Cancer Genomics Analysis Suite.
Provides reliable message delivery with retry mechanisms and priority handling.
"""

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class MessageStatus(Enum):
    """Message delivery status."""
    PENDING = "pending"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class NotificationMessage:
    """Represents a notification message in the queue."""
    id: str
    recipient: str
    subject: str
    content: str
    message_type: str
    priority: MessagePriority
    status: MessageStatus
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for storage."""
        data = asdict(self)
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        if self.scheduled_at:
            data['scheduled_at'] = self.scheduled_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotificationMessage':
        """Create message from dictionary."""
        data['priority'] = MessagePriority(data['priority'])
        data['status'] = MessageStatus(data['status'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('scheduled_at'):
            data['scheduled_at'] = datetime.fromisoformat(data['scheduled_at'])
        return cls(**data)


class DeliveryQueue:
    """
    Manages notification message queuing and delivery.
    
    Features:
    - Priority-based message queuing
    - Retry mechanisms with exponential backoff
    - Scheduled message delivery
    - Persistent storage
    - Delivery status tracking
    - Batch processing
    """
    
    def __init__(self, db_path: str = None, max_workers: int = 3):
        """
        Initialize delivery queue.
        
        Args:
            db_path: Path to SQLite database file
            max_workers: Maximum number of delivery workers
        """
        self.db_path = db_path or str(Path(__file__).parent / 'notification_queue.db')
        self.max_workers = max_workers
        self.workers = []
        self.is_running = False
        self.delivery_handlers = {}
        
        # Initialize database
        self._init_database()
        
        # Start worker threads
        self._start_workers()
    
    def _init_database(self):
        """Initialize SQLite database for message storage."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    recipient TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    content TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    scheduled_at TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    metadata TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_status_priority 
                ON messages(status, priority DESC, created_at)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_scheduled 
                ON messages(scheduled_at) WHERE scheduled_at IS NOT NULL
            ''')
    
    def _start_workers(self):
        """Start delivery worker threads."""
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"DeliveryWorker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        
        self.is_running = True
        logger.info(f"Started {self.max_workers} delivery workers")
    
    def _worker_loop(self):
        """Main worker loop for processing messages."""
        while self.is_running:
            try:
                # Get next message to process
                message = self._get_next_message()
                
                if message:
                    self._process_message(message)
                else:
                    # No messages to process, wait a bit
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Worker error: {str(e)}")
                time.sleep(5)  # Wait before retrying
    
    def _get_next_message(self) -> Optional[NotificationMessage]:
        """Get the next message to process based on priority and schedule."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM messages 
                WHERE status IN ('pending', 'retrying')
                AND (scheduled_at IS NULL OR scheduled_at <= ?)
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
            ''', (datetime.now().isoformat(),))
            
            row = cursor.fetchone()
            if row:
                # Update status to processing
                conn.execute('''
                    UPDATE messages 
                    SET status = 'processing', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (row['id'],))
                
                return NotificationMessage.from_dict(dict(row))
        
        return None
    
    def _process_message(self, message: NotificationMessage):
        """Process a single message for delivery."""
        try:
            # Get delivery handler for message type
            handler = self.delivery_handlers.get(message.message_type)
            if not handler:
                logger.error(f"No handler for message type: {message.message_type}")
                self._mark_message_failed(message, "No delivery handler")
                return
            
            # Attempt delivery
            success = handler(message)
            
            if success:
                self._mark_message_delivered(message)
                logger.info(f"Message {message.id} delivered successfully")
            else:
                self._handle_delivery_failure(message)
                
        except Exception as e:
            logger.error(f"Error processing message {message.id}: {str(e)}")
            self._handle_delivery_failure(message, str(e))
    
    def _handle_delivery_failure(self, message: NotificationMessage, error: str = None):
        """Handle delivery failure with retry logic."""
        message.retry_count += 1
        
        if message.retry_count >= message.max_retries:
            # Max retries exceeded, mark as failed
            self._mark_message_failed(message, error or "Max retries exceeded")
        else:
            # Schedule retry with exponential backoff
            retry_delay = min(300, 2 ** message.retry_count)  # Max 5 minutes
            retry_time = datetime.now() + timedelta(seconds=retry_delay)
            
            self._update_message_status(
                message.id, 
                MessageStatus.RETRYING,
                retry_count=message.retry_count,
                scheduled_at=retry_time
            )
            
            logger.info(f"Message {message.id} scheduled for retry {message.retry_count} at {retry_time}")
    
    def _mark_message_delivered(self, message: NotificationMessage):
        """Mark message as delivered."""
        self._update_message_status(message.id, MessageStatus.DELIVERED)
    
    def _mark_message_failed(self, message: NotificationMessage, error: str):
        """Mark message as failed."""
        self._update_message_status(
            message.id, 
            MessageStatus.FAILED,
            metadata={'error': error, 'failed_at': datetime.now().isoformat()}
        )
    
    def _update_message_status(self, message_id: str, status: MessageStatus, 
                             **updates):
        """Update message status and other fields."""
        with sqlite3.connect(self.db_path) as conn:
            set_clauses = ['status = ?', 'updated_at = CURRENT_TIMESTAMP']
            params = [status.value]
            
            for key, value in updates.items():
                if key == 'metadata' and isinstance(value, dict):
                    set_clauses.append(f'{key} = ?')
                    params.append(json.dumps(value))
                else:
                    set_clauses.append(f'{key} = ?')
                    params.append(value)
            
            params.append(message_id)
            
            conn.execute(f'''
                UPDATE messages 
                SET {', '.join(set_clauses)}
                WHERE id = ?
            ''', params)
    
    def register_delivery_handler(self, message_type: str, handler: Callable):
        """
        Register a delivery handler for a specific message type.
        
        Args:
            message_type: Type of message to handle
            handler: Function that takes NotificationMessage and returns bool
        """
        self.delivery_handlers[message_type] = handler
        logger.info(f"Registered delivery handler for message type: {message_type}")
    
    def enqueue_message(self, recipient: str, subject: str, content: str,
                       message_type: str, priority: MessagePriority = MessagePriority.NORMAL,
                       scheduled_at: Optional[datetime] = None,
                       max_retries: int = 3, metadata: Dict[str, Any] = None) -> str:
        """
        Add a message to the delivery queue.
        
        Args:
            recipient: Message recipient
            subject: Message subject
            content: Message content
            message_type: Type of message
            priority: Message priority
            scheduled_at: When to deliver the message (None for immediate)
            max_retries: Maximum number of delivery retries
            metadata: Additional message metadata
            
        Returns:
            str: Message ID
        """
        message_id = str(uuid.uuid4())
        message = NotificationMessage(
            id=message_id,
            recipient=recipient,
            subject=subject,
            content=content,
            message_type=message_type,
            priority=priority,
            status=MessageStatus.PENDING,
            created_at=datetime.now(),
            scheduled_at=scheduled_at,
            max_retries=max_retries,
            metadata=metadata or {}
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO messages (
                    id, recipient, subject, content, message_type,
                    priority, status, created_at, scheduled_at,
                    max_retries, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message.id, message.recipient, message.subject,
                message.content, message.message_type, message.priority.value,
                message.status.value, message.created_at.isoformat(),
                message.scheduled_at.isoformat() if message.scheduled_at else None,
                message.max_retries, json.dumps(message.metadata)
            ))
        
        logger.info(f"Enqueued message {message_id} for {recipient}")
        return message_id
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status and statistics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get counts by status
            cursor = conn.execute('''
                SELECT status, COUNT(*) as count 
                FROM messages 
                GROUP BY status
            ''')
            status_counts = {row['status']: row['count'] for row in cursor}
            
            # Get oldest pending message
            cursor = conn.execute('''
                SELECT created_at FROM messages 
                WHERE status = 'pending' 
                ORDER BY created_at ASC 
                LIMIT 1
            ''')
            oldest_pending = cursor.fetchone()
            
            # Get retry statistics
            cursor = conn.execute('''
                SELECT AVG(retry_count) as avg_retries,
                       MAX(retry_count) as max_retries
                FROM messages 
                WHERE status IN ('retrying', 'failed')
            ''')
            retry_stats = cursor.fetchone()
        
        return {
            'status_counts': status_counts,
            'oldest_pending': oldest_pending['created_at'] if oldest_pending else None,
            'average_retries': retry_stats['avg_retries'] or 0,
            'max_retries': retry_stats['max_retries'] or 0,
            'active_workers': len(self.workers),
            'is_running': self.is_running
        }
    
    def get_messages_by_status(self, status: MessageStatus, 
                              limit: int = 100) -> List[NotificationMessage]:
        """Get messages by status."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM messages 
                WHERE status = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (status.value, limit))
            
            return [NotificationMessage.from_dict(dict(row)) for row in cursor]
    
    def retry_failed_messages(self, message_ids: List[str] = None) -> int:
        """
        Retry failed messages.
        
        Args:
            message_ids: Specific message IDs to retry (None for all failed)
            
        Returns:
            int: Number of messages queued for retry
        """
        with sqlite3.connect(self.db_path) as conn:
            if message_ids:
                placeholders = ','.join(['?' for _ in message_ids])
                conn.execute(f'''
                    UPDATE messages 
                    SET status = 'pending', retry_count = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders}) AND status = 'failed'
                ''', message_ids)
            else:
                conn.execute('''
                    UPDATE messages 
                    SET status = 'pending', retry_count = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE status = 'failed'
                ''')
            
            return conn.total_changes
    
    def cleanup_old_messages(self, days_old: int = 30) -> int:
        """
        Clean up old delivered/failed messages.
        
        Args:
            days_old: Remove messages older than this many days
            
        Returns:
            int: Number of messages removed
        """
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                DELETE FROM messages 
                WHERE status IN ('delivered', 'failed') 
                AND created_at < ?
            ''', (cutoff_date.isoformat(),))
            
            return conn.total_changes
    
    def stop(self):
        """Stop the delivery queue and workers."""
        self.is_running = False
        logger.info("Delivery queue stopped")
