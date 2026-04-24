"""
Phylogenetic Tree Viewer Dashboard

This module provides an interactive dashboard for phylogenetic tree construction
and visualization, allowing users to upload sequences, configure tree building
parameters, and visualize results through a web-based interface.
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

from .tree_builder import PhylogeneticTreeBuilder, TreeConstructionConfig


class TreeDashboard:
    """
    Interactive dashboard for phylogenetic tree construction and visualization.
    
    This class provides methods to create and manage an interactive
    web-based dashboard for phylogenetic analysis.
    """
    
    def __init__(self, app: dash.Dash):
        """
        Initialize the tree dashboard.
        
        Args:
            app (dash.Dash): Dash application instance
        """
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.builder = PhylogeneticTreeBuilder()
        
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
                html.H1("Phylogenetic Tree Viewer", className="text-center mb-4"),
                html.P("Comprehensive phylogenetic tree construction and visualization tools for cancer genomics research", 
                       className="text-center text-muted")
            ], className="jumbotron"),
            
            # Main content
            html.Div([
                # Sequence upload section
                html.Div([
                    html.H3("Sequence Data Upload"),
                    html.Div([
                        html.Label("Upload Multiple Sequence Alignment (FASTA/PHYLIP/CLUSTAL):", className="form-label"),
                        dcc.Upload(
                            id='upload-alignment',
                            children=html.Div([
                                'Drag and Drop or ',
                                html.A('Select Alignment File')
                            ]),
                            style={
                                'width': '100%', 'height': '60px', 'lineHeight': '60px',
                                'borderWidth': '1px', 'borderStyle': 'dashed',
                                'borderRadius': '5px', 'textAlign': 'center'
                            },
                            multiple=False
                        ),
                        html.Div(id='tree-upload-status', className="mt-3")
                    ])
                ], className="card mb-4"),
                
                # Tree construction configuration
                html.Div([
                    html.H3("Tree Construction Configuration"),
                    html.Div([
                        html.Div([
                            html.Label("Tree Building Method:", className="form-label"),
                            dcc.Dropdown(
                                id='tree-method',
                                options=[
                                    {'label': 'Neighbor Joining', 'value': 'neighbor_joining'},
                                    {'label': 'UPGMA', 'value': 'upgma'},
                                    {'label': 'Parsimony', 'value': 'parsimony'}
                                ],
                                value='neighbor_joining',
                                className="mb-2"
                            ),
                            html.Label("Distance Model:", className="form-label"),
                            dcc.Dropdown(
                                id='distance-model',
                                options=[
                                    {'label': 'Identity', 'value': 'identity'},
                                    {'label': 'Hamming', 'value': 'hamming'},
                                    {'label': 'Jukes-Cantor', 'value': 'jukes_cantor'},
                                    {'label': 'Kimura 2-Parameter', 'value': 'kimura'}
                                ],
                                value='identity',
                                className="mb-2"
                            )
                        ], className="col-md-4"),
                        html.Div([
                            html.Label("Bootstrap Replicates:", className="form-label"),
                            dcc.Input(
                                id='bootstrap-replicates',
                                type='number',
                                value=100,
                                min=0,
                                max=1000,
                                className="form-control mb-2"
                            ),
                            html.Label("Bootstrap Threshold:", className="form-label"),
                            dcc.Input(
                                id='bootstrap-threshold',
                                type='number',
                                value=0.7,
                                min=0.0,
                                max=1.0,
                                step=0.1,
                                className="form-control mb-2"
                            )
                        ], className="col-md-4"),
                        html.Div([
                            dcc.Checklist(
                                id='tree-options',
                                options=[
                                    {'label': 'Generate Consensus Tree', 'value': 'consensus'},
                                    {'label': 'Calculate Support Values', 'value': 'support'},
                                    {'label': 'Optimize Branch Lengths', 'value': 'optimize_branches'},
                                    {'label': 'Optimize Topology', 'value': 'optimize_topology'}
                                ],
                                value=['consensus', 'support'],
                                className="form-check"
                            )
                        ], className="col-md-4")
                    ], className="row"),
                    html.Div([
                        html.Button('Build Tree', id='build-tree-btn', 
                                  className="btn btn-primary me-2"),
                        html.Button('Clear Data', id='clear-data-btn', 
                                  className="btn btn-secondary")
                    ], className="mt-3")
                ], className="card mb-4"),
                
                # Alignment preview
                html.Div([
                    html.H3("Alignment Preview"),
                    html.Div(id='tree-alignment-preview')
                ], className="card mb-4"),
                
                # Tree construction results
                html.Div([
                    html.H3("Tree Construction Results"),
                    html.Div(id='tree-results')
                ], className="card mb-4"),
                
                # Tree visualization
                html.Div([
                    html.H3("Tree Visualization"),
                    html.Div(id='tree-visualization')
                ], className="card mb-4"),
                
                # Tree comparison
                html.Div([
                    html.H3("Tree Comparison"),
                    html.Div([
                        html.Div([
                            html.Label("Select Tree 1:", className="form-label"),
                            dcc.Dropdown(id='tree1-select', className="mb-2"),
                            html.Label("Select Tree 2:", className="form-label"),
                            dcc.Dropdown(id='tree2-select', className="mb-2"),
                            html.Button('Compare Trees', id='compare-trees-btn', 
                                      className="btn btn-info")
                        ], className="col-md-6"),
                        html.Div([
                            html.Div(id='tree-comparison-results')
                        ], className="col-md-6")
                    ], className="row")
                ], className="card mb-4")
                
            ], className="container-fluid")
        ])
    
    def _register_callbacks(self):
        """Register dashboard callbacks."""
        
        @self.app.callback(
            [Output('tree-upload-status', 'children'),
             Output('tree-alignment-preview', 'children')],
            [Input('upload-alignment', 'contents')],
            [State('upload-alignment', 'filename')]
        )
        def handle_alignment_upload(contents, filename):
            """Handle alignment file upload."""
            if contents:
                try:
                    content_type, content_string = contents.split(',')
                    decoded = base64.b64decode(content_string)
                    
                    # Determine file format
                    if filename.endswith('.fasta') or filename.endswith('.fa'):
                        file_format = 'fasta'
                    elif filename.endswith('.phylip'):
                        file_format = 'phylip'
                    elif filename.endswith('.clustal'):
                        file_format = 'clustal'
                    else:
                        file_format = 'fasta'  # default
                    
                    # Save to temporary file
                    temp_file = f"temp_{filename}"
                    with open(temp_file, 'wb') as f:
                        f.write(decoded)
                    
                    # Load sequences
                    result = self.builder.load_sequences(temp_file)
                    
                    # Clean up temp file
                    import os
                    os.remove(temp_file)
                    
                    if result['success']:
                        # Create alignment preview
                        preview = self._create_alignment_preview()
                        
                        return html.Div([
                            html.P(f"Successfully loaded {result['sequences']} sequences, length {result['alignment_length']}", 
                                  className="text-success")
                        ]), preview
                    else:
                        return html.Div([
                            html.P(f"Error loading alignment: {result['error']}", 
                                  className="text-danger")
                        ]), html.Div()
                
                except Exception as e:
                    return html.Div([
                        html.P(f"Error processing uploaded file: {str(e)}", className="text-danger")
                    ]), html.Div()
            
            return "", html.Div()
        
        @self.app.callback(
            [Output('tree-results', 'children'),
             Output('tree-visualization', 'children'),
             Output('tree1-select', 'options'),
             Output('tree2-select', 'options')],
            [Input('build-tree-btn', 'n_clicks')],
            [State('tree-method', 'value'),
             State('distance-model', 'value'),
             State('bootstrap-replicates', 'value'),
             State('bootstrap-threshold', 'value'),
             State('tree-options', 'value')]
        )
        def build_tree(n_clicks, method, distance_model, bootstrap_replicates, 
                      bootstrap_threshold, options):
            """Build phylogenetic tree."""
            if n_clicks == 0 or self.builder.sequence_alignment is None:
                return html.P("Upload alignment data and click 'Build Tree'"), html.Div(), [], []
            
            try:
                # Configure tree construction
                config = TreeConstructionConfig(
                    method=method or 'neighbor_joining',
                    distance_model=distance_model or 'identity',
                    bootstrap_replicates=bootstrap_replicates or 100,
                    bootstrap_threshold=bootstrap_threshold or 0.7,
                    generate_consensus_tree='consensus' in options,
                    calculate_support_values='support' in options,
                    optimize_branch_lengths='optimize_branches' in options,
                    optimize_topology='optimize_topology' in options
                )
                
                # Update builder config
                self.builder.config = config
                
                # Build tree
                result = self.builder.build_tree()
                
                if result['success']:
                    # Create results display
                    results_display = self._create_tree_results_display(result)
                    
                    # Create tree visualization
                    visualization = self._create_tree_visualization(result['tree_name'])
                    
                    # Update tree selection options
                    tree_summary = self.builder.get_tree_summary()
                    tree_options = [{'label': name, 'value': name} for name in tree_summary['tree_names']]
                    
                    return results_display, visualization, tree_options, tree_options
                else:
                    return html.Div([
                        html.H4("Tree Construction Error", className="text-danger"),
                        html.P(result['error'])
                    ]), html.Div(), [], []
                    
            except Exception as e:
                error_msg = f"Tree construction failed: {str(e)}"
                self.logger.error(error_msg)
                return html.Div([
                    html.H4("Tree Construction Error", className="text-danger"),
                    html.P(error_msg)
                ]), html.Div(), [], []
        
        @self.app.callback(
            [Output('tree-comparison-results', 'children')],
            [Input('compare-trees-btn', 'n_clicks')],
            [State('tree1-select', 'value'),
             State('tree2-select', 'value')]
        )
        def compare_trees(n_clicks, tree1, tree2):
            """Compare two phylogenetic trees."""
            if n_clicks == 0 or not tree1 or not tree2:
                return [html.P("Select two trees to compare")]
            
            if tree1 == tree2:
                return [html.P("Please select two different trees for comparison")]
            
            try:
                comparison = self.builder.compare_trees(tree1, tree2)
                
                if 'error' in comparison:
                    return [html.Div([
                        html.H5("Comparison Error", className="text-danger"),
                        html.P(comparison['error'])
                    ])]
                
                # Create comparison display
                comparison_display = self._create_tree_comparison_display(comparison)
                return [comparison_display]
                
            except Exception as e:
                return [html.Div([
                    html.H5("Comparison Error", className="text-danger"),
                    html.P(str(e))
                ])]
        
        @self.app.callback(
            [Output('upload-alignment', 'contents')],
            [Input('clear-data-btn', 'n_clicks')]
        )
        def clear_data(n_clicks):
            """Clear uploaded data."""
            if n_clicks:
                self.builder.sequence_alignment = None
                self.builder.clear_trees()
                return [None]
            return [dash.no_update]
    
    def _create_alignment_preview(self) -> html.Div:
        """Create alignment preview display."""
        if self.builder.sequence_alignment is None:
            return html.Div()
        
        alignment = self.builder.sequence_alignment
        
        # Create preview table
        preview_data = []
        for i, record in enumerate(alignment[:10]):  # Show first 10 sequences
            sequence = str(record.seq)
            preview_data.append({
                'Sequence': record.id,
                'Length': len(sequence),
                'Preview': sequence[:50] + '...' if len(sequence) > 50 else sequence
            })
        
        return html.Div([
            html.H5("Alignment Summary"),
            html.P(f"Total sequences: {len(alignment)}"),
            html.P(f"Alignment length: {alignment.get_alignment_length()}"),
            dash_table.DataTable(
                data=preview_data,
                columns=[{"name": i, "id": i} for i in preview_data[0].keys()],
                style_cell={'textAlign': 'left', 'fontSize': 12},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                page_size=10
            )
        ])
    
    def _create_tree_results_display(self, result: Dict[str, Any]) -> html.Div:
        """Create tree construction results display."""
        components = []
        
        # Basic information
        components.append(html.H4("Tree Construction Summary"))
        components.append(html.P(f"Tree Name: {result['tree_name']}"))
        components.append(html.P(f"Method: {result['method']}"))
        components.append(html.P(f"Construction Time: {result['construction_time']:.2f} seconds"))
        
        # Tree statistics
        if 'tree_statistics' in result:
            stats = result['tree_statistics']
            components.append(html.H4("Tree Statistics"))
            
            stats_data = [
                {'Metric': 'Tree Length', 'Value': f"{stats.get('tree_length', 0):.3f}"},
                {'Metric': 'Number of Tips', 'Value': stats.get('number_of_tips', 0)},
                {'Metric': 'Number of Internal Nodes', 'Value': stats.get('number_of_internal_nodes', 0)},
                {'Metric': 'Average Branch Length', 'Value': f"{stats.get('average_branch_length', 0):.3f}"},
                {'Metric': 'Min Branch Length', 'Value': f"{stats.get('min_branch_length', 0):.3f}"},
                {'Metric': 'Max Branch Length', 'Value': f"{stats.get('max_branch_length', 0):.3f}"}
            ]
            
            components.append(dash_table.DataTable(
                data=stats_data,
                columns=[{"name": i, "id": i} for i in stats_data[0].keys()],
                style_cell={'textAlign': 'left'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
            ))
        
        # Bootstrap results
        if 'bootstrap_results' in result and result['bootstrap_results']:
            bootstrap = result['bootstrap_results']
            if 'error' not in bootstrap:
                components.append(html.H4("Bootstrap Analysis"))
                components.append(html.P(f"Bootstrap Replicates: {bootstrap['bootstrap_replicates']}"))
                components.append(html.P(f"High Support Nodes: {bootstrap['high_support_nodes']}"))
                
                if 'support_values' in bootstrap:
                    support_data = []
                    for node, support in bootstrap['support_values'].items():
                        support_data.append({
                            'Node': node,
                            'Bootstrap Support': f"{support:.3f}"
                        })
                    
                    if support_data:
                        components.append(dash_table.DataTable(
                            data=support_data,
                            columns=[{"name": i, "id": i} for i in support_data[0].keys()],
                            style_cell={'textAlign': 'left', 'fontSize': 12},
                            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                            page_size=10
                        ))
        
        return html.Div(components)
    
    def _create_tree_visualization(self, tree_name: str) -> html.Div:
        """Create tree visualization display."""
        try:
            # Create tree visualization
            viz_path = self.builder.create_tree_visualization(tree_name)
            
            # Display the image
            return html.Div([
                html.H4(f"Tree Visualization: {tree_name}"),
                html.Img(src=f"data:image/png;base64,{self._encode_image(viz_path)}", 
                        style={'width': '100%', 'height': 'auto'})
            ])
            
        except Exception as e:
            return html.Div([
                html.H4("Visualization Error", className="text-danger"),
                html.P(str(e))
            ])
    
    def _create_tree_comparison_display(self, comparison: Dict[str, Any]) -> html.Div:
        """Create tree comparison display."""
        components = []
        
        components.append(html.H5("Tree Comparison Results"))
        components.append(html.P(f"Robinson-Foulds Distance: {comparison['robinson_foulds_distance']}"))
        
        # Tree 1 statistics
        tree1_stats = comparison['tree1']['statistics']
        components.append(html.H6("Tree 1 Statistics"))
        components.append(html.P(f"Tree Length: {tree1_stats['tree_length']:.3f}"))
        components.append(html.P(f"Number of Tips: {tree1_stats['number_of_tips']}"))
        
        # Tree 2 statistics
        tree2_stats = comparison['tree2']['statistics']
        components.append(html.H6("Tree 2 Statistics"))
        components.append(html.P(f"Tree Length: {tree2_stats['tree_length']:.3f}"))
        components.append(html.P(f"Number of Tips: {tree2_stats['number_of_tips']}"))
        
        return html.Div(components)
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image file to base64 string."""
        try:
            with open(image_path, 'rb') as f:
                encoded = base64.b64encode(f.read()).decode()
            return encoded
        except Exception as e:
            self.logger.error(f"Error encoding image: {e}")
            return ""


# Legacy function for backward compatibility
def register_callbacks(app):
    """Register callbacks for this module (legacy function)."""
    dashboard = TreeDashboard(app)
    return dashboard

# Legacy layout for backward compatibility
layout = html.Div([
    html.H1("Phylogenetic Tree Viewer"),
    html.P("This module provides phylogenetic tree construction and visualization tools."),
    html.Div([
        html.Label("Upload Multiple Sequence Alignment:"),
        dcc.Upload(
            id='upload-data',
            children=html.Div(['Drag and Drop or ', html.A('Select Files')]),
            style={'width': '100%', 'height': '60px', 'lineHeight': '60px', 'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px', 'textAlign': 'center'},
            multiple=False
        ),
        html.Div(id='tree-output')
    ])
])
