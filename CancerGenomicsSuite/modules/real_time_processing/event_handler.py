#!/usr/bin/env python3
"""
Event Handler

This module provides event handling capabilities for real-time cancer genomics
data processing workflows.
"""

import logging
import json
import time
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

from .kafka_manager import KafkaManager

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event types for cancer genomics processing."""
    DATA_RECEIVED = "data_received"
    PROCESSING_STARTED = "processing_started"
    PROCESSING_COMPLETED = "processing_completed"
    PROCESSING_FAILED = "processing_failed"
    QUALITY_CHECK_PASSED = "quality_check_passed"
    QUALITY_CHECK_FAILED = "quality_check_failed"
    ANOMALY_DETECTED = "anomaly_detected"
    THRESHOLD_EXCEEDED = "threshold_exceeded"
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_STOPPED = "pipeline_stopped"
    PIPELINE_ERROR = "pipeline_error"
    RESOURCE_LOW = "resource_low"
    RESOURCE_CRITICAL = "resource_critical"


class EventSeverity(Enum):
    """Event severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventHandler:
    """
    Event handler for cancer genomics real-time processing.
    
    Provides functionality to:
    - Handle and process events
    - Route events to appropriate handlers
    - Manage event subscriptions
    - Store and retrieve event history
    - Trigger automated responses
    """
    
    def __init__(
        self,
        kafka_manager: KafkaManager,
        event_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize event handler.
        
        Args:
            kafka_manager: Kafka manager instance
            event_config: Event handling configuration
        """
        self.kafka_manager = kafka_manager
        self.event_config = event_config or {}
        
        # Event management
        self.event_handlers = {}
        self.event_subscriptions = {}
        self.event_history = []
        self.event_filters = {}
        
        # Event routing
        self.event_routing = {}
        self.event_priorities = {}
        
        # Automated responses
        self.automated_responses = {}
        self.response_triggers = {}
        
        # Event storage
        self.max_history_size = self.event_config.get("max_history_size", 10000)
        self.event_retention_days = self.event_config.get("event_retention_days", 30)
        
        # Event processing
        self.event_processor_thread = None
        self.processing_enabled = True
        
        # Statistics
        self.event_stats = {
            "total_events": 0,
            "events_by_type": {},
            "events_by_severity": {},
            "handlers_executed": 0,
            "automated_responses": 0,
            "start_time": datetime.now()
        }
        
        # Start event processing
        self.start_event_processing()
    
    def register_event_handler(
        self,
        event_type: EventType,
        handler: Callable[[Dict[str, Any]], None],
        priority: int = 0
    ):
        """
        Register an event handler.
        
        Args:
            event_type: Type of event to handle
            handler: Function to handle the event
            priority: Handler priority (higher = more priority)
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        
        self.event_handlers[event_type].append({
            "handler": handler,
            "priority": priority,
            "registered_at": datetime.now()
        })
        
        # Sort handlers by priority
        self.event_handlers[event_type].sort(key=lambda x: x["priority"], reverse=True)
        
        logger.info(f"Registered event handler for {event_type.value}")
    
    def unregister_event_handler(self, event_type: EventType, handler: Callable):
        """
        Unregister an event handler.
        
        Args:
            event_type: Type of event
            handler: Handler function to remove
        """
        if event_type in self.event_handlers:
            self.event_handlers[event_type] = [
                h for h in self.event_handlers[event_type] if h["handler"] != handler
            ]
            logger.info(f"Unregistered event handler for {event_type.value}")
    
    def subscribe_to_events(
        self,
        event_types: List[EventType],
        callback: Callable[[Dict[str, Any]], None],
        filter_criteria: Optional[Dict[str, Any]] = None
    ):
        """
        Subscribe to specific event types.
        
        Args:
            event_types: List of event types to subscribe to
            callback: Function to call when events are received
            filter_criteria: Optional filter criteria
        """
        subscription_id = f"sub_{len(self.event_subscriptions)}"
        
        self.event_subscriptions[subscription_id] = {
            "event_types": event_types,
            "callback": callback,
            "filter_criteria": filter_criteria or {},
            "created_at": datetime.now()
        }
        
        logger.info(f"Created event subscription {subscription_id} for {len(event_types)} event types")
        return subscription_id
    
    def unsubscribe_from_events(self, subscription_id: str):
        """
        Unsubscribe from events.
        
        Args:
            subscription_id: Subscription ID to remove
        """
        if subscription_id in self.event_subscriptions:
            del self.event_subscriptions[subscription_id]
            logger.info(f"Removed event subscription {subscription_id}")
    
    def emit_event(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        severity: EventSeverity = EventSeverity.INFO,
        source: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """
        Emit an event.
        
        Args:
            event_type: Type of event
            data: Event data
            severity: Event severity
            source: Event source
            correlation_id: Correlation ID for tracking
            
        Returns:
            Event ID
        """
        event_id = f"evt_{int(time.time() * 1000)}"
        
        event = {
            "id": event_id,
            "type": event_type.value,
            "severity": severity.value,
            "data": data,
            "source": source or "unknown",
            "correlation_id": correlation_id,
            "timestamp": datetime.now().isoformat(),
            "processed": False
        }
        
        # Store event in history
        self._store_event(event)
        
        # Update statistics
        self._update_event_stats(event)
        
        # Process event
        self._process_event(event)
        
        logger.debug(f"Emitted event {event_id} of type {event_type.value}")
        return event_id
    
    def _store_event(self, event: Dict[str, Any]):
        """Store event in history."""
        self.event_history.append(event)
        
        # Maintain history size
        if len(self.event_history) > self.max_history_size:
            self.event_history = self.event_history[-self.max_history_size:]
    
    def _update_event_stats(self, event: Dict[str, Any]):
        """Update event statistics."""
        self.event_stats["total_events"] += 1
        
        # Count by type
        event_type = event["type"]
        self.event_stats["events_by_type"][event_type] = self.event_stats["events_by_type"].get(event_type, 0) + 1
        
        # Count by severity
        severity = event["severity"]
        self.event_stats["events_by_severity"][severity] = self.event_stats["events_by_severity"].get(severity, 0) + 1
    
    def _process_event(self, event: Dict[str, Any]):
        """Process an event."""
        try:
            event_type = EventType(event["type"])
            
            # Execute registered handlers
            if event_type in self.event_handlers:
                for handler_info in self.event_handlers[event_type]:
                    try:
                        handler_info["handler"](event)
                        self.event_stats["handlers_executed"] += 1
                    except Exception as e:
                        logger.error(f"Error in event handler: {e}")
            
            # Notify subscribers
            self._notify_subscribers(event)
            
            # Check for automated responses
            self._check_automated_responses(event)
            
            # Mark as processed
            event["processed"] = True
            
        except Exception as e:
            logger.error(f"Error processing event {event['id']}: {e}")
    
    def _notify_subscribers(self, event: Dict[str, Any]):
        """Notify event subscribers."""
        event_type = EventType(event["type"])
        
        for subscription_id, subscription in self.event_subscriptions.items():
            if event_type in subscription["event_types"]:
                # Check filter criteria
                if self._matches_filter(event, subscription["filter_criteria"]):
                    try:
                        subscription["callback"](event)
                    except Exception as e:
                        logger.error(f"Error in subscription callback {subscription_id}: {e}")
    
    def _matches_filter(self, event: Dict[str, Any], filter_criteria: Dict[str, Any]) -> bool:
        """Check if event matches filter criteria."""
        for key, expected_value in filter_criteria.items():
            if key == "severity":
                if event["severity"] != expected_value:
                    return False
            elif key == "source":
                if event["source"] != expected_value:
                    return False
            elif key == "data_field":
                field_name = expected_value.get("field")
                field_value = expected_value.get("value")
                if event["data"].get(field_name) != field_value:
                    return False
            elif key == "time_range":
                # Check if event is within time range
                event_time = datetime.fromisoformat(event["timestamp"])
                start_time = expected_value.get("start")
                end_time = expected_value.get("end")
                
                if start_time and event_time < start_time:
                    return False
                if end_time and event_time > end_time:
                    return False
        
        return True
    
    def _check_automated_responses(self, event: Dict[str, Any]):
        """Check for automated responses to events."""
        event_type = EventType(event["type"])
        
        if event_type in self.automated_responses:
            response_config = self.automated_responses[event_type]
            
            # Check trigger conditions
            if self._check_response_triggers(event, response_config):
                self._execute_automated_response(event, response_config)
    
    def _check_response_triggers(self, event: Dict[str, Any], response_config: Dict[str, Any]) -> bool:
        """Check if automated response should be triggered."""
        triggers = response_config.get("triggers", [])
        
        for trigger in triggers:
            trigger_type = trigger.get("type")
            
            if trigger_type == "event_count":
                # Check if event count threshold is reached
                event_type = event["type"]
                time_window = trigger.get("time_window", 300)  # 5 minutes default
                threshold = trigger.get("threshold", 10)
                
                recent_events = self._count_recent_events(event_type, time_window)
                if recent_events >= threshold:
                    return True
            
            elif trigger_type == "severity":
                # Check severity threshold
                severity_threshold = trigger.get("severity")
                if event["severity"] == severity_threshold:
                    return True
            
            elif trigger_type == "data_condition":
                # Check data condition
                field = trigger.get("field")
                operator = trigger.get("operator")
                value = trigger.get("value")
                
                event_value = event["data"].get(field)
                if self._evaluate_condition(event_value, operator, value):
                    return True
        
        return False
    
    def _count_recent_events(self, event_type: str, time_window: int) -> int:
        """Count recent events of a specific type."""
        cutoff_time = datetime.now().timestamp() - time_window
        count = 0
        
        for event in self.event_history:
            if (event["type"] == event_type and 
                datetime.fromisoformat(event["timestamp"]).timestamp() > cutoff_time):
                count += 1
        
        return count
    
    def _evaluate_condition(self, value: Any, operator: str, expected_value: Any) -> bool:
        """Evaluate a condition."""
        if operator == "equals":
            return value == expected_value
        elif operator == "not_equals":
            return value != expected_value
        elif operator == "greater_than":
            return value > expected_value
        elif operator == "less_than":
            return value < expected_value
        elif operator == "greater_equal":
            return value >= expected_value
        elif operator == "less_equal":
            return value <= expected_value
        elif operator == "contains":
            return expected_value in str(value)
        else:
            return False
    
    def _execute_automated_response(self, event: Dict[str, Any], response_config: Dict[str, Any]):
        """Execute automated response."""
        response_type = response_config.get("type")
        
        try:
            if response_type == "send_alert":
                self._send_alert(event, response_config)
            elif response_type == "scale_resources":
                self._scale_resources(event, response_config)
            elif response_type == "restart_pipeline":
                self._restart_pipeline(event, response_config)
            elif response_type == "custom_action":
                self._execute_custom_action(event, response_config)
            
            self.event_stats["automated_responses"] += 1
            logger.info(f"Executed automated response {response_type} for event {event['id']}")
        
        except Exception as e:
            logger.error(f"Error executing automated response: {e}")
    
    def _send_alert(self, event: Dict[str, Any], response_config: Dict[str, Any]):
        """Send alert for event."""
        alert_config = response_config.get("alert_config", {})
        
        # Create alert message
        alert_message = {
            "type": "alert",
            "event_id": event["id"],
            "event_type": event["type"],
            "severity": event["severity"],
            "message": alert_config.get("message", f"Event {event['type']} occurred"),
            "timestamp": datetime.now().isoformat(),
            "data": event["data"]
        }
        
        # Send to Kafka topic
        topic = alert_config.get("topic", "alerts")
        self.kafka_manager.produce_message(topic, alert_message)
    
    def _scale_resources(self, event: Dict[str, Any], response_config: Dict[str, Any]):
        """Scale resources based on event."""
        scale_config = response_config.get("scale_config", {})
        
        # Emit scaling event
        scaling_event = {
            "action": "scale_resources",
            "scale_factor": scale_config.get("scale_factor", 1.5),
            "resource_type": scale_config.get("resource_type", "processing_nodes"),
            "reason": f"Event {event['type']} triggered scaling",
            "event_id": event["id"]
        }
        
        self.emit_event(
            EventType.RESOURCE_LOW,
            scaling_event,
            EventSeverity.WARNING,
            source="event_handler"
        )
    
    def _restart_pipeline(self, event: Dict[str, Any], response_config: Dict[str, Any]):
        """Restart pipeline based on event."""
        restart_config = response_config.get("restart_config", {})
        
        # Emit restart event
        restart_event = {
            "action": "restart_pipeline",
            "pipeline_name": restart_config.get("pipeline_name"),
            "reason": f"Event {event['type']} triggered restart",
            "event_id": event["id"]
        }
        
        self.emit_event(
            EventType.PIPELINE_ERROR,
            restart_event,
            EventSeverity.WARNING,
            source="event_handler"
        )
    
    def _execute_custom_action(self, event: Dict[str, Any], response_config: Dict[str, Any]):
        """Execute custom action."""
        action_config = response_config.get("action_config", {})
        action_function = action_config.get("function")
        
        if action_function and callable(action_function):
            action_function(event, action_config)
    
    def register_automated_response(
        self,
        event_type: EventType,
        response_config: Dict[str, Any]
    ):
        """
        Register an automated response for an event type.
        
        Args:
            event_type: Event type to respond to
            response_config: Response configuration
        """
        self.automated_responses[event_type] = response_config
        logger.info(f"Registered automated response for {event_type.value}")
    
    def start_event_processing(self):
        """Start event processing thread."""
        if self.event_processor_thread and self.event_processor_thread.is_alive():
            return
        
        def event_processor_worker():
            while self.processing_enabled:
                try:
                    # Process any pending events
                    time.sleep(0.1)  # Small delay to prevent busy waiting
                except Exception as e:
                    logger.error(f"Error in event processor thread: {e}")
                    time.sleep(1)
        
        self.event_processor_thread = threading.Thread(target=event_processor_worker, daemon=True)
        self.event_processor_thread.start()
        logger.info("Started event processing")
    
    def stop_event_processing(self):
        """Stop event processing."""
        self.processing_enabled = False
        if self.event_processor_thread:
            self.event_processor_thread.join(timeout=5)
        logger.info("Stopped event processing")
    
    def get_event_history(
        self,
        event_type: Optional[EventType] = None,
        severity: Optional[EventSeverity] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get event history with optional filtering.
        
        Args:
            event_type: Filter by event type
            severity: Filter by severity
            limit: Maximum number of events to return
            
        Returns:
            List of events
        """
        filtered_events = self.event_history
        
        if event_type:
            filtered_events = [e for e in filtered_events if e["type"] == event_type.value]
        
        if severity:
            filtered_events = [e for e in filtered_events if e["severity"] == severity.value]
        
        # Sort by timestamp (newest first)
        filtered_events.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return filtered_events[:limit]
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """
        Get event statistics.
        
        Returns:
            Dictionary with event statistics
        """
        stats = self.event_stats.copy()
        
        # Add current time
        stats["current_time"] = datetime.now().isoformat()
        
        # Add handler counts
        stats["registered_handlers"] = sum(len(handlers) for handlers in self.event_handlers.values())
        stats["active_subscriptions"] = len(self.event_subscriptions)
        stats["automated_responses_registered"] = len(self.automated_responses)
        
        # Add recent activity
        recent_events = self.get_event_history(limit=10)
        stats["recent_events"] = [
            {
                "id": event["id"],
                "type": event["type"],
                "severity": event["severity"],
                "timestamp": event["timestamp"]
            }
            for event in recent_events
        ]
        
        return stats
    
    def clear_event_history(self, older_than_days: Optional[int] = None):
        """
        Clear event history.
        
        Args:
            older_than_days: Clear events older than this many days
        """
        if older_than_days:
            cutoff_time = datetime.now().timestamp() - (older_than_days * 24 * 3600)
            self.event_history = [
                event for event in self.event_history
                if datetime.fromisoformat(event["timestamp"]).timestamp() > cutoff_time
            ]
        else:
            self.event_history.clear()
        
        logger.info(f"Cleared event history (older than {older_than_days} days)" if older_than_days else "Cleared all event history")
    
    def create_cancer_genomics_event_handlers(self):
        """Create pre-configured event handlers for cancer genomics workflows."""
        
        # Data quality handler
        def handle_quality_check_failed(event):
            logger.warning(f"Quality check failed: {event['data']}")
            # Could trigger data reprocessing or alerting
        
        self.register_event_handler(EventType.QUALITY_CHECK_FAILED, handle_quality_check_failed, priority=10)
        
        # Processing error handler
        def handle_processing_failed(event):
            logger.error(f"Processing failed: {event['data']}")
            # Could trigger retry logic or fallback processing
        
        self.register_event_handler(EventType.PROCESSING_FAILED, handle_processing_failed, priority=10)
        
        # Anomaly detection handler
        def handle_anomaly_detected(event):
            logger.warning(f"Anomaly detected: {event['data']}")
            # Could trigger investigation or alerting
        
        self.register_event_handler(EventType.ANOMALY_DETECTED, handle_anomaly_detected, priority=8)
        
        # Resource monitoring handler
        def handle_resource_critical(event):
            logger.critical(f"Critical resource level: {event['data']}")
            # Could trigger emergency scaling or shutdown
        
        self.register_event_handler(EventType.RESOURCE_CRITICAL, handle_resource_critical, priority=15)
        
        # Register automated responses
        self.register_automated_response(
            EventType.QUALITY_CHECK_FAILED,
            {
                "type": "send_alert",
                "alert_config": {
                    "topic": "quality_alerts",
                    "message": "Data quality check failed - investigation required"
                },
                "triggers": [
                    {
                        "type": "event_count",
                        "time_window": 300,
                        "threshold": 5
                    }
                ]
            }
        )
        
        self.register_automated_response(
            EventType.RESOURCE_CRITICAL,
            {
                "type": "scale_resources",
                "scale_config": {
                    "scale_factor": 2.0,
                    "resource_type": "processing_nodes"
                },
                "triggers": [
                    {
                        "type": "severity",
                        "severity": "critical"
                    }
                ]
            }
        )
        
        logger.info("Created cancer genomics event handlers")
