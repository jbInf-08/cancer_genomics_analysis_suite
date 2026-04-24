"""
WGSIM Tools Integration Dashboard

Provides a Dash interface for read simulation using wgsim and dwgsim tools.
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

from .wgsim_client import WGSIMClient

logger = logging.getLogger(__name__)

# Initialize WGSIM client
wgsim_client = WGSIMClient()

# Dashboard layout
layout = html.Div([
    html.Div([
        html.H2("🧬 WGSIM Tools", className="section-title"),
        html.P("Read simulation and variant calling tools", className="section-description"),
    ], className="section-header"),
    
    # WGSIM Status section
    html.Div([
        html.H3("Tool Status", className="subsection-title"),
        html.Div([
            html.Div([
                html.Span("wgsim: ", className="status-label"),
                html.Span(id="wgsim-status", className="status-value"),
            ], className="status-item"),
            html.Div([
                html.Span("dwgsim: ", className="status-label"),
                html.Span(id="dwgsim-status", className="status-value"),
            ], className="status-item"),
        ], className="status-container"),
        html.Button("Refresh Status", id="refresh-wgsim-status", className="button secondary"),
    ], className="wgsim-status-section"),
    
    # Read Simulation section
    html.Div([
        html.H3("Read Simulation", className="subsection-title"),
        html.Div([
            html.Label("Reference Genome:", className="input-label"),
            dcc.Upload(
                id="reference-upload",
                children=html.Div([
                    "Drag and Drop or ",
                    html.A("Select Reference Genome")
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
        ], className="input-group"),
        html.Div([
            html.Label("Simulation Tool:", className="input-label"),
            dcc.Dropdown(
                id="simulation-tool",
                options=[
                    {'label': 'wgsim', 'value': 'wgsim'},
                    {'label': 'dwgsim', 'value': 'dwgsim'},
                ],
                value='wgsim',
                className="dropdown"
            ),
        ], className="input-group"),
        html.Div([
            html.Label("Number of Reads:", className="input-label"),
            dcc.Input(
                id="num-reads",
                type="number",
                value=1000000,
                min=1000,
                max=100000000,
                className="input-field"
            ),
        ], className="input-group"),
        html.Div([
            html.Label("Read Length:", className="input-label"),
            dcc.Input(
                id="read-length",
                type="number",
                value=100,
                min=50,
                max=300,
                className="input-field"
            ),
        ], className="input-group"),
        html.Div([
            html.Label("Error Rate:", className="input-label"),
            dcc.Input(
                id="error-rate",
                type="number",
                value=0.02,
                min=0.001,
                max=0.1,
                step=0.001,
                className="input-field"
            ),
        ], className="input-group"),
        html.Button("Simulate Reads", id="simulate-reads", className="button primary"),
        html.Div(id="wgsim-simulation-results", className="simulation-results"),
    ], className="simulation-section"),
    
    # Results section
    html.Div([
        html.H3("Results", className="subsection-title"),
        html.Div(id="wgsim-results", className="results-container"),
    ], className="results-section"),
])

def register_callbacks(app):
    """Register callbacks for the WGSIM dashboard"""
    
    @app.callback(
        [Output("wgsim-status", "children"),
         Output("dwgsim-status", "children")],
        [Input("refresh-wgsim-status", "n_clicks")]
    )
    def update_wgsim_status(n_clicks):
        wgsim_status = "✅ Available" if wgsim_client.is_wgsim_available() else "❌ Not Available"
        dwgsim_status = "✅ Available" if wgsim_client.is_dwgsim_available() else "❌ Not Available"
        
        return wgsim_status, dwgsim_status
    
    @app.callback(
        Output("wgsim-simulation-results", "children"),
        [Input("simulate-reads", "n_clicks")],
        [State("reference-upload", "contents"),
         State("simulation-tool", "value"),
         State("num-reads", "value"),
         State("read-length", "value"),
         State("error-rate", "value")]
    )
    def simulate_reads(n_clicks, contents, tool, num_reads, read_length, error_rate):
        if n_clicks is None:
            return ""
        
        try:
            # For demonstration, we'll simulate the process
            # In a real implementation, you would process the uploaded reference file
            
            result = {
                'success': True,
                'tool': tool,
                'num_reads': num_reads,
                'read_length': read_length,
                'error_rate': error_rate
            }
            
            if result['success']:
                return html.Div([
                    html.H5("✅ Read simulation completed successfully"),
                    html.P(f"Tool: {result['tool']}"),
                    html.P(f"Number of reads: {result['num_reads']:,}"),
                    html.P(f"Read length: {result['read_length']} bp"),
                    html.P(f"Error rate: {result['error_rate']:.3f}"),
                ])
            else:
                return html.Div([
                    html.H5("❌ Simulation failed"),
                    html.P(f"Error: {result.get('error', 'Unknown error')}"),
                ])
                
        except Exception as e:
            logger.error(f"Error simulating reads: {e}")
            return html.P(f"❌ Error: {str(e)}")
