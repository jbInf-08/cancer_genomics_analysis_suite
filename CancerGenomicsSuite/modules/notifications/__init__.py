"""
Notifications Module

This module provides comprehensive notification services for the Cancer Genomics Analysis Suite.
It includes email digest functionality, delivery queue management, and alert monitoring.

Components:
- EmailDigest: Handles email notifications and digest creation
- DeliveryQueue: Manages message queuing and delivery
- AlertMonitor: Monitors system health and triggers alerts
"""

from .alert_monitor import AlertMonitor
from .delivery_queue import DeliveryQueue
from .email_digest import EmailDigest

__all__ = ["EmailDigest", "DeliveryQueue", "AlertMonitor"]

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite"
