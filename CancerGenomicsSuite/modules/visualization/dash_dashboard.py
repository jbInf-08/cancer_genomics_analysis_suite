"""
Interactive Dash Dashboard for Cancer Genomics Analysis

This module provides a comprehensive interactive dashboard using Plotly Dash
for real-time cancer genomics data visualization and analysis.
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime, timedelta
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
import redis
import psycopg2
from sqlalchemy import create_engine
import plotly.figure_factory as ff
from scipy import stats
import seaborn as sns
import matplotlib.pyplot as plt
import io
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CancerGenomicsDashboard:
    """Main dashboard class for cancer genomics visualization"""
    
    def __init__(self, 
                 redis_host: str = "redis-master",
                 redis_port: int = 6379,
                 postgres_host: str = "postgresql",
                 postgres_port: int = 5432,
                 postgres_db: str = "genomics_db",
                 postgres_user: str = "postgres",
                 postgres_password: str = "postgres-password"):
        
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        self.postgres_engine = create_engine(
            f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
        )
        
        # Initialize Dash app
        self.app = dash.Dash(__name__, 
                           external_stylesheets=[
                               'https://codepen.io/chriddyp/pen/bWLwgP.css',
                               'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css'
                           ])
        
        self.setup_layout()
        self.setup_callbacks()
    
    def setup_layout(self):
        """Setup the dashboard layout"""
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1([
                    html.I(className="fas fa-dna", style={"margin-right": "10px"}),
                    "Cancer Genomics Analysis Dashboard"
                ], style={"color": "white", "margin": "0"}),
                html.Div([
                    html.Span("Real-time", className="badge badge-success", style={"margin-right": "10px"}),
                    html.Span(id="last-update", className="badge badge-info")
                ], style={"float": "right"})
            ], className="header", style={
                "background": "linear-gradient(90deg, #1f4e79 0%, #2d5a87 100%)",
                "padding": "20px",
                "margin-bottom": "20px",
                "border-radius": "10px",
                "box-shadow": "0 4px 6px rgba(0,0,0,0.1)"
            }),
            
            # Control Panel
            html.Div([
                html.Div([
                    html.Label("Select Time Range:", style={"font-weight": "bold"}),
                    dcc.Dropdown(
                        id="time-range-dropdown",
                        options=[
                            {"label": "Last Hour", "value": "1h"},
                            {"label": "Last 6 Hours", "value": "6h"},
                            {"label": "Last 24 Hours", "value": "24h"},
                            {"label": "Last 7 Days", "value": "7d"},
                            {"label": "Last 30 Days", "value": "30d"}
                        ],
                        value="24h",
                        style={"margin-bottom": "10px"}
                    )
                ], className="col-md-3"),
                
                html.Div([
                    html.Label("Select Gene:", style={"font-weight": "bold"}),
                    dcc.Dropdown(
                        id="gene-dropdown",
                        placeholder="Select gene...",
                        style={"margin-bottom": "10px"}
                    )
                ], className="col-md-3"),
                
                html.Div([
                    html.Label("Select Patient:", style={"font-weight": "bold"}),
                    dcc.Dropdown(
                        id="patient-dropdown",
                        placeholder="Select patient...",
                        style={"margin-bottom": "10px"}
                    )
                ], className="col-md-3"),
                
                html.Div([
                    html.Label("Analysis Type:", style={"font-weight": "bold"}),
                    dcc.Dropdown(
                        id="analysis-type-dropdown",
                        options=[
                            {"label": "Mutation Analysis", "value": "mutations"},
                            {"label": "Gene Expression", "value": "expression"},
                            {"label": "Pathway Analysis", "value": "pathways"},
                            {"label": "Clinical Data", "value": "clinical"}
                        ],
                        value="mutations",
                        style={"margin-bottom": "10px"}
                    )
                ], className="col-md-3")
            ], className="row", style={"margin-bottom": "20px"}),
            
            # Key Metrics Cards
            html.Div([
                html.Div([
                    html.Div([
                        html.Div([
                            html.I(className="fas fa-virus", style={"font-size": "2em", "color": "#e74c3c"}),
                            html.H3(id="total-mutations", children="0", style={"margin": "0", "color": "#e74c3c"}),
                            html.P("Total Mutations", style={"margin": "0", "color": "#7f8c8d"})
                        ], className="metric-card")
                    ], className="col-md-3"),
                    
                    html.Div([
                        html.Div([
                            html.I(className="fas fa-exclamation-triangle", style={"font-size": "2em", "color": "#f39c12"}),
                            html.H3(id="critical-mutations", children="0", style={"margin": "0", "color": "#f39c12"}),
                            html.P("Critical Mutations", style={"margin": "0", "color": "#7f8c8d"})
                        ], className="metric-card")
                    ], className="col-md-3"),
                    
                    html.Div([
                        html.Div([
                            html.I(className="fas fa-users", style={"font-size": "2em", "color": "#3498db"}),
                            html.H3(id="total-patients", children="0", style={"margin": "0", "color": "#3498db"}),
                            html.P("Total Patients", style={"margin": "0", "color": "#7f8c8d"})
                        ], className="metric-card")
                    ], className="col-md-3"),
                    
                    html.Div([
                        html.Div([
                            html.I(className="fas fa-chart-line", style={"font-size": "2em", "color": "#27ae60"}),
                            html.H3(id="analysis-rate", children="0/min", style={"margin": "0", "color": "#27ae60"}),
                            html.P("Analysis Rate", style={"margin": "0", "color": "#7f8c8d"})
                        ], className="metric-card")
                    ], className="col-md-3")
                ], className="row")
            ], style={"margin-bottom": "30px"}),
            
            # Main Content Area
            html.Div([
                # Left Column - Charts
                html.Div([
                    # Mutation Timeline
                    html.Div([
                        html.H4("Mutation Timeline", style={"margin-bottom": "15px"}),
                        dcc.Graph(id="mutation-timeline-chart")
                    ], className="chart-container", style={"margin-bottom": "20px"}),
                    
                    # Gene Expression Heatmap
                    html.Div([
                        html.H4("Gene Expression Heatmap", style={"margin-bottom": "15px"}),
                        dcc.Graph(id="expression-heatmap")
                    ], className="chart-container", style={"margin-bottom": "20px"}),
                    
                    # Pathway Analysis
                    html.Div([
                        html.H4("Pathway Analysis", style={"margin-bottom": "15px"}),
                        dcc.Graph(id="pathway-analysis-chart")
                    ], className="chart-container")
                ], className="col-md-8"),
                
                # Right Column - Tables and Details
                html.Div([
                    # Recent Mutations Table
                    html.Div([
                        html.H4("Recent Mutations", style={"margin-bottom": "15px"}),
                        html.Div(id="recent-mutations-table")
                    ], className="table-container", style={"margin-bottom": "20px"}),
                    
                    # Gene Network
                    html.Div([
                        html.H4("Gene Network", style={"margin-bottom": "15px"}),
                        dcc.Graph(id="gene-network-graph")
                    ], className="chart-container", style={"margin-bottom": "20px"}),
                    
                    # Clinical Summary
                    html.Div([
                        html.H4("Clinical Summary", style={"margin-bottom": "15px"}),
                        html.Div(id="clinical-summary")
                    ], className="info-container")
                ], className="col-md-4")
            ], className="row"),
            
            # Footer
            html.Div([
                html.P("Cancer Genomics Analysis Suite v1.0.0", style={"text-align": "center", "color": "#7f8c8d"})
            ], style={"margin-top": "50px", "padding": "20px"})
        ])
    
    def setup_callbacks(self):
        """Setup dashboard callbacks"""
        
        @self.app.callback(
            [Output("last-update", "children"),
             Output("total-mutations", "children"),
             Output("critical-mutations", "children"),
             Output("total-patients", "children"),
             Output("analysis-rate", "children")],
            [Input("time-range-dropdown", "value")],
            prevent_initial_call=False
        )
        def update_metrics(time_range):
            """Update key metrics"""
            try:
                # Get current time
                current_time = datetime.now().strftime("%H:%M:%S")
                
                # Get metrics from Redis
                total_mutations = self.redis_client.get("metrics:total_mutations") or "0"
                critical_mutations = self.redis_client.get("metrics:critical_mutations") or "0"
                total_patients = self.redis_client.get("metrics:total_patients") or "0"
                analysis_rate = self.redis_client.get("metrics:analysis_rate") or "0"
                
                return (
                    f"Updated: {current_time}",
                    f"{total_mutations:,}",
                    f"{critical_mutations:,}",
                    f"{total_patients:,}",
                    f"{analysis_rate}/min"
                )
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
                return "Error", "0", "0", "0", "0/min"
        
        @self.app.callback(
            Output("mutation-timeline-chart", "figure"),
            [Input("time-range-dropdown", "value"),
             Input("gene-dropdown", "value"),
             Input("patient-dropdown", "value")]
        )
        def update_mutation_timeline(time_range, selected_gene, selected_patient):
            """Update mutation timeline chart"""
            try:
                # Query mutation data
                query = """
                SELECT timestamp, gene, mutation_type, severity, patient_id
                FROM mutations 
                WHERE timestamp >= NOW() - INTERVAL %s
                """
                
                if selected_gene:
                    query += " AND gene = %s"
                if selected_patient:
                    query += " AND patient_id = %s"
                
                query += " ORDER BY timestamp DESC LIMIT 1000"
                
                params = [time_range]
                if selected_gene:
                    params.append(selected_gene)
                if selected_patient:
                    params.append(selected_patient)
                
                df = pd.read_sql(query, self.postgres_engine, params=params)
                
                if df.empty:
                    return go.Figure().add_annotation(
                        text="No data available for the selected criteria",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False
                    )
                
                # Create timeline chart
                fig = px.scatter(
                    df, x="timestamp", y="gene",
                    color="severity",
                    size="severity",
                    hover_data=["mutation_type", "patient_id"],
                    title="Mutation Timeline",
                    color_discrete_map={
                        "critical": "#e74c3c",
                        "high": "#f39c12",
                        "medium": "#f1c40f",
                        "low": "#27ae60"
                    }
                )
                
                fig.update_layout(
                    xaxis_title="Time",
                    yaxis_title="Gene",
                    height=400,
                    showlegend=True
                )
                
                return fig
                
            except Exception as e:
                logger.error(f"Error updating mutation timeline: {e}")
                return go.Figure().add_annotation(
                    text="Error loading data",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
        
        @self.app.callback(
            Output("expression-heatmap", "figure"),
            [Input("time-range-dropdown", "value"),
             Input("gene-dropdown", "value")]
        )
        def update_expression_heatmap(time_range, selected_gene):
            """Update gene expression heatmap"""
            try:
                # Query expression data
                query = """
                SELECT gene, sample_id, expression_value, tissue_type
                FROM gene_expression 
                WHERE timestamp >= NOW() - INTERVAL %s
                """
                
                if selected_gene:
                    query += " AND gene = %s"
                
                query += " ORDER BY gene, sample_id"
                
                params = [time_range]
                if selected_gene:
                    params.append(selected_gene)
                
                df = pd.read_sql(query, self.postgres_engine, params=params)
                
                if df.empty:
                    return go.Figure().add_annotation(
                        text="No expression data available",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False
                    )
                
                # Create pivot table for heatmap
                pivot_df = df.pivot_table(
                    values="expression_value",
                    index="gene",
                    columns="sample_id",
                    aggfunc="mean"
                )
                
                # Create heatmap
                fig = px.imshow(
                    pivot_df.values,
                    x=pivot_df.columns,
                    y=pivot_df.index,
                    color_continuous_scale="RdYlBu_r",
                    title="Gene Expression Heatmap"
                )
                
                fig.update_layout(
                    height=400,
                    xaxis_title="Sample ID",
                    yaxis_title="Gene"
                )
                
                return fig
                
            except Exception as e:
                logger.error(f"Error updating expression heatmap: {e}")
                return go.Figure().add_annotation(
                    text="Error loading expression data",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
        
        @self.app.callback(
            Output("pathway-analysis-chart", "figure"),
            [Input("time-range-dropdown", "value"),
             Input("gene-dropdown", "value")]
        )
        def update_pathway_analysis(time_range, selected_gene):
            """Update pathway analysis chart"""
            try:
                # Query pathway data
                query = """
                SELECT pathway_name, gene_count, enrichment_score, pathway_type
                FROM pathway_analysis 
                WHERE timestamp >= NOW() - INTERVAL %s
                """
                
                if selected_gene:
                    query += " AND pathway_name IN (SELECT pathway_name FROM gene_pathways WHERE gene = %s)"
                
                query += " ORDER BY enrichment_score DESC LIMIT 20"
                
                params = [time_range]
                if selected_gene:
                    params.append(selected_gene)
                
                df = pd.read_sql(query, self.postgres_engine, params=params)
                
                if df.empty:
                    return go.Figure().add_annotation(
                        text="No pathway data available",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False
                    )
                
                # Create bar chart
                fig = px.bar(
                    df, x="enrichment_score", y="pathway_name",
                    color="pathway_type",
                    title="Top Enriched Pathways",
                    orientation="h"
                )
                
                fig.update_layout(
                    height=400,
                    xaxis_title="Enrichment Score",
                    yaxis_title="Pathway"
                )
                
                return fig
                
            except Exception as e:
                logger.error(f"Error updating pathway analysis: {e}")
                return go.Figure().add_annotation(
                    text="Error loading pathway data",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
        
        @self.app.callback(
            Output("recent-mutations-table", "children"),
            [Input("time-range-dropdown", "value")]
        )
        def update_recent_mutations_table(time_range):
            """Update recent mutations table"""
            try:
                # Query recent mutations
                query = """
                SELECT timestamp, gene, mutation_type, severity, patient_id, pathogenicity_score
                FROM mutations 
                WHERE timestamp >= NOW() - INTERVAL %s
                ORDER BY timestamp DESC 
                LIMIT 10
                """
                
                df = pd.read_sql(query, self.postgres_engine, params=[time_range])
                
                if df.empty:
                    return html.P("No recent mutations found")
                
                # Create table
                table = dash_table.DataTable(
                    data=df.to_dict('records'),
                    columns=[
                        {"name": "Time", "id": "timestamp", "type": "datetime"},
                        {"name": "Gene", "id": "gene"},
                        {"name": "Type", "id": "mutation_type"},
                        {"name": "Severity", "id": "severity"},
                        {"name": "Patient", "id": "patient_id"},
                        {"name": "Score", "id": "pathogenicity_score", "type": "numeric", "format": {"specifier": ".2f"}}
                    ],
                    style_cell={
                        "textAlign": "left",
                        "padding": "10px",
                        "fontSize": "12px"
                    },
                    style_header={
                        "backgroundColor": "#f8f9fa",
                        "fontWeight": "bold"
                    },
                    style_data_conditional=[
                        {
                            "if": {"filter_query": "{severity} = critical"},
                            "backgroundColor": "#f8d7da",
                            "color": "#721c24"
                        },
                        {
                            "if": {"filter_query": "{severity} = high"},
                            "backgroundColor": "#fff3cd",
                            "color": "#856404"
                        }
                    ]
                )
                
                return table
                
            except Exception as e:
                logger.error(f"Error updating mutations table: {e}")
                return html.P("Error loading mutations data")
        
        @self.app.callback(
            Output("gene-network-graph", "figure"),
            [Input("gene-dropdown", "value")]
        )
        def update_gene_network(selected_gene):
            """Update gene network graph"""
            try:
                if not selected_gene:
                    return go.Figure().add_annotation(
                        text="Select a gene to view network",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False
                    )
                
                # Query gene network data
                query = """
                SELECT gene1, gene2, interaction_type, confidence_score
                FROM gene_interactions 
                WHERE gene1 = %s OR gene2 = %s
                """
                
                df = pd.read_sql(query, self.postgres_engine, params=[selected_gene, selected_gene])
                
                if df.empty:
                    return go.Figure().add_annotation(
                        text="No network data available for this gene",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False
                    )
                
                # Create network graph
                import networkx as nx
                
                G = nx.Graph()
                for _, row in df.iterrows():
                    G.add_edge(row['gene1'], row['gene2'], 
                             interaction_type=row['interaction_type'],
                             confidence=row['confidence_score'])
                
                pos = nx.spring_layout(G, k=1, iterations=50)
                
                edge_x = []
                edge_y = []
                for edge in G.edges():
                    x0, y0 = pos[edge[0]]
                    x1, y1 = pos[edge[1]]
                    edge_x.extend([x0, x1, None])
                    edge_y.extend([y0, y1, None])
                
                edge_trace = go.Scatter(
                    x=edge_x, y=edge_y,
                    line=dict(width=0.5, color='#888'),
                    hoverinfo='none',
                    mode='lines'
                )
                
                node_x = []
                node_y = []
                node_text = []
                for node in G.nodes():
                    x, y = pos[node]
                    node_x.append(x)
                    node_y.append(y)
                    node_text.append(node)
                
                node_trace = go.Scatter(
                    x=node_x, y=node_y,
                    mode='markers+text',
                    hoverinfo='text',
                    text=node_text,
                    textposition="middle center",
                    marker=dict(
                        size=20,
                        color='lightblue',
                        line=dict(width=2, color='black')
                    )
                )
                
                fig = go.Figure(data=[edge_trace, node_trace],
                              layout=go.Layout(
                                  title=f'Gene Network: {selected_gene}',
                                  titlefont_size=16,
                                  showlegend=False,
                                  hovermode='closest',
                                  margin=dict(b=20,l=5,r=5,t=40),
                                  annotations=[ dict(
                                      text="Gene interaction network",
                                      showarrow=False,
                                      xref="paper", yref="paper",
                                      x=0.005, y=-0.002,
                                      xanchor='left', yanchor='bottom',
                                      font=dict(color="black", size=12)
                                  )],
                                  xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                  yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                  height=300
                              ))
                
                return fig
                
            except Exception as e:
                logger.error(f"Error updating gene network: {e}")
                return go.Figure().add_annotation(
                    text="Error loading network data",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
        
        @self.app.callback(
            Output("clinical-summary", "children"),
            [Input("patient-dropdown", "value")]
        )
        def update_clinical_summary(selected_patient):
            """Update clinical summary"""
            try:
                if not selected_patient:
                    return html.P("Select a patient to view clinical summary")
                
                # Query clinical data
                query = """
                SELECT age, gender, diagnosis, stage, treatment_status, survival_months
                FROM clinical_data 
                WHERE patient_id = %s
                """
                
                df = pd.read_sql(query, self.postgres_engine, params=[selected_patient])
                
                if df.empty:
                    return html.P("No clinical data available for this patient")
                
                patient_data = df.iloc[0]
                
                summary = html.Div([
                    html.H5(f"Patient: {selected_patient}"),
                    html.P(f"Age: {patient_data['age']} years"),
                    html.P(f"Gender: {patient_data['gender']}"),
                    html.P(f"Diagnosis: {patient_data['diagnosis']}"),
                    html.P(f"Stage: {patient_data['stage']}"),
                    html.P(f"Treatment Status: {patient_data['treatment_status']}"),
                    html.P(f"Survival: {patient_data['survival_months']} months")
                ])
                
                return summary
                
            except Exception as e:
                logger.error(f"Error updating clinical summary: {e}")
                return html.P("Error loading clinical data")
        
        @self.app.callback(
            [Output("gene-dropdown", "options"),
             Output("patient-dropdown", "options")],
            [Input("time-range-dropdown", "value")]
        )
        def update_dropdown_options(time_range):
            """Update dropdown options based on time range"""
            try:
                # Get unique genes
                gene_query = """
                SELECT DISTINCT gene 
                FROM mutations 
                WHERE timestamp >= NOW() - INTERVAL %s
                ORDER BY gene
                """
                genes_df = pd.read_sql(gene_query, self.postgres_engine, params=[time_range])
                gene_options = [{"label": gene, "value": gene} for gene in genes_df['gene'].tolist()]
                
                # Get unique patients
                patient_query = """
                SELECT DISTINCT patient_id 
                FROM mutations 
                WHERE timestamp >= NOW() - INTERVAL %s
                ORDER BY patient_id
                """
                patients_df = pd.read_sql(patient_query, self.postgres_engine, params=[time_range])
                patient_options = [{"label": patient, "value": patient} for patient in patients_df['patient_id'].tolist()]
                
                return gene_options, patient_options
                
            except Exception as e:
                logger.error(f"Error updating dropdown options: {e}")
                return [], []
    
    def run(self, host="0.0.0.0", port=8050, debug=False):
        """Run the dashboard"""
        logger.info(f"Starting Cancer Genomics Dashboard on {host}:{port}")
        self.app.run_server(host=host, port=port, debug=debug)

# Streamlit Dashboard
class StreamlitDashboard:
    """Streamlit-based dashboard for cancer genomics analysis"""
    
    def __init__(self):
        import streamlit as st
        self.st = st
    
    def create_dashboard(self):
        """Create Streamlit dashboard"""
        self.st.set_page_config(
            page_title="Cancer Genomics Analysis",
            page_icon="🧬",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Sidebar
        self.st.sidebar.title("🧬 Cancer Genomics Analysis")
        
        # Main content
        self.st.title("Cancer Genomics Analysis Dashboard")
        
        # Create tabs
        tab1, tab2, tab3, tab4 = self.st.tabs(["Overview", "Mutations", "Expression", "Pathways"])
        
        with tab1:
            self.create_overview_tab()
        
        with tab2:
            self.create_mutations_tab()
        
        with tab3:
            self.create_expression_tab()
        
        with tab4:
            self.create_pathways_tab()
    
    def create_overview_tab(self):
        """Create overview tab"""
        col1, col2, col3, col4 = self.st.columns(4)
        
        with col1:
            self.st.metric("Total Mutations", "1,234", "12")
        
        with col2:
            self.st.metric("Critical Mutations", "45", "3")
        
        with col3:
            self.st.metric("Total Patients", "89", "5")
        
        with col4:
            self.st.metric("Analysis Rate", "2.3/min", "0.1")
        
        # Charts
        col1, col2 = self.st.columns(2)
        
        with col1:
            self.st.subheader("Mutation Distribution")
            # Add chart here
        
        with col2:
            self.st.subheader("Gene Expression")
            # Add chart here
    
    def create_mutations_tab(self):
        """Create mutations tab"""
        self.st.subheader("Mutation Analysis")
        # Add mutation analysis content
    
    def create_expression_tab(self):
        """Create expression tab"""
        self.st.subheader("Gene Expression Analysis")
        # Add expression analysis content
    
    def create_pathways_tab(self):
        """Create pathways tab"""
        self.st.subheader("Pathway Analysis")
        # Add pathway analysis content

# Main execution
if __name__ == "__main__":
    # Create and run Dash dashboard
    dashboard = CancerGenomicsDashboard()
    dashboard.run(debug=True)
