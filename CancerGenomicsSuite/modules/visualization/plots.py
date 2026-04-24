"""
Plots Module

Provides comprehensive plotting functionality for cancer genomics data visualization.
Supports various plot types including heatmaps, scatter plots, box plots, and specialized genomics plots.
"""

import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
import plotly.figure_factory as ff
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class PlotType(Enum):
    """Types of plots supported."""
    SCATTER = "scatter"
    LINE = "line"
    BAR = "bar"
    HISTOGRAM = "histogram"
    BOX = "box"
    VIOLIN = "violin"
    HEATMAP = "heatmap"
    VOLCANO = "volcano"
    MA_PLOT = "ma_plot"
    PCA = "pca"
    TSNE = "tsne"
    UMAP = "umap"
    MANHATTAN = "manhattan"
    QQ_PLOT = "qq_plot"
    SURVIVAL_CURVE = "survival_curve"
    GENE_EXPRESSION = "gene_expression"
    MUTATION_LANDSCAPE = "mutation_landscape"
    PATHWAY_ENRICHMENT = "pathway_enrichment"


@dataclass
class PlotConfig:
    """Configuration for plot generation."""
    title: str = ""
    x_label: str = ""
    y_label: str = ""
    width: int = 800
    height: int = 600
    theme: str = "default"
    color_palette: str = "viridis"
    show_legend: bool = True
    show_grid: bool = True
    interactive: bool = True
    save_format: str = "png"
    dpi: int = 300
    custom_colors: List[str] = field(default_factory=list)
    annotations: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PlotManager:
    """
    Manages plot creation and customization for genomics data.
    
    Features:
    - Multiple plot types for genomics data
    - Interactive and static plots
    - Customizable themes and colors
    - Export functionality
    - Statistical annotations
    - Publication-ready formatting
    """
    
    def __init__(self, default_theme: str = "default"):
        """
        Initialize PlotManager.
        
        Args:
            default_theme: Default theme to use for plots
        """
        self.default_theme = default_theme
        self.plot_cache = {}
        self.output_dir = Path("outputs/plots")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set default matplotlib style
        plt.style.use('default')
        sns.set_palette("husl")
    
    def create_plot(self, plot_type: PlotType, data: Union[pd.DataFrame, np.ndarray, Dict],
                   config: PlotConfig = None, **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        Create a plot of the specified type.
        
        Args:
            plot_type: Type of plot to create
            data: Data to plot
            config: Plot configuration
            **kwargs: Additional plot-specific parameters
            
        Returns:
            Plot figure object
        """
        if config is None:
            config = PlotConfig()
        
        # Apply theme
        self._apply_theme(config.theme)
        
        # Create plot based on type
        if plot_type == PlotType.SCATTER:
            return self._create_scatter_plot(data, config, **kwargs)
        elif plot_type == PlotType.HEATMAP:
            return self._create_heatmap(data, config, **kwargs)
        elif plot_type == PlotType.VOLCANO:
            return self._create_volcano_plot(data, config, **kwargs)
        elif plot_type == PlotType.MA_PLOT:
            return self._create_ma_plot(data, config, **kwargs)
        elif plot_type == PlotType.PCA:
            return self._create_pca_plot(data, config, **kwargs)
        elif plot_type == PlotType.MANHATTAN:
            return self._create_manhattan_plot(data, config, **kwargs)
        elif plot_type == PlotType.SURVIVAL_CURVE:
            return self._create_survival_curve(data, config, **kwargs)
        elif plot_type == PlotType.GENE_EXPRESSION:
            return self._create_gene_expression_plot(data, config, **kwargs)
        elif plot_type == PlotType.MUTATION_LANDSCAPE:
            return self._create_mutation_landscape(data, config, **kwargs)
        elif plot_type == PlotType.PATHWAY_ENRICHMENT:
            return self._create_pathway_enrichment_plot(data, config, **kwargs)
        else:
            return self._create_generic_plot(plot_type, data, config, **kwargs)
    
    def _apply_theme(self, theme: str):
        """Apply visualization theme."""
        if theme == "dark":
            plt.style.use('dark_background')
            sns.set_style("darkgrid")
        elif theme == "white":
            plt.style.use('default')
            sns.set_style("whitegrid")
        elif theme == "minimal":
            plt.style.use('default')
            sns.set_style("white")
        else:
            plt.style.use('default')
            sns.set_style("whitegrid")
    
    def _create_scatter_plot(self, data: pd.DataFrame, config: PlotConfig, **kwargs) -> go.Figure:
        """Create scatter plot."""
        x_col = kwargs.get('x', data.columns[0])
        y_col = kwargs.get('y', data.columns[1])
        color_col = kwargs.get('color')
        size_col = kwargs.get('size')
        
        fig = px.scatter(
            data, x=x_col, y=y_col, color=color_col, size=size_col,
            title=config.title,
            width=config.width,
            height=config.height,
            color_discrete_sequence=config.custom_colors if config.custom_colors else None
        )
        
        fig.update_layout(
            xaxis_title=config.x_label or x_col,
            yaxis_title=config.y_label or y_col,
            showlegend=config.show_legend,
            template="plotly_white" if config.theme == "white" else "plotly_dark" if config.theme == "dark" else "plotly"
        )
        
        return fig
    
    def _create_heatmap(self, data: pd.DataFrame, config: PlotConfig, **kwargs) -> go.Figure:
        """Create heatmap."""
        # Handle different data formats
        if isinstance(data, pd.DataFrame):
            if data.index.name and data.columns.name:
                # Correlation matrix or similar
                fig = go.Figure(data=go.Heatmap(
                    z=data.values,
                    x=data.columns,
                    y=data.index,
                    colorscale=config.color_palette,
                    showscale=True
                ))
            else:
                # Gene expression or similar matrix
                fig = go.Figure(data=go.Heatmap(
                    z=data.values,
                    x=data.columns,
                    y=data.index,
                    colorscale=config.color_palette,
                    showscale=True
                ))
        else:
            # NumPy array
            fig = go.Figure(data=go.Heatmap(
                z=data,
                colorscale=config.color_palette,
                showscale=True
            ))
        
        fig.update_layout(
            title=config.title,
            width=config.width,
            height=config.height,
            template="plotly_white" if config.theme == "white" else "plotly_dark" if config.theme == "dark" else "plotly"
        )
        
        return fig
    
    def _create_volcano_plot(self, data: pd.DataFrame, config: PlotConfig, **kwargs) -> go.Figure:
        """Create volcano plot for differential expression analysis."""
        log2fc_col = kwargs.get('log2fc', 'log2FoldChange')
        pvalue_col = kwargs.get('pvalue', 'pvalue')
        gene_col = kwargs.get('gene', 'gene_id')
        
        # Calculate -log10(pvalue)
        data['neg_log10_pvalue'] = -np.log10(data[pvalue_col] + 1e-300)
        
        # Determine significance
        fc_threshold = kwargs.get('fc_threshold', 1.0)
        pvalue_threshold = kwargs.get('pvalue_threshold', 0.05)
        
        data['significant'] = (
            (np.abs(data[log2fc_col]) > fc_threshold) & 
            (data[pvalue_col] < pvalue_threshold)
        )
        
        fig = px.scatter(
            data, x=log2fc_col, y='neg_log10_pvalue',
            color='significant',
            hover_data=[gene_col] if gene_col in data.columns else None,
            title=config.title or "Volcano Plot",
            width=config.width,
            height=config.height,
            color_discrete_map={True: 'red', False: 'gray'}
        )
        
        # Add threshold lines
        fig.add_hline(y=-np.log10(pvalue_threshold), line_dash="dash", line_color="black")
        fig.add_vline(x=fc_threshold, line_dash="dash", line_color="black")
        fig.add_vline(x=-fc_threshold, line_dash="dash", line_color="black")
        
        fig.update_layout(
            xaxis_title=config.x_label or "Log2 Fold Change",
            yaxis_title=config.y_label or "-Log10 P-value",
            template="plotly_white" if config.theme == "white" else "plotly_dark" if config.theme == "dark" else "plotly"
        )
        
        return fig
    
    def _create_ma_plot(self, data: pd.DataFrame, config: PlotConfig, **kwargs) -> go.Figure:
        """Create MA plot for differential expression analysis."""
        mean_col = kwargs.get('mean', 'baseMean')
        log2fc_col = kwargs.get('log2fc', 'log2FoldChange')
        gene_col = kwargs.get('gene', 'gene_id')
        
        # Calculate log2(mean)
        data['log2_mean'] = np.log2(data[mean_col] + 1)
        
        fig = px.scatter(
            data, x='log2_mean', y=log2fc_col,
            hover_data=[gene_col] if gene_col in data.columns else None,
            title=config.title or "MA Plot",
            width=config.width,
            height=config.height
        )
        
        # Add horizontal line at y=0
        fig.add_hline(y=0, line_dash="dash", line_color="red")
        
        fig.update_layout(
            xaxis_title=config.x_label or "Log2 Mean Expression",
            yaxis_title=config.y_label or "Log2 Fold Change",
            template="plotly_white" if config.theme == "white" else "plotly_dark" if config.theme == "dark" else "plotly"
        )
        
        return fig
    
    def _create_pca_plot(self, data: pd.DataFrame, config: PlotConfig, **kwargs) -> go.Figure:
        """Create PCA plot."""
        from sklearn.decomposition import PCA
        
        # Perform PCA
        pca = PCA(n_components=2)
        pca_result = pca.fit_transform(data)
        
        # Create DataFrame for plotting
        pca_df = pd.DataFrame({
            'PC1': pca_result[:, 0],
            'PC2': pca_result[:, 1]
        })
        
        # Add sample labels if available
        if 'sample_labels' in kwargs:
            pca_df['sample_labels'] = kwargs['sample_labels']
        
        fig = px.scatter(
            pca_df, x='PC1', y='PC2',
            color='sample_labels' if 'sample_labels' in kwargs else None,
            title=config.title or "PCA Plot",
            width=config.width,
            height=config.height
        )
        
        # Add explained variance to axis labels
        pc1_var = pca.explained_variance_ratio_[0] * 100
        pc2_var = pca.explained_variance_ratio_[1] * 100
        
        fig.update_layout(
            xaxis_title=f"PC1 ({pc1_var:.1f}% variance)",
            yaxis_title=f"PC2 ({pc2_var:.1f}% variance)",
            template="plotly_white" if config.theme == "white" else "plotly_dark" if config.theme == "dark" else "plotly"
        )
        
        return fig
    
    def _create_manhattan_plot(self, data: pd.DataFrame, config: PlotConfig, **kwargs) -> go.Figure:
        """Create Manhattan plot for GWAS results."""
        chr_col = kwargs.get('chromosome', 'chr')
        pos_col = kwargs.get('position', 'pos')
        pvalue_col = kwargs.get('pvalue', 'pvalue')
        
        # Calculate -log10(pvalue)
        data['neg_log10_pvalue'] = -np.log10(data[pvalue_col] + 1e-300)
        
        # Create cumulative position
        data = data.sort_values([chr_col, pos_col])
        data['cumulative_pos'] = 0
        cumulative_pos = 0
        chr_positions = {}
        
        for chr_id in data[chr_col].unique():
            chr_positions[chr_id] = cumulative_pos
            chr_data = data[data[chr_col] == chr_id]
            data.loc[data[chr_col] == chr_id, 'cumulative_pos'] = chr_data[pos_col] + cumulative_pos
            cumulative_pos += chr_data[pos_col].max()
        
        fig = px.scatter(
            data, x='cumulative_pos', y='neg_log10_pvalue',
            color=chr_col,
            title=config.title or "Manhattan Plot",
            width=config.width,
            height=config.height
        )
        
        # Add significance threshold line
        significance_threshold = kwargs.get('significance_threshold', 5e-8)
        fig.add_hline(y=-np.log10(significance_threshold), line_dash="dash", line_color="red")
        
        # Update x-axis to show chromosome labels
        fig.update_layout(
            xaxis_title="Chromosome",
            yaxis_title="-Log10 P-value",
            template="plotly_white" if config.theme == "white" else "plotly_dark" if config.theme == "dark" else "plotly"
        )
        
        return fig
    
    def _create_survival_curve(self, data: pd.DataFrame, config: PlotConfig, **kwargs) -> go.Figure:
        """Create survival curve plot."""
        time_col = kwargs.get('time', 'time')
        event_col = kwargs.get('event', 'event')
        group_col = kwargs.get('group', 'group')
        
        # This is a simplified version - in practice, you'd use lifelines or similar
        fig = go.Figure()
        
        for group in data[group_col].unique():
            group_data = data[data[group_col] == group]
            # Calculate survival probabilities (simplified)
            survival_prob = np.exp(-group_data[time_col] / group_data[time_col].mean())
            
            fig.add_trace(go.Scatter(
                x=group_data[time_col],
                y=survival_prob,
                mode='lines',
                name=group,
                line=dict(width=3)
            ))
        
        fig.update_layout(
            title=config.title or "Survival Curves",
            xaxis_title=config.x_label or "Time",
            yaxis_title=config.y_label or "Survival Probability",
            width=config.width,
            height=config.height,
            template="plotly_white" if config.theme == "white" else "plotly_dark" if config.theme == "dark" else "plotly"
        )
        
        return fig
    
    def _create_gene_expression_plot(self, data: pd.DataFrame, config: PlotConfig, **kwargs) -> go.Figure:
        """Create gene expression plot (box plot or violin plot)."""
        plot_style = kwargs.get('style', 'box')  # 'box' or 'violin'
        
        if plot_style == 'violin':
            fig = px.violin(
                data, y=data.columns[0],
                title=config.title or "Gene Expression Distribution",
                width=config.width,
                height=config.height
            )
        else:
            fig = px.box(
                data, y=data.columns[0],
                title=config.title or "Gene Expression Distribution",
                width=config.width,
                height=config.height
            )
        
        fig.update_layout(
            yaxis_title=config.y_label or "Expression Level",
            template="plotly_white" if config.theme == "white" else "plotly_dark" if config.theme == "dark" else "plotly"
        )
        
        return fig
    
    def _create_mutation_landscape(self, data: pd.DataFrame, config: PlotConfig, **kwargs) -> go.Figure:
        """Create mutation landscape plot."""
        sample_col = kwargs.get('sample', 'sample')
        gene_col = kwargs.get('gene', 'gene')
        mutation_col = kwargs.get('mutation', 'mutation_type')
        
        # Create pivot table for heatmap
        pivot_data = data.pivot_table(
            index=gene_col, 
            columns=sample_col, 
            values=mutation_col, 
            aggfunc='first',
            fill_value='No Mutation'
        )
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot_data.values,
            x=pivot_data.columns,
            y=pivot_data.index,
            colorscale='Viridis',
            showscale=True
        ))
        
        fig.update_layout(
            title=config.title or "Mutation Landscape",
            xaxis_title="Samples",
            yaxis_title="Genes",
            width=config.width,
            height=config.height,
            template="plotly_white" if config.theme == "white" else "plotly_dark" if config.theme == "dark" else "plotly"
        )
        
        return fig
    
    def _create_pathway_enrichment_plot(self, data: pd.DataFrame, config: PlotConfig, **kwargs) -> go.Figure:
        """Create pathway enrichment plot."""
        pathway_col = kwargs.get('pathway', 'pathway')
        pvalue_col = kwargs.get('pvalue', 'pvalue')
        count_col = kwargs.get('count', 'count')
        
        # Sort by p-value
        data = data.sort_values(pvalue_col)
        
        # Calculate -log10(pvalue)
        data['neg_log10_pvalue'] = -np.log10(data[pvalue_col] + 1e-300)
        
        fig = px.bar(
            data.head(20),  # Top 20 pathways
            x='neg_log10_pvalue',
            y=pathway_col,
            orientation='h',
            title=config.title or "Pathway Enrichment",
            width=config.width,
            height=config.height
        )
        
        fig.update_layout(
            xaxis_title="-Log10 P-value",
            yaxis_title="Pathway",
            template="plotly_white" if config.theme == "white" else "plotly_dark" if config.theme == "dark" else "plotly"
        )
        
        return fig
    
    def _create_generic_plot(self, plot_type: PlotType, data: Union[pd.DataFrame, np.ndarray], 
                           config: PlotConfig, **kwargs) -> go.Figure:
        """Create generic plot for unsupported types."""
        logger.warning(f"Generic plot creation for {plot_type.value}")
        
        if isinstance(data, pd.DataFrame):
            # Use first two columns for generic plot
            x_col, y_col = data.columns[0], data.columns[1]
            fig = px.scatter(data, x=x_col, y=y_col, title=config.title)
        else:
            # NumPy array - create simple scatter
            fig = go.Figure(data=go.Scatter(y=data.flatten(), mode='markers'))
        
        fig.update_layout(
            width=config.width,
            height=config.height,
            template="plotly_white" if config.theme == "white" else "plotly_dark" if config.theme == "dark" else "plotly"
        )
        
        return fig
    
    def save_plot(self, figure: Union[go.Figure, plt.Figure], filename: str, 
                  config: PlotConfig = None) -> str:
        """
        Save plot to file.
        
        Args:
            figure: Plot figure to save
            filename: Output filename
            config: Plot configuration
            
        Returns:
            str: Path to saved file
        """
        if config is None:
            config = PlotConfig()
        
        output_path = self.output_dir / f"{filename}.{config.save_format}"
        
        if isinstance(figure, go.Figure):
            # Plotly figure
            if config.save_format == 'html':
                figure.write_html(str(output_path))
            elif config.save_format == 'json':
                figure.write_json(str(output_path))
            else:
                figure.write_image(str(output_path), width=config.width, height=config.height, scale=2)
        else:
            # Matplotlib figure
            figure.savefig(str(output_path), dpi=config.dpi, bbox_inches='tight')
        
        logger.info(f"Plot saved to {output_path}")
        return str(output_path)
    
    def create_plot_grid(self, plots: List[Tuple[PlotType, Union[pd.DataFrame, np.ndarray], PlotConfig]], 
                        grid_shape: Tuple[int, int] = None) -> go.Figure:
        """
        Create a grid of subplots.
        
        Args:
            plots: List of (plot_type, data, config) tuples
            grid_shape: (rows, cols) for subplot grid
            
        Returns:
            go.Figure: Combined subplot figure
        """
        if grid_shape is None:
            n_plots = len(plots)
            cols = int(np.ceil(np.sqrt(n_plots)))
            rows = int(np.ceil(n_plots / cols))
        else:
            rows, cols = grid_shape
        
        fig = make_subplots(
            rows=rows, cols=cols,
            subplot_titles=[config.title for _, _, config in plots]
        )
        
        for i, (plot_type, data, config) in enumerate(plots):
            row = (i // cols) + 1
            col = (i % cols) + 1
            
            # Create individual plot
            individual_fig = self.create_plot(plot_type, data, config)
            
            # Add to subplot (simplified - would need more complex logic for different plot types)
            if hasattr(individual_fig, 'data'):
                for trace in individual_fig.data:
                    fig.add_trace(trace, row=row, col=col)
        
        fig.update_layout(
            height=600 * rows,
            width=800 * cols,
            showlegend=False
        )
        
        return fig
    
    def get_plot_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Get statistical summary for plotting.
        
        Args:
            data: Data to analyze
            
        Returns:
            Dict containing statistical information
        """
        stats = {
            'shape': data.shape,
            'columns': list(data.columns),
            'dtypes': data.dtypes.to_dict(),
            'missing_values': data.isnull().sum().to_dict(),
            'numeric_summary': data.describe().to_dict() if len(data.select_dtypes(include=[np.number]).columns) > 0 else {},
            'categorical_summary': data.select_dtypes(include=['object']).describe().to_dict() if len(data.select_dtypes(include=['object']).columns) > 0 else {}
        }
        
        return stats
