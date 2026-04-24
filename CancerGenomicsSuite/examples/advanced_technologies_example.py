#!/usr/bin/env python3
"""
Advanced Technologies Integration Example

This example demonstrates how to use all the advanced technologies
integrated into the Cancer Genomics Analysis Suite:
- Pipeline Orchestration (Nextflow/Snakemake)
- Graph Analytics (Neo4j/NetworkX)
- Real-time Processing (Apache Kafka)
- OAuth2 Authentication (Keycloak/Auth0)
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Settings
from modules.pipeline_orchestration.nextflow_manager import NextflowManager
from modules.pipeline_orchestration.snakemake_manager import SnakemakeManager
from modules.graph_analytics.neo4j_manager import Neo4jManager
from modules.graph_analytics.networkx_analyzer import NetworkXAnalyzer
from modules.real_time_processing.kafka_manager import KafkaManager
from modules.oauth2_auth.keycloak_client import KeycloakClient
from modules.oauth2_auth.auth0_client import Auth0Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AdvancedTechnologiesDemo:
    """Demonstration class for advanced technologies integration."""
    
    def __init__(self):
        """Initialize the demo with configuration."""
        self.settings = Settings()
        self.setup_managers()
        
    def setup_managers(self):
        """Initialize all technology managers."""
        try:
            # Pipeline Orchestration
            if self.settings.features.enable_pipeline_orchestration:
                self.nextflow_manager = NextflowManager()
                self.snakemake_manager = SnakemakeManager()
                logger.info("Pipeline orchestration managers initialized")
            
            # Graph Analytics
            if self.settings.features.enable_graph_analytics:
                self.neo4j_manager = Neo4jManager()
                self.networkx_analyzer = NetworkXAnalyzer()
                logger.info("Graph analytics managers initialized")
            
            # Real-time Processing
            if self.settings.features.enable_kafka_streaming:
                self.kafka_manager = KafkaManager()
                logger.info("Kafka manager initialized")
            
            # OAuth2 Authentication
            if self.settings.features.enable_oauth2_auth:
                if self.settings.oauth2.keycloak_enabled:
                    self.keycloak_client = KeycloakClient()
                if self.settings.oauth2.auth0_enabled:
                    self.auth0_client = Auth0Client()
                logger.info("OAuth2 clients initialized")
                
        except Exception as e:
            logger.error(f"Error initializing managers: {e}")
            raise
    
    async def demonstrate_pipeline_orchestration(self):
        """Demonstrate pipeline orchestration capabilities."""
        logger.info("=== Pipeline Orchestration Demo ===")
        
        if not self.settings.features.enable_pipeline_orchestration:
            logger.info("Pipeline orchestration is disabled")
            return
        
        try:
            # Example Nextflow pipeline execution
            logger.info("Executing Nextflow pipeline...")
            nextflow_result = await self.nextflow_manager.execute_pipeline(
                pipeline_path="examples/pipelines/variant_calling.nf",
                input_data="examples/data/samples/",
                output_dir="examples/results/variants/",
                config={
                    "reference_genome": "hg38",
                    "threads": 4,
                    "memory": "8GB"
                }
            )
            logger.info(f"Nextflow pipeline result: {nextflow_result}")
            
            # Example Snakemake workflow execution
            logger.info("Executing Snakemake workflow...")
            snakemake_result = await self.snakemake_manager.execute_workflow(
                snakefile="examples/workflows/rna_seq_analysis.smk",
                config_file="examples/configs/rna_seq_config.yaml",
                cores=8,
                config={
                    "samples": ["S001", "S002", "S003"],
                    "reference": "hg38",
                    "threads": 4
                }
            )
            logger.info(f"Snakemake workflow result: {snakemake_result}")
            
        except Exception as e:
            logger.error(f"Pipeline orchestration demo failed: {e}")
    
    async def demonstrate_graph_analytics(self):
        """Demonstrate graph analytics capabilities."""
        logger.info("=== Graph Analytics Demo ===")
        
        if not self.settings.features.enable_graph_analytics:
            logger.info("Graph analytics is disabled")
            return
        
        try:
            # Example Neo4j operations
            logger.info("Creating gene interaction network in Neo4j...")
            await self.neo4j_manager.create_gene_network(
                genes=["BRCA1", "BRCA2", "TP53", "EGFR", "MYC"],
                interactions="examples/data/gene_interactions.csv"
            )
            
            # Query gene relationships
            relationships = await self.neo4j_manager.get_gene_relationships("BRCA1")
            logger.info(f"BRCA1 relationships: {relationships}")
            
            # Example NetworkX analysis
            logger.info("Building expression network with NetworkX...")
            network = await self.networkx_analyzer.build_expression_network(
                expression_data="examples/data/gene_expression.csv",
                correlation_threshold=0.7
            )
            
            # Calculate centrality measures
            centrality = await self.networkx_analyzer.calculate_centrality(network)
            logger.info(f"Network centrality measures: {centrality}")
            
            # Community detection
            communities = await self.networkx_analyzer.detect_communities(network)
            logger.info(f"Detected communities: {len(communities)}")
            
        except Exception as e:
            logger.error(f"Graph analytics demo failed: {e}")
    
    async def demonstrate_real_time_processing(self):
        """Demonstrate real-time processing capabilities."""
        logger.info("=== Real-time Processing Demo ===")
        
        if not self.settings.features.enable_kafka_streaming:
            logger.info("Kafka streaming is disabled")
            return
        
        try:
            # Send genomics data to Kafka
            logger.info("Sending genomics data to Kafka...")
            sample_data = {
                "sample_id": "S001",
                "patient_id": "P001",
                "gene_expression": {
                    "BRCA1": 2.5,
                    "BRCA2": 1.8,
                    "TP53": 3.2
                },
                "mutations": [
                    {"gene": "BRCA1", "variant": "c.5266dupC", "type": "frameshift"}
                ],
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "tissue_type": "breast",
                    "stage": "IIA",
                    "grade": "2"
                }
            }
            
            await self.kafka_manager.send_data(
                topic=self.settings.kafka.kafka_data_topic,
                data=sample_data
            )
            logger.info("Genomics data sent to Kafka")
            
            # Process streaming data
            logger.info("Processing streaming data...")
            processed_data = await self.kafka_manager.process_streaming_data(
                topic=self.settings.kafka.kafka_data_topic,
                processor=self.process_genomics_data
            )
            logger.info(f"Processed data: {processed_data}")
            
        except Exception as e:
            logger.error(f"Real-time processing demo failed: {e}")
    
    async def demonstrate_oauth2_authentication(self):
        """Demonstrate OAuth2 authentication capabilities."""
        logger.info("=== OAuth2 Authentication Demo ===")
        
        if not self.settings.features.enable_oauth2_auth:
            logger.info("OAuth2 authentication is disabled")
            return
        
        try:
            # Example Keycloak authentication
            if self.settings.oauth2.keycloak_enabled:
                logger.info("Testing Keycloak authentication...")
                user_info = await self.keycloak_client.authenticate_user(
                    username="demo@example.com",
                    password="demo_password"
                )
                logger.info(f"Keycloak user info: {user_info}")
                
                # Get user roles
                roles = await self.keycloak_client.get_user_roles(user_info["sub"])
                logger.info(f"User roles: {roles}")
            
            # Example Auth0 authentication
            if self.settings.oauth2.auth0_enabled:
                logger.info("Testing Auth0 authentication...")
                user_info = await self.auth0_client.authenticate_user(
                    email="demo@example.com",
                    password="demo_password"
                )
                logger.info(f"Auth0 user info: {user_info}")
                
                # Get user profile
                profile = await self.auth0_client.get_user_profile(user_info["sub"])
                logger.info(f"User profile: {profile}")
            
        except Exception as e:
            logger.error(f"OAuth2 authentication demo failed: {e}")
    
    async def process_genomics_data(self, data: Dict) -> Dict:
        """Process genomics data from Kafka stream."""
        logger.info(f"Processing genomics data for sample: {data.get('sample_id')}")
        
        # Simulate data processing
        processed_data = {
            "sample_id": data.get("sample_id"),
            "processed_at": datetime.now().isoformat(),
            "analysis_results": {
                "expression_summary": {
                    "total_genes": len(data.get("gene_expression", {})),
                    "high_expression": sum(1 for v in data.get("gene_expression", {}).values() if v > 2.0)
                },
                "mutation_summary": {
                    "total_mutations": len(data.get("mutations", [])),
                    "pathogenic_mutations": len([m for m in data.get("mutations", []) if m.get("type") == "frameshift"])
                }
            }
        }
        
        return processed_data
    
    async def run_comprehensive_demo(self):
        """Run a comprehensive demonstration of all technologies."""
        logger.info("Starting Advanced Technologies Comprehensive Demo")
        
        try:
            # Run all demonstrations
            await self.demonstrate_pipeline_orchestration()
            await self.demonstrate_graph_analytics()
            await self.demonstrate_real_time_processing()
            await self.demonstrate_oauth2_authentication()
            
            logger.info("Advanced Technologies Demo completed successfully!")
            
        except Exception as e:
            logger.error(f"Comprehensive demo failed: {e}")
            raise
    
    async def run_integrated_workflow(self):
        """Run an integrated workflow using all technologies."""
        logger.info("=== Integrated Workflow Demo ===")
        
        try:
            # Step 1: Authenticate user
            if self.settings.features.enable_oauth2_auth:
                logger.info("Step 1: User Authentication")
                if self.settings.oauth2.keycloak_enabled:
                    user_info = await self.keycloak_client.authenticate_user(
                        username="researcher@example.com",
                        password="research_password"
                    )
                    logger.info(f"User authenticated: {user_info['preferred_username']}")
            
            # Step 2: Execute analysis pipeline
            if self.settings.features.enable_pipeline_orchestration:
                logger.info("Step 2: Pipeline Execution")
                pipeline_result = await self.nextflow_manager.execute_pipeline(
                    pipeline_path="examples/pipelines/integrated_analysis.nf",
                    input_data="examples/data/integrated_samples/",
                    output_dir="examples/results/integrated_analysis/"
                )
                logger.info("Pipeline execution completed")
            
            # Step 3: Build and analyze gene network
            if self.settings.features.enable_graph_analytics:
                logger.info("Step 3: Graph Analysis")
                network = await self.networkx_analyzer.build_expression_network(
                    expression_data="examples/results/integrated_analysis/expression_data.csv",
                    correlation_threshold=0.8
                )
                
                # Store network in Neo4j
                await self.neo4j_manager.create_gene_network(
                    genes=list(network.nodes()),
                    interactions="examples/results/integrated_analysis/network_edges.csv"
                )
                logger.info("Graph analysis completed")
            
            # Step 4: Stream results to Kafka
            if self.settings.features.enable_kafka_streaming:
                logger.info("Step 4: Real-time Results Streaming")
                results_data = {
                    "analysis_id": "INT_001",
                    "pipeline_result": pipeline_result,
                    "network_summary": {
                        "nodes": len(network.nodes()),
                        "edges": len(network.edges())
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
                await self.kafka_manager.send_data(
                    topic=self.settings.kafka.kafka_results_topic,
                    data=results_data
                )
                logger.info("Results streamed to Kafka")
            
            logger.info("Integrated workflow completed successfully!")
            
        except Exception as e:
            logger.error(f"Integrated workflow failed: {e}")
            raise


async def main():
    """Main function to run the demonstration."""
    try:
        # Create demo instance
        demo = AdvancedTechnologiesDemo()
        
        # Run comprehensive demo
        await demo.run_comprehensive_demo()
        
        # Run integrated workflow
        await demo.run_integrated_workflow()
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main())
