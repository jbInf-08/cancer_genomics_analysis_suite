#!/usr/bin/env python3
"""
Graph Visualizer

This module provides graph visualization capabilities for cancer genomics data
using various visualization libraries.
"""

import logging
from typing import Dict, List, Optional, Any, Union, Tuple
import pandas as pd
import numpy as np

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    from matplotlib.patches import Circle
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.express as px
    MATPLOTLIB_AVAILABLE = True
    PLOTLY_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    PLOTLY_AVAILABLE = False
    logging.warning("Visualization libraries not available. Install matplotlib and plotly packages.")

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

logger = logging.getLogger(__name__)


class GraphVisualizer:
    """
    Graph visualizer for cancer genomics data.
    
    Provides functionality to:
    - Visualize gene networks
    - Create interactive plots
    - Generate publication-ready figures
    - Export visualizations
    """
    
    def __init__(self, style: str = "default"):
        """
        Initialize graph visualizer.
        
        Args:
            style: Visualization style ("default", "publication", "interactive")
        """
        if not MATPLOTLIB_AVAILABLE and not PLOTLY_AVAILABLE:
            raise ImportError("Visualization libraries not available. Install matplotlib and plotly packages.")
        
        self.style = style
        self.setup_style()
    
    def setup_style(self):
        """Setup visualization style."""
        if MATPLOTLIB_AVAILABLE:
            if self.style == "publication":
                plt.style.use('seaborn-v0_8-whitegrid')
                plt.rcParams.update({
                    'font.size': 12,
                    'axes.titlesize': 14,
                    'axes.labelsize': 12,
                    'xtick.labelsize': 10,
                    'ytick.labelsize': 10,
                    'legend.fontsize': 10,
                    'figure.titlesize': 16
                })
            else:
                plt.style.use('default')
    
    def visualize_gene_network(
        self,
        graph: 'nx.Graph',
        layout: str = "spring",
        node_size_attr: Optional[str] = None,
        node_color_attr: Optional[str] = None,
        edge_width_attr: Optional[str] = None,
        title: str = "Gene Network",
        figsize: Tuple[int, int] = (12, 8),
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Visualize a gene network using matplotlib.
        
        Args:
            graph: NetworkX graph
            layout: Layout algorithm ("spring", "circular", "random", "kamada_kawai")
            node_size_attr: Node attribute for size mapping
            node_color_attr: Node attribute for color mapping
            edge_width_attr: Edge attribute for width mapping
            title: Plot title
            figsize: Figure size
            save_path: Path to save the plot
            
        Returns:
            Matplotlib figure
        """
        if not MATPLOTLIB_AVAILABLE or not NETWORKX_AVAILABLE:
            raise ImportError("Required libraries not available")
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Choose layout
        if layout == "spring":
            pos = nx.spring_layout(graph, k=1, iterations=50)
        elif layout == "circular":
            pos = nx.circular_layout(graph)
        elif layout == "random":
            pos = nx.random_layout(graph)
        elif layout == "kamada_kawai":
            pos = nx.kamada_kawai_layout(graph)
        else:
            pos = nx.spring_layout(graph)
        
        # Prepare node sizes
        if node_size_attr and node_size_attr in next(iter(graph.nodes(data=True)))[1]:
            node_sizes = [graph.nodes[node].get(node_size_attr, 100) for node in graph.nodes()]
            # Normalize sizes
            node_sizes = np.array(node_sizes)
            node_sizes = (node_sizes - node_sizes.min()) / (node_sizes.max() - node_sizes.min()) * 500 + 50
        else:
            node_sizes = 100
        
        # Prepare node colors
        if node_color_attr and node_color_attr in next(iter(graph.nodes(data=True)))[1]:
            node_colors = [graph.nodes[node].get(node_color_attr, 0) for node in graph.nodes()]
        else:
            node_colors = 'lightblue'
        
        # Prepare edge widths
        if edge_width_attr and edge_width_attr in next(iter(graph.edges(data=True)))[2]:
            edge_widths = [graph.edges[edge].get(edge_width_attr, 1) for edge in graph.edges()]
            # Normalize widths
            edge_widths = np.array(edge_widths)
            if edge_widths.max() > edge_widths.min():
                edge_widths = (edge_widths - edge_widths.min()) / (edge_widths.max() - edge_widths.min()) * 3 + 0.5
        else:
            edge_widths = 1
        
        # Draw network
        nx.draw_networkx_nodes(
            graph, pos,
            node_size=node_sizes,
            node_color=node_colors,
            alpha=0.7,
            ax=ax
        )
        
        nx.draw_networkx_edges(
            graph, pos,
            width=edge_widths,
            alpha=0.5,
            edge_color='gray',
            ax=ax
        )
        
        # Draw labels for high-degree nodes
        degrees = dict(graph.degree())
        high_degree_nodes = [node for node, degree in degrees.items() if degree > np.percentile(list(degrees.values()), 90)]
        
        nx.draw_networkx_labels(
            graph, pos,
            labels={node: node for node in high_degree_nodes},
            font_size=8,
            ax=ax
        )
        
        ax.set_title(title)
        ax.axis('off')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def create_interactive_network(
        self,
        graph: 'nx.Graph',
        layout: str = "spring",
        node_size_attr: Optional[str] = None,
        node_color_attr: Optional[str] = None,
        title: str = "Interactive Gene Network"
    ) -> go.Figure:
        """
        Create an interactive network visualization using Plotly.
        
        Args:
            graph: NetworkX graph
            layout: Layout algorithm
            node_size_attr: Node attribute for size mapping
            node_color_attr: Node attribute for color mapping
            title: Plot title
            
        Returns:
            Plotly figure
        """
        if not PLOTLY_AVAILABLE or not NETWORKX_AVAILABLE:
            raise ImportError("Required libraries not available")
        
        # Choose layout
        if layout == "spring":
            pos = nx.spring_layout(graph, k=1, iterations=50)
        elif layout == "circular":
            pos = nx.circular_layout(graph)
        elif layout == "random":
            pos = nx.random_layout(graph)
        elif layout == "kamada_kawai":
            pos = nx.kamada_kawai_layout(graph)
        else:
            pos = nx.spring_layout(graph)
        
        # Prepare node data
        node_x = []
        node_y = []
        node_text = []
        node_sizes = []
        node_colors = []
        
        for node in graph.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            
            # Node text
            node_attrs = graph.nodes[node]
            text = f"<b>{node}</b><br>"
            for attr, value in node_attrs.items():
                text += f"{attr}: {value}<br>"
            node_text.append(text)
            
            # Node size
            if node_size_attr and node_size_attr in node_attrs:
                size = node_attrs[node_size_attr]
                node_sizes.append(max(10, min(50, size * 5)))
            else:
                node_sizes.append(20)
            
            # Node color
            if node_color_attr and node_color_attr in node_attrs:
                node_colors.append(node_attrs[node_color_attr])
            else:
                node_colors.append(0)
        
        # Prepare edge data
        edge_x = []
        edge_y = []
        edge_info = []
        
        for edge in graph.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            
            # Edge info
            edge_attrs = graph.edges[edge]
            info = f"<b>{edge[0]} - {edge[1]}</b><br>"
            for attr, value in edge_attrs.items():
                info += f"{attr}: {value}<br>"
            edge_info.append(info)
        
        # Create figure
        fig = go.Figure()
        
        # Add edges
        fig.add_trace(go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines',
            showlegend=False
        ))
        
        # Add nodes
        fig.add_trace(go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            hovertext=node_text,
            text=[node for node in graph.nodes()],
            textposition="middle center",
            marker=dict(
                size=node_sizes,
                color=node_colors,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title=node_color_attr or "Node Color"),
                line=dict(width=2, color='black')
            ),
            showlegend=False
        ))
        
        # Update layout
        fig.update_layout(
            title=title,
            titlefont_size=16,
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20,l=5,r=5,t=40),
            annotations=[ dict(
                text="Interactive network visualization",
                showarrow=False,
                xref="paper", yref="paper",
                x=0.005, y=-0.002,
                xanchor='left', yanchor='bottom',
                font=dict(color='gray', size=12)
            )],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
        
        return fig
    
    def plot_centrality_analysis(
        self,
        centrality_data: Dict[str, Dict[str, float]],
        top_k: int = 20,
        figsize: Tuple[int, int] = (15, 10),
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Plot centrality analysis results.
        
        Args:
            centrality_data: Dictionary with centrality measures
            top_k: Number of top genes to show
            figsize: Figure size
            save_path: Path to save the plot
            
        Returns:
            Matplotlib figure
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("Matplotlib not available")
        
        # Prepare data
        genes = list(centrality_data.keys())
        centrality_types = list(next(iter(centrality_data.values())).keys())
        
        # Create subplots
        fig, axes = plt.subplots(2, 2, figsize=figsize)
        axes = axes.flatten()
        
        for i, centrality_type in enumerate(centrality_types):
            if i >= 4:
                break
            
            # Get top genes for this centrality measure
            gene_scores = [(gene, centrality_data[gene][centrality_type]) for gene in genes]
            gene_scores.sort(key=lambda x: x[1], reverse=True)
            top_genes = gene_scores[:top_k]
            
            # Plot
            genes_plot = [item[0] for item in top_genes]
            scores_plot = [item[1] for item in top_genes]
            
            axes[i].barh(genes_plot, scores_plot)
            axes[i].set_title(f'Top {top_k} Genes by {centrality_type.replace("_", " ").title()}')
            axes[i].set_xlabel(centrality_type.replace("_", " ").title())
            axes[i].invert_yaxis()
        
        # Hide unused subplots
        for i in range(len(centrality_types), 4):
            axes[i].set_visible(False)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_community_structure(
        self,
        graph: 'nx.Graph',
        communities: Dict[str, int],
        layout: str = "spring",
        figsize: Tuple[int, int] = (12, 8),
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Plot community structure of the network.
        
        Args:
            graph: NetworkX graph
            communities: Dictionary mapping nodes to community IDs
            layout: Layout algorithm
            figsize: Figure size
            save_path: Path to save the plot
            
        Returns:
            Matplotlib figure
        """
        if not MATPLOTLIB_AVAILABLE or not NETWORKX_AVAILABLE:
            raise ImportError("Required libraries not available")
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Choose layout
        if layout == "spring":
            pos = nx.spring_layout(graph, k=1, iterations=50)
        elif layout == "circular":
            pos = nx.circular_layout(graph)
        else:
            pos = nx.spring_layout(graph)
        
        # Color nodes by community
        num_communities = len(set(communities.values()))
        colors = plt.cm.Set3(np.linspace(0, 1, num_communities))
        
        for community_id in range(num_communities):
            community_nodes = [node for node, comm in communities.items() if comm == community_id]
            
            nx.draw_networkx_nodes(
                graph, pos,
                nodelist=community_nodes,
                node_color=[colors[community_id]],
                node_size=100,
                alpha=0.7,
                ax=ax
            )
        
        # Draw edges
        nx.draw_networkx_edges(
            graph, pos,
            alpha=0.5,
            edge_color='gray',
            ax=ax
        )
        
        # Draw labels for high-degree nodes
        degrees = dict(graph.degree())
        high_degree_nodes = [node for node, degree in degrees.items() if degree > np.percentile(list(degrees.values()), 90)]
        
        nx.draw_networkx_labels(
            graph, pos,
            labels={node: node for node in high_degree_nodes},
            font_size=8,
            ax=ax
        )
        
        ax.set_title(f"Community Structure ({num_communities} communities)")
        ax.axis('off')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_pathway_enrichment(
        self,
        enrichment_data: pd.DataFrame,
        top_k: int = 20,
        figsize: Tuple[int, int] = (12, 8),
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Plot pathway enrichment results.
        
        Args:
            enrichment_data: DataFrame with enrichment results
            top_k: Number of top pathways to show
            figsize: Figure size
            save_path: Path to save the plot
            
        Returns:
            Matplotlib figure
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("Matplotlib not available")
        
        # Get top pathways
        top_pathways = enrichment_data.head(top_k)
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
        
        # Plot 1: Fold enrichment
        y_pos = np.arange(len(top_pathways))
        ax1.barh(y_pos, top_pathways['fold_enrichment'])
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(top_pathways['pathway_name'], fontsize=8)
        ax1.set_xlabel('Fold Enrichment')
        ax1.set_title('Top Pathways by Fold Enrichment')
        ax1.invert_yaxis()
        
        # Plot 2: -log10(p-value)
        p_values = -np.log10(top_pathways['p_value'])
        ax2.barh(y_pos, p_values)
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(top_pathways['pathway_name'], fontsize=8)
        ax2.set_xlabel('-log10(p-value)')
        ax2.set_title('Top Pathways by Significance')
        ax2.invert_yaxis()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def create_dashboard(
        self,
        graph: 'nx.Graph',
        centrality_data: Dict[str, Dict[str, float]],
        communities: Dict[str, int],
        enrichment_data: Optional[pd.DataFrame] = None
    ) -> go.Figure:
        """
        Create an interactive dashboard with multiple visualizations.
        
        Args:
            graph: NetworkX graph
            centrality_data: Centrality analysis results
            communities: Community detection results
            enrichment_data: Optional pathway enrichment data
            
        Returns:
            Plotly figure with subplots
        """
        if not PLOTLY_AVAILABLE:
            raise ImportError("Plotly not available")
        
        # Create subplots
        if enrichment_data is not None:
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Network Visualization', 'Centrality Analysis', 
                              'Community Structure', 'Pathway Enrichment'),
                specs=[[{"type": "scatter"}, {"type": "bar"}],
                       [{"type": "scatter"}, {"type": "bar"}]]
            )
        else:
            fig = make_subplots(
                rows=1, cols=3,
                subplot_titles=('Network Visualization', 'Centrality Analysis', 'Community Structure'),
                specs=[[{"type": "scatter"}, {"type": "bar"}, {"type": "scatter"}]]
            )
        
        # Network visualization (placeholder - would need actual network coordinates)
        fig.add_trace(
            go.Scatter(x=[0, 1], y=[0, 1], mode='markers', name='Network'),
            row=1, col=1
        )
        
        # Centrality analysis
        if centrality_data:
            genes = list(centrality_data.keys())[:10]  # Top 10 genes
            degree_centrality = [centrality_data[gene]['degree_centrality'] for gene in genes]
            
            fig.add_trace(
                go.Bar(x=genes, y=degree_centrality, name='Degree Centrality'),
                row=1, col=2
            )
        
        # Community structure (placeholder)
        fig.add_trace(
            go.Scatter(x=[0, 1], y=[0, 1], mode='markers', name='Communities'),
            row=2 if enrichment_data else 1, col=3
        )
        
        # Pathway enrichment
        if enrichment_data is not None:
            top_pathways = enrichment_data.head(10)
            fig.add_trace(
                go.Bar(x=top_pathways['pathway_name'], y=top_pathways['fold_enrichment'], 
                      name='Fold Enrichment'),
                row=2, col=2
            )
        
        # Update layout
        fig.update_layout(
            title_text="Cancer Genomics Analysis Dashboard",
            showlegend=False,
            height=800
        )
        
        return fig
    
    def export_visualization(self, fig: Union[plt.Figure, go.Figure], output_path: str, format: str = "png"):
        """
        Export visualization to file.
        
        Args:
            fig: Matplotlib or Plotly figure
            output_path: Output file path
            format: Export format ("png", "pdf", "svg", "html")
        """
        if isinstance(fig, plt.Figure):
            if format == "html":
                raise ValueError("HTML export not supported for matplotlib figures")
            fig.savefig(output_path, format=format, dpi=300, bbox_inches='tight')
        elif isinstance(fig, go.Figure):
            if format == "html":
                fig.write_html(output_path)
            else:
                fig.write_image(output_path, format=format, width=1200, height=800)
        
        logger.info(f"Visualization exported to {output_path}")
