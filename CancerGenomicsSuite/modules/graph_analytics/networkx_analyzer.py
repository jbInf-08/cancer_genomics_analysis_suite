#!/usr/bin/env python3
"""
NetworkX Analyzer

This module provides NetworkX-based graph analysis capabilities
for cancer genomics data.
"""

import logging
from typing import Dict, List, Optional, Any, Union, Tuple
import pandas as pd
import numpy as np

try:
    import networkx as nx
    from networkx.algorithms import centrality, community, shortest_paths
    from networkx.algorithms.centrality import betweenness_centrality, closeness_centrality, degree_centrality
    from networkx.algorithms.community import greedy_modularity_communities, label_propagation_communities
    from networkx.algorithms.shortest_paths import shortest_path_length
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logging.warning("NetworkX not available. Install networkx package.")

logger = logging.getLogger(__name__)


class NetworkXAnalyzer:
    """
    NetworkX-based graph analyzer for cancer genomics data.
    
    Provides functionality to:
    - Build and analyze gene networks
    - Calculate centrality measures
    - Detect communities and modules
    - Perform pathway analysis
    - Visualize network structures
    """
    
    def __init__(self):
        """Initialize NetworkX analyzer."""
        if not NETWORKX_AVAILABLE:
            raise ImportError("NetworkX not available. Install networkx package.")
        
        self.graph = nx.Graph()
        self.directed_graph = nx.DiGraph()
        self.analysis_results = {}
    
    def build_gene_network(
        self,
        gene_data: pd.DataFrame,
        interaction_data: pd.DataFrame,
        expression_data: Optional[pd.DataFrame] = None,
        directed: bool = False
    ) -> nx.Graph:
        """
        Build a gene network from interaction and expression data.
        
        Args:
            gene_data: DataFrame with gene information
            interaction_data: DataFrame with gene interactions
            expression_data: Optional DataFrame with expression data
            directed: Whether to create a directed graph
            
        Returns:
            NetworkX graph object
        """
        if directed:
            graph = nx.DiGraph()
        else:
            graph = nx.Graph()
        
        # Add gene nodes
        for _, gene in gene_data.iterrows():
            node_attrs = {
                "gene_id": gene.get("gene_id", ""),
                "gene_name": gene.get("gene_name", ""),
                "chromosome": gene.get("chromosome", ""),
                "start_pos": gene.get("start_pos", 0),
                "end_pos": gene.get("end_pos", 0),
                "strand": gene.get("strand", "+")
            }
            
            # Add expression data if available
            if expression_data is not None and gene["gene_name"] in expression_data.columns:
                node_attrs["expression"] = expression_data[gene["gene_name"]].mean()
            
            graph.add_node(gene["gene_name"], **node_attrs)
        
        # Add interaction edges
        for _, interaction in interaction_data.iterrows():
            gene1 = interaction["gene1"]
            gene2 = interaction["gene2"]
            
            if gene1 in graph.nodes and gene2 in graph.nodes:
                edge_attrs = {
                    "interaction_type": interaction.get("interaction_type", "unknown"),
                    "confidence": interaction.get("confidence", 0.0),
                    "source": interaction.get("source", "unknown")
                }
                
                graph.add_edge(gene1, gene2, **edge_attrs)
        
        if directed:
            self.directed_graph = graph
        else:
            self.graph = graph
        
        logger.info(f"Built gene network with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
        return graph
    
    def build_protein_interaction_network(
        self,
        protein_data: pd.DataFrame,
        interaction_data: pd.DataFrame,
        directed: bool = False
    ) -> nx.Graph:
        """
        Build a protein-protein interaction network.
        
        Args:
            protein_data: DataFrame with protein information
            interaction_data: DataFrame with protein interactions
            directed: Whether to create a directed graph
            
        Returns:
            NetworkX graph object
        """
        if directed:
            graph = nx.DiGraph()
        else:
            graph = nx.Graph()
        
        # Add protein nodes
        for _, protein in protein_data.iterrows():
            node_attrs = {
                "protein_id": protein.get("protein_id", ""),
                "protein_name": protein.get("protein_name", ""),
                "uniprot_id": protein.get("uniprot_id", ""),
                "molecular_weight": protein.get("molecular_weight", 0),
                "function": protein.get("function", "")
            }
            
            graph.add_node(protein["protein_name"], **node_attrs)
        
        # Add interaction edges
        for _, interaction in interaction_data.iterrows():
            protein1 = interaction["protein1"]
            protein2 = interaction["protein2"]
            
            if protein1 in graph.nodes and protein2 in graph.nodes:
                edge_attrs = {
                    "interaction_type": interaction.get("interaction_type", "unknown"),
                    "confidence": interaction.get("confidence", 0.0),
                    "experimental_method": interaction.get("experimental_method", "unknown"),
                    "source": interaction.get("source", "unknown")
                }
                
                graph.add_edge(protein1, protein2, **edge_attrs)
        
        if directed:
            self.directed_graph = graph
        else:
            self.graph = graph
        
        logger.info(f"Built protein network with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
        return graph
    
    def build_pathway_network(
        self,
        pathway_data: pd.DataFrame,
        gene_pathway_data: pd.DataFrame,
        gene_interaction_data: Optional[pd.DataFrame] = None
    ) -> nx.Graph:
        """
        Build a pathway-gene network.
        
        Args:
            pathway_data: DataFrame with pathway information
            gene_pathway_data: DataFrame linking genes to pathways
            gene_interaction_data: Optional DataFrame with gene interactions
            
        Returns:
            NetworkX bipartite graph
        """
        graph = nx.Graph()
        
        # Add pathway nodes
        for _, pathway in pathway_data.iterrows():
            node_attrs = {
                "pathway_id": pathway.get("pathway_id", ""),
                "pathway_name": pathway.get("pathway_name", ""),
                "pathway_type": pathway.get("pathway_type", ""),
                "description": pathway.get("description", "")
            }
            
            graph.add_node(pathway["pathway_name"], node_type="pathway", **node_attrs)
        
        # Add gene nodes
        genes_in_pathways = set(gene_pathway_data["gene_name"].unique())
        for gene in genes_in_pathways:
            graph.add_node(gene, node_type="gene")
        
        # Add gene-pathway edges
        for _, row in gene_pathway_data.iterrows():
            gene = row["gene_name"]
            pathway = row["pathway_name"]
            
            if gene in graph.nodes and pathway in graph.nodes:
                edge_attrs = {
                    "role": row.get("role", "member"),
                    "confidence": row.get("confidence", 1.0)
                }
                
                graph.add_edge(gene, pathway, **edge_attrs)
        
        # Add gene-gene edges if interaction data is provided
        if gene_interaction_data is not None:
            for _, interaction in gene_interaction_data.iterrows():
                gene1 = interaction["gene1"]
                gene2 = interaction["gene2"]
                
                if gene1 in graph.nodes and gene2 in graph.nodes:
                    edge_attrs = {
                        "interaction_type": interaction.get("interaction_type", "unknown"),
                        "confidence": interaction.get("confidence", 0.0)
                    }
                    
                    graph.add_edge(gene1, gene2, **edge_attrs)
        
        self.graph = graph
        logger.info(f"Built pathway network with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
        return graph
    
    def calculate_centrality_measures(self, graph: Optional[nx.Graph] = None) -> Dict[str, Dict[str, float]]:
        """
        Calculate centrality measures for all nodes in the graph.
        
        Args:
            graph: NetworkX graph (uses self.graph if None)
            
        Returns:
            Dictionary with centrality measures for each node
        """
        if graph is None:
            graph = self.graph
        
        if graph.number_of_nodes() == 0:
            return {}
        
        # Calculate centrality measures
        degree_cent = degree_centrality(graph)
        betweenness_cent = betweenness_centrality(graph)
        closeness_cent = closeness_centrality(graph)
        
        # Calculate eigenvector centrality
        try:
            eigenvector_cent = nx.eigenvector_centrality(graph, max_iter=1000)
        except nx.PowerIterationFailedConvergence:
            eigenvector_cent = {node: 0.0 for node in graph.nodes()}
        
        # Combine results
        centrality_results = {}
        for node in graph.nodes():
            centrality_results[node] = {
                "degree_centrality": degree_cent[node],
                "betweenness_centrality": betweenness_cent[node],
                "closeness_centrality": closeness_cent[node],
                "eigenvector_centrality": eigenvector_cent[node]
            }
        
        self.analysis_results["centrality"] = centrality_results
        logger.info("Calculated centrality measures")
        return centrality_results
    
    def detect_communities(self, graph: Optional[nx.Graph] = None, method: str = "greedy") -> Dict[str, int]:
        """
        Detect communities in the graph.
        
        Args:
            graph: NetworkX graph (uses self.graph if None)
            method: Community detection method ("greedy" or "label_propagation")
            
        Returns:
            Dictionary mapping nodes to community IDs
        """
        if graph is None:
            graph = self.graph
        
        if graph.number_of_nodes() == 0:
            return {}
        
        # Detect communities
        if method == "greedy":
            communities = list(greedy_modularity_communities(graph))
        elif method == "label_propagation":
            communities = list(label_propagation_communities(graph))
        else:
            raise ValueError(f"Unknown community detection method: {method}")
        
        # Create node-to-community mapping
        community_mapping = {}
        for i, community in enumerate(communities):
            for node in community:
                community_mapping[node] = i
        
        self.analysis_results["communities"] = community_mapping
        logger.info(f"Detected {len(communities)} communities using {method} method")
        return community_mapping
    
    def find_shortest_paths(
        self,
        source: str,
        target: str,
        graph: Optional[nx.Graph] = None
    ) -> List[List[str]]:
        """
        Find shortest paths between two nodes.
        
        Args:
            source: Source node
            target: Target node
            graph: NetworkX graph (uses self.graph if None)
            
        Returns:
            List of shortest paths
        """
        if graph is None:
            graph = self.graph
        
        if source not in graph.nodes() or target not in graph.nodes():
            return []
        
        try:
            paths = list(nx.all_shortest_paths(graph, source, target))
            return paths
        except nx.NetworkXNoPath:
            return []
    
    def calculate_pathway_enrichment(
        self,
        gene_list: List[str],
        pathway_data: pd.DataFrame,
        gene_pathway_data: pd.DataFrame,
        background_genes: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Calculate pathway enrichment for a list of genes.
        
        Args:
            gene_list: List of genes to test
            pathway_data: DataFrame with pathway information
            gene_pathway_data: DataFrame linking genes to pathways
            background_genes: Background gene set (all genes if None)
            
        Returns:
            DataFrame with enrichment results
        """
        from scipy.stats import hypergeom
        
        if background_genes is None:
            background_genes = list(set(gene_pathway_data["gene_name"].unique()))
        
        enrichment_results = []
        
        for _, pathway in pathway_data.iterrows():
            pathway_name = pathway["pathway_name"]
            
            # Get genes in pathway
            pathway_genes = set(gene_pathway_data[gene_pathway_data["pathway_name"] == pathway_name]["gene_name"])
            
            # Calculate overlap
            overlap_genes = set(gene_list) & pathway_genes
            overlap_count = len(overlap_genes)
            
            if overlap_count == 0:
                continue
            
            # Hypergeometric test
            N = len(background_genes)  # Total genes
            K = len(pathway_genes)  # Genes in pathway
            n = len(gene_list)  # Genes in test set
            k = overlap_count  # Overlap
            
            p_value = hypergeom.sf(k-1, N, K, n)
            
            # Calculate fold enrichment
            expected = (K * n) / N
            fold_enrichment = k / expected if expected > 0 else 0
            
            enrichment_results.append({
                "pathway_name": pathway_name,
                "pathway_id": pathway.get("pathway_id", ""),
                "pathway_type": pathway.get("pathway_type", ""),
                "genes_in_pathway": K,
                "genes_in_test_set": n,
                "overlap_count": overlap_count,
                "expected_overlap": expected,
                "fold_enrichment": fold_enrichment,
                "p_value": p_value,
                "overlap_genes": list(overlap_genes)
            })
        
        # Create DataFrame and sort by p-value
        results_df = pd.DataFrame(enrichment_results)
        if not results_df.empty:
            results_df = results_df.sort_values("p_value")
        
        return results_df
    
    def analyze_network_topology(self, graph: Optional[nx.Graph] = None) -> Dict[str, Any]:
        """
        Analyze network topology properties.
        
        Args:
            graph: NetworkX graph (uses self.graph if None)
            
        Returns:
            Dictionary with topology metrics
        """
        if graph is None:
            graph = self.graph
        
        if graph.number_of_nodes() == 0:
            return {}
        
        # Basic metrics
        num_nodes = graph.number_of_nodes()
        num_edges = graph.number_of_edges()
        
        # Connectivity
        is_connected = nx.is_connected(graph)
        num_components = nx.number_connected_components(graph)
        
        # Density
        density = nx.density(graph)
        
        # Clustering
        avg_clustering = nx.average_clustering(graph)
        
        # Path length (for connected components)
        if is_connected:
            avg_path_length = nx.average_shortest_path_length(graph)
            diameter = nx.diameter(graph)
        else:
            avg_path_length = None
            diameter = None
        
        # Degree statistics
        degrees = [d for n, d in graph.degree()]
        degree_stats = {
            "mean_degree": np.mean(degrees),
            "std_degree": np.std(degrees),
            "min_degree": np.min(degrees),
            "max_degree": np.max(degrees)
        }
        
        # Assortativity
        assortativity = nx.degree_assortativity_coefficient(graph)
        
        topology_metrics = {
            "num_nodes": num_nodes,
            "num_edges": num_edges,
            "is_connected": is_connected,
            "num_components": num_components,
            "density": density,
            "avg_clustering": avg_clustering,
            "avg_path_length": avg_path_length,
            "diameter": diameter,
            "degree_stats": degree_stats,
            "assortativity": assortativity
        }
        
        self.analysis_results["topology"] = topology_metrics
        logger.info("Analyzed network topology")
        return topology_metrics
    
    def find_hub_genes(self, graph: Optional[nx.Graph] = None, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Find hub genes based on degree centrality.
        
        Args:
            graph: NetworkX graph (uses self.graph if None)
            top_k: Number of top hub genes to return
            
        Returns:
            List of (gene_name, degree_centrality) tuples
        """
        if graph is None:
            graph = self.graph
        
        if graph.number_of_nodes() == 0:
            return []
        
        degree_cent = degree_centrality(graph)
        hub_genes = sorted(degree_cent.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        logger.info(f"Found {len(hub_genes)} hub genes")
        return hub_genes
    
    def find_bottleneck_genes(self, graph: Optional[nx.Graph] = None, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Find bottleneck genes based on betweenness centrality.
        
        Args:
            graph: NetworkX graph (uses self.graph if None)
            top_k: Number of top bottleneck genes to return
            
        Returns:
            List of (gene_name, betweenness_centrality) tuples
        """
        if graph is None:
            graph = self.graph
        
        if graph.number_of_nodes() == 0:
            return []
        
        betweenness_cent = betweenness_centrality(graph)
        bottleneck_genes = sorted(betweenness_cent.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        logger.info(f"Found {len(bottleneck_genes)} bottleneck genes")
        return bottleneck_genes
    
    def get_network_statistics(self, graph: Optional[nx.Graph] = None) -> Dict[str, Any]:
        """
        Get comprehensive network statistics.
        
        Args:
            graph: NetworkX graph (uses self.graph if None)
            
        Returns:
            Dictionary with network statistics
        """
        if graph is None:
            graph = self.graph
        
        stats = {
            "basic_metrics": {
                "num_nodes": graph.number_of_nodes(),
                "num_edges": graph.number_of_edges(),
                "density": nx.density(graph)
            },
            "connectivity": {
                "is_connected": nx.is_connected(graph),
                "num_components": nx.number_connected_components(graph)
            },
            "clustering": {
                "avg_clustering": nx.average_clustering(graph)
            }
        }
        
        # Add degree statistics
        degrees = [d for n, d in graph.degree()]
        if degrees:
            stats["degree_distribution"] = {
                "mean": np.mean(degrees),
                "std": np.std(degrees),
                "min": np.min(degrees),
                "max": np.max(degrees)
            }
        
        # Add path length for connected graphs
        if stats["connectivity"]["is_connected"]:
            stats["path_length"] = {
                "avg_path_length": nx.average_shortest_path_length(graph),
                "diameter": nx.diameter(graph)
            }
        
        return stats
    
    def export_network_data(self, graph: Optional[nx.Graph] = None, output_file: str = "network_data.json"):
        """
        Export network data to JSON file.
        
        Args:
            graph: NetworkX graph (uses self.graph if None)
            output_file: Output file path
        """
        if graph is None:
            graph = self.graph
        
        # Convert to dictionary format
        network_data = {
            "nodes": [
                {
                    "id": node,
                    "attributes": dict(graph.nodes[node])
                }
                for node in graph.nodes()
            ],
            "edges": [
                {
                    "source": edge[0],
                    "target": edge[1],
                    "attributes": dict(graph.edges[edge])
                }
                for edge in graph.edges()
            ],
            "statistics": self.get_network_statistics(graph)
        }
        
        import json
        with open(output_file, 'w') as f:
            json.dump(network_data, f, indent=2, default=str)
        
        logger.info(f"Network data exported to {output_file}")
    
    def clear_graph(self):
        """Clear the current graph."""
        self.graph.clear()
        self.directed_graph.clear()
        self.analysis_results.clear()
        logger.info("Graph cleared")
