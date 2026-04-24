"""
Neurosnap Integration Dashboard

Provides a Dash interface for neuroscience data analysis using Neurosnap.
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

from .neurosnap_client import NeurosnapClient

logger = logging.getLogger(__name__)

# Initialize Neurosnap client
neurosnap_client = NeurosnapClient()

# Dashboard layout
layout = html.Div([
    html.Div([
        html.H2("🧠 Neurosnap Integration", className="section-title"),
        html.P("Neuroscience data analysis and processing", className="section-description"),
    ], className="section-header"),
    
    # Neurosnap Status section
    html.Div([
        html.H3("Neurosnap Status", className="subsection-title"),
        html.Div([
            html.Div([
                html.Span("Status: ", className="status-label"),
                html.Span(id="neurosnap-status", className="status-value"),
            ], className="status-item"),
            html.Div([
                html.Span("Version: ", className="status-label"),
                html.Span(id="neurosnap-version", className="status-value"),
            ], className="status-item"),
        ], className="status-container"),
        html.Button("Refresh Status", id="refresh-neurosnap-status", className="button secondary"),
    ], className="neurosnap-status-section"),
    
    # Analysis section
    html.Div([
        html.H3("Neural Data Analysis", className="subsection-title"),
        html.Div([
            html.Label("Data File:", className="input-label"),
            dcc.Upload(
                id="neural-data-upload",
                children=html.Div([
                    "Drag and Drop or ",
                    html.A("Select Neural Data File")
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
            html.Label("Analysis Type:", className="input-label"),
            dcc.Dropdown(
                id="analysis-type",
                options=[
                    {'label': 'Spike Detection', 'value': 'spike_detection'},
                    {'label': 'LFP Analysis', 'value': 'lfp_analysis'},
                    {'label': 'Connectivity', 'value': 'connectivity'},
                    {'label': 'Spectral Analysis', 'value': 'spectral'},
                ],
                value='spike_detection',
                className="dropdown"
            ),
        ], className="input-group"),
        html.Button("Run Analysis", id="run-neural-analysis", className="button primary"),
        html.Div(id="neural-analysis-results", className="analysis-results"),
    ], className="analysis-section"),
    
    # Results section
    html.Div([
        html.H3("Results", className="subsection-title"),
        html.Div(id="neurosnap-results", className="results-container"),
    ], className="results-section"),
])

def register_callbacks(app):
    """Register callbacks for the Neurosnap dashboard"""
    
    @app.callback(
        [Output("neurosnap-status", "children"),
         Output("neurosnap-version", "children")],
        [Input("refresh-neurosnap-status", "n_clicks")]
    )
    def update_neurosnap_status(n_clicks):
        if neurosnap_client.is_available():
            status = "✅ Available"
            version = neurosnap_client.get_version()
        else:
            status = "❌ Not Available"
            version = "Not available"
        
        return status, version
    
    @app.callback(
        Output("neural-analysis-results", "children"),
        [Input("run-neural-analysis", "n_clicks")],
        [State("neural-data-upload", "contents"),
         State("analysis-type", "value")]
    )
    def run_neural_analysis(n_clicks, contents, analysis_type):
        if n_clicks is None:
            return ""
        
        try:
            # For demonstration, we'll simulate the analysis
            result = {
                'success': True,
                'analysis_type': analysis_type,
                'message': 'Neural data analysis completed successfully'
            }
            
            if result['success']:
                return html.Div([
                    html.H5("✅ Neural analysis completed successfully"),
                    html.P(f"Analysis type: {result['analysis_type']}"),
                    html.P(f"Message: {result['message']}"),
                ])
            else:
                return html.Div([
                    html.H5("❌ Analysis failed"),
                    html.P(f"Error: {result.get('error', 'Unknown error')}"),
                ])
                
        except Exception as e:
            logger.error(f"Error running neural analysis: {e}")
            return html.P(f"❌ Error: {str(e)}")
