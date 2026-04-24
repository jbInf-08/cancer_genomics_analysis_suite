"""
Alert Monitor Module

Monitors system health and triggers alerts for the Cancer Genomics Analysis Suite.
Provides comprehensive monitoring of system resources, analysis status, and error conditions.
"""

import logging
import threading
import time
import psutil
import json
import requests
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class Alert:
    """Represents a system alert."""
    id: str
    title: str
    description: str
    severity: AlertSeverity
    status: AlertStatus
    source: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for storage."""
        data = asdict(self)
        data['severity'] = self.severity.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        if self.acknowledged_at:
            data['acknowledged_at'] = self.acknowledged_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Alert':
        """Create alert from dictionary."""
        data['severity'] = AlertSeverity(data['severity'])
        data['status'] = AlertStatus(data['status'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('resolved_at'):
            data['resolved_at'] = datetime.fromisoformat(data['resolved_at'])
        if data.get('acknowledged_at'):
            data['acknowledged_at'] = datetime.fromisoformat(data['acknowledged_at'])
        return cls(**data)


@dataclass
class SystemMetrics:
    """System performance metrics."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    active_connections: int
    queue_size: int
    failed_analyses: int
    completed_analyses: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class WebhookNotifier:
    """Base class for webhook notifications."""
    
    def __init__(self, webhook_url: str, timeout: int = 30):
        self.webhook_url = webhook_url
        self.timeout = timeout
        self.session = requests.Session()
    
    def send_alert(self, alert: Alert) -> bool:
        """Send alert notification via webhook."""
        try:
            payload = self._format_payload(alert)
            response = self.session.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            logger.info(f"Webhook notification sent successfully for alert {alert.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send webhook notification for alert {alert.id}: {e}")
            return False
    
    def _format_payload(self, alert: Alert) -> Dict[str, Any]:
        """Format alert data for webhook payload."""
        raise NotImplementedError


class SlackNotifier(WebhookNotifier):
    """Slack webhook notifier."""
    
    def _format_payload(self, alert: Alert) -> Dict[str, Any]:
        """Format alert for Slack webhook."""
        # Determine color based on severity
        color_map = {
            AlertSeverity.INFO: "#36a64f",      # Green
            AlertSeverity.WARNING: "#ffaa00",   # Yellow
            AlertSeverity.ERROR: "#ff6600",     # Orange
            AlertSeverity.CRITICAL: "#ff0000"   # Red
        }
        
        # Create Slack attachment
        attachment = {
            "color": color_map.get(alert.severity, "#cccccc"),
            "title": f"🚨 {alert.title}",
            "text": alert.description,
            "fields": [
                {
                    "title": "Severity",
                    "value": alert.severity.value.upper(),
                    "short": True
                },
                {
                    "title": "Source",
                    "value": alert.source,
                    "short": True
                },
                {
                    "title": "Status",
                    "value": alert.status.value.upper(),
                    "short": True
                },
                {
                    "title": "Created",
                    "value": alert.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "short": True
                }
            ],
            "footer": "Cancer Genomics Analysis Suite",
            "ts": int(alert.created_at.timestamp())
        }
        
        # Add metadata if available
        if alert.metadata:
            metadata_text = "\n".join([f"• {k}: {v}" for k, v in alert.metadata.items()])
            attachment["fields"].append({
                "title": "Details",
                "value": metadata_text,
                "short": False
            })
        
        return {
            "text": f"Alert from Cancer Genomics Analysis Suite",
            "attachments": [attachment]
        }


class TeamsNotifier(WebhookNotifier):
    """Microsoft Teams webhook notifier."""
    
    def _format_payload(self, alert: Alert) -> Dict[str, Any]:
        """Format alert for Teams webhook."""
        # Determine color based on severity
        color_map = {
            AlertSeverity.INFO: "00ff00",       # Green
            AlertSeverity.WARNING: "ffff00",    # Yellow
            AlertSeverity.ERROR: "ff6600",      # Orange
            AlertSeverity.CRITICAL: "ff0000"    # Red
        }
        
        # Create Teams message card
        card = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": color_map.get(alert.severity, "cccccc"),
            "summary": f"Alert: {alert.title}",
            "sections": [{
                "activityTitle": f"🚨 {alert.title}",
                "activitySubtitle": f"Severity: {alert.severity.value.upper()}",
                "activityImage": "https://via.placeholder.com/64x64/ff0000/ffffff?text=!",
                "text": alert.description,
                "facts": [
                    {
                        "name": "Source",
                        "value": alert.source
                    },
                    {
                        "name": "Status",
                        "value": alert.status.value.upper()
                    },
                    {
                        "name": "Created",
                        "value": alert.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
                    }
                ],
                "markdown": True
            }]
        }
        
        # Add metadata if available
        if alert.metadata:
            metadata_facts = []
            for k, v in alert.metadata.items():
                metadata_facts.append({
                    "name": k,
                    "value": str(v)
                })
            card["sections"][0]["facts"].extend(metadata_facts)
        
        return card


