"""
DNA Sequence Analyzer Dashboard

This module provides an interactive dashboard for DNA sequence analysis,
allowing users to input sequences, configure analysis parameters, and
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

from .analyzer import DNAAnalyzer, AnalysisConfig
from .utils import DNAUtils


class DNADashboard:
    """
    Interactive dashboard for DNA sequence analysis.
    
    This class provides methods to create and manage an interactive
    web-based dashboard for DNA sequence analysis.
    """
    
    def __init__(self, app: dash.Dash):
        """
        Initialize the DNA dashboard.
        
        Args:
            app (dash.Dash): Dash application instance
        """
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.analyzer = DNAAnalyzer()
        self.utils = DNAUtils()
        
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
                html.H1("DNA Sequence Analyzer", className="text-center mb-4"),
                html.P("Comprehensive DNA sequence analysis tools for cancer genomics research", 
                       className="text-center text-muted")
            ], className="jumbotron"),
            
            # Main content
            html.Div([
                # Input section
                html.Div([
                    html.H3("Sequence Input"),
                    html.Div([
                        html.Label("Sequence Name:", className="form-label"),
                        dcc.Input(
                            id='sequence-name',
                            type='text',
                            placeholder='Enter sequence name...',
                            className="form-control mb-3"
                        ),
                        html.Label("DNA Sequence:", className="form-label"),
                        dcc.Textarea(
                            id='dna-sequence-input',
                            placeholder='Enter DNA sequence here (ATCG)...',
                            style={'width': '100%', 'height': 200},
                            className="form-control mb-3"
                        ),
                        html.Div([
                            html.Button('Analyze Sequence', id='analyze-btn', 
                                      className="btn btn-primary me-2"),
                            html.Button('Clear', id='clear-btn', 
                                      className="btn btn-secondary")
                        ])
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
                                    {'label': 'Calculate Statistics', 'value': 'statistics'},
                                    {'label': 'Find ORFs', 'value': 'orfs'},
                                    {'label': 'Translate Sequences', 'value': 'translation'},
                                    {'label': 'Find Restriction Sites', 'value': 'restriction'},
                                    {'label': 'Calculate Codon Usage', 'value': 'codon_usage'}
                                ],
                                value=['statistics', 'orfs', 'translation'],
                                className="form-check"
                            )
                        ], className="col-md-6"),
                        html.Div([
                            html.Label("Minimum ORF Length:", className="form-label"),
                            dcc.Input(
                                id='min-orf-length',
                                type='number',
                                value=150,
                                min=30,
                                max=1000,
                                className="form-control"
                            )
                        ], className="col-md-6")
                    ], className="row")
                ], className="card mb-4"),
                
                # Results section
                html.Div([
                    html.H3("Analysis Results"),
                    html.Div(id='dna-analysis-results')
                ], className="card mb-4"),
                
                # Visualizations
                html.Div([
                    html.H3("Visualizations"),
                    html.Div(id='dna-visualizations')
                ], className="card mb-4")
                
            ], className="container-fluid")
        ])
    
    def _register_callbacks(self):
        """Register dashboard callbacks."""
        
        @self.app.callback(
            [Output('dna-analysis-results', 'children'),
             Output('dna-visualizations', 'children')],
            [Input('analyze-btn', 'n_clicks')],
            [State('dna-sequence-input', 'value'),
             State('sequence-name', 'value'),
             State('analysis-options', 'value'),
             State('min-orf-length', 'value')]
        )
        def analyze_sequence(n_clicks, sequence, name, options, min_orf_length):
            """Analyze DNA sequence and display results."""
            if n_clicks == 0 or not sequence:
                return html.P("Enter a sequence and click 'Analyze Sequence'"), html.Div()
            
            try:
                # Configure analysis
                config = AnalysisConfig(
                    calculate_statistics='statistics' in options,
                    find_orfs='orfs' in options,
                    translate_sequences='translation' in options,
                    find_restriction_sites='restriction' in options,
                    calculate_codon_usage='codon_usage' in options,
                    min_orf_length=min_orf_length or 150
                )
                
                # Update analyzer config
                self.analyzer.config = config
                
                # Perform analysis
                sequence_name = name or "Unknown Sequence"
                results = self.analyzer.analyze_sequence(sequence, sequence_name)
                
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
            [Output('dna-sequence-input', 'value'),
             Output('sequence-name', 'value')],
            [Input('clear-btn', 'n_clicks')]
        )
        def clear_inputs(n_clicks):
            """Clear input fields."""
            if n_clicks:
                return "", ""
            return dash.no_update, dash.no_update
    
    def _create_results_display(self, results: Dict[str, Any]) -> html.Div:
        """Create results display components."""
        if not results.get('valid', False):
            return html.Div([
                html.H4("Invalid Sequence", className="text-danger"),
                html.P(f"Errors: {', '.join(results.get('errors', []))}")
            ])
        
        components = []
        
        # Basic information
        components.append(html.H4("Sequence Information"))
        components.append(html.P(f"Name: {results.get('sequence_name', 'Unknown')}"))
        components.append(html.P(f"Length: {results.get('sequence_length', 0)} bp"))
        
        if results.get('warnings'):
            components.append(html.Div([
                html.H5("Warnings", className="text-warning"),
                html.Ul([html.Li(warning) for warning in results['warnings']])
            ]))
        
        # Statistics
        if 'statistics' in results:
            stats = results['statistics']
            components.append(html.H4("Sequence Statistics"))
            
            # Create statistics table
            stats_data = [
                {'Metric': 'GC Content', 'Value': f"{stats.get('gc_content', 0):.2f}%"},
                {'Metric': 'AT Content', 'Value': f"{stats.get('at_content', 0):.2f}%"},
                {'Metric': 'Molecular Weight', 'Value': f"{stats.get('molecular_weight', 0):.2f} Da" if stats.get('molecular_weight') else 'N/A'},
                {'Metric': 'Complexity', 'Value': f"{stats.get('complexity', 0):.3f}"}
            ]
            
            components.append(dash_table.DataTable(
                data=stats_data,
                columns=[{"name": i, "id": i} for i in stats_data[0].keys()],
                style_cell={'textAlign': 'left'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
            ))
        
        # ORFs
        if 'orfs' in results and results['orfs']:
            components.append(html.H4("Open Reading Frames"))
            orfs_data = []
            for i, orf in enumerate(results['orfs'][:10]):  # Show top 10
                orfs_data.append({
                    'Frame': orf['frame'],
                    'Start': orf['start'],
                    'End': orf['end'],
                    'Length': orf['length'],
                    'Start Codon': orf['start_codon'],
                    'Stop Codon': orf['stop_codon']
                })
            
            components.append(dash_table.DataTable(
                data=orfs_data,
                columns=[{"name": i, "id": i} for i in orfs_data[0].keys()],
                style_cell={'textAlign': 'left'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                page_size=10
            ))
        
        # Restriction sites
        if 'restriction_sites' in results and results['restriction_sites']:
            components.append(html.H4("Restriction Sites"))
            sites_data = []
            for site in results['restriction_sites']:
                sites_data.append({
                    'Enzyme': site['enzyme'],
                    'Recognition Sequence': site['recognition_sequence'],
                    'Position': site['position'],
                    'Cut Position': site['cut_position']
                })
            
            components.append(dash_table.DataTable(
                data=sites_data,
                columns=[{"name": i, "id": i} for i in sites_data[0].keys()],
                style_cell={'textAlign': 'left'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
            ))
        
        return html.Div(components)
    
    def _create_visualizations(self, results: Dict[str, Any]) -> html.Div:
        """Create visualization components."""
        components = []
        
        # GC content visualization
        if 'statistics' in results and 'gc_content' in results['statistics']:
            gc_content = results['statistics']['gc_content']
            
            fig = go.Figure(data=[
                go.Bar(x=['GC Content'], y=[gc_content], 
                      marker_color='lightblue', text=[f'{gc_content:.1f}%'],
                      textposition='auto')
            ])
            fig.add_hline(y=50, line_dash="dash", line_color="red", 
                         annotation_text="50% GC")
            fig.update_layout(
                title="GC Content",
                yaxis_title="GC Content (%)",
                showlegend=False
            )
            
            components.append(dcc.Graph(figure=fig))
        
        # Nucleotide composition
        if 'statistics' in results and 'nucleotide_counts' in results['statistics']:
            nuc_counts = results['statistics']['nucleotide_counts']
            
            fig = go.Figure(data=[
                go.Bar(x=list(nuc_counts.keys()), y=list(nuc_counts.values()),
                      marker_color=['red', 'blue', 'green', 'orange'])
            ])
            fig.update_layout(
                title="Nucleotide Composition",
                xaxis_title="Nucleotide",
                yaxis_title="Count"
            )
            
            components.append(dcc.Graph(figure=fig))
        
        # ORF length distribution
        if 'orfs' in results and results['orfs']:
            orf_lengths = [orf['length'] for orf in results['orfs']]
            
            fig = go.Figure(data=[
                go.Histogram(x=orf_lengths, nbinsx=20, marker_color='lightgreen')
            ])
            fig.update_layout(
                title="ORF Length Distribution",
                xaxis_title="ORF Length (bp)",
                yaxis_title="Frequency"
            )
            
            components.append(dcc.Graph(figure=fig))
        
        return html.Div(components)


# Legacy function for backward compatibility
def register_callbacks(app):
    """Register callbacks for this module (legacy function)."""
    dashboard = DNADashboard(app)
    return dashboard

# Legacy layout for backward compatibility
layout = html.Div([
    html.H1("DNA Sequence Analyzer"),
    html.P("This module provides comprehensive DNA sequence analysis tools."),
    html.Div([
        html.Label("Input DNA Sequence:"),
        dcc.Textarea(
            id='dna-input',
            placeholder='Enter DNA sequence here...',
            style={'width': '100%', 'height': 200}
        ),
        html.Button('Analyze', id='analyze-btn', n_clicks=0),
        html.Div(id='dna-output')
    ])
])
