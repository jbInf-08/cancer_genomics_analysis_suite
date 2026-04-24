"""
Neo4j Mutation Analyzer for Real-time Cancer Genomics Graph Analysis

This module provides advanced graph analytics for mutation data using Neo4j,
including pathway analysis, gene interaction networks, and mutation clustering.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import numpy as np
import pandas as pd
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, TransientError
import networkx as nx
from prometheus_client import Counter, Histogram, Gauge
import aiohttp
import asyncpg

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
NEO4J_QUERIES = Counter('neo4j_queries_total', 'Total Neo4j queries executed', ['query_type', 'status'])
NEO4J_QUERY_DURATION = Histogram('neo4j_query_duration_seconds', 'Neo4j query execution time', ['query_type'])
GRAPH_ANALYTICS_OPERATIONS = Counter('graph_analytics_operations_total', 'Total graph analytics operations', ['operation_type', 'status'])
PATHWAY_ANALYSES = Counter('pathway_analyses_total', 'Total pathway analyses performed', ['pathway_type'])
GENE_NETWORK_ANALYSES = Counter('gene_network_analyses_total', 'Total gene network analyses performed', ['analysis_type'])
MUTATION_CLUSTERS = Gauge('mutation_clusters_total', 'Total mutation clusters identified', ['cluster_type'])

@dataclass
class GeneNode:
    """Data class for gene nodes in the graph"""
    id: str
    name: str
    symbol: str
    chromosome: str
    start_position: int
    end_position: int
    gene_type: str
    description: str
    aliases: List[str] = None
    pathways: List[str] = None
    functions: List[str] = None
    
    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []
        if self.pathways is None:
            self.pathways = []
        if self.functions is None:
            self.functions = []

@dataclass
class PathwayNode:
    """Data class for pathway nodes in the graph"""
    id: str
    name: str
    description: str
    source: str  # KEGG, Reactome, etc.
    pathway_type: str
    genes: List[str] = None
    interactions: List[Dict] = None
    
    def __post_init__(self):
        if self.genes is None:
            self.genes = []
        if self.interactions is None:
            self.interactions = []

@dataclass
class MutationCluster:
    """Data class for mutation clusters"""
    id: str
    cluster_type: str
    mutations: List[str]
    genes: List[str]
    pathways: List[str]
    severity: str
    patient_count: int
    cluster_score: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class Neo4jMutationAnalyzer:
    """Advanced Neo4j-based mutation analyzer with graph analytics"""
    
    def __init__(self, uri: str, username: str, password: str, database: str = "neo4j"):
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.driver: Optional[Driver] = None
        self.session: Optional[Session] = None
    
    async def connect(self):
        """Establish connection to Neo4j"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.username, self.password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_acquisition_timeout=60
            )
            
            # Test connection
            with self.driver.session(database=self.database) as session:
                session.run("RETURN 1")
            
            logger.info("Connected to Neo4j successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False
    
    async def disconnect(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            logger.info("Disconnected from Neo4j")
    
    def __enter__(self):
        if not self.driver:
            raise RuntimeError("Neo4j driver not initialized. Call connect() first.")
        self.session = self.driver.session(database=self.database)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            self.session.close()
    
    async def create_gene_node(self, gene: GeneNode) -> bool:
        """Create or update a gene node in Neo4j"""
        start_time = datetime.now()
        
        try:
            query = """
            MERGE (g:Gene {id: $id})
            SET g.name = $name,
                g.symbol = $symbol,
                g.chromosome = $chromosome,
                g.start_position = $start_position,
                g.end_position = $end_position,
                g.gene_type = $gene_type,
                g.description = $description,
                g.aliases = $aliases,
                g.pathways = $pathways,
                g.functions = $functions,
                g.updated_at = datetime()
            RETURN g
            """
            
            with self.session as session:
                result = session.run(query, **asdict(gene))
                result.single()
            
            NEO4J_QUERIES.labels(query_type='create_gene', status='success').inc()
            NEO4J_QUERY_DURATION.labels(query_type='create_gene').observe(
                (datetime.now() - start_time).total_seconds()
            )
            return True
            
        except Exception as e:
            logger.error(f"Error creating gene node: {e}")
            NEO4J_QUERIES.labels(query_type='create_gene', status='error').inc()
            return False
    
    async def create_pathway_node(self, pathway: PathwayNode) -> bool:
        """Create or update a pathway node in Neo4j"""
        start_time = datetime.now()
        
        try:
            query = """
            MERGE (p:Pathway {id: $id})
            SET p.name = $name,
                p.description = $description,
                p.source = $source,
                p.pathway_type = $pathway_type,
                p.genes = $genes,
                p.interactions = $interactions,
                p.updated_at = datetime()
            RETURN p
            """
            
            with self.session as session:
                result = session.run(query, **asdict(pathway))
                result.single()
            
            NEO4J_QUERIES.labels(query_type='create_pathway', status='success').inc()
            NEO4J_QUERY_DURATION.labels(query_type='create_pathway').observe(
                (datetime.now() - start_time).total_seconds()
            )
            return True
            
        except Exception as e:
            logger.error(f"Error creating pathway node: {e}")
            NEO4J_QUERIES.labels(query_type='create_pathway', status='error').inc()
            return False
    
    async def create_gene_interaction(self, gene1_id: str, gene2_id: str, interaction_type: str, 
                                    confidence: float = 1.0, source: str = "unknown") -> bool:
        """Create gene-gene interaction relationship"""
        start_time = datetime.now()
        
        try:
            query = """
            MATCH (g1:Gene {id: $gene1_id})
            MATCH (g2:Gene {id: $gene2_id})
            MERGE (g1)-[r:INTERACTS_WITH]->(g2)
            SET r.interaction_type = $interaction_type,
                r.confidence = $confidence,
                r.source = $source,
                r.updated_at = datetime()
            RETURN r
            """
            
            with self.session as session:
                result = session.run(query, 
                                   gene1_id=gene1_id, 
                                   gene2_id=gene2_id,
                                   interaction_type=interaction_type,
                                   confidence=confidence,
                                   source=source)
                result.single()
            
            NEO4J_QUERIES.labels(query_type='create_interaction', status='success').inc()
            NEO4J_QUERY_DURATION.labels(query_type='create_interaction').observe(
                (datetime.now() - start_time).total_seconds()
            )
            return True
            
        except Exception as e:
            logger.error(f"Error creating gene interaction: {e}")
            NEO4J_QUERIES.labels(query_type='create_interaction', status='error').inc()
            return False
    
    async def create_pathway_gene_relationship(self, pathway_id: str, gene_id: str) -> bool:
        """Create pathway-gene relationship"""
        start_time = datetime.now()
        
        try:
            query = """
            MATCH (p:Pathway {id: $pathway_id})
            MATCH (g:Gene {id: $gene_id})
            MERGE (p)-[r:CONTAINS_GENE]->(g)
            SET r.updated_at = datetime()
            RETURN r
            """
            
            with self.session as session:
                result = session.run(query, pathway_id=pathway_id, gene_id=gene_id)
                result.single()
            
            NEO4J_QUERIES.labels(query_type='create_pathway_gene', status='success').inc()
            NEO4J_QUERY_DURATION.labels(query_type='create_pathway_gene').observe(
                (datetime.now() - start_time).total_seconds()
            )
            return True
            
        except Exception as e:
            logger.error(f"Error creating pathway-gene relationship: {e}")
            NEO4J_QUERIES.labels(query_type='create_pathway_gene', status='error').inc()
            return False
    
    async def analyze_mutation_impact(self, mutation_id: str) -> Dict[str, Any]:
        """Analyze the impact of a mutation on gene networks and pathways"""
        start_time = datetime.now()
        
        try:
            query = """
            MATCH (m:Mutation {id: $mutation_id})-[:AFFECTS]->(g:Gene)
            OPTIONAL MATCH (g)-[r:INTERACTS_WITH]-(related:Gene)
            OPTIONAL MATCH (g)-[:PART_OF_PATHWAY]-(p:Pathway)
            OPTIONAL MATCH (related)-[:PART_OF_PATHWAY]-(related_pathway:Pathway)
            
            RETURN g,
                   collect(DISTINCT related) as interacting_genes,
                   collect(DISTINCT p) as affected_pathways,
                   collect(DISTINCT related_pathway) as related_pathways,
                   collect(DISTINCT r) as interactions
            """
            
            with self.session as session:
                result = session.run(query, mutation_id=mutation_id)
                record = result.single()
            
            if not record:
                return {'error': 'Mutation not found'}
            
            gene = record['g']
            interacting_genes = [dict(gene) for gene in record['interacting_genes']]
            affected_pathways = [dict(pathway) for pathway in record['affected_pathways']]
            related_pathways = [dict(pathway) for pathway in record['related_pathways']]
            interactions = [dict(interaction) for interaction in record['interactions']]
            
            # Calculate impact score
            impact_score = self._calculate_impact_score(
                gene, interacting_genes, affected_pathways, interactions
            )
            
            analysis_result = {
                'mutation_id': mutation_id,
                'affected_gene': dict(gene),
                'interacting_genes': interacting_genes,
                'affected_pathways': affected_pathways,
                'related_pathways': related_pathways,
                'interactions': interactions,
                'impact_score': impact_score,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            NEO4J_QUERIES.labels(query_type='analyze_impact', status='success').inc()
            NEO4J_QUERY_DURATION.labels(query_type='analyze_impact').observe(
                (datetime.now() - start_time).total_seconds()
            )
            
            GRAPH_ANALYTICS_OPERATIONS.labels(operation_type='mutation_impact', status='success').inc()
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing mutation impact: {e}")
            NEO4J_QUERIES.labels(query_type='analyze_impact', status='error').inc()
            GRAPH_ANALYTICS_OPERATIONS.labels(operation_type='mutation_impact', status='error').inc()
            return {'error': str(e)}
    
    async def find_mutation_clusters(self, patient_id: str = None, 
                                   min_cluster_size: int = 3) -> List[MutationCluster]:
        """Find clusters of related mutations"""
        start_time = datetime.now()
        
        try:
            if patient_id:
                query = """
                MATCH (p:Patient {id: $patient_id})-[:HAS_MUTATION]->(m:Mutation)
                MATCH (m)-[:AFFECTS]->(g:Gene)
                MATCH (g)-[:INTERACTS_WITH]-(related:Gene)<-[:AFFECTS]-(related_mutation:Mutation)
                WHERE related_mutation <> m
                
                WITH m, g, collect(DISTINCT related_mutation) as related_mutations
                WHERE size(related_mutations) >= $min_cluster_size
                
                RETURN m, g, related_mutations,
                       collect(DISTINCT g.symbol) as gene_symbols
                """
            else:
                query = """
                MATCH (m:Mutation)-[:AFFECTS]->(g:Gene)
                MATCH (g)-[:INTERACTS_WITH]-(related:Gene)<-[:AFFECTS]-(related_mutation:Mutation)
                WHERE related_mutation <> m
                
                WITH m, g, collect(DISTINCT related_mutation) as related_mutations
                WHERE size(related_mutations) >= $min_cluster_size
                
                RETURN m, g, related_mutations,
                       collect(DISTINCT g.symbol) as gene_symbols
                """
            
            with self.session as session:
                result = session.run(query, 
                                   patient_id=patient_id, 
                                   min_cluster_size=min_cluster_size)
                records = list(result)
            
            clusters = []
            for record in records:
                mutation = record['m']
                gene = record['g']
                related_mutations = record['related_mutations']
                gene_symbols = record['gene_symbols']
                
                cluster = MutationCluster(
                    id=f"cluster_{mutation['id']}_{int(datetime.now().timestamp())}",
                    cluster_type="gene_interaction",
                    mutations=[mutation['id']] + [m['id'] for m in related_mutations],
                    genes=gene_symbols,
                    pathways=[],  # Will be populated separately
                    severity=self._determine_cluster_severity(related_mutations),
                    patient_count=len(set(m.get('patient_id', '') for m in related_mutations)),
                    cluster_score=self._calculate_cluster_score(related_mutations),
                    metadata={
                        'central_gene': gene['symbol'],
                        'cluster_size': len(related_mutations) + 1,
                        'interaction_types': [m.get('mutation_type', 'unknown') for m in related_mutations]
                    }
                )
                clusters.append(cluster)
            
            NEO4J_QUERIES.labels(query_type='find_clusters', status='success').inc()
            NEO4J_QUERY_DURATION.labels(query_type='find_clusters').observe(
                (datetime.now() - start_time).total_seconds()
            )
            
            MUTATION_CLUSTERS.labels(cluster_type='gene_interaction').set(len(clusters))
            GRAPH_ANALYTICS_OPERATIONS.labels(operation_type='clustering', status='success').inc()
            
            return clusters
            
        except Exception as e:
            logger.error(f"Error finding mutation clusters: {e}")
            NEO4J_QUERIES.labels(query_type='find_clusters', status='error').inc()
            GRAPH_ANALYTICS_OPERATIONS.labels(operation_type='clustering', status='error').inc()
            return []
    
    async def analyze_pathway_enrichment(self, gene_list: List[str]) -> Dict[str, Any]:
        """Analyze pathway enrichment for a list of genes"""
        start_time = datetime.now()
        
        try:
            query = """
            UNWIND $gene_list as gene_symbol
            MATCH (g:Gene {symbol: gene_symbol})-[:PART_OF_PATHWAY]->(p:Pathway)
            
            WITH p, count(g) as gene_count, collect(g.symbol) as genes_in_pathway
            WHERE gene_count >= 2
            
            MATCH (p)<-[:PART_OF_PATHWAY]-(all_genes:Gene)
            WITH p, gene_count, genes_in_pathway, count(all_genes) as total_genes_in_pathway
            
            RETURN p.name as pathway_name,
                   p.description as pathway_description,
                   p.source as pathway_source,
                   gene_count,
                   total_genes_in_pathway,
                   genes_in_pathway,
                   (gene_count * 1.0 / total_genes_in_pathway) as enrichment_ratio
            ORDER BY enrichment_ratio DESC
            """
            
            with self.session as session:
                result = session.run(query, gene_list=gene_list)
                records = list(result)
            
            pathway_enrichment = {
                'input_genes': gene_list,
                'enriched_pathways': [
                    {
                        'name': record['pathway_name'],
                        'description': record['pathway_description'],
                        'source': record['pathway_source'],
                        'gene_count': record['gene_count'],
                        'total_genes': record['total_genes_in_pathway'],
                        'enrichment_ratio': record['enrichment_ratio'],
                        'genes_in_pathway': record['genes_in_pathway']
                    }
                    for record in records
                ],
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            NEO4J_QUERIES.labels(query_type='pathway_enrichment', status='success').inc()
            NEO4J_QUERY_DURATION.labels(query_type='pathway_enrichment').observe(
                (datetime.now() - start_time).total_seconds()
            )
            
            PATHWAY_ANALYSES.labels(pathway_type='enrichment').inc()
            GRAPH_ANALYTICS_OPERATIONS.labels(operation_type='pathway_enrichment', status='success').inc()
            
            return pathway_enrichment
            
        except Exception as e:
            logger.error(f"Error analyzing pathway enrichment: {e}")
            NEO4J_QUERIES.labels(query_type='pathway_enrichment', status='error').inc()
            GRAPH_ANALYTICS_OPERATIONS.labels(operation_type='pathway_enrichment', status='error').inc()
            return {'error': str(e)}
    
    async def get_gene_network_analysis(self, gene_id: str, max_depth: int = 2) -> Dict[str, Any]:
        """Get comprehensive gene network analysis"""
        start_time = datetime.now()
        
        try:
            query = """
            MATCH (g:Gene {id: $gene_id})
            OPTIONAL MATCH path = (g)-[:INTERACTS_WITH*1..$max_depth]-(related:Gene)
            OPTIONAL MATCH (g)-[:PART_OF_PATHWAY]->(p:Pathway)
            OPTIONAL MATCH (g)<-[:AFFECTS]-(m:Mutation)
            
            WITH g, 
                 collect(DISTINCT related) as network_genes,
                 collect(DISTINCT p) as pathways,
                 collect(DISTINCT m) as mutations,
                 collect(DISTINCT path) as interaction_paths
            
            RETURN g,
                   network_genes,
                   pathways,
                   mutations,
                   size(network_genes) as network_size,
                   size(pathways) as pathway_count,
                   size(mutations) as mutation_count
            """
            
            with self.session as session:
                result = session.run(query, gene_id=gene_id, max_depth=max_depth)
                record = result.single()
            
            if not record:
                return {'error': 'Gene not found'}
            
            gene = record['g']
            network_genes = [dict(g) for g in record['network_genes']]
            pathways = [dict(p) for p in record['pathways']]
            mutations = [dict(m) for m in record['mutations']]
            
            # Calculate network metrics
            network_metrics = self._calculate_network_metrics(network_genes, pathways, mutations)
            
            analysis_result = {
                'gene': dict(gene),
                'network_genes': network_genes,
                'pathways': pathways,
                'mutations': mutations,
                'network_metrics': network_metrics,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            NEO4J_QUERIES.labels(query_type='network_analysis', status='success').inc()
            NEO4J_QUERY_DURATION.labels(query_type='network_analysis').observe(
                (datetime.now() - start_time).total_seconds()
            )
            
            GENE_NETWORK_ANALYSES.labels(analysis_type='comprehensive').inc()
            GRAPH_ANALYTICS_OPERATIONS.labels(operation_type='network_analysis', status='success').inc()
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in gene network analysis: {e}")
            NEO4J_QUERIES.labels(query_type='network_analysis', status='error').inc()
            GRAPH_ANALYTICS_OPERATIONS.labels(operation_type='network_analysis', status='error').inc()
            return {'error': str(e)}
    
    def _calculate_impact_score(self, gene: Dict, interacting_genes: List[Dict], 
                              affected_pathways: List[Dict], interactions: List[Dict]) -> float:
        """Calculate mutation impact score based on network analysis"""
        base_score = 0.5
        
        # Gene centrality score
        centrality_score = min(len(interacting_genes) / 10.0, 1.0)
        
        # Pathway importance score
        pathway_score = min(len(affected_pathways) / 5.0, 1.0)
        
        # Interaction strength score
        interaction_score = 0.0
        if interactions:
            avg_confidence = np.mean([i.get('confidence', 0.5) for i in interactions])
            interaction_score = avg_confidence
        
        # Combined impact score
        impact_score = (base_score + centrality_score + pathway_score + interaction_score) / 4.0
        
        return min(impact_score, 1.0)
    
    def _determine_cluster_severity(self, mutations: List[Dict]) -> str:
        """Determine cluster severity based on mutation severities"""
        severities = [m.get('severity', 'unknown') for m in mutations]
        
        if 'critical' in severities:
            return 'critical'
        elif 'high' in severities:
            return 'high'
        elif 'medium' in severities:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_cluster_score(self, mutations: List[Dict]) -> float:
        """Calculate cluster significance score"""
        if not mutations:
            return 0.0
        
        # Base score from cluster size
        size_score = min(len(mutations) / 10.0, 1.0)
        
        # Severity score
        severity_weights = {'critical': 1.0, 'high': 0.8, 'medium': 0.6, 'low': 0.4, 'unknown': 0.2}
        severity_scores = [severity_weights.get(m.get('severity', 'unknown'), 0.2) for m in mutations]
        avg_severity_score = np.mean(severity_scores)
        
        # Pathogenicity score
        pathogenicity_scores = [m.get('pathogenicity_score', 0.0) for m in mutations if m.get('pathogenicity_score')]
        avg_pathogenicity_score = np.mean(pathogenicity_scores) if pathogenicity_scores else 0.0
        
        # Combined cluster score
        cluster_score = (size_score + avg_severity_score + avg_pathogenicity_score) / 3.0
        
        return min(cluster_score, 1.0)
    
    def _calculate_network_metrics(self, network_genes: List[Dict], 
                                 pathways: List[Dict], mutations: List[Dict]) -> Dict[str, Any]:
        """Calculate network analysis metrics"""
        return {
            'network_size': len(network_genes),
            'pathway_count': len(pathways),
            'mutation_count': len(mutations),
            'network_density': self._calculate_network_density(network_genes),
            'pathway_diversity': len(set(p.get('source', 'unknown') for p in pathways)),
            'mutation_severity_distribution': self._calculate_severity_distribution(mutations)
        }
    
    def _calculate_network_density(self, network_genes: List[Dict]) -> float:
        """Calculate network density"""
        if len(network_genes) <= 1:
            return 0.0
        
        # Simplified density calculation
        max_possible_edges = len(network_genes) * (len(network_genes) - 1) / 2
        # This is a simplified calculation - in practice, you'd count actual edges
        estimated_edges = len(network_genes) * 0.3  # Assume 30% connectivity
        
        return min(estimated_edges / max_possible_edges, 1.0)
    
    def _calculate_severity_distribution(self, mutations: List[Dict]) -> Dict[str, int]:
        """Calculate mutation severity distribution"""
        distribution = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'unknown': 0}
        
        for mutation in mutations:
            severity = mutation.get('severity', 'unknown')
            distribution[severity] = distribution.get(severity, 0) + 1
        
        return distribution

class RealTimeMutationAnalyzer:
    """Real-time mutation analyzer integrating with Kafka streams"""
    
    def __init__(self, neo4j_analyzer: Neo4jMutationAnalyzer):
        self.neo4j_analyzer = neo4j_analyzer
        self.running = False
    
    async def process_mutation_stream(self, mutation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process mutation data from stream and perform graph analysis"""
        try:
            mutation_id = mutation_data['id']
            
            # Perform mutation impact analysis
            impact_analysis = await self.neo4j_analyzer.analyze_mutation_impact(mutation_id)
            
            # Find related mutation clusters
            clusters = await self.neo4j_analyzer.find_mutation_clusters()
            
            # Analyze pathway enrichment if multiple genes are affected
            gene_list = mutation_data.get('affected_genes', [])
            if len(gene_list) > 1:
                pathway_enrichment = await self.neo4j_analyzer.analyze_pathway_enrichment(gene_list)
            else:
                pathway_enrichment = None
            
            # Get gene network analysis for primary affected gene
            primary_gene = mutation_data.get('primary_gene')
            if primary_gene:
                network_analysis = await self.neo4j_analyzer.get_gene_network_analysis(primary_gene)
            else:
                network_analysis = None
            
            analysis_result = {
                'mutation_id': mutation_id,
                'impact_analysis': impact_analysis,
                'related_clusters': [asdict(cluster) for cluster in clusters[:5]],  # Top 5 clusters
                'pathway_enrichment': pathway_enrichment,
                'network_analysis': network_analysis,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error processing mutation stream: {e}")
            return {'error': str(e)}

# Example usage and testing
async def main():
    """Example usage of the Neo4j mutation analyzer"""
    
    # Configuration
    config = {
        'uri': 'bolt://neo4j:7687',
        'username': 'neo4j',
        'password': 'neo4j-password',
        'database': 'neo4j'
    }
    
    # Initialize analyzer
    analyzer = Neo4jMutationAnalyzer(**config)
    
    if await analyzer.connect():
        try:
            # Example: Create a gene node
            gene = GeneNode(
                id="GENE_TP53",
                name="tumor protein p53",
                symbol="TP53",
                chromosome="17",
                start_position=7668402,
                end_position=7687550,
                gene_type="protein_coding",
                description="Tumor suppressor protein",
                aliases=["p53", "TRP53"],
                pathways=["p53_signaling_pathway"],
                functions=["tumor_suppression", "cell_cycle_regulation"]
            )
            
            await analyzer.create_gene_node(gene)
            
            # Example: Analyze mutation impact
            impact_result = await analyzer.analyze_mutation_impact("MUTATION_123")
            print(f"Impact analysis result: {impact_result}")
            
            # Example: Find mutation clusters
            clusters = await analyzer.find_mutation_clusters()
            print(f"Found {len(clusters)} mutation clusters")
            
        finally:
            await analyzer.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
