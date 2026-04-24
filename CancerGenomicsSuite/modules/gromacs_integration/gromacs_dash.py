"""
GROMACS Integration Dashboard

Provides a Dash interface for molecular dynamics simulations using GROMACS.
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

from .gromacs_client import GROMACSClient

logger = logging.getLogger(__name__)

# Initialize GROMACS client
gromacs_client = GROMACSClient()

# Dashboard layout
layout = html.Div([
    html.Div([
        html.H2("⚛️ GROMACS Integration", className="section-title"),
        html.P("Molecular dynamics simulations and analysis", className="section-description"),
    ], className="section-header"),
    
    # GROMACS Status section
    html.Div([
        html.H3("GROMACS Status", className="subsection-title"),
        html.Div([
            html.Div([
                html.Span("Status: ", className="status-label"),
                html.Span(id="gromacs-status", className="status-value"),
            ], className="status-item"),
            html.Div([
                html.Span("Version: ", className="status-label"),
                html.Span(id="gromacs-version", className="status-value"),
            ], className="status-item"),
        ], className="status-container"),
        html.Button("Refresh Status", id="refresh-gromacs-status", className="button secondary"),
    ], className="gromacs-status-section"),
    
    # Simulation section
    html.Div([
        html.H3("Molecular Dynamics Simulation", className="subsection-title"),
        html.Div([
            html.Label("Input Files:", className="input-label"),
            dcc.Upload(
                id="gromacs-file-upload",
                children=html.Div([
                    "Drag and Drop or ",
                    html.A("Select GROMACS Files")
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
        ], className="input-group"),
        html.Button("Run Simulation", id="run-simulation", className="button primary"),
        html.Div(id="gromacs-simulation-results", className="simulation-results"),
    ], className="simulation-section"),
    
    # Results section
    html.Div([
        html.H3("Results", className="subsection-title"),
        html.Div(id="gromacs-results", className="results-container"),
    ], className="results-section"),
])

def register_callbacks(app):
    """Register callbacks for the GROMACS dashboard"""
    
    @app.callback(
        [Output("gromacs-status", "children"),
         Output("gromacs-version", "children")],
        [Input("refresh-gromacs-status", "n_clicks")]
    )
    def update_gromacs_status(n_clicks):
        if gromacs_client.is_available():
            status = "✅ Available"
            version = gromacs_client.get_version()
        else:
            status = "❌ Not Available"
            version = "Not available"
        
        return status, version
    
    @app.callback(
        Output("gromacs-simulation-results", "children"),
        [Input("run-simulation", "n_clicks")],
        [State("gromacs-file-upload", "contents")]
    )
    def run_simulation(n_clicks, contents):
        if n_clicks is None:
            return ""
        
        try:
            # Process uploaded files and run simulation
            result = gromacs_client.run_simulation({}, {})
            
            if result['success']:
                return html.Div([
                    html.H5("✅ Simulation completed successfully"),
                    html.P("Molecular dynamics simulation finished"),
                ])
            else:
                return html.Div([
                    html.H5("❌ Simulation failed"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error running simulation: {e}")
            return html.P(f"❌ Error: {str(e)}")
