"""
PyMOL Integration Dashboard

Provides a Dash interface for molecular visualization, structure analysis,
and protein modeling using PyMOL.
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import json
import base64
import os
from typing import Dict, List, Any
import logging

from .pymol_client import PyMOLClient

logger = logging.getLogger(__name__)

# Initialize PyMOL client
pymol_client = PyMOLClient()

# Dashboard layout
layout = html.Div([
    html.Div([
        html.H2("🧬 PyMOL Integration", className="section-title"),
        html.P("Molecular visualization, structure analysis, and protein modeling", className="section-description"),
    ], className="section-header"),
    
    # PyMOL Status section
    html.Div([
        html.H3("PyMOL Status", className="subsection-title"),
        html.Div([
            html.Div([
                html.Span("Status: ", className="status-label"),
                html.Span(id="pymol-status", className="status-value"),
            ], className="status-item"),
            html.Div([
                html.Span("Version: ", className="status-label"),
                html.Span(id="pymol-version", className="status-value"),
            ], className="status-item"),
            html.Div([
                html.Span("Path: ", className="status-label"),
                html.Span(id="pymol-path", className="status-value"),
            ], className="status-item"),
        ], className="status-container"),
        html.Button("Refresh Status", id="refresh-pymol-status", className="button secondary"),
    ], className="pymol-status-section"),
    
    # Structure Loading section
    html.Div([
        html.H3("Load Structure", className="subsection-title"),
        dcc.Tabs(id="load-structure-tabs", value="file", children=[
            dcc.Tab(label="From File", value="file"),
            dcc.Tab(label="From PDB", value="pdb"),
        ]),
        html.Div(id="load-structure-content", className="load-structure-content"),
    ], className="load-structure-section"),
    
    # Structure Visualization section
    html.Div([
        html.H3("Visualization", className="subsection-title"),
        html.Div([
            html.Div([
                html.Label("Object Name:", className="input-label"),
                dcc.Input(
                    id="object-name",
                    type="text",
                    placeholder="mol",
                    className="input-field"
                ),
            ], className="input-group"),
            html.Div([
                html.Label("Style:", className="input-label"),
                dcc.Dropdown(
                    id="visualization-style",
                    options=[
                        {'label': 'Cartoon', 'value': 'cartoon'},
                        {'label': 'Stick', 'value': 'stick'},
                        {'label': 'Sphere', 'value': 'sphere'},
                        {'label': 'Surface', 'value': 'surface'},
                        {'label': 'Ribbon', 'value': 'ribbon'},
                    ],
                    value='cartoon',
                    className="dropdown"
                ),
            ], className="input-group"),
            html.Div([
                html.Label("Color:", className="input-label"),
                dcc.Dropdown(
                    id="visualization-color",
                    options=[
                        {'label': 'Spectrum', 'value': 'spectrum'},
                        {'label': 'Rainbow', 'value': 'rainbow'},
                        {'label': 'Secondary Structure', 'value': 'ss'},
                        {'label': 'Element', 'value': 'element'},
                        {'label': 'Chain', 'value': 'chain'},
                    ],
                    value='spectrum',
                    className="dropdown"
                ),
            ], className="input-group"),
            html.Button("Visualize Structure", id="visualize-structure", className="button primary"),
            html.Div(id="visualization-results", className="visualization-results"),
        ], className="visualization-section"),
    ], className="visualization-section"),
    
    # Structure Analysis section
    html.Div([
        html.H3("Structure Analysis", className="subsection-title"),
        dcc.Tabs(id="analysis-tabs", value="alignment", children=[
            dcc.Tab(label="Alignment", value="alignment"),
            dcc.Tab(label="Distance", value="distance"),
            dcc.Tab(label="Secondary Structure", value="secondary"),
            dcc.Tab(label="Surface", value="surface"),
        ]),
        html.Div(id="pymol-analysis-content", className="analysis-content"),
    ], className="analysis-section"),
    
    # Structure Manipulation section
    html.Div([
        html.H3("Structure Manipulation", className="subsection-title"),
        dcc.Tabs(id="manipulation-tabs", value="mutation", children=[
            dcc.Tab(label="Mutation", value="mutation"),
            dcc.Tab(label="Export", value="export"),
            dcc.Tab(label="Animation", value="animation"),
        ]),
        html.Div(id="manipulation-content", className="manipulation-content"),
    ], className="manipulation-section"),
    
    # PyMOL Commands section
    html.Div([
        html.H3("PyMOL Commands", className="subsection-title"),
        html.Div([
            html.Label("PyMOL Commands:", className="input-label"),
            dcc.Textarea(
                id="pymol-commands",
                placeholder="# Enter PyMOL commands here...\n# Example:\n# load structure.pdb, mol\n# show cartoon, mol\n# color spectrum, mol\n# ray\n# png output.png",
                style={'width': '100%', 'height': '200px', 'fontFamily': 'monospace'},
                className="code-editor"
            ),
        ], className="input-group"),
        html.Div([
            html.Button("Execute Commands", id="execute-pymol-commands", className="button primary"),
            html.Button("Clear", id="clear-pymol-commands", className="button secondary"),
            html.Button("Load Example", id="load-pymol-example", className="button secondary"),
        ], className="button-group"),
        html.Div(id="pymol-command-results", className="command-results"),
    ], className="commands-section"),
    
    # Results section
    html.Div([
        html.H3("Results", className="subsection-title"),
        html.Div(id="pymol-results", className="results-container"),
    ], className="results-section"),
    
    # Hidden divs for storing data
    html.Div(id="pymol-data", style={"display": "none"}),
])

def register_callbacks(app):
    """Register callbacks for the PyMOL dashboard"""
    
    @app.callback(
        [Output("pymol-status", "children"),
         Output("pymol-version", "children"),
         Output("pymol-path", "children")],
        [Input("refresh-pymol-status", "n_clicks")]
    )
    def update_pymol_status(n_clicks):
        if pymol_client.is_available():
            status = "✅ Available"
            version = pymol_client.get_version()
            path = pymol_client.pymol_path or "Not found"
        else:
            status = "❌ Not Available"
            version = "Not available"
            path = "Not found"
        
        return status, version, path
    
    @app.callback(
        Output("load-structure-content", "children"),
        [Input("load-structure-tabs", "value")]
    )
    def update_load_structure_content(active_tab):
        if active_tab == "file":
            return html.Div([
                html.H4("Load Structure from File"),
                dcc.Upload(
                    id="structure-file-upload",
                    children=html.Div([
                        "Drag and Drop or ",
                        html.A("Select Structure File")
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
                    html.Label("Object Name:", className="input-label"),
                    dcc.Input(
                        id="file-object-name",
                        type="text",
                        value="mol",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Button("Load Structure", id="load-file-structure", className="button primary"),
                html.Div(id="file-load-results", className="load-results"),
            ])
        
        elif active_tab == "pdb":
            return html.Div([
                html.H4("Fetch Structure from PDB"),
                html.Div([
                    html.Label("PDB ID:", className="input-label"),
                    dcc.Input(
                        id="pdb-id",
                        type="text",
                        placeholder="1CRN",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Object Name:", className="input-label"),
                    dcc.Input(
                        id="pdb-object-name",
                        type="text",
                        placeholder="pdb_structure",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Button("Fetch Structure", id="fetch-pdb-structure", className="button primary"),
                html.Div(id="pdb-fetch-results", className="fetch-results"),
            ])
    
    @app.callback(
        Output("file-load-results", "children"),
        [Input("load-file-structure", "n_clicks")],
        [State("structure-file-upload", "contents"),
         State("file-object-name", "value")]
    )
    def load_file_structure(n_clicks, contents, object_name):
        if n_clicks is None or not contents:
            return ""
        
        if not pymol_client.is_available():
            return html.P("❌ PyMOL not available")
        
        try:
            # Save uploaded file
            import base64
            import io
            
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdb') as f:
                f.write(decoded)
                temp_file = f.name
            
            # Load structure
            result = pymol_client.load_structure(temp_file, object_name)
            
            # Clean up temporary file
            os.unlink(temp_file)
            
            if result['success']:
                return html.Div([
                    html.H5("✅ Structure loaded successfully"),
                    html.P(f"Object name: {object_name}"),
                    html.P(f"File: {temp_file}"),
                ])
            else:
                return html.Div([
                    html.H5("❌ Failed to load structure"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error loading structure file: {e}")
            return html.P(f"❌ Error: {str(e)}")
    
    @app.callback(
        Output("pdb-fetch-results", "children"),
        [Input("fetch-pdb-structure", "n_clicks")],
        [State("pdb-id", "value"),
         State("pdb-object-name", "value")]
    )
    def fetch_pdb_structure(n_clicks, pdb_id, object_name):
        if n_clicks is None or not pdb_id:
            return ""
        
        if not pymol_client.is_available():
            return html.P("❌ PyMOL not available")
        
        try:
            # Fetch structure from PDB
            result = pymol_client.fetch_structure(pdb_id, object_name)
            
            if result['success']:
                return html.Div([
                    html.H5("✅ Structure fetched successfully"),
                    html.P(f"PDB ID: {pdb_id}"),
                    html.P(f"Object name: {object_name}"),
                ])
            else:
                return html.Div([
                    html.H5("❌ Failed to fetch structure"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error fetching PDB structure: {e}")
            return html.P(f"❌ Error: {str(e)}")
    
    @app.callback(
        Output("visualization-results", "children"),
        [Input("visualize-structure", "n_clicks")],
        [State("object-name", "value"),
         State("visualization-style", "value"),
         State("visualization-color", "value")]
    )
    def visualize_structure(n_clicks, object_name, style, color):
        if n_clicks is None or not object_name:
            return ""
        
        if not pymol_client.is_available():
            return html.P("❌ PyMOL not available")
        
        try:
            # Create output file
            output_file = f"structure_{object_name}_{style}_{color}.png"
            
            # Visualize structure
            result = pymol_client.visualize_structure(object_name, style, color, output_file)
            
            if result['success']:
                # Display image if available
                image_display = ""
                if result.get('output_file') and os.path.exists(result['output_file']):
                    with open(result['output_file'], 'rb') as f:
                        image_data = base64.b64encode(f.read()).decode()
                    image_display = html.Img(
                        src=f"data:image/png;base64,{image_data}",
                        style={'max-width': '100%', 'height': 'auto'}
                    )
                
                return html.Div([
                    html.H5("✅ Structure visualized successfully"),
                    html.P(f"Object: {object_name}"),
                    html.P(f"Style: {style}"),
                    html.P(f"Color: {color}"),
                    image_display,
                ])
            else:
                return html.Div([
                    html.H5("❌ Failed to visualize structure"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error visualizing structure: {e}")
            return html.P(f"❌ Error: {str(e)}")
    
    @app.callback(
        Output("pymol-analysis-content", "children"),
        [Input("analysis-tabs", "value")]
    )
    def update_analysis_content(active_tab):
        if active_tab == "alignment":
            return html.Div([
                html.H4("Structure Alignment"),
                html.Div([
                    html.Label("Object 1:", className="input-label"),
                    dcc.Input(
                        id="align-object1",
                        type="text",
                        placeholder="mol1",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Object 2:", className="input-label"),
                    dcc.Input(
                        id="align-object2",
                        type="text",
                        placeholder="mol2",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Method:", className="input-label"),
                    dcc.Dropdown(
                        id="alignment-method",
                        options=[
                            {'label': 'Align', 'value': 'align'},
                            {'label': 'Super', 'value': 'super'},
                            {'label': 'CEAlign', 'value': 'cealign'},
                        ],
                        value='align',
                        className="dropdown"
                    ),
                ], className="input-group"),
                html.Button("Align Structures", id="align-structures", className="button primary"),
                html.Div(id="alignment-results", className="analysis-results"),
            ])
        
        elif active_tab == "distance":
            return html.Div([
                html.H4("Distance Calculation"),
                html.Div([
                    html.Label("Object Name:", className="input-label"),
                    dcc.Input(
                        id="distance-object",
                        type="text",
                        placeholder="mol",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Selection 1:", className="input-label"),
                    dcc.Input(
                        id="distance-selection1",
                        type="text",
                        placeholder="resi 10",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Selection 2:", className="input-label"),
                    dcc.Input(
                        id="distance-selection2",
                        type="text",
                        placeholder="resi 20",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Button("Calculate Distance", id="calculate-distance", className="button primary"),
                html.Div(id="distance-results", className="analysis-results"),
            ])
        
        elif active_tab == "secondary":
            return html.Div([
                html.H4("Secondary Structure Analysis"),
                html.Div([
                    html.Label("Object Name:", className="input-label"),
                    dcc.Input(
                        id="secondary-object",
                        type="text",
                        placeholder="mol",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Button("Analyze Secondary Structure", id="analyze-secondary", className="button primary"),
                html.Div(id="secondary-results", className="analysis-results"),
            ])
        
        elif active_tab == "surface":
            return html.Div([
                html.H4("Surface Creation"),
                html.Div([
                    html.Label("Object Name:", className="input-label"),
                    dcc.Input(
                        id="surface-object",
                        type="text",
                        placeholder="mol",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Surface Type:", className="input-label"),
                    dcc.Dropdown(
                        id="surface-type",
                        options=[
                            {'label': 'Surface', 'value': 'surface'},
                            {'label': 'Dots', 'value': 'dots'},
                            {'label': 'Mesh', 'value': 'mesh'},
                        ],
                        value='surface',
                        className="dropdown"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Transparency:", className="input-label"),
                    dcc.Slider(
                        id="surface-transparency",
                        min=0,
                        max=1,
                        step=0.1,
                        value=0.5,
                        marks={i/10: str(i/10) for i in range(0, 11, 2)},
                        className="slider"
                    ),
                ], className="input-group"),
                html.Button("Create Surface", id="create-surface", className="button primary"),
                html.Div(id="surface-results", className="analysis-results"),
            ])
    
    @app.callback(
        Output("alignment-results", "children"),
        [Input("align-structures", "n_clicks")],
        [State("align-object1", "value"),
         State("align-object2", "value"),
         State("alignment-method", "value")]
    )
    def align_structures(n_clicks, object1, object2, method):
        if n_clicks is None or not object1 or not object2:
            return ""
        
        if not pymol_client.is_available():
            return html.P("❌ PyMOL not available")
        
        try:
            # Align structures
            result = pymol_client.align_structures(object1, object2, method)
            
            if result['success']:
                rmsd_info = ""
                if 'rmsd' in result:
                    rmsd_info = html.P(f"RMSD: {result['rmsd']:.3f} Å")
                
                return html.Div([
                    html.H5("✅ Structures aligned successfully"),
                    html.P(f"Method: {method}"),
                    html.P(f"Object 1: {object1}"),
                    html.P(f"Object 2: {object2}"),
                    rmsd_info,
                ])
            else:
                return html.Div([
                    html.H5("❌ Failed to align structures"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error aligning structures: {e}")
            return html.P(f"❌ Error: {str(e)}")
    
    @app.callback(
        Output("pymol-command-results", "children"),
        [Input("execute-pymol-commands", "n_clicks")],
        [State("pymol-commands", "value")]
    )
    def execute_pymol_commands(n_clicks, commands):
        if n_clicks is None or not commands:
            return ""
        
        if not pymol_client.is_available():
            return html.P("❌ PyMOL not available")
        
        try:
            # Execute PyMOL commands
            result = pymol_client.execute_pymol_script(commands)
            
            if result['success']:
                output_content = []
                if result['output']:
                    output_content.append(html.H4("Output:"))
                    output_content.append(html.Pre(result['output'], className="code-output"))
                
                if result['error_output']:
                    output_content.append(html.H4("Messages:"))
                    output_content.append(html.Pre(result['error_output'], className="code-messages"))
                
                return html.Div([
                    html.H5("✅ Commands executed successfully"),
                    html.Div(output_content)
                ])
            else:
                return html.Div([
                    html.H5("❌ Command execution failed"),
                    html.P(f"Error: {result['error']}"),
                    html.Pre(result['error_output'], className="error-output")
                ])
                
        except Exception as e:
            logger.error(f"Error executing PyMOL commands: {e}")
            return html.P(f"❌ Error: {str(e)}")
    
    @app.callback(
        Output("pymol-commands", "value"),
        [Input("clear-pymol-commands", "n_clicks"),
         Input("load-pymol-example", "n_clicks")]
    )
    def manage_pymol_commands(clear_clicks, example_clicks):
        ctx = callback_context
        if not ctx.triggered:
            return ""
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if button_id == "clear-pymol-commands":
            return ""
        elif button_id == "load-pymol-example":
            example_commands = """
# Example PyMOL commands for protein visualization
# Load a protein structure
fetch 1CRN, protein

# Show as cartoon with spectrum coloring
show cartoon, protein
color spectrum, protein

# Create a nice view
zoom protein
center protein

# Add some additional visualizations
show sticks, protein and resi 1-10
color red, protein and resi 1-10

# Create surface
show surface, protein
set transparency, 0.5, protein

# Render high-quality image
ray
png protein_visualization.png
"""
            return example_commands
        
        return ""
