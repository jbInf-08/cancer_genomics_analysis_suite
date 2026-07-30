"""
Real-time Processing Module

This module provides real-time data processing capabilities using Apache Kafka
for cancer genomics analysis workflows.
"""

from .data_pipeline import DataPipeline
from .event_handler import EventHandler
from .kafka_manager import KafkaManager
from .stream_processor import StreamProcessor

__all__ = ["KafkaManager", "StreamProcessor", "DataPipeline", "EventHandler"]
