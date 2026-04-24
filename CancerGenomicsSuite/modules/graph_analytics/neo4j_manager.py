#!/usr/bin/env python3
"""
Neo4j Manager

This module provides comprehensive Neo4j database management capabilities
for cancer genomics graph analytics.
"""

import logging
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime
import json
import pandas as pd

try:
    from neo4j import GraphDatabase
    from py2neo import Graph, Node, Relationship, NodeMatcher, RelationshipMatcher
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logging.warning("Neo4j drivers not available. Install neo4j and py2neo packages.")

logger = logging.getLogger(__name__)


class Neo4jManager:
    """
    Manager for Neo4j graph database operations in cancer genomics analysis.
    
    Provides functionality to:
    - Connect to Neo4j database
    - Create and manage nodes and relationships
    - Execute Cypher queries
    - Import/export graph data
    - Perform graph analytics
    """
    
    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        username: str = "neo4j",
        password: str = "password",
        database: str = "neo4j"
    ):
        """
        Initialize Neo4j manager.
        
        Args:
            uri: Neo4j database URI
            username: Database username
            password: Database password
            database: Database name
        """
        if not NEO4J_AVAILABLE:
            raise ImportError("Neo4j drivers not available. Install neo4j and py2neo packages.")
        
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        
        # Initialize drivers
        self.driver = None
        self.graph = None
        self.node_matcher = None
        self.relationship_matcher = None
        
        # Connect to database
        self.connect()
    
    def connect(self):
        """Connect to Neo4j database."""
        try:
            # Initialize official driver
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            
            # Initialize py2neo graph
            self.graph = Graph(
                self.uri,
                auth=(self.username, self.password),
                database=self.database
            )
            
            # Initialize matchers
            self.node_matcher = NodeMatcher(self.graph)
            self.relationship_matcher = RelationshipMatcher(self.graph)
            
            # Test connection
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                result.single()
            
            logger.info(f"Connected to Neo4j database: {self.uri}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from Neo4j database."""
        if self.driver:
            self.driver.close()
            logger.info("Disconnected from Neo4j database")
    
    def create_gene_node(
        self,
        gene_id: str,
        gene_name: str,
        chromosome: str,
        start_pos: int,
        end_pos: int,
        strand: str,
        properties: Optional[Dict] = None
    ) -> Node:
        """
        Create a gene node in the graph.
        
        Args:
            gene_id: Gene identifier (e.g., ENSG00000139618)
            gene_name: Gene symbol (e.g., BRCA1)
            chromosome: Chromosome number
            start_pos: Start position
            end_pos: End position
            strand: Strand (+ or -)
            properties: Additional properties
            
        Returns:
            Created gene node
        """
        node_properties = {
            "gene_id": gene_id,
            "gene_name": gene_name,
            "chromosome": chromosome,
            "start_pos": start_pos,
            "end_pos": end_pos,
            "strand": strand,
            "created_at": datetime.now().isoformat(),
            **(properties or {})
        }
        
        gene_node = Node("Gene", **node_properties)
        self.graph.create(gene_node)
        
        logger.debug(f"Created gene node: {gene_name} ({gene_id})")
        return gene_node
    
    def create_protein_node(
        self,
        protein_id: str,
        protein_name: str,
        uniprot_id: Optional[str] = None,
        properties: Optional[Dict] = None
    ) -> Node:
        """
        Create a protein node in the graph.
        
        Args:
            protein_id: Protein identifier
            protein_name: Protein name
            uniprot_id: UniProt identifier
            properties: Additional properties
            
        Returns:
            Created protein node
        """
        node_properties = {
            "protein_id": protein_id,
            "protein_name": protein_name,
            "uniprot_id": uniprot_id,
            "created_at": datetime.now().isoformat(),
            **(properties or {})
        }
        
        protein_node = Node("Protein", **node_properties)
        self.graph.create(protein_node)
        
        logger.debug(f"Created protein node: {protein_name} ({protein_id})")
        return protein_node
    
    def create_variant_node(
        self,
        variant_id: str,
        chromosome: str,
        position: int,
        ref_allele: str,
        alt_allele: str,
        variant_type: str,
        properties: Optional[Dict] = None
    ) -> Node:
        """
        Create a variant node in the graph.
        
        Args:
            variant_id: Variant identifier
            chromosome: Chromosome
            position: Genomic position
            ref_allele: Reference allele
            alt_allele: Alternative allele
            variant_type: Type of variant (SNV, INDEL, etc.)
            properties: Additional properties
            
        Returns:
            Created variant node
        """
        node_properties = {
            "variant_id": variant_id,
            "chromosome": chromosome,
            "position": position,
            "ref_allele": ref_allele,
            "alt_allele": alt_allele,
            "variant_type": variant_type,
            "created_at": datetime.now().isoformat(),
            **(properties or {})
        }
        
        variant_node = Node("Variant", **node_properties)
        self.graph.create(variant_node)
        
        logger.debug(f"Created variant node: {variant_id}")
        return variant_node
    
    def create_patient_node(
        self,
        patient_id: str,
        age: Optional[int] = None,
        gender: Optional[str] = None,
        cancer_type: Optional[str] = None,
        properties: Optional[Dict] = None
    ) -> Node:
        """
        Create a patient node in the graph.
        
        Args:
            patient_id: Patient identifier
            age: Patient age
            gender: Patient gender
            cancer_type: Type of cancer
            properties: Additional properties
            
        Returns:
            Created patient node
        """
        node_properties = {
            "patient_id": patient_id,
            "age": age,
            "gender": gender,
            "cancer_type": cancer_type,
            "created_at": datetime.now().isoformat(),
            **(properties or {})
        }
        
        patient_node = Node("Patient", **node_properties)
        self.graph.create(patient_node)
        
        logger.debug(f"Created patient node: {patient_id}")
        return patient_node
    
    def create_relationship(
        self,
        start_node: Node,
        relationship_type: str,
        end_node: Node,
        properties: Optional[Dict] = None
    ) -> Relationship:
        """
        Create a relationship between two nodes.
        
        Args:
            start_node: Start node
            relationship_type: Type of relationship
            end_node: End node
            properties: Relationship properties
            
        Returns:
            Created relationship
        """
        rel_properties = {
            "created_at": datetime.now().isoformat(),
            **(properties or {})
        }
        
        relationship = Relationship(start_node, relationship_type, end_node, **rel_properties)
        self.graph.create(relationship)
        
        logger.debug(f"Created relationship: {start_node} -[{relationship_type}]-> {end_node}")
        return relationship
    
    def execute_cypher_query(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """
        Execute a Cypher query.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            Query results
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Failed to execute Cypher query: {e}")
            raise
    
    def find_genes_by_chromosome(self, chromosome: str) -> List[Node]:
        """
        Find all genes on a specific chromosome.
        
        Args:
            chromosome: Chromosome number
            
        Returns:
            List of gene nodes
        """
        query = """
        MATCH (g:Gene)
        WHERE g.chromosome = $chromosome
        RETURN g
        ORDER BY g.start_pos
        """
        
        results = self.execute_cypher_query(query, {"chromosome": chromosome})
        return [result["g"] for result in results]
    
    def find_variants_in_gene(self, gene_name: str) -> List[Dict]:
        """
        Find all variants in a specific gene.
        
        Args:
            gene_name: Gene symbol
            
        Returns:
            List of variant information
        """
        query = """
        MATCH (g:Gene {gene_name: $gene_name})
        MATCH (v:Variant)
        WHERE v.chromosome = g.chromosome 
        AND v.position >= g.start_pos 
        AND v.position <= g.end_pos
        RETURN v, g
        ORDER BY v.position
        """
        
        return self.execute_cypher_query(query, {"gene_name": gene_name})
    
    def find_protein_interactions(self, protein_name: str) -> List[Dict]:
        """
        Find protein-protein interactions for a specific protein.
        
        Args:
            protein_name: Protein name
            
        Returns:
            List of interaction information
        """
        query = """
        MATCH (p1:Protein {protein_name: $protein_name})
        MATCH (p1)-[r:INTERACTS_WITH]-(p2:Protein)
        RETURN p1, r, p2
        """
        
        return self.execute_cypher_query(query, {"protein_name": protein_name})
    
    def find_pathway_genes(self, pathway_name: str) -> List[Dict]:
        """
        Find all genes in a specific pathway.
        
        Args:
            pathway_name: Pathway name
            
        Returns:
            List of gene information
        """
        query = """
        MATCH (p:Pathway {pathway_name: $pathway_name})
        MATCH (p)-[:CONTAINS]->(g:Gene)
        RETURN g, p
        ORDER BY g.gene_name
        """
        
        return self.execute_cypher_query(query, {"pathway_name": pathway_name})
    
    def find_patient_mutations(self, patient_id: str) -> List[Dict]:
        """
        Find all mutations for a specific patient.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            List of mutation information
        """
        query = """
        MATCH (pt:Patient {patient_id: $patient_id})
        MATCH (pt)-[:HAS_MUTATION]->(v:Variant)
        MATCH (v)-[:AFFECTS]->(g:Gene)
        RETURN pt, v, g
        ORDER BY v.chromosome, v.position
        """
        
        return self.execute_cypher_query(query, {"patient_id": patient_id})
    
    def calculate_gene_centrality(self, gene_name: str) -> Dict[str, float]:
        """
        Calculate centrality measures for a gene.
        
        Args:
            gene_name: Gene symbol
            
        Returns:
            Dictionary with centrality measures
        """
        # Degree centrality
        degree_query = """
        MATCH (g:Gene {gene_name: $gene_name})
        MATCH (g)-[r]-(connected)
        RETURN count(r) as degree_centrality
        """
        
        degree_result = self.execute_cypher_query(degree_query, {"gene_name": gene_name})
        degree_centrality = degree_result[0]["degree_centrality"] if degree_result else 0
        
        # Betweenness centrality (simplified)
        betweenness_query = """
        MATCH (g:Gene {gene_name: $gene_name})
        MATCH path = shortestPath((start)-[*]-(end))
        WHERE g IN nodes(path)
        AND start <> g AND end <> g
        RETURN count(path) as betweenness_centrality
        """
        
        betweenness_result = self.execute_cypher_query(betweenness_query, {"gene_name": gene_name})
        betweenness_centrality = betweenness_result[0]["betweenness_centrality"] if betweenness_result else 0
        
        return {
            "degree_centrality": degree_centrality,
            "betweenness_centrality": betweenness_centrality
        }
    
    def find_shortest_path(self, start_gene: str, end_gene: str) -> List[Dict]:
        """
        Find shortest path between two genes.
        
        Args:
            start_gene: Start gene symbol
            end_gene: End gene symbol
            
        Returns:
            List of nodes in the shortest path
        """
        query = """
        MATCH (start:Gene {gene_name: $start_gene})
        MATCH (end:Gene {gene_name: $end_gene})
        MATCH path = shortestPath((start)-[*]-(end))
        RETURN path
        """
        
        results = self.execute_cypher_query(query, {"start_gene": start_gene, "end_gene": end_gene})
        return results
    
    def import_gene_data(self, gene_data: pd.DataFrame):
        """
        Import gene data from DataFrame.
        
        Args:
            gene_data: DataFrame with gene information
        """
        for _, row in gene_data.iterrows():
            self.create_gene_node(
                gene_id=row.get("gene_id", ""),
                gene_name=row.get("gene_name", ""),
                chromosome=row.get("chromosome", ""),
                start_pos=row.get("start_pos", 0),
                end_pos=row.get("end_pos", 0),
                strand=row.get("strand", "+"),
                properties=row.to_dict()
            )
        
        logger.info(f"Imported {len(gene_data)} genes")
    
    def import_variant_data(self, variant_data: pd.DataFrame):
        """
        Import variant data from DataFrame.
        
        Args:
            variant_data: DataFrame with variant information
        """
        for _, row in variant_data.iterrows():
            self.create_variant_node(
                variant_id=row.get("variant_id", ""),
                chromosome=row.get("chromosome", ""),
                position=row.get("position", 0),
                ref_allele=row.get("ref_allele", ""),
                alt_allele=row.get("alt_allele", ""),
                variant_type=row.get("variant_type", "SNV"),
                properties=row.to_dict()
            )
        
        logger.info(f"Imported {len(variant_data)} variants")
    
    def import_protein_interactions(self, interaction_data: pd.DataFrame):
        """
        Import protein-protein interaction data.
        
        Args:
            interaction_data: DataFrame with interaction information
        """
        for _, row in interaction_data.iterrows():
            # Create or get protein nodes
            protein1 = self.node_matcher.match("Protein", protein_name=row["protein1"]).first()
            if not protein1:
                protein1 = self.create_protein_node(
                    protein_id=row["protein1"],
                    protein_name=row["protein1"]
                )
            
            protein2 = self.node_matcher.match("Protein", protein_name=row["protein2"]).first()
            if not protein2:
                protein2 = self.create_protein_node(
                    protein_id=row["protein2"],
                    protein_name=row["protein2"]
                )
            
            # Create interaction relationship
            self.create_relationship(
                protein1,
                "INTERACTS_WITH",
                protein2,
                properties={
                    "interaction_type": row.get("interaction_type", "unknown"),
                    "confidence": row.get("confidence", 0.0),
                    "source": row.get("source", "unknown")
                }
            )
        
        logger.info(f"Imported {len(interaction_data)} protein interactions")
    
    def create_gene_variant_relationships(self):
        """
        Create relationships between genes and variants based on genomic coordinates.
        """
        query = """
        MATCH (g:Gene), (v:Variant)
        WHERE v.chromosome = g.chromosome 
        AND v.position >= g.start_pos 
        AND v.position <= g.end_pos
        CREATE (v)-[:AFFECTS]->(g)
        """
        
        result = self.execute_cypher_query(query)
        logger.info("Created gene-variant relationships")
    
    def create_gene_protein_relationships(self):
        """
        Create relationships between genes and proteins.
        """
        query = """
        MATCH (g:Gene), (p:Protein)
        WHERE g.gene_name = p.protein_name
        OR g.gene_id = p.protein_id
        CREATE (g)-[:ENCODES]->(p)
        """
        
        result = self.execute_cypher_query(query)
        logger.info("Created gene-protein relationships")
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """
        Get graph database statistics.
        
        Returns:
            Dictionary with graph statistics
        """
        stats = {}
        
        # Count nodes by label
        node_counts_query = """
        CALL db.labels() YIELD label
        CALL apoc.cypher.run('MATCH (n:' + label + ') RETURN count(n) as count', {}) YIELD value
        RETURN label, value.count as count
        """
        
        try:
            node_counts = self.execute_cypher_query(node_counts_query)
            stats["node_counts"] = {item["label"]: item["count"] for item in node_counts}
        except Exception as e:
            logger.warning(f"Could not get node counts: {e}")
            stats["node_counts"] = {}
        
        # Count relationships by type
        rel_counts_query = """
        CALL db.relationshipTypes() YIELD relationshipType
        CALL apoc.cypher.run('MATCH ()-[r:' + relationshipType + ']->() RETURN count(r) as count', {}) YIELD value
        RETURN relationshipType, value.count as count
        """
        
        try:
            rel_counts = self.execute_cypher_query(rel_counts_query)
            stats["relationship_counts"] = {item["relationshipType"]: item["count"] for item in rel_counts}
        except Exception as e:
            logger.warning(f"Could not get relationship counts: {e}")
            stats["relationship_counts"] = {}
        
        # Total counts
        total_nodes_query = "MATCH (n) RETURN count(n) as total_nodes"
        total_rels_query = "MATCH ()-[r]->() RETURN count(r) as total_relationships"
        
        try:
            total_nodes = self.execute_cypher_query(total_nodes_query)[0]["total_nodes"]
            total_rels = self.execute_cypher_query(total_rels_query)[0]["total_relationships"]
            
            stats["total_nodes"] = total_nodes
            stats["total_relationships"] = total_rels
        except Exception as e:
            logger.warning(f"Could not get total counts: {e}")
            stats["total_nodes"] = 0
            stats["total_relationships"] = 0
        
        return stats
    
    def clear_database(self):
        """Clear all data from the database."""
        query = "MATCH (n) DETACH DELETE n"
        self.execute_cypher_query(query)
        logger.info("Database cleared")
    
    def export_graph_data(self, output_file: str):
        """
        Export graph data to JSON file.
        
        Args:
            output_file: Output file path
        """
        # Export nodes
        nodes_query = "MATCH (n) RETURN n"
        nodes = self.execute_cypher_query(nodes_query)
        
        # Export relationships
        rels_query = "MATCH ()-[r]->() RETURN r"
        relationships = self.execute_cypher_query(rels_query)
        
        export_data = {
            "nodes": nodes,
            "relationships": relationships,
            "exported_at": datetime.now().isoformat()
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Graph data exported to {output_file}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
