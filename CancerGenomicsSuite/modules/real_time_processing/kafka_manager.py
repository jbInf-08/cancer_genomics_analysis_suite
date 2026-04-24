#!/usr/bin/env python3
"""
Kafka Manager

This module provides comprehensive Apache Kafka management capabilities
for real-time cancer genomics data processing.
"""

import logging
import json
import time
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor

try:
    from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
    from kafka.admin import ConfigResource, ConfigResourceType, NewTopic
    from kafka.errors import KafkaError, TopicAlreadyExistsError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logging.warning("Kafka Python client not available. Install kafka-python package.")

try:
    from confluent_kafka import Producer, Consumer, AdminClient
    from confluent_kafka.admin import ConfigResource as ConfluentConfigResource
    from confluent_kafka.admin import NewTopic as ConfluentNewTopic
    CONFLUENT_KAFKA_AVAILABLE = True
except ImportError:
    CONFLUENT_KAFKA_AVAILABLE = False
    logging.warning("Confluent Kafka client not available. Install confluent-kafka package.")

logger = logging.getLogger(__name__)


class KafkaManager:
    """
    Manager for Apache Kafka operations in cancer genomics analysis.
    
    Provides functionality to:
    - Connect to Kafka clusters
    - Create and manage topics
    - Produce and consume messages
    - Monitor cluster health
    - Handle real-time data streams
    """
    
    def __init__(
        self,
        bootstrap_servers: List[str] = ["localhost:9092"],
        client_id: str = "cancer_genomics_kafka",
        use_confluent: bool = False
    ):
        """
        Initialize Kafka manager.
        
        Args:
            bootstrap_servers: List of Kafka broker addresses
            client_id: Client identifier
            use_confluent: Whether to use Confluent Kafka client
        """
        if not KAFKA_AVAILABLE and not CONFLUENT_KAFKA_AVAILABLE:
            raise ImportError("Kafka clients not available. Install kafka-python or confluent-kafka package.")
        
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        self.use_confluent = use_confluent and CONFLUENT_KAFKA_AVAILABLE
        
        # Kafka clients
        self.producer = None
        self.consumer = None
        self.admin_client = None
        
        # Topic management
        self.topics = {}
        self.consumer_groups = {}
        
        # Connection status
        self.connected = False
        
        # Connect to Kafka
        self.connect()
    
    def connect(self):
        """Connect to Kafka cluster."""
        try:
            if self.use_confluent:
                self._connect_confluent()
            else:
                self._connect_kafka_python()
            
            self.connected = True
            logger.info(f"Connected to Kafka cluster: {self.bootstrap_servers}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            self.connected = False
            raise
    
    def _connect_confluent(self):
        """Connect using Confluent Kafka client."""
        # Producer configuration
        producer_config = {
            'bootstrap.servers': ','.join(self.bootstrap_servers),
            'client.id': self.client_id,
            'acks': 'all',
            'retries': 3,
            'batch.size': 16384,
            'linger.ms': 10,
            'buffer.memory': 33554432
        }
        
        # Consumer configuration
        consumer_config = {
            'bootstrap.servers': ','.join(self.bootstrap_servers),
            'client.id': self.client_id,
            'group.id': f"{self.client_id}_group",
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True,
            'auto.commit.interval.ms': 1000
        }
        
        # Admin client configuration
        admin_config = {
            'bootstrap.servers': ','.join(self.bootstrap_servers),
            'client.id': f"{self.client_id}_admin"
        }
        
        self.producer = Producer(producer_config)
        self.consumer = Consumer(consumer_config)
        self.admin_client = AdminClient(admin_config)
    
    def _connect_kafka_python(self):
        """Connect using kafka-python client."""
        # Producer configuration
        producer_config = {
            'bootstrap_servers': self.bootstrap_servers,
            'client_id': self.client_id,
            'acks': 'all',
            'retries': 3,
            'batch_size': 16384,
            'linger_ms': 10,
            'buffer_memory': 33554432,
            'value_serializer': lambda v: json.dumps(v).encode('utf-8')
        }
        
        # Consumer configuration
        consumer_config = {
            'bootstrap_servers': self.bootstrap_servers,
            'client_id': self.client_id,
            'group_id': f"{self.client_id}_group",
            'auto_offset_reset': 'earliest',
            'enable_auto_commit': True,
            'auto_commit_interval_ms': 1000,
            'value_deserializer': lambda m: json.loads(m.decode('utf-8'))
        }
        
        # Admin client configuration
        admin_config = {
            'bootstrap_servers': self.bootstrap_servers,
            'client_id': f"{self.client_id}_admin"
        }
        
        self.producer = KafkaProducer(**producer_config)
        self.consumer = KafkaConsumer(**consumer_config)
        self.admin_client = KafkaAdminClient(**admin_config)
    
    def create_topic(
        self,
        topic_name: str,
        num_partitions: int = 3,
        replication_factor: int = 1,
        config: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Create a new Kafka topic.
        
        Args:
            topic_name: Name of the topic
            num_partitions: Number of partitions
            replication_factor: Replication factor
            config: Topic configuration
            
        Returns:
            True if topic was created successfully
        """
        try:
            if self.use_confluent:
                return self._create_topic_confluent(topic_name, num_partitions, replication_factor, config)
            else:
                return self._create_topic_kafka_python(topic_name, num_partitions, replication_factor, config)
        
        except Exception as e:
            logger.error(f"Failed to create topic {topic_name}: {e}")
            return False
    
    def _create_topic_confluent(self, topic_name: str, num_partitions: int, replication_factor: int, config: Optional[Dict]) -> bool:
        """Create topic using Confluent client."""
        topic = ConfluentNewTopic(
            topic=topic_name,
            num_partitions=num_partitions,
            replication_factor=replication_factor,
            config=config or {}
        )
        
        fs = self.admin_client.create_topics([topic])
        
        for topic_name, f in fs.items():
            try:
                f.result()
                logger.info(f"Topic {topic_name} created successfully")
                self.topics[topic_name] = {
                    "partitions": num_partitions,
                    "replication_factor": replication_factor,
                    "config": config or {}
                }
                return True
            except Exception as e:
                if "Topic already exists" in str(e):
                    logger.info(f"Topic {topic_name} already exists")
                    return True
                else:
                    logger.error(f"Failed to create topic {topic_name}: {e}")
                    return False
    
    def _create_topic_kafka_python(self, topic_name: str, num_partitions: int, replication_factor: int, config: Optional[Dict]) -> bool:
        """Create topic using kafka-python client."""
        topic = NewTopic(
            name=topic_name,
            num_partitions=num_partitions,
            replication_factor=replication_factor,
            topic_configs=config or {}
        )
        
        try:
            self.admin_client.create_topics([topic])
            logger.info(f"Topic {topic_name} created successfully")
            self.topics[topic_name] = {
                "partitions": num_partitions,
                "replication_factor": replication_factor,
                "config": config or {}
            }
            return True
        except TopicAlreadyExistsError:
            logger.info(f"Topic {topic_name} already exists")
            return True
        except Exception as e:
            logger.error(f"Failed to create topic {topic_name}: {e}")
            return False
    
    def list_topics(self) -> List[str]:
        """
        List all topics in the cluster.
        
        Returns:
            List of topic names
        """
        try:
            if self.use_confluent:
                metadata = self.admin_client.list_topics(timeout=10)
                return list(metadata.topics.keys())
            else:
                metadata = self.admin_client.list_topics()
                return list(metadata.topics.keys())
        except Exception as e:
            logger.error(f"Failed to list topics: {e}")
            return []
    
    def delete_topic(self, topic_name: str) -> bool:
        """
        Delete a Kafka topic.
        
        Args:
            topic_name: Name of the topic to delete
            
        Returns:
            True if topic was deleted successfully
        """
        try:
            if self.use_confluent:
                fs = self.admin_client.delete_topics([topic_name])
                for topic_name, f in fs.items():
                    f.result()
            else:
                self.admin_client.delete_topics([topic_name])
            
            if topic_name in self.topics:
                del self.topics[topic_name]
            
            logger.info(f"Topic {topic_name} deleted successfully")
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete topic {topic_name}: {e}")
            return False
    
    def produce_message(
        self,
        topic: str,
        message: Dict[str, Any],
        key: Optional[str] = None,
        partition: Optional[int] = None
    ) -> bool:
        """
        Produce a message to a Kafka topic.
        
        Args:
            topic: Target topic name
            message: Message data
            key: Message key
            partition: Target partition
            
        Returns:
            True if message was sent successfully
        """
        try:
            # Add metadata to message
            message_with_metadata = {
                "data": message,
                "timestamp": datetime.now().isoformat(),
                "producer_id": self.client_id
            }
            
            if self.use_confluent:
                return self._produce_message_confluent(topic, message_with_metadata, key, partition)
            else:
                return self._produce_message_kafka_python(topic, message_with_metadata, key, partition)
        
        except Exception as e:
            logger.error(f"Failed to produce message to topic {topic}: {e}")
            return False
    
    def _produce_message_confluent(self, topic: str, message: Dict, key: Optional[str], partition: Optional[int]) -> bool:
        """Produce message using Confluent client."""
        try:
            self.producer.produce(
                topic=topic,
                value=json.dumps(message),
                key=key,
                partition=partition,
                callback=self._delivery_callback
            )
            self.producer.flush()
            return True
        except Exception as e:
            logger.error(f"Failed to produce message: {e}")
            return False
    
    def _produce_message_kafka_python(self, topic: str, message: Dict, key: Optional[str], partition: Optional[int]) -> bool:
        """Produce message using kafka-python client."""
        try:
            future = self.producer.send(
                topic=topic,
                value=message,
                key=key,
                partition=partition
            )
            future.get(timeout=10)
            return True
        except Exception as e:
            logger.error(f"Failed to produce message: {e}")
            return False
    
    def _delivery_callback(self, err, msg):
        """Callback for message delivery confirmation."""
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")
    
    def consume_messages(
        self,
        topics: List[str],
        group_id: Optional[str] = None,
        auto_offset_reset: str = "earliest",
        max_messages: Optional[int] = None,
        timeout_ms: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Consume messages from Kafka topics.
        
        Args:
            topics: List of topics to consume from
            group_id: Consumer group ID
            auto_offset_reset: Offset reset strategy
            max_messages: Maximum number of messages to consume
            timeout_ms: Timeout in milliseconds
            
        Returns:
            List of consumed messages
        """
        try:
            if self.use_confluent:
                return self._consume_messages_confluent(topics, group_id, auto_offset_reset, max_messages, timeout_ms)
            else:
                return self._consume_messages_kafka_python(topics, group_id, auto_offset_reset, max_messages, timeout_ms)
        
        except Exception as e:
            logger.error(f"Failed to consume messages: {e}")
            return []
    
    def _consume_messages_confluent(self, topics: List[str], group_id: Optional[str], auto_offset_reset: str, max_messages: Optional[int], timeout_ms: int) -> List[Dict]:
        """Consume messages using Confluent client."""
        # Update consumer configuration
        if group_id:
            self.consumer = Consumer({
                'bootstrap.servers': ','.join(self.bootstrap_servers),
                'group.id': group_id,
                'auto.offset.reset': auto_offset_reset,
                'enable.auto.commit': True
            })
        
        self.consumer.subscribe(topics)
        messages = []
        
        try:
            while True:
                msg = self.consumer.poll(timeout=timeout_ms / 1000)
                
                if msg is None:
                    break
                
                if msg.error():
                    logger.error(f"Consumer error: {msg.error()}")
                    continue
                
                try:
                    message_data = json.loads(msg.value().decode('utf-8'))
                    messages.append({
                        "topic": msg.topic(),
                        "partition": msg.partition(),
                        "offset": msg.offset(),
                        "key": msg.key().decode('utf-8') if msg.key() else None,
                        "data": message_data
                    })
                except json.JSONDecodeError:
                    logger.warning(f"Failed to decode message: {msg.value()}")
                    continue
                
                if max_messages and len(messages) >= max_messages:
                    break
        
        finally:
            self.consumer.close()
        
        return messages
    
    def _consume_messages_kafka_python(self, topics: List[str], group_id: Optional[str], auto_offset_reset: str, max_messages: Optional[int], timeout_ms: int) -> List[Dict]:
        """Consume messages using kafka-python client."""
        # Update consumer configuration
        consumer_config = {
            'bootstrap_servers': self.bootstrap_servers,
            'group_id': group_id or f"{self.client_id}_group",
            'auto_offset_reset': auto_offset_reset,
            'enable_auto_commit': True
        }
        
        consumer = KafkaConsumer(**consumer_config)
        consumer.subscribe(topics)
        
        messages = []
        
        try:
            for message in consumer:
                messages.append({
                    "topic": message.topic,
                    "partition": message.partition,
                    "offset": message.offset,
                    "key": message.key.decode('utf-8') if message.key else None,
                    "data": message.value
                })
                
                if max_messages and len(messages) >= max_messages:
                    break
        
        finally:
            consumer.close()
        
        return messages
    
    def start_consumer_group(
        self,
        topics: List[str],
        group_id: str,
        message_handler: Callable[[Dict[str, Any]], None],
        auto_offset_reset: str = "earliest"
    ) -> threading.Thread:
        """
        Start a consumer group in a separate thread.
        
        Args:
            topics: List of topics to consume from
            group_id: Consumer group ID
            message_handler: Function to handle consumed messages
            auto_offset_reset: Offset reset strategy
            
        Returns:
            Thread object running the consumer
        """
        def consumer_worker():
            try:
                if self.use_confluent:
                    consumer = Consumer({
                        'bootstrap.servers': ','.join(self.bootstrap_servers),
                        'group.id': group_id,
                        'auto.offset.reset': auto_offset_reset,
                        'enable.auto.commit': True
                    })
                else:
                    consumer = KafkaConsumer(
                        bootstrap_servers=self.bootstrap_servers,
                        group_id=group_id,
                        auto_offset_reset=auto_offset_reset,
                        enable_auto_commit=True,
                        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
                    )
                
                consumer.subscribe(topics)
                self.consumer_groups[group_id] = consumer
                
                logger.info(f"Started consumer group {group_id} for topics: {topics}")
                
                while True:
                    if self.use_confluent:
                        msg = consumer.poll(timeout=1.0)
                        if msg is None:
                            continue
                        
                        if msg.error():
                            logger.error(f"Consumer error: {msg.error()}")
                            continue
                        
                        try:
                            message_data = json.loads(msg.value().decode('utf-8'))
                            message_info = {
                                "topic": msg.topic(),
                                "partition": msg.partition(),
                                "offset": msg.offset(),
                                "key": msg.key().decode('utf-8') if msg.key() else None,
                                "data": message_data
                            }
                            message_handler(message_info)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to decode message: {msg.value()}")
                            continue
                    else:
                        for message in consumer:
                            message_info = {
                                "topic": message.topic,
                                "partition": message.partition,
                                "offset": message.offset,
                                "key": message.key.decode('utf-8') if message.key else None,
                                "data": message.value
                            }
                            message_handler(message_info)
            
            except Exception as e:
                logger.error(f"Consumer group {group_id} error: {e}")
            finally:
                if group_id in self.consumer_groups:
                    del self.consumer_groups[group_id]
        
        thread = threading.Thread(target=consumer_worker, daemon=True)
        thread.start()
        return thread
    
    def stop_consumer_group(self, group_id: str):
        """
        Stop a consumer group.
        
        Args:
            group_id: Consumer group ID to stop
        """
        if group_id in self.consumer_groups:
            try:
                self.consumer_groups[group_id].close()
                del self.consumer_groups[group_id]
                logger.info(f"Stopped consumer group {group_id}")
            except Exception as e:
                logger.error(f"Failed to stop consumer group {group_id}: {e}")
    
    def get_cluster_metadata(self) -> Dict[str, Any]:
        """
        Get Kafka cluster metadata.
        
        Returns:
            Dictionary with cluster information
        """
        try:
            if self.use_confluent:
                metadata = self.admin_client.list_topics(timeout=10)
                return {
                    "brokers": list(metadata.brokers.keys()),
                    "topics": list(metadata.topics.keys()),
                    "cluster_id": metadata.cluster_id
                }
            else:
                metadata = self.admin_client.list_topics()
                return {
                    "brokers": list(metadata.brokers.keys()),
                    "topics": list(metadata.topics.keys()),
                    "cluster_id": metadata.cluster_id
                }
        except Exception as e:
            logger.error(f"Failed to get cluster metadata: {e}")
            return {}
    
    def get_topic_metadata(self, topic_name: str) -> Dict[str, Any]:
        """
        Get metadata for a specific topic.
        
        Args:
            topic_name: Name of the topic
            
        Returns:
            Dictionary with topic metadata
        """
        try:
            if self.use_confluent:
                metadata = self.admin_client.list_topics(timeout=10)
                if topic_name in metadata.topics:
                    topic_metadata = metadata.topics[topic_name]
                    return {
                        "name": topic_name,
                        "partitions": len(topic_metadata.partitions),
                        "replication_factor": len(topic_metadata.partitions[0].replicas),
                        "partition_details": {
                            str(pid): {
                                "leader": partition.leader,
                                "replicas": partition.replicas,
                                "isr": partition.isr
                            }
                            for pid, partition in topic_metadata.partitions.items()
                        }
                    }
            else:
                metadata = self.admin_client.list_topics()
                if topic_name in metadata.topics:
                    topic_metadata = metadata.topics[topic_name]
                    return {
                        "name": topic_name,
                        "partitions": len(topic_metadata.partitions),
                        "replication_factor": len(topic_metadata.partitions[0].replicas),
                        "partition_details": {
                            str(pid): {
                                "leader": partition.leader,
                                "replicas": partition.replicas,
                                "isr": partition.isr
                            }
                            for pid, partition in topic_metadata.partitions.items()
                        }
                    }
            
            return {}
        
        except Exception as e:
            logger.error(f"Failed to get topic metadata for {topic_name}: {e}")
            return {}
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the Kafka cluster.
        
        Returns:
            Dictionary with health status
        """
        health_status = {
            "connected": self.connected,
            "timestamp": datetime.now().isoformat(),
            "cluster_metadata": {},
            "topics": [],
            "consumer_groups": list(self.consumer_groups.keys())
        }
        
        if self.connected:
            try:
                health_status["cluster_metadata"] = self.get_cluster_metadata()
                health_status["topics"] = self.list_topics()
            except Exception as e:
                health_status["error"] = str(e)
                health_status["connected"] = False
        
        return health_status
    
    def close(self):
        """Close all Kafka connections."""
        try:
            if self.producer:
                if self.use_confluent:
                    self.producer.flush()
                else:
                    self.producer.close()
            
            if self.consumer:
                if self.use_confluent:
                    self.consumer.close()
                else:
                    self.consumer.close()
            
            # Close all consumer groups
            for group_id in list(self.consumer_groups.keys()):
                self.stop_consumer_group(group_id)
            
            if self.admin_client:
                if self.use_confluent:
                    pass  # Confluent admin client doesn't need explicit closing
                else:
                    self.admin_client.close()
            
            self.connected = False
            logger.info("Kafka connections closed")
        
        except Exception as e:
            logger.error(f"Error closing Kafka connections: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
