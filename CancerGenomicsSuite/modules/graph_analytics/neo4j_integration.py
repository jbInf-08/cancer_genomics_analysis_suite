#!/usr/bin/env python3
"""
Neo4j Integration for Cancer Genomics Analysis

This module provides comprehensive Neo4j integration for graph-based
genomics data modeling, analysis, and visualization.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, AuthError
import networkx as nx
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """Enumeration of node types in the genomics graph."""
    GENE = "Gene"
    PROTEIN = "Protein"
    VARIANT = "Variant"
    PATHWAY = "Pathway"
    DISEASE = "Disease"
    DRUG = "Drug"
    SAMPLE = "Sample"
    PATIENT = "Patient"
    STUDY = "Study"
    PUBLICATION = "Publication"
    CLINICAL_TRIAL = "ClinicalTrial"
    BIOMARKER = "Biomarker"
    MUTATION = "Mutation"
    EXPRESSION = "Expression"
    COPY_NUMBER = "CopyNumber"
    METHYLATION = "Methylation"


class RelationshipType(Enum):
    """Enumeration of relationship types in the genomics graph."""
    INTERACTS_WITH = "INTERACTS_WITH"
    REGULATES = "REGULATES"
    EXPRESSES = "EXPRESSES"
    MUTATED_IN = "MUTATED_IN"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    TREATED_BY = "TREATED_BY"
    PARTICIPATES_IN = "PARTICIPATES_IN"
    PUBLISHED_IN = "PUBLISHED_IN"
    ENROLLED_IN = "ENROLLED_IN"
    PREDICTS = "PREDICTS"
    CORRELATES_WITH = "CORRELATES_WITH"
    COEXPRESSED_WITH = "COEXPRESSED_WITH"
    PATHWAY_MEMBER = "PATHWAY_MEMBER"
    DRUG_TARGET = "DRUG_TARGET"
    BIOMARKER_FOR = "BIOMARKER_FOR"


@dataclass
class GraphNode:
    """Represents a node in the genomics graph."""
    node_type: NodeType
    properties: Dict[str, Any]
    labels: List[str] = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = [self.node_type.value]


@dataclass
class GraphRelationship:
    """Represents a relationship in the genomics graph."""
    relationship_type: RelationshipType
    source_node: str
    target_node: str
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


class Neo4jGenomicsGraph:
    """
    Neo4j-based genomics graph database manager.
    
    Provides functionality to:
    - Connect to Neo4j database
    - Create and manage genomics graph schema
    - Import genomics data into graph format
    - Perform graph-based queries and analysis
    - Export graph data for visualization
    """
    
    def __init__(self, uri: str, username: str, password: str, database: str = "neo4j"):
        """
        Initialize Neo4j connection.
        
        Args:
            uri: Neo4j database URI
            username: Database username
            password: Database password
            database: Database name
        """
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.driver: Optional[Driver] = None
        self._connect()
    
    def _connect(self):
        """Establish connection to Neo4j database."""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            # Test connection
            with self.driver.session(database=self.database) as session:
                session.run("RETURN 1")
            logger.info(f"Connected to Neo4j database: {self.uri}")
        except (ServiceUnavailable, AuthError) as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    def create_schema(self):
        """Create genomics graph schema with constraints and indexes."""
        schema_queries = [
            # Create constraints
            "CREATE CONSTRAINT gene_id IF NOT EXISTS FOR (g:Gene) REQUIRE g.id IS UNIQUE",
            "CREATE CONSTRAINT protein_id IF NOT EXISTS FOR (p:Protein) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT variant_id IF NOT EXISTS FOR (v:Variant) REQUIRE v.id IS UNIQUE",
            "CREATE CONSTRAINT pathway_id IF NOT EXISTS FOR (p:Pathway) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT disease_id IF NOT EXISTS FOR (d:Disease) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT drug_id IF NOT EXISTS FOR (d:Drug) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT sample_id IF NOT EXISTS FOR (s:Sample) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT patient_id IF NOT EXISTS FOR (p:Patient) REQUIRE p.id IS UNIQUE",
            
            # Create indexes
            "CREATE INDEX gene_symbol IF NOT EXISTS FOR (g:Gene) ON (g.symbol)",
            "CREATE INDEX protein_name IF NOT EXISTS FOR (p:Protein) ON (p.name)",
            "CREATE INDEX variant_chromosome IF NOT EXISTS FOR (v:Variant) ON (v.chromosome)",
            "CREATE INDEX variant_position IF NOT EXISTS FOR (v:Variant) ON (v.position)",
            "CREATE INDEX pathway_name IF NOT EXISTS FOR (p:Pathway) ON (p.name)",
            "CREATE INDEX disease_name IF NOT EXISTS FOR (d:Disease) ON (d.name)",
            "CREATE INDEX drug_name IF NOT EXISTS FOR (d:Drug) ON (d.name)",
            "CREATE INDEX sample_type IF NOT EXISTS FOR (s:Sample) ON (s.type)",
            "CREATE INDEX patient_age IF NOT EXISTS FOR (p:Patient) ON (p.age)",
        ]
        
        with self.driver.session(database=self.database) as session:
            for query in schema_queries:
                try:
                    session.run(query)
                    logger.info(f"Executed schema query: {query[:50]}...")
                except Exception as e:
                    logger.warning(f"Schema query failed (may already exist): {e}")
    
    def create_node(self, node: GraphNode) -> bool:
        """
        Create a single node in the graph.
        
        Args:
            node: GraphNode object to create
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.driver.session(database=self.database) as session:
                # Build Cypher query
                labels = ":".join(node.labels)
                properties = json.dumps(node.properties).replace('"', "'")
                
                query = f"""
                MERGE (n:{labels} {{id: $id}})
                SET n += $properties
                RETURN n
                """
                
                result = session.run(query, {
                    "id": node.properties.get("id"),
                    "properties": node.properties
                })
                
                return result.single() is not None
                
        except Exception as e:
            logger.error(f"Failed to create node: {e}")
            return False
    
    def create_relationship(self, relationship: GraphRelationship) -> bool:
        """
        Create a relationship between two nodes.
        
        Args:
            relationship: GraphRelationship object to create
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.driver.session(database=self.database) as session:
                query = f"""
                MATCH (a {{id: $source_id}}), (b {{id: $target_id}})
                MERGE (a)-[r:{relationship.relationship_type.value}]->(b)
                SET r += $properties
                RETURN r
                """
                
                result = session.run(query, {
                    "source_id": relationship.source_node,
                    "target_id": relationship.target_node,
                    "properties": relationship.properties or {}
                })
                
                return result.single() is not None
                
        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            return False
    
    def import_genomics_data(self, data: Dict[str, pd.DataFrame]) -> Dict[str, int]:
        """
        Import genomics data into Neo4j graph.
        
        Args:
            data: Dictionary containing genomics data DataFrames
            
        Returns:
            Dictionary with import statistics
        """
        stats = {}
        
        try:
            with self.driver.session(database=self.database) as session:
                # Import genes
                if "genes" in data:
                    stats["genes"] = self._import_genes(session, data["genes"])
                
                # Import variants
                if "variants" in data:
                    stats["variants"] = self._import_variants(session, data["variants"])
                
                # Import pathways
                if "pathways" in data:
                    stats["pathways"] = self._import_pathways(session, data["pathways"])
                
                # Import samples
                if "samples" in data:
                    stats["samples"] = self._import_samples(session, data["samples"])
                
                # Import patients
                if "patients" in data:
                    stats["patients"] = self._import_patients(session, data["patients"])
                
                # Import relationships
                if "relationships" in data:
                    stats["relationships"] = self._import_relationships(session, data["relationships"])
                
        except Exception as e:
            logger.error(f"Failed to import genomics data: {e}")
            raise
        
        return stats
    
    def _import_genes(self, session: Session, genes_df: pd.DataFrame) -> int:
        """Import gene data into Neo4j."""
        query = """
        UNWIND $genes AS gene
        MERGE (g:Gene {id: gene.id})
        SET g += gene
        RETURN count(g) as count
        """
        
        genes_data = genes_df.to_dict('records')
        result = session.run(query, {"genes": genes_data})
        return result.single()["count"]
    
    def _import_variants(self, session: Session, variants_df: pd.DataFrame) -> int:
        """Import variant data into Neo4j."""
        query = """
        UNWIND $variants AS variant
        MERGE (v:Variant {id: variant.id})
        SET v += variant
        RETURN count(v) as count
        """
        
        variants_data = variants_df.to_dict('records')
        result = session.run(query, {"variants": variants_data})
        return result.single()["count"]
    
    def _import_pathways(self, session: Session, pathways_df: pd.DataFrame) -> int:
        """Import pathway data into Neo4j."""
        query = """
        UNWIND $pathways AS pathway
        MERGE (p:Pathway {id: pathway.id})
        SET p += pathway
        RETURN count(p) as count
        """
        
        pathways_data = pathways_df.to_dict('records')
        result = session.run(query, {"pathways": pathways_data})
        return result.single()["count"]
    
    def _import_samples(self, session: Session, samples_df: pd.DataFrame) -> int:
        """Import sample data into Neo4j."""
        query = """
        UNWIND $samples AS sample
        MERGE (s:Sample {id: sample.id})
        SET s += sample
        RETURN count(s) as count
        """
        
        samples_data = samples_df.to_dict('records')
        result = session.run(query, {"samples": samples_data})
        return result.single()["count"]
    
    def _import_patients(self, session: Session, patients_df: pd.DataFrame) -> int:
        """Import patient data into Neo4j."""
        query = """
        UNWIND $patients AS patient
        MERGE (p:Patient {id: patient.id})
        SET p += patient
        RETURN count(p) as count
        """
        
        patients_data = patients_df.to_dict('records')
        result = session.run(query, {"patients": patients_data})
        return result.single()["count"]
    
    def _import_relationships(self, session: Session, relationships_df: pd.DataFrame) -> int:
        """Import relationship data into Neo4j."""
        query = """
        UNWIND $relationships AS rel
        MATCH (a {id: rel.source_id}), (b {id: rel.target_id})
        MERGE (a)-[r:RELATIONSHIP]->(b)
        SET r += rel.properties
        RETURN count(r) as count
        """
        
        relationships_data = relationships_df.to_dict('records')
        result = session.run(query, {"relationships": relationships_data})
        return result.single()["count"]
    
    def query_graph(self, cypher_query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query on the graph.
        
        Args:
            cypher_query: Cypher query string
            parameters: Query parameters
            
        Returns:
            List of query results
        """
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(cypher_query, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []
    
    def find_gene_interactions(self, gene_id: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        """
        Find gene interactions up to specified depth.
        
        Args:
            gene_id: Gene identifier
            max_depth: Maximum interaction depth
            
        Returns:
            List of interaction results
        """
        query = f"""
        MATCH (g:Gene {{id: $gene_id}})-[r*1..{max_depth}]-(connected)
        RETURN g, r, connected
        ORDER BY length(r)
        """
        
        return self.query_graph(query, {"gene_id": gene_id})
    
    def find_pathway_genes(self, pathway_id: str) -> List[Dict[str, Any]]:
        """
        Find genes in a specific pathway.
        
        Args:
            pathway_id: Pathway identifier
            
        Returns:
            List of pathway genes
        """
        query = """
        MATCH (p:Pathway {id: $pathway_id})-[:PATHWAY_MEMBER]->(g:Gene)
        RETURN g
        ORDER BY g.symbol
        """
        
        return self.query_graph(query, {"pathway_id": pathway_id})
    
    def find_disease_genes(self, disease_id: str) -> List[Dict[str, Any]]:
        """
        Find genes associated with a disease.
        
        Args:
            disease_id: Disease identifier
            
        Returns:
            List of disease-associated genes
        """
        query = """
        MATCH (d:Disease {id: $disease_id})-[:ASSOCIATED_WITH]->(g:Gene)
        RETURN g
        ORDER BY g.symbol
        """
        
        return self.query_graph(query, {"disease_id": disease_id})
    
    def find_drug_targets(self, drug_id: str) -> List[Dict[str, Any]]:
        """
        Find targets for a specific drug.
        
        Args:
            drug_id: Drug identifier
            
        Returns:
            List of drug targets
        """
        query = """
        MATCH (d:Drug {id: $drug_id})-[:DRUG_TARGET]->(t)
        RETURN t
        ORDER BY t.name
        """
        
        return self.query_graph(query, {"drug_id": drug_id})
    
    def find_biomarkers(self, disease_id: str) -> List[Dict[str, Any]]:
        """
        Find biomarkers for a disease.
        
        Args:
            disease_id: Disease identifier
            
        Returns:
            List of biomarkers
        """
        query = """
        MATCH (d:Disease {id: $disease_id})-[:BIOMARKER_FOR]-(b:Biomarker)
        RETURN b
        ORDER BY b.name
        """
        
        return self.query_graph(query, {"disease_id": disease_id})
    
    def find_clinical_trials(self, gene_id: str) -> List[Dict[str, Any]]:
        """
        Find clinical trials for a gene.
        
        Args:
            gene_id: Gene identifier
            
        Returns:
            List of clinical trials
        """
        query = """
        MATCH (g:Gene {id: $gene_id})-[:PARTICIPATES_IN]->(ct:ClinicalTrial)
        RETURN ct
        ORDER BY ct.name
        """
        
        return self.query_graph(query, {"gene_id": gene_id})
    
    def find_publications(self, gene_id: str) -> List[Dict[str, Any]]:
        """
        Find publications related to a gene.
        
        Args:
            gene_id: Gene identifier
            
        Returns:
            List of publications
        """
        query = """
        MATCH (g:Gene {id: $gene_id})-[:PUBLISHED_IN]->(p:Publication)
        RETURN p
        ORDER BY p.year DESC
        """
        
        return self.query_graph(query, {"gene_id": gene_id})
    
    def find_network_analysis(self, gene_ids: List[str]) -> Dict[str, Any]:
        """
        Perform network analysis on a set of genes.
        
        Args:
            gene_ids: List of gene identifiers
            
        Returns:
            Network analysis results
        """
        # Find shortest paths between genes
        query = """
        MATCH (g1:Gene), (g2:Gene)
        WHERE g1.id IN $gene_ids AND g2.id IN $gene_ids AND g1.id < g2.id
        MATCH path = shortestPath((g1)-[*]-(g2))
        RETURN g1.id as source, g2.id as target, length(path) as distance
        """
        
        results = self.query_graph(query, {"gene_ids": gene_ids})
        
        # Calculate network metrics
        network_metrics = {
            "total_genes": len(gene_ids),
            "connected_pairs": len(results),
            "average_distance": np.mean([r["distance"] for r in results]) if results else 0,
            "max_distance": max([r["distance"] for r in results]) if results else 0,
            "min_distance": min([r["distance"] for r in results]) if results else 0
        }
        
        return network_metrics
    
    def export_to_networkx(self, gene_ids: List[str] = None) -> nx.Graph:
        """
        Export graph data to NetworkX format.
        
        Args:
            gene_ids: Optional list of gene IDs to filter
            
        Returns:
            NetworkX graph object
        """
        G = nx.Graph()
        
        # Get nodes
        if gene_ids:
            query = """
            MATCH (n)
            WHERE n.id IN $gene_ids
            RETURN n
            """
            nodes = self.query_graph(query, {"gene_ids": gene_ids})
        else:
            query = "MATCH (n) RETURN n"
            nodes = self.query_graph(query)
        
        # Add nodes to NetworkX graph
        for node in nodes:
            node_data = node["n"]
            G.add_node(node_data["id"], **node_data)
        
        # Get relationships
        if gene_ids:
            query = """
            MATCH (a)-[r]->(b)
            WHERE a.id IN $gene_ids AND b.id IN $gene_ids
            RETURN a.id as source, b.id as target, r
            """
            relationships = self.query_graph(query, {"gene_ids": gene_ids})
        else:
            query = """
            MATCH (a)-[r]->(b)
            RETURN a.id as source, b.id as target, r
            """
            relationships = self.query_graph(query)
        
        # Add edges to NetworkX graph
        for rel in relationships:
            G.add_edge(rel["source"], rel["target"], **rel["r"])
        
        return G
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive graph statistics.
        
        Returns:
            Dictionary with graph statistics
        """
        stats = {}
        
        # Node counts by type
        node_count_query = """
        MATCH (n)
        RETURN labels(n)[0] as label, count(n) as count
        ORDER BY count DESC
        """
        node_counts = self.query_graph(node_count_query)
        stats["node_counts"] = {item["label"]: item["count"] for item in node_counts}
        
        # Relationship counts by type
        rel_count_query = """
        MATCH ()-[r]->()
        RETURN type(r) as relationship_type, count(r) as count
        ORDER BY count DESC
        """
        rel_counts = self.query_graph(rel_count_query)
        stats["relationship_counts"] = {item["relationship_type"]: item["count"] for item in rel_counts}
        
        # Graph density
        total_nodes = sum(stats["node_counts"].values())
        total_relationships = sum(stats["relationship_counts"].values())
        stats["density"] = total_relationships / (total_nodes * (total_nodes - 1)) if total_nodes > 1 else 0
        
        # Average degree
        degree_query = """
        MATCH (n)
        RETURN avg(size((n)--())) as avg_degree
        """
        degree_result = self.query_graph(degree_query)
        stats["average_degree"] = degree_result[0]["avg_degree"] if degree_result else 0
        
        return stats
    
    def create_sample_workflow(self, sample_id: str, workflow_type: str) -> bool:
        """
        Create a workflow node for a sample.
        
        Args:
            sample_id: Sample identifier
            workflow_type: Type of workflow
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.driver.session(database=self.database) as session:
                query = """
                MATCH (s:Sample {id: $sample_id})
                CREATE (w:Workflow {
                    id: $workflow_id,
                    type: $workflow_type,
                    status: 'created',
                    created_at: datetime()
                })
                CREATE (s)-[:HAS_WORKFLOW]->(w)
                RETURN w
                """
                
                workflow_id = f"{sample_id}_{workflow_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                result = session.run(query, {
                    "sample_id": sample_id,
                    "workflow_id": workflow_id,
                    "workflow_type": workflow_type
                })
                
                return result.single() is not None
                
        except Exception as e:
            logger.error(f"Failed to create workflow: {e}")
            return False
    
    def update_workflow_status(self, workflow_id: str, status: str, results: Dict[str, Any] = None) -> bool:
        """
        Update workflow status and results.
        
        Args:
            workflow_id: Workflow identifier
            status: New status
            results: Optional results data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.driver.session(database=self.database) as session:
                query = """
                MATCH (w:Workflow {id: $workflow_id})
                SET w.status = $status,
                    w.updated_at = datetime()
                """
                
                if results:
                    query += ", w.results = $results"
                
                query += " RETURN w"
                
                params = {
                    "workflow_id": workflow_id,
                    "status": status
                }
                
                if results:
                    params["results"] = results
                
                result = session.run(query, params)
                return result.single() is not None
                
        except Exception as e:
            logger.error(f"Failed to update workflow status: {e}")
            return False
    
    def find_workflow_results(self, sample_id: str) -> List[Dict[str, Any]]:
        """
        Find workflow results for a sample.
        
        Args:
            sample_id: Sample identifier
            
        Returns:
            List of workflow results
        """
        query = """
        MATCH (s:Sample {id: $sample_id})-[:HAS_WORKFLOW]->(w:Workflow)
        RETURN w
        ORDER BY w.created_at DESC
        """
        
        return self.query_graph(query, {"sample_id": sample_id})
    
    def cleanup_old_data(self, days_old: int = 30) -> int:
        """
        Clean up old data from the graph.
        
        Args:
            days_old: Number of days old data to clean up
            
        Returns:
            Number of nodes deleted
        """
        try:
            with self.driver.session(database=self.database) as session:
                query = """
                MATCH (n)
                WHERE n.created_at < datetime() - duration('P%dD')
                DETACH DELETE n
                RETURN count(n) as deleted_count
                """ % days_old
                
                result = session.run(query)
                deleted_count = result.single()["deleted_count"]
                
                logger.info(f"Cleaned up {deleted_count} old nodes")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return 0


class GenomicsGraphAnalyzer:
    """
    Advanced graph analysis for genomics data.
    
    Provides specialized analysis methods for genomics graphs.
    """
    
    def __init__(self, neo4j_graph: Neo4jGenomicsGraph):
        """
        Initialize analyzer with Neo4j graph connection.
        
        Args:
            neo4j_graph: Neo4jGenomicsGraph instance
        """
        self.graph = neo4j_graph
    
    def find_disease_modules(self, disease_id: str) -> List[Dict[str, Any]]:
        """
        Find disease-associated gene modules.
        
        Args:
            disease_id: Disease identifier
            
        Returns:
            List of disease modules
        """
        query = """
        MATCH (d:Disease {id: $disease_id})-[:ASSOCIATED_WITH]->(g:Gene)
        MATCH (g)-[:INTERACTS_WITH]-(interacting_gene:Gene)
        WHERE (interacting_gene)-[:ASSOCIATED_WITH]->(d)
        RETURN g, interacting_gene, d
        """
        
        return self.graph.query_graph(query, {"disease_id": disease_id})
    
    def find_drug_repurposing_candidates(self, disease_id: str) -> List[Dict[str, Any]]:
        """
        Find drug repurposing candidates for a disease.
        
        Args:
            disease_id: Disease identifier
            
        Returns:
            List of drug repurposing candidates
        """
        query = """
        MATCH (d:Disease {id: $disease_id})-[:ASSOCIATED_WITH]->(g:Gene)
        MATCH (g)<-[:DRUG_TARGET]-(drug:Drug)
        MATCH (drug)-[:TREATED_BY]->(other_disease:Disease)
        WHERE other_disease.id <> $disease_id
        RETURN drug, other_disease, count(g) as target_count
        ORDER BY target_count DESC
        """
        
        return self.graph.query_graph(query, {"disease_id": disease_id})
    
    def find_biomarker_combinations(self, disease_id: str) -> List[Dict[str, Any]]:
        """
        Find biomarker combinations for disease diagnosis.
        
        Args:
            disease_id: Disease identifier
            
        Returns:
            List of biomarker combinations
        """
        query = """
        MATCH (d:Disease {id: $disease_id})-[:BIOMARKER_FOR]-(b1:Biomarker)
        MATCH (d)-[:BIOMARKER_FOR]-(b2:Biomarker)
        WHERE b1.id < b2.id
        MATCH (b1)-[:CORRELATES_WITH]-(b2)
        RETURN b1, b2, d
        """
        
        return self.graph.query_graph(query, {"disease_id": disease_id})
    
    def find_pathway_enrichment(self, gene_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Find pathway enrichment for a set of genes.
        
        Args:
            gene_ids: List of gene identifiers
            
        Returns:
            List of enriched pathways
        """
        query = """
        MATCH (g:Gene)
        WHERE g.id IN $gene_ids
        MATCH (g)-[:PATHWAY_MEMBER]->(p:Pathway)
        RETURN p, count(g) as gene_count
        ORDER BY gene_count DESC
        """
        
        return self.graph.query_graph(query, {"gene_ids": gene_ids})
    
    def find_clinical_trial_opportunities(self, gene_id: str) -> List[Dict[str, Any]]:
        """
        Find clinical trial opportunities for a gene.
        
        Args:
            gene_id: Gene identifier
            
        Returns:
            List of clinical trial opportunities
        """
        query = """
        MATCH (g:Gene {id: $gene_id})
        MATCH (g)-[:ASSOCIATED_WITH]->(d:Disease)
        MATCH (d)<-[:TREATED_BY]-(drug:Drug)
        MATCH (drug)-[:PARTICIPATES_IN]->(ct:ClinicalTrial)
        WHERE ct.status = 'recruiting'
        RETURN ct, drug, d
        ORDER BY ct.start_date
        """
        
        return self.graph.query_graph(query, {"gene_id": gene_id})
    
    def find_publication_networks(self, gene_id: str) -> List[Dict[str, Any]]:
        """
        Find publication networks for a gene.
        
        Args:
            gene_id: Gene identifier
            
        Returns:
            List of publication networks
        """
        query = """
        MATCH (g:Gene {id: $gene_id})-[:PUBLISHED_IN]->(p:Publication)
        MATCH (p)-[:COAUTHORED_BY]->(author:Author)
        MATCH (author)-[:COAUTHORED_BY]->(other_pub:Publication)
        MATCH (other_pub)<-[:PUBLISHED_IN]-(other_gene:Gene)
        WHERE other_gene.id <> $gene_id
        RETURN g, p, author, other_pub, other_gene
        """
        
        return self.graph.query_graph(query, {"gene_id": gene_id})
    
    def find_expression_correlations(self, gene_id: str) -> List[Dict[str, Any]]:
        """
        Find expression correlations for a gene.
        
        Args:
            gene_id: Gene identifier
            
        Returns:
            List of expression correlations
        """
        query = """
        MATCH (g:Gene {id: $gene_id})-[:COEXPRESSED_WITH]-(correlated_gene:Gene)
        MATCH (g)-[:EXPRESSES]->(e1:Expression)
        MATCH (correlated_gene)-[:EXPRESSES]->(e2:Expression)
        WHERE e1.sample_id = e2.sample_id
        RETURN g, correlated_gene, e1, e2
        ORDER BY e1.value DESC
        """
        
        return self.graph.query_graph(query, {"gene_id": gene_id})
    
    def find_mutation_hotspots(self, gene_id: str) -> List[Dict[str, Any]]:
        """
        Find mutation hotspots in a gene.
        
        Args:
            gene_id: Gene identifier
            
        Returns:
            List of mutation hotspots
        """
        query = """
        MATCH (g:Gene {id: $gene_id})-[:MUTATED_IN]->(v:Variant)
        MATCH (v)-[:ASSOCIATED_WITH]->(d:Disease)
        RETURN g, v, d, count(d) as disease_count
        ORDER BY disease_count DESC
        """
        
        return self.graph.query_graph(query, {"gene_id": gene_id})
    
    def find_copy_number_alterations(self, gene_id: str) -> List[Dict[str, Any]]:
        """
        Find copy number alterations for a gene.
        
        Args:
            gene_id: Gene identifier
            
        Returns:
            List of copy number alterations
        """
        query = """
        MATCH (g:Gene {id: $gene_id})-[:COPY_NUMBER]->(cna:CopyNumber)
        MATCH (cna)-[:ASSOCIATED_WITH]->(d:Disease)
        RETURN g, cna, d
        ORDER BY cna.value DESC
        """
        
        return self.graph.query_graph(query, {"gene_id": gene_id})
    
    def find_methylation_patterns(self, gene_id: str) -> List[Dict[str, Any]]:
        """
        Find methylation patterns for a gene.
        
        Args:
            gene_id: Gene identifier
            
        Returns:
            List of methylation patterns
        """
        query = """
        MATCH (g:Gene {id: $gene_id})-[:METHYLATION]->(m:Methylation)
        MATCH (m)-[:ASSOCIATED_WITH]->(d:Disease)
        RETURN g, m, d
        ORDER BY m.value DESC
        """
        
        return self.graph.query_graph(query, {"gene_id": gene_id})
    
    def find_network_centrality(self, gene_ids: List[str]) -> Dict[str, Any]:
        """
        Calculate network centrality measures for genes.
        
        Args:
            gene_ids: List of gene identifiers
            
        Returns:
            Dictionary with centrality measures
        """
        # Export to NetworkX for centrality calculations
        G = self.graph.export_to_networkx(gene_ids)
        
        if len(G.nodes()) == 0:
            return {}
        
        centrality_measures = {
            "degree_centrality": nx.degree_centrality(G),
            "betweenness_centrality": nx.betweenness_centrality(G),
            "closeness_centrality": nx.closeness_centrality(G),
            "eigenvector_centrality": nx.eigenvector_centrality(G, max_iter=1000),
            "pagerank": nx.pagerank(G)
        }
        
        return centrality_measures
    
    def find_community_structure(self, gene_ids: List[str]) -> Dict[str, Any]:
        """
        Find community structure in gene network.
        
        Args:
            gene_ids: List of gene identifiers
            
        Returns:
            Dictionary with community structure
        """
        # Export to NetworkX for community detection
        G = self.graph.export_to_networkx(gene_ids)
        
        if len(G.nodes()) == 0:
            return {}
        
        # Use Louvain algorithm for community detection
        try:
            import networkx.algorithms.community as nx_comm
            communities = nx_comm.louvain_communities(G)
            
            community_structure = {
                "communities": list(communities),
                "modularity": nx_comm.modularity(G, communities),
                "number_of_communities": len(communities),
                "community_sizes": [len(community) for community in communities]
            }
            
            return community_structure
            
        except ImportError:
            logger.warning("NetworkX community detection not available")
            return {}
    
    def find_graph_motifs(self, gene_ids: List[str]) -> Dict[str, Any]:
        """
        Find graph motifs in gene network.
        
        Args:
            gene_ids: List of gene identifiers
            
        Returns:
            Dictionary with motif information
        """
        # Export to NetworkX for motif analysis
        G = self.graph.export_to_networkx(gene_ids)
        
        if len(G.nodes()) == 0:
            return {}
        
        motifs = {
            "triangles": len(list(nx.triangles(G).values())),
            "clustering_coefficient": nx.average_clustering(G),
            "transitivity": nx.transitivity(G),
            "density": nx.density(G)
        }
        
        return motifs


