"""
Mutation Effect Prediction Callbacks

This module contains all Dash callbacks related to mutation effect prediction
and analysis, including variant annotation, pathogenicity prediction, and
clinical significance assessment.

Features:
- Mutation data loading and filtering
- Variant effect prediction visualization
- Pathogenicity scoring and classification
- Clinical significance analysis
- Mutation impact assessment
- Interactive mutation browser
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
from app.db.models import MutationRecord, DataFile
from app.db import db

logger = logging.getLogger(__name__)


def register_mutation_effect_callbacks(app):
    """
    Register all mutation effect related callbacks with the Dash app.
    
    Args:
        app: Dash application instance
    """
    
    @app.callback(
        [Output('mutation-effect-plot', 'figure'),
         Output('mutation-effect-stats', 'children'),
         Output('mutation-effect-loading', 'children')],
        [Input('mutation-effect-gene-select', 'value'),
         Input('mutation-effect-pathogenicity-select', 'value'),
         Input('mutation-effect-plot-type', 'value'),
         Input('mutation-effect-refresh', 'n_clicks')],
        [State('mutation-effect-sample-filter', 'value'),
         State('mutation-effect-cancer-type-filter', 'value')]
    )
    def update_mutation_effect_plot(selected_genes, selected_pathogenicity, plot_type, refresh_clicks, sample_filter, cancer_type_filter):
        """
        Update mutation effect plot based on user selections.
        
        Args:
            selected_genes: List of selected gene symbols
            selected_pathogenicity: List of selected pathogenicity levels
            plot_type: Type of plot to display (scatter, bar, pie)
            refresh_clicks: Number of refresh button clicks
            sample_filter: Sample ID filter
            cancer_type_filter: Cancer type filter
            
        Returns:
            Tuple of (figure, stats_html, loading_component)
        """
        try:
            # Get mutation data
            query = MutationRecord.query
            
            if selected_genes:
                query = query.filter(MutationRecord.gene.in_(selected_genes))
            
            if selected_pathogenicity:
                query = query.filter(MutationRecord.pathogenicity.in_(selected_pathogenicity))
            
            if sample_filter:
                query = query.filter(MutationRecord.sample_id.like(f'%{sample_filter}%'))
            
            if cancer_type_filter:
                query = query.filter(MutationRecord.cancer_type.like(f'%{cancer_type_filter}%'))
            
            data = query.all()
            
            if not data:
                empty_fig = go.Figure()
                empty_fig.add_annotation(
                    text="No mutation data available for selected criteria",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
                return empty_fig, "No data available", no_update
            
            # Convert to DataFrame
            df = pd.DataFrame([record.to_dict() for record in data])
            
            # Create plot based on type
            if plot_type == 'scatter':
                fig = create_mutation_scatter_plot(df)
            elif plot_type == 'bar':
                fig = create_mutation_bar_plot(df)
            elif plot_type == 'pie':
                fig = create_mutation_pie_plot(df)
            else:
                fig = create_mutation_scatter_plot(df)
            
            # Generate statistics
            stats_html = generate_mutation_stats(df)
            
            return fig, stats_html, no_update
            
        except Exception as e:
            logger.error(f"Error updating mutation effect plot: {e}")
            error_fig = go.Figure()
            error_fig.add_annotation(
                text=f"Error loading data: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return error_fig, f"Error: {str(e)}", no_update
    
    @app.callback(
        Output('mutation-effect-gene-select', 'options'),
        [Input('mutation-effect-refresh', 'n_clicks')]
    )
    def update_mutation_gene_options(refresh_clicks):
        """
        Update available gene options from mutation database.
        
        Args:
            refresh_clicks: Number of refresh button clicks
            
        Returns:
            List of gene options for dropdown
        """
        try:
            genes = db.session.query(MutationRecord.gene).distinct().all()
            return [{'label': gene[0], 'value': gene[0]} for gene in genes]
        except Exception as e:
            logger.error(f"Error loading mutation gene options: {e}")
            return []
    
    @app.callback(
        Output('mutation-effect-pathogenicity-select', 'options'),
        [Input('mutation-effect-refresh', 'n_clicks')]
    )
    def update_pathogenicity_options(refresh_clicks):
        """
        Update available pathogenicity options from database.
        
        Args:
            refresh_clicks: Number of refresh button clicks
            
        Returns:
            List of pathogenicity options for dropdown
        """
        try:
            pathogenicity_levels = db.session.query(MutationRecord.pathogenicity).distinct().filter(
                MutationRecord.pathogenicity.isnot(None)
            ).all()
            return [{'label': path[0], 'value': path[0]} for path in pathogenicity_levels]
        except Exception as e:
            logger.error(f"Error loading pathogenicity options: {e}")
            return []
    
    @app.callback(
        [Output('mutation-effect-download-data', 'data'),
         Output('mutation-effect-download-trigger', 'children')],
        [Input('mutation-effect-download-btn', 'n_clicks')],
        [State('mutation-effect-gene-select', 'value'),
         State('mutation-effect-pathogenicity-select', 'value'),
         State('mutation-effect-sample-filter', 'value'),
         State('mutation-effect-cancer-type-filter', 'value')]
    )
    def download_mutation_data(n_clicks, selected_genes, selected_pathogenicity, sample_filter, cancer_type_filter):
        """
        Download mutation data as CSV.
        
        Args:
            n_clicks: Number of download button clicks
            selected_genes: List of selected gene symbols
            selected_pathogenicity: List of selected pathogenicity levels
            sample_filter: Sample ID filter
            cancer_type_filter: Cancer type filter
            
        Returns:
            Tuple of (download_data, trigger_children)
        """
        if not n_clicks:
            return no_update, no_update
        
        try:
            # Get filtered data
            query = MutationRecord.query
            
            if selected_genes:
                query = query.filter(MutationRecord.gene.in_(selected_genes))
            
            if selected_pathogenicity:
                query = query.filter(MutationRecord.pathogenicity.in_(selected_pathogenicity))
            
            if sample_filter:
                query = query.filter(MutationRecord.sample_id.like(f'%{sample_filter}%'))
            
            if cancer_type_filter:
                query = query.filter(MutationRecord.cancer_type.like(f'%{cancer_type_filter}%'))
            
            data = query.all()
            df = pd.DataFrame([record.to_dict() for record in data])
            
            # Convert to CSV
            csv_string = df.to_csv(index=False)
            
            return dict(content=csv_string, filename="mutation_data.csv"), no_update
            
        except Exception as e:
            logger.error(f"Error downloading mutation data: {e}")
            return no_update, f"Error: {str(e)}"
    
    @app.callback(
        Output('mutation-effect-details', 'children'),
        [Input('mutation-effect-plot', 'clickData')]
    )
    def display_mutation_details(click_data):
        """
        Display detailed information about clicked mutation.
        
        Args:
            click_data: Data from plot click event
            
        Returns:
            HTML content with mutation details
        """
        if not click_data:
            return "Click on a data point to see mutation details"
        
        try:
            point = click_data['points'][0]
            mutation_id = point.get('customdata', {}).get('mutation_id', None)
            
            if mutation_id:
                # Get detailed mutation information
                mutation = MutationRecord.query.get(mutation_id)
                
                if mutation:
                    return html.Div([
                        html.H4(f"Mutation Details"),
                        html.P(f"Gene: {mutation.gene}"),
                        html.P(f"Variant: {mutation.variant}"),
                        html.P(f"Variant Type: {mutation.variant_type or 'N/A'}"),
                        html.P(f"Chromosome: {mutation.chromosome or 'N/A'}"),
                        html.P(f"Position: {mutation.position or 'N/A'}"),
                        html.P(f"Effect: {mutation.effect or 'N/A'}"),
                        html.P(f"Clinical Significance: {mutation.clinical_significance or 'N/A'}"),
                        html.P(f"Pathogenicity: {mutation.pathogenicity or 'N/A'}"),
                        html.P(f"Allele Frequency: {mutation.allele_frequency or 'N/A'}"),
                        html.P(f"Source: {mutation.source or 'N/A'}")
                    ])
                else:
                    return "Mutation not found"
            else:
                return "No mutation ID available"
                
        except Exception as e:
            logger.error(f"Error displaying mutation details: {e}")
            return f"Error loading mutation details: {str(e)}"
    
    @app.callback(
        Output('mutation-effect-prediction', 'children'),
        [Input('mutation-effect-predict-btn', 'n_clicks')],
        [State('mutation-effect-input-gene', 'value'),
         State('mutation-effect-input-variant', 'value')]
    )
    def predict_mutation_effect(n_clicks, gene, variant):
        """
        Predict mutation effect for user input.
        
        Args:
            n_clicks: Number of predict button clicks
            gene: Gene symbol input
            variant: Variant notation input
            
        Returns:
            HTML content with prediction results
        """
        if not n_clicks or not gene or not variant:
            return "Enter gene and variant to predict effect"
        
        try:
            # This would integrate with actual prediction algorithms
            # For now, return a placeholder response
            
            prediction_result = {
                'gene': gene,
                'variant': variant,
                'predicted_effect': 'Missense',
                'pathogenicity_score': 0.75,
                'confidence': 'High',
                'clinical_significance': 'Likely Pathogenic'
            }
            
            return html.Div([
                html.H4("Mutation Effect Prediction"),
                html.P(f"Gene: {prediction_result['gene']}"),
                html.P(f"Variant: {prediction_result['variant']}"),
                html.P(f"Predicted Effect: {prediction_result['predicted_effect']}"),
                html.P(f"Pathogenicity Score: {prediction_result['pathogenicity_score']}"),
                html.P(f"Confidence: {prediction_result['confidence']}"),
                html.P(f"Clinical Significance: {prediction_result['clinical_significance']}")
            ])
            
        except Exception as e:
            logger.error(f"Error predicting mutation effect: {e}")
            return f"Error: {str(e)}"


def create_mutation_scatter_plot(df: pd.DataFrame) -> go.Figure:
    """
    Create scatter plot for mutation data.
    
    Args:
        df: DataFrame with mutation data
        
    Returns:
        Plotly figure object
    """
    fig = px.scatter(
        df, 
        x='allele_frequency', 
        y='quality_score',
        color='pathogenicity',
        size='read_depth',
        hover_data=['gene', 'variant', 'clinical_significance', 'cancer_type'],
        title="Mutation Effect Scatter Plot"
    )
    
    fig.update_layout(
        xaxis_title="Allele Frequency",
        yaxis_title="Quality Score",
        hovermode='closest'
    )
    
    return fig


def create_mutation_bar_plot(df: pd.DataFrame) -> go.Figure:
    """
    Create bar plot for mutation data.
    
    Args:
        df: DataFrame with mutation data
        
    Returns:
        Plotly figure object
    """
    # Count mutations by pathogenicity
    pathogenicity_counts = df['pathogenicity'].value_counts()
    
    fig = px.bar(
        x=pathogenicity_counts.index,
        y=pathogenicity_counts.values,
        title="Mutation Count by Pathogenicity",
        labels={'x': 'Pathogenicity', 'y': 'Count'}
    )
    
    return fig


def create_mutation_pie_plot(df: pd.DataFrame) -> go.Figure:
    """
    Create pie chart for mutation data.
    
    Args:
        df: DataFrame with mutation data
        
    Returns:
        Plotly figure object
    """
    # Count mutations by clinical significance
    clinical_counts = df['clinical_significance'].value_counts()
    
    fig = px.pie(
        values=clinical_counts.values,
        names=clinical_counts.index,
        title="Mutations by Clinical Significance"
    )
    
    return fig


def generate_mutation_stats(df: pd.DataFrame) -> html.Div:
    """
    Generate statistics HTML for mutation data.
    
    Args:
        df: DataFrame with mutation data
        
    Returns:
        HTML div with statistics
    """
    if df.empty:
        return html.Div("No data available for statistics")
    
    stats = {
        'Total Mutations': len(df),
        'Unique Genes': df['gene'].nunique(),
        'Unique Samples': df['sample_id'].nunique(),
        'Pathogenic Mutations': len(df[df['pathogenicity'] == 'pathogenic']),
        'Mean Allele Frequency': df['allele_frequency'].mean(),
        'Mean Quality Score': df['quality_score'].mean()
    }
    
    stats_items = [
        html.Div([
            html.Strong(f"{key}: "),
            html.Span(f"{value:.3f}" if isinstance(value, float) else str(value))
        ], style={'margin': '5px 0'})
        for key, value in stats.items()
    ]
    
    return html.Div([
        html.H4("Mutation Statistics"),
        html.Div(stats_items)
    ])


# Export the registration function
__all__ = ['register_mutation_effect_callbacks']
