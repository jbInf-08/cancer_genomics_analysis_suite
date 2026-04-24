#!/usr/bin/env python3
"""
Alert Monitor Webhook Fallback Example

This script demonstrates how to set up and use the Slack/Teams webhook fallback
functionality in the Cancer Genomics Analysis Suite alert monitoring system.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the parent directory to the path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from modules.notifications.alert_monitor import (
    AlertMonitor, 
    AlertSeverity, 
    AlertStatus,
    SlackNotifier,
    TeamsNotifier,
    EmailNotifier
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def demonstrate_webhook_setup():
    """Demonstrate how to set up webhook notifications."""
    logger.info("=== Webhook Setup Example ===")
    
    # Initialize alert monitor
    monitor = AlertMonitor()
    
    # Example 1: Slack Webhook Setup (set SLACK_WEBHOOK_URL in the environment)
    logger.info("Setting up Slack webhook notification...")
    slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if not slack_webhook_url:
        logger.warning("SLACK_WEBHOOK_URL is not set; skipping Slack example")
    else:
        try:
            monitor.setup_slack_notification(slack_webhook_url, timeout=30)
            logger.info("✅ Slack notification configured successfully")
        except Exception as e:
            logger.error(f"❌ Failed to configure Slack notification: {e}")
    
    # Example 2: Microsoft Teams Webhook Setup
    logger.info("Setting up Microsoft Teams webhook notification...")
    teams_webhook_url = os.environ.get("TEAMS_WEBHOOK_URL", "").strip()
    if not teams_webhook_url:
        logger.warning("TEAMS_WEBHOOK_URL is not set; using placeholder (will likely fail to register)")
        teams_webhook_url = "https://example.invalid/webhook"
    
    try:
        monitor.setup_teams_notification(teams_webhook_url, timeout=30)
        logger.info("✅ Teams notification configured successfully")
    except Exception as e:
        logger.error(f"❌ Failed to configure Teams notification: {e}")
    
    # Example 3: Email Fallback Setup
    logger.info("Setting up email fallback notification...")
    try:
        monitor.setup_email_notification(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="your-email@gmail.com",
            password="your-app-password",  # Use app-specific password for Gmail
            from_email="your-email@gmail.com",
            to_emails=["admin@your-org.com", "alerts@your-org.com", "devops@your-org.com"]
        )
        logger.info("✅ Email notification configured successfully")
    except Exception as e:
        logger.error(f"❌ Failed to configure email notification: {e}")
    
    return monitor

def demonstrate_alert_creation(monitor):
    """Demonstrate creating alerts that will trigger webhook notifications."""
    logger.info("\n=== Alert Creation Example ===")
    
    # Create a test alert
    from modules.notifications.alert_monitor import Alert
    from datetime import datetime
    import uuid
    
    test_alert = Alert(
        id=str(uuid.uuid4()),
        title="High CPU Usage Detected",
        description="CPU usage has exceeded 90% for the past 5 minutes. This may indicate a performance issue or resource bottleneck.",
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.ACTIVE,
        source="system.monitor.cpu",
        created_at=datetime.now(),
        metadata={
            "cpu_percent": 92.5,
            "memory_percent": 78.3,
            "disk_percent": 45.2,
            "active_connections": 156,
            "queue_size": 23,
            "server": "genomics-server-01",
            "region": "us-east-1"
        }
    )
    
    logger.info(f"Created test alert: {test_alert.title}")
    logger.info(f"Alert ID: {test_alert.id}")
    logger.info(f"Severity: {test_alert.severity.value}")
    
    # Manually trigger notifications (this would normally be called by the monitor)
    monitor._send_notifications(test_alert)
    
    return test_alert

def demonstrate_custom_alert_rules(monitor):
    """Demonstrate adding custom alert rules that will trigger webhook notifications."""
    logger.info("\n=== Custom Alert Rules Example ===")
    
    # Add custom alert rules
    monitor.add_alert_rule(
        name="disk_space_critical",
        condition=lambda metrics: metrics.disk_percent > 95,
        severity=AlertSeverity.CRITICAL,
        title="Critical Disk Space",
        description="Disk usage is above 95% - immediate action required"
    )
    
    monitor.add_alert_rule(
        name="memory_usage_high",
        condition=lambda metrics: metrics.memory_percent > 85,
        severity=AlertSeverity.WARNING,
        title="High Memory Usage",
        description="Memory usage is above 85% - monitor closely"
    )
    
    monitor.add_alert_rule(
        name="queue_backlog",
        condition=lambda metrics: metrics.queue_size > 50,
        severity=AlertSeverity.ERROR,
        title="Processing Queue Backlog",
        description="Processing queue has more than 50 pending jobs"
    )
    
    logger.info("✅ Added custom alert rules:")
    logger.info("  - disk_space_critical (Critical)")
    logger.info("  - memory_usage_high (Warning)")
    logger.info("  - queue_backlog (Error)")

def demonstrate_notification_priority():
    """Demonstrate notification priority and fallback behavior."""
    logger.info("\n=== Notification Priority Example ===")
    
    # Create a monitor with different notification channels
    monitor = AlertMonitor()
    
    # Set up notifications in priority order
    logger.info("Setting up notification channels in priority order...")
    
    # Primary: Slack (fastest, most visible) — set SLACK_WEBHOOK_URL / TEAMS_WEBHOOK_URL
    slack = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if slack:
        monitor.setup_slack_notification(slack)
    teams = os.environ.get("TEAMS_WEBHOOK_URL", "").strip()
    if teams:
        monitor.setup_teams_notification(teams)
    
    # Fallback: Email (most reliable, but slower)
    monitor.setup_email_notification(
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        username="your-email@gmail.com",
        password="your-app-password",
        from_email="your-email@gmail.com",
        to_emails=["admin@your-org.com"]
    )
    
    # Configure retry behavior
    monitor.notification_retry_count = 3
    monitor.notification_retry_delay = 5  # seconds
    
    logger.info("✅ Notification channels configured with fallback priority:")
    logger.info("  1. Slack (Primary - Fast)")
    logger.info("  2. Teams (Secondary - Enterprise)")
    logger.info("  3. Email (Fallback - Reliable)")
    logger.info(f"  Retry attempts: {monitor.notification_retry_count}")
    logger.info(f"  Retry delay: {monitor.notification_retry_delay} seconds")

def demonstrate_webhook_formatting():
    """Demonstrate the different webhook message formats."""
    logger.info("\n=== Webhook Message Formatting Example ===")
    
    from modules.notifications.alert_monitor import Alert
    from datetime import datetime
    import uuid
    
    # Create different types of alerts to show formatting
    alerts = [
        Alert(
            id=str(uuid.uuid4()),
            title="System Startup Complete",
            description="All services have started successfully and are ready to process requests.",
            severity=AlertSeverity.INFO,
            status=AlertStatus.ACTIVE,
            source="system.startup",
            created_at=datetime.now(),
            metadata={"startup_time": "45.2s", "services_started": 12}
        ),
        Alert(
            id=str(uuid.uuid4()),
            title="Database Connection Pool Exhausted",
            description="All database connections are in use. New requests may be queued or rejected.",
            severity=AlertSeverity.ERROR,
            status=AlertStatus.ACTIVE,
            source="database.connection_pool",
            created_at=datetime.now(),
            metadata={
                "active_connections": 100,
                "max_connections": 100,
                "queued_requests": 15,
                "database": "genomics_db"
            }
        ),
        Alert(
            id=str(uuid.uuid4()),
            title="Pipeline Execution Failed",
            description="RNA-seq analysis pipeline failed during alignment step. Check logs for details.",
            severity=AlertSeverity.CRITICAL,
            status=AlertStatus.ACTIVE,
            source="pipeline.rna_seq_analysis",
            created_at=datetime.now(),
            metadata={
                "pipeline_id": "rna_seq_001",
                "sample_id": "SAMPLE_001",
                "failed_step": "hisat2_alignment",
                "error_code": "ALIGNMENT_FAILED",
                "execution_time": "2h 15m"
            }
        )
    ]
    
    # Show how each alert would be formatted for different channels
    for alert in alerts:
        logger.info(f"\nAlert: {alert.title} ({alert.severity.value})")
        
        # Slack formatting
        slack_notifier = SlackNotifier("dummy_url")
        slack_payload = slack_notifier._format_payload(alert)
        logger.info("Slack format:")
        logger.info(f"  Title: {slack_payload['attachments'][0]['title']}")
        logger.info(f"  Color: {slack_payload['attachments'][0]['color']}")
        logger.info(f"  Fields: {len(slack_payload['attachments'][0]['fields'])}")
        
        # Teams formatting
        teams_notifier = TeamsNotifier("dummy_url")
        teams_payload = teams_notifier._format_payload(alert)
        logger.info("Teams format:")
        logger.info(f"  Summary: {teams_payload['summary']}")
        logger.info(f"  Theme Color: {teams_payload['themeColor']}")
        logger.info(f"  Facts: {len(teams_payload['sections'][0]['facts'])}")

def demonstrate_monitoring_integration():
    """Demonstrate how the webhook notifications integrate with the monitoring system."""
    logger.info("\n=== Monitoring Integration Example ===")
    
    # Initialize monitor with webhook notifications
    monitor = AlertMonitor()
    
    # Set up notifications (from environment)
    slack = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    teams = os.environ.get("TEAMS_WEBHOOK_URL", "").strip()
    if slack:
        monitor.setup_slack_notification(slack)
    if teams:
        monitor.setup_teams_notification(teams)
    
    # Add custom alert rules
    monitor.add_alert_rule(
        name="pipeline_failure_rate",
        condition=lambda metrics: metrics.failed_analyses > 5 and metrics.completed_analyses > 0,
        severity=AlertSeverity.ERROR,
        title="High Pipeline Failure Rate",
        description="Multiple pipeline executions have failed recently"
    )
    
    # Start monitoring (this would normally run continuously)
    logger.info("Starting monitoring with webhook notifications...")
    monitor.start_monitoring()
    
    # Let it run for a few seconds to demonstrate
    import time
    time.sleep(3)
    
    # Check for any alerts that were created
    active_alerts = monitor.get_active_alerts()
    logger.info(f"Active alerts: {len(active_alerts)}")
    
    for alert in active_alerts:
        logger.info(f"  - {alert.title} ({alert.severity.value}) from {alert.source}")
    
    # Stop monitoring
    monitor.stop_monitoring()
    logger.info("Monitoring stopped")

def main():
    """Main example function."""
    logger.info("Starting Alert Monitor Webhook Fallback Example")
    
    try:
        # Demonstrate webhook setup
        monitor = demonstrate_webhook_setup()
        
        # Demonstrate alert creation
        test_alert = demonstrate_alert_creation(monitor)
        
        # Demonstrate custom alert rules
        demonstrate_custom_alert_rules(monitor)
        
        # Demonstrate notification priority
        demonstrate_notification_priority()
        
        # Demonstrate webhook formatting
        demonstrate_webhook_formatting()
        
        # Demonstrate monitoring integration
        demonstrate_monitoring_integration()
        
        logger.info("\n✅ All webhook fallback examples completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error in webhook example: {e}")
        raise

if __name__ == "__main__":
    main()
