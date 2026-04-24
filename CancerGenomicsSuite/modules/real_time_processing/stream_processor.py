#!/usr/bin/env python3
"""
Stream Processor

This module provides real-time stream processing capabilities for cancer genomics data
using Apache Kafka and various processing engines.
"""

import logging
import json
import time
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import numpy as np

from .kafka_manager import KafkaManager

logger = logging.getLogger(__name__)


class StreamProcessor:
    """
    Real-time stream processor for cancer genomics data.
    
    Provides functionality to:
    - Process real-time data streams
    - Apply transformations and filters
    - Aggregate and analyze data
    - Handle data quality checks
    - Integrate with analysis pipelines
    """
    
    def __init__(
        self,
        kafka_manager: KafkaManager,
        processing_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize stream processor.
        
        Args:
            kafka_manager: Kafka manager instance
            processing_config: Processing configuration
        """
        self.kafka_manager = kafka_manager
        self.processing_config = processing_config or {}
        
        # Processing state
        self.active_processors = {}
        self.processing_stats = {
            "messages_processed": 0,
            "messages_failed": 0,
            "processing_time": 0,
            "start_time": None
        }
        
        # Data buffers
        self.data_buffers = {}
        self.buffer_sizes = self.processing_config.get("buffer_sizes", {})
        
        # Processing functions
        self.transform_functions = {}
        self.filter_functions = {}
        self.aggregation_functions = {}
    
    def create_processing_pipeline(
        self,
        pipeline_name: str,
        input_topics: List[str],
        output_topics: List[str],
        processing_steps: List[Dict[str, Any]]
    ) -> bool:
        """
        Create a processing pipeline.
        
        Args:
            pipeline_name: Name of the pipeline
            input_topics: List of input topics
            output_topics: List of output topics
            processing_steps: List of processing steps
            
        Returns:
            True if pipeline was created successfully
        """
        try:
            pipeline_config = {
                "name": pipeline_name,
                "input_topics": input_topics,
                "output_topics": output_topics,
                "processing_steps": processing_steps,
                "created_at": datetime.now().isoformat(),
                "status": "created"
            }
            
            self.active_processors[pipeline_name] = pipeline_config
            
            logger.info(f"Created processing pipeline: {pipeline_name}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to create pipeline {pipeline_name}: {e}")
            return False
    
    def start_pipeline(
        self,
        pipeline_name: str,
        group_id: Optional[str] = None
    ) -> bool:
        """
        Start a processing pipeline.
        
        Args:
            pipeline_name: Name of the pipeline to start
            group_id: Consumer group ID
            
        Returns:
            True if pipeline was started successfully
        """
        if pipeline_name not in self.active_processors:
            logger.error(f"Pipeline {pipeline_name} not found")
            return False
        
        pipeline_config = self.active_processors[pipeline_name]
        
        try:
            # Create message handler
            def message_handler(message: Dict[str, Any]):
                self._process_message(pipeline_name, message)
            
            # Start consumer group
            consumer_group_id = group_id or f"{pipeline_name}_group"
            thread = self.kafka_manager.start_consumer_group(
                topics=pipeline_config["input_topics"],
                group_id=consumer_group_id,
                message_handler=message_handler
            )
            
            # Update pipeline status
            pipeline_config["status"] = "running"
            pipeline_config["consumer_group_id"] = consumer_group_id
            pipeline_config["thread"] = thread
            pipeline_config["started_at"] = datetime.now().isoformat()
            
            # Initialize processing stats
            if not self.processing_stats["start_time"]:
                self.processing_stats["start_time"] = datetime.now()
            
            logger.info(f"Started processing pipeline: {pipeline_name}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to start pipeline {pipeline_name}: {e}")
            return False
    
    def stop_pipeline(self, pipeline_name: str) -> bool:
        """
        Stop a processing pipeline.
        
        Args:
            pipeline_name: Name of the pipeline to stop
            
        Returns:
            True if pipeline was stopped successfully
        """
        if pipeline_name not in self.active_processors:
            logger.error(f"Pipeline {pipeline_name} not found")
            return False
        
        pipeline_config = self.active_processors[pipeline_name]
        
        try:
            # Stop consumer group
            if "consumer_group_id" in pipeline_config:
                self.kafka_manager.stop_consumer_group(pipeline_config["consumer_group_id"])
            
            # Update pipeline status
            pipeline_config["status"] = "stopped"
            pipeline_config["stopped_at"] = datetime.now().isoformat()
            
            logger.info(f"Stopped processing pipeline: {pipeline_name}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to stop pipeline {pipeline_name}: {e}")
            return False
    
    def _process_message(self, pipeline_name: str, message: Dict[str, Any]):
        """
        Process a single message through the pipeline.
        
        Args:
            pipeline_name: Name of the pipeline
            message: Message to process
        """
        start_time = time.time()
        
        try:
            pipeline_config = self.active_processors[pipeline_name]
            processing_steps = pipeline_config["processing_steps"]
            
            # Extract data from message
            data = message.get("data", {})
            current_data = data
            
            # Apply processing steps
            for step in processing_steps:
                step_type = step.get("type")
                step_config = step.get("config", {})
                
                if step_type == "transform":
                    current_data = self._apply_transform(current_data, step_config)
                elif step_type == "filter":
                    if not self._apply_filter(current_data, step_config):
                        return  # Skip this message
                elif step_type == "aggregate":
                    current_data = self._apply_aggregation(current_data, step_config)
                elif step_type == "quality_check":
                    if not self._apply_quality_check(current_data, step_config):
                        logger.warning(f"Quality check failed for message in pipeline {pipeline_name}")
                        return
                elif step_type == "custom":
                    current_data = self._apply_custom_function(current_data, step_config)
            
            # Send processed data to output topics
            if current_data and pipeline_config["output_topics"]:
                for output_topic in pipeline_config["output_topics"]:
                    self.kafka_manager.produce_message(
                        topic=output_topic,
                        message=current_data,
                        key=message.get("key")
                    )
            
            # Update statistics
            self.processing_stats["messages_processed"] += 1
            processing_time = time.time() - start_time
            self.processing_stats["processing_time"] += processing_time
        
        except Exception as e:
            logger.error(f"Error processing message in pipeline {pipeline_name}: {e}")
            self.processing_stats["messages_failed"] += 1
    
    def _apply_transform(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply transformation to data.
        
        Args:
            data: Input data
            config: Transformation configuration
            
        Returns:
            Transformed data
        """
        transform_type = config.get("transform_type")
        
        if transform_type == "normalize":
            return self._normalize_data(data, config)
        elif transform_type == "scale":
            return self._scale_data(data, config)
        elif transform_type == "encode":
            return self._encode_data(data, config)
        elif transform_type == "extract_features":
            return self._extract_features(data, config)
        else:
            logger.warning(f"Unknown transform type: {transform_type}")
            return data
    
    def _normalize_data(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize data values."""
        fields = config.get("fields", [])
        method = config.get("method", "z_score")
        
        for field in fields:
            if field in data and isinstance(data[field], (int, float)):
                value = data[field]
                
                if method == "z_score":
                    # Z-score normalization (requires mean and std from config)
                    mean = config.get("mean", 0)
                    std = config.get("std", 1)
                    data[field] = (value - mean) / std if std != 0 else value
                
                elif method == "min_max":
                    # Min-max normalization
                    min_val = config.get("min", 0)
                    max_val = config.get("max", 1)
                    data[field] = (value - min_val) / (max_val - min_val) if max_val != min_val else value
                
                elif method == "log":
                    # Log transformation
                    data[field] = np.log(value + 1) if value >= 0 else value
        
        return data
    
    def _scale_data(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Scale data values."""
        fields = config.get("fields", [])
        scale_factor = config.get("scale_factor", 1.0)
        
        for field in fields:
            if field in data and isinstance(data[field], (int, float)):
                data[field] *= scale_factor
        
        return data
    
    def _encode_data(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Encode categorical data."""
        fields = config.get("fields", [])
        encoding_type = config.get("encoding_type", "one_hot")
        
        for field in fields:
            if field in data:
                value = data[field]
                
                if encoding_type == "one_hot":
                    # One-hot encoding (simplified)
                    categories = config.get("categories", [])
                    if value in categories:
                        encoded = {f"{field}_{cat}": 1 if cat == value else 0 for cat in categories}
                        data.update(encoded)
                        del data[field]
                
                elif encoding_type == "label":
                    # Label encoding
                    mapping = config.get("mapping", {})
                    data[field] = mapping.get(value, value)
        
        return data
    
    def _extract_features(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features from data."""
        feature_configs = config.get("features", [])
        
        for feature_config in feature_configs:
            feature_name = feature_config.get("name")
            feature_type = feature_config.get("type")
            source_fields = feature_config.get("source_fields", [])
            
            if feature_type == "sum":
                values = [data.get(field, 0) for field in source_fields if isinstance(data.get(field), (int, float))]
                data[feature_name] = sum(values)
            
            elif feature_type == "mean":
                values = [data.get(field, 0) for field in source_fields if isinstance(data.get(field), (int, float))]
                data[feature_name] = np.mean(values) if values else 0
            
            elif feature_type == "max":
                values = [data.get(field, 0) for field in source_fields if isinstance(data.get(field), (int, float))]
                data[feature_name] = max(values) if values else 0
            
            elif feature_type == "min":
                values = [data.get(field, 0) for field in source_fields if isinstance(data.get(field), (int, float))]
                data[feature_name] = min(values) if values else 0
        
        return data
    
    def _apply_filter(self, data: Dict[str, Any], config: Dict[str, Any]) -> bool:
        """
        Apply filter to data.
        
        Args:
            data: Input data
            config: Filter configuration
            
        Returns:
            True if data passes filter, False otherwise
        """
        filter_type = config.get("filter_type")
        
        if filter_type == "range":
            return self._range_filter(data, config)
        elif filter_type == "value":
            return self._value_filter(data, config)
        elif filter_type == "exists":
            return self._exists_filter(data, config)
        else:
            logger.warning(f"Unknown filter type: {filter_type}")
            return True
    
    def _range_filter(self, data: Dict[str, Any], config: Dict[str, Any]) -> bool:
        """Filter data by value range."""
        field = config.get("field")
        min_val = config.get("min")
        max_val = config.get("max")
        
        if field not in data:
            return False
        
        value = data[field]
        if not isinstance(value, (int, float)):
            return False
        
        if min_val is not None and value < min_val:
            return False
        
        if max_val is not None and value > max_val:
            return False
        
        return True
    
    def _value_filter(self, data: Dict[str, Any], config: Dict[str, Any]) -> bool:
        """Filter data by specific values."""
        field = config.get("field")
        allowed_values = config.get("allowed_values", [])
        excluded_values = config.get("excluded_values", [])
        
        if field not in data:
            return False
        
        value = data[field]
        
        if allowed_values and value not in allowed_values:
            return False
        
        if excluded_values and value in excluded_values:
            return False
        
        return True
    
    def _exists_filter(self, data: Dict[str, Any], config: Dict[str, Any]) -> bool:
        """Filter data by field existence."""
        fields = config.get("fields", [])
        require_all = config.get("require_all", True)
        
        if require_all:
            return all(field in data for field in fields)
        else:
            return any(field in data for field in fields)
    
    def _apply_aggregation(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply aggregation to data.
        
        Args:
            data: Input data
            config: Aggregation configuration
            
        Returns:
            Aggregated data
        """
        aggregation_type = config.get("aggregation_type")
        buffer_name = config.get("buffer_name")
        
        if not buffer_name:
            return data
        
        # Initialize buffer if needed
        if buffer_name not in self.data_buffers:
            buffer_size = self.buffer_sizes.get(buffer_name, 100)
            self.data_buffers[buffer_name] = []
        
        # Add data to buffer
        self.data_buffers[buffer_name].append(data)
        
        # Maintain buffer size
        buffer_size = self.buffer_sizes.get(buffer_name, 100)
        if len(self.data_buffers[buffer_name]) > buffer_size:
            self.data_buffers[buffer_name] = self.data_buffers[buffer_name][-buffer_size:]
        
        # Apply aggregation
        if aggregation_type == "window":
            return self._window_aggregation(buffer_name, config)
        elif aggregation_type == "batch":
            return self._batch_aggregation(buffer_name, config)
        else:
            return data
    
    def _window_aggregation(self, buffer_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply window-based aggregation."""
        window_size = config.get("window_size", 10)
        aggregation_fields = config.get("aggregation_fields", [])
        aggregation_method = config.get("aggregation_method", "mean")
        
        buffer_data = self.data_buffers[buffer_name]
        
        if len(buffer_data) < window_size:
            return buffer_data[-1] if buffer_data else {}
        
        # Get window data
        window_data = buffer_data[-window_size:]
        
        # Aggregate fields
        aggregated_data = {}
        for field in aggregation_fields:
            values = [item.get(field) for item in window_data if field in item and isinstance(item[field], (int, float))]
            
            if values:
                if aggregation_method == "mean":
                    aggregated_data[field] = np.mean(values)
                elif aggregation_method == "sum":
                    aggregated_data[field] = np.sum(values)
                elif aggregation_method == "max":
                    aggregated_data[field] = np.max(values)
                elif aggregation_method == "min":
                    aggregated_data[field] = np.min(values)
                elif aggregation_method == "std":
                    aggregated_data[field] = np.std(values)
        
        return aggregated_data
    
    def _batch_aggregation(self, buffer_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply batch-based aggregation."""
        batch_size = config.get("batch_size", 100)
        aggregation_fields = config.get("aggregation_fields", [])
        aggregation_method = config.get("aggregation_method", "mean")
        
        buffer_data = self.data_buffers[buffer_name]
        
        if len(buffer_data) < batch_size:
            return {}
        
        # Aggregate all data in buffer
        aggregated_data = {}
        for field in aggregation_fields:
            values = [item.get(field) for item in buffer_data if field in item and isinstance(item[field], (int, float))]
            
            if values:
                if aggregation_method == "mean":
                    aggregated_data[field] = np.mean(values)
                elif aggregation_method == "sum":
                    aggregated_data[field] = np.sum(values)
                elif aggregation_method == "max":
                    aggregated_data[field] = np.max(values)
                elif aggregation_method == "min":
                    aggregated_data[field] = np.min(values)
                elif aggregation_method == "std":
                    aggregated_data[field] = np.std(values)
        
        # Clear buffer after batch aggregation
        self.data_buffers[buffer_name] = []
        
        return aggregated_data
    
    def _apply_quality_check(self, data: Dict[str, Any], config: Dict[str, Any]) -> bool:
        """
        Apply data quality checks.
        
        Args:
            data: Input data
            config: Quality check configuration
            
        Returns:
            True if data passes quality checks, False otherwise
        """
        checks = config.get("checks", [])
        
        for check in checks:
            check_type = check.get("type")
            
            if check_type == "completeness":
                if not self._check_completeness(data, check):
                    return False
            elif check_type == "validity":
                if not self._check_validity(data, check):
                    return False
            elif check_type == "consistency":
                if not self._check_consistency(data, check):
                    return False
        
        return True
    
    def _check_completeness(self, data: Dict[str, Any], check_config: Dict[str, Any]) -> bool:
        """Check data completeness."""
        required_fields = check_config.get("required_fields", [])
        min_completeness = check_config.get("min_completeness", 1.0)
        
        present_fields = sum(1 for field in required_fields if field in data and data[field] is not None)
        completeness = present_fields / len(required_fields) if required_fields else 1.0
        
        return completeness >= min_completeness
    
    def _check_validity(self, data: Dict[str, Any], check_config: Dict[str, Any]) -> bool:
        """Check data validity."""
        field_rules = check_config.get("field_rules", {})
        
        for field, rules in field_rules.items():
            if field not in data:
                continue
            
            value = data[field]
            
            # Check data type
            expected_type = rules.get("type")
            if expected_type and not isinstance(value, expected_type):
                return False
            
            # Check value range
            min_val = rules.get("min")
            max_val = rules.get("max")
            if isinstance(value, (int, float)):
                if min_val is not None and value < min_val:
                    return False
                if max_val is not None and value > max_val:
                    return False
            
            # Check allowed values
            allowed_values = rules.get("allowed_values")
            if allowed_values and value not in allowed_values:
                return False
        
        return True
    
    def _check_consistency(self, data: Dict[str, Any], check_config: Dict[str, Any]) -> bool:
        """Check data consistency."""
        consistency_rules = check_config.get("rules", [])
        
        for rule in consistency_rules:
            rule_type = rule.get("type")
            
            if rule_type == "sum":
                fields = rule.get("fields", [])
                expected_sum = rule.get("expected_sum")
                actual_sum = sum(data.get(field, 0) for field in fields if isinstance(data.get(field), (int, float)))
                
                if expected_sum is not None and abs(actual_sum - expected_sum) > rule.get("tolerance", 0):
                    return False
            
            elif rule_type == "ratio":
                field1 = rule.get("field1")
                field2 = rule.get("field2")
                expected_ratio = rule.get("expected_ratio")
                
                if field1 in data and field2 in data and data[field2] != 0:
                    actual_ratio = data[field1] / data[field2]
                    if expected_ratio is not None and abs(actual_ratio - expected_ratio) > rule.get("tolerance", 0):
                        return False
        
        return True
    
    def _apply_custom_function(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply custom processing function."""
        function_name = config.get("function_name")
        
        if function_name in self.transform_functions:
            return self.transform_functions[function_name](data, config)
        else:
            logger.warning(f"Custom function {function_name} not found")
            return data
    
    def register_transform_function(self, name: str, function: Callable):
        """
        Register a custom transform function.
        
        Args:
            name: Function name
            function: Function to register
        """
        self.transform_functions[name] = function
        logger.info(f"Registered transform function: {name}")
    
    def register_filter_function(self, name: str, function: Callable):
        """
        Register a custom filter function.
        
        Args:
            name: Function name
            function: Function to register
        """
        self.filter_functions[name] = function
        logger.info(f"Registered filter function: {name}")
    
    def register_aggregation_function(self, name: str, function: Callable):
        """
        Register a custom aggregation function.
        
        Args:
            name: Function name
            function: Function to register
        """
        self.aggregation_functions[name] = function
        logger.info(f"Registered aggregation function: {name}")
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get processing statistics.
        
        Returns:
            Dictionary with processing statistics
        """
        stats = self.processing_stats.copy()
        
        # Add pipeline-specific stats
        stats["active_pipelines"] = len([p for p in self.active_processors.values() if p["status"] == "running"])
        stats["total_pipelines"] = len(self.active_processors)
        
        # Calculate processing rate
        if stats["start_time"]:
            runtime = (datetime.now() - stats["start_time"]).total_seconds()
            if runtime > 0:
                stats["messages_per_second"] = stats["messages_processed"] / runtime
                stats["avg_processing_time"] = stats["processing_time"] / stats["messages_processed"] if stats["messages_processed"] > 0 else 0
        
        return stats
    
    def get_pipeline_status(self, pipeline_name: str) -> Dict[str, Any]:
        """
        Get status of a specific pipeline.
        
        Args:
            pipeline_name: Name of the pipeline
            
        Returns:
            Dictionary with pipeline status
        """
        if pipeline_name not in self.active_processors:
            return {}
        
        return self.active_processors[pipeline_name].copy()
    
    def list_pipelines(self) -> List[Dict[str, Any]]:
        """
        List all pipelines.
        
        Returns:
            List of pipeline information
        """
        return list(self.active_processors.values())
    
    def clear_buffers(self):
        """Clear all data buffers."""
        self.data_buffers.clear()
        logger.info("Cleared all data buffers")
    
    def reset_statistics(self):
        """Reset processing statistics."""
        self.processing_stats = {
            "messages_processed": 0,
            "messages_failed": 0,
            "processing_time": 0,
            "start_time": datetime.now()
        }
        logger.info("Reset processing statistics")
