#!/usr/bin/env python3
"""
Pathway Analyzer

This module provides pathway analysis capabilities for cancer genomics data
using graph-based approaches.
"""

import logging
from typing import Dict, List, Optional, Any, Union, Tuple
import pandas as pd
import numpy as np
from scipy.stats import hypergeom, fisher_exact
from collections import defaultdict

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

logger = logging.getLogger(__name__)


class PathwayAnalyzer:
    """
    Pathway analyzer for cancer genomics data.
    
    Provides functionality to:
    - Analyze pathway enrichment
    - Detect pathway modules
    - Calculate pathway centrality
    - Identify pathway interactions
    - Perform pathway-based network analysis
    """
    
    def __init__(self):
        """Initialize pathway analyzer."""
        self.pathway_data = {}
        self.gene_pathway_mapping = defaultdict(list)
        self.pathway_gene_mapping = defaultdict(list)
        self.pathway_graph = nx.Graph()
    
    def load_pathway_data(
        self,
        pathway_data: pd.DataFrame,
        gene_pathway_data: pd.DataFrame
    ):
        """
        Load pathway and gene-pathway mapping data.
        
        Args:
            pathway_data: DataFrame with pathway information
            gene_pathway_data: DataFrame linking genes to pathways
        """
        # Store pathway data
        for _, pathway in pathway_data.iterrows():
            pathway_id = pathway.get("pathway_id", "")
            pathway_name = pathway.get("pathway_name", "")
            
            self.pathway_data[pathway_name] = {
                "pathway_id": pathway_id,
                "pathway_name": pathway_name,
                "pathway_type": pathway.get("pathway_type", ""),
                "description": pathway.get("description", ""),
                "source": pathway.get("source", ""),
                "genes": []
            }
        
        # Create gene-pathway mappings
        for _, row in gene_pathway_data.iterrows():
            gene_name = row["gene_name"]
            pathway_name = row["pathway_name"]
            
            if pathway_name in self.pathway_data:
                self.gene_pathway_mapping[gene_name].append(pathway_name)
                self.pathway_gene_mapping[pathway_name].append(gene_name)
                self.pathway_data[pathway_name]["genes"].append(gene_name)
        
        # Build pathway graph based on gene overlap
        self._build_pathway_graph()
        
        logger.info(f"Loaded {len(self.pathway_data)} pathways with {len(self.gene_pathway_mapping)} genes")
    
    def _build_pathway_graph(self):
        """Build a graph of pathways based on gene overlap."""
        pathway_names = list(self.pathway_data.keys())
        
        for i, pathway1 in enumerate(pathway_names):
            for j, pathway2 in enumerate(pathway_names[i+1:], i+1):
                # Calculate gene overlap
                genes1 = set(self.pathway_gene_mapping[pathway1])
                genes2 = set(self.pathway_gene_mapping[pathway2])
                
                overlap = len(genes1 & genes2)
                union = len(genes1 | genes2)
                
                if overlap > 0:
                    # Jaccard similarity
                    jaccard = overlap / union if union > 0 else 0
                    
                    # Add edge with similarity weight
                    self.pathway_graph.add_edge(
                        pathway1, pathway2,
                        overlap=overlap,
                        jaccard_similarity=jaccard,
                        union_size=union
                    )
        
        logger.info(f"Built pathway graph with {self.pathway_graph.number_of_nodes()} nodes and {self.pathway_graph.number_of_edges()} edges")
    
    def calculate_pathway_enrichment(
        self,
        gene_list: List[str],
        background_genes: Optional[List[str]] = None,
        method: str = "hypergeometric",
        min_pathway_size: int = 5,
        max_pathway_size: int = 500
    ) -> pd.DataFrame:
        """
        Calculate pathway enrichment for a list of genes.
        
        Args:
            gene_list: List of genes to test
            background_genes: Background gene set (all genes if None)
            method: Statistical method ("hypergeometric" or "fisher")
            min_pathway_size: Minimum pathway size
            max_pathway_size: Maximum pathway size
            
        Returns:
            DataFrame with enrichment results
        """
        if background_genes is None:
            background_genes = list(self.gene_pathway_mapping.keys())
        
        enrichment_results = []
        
        for pathway_name, pathway_info in self.pathway_data.items():
            pathway_genes = set(pathway_info["genes"])
            
            # Filter by pathway size
            if len(pathway_genes) < min_pathway_size or len(pathway_genes) > max_pathway_size:
                continue
            
            # Calculate overlap
            overlap_genes = set(gene_list) & pathway_genes
            overlap_count = len(overlap_genes)
            
            if overlap_count == 0:
                continue
            
            # Statistical test
            if method == "hypergeometric":
                p_value = self._hypergeometric_test(
                    overlap_count, len(gene_list), len(pathway_genes), len(background_genes)
                )
            elif method == "fisher":
                p_value = self._fisher_exact_test(
                    overlap_count, len(gene_list), len(pathway_genes), len(background_genes)
                )
            else:
                raise ValueError(f"Unknown method: {method}")
            
            # Calculate fold enrichment
            expected = (len(pathway_genes) * len(gene_list)) / len(background_genes)
            fold_enrichment = overlap_count / expected if expected > 0 else 0
            
            # Calculate enrichment ratio
            enrichment_ratio = (overlap_count / len(gene_list)) / (len(pathway_genes) / len(background_genes))
            
            enrichment_results.append({
                "pathway_name": pathway_name,
                "pathway_id": pathway_info["pathway_id"],
                "pathway_type": pathway_info["pathway_type"],
                "description": pathway_info["description"],
                "genes_in_pathway": len(pathway_genes),
                "genes_in_test_set": len(gene_list),
                "overlap_count": overlap_count,
                "expected_overlap": expected,
                "fold_enrichment": fold_enrichment,
                "enrichment_ratio": enrichment_ratio,
                "p_value": p_value,
                "overlap_genes": list(overlap_genes)
            })
        
        # Create DataFrame and sort by p-value
        results_df = pd.DataFrame(enrichment_results)
        if not results_df.empty:
            results_df = results_df.sort_values("p_value")
            
            # Calculate FDR correction
            from statsmodels.stats.multitest import multipletests
            _, pvals_corrected, _, _ = multipletests(results_df["p_value"], method='fdr_bh')
            results_df["fdr_corrected_p_value"] = pvals_corrected
        
        return results_df
    
    def _hypergeometric_test(self, overlap: int, test_size: int, pathway_size: int, background_size: int) -> float:
        """Perform hypergeometric test."""
        return hypergeom.sf(overlap - 1, background_size, pathway_size, test_size)
    
    def _fisher_exact_test(self, overlap: int, test_size: int, pathway_size: int, background_size: int) -> float:
        """Perform Fisher's exact test."""
        # Create contingency table
        a = overlap  # overlap
        b = test_size - overlap  # test set not in pathway
        c = pathway_size - overlap  # pathway not in test set
        d = background_size - test_size - c  # neither
        
        _, p_value = fisher_exact([[a, b], [c, d]], alternative='greater')
        return p_value
    
    def find_pathway_modules(
        self,
        method: str = "greedy",
        min_module_size: int = 3
    ) -> Dict[str, List[str]]:
        """
        Find pathway modules using community detection.
        
        Args:
            method: Community detection method ("greedy" or "label_propagation")
            min_module_size: Minimum module size
            
        Returns:
            Dictionary mapping module IDs to pathway lists
        """
        if not NETWORKX_AVAILABLE:
            raise ImportError("NetworkX not available")
        
        if self.pathway_graph.number_of_nodes() == 0:
            return {}
        
        # Detect communities
        if method == "greedy":
            from networkx.algorithms.community import greedy_modularity_communities
            communities = list(greedy_modularity_communities(self.pathway_graph))
        elif method == "label_propagation":
            from networkx.algorithms.community import label_propagation_communities
            communities = list(label_propagation_communities(self.pathway_graph))
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # Filter by minimum size
        modules = {}
        for i, community in enumerate(communities):
            if len(community) >= min_module_size:
                modules[f"module_{i}"] = list(community)
        
        logger.info(f"Found {len(modules)} pathway modules")
        return modules
    
    def calculate_pathway_centrality(self) -> Dict[str, Dict[str, float]]:
        """
        Calculate centrality measures for pathways.
        
        Returns:
            Dictionary with centrality measures for each pathway
        """
        if not NETWORKX_AVAILABLE:
            raise ImportError("NetworkX not available")
        
        if self.pathway_graph.number_of_nodes() == 0:
            return {}
        
        # Calculate centrality measures
        degree_cent = nx.degree_centrality(self.pathway_graph)
        betweenness_cent = nx.betweenness_centrality(self.pathway_graph)
        closeness_cent = nx.closeness_centrality(self.pathway_graph)
        
        # Calculate eigenvector centrality
        try:
            eigenvector_cent = nx.eigenvector_centrality(self.pathway_graph, max_iter=1000)
        except nx.PowerIterationFailedConvergence:
            eigenvector_cent = {node: 0.0 for node in self.pathway_graph.nodes()}
        
        # Combine results
        centrality_results = {}
        for pathway in self.pathway_graph.nodes():
            centrality_results[pathway] = {
                "degree_centrality": degree_cent[pathway],
                "betweenness_centrality": betweenness_cent[pathway],
                "closeness_centrality": closeness_cent[pathway],
                "eigenvector_centrality": eigenvector_cent[pathway]
            }
        
        return centrality_results
    
    def find_pathway_interactions(
        self,
        pathway1: str,
        pathway2: str
    ) -> Dict[str, Any]:
        """
        Find interactions between two pathways.
        
        Args:
            pathway1: First pathway name
            pathway2: Second pathway name
            
        Returns:
            Dictionary with interaction information
        """
        if pathway1 not in self.pathway_data or pathway2 not in self.pathway_data:
            return {}
        
        genes1 = set(self.pathway_gene_mapping[pathway1])
        genes2 = set(self.pathway_gene_mapping[pathway2])
        
        # Calculate overlap
        overlap_genes = genes1 & genes2
        union_genes = genes1 | genes2
        
        # Calculate similarity measures
        jaccard_similarity = len(overlap_genes) / len(union_genes) if union_genes else 0
        overlap_coefficient = len(overlap_genes) / min(len(genes1), len(genes2)) if genes1 and genes2 else 0
        
        # Check if pathways are connected in the graph
        graph_connected = self.pathway_graph.has_edge(pathway1, pathway2)
        graph_similarity = 0
        if graph_connected:
            graph_similarity = self.pathway_graph[pathway1][pathway2].get("jaccard_similarity", 0)
        
        return {
            "pathway1": pathway1,
            "pathway2": pathway2,
            "overlap_genes": list(overlap_genes),
            "overlap_count": len(overlap_genes),
            "union_count": len(union_genes),
            "jaccard_similarity": jaccard_similarity,
            "overlap_coefficient": overlap_coefficient,
            "graph_connected": graph_connected,
            "graph_similarity": graph_similarity
        }
    
    def get_pathway_statistics(self) -> Dict[str, Any]:
        """
        Get pathway database statistics.
        
        Returns:
            Dictionary with pathway statistics
        """
        stats = {
            "total_pathways": len(self.pathway_data),
            "total_genes": len(self.gene_pathway_mapping),
            "pathway_types": {},
            "pathway_sizes": [],
            "gene_pathway_counts": [],
            "graph_metrics": {}
        }
        
        # Pathway types
        for pathway_info in self.pathway_data.values():
            pathway_type = pathway_info.get("pathway_type", "unknown")
            stats["pathway_types"][pathway_type] = stats["pathway_types"].get(pathway_type, 0) + 1
        
        # Pathway sizes
        for pathway_info in self.pathway_data.values():
            stats["pathway_sizes"].append(len(pathway_info["genes"]))
        
        # Gene-pathway counts
        for gene, pathways in self.gene_pathway_mapping.items():
            stats["gene_pathway_counts"].append(len(pathways))
        
        # Graph metrics
        if self.pathway_graph.number_of_nodes() > 0:
            stats["graph_metrics"] = {
                "num_nodes": self.pathway_graph.number_of_nodes(),
                "num_edges": self.pathway_graph.number_of_edges(),
                "density": nx.density(self.pathway_graph),
                "avg_clustering": nx.average_clustering(self.pathway_graph)
            }
        
        return stats
    
    def find_similar_pathways(
        self,
        pathway_name: str,
        top_k: int = 10,
        min_similarity: float = 0.1
    ) -> List[Tuple[str, float]]:
        """
        Find pathways similar to a given pathway.
        
        Args:
            pathway_name: Pathway name
            top_k: Number of top similar pathways to return
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of (pathway_name, similarity) tuples
        """
        if pathway_name not in self.pathway_data:
            return []
        
        similarities = []
        
        for other_pathway in self.pathway_data.keys():
            if other_pathway == pathway_name:
                continue
            
            # Get similarity from graph
            if self.pathway_graph.has_edge(pathway_name, other_pathway):
                similarity = self.pathway_graph[pathway_name][other_pathway].get("jaccard_similarity", 0)
                
                if similarity >= min_similarity:
                    similarities.append((other_pathway, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def analyze_pathway_dysregulation(
        self,
        gene_expression_data: pd.DataFrame,
        sample_groups: Dict[str, List[str]],
        pathway_name: str,
        method: str = "mean"
    ) -> Dict[str, Any]:
        """
        Analyze pathway dysregulation between sample groups.
        
        Args:
            gene_expression_data: DataFrame with gene expression data
            sample_groups: Dictionary mapping group names to sample lists
            pathway_name: Pathway to analyze
            method: Aggregation method ("mean", "median", "sum")
            
        Returns:
            Dictionary with dysregulation analysis results
        """
        if pathway_name not in self.pathway_data:
            return {}
        
        pathway_genes = self.pathway_data[pathway_name]["genes"]
        
        # Filter genes that are in the expression data
        available_genes = [gene for gene in pathway_genes if gene in gene_expression_data.columns]
        
        if not available_genes:
            return {}
        
        # Calculate pathway scores for each group
        group_scores = {}
        
        for group_name, samples in sample_groups.items():
            # Filter samples that are in the expression data
            available_samples = [sample for sample in samples if sample in gene_expression_data.index]
            
            if not available_samples:
                continue
            
            # Get expression data for pathway genes
            pathway_expression = gene_expression_data.loc[available_samples, available_genes]
            
            # Calculate pathway score
            if method == "mean":
                pathway_score = pathway_expression.mean(axis=1).mean()
            elif method == "median":
                pathway_score = pathway_expression.median(axis=1).median()
            elif method == "sum":
                pathway_score = pathway_expression.sum(axis=1).mean()
            else:
                raise ValueError(f"Unknown method: {method}")
            
            group_scores[group_name] = {
                "pathway_score": pathway_score,
                "num_genes": len(available_genes),
                "num_samples": len(available_samples)
            }
        
        return {
            "pathway_name": pathway_name,
            "method": method,
            "group_scores": group_scores,
            "available_genes": available_genes
        }
    
    def export_pathway_data(self, output_file: str):
        """
        Export pathway data to JSON file.
        
        Args:
            output_file: Output file path
        """
        import json
        
        export_data = {
            "pathway_data": self.pathway_data,
            "gene_pathway_mapping": dict(self.gene_pathway_mapping),
            "pathway_gene_mapping": dict(self.pathway_gene_mapping),
            "statistics": self.get_pathway_statistics()
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Pathway data exported to {output_file}")
