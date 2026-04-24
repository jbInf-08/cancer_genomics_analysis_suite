"""
Protein Structure Visualizer Dash Dashboard

This module provides a Dash-based web interface for protein structure visualization,
allowing users to load structures, analyze properties, visualize 3D structures,
and explore structural features interactively.
"""

import time

import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table, no_update
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import numpy as np
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import base64
import io
import math

from .visualizer import (
    ProteinStructureVisualizer,
    ProteinStructure,
    Atom,
    Residue,
    StructuralFeature,
    create_sample_protein_structure,
    create_sample_visualizer,
)

from CancerGenomicsSuite.modules.pipeline_orchestration.celery_md_poll import (
    poll_md_async_result,
)
from CancerGenomicsSuite.modules.pipeline_orchestration.md_workflow_dash_display import (
    md_workflow_result_to_div,
)
from CancerGenomicsSuite.modules.pipeline_orchestration.workflow_executor import (
    WorkflowExecutor,
)
from CancerGenomicsSuite.modules.gene_annotation.dash_error_display import (
    structured_error_to_dash,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProteinStructureDashboard:
    """
    Dash dashboard for protein structure visualization.
    """
    
    def __init__(self, app_name: str = "Protein Structure Visualizer"):
        """
        Initialize the protein structure visualization dashboard.
        
        Args:
            app_name: Name of the Dash app
        """
        self.app = dash.Dash(__name__)
        self.app.title = app_name
        self.visualizer = create_sample_visualizer()
        self.current_structure = None
        self._workflow_executor = WorkflowExecutor()
        self.setup_layout()
        self.setup_callbacks()
    
    def setup_layout(self):
        """Set up the dashboard layout."""
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1("Protein Structure Visualizer", className="header-title"),
                html.P("Interactive 3D protein structure visualization and analysis", className="header-subtitle")
            ], className="header"),
            
            # Structure Upload Panel
            html.Div([
                html.H3("Load Protein Structure"),
                html.Div([
                    html.Div([
                        html.Label("Structure File (PDB/CIF):"),
                        dcc.Upload(
                            id="structure-upload",
                            children=html.Div([
                                "Drag and Drop or ",
                                html.A("Select Structure File")
                            ]),
                            style={
                                "width": "100%",
                                "height": "60px",
                                "lineHeight": "60px",
                                "borderWidth": "1px",
                                "borderStyle": "dashed",
                                "borderRadius": "5px",
                                "textAlign": "center",
                                "margin": "10px"
                            },
                            multiple=False
                        )
                    ], className="upload-group"),
                    
                    html.Div([
                        html.Span(
                            [
                                html.Label("PDB ID (optional)"),
                                html.Span(
                                    " ⓘ",
                                    title="Four-character RCSB code for fetch / MD when not using AlphaFold.",
                                ),
                            ]
                        ),
                        dcc.Input(
                            id="pdb-id-input",
                            type="text",
                            placeholder="e.g., 1CRN, 1HTM",
                        ),
                    ], className="upload-group"),
                    html.Div([
                        html.Span(
                            [
                                html.Label("UniProt for AlphaFold (optional)"),
                                html.Span(
                                    " ⓘ",
                                    title="If set, MD uses AlphaFold DB model_v4 PDB instead of RCSB when PDB ID empty.",
                                ),
                            ]
                        ),
                        dcc.Input(
                            id="structure-md-uniprot-input",
                            type="text",
                            placeholder="e.g. P04637",
                            value="",
                        ),
                    ], className="upload-group"),
                    html.Div([
                        dcc.Checklist(
                            id="structure-md-use-gene-checklist",
                            options=[
                                {
                                    "label": "Resolve AlphaFold via gene symbol (uses PDB ID field as gene)",
                                    "value": "use_gene",
                                }
                            ],
                            value=[],
                            inputStyle={"marginRight": "8px"},
                        ),
                    ], className="upload-group"),
                    html.Div([
                        dcc.Checklist(
                            id="structure-md-celery-checklist",
                            options=[
                                {
                                    "label": "Queue MD on Celery worker",
                                    "value": "celery",
                                }
                            ],
                            value=[],
                            inputStyle={"marginRight": "8px"},
                        ),
                        html.Span(
                            " ⓘ",
                            title="Non-blocking; requires celery worker and md_workflow_tasks import path.",
                        ),
                    ], className="upload-group"),
                    html.Div([
                        dcc.Checklist(
                            id="structure-md-poll-celery-checklist",
                            options=[
                                {
                                    "label": "Poll Celery result backend in this tab",
                                    "value": "poll",
                                }
                            ],
                            value=["poll"],
                            inputStyle={"marginRight": "8px"},
                        ),
                        html.Span(
                            " ⓘ",
                            title="Optional progress and final MD summary when a result backend is configured.",
                        ),
                    ], className="upload-group"),
                    dcc.Store(id="structure-md-celery-task-store", data=None),
                    dcc.Interval(
                        id="structure-md-celery-poll-interval",
                        interval=3000,
                        n_intervals=0,
                        disabled=True,
                    ),
                    html.Button("Load Structure", id="load-structure-button", className="load-button"),
                    html.Button("Load Sample Structure", id="load-sample-button", className="sample-button"),
                    html.Button(
                        "Run MD (GROMACS)",
                        id="structure-run-md-button",
                        className="viz-button",
                        title=(
                            "Runs WorkflowExecutor MD: vacuum steepest-descent EM, not production MD. "
                            "See docs/MD_GROMACS_AND_ENSEMBL.md."
                        ),
                    ),
                    html.Div(
                        id="structure-md-output",
                        className="structure-info",
                        style={"marginTop": "10px"},
                    ),
                ], className="upload-grid")
            ], className="upload-panel"),
            
            # Structure Information Panel
            html.Div([
                html.H3("Structure Information"),
                html.Div(id="structure-info", className="structure-info")
            ], className="info-panel"),
            
            # Visualization Controls Panel
            html.Div([
                html.H3("Visualization Controls"),
                html.Div([
                    html.Div([
                        html.Label("Chain:"),
                        dcc.Dropdown(
                            id="chain-dropdown",
                            options=[],
                            clearable=False
                        )
                    ], className="control-group"),
                    
                    html.Div([
                        html.Label("Representation:"),
                        dcc.Dropdown(
                            id="representation-dropdown",
                            options=[
                                {"label": "Cartoon", "value": "cartoon"},
                                {"label": "Stick", "value": "stick"},
                                {"label": "Sphere", "value": "sphere"},
                                {"label": "Surface", "value": "surface"},
                                {"label": "Ribbon", "value": "ribbon"}
                            ],
                            value="cartoon",
                            clearable=False
                        )
                    ], className="control-group"),
                    
                    html.Div([
                        html.Label("Color Scheme:"),
                        dcc.Dropdown(
                            id="color-scheme-dropdown",
                            options=[
                                {"label": "Chain", "value": "chain"},
                                {"label": "Secondary Structure", "value": "secondary"},
                                {"label": "Residue Type", "value": "residue"},
                                {"label": "B-factor", "value": "bfactor"},
                                {"label": "Hydrophobicity", "value": "hydrophobicity"}
                            ],
                            value="chain",
                            clearable=False
                        )
                    ], className="control-group"),
                    
                    html.Div([
                        html.Label("Show Features:"),
                        dcc.Checklist(
                            id="features-checklist",
                            options=[
                                {"label": "Domains", "value": "domains"},
                                {"label": "Binding Sites", "value": "binding_sites"},
                                {"label": "Active Sites", "value": "active_sites"},
                                {"label": "Secondary Structure", "value": "secondary_structure"}
                            ],
                            value=["domains"],
                            inline=True
                        )
                    ], className="control-group")
                ], className="controls-grid"),
                
                html.Div([
                    html.Button("Update Visualization", id="update-viz-button", className="viz-button"),
                    html.Button("Reset View", id="reset-view-button", className="reset-button")
                ], className="button-group")
            ], className="controls-panel"),
            
            # 3D Visualization Panel
            html.Div([
                html.H3("3D Structure Visualization"),
                dcc.Graph(
                    id="structure-3d-plot",
                    config={
                        'displayModeBar': True,
                        'displaylogo': False,
                        'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d']
                    }
                )
            ], className="visualization-panel"),
            
            # Analysis Panel
            html.Div([
                html.H3("Structure Analysis"),
                dcc.Tabs(id="analysis-tabs", value="statistics", children=[
                    dcc.Tab(label="Statistics", value="statistics"),
                    dcc.Tab(label="Distances", value="distances"),
                    dcc.Tab(label="Nearby Residues", value="nearby"),
                    dcc.Tab(label="Secondary Structure", value="secondary"),
                    dcc.Tab(label="Features", value="features")
                ]),
                html.Div(id="structure-analysis-content", className="analysis-content")
            ], className="analysis-panel"),
            
            # Results Table Panel
            html.Div([
                html.H3("Structure Data"),
                html.Div([
                    html.Label("Show:"),
                    dcc.Dropdown(
                        id="data-type-dropdown",
                        options=[
                            {"label": "Atoms", "value": "atoms"},
                            {"label": "Residues", "value": "residues"},
                            {"label": "Chains", "value": "chains"},
                            {"label": "Features", "value": "features"}
                        ],
                        value="residues",
                        clearable=False
                    )
                ], className="table-controls"),
                html.Div(id="data-table-container")
            ], className="table-panel"),
            
            # Export Panel
            html.Div([
                html.H3("Export Structure"),
                html.Div([
                    html.Label("Format:"),
                    dcc.Dropdown(
                        id="export-format-dropdown",
                        options=[
                            {"label": "JSON", "value": "json"},
                            {"label": "PDB", "value": "pdb"},
                            {"label": "XYZ", "value": "xyz"}
                        ],
                        value="json",
                        clearable=False,
                        style={"width": "150px"}
                    ),
                    html.Button("Export", id="export-button", className="export-button")
                ], className="export-controls"),
                html.Div(id="export-output", className="export-output")
            ], className="export-panel"),
            
            # Statistics Panel
            html.Div([
                html.H3("Visualizer Statistics"),
                html.Div(id="statistics-display", className="statistics-display")
            ], className="statistics-panel"),
            
            # Hidden divs to store data
            html.Div(id="loaded-structure", style={"display": "none"}),
            html.Div(id="analysis-status", style={"display": "none"})
        ], className="main-container")
    
    def setup_callbacks(self):
        """Set up Dash callbacks for interactivity."""
        
        @self.app.callback(
            [Output("loaded-structure", "children"),
             Output("structure-info", "children"),
             Output("chain-dropdown", "options"),
             Output("chain-dropdown", "value")],
            [Input("load-structure-button", "n_clicks"),
             Input("load-sample-button", "n_clicks")],
            [State("structure-upload", "contents"),
             State("pdb-id-input", "value")]
        )
        def load_structure(load_clicks, sample_clicks, structure_content, pdb_id):
            """Load protein structure."""
            
            ctx = callback_context
            if not ctx.triggered:
                return "", "", [], None
            
            button_id = ctx.triggered[0]["prop_id"].split(".")[0]
            
            if button_id == "load-sample-button" and sample_clicks:
                # Load sample structure
                self.visualizer = create_sample_visualizer()
                self.current_structure = self.visualizer.current_structure
                
            elif button_id == "load-structure-button" and load_clicks:
                # Load uploaded structure
                if not structure_content:
                    return "", "Please upload a structure file", [], None
                
                try:
                    # Parse uploaded file
                    content_type, content_string = structure_content.split(',')
                    decoded = base64.b64decode(content_string)
                    
                    # Save to temporary file and load
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.pdb', delete=False) as tmp_file:
                        tmp_file.write(decoded.decode('utf-8'))
                        tmp_file_path = tmp_file.name
                    
                    self.visualizer.load_structure(tmp_file_path, pdb_id)
                    self.current_structure = self.visualizer.current_structure
                    
                    # Clean up temporary file
                    import os
                    os.unlink(tmp_file_path)
                    
                except Exception as e:
                    return "", f"Error loading structure: {str(e)}", [], None
            
            else:
                return "", "", [], None
            
            # Generate structure info and chain options
            if self.current_structure:
                structure_info = self._create_structure_info()
                chain_options = [{"label": chain_id, "value": chain_id} for chain_id in self.current_structure.chains.keys()]
                chain_value = chain_options[0]["value"] if chain_options else None
                structure_json = json.dumps(self.current_structure.to_dict())
            else:
                structure_info = "No structure loaded"
                chain_options = []
                chain_value = None
                structure_json = ""
            
            return structure_json, structure_info, chain_options, chain_value

        @self.app.callback(
            [
                Output("structure-md-output", "children"),
                Output("structure-md-celery-task-store", "data"),
                Output("structure-md-celery-poll-interval", "disabled"),
            ],
            [Input("structure-run-md-button", "n_clicks")],
            [
                State("pdb-id-input", "value"),
                State("structure-md-uniprot-input", "value"),
                State("structure-md-use-gene-checklist", "value"),
                State("structure-md-celery-checklist", "value"),
                State("structure-md-poll-celery-checklist", "value"),
            ],
        )
        def run_structure_md(n_clicks, pdb_id, uniprot, gene_flags, celery_flags, poll_flags):
            if not n_clicks:
                return "", None, True
            pid = (pdb_id or "").strip().upper()
            up = (uniprot or "").strip().upper()
            use_gene = gene_flags and "use_gene" in gene_flags
            use_celery = celery_flags and "celery" in celery_flags
            want_poll = poll_flags and "poll" in poll_flags

            cfg: Dict[str, Any] = {}
            wf_suffix = "structure"
            if len(pid) == 4:
                cfg["pdb_id"] = pid
                wf_suffix = pid
            elif up and len(up) >= 6:
                cfg["alphafold_uniprot"] = up
                wf_suffix = up
            elif use_gene and pid:
                cfg["alphafold_gene_symbol"] = pid.strip()
                wf_suffix = pid.strip()[:16]
            else:
                msg = (
                    "Enter a four-letter PDB ID, a UniProt accession for AlphaFold, "
                    "or enable gene resolution and type a gene symbol in the PDB ID field."
                )
                return html.P(msg, className="error-message"), None, True

            wname = f"md_structure_dash_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{wf_suffix}"

            if use_celery:
                try:
                    from celery_worker.tasks.md_workflow_tasks import run_md_workflow
                except ImportError:
                    run_md_workflow = None
                if run_md_workflow is None:
                    return (
                        html.P(
                            "Celery md task not importable; run without Celery or fix PYTHONPATH.",
                            className="error-message",
                        ),
                        None,
                        True,
                    )
                hp = self._workflow_executor.history_persist_path
                ar = run_md_workflow.delay(
                    cfg,
                    wname,
                    work_dir=str(self._workflow_executor.work_dir),
                    history_persist_path=str(hp) if hp else None,
                )
                tid = ar.id
                if want_poll:
                    return (
                        html.Div(
                            [
                                html.P([html.Strong("Celery task submitted — polling")]),
                                html.P(
                                    [
                                        "Task id: ",
                                        html.Code(tid, style={"wordBreak": "break-all"}),
                                    ]
                                ),
                                html.P(f"Workflow: {wname}", style={"fontSize": "0.95em"}),
                            ]
                        ),
                        {"task_id": tid, "workflow_name": wname, "t_mono": time.monotonic()},
                        False,
                    )
                return (
                    html.Div(
                        [
                            html.P([html.Strong("Celery task submitted")]),
                            html.P(
                                [
                                    "Task id: ",
                                    html.Code(tid, style={"wordBreak": "break-all"}),
                                ]
                            ),
                            html.P(f"Workflow: {wname}", style={"fontSize": "0.95em"}),
                            html.P(
                                "Polling is off — enable “Poll Celery result backend” or check Flower.",
                                style={"fontSize": "0.9em"},
                            ),
                        ]
                    ),
                    None,
                    True,
                )

            try:
                res = self._workflow_executor.run_molecular_dynamics_workflow(
                    cfg, workflow_name=wname
                )
            except Exception as e:
                logger.exception("Structure MD workflow failed")
                return html.P(f"Error: {e}", className="error-message"), None, True

            return (
                md_workflow_result_to_div(res, wname, structured_error_to_dash),
                None,
                True,
            )

        @self.app.callback(
            Output("structure-md-output", "children", allow_duplicate=True),
            Output("structure-md-celery-task-store", "data", allow_duplicate=True),
            Output("structure-md-celery-poll-interval", "disabled", allow_duplicate=True),
            Input("structure-md-celery-poll-interval", "n_intervals"),
            State("structure-md-celery-task-store", "data"),
            prevent_initial_call=True,
        )
        def poll_structure_md_celery(_n_intervals, store):
            if not store or not store.get("task_id"):
                return no_update, no_update, no_update
            div, stop = poll_md_async_result(
                str(store["task_id"]),
                str(store.get("workflow_name") or ""),
                structured_error_to_dash=structured_error_to_dash,
                started_monotonic=store.get("t_mono"),
            )
            if stop:
                return div, None, True
            return div, store, False
        
        @self.app.callback(
            [Output("structure-3d-plot", "figure"),
             Output("analysis-status", "children")],
            [Input("update-viz-button", "n_clicks"),
             Input("reset-view-button", "n_clicks")],
            [State("chain-dropdown", "value"),
             State("representation-dropdown", "value"),
             State("color-scheme-dropdown", "value"),
             State("features-checklist", "value")]
        )
        def update_visualization(update_clicks, reset_clicks, chain_id, representation, color_scheme, features):
            """Update 3D structure visualization."""
            
            if not self.current_structure:
                return go.Figure().add_annotation(
                    text="No structure loaded",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                ), ""
            
            try:
                figure = self._create_3d_structure_plot(chain_id, representation, color_scheme, features)
                status = "Visualization updated successfully"
                return figure, status
                
            except Exception as e:
                return go.Figure().add_annotation(
                    text=f"Error creating visualization: {str(e)}",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                ), f"Error: {str(e)}"
        
        @self.app.callback(
            Output("structure-analysis-content", "children"),
            [Input("analysis-tabs", "value")],
            [State("chain-dropdown", "value")]
        )
        def update_analysis_content(tab_value, chain_id):
            """Update analysis content based on selected tab."""
            if not self.current_structure:
                return "No structure loaded"
            
            if tab_value == "statistics":
                return self._create_statistics_content(chain_id)
            elif tab_value == "distances":
                return self._create_distances_content(chain_id)
            elif tab_value == "nearby":
                return self._create_nearby_residues_content(chain_id)
            elif tab_value == "secondary":
                return self._create_secondary_structure_content(chain_id)
            elif tab_value == "features":
                return self._create_features_content()
            else:
                return "Select an analysis tab"
        
        @self.app.callback(
            Output("data-table-container", "children"),
            [Input("data-type-dropdown", "value")],
            [State("chain-dropdown", "value")]
        )
        def update_data_table(data_type, chain_id):
            """Update data table based on selection."""
            if not self.current_structure:
                return "No structure loaded"
            
            if data_type == "atoms":
                return self._create_atoms_table(chain_id)
            elif data_type == "residues":
                return self._create_residues_table(chain_id)
            elif data_type == "chains":
                return self._create_chains_table()
            elif data_type == "features":
                return self._create_features_table()
            else:
                return "Select a data type"
        
        @self.app.callback(
            Output("export-output", "children"),
            [Input("export-button", "n_clicks")],
            [State("export-format-dropdown", "value")]
        )
        def export_structure(export_clicks, format_type):
            """Export structure data."""
            if not export_clicks or not self.current_structure:
                return ""
            
            try:
                exported_data = self.visualizer.export_structure(self.current_structure.pdb_id, format_type)
                
                if format_type == "json":
                    data_dict = json.loads(exported_data)
                    formatted_data = json.dumps(data_dict, indent=2)
                else:
                    formatted_data = exported_data
                
                return html.Div([
                    html.H4(f"Exported Structure ({format_type.upper()})"),
                    html.Pre(formatted_data, className="export-data")
                ])
                
            except Exception as e:
                return html.Div([
                    html.H4("Export Error"),
                    html.P(f"Error exporting structure: {str(e)}")
                ], className="error-message")
        
        @self.app.callback(
            Output("statistics-display", "children"),
            [Input("load-structure-button", "n_clicks"),
             Input("load-sample-button", "n_clicks")]
        )
        def update_statistics(load_clicks, sample_clicks):
            """Update visualizer statistics."""
            stats = self.visualizer.get_statistics()
            
            return html.Div([
                html.P([
                    html.Strong("Loaded Structures: "), str(stats["loaded_structures"]),
                    html.Br(),
                    html.Strong("Structure IDs: "), ", ".join(stats["structure_ids"]),
                    html.Br(),
                    html.Strong("Current Structure: "), stats["current_structure"] or "None",
                    html.Br(),
                    html.Strong("Supported Formats: "), ", ".join(stats["supported_formats"]),
                    html.Br(),
                    html.Strong("Total Features: "), str(stats["total_features"])
                ])
            ])
    
    def _create_structure_info(self) -> html.Div:
        """Create structure information display."""
        if not self.current_structure:
            return html.P("No structure loaded")
        
        structure = self.current_structure
        
        return html.Div([
            html.P([
                html.Strong("PDB ID: "), structure.pdb_id,
                html.Br(),
                html.Strong("Title: "), structure.title,
                html.Br(),
                html.Strong("Resolution: "), f"{structure.resolution:.2f} Å" if structure.resolution else "N/A",
                html.Br(),
                html.Strong("R-value: "), f"{structure.r_value:.3f}" if structure.r_value else "N/A",
                html.Br(),
                html.Strong("R-free: "), f"{structure.r_free:.3f}" if structure.r_free else "N/A",
                html.Br(),
                html.Strong("Chains: "), ", ".join(structure.chains.keys()),
                html.Br(),
                html.Strong("Total Atoms: "), str(len(structure.get_all_atoms())),
                html.Br(),
                html.Strong("Total Residues: "), str(sum(len(chain) for chain in structure.chains.values()))
            ])
        ])
    
    def _create_3d_structure_plot(self, chain_id: str, representation: str, 
                                 color_scheme: str, features: List[str]) -> go.Figure:
        """Create 3D structure visualization."""
        if not self.current_structure:
            return go.Figure()
        
        structure = self.current_structure
        chain = structure.get_chain(chain_id) if chain_id else None
        
        if not chain:
            return go.Figure().add_annotation(
                text="Chain not found",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
        
        # Create traces for different representations
        traces = []
        
        if representation == "cartoon":
            # Simplified cartoon representation using CA atoms
            ca_atoms = []
            for residue in chain:
                ca_atom = residue.get_atom("CA")
                if ca_atom:
                    ca_atoms.append(ca_atom)
            
            if ca_atoms:
                x_coords = [atom.x for atom in ca_atoms]
                y_coords = [atom.y for atom in ca_atoms]
                z_coords = [atom.z for atom in ca_atoms]
                
                # Create color array based on color scheme
                if color_scheme == "chain":
                    colors = ["#FF6B6B"] * len(ca_atoms)
                elif color_scheme == "secondary":
                    colors = ["#4ECDC4" if i % 4 == 0 else "#FF6B6B" for i in range(len(ca_atoms))]
                else:
                    colors = ["#45B7D1"] * len(ca_atoms)
                
                trace = go.Scatter3d(
                    x=x_coords,
                    y=y_coords,
                    z=z_coords,
                    mode='lines+markers',
                    line=dict(color='#333333', width=8),
                    marker=dict(size=4, color=colors),
                    name="Backbone",
                    hovertemplate="Residue: %{text}<extra></extra>",
                    text=[f"{atom.residue_name}{atom.residue_number}" for atom in ca_atoms]
                )
                traces.append(trace)
        
        elif representation == "stick":
            # Stick representation for all atoms
            all_atoms = []
            for residue in chain:
                all_atoms.extend(residue.atoms)
            
            if all_atoms:
                x_coords = [atom.x for atom in all_atoms]
                y_coords = [atom.y for atom in all_atoms]
                z_coords = [atom.z for atom in all_atoms]
                
                # Color by element
                element_colors = {
                    "C": "#333333", "N": "#3050F8", "O": "#FF0D0D", 
                    "S": "#FFFF30", "H": "#FFFFFF", "P": "#FF8000"
                }
                colors = [element_colors.get(atom.element, "#888888") for atom in all_atoms]
                
                trace = go.Scatter3d(
                    x=x_coords,
                    y=y_coords,
                    z=z_coords,
                    mode='markers',
                    marker=dict(size=3, color=colors),
                    name="Atoms",
                    hovertemplate="%{text}<extra></extra>",
                    text=[f"{atom.element} {atom.residue_name}{atom.residue_number}" for atom in all_atoms]
                )
                traces.append(trace)
        
        # Add feature traces if requested
        if "domains" in features and structure.pdb_id in self.visualizer.structural_features:
            for feature in self.visualizer.structural_features[structure.pdb_id]:
                if feature.feature_type == "domain":
                    # Highlight domain residues
                    domain_residues = []
                    for residue in chain:
                        if feature.start_residue <= residue.residue_number <= feature.end_residue:
                            ca_atom = residue.get_atom("CA")
                            if ca_atom:
                                domain_residues.append(ca_atom)
                    
                    if domain_residues:
                        x_coords = [atom.x for atom in domain_residues]
                        y_coords = [atom.y for atom in domain_residues]
                        z_coords = [atom.z for atom in domain_residues]
                        
                        trace = go.Scatter3d(
                            x=x_coords,
                            y=y_coords,
                            z=z_coords,
                            mode='markers',
                            marker=dict(size=6, color="#96CEB4"),
                            name=f"Domain: {feature.name}",
                            hovertemplate="%{text}<extra></extra>",
                            text=[f"{atom.residue_name}{atom.residue_number}" for atom in domain_residues]
                        )
                        traces.append(trace)
        
        # Create figure
        fig = go.Figure(data=traces)
        
        fig.update_layout(
            title=f"3D Structure: {structure.pdb_id} Chain {chain_id}",
            scene=dict(
                xaxis_title="X (Å)",
                yaxis_title="Y (Å)",
                zaxis_title="Z (Å)",
                aspectmode="data"
            ),
            height=600,
            showlegend=True
        )
        
        return fig
    
    def _create_statistics_content(self, chain_id: str) -> html.Div:
        """Create statistics analysis content."""
        if not self.current_structure or not chain_id:
            return "No structure or chain selected"
        
        try:
            stats = self.visualizer.get_chain_statistics(self.current_structure.pdb_id, chain_id)
            
            return html.Div([
                html.H4(f"Chain {chain_id} Statistics"),
                html.P([
                    html.Strong("Total Residues: "), str(stats["total_residues"]),
                    html.Br(),
                    html.Strong("Total Atoms: "), str(stats["total_atoms"]),
                    html.Br(),
                    html.Strong("Chain Length: "), f"{stats['chain_length']:.2f} Å",
                    html.Br(),
                    html.Strong("Residue Range: "), f"{stats['first_residue']} - {stats['last_residue']}"
                ]),
                html.H5("Residue Composition:"),
                html.Ul([
                    html.Li(f"{residue_type}: {count}")
                    for residue_type, count in stats["residue_types"].items()
                ])
            ])
            
        except Exception as e:
            return f"Error calculating statistics: {str(e)}"
    
    def _create_distances_content(self, chain_id: str) -> html.Div:
        """Create distance analysis content."""
        if not self.current_structure or not chain_id:
            return "No structure or chain selected"
        
        return html.Div([
            html.H4("Distance Calculator"),
            html.Div([
                html.Div([
                    html.Label("Residue 1:"),
                    dcc.Input(id="residue1-input", type="number", value=1, min=1)
                ], className="distance-input"),
                html.Div([
                    html.Label("Residue 2:"),
                    dcc.Input(id="residue2-input", type="number", value=5, min=1)
                ], className="distance-input"),
                html.Button("Calculate Distance", id="calculate-distance-button", className="calc-button")
            ], className="distance-controls"),
            html.Div(id="distance-result", className="distance-result")
        ])
    
    def _create_nearby_residues_content(self, chain_id: str) -> html.Div:
        """Create nearby residues analysis content."""
        if not self.current_structure or not chain_id:
            return "No structure or chain selected"
        
        return html.Div([
            html.H4("Nearby Residues Finder"),
            html.Div([
                html.Div([
                    html.Label("Target Residue:"),
                    dcc.Input(id="target-residue-input", type="number", value=10, min=1)
                ], className="nearby-input"),
                html.Div([
                    html.Label("Distance Cutoff (Å):"),
                    dcc.Input(id="distance-cutoff-input", type="number", value=5.0, min=0.1, step=0.1)
                ], className="nearby-input"),
                html.Button("Find Nearby", id="find-nearby-button", className="find-button")
            ], className="nearby-controls"),
            html.Div(id="nearby-results", className="nearby-results")
        ])
    
    def _create_secondary_structure_content(self, chain_id: str) -> html.Div:
        """Create secondary structure analysis content."""
        if not self.current_structure or not chain_id:
            return "No structure or chain selected"
        
        try:
            secondary_structure = self.visualizer.get_secondary_structure(self.current_structure.pdb_id, chain_id)
            
            content = [html.H4(f"Secondary Structure - Chain {chain_id}")]
            
            for ss_type, ranges in secondary_structure.items():
                if ranges:
                    content.append(html.H5(ss_type.title()))
                    content.append(html.Ul([
                        html.Li(f"Residues {start}-{end}")
                        for start, end in ranges
                    ]))
            
            return html.Div(content)
            
        except Exception as e:
            return f"Error analyzing secondary structure: {str(e)}"
    
    def _create_features_content(self) -> html.Div:
        """Create structural features content."""
        if not self.current_structure:
            return "No structure loaded"
        
        pdb_id = self.current_structure.pdb_id
        if pdb_id not in self.visualizer.structural_features:
            return "No structural features found"
        
        features = self.visualizer.structural_features[pdb_id]
        
        content = [html.H4("Structural Features")]
        
        for feature in features:
            content.append(html.Div([
                html.H5(f"{feature.feature_type.title()}: {feature.name}"),
                html.P([
                    html.Strong("Description: "), feature.description,
                    html.Br(),
                    html.Strong("Chain: "), feature.chain_id,
                    html.Br(),
                    html.Strong("Residues: "), f"{feature.start_residue}-{feature.end_residue}",
                    html.Br(),
                    html.Strong("Confidence: "), f"{feature.confidence:.2f}"
                ])
            ], className="feature-item"))
        
        return html.Div(content)
    
    def _create_atoms_table(self, chain_id: str) -> html.Div:
        """Create atoms data table."""
        if not self.current_structure or not chain_id:
            return "No structure or chain selected"
        
        chain = self.current_structure.get_chain(chain_id)
        if not chain:
            return "Chain not found"
        
        # Prepare data for table
        table_data = []
        for residue in chain:
            for atom in residue.atoms:
                table_data.append({
                    "Atom ID": atom.atom_id,
                    "Atom Name": atom.atom_name,
                    "Residue": f"{residue.residue_name}{residue.residue_number}",
                    "Element": atom.element,
                    "X": f"{atom.x:.3f}",
                    "Y": f"{atom.y:.3f}",
                    "Z": f"{atom.z:.3f}",
                    "B-factor": f"{atom.b_factor:.2f}"
                })
        
        return dash_table.DataTable(
            data=table_data,
            columns=[{"name": col, "id": col} for col in table_data[0].keys()],
            style_cell={"textAlign": "left", "padding": "10px"},
            style_header={"backgroundColor": "#f0f0f0", "fontWeight": "bold"},
            page_size=20,
            sort_action="native",
            filter_action="native"
        )
    
    def _create_residues_table(self, chain_id: str) -> html.Div:
        """Create residues data table."""
        if not self.current_structure or not chain_id:
            return "No structure or chain selected"
        
        chain = self.current_structure.get_chain(chain_id)
        if not chain:
            return "Chain not found"
        
        # Prepare data for table
        table_data = []
        for residue in chain:
            center = residue.get_center()
            table_data.append({
                "Residue Number": residue.residue_number,
                "Residue Name": residue.residue_name,
                "Chain": residue.chain_id,
                "Atom Count": len(residue.atoms),
                "Center X": f"{center[0]:.3f}",
                "Center Y": f"{center[1]:.3f}",
                "Center Z": f"{center[2]:.3f}"
            })
        
        return dash_table.DataTable(
            data=table_data,
            columns=[{"name": col, "id": col} for col in table_data[0].keys()],
            style_cell={"textAlign": "left", "padding": "10px"},
            style_header={"backgroundColor": "#f0f0f0", "fontWeight": "bold"},
            page_size=20,
            sort_action="native",
            filter_action="native"
        )
    
    def _create_chains_table(self) -> html.Div:
        """Create chains data table."""
        if not self.current_structure:
            return "No structure loaded"
        
        # Prepare data for table
        table_data = []
        for chain_id, chain in self.current_structure.chains.items():
            stats = self.visualizer.get_chain_statistics(self.current_structure.pdb_id, chain_id)
            table_data.append({
                "Chain ID": chain_id,
                "Residue Count": stats["total_residues"],
                "Atom Count": stats["total_atoms"],
                "Length (Å)": f"{stats['chain_length']:.2f}",
                "First Residue": stats["first_residue"],
                "Last Residue": stats["last_residue"]
            })
        
        return dash_table.DataTable(
            data=table_data,
            columns=[{"name": col, "id": col} for col in table_data[0].keys()],
            style_cell={"textAlign": "left", "padding": "10px"},
            style_header={"backgroundColor": "#f0f0f0", "fontWeight": "bold"},
            page_size=20,
            sort_action="native",
            filter_action="native"
        )
    
    def _create_features_table(self) -> html.Div:
        """Create features data table."""
        if not self.current_structure:
            return "No structure loaded"
        
        pdb_id = self.current_structure.pdb_id
        if pdb_id not in self.visualizer.structural_features:
            return "No structural features found"
        
        features = self.visualizer.structural_features[pdb_id]
        
        # Prepare data for table
        table_data = []
        for feature in features:
            table_data.append({
                "Type": feature.feature_type,
                "Name": feature.name,
                "Description": feature.description,
                "Chain": feature.chain_id,
                "Start": feature.start_residue,
                "End": feature.end_residue,
                "Confidence": f"{feature.confidence:.2f}"
            })
        
        return dash_table.DataTable(
            data=table_data,
            columns=[{"name": col, "id": col} for col in table_data[0].keys()],
            style_cell={"textAlign": "left", "padding": "10px"},
            style_header={"backgroundColor": "#f0f0f0", "fontWeight": "bold"},
            page_size=20,
            sort_action="native",
            filter_action="native"
        )
    
    def run(self, debug: bool = True, port: int = 8053):
        """
        Run the dashboard.
        
        Args:
            debug: Enable debug mode
            port: Port to run the app on
        """
        logger.info(f"Starting Protein Structure Visualizer Dashboard on port {port}")
        self.app.run_server(debug=debug, port=port)


# CSS Styles
custom_css = """
.main-container {
    fontFamily: 'Inter', sans-serif;
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
}

.header {
    text-align: center;
    margin-bottom: 30px;
    padding: 20px;
    background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
    color: white;
    border-radius: 10px;
}

.header-title {
    margin: 0;
    font-size: 2.5em;
    font-weight: 700;
}

.header-subtitle {
    margin: 10px 0 0 0;
    font-size: 1.1em;
    opacity: 0.9;
}

.upload-panel, .info-panel, .controls-panel, .visualization-panel, .analysis-panel, .table-panel, .export-panel, .statistics-panel {
    margin-bottom: 20px;
    padding: 20px;
    background: white;
    border-radius: 8px;
    border: 1px solid #e9ecef;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.upload-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 15px;
    margin-bottom: 20px;
}

.upload-group {
    display: flex;
    flex-direction: column;
}

.upload-group label {
    font-weight: 500;
    margin-bottom: 5px;
    color: #495057;
}

.load-button, .sample-button {
    background: #2ecc71;
    color: white;
    border: none;
    padding: 12px 24px;
    border-radius: 5px;
    cursor: pointer;
    font-weight: 500;
    font-size: 1.1em;
    transition: background-color 0.2s;
    margin: 5px;
}

.load-button:hover, .sample-button:hover {
    background: #27ae60;
}

.structure-info {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 5px;
    border-left: 4px solid #2ecc71;
}

.controls-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    margin-bottom: 20px;
}

.control-group {
    display: flex;
    flex-direction: column;
}

.control-group label {
    font-weight: 500;
    margin-bottom: 5px;
    color: #495057;
}

.button-group {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}

.viz-button, .reset-button {
    background: #3498db;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 5px;
    cursor: pointer;
    font-weight: 500;
    transition: background-color 0.2s;
}

.viz-button:hover, .reset-button:hover {
    background: #2980b9;
}

.visualization-panel {
    background: white;
    border-radius: 8px;
    border: 1px solid #e9ecef;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    overflow: hidden;
}

.analysis-content {
    margin-top: 20px;
    background: #f8f9fa;
    padding: 15px;
    border-radius: 5px;
}

.distance-controls, .nearby-controls {
    display: flex;
    gap: 10px;
    align-items: center;
    margin-bottom: 15px;
}

.distance-input, .nearby-input {
    display: flex;
    flex-direction: column;
    min-width: 120px;
}

.calc-button, .find-button {
    background: #e74c3c;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-weight: 500;
}

.calc-button:hover, .find-button:hover {
    background: #c0392b;
}

.distance-result, .nearby-results {
    background: white;
    padding: 15px;
    border-radius: 5px;
    border: 1px solid #e9ecef;
    margin-top: 10px;
}

.feature-item {
    background: white;
    padding: 15px;
    margin-bottom: 10px;
    border-radius: 5px;
    border-left: 4px solid #f39c12;
}

.table-controls {
    display: flex;
    gap: 10px;
    align-items: center;
    margin-bottom: 15px;
}

.export-controls {
    display: flex;
    gap: 10px;
    align-items: center;
    margin-bottom: 15px;
}

.export-button {
    background: #9b59b6;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 5px;
    cursor: pointer;
    font-weight: 500;
}

.export-button:hover {
    background: #8e44ad;
}

.export-data {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 5px;
    border: 1px solid #e9ecef;
    max-height: 400px;
    overflow-y: auto;
    fontFamily: 'Courier New', monospace;
    font-size: 0.9em;
}

.statistics-display {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 5px;
}

.error-message {
    color: #dc3545;
    background: #f8d7da;
    padding: 10px;
    border-radius: 5px;
    border: 1px solid #f5c6cb;
}
"""


def create_protein_structure_dashboard() -> ProteinStructureDashboard:
    """
    Create and return a protein structure visualization dashboard instance.
    
    Returns:
        ProteinStructureDashboard instance
    """
    return ProteinStructureDashboard()


if __name__ == "__main__":
    # Create and run the dashboard
    dashboard = create_protein_structure_dashboard()
    
    # Add custom CSS
    dashboard.app.index_string = f"""
    <!DOCTYPE html>
    <html>
        <head>
            {{%metas%}}
            <title>{{%title%}}</title>
            {{%favicon%}}
            {{%css%}}
            <style>{custom_css}</style>
        </head>
        <body>
            {{%app_entry%}}
            <footer>
                {{%config%}}
                {{%scripts%}}
                {{%renderer%}}
            </footer>
        </body>
    </html>
    """
    
    dashboard.run(debug=True, port=8053)
