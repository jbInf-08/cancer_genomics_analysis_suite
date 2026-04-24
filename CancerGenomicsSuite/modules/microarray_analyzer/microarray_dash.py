"""
Microarray Analyzer Dash Dashboard

This module provides a Dash-based web interface for microarray data analysis,
allowing users to load data, perform normalization, differential expression analysis,
clustering, and visualization with interactive plots and tables.
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import numpy as np
import json
from typing import Dict, List, Any, Optional
import logging
import base64
import io

from .microarray import (
    MicroarrayAnalyzer,
    MicroarrayData,
    DifferentialExpressionResult,
    ClusteringResult,
    create_sample_microarray_data,
    create_sample_analyzer
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MicroarrayDashboard:
    """
    Dash dashboard for microarray data analysis.
    """
    
    def __init__(self, app_name: str = "Microarray Analyzer"):
        """
        Initialize the microarray analysis dashboard.
        
        Args:
            app_name: Name of the Dash app
        """
        self.app = dash.Dash(__name__)
        self.app.title = app_name
        self.analyzer = create_sample_analyzer()
        self.current_data = None
        self.setup_layout()
        self.setup_callbacks()
    
    def setup_layout(self):
        """Set up the dashboard layout."""
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1("Microarray Data Analyzer", className="header-title"),
                html.P("Comprehensive microarray data analysis with normalization, differential expression, and clustering", className="header-subtitle")
            ], className="header"),
            
            # Data Upload Panel
            html.Div([
                html.H3("Data Upload"),
                html.Div([
                    html.Div([
                        html.Label("Expression Matrix (CSV/TSV):"),
                        dcc.Upload(
                            id="expression-upload",
                            children=html.Div([
                                "Drag and Drop or ",
                                html.A("Select Expression File")
                            ]),
                            style={
                                "width": "100%",
                                "height": "60px",
                                "lineHeight": "60px",
                                "borderWidth": "1px",
                                "borderStyle": "dashed",
                                "borderRadius": "5px",
                                "textAlign": "center",
                                "margin": "10px"
                            },
                            multiple=False
                        )
                    ], className="upload-group"),
                    
                    html.Div([
                        html.Label("Sample Metadata (CSV/TSV):"),
                        dcc.Upload(
                            id="sample-metadata-upload",
                            children=html.Div([
                                "Drag and Drop or ",
                                html.A("Select Sample Metadata File")
                            ]),
                            style={
                                "width": "100%",
                                "height": "60px",
                                "lineHeight": "60px",
                                "borderWidth": "1px",
                                "borderStyle": "dashed",
                                "borderRadius": "5px",
                                "textAlign": "center",
                                "margin": "10px"
                            },
                            multiple=False
                        )
                    ], className="upload-group"),
                    
                    html.Div([
                        html.Label("Gene Metadata (CSV/TSV):"),
                        dcc.Upload(
                            id="gene-metadata-upload",
                            children=html.Div([
                                "Drag and Drop or ",
                                html.A("Select Gene Metadata File")
                            ]),
                            style={
                                "width": "100%",
                                "height": "60px",
                                "lineHeight": "60px",
                                "borderWidth": "1px",
                                "borderStyle": "dashed",
                                "borderRadius": "5px",
                                "textAlign": "center",
                                "margin": "10px"
                            },
                            multiple=False
                        )
                    ], className="upload-group"),
                    
                    html.Div([
                        html.Label("Platform:"),
                        dcc.Dropdown(
                            id="platform-dropdown",
                            options=[
                                {"label": "Affymetrix", "value": "Affymetrix"},
                                {"label": "Illumina", "value": "Illumina"},
                                {"label": "Agilent", "value": "Agilent"},
                                {"label": "NimbleGen", "value": "NimbleGen"},
                                {"label": "Custom", "value": "Custom"}
                            ],
                            value="Custom",
                            clearable=False
                        )
                    ], className="upload-group"),
                    
                    html.Button("Load Data", id="load-data-button", className="load-button"),
                    html.Button("Load Sample Data", id="load-sample-button", className="sample-button")
                ], className="upload-grid")
            ], className="upload-panel"),
            
            # Data Summary Panel
            html.Div([
                html.H3("Data Summary"),
                html.Div(id="data-summary", className="data-summary")
            ], className="summary-panel"),
            
            # Analysis Controls Panel
            html.Div([
                html.H3("Analysis Controls"),
                html.Div([
                    html.Div([
                        html.Label("Normalization Method:"),
                        dcc.Dropdown(
                            id="normalization-dropdown",
                            options=[
                                {"label": "Quantile", "value": "quantile"},
                                {"label": "RMA", "value": "rma"},
                                {"label": "LOESS", "value": "loess"},
                                {"label": "VSN", "value": "vsn"},
                                {"label": "None", "value": "none"}
                            ],
                            value="quantile",
                            clearable=False
                        )
                    ], className="control-group"),
                    
                    html.Div([
                        html.Label("Group Column:"),
                        dcc.Dropdown(
                            id="group-column-dropdown",
                            options=[],
                            clearable=False
                        )
                    ], className="control-group"),
                    
                    html.Div([
                        html.Label("Group 1:"),
                        dcc.Dropdown(
                            id="group1-dropdown",
                            options=[],
                            clearable=False
                        )
                    ], className="control-group"),
                    
                    html.Div([
                        html.Label("Group 2:"),
                        dcc.Dropdown(
                            id="group2-dropdown",
                            options=[],
                            clearable=False
                        )
                    ], className="control-group"),
                    
                    html.Div([
                        html.Label("Fold Change Threshold:"),
                        dcc.Input(
                            id="fold-change-threshold",
                            type="number",
                            value=1.5,
                            min=1.0,
                            step=0.1
                        )
                    ], className="control-group"),
                    
                    html.Div([
                        html.Label("P-value Threshold:"),
                        dcc.Input(
                            id="pvalue-threshold",
                            type="number",
                            value=0.05,
                            min=0.001,
                            max=1.0,
                            step=0.001
                        )
                    ], className="control-group")
                ], className="controls-grid"),
                
                html.Div([
                    html.Button("Normalize Data", id="normalize-button", className="analyze-button"),
                    html.Button("Differential Expression", id="diff-expr-button", className="analyze-button"),
                    html.Button("Clustering", id="clustering-button", className="analyze-button"),
                    html.Button("PCA", id="pca-button", className="analyze-button")
                ], className="button-group")
            ], className="controls-panel"),
            
            # Visualization Panel
            html.Div([
                html.H3("Visualizations"),
                dcc.Tabs(id="visualization-tabs", value="heatmap", children=[
                    dcc.Tab(label="Expression Heatmap", value="heatmap"),
                    dcc.Tab(label="Differential Expression", value="diff-expr"),
                    dcc.Tab(label="Clustering", value="clustering"),
                    dcc.Tab(label="PCA", value="pca"),
                    dcc.Tab(label="Quality Control", value="qc")
                ]),
                html.Div(id="visualization-content", className="visualization-content")
            ], className="visualization-panel"),
            
            # Results Table Panel
            html.Div([
                html.H3("Results Table"),
                html.Div([
                    html.Label("Show:"),
                    dcc.Dropdown(
                        id="results-type-dropdown",
                        options=[
                            {"label": "Differential Expression", "value": "diff-expr"},
                            {"label": "Top Genes", "value": "top-genes"},
                            {"label": "Sample Metadata", "value": "sample-metadata"},
                            {"label": "Gene Metadata", "value": "gene-metadata"}
                        ],
                        value="diff-expr",
                        clearable=False
                    )
                ], className="table-controls"),
                html.Div(id="results-table-container")
            ], className="table-panel"),
            
            # Export Panel
            html.Div([
                html.H3("Export Results"),
                html.Div([
                    html.Label("Format:"),
                    dcc.Dropdown(
                        id="export-format-dropdown",
                        options=[
                            {"label": "JSON", "value": "json"},
                            {"label": "CSV", "value": "csv"},
                            {"label": "TSV", "value": "tsv"}
                        ],
                        value="json",
                        clearable=False,
                        style={"width": "150px"}
                    ),
                    html.Button("Export", id="export-button", className="export-button")
                ], className="export-controls"),
                html.Div(id="export-output", className="export-output")
            ], className="export-panel"),
            
            # Statistics Panel
            html.Div([
                html.H3("Analysis Statistics"),
                html.Div(id="statistics-display", className="statistics-display")
            ], className="statistics-panel"),
            
            # Hidden divs to store data
            html.Div(id="uploaded-data", style={"display": "none"}),
            html.Div(id="analysis-status", style={"display": "none"})
        ], className="main-container")
    
    def setup_callbacks(self):
        """Set up Dash callbacks for interactivity."""
        
        @self.app.callback(
            [Output("uploaded-data", "children"),
             Output("data-summary", "children"),
             Output("group-column-dropdown", "options"),
             Output("group-column-dropdown", "value")],
            [Input("load-data-button", "n_clicks"),
             Input("load-sample-button", "n_clicks")],
            [State("expression-upload", "contents"),
             State("sample-metadata-upload", "contents"),
             State("gene-metadata-upload", "contents"),
             State("platform-dropdown", "value")]
        )
        def load_data(load_clicks, sample_clicks, expression_content, sample_content, gene_content, platform):
            """Load microarray data."""
            
            ctx = callback_context
            if not ctx.triggered:
                return "", "", [], None
            
            button_id = ctx.triggered[0]["prop_id"].split(".")[0]
            
            if button_id == "load-sample-button" and sample_clicks:
                # Load sample data
                self.analyzer = create_sample_analyzer()
                self.current_data = self.analyzer.data
                
            elif button_id == "load-data-button" and load_clicks:
                # Load uploaded data
                if not all([expression_content, sample_content, gene_content]):
                    return "", "Please upload all required files", [], None
                
                try:
                    # Parse uploaded files
                    expression_df = self._parse_uploaded_file(expression_content)
                    sample_df = self._parse_uploaded_file(sample_content)
                    gene_df = self._parse_uploaded_file(gene_content)
                    
                    # Create analyzer and load data
                    self.analyzer = MicroarrayAnalyzer()
                    self.current_data = self.analyzer.load_data(
                        expression_df, sample_df, gene_df, platform
                    )
                    
                except Exception as e:
                    return "", f"Error loading data: {str(e)}", [], None
            
            else:
                return "", "", [], None
            
            # Generate summary and options
            summary = self._create_data_summary()
            group_options = [{"label": col, "value": col} for col in self.current_data.sample_metadata.columns]
            group_value = group_options[0]["value"] if group_options else None
            
            data_json = json.dumps(self.current_data.to_dict())
            
            return data_json, summary, group_options, group_value
        
        @self.app.callback(
            [Output("group1-dropdown", "options"),
             Output("group2-dropdown", "options")],
            [Input("group-column-dropdown", "value")]
        )
        def update_group_options(group_column):
            """Update group options based on selected column."""
            if not group_column or not self.current_data:
                return [], []
            
            unique_values = self.current_data.sample_metadata[group_column].unique()
            options = [{"label": val, "value": val} for val in unique_values]
            
            return options, options
        
        @self.app.callback(
            [Output("visualization-content", "children"),
             Output("analysis-status", "children")],
            [Input("normalize-button", "n_clicks"),
             Input("diff-expr-button", "n_clicks"),
             Input("clustering-button", "n_clicks"),
             Input("pca-button", "n_clicks"),
             Input("visualization-tabs", "value")],
            [State("normalization-dropdown", "value"),
             State("group-column-dropdown", "value"),
             State("group1-dropdown", "value"),
             State("group2-dropdown", "value"),
             State("fold-change-threshold", "value"),
             State("pvalue-threshold", "value")]
        )
        def run_analysis(normalize_clicks, diff_expr_clicks, clustering_clicks, pca_clicks, 
                        tab_value, norm_method, group_column, group1, group2, fc_threshold, pval_threshold):
            """Run microarray analysis."""
            
            ctx = callback_context
            if not ctx.triggered:
                return "", ""
            
            button_id = ctx.triggered[0]["prop_id"].split(".")[0]
            
            if not self.current_data:
                return "Please load data first", ""
            
            try:
                if button_id == "normalize-button" and normalize_clicks:
                    self.analyzer.normalize_data(norm_method)
                    
                elif button_id == "diff-expr-button" and diff_expr_clicks:
                    if not all([group_column, group1, group2]):
                        return "Please select groups for differential expression analysis", ""
                    
                    self.analyzer.fold_change_threshold = fc_threshold
                    self.analyzer.p_value_threshold = pval_threshold
                    self.analyzer.perform_differential_expression(group_column, group1, group2)
                    
                elif button_id == "clustering-button" and clustering_clicks:
                    self.analyzer.perform_clustering("kmeans", n_clusters=3)
                    
                elif button_id == "pca-button" and pca_clicks:
                    self.analyzer.perform_pca(n_components=2)
                
                # Generate visualization based on current tab
                visualization = self._create_visualization(tab_value)
                status = "Analysis completed successfully"
                
                return visualization, status
                
            except Exception as e:
                return f"Error in analysis: {str(e)}", ""
        
        @self.app.callback(
            Output("results-table-container", "children"),
            [Input("results-type-dropdown", "value")]
        )
        def update_results_table(results_type):
            """Update results table based on selection."""
            if not self.analyzer:
                return "No data loaded"
            
            if results_type == "diff-expr" and self.analyzer.differential_results:
                return self._create_differential_expression_table()
            elif results_type == "top-genes" and self.analyzer.differential_results:
                return self._create_top_genes_table()
            elif results_type == "sample-metadata" and self.current_data:
                return self._create_sample_metadata_table()
            elif results_type == "gene-metadata" and self.current_data:
                return self._create_gene_metadata_table()
            else:
                return "No data available for selected type"
        
        @self.app.callback(
            Output("export-output", "children"),
            [Input("export-button", "n_clicks")],
            [State("export-format-dropdown", "value")]
        )
        def export_results(export_clicks, format_type):
            """Export analysis results."""
            if not export_clicks or not self.analyzer:
                return ""
            
            try:
                exported_data = self.analyzer.export_results(format_type)
                
                if format_type == "json":
                    data_dict = json.loads(exported_data)
                    formatted_data = json.dumps(data_dict, indent=2)
                else:
                    formatted_data = exported_data
                
                return html.Div([
                    html.H4(f"Exported Data ({format_type.upper()})"),
                    html.Pre(formatted_data, className="export-data")
                ])
                
            except Exception as e:
                return html.Div([
                    html.H4("Export Error"),
                    html.P(f"Error exporting data: {str(e)}")
                ], className="error-message")
        
        @self.app.callback(
            Output("statistics-display", "children"),
            [Input("load-data-button", "n_clicks"),
             Input("load-sample-button", "n_clicks"),
             Input("normalize-button", "n_clicks"),
             Input("diff-expr-button", "n_clicks")]
        )
        def update_statistics(load_clicks, sample_clicks, norm_clicks, diff_clicks):
            """Update analysis statistics."""
            if not self.analyzer:
                return "No data loaded"
            
            stats = self.analyzer.get_statistics()
            
            return html.Div([
                html.P([
                    html.Strong("Data Status: "), "Loaded" if stats["data_loaded"] else "Not loaded",
                    html.Br(),
                    html.Strong("Normalized Data: "), "Available" if stats["normalized_data_available"] else "Not available",
                    html.Br(),
                    html.Strong("Differential Results: "), str(stats["differential_results_count"]),
                    html.Br(),
                    html.Strong("Clustering: "), "Completed" if stats["clustering_performed"] else "Not performed",
                    html.Br(),
                    html.Strong("PCA: "), "Completed" if stats["pca_performed"] else "Not performed"
                ])
            ])
    
    def _parse_uploaded_file(self, content):
        """Parse uploaded file content."""
        content_type, content_string = content.split(',')
        decoded = base64.b64decode(content_string)
        
        try:
            if 'csv' in content_type:
                df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), index_col=0)
            elif 'tsv' in content_type:
                df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), sep='\t', index_col=0)
            else:
                return None
        except Exception as e:
            logger.error(f"Error parsing uploaded file: {e}")
            return None
        
        return df
    
    def _create_data_summary(self) -> html.Div:
        """Create data summary display."""
        if not self.current_data:
            return html.P("No data loaded")
        
        shape = self.current_data.get_shape()
        quality = self.current_data.quality_metrics
        
        return html.Div([
            html.P([
                html.Strong("Platform: "), self.current_data.platform,
                html.Br(),
                html.Strong("Dimensions: "), f"{shape[0]} genes × {shape[1]} samples",
                html.Br(),
                html.Strong("Mean Expression: "), f"{quality['mean_expression']:.2f}",
                html.Br(),
                html.Strong("Missing Values: "), str(quality['missing_values']),
                html.Br(),
                html.Strong("Normalization: "), self.current_data.normalization_method
            ])
        ])
    
    def _create_visualization(self, tab_value: str) -> html.Div:
        """Create visualization based on tab selection."""
        if not self.current_data:
            return html.P("No data loaded")
        
        if tab_value == "heatmap":
            return self._create_heatmap()
        elif tab_value == "diff-expr":
            return self._create_differential_expression_plot()
        elif tab_value == "clustering":
            return self._create_clustering_plot()
        elif tab_value == "pca":
            return self._create_pca_plot()
        elif tab_value == "qc":
            return self._create_quality_control_plots()
        else:
            return html.P("Select a visualization tab")
    
    def _create_heatmap(self) -> html.Div:
        """Create expression heatmap."""
        if not self.current_data:
            return html.P("No data loaded")
        
        # Sample a subset of genes for visualization
        expression_matrix = self.current_data.expression_matrix
        n_genes_to_show = min(100, expression_matrix.shape[0])
        sampled_genes = np.random.choice(expression_matrix.index, n_genes_to_show, replace=False)
        sampled_data = expression_matrix.loc[sampled_genes]
        
        fig = px.imshow(
            sampled_data.values,
            x=sampled_data.columns,
            y=sampled_data.index,
            color_continuous_scale='RdBu_r',
            aspect='auto'
        )
        
        fig.update_layout(
            title="Expression Heatmap (Sample of Genes)",
            xaxis_title="Samples",
            yaxis_title="Genes",
            height=600
        )
        
        return dcc.Graph(figure=fig)
    
    def _create_differential_expression_plot(self) -> html.Div:
        """Create differential expression volcano plot."""
        if not self.analyzer.differential_results:
            return html.P("Run differential expression analysis first")
        
        # Prepare data for volcano plot
        data = []
        for result in self.analyzer.differential_results:
            data.append({
                'gene_symbol': result.gene_symbol,
                'log2_fold_change': result.log2_fold_change,
                'neg_log10_pvalue': -np.log10(result.p_value + 1e-10),
                'significant': result.significant,
                'p_value': result.p_value
            })
        
        df = pd.DataFrame(data)
        
        # Create volcano plot
        fig = px.scatter(
            df, x='log2_fold_change', y='neg_log10_pvalue',
            color='significant',
            hover_data=['gene_symbol', 'p_value'],
            title="Volcano Plot - Differential Expression",
            labels={
                'log2_fold_change': 'Log2 Fold Change',
                'neg_log10_pvalue': '-Log10 P-value'
            }
        )
        
        # Add significance lines
        fig.add_hline(y=-np.log10(0.05), line_dash="dash", line_color="red")
        fig.add_vline(x=np.log2(1.5), line_dash="dash", line_color="red")
        fig.add_vline(x=-np.log2(1.5), line_dash="dash", line_color="red")
        
        return dcc.Graph(figure=fig)
    
    def _create_clustering_plot(self) -> html.Div:
        """Create clustering visualization."""
        if not self.analyzer.clustering_results:
            return html.P("Run clustering analysis first")
        
        # Create a simple bar plot showing cluster sizes
        cluster_labels = self.analyzer.clustering_results.cluster_labels
        cluster_counts = pd.Series(cluster_labels).value_counts().sort_index()
        
        fig = px.bar(
            x=cluster_counts.index,
            y=cluster_counts.values,
            title="Cluster Sizes",
            labels={'x': 'Cluster', 'y': 'Number of Samples'}
        )
        
        return dcc.Graph(figure=fig)
    
    def _create_pca_plot(self) -> html.Div:
        """Create PCA visualization."""
        if not self.analyzer.pca_results:
            return html.P("Run PCA analysis first")
        
        pca_data = self.analyzer.pca_results
        components = np.array(pca_data['components'])
        
        # Create PCA scatter plot
        fig = px.scatter(
            x=components[:, 0],
            y=components[:, 1],
            title="PCA Plot",
            labels={'x': f'PC1 ({pca_data["explained_variance_ratio"][0]:.1%})',
                   'y': f'PC2 ({pca_data["explained_variance_ratio"][1]:.1%})'}
        )
        
        return dcc.Graph(figure=fig)
    
    def _create_quality_control_plots(self) -> html.Div:
        """Create quality control plots."""
        if not self.current_data:
            return html.P("No data loaded")
        
        expression_matrix = self.current_data.expression_matrix
        
        # Create box plot of expression values
        fig = px.box(
            x=expression_matrix.columns,
            y=expression_matrix.values.flatten(),
            title="Expression Distribution by Sample"
        )
        
        fig.update_layout(
            xaxis_title="Samples",
            yaxis_title="Expression Value",
            height=400
        )
        
        return dcc.Graph(figure=fig)
    
    def _create_differential_expression_table(self) -> html.Div:
        """Create differential expression results table."""
        if not self.analyzer.differential_results:
            return html.P("No differential expression results available")
        
        # Prepare data for table
        table_data = []
        for result in self.analyzer.differential_results:
            table_data.append({
                "Gene ID": result.gene_id,
                "Gene Symbol": result.gene_symbol,
                "Log2 Fold Change": f"{result.log2_fold_change:.3f}",
                "P-value": f"{result.p_value:.3e}",
                "Adjusted P-value": f"{result.adjusted_p_value:.3e}",
                "Significant": "Yes" if result.significant else "No",
                "Effect Size": f"{result.effect_size:.3f}"
            })
        
        return dash_table.DataTable(
            data=table_data,
            columns=[{"name": col, "id": col} for col in table_data[0].keys()],
            style_cell={"textAlign": "left", "padding": "10px"},
            style_header={"backgroundColor": "#f0f0f0", "fontWeight": "bold"},
            style_data_conditional=[
                {
                    "if": {"row_index": "odd"},
                    "backgroundColor": "#f9f9f9"
                },
                {
                    "if": {"filter_query": "{Significant} = Yes"},
                    "backgroundColor": "#ffebee"
                }
            ],
            page_size=20,
            sort_action="native",
            filter_action="native",
            export_format="csv"
        )
    
    def _create_top_genes_table(self) -> html.Div:
        """Create top genes table."""
        if not self.analyzer.differential_results:
            return html.P("No differential expression results available")
        
        top_genes = self.analyzer.get_top_differentially_expressed(n=50, sort_by="p_value")
        
        table_data = []
        for gene in top_genes:
            table_data.append({
                "Gene Symbol": gene.gene_symbol,
                "Log2 Fold Change": f"{gene.log2_fold_change:.3f}",
                "P-value": f"{gene.p_value:.3e}",
                "Significant": "Yes" if gene.significant else "No"
            })
        
        return dash_table.DataTable(
            data=table_data,
            columns=[{"name": col, "id": col} for col in table_data[0].keys()],
            style_cell={"textAlign": "left", "padding": "10px"},
            style_header={"backgroundColor": "#f0f0f0", "fontWeight": "bold"},
            page_size=20,
            sort_action="native",
            filter_action="native"
        )
    
    def _create_sample_metadata_table(self) -> html.Div:
        """Create sample metadata table."""
        if not self.current_data:
            return html.P("No data loaded")
        
        return dash_table.DataTable(
            data=self.current_data.sample_metadata.to_dict('records'),
            columns=[{"name": col, "id": col} for col in self.current_data.sample_metadata.columns],
            style_cell={"textAlign": "left", "padding": "10px"},
            style_header={"backgroundColor": "#f0f0f0", "fontWeight": "bold"},
            page_size=20,
            sort_action="native",
            filter_action="native"
        )
    
    def _create_gene_metadata_table(self) -> html.Div:
        """Create gene metadata table."""
        if not self.current_data:
            return html.P("No data loaded")
        
        # Show only first 100 genes for performance
        gene_data = self.current_data.gene_metadata.head(100)
        
        return dash_table.DataTable(
            data=gene_data.to_dict('records'),
            columns=[{"name": col, "id": col} for col in gene_data.columns],
            style_cell={"textAlign": "left", "padding": "10px"},
            style_header={"backgroundColor": "#f0f0f0", "fontWeight": "bold"},
            page_size=20,
            sort_action="native",
            filter_action="native"
        )
    
    def run(self, debug: bool = True, port: int = 8052):
        """
        Run the dashboard.
        
        Args:
            debug: Enable debug mode
            port: Port to run the app on
        """
        logger.info(f"Starting Microarray Analyzer Dashboard on port {port}")
        self.app.run_server(debug=debug, port=port)


# CSS Styles
custom_css = """
.main-container {
    fontFamily: 'Inter', sans-serif;
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
}

