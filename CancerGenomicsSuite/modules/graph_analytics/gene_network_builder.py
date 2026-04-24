#!/usr/bin/env python3
"""
Gene Network Builder

This module provides functionality to build gene networks from various
data sources for cancer genomics analysis.
"""

import logging
from typing import Dict, List, Optional, Any, Union, Tuple
import pandas as pd
import numpy as np
from collections import defaultdict

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

logger = logging.getLogger(__name__)


class GeneNetworkBuilder:
    """
    Gene network builder for cancer genomics data.
    
    Provides functionality to:
    - Build networks from expression data
    - Create networks from protein interactions
    - Integrate multiple data sources
    - Filter and validate networks
    - Export network data
    """
    
    def __init__(self):
        """Initialize gene network builder."""
        if not NETWORKX_AVAILABLE:
            raise ImportError("NetworkX not available. Install networkx package.")
        
        self.networks = {}
        self.integrated_network = nx.Graph()
    
    def build_coexpression_network(
        self,
        expression_data: pd.DataFrame,
        correlation_threshold: float = 0.7,
        p_value_threshold: float = 0.05,
        method: str = "pearson"
    ) -> nx.Graph:
        """
        Build a co-expression network from gene expression data.
        
        Args:
            expression_data: DataFrame with gene expression data (genes as columns)
            correlation_threshold: Minimum correlation threshold
            p_value_threshold: Maximum p-value threshold
            method: Correlation method ("pearson", "spearman", "kendall")
            
        Returns:
            NetworkX graph with co-expression relationships
        """
        from scipy.stats import pearsonr, spearmanr, kendalltau
        
        # Transpose data to have genes as rows
        if expression_data.index.dtype == 'object':
            # Assume samples are rows, genes are columns
            data = expression_data.T
        else:
            data = expression_data
        
        genes = data.index.tolist()
        network = nx.Graph()
        
        # Add all genes as nodes
        for gene in genes:
            network.add_node(gene, node_type="gene")
        
        # Calculate correlations
        num_genes = len(genes)
        edges_added = 0
        
        for i in range(num_genes):
            for j in range(i + 1, num_genes):
                gene1 = genes[i]
                gene2 = genes[j]
                
                # Calculate correlation
                if method == "pearson":
                    corr, p_value = pearsonr(data.iloc[i], data.iloc[j])
                elif method == "spearman":
                    corr, p_value = spearmanr(data.iloc[i], data.iloc[j])
                elif method == "kendall":
                    corr, p_value = kendalltau(data.iloc[i], data.iloc[j])
                else:
                    raise ValueError(f"Unknown correlation method: {method}")
                
                # Add edge if criteria are met
                if (abs(corr) >= correlation_threshold and 
                    p_value <= p_value_threshold and 
                    not np.isnan(corr)):
                    
                    network.add_edge(
                        gene1, gene2,
                        correlation=corr,
                        p_value=p_value,
                        edge_type="coexpression",
                        method=method
                    )
                    edges_added += 1
        
        self.networks["coexpression"] = network
        logger.info(f"Built co-expression network with {network.number_of_nodes()} nodes and {edges_added} edges")
        return network
    
    def build_protein_interaction_network(
        self,
        interaction_data: pd.DataFrame,
        confidence_threshold: float = 0.5,
        include_self_loops: bool = False
    ) -> nx.Graph:
        """
        Build a protein-protein interaction network.
        
        Args:
            interaction_data: DataFrame with protein interactions
            confidence_threshold: Minimum confidence threshold
            include_self_loops: Whether to include self-interactions
            
        Returns:
            NetworkX graph with protein interactions
        """
        network = nx.Graph()
        
        for _, row in interaction_data.iterrows():
            protein1 = row["protein1"]
            protein2 = row["protein2"]
            confidence = row.get("confidence", 1.0)
            
            # Skip if confidence is too low
            if confidence < confidence_threshold:
                continue
            
            # Skip self-loops if not desired
            if not include_self_loops and protein1 == protein2:
                continue
            
            # Add nodes
            network.add_node(protein1, node_type="protein")
            network.add_node(protein2, node_type="protein")
            
            # Add edge
            network.add_edge(
                protein1, protein2,
                confidence=confidence,
                interaction_type=row.get("interaction_type", "unknown"),
                experimental_method=row.get("experimental_method", "unknown"),
                source=row.get("source", "unknown"),
                edge_type="protein_interaction"
            )
        
        self.networks["protein_interaction"] = network
        logger.info(f"Built protein interaction network with {network.number_of_nodes()} nodes and {network.number_of_edges()} edges")
        return network
    
    def build_pathway_network(
        self,
        pathway_data: pd.DataFrame,
        gene_pathway_data: pd.DataFrame,
        include_gene_interactions: bool = True
    ) -> nx.Graph:
        """
        Build a pathway-gene network.
        
        Args:
            pathway_data: DataFrame with pathway information
            gene_pathway_data: DataFrame linking genes to pathways
            include_gene_interactions: Whether to include gene-gene edges
            
        Returns:
            NetworkX bipartite graph
        """
        network = nx.Graph()
        
        # Add pathway nodes
        for _, pathway in pathway_data.iterrows():
            pathway_name = pathway["pathway_name"]
            network.add_node(
                pathway_name,
                node_type="pathway",
                pathway_id=pathway.get("pathway_id", ""),
                pathway_type=pathway.get("pathway_type", ""),
                description=pathway.get("description", "")
            )
        
        # Add gene nodes and gene-pathway edges
        genes_in_pathways = set()
        for _, row in gene_pathway_data.iterrows():
            gene_name = row["gene_name"]
            pathway_name = row["pathway_name"]
            
            if pathway_name in network.nodes():
                network.add_node(gene_name, node_type="gene")
                genes_in_pathways.add(gene_name)
                
                network.add_edge(
                    gene_name, pathway_name,
                    role=row.get("role", "member"),
                    confidence=row.get("confidence", 1.0),
                    edge_type="gene_pathway"
                )
        
        # Add gene-gene edges if desired
        if include_gene_interactions:
            gene_list = list(genes_in_pathways)
            for i, gene1 in enumerate(gene_list):
                for gene2 in gene_list[i+1:]:
                    # Check if genes are in the same pathway
                    pathways1 = set(network.neighbors(gene1))
                    pathways2 = set(network.neighbors(gene2))
                    common_pathways = pathways1 & pathways2
                    
                    if common_pathways:
                        # Add edge with pathway overlap information
                        network.add_edge(
                            gene1, gene2,
                            common_pathways=list(common_pathways),
                            pathway_overlap=len(common_pathways),
                            edge_type="pathway_co_membership"
                        )
        
        self.networks["pathway"] = network
        logger.info(f"Built pathway network with {network.number_of_nodes()} nodes and {network.number_of_edges()} edges")
        return network
    
    def build_mutation_network(
        self,
        mutation_data: pd.DataFrame,
        gene_data: pd.DataFrame,
        co_mutation_threshold: int = 2
    ) -> nx.Graph:
        """
        Build a mutation co-occurrence network.
        
        Args:
            mutation_data: DataFrame with mutation data
            gene_data: DataFrame with gene information
            co_mutation_threshold: Minimum number of co-mutations
            
        Returns:
            NetworkX graph with mutation relationships
        """
        network = nx.Graph()
        
        # Add gene nodes
        for _, gene in gene_data.iterrows():
            gene_name = gene["gene_name"]
            network.add_node(
                gene_name,
                node_type="gene",
                gene_id=gene.get("gene_id", ""),
                chromosome=gene.get("chromosome", ""),
                start_pos=gene.get("start_pos", 0),
                end_pos=gene.get("end_pos", 0)
            )
        
        # Count co-mutations
        co_mutation_counts = defaultdict(int)
        
        for _, mutation in mutation_data.iterrows():
            patient_id = mutation["patient_id"]
            gene_name = mutation["gene_name"]
            
            if gene_name in network.nodes():
                # Find other mutations in the same patient
                patient_mutations = mutation_data[
                    (mutation_data["patient_id"] == patient_id) & 
                    (mutation_data["gene_name"] != gene_name)
                ]["gene_name"].tolist()
                
                for other_gene in patient_mutations:
                    if other_gene in network.nodes():
                        # Count co-mutation
                        pair = tuple(sorted([gene_name, other_gene]))
                        co_mutation_counts[pair] += 1
        
        # Add edges for significant co-mutations
        for (gene1, gene2), count in co_mutation_counts.items():
            if count >= co_mutation_threshold:
                network.add_edge(
                    gene1, gene2,
                    co_mutation_count=count,
                    edge_type="co_mutation"
                )
        
        self.networks["mutation"] = network
        logger.info(f"Built mutation network with {network.number_of_nodes()} nodes and {network.number_of_edges()} edges")
        return network
    
    def integrate_networks(
        self,
        network_names: List[str],
        integration_method: str = "union",
        edge_weight_attr: str = "weight"
    ) -> nx.Graph:
        """
        Integrate multiple networks into a single network.
        
        Args:
            network_names: List of network names to integrate
            integration_method: Integration method ("union", "intersection", "weighted")
            edge_weight_attr: Edge attribute to use for weighting
            
        Returns:
            Integrated NetworkX graph
        """
        if not network_names:
            return nx.Graph()
        
        # Start with the first network
        integrated = self.networks[network_names[0]].copy()
        
        # Integrate additional networks
        for network_name in network_names[1:]:
            if network_name not in self.networks:
                logger.warning(f"Network {network_name} not found")
                continue
            
            network = self.networks[network_name]
            
            if integration_method == "union":
                # Add all nodes and edges
                integrated = nx.compose(integrated, network)
            
            elif integration_method == "intersection":
                # Keep only common edges
                common_edges = set(integrated.edges()) & set(network.edges())
                integrated = nx.Graph()
                integrated.add_edges_from(common_edges)
            
            elif integration_method == "weighted":
                # Combine networks with weights
                for edge in network.edges(data=True):
                    node1, node2, attrs = edge
                    
                    if integrated.has_edge(node1, node2):
                        # Update weight
                        current_weight = integrated[node1][node2].get(edge_weight_attr, 1.0)
                        new_weight = attrs.get(edge_weight_attr, 1.0)
                        integrated[node1][node2][edge_weight_attr] = current_weight + new_weight
                    else:
                        # Add new edge
                        integrated.add_edge(node1, node2, **attrs)
        
        self.integrated_network = integrated
        logger.info(f"Integrated {len(network_names)} networks into a single network with {integrated.number_of_nodes()} nodes and {integrated.number_of_edges()} edges")
        return integrated
    
    def filter_network(
        self,
        network: nx.Graph,
        min_degree: int = 1,
        max_degree: Optional[int] = None,
        edge_weight_threshold: Optional[float] = None,
        edge_weight_attr: str = "weight"
    ) -> nx.Graph:
        """
        Filter network based on node and edge criteria.
        
        Args:
            network: NetworkX graph to filter
            min_degree: Minimum node degree
            max_degree: Maximum node degree
            edge_weight_threshold: Minimum edge weight
            edge_weight_attr: Edge weight attribute name
            
        Returns:
            Filtered NetworkX graph
        """
        filtered = network.copy()
        
        # Filter by edge weight
        if edge_weight_threshold is not None:
            edges_to_remove = []
            for edge in filtered.edges(data=True):
                weight = edge[2].get(edge_weight_attr, 1.0)
                if weight < edge_weight_threshold:
                    edges_to_remove.append((edge[0], edge[1]))
            
            filtered.remove_edges_from(edges_to_remove)
        
        # Filter by node degree
        nodes_to_remove = []
        for node in filtered.nodes():
            degree = filtered.degree(node)
            if degree < min_degree or (max_degree is not None and degree > max_degree):
                nodes_to_remove.append(node)
        
        filtered.remove_nodes_from(nodes_to_remove)
        
        logger.info(f"Filtered network: {network.number_of_nodes()} -> {filtered.number_of_nodes()} nodes, {network.number_of_edges()} -> {filtered.number_of_edges()} edges")
        return filtered
    
    def get_network_statistics(self, network: Optional[nx.Graph] = None) -> Dict[str, Any]:
        """
        Get comprehensive network statistics.
        
        Args:
            network: NetworkX graph (uses integrated network if None)
            
        Returns:
            Dictionary with network statistics
        """
        if network is None:
            network = self.integrated_network
        
        if network.number_of_nodes() == 0:
            return {}
        
        stats = {
            "basic_metrics": {
                "num_nodes": network.number_of_nodes(),
                "num_edges": network.number_of_edges(),
                "density": nx.density(network)
            },
            "connectivity": {
                "is_connected": nx.is_connected(network),
                "num_components": nx.number_connected_components(network)
            },
            "degree_distribution": {},
            "clustering": {
                "avg_clustering": nx.average_clustering(network)
            }
        }
        
        # Degree statistics
        degrees = [d for n, d in network.degree()]
        if degrees:
            stats["degree_distribution"] = {
                "mean": np.mean(degrees),
                "std": np.std(degrees),
                "min": np.min(degrees),
                "max": np.max(degrees),
                "median": np.median(degrees)
            }
        
        # Path length for connected graphs
        if stats["connectivity"]["is_connected"]:
            stats["path_length"] = {
                "avg_path_length": nx.average_shortest_path_length(network),
                "diameter": nx.diameter(network)
            }
        
        # Node type distribution
        node_types = defaultdict(int)
        for node, attrs in network.nodes(data=True):
            node_type = attrs.get("node_type", "unknown")
            node_types[node_type] += 1
        stats["node_types"] = dict(node_types)
        
        # Edge type distribution
        edge_types = defaultdict(int)
        for edge, attrs in network.edges(data=True):
            edge_type = attrs.get("edge_type", "unknown")
            edge_types[edge_type] += 1
        stats["edge_types"] = dict(edge_types)
        
        return stats
    
    def export_network(
        self,
        network: nx.Graph,
        output_file: str,
        format: str = "graphml"
    ):
        """
        Export network to file.
        
        Args:
            network: NetworkX graph
            output_file: Output file path
            format: Export format ("graphml", "gml", "edgelist", "json")
        """
        if format == "graphml":
            nx.write_graphml(network, output_file)
        elif format == "gml":
            nx.write_gml(network, output_file)
        elif format == "edgelist":
            nx.write_edgelist(network, output_file)
        elif format == "json":
            import json
            data = nx.node_link_data(network)
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
        else:
            raise ValueError(f"Unknown format: {format}")
        
        logger.info(f"Network exported to {output_file} in {format} format")
    
    def get_network_summary(self) -> Dict[str, Any]:
        """
        Get summary of all built networks.
        
        Returns:
            Dictionary with network summaries
        """
        summary = {
            "networks": {},
            "integrated_network": {}
        }
        
        # Individual networks
        for name, network in self.networks.items():
            summary["networks"][name] = {
                "num_nodes": network.number_of_nodes(),
                "num_edges": network.number_of_edges(),
                "density": nx.density(network),
                "is_connected": nx.is_connected(network)
            }
        
        # Integrated network
        if self.integrated_network.number_of_nodes() > 0:
            summary["integrated_network"] = {
                "num_nodes": self.integrated_network.number_of_nodes(),
                "num_edges": self.integrated_network.number_of_edges(),
                "density": nx.density(self.integrated_network),
                "is_connected": nx.is_connected(self.integrated_network)
            }
        
        return summary
