"""
Gene Expression Analysis Callbacks

This module contains all Dash callbacks related to gene expression analysis,
including data visualization, statistical analysis, and interactive plots.

Features:
- Gene expression data loading and filtering
- Interactive scatter plots and heatmaps
- Statistical analysis and comparisons
- Data export and download functionality
- Real-time data updates and filtering
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context, no_update
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import logging

# Import database models and utilities
from ...orm.models import GeneExpression, DataFile
from ...orm import db

logger = logging.getLogger(__name__)


def register_gene_expression_callbacks(app):
    """
    Register all gene expression related callbacks with the Dash app.
    
    Args:
        app: Dash application instance
    """
    
    @app.callback(
        [Output('gene-expression-plot', 'figure'),
         Output('gene-expression-stats', 'children'),
         Output('gene-expression-loading', 'children')],
        [Input('gene-expression-gene-select', 'value'),
         Input('gene-expression-condition-select', 'value'),
         Input('gene-expression-plot-type', 'value'),
         Input('gene-expression-refresh', 'n_clicks')],
        [State('gene-expression-sample-filter', 'value')]
    )
    def update_gene_expression_plot(selected_genes, selected_conditions, plot_type, refresh_clicks, sample_filter):
        """
        Update gene expression plot based on user selections.
        
        Args:
            selected_genes: List of selected gene symbols
            selected_conditions: List of selected conditions
            plot_type: Type of plot to display (scatter, box, heatmap)
            refresh_clicks: Number of refresh button clicks
            sample_filter: Sample ID filter
            
        Returns:
            Tuple of (figure, stats_html, loading_component)
        """
        try:
            # Get gene expression data
            query = GeneExpression.query
            
            if selected_genes:
                query = query.filter(GeneExpression.gene_symbol.in_(selected_genes))
            
            if selected_conditions:
                query = query.filter(GeneExpression.condition.in_(selected_conditions))
            
            if sample_filter:
                query = query.filter(GeneExpression.sample_id.like(f'%{sample_filter}%'))
            
            data = query.all()
            
            if not data:
                empty_fig = go.Figure()
                empty_fig.add_annotation(
                    text="No data available for selected criteria",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
                return empty_fig, "No data available", no_update
            
            # Convert to DataFrame
            df = pd.DataFrame([record.to_dict() for record in data])
            
            # Create plot based on type
            if plot_type == 'scatter':
                fig = create_scatter_plot(df)
            elif plot_type == 'box':
                fig = create_box_plot(df)
            elif plot_type == 'heatmap':
                fig = create_heatmap(df)
            else:
                fig = create_scatter_plot(df)
            
            # Generate statistics
            stats_html = generate_expression_stats(df)
            
            return fig, stats_html, no_update
            
        except Exception as e:
            logger.error(f"Error updating gene expression plot: {e}")
            error_fig = go.Figure()
            error_fig.add_annotation(
                text=f"Error loading data: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return error_fig, f"Error: {str(e)}", no_update
    
    @app.callback(
        Output('gene-expression-gene-select', 'options'),
        [Input('gene-expression-refresh', 'n_clicks')]
    )
    def update_gene_options(refresh_clicks):
        """
        Update available gene options from database.
        
        Args:
            refresh_clicks: Number of refresh button clicks
            
        Returns:
            List of gene options for dropdown
        """
        try:
            genes = db.session.query(GeneExpression.gene_symbol).distinct().all()
            return [{'label': gene[0], 'value': gene[0]} for gene in genes]
        except Exception as e:
            logger.error(f"Error loading gene options: {e}")
            return []
    
    @app.callback(
        Output('gene-expression-condition-select', 'options'),
        [Input('gene-expression-refresh', 'n_clicks')]
    )
    def update_condition_options(refresh_clicks):
        """
        Update available condition options from database.
        
        Args:
            refresh_clicks: Number of refresh button clicks
            
        Returns:
            List of condition options for dropdown
        """
        try:
            conditions = db.session.query(GeneExpression.condition).distinct().filter(
                GeneExpression.condition.isnot(None)
            ).all()
            return [{'label': cond[0], 'value': cond[0]} for cond in conditions]
        except Exception as e:
            logger.error(f"Error loading condition options: {e}")
            return []
    
    @app.callback(
        [Output('gene-expression-download-data', 'data'),
         Output('gene-expression-download-trigger', 'children')],
        [Input('gene-expression-download-btn', 'n_clicks')],
        [State('gene-expression-gene-select', 'value'),
         State('gene-expression-condition-select', 'value'),
         State('gene-expression-sample-filter', 'value')]
    )
    def download_gene_expression_data(n_clicks, selected_genes, selected_conditions, sample_filter):
        """
        Download gene expression data as CSV.
        
        Args:
            n_clicks: Number of download button clicks
            selected_genes: List of selected gene symbols
            selected_conditions: List of selected conditions
            sample_filter: Sample ID filter
            
        Returns:
            Tuple of (download_data, trigger_children)
        """
        if not n_clicks:
            return no_update, no_update
        
        try:
            # Get filtered data
            query = GeneExpression.query
            
            if selected_genes:
                query = query.filter(GeneExpression.gene_symbol.in_(selected_genes))
            
            if selected_conditions:
                query = query.filter(GeneExpression.condition.in_(selected_conditions))
            
            if sample_filter:
                query = query.filter(GeneExpression.sample_id.like(f'%{sample_filter}%'))
            
            data = query.all()
            df = pd.DataFrame([record.to_dict() for record in data])
            
            # Convert to CSV
            csv_string = df.to_csv(index=False)
            
            return dict(content=csv_string, filename="gene_expression_data.csv"), no_update
            
        except Exception as e:
            logger.error(f"Error downloading gene expression data: {e}")
            return no_update, f"Error: {str(e)}"
    
    @app.callback(
        Output('gene-expression-sample-info', 'children'),
        [Input('gene-expression-plot', 'clickData')]
    )
    def display_sample_info(click_data):
        """
        Display detailed information about clicked sample.
        
        Args:
            click_data: Data from plot click event
            
        Returns:
            HTML content with sample information
        """
        if not click_data:
            return "Click on a data point to see sample details"
        
        try:
            point = click_data['points'][0]
            sample_id = point.get('customdata', {}).get('sample_id', 'Unknown')
            
            # Get detailed sample information
            sample_data = GeneExpression.query.filter_by(sample_id=sample_id).first()
            
            if sample_data:
                return html.Div([
                    html.H4(f"Sample: {sample_id}"),
                    html.P(f"Gene: {sample_data.gene_symbol}"),
                    html.P(f"Expression Value: {sample_data.expression_value}"),
                    html.P(f"Condition: {sample_data.condition or 'N/A'}"),
                    html.P(f"Tissue Type: {sample_data.tissue_type or 'N/A'}"),
                    html.P(f"Quality Score: {sample_data.quality_score or 'N/A'}")
                ])
            else:
                return f"No detailed information available for sample {sample_id}"
                
        except Exception as e:
            logger.error(f"Error displaying sample info: {e}")
            return f"Error loading sample information: {str(e)}"


def create_scatter_plot(df: pd.DataFrame) -> go.Figure:
    """
    Create scatter plot for gene expression data.
    
    Args:
        df: DataFrame with gene expression data
        
    Returns:
        Plotly figure object
    """
    fig = px.scatter(
        df, 
        x='sample_id', 
        y='expression_value',
        color='condition',
        size='quality_score',
        hover_data=['gene_symbol', 'tissue_type', 'cell_line'],
        title="Gene Expression Scatter Plot"
    )
    
    fig.update_layout(
        xaxis_title="Sample ID",
        yaxis_title="Expression Value",
        hovermode='closest'
    )
    
    return fig


def create_box_plot(df: pd.DataFrame) -> go.Figure:
    """
    Create box plot for gene expression data.
    
    Args:
        df: DataFrame with gene expression data
        
    Returns:
        Plotly figure object
    """
    fig = px.box(
        df,
        x='condition',
        y='expression_value',
        color='gene_symbol',
        title="Gene Expression Box Plot"
    )
    
    fig.update_layout(
        xaxis_title="Condition",
        yaxis_title="Expression Value"
    )
    
    return fig


def create_heatmap(df: pd.DataFrame) -> go.Figure:
    """
    Create heatmap for gene expression data.
    
    Args:
        df: DataFrame with gene expression data
        
    Returns:
        Plotly figure object
    """
    # Pivot data for heatmap
    pivot_df = df.pivot_table(
        values='expression_value',
        index='gene_symbol',
        columns='sample_id',
        aggfunc='mean'
    )
    
    fig = px.imshow(
        pivot_df.values,
        x=pivot_df.columns,
        y=pivot_df.index,
        color_continuous_scale='RdBu_r',
        title="Gene Expression Heatmap"
    )
    
    fig.update_layout(
        xaxis_title="Sample ID",
        yaxis_title="Gene Symbol"
    )
    
    return fig


def generate_expression_stats(df: pd.DataFrame) -> html.Div:
    """
    Generate statistics HTML for gene expression data.
    
    Args:
        df: DataFrame with gene expression data
        
    Returns:
        HTML div with statistics
    """
    if df.empty:
        return html.Div("No data available for statistics")
    
    stats = {
        'Total Records': len(df),
        'Unique Genes': df['gene_symbol'].nunique(),
        'Unique Samples': df['sample_id'].nunique(),
        'Mean Expression': df['expression_value'].mean(),
        'Median Expression': df['expression_value'].median(),
        'Std Expression': df['expression_value'].std()
    }
    
    stats_items = [
        html.Div([
            html.Strong(f"{key}: "),
            html.Span(f"{value:.2f}" if isinstance(value, float) else str(value))
        ], style={'margin': '5px 0'})
        for key, value in stats.items()
    ]
    
    return html.Div([
        html.H4("Statistics"),
        html.Div(stats_items)
    ])


# Export the registration function
__all__ = ['register_gene_expression_callbacks']
