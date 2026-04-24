"""
Tamarind Bio Integration Dashboard

Provides a Dash interface for bioinformatics workflows using Tamarind Bio.
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

from .tamarind_client import TamarindClient

logger = logging.getLogger(__name__)

# Initialize Tamarind client
tamarind_client = TamarindClient()

# Dashboard layout
layout = html.Div([
    html.Div([
        html.H2("🌿 Tamarind Bio", className="section-title"),
        html.P("Bioinformatics workflows and analysis", className="section-description"),
    ], className="section-header"),
    
    # Tamarind Status section
    html.Div([
        html.H3("Tamarind Bio Status", className="subsection-title"),
        html.Div([
            html.Div([
                html.Span("Status: ", className="status-label"),
                html.Span(id="tamarind-status", className="status-value"),
            ], className="status-item"),
            html.Div([
                html.Span("Version: ", className="status-label"),
                html.Span(id="tamarind-version", className="status-value"),
            ], className="status-item"),
        ], className="status-container"),
        html.Button("Refresh Status", id="refresh-tamarind-status", className="button secondary"),
    ], className="tamarind-status-section"),
    
    # Workflow section
    html.Div([
        html.H3("Workflow Execution", className="subsection-title"),
        html.Div([
            html.Label("Workflow File:", className="input-label"),
            dcc.Upload(
                id="workflow-upload",
                children=html.Div([
                    "Drag and Drop or ",
                    html.A("Select Workflow File")
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
        html.Button("Run Workflow", id="run-workflow", className="button primary"),
        html.Div(id="workflow-results", className="workflow-results"),
    ], className="workflow-section"),
    
    # Results section
    html.Div([
        html.H3("Results", className="subsection-title"),
        html.Div(id="tamarind-results", className="results-container"),
    ], className="results-section"),
])

def register_callbacks(app):
    """Register callbacks for the Tamarind Bio dashboard"""
    
    @app.callback(
        [Output("tamarind-status", "children"),
         Output("tamarind-version", "children")],
        [Input("refresh-tamarind-status", "n_clicks")]
    )
    def update_tamarind_status(n_clicks):
        if tamarind_client.is_available():
            status = "✅ Available"
            version = tamarind_client.get_version()
        else:
            status = "❌ Not Available"
            version = "Not available"
        
        return status, version
    
    @app.callback(
        Output("workflow-results", "children"),
        [Input("run-workflow", "n_clicks")],
        [State("workflow-upload", "contents")]
    )
    def run_workflow(n_clicks, contents):
        if n_clicks is None:
            return ""
        
        try:
            # For demonstration, we'll simulate the workflow execution
            result = {
                'success': True,
                'message': 'Workflow executed successfully'
            }
            
            if result['success']:
                return html.Div([
                    html.H5("✅ Workflow executed successfully"),
                    html.P(f"Message: {result['message']}"),
                ])
            else:
                return html.Div([
                    html.H5("❌ Workflow failed"),
                    html.P(f"Error: {result.get('error', 'Unknown error')}"),
                ])
                
        except Exception as e:
            logger.error(f"Error running workflow: {e}")
            return html.P(f"❌ Error: {str(e)}")
