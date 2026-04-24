#!/usr/bin/env python3
"""
NGS Pipeline Integration Usage Example

This script demonstrates how to use the NGS Pipeline integration features
of the Cancer Genomics Analysis Suite.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the parent directory to the path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from modules.ngs_platform_support import (
    EnhancedWorkflowDispatcher,
    PipelineDefinition,
    PipelineStatus,
    PipelineType
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main example function."""
    logger.info("Starting NGS Pipeline Integration Example")
    
    # Initialize the enhanced workflow dispatcher
    dispatcher = EnhancedWorkflowDispatcher()
    
    try:
        # Example 1: Load a pipeline definition
        logger.info("Example 1: Loading pipeline definition")
        pipeline_path = Path(__file__).parent / "example_ngs_pipeline.yaml"
        
        if pipeline_path.exists():
            pipeline = await dispatcher.load_pipeline(pipeline_path)
            logger.info(f"Loaded pipeline: {pipeline.name} v{pipeline.version}")
            logger.info(f"Pipeline type: {pipeline.pipeline_type.value}")
            logger.info(f"Number of steps: {len(pipeline.steps)}")
            
            # List all steps
            for i, step in enumerate(pipeline.steps, 1):
                logger.info(f"  Step {i}: {step.name}")
                logger.info(f"    Command: {step.command[:100]}...")
                logger.info(f"    Dependencies: {step.dependencies}")
        else:
            logger.warning(f"Pipeline file not found: {pipeline_path}")
            return
        
        # Example 2: Execute a pipeline
        logger.info("\nExample 2: Executing pipeline")
        
        # Define inputs for the pipeline
        inputs = {
            "fastq_files": "/path/to/sample_R1.fastq.gz,/path/to/sample_R2.fastq.gz",
            "reference_genome": "/path/to/reference.fa",
            "gtf_annotation": "/path/to/annotation.gtf",
            "sample_name": "sample_001"
        }
        
        # Define parameters
        parameters = {
            "threads": 8,
            "memory": "32G",
            "quality_threshold": 20,
            "output_dir": "/path/to/output"
        }
        
        # Execute the pipeline
        execution_id = await dispatcher.execute_pipeline(
            pipeline_name=pipeline.name,
            inputs=inputs,
            parameters=parameters
        )
        
        logger.info(f"Pipeline execution started with ID: {execution_id}")
        
        # Example 3: Monitor pipeline execution
        logger.info("\nExample 3: Monitoring pipeline execution")
        
        # Check status multiple times
        for i in range(5):
            await asyncio.sleep(2)  # Wait 2 seconds between checks
            
            try:
                execution = await dispatcher.get_pipeline_status(execution_id)
                logger.info(f"Execution status: {execution.status.value}")
                logger.info(f"Progress: {execution.progress:.1f}%")
                
                if execution.current_step:
                    logger.info(f"Current step: {execution.current_step}")
                
                if execution.status in [PipelineStatus.COMPLETED, PipelineStatus.FAILED, PipelineStatus.CANCELLED]:
                    logger.info(f"Pipeline execution finished with status: {execution.status.value}")
                    if execution.error_message:
                        logger.error(f"Error message: {execution.error_message}")
                    break
                    
            except Exception as e:
                logger.error(f"Error checking execution status: {e}")
        
        # Example 4: List available pipelines
        logger.info("\nExample 4: Listing available pipelines")
        pipelines = await dispatcher.list_available_pipelines()
        logger.info(f"Available pipelines: {len(pipelines)}")
        
        for pipeline in pipelines:
            logger.info(f"  - {pipeline.name} v{pipeline.version} ({pipeline.pipeline_type.value})")
        
        # Example 5: Get pipeline logs
        logger.info("\nExample 5: Getting pipeline logs")
        try:
            logs = await dispatcher.pipeline_manager.get_pipeline_logs(execution_id)
            logger.info(f"Pipeline logs ({len(logs)} entries):")
            for log_entry in logs[-5:]:  # Show last 5 log entries
                logger.info(f"  {log_entry}")
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
        
        # Example 6: Cleanup old executions
        logger.info("\nExample 6: Cleaning up old executions")
        cleaned_count = await dispatcher.cleanup_pipeline_executions(days_old=7)
        logger.info(f"Cleaned up {cleaned_count} old executions")
        
    except Exception as e:
        logger.error(f"Error in main example: {e}")
        raise
    
    logger.info("NGS Pipeline Integration Example completed")

async def demonstrate_alert_monitoring():
    """Demonstrate alert monitoring with webhook notifications."""
    logger.info("\n=== Alert Monitoring Example ===")
    
    from modules.notifications.alert_monitor import (
        AlertMonitor, AlertSeverity, AlertStatus
    )
    
    # Initialize alert monitor
    monitor = AlertMonitor()
    
    # Set up Slack notification (example - replace with real webhook URL)
    slack_webhook_url = "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
    # monitor.setup_slack_notification(slack_webhook_url)
    
    # Set up Teams notification (example - replace with real webhook URL)
    teams_webhook_url = "https://your-org.webhook.office.com/webhookb2/YOUR-TEAMS-WEBHOOK"
    # monitor.setup_teams_notification(teams_webhook_url)
    
    # Set up email notification (example - replace with real SMTP settings)
    # monitor.setup_email_notification(
    #     smtp_server="smtp.gmail.com",
    #     smtp_port=587,
    #     username="your-email@gmail.com",
    #     password="your-app-password",
    #     from_email="your-email@gmail.com",
    #     to_emails=["admin@your-org.com", "alerts@your-org.com"]
    # )
    
    # Add a custom alert rule
    monitor.add_alert_rule(
        name="custom_high_cpu",
        condition=lambda metrics: metrics.cpu_percent > 90,
        severity=AlertSeverity.CRITICAL,
        title="Custom High CPU Alert",
        description="CPU usage is above 90%"
    )
    
    # Start monitoring
    monitor.start_monitoring()
    
    # Let it run for a few seconds
    await asyncio.sleep(5)
    
    # Get active alerts
    active_alerts = monitor.get_active_alerts()
    logger.info(f"Active alerts: {len(active_alerts)}")
    
    for alert in active_alerts:
        logger.info(f"  - {alert.title} ({alert.severity.value})")
    
    # Stop monitoring
    monitor.stop_monitoring()
    
    logger.info("Alert monitoring example completed")

if __name__ == "__main__":
    # Run the main example
    asyncio.run(main())
    
    # Run the alert monitoring example
    asyncio.run(demonstrate_alert_monitoring())