class EmailNotifier:
    """Email notification fallback."""
    
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str,
                 from_email: str, to_emails: List[str]):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails
    
    def send_alert(self, alert: Alert) -> bool:
        """Send alert notification via email."""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ", ".join(self.to_emails)
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"
            
            # Create email body
            body = f"""
Alert Details:
==============

Title: {alert.title}
Description: {alert.description}
Severity: {alert.severity.value.upper()}
Source: {alert.source}
Status: {alert.status.value.upper()}
Created: {alert.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")}

"""
            
            if alert.metadata:
                body += "Additional Information:\n"
                for k, v in alert.metadata.items():
                    body += f"  {k}: {v}\n"
            
            body += f"""
Alert ID: {alert.id}

This is an automated alert from the Cancer Genomics Analysis Suite.
Please investigate and take appropriate action.

Best regards,
Cancer Genomics Analysis Suite
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            text = msg.as_string()
            server.sendmail(self.from_email, self.to_emails, text)
            server.quit()
            
            logger.info(f"Email notification sent successfully for alert {alert.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification for alert {alert.id}: {e}")
            return False


class AlertMonitor:
    """
    Monitors system health and triggers alerts.
    
    Features:
    - System resource monitoring
    - Analysis status monitoring
    - Custom alert rules
    - Alert escalation
    - Historical metrics tracking
    - Alert suppression
    """
    
    def __init__(self, db_path: str = None, check_interval: int = 60):
        """
        Initialize alert monitor.
        
        Args:
            db_path: Path to SQLite database file
            check_interval: Monitoring check interval in seconds
        """
        self.db_path = db_path or str(Path(__file__).parent / 'alert_monitor.db')
        self.check_interval = check_interval
        self.is_running = False
        self.monitor_thread = None
        self.alert_handlers = []
        self.alert_rules = {}
        
        # Notification channels
        self.slack_notifier = None
        self.teams_notifier = None
        self.email_notifier = None
        self.notification_enabled = True
        self.notification_retry_count = 3
        self.notification_retry_delay = 5  # seconds
        
        # Initialize database
        self._init_database()
        
        # Set up default alert rules
        self._setup_default_rules()
    
    def _init_database(self):
        """Initialize SQLite database for alerts and metrics."""
        with sqlite3.connect(self.db_path) as conn:
            # Alerts table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT,
                    acknowledged_by TEXT,
                    acknowledged_at TEXT,
                    metadata TEXT
                )
            ''')
            
            # Metrics table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    cpu_percent REAL NOT NULL,
                    memory_percent REAL NOT NULL,
                    disk_percent REAL NOT NULL,
                    active_connections INTEGER NOT NULL,
                    queue_size INTEGER NOT NULL,
                    failed_analyses INTEGER NOT NULL,
                    completed_analyses INTEGER NOT NULL
                )
            ''')
            
            # Create indexes
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_alerts_status_severity 
                ON alerts(status, severity, created_at)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp 
                ON metrics(timestamp)
            ''')
    
    def _setup_default_rules(self):
        """Set up default alert rules."""
        self.alert_rules = {
            'high_cpu': {
                'condition': lambda metrics: metrics.cpu_percent > 80,
                'severity': AlertSeverity.WARNING,
                'title': 'High CPU Usage',
                'description': 'CPU usage is above 80%'
            },
            'critical_cpu': {
                'condition': lambda metrics: metrics.cpu_percent > 95,
                'severity': AlertSeverity.CRITICAL,
                'title': 'Critical CPU Usage',
                'description': 'CPU usage is above 95%'
            },
            'high_memory': {
                'condition': lambda metrics: metrics.memory_percent > 85,
                'severity': AlertSeverity.WARNING,
                'title': 'High Memory Usage',
                'description': 'Memory usage is above 85%'
            },
            'critical_memory': {
                'condition': lambda metrics: metrics.memory_percent > 95,
                'severity': AlertSeverity.CRITICAL,
                'title': 'Critical Memory Usage',
                'description': 'Memory usage is above 95%'
            },
            'high_disk': {
                'condition': lambda metrics: metrics.disk_percent > 90,
                'severity': AlertSeverity.WARNING,
                'title': 'High Disk Usage',
                'description': 'Disk usage is above 90%'
            },
            'large_queue': {
                'condition': lambda metrics: metrics.queue_size > 100,
                'severity': AlertSeverity.WARNING,
                'title': 'Large Processing Queue',
                'description': 'Processing queue has more than 100 items'
            },
            'high_failure_rate': {
                'condition': lambda metrics: metrics.failed_analyses > 10 and 
                                           metrics.completed_analyses > 0 and
                                           (metrics.failed_analyses / (metrics.completed_analyses + metrics.failed_analyses)) > 0.2,
                'severity': AlertSeverity.ERROR,
                'title': 'High Analysis Failure Rate',
                'description': 'Analysis failure rate is above 20%'
            }
        }
    
    def start_monitoring(self):
        """Start the monitoring thread."""
        if not self.is_running:
            self.is_running = True
            self.monitor_thread = threading.Thread(
                target=self._monitoring_loop,
                name="AlertMonitor",
                daemon=True
            )
            self.monitor_thread.start()
            logger.info("Alert monitoring started")
    
    def stop_monitoring(self):
        """Stop the monitoring thread."""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Alert monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.is_running:
            try:
                # Collect system metrics
                metrics = self._collect_metrics()
                
                # Store metrics
                self._store_metrics(metrics)
                
                # Check alert rules
                self._check_alert_rules(metrics)
                
                # Wait for next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Monitoring error: {str(e)}")
                time.sleep(self.check_interval)
    
    def _collect_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        try:
            # System resource metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Application-specific metrics (these would be provided by the main application)
            active_connections = self._get_active_connections()
            queue_size = self._get_queue_size()
            failed_analyses = self._get_failed_analyses_count()
            completed_analyses = self._get_completed_analyses_count()
            
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk.percent,
                active_connections=active_connections,
                queue_size=queue_size,
                failed_analyses=failed_analyses,
                completed_analyses=completed_analyses
            )
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {str(e)}")
            # Return default metrics on error
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=0,
                memory_percent=0,
                disk_percent=0,
                active_connections=0,
                queue_size=0,
                failed_analyses=0,
                completed_analyses=0
            )
    
    def _get_active_connections(self) -> int:
        """Get number of active database connections."""
        # This would be implemented based on your database setup
        return 0
    
    def _get_queue_size(self) -> int:
        """Get current processing queue size."""
        # This would be implemented based on your queue system
        return 0
    
    def _get_failed_analyses_count(self) -> int:
        """Get count of failed analyses in the last hour."""
        # This would be implemented based on your analysis tracking
        return 0
    
    def _get_completed_analyses_count(self) -> int:
        """Get count of completed analyses in the last hour."""
        # This would be implemented based on your analysis tracking
        return 0
    
    def _store_metrics(self, metrics: SystemMetrics):
        """Store metrics in database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO metrics (
                    timestamp, cpu_percent, memory_percent, disk_percent,
                    active_connections, queue_size, failed_analyses, completed_analyses
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.timestamp.isoformat(),
                metrics.cpu_percent,
                metrics.memory_percent,
                metrics.disk_percent,
                metrics.active_connections,
                metrics.queue_size,
                metrics.failed_analyses,
                metrics.completed_analyses
            ))
    
    def _check_alert_rules(self, metrics: SystemMetrics):
        """Check alert rules against current metrics."""
        for rule_name, rule in self.alert_rules.items():
            try:
                if rule['condition'](metrics):
                    # Check if alert already exists and is active
                    if not self._has_active_alert(rule_name):
                        self._create_alert(
                            title=rule['title'],
                            description=rule['description'],
                            severity=rule['severity'],
                            source=f"monitor.{rule_name}",
                            metadata={'metrics': metrics.to_dict()}
                        )
                else:
                    # Condition no longer met, resolve any active alerts
                    self._resolve_alert_by_source(f"monitor.{rule_name}")
                    
            except Exception as e:
                logger.error(f"Error checking rule {rule_name}: {str(e)}")
    
    def _has_active_alert(self, rule_name: str) -> bool:
        """Check if there's an active alert for a rule."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT COUNT(*) FROM alerts 
                WHERE source = ? AND status = 'active'
            ''', (f"monitor.{rule_name}",))
            
            return cursor.fetchone()[0] > 0
    
    def _create_alert(self, title: str, description: str, severity: AlertSeverity,
                     source: str, metadata: Dict[str, Any] = None) -> str:
        """Create a new alert."""
        alert_id = str(uuid.uuid4())
        alert = Alert(
            id=alert_id,
            title=title,
            description=description,
            severity=severity,
            status=AlertStatus.ACTIVE,
            source=source,
            created_at=datetime.now(),
            metadata=metadata or {}
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO alerts (
                    id, title, description, severity, status, source,
                    created_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.id, alert.title, alert.description,
                alert.severity.value, alert.status.value,
                alert.source, alert.created_at.isoformat(),
                json.dumps(alert.metadata)
            ))
        
        # Notify alert handlers
        self._notify_alert_handlers(alert)
        
        logger.info(f"Created alert: {title} ({severity.value})")
        return alert_id
    
    def _resolve_alert_by_source(self, source: str):
        """Resolve all active alerts from a specific source."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE alerts 
                SET status = 'resolved', resolved_at = ?
                WHERE source = ? AND status = 'active'
            ''', (datetime.now().isoformat(), source))
    
    def _notify_alert_handlers(self, alert: Alert):
        """Notify registered alert handlers and send notifications."""
        # Notify custom alert handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {str(e)}")
        
        # Send webhook and email notifications
        self._send_notifications(alert)
    
    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Add an alert handler function."""
        self.alert_handlers.append(handler)
        logger.info("Added alert handler")
    
    def add_alert_rule(self, name: str, condition: Callable[[SystemMetrics], bool],
                      severity: AlertSeverity, title: str, description: str):
        """Add a custom alert rule."""
        self.alert_rules[name] = {
            'condition': condition,
            'severity': severity,
            'title': title,
            'description': description
        }
        logger.info(f"Added alert rule: {name}")
    
    def setup_slack_notification(self, webhook_url: str, timeout: int = 30):
        """Set up Slack webhook notification."""
        try:
            self.slack_notifier = SlackNotifier(webhook_url, timeout)
            logger.info("Slack notification configured")
        except Exception as e:
            logger.error(f"Failed to configure Slack notification: {e}")
    
    def setup_teams_notification(self, webhook_url: str, timeout: int = 30):
        """Set up Microsoft Teams webhook notification."""
        try:
            self.teams_notifier = TeamsNotifier(webhook_url, timeout)
            logger.info("Teams notification configured")
        except Exception as e:
            logger.error(f"Failed to configure Teams notification: {e}")
    
    def setup_email_notification(self, smtp_server: str, smtp_port: int, 
                                username: str, password: str, from_email: str, 
                                to_emails: List[str]):
        """Set up email notification fallback."""
        try:
            self.email_notifier = EmailNotifier(
                smtp_server, smtp_port, username, password, from_email, to_emails
            )
            logger.info("Email notification configured")
        except Exception as e:
            logger.error(f"Failed to configure email notification: {e}")
    
    def enable_notifications(self, enabled: bool = True):
        """Enable or disable notifications."""
        self.notification_enabled = enabled
        logger.info(f"Notifications {'enabled' if enabled else 'disabled'}")
    
    def _send_notifications(self, alert: Alert):
        """Send notifications through all configured channels."""
        if not self.notification_enabled:
            return
        
        # Send Slack notification
        if self.slack_notifier:
            self._send_with_retry(self.slack_notifier, alert, "Slack")
        
        # Send Teams notification
        if self.teams_notifier:
            self._send_with_retry(self.teams_notifier, alert, "Teams")
        
        # Send email notification (fallback)
        if self.email_notifier:
            self._send_with_retry(self.email_notifier, alert, "Email")
    
    def _send_with_retry(self, notifier, alert: Alert, channel_name: str):
        """Send notification with retry logic."""
        for attempt in range(self.notification_retry_count):
            try:
                success = notifier.send_alert(alert)
                if success:
                    logger.info(f"{channel_name} notification sent successfully for alert {alert.id}")
                    return
                else:
                    logger.warning(f"{channel_name} notification failed for alert {alert.id}, attempt {attempt + 1}")
            except Exception as e:
                logger.error(f"{channel_name} notification error for alert {alert.id}, attempt {attempt + 1}: {e}")
            
            if attempt < self.notification_retry_count - 1:
                time.sleep(self.notification_retry_delay)
        
        logger.error(f"Failed to send {channel_name} notification for alert {alert.id} after {self.notification_retry_count} attempts")
    
    def get_active_alerts(self, severity: AlertSeverity = None) -> List[Alert]:
        """Get active alerts, optionally filtered by severity."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if severity:
                cursor = conn.execute('''
                    SELECT * FROM alerts 
                    WHERE status = 'active' AND severity = ?
                    ORDER BY created_at DESC
                ''', (severity.value,))
            else:
                cursor = conn.execute('''
                    SELECT * FROM alerts 
                    WHERE status = 'active'
                    ORDER BY severity DESC, created_at DESC
                ''')
            
            return [Alert.from_dict(dict(row)) for row in cursor]
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                UPDATE alerts 
                SET status = 'acknowledged', acknowledged_by = ?, acknowledged_at = ?
                WHERE id = ? AND status = 'active'
            ''', (acknowledged_by, datetime.now().isoformat(), alert_id))
            
            return cursor.rowcount > 0
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                UPDATE alerts 
                SET status = 'resolved', resolved_at = ?
                WHERE id = ? AND status IN ('active', 'acknowledged')
            ''', (datetime.now().isoformat(), alert_id))
            
            return cursor.rowcount > 0
    
    def get_metrics_history(self, hours: int = 24) -> List[SystemMetrics]:
        """Get metrics history for the specified number of hours."""
        since = datetime.now() - timedelta(hours=hours)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM metrics 
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
            ''', (since.isoformat(),))
            
            return [SystemMetrics(
                timestamp=datetime.fromisoformat(row['timestamp']),
                cpu_percent=row['cpu_percent'],
                memory_percent=row['memory_percent'],
                disk_percent=row['disk_percent'],
                active_connections=row['active_connections'],
                queue_size=row['queue_size'],
                failed_analyses=row['failed_analyses'],
                completed_analyses=row['completed_analyses']
            ) for row in cursor]
    
    def get_alert_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get alert statistics for the specified number of days."""
        since = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Count by severity
            cursor = conn.execute('''
                SELECT severity, COUNT(*) as count 
                FROM alerts 
                WHERE created_at >= ?
                GROUP BY severity
            ''', (since.isoformat(),))
            severity_counts = {row['severity']: row['count'] for row in cursor}
            
            # Count by status
            cursor = conn.execute('''
                SELECT status, COUNT(*) as count 
                FROM alerts 
                WHERE created_at >= ?
                GROUP BY status
            ''', (since.isoformat(),))
            status_counts = {row['status']: row['count'] for row in cursor}
            
            # Average resolution time
            cursor = conn.execute('''
                SELECT AVG(
                    (julianday(resolved_at) - julianday(created_at)) * 24 * 60
                ) as avg_resolution_minutes
                FROM alerts 
                WHERE resolved_at IS NOT NULL AND created_at >= ?
            ''', (since.isoformat(),))
            avg_resolution = cursor.fetchone()['avg_resolution_minutes'] or 0
        
        return {
            'severity_counts': severity_counts,
            'status_counts': status_counts,
            'average_resolution_minutes': avg_resolution,
            'period_days': days
        }
    
    def cleanup_old_data(self, days: int = 30):
        """Clean up old alerts and metrics."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            # Clean up old resolved alerts
            conn.execute('''
                DELETE FROM alerts 
                WHERE status = 'resolved' AND resolved_at < ?
            ''', (cutoff_date.isoformat(),))
            
            # Clean up old metrics
            conn.execute('''
                DELETE FROM metrics 
                WHERE timestamp < ?
            ''', (cutoff_date.isoformat(),))
            
            logger.info(f"Cleaned up data older than {days} days")