.header {
    text-align: center;
    margin-bottom: 30px;
    padding: 20px;
    background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%);
    color: white;
    border-radius: 10px;
}

.header-title {
    margin: 0;
    font-size: 2.5em;
    font-weight: 700;
}

.header-subtitle {
    margin: 10px 0 0 0;
    font-size: 1.1em;
    opacity: 0.9;
}

.upload-panel, .summary-panel, .controls-panel, .visualization-panel, .table-panel, .export-panel, .statistics-panel {
    margin-bottom: 20px;
    padding: 20px;
    background: white;
    border-radius: 8px;
    border: 1px solid #e9ecef;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.upload-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 15px;
    margin-bottom: 20px;
}

.upload-group {
    display: flex;
    flex-direction: column;
}

.upload-group label {
    font-weight: 500;
    margin-bottom: 5px;
    color: #495057;
}

.load-button, .sample-button {
    background: #9b59b6;
    color: white;
    border: none;
    padding: 12px 24px;
    border-radius: 5px;
    cursor: pointer;
    font-weight: 500;
    font-size: 1.1em;
    transition: background-color 0.2s;
    margin: 5px;
}

.load-button:hover, .sample-button:hover {
    background: #8e44ad;
}

.data-summary {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 5px;
    border-left: 4px solid #9b59b6;
}

