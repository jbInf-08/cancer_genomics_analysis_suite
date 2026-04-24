"""
Protein Sequence Viewer Dashboard

This module provides an interactive dashboard for protein sequence analysis,
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

from .viewer import ProteinViewer, ProteinAnalysisConfig


class ProteinDashboard:
    """
    Interactive dashboard for protein sequence analysis.
    
    This class provides methods to create and manage an interactive
    web-based dashboard for protein sequence analysis.
    """
    
    def __init__(self, app: dash.Dash):
        """
        Initialize the protein dashboard.
        
        Args:
            app (dash.Dash): Dash application instance
        """
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.viewer = ProteinViewer()
        
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
                html.H1("Protein Sequence Viewer", className="text-center mb-4"),
                html.P("Comprehensive protein sequence analysis tools for cancer genomics research", 
                       className="text-center text-muted")
            ], className="jumbotron"),
            
            # Main content
            html.Div([
                # Input section
                html.Div([
                    html.H3("Protein Sequence Input"),
                    html.Div([
                        html.Label("Sequence Name:", className="form-label"),
                        dcc.Input(
                            id='protein-sequence-name',
                            type='text',
                            placeholder='Enter protein sequence name...',
                            className="form-control mb-3"
                        ),
                        html.Label("Protein Sequence:", className="form-label"),
                        dcc.Textarea(
                            id='protein-sequence-input',
                            placeholder='Enter protein sequence here (single letter code)...',
                            style={'width': '100%', 'height': 200},
                            className="form-control mb-3"
                        ),
                        html.Div([
                            html.Button('Analyze Protein', id='analyze-protein-btn', 
                                      className="btn btn-primary me-2"),
                            html.Button('Clear', id='clear-protein-btn', 
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
                                id='protein-analysis-options',
                                options=[
                                    {'label': 'Calculate Statistics', 'value': 'statistics'},
                                    {'label': 'Find Motifs', 'value': 'motifs'},
                                    {'label': 'Predict Secondary Structure', 'value': 'secondary_structure'},
                                    {'label': 'Calculate Hydrophobicity', 'value': 'hydrophobicity'},
                                    {'label': 'Find Disulfide Bonds', 'value': 'disulfide_bonds'},
                                    {'label': 'Analyze Amino Acid Composition', 'value': 'composition'}
                                ],
                                value=['statistics', 'motifs', 'secondary_structure'],
                                className="form-check"
                            )
                        ], className="col-md-6"),
                        html.Div([
                            html.Label("Hydrophobicity Window Size:", className="form-label"),
                            dcc.Input(
                                id='hydrophobicity-window',
                                type='number',
                                value=9,
                                min=3,
                                max=21,
                                step=2,
                                className="form-control"
                            )
                        ], className="col-md-6")
                    ], className="row")
                ], className="card mb-4"),
                
                # Results section
                html.Div([
                    html.H3("Analysis Results"),
                    html.Div(id='protein-analysis-results')
                ], className="card mb-4"),
                
                # Visualizations
                html.Div([
                    html.H3("Visualizations"),
                    html.Div(id='protein-visualizations')
                ], className="card mb-4")
                
            ], className="container-fluid")
        ])
    
    def _register_callbacks(self):
        """Register dashboard callbacks."""
        
        @self.app.callback(
            [Output('protein-analysis-results', 'children'),
             Output('protein-visualizations', 'children')],
            [Input('analyze-protein-btn', 'n_clicks')],
            [State('protein-sequence-input', 'value'),
             State('protein-sequence-name', 'value'),
             State('protein-analysis-options', 'value'),
             State('hydrophobicity-window', 'value')]
        )
        def analyze_protein(n_clicks, sequence, name, options, hydrophobicity_window):
            """Analyze protein sequence and display results."""
            if n_clicks == 0 or not sequence:
                return html.P("Enter a protein sequence and click 'Analyze Protein'"), html.Div()
            
            try:
                # Configure analysis
                config = ProteinAnalysisConfig(
                    calculate_statistics='statistics' in options,
                    find_motifs='motifs' in options,
                    predict_secondary_structure='secondary_structure' in options,
                    calculate_hydrophobicity='hydrophobicity' in options,
                    find_disulfide_bonds='disulfide_bonds' in options,
                    analyze_amino_acid_composition='composition' in options,
                    hydrophobicity_window=hydrophobicity_window or 9
                )
                
                # Update viewer config
                self.viewer.config = config
                
                # Perform analysis
                sequence_name = name or "Unknown Protein"
                results = self.viewer.analyze_sequence(sequence, sequence_name)
                
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
            [Output('protein-sequence-input', 'value'),
             Output('protein-sequence-name', 'value')],
            [Input('clear-protein-btn', 'n_clicks')]
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
        components.append(html.H4("Protein Information"))
        components.append(html.P(f"Name: {results.get('sequence_name', 'Unknown')}"))
        components.append(html.P(f"Length: {results.get('sequence_length', 0)} amino acids"))
        
        if results.get('warnings'):
            components.append(html.Div([
                html.H5("Warnings", className="text-warning"),
                html.Ul([html.Li(warning) for warning in results['warnings']])
            ]))
        
        # Statistics
        if 'statistics' in results:
            stats = results['statistics']
            components.append(html.H4("Protein Statistics"))
            
            # Create statistics table
            stats_data = [
                {'Metric': 'Molecular Weight', 'Value': f"{stats.get('molecular_weight', 0):.2f} Da"},
                {'Metric': 'Isoelectric Point', 'Value': f"{stats.get('isoelectric_point', 0):.2f}"},
                {'Metric': 'Aromaticity', 'Value': f"{stats.get('aromaticity', 0):.3f}"},
                {'Metric': 'Instability Index', 'Value': f"{stats.get('instability_index', 0):.2f}"},
                {'Metric': 'GRAVY', 'Value': f"{stats.get('gravy', 0):.3f}"},
                {'Metric': 'Net Charge (pH 7)', 'Value': f"{stats.get('charge_at_ph7', 0):.2f}"},
                {'Metric': 'Extinction Coefficient', 'Value': f"{stats.get('extinction_coefficient', 0):.0f} M⁻¹cm⁻¹"},
                {'Metric': 'Estimated Half-life', 'Value': stats.get('half_life', 'Unknown')}
            ]
            
            components.append(dash_table.DataTable(
                data=stats_data,
                columns=[{"name": i, "id": i} for i in stats_data[0].keys()],
                style_cell={'textAlign': 'left'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
            ))
        
        # Motifs
        if 'motifs' in results and results['motifs']:
            components.append(html.H4("Protein Motifs"))
            motifs_data = []
            for motif in results['motifs'][:10]:  # Show top 10
                motifs_data.append({
                    'Motif': motif['name'],
                    'Position': f"{motif['start']}-{motif['end']}",
                    'Sequence': motif['sequence'],
                    'Confidence': motif['confidence']
                })
            
            components.append(dash_table.DataTable(
                data=motifs_data,
                columns=[{"name": i, "id": i} for i in motifs_data[0].keys()],
                style_cell={'textAlign': 'left'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                page_size=10
            ))
        
        # Secondary structure
        if 'secondary_structure' in results:
            ss = results['secondary_structure']
            components.append(html.H4("Secondary Structure Prediction"))
            components.append(html.P(f"Predicted Structure: {ss.get('predicted_structure', 'Unknown')}"))
            components.append(html.P(f"Method: {ss.get('method', 'Unknown')}"))
            components.append(html.P(f"Confidence: {ss.get('confidence', 'Unknown')}"))
        
        # Disulfide bonds
        if 'disulfide_bonds' in results and results['disulfide_bonds']:
            components.append(html.H4("Disulfide Bonds"))
            bonds_data = []
            for bond in results['disulfide_bonds']:
                bonds_data.append({
                    'Cysteine 1': bond['cys1_position'],
                    'Cysteine 2': bond['cys2_position'],
                    'Distance': bond['distance'],
                    'Confidence': bond['confidence']
                })
            
            components.append(dash_table.DataTable(
                data=bonds_data,
                columns=[{"name": i, "id": i} for i in bonds_data[0].keys()],
                style_cell={'textAlign': 'left'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
            ))
        
        # Amino acid composition
        if 'amino_acid_composition' in results:
            comp = results['amino_acid_composition']
            components.append(html.H4("Amino Acid Composition"))
            
            # Property percentages
            if 'property_percentages' in comp:
                property_data = []
                for prop, percentage in comp['property_percentages'].items():
                    property_data.append({
                        'Property': prop.replace('_', ' ').title(),
                        'Percentage': f"{percentage:.1f}%"
                    })
                
                components.append(dash_table.DataTable(
                    data=property_data,
                    columns=[{"name": i, "id": i} for i in property_data[0].keys()],
                    style_cell={'textAlign': 'left'},
                    style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
                ))
        
        return html.Div(components)
    
    def _create_visualizations(self, results: Dict[str, Any]) -> html.Div:
        """Create visualization components."""
        components = []
        
        # Amino acid composition pie chart
        if 'amino_acid_composition' in results and 'amino_acid_percentages' in results['amino_acid_composition']:
            aa_percentages = results['amino_acid_composition']['amino_acid_percentages']
            
            fig = go.Figure(data=[go.Pie(
                labels=list(aa_percentages.keys()),
                values=list(aa_percentages.values()),
                hole=0.3
            )])
            fig.update_layout(
                title="Amino Acid Composition",
                showlegend=True
            )
            
            components.append(dcc.Graph(figure=fig))
        
        # Hydrophobicity profile
        if 'hydrophobicity' in results:
            hydro = results['hydrophobicity']
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=hydro['positions'],
                y=hydro['hydrophobicity_values'],
                mode='lines+markers',
                name='Hydrophobicity',
                line=dict(color='blue', width=2)
            ))
            fig.add_hline(y=0, line_dash="dash", line_color="red", 
                         annotation_text="Hydrophobic/Hydrophilic Boundary")
            fig.update_layout(
                title=f"Hydrophobicity Profile (window size: {hydro['window_size']})",
                xaxis_title="Position",
                yaxis_title="Hydrophobicity",
                showlegend=False
            )
            
            components.append(dcc.Graph(figure=fig))
        
        # Property composition bar chart
        if 'amino_acid_composition' in results and 'property_percentages' in results['amino_acid_composition']:
            properties = results['amino_acid_composition']['property_percentages']
            
            fig = go.Figure(data=[
                go.Bar(
                    x=list(properties.keys()),
                    y=list(properties.values()),
                    marker_color=['lightblue', 'lightgreen', 'lightcoral', 'lightyellow', 'lightpink', 'lightgray']
                )
            ])
            fig.update_layout(
                title="Amino Acid Property Composition",
                xaxis_title="Property",
                yaxis_title="Percentage (%)",
                xaxis_tickangle=-45
            )
            
            components.append(dcc.Graph(figure=fig))
        
        # Molecular weight comparison (if multiple sequences)
        if 'statistics' in results and 'molecular_weight' in results['statistics']:
            mw = results['statistics']['molecular_weight']
            
            fig = go.Figure(data=[
                go.Bar(x=['Molecular Weight'], y=[mw], 
                      marker_color='lightgreen', text=[f'{mw:.0f} Da'],
                      textposition='auto')
            ])
            fig.update_layout(
                title="Molecular Weight",
                yaxis_title="Molecular Weight (Da)",
                showlegend=False
            )
            
            components.append(dcc.Graph(figure=fig))
        
        return html.Div(components)


# Legacy function for backward compatibility
def register_callbacks(app):
    """Register callbacks for this module (legacy function)."""
    dashboard = ProteinDashboard(app)
    return dashboard

# Legacy layout for backward compatibility
layout = html.Div([
    html.H1("Protein Sequence Viewer"),
    html.P("This module provides comprehensive protein sequence analysis tools."),
    html.Div([
        html.Label("Input Protein Sequence:"),
        dcc.Textarea(
            id='protein-input',
            placeholder='Enter protein sequence here...',
            style={'width': '100%', 'height': 200}
        ),
        html.Button('Analyze', id='analyze-protein-btn', n_clicks=0),
        html.Div(id='protein-output')
    ])
])
