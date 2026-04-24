"""
Kafka Stream Processor for Real-time Cancer Genomics Analysis

This module provides real-time processing of mutation data from Kafka streams,
integrating with Neo4j for graph analysis and emitting Prometheus metrics.
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
import asyncio
import aiohttp
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
import neo4j
from neo4j import GraphDatabase
import pandas as pd
from sklearn.ensemble import IsolationForest
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
MUTATIONS_PROCESSED = Counter('mutations_processed_total', 'Total mutations processed', ['gene', 'mutation_type', 'severity'])
MUTATION_PROCESSING_DURATION = Histogram('mutation_processing_duration_seconds', 'Time spent processing mutations', ['gene'])
MUTATION_ALERTS = Counter('mutation_alerts_total', 'Total mutation alerts generated', ['severity', 'gene', 'mutation'])
MUTATIONS_BY_GENE = Gauge('mutations_by_gene_total', 'Total mutations by gene', ['gene'])
KAFKA_MESSAGES_CONSUMED = Counter('kafka_messages_consumed_total', 'Total Kafka messages consumed', ['topic'])
KAFKA_MESSAGES_PRODUCED = Counter('kafka_messages_produced_total', 'Total Kafka messages produced', ['topic'])
KAFKA_CONSUMER_LAG = Gauge('kafka_consumer_lag_sum', 'Kafka consumer lag', ['topic', 'partition'])
STREAM_PROCESSING_RATE = Gauge('stream_processing_rate', 'Stream processing rate', ['processor_type'])
NEO4J_OPERATIONS = Counter('neo4j_operations_total', 'Total Neo4j operations', ['operation_type', 'status'])
ML_PREDICTIONS = Counter('ml_predictions_total', 'Total ML predictions made', ['model_type', 'prediction'])

@dataclass
class MutationData:
    """Data class for mutation information"""
    id: str
    gene: str
    mutation_type: str
    chromosome: str
    position: int
    reference: str
    alternate: str
    patient_id: str
    sample_id: str
    timestamp: datetime
    severity: str = "unknown"
    clinical_significance: str = "unknown"
    population_frequency: float = 0.0
    pathogenicity_score: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class AlertData:
    """Data class for alert information"""
    id: str
    mutation_id: str
    severity: str
    message: str
    timestamp: datetime
    gene: str
    mutation: str
    patient_id: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class Neo4jGraphProcessor:
    """Neo4j graph database processor for mutation analysis"""
    
    def __init__(self, uri: str, username: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self.session = None
    
    def __enter__(self):
        self.session = self.driver.session()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            self.session.close()
        self.driver.close()
    
    async def create_mutation_node(self, mutation: MutationData) -> bool:
        """Create a mutation node in Neo4j"""
        try:
            query = """
            MERGE (m:Mutation {id: $id})
            SET m.gene = $gene,
                m.mutation_type = $mutation_type,
                m.chromosome = $chromosome,
                m.position = $position,
                m.reference = $reference,
                m.alternate = $alternate,
                m.severity = $severity,
                m.clinical_significance = $clinical_significance,
                m.population_frequency = $population_frequency,
                m.pathogenicity_score = $pathogenicity_score,
                m.timestamp = $timestamp,
                m.metadata = $metadata
            RETURN m
            """
            
            result = self.session.run(query, **asdict(mutation))
            NEO4J_OPERATIONS.labels(operation_type='create_mutation', status='success').inc()
            return True
            
        except Exception as e:
            logger.error(f"Error creating mutation node: {e}")
            NEO4J_OPERATIONS.labels(operation_type='create_mutation', status='error').inc()
            return False
    
    async def create_patient_node(self, patient_id: str, sample_id: str) -> bool:
        """Create a patient node in Neo4j"""
        try:
            query = """
            MERGE (p:Patient {id: $patient_id})
            MERGE (s:Sample {id: $sample_id})
            MERGE (p)-[:HAS_SAMPLE]->(s)
            RETURN p, s
            """
            
            result = self.session.run(query, patient_id=patient_id, sample_id=sample_id)
            NEO4J_OPERATIONS.labels(operation_type='create_patient', status='success').inc()
            return True
            
        except Exception as e:
            logger.error(f"Error creating patient node: {e}")
            NEO4J_OPERATIONS.labels(operation_type='create_patient', status='error').inc()
            return False
    
    async def create_mutation_patient_relationship(self, mutation_id: str, patient_id: str) -> bool:
        """Create relationship between mutation and patient"""
        try:
            query = """
            MATCH (m:Mutation {id: $mutation_id})
            MATCH (p:Patient {id: $patient_id})
            MERGE (p)-[:HAS_MUTATION]->(m)
            RETURN m, p
            """
            
            result = self.session.run(query, mutation_id=mutation_id, patient_id=patient_id)
            NEO4J_OPERATIONS.labels(operation_type='create_relationship', status='success').inc()
            return True
            
        except Exception as e:
            logger.error(f"Error creating mutation-patient relationship: {e}")
            NEO4J_OPERATIONS.labels(operation_type='create_relationship', status='error').inc()
            return False
    
    async def find_similar_mutations(self, mutation: MutationData, threshold: float = 0.8) -> List[Dict]:
        """Find similar mutations in the graph"""
        try:
            query = """
            MATCH (m:Mutation)
            WHERE m.gene = $gene 
            AND m.mutation_type = $mutation_type
            AND m.chromosome = $chromosome
            AND abs(m.position - $position) <= 100
            RETURN m, 
                   abs(m.position - $position) as distance,
                   m.pathogenicity_score,
                   m.severity
            ORDER BY distance
            LIMIT 10
            """
            
            result = self.session.run(query, **asdict(mutation))
            similar_mutations = []
            
            for record in result:
                similar_mutations.append({
                    'id': record['m']['id'],
                    'distance': record['distance'],
                    'pathogenicity_score': record['pathogenicity_score'],
                    'severity': record['severity']
                })
            
            NEO4J_OPERATIONS.labels(operation_type='find_similar', status='success').inc()
            return similar_mutations
            
        except Exception as e:
            logger.error(f"Error finding similar mutations: {e}")
            NEO4J_OPERATIONS.labels(operation_type='find_similar', status='error').inc()
            return []
    
    async def get_gene_network(self, gene: str) -> Dict:
        """Get gene interaction network"""
        try:
            query = """
            MATCH (g:Gene {name: $gene})-[:INTERACTS_WITH]-(related:Gene)
            RETURN g, related, 
                   [(g)-[r:INTERACTS_WITH]-(related) | r.interaction_type] as interaction_types
            """
            
            result = self.session.run(query, gene=gene)
            network = {
                'gene': gene,
                'interactions': []
            }
            
            for record in result:
                network['interactions'].append({
                    'gene': record['related']['name'],
                    'interaction_types': record['interaction_types']
                })
            
            NEO4J_OPERATIONS.labels(operation_type='get_network', status='success').inc()
            return network
            
        except Exception as e:
            logger.error(f"Error getting gene network: {e}")
            NEO4J_OPERATIONS.labels(operation_type='get_network', status='error').inc()
            return {'gene': gene, 'interactions': []}

class MLAnomalyDetector:
    """Machine learning anomaly detector for mutations"""
    
    def __init__(self):
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        self.feature_columns = [
            'position', 'population_frequency', 'pathogenicity_score'
        ]
        self.is_trained = False
        self.training_data = []
    
    def add_training_data(self, mutation: MutationData):
        """Add mutation data for training"""
        features = [
            mutation.position,
            mutation.population_frequency,
            mutation.pathogenicity_score
        ]
        self.training_data.append(features)
    
    def train_model(self):
        """Train the anomaly detection model"""
        if len(self.training_data) < 100:
            logger.warning("Not enough training data for anomaly detection")
            return False
        
        try:
            X = np.array(self.training_data)
            self.isolation_forest.fit(X)
            self.is_trained = True
            logger.info("Anomaly detection model trained successfully")
            return True
        except Exception as e:
            logger.error(f"Error training anomaly detection model: {e}")
            return False
    
    def predict_anomaly(self, mutation: MutationData) -> Dict[str, Any]:
        """Predict if mutation is anomalous"""
        if not self.is_trained:
            return {
                'is_anomaly': False,
                'anomaly_score': 0.0,
                'confidence': 0.0
            }
        
        try:
            features = np.array([[
                mutation.position,
                mutation.population_frequency,
                mutation.pathogenicity_score
            ]])
            
            anomaly_score = self.isolation_forest.decision_function(features)[0]
            is_anomaly = self.isolation_forest.predict(features)[0] == -1
            
            # Convert to probability-like score
            confidence = abs(anomaly_score)
            
            ML_PREDICTIONS.labels(model_type='anomaly_detection', prediction='anomaly' if is_anomaly else 'normal').inc()
            
            return {
                'is_anomaly': bool(is_anomaly),
                'anomaly_score': float(anomaly_score),
                'confidence': float(confidence)
            }
            
        except Exception as e:
            logger.error(f"Error predicting anomaly: {e}")
            return {
                'is_anomaly': False,
                'anomaly_score': 0.0,
                'confidence': 0.0
            }

class KafkaStreamProcessor:
    """Main Kafka stream processor for real-time mutation analysis"""
    
    def __init__(self, 
                 kafka_bootstrap_servers: str,
                 neo4j_uri: str,
                 neo4j_username: str,
                 neo4j_password: str,
                 topics: Dict[str, str]):
        
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.topics = topics
        self.consumer = None
        self.producer = None
        self.neo4j_processor = None
        self.ml_detector = MLAnomalyDetector()
        self.running = False
        
        # Initialize Neo4j connection
        self.neo4j_uri = neo4j_uri
        self.neo4j_username = neo4j_username
        self.neo4j_password = neo4j_password
    
    async def initialize(self):
        """Initialize Kafka consumer and producer"""
        try:
            # Initialize Kafka consumer
            self.consumer = KafkaConsumer(
                self.topics['mutations'],
                bootstrap_servers=self.kafka_bootstrap_servers,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                group_id='cancer-genomics-processor',
                auto_offset_reset='latest',
                enable_auto_commit=True,
                consumer_timeout_ms=1000
            )
            
            # Initialize Kafka producer
            self.producer = KafkaProducer(
                bootstrap_servers=self.kafka_bootstrap_servers,
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                retries=3,
                retry_backoff_ms=100
            )
            
            # Initialize Neo4j processor
            self.neo4j_processor = Neo4jGraphProcessor(
                self.neo4j_uri, 
                self.neo4j_username, 
                self.neo4j_password
            )
            
            logger.info("Kafka stream processor initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Kafka stream processor: {e}")
            return False
    
    async def process_mutation(self, mutation_data: Dict[str, Any]) -> Optional[AlertData]:
        """Process a single mutation and generate alerts if necessary"""
        start_time = time.time()
        
        try:
            # Parse mutation data
            mutation = MutationData(
                id=mutation_data['id'],
                gene=mutation_data['gene'],
                mutation_type=mutation_data['mutation_type'],
                chromosome=mutation_data['chromosome'],
                position=mutation_data['position'],
                reference=mutation_data['reference'],
                alternate=mutation_data['alternate'],
                patient_id=mutation_data['patient_id'],
                sample_id=mutation_data['sample_id'],
                timestamp=datetime.fromisoformat(mutation_data['timestamp']),
                severity=mutation_data.get('severity', 'unknown'),
                clinical_significance=mutation_data.get('clinical_significance', 'unknown'),
                population_frequency=mutation_data.get('population_frequency', 0.0),
                pathogenicity_score=mutation_data.get('pathogenicity_score', 0.0),
                metadata=mutation_data.get('metadata', {})
            )
            
            # Update Prometheus metrics
            MUTATIONS_PROCESSED.labels(
                gene=mutation.gene,
                mutation_type=mutation.mutation_type,
                severity=mutation.severity
            ).inc()
            
            MUTATIONS_BY_GENE.labels(gene=mutation.gene).inc()
            
            # Process with Neo4j
            with self.neo4j_processor as neo4j:
                # Create mutation node
                await neo4j.create_mutation_node(mutation)
                
                # Create patient node
                await neo4j.create_patient_node(mutation.patient_id, mutation.sample_id)
                
                # Create relationship
                await neo4j.create_mutation_patient_relationship(mutation.id, mutation.patient_id)
                
                # Find similar mutations
                similar_mutations = await neo4j.find_similar_mutations(mutation)
                
                # Get gene network
                gene_network = await neo4j.get_gene_network(mutation.gene)
            
            # ML anomaly detection
            anomaly_result = self.ml_detector.predict_anomaly(mutation)
            
            # Add to training data
            self.ml_detector.add_training_data(mutation)
            
            # Retrain model periodically
            if len(self.ml_detector.training_data) % 1000 == 0:
                self.ml_detector.train_model()
            
            # Determine if alert should be generated
            alert = None
            if self._should_generate_alert(mutation, anomaly_result, similar_mutations):
                alert = AlertData(
                    id=f"alert_{mutation.id}_{int(time.time())}",
                    mutation_id=mutation.id,
                    severity=self._determine_alert_severity(mutation, anomaly_result),
                    message=self._generate_alert_message(mutation, anomaly_result),
                    timestamp=datetime.now(),
                    gene=mutation.gene,
                    mutation=f"{mutation.reference}->{mutation.alternate}",
                    patient_id=mutation.patient_id,
                    metadata={
                        'anomaly_result': anomaly_result,
                        'similar_mutations': similar_mutations,
                        'gene_network': gene_network
                    }
                )
                
                # Update alert metrics
                MUTATION_ALERTS.labels(
                    severity=alert.severity,
                    gene=alert.gene,
                    mutation=alert.mutation
                ).inc()
            
            # Record processing duration
            processing_time = time.time() - start_time
            MUTATION_PROCESSING_DURATION.labels(gene=mutation.gene).observe(processing_time)
            
            return alert
            
        except Exception as e:
            logger.error(f"Error processing mutation: {e}")
            return None
    
    def _should_generate_alert(self, mutation: MutationData, anomaly_result: Dict, similar_mutations: List) -> bool:
        """Determine if an alert should be generated for this mutation"""
        # High severity mutations
        if mutation.severity in ['critical', 'high']:
            return True
        
        # Anomalous mutations
        if anomaly_result['is_anomaly'] and anomaly_result['confidence'] > 0.7:
            return True
        
        # Mutations with high pathogenicity score
        if mutation.pathogenicity_score > 0.8:
            return True
        
        # Mutations in critical genes
        critical_genes = ['TP53', 'BRCA1', 'BRCA2', 'EGFR', 'KRAS', 'MYC']
        if mutation.gene in critical_genes and mutation.severity != 'benign':
            return True
        
        # Mutations with similar high-severity mutations
        if similar_mutations:
            high_severity_similar = any(
                sim['severity'] in ['critical', 'high'] 
                for sim in similar_mutations
            )
            if high_severity_similar:
                return True
        
        return False
    
    def _determine_alert_severity(self, mutation: MutationData, anomaly_result: Dict) -> str:
        """Determine alert severity level"""
        if mutation.severity == 'critical':
            return 'critical'
        elif mutation.severity == 'high' or mutation.pathogenicity_score > 0.9:
            return 'high'
        elif anomaly_result['is_anomaly'] or mutation.pathogenicity_score > 0.7:
            return 'medium'
        else:
            return 'low'
    
    def _generate_alert_message(self, mutation: MutationData, anomaly_result: Dict) -> str:
        """Generate alert message"""
        message = f"Mutation alert for {mutation.gene}: {mutation.reference}->{mutation.alternate}"
        
        if mutation.severity in ['critical', 'high']:
            message += f" (Severity: {mutation.severity})"
        
        if anomaly_result['is_anomaly']:
            message += f" (Anomaly detected, confidence: {anomaly_result['confidence']:.2f})"
        
        if mutation.pathogenicity_score > 0.7:
            message += f" (High pathogenicity score: {mutation.pathogenicity_score:.2f})"
        
        return message
    
    async def send_alert(self, alert: AlertData):
        """Send alert to Kafka topic"""
        try:
            alert_data = asdict(alert)
            alert_data['timestamp'] = alert.timestamp.isoformat()
            
            self.producer.send(
                self.topics['alerts'],
                value=alert_data
            )
            
            KAFKA_MESSAGES_PRODUCED.labels(topic=self.topics['alerts']).inc()
            logger.info(f"Alert sent: {alert.id}")
            
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    async def run(self):
        """Main processing loop"""
        if not await self.initialize():
            logger.error("Failed to initialize stream processor")
            return
        
        self.running = True
        logger.info("Starting Kafka stream processor...")
        
        try:
            while self.running:
                # Consume messages from Kafka
                message_batch = self.consumer.poll(timeout_ms=1000)
                
                for topic_partition, messages in message_batch.items():
                    KAFKA_MESSAGES_CONSUMED.labels(topic=topic_partition.topic).inc()
                    
                    for message in messages:
                        try:
                            # Process mutation
                            alert = await self.process_mutation(message.value)
                            
                            # Send alert if generated
                            if alert:
                                await self.send_alert(alert)
                            
                            # Update processing rate
                            STREAM_PROCESSING_RATE.labels(processor_type='mutation').inc()
                            
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                
                # Update consumer lag metrics
                for topic_partition in self.consumer.assignment():
                    try:
                        committed = self.consumer.committed(topic_partition)
                        if committed:
                            high_water = self.consumer.get_watermark_offsets(topic_partition)[1]
                            lag = high_water - committed
                            KAFKA_CONSUMER_LAG.labels(
                                topic=topic_partition.topic,
                                partition=topic_partition.partition
                            ).set(lag)
                    except Exception as e:
                        logger.error(f"Error getting consumer lag: {e}")
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            logger.error(f"Error in main processing loop: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the stream processor"""
        self.running = False
        
        if self.consumer:
            self.consumer.close()
        
        if self.producer:
            self.producer.flush()
            self.producer.close()
        
        if self.neo4j_processor:
            self.neo4j_processor.driver.close()
        
        logger.info("Kafka stream processor shutdown complete")

async def main():
    """Main entry point"""
    # Configuration
    config = {
        'kafka_bootstrap_servers': 'kafka:9092',
        'neo4j_uri': 'bolt://neo4j:7687',
        'neo4j_username': 'neo4j',
        'neo4j_password': 'neo4j-password',
        'topics': {
            'mutations': 'mutations',
            'alerts': 'alerts',
            'clinical_feeds': 'clinical-feeds',
            'patient_data': 'patient-data',
            'analytics': 'analytics',
            'metrics': 'metrics'
        }
    }
    
    # Start Prometheus metrics server
    start_http_server(8080)
    logger.info("Prometheus metrics server started on port 8080")
    
    # Create and run stream processor
    processor = KafkaStreamProcessor(**config)
    await processor.run()

if __name__ == "__main__":
    asyncio.run(main())