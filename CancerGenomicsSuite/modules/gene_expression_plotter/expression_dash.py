"""
Gene Expression Plotter Dashboard

This module provides an interactive dashboard for gene expression analysis,
allowing users to upload data, configure analysis parameters, and
visualize results through a web-based interface.
"""

import logging
from typing import Dict, List, Any, Optional
import dash
from dash import html, dcc, dash_table, Input, Output, State, callback_context
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import json
import base64
import io

from .plotter import GeneExpressionPlotter, ExpressionAnalysisConfig


class ExpressionDashboard:
    """
    Interactive dashboard for gene expression analysis.
    
    This class provides methods to create and manage an interactive
    web-based dashboard for gene expression analysis.
    """
    
    def __init__(self, app: dash.Dash):
        """
        Initialize the expression dashboard.
        
        Args:
            app (dash.Dash): Dash application instance
        """
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.plotter = GeneExpressionPlotter()
        
        # Register callbacks
        self._register_callbacks()
    
    def get_layout(self) -> html.Div:
        """
        Get the dashboard layout.
        
        Returns:
            html.Div: Dashboard layout
        """
        return html.Div([
            # Header
            html.Div([
                html.H1("Gene Expression Plotter", className="text-center mb-4"),
                html.P("Comprehensive gene expression analysis tools for cancer genomics research", 
                       className="text-center text-muted")
            ], className="jumbotron"),
            
            # Main content
            html.Div([
                # Data upload section
                html.Div([
                    html.H3("Data Upload"),
                    html.Div([
                        html.Label("Expression Data (CSV/TSV):", className="form-label"),
                        dcc.Upload(
                            id='upload-expression-data',
                            children=html.Div([
                                'Drag and Drop or ',
                                html.A('Select Expression Data File')
                            ]),
                            style={
                                'width': '100%', 'height': '60px', 'lineHeight': '60px',
                                'borderWidth': '1px', 'borderStyle': 'dashed',
                                'borderRadius': '5px', 'textAlign': 'center'
                            },
                            multiple=False
                        ),
                        html.Br(),
                        html.Label("Sample Metadata (Optional, CSV/TSV):", className="form-label"),
                        dcc.Upload(
                            id='upload-metadata',
                            children=html.Div([
                                'Drag and Drop or ',
                                html.A('Select Metadata File')
                            ]),
                            style={
                                'width': '100%', 'height': '60px', 'lineHeight': '60px',
                                'borderWidth': '1px', 'borderStyle': 'dashed',
                                'borderRadius': '5px', 'textAlign': 'center'
                            },
                            multiple=False
                        ),
                        html.Div(id='expression-upload-status', className="mt-3")
                    ])
                ], className="card mb-4"),
                
                # Analysis configuration
                html.Div([
                    html.H3("Analysis Configuration"),
                    html.Div([
                        html.Div([
                            dcc.Checklist(
                                id='analysis-options',
                                options=[
                                    {'label': 'Normalize Data', 'value': 'normalize'},
                                    {'label': 'Log Transform', 'value': 'log_transform'},
                                    {'label': 'Filter Low Expression', 'value': 'filter_low'},
                                    {'label': 'Perform Clustering', 'value': 'clustering'},
                                    {'label': 'Perform PCA', 'value': 'pca'},
                                    {'label': 'Calculate Correlations', 'value': 'correlations'},
                                    {'label': 'Differential Expression', 'value': 'differential'}
                                ],
                                value=['normalize', 'log_transform', 'filter_low', 'pca', 'correlations'],
                                className="form-check"
                            )
                        ], className="col-md-6"),
                        html.Div([
                            html.Label("Min Expression Threshold:", className="form-label"),
                            dcc.Input(
                                id='min-expression-threshold',
                                type='number',
                                value=1.0,
                                min=0.1,
                                max=10.0,
                                step=0.1,
                                className="form-control mb-2"
                            ),
                            html.Label("Min Samples with Expression:", className="form-label"),
                            dcc.Input(
                                id='min-samples-expression',
                                type='number',
                                value=3,
                                min=1,
                                max=20,
                                className="form-control mb-2"
                            ),
                            html.Label("Number of Clusters:", className="form-label"),
                            dcc.Input(
                                id='n-clusters',
                                type='number',
                                value=3,
                                min=2,
                                max=10,
                                className="form-control"
                            )
                        ], className="col-md-6")
                    ], className="row"),
                    html.Div([
                        html.Button('Run Analysis', id='run-analysis-btn', 
                                  className="btn btn-primary me-2"),
                        html.Button('Clear Data', id='clear-data-btn', 
                                  className="btn btn-secondary")
                    ], className="mt-3")
                ], className="card mb-4"),
                
                # Data preview
                html.Div([
                    html.H3("Data Preview"),
                    html.Div(id='expression-data-preview')
                ], className="card mb-4"),
                
                # Analysis results
                html.Div([
                    html.H3("Analysis Results"),
                    html.Div(id='expression-analysis-results')
                ], className="card mb-4"),
                
                # Visualizations
                html.Div([
                    html.H3("Visualizations"),
                    html.Div(id='expression-visualizations')
                ], className="card mb-4")
                
            ], className="container-fluid")
        ])
    
    def _register_callbacks(self):
        """Register dashboard callbacks."""
        
        @self.app.callback(
            [Output('expression-upload-status', 'children'),
             Output('expression-data-preview', 'children')],
            [Input('upload-expression-data', 'contents'),
             Input('upload-metadata', 'contents')],
            [State('upload-expression-data', 'filename'),
             State('upload-metadata', 'filename')]
        )
        def handle_upload(expression_contents, metadata_contents, expression_filename, metadata_filename):
            """Handle file uploads."""
            ctx = callback_context
            if not ctx.triggered:
                return "", ""
            
            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
            
            if trigger_id == 'upload-expression-data' and expression_contents:
                return self._process_expression_upload(expression_contents, expression_filename)
            elif trigger_id == 'upload-metadata' and metadata_contents:
                return self._process_metadata_upload(metadata_contents, metadata_filename)
            
            return "", ""
        
        @self.app.callback(
            [Output('expression-analysis-results', 'children'),
             Output('expression-visualizations', 'children')],
            [Input('run-analysis-btn', 'n_clicks')],
            [State('analysis-options', 'value'),
             State('min-expression-threshold', 'value'),
             State('min-samples-expression', 'value'),
             State('n-clusters', 'value')]
        )
        def run_analysis(n_clicks, options, min_threshold, min_samples, n_clusters):
            """Run gene expression analysis."""
            if n_clicks == 0 or self.plotter.expression_data is None:
                return html.P("Upload data and click 'Run Analysis'"), html.Div()
            
            try:
                # Configure analysis
                config = ExpressionAnalysisConfig(
                    normalize_data='normalize' in options,
                    log_transform='log_transform' in options,
                    filter_low_expression='filter_low' in options,
                    perform_clustering='clustering' in options,
                    perform_pca='pca' in options,
                    calculate_correlations='correlations' in options,
                    perform_differential_expression='differential' in options,
                    min_expression_threshold=min_threshold or 1.0,
                    min_samples_with_expression=min_samples or 3,
                    n_clusters=n_clusters or 3
                )
                
                # Update plotter config
                self.plotter.config = config
                
                # Preprocess data
                preprocess_results = self.plotter.preprocess_data()
                if not preprocess_results['success']:
                    return html.Div([
                        html.H4("Preprocessing Error", className="text-danger"),
                        html.P(preprocess_results['error'])
                    ]), html.Div()
                
                # Perform analysis
                results = self.plotter.analyze_expression()
                if not results.get('success', True):
                    return html.Div([
                        html.H4("Analysis Error", className="text-danger"),
                        html.P(results.get('error', 'Unknown error'))
                    ]), html.Div()
                
                # Create results display
                results_display = self._create_results_display(results)
                
                # Create visualizations
                visualizations = self._create_visualizations(results)
                
                return results_display, visualizations
                
            except Exception as e:
                error_msg = f"Analysis failed: {str(e)}"
                self.logger.error(error_msg)
                return html.Div([
                    html.H4("Analysis Error", className="text-danger"),
                    html.P(error_msg)
                ]), html.Div()
        
        @self.app.callback(
            [Output('upload-expression-data', 'contents'),
             Output('upload-metadata', 'contents'),
             Output('expression-data-preview', 'children', allow_duplicate=True)],
            [Input('clear-data-btn', 'n_clicks')],
            prevent_initial_call=True
        )
        def clear_data(n_clicks):
            """Clear uploaded data."""
            if n_clicks:
                self.plotter.expression_data = None
                self.plotter.metadata = None
                return None, None, html.P("Data cleared")
            return dash.no_update, dash.no_update, dash.no_update
    
    def _process_expression_upload(self, contents, filename):
        """Process expression data upload."""
        try:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            
            if filename.endswith('.csv'):
                df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), index_col=0)
            elif filename.endswith('.tsv'):
                df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), sep='\t', index_col=0)
            else:
                return html.Div([
                    html.P("Unsupported file format. Please upload CSV or TSV files.", 
                          className="text-danger")
                ]), html.Div()
            
            # Load data into plotter
            load_results = self.plotter.load_expression_data(df)
            
            if load_results['success']:
                # Create data preview
                preview = self._create_data_preview(df, "Expression Data")
                
                return html.Div([
                    html.P(f"Successfully loaded {load_results['genes']} genes and {load_results['samples']} samples", 
                          className="text-success")
                ]), preview
            else:
                return html.Div([
                    html.P(f"Error loading data: {load_results['error']}", 
                          className="text-danger")
                ]), html.Div()
                
        except Exception as e:
            return html.Div([
                html.P(f"Error processing file: {str(e)}", className="text-danger")
            ]), html.Div()
    
    def _process_metadata_upload(self, contents, filename):
        """Process metadata upload."""
        try:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            
            if filename.endswith('.csv'):
                df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), index_col=0)
            elif filename.endswith('.tsv'):
                df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), sep='\t', index_col=0)
            else:
                return html.Div([
                    html.P("Unsupported file format. Please upload CSV or TSV files.", 
                          className="text-danger")
                ]), html.Div()
            
            # Load metadata into plotter
            self.plotter.metadata = df
            
            # Create metadata preview
            preview = self._create_data_preview(df, "Sample Metadata")
            
            return html.Div([
                html.P(f"Successfully loaded metadata for {len(df)} samples", 
                      className="text-success")
            ]), preview
                
        except Exception as e:
            return html.Div([
                html.P(f"Error processing metadata: {str(e)}", className="text-danger")
            ]), html.Div()
    
    def _create_data_preview(self, df: pd.DataFrame, title: str) -> html.Div:
        """Create data preview table."""
        # Show first 10 rows and columns
        preview_df = df.iloc[:10, :10]
        
        return html.Div([
            html.H5(title),
            dash_table.DataTable(
                data=preview_df.to_dict('records'),
                columns=[{"name": i, "id": i} for i in preview_df.columns],
                style_cell={'textAlign': 'left', 'fontSize': 12},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                page_size=10
            ),
            html.P(f"Showing first 10 rows and columns of {df.shape[0]} x {df.shape[1]} data")
        ])
    
    def _create_results_display(self, results: Dict[str, Any]) -> html.Div:
        """Create results display components."""
        components = []
        
        # Basic information
        components.append(html.H4("Analysis Summary"))
        components.append(html.P(f"Genes: {results.get('data_shape', [0, 0])[0]}"))
        components.append(html.P(f"Samples: {results.get('data_shape', [0, 0])[1]}"))
        
        # Basic statistics
        if 'basic_statistics' in results:
            stats = results['basic_statistics']['overall']
            components.append(html.H4("Basic Statistics"))
            
            stats_data = [
                {'Metric': 'Mean Expression', 'Value': f"{stats.get('mean_expression', 0):.3f}"},
                {'Metric': 'Median Expression', 'Value': f"{stats.get('median_expression', 0):.3f}"},
                {'Metric': 'Std Expression', 'Value': f"{stats.get('std_expression', 0):.3f}"},
                {'Metric': 'Min Expression', 'Value': f"{stats.get('min_expression', 0):.3f}"},
                {'Metric': 'Max Expression', 'Value': f"{stats.get('max_expression', 0):.3f}"},
                {'Metric': 'Zero Expression %', 'Value': f"{stats.get('zero_expression_percentage', 0):.1f}%"}
            ]
            
            components.append(dash_table.DataTable(
                data=stats_data,
                columns=[{"name": i, "id": i} for i in stats_data[0].keys()],
                style_cell={'textAlign': 'left'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
            ))
        
        # PCA results
        if 'pca' in results:
            pca = results['pca']
            components.append(html.H4("Principal Component Analysis"))
            components.append(html.P(f"PC1 explains {pca['explained_variance_ratio'][0]*100:.1f}% of variance"))
            components.append(html.P(f"PC2 explains {pca['explained_variance_ratio'][1]*100:.1f}% of variance"))
        
        # Clustering results
        if 'clustering' in results:
            clustering = results['clustering']
            components.append(html.H4("Clustering Results"))
            components.append(html.P(f"Method: {clustering['method']}"))
            if clustering['method'] == 'kmeans':
                components.append(html.P(f"Number of clusters: {clustering['n_clusters']}"))
                components.append(html.P(f"Inertia: {clustering['inertia']:.2f}"))
        
        # Differential expression results
        if 'differential_expression' in results:
            de = results['differential_expression']
            if 'error' not in de:
                components.append(html.H4("Differential Expression"))
                components.append(html.P(f"Comparison: {de['comparison']}"))
                components.append(html.P(f"Significant genes: {de['significant_genes']} / {de['total_genes']}"))
        
        return html.Div(components)
    
    def _create_visualizations(self, results: Dict[str, Any]) -> html.Div:
        """Create visualization components."""
        components = []
        
        # Expression distribution
        if 'basic_statistics' in results and self.plotter.expression_data is not None:
            # Sample expression distribution
            sample_means = self.plotter.expression_data.mean(axis=0)
            
            fig = go.Figure(data=[
                go.Histogram(x=sample_means, nbinsx=30, name='Sample Mean Expression')
            ])
            fig.update_layout(
                title="Sample Mean Expression Distribution",
                xaxis_title="Mean Expression",
                yaxis_title="Frequency"
            )
            components.append(dcc.Graph(figure=fig))
        
        # PCA plot
        if 'pca' in results:
            pca = results['pca']
            pca_df = pd.DataFrame(pca['components']).T
            
            fig = go.Figure(data=[
                go.Scatter(
                    x=pca_df.iloc[:, 0],
                    y=pca_df.iloc[:, 1],
                    mode='markers',
                    text=pca_df.index,
                    name='Samples'
                )
            ])
            fig.update_layout(
                title="PCA Plot",
                xaxis_title=f"PC1 ({pca['explained_variance_ratio'][0]*100:.1f}%)",
                yaxis_title=f"PC2 ({pca['explained_variance_ratio'][1]*100:.1f}%)"
            )
            components.append(dcc.Graph(figure=fig))
        
        # Sample correlation heatmap
        if 'correlations' in results and self.plotter.expression_data is not None:
            sample_corr = self.plotter.expression_data.corr()
            
            fig = go.Figure(data=go.Heatmap(
                z=sample_corr.values,
                x=sample_corr.columns,
                y=sample_corr.index,
                colorscale='RdBu',
                zmid=0
            ))
            fig.update_layout(
                title="Sample Correlation Heatmap",
                xaxis_title="Samples",
                yaxis_title="Samples"
            )
            components.append(dcc.Graph(figure=fig))
        
        # Differential expression volcano plot
        if 'differential_expression' in results:
            de = results['differential_expression']
            if 'error' not in de:
                de_df = pd.DataFrame(de['results'])
                
                fig = go.Figure()
                
                # Non-significant points
                non_sig = de_df[~de_df['significant']]
                fig.add_trace(go.Scatter(
                    x=non_sig['log2_fold_change'],
                    y=-np.log10(non_sig['p_value']),
                    mode='markers',
                    marker=dict(color='gray', size=4),
                    name='Non-significant'
                ))
                
                # Significant points
                sig = de_df[de_df['significant']]
                if len(sig) > 0:
                    fig.add_trace(go.Scatter(
                        x=sig['log2_fold_change'],
                        y=-np.log10(sig['p_value']),
                        mode='markers',
                        marker=dict(color='red', size=6),
                        text=sig['gene'],
                        name='Significant'
                    ))
                
                fig.update_layout(
                    title="Volcano Plot",
                    xaxis_title="Log2 Fold Change",
                    yaxis_title="-Log10 P-value"
                )
                components.append(dcc.Graph(figure=fig))
        
        return html.Div(components)


# Legacy function for backward compatibility
def register_callbacks(app):
    """Register callbacks for this module (legacy function)."""
    dashboard = ExpressionDashboard(app)
    return dashboard

# Legacy layout for backward compatibility
layout = html.Div([
    html.H1("Gene Expression Plotter"),
    html.P("This module provides gene expression visualization tools."),
    html.Div([
        html.Label("Upload Expression Data:"),
        dcc.Upload(
            id='upload-data',
            children=html.Div(['Drag and Drop or ', html.A('Select Files')]),
            style={'width': '100%', 'height': '60px', 'lineHeight': '60px', 'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px', 'textAlign': 'center'},
            multiple=False
        ),
        html.Div(id='expression-output')
    ])
])