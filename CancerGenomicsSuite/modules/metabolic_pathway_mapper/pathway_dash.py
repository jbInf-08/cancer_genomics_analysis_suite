"""
Pathway Dashboard Module

This module provides a comprehensive Dash-based dashboard for metabolic pathway
analysis and visualization.
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import json
from typing import Dict, List, Any, Optional
import logging

from .mapper import MetabolicPathwayMapper, create_mock_pathway_data
from .kegg_overlay import KEGGPathwayOverlay

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PathwayDashboard:
    """
    A comprehensive dashboard for metabolic pathway analysis.
    """
    
    def __init__(self, app: dash.Dash):
        """
        Initialize the pathway dashboard.
        
        Args:
            app: Dash application instance
        """
        self.app = app
        self.mapper = MetabolicPathwayMapper()
        self.kegg_overlay = KEGGPathwayOverlay()
        self.current_data = None
        self.setup_callbacks()
    
    def create_layout(self) -> html.Div:
        """
        Create the main dashboard layout.
        
        Returns:
            HTML div containing the dashboard layout
        """
        return html.Div([
            # Header
            html.Div([
                html.H1("Metabolic Pathway Analysis Dashboard", 
                       className="text-center mb-4"),
                html.P("Comprehensive analysis and visualization of metabolic pathways in cancer genomics",
                      className="text-center text-muted mb-4")
            ], className="container-fluid"),
            
            # Control Panel
            html.Div([
                html.Div([
                    html.H4("Data Upload & Configuration", className="card-title"),
                    
                    # File upload section
                    html.Div([
                        dcc.Upload(
                            id='upload-expression-data',
                            children=html.Div([
                                'Drag and Drop or ',
                                html.A('Select Gene Expression Data')
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
                        dcc.Upload(
                            id='upload-mutation-data',
                            children=html.Div([
                                'Drag and Drop or ',
                                html.A('Select Mutation Data')
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
                        )
                    ], className="mb-3"),
                    
                    # Configuration options
                    html.Div([
                        html.Label("Dysregulation Threshold (Z-score):"),
                        dcc.Slider(
                            id='dysregulation-threshold',
                            min=0.5,
                            max=5.0,
                            step=0.1,
                            value=2.0,
                            marks={i: str(i) for i in range(1, 6)},
                            tooltip={"placement": "bottom", "always_visible": True}
                        )
                    ], className="mb-3"),
                    
                    # Action buttons
                    html.Div([
                        html.Button('Load Mock Data', id='load-mock-data', 
                                  className='btn btn-primary me-2'),
                        html.Button('Analyze Pathways', id='analyze-pathways', 
                                  className='btn btn-success me-2'),
                        html.Button('Export Results', id='export-results', 
                                  className='btn btn-info')
                    ], className="d-flex flex-wrap gap-2")
                    
                ], className="card-body")
            ], className="card mb-4"),
            
            # Main content area
            html.Div([
                # Tabs for different views
                dcc.Tabs(id="main-tabs", value="overview", children=[
                    dcc.Tab(label="Overview", value="overview"),
                    dcc.Tab(label="Pathway Analysis", value="pathway-analysis"),
                    dcc.Tab(label="Network Visualization", value="network-viz"),
                    dcc.Tab(label="Expression Heatmaps", value="heatmaps"),
                    dcc.Tab(label="KEGG Integration", value="kegg")
                ]),
                
                # Tab content
                html.Div(id="pathway-tab-content", className="mt-3")
                
            ], className="container-fluid"),
            
            # Hidden divs for storing data
            html.Div(id='pathway-data', style={'display': 'none'}),
            html.Div(id='pathway-analysis-results', style={'display': 'none'}),
            
            # Download components
            dcc.Download(id="pathway-download-results"),
            dcc.Download(id="download-network")
        ])
    
    def create_overview_tab(self) -> html.Div:
        """Create the overview tab content."""
        return html.Div([
            html.Div([
                html.H4("Pathway Network Summary"),
                html.Div(id="network-summary", className="row")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Top Dysregulated Pathways"),
                dcc.Graph(id="dysregulated-pathways-chart")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Pathway Activity Distribution"),
                dcc.Graph(id="pathway-activity-distribution")
            ], className="card")
        ])
    
    def create_pathway_analysis_tab(self) -> html.Div:
        """Create the pathway analysis tab content."""
        return html.Div([
            html.Div([
                html.H4("Select Pathway for Analysis"),
                dcc.Dropdown(
                    id="pathway-selector",
                    placeholder="Select a pathway...",
                    className="mb-3"
                ),
                html.Div(id="pathway-analysis-details")
            ], className="card")
        ])
    
    def create_network_visualization_tab(self) -> html.Div:
        """Create the network visualization tab content."""
        return html.Div([
            html.Div([
                html.H4("Interactive Pathway Network"),
                dcc.Graph(id="pathway-network-graph", style={'height': '600px'}),
                html.Div([
                    html.Label("Layout Algorithm:"),
                    dcc.Dropdown(
                        id="layout-algorithm",
                        options=[
                            {'label': 'Spring Layout', 'value': 'spring'},
                            {'label': 'Circular Layout', 'value': 'circular'},
                            {'label': 'Hierarchical Layout', 'value': 'hierarchical'}
                        ],
                        value='spring',
                        className="mb-2"
                    )
                ], className="mt-3")
            ], className="card")
        ])
    
    def create_heatmaps_tab(self) -> html.Div:
        """Create the expression heatmaps tab content."""
        return html.Div([
            html.Div([
                html.H4("Gene Expression Heatmaps"),
                dcc.Dropdown(
                    id="heatmap-pathway-selector",
                    placeholder="Select pathway for heatmap...",
                    className="mb-3"
                ),
                dcc.Graph(id="expression-heatmap", style={'height': '600px'})
            ], className="card")
        ])
    
    def create_kegg_tab(self) -> html.Div:
        """Create the KEGG integration tab content."""
        return html.Div([
            html.Div([
                html.H4("KEGG Pathway Integration"),
                html.Div([
                    html.Label("KEGG Pathway ID:"),
                    dcc.Input(
                        id="kegg-pathway-id",
                        type="text",
                        placeholder="e.g., hsa00010",
                        className="form-control mb-2"
                    ),
                    html.Button("Load KEGG Pathway", id="load-kegg-pathway", 
                              className="btn btn-primary mb-3")
                ]),
                html.Div(id="kegg-pathway-content")
            ], className="card")
        ])
    
    def setup_callbacks(self):
        """Set up all dashboard callbacks."""
        
        @self.app.callback(
            [Output('pathway-data', 'children'),
             Output('network-summary', 'children')],
            [Input('load-mock-data', 'n_clicks')]
        )
        def load_mock_data(n_clicks):
            """Load mock data and create pathway network."""
            if n_clicks:
                try:
                    # Create mock pathway data
                    pathway_data = create_mock_pathway_data()
                    
                    # Create pathway network
                    network = self.mapper.create_pathway_network(pathway_data)
                    
                    # Get summary
                    summary = self.mapper.get_pathway_summary()
                    
                    # Store data
                    data_json = json.dumps({
                        'pathway_data': pathway_data,
                        'summary': summary
                    })
                    
                    # Create summary cards
                    summary_cards = self.create_summary_cards(summary)
                    
                    return data_json, summary_cards
                    
                except Exception as e:
                    logger.error(f"Error loading mock data: {e}")
                    return "", html.Div(f"Error: {str(e)}", className="alert alert-danger")
            
            return "", html.Div("Click 'Load Mock Data' to begin analysis", 
                              className="text-muted")
        
        @self.app.callback(
            [Output('pathway-analysis-results', 'children'),
             Output('dysregulated-pathways-chart', 'figure'),
             Output('pathway-activity-distribution', 'figure')],
            [Input('analyze-pathways', 'n_clicks'),
             Input('dysregulation-threshold', 'value')],
            [State('pathway-data', 'children')]
        )
        def analyze_pathways(n_clicks, threshold, pathway_data_json):
            """Analyze pathways and create visualizations."""
            if n_clicks and pathway_data_json:
                try:
                    data = json.loads(pathway_data_json)
                    pathway_data = data['pathway_data']
                    
                    # Recreate network
                    network = self.mapper.create_pathway_network(pathway_data)
                    
                    # Simulate expression data for analysis
                    self.create_mock_expression_data(pathway_data)
                    
                    # Identify dysregulated pathways
                    dysregulated = self.mapper.identify_dysregulated_pathways(threshold)
                    
                    # Create visualizations
                    dysregulated_chart = self.create_dysregulated_pathways_chart(dysregulated)
                    activity_dist = self.create_activity_distribution_chart(dysregulated)
                    
                    # Store results
                    results_json = json.dumps(dysregulated, default=str)
                    
                    return results_json, dysregulated_chart, activity_dist
                    
                except Exception as e:
                    logger.error(f"Error analyzing pathways: {e}")
                    empty_fig = go.Figure()
                    return "", empty_fig, empty_fig
            
            return "", go.Figure(), go.Figure()
        
        @self.app.callback(
            Output('pathway-tab-content', 'children'),
            [Input('main-tabs', 'value')]
        )
        def render_tab_content(active_tab):
            """Render content based on active tab."""
            if active_tab == 'overview':
                return self.create_overview_tab()
            elif active_tab == 'pathway-analysis':
                return self.create_pathway_analysis_tab()
            elif active_tab == 'network-viz':
                return self.create_network_visualization_tab()
            elif active_tab == 'heatmaps':
                return self.create_heatmaps_tab()
            elif active_tab == 'kegg':
                return self.create_kegg_tab()
            else:
                return html.Div("Select a tab to view content")
        
        @self.app.callback(
            Output('pathway-network-graph', 'figure'),
            [Input('pathway-data', 'children'),
             Input('layout-algorithm', 'value')]
        )
        def update_network_graph(pathway_data_json, layout):
            """Update the network visualization."""
            if pathway_data_json:
                try:
                    data = json.loads(pathway_data_json)
                    pathway_data = data['pathway_data']
                    
                    # Recreate network
                    network = self.mapper.create_pathway_network(pathway_data)
                    
                    # Create visualization
                    fig = self.create_network_visualization(network, layout)
                    return fig
                    
                except Exception as e:
                    logger.error(f"Error creating network graph: {e}")
                    return go.Figure()
            
            return go.Figure()
    
    def create_summary_cards(self, summary: Dict[str, Any]) -> html.Div:
        """Create summary cards for the overview."""
        cards = []
        
        metrics = [
            ('Total Pathways', summary['total_pathways'], 'primary'),
            ('Total Genes', summary['total_genes'], 'success'),
            ('Network Density', f"{summary['network_density']:.3f}", 'info'),
            ('Total Connections', summary['total_edges'], 'warning')
        ]
        
        for title, value, color in metrics:
            card = html.Div([
                html.Div([
                    html.H5(str(value), className="card-title"),
                    html.P(title, className="card-text")
                ], className="card-body text-center")
            ], className=f"card border-{color} mb-2")
            cards.append(html.Div(card, className="col-md-3"))
        
        return html.Div(cards, className="row")
    
    def create_dysregulated_pathways_chart(self, dysregulated: List[Dict[str, Any]]) -> go.Figure:
        """Create a chart showing dysregulated pathways."""
        if not dysregulated:
            return go.Figure()
        
        pathway_names = [p['pathway_name'] for p in dysregulated]
        scores = [p['dysregulation_score'] for p in dysregulated]
        
        fig = go.Figure(data=[
            go.Bar(
                x=pathway_names,
                y=scores,
                marker_color=['red' if score > 0 else 'blue' for score in scores],
                text=[f"{score:.2f}" for score in scores],
                textposition='auto'
            )
        ])
        
        fig.update_layout(
            title="Dysregulated Pathways",
            xaxis_title="Pathway",
            yaxis_title="Dysregulation Score",
            height=400
        )
        
        return fig
    
    def create_activity_distribution_chart(self, dysregulated: List[Dict[str, Any]]) -> go.Figure:
        """Create a distribution chart of pathway activities."""
        if not dysregulated:
            return go.Figure()
        
        scores = [p['dysregulation_score'] for p in dysregulated]
        
        fig = go.Figure(data=[
            go.Histogram(
                x=scores,
                nbinsx=20,
                marker_color='lightblue',
                opacity=0.7
            )
        ])
        
        fig.update_layout(
            title="Pathway Activity Distribution",
            xaxis_title="Dysregulation Score",
            yaxis_title="Frequency",
            height=400
        )
        
        return fig
    
    def create_network_visualization(self, network, layout: str = 'spring') -> go.Figure:
        """Create a network visualization."""
        import networkx as nx
        
        # Create layout
        if layout == 'spring':
            pos = nx.spring_layout(network, k=3, iterations=50)
        elif layout == 'circular':
            pos = nx.circular_layout(network)
        else:
            pos = nx.spring_layout(network, k=3, iterations=50)
        
        # Prepare edge traces
        edge_x = []
        edge_y = []
        for edge in network.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=2, color='#888'),
            hoverinfo='none',
            mode='lines'
        )
        
        # Prepare node traces
        node_x = []
        node_y = []
        node_text = []
        node_colors = []
        
        for node in network.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(node)
            
            if network.nodes[node]['type'] == 'pathway':
                node_colors.append('red')
            else:
                node_colors.append('lightblue')
        
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            text=node_text,
            textposition="middle center",
            marker=dict(
                size=20,
                color=node_colors,
                line=dict(width=2, color='black')
            )
        )
        
        fig = go.Figure(data=[edge_trace, node_trace],
                       layout=go.Layout(
                           title='Pathway Network Visualization',
                           titlefont_size=16,
                           showlegend=False,
                           hovermode='closest',
                           margin=dict(b=20,l=5,r=5,t=40),
                           xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                           yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                       ))
        
        return fig
    
    def create_mock_expression_data(self, pathway_data: Dict[str, List[str]]):
        """Create mock expression data for analysis."""
        all_genes = []
        for genes in pathway_data.values():
            all_genes.extend(genes)
        
        # Create mock expression data
        np.random.seed(42)
        n_samples = 50
        
        expression_data = {
            'gene_id': all_genes,
        }
        
        for i in range(n_samples):
            expression_data[f'sample_{i}'] = np.random.normal(0, 1, len(all_genes))
        
        self.mapper.gene_expression_data = pd.DataFrame(expression_data)


def create_pathway_dashboard(app: dash.Dash) -> PathwayDashboard:
    """
    Create and configure a pathway analysis dashboard.
    
    Args:
        app: Dash application instance
        
    Returns:
        Configured PathwayDashboard instance
    """
    dashboard = PathwayDashboard(app)
    return dashboard


def main():
    """Main function for testing the dashboard."""
    app = dash.Dash(__name__)
    dashboard = create_pathway_dashboard(app)
    app.layout = dashboard.create_layout()
    
    if __name__ == "__main__":
        app.run_server(debug=True)


if __name__ == "__main__":
    main()