.controls-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    margin-bottom: 20px;
}

.control-group {
    display: flex;
    flex-direction: column;
}

.control-group label {
    font-weight: 500;
    margin-bottom: 5px;
    color: #495057;
}

.button-group {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}

.analyze-button {
    background: #3498db;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 5px;
    cursor: pointer;
    font-weight: 500;
    transition: background-color 0.2s;
}

.analyze-button:hover {
    background: #2980b9;
}

.visualization-content {
    margin-top: 20px;
    background: white;
    border-radius: 8px;
    border: 1px solid #e9ecef;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    overflow: hidden;
}

.table-controls {
    display: flex;
    gap: 10px;
    align-items: center;
    margin-bottom: 15px;
}

.export-controls {
    display: flex;
    gap: 10px;
    align-items: center;
    margin-bottom: 15px;
}

.export-button {
    background: #27ae60;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 5px;
    cursor: pointer;
    font-weight: 500;
}

.export-button:hover {
    background: #229954;
}

.export-data {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 5px;
    border: 1px solid #e9ecef;
    max-height: 400px;
    overflow-y: auto;
    fontFamily: 'Courier New', monospace;
    font-size: 0.9em;
}

.statistics-display {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 5px;
}

.error-message {
    color: #dc3545;
    background: #f8d7da;
    padding: 10px;
    border-radius: 5px;
    border: 1px solid #f5c6cb;
}
"""


def create_microarray_dashboard() -> MicroarrayDashboard:
    """
    Create and return a microarray analysis dashboard instance.
    
    Returns:
        MicroarrayDashboard instance
    """
    return MicroarrayDashboard()


if __name__ == "__main__":
    # Create and run the dashboard
    dashboard = create_microarray_dashboard()
    
    # Add custom CSS
    dashboard.app.index_string = f"""
    <!DOCTYPE html>
    <html>
        <head>
            {{%metas%}}
            <title>{{%title%}}</title>
            {{%favicon%}}
            {{%css%}}
            <style>{custom_css}</style>
        </head>
        <body>
            {{%app_entry%}}
            <footer>
                {{%config%}}
                {{%scripts%}}
                {{%renderer%}}
            </footer>
        </body>
    </html>
    """
    
    dashboard.run(debug=True, port=8052)