def create_sample_genomics_graph() -> Neo4jGenomicsGraph:
    """
    Create a sample genomics graph with test data.
    
    Returns:
        Neo4jGenomicsGraph instance with sample data
    """
    # Initialize graph
    graph = Neo4jGenomicsGraph(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        username=os.getenv("NEO4J_USERNAME", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password"),
        database=os.getenv("NEO4J_DATABASE", "neo4j")
    )
    
    # Create schema
    graph.create_schema()
    
    # Create sample data
    sample_data = {
        "genes": pd.DataFrame([
            {"id": "GENE1", "symbol": "BRCA1", "name": "Breast cancer type 1 susceptibility protein", "chromosome": "17", "start": 43094690, "end": 43125364},
            {"id": "GENE2", "symbol": "BRCA2", "name": "Breast cancer type 2 susceptibility protein", "chromosome": "13", "start": 32315086, "end": 32400266},
            {"id": "GENE3", "symbol": "TP53", "name": "Tumor protein p53", "chromosome": "17", "start": 7661779, "end": 7687550},
            {"id": "GENE4", "symbol": "EGFR", "name": "Epidermal growth factor receptor", "chromosome": "7", "start": 55019017, "end": 55211628},
            {"id": "GENE5", "symbol": "KRAS", "name": "KRAS proto-oncogene", "chromosome": "12", "start": 25204789, "end": 25252093}
        ]),
        
        "variants": pd.DataFrame([
            {"id": "VAR1", "gene_id": "GENE1", "chromosome": "17", "position": 43094690, "ref": "A", "alt": "T", "type": "SNV"},
            {"id": "VAR2", "gene_id": "GENE2", "chromosome": "13", "position": 32315086, "ref": "G", "alt": "C", "type": "SNV"},
            {"id": "VAR3", "gene_id": "GENE3", "chromosome": "17", "position": 7661779, "ref": "T", "alt": "G", "type": "SNV"},
            {"id": "VAR4", "gene_id": "GENE4", "chromosome": "7", "position": 55019017, "ref": "C", "alt": "A", "type": "SNV"},
            {"id": "VAR5", "gene_id": "GENE5", "chromosome": "12", "position": 25204789, "ref": "A", "alt": "G", "type": "SNV"}
        ]),
        
        "pathways": pd.DataFrame([
            {"id": "PATH1", "name": "DNA repair", "description": "Pathway involved in DNA repair mechanisms"},
            {"id": "PATH2", "name": "Cell cycle", "description": "Pathway involved in cell cycle regulation"},
            {"id": "PATH3", "name": "Growth factor signaling", "description": "Pathway involved in growth factor signaling"}
        ]),
        
        "samples": pd.DataFrame([
            {"id": "SAMPLE1", "type": "tumor", "tissue": "breast", "patient_id": "PATIENT1"},
            {"id": "SAMPLE2", "type": "normal", "tissue": "breast", "patient_id": "PATIENT1"},
            {"id": "SAMPLE3", "type": "tumor", "tissue": "lung", "patient_id": "PATIENT2"},
            {"id": "SAMPLE4", "type": "normal", "tissue": "lung", "patient_id": "PATIENT2"}
        ]),
        
        "patients": pd.DataFrame([
            {"id": "PATIENT1", "age": 45, "gender": "female", "diagnosis": "breast_cancer"},
            {"id": "PATIENT2", "age": 62, "gender": "male", "diagnosis": "lung_cancer"},
            {"id": "PATIENT3", "age": 38, "gender": "female", "diagnosis": "ovarian_cancer"}
        ])
    }
    
    # Import data
    stats = graph.import_genomics_data(sample_data)
    logger.info(f"Imported sample data: {stats}")
    
    return graph


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Create sample graph
    graph = create_sample_genomics_graph()
    
    try:
        # Get graph statistics
        stats = graph.get_graph_statistics()
        print("Graph Statistics:", json.dumps(stats, indent=2))
        
        # Find gene interactions
        interactions = graph.find_gene_interactions("GENE1", max_depth=2)
        print(f"Found {len(interactions)} interactions for GENE1")
        
        # Create analyzer
        analyzer = GenomicsGraphAnalyzer(graph)
        
        # Find network centrality
        centrality = analyzer.find_network_centrality(["GENE1", "GENE2", "GENE3"])
        print("Network Centrality:", json.dumps(centrality, indent=2))
        
    finally:
        graph.close()
