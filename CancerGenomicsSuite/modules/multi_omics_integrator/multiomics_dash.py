"""
Multi-Omics Dashboard Module

This module provides a comprehensive Dash-based dashboard for multi-omics
data integration, analysis, and visualization.
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import json
from typing import Dict, List, Any, Optional
import logging
import base64
import io

from .integrator import MultiOmicsIntegrator, create_mock_omics_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultiOmicsDashboard:
    """
    A comprehensive dashboard for multi-omics data integration and analysis.
    """
    
    def __init__(self, app: dash.Dash):
        """
        Initialize the multi-omics dashboard.
        
        Args:
            app: Dash application instance
        """
        self.app = app
        self.integrator = MultiOmicsIntegrator()
        self.current_data = None
        self.setup_callbacks()
    
    def create_layout(self) -> html.Div:
        """
        Create the main dashboard layout.
        
        Returns:
            HTML div containing the dashboard layout
        """
        return html.Div([
            # Header
            html.Div([
                html.H1("Multi-Omics Integration Dashboard", 
                       className="text-center mb-4"),
                html.P("Comprehensive integration and analysis of multiple omics data types",
                      className="text-center text-muted mb-4")
            ], className="container-fluid"),
            
            # Control Panel
            html.Div([
                html.Div([
                    html.H4("Data Upload & Configuration", className="card-title"),
                    
                    # File upload section
                    html.Div([
                        html.Label("Upload Omics Data Files:"),
                        dcc.Upload(
                            id='upload-omics-data',
                            children=html.Div([
                                'Drag and Drop or ',
                                html.A('Select Multiple Omics Data Files')
                            ]),
                            style={
                                'width': '100%',
                                'height': '60px',
                                'lineHeight': '60px',
                                'borderWidth': '1px',
                                'borderStyle': 'dashed',
                                'borderRadius': '5px',
                                'textAlign': 'center',
                                'margin': '10px'
                            },
                            multiple=True
                        ),
                        html.Small("Supported formats: CSV, TSV, Excel", className="text-muted")
                    ], className="mb-3"),
                    
                    # Data type configuration
                    html.Div([
                        html.Label("Configure Data Types:"),
                        html.Div(id="data-type-config", className="mb-3")
                    ]),
                    
                    # Integration parameters
                    html.Div([
                        html.Label("Integration Method:"),
                        dcc.Dropdown(
                            id='integration-method',
                            options=[
                                {'label': 'Concatenation', 'value': 'concatenation'},
                                {'label': 'PCA Integration', 'value': 'pca'},
                                {'label': 'ICA Integration', 'value': 'ica'}
                            ],
                            value='concatenation',
                            className="mb-2"
                        ),
                        html.Label("Normalization Method:"),
                        dcc.Dropdown(
                            id='normalization-method',
                            options=[
                                {'label': 'Z-score', 'value': 'zscore'},
                                {'label': 'Min-Max', 'value': 'minmax'},
                                {'label': 'Quantile', 'value': 'quantile'},
                                {'label': 'Log2', 'value': 'log2'}
                            ],
                            value='zscore',
                            className="mb-2"
                        )
                    ], className="mb-3"),
                    
                    # Action buttons
                    html.Div([
                        html.Button('Load Mock Data', id='load-mock-data', 
                                  className='btn btn-primary me-2'),
                        html.Button('Integrate Data', id='integrate-data', 
                                  className='btn btn-success me-2'),
                        html.Button('Run Analysis', id='run-analysis', 
                                  className='btn btn-info me-2'),
                        html.Button('Export Results', id='export-results', 
                                  className='btn btn-warning')
                    ], className="d-flex flex-wrap gap-2")
                    
                ], className="card-body")
            ], className="card mb-4"),
            
            # Main content area
            html.Div([
                # Tabs for different views
                dcc.Tabs(id="main-tabs", value="overview", children=[
                    dcc.Tab(label="Data Overview", value="overview"),
                    dcc.Tab(label="Integration Results", value="integration"),
                    dcc.Tab(label="Dimensionality Reduction", value="dimension-reduction"),
                    dcc.Tab(label="Clustering Analysis", value="clustering"),
                    dcc.Tab(label="Correlation Analysis", value="correlation"),
                    dcc.Tab(label="Visualization", value="visualization")
                ]),
                
                # Tab content
                html.Div(id="multiomics-tab-content", className="mt-3")
                
            ], className="container-fluid"),
            
            # Hidden divs for storing data
            html.Div(id='omics-data', style={'display': 'none'}),
            html.Div(id='integration-results', style={'display': 'none'}),
            html.Div(id='multiomics-analysis-results', style={'display': 'none'}),
            
            # Download components
            dcc.Download(id="multiomics-download-results"),
            dcc.Download(id="download-data")
        ])
    
    def create_overview_tab(self) -> html.Div:
        """Create the data overview tab content."""
        return html.Div([
            html.Div([
                html.H4("Multi-Omics Data Overview"),
                dcc.Graph(id="data-overview-plot")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Data Quality Metrics"),
                html.Div(id="quality-metrics", className="row")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Data Summary"),
                html.Div(id="data-summary")
            ], className="card")
        ])
    
    def create_integration_tab(self) -> html.Div:
        """Create the integration results tab content."""
        return html.Div([
            html.Div([
                html.H4("Integration Results"),
                html.Div(id="integration-summary", className="mb-3"),
                dcc.Graph(id="integration-plot")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Feature Importance"),
                dcc.Graph(id="feature-importance-plot")
            ], className="card")
        ])
    
    def create_dimension_reduction_tab(self) -> html.Div:
        """Create the dimensionality reduction tab content."""
        return html.Div([
            html.Div([
                html.H4("Dimensionality Reduction"),
                html.Div([
                    html.Label("Reduction Method:"),
                    dcc.Dropdown(
                        id="reduction-method",
                        options=[
                            {'label': 'PCA', 'value': 'pca'},
                            {'label': 't-SNE', 'value': 'tsne'},
                            {'label': 'UMAP', 'value': 'umap'}
                        ],
                        value='pca',
                        className="mb-2"
                    ),
                    html.Label("Number of Components:"),
                    dcc.Slider(
                        id='n-components',
                        min=2,
                        max=10,
                        step=1,
                        value=2,
                        marks={i: str(i) for i in range(2, 11)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                    html.Button("Run Dimensionality Reduction", id="run-reduction", 
                              className="btn btn-primary mt-2")
                ], className="mb-3"),
                dcc.Graph(id="reduction-plot")
            ], className="card")
        ])
    
    def create_clustering_tab(self) -> html.Div:
        """Create the clustering analysis tab content."""
        return html.Div([
            html.Div([
                html.H4("Clustering Analysis"),
                html.Div([
                    html.Label("Clustering Method:"),
                    dcc.Dropdown(
                        id="clustering-method",
                        options=[
                            {'label': 'K-means', 'value': 'kmeans'},
                            {'label': 'DBSCAN', 'value': 'dbscan'},
                            {'label': 'Hierarchical', 'value': 'hierarchical'}
                        ],
                        value='kmeans',
                        className="mb-2"
                    ),
                    html.Label("Number of Clusters:"),
                    dcc.Slider(
                        id='n-clusters',
                        min=2,
                        max=10,
                        step=1,
                        value=3,
                        marks={i: str(i) for i in range(2, 11)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                    html.Button("Run Clustering", id="run-clustering", 
                              className="btn btn-primary mt-2")
                ], className="mb-3"),
                dcc.Graph(id="clustering-plot")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Clustering Results"),
                html.Div(id="clustering-results")
            ], className="card")
        ])
    
    def create_correlation_tab(self) -> html.Div:
        """Create the correlation analysis tab content."""
        return html.Div([
            html.Div([
                html.H4("Inter-Omics Correlations"),
                dcc.Graph(id="correlation-heatmap")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Feature Correlations"),
                html.Div([
                    html.Label("Select Data Types for Correlation:"),
                    dcc.Checklist(
                        id="correlation-data-types",
                        options=[],
                        value=[],
                        className="mb-2"
                    ),
                    html.Button("Update Correlation Plot", id="update-correlation", 
                              className="btn btn-primary")
                ], className="mb-3"),
                dcc.Graph(id="feature-correlation-plot")
            ], className="card")
        ])
    
    def create_visualization_tab(self) -> html.Div:
        """Create the visualization tab content."""
        return html.Div([
            html.Div([
                html.H4("Interactive Visualizations"),
                html.Div([
                    html.Label("Visualization Type:"),
                    dcc.Dropdown(
                        id="visualization-type",
                        options=[
                            {'label': 'PCA Plot', 'value': 'pca'},
                            {'label': 't-SNE Plot', 'value': 'tsne'},
                            {'label': 'UMAP Plot', 'value': 'umap'},
                            {'label': 'Heatmap', 'value': 'heatmap'},
                            {'label': 'Box Plot', 'value': 'boxplot'}
                        ],
                        value='pca',
                        className="mb-2"
                    ),
                    html.Label("Color by:"),
                    dcc.Dropdown(
                        id="color-by",
                        options=[],
                        value=None,
                        className="mb-2"
                    )
                ], className="mb-3"),
                dcc.Graph(id="main-visualization", style={'height': '600px'})
            ], className="card")
        ])
    
    def setup_callbacks(self):
        """Set up all dashboard callbacks."""
        
        @self.app.callback(
            [Output('omics-data', 'children'),
             Output('data-type-config', 'children')],
            [Input('load-mock-data', 'n_clicks')]
        )
        def load_mock_data(n_clicks):
            """Load mock data and create configuration interface."""
            if n_clicks:
                try:
                    # Create mock data
                    mock_data = create_mock_omics_data()
                    
                    # Store data
                    data_json = json.dumps({
                        data_type: data.to_dict() for data_type, data in mock_data.items()
                    })
                    
                    # Create data type configuration
                    config_children = []
                    for data_type in mock_data.keys():
                        config_children.append(
                            html.Div([
                                html.Label(f"{data_type.title()} Data:"),
                                dcc.Input(
                                    id=f"data-type-{data_type}",
                                    type="text",
                                    value=data_type,
                                    className="form-control mb-2"
                                )
                            ], className="col-md-3")
                        )
                    
                    config_div = html.Div(config_children, className="row")
                    
                    return data_json, config_div
                    
                except Exception as e:
                    logger.error(f"Error loading mock data: {e}")
                    return "", html.Div(f"Error: {str(e)}", className="alert alert-danger")
            
            return "", html.Div("Click 'Load Mock Data' to begin", className="text-muted")
        
        @self.app.callback(
            [Output('integration-results', 'children'),
             Output('integration-summary', 'children')],
            [Input('integrate-data', 'n_clicks')],
            [State('omics-data', 'children'),
             State('integration-method', 'value'),
             State('normalization-method', 'value')]
        )
        def integrate_data(n_clicks, omics_data_json, integration_method, normalization_method):
            """Integrate omics data."""
            if n_clicks and omics_data_json:
                try:
                    # Load data
                    data_dict = json.loads(omics_data_json)
                    
                    # Clear previous data
                    self.integrator.omics_data = {}
                    
                    # Load each data type
                    for data_type, data_dict in data_dict.items():
                        data_df = pd.DataFrame(data_dict)
                        self.integrator.omics_data[data_type] = data_df
                        
                        # Normalize data
                        self.integrator.normalize_data(data_type, method=normalization_method)
                    
                    # Integrate data
                    integrated_data = self.integrator.integrate_omics_data(
                        integration_method=integration_method
                    )
                    
                    # Get summary
                    summary = self.integrator.get_integration_summary()
                    
                    # Create summary display
                    summary_children = self.create_integration_summary_display(summary)
                    
                    # Store results
                    results_json = json.dumps({
                        'summary': summary,
                        'integrated_data_shape': integrated_data.shape
                    })
                    
                    return results_json, summary_children
                    
                except Exception as e:
                    logger.error(f"Error integrating data: {e}")
                    return "", html.Div(f"Error: {str(e)}", className="alert alert-danger")
            
            return "", html.Div("Click 'Integrate Data' to begin integration", className="text-muted")
        
        @self.app.callback(
            Output('multiomics-tab-content', 'children'),
            [Input('main-tabs', 'value')]
        )
        def render_tab_content(active_tab):
            """Render content based on active tab."""
            if active_tab == 'overview':
                return self.create_overview_tab()
            elif active_tab == 'integration':
                return self.create_integration_tab()
            elif active_tab == 'dimension-reduction':
                return self.create_dimension_reduction_tab()
            elif active_tab == 'clustering':
                return self.create_clustering_tab()
            elif active_tab == 'correlation':
                return self.create_correlation_tab()
            elif active_tab == 'visualization':
                return self.create_visualization_tab()
            else:
                return html.Div("Select a tab to view content")
        
        @self.app.callback(
            Output('reduction-plot', 'figure'),
            [Input('run-reduction', 'n_clicks')],
            [State('reduction-method', 'value'),
             State('n-components', 'value')]
        )
        def run_dimensionality_reduction(n_clicks, method, n_components):
            """Run dimensionality reduction and create plot."""
            if n_clicks and self.integrator.integrated_data is not None:
                try:
                    # Perform dimensionality reduction
                    reduced_data = self.integrator.perform_dimensionality_reduction(
                        method=method, n_components=n_components
                    )
                    
                    # Create visualization
                    fig = self.integrator.create_integration_visualization(method=method)
                    return fig
                    
                except Exception as e:
                    logger.error(f"Error in dimensionality reduction: {e}")
                    return go.Figure()
            
            return go.Figure()
        
        @self.app.callback(
            [Output('clustering-plot', 'figure'),
             Output('clustering-results', 'children')],
            [Input('run-clustering', 'n_clicks')],
            [State('clustering-method', 'value'),
             State('n-clusters', 'value')]
        )
        def run_clustering(n_clicks, method, n_clusters):
            """Run clustering analysis and create plots."""
            if n_clicks and self.integrator.integrated_data is not None:
                try:
                    # Perform clustering
                    clustering_results = self.integrator.perform_clustering(
                        method=method, n_clusters=n_clusters
                    )
                    
                    # Create visualization
                    fig = self.integrator.create_integration_visualization(method='pca')
                    
                    # Create results display
                    results_children = self.create_clustering_results_display(clustering_results)
                    
                    return fig, results_children
                    
                except Exception as e:
                    logger.error(f"Error in clustering: {e}")
                    return go.Figure(), html.Div(f"Error: {str(e)}", className="alert alert-danger")
            
            return go.Figure(), html.Div("Click 'Run Clustering' to begin analysis", className="text-muted")
        
        @self.app.callback(
            Output('correlation-heatmap', 'figure'),
            [Input('integration-results', 'children')]
        )
        def update_correlation_heatmap(integration_results_json):
            """Update correlation heatmap."""
            if integration_results_json and self.integrator.omics_data:
                try:
                    fig = self.integrator.create_correlation_heatmap()
                    return fig
                except Exception as e:
                    logger.error(f"Error creating correlation heatmap: {e}")
                    return go.Figure()
            
            return go.Figure()
        
        @self.app.callback(
            Output('data-overview-plot', 'figure'),
            [Input('omics-data', 'children')]
        )
        def update_data_overview(omics_data_json):
            """Update data overview plot."""
            if omics_data_json:
                try:
                    fig = self.integrator.create_data_overview_plot()
                    return fig
                except Exception as e:
                    logger.error(f"Error creating overview plot: {e}")
                    return go.Figure()
            
            return go.Figure()
    
    def create_integration_summary_display(self, summary: Dict[str, Any]) -> html.Div:
        """Create display for integration summary."""
        cards = []
        
        metrics = [
            ('Data Types', len(summary['data_types']), 'primary'),
            ('Total Features', summary['total_features'], 'success'),
            ('Total Samples', summary['total_samples'], 'info'),
            ('Integration Method', summary['integration_method'], 'warning')
        ]
        
        for title, value, color in metrics:
            card = html.Div([
                html.Div([
                    html.H5(str(value), className="card-title"),
                    html.P(title, className="card-text")
                ], className="card-body text-center")
            ], className=f"card border-{color} mb-2")
            cards.append(html.Div(card, className="col-md-3"))
        
        return html.Div(cards, className="row")
    
    def create_clustering_results_display(self, results: Dict[str, Any]) -> html.Div:
        """Create display for clustering results."""
        return html.Div([
            html.Div([
                html.H5("Clustering Summary"),
                html.P(f"Method: {results['method']}"),
                html.P(f"Number of Clusters: {results['n_clusters']}"),
                html.P(f"Silhouette Score: {results['silhouette_score']:.3f}")
            ], className="card-body")
        ], className="card")


def create_multiomics_dashboard(app: dash.Dash) -> MultiOmicsDashboard:
    """
    Create and configure a multi-omics integration dashboard.
    
    Args:
        app: Dash application instance
        
    Returns:
        Configured MultiOmicsDashboard instance
    """
    dashboard = MultiOmicsDashboard(app)
    return dashboard


def main():
    """Main function for testing the dashboard."""
    app = dash.Dash(__name__)
    dashboard = create_multiomics_dashboard(app)
    app.layout = dashboard.create_layout()
    
    if __name__ == "__main__":
        app.run_server(debug=True)


if __name__ == "__main__":
    main()
