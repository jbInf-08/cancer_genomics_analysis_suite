"""
Metabolic Pathway Mapper Module

This module provides comprehensive functionality for mapping and analyzing
metabolic pathways in cancer genomics data.
"""

import pandas as pd
import numpy as np
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Tuple, Optional, Any
import json
import requests
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetabolicPathwayMapper:
    """
    A comprehensive class for mapping and analyzing metabolic pathways
    in cancer genomics data.
    """
    
    def __init__(self):
        """Initialize the pathway mapper."""
        self.pathways = {}
        self.gene_expression_data = None
        self.mutation_data = None
        self.pathway_network = nx.DiGraph()
        self.kegg_pathways = {}
        
    def load_gene_expression_data(self, file_path: str) -> pd.DataFrame:
        """
        Load gene expression data from CSV file.
        
        Args:
            file_path: Path to the gene expression CSV file
            
        Returns:
            DataFrame containing gene expression data
        """
        try:
            self.gene_expression_data = pd.read_csv(file_path)
            logger.info(f"Loaded gene expression data with {len(self.gene_expression_data)} genes")
            return self.gene_expression_data
        except Exception as e:
            logger.error(f"Error loading gene expression data: {e}")
            raise
    
    def load_mutation_data(self, file_path: str) -> pd.DataFrame:
        """
        Load mutation data from CSV file.
        
        Args:
            file_path: Path to the mutation CSV file
            
        Returns:
            DataFrame containing mutation data
        """
        try:
            self.mutation_data = pd.read_csv(file_path)
            logger.info(f"Loaded mutation data with {len(self.mutation_data)} mutations")
            return self.mutation_data
        except Exception as e:
            logger.error(f"Error loading mutation data: {e}")
            raise
    
    def create_pathway_network(self, pathway_data: Dict[str, List[str]]) -> nx.DiGraph:
        """
        Create a network graph from pathway data.
        
        Args:
            pathway_data: Dictionary mapping pathway names to lists of genes
            
        Returns:
            NetworkX directed graph representing the pathway network
        """
        self.pathway_network = nx.DiGraph()
        
        for pathway_name, genes in pathway_data.items():
            # Add pathway as a node
            self.pathway_network.add_node(pathway_name, type='pathway')
            
            # Add genes as nodes and connect them to the pathway
            for gene in genes:
                self.pathway_network.add_node(gene, type='gene')
                self.pathway_network.add_edge(pathway_name, gene)
        
        logger.info(f"Created pathway network with {self.pathway_network.number_of_nodes()} nodes and {self.pathway_network.number_of_edges()} edges")
        return self.pathway_network
    
    def analyze_pathway_activity(self, pathway_name: str) -> Dict[str, Any]:
        """
        Analyze the activity of a specific pathway.
        
        Args:
            pathway_name: Name of the pathway to analyze
            
        Returns:
            Dictionary containing pathway analysis results
        """
        if self.gene_expression_data is None:
            raise ValueError("Gene expression data not loaded")
        
        # Get genes in the pathway
        pathway_genes = [node for node in self.pathway_network.neighbors(pathway_name) 
                        if self.pathway_network.nodes[node]['type'] == 'gene']
        
        if not pathway_genes:
            return {"error": f"No genes found for pathway {pathway_name}"}
        
        # Filter expression data for pathway genes
        pathway_expression = self.gene_expression_data[
            self.gene_expression_data['gene_id'].isin(pathway_genes)
        ]
        
        # Calculate pathway activity metrics
        mean_expression = pathway_expression.select_dtypes(include=[np.number]).mean().mean()
        std_expression = pathway_expression.select_dtypes(include=[np.number]).std().mean()
        
        # Calculate pathway score (mean of normalized expression)
        expression_cols = pathway_expression.select_dtypes(include=[np.number]).columns
        pathway_scores = pathway_expression[expression_cols].mean(axis=0)
        
        analysis_results = {
            'pathway_name': pathway_name,
            'num_genes': len(pathway_genes),
            'mean_expression': mean_expression,
            'std_expression': std_expression,
            'pathway_score': pathway_scores.mean(),
            'genes': pathway_genes,
            'expression_data': pathway_expression.to_dict('records')
        }
        
        return analysis_results
    
    def identify_dysregulated_pathways(self, threshold: float = 2.0) -> List[Dict[str, Any]]:
        """
        Identify dysregulated pathways based on expression data.
        
        Args:
            threshold: Z-score threshold for dysregulation
            
        Returns:
            List of dysregulated pathways with their analysis
        """
        if self.gene_expression_data is None:
            raise ValueError("Gene expression data not loaded")
        
        dysregulated_pathways = []
        
        # Get all pathway nodes
        pathway_nodes = [node for node in self.pathway_network.nodes() 
                        if self.pathway_network.nodes[node]['type'] == 'pathway']
        
        for pathway in pathway_nodes:
            analysis = self.analyze_pathway_activity(pathway)
            
            if 'error' not in analysis:
                # Calculate z-score for pathway activity
                pathway_score = analysis['pathway_score']
                if abs(pathway_score) > threshold:
                    analysis['dysregulation_score'] = pathway_score
                    analysis['is_dysregulated'] = True
                    dysregulated_pathways.append(analysis)
        
        # Sort by dysregulation score
        dysregulated_pathways.sort(key=lambda x: abs(x['dysregulation_score']), reverse=True)
        
        logger.info(f"Identified {len(dysregulated_pathways)} dysregulated pathways")
        return dysregulated_pathways
    
    def create_pathway_visualization(self, pathway_name: str) -> go.Figure:
        """
        Create an interactive visualization of a pathway.
        
        Args:
            pathway_name: Name of the pathway to visualize
            
        Returns:
            Plotly figure object
        """
        if pathway_name not in self.pathway_network:
            raise ValueError(f"Pathway {pathway_name} not found in network")
        
        # Get subgraph for the pathway
        pathway_genes = [node for node in self.pathway_network.neighbors(pathway_name) 
                        if self.pathway_network.nodes[node]['type'] == 'gene']
        
        subgraph = self.pathway_network.subgraph([pathway_name] + pathway_genes)
        
        # Create layout
        pos = nx.spring_layout(subgraph, k=3, iterations=50)
        
        # Prepare edge traces
        edge_x = []
        edge_y = []
        for edge in subgraph.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=2, color='#888'),
            hoverinfo='none',
            mode='lines'
        )
        
        # Prepare node traces
        node_x = []
        node_y = []
        node_text = []
        node_colors = []
        
        for node in subgraph.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(node)
            
            if self.pathway_network.nodes[node]['type'] == 'pathway':
                node_colors.append('red')
            else:
                node_colors.append('lightblue')
        
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            text=node_text,
            textposition="middle center",
            marker=dict(
                size=20,
                color=node_colors,
                line=dict(width=2, color='black')
            )
        )
        
        # Create figure
        fig = go.Figure(data=[edge_trace, node_trace],
                       layout=go.Layout(
                           title=f'Pathway Network: {pathway_name}',
                           titlefont_size=16,
                           showlegend=False,
                           hovermode='closest',
                           margin=dict(b=20,l=5,r=5,t=40),
                           annotations=[ dict(
                               text="Interactive pathway visualization",
                               showarrow=False,
                               xref="paper", yref="paper",
                               x=0.005, y=-0.002,
                               xanchor='left', yanchor='bottom',
                               font=dict(color="gray", size=12)
                           )],
                           xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                           yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                       ))
        
        return fig
    
    def create_expression_heatmap(self, pathway_name: str) -> go.Figure:
        """
        Create a heatmap of gene expression for a pathway.
        
        Args:
            pathway_name: Name of the pathway
            
        Returns:
            Plotly heatmap figure
        """
        if self.gene_expression_data is None:
            raise ValueError("Gene expression data not loaded")
        
        # Get pathway genes
        pathway_genes = [node for node in self.pathway_network.neighbors(pathway_name) 
                        if self.pathway_network.nodes[node]['type'] == 'gene']
        
        # Filter expression data
        pathway_expression = self.gene_expression_data[
            self.gene_expression_data['gene_id'].isin(pathway_genes)
        ]
        
        if pathway_expression.empty:
            raise ValueError(f"No expression data found for pathway {pathway_name}")
        
        # Prepare data for heatmap
        expression_cols = pathway_expression.select_dtypes(include=[np.number]).columns
        heatmap_data = pathway_expression.set_index('gene_id')[expression_cols]
        
        # Create heatmap
        fig = px.imshow(
            heatmap_data,
            title=f'Gene Expression Heatmap: {pathway_name}',
            labels=dict(x="Samples", y="Genes", color="Expression Level"),
            color_continuous_scale='RdBu_r'
        )
        
        fig.update_layout(
            width=800,
            height=600,
            font=dict(size=12)
        )
        
        return fig
    
    def export_pathway_analysis(self, output_path: str, analysis_results: List[Dict[str, Any]]) -> None:
        """
        Export pathway analysis results to JSON file.
        
        Args:
            output_path: Path to save the results
            analysis_results: List of analysis results to export
        """
        try:
            with open(output_path, 'w') as f:
                json.dump(analysis_results, f, indent=2, default=str)
            logger.info(f"Exported pathway analysis to {output_path}")
        except Exception as e:
            logger.error(f"Error exporting analysis: {e}")
            raise
    
    def get_pathway_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all pathways in the network.
        
        Returns:
            Dictionary containing pathway summary statistics
        """
        pathway_nodes = [node for node in self.pathway_network.nodes() 
                        if self.pathway_network.nodes[node]['type'] == 'pathway']
        
        gene_nodes = [node for node in self.pathway_network.nodes() 
                     if self.pathway_network.nodes[node]['type'] == 'gene']
        
        summary = {
            'total_pathways': len(pathway_nodes),
            'total_genes': len(gene_nodes),
            'total_nodes': self.pathway_network.number_of_nodes(),
            'total_edges': self.pathway_network.number_of_edges(),
            'pathways': pathway_nodes,
            'network_density': nx.density(self.pathway_network)
        }
        
        return summary


def create_mock_pathway_data() -> Dict[str, List[str]]:
    """
    Create mock pathway data for testing and demonstration.
    
    Returns:
        Dictionary mapping pathway names to gene lists
    """
    return {
        'Glycolysis': ['HK1', 'HK2', 'PFKP', 'ALDOA', 'TPI1', 'GAPDH', 'PGK1', 'PGAM1', 'ENO1', 'PKM'],
        'TCA_Cycle': ['CS', 'ACO1', 'IDH1', 'IDH2', 'OGDH', 'SUCLA2', 'SDHA', 'FH', 'MDH1', 'MDH2'],
        'Oxidative_Phosphorylation': ['NDUFA1', 'NDUFA2', 'NDUFB1', 'SDHA', 'SDHB', 'UQCRC1', 'CYC1', 'COX4I1', 'ATP5A1', 'ATP5B'],
        'Fatty_Acid_Synthesis': ['ACACA', 'FASN', 'SCD', 'FADS1', 'FADS2', 'ELOVL1', 'ELOVL2', 'ELOVL3', 'ELOVL4', 'ELOVL5'],
        'Nucleotide_Synthesis': ['ADPRT', 'ADPRH', 'ADPRS', 'ADPRT2', 'ADPRT3', 'ADPRT4', 'ADPRT5', 'ADPRT6', 'ADPRT7', 'ADPRT8'],
        'Amino_Acid_Metabolism': ['GOT1', 'GOT2', 'GPT', 'GPT2', 'ALAT1', 'ALAT2', 'ALAT3', 'ALAT4', 'ALAT5', 'ALAT6'],
        'DNA_Repair': ['BRCA1', 'BRCA2', 'TP53', 'ATM', 'ATR', 'CHEK1', 'CHEK2', 'RAD51', 'RAD52', 'RAD54'],
        'Cell_Cycle': ['CCND1', 'CCND2', 'CCND3', 'CCNE1', 'CCNE2', 'CDK2', 'CDK4', 'CDK6', 'CDKN1A', 'CDKN1B']
    }


def main():
    """Main function for testing the pathway mapper."""
    # Create mapper instance
    mapper = MetabolicPathwayMapper()
    
    # Create mock pathway data
    pathway_data = create_mock_pathway_data()
    
    # Create pathway network
    network = mapper.create_pathway_network(pathway_data)
    
    # Get pathway summary
    summary = mapper.get_pathway_summary()
    print("Pathway Summary:")
    print(json.dumps(summary, indent=2))
    
    # Analyze a specific pathway
    glycolysis_analysis = mapper.analyze_pathway_activity('Glycolysis')
    print("\nGlycolysis Analysis:")
    print(json.dumps(glycolysis_analysis, indent=2, default=str))


if __name__ == "__main__":
    main()
