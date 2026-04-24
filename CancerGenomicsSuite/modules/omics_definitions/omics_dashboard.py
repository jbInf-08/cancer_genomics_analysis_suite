"""
Comprehensive Omics Dashboard

This module provides a comprehensive dashboard for all omics fields with interactive
visualizations, data management, and analysis capabilities.
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union
import logging
import json
from pathlib import Path

from .omics_registry import get_omics_registry, OmicsFieldRegistry
from .omics_processor import get_omics_processor_factory, OmicsProcessorFactory
from .omics_metadata import get_omics_metadata_manager, OmicsMetadataManager
from .omics_integration import get_omics_integration_engine, OmicsIntegrationEngine

logger = logging.getLogger(__name__)


class ComprehensiveOmicsDashboard:
    """Comprehensive dashboard for all omics fields."""
    
    def __init__(self):
        """Initialize the comprehensive omics dashboard."""
        self.registry = get_omics_registry()
        self.processor_factory = get_omics_processor_factory()
        self.metadata_manager = get_omics_metadata_manager()
        self.integration_engine = get_omics_integration_engine()
        
        # Data storage
        self.loaded_data: Dict[str, pd.DataFrame] = {}
        self.processed_data: Dict[str, pd.DataFrame] = {}
        self.integration_results: Dict[str, Any] = {}
        
        # Initialize Dash app
        self.app = dash.Dash(__name__)
        self.app.title = "Comprehensive Omics Analysis Dashboard"
        
        # Setup layout and callbacks
        self._setup_layout()
        self._setup_callbacks()
    
    def _setup_layout(self):
        """Setup the dashboard layout."""
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1("Comprehensive Omics Analysis Dashboard", 
                       className="text-center mb-4"),
                html.P("Advanced multi-omics data analysis and integration platform", 
                      className="text-center text-muted mb-4")
            ], className="container-fluid"),
            
            # Main content
            html.Div([
                # Sidebar
                html.Div([
                    # Data Management Section
                    html.Div([
                        html.H4("Data Management", className="mb-3"),
                        
                        # Omics Type Selection
                        html.Div([
                            html.Label("Select Omics Type:", className="form-label"),
                            dcc.Dropdown(
                                id='omics-type-dropdown',
                                options=[
                                    {'label': field.full_name, 'value': field.name}
                                    for field in self.registry.get_all_fields().values()
                                ],
                                value='genomics',
                                className="mb-2"
                            )
                        ], className="mb-3"),
                        
                        # File Upload
                        html.Div([
                            html.Label("Upload Data File:", className="form-label"),
                            dcc.Upload(
                                id='upload-data',
                                children=html.Div([
                                    'Drag and Drop or ',
                                    html.A('Select Files')
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
                                multiple=False
                            )
                        ], className="mb-3"),
                        
                        # Data Processing Controls
                        html.Div([
                            html.Label("Processing Options:", className="form-label"),
                            dcc.Checklist(
                                id='processing-options',
                                options=[
                                    {'label': 'Quality Control', 'value': 'qc'},
                                    {'label': 'Normalization', 'value': 'normalization'},
                                    {'label': 'Filtering', 'value': 'filtering'}
                                ],
                                value=['qc'],
                                className="mb-2"
                            )
                        ], className="mb-3"),
                        
                        # Load Data Button
                        html.Button('Load and Process Data', 
                                  id='load-data-btn', 
                                  className='btn btn-primary btn-block mb-3'),
                        
                        # Data Summary
                        html.Div(id='data-summary', className="mb-3")
                        
                    ], className="card mb-4"),
                    
                    # Analysis Controls Section
                    html.Div([
                        html.H4("Analysis Controls", className="mb-3"),
                        
                        # Integration Method
                        html.Div([
                            html.Label("Integration Method:", className="form-label"),
                            dcc.Dropdown(
                                id='integration-method',
                                options=[
                                    {'label': 'Concatenation', 'value': 'concatenation'},
                                    {'label': 'PCA Integration', 'value': 'pca'},
                                    {'label': 'ICA Integration', 'value': 'ica'},
                                    {'label': 'CCA Integration', 'value': 'cca'},
                                    {'label': 'PLS Integration', 'value': 'pls'},
                                    {'label': 'Network Integration', 'value': 'network'}
                                ],
                                value='concatenation',
                                className="mb-2"
                            )
                        ], className="mb-3"),
                        
                        # Clustering Method
                        html.Div([
                            html.Label("Clustering Method:", className="form-label"),
                            dcc.Dropdown(
                                id='clustering-method',
                                options=[
                                    {'label': 'K-Means', 'value': 'kmeans'},
                                    {'label': 'DBSCAN', 'value': 'dbscan'},
                                    {'label': 'Agglomerative', 'value': 'agglomerative'}
                                ],
                                value='kmeans',
                                className="mb-2"
                            )
                        ], className="mb-3"),
                        
                        # Number of Clusters
                        html.Div([
                            html.Label("Number of Clusters:", className="form-label"),
                            dcc.Slider(
                                id='n-clusters',
                                min=2,
                                max=10,
                                step=1,
                                value=3,
                                marks={i: str(i) for i in range(2, 11)},
                                className="mb-2"
                            )
                        ], className="mb-3"),
                        
                        # Run Analysis Button
                        html.Button('Run Analysis', 
                                  id='run-analysis-btn', 
                                  className='btn btn-success btn-block mb-3'),
                        
                    ], className="card mb-4"),
                    
                    # Omics Field Information
                    html.Div([
                        html.H4("Omics Field Info", className="mb-3"),
                        html.Div(id='omics-field-info', className="small")
                    ], className="card")
                    
                ], className="col-md-3"),
                
                # Main Content Area
                html.Div([
                    # Tabs for different views
                    dcc.Tabs(id="main-tabs", value="overview", children=[
                        # Overview Tab
                        dcc.Tab(label="Overview", value="overview", children=[
                            html.Div([
                                # Statistics Cards
                                html.Div([
                                    html.Div([
                                        html.H5("Total Omics Fields", className="card-title"),
                                        html.H3(id="total-omics-fields", className="text-primary")
                                    ], className="card-body text-center")
                                ], className="card col-md-3"),
                                
                                html.Div([
                                    html.Div([
                                        html.H5("Loaded Datasets", className="card-title"),
                                        html.H3(id="loaded-datasets", className="text-success")
                                    ], className="card-body text-center")
                                ], className="card col-md-3"),
                                
                                html.Div([
                                    html.Div([
                                        html.H5("Processed Datasets", className="card-title"),
                                        html.H3(id="processed-datasets", className="text-info")
                                    ], className="card-body text-center")
                                ], className="card col-md-3"),
                                
                                html.Div([
                                    html.Div([
                                        html.H5("Integration Results", className="card-title"),
                                        html.H3(id="integration-results", className="text-warning")
                                    ], className="card-body text-center")
                                ], className="card col-md-3")
                                
                            ], className="row mb-4"),
                            
                            # Omics Categories Overview
                            html.Div([
                                html.H4("Omics Categories Overview"),
                                dcc.Graph(id="omics-categories-chart")
                            ], className="card mb-4"),
                            
                            # Recent Activity
                            html.Div([
                                html.H4("Recent Activity"),
                                html.Div(id="recent-activity")
                            ], className="card")
                            
                        ]),
                        
                        # Data Management Tab
                        dcc.Tab(label="Data Management", value="data-management", children=[
                            html.Div([
                                # Data Table
                                html.Div([
                                    html.H4("Loaded Data"),
                                    html.Div(id="data-table-container")
                                ], className="card mb-4"),
                                
                                # Data Quality Metrics
                                html.Div([
                                    html.H4("Data Quality Metrics"),
                                    html.Div(id="quality-metrics-container")
                                ], className="card mb-4"),
                                
                                # Metadata Management
                                html.Div([
                                    html.H4("Metadata Management"),
                                    html.Div(id="metadata-container")
                                ], className="card")
                                
                            ])
                        ]),
                        
                        # Analysis Tab
                        dcc.Tab(label="Analysis", value="analysis", children=[
                            html.Div([
                                # Integration Results
                                html.Div([
                                    html.H4("Integration Results"),
                                    html.Div(id="integration-results-container")
                                ], className="card mb-4"),
                                
                                # Clustering Results
                                html.Div([
                                    html.H4("Clustering Results"),
                                    html.Div(id="clustering-results-container")
                                ], className="card mb-4"),
                                
                                # Dimensionality Reduction
                                html.Div([
                                    html.H4("Dimensionality Reduction"),
                                    html.Div(id="dimensionality-reduction-container")
                                ], className="card mb-4"),
                                
                                # Correlation Analysis
                                html.Div([
                                    html.H4("Correlation Analysis"),
                                    html.Div(id="correlation-analysis-container")
                                ], className="card")
                                
                            ])
                        ]),
                        
                        # Visualization Tab
                        dcc.Tab(label="Visualization", value="visualization", children=[
                            html.Div([
                                # Main Visualization Area
                                html.Div([
                                    html.H4("Interactive Visualizations"),
                                    dcc.Graph(id="main-visualization", style={'height': '600px'})
                                ], className="card mb-4"),
                                
                                # Visualization Controls
                                html.Div([
                                    html.H4("Visualization Controls"),
                                    html.Div([
                                        html.Div([
                                            html.Label("Visualization Type:", className="form-label"),
                                            dcc.Dropdown(
                                                id='viz-type',
                                                options=[
                                                    {'label': 'Heatmap', 'value': 'heatmap'},
                                                    {'label': 'PCA Plot', 'value': 'pca'},
                                                    {'label': 't-SNE Plot', 'value': 'tsne'},
                                                    {'label': 'UMAP Plot', 'value': 'umap'},
                                                    {'label': 'Network Plot', 'value': 'network'},
                                                    {'label': 'Correlation Matrix', 'value': 'correlation'}
                                                ],
                                                value='heatmap',
                                                className="mb-2"
                                            )
                                        ], className="col-md-6"),
                                        
                                        html.Div([
                                            html.Label("Color By:", className="form-label"),
                                            dcc.Dropdown(
                                                id='color-by',
                                                options=[],
                                                className="mb-2"
                                            )
                                        ], className="col-md-6")
                                        
                                    ], className="row")
                                ], className="card mb-4"),
                                
                                # Additional Visualizations
                                html.Div([
                                    html.H4("Additional Visualizations"),
                                    html.Div(id="additional-visualizations")
                                ], className="card")
                                
                            ])
                        ]),
                        
                        # Reports Tab
                        dcc.Tab(label="Reports", value="reports", children=[
                            html.Div([
                                # Report Generation
                                html.Div([
                                    html.H4("Generate Reports"),
                                    html.Div([
                                        html.Button('Generate Data Summary Report', 
                                                  id='generate-data-report', 
                                                  className='btn btn-primary mr-2'),
                                        html.Button('Generate Analysis Report', 
                                                  id='generate-analysis-report', 
                                                  className='btn btn-success mr-2'),
                                        html.Button('Generate Integration Report', 
                                                  id='generate-integration-report', 
                                                  className='btn btn-info')
                                    ], className="mb-3")
                                ], className="card mb-4"),
                                
                                # Report Display
                                html.Div([
                                    html.H4("Generated Reports"),
                                    html.Div(id="report-display")
                                ], className="card")
                                
                            ])
                        ])
                        
                    ])
                    
                ], className="col-md-9")
                
            ], className="row")
            
        ], className="container-fluid")
    
    def _setup_callbacks(self):
        """Setup dashboard callbacks."""
        
        @self.app.callback(
            [Output('total-omics-fields', 'children'),
             Output('loaded-datasets', 'children'),
             Output('processed-datasets', 'children'),
             Output('integration-results', 'children')],
            [Input('main-tabs', 'value')]
        )
        def update_overview_stats(tab_value):
            """Update overview statistics."""
            total_fields = len(self.registry.get_all_fields())
            loaded_count = len(self.loaded_data)
            processed_count = len(self.processed_data)
            integration_count = len(self.integration_results)
            
            return total_fields, loaded_count, processed_count, integration_count
        
        @self.app.callback(
            Output('omics-categories-chart', 'figure'),
            [Input('main-tabs', 'value')]
        )
        def update_omics_categories_chart(tab_value):
            """Update omics categories chart."""
            stats = self.registry.get_statistics()
            categories = stats['categories']
            
            fig = px.pie(
                values=list(categories.values()),
                names=list(categories.keys()),
                title="Distribution of Omics Fields by Category"
            )
            
            return fig
        
        @self.app.callback(
            Output('omics-field-info', 'children'),
            [Input('omics-type-dropdown', 'value')]
        )
        def update_omics_field_info(omics_type):
            """Update omics field information."""
            if not omics_type:
                return "Select an omics type to view information"
            
            field = self.registry.get_field(omics_type)
            if not field:
                return "Field not found"
            
            info_html = f"""
            <strong>{field.full_name}</strong><br>
            <em>{field.description}</em><br><br>
            
            <strong>Category:</strong> {field.category}<br>
            <strong>Data Type:</strong> {field.data_type.value}<br>
            <strong>Complexity:</strong> {field.complexity_level}<br>
            <strong>Maturity:</strong> {field.maturity_level}<br>
            <strong>Clinical Relevance:</strong> {field.clinical_relevance}<br><br>
            
            <strong>Primary Entities:</strong><br>
            {', '.join(field.primary_entities[:5])}<br><br>
            
            <strong>Supported Analyses:</strong><br>
            {', '.join(field.supported_analyses[:5])}<br><br>
            
            <strong>Required Tools:</strong><br>
            {', '.join(field.required_tools[:5])}
            """
            
            return info_html
        
        @self.app.callback(
            [Output('data-summary', 'children'),
             Output('data-table-container', 'children')],
            [Input('load-data-btn', 'n_clicks')],
            [State('omics-type-dropdown', 'value'),
             State('upload-data', 'contents'),
             State('upload-data', 'filename'),
             State('processing-options', 'value')]
        )
        def load_and_process_data(n_clicks, omics_type, contents, filename, processing_options):
            """Load and process omics data."""
            if not n_clicks or not omics_type or not contents:
                return "No data loaded", "No data to display"
            
            try:
                # Parse uploaded file
                import base64
                import io
                
                content_type, content_string = contents.split(',')
                decoded = base64.b64decode(content_string)
                
                if filename.endswith('.csv'):
                    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
                elif filename.endswith('.tsv'):
                    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), sep='\t')
                else:
                    return "Unsupported file format", "Please upload CSV or TSV files"
                
                # Process data
                processor = self.processor_factory.create_processor(omics_type)
                result = processor.load_data(filename, data=df)
                
                if result.success:
                    self.loaded_data[omics_type] = result.data
                    
                    # Apply processing options
                    if 'qc' in processing_options:
                        qc_metrics = processor.quality_control(result.data, omics_type)
                        result.quality_metrics = qc_metrics.__dict__
                    
                    if 'normalization' in processing_options:
                        norm_result = processor.normalize_data(result.data, 'standard')
                        if norm_result.success:
                            self.processed_data[omics_type] = norm_result.data
                    
                    # Create summary
                    summary = f"""
                    <div class="alert alert-success">
                        <strong>Data loaded successfully!</strong><br>
                        Features: {result.data.shape[0]}<br>
                        Samples: {result.data.shape[1]}<br>
                        Data type: {omics_type}
                    </div>
                    """
                    
                    # Create data table
                    table = html.Div([
                        html.H5(f"{omics_type.title()} Data Preview"),
                        html.Div([
                            html.Table([
                                html.Thead([
                                    html.Tr([html.Th(col) for col in result.data.columns[:10]])
                                ]),
                                html.Tbody([
                                    html.Tr([
                                        html.Td(result.data.iloc[i, j]) 
                                        for j in range(min(10, result.data.shape[1]))
                                    ]) for i in range(min(10, result.data.shape[0]))
                                ])
                            ], className="table table-striped table-sm")
                        ], style={'max-height': '400px', 'overflow-y': 'auto'})
                    ])
                    
                    return summary, table
                else:
                    return f"Error loading data: {result.error_message}", "Error occurred"
                    
            except Exception as e:
                logger.error(f"Error in load_and_process_data: {e}")
                return f"Error: {str(e)}", "Error occurred"
        
        @self.app.callback(
            [Output('integration-results-container', 'children'),
             Output('clustering-results-container', 'children'),
             Output('dimensionality-reduction-container', 'children')],
            [Input('run-analysis-btn', 'n_clicks')],
            [State('integration-method', 'value'),
             State('clustering-method', 'value'),
             State('n-clusters', 'value')]
        )
        def run_analysis(n_clicks, integration_method, clustering_method, n_clusters):
            """Run multi-omics analysis."""
            if not n_clicks or len(self.loaded_data) < 2:
                return "No analysis run", "No analysis run", "No analysis run"
            
            try:
                # Integration
                integration_result = self.integration_engine.integrate_omics_data(
                    self.loaded_data, method=integration_method
                )
                self.integration_results[integration_method] = integration_result
                
                # Clustering
                if integration_result.integrated_data is not None:
                    clusters = self.integration_engine.perform_clustering(
                        integration_result.integrated_data,
                        method=clustering_method,
                        n_clusters=n_clusters
                    )
                    integration_result.sample_clusters = clusters
                    
                    # Dimensionality reduction
                    reduced_data = self.integration_engine.perform_dimensionality_reduction(
                        integration_result.integrated_data,
                        method='pca',
                        n_components=2
                    )
                    
                    # Create results displays
                    integration_display = html.Div([
                        html.H5("Integration Results"),
                        html.P(f"Method: {integration_method}"),
                        html.P(f"Features: {integration_result.integrated_data.shape[0]}"),
                        html.P(f"Samples: {integration_result.integrated_data.shape[1]}"),
                        html.P(f"Quality metrics: {integration_result.quality_metrics}")
                    ])
                    
                    clustering_display = html.Div([
                        html.H5("Clustering Results"),
                        html.P(f"Method: {clustering_method}"),
                        html.P(f"Number of clusters: {len(clusters.unique())}"),
                        html.P(f"Cluster distribution: {clusters.value_counts().to_dict()}")
                    ])
                    
                    dimensionality_display = html.Div([
                        html.H5("Dimensionality Reduction Results"),
                        html.P(f"Method: PCA"),
                        html.P(f"Components: {reduced_data.shape[1]}"),
                        html.P(f"Explained variance: {integration_result.quality_metrics.get('variance_explained', 'N/A')}")
                    ])
                    
                    return integration_display, clustering_display, dimensionality_display
                else:
                    return "Integration failed", "Clustering failed", "Dimensionality reduction failed"
                    
            except Exception as e:
                logger.error(f"Error in run_analysis: {e}")
                return f"Error: {str(e)}", f"Error: {str(e)}", f"Error: {str(e)}"
        
        @self.app.callback(
            Output('main-visualization', 'figure'),
            [Input('viz-type', 'value'),
             Input('color-by', 'value')]
        )
        def update_main_visualization(viz_type, color_by):
            """Update main visualization."""
            if not self.loaded_data:
                return go.Figure().add_annotation(
                    text="No data loaded",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
            
            try:
                if viz_type == 'heatmap':
                    # Create heatmap from first loaded dataset
                    data = list(self.loaded_data.values())[0]
                    fig = px.imshow(
                        data.iloc[:50, :20],  # Show subset for performance
                        title=f"Heatmap of {list(self.loaded_data.keys())[0]} Data"
                    )
                    
                elif viz_type == 'pca':
                    # Create PCA plot
                    if self.integration_results:
                        result = list(self.integration_results.values())[0]
                        if result.integrated_data is not None:
                            reduced_data = self.integration_engine.perform_dimensionality_reduction(
                                result.integrated_data, method='pca', n_components=2
                            )
                            fig = px.scatter(
                                reduced_data,
                                x='PC1', y='PC2',
                                title="PCA Plot of Integrated Data"
                            )
                        else:
                            fig = go.Figure().add_annotation(
                                text="No integrated data available",
                                xref="paper", yref="paper",
                                x=0.5, y=0.5, showarrow=False
                            )
                    else:
                        fig = go.Figure().add_annotation(
                            text="No integration results available",
                            xref="paper", yref="paper",
                            x=0.5, y=0.5, showarrow=False
                        )
                        
                else:
                    fig = go.Figure().add_annotation(
                        text=f"Visualization type '{viz_type}' not implemented",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False
                    )
                
                return fig
                
            except Exception as e:
                logger.error(f"Error in update_main_visualization: {e}")
                return go.Figure().add_annotation(
                    text=f"Error: {str(e)}",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
        
        @self.app.callback(
            Output('report-display', 'children'),
            [Input('generate-data-report', 'n_clicks'),
             Input('generate-analysis-report', 'n_clicks'),
             Input('generate-integration-report', 'n_clicks')]
        )
        def generate_reports(data_report_clicks, analysis_report_clicks, integration_report_clicks):
            """Generate various reports."""
            ctx = callback_context
            if not ctx.triggered:
                return "Select a report type to generate"
            
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            
            try:
                if button_id == 'generate-data-report':
                    # Generate data summary report
                    report = f"""
                    # Data Summary Report
                    Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
                    
                    ## Loaded Datasets
                    """
                    for omics_type, data in self.loaded_data.items():
                        report += f"- {omics_type}: {data.shape[0]} features, {data.shape[1]} samples\n"
                    
                    report += f"""
                    ## Processed Datasets
                    """
                    for omics_type, data in self.processed_data.items():
                        report += f"- {omics_type}: {data.shape[0]} features, {data.shape[1]} samples\n"
                    
                    return html.Div([
                        html.H5("Data Summary Report"),
                        html.Pre(report, style={'white-space': 'pre-wrap'})
                    ])
                
                elif button_id == 'generate-analysis-report':
                    # Generate analysis report
                    report = f"""
                    # Analysis Report
                    Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
                    
                    ## Integration Results
                    """
                    for method, result in self.integration_results.items():
                        report += f"- {method}: {result.quality_metrics}\n"
                    
                    return html.Div([
                        html.H5("Analysis Report"),
                        html.Pre(report, style={'white-space': 'pre-wrap'})
                    ])
                
                elif button_id == 'generate-integration-report':
                    # Generate integration report
                    if self.integration_results:
                        result = list(self.integration_results.values())[0]
                        report = self.integration_engine.generate_integration_report(
                            result, self.loaded_data
                        )
                        return html.Div([
                            html.H5("Integration Report"),
                            html.Pre(report, style={'white-space': 'pre-wrap'})
                        ])
                    else:
                        return html.Div([
                            html.H5("Integration Report"),
                            html.P("No integration results available")
                        ])
                
            except Exception as e:
                logger.error(f"Error generating report: {e}")
                return html.Div([
                    html.H5("Error"),
                    html.P(f"Error generating report: {str(e)}")
                ])
    
    def run(self, debug: bool = True, port: int = 8050):
        """Run the dashboard."""
        self.app.run_server(debug=debug, port=port)


def create_comprehensive_omics_dashboard() -> ComprehensiveOmicsDashboard:
    """Create and return a comprehensive omics dashboard instance."""
    return ComprehensiveOmicsDashboard()


if __name__ == "__main__":
    # Create and run the dashboard
    dashboard = create_comprehensive_omics_dashboard()
    dashboard.run(debug=True, port=8050)
