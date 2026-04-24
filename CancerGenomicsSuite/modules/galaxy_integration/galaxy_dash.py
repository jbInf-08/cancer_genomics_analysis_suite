"""
Galaxy Integration Dashboard

Provides a Dash interface for interacting with Galaxy workflows and tools.
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import json
from typing import Dict, List, Any
import logging

from .galaxy_client import GalaxyClient, GalaxyWorkflow, GalaxyDataset

logger = logging.getLogger(__name__)

# Initialize Galaxy client
galaxy_client = GalaxyClient()

# Dashboard layout
layout = html.Div([
    html.Div([
        html.H2("🌌 Galaxy Integration", className="section-title"),
        html.P("Access Galaxy workflows, tools, and data analysis capabilities", className="section-description"),
    ], className="section-header"),
    
    # Configuration section
    html.Div([
        html.H3("Configuration", className="subsection-title"),
        html.Div([
            html.Label("Galaxy URL:", className="input-label"),
            dcc.Input(
                id="galaxy-url",
                type="url",
                value="https://usegalaxy.org",
                placeholder="https://usegalaxy.org",
                className="input-field"
            ),
        ], className="input-group"),
        html.Div([
            html.Label("API Key:", className="input-label"),
            dcc.Input(
                id="galaxy-api-key",
                type="password",
                placeholder="Enter your Galaxy API key",
                className="input-field"
            ),
        ], className="input-group"),
        html.Button("Connect to Galaxy", id="connect-galaxy", className="button primary"),
        html.Div(id="connection-status", className="status-message"),
    ], className="config-section"),
    
    # Workflows section
    html.Div([
        html.H3("Available Workflows", className="subsection-title"),
        html.Div([
            html.Button("Refresh Workflows", id="refresh-workflows", className="button secondary"),
            html.Div(id="workflows-list", className="workflows-container"),
        ]),
    ], className="workflows-section"),
    
    # Tools section
    html.Div([
        html.H3("Available Tools", className="subsection-title"),
        html.Div([
            html.Button("Refresh Tools", id="refresh-tools", className="button secondary"),
            dcc.Input(
                id="tool-search",
                type="text",
                placeholder="Search tools...",
                className="input-field"
            ),
            html.Div(id="tools-list", className="tools-container"),
        ]),
    ], className="tools-section"),
    
    # File upload section
    html.Div([
        html.H3("Upload Files", className="subsection-title"),
        dcc.Upload(
            id="file-upload",
            children=html.Div([
                "Drag and Drop or ",
                html.A("Select Files")
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
        html.Div(id="galaxy-upload-status", className="upload-status"),
    ], className="upload-section"),
    
    # Workflow execution section
    html.Div([
        html.H3("Execute Workflow", className="subsection-title"),
        html.Div([
            html.Label("Select Workflow:", className="input-label"),
            dcc.Dropdown(
                id="workflow-selector",
                placeholder="Choose a workflow...",
                className="dropdown"
            ),
        ], className="input-group"),
        html.Div([
            html.Label("Input Parameters:", className="input-label"),
            html.Div(id="workflow-parameters", className="parameters-container"),
        ], className="input-group"),
        html.Button("Run Workflow", id="run-workflow", className="button primary"),
        html.Div(id="workflow-status", className="workflow-status"),
    ], className="execution-section"),
    
    # Results section
    html.Div([
        html.H3("Results", className="subsection-title"),
        html.Div(id="results-container", className="results-container"),
    ], className="results-section"),
    
    # Hidden divs for storing data
    html.Div(id="galaxy-data", style={"display": "none"}),
    html.Div(id="workflow-data", style={"display": "none"}),
])

def register_callbacks(app):
    """Register callbacks for the Galaxy dashboard"""
    
    @app.callback(
        [Output("connection-status", "children"),
         Output("galaxy-data", "children")],
        [Input("connect-galaxy", "n_clicks")],
        [State("galaxy-url", "value"),
         State("galaxy-api-key", "value")]
    )
    def connect_to_galaxy(n_clicks, url, api_key):
        if n_clicks is None:
            return "", ""
        
        try:
            global galaxy_client
            galaxy_client = GalaxyClient(url, api_key)
            
            # Test connection by fetching workflows
            workflows = galaxy_client.get_workflows()
            
            if workflows:
                status = html.Div([
                    html.Span("✅ Connected to Galaxy successfully", className="success-message"),
                    html.Br(),
                    html.Span(f"Found {len(workflows)} workflows", className="info-message")
                ])
                return status, json.dumps([{"id": w.id, "name": w.name} for w in workflows])
            else:
                return html.Span("⚠️ Connected but no workflows found", className="warning-message"), ""
                
        except Exception as e:
            logger.error(f"Error connecting to Galaxy: {e}")
            return html.Span(f"❌ Connection failed: {str(e)}", className="error-message"), ""
    
    @app.callback(
        Output("workflows-list", "children"),
        [Input("refresh-workflows", "n_clicks"),
         Input("galaxy-data", "children")]
    )
    def update_workflows_list(n_clicks, galaxy_data):
        if not galaxy_data:
            return html.P("No Galaxy connection available")
        
        try:
            workflows_data = json.loads(galaxy_data)
            workflows = []
            
            for workflow in workflows_data:
                workflow_card = html.Div([
                    html.H4(workflow["name"], className="workflow-name"),
                    html.P(f"ID: {workflow['id']}", className="workflow-id"),
                    html.Button(
                        "Select",
                        id={"type": "select-workflow", "index": workflow["id"]},
                        className="button small"
                    )
                ], className="workflow-card")
                workflows.append(workflow_card)
            
            return workflows
            
        except Exception as e:
            logger.error(f"Error updating workflows: {e}")
            return html.P(f"Error loading workflows: {str(e)}")
    
    @app.callback(
        Output("tools-list", "children"),
        [Input("refresh-tools", "n_clicks"),
         Input("tool-search", "value")]
    )
    def update_tools_list(n_clicks, search_term):
        try:
            tools = galaxy_client.get_tools()
            
            if search_term:
                tools = [tool for tool in tools if search_term.lower() in tool.get("name", "").lower()]
            
            tools_list = []
            for tool in tools[:20]:  # Limit to first 20 tools
                tool_card = html.Div([
                    html.H4(tool.get("name", "Unknown"), className="tool-name"),
                    html.P(tool.get("description", "No description"), className="tool-description"),
                    html.P(f"Version: {tool.get('version', 'Unknown')}", className="tool-version"),
                ], className="tool-card")
                tools_list.append(tool_card)
            
            return tools_list
            
        except Exception as e:
            logger.error(f"Error updating tools: {e}")
            return html.P(f"Error loading tools: {str(e)}")
    
    @app.callback(
        Output("galaxy-upload-status", "children"),
        [Input("file-upload", "contents")],
        [State("file-upload", "filename")]
    )
    def handle_file_upload(contents, filename):
        if contents is None:
            return ""
        
        try:
            # Process uploaded files
            status_messages = []
            for content, name in zip(contents, filename):
                # Here you would typically save the file and upload to Galaxy
                status_messages.append(html.P(f"✅ Uploaded: {name}"))
            
            return html.Div(status_messages)
            
        except Exception as e:
            logger.error(f"Error handling file upload: {e}")
            return html.P(f"❌ Upload failed: {str(e)}")
    
    @app.callback(
        [Output("workflow-parameters", "children"),
         Output("workflow-data", "children")],
        [Input("workflow-selector", "value")]
    )
    def update_workflow_parameters(workflow_id):
        if not workflow_id:
            return "", ""
        
        try:
            # Get workflow details and create parameter inputs
            workflows = galaxy_client.get_workflows()
            selected_workflow = next((w for w in workflows if w.id == workflow_id), None)
            
            if not selected_workflow:
                return html.P("Workflow not found"), ""
            
            parameters = []
            for step in selected_workflow.steps:
                if step.get("type") == "data_input":
                    param_input = html.Div([
                        html.Label(f"{step.get('label', 'Input')}:", className="input-label"),
                        dcc.Input(
                            id=f"param-{step['id']}",
                            placeholder=f"Enter {step.get('label', 'value')}",
                            className="input-field"
                        )
                    ], className="parameter-group")
                    parameters.append(param_input)
            
            return parameters, json.dumps({
                "id": selected_workflow.id,
                "name": selected_workflow.name,
                "steps": selected_workflow.steps
            })
            
        except Exception as e:
            logger.error(f"Error updating workflow parameters: {e}")
            return html.P(f"Error loading workflow: {str(e)}"), ""
    
    @app.callback(
        Output("workflow-status", "children"),
        [Input("run-workflow", "n_clicks")],
        [State("workflow-data", "children")]
    )
    def run_workflow_execution(n_clicks, workflow_data):
        if n_clicks is None or not workflow_data:
            return ""
        
        try:
            workflow_info = json.loads(workflow_data)
            
            # Collect parameters from inputs
            inputs = {}
            # This would need to be implemented to collect actual parameter values
            
            # Run workflow
            job_id = galaxy_client.run_workflow(workflow_info["id"], inputs)
            
            if job_id:
                return html.Div([
                    html.P(f"✅ Workflow started successfully", className="success-message"),
                    html.P(f"Job ID: {job_id}", className="info-message"),
                    html.Button("Check Status", id="check-status", className="button secondary")
                ])
            else:
                return html.P("❌ Failed to start workflow", className="error-message")
                
        except Exception as e:
            logger.error(f"Error running workflow: {e}")
            return html.P(f"❌ Error: {str(e)}", className="error-message")
    
    @app.callback(
        Output("results-container", "children"),
        [Input("check-status", "n_clicks")]
    )
    def check_workflow_status(n_clicks):
        if n_clicks is None:
            return html.P("No workflow running")
        
        try:
            # Get job status and results
            # This would need to be implemented based on the specific job ID
            return html.Div([
                html.H4("Workflow Results"),
                html.P("Results will appear here when workflow completes"),
                html.Button("Download Results", className="button primary")
            ])
            
        except Exception as e:
            logger.error(f"Error checking status: {e}")
            return html.P(f"Error: {str(e)}")
