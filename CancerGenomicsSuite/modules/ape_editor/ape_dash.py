"""
A Plasmid Editor (APE) Integration Dashboard

Provides a Dash interface for plasmid design, analysis, and visualization.
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import json
import os
from typing import Dict, List, Any
import logging

from .ape_client import APEClient

logger = logging.getLogger(__name__)

# Initialize APE client
ape_client = APEClient()

# Dashboard layout
layout = html.Div([
    html.Div([
        html.H2("🧬 A Plasmid Editor (APE)", className="section-title"),
        html.P("Plasmid design, analysis, and visualization", className="section-description"),
    ], className="section-header"),
    
    # APE Status section
    html.Div([
        html.H3("APE Status", className="subsection-title"),
        html.Div([
            html.Div([
                html.Span("Status: ", className="status-label"),
                html.Span(id="ape-status", className="status-value"),
            ], className="status-item"),
            html.Div([
                html.Span("Version: ", className="status-label"),
                html.Span(id="ape-version", className="status-value"),
            ], className="status-item"),
            html.Div([
                html.Span("Path: ", className="status-label"),
                html.Span(id="ape-path", className="status-value"),
            ], className="status-item"),
        ], className="status-container"),
        html.Button("Refresh Status", id="refresh-ape-status", className="button secondary"),
    ], className="ape-status-section"),
    
    # Plasmid Management section
    html.Div([
        html.H3("Plasmid Management", className="subsection-title"),
        dcc.Tabs(id="plasmid-tabs", value="create", children=[
            dcc.Tab(label="Create Plasmid", value="create"),
            dcc.Tab(label="Load Plasmid", value="load"),
            dcc.Tab(label="Edit Features", value="features"),
        ]),
        html.Div(id="plasmid-content", className="plasmid-content"),
    ], className="plasmid-section"),
    
    # Analysis Tools section
    html.Div([
        html.H3("Analysis Tools", className="subsection-title"),
        dcc.Tabs(id="analysis-tabs", value="restriction", children=[
            dcc.Tab(label="Restriction Sites", value="restriction"),
            dcc.Tab(label="Primer Design", value="primers"),
            dcc.Tab(label="Cloning Simulation", value="cloning"),
        ]),
        html.Div(id="ape-analysis-content", className="analysis-content"),
    ], className="analysis-section"),
    
    # Export section
    html.Div([
        html.H3("Export Options", className="subsection-title"),
        html.Div([
            html.Div([
                html.Label("Export Format:", className="input-label"),
                dcc.Dropdown(
                    id="export-format",
                    options=[
                        {'label': 'GenBank', 'value': 'genbank'},
                        {'label': 'FASTA', 'value': 'fasta'},
                        {'label': 'APE', 'value': 'ape'},
                    ],
                    value='genbank',
                    className="dropdown"
                ),
            ], className="input-group"),
            html.Button("Export Plasmid", id="export-plasmid", className="button primary"),
            html.Div(id="export-results", className="export-results"),
        ], className="export-section"),
    ], className="export-section"),
    
    # Plasmid Visualization section
    html.Div([
        html.H3("Plasmid Visualization", className="subsection-title"),
        html.Div([
            html.Button("Generate Visualization", id="visualize-plasmid", className="button primary"),
            html.Div(id="plasmid-visualization", className="visualization-container"),
        ], className="visualization-section"),
    ], className="visualization-section"),
    
    # Results section
    html.Div([
        html.H3("Results", className="subsection-title"),
        html.Div(id="ape-results", className="results-container"),
    ], className="results-section"),
    
    # Hidden divs for storing data
    html.Div(id="ape-data", style={"display": "none"}),
])

def register_callbacks(app):
    """Register callbacks for the APE dashboard"""
    
    @app.callback(
        [Output("ape-status", "children"),
         Output("ape-version", "children"),
         Output("ape-path", "children")],
        [Input("refresh-ape-status", "n_clicks")]
    )
    def update_ape_status(n_clicks):
        if ape_client.is_available():
            status = "✅ Available"
            version = ape_client.get_version()
            path = ape_client.ape_path or "Not found"
        else:
            status = "❌ Not Available"
            version = "Not available"
            path = "Not found"
        
        return status, version, path
    
    @app.callback(
        Output("plasmid-content", "children"),
        [Input("plasmid-tabs", "value")]
    )
    def update_plasmid_content(active_tab):
        if active_tab == "create":
            return html.Div([
                html.H4("Create New Plasmid"),
                html.Div([
                    html.Label("Plasmid Name:", className="input-label"),
                    dcc.Input(
                        id="plasmid-name",
                        type="text",
                        placeholder="pUC19",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("DNA Sequence:", className="input-label"),
                    dcc.Textarea(
                        id="plasmid-sequence",
                        placeholder="ATCGATCGATCG...",
                        style={'width': '100%', 'height': '200px', 'fontFamily': 'monospace'},
                        className="textarea-field"
                    ),
                ], className="input-group"),
                html.Button("Create Plasmid", id="create-plasmid", className="button primary"),
                html.Div(id="create-plasmid-results", className="creation-results"),
            ])
        
        elif active_tab == "load":
            return html.Div([
                html.H4("Load Plasmid from File"),
                dcc.Upload(
                    id="plasmid-file-upload",
                    children=html.Div([
                        "Drag and Drop or ",
                        html.A("Select Plasmid File")
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
                ),
                html.Div([
                    html.Label("Or enter file path:", className="input-label"),
                    dcc.Input(
                        id="plasmid-file-path",
                        type="text",
                        placeholder="/path/to/plasmid.gb",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Button("Load Plasmid", id="load-plasmid", className="button primary"),
                html.Div(id="load-plasmid-results", className="load-results"),
            ])
        
        elif active_tab == "features":
            return html.Div([
                html.H4("Edit Features"),
                html.Div([
                    html.Label("Feature Name:", className="input-label"),
                    dcc.Input(
                        id="feature-name",
                        type="text",
                        placeholder="promoter",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Feature Type:", className="input-label"),
                    dcc.Dropdown(
                        id="feature-type",
                        options=[
                            {'label': 'Gene', 'value': 'gene'},
                            {'label': 'Promoter', 'value': 'promoter'},
                            {'label': 'Terminator', 'value': 'terminator'},
                            {'label': 'Origin of Replication', 'value': 'ori'},
                            {'label': 'Antibiotic Resistance', 'value': 'resistance'},
                            {'label': 'Multiple Cloning Site', 'value': 'mcs'},
                        ],
                        value='gene',
                        className="dropdown"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Start Position:", className="input-label"),
                    dcc.Input(
                        id="feature-start",
                        type="number",
                        placeholder="1",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("End Position:", className="input-label"),
                    dcc.Input(
                        id="feature-end",
                        type="number",
                        placeholder="100",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Button("Add Feature", id="add-feature", className="button primary"),
                html.Div(id="feature-results", className="feature-results"),
            ])
    
    @app.callback(
        Output("create-plasmid-results", "children"),
        [Input("create-plasmid", "n_clicks")],
        [State("plasmid-name", "value"),
         State("plasmid-sequence", "value")]
    )
    def create_plasmid(n_clicks, name, sequence):
        if n_clicks is None or not name or not sequence:
            return ""
        
        try:
            # Validate sequence (basic check)
            sequence_clean = sequence.upper().replace('\n', '').replace(' ', '')
            valid_bases = set('ATCGN')
            if not all(base in valid_bases for base in sequence_clean):
                return html.Div([
                    html.H5("❌ Invalid sequence"),
                    html.P("Sequence must contain only A, T, C, G, or N"),
                ])
            
            result = ape_client.create_plasmid(name, sequence_clean)
            
            if result['success']:
                return html.Div([
                    html.H5("✅ Plasmid created successfully"),
                    html.P(f"Name: {result['plasmid_name']}"),
                    html.P(f"Length: {result['sequence_length']} bp"),
                    html.P(f"File: {result['file_path']}"),
                ])
            else:
                return html.Div([
                    html.H5("❌ Failed to create plasmid"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error creating plasmid: {e}")
            return html.P(f"❌ Error: {str(e)}")
    
    @app.callback(
        Output("load-plasmid-results", "children"),
        [Input("load-plasmid", "n_clicks")],
        [State("plasmid-file-path", "value")]
    )
    def load_plasmid(n_clicks, file_path):
        if n_clicks is None or not file_path:
            return ""
        
        try:
            result = ape_client.load_plasmid(file_path)
            
            if result['success']:
                plasmid_data = result['plasmid_data']
                return html.Div([
                    html.H5("✅ Plasmid loaded successfully"),
                    html.P(f"Name: {plasmid_data.get('name', 'Unknown')}"),
                    html.P(f"Length: {len(plasmid_data.get('sequence', ''))} bp"),
                    html.P(f"Features: {len(plasmid_data.get('features', []))}"),
                    html.P(f"File: {result['file_path']}"),
                ])
            else:
                return html.Div([
                    html.H5("❌ Failed to load plasmid"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error loading plasmid: {e}")
            return html.P(f"❌ Error: {str(e)}")
    
    @app.callback(
        Output("ape-analysis-content", "children"),
        [Input("analysis-tabs", "value")]
    )
    def update_analysis_content(active_tab):
        if active_tab == "restriction":
            return html.Div([
                html.H4("Restriction Site Analysis"),
                html.Div([
                    html.Label("DNA Sequence:", className="input-label"),
                    dcc.Textarea(
                        id="restriction-sequence",
                        placeholder="ATCGATCGATCG...",
                        style={'width': '100%', 'height': '150px', 'fontFamily': 'monospace'},
                        className="textarea-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Restriction Enzymes (optional):", className="input-label"),
                    dcc.Dropdown(
                        id="restriction-enzymes",
                        options=[
                            {'label': 'EcoRI', 'value': 'EcoRI'},
                            {'label': 'BamHI', 'value': 'BamHI'},
                            {'label': 'HindIII', 'value': 'HindIII'},
                            {'label': 'XbaI', 'value': 'XbaI'},
                            {'label': 'SalI', 'value': 'SalI'},
                            {'label': 'PstI', 'value': 'PstI'},
                            {'label': 'KpnI', 'value': 'KpnI'},
                            {'label': 'SacI', 'value': 'SacI'},
                            {'label': 'XhoI', 'value': 'XhoI'},
                            {'label': 'NotI', 'value': 'NotI'},
                        ],
                        multi=True,
                        placeholder="Select enzymes (leave empty for all)",
                        className="dropdown"
                    ),
                ], className="input-group"),
                html.Button("Find Restriction Sites", id="find-restriction-sites", className="button primary"),
                html.Div(id="restriction-results", className="restriction-results"),
            ])
        
        elif active_tab == "primers":
            return html.Div([
                html.H4("Primer Design"),
                html.Div([
                    html.Label("DNA Sequence:", className="input-label"),
                    dcc.Textarea(
                        id="primer-sequence",
                        placeholder="ATCGATCGATCG...",
                        style={'width': '100%', 'height': '150px', 'fontFamily': 'monospace'},
                        className="textarea-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Target Region Start:", className="input-label"),
                    dcc.Input(
                        id="target-start",
                        type="number",
                        placeholder="100",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Target Region End:", className="input-label"),
                    dcc.Input(
                        id="target-end",
                        type="number",
                        placeholder="200",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Primer Length:", className="input-label"),
                    dcc.Input(
                        id="primer-length",
                        type="number",
                        value=20,
                        min=15,
                        max=30,
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Button("Design Primers", id="design-primers", className="button primary"),
                html.Div(id="primer-results", className="primer-results"),
            ])
        
        elif active_tab == "cloning":
            return html.Div([
                html.H4("Cloning Simulation"),
                html.Div([
                    html.Label("Vector Sequence:", className="input-label"),
                    dcc.Textarea(
                        id="vector-sequence",
                        placeholder="Vector DNA sequence...",
                        style={'width': '100%', 'height': '100px', 'fontFamily': 'monospace'},
                        className="textarea-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Insert Sequence:", className="input-label"),
                    dcc.Textarea(
                        id="insert-sequence",
                        placeholder="Insert DNA sequence...",
                        style={'width': '100%', 'height': '100px', 'fontFamily': 'monospace'},
                        className="textarea-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Vector Cut Position:", className="input-label"),
                    dcc.Input(
                        id="vector-cut",
                        type="number",
                        placeholder="100",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Insert Cut Position:", className="input-label"),
                    dcc.Input(
                        id="insert-cut",
                        type="number",
                        placeholder="50",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Button("Simulate Cloning", id="simulate-cloning", className="button primary"),
                html.Div(id="cloning-results", className="cloning-results"),
            ])
    
    @app.callback(
        Output("restriction-results", "children"),
        [Input("find-restriction-sites", "n_clicks")],
        [State("restriction-sequence", "value"),
         State("restriction-enzymes", "value")]
    )
    def find_restriction_sites(n_clicks, sequence, enzymes):
        if n_clicks is None or not sequence:
            return ""
        
        try:
            # Clean sequence
            sequence_clean = sequence.upper().replace('\n', '').replace(' ', '')
            
            result = ape_client.find_restriction_sites(sequence_clean, enzymes)
            
            if result['success']:
                sites = result['sites']
                if sites:
                    site_items = []
                    for site in sites[:20]:  # Show first 20 sites
                        site_item = html.Div([
                            html.Span(f"{site['enzyme']}:", className="enzyme-name"),
                            html.Span(f"Position {site['position']}", className="site-position"),
                            html.Span(f"({site['sequence']})", className="site-sequence"),
                        ], className="restriction-site")
                        site_items.append(site_item)
                    
                    return html.Div([
                        html.H5(f"🔍 Restriction Sites Found ({result['total_sites']})"),
                        html.P(f"Sequence length: {result['sequence_length']} bp"),
                        html.Div(site_items, className="sites-list")
                    ])
                else:
                    return html.Div([
                        html.H5("🔍 No restriction sites found"),
                        html.P(f"Sequence length: {result['sequence_length']} bp"),
                    ])
            else:
                return html.Div([
                    html.H5("❌ Failed to find restriction sites"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error finding restriction sites: {e}")
            return html.P(f"❌ Error: {str(e)}")
    
    @app.callback(
        Output("primer-results", "children"),
        [Input("design-primers", "n_clicks")],
        [State("primer-sequence", "value"),
         State("target-start", "value"),
         State("target-end", "value"),
         State("primer-length", "value")]
    )
    def design_primers(n_clicks, sequence, start, end, length):
        if n_clicks is None or not sequence or not start or not end:
            return ""
        
        try:
            # Clean sequence
            sequence_clean = sequence.upper().replace('\n', '').replace(' ', '')
            
            result = ape_client.design_primers(sequence_clean, (start, end), length)
            
            if result['success']:
                primers = result['primers']
                return html.Div([
                    html.H5("🧬 Primers Designed Successfully"),
                    html.Div([
                        html.H6("Forward Primer:"),
                        html.P(f"Sequence: {primers['forward']['sequence']}"),
                        html.P(f"Position: {primers['forward']['position']}"),
                        html.P(f"Length: {primers['forward']['length']} bp"),
                        html.P(f"Tm: {primers['forward']['tm']:.1f}°C"),
                        html.P(f"GC Content: {primers['forward']['gc_content']:.1f}%"),
                    ], className="primer-info"),
                    html.Div([
                        html.H6("Reverse Primer:"),
                        html.P(f"Sequence: {primers['reverse']['sequence']}"),
                        html.P(f"Position: {primers['reverse']['position']}"),
                        html.P(f"Length: {primers['reverse']['length']} bp"),
                        html.P(f"Tm: {primers['reverse']['tm']:.1f}°C"),
                        html.P(f"GC Content: {primers['reverse']['gc_content']:.1f}%"),
                    ], className="primer-info"),
                    html.Div([
                        html.H6("Target Region:"),
                        html.P(f"Sequence: {result['target_sequence']}"),
                        html.P(f"Length: {len(result['target_sequence'])} bp"),
                    ], className="target-info"),
                ])
            else:
                return html.Div([
                    html.H5("❌ Failed to design primers"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error designing primers: {e}")
            return html.P(f"❌ Error: {str(e)}")
    
    @app.callback(
        Output("cloning-results", "children"),
        [Input("simulate-cloning", "n_clicks")],
        [State("vector-sequence", "value"),
         State("insert-sequence", "value"),
         State("vector-cut", "value"),
         State("insert-cut", "value")]
    )
    def simulate_cloning(n_clicks, vector_seq, insert_seq, vector_cut, insert_cut):
        if n_clicks is None or not vector_seq or not insert_seq or not vector_cut or not insert_cut:
            return ""
        
        try:
            # Clean sequences
            vector_clean = vector_seq.upper().replace('\n', '').replace(' ', '')
            insert_clean = insert_seq.upper().replace('\n', '').replace(' ', '')
            
            result = ape_client.simulate_cloning(vector_clean, insert_clean, (vector_cut, insert_cut))
            
            if result['success']:
                return html.Div([
                    html.H5("🧬 Cloning Simulation Completed"),
                    html.Div([
                        html.P(f"Vector length: {result['vector_length']} bp"),
                        html.P(f"Insert length: {result['insert_length']} bp"),
                        html.P(f"Recombinant length: {result['recombinant_length']} bp"),
                        html.P(f"Vector cut position: {result['vector_site']}"),
                        html.P(f"Insert cut position: {result['insert_site']}"),
                    ], className="cloning-info"),
                    html.Div([
                        html.H6("Recombinant Sequence:"),
                        html.Pre(result['recombinant_sequence'][:200] + "..." if len(result['recombinant_sequence']) > 200 else result['recombinant_sequence'], className="sequence-preview")
                    ], className="sequence-preview"),
                ])
            else:
                return html.Div([
                    html.H5("❌ Failed to simulate cloning"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error simulating cloning: {e}")
            return html.P(f"❌ Error: {str(e)}")
    
    @app.callback(
        Output("export-results", "children"),
        [Input("export-plasmid", "n_clicks")],
        [State("export-format", "value")]
    )
    def export_plasmid(n_clicks, format):
        if n_clicks is None:
            return ""
        
        try:
            # Create sample plasmid data for demonstration
            sample_plasmid = {
                'name': 'pUC19',
                'sequence': 'ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG',
                'features': [
                    {'name': 'AmpR', 'type': 'resistance', 'start': 1, 'end': 20},
                    {'name': 'lacZ', 'type': 'gene', 'start': 21, 'end': 40},
                    {'name': 'ori', 'type': 'ori', 'start': 41, 'end': 60}
                ],
                'metadata': {'created_by': 'Cancer Genomics Analysis Suite'}
            }
            
            result = ape_client.export_plasmid(sample_plasmid, format)
            
            if result['success']:
                return html.Div([
                    html.H5("✅ Plasmid exported successfully"),
                    html.P(f"Format: {result['format']}"),
                    html.P(f"File: {result['output_file']}"),
                    html.Button("Download File", className="button secondary"),
                ])
            else:
                return html.Div([
                    html.H5("❌ Failed to export plasmid"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error exporting plasmid: {e}")
            return html.P(f"❌ Error: {str(e)}")
    
    @app.callback(
        Output("plasmid-visualization", "children"),
        [Input("visualize-plasmid", "n_clicks")]
    )
    def visualize_plasmid(n_clicks):
        if n_clicks is None:
            return ""
        
        try:
            # Create a simple circular plasmid visualization
            import plotly.graph_objects as go
            
            # Sample data for visualization
            features = [
                {'name': 'AmpR', 'start': 0, 'end': 60, 'color': 'red'},
                {'name': 'lacZ', 'start': 60, 'end': 120, 'color': 'blue'},
                {'name': 'ori', 'start': 120, 'end': 180, 'color': 'green'},
                {'name': 'MCS', 'start': 180, 'end': 240, 'color': 'orange'},
            ]
            
            # Create circular plot
            fig = go.Figure()
            
            # Add features as arcs
            for feature in features:
                start_angle = (feature['start'] / 360) * 2 * 3.14159
                end_angle = (feature['end'] / 360) * 2 * 3.14159
                
                # Create arc
                angles = [start_angle, end_angle]
                x = [1.1 * go.math.cos(angle) for angle in angles]
                y = [1.1 * go.math.sin(angle) for angle in angles]
                
                fig.add_trace(go.Scatter(
                    x=x, y=y,
                    mode='lines+markers',
                    name=feature['name'],
                    line=dict(color=feature['color'], width=10),
                    marker=dict(size=8)
                ))
            
            # Add outer circle
            theta = [i * 2 * 3.14159 / 100 for i in range(101)]
            x_circle = [go.math.cos(angle) for angle in theta]
            y_circle = [go.math.sin(angle) for angle in theta]
            
            fig.add_trace(go.Scatter(
                x=x_circle, y=y_circle,
                mode='lines',
                line=dict(color='black', width=2),
                showlegend=False
            ))
            
            fig.update_layout(
                title="Plasmid Map",
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                showlegend=True,
                width=500,
                height=500
            )
            
            return dcc.Graph(figure=fig)
            
        except Exception as e:
            logger.error(f"Error creating visualization: {e}")
            return html.P(f"❌ Error creating visualization: {str(e)}")
