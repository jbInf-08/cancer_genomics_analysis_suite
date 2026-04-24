"""
Drug Discovery Dashboard for Cancer Genomics Analysis

This module provides an interactive dashboard for drug discovery and analysis
using Dash/Plotly for visualization and user interaction.
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import logging

from .drug_analyzer import DrugAnalyzer, DrugResult, DrugDiscoveryConfig

logger = logging.getLogger(__name__)


class DrugDiscoveryDashboard:
    """Interactive dashboard for drug discovery."""
    
    def __init__(self, app: Optional[dash.Dash] = None):
        """Initialize the drug discovery dashboard."""
        self.app = app or dash.Dash(__name__)
        self.analyzer = DrugAnalyzer()
        self.results = []
        self.current_data = None
        
        self._setup_layout()
        self._setup_callbacks()
    
    def _setup_layout(self):
        """Setup the dashboard layout."""
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1("Drug Discovery Dashboard", 
                       style={'textAlign': 'center', 'color': '#2c3e50'}),
                html.P("Discover and analyze drugs for cancer treatment",
                      style={'textAlign': 'center', 'color': '#7f8c8d'})
            ], style={'marginBottom': '30px'}),
            
            # Control Panel
            html.Div([
                html.Div([
                    html.H3("Analysis Configuration", style={'color': '#2c3e50'}),
                    
                    # File Upload
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div([
                            'Drag and Drop or ',
                            html.A('Select Files')
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
                    
                    # Analysis Parameters
                    html.Div([
                        html.Label("Min Efficacy Score:"),
                        dcc.Slider(
                            id='efficacy-threshold',
                            min=0.0,
                            max=1.0,
                            step=0.05,
                            value=0.6,
                            marks={i/10: str(i/10) for i in range(0, 11, 2)},
                            tooltip={"placement": "bottom", "always_visible": True}
                        )
                    ], style={'margin': '10px 0'}),
                    
                    html.Div([
                        html.Label("Min Safety Score:"),
                        dcc.Slider(
                            id='safety-threshold',
                            min=0.0,
                            max=1.0,
                            step=0.05,
                            value=0.7,
                            marks={i/10: str(i/10) for i in range(0, 11, 2)},
                            tooltip={"placement": "bottom", "always_visible": True}
                        )
                    ], style={'margin': '10px 0'}),
                    
                    html.Div([
                        html.Label("Repurposing Threshold:"),
                        dcc.Slider(
                            id='repurposing-threshold',
                            min=0.0,
                            max=1.0,
                            step=0.05,
                            value=0.8,
                            marks={i/10: str(i/10) for i in range(0, 11, 2)},
                            tooltip={"placement": "bottom", "always_visible": True}
                        )
                    ], style={'margin': '10px 0'}),
                    
                    # Analysis Type
                    html.Div([
                        html.Label("Analysis Type:"),
                        dcc.Dropdown(
                            id='analysis-type',
                            options=[
                                {'label': 'Comprehensive', 'value': 'comprehensive'},
                                {'label': 'Repurposing', 'value': 'repurposing'},
                                {'label': 'Target Identification', 'value': 'target_identification'}
                            ],
                            value='comprehensive'
                        )
                    ], style={'margin': '10px 0'}),
                    
                    # Run Analysis Button
                    html.Button(
                        'Run Drug Discovery',
                        id='run-analysis',
                        n_clicks=0,
                        style={
                            'backgroundColor': '#3498db',
                            'color': 'white',
                            'border': 'none',
                            'padding': '10px 20px',
                            'borderRadius': '5px',
                            'cursor': 'pointer',
                            'width': '100%',
                            'marginTop': '20px'
                        }
                    )
                    
                ], style={'width': '30%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '20px'}),
                
                # Results Panel
                html.Div([
                    html.H3("Drug Discovery Results", style={'color': '#2c3e50'}),
                    
                    # Summary Statistics
                    html.Div(id='summary-stats', style={'marginBottom': '20px'}),
                    
                    # Results Table
                    html.Div(id='results-table'),
                    
                    # Export Buttons
                    html.Div([
                        html.Button(
                            'Export to CSV',
                            id='export-csv',
                            n_clicks=0,
                            style={
                                'backgroundColor': '#27ae60',
                                'color': 'white',
                                'border': 'none',
                                'padding': '10px 15px',
                                'borderRadius': '5px',
                                'cursor': 'pointer',
                                'marginRight': '10px'
                            }
                        ),
                        html.Button(
                            'Export to Excel',
                            id='export-excel',
                            n_clicks=0,
                            style={
                                'backgroundColor': '#e74c3c',
                                'color': 'white',
                                'border': 'none',
                                'padding': '10px 15px',
                                'borderRadius': '5px',
                                'cursor': 'pointer'
                            }
                        )
                    ], style={'marginTop': '20px'})
                    
                ], style={'width': '70%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '20px'})
                
            ], style={'display': 'flex'}),
            
            # Visualization Panel
            html.Div([
                html.H3("Drug Analysis Visualizations", style={'color': '#2c3e50', 'textAlign': 'center'}),
                
                # Visualization Tabs
                dcc.Tabs(id='viz-tabs', value='efficacy-safety', children=[
                    dcc.Tab(label='Efficacy vs Safety', value='efficacy-safety'),
                    dcc.Tab(label='Drug Scores', value='drug-scores'),
                    dcc.Tab(label='Target Analysis', value='target-analysis'),
                    dcc.Tab(label='Repurposing Potential', value='repurposing'),
                    dcc.Tab(label='Drug Network', value='network')
                ]),
                
                html.Div(id='viz-content', style={'marginTop': '20px'})
                
            ], style={'marginTop': '30px', 'padding': '20px'})
            
        ])
    
    def _setup_callbacks(self):
        """Setup dashboard callbacks."""
        
        @self.app.callback(
            [Output('summary-stats', 'children'),
             Output('results-table', 'children')],
            [Input('run-analysis', 'n_clicks')],
            [State('upload-data', 'contents'),
             State('efficacy-threshold', 'value'),
             State('safety-threshold', 'value'),
             State('repurposing-threshold', 'value'),
             State('analysis-type', 'value')]
        )
        def run_analysis(n_clicks, contents, efficacy_threshold, safety_threshold, repurposing_threshold, analysis_type):
            """Run drug discovery analysis."""
            if n_clicks == 0 or not contents:
                return "", ""
            
            try:
                # Parse uploaded data
                genomic_data, drug_data = self._parse_uploaded_data(contents)
                
                if genomic_data is None or drug_data is None:
                    return html.Div("Error: Could not parse uploaded data", 
                                  style={'color': 'red'}), ""
                
                # Update configuration
                config = DrugDiscoveryConfig(
                    min_efficacy_score=efficacy_threshold,
                    min_safety_score=safety_threshold,
                    repurposing_threshold=repurposing_threshold
                )
                self.analyzer.config = config
                
                # Run analysis
                results = self.analyzer.analyze_drugs(genomic_data, drug_data, analysis_type)
                self.results = results
                self.current_data = genomic_data
                
                # Generate summary statistics
                summary_stats = self._generate_summary_stats(results)
                
                # Generate results table
                results_table = self._generate_results_table(results)
                
                return summary_stats, results_table
                
            except Exception as e:
                logger.error(f"Error in analysis: {e}")
                return html.Div(f"Error: {str(e)}", style={'color': 'red'}), ""
        
        @self.app.callback(
            Output('viz-content', 'children'),
            [Input('viz-tabs', 'value')]
        )
        def update_visualization(active_tab):
            """Update visualization based on selected tab."""
            if not self.results:
                return html.Div("No results to visualize. Please run analysis first.")
            
            if active_tab == 'efficacy-safety':
                return self._create_efficacy_safety_plot()
            elif active_tab == 'drug-scores':
                return self._create_drug_scores_plot()
            elif active_tab == 'target-analysis':
                return self._create_target_analysis_plot()
            elif active_tab == 'repurposing':
                return self._create_repurposing_plot()
            elif active_tab == 'network':
                return self._create_network_plot()
            else:
                return html.Div("Visualization not implemented yet.")
        
        @self.app.callback(
            Output('export-csv', 'n_clicks'),
            [Input('export-csv', 'n_clicks')]
        )
        def export_csv(n_clicks):
            """Export results to CSV."""
            if n_clicks > 0 and self.results:
                try:
                    self.analyzer.export_results('drug_results.csv', 'csv')
                    return 0  # Reset button
                except Exception as e:
                    logger.error(f"Error exporting CSV: {e}")
            return n_clicks
        
        @self.app.callback(
            Output('export-excel', 'n_clicks'),
            [Input('export-excel', 'n_clicks')]
        )
        def export_excel(n_clicks):
            """Export results to Excel."""
            if n_clicks > 0 and self.results:
                try:
                    self.analyzer.export_results('drug_results.xlsx', 'excel')
                    return 0  # Reset button
                except Exception as e:
                    logger.error(f"Error exporting Excel: {e}")
            return n_clicks
    
    def _parse_uploaded_data(self, contents):
        """Parse uploaded data files."""
        try:
            if not contents:
                return None, None
            
            # For now, use mock data
            # In practice, you would parse the uploaded files
            np.random.seed(42)
            n_samples = 100
            n_genes = 50
            n_drugs = 20
            
            # Generate mock genomic data
            genomic_data = pd.DataFrame(
                np.random.randn(n_genes, n_samples),
                index=[f'Gene_{i}' for i in range(n_genes)],
                columns=[f'Sample_{i}' for i in range(n_samples)]
            )
            
            # Generate mock drug data
            drug_data = pd.DataFrame({
                'name': [f'Drug_{i}' for i in range(n_drugs)],
                'type': np.random.choice(['targeted', 'chemotherapy', 'immunotherapy'], n_drugs),
                'indication': np.random.choice(['cancer', 'other'], n_drugs),
                'IC50': np.random.exponential(1.0, n_drugs),
                'toxicity': np.random.choice(['low', 'moderate', 'high'], n_drugs)
            }, index=[f'Drug_{i}' for i in range(n_drugs)])
            
            return genomic_data, drug_data
            
        except Exception as e:
            logger.error(f"Error parsing uploaded data: {e}")
            return None, None
    
    def _generate_summary_stats(self, results: List[DrugResult]) -> html.Div:
        """Generate summary statistics display."""
        if not results:
            return html.Div("No results available")
        
        total_drugs = len(results)
        high_efficacy = len([r for r in results if r.efficacy_score > 0.8])
        high_safety = len([r for r in results if r.safety_score > 0.8])
        repurposing_candidates = len([r for r in results if r.repurposing_potential > 0.8])
        
        stats_cards = [
            html.Div([
                html.H4(str(total_drugs), style={'color': '#3498db', 'margin': '0'}),
                html.P("Total Drugs", style={'margin': '0', 'color': '#7f8c8d'})
            ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': '#ecf0f1', 'borderRadius': '5px', 'margin': '5px'}),
            
            html.Div([
                html.H4(str(high_efficacy), style={'color': '#e74c3c', 'margin': '0'}),
                html.P("High Efficacy", style={'margin': '0', 'color': '#7f8c8d'})
            ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': '#ecf0f1', 'borderRadius': '5px', 'margin': '5px'}),
            
            html.Div([
                html.H4(str(high_safety), style={'color': '#f39c12', 'margin': '0'}),
                html.P("High Safety", style={'margin': '0', 'color': '#7f8c8d'})
            ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': '#ecf0f1', 'borderRadius': '5px', 'margin': '5px'}),
            
            html.Div([
                html.H4(str(repurposing_candidates), style={'color': '#27ae60', 'margin': '0'}),
                html.P("Repurposing Candidates", style={'margin': '0', 'color': '#7f8c8d'})
            ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': '#ecf0f1', 'borderRadius': '5px', 'margin': '5px'})
        ]
        
        return html.Div(stats_cards, style={'display': 'flex', 'justifyContent': 'space-around'})
    
    def _generate_results_table(self, results: List[DrugResult]) -> html.Div:
        """Generate results table."""
        if not results:
            return html.Div("No results to display")
        
        # Convert results to DataFrame
        table_data = []
        for result in results[:20]:  # Show top 20 results
            table_data.append({
                'Drug': result.drug_name,
                'Type': result.drug_type,
                'Efficacy Score': f"{result.efficacy_score:.3f}",
                'Safety Score': f"{result.safety_score:.3f}",
                'Repurposing Potential': f"{result.repurposing_potential:.3f}",
                'Targets': '; '.join(result.target_genes[:3]),  # Show first 3 targets
                'Mechanism': result.mechanism_of_action[:50] + '...' if len(result.mechanism_of_action) > 50 else result.mechanism_of_action
            })
        
        df = pd.DataFrame(table_data)
        
        return html.Div([
            html.H4("Top Drug Candidates", style={'color': '#2c3e50'}),
            html.Table([
                html.Thead([
                    html.Tr([html.Th(col) for col in df.columns])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td(df.iloc[i][col]) for col in df.columns
                    ]) for i in range(len(df))
                ])
            ], style={'width': '100%', 'borderCollapse': 'collapse', 'border': '1px solid #ddd'})
        ])
    
    def _create_efficacy_safety_plot(self) -> dcc.Graph:
        """Create efficacy vs safety scatter plot."""
        if not self.results:
            return dcc.Graph()
        
        x_data = [r.efficacy_score for r in self.results]
        y_data = [r.safety_score for r in self.results]
        text_data = [r.drug_name for r in self.results]
        
        # Color by repurposing potential
        colors = []
        for r in self.results:
            if r.repurposing_potential > 0.8:
                colors.append('green')
            elif r.repurposing_potential > 0.5:
                colors.append('orange')
            else:
                colors.append('blue')
        
        fig = go.Figure(data=go.Scatter(
            x=x_data,
            y=y_data,
            mode='markers',
            marker=dict(
                color=colors,
                size=10,
                opacity=0.7
            ),
            text=text_data,
            hovertemplate='<b>%{text}</b><br>' +
                         'Efficacy: %{x:.3f}<br>' +
                         'Safety: %{y:.3f}<extra></extra>'
        ))
        
        fig.update_layout(
            title='Drug Efficacy vs Safety',
            xaxis_title='Efficacy Score',
            yaxis_title='Safety Score',
            hovermode='closest'
        )
        
        return dcc.Graph(figure=fig)
    
    def _create_drug_scores_plot(self) -> dcc.Graph:
        """Create drug scores bar plot."""
        if not self.results:
            return dcc.Graph()
        
        # Get top 10 drugs by combined score
        top_drugs = sorted(
            self.results, 
            key=lambda x: (x.efficacy_score + x.safety_score + x.repurposing_potential) / 3,
            reverse=True
        )[:10]
        
        drug_names = [r.drug_name for r in top_drugs]
        efficacy_scores = [r.efficacy_score for r in top_drugs]
        safety_scores = [r.safety_score for r in top_drugs]
        repurposing_scores = [r.repurposing_potential for r in top_drugs]
        
        fig = go.Figure(data=[
            go.Bar(name='Efficacy', x=drug_names, y=efficacy_scores, marker_color='red'),
            go.Bar(name='Safety', x=drug_names, y=safety_scores, marker_color='green'),
            go.Bar(name='Repurposing', x=drug_names, y=repurposing_scores, marker_color='blue')
        ])
        
        fig.update_layout(
            title='Drug Scores Comparison',
            xaxis_title='Drugs',
            yaxis_title='Score',
            barmode='group',
            hovermode='closest'
        )
        
        return dcc.Graph(figure=fig)
    
    def _create_target_analysis_plot(self) -> dcc.Graph:
        """Create target analysis plot."""
        if not self.results:
            return dcc.Graph()
        
        # Count target frequency
        target_counts = {}
        for result in self.results:
            for target in result.target_genes:
                target_counts[target] = target_counts.get(target, 0) + 1
        
        # Get top targets
        top_targets = sorted(target_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        target_names = [t[0] for t in top_targets]
        target_counts_list = [t[1] for t in top_targets]
        
        fig = go.Figure(data=go.Bar(
            x=target_names,
            y=target_counts_list,
            marker_color='lightblue'
        ))
        
        fig.update_layout(
            title='Most Targeted Genes',
            xaxis_title='Target Genes',
            yaxis_title='Number of Drugs',
            hovermode='closest'
        )
        
        return dcc.Graph(figure=fig)
    
    def _create_repurposing_plot(self) -> dcc.Graph:
        """Create repurposing potential plot."""
        if not self.results:
            return dcc.Graph()
        
        # Filter drugs with repurposing potential
        repurposing_drugs = [r for r in self.results if r.repurposing_potential > 0.5]
        
        if not repurposing_drugs:
            return html.Div("No drugs with significant repurposing potential found.")
        
        drug_names = [r.drug_name for r in repurposing_drugs]
        repurposing_scores = [r.repurposing_potential for r in repurposing_drugs]
        
        fig = go.Figure(data=go.Bar(
            x=drug_names,
            y=repurposing_scores,
            marker_color='green'
        ))
        
        fig.update_layout(
            title='Drug Repurposing Potential',
            xaxis_title='Drugs',
            yaxis_title='Repurposing Score',
            hovermode='closest'
        )
        
        return dcc.Graph(figure=fig)
    
    def _create_network_plot(self) -> dcc.Graph:
        """Create drug-target network plot."""
        if not self.results:
            return dcc.Graph()
        
        # Create a simple network visualization
        # In practice, this would use actual network analysis
        
        # Mock network data
        nodes = []
        edges = []
        
        # Add drug nodes
        for i, result in enumerate(self.results[:10]):  # Top 10 drugs
            nodes.append({
                'id': result.drug_id,
                'label': result.drug_name,
                'type': 'drug',
                'size': result.efficacy_score * 20,
                'color': 'blue'
            })
            
            # Add target nodes and edges
            for target in result.target_genes[:3]:  # Top 3 targets per drug
                if not any(n['id'] == target for n in nodes):
                    nodes.append({
                        'id': target,
                        'label': target,
                        'type': 'target',
                        'size': 10,
                        'color': 'red'
                    })
                
                edges.append({
                    'source': result.drug_id,
                    'target': target,
                    'weight': result.efficacy_score
                })
        
        # Create network plot using plotly
        fig = go.Figure()
        
        # Add edges
        for edge in edges:
            fig.add_trace(go.Scatter(
                x=[0, 1],  # Mock coordinates
                y=[0, 1],
                mode='lines',
                line=dict(width=1, color='gray'),
                showlegend=False,
                hoverinfo='none'
            ))
        
        # Add nodes
        for node in nodes:
            fig.add_trace(go.Scatter(
                x=[0.5],  # Mock coordinates
                y=[0.5],
                mode='markers+text',
                marker=dict(
                    size=node['size'],
                    color=node['color'],
                    opacity=0.7
                ),
                text=node['label'],
                textposition='middle center',
                name=node['label'],
                showlegend=False
            ))
        
        fig.update_layout(
            title='Drug-Target Network (Mock)',
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            hovermode='closest'
        )
        
        return dcc.Graph(figure=fig)
    
    def run_server(self, debug: bool = True, port: int = 8051):
        """Run the dashboard server."""
        self.app.run_server(debug=debug, port=port)


class DrugVisualizationEngine:
    """Engine for creating drug visualizations."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_efficacy_safety_plot(self, results: List[DrugResult]) -> go.Figure:
        """Create efficacy vs safety scatter plot."""
        if not results:
            return go.Figure()
        
        x_data = [r.efficacy_score for r in results]
        y_data = [r.safety_score for r in results]
        text_data = [r.drug_name for r in results]
        
        # Color by repurposing potential
        colors = []
        for r in results:
            if r.repurposing_potential > 0.8:
                colors.append('green')
            elif r.repurposing_potential > 0.5:
                colors.append('orange')
            else:
                colors.append('blue')
        
        fig = go.Figure(data=go.Scatter(
            x=x_data,
            y=y_data,
            mode='markers',
            marker=dict(color=colors, size=10, opacity=0.7),
            text=text_data,
            hovertemplate='<b>%{text}</b><br>Efficacy: %{x:.3f}<br>Safety: %{y:.3f}<extra></extra>'
        ))
        
        fig.update_layout(
            title='Drug Efficacy vs Safety',
            xaxis_title='Efficacy Score',
            yaxis_title='Safety Score',
            hovermode='closest'
        )
        
        return fig
    
    def create_drug_scores_plot(self, results: List[DrugResult], top_n: int = 10) -> go.Figure:
        """Create drug scores bar plot."""
        if not results:
            return go.Figure()
        
        # Get top N drugs by combined score
        top_drugs = sorted(
            results, 
            key=lambda x: (x.efficacy_score + x.safety_score + x.repurposing_potential) / 3,
            reverse=True
        )[:top_n]
        
        drug_names = [r.drug_name for r in top_drugs]
        efficacy_scores = [r.efficacy_score for r in top_drugs]
        safety_scores = [r.safety_score for r in top_drugs]
        repurposing_scores = [r.repurposing_potential for r in top_drugs]
        
        fig = go.Figure(data=[
            go.Bar(name='Efficacy', x=drug_names, y=efficacy_scores, marker_color='red'),
            go.Bar(name='Safety', x=drug_names, y=safety_scores, marker_color='green'),
            go.Bar(name='Repurposing', x=drug_names, y=repurposing_scores, marker_color='blue')
        ])
        
        fig.update_layout(
            title='Drug Scores Comparison',
            xaxis_title='Drugs',
            yaxis_title='Score',
            barmode='group',
            hovermode='closest'
        )
        
        return fig
    
    def create_target_analysis_plot(self, results: List[DrugResult]) -> go.Figure:
        """Create target analysis plot."""
        if not results:
            return go.Figure()
        
        # Count target frequency
        target_counts = {}
        for result in results:
            for target in result.target_genes:
                target_counts[target] = target_counts.get(target, 0) + 1
        
        # Get top targets
        top_targets = sorted(target_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        target_names = [t[0] for t in top_targets]
        target_counts_list = [t[1] for t in top_targets]
        
        fig = go.Figure(data=go.Bar(
            x=target_names,
            y=target_counts_list,
            marker_color='lightblue'
        ))
        
        fig.update_layout(
            title='Most Targeted Genes',
            xaxis_title='Target Genes',
            yaxis_title='Number of Drugs',
            hovermode='closest'
        )
        
        return fig
