#!/usr/bin/env python3
"""
Test Webhook Notifications

This script provides a simple way to test the webhook notification functionality
without running the full monitoring system.
"""

import logging
import os
import sys
from pathlib import Path
from datetime import datetime
import uuid

# Add the parent directory to the path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from modules.notifications.alert_monitor import (
    AlertMonitor,
    Alert,
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

def create_test_alert(severity: AlertSeverity, title: str, description: str) -> Alert:
    """Create a test alert with the specified parameters."""
    return Alert(
        id=str(uuid.uuid4()),
        title=title,
        description=description,
        severity=severity,
        status=AlertStatus.ACTIVE,
        source="test.webhook",
        created_at=datetime.now(),
        metadata={
            "test_mode": True,
            "test_timestamp": datetime.now().isoformat(),
            "test_severity": severity.value
        }
    )

def test_slack_webhook(webhook_url: str):
    """Test Slack webhook notification."""
    logger.info("Testing Slack webhook notification...")
    
    try:
        notifier = SlackNotifier(webhook_url)
        
        # Create test alerts for different severities
        test_alerts = [
            create_test_alert(AlertSeverity.INFO, "Test Info Alert", "This is a test info alert from the Cancer Genomics Analysis Suite."),
            create_test_alert(AlertSeverity.WARNING, "Test Warning Alert", "This is a test warning alert indicating a potential issue."),
            create_test_alert(AlertSeverity.ERROR, "Test Error Alert", "This is a test error alert indicating a problem that needs attention."),
            create_test_alert(AlertSeverity.CRITICAL, "Test Critical Alert", "This is a test critical alert requiring immediate action.")
        ]
        
        for alert in test_alerts:
            logger.info(f"Sending {alert.severity.value} alert to Slack...")
            success = notifier.send_alert(alert)
            if success:
                logger.info(f"✅ {alert.severity.value} alert sent successfully to Slack")
            else:
                logger.error(f"❌ Failed to send {alert.severity.value} alert to Slack")
            
            # Wait a moment between alerts
            import time
            time.sleep(2)
            
    except Exception as e:
        logger.error(f"❌ Error testing Slack webhook: {e}")

def test_teams_webhook(webhook_url: str):
    """Test Microsoft Teams webhook notification."""
    logger.info("Testing Microsoft Teams webhook notification...")
    
    try:
        notifier = TeamsNotifier(webhook_url)
        
        # Create test alerts for different severities
        test_alerts = [
            create_test_alert(AlertSeverity.INFO, "Test Info Alert", "This is a test info alert from the Cancer Genomics Analysis Suite."),
            create_test_alert(AlertSeverity.WARNING, "Test Warning Alert", "This is a test warning alert indicating a potential issue."),
            create_test_alert(AlertSeverity.ERROR, "Test Error Alert", "This is a test error alert indicating a problem that needs attention."),
            create_test_alert(AlertSeverity.CRITICAL, "Test Critical Alert", "This is a test critical alert requiring immediate action.")
        ]
        
        for alert in test_alerts:
            logger.info(f"Sending {alert.severity.value} alert to Teams...")
            success = notifier.send_alert(alert)
            if success:
                logger.info(f"✅ {alert.severity.value} alert sent successfully to Teams")
            else:
                logger.error(f"❌ Failed to send {alert.severity.value} alert to Teams")
            
            # Wait a moment between alerts
            import time
            time.sleep(2)
            
    except Exception as e:
        logger.error(f"❌ Error testing Teams webhook: {e}")

def test_email_notification(smtp_server: str, smtp_port: int, username: str, password: str, from_email: str, to_emails: list):
    """Test email notification."""
    logger.info("Testing email notification...")
    
    try:
        notifier = EmailNotifier(smtp_server, smtp_port, username, password, from_email, to_emails)
        
        # Create a test alert
        test_alert = create_test_alert(
            AlertSeverity.CRITICAL,
            "Test Email Alert",
            "This is a test email alert from the Cancer Genomics Analysis Suite to verify email notification functionality."
        )
        
        logger.info("Sending test alert via email...")
        success = notifier.send_alert(test_alert)
        if success:
            logger.info("✅ Test alert sent successfully via email")
        else:
            logger.error("❌ Failed to send test alert via email")
            
    except Exception as e:
        logger.error(f"❌ Error testing email notification: {e}")

def test_alert_monitor_integration():
    """Test the full alert monitor with webhook integration."""
    logger.info("Testing Alert Monitor with webhook integration...")
    
    try:
        # Initialize monitor
        monitor = AlertMonitor()
        
        slack_url = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
        teams_url = os.environ.get("TEAMS_WEBHOOK_URL", "").strip()
        if slack_url:
            monitor.setup_slack_notification(slack_url)
        if teams_url:
            monitor.setup_teams_notification(teams_url)
        
        # Create a test alert
        test_alert = create_test_alert(
            AlertSeverity.ERROR,
            "Integration Test Alert",
            "This is a test alert to verify the integration between AlertMonitor and webhook notifications."
        )
        
        # Manually trigger notifications
        logger.info("Triggering webhook notifications through AlertMonitor...")
        monitor._send_notifications(test_alert)
        
        logger.info("✅ AlertMonitor webhook integration test completed")
        
    except Exception as e:
        logger.error(f"❌ Error testing AlertMonitor integration: {e}")

def main():
    """Main test function."""
    logger.info("Starting Webhook Notification Tests")
    
    # Set SLACK_WEBHOOK_URL and TEAMS_WEBHOOK_URL in the environment
    SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
    TEAMS_WEBHOOK_URL = os.environ.get("TEAMS_WEBHOOK_URL", "")
    
    # Email configuration - Replace with your actual SMTP settings
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USERNAME = "your-email@gmail.com"
    SMTP_PASSWORD = "your-app-password"
    FROM_EMAIL = "your-email@gmail.com"
    TO_EMAILS = ["admin@your-org.com"]
    
    print("=" * 60)
    print("WEBHOOK NOTIFICATION TEST")
    print("=" * 60)
    print()
    print("⚠️  IMPORTANT: Before running this test, please update the webhook URLs")
    print("   and email settings in this script with your actual values.")
    print()
    print("Current configuration:")
    print(
        f"  Slack Webhook: {(SLACK_WEBHOOK_URL or '(not set)')[:50]}"
        + ("..." if len(SLACK_WEBHOOK_URL) > 50 else "")
    )
    print(
        f"  Teams Webhook: {(TEAMS_WEBHOOK_URL or '(not set)')[:50]}"
        + ("..." if len(TEAMS_WEBHOOK_URL) > 50 else "")
    )
    print(f"  Email SMTP: {SMTP_SERVER}:{SMTP_PORT}")
    print()
    
    # Ask for confirmation
    response = input("Do you want to proceed with the test? (y/N): ").strip().lower()
    if response != 'y':
        print("Test cancelled.")
        return
    
    try:
        # Test individual webhook notifications
        print("\n1. Testing Slack webhook...")
        test_slack_webhook(SLACK_WEBHOOK_URL)
        
        print("\n2. Testing Teams webhook...")
        test_teams_webhook(TEAMS_WEBHOOK_URL)
        
        print("\n3. Testing email notification...")
        test_email_notification(SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, FROM_EMAIL, TO_EMAILS)
        
        print("\n4. Testing AlertMonitor integration...")
        test_alert_monitor_integration()
        
        print("\n✅ All webhook notification tests completed!")
        print("\nCheck your Slack channel, Teams channel, and email inbox for test messages.")
        
    except Exception as e:
        logger.error(f"❌ Error during webhook tests: {e}")
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    main()
