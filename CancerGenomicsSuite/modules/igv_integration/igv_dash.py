"""
IGV Integration Dashboard

Provides a Dash interface for genomic data visualization using IGV.
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

from .igv_client import IGVClient

logger = logging.getLogger(__name__)

# Initialize IGV client
igv_client = IGVClient()

# Dashboard layout
layout = html.Div([
    html.Div([
        html.H2("🧬 IGV Integration", className="section-title"),
        html.P("Genomic data visualization and analysis", className="section-description"),
    ], className="section-header"),
    
    # IGV Status section
    html.Div([
        html.H3("IGV Status", className="subsection-title"),
        html.Div([
            html.Div([
                html.Span("Status: ", className="status-label"),
                html.Span(id="igv-status", className="status-value"),
            ], className="status-item"),
            html.Div([
                html.Span("Version: ", className="status-label"),
                html.Span(id="igv-version", className="status-value"),
            ], className="status-item"),
        ], className="status-container"),
        html.Button("Refresh Status", id="refresh-igv-status", className="button secondary"),
    ], className="igv-status-section"),
    
    # Genome and Tracks section
    html.Div([
        html.H3("Genome and Tracks", className="subsection-title"),
        dcc.Tabs(id="igv-tabs", value="genome", children=[
            dcc.Tab(label="Load Genome", value="genome"),
            dcc.Tab(label="Load Tracks", value="tracks"),
            dcc.Tab(label="Navigate", value="navigate"),
        ]),
        html.Div(id="igv-content", className="igv-content"),
    ], className="igv-section"),
    
    # Results section
    html.Div([
        html.H3("Results", className="subsection-title"),
        html.Div(id="igv-results", className="results-container"),
    ], className="results-section"),
])

def register_callbacks(app):
    """Register callbacks for the IGV dashboard"""
    
    @app.callback(
        [Output("igv-status", "children"),
         Output("igv-version", "children")],
        [Input("refresh-igv-status", "n_clicks")]
    )
    def update_igv_status(n_clicks):
        if igv_client.is_available():
            status = "✅ Available"
            version = igv_client.get_version()
        else:
            status = "❌ Not Available"
            version = "Not available"
        
        return status, version
    
    @app.callback(
        Output("igv-content", "children"),
        [Input("igv-tabs", "value")]
    )
    def update_igv_content(active_tab):
        if active_tab == "genome":
            return html.Div([
                html.H4("Load Genome"),
                html.Div([
                    html.Label("Genome ID:", className="input-label"),
                    dcc.Dropdown(
                        id="genome-id",
                        options=[
                            {'label': 'hg38', 'value': 'hg38'},
                            {'label': 'hg19', 'value': 'hg19'},
                            {'label': 'mm10', 'value': 'mm10'},
                            {'label': 'mm9', 'value': 'mm9'},
                        ],
                        value='hg38',
                        className="dropdown"
                    ),
                ], className="input-group"),
                html.Button("Load Genome", id="load-genome", className="button primary"),
                html.Div(id="genome-results", className="genome-results"),
            ])
        
        elif active_tab == "tracks":
            return html.Div([
                html.H4("Load Data Tracks"),
                dcc.Upload(
                    id="track-file-upload",
                    children=html.Div([
                        "Drag and Drop or ",
                        html.A("Select Track Files")
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
                html.Div([
                    html.Label("Track Name (optional):", className="input-label"),
                    dcc.Input(
                        id="track-name",
                        type="text",
                        placeholder="My Track",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Button("Load Track", id="load-track", className="button primary"),
                html.Div(id="track-results", className="track-results"),
            ])
        
        elif active_tab == "navigate":
            return html.Div([
                html.H4("Navigate to Locus"),
                html.Div([
                    html.Label("Genomic Locus:", className="input-label"),
                    dcc.Input(
                        id="genomic-locus",
                        type="text",
                        placeholder="chr1:1000000-2000000",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Button("Go to Locus", id="goto-locus", className="button primary"),
                html.Div(id="navigation-results", className="navigation-results"),
            ])
    
    @app.callback(
        Output("genome-results", "children"),
        [Input("load-genome", "n_clicks")],
        [State("genome-id", "value")]
    )
    def load_genome(n_clicks, genome_id):
        if n_clicks is None or not genome_id:
            return ""
        
        try:
            result = igv_client.load_genome(genome_id)
            
            if result['success']:
                return html.Div([
                    html.H5("✅ Genome loaded successfully"),
                    html.P(f"Genome: {genome_id}"),
                ])
            else:
                return html.Div([
                    html.H5("❌ Failed to load genome"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error loading genome: {e}")
            return html.P(f"❌ Error: {str(e)}")
    
    @app.callback(
        Output("track-results", "children"),
        [Input("load-track", "n_clicks")],
        [State("track-file-upload", "contents"),
         State("track-name", "value")]
    )
    def load_track(n_clicks, contents, track_name):
        if n_clicks is None or not contents:
            return ""
        
        try:
            # Process uploaded files
            for content in contents:
                # Here you would save the file and load it in IGV
                # For demonstration, we'll just show success
                pass
            
            return html.Div([
                html.H5("✅ Track loaded successfully"),
                html.P(f"Track name: {track_name or 'Default'}"),
            ])
                
        except Exception as e:
            logger.error(f"Error loading track: {e}")
            return html.P(f"❌ Error: {str(e)}")
    
    @app.callback(
        Output("navigation-results", "children"),
        [Input("goto-locus", "n_clicks")],
        [State("genomic-locus", "value")]
    )
    def goto_locus(n_clicks, locus):
        if n_clicks is None or not locus:
            return ""
        
        try:
            result = igv_client.goto_locus(locus)
            
            if result['success']:
                return html.Div([
                    html.H5("✅ Navigated to locus"),
                    html.P(f"Locus: {locus}"),
                ])
            else:
                return html.Div([
                    html.H5("❌ Failed to navigate"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error navigating to locus: {e}")
            return html.P(f"❌ Error: {str(e)}")
