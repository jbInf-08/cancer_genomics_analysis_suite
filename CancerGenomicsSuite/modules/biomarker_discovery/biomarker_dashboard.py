"""
Biomarker Discovery Dashboard for Cancer Genomics Analysis

This module provides an interactive dashboard for biomarker discovery and analysis
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

from .biomarker_analyzer import BiomarkerAnalyzer, BiomarkerResult, BiomarkerDiscoveryConfig

logger = logging.getLogger(__name__)


class BiomarkerDiscoveryDashboard:
    """Interactive dashboard for biomarker discovery."""
    
    def __init__(self, app: Optional[dash.Dash] = None):
        """Initialize the biomarker discovery dashboard."""
        self.app = app or dash.Dash(__name__)
        self.analyzer = BiomarkerAnalyzer()
        self.results = []
        self.current_data = None
        self.current_labels = None
        
        self._setup_layout()
        self._setup_callbacks()
    
    def _setup_layout(self):
        """Setup the dashboard layout."""
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1("Biomarker Discovery Dashboard", 
                       style={'textAlign': 'center', 'color': '#2c3e50'}),
                html.P("Discover and analyze biomarkers for cancer genomics",
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
                        html.Label("P-value Threshold:"),
                        dcc.Slider(
                            id='p-value-threshold',
                            min=0.001,
                            max=0.1,
                            step=0.001,
                            value=0.05,
                            marks={i/100: str(i/100) for i in range(1, 11, 2)},
                            tooltip={"placement": "bottom", "always_visible": True}
                        )
                    ], style={'margin': '10px 0'}),
                    
                    html.Div([
                        html.Label("Effect Size Threshold:"),
                        dcc.Slider(
                            id='effect-size-threshold',
                            min=0.1,
                            max=1.0,
                            step=0.05,
                            value=0.2,
                            marks={i/10: str(i/10) for i in range(1, 11, 2)},
                            tooltip={"placement": "bottom", "always_visible": True}
                        )
                    ], style={'margin': '10px 0'}),
                    
                    html.Div([
                        html.Label("AUC Threshold:"),
                        dcc.Slider(
                            id='auc-threshold',
                            min=0.5,
                            max=1.0,
                            step=0.05,
                            value=0.7,
                            marks={i/10: str(i/10) for i in range(5, 11)},
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
                                {'label': 'Statistical Only', 'value': 'statistical'},
                                {'label': 'Machine Learning Only', 'value': 'ml'}
                            ],
                            value='comprehensive'
                        )
                    ], style={'margin': '10px 0'}),
                    
                    # Run Analysis Button
                    html.Button(
                        'Run Biomarker Discovery',
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
                    html.H3("Biomarker Discovery Results", style={'color': '#2c3e50'}),
                    
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
                html.H3("Biomarker Visualizations", style={'color': '#2c3e50', 'textAlign': 'center'}),
                
                # Visualization Tabs
                dcc.Tabs(id='viz-tabs', value='volcano-plot', children=[
                    dcc.Tab(label='Volcano Plot', value='volcano-plot'),
                    dcc.Tab(label='Manhattan Plot', value='manhattan-plot'),
                    dcc.Tab(label='ROC Curves', value='roc-curves'),
                    dcc.Tab(label='Effect Size Distribution', value='effect-size'),
                    dcc.Tab(label='Biomarker Network', value='network')
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
             State('p-value-threshold', 'value'),
             State('effect-size-threshold', 'value'),
             State('auc-threshold', 'value'),
             State('analysis-type', 'value')]
        )
        def run_analysis(n_clicks, contents, p_threshold, effect_threshold, auc_threshold, analysis_type):
            """Run biomarker discovery analysis."""
            if n_clicks == 0 or not contents:
                return "", ""
            
            try:
                # Parse uploaded data
                data, labels = self._parse_uploaded_data(contents)
                
                if data is None or labels is None:
                    return html.Div("Error: Could not parse uploaded data", 
                                  style={'color': 'red'}), ""
                
                # Update configuration
                config = BiomarkerDiscoveryConfig(
                    p_value_threshold=p_threshold,
                    effect_size_threshold=effect_threshold,
                    auc_threshold=auc_threshold
                )
                self.analyzer.config = config
                
                # Run analysis
                if analysis_type == 'statistical':
                    from .biomarker_analyzer import StatisticalBiomarkerDiscovery
                    analyzer = StatisticalBiomarkerDiscovery(config)
                elif analysis_type == 'ml':
                    from .biomarker_analyzer import MLBiomarkerDiscovery
                    analyzer = MLBiomarkerDiscovery(config)
                else:
                    analyzer = self.analyzer
                
                results = analyzer.discover_biomarkers(data, labels)
                self.results = results
                self.current_data = data
                self.current_labels = labels
                
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
            
            if active_tab == 'volcano-plot':
                return self._create_volcano_plot()
            elif active_tab == 'manhattan-plot':
                return self._create_manhattan_plot()
            elif active_tab == 'roc-curves':
                return self._create_roc_curves()
            elif active_tab == 'effect-size':
                return self._create_effect_size_plot()
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
                    self.analyzer.export_results('biomarker_results.csv', 'csv')
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
                    self.analyzer.export_results('biomarker_results.xlsx', 'excel')
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
            n_features = 50
            
            # Generate mock expression data
            data = pd.DataFrame(
                np.random.randn(n_features, n_samples),
                index=[f'Gene_{i}' for i in range(n_features)],
                columns=[f'Sample_{i}' for i in range(n_samples)]
            )
            
            # Generate mock labels (binary classification)
            labels = pd.Series(
                np.random.choice([0, 1], size=n_samples),
                index=[f'Sample_{i}' for i in range(n_samples)]
            )
            
            return data, labels
            
        except Exception as e:
            logger.error(f"Error parsing uploaded data: {e}")
            return None, None
    
    def _generate_summary_stats(self, results: List[BiomarkerResult]) -> html.Div:
        """Generate summary statistics display."""
        if not results:
            return html.Div("No results available")
        
        total_biomarkers = len(results)
        significant_biomarkers = len([r for r in results if r.p_value < 0.05])
        high_effect_biomarkers = len([r for r in results if r.effect_size > 0.5])
        high_auc_biomarkers = len([r for r in results if r.auc_score > 0.8])
        
        stats_cards = [
            html.Div([
                html.H4(str(total_biomarkers), style={'color': '#3498db', 'margin': '0'}),
                html.P("Total Biomarkers", style={'margin': '0', 'color': '#7f8c8d'})
            ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': '#ecf0f1', 'borderRadius': '5px', 'margin': '5px'}),
            
            html.Div([
                html.H4(str(significant_biomarkers), style={'color': '#e74c3c', 'margin': '0'}),
                html.P("Significant (p<0.05)", style={'margin': '0', 'color': '#7f8c8d'})
            ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': '#ecf0f1', 'borderRadius': '5px', 'margin': '5px'}),
            
            html.Div([
                html.H4(str(high_effect_biomarkers), style={'color': '#f39c12', 'margin': '0'}),
                html.P("High Effect Size", style={'margin': '0', 'color': '#7f8c8d'})
            ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': '#ecf0f1', 'borderRadius': '5px', 'margin': '5px'}),
            
            html.Div([
                html.H4(str(high_auc_biomarkers), style={'color': '#27ae60', 'margin': '0'}),
                html.P("High AUC (>0.8)", style={'margin': '0', 'color': '#7f8c8d'})
            ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': '#ecf0f1', 'borderRadius': '5px', 'margin': '5px'})
        ]
        
        return html.Div(stats_cards, style={'display': 'flex', 'justifyContent': 'space-around'})
    
    def _generate_results_table(self, results: List[BiomarkerResult]) -> html.Div:
        """Generate results table."""
        if not results:
            return html.Div("No results to display")
        
        # Convert results to DataFrame
        table_data = []
        for result in results[:20]:  # Show top 20 results
            table_data.append({
                'Biomarker': result.biomarker_name,
                'Type': result.biomarker_type,
                'P-value': f"{result.p_value:.2e}",
                'Effect Size': f"{result.effect_size:.3f}",
                'AUC': f"{result.auc_score:.3f}",
                'Sensitivity': f"{result.sensitivity:.3f}",
                'Specificity': f"{result.specificity:.3f}",
                'Clinical Significance': result.clinical_significance
            })
        
        df = pd.DataFrame(table_data)
        
        return html.Div([
            html.H4("Top Biomarkers", style={'color': '#2c3e50'}),
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
    
    def _create_volcano_plot(self) -> dcc.Graph:
        """Create volcano plot visualization."""
        if not self.results:
            return dcc.Graph()
        
        # Prepare data for volcano plot
        x_data = [np.log2(r.effect_size + 0.001) for r in self.results]  # Log2 fold change
        y_data = [-np.log10(r.p_value + 1e-10) for r in self.results]  # -log10 p-value
        text_data = [r.biomarker_name for r in self.results]
        
        # Color by significance
        colors = []
        for r in self.results:
            if r.p_value < 0.05 and r.effect_size > 0.2:
                colors.append('red')
            elif r.p_value < 0.05:
                colors.append('orange')
            else:
                colors.append('gray')
        
        fig = go.Figure(data=go.Scatter(
            x=x_data,
            y=y_data,
            mode='markers',
            marker=dict(
                color=colors,
                size=8,
                opacity=0.7
            ),
            text=text_data,
            hovertemplate='<b>%{text}</b><br>' +
                         'Effect Size: %{x:.3f}<br>' +
                         'P-value: %{y:.3f}<extra></extra>'
        ))
        
        fig.update_layout(
            title='Volcano Plot: Effect Size vs P-value',
            xaxis_title='Log2 Effect Size',
            yaxis_title='-Log10 P-value',
            hovermode='closest'
        )
        
        return dcc.Graph(figure=fig)
    
    def _create_manhattan_plot(self) -> dcc.Graph:
        """Create Manhattan plot visualization."""
        if not self.results:
            return dcc.Graph()
        
        # Prepare data for Manhattan plot
        x_data = list(range(len(self.results)))
        y_data = [-np.log10(r.p_value + 1e-10) for r in self.results]
        text_data = [r.biomarker_name for r in self.results]
        
        fig = go.Figure(data=go.Scatter(
            x=x_data,
            y=y_data,
            mode='markers',
            marker=dict(
                color='blue',
                size=6,
                opacity=0.7
            ),
            text=text_data,
            hovertemplate='<b>%{text}</b><br>' +
                         'P-value: %{y:.3f}<extra></extra>'
        ))
        
        # Add significance line
        fig.add_hline(y=-np.log10(0.05), line_dash="dash", line_color="red",
                     annotation_text="p = 0.05")
        
        fig.update_layout(
            title='Manhattan Plot: Biomarker Significance',
            xaxis_title='Biomarker Index',
            yaxis_title='-Log10 P-value',
            hovermode='closest'
        )
        
        return dcc.Graph(figure=fig)
    
    def _create_roc_curves(self) -> dcc.Graph:
        """Create ROC curves visualization."""
        if not self.results:
            return dcc.Graph()
        
        fig = go.Figure()
        
        # Add ROC curves for top biomarkers
        top_biomarkers = sorted(self.results, key=lambda x: x.auc_score, reverse=True)[:5]
        
        for i, result in enumerate(top_biomarkers):
            # Generate mock ROC curve data
            fpr = np.linspace(0, 1, 100)
            tpr = np.linspace(0, 1, 100) * result.auc_score + np.random.normal(0, 0.05, 100)
            tpr = np.clip(tpr, 0, 1)
            
            fig.add_trace(go.Scatter(
                x=fpr,
                y=tpr,
                mode='lines',
                name=f'{result.biomarker_name} (AUC={result.auc_score:.3f})',
                line=dict(width=2)
            ))
        
        # Add diagonal line
        fig.add_trace(go.Scatter(
            x=[0, 1],
            y=[0, 1],
            mode='lines',
            name='Random Classifier',
            line=dict(dash='dash', color='gray')
        ))
        
        fig.update_layout(
            title='ROC Curves for Top Biomarkers',
            xaxis_title='False Positive Rate',
            yaxis_title='True Positive Rate',
            hovermode='closest'
        )
        
        return dcc.Graph(figure=fig)
    
    def _create_effect_size_plot(self) -> dcc.Graph:
        """Create effect size distribution plot."""
        if not self.results:
            return dcc.Graph()
        
        effect_sizes = [r.effect_size for r in self.results]
        
        fig = go.Figure(data=go.Histogram(
            x=effect_sizes,
            nbinsx=20,
            marker_color='lightblue',
            opacity=0.7
        ))
        
        fig.update_layout(
            title='Distribution of Effect Sizes',
            xaxis_title='Effect Size',
            yaxis_title='Frequency',
            hovermode='closest'
        )
        
        return dcc.Graph(figure=fig)
    
    def _create_network_plot(self) -> dcc.Graph:
        """Create biomarker network plot."""
        if not self.results:
            return dcc.Graph()
        
        # Create a simple network visualization
        # In practice, this would use actual network analysis
        
        # Mock network data
        nodes = []
        edges = []
        
        # Add nodes for top biomarkers
        top_biomarkers = sorted(self.results, key=lambda x: x.effect_size, reverse=True)[:10]
        
        for i, result in enumerate(top_biomarkers):
            nodes.append({
                'id': result.biomarker_name,
                'label': result.biomarker_name,
                'size': result.effect_size * 20,
                'color': 'red' if result.p_value < 0.05 else 'gray'
            })
        
        # Add some mock edges
        for i in range(len(nodes) - 1):
            edges.append({
                'source': nodes[i]['id'],
                'target': nodes[i + 1]['id'],
                'weight': 0.5
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
            title='Biomarker Network (Mock)',
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            hovermode='closest'
        )
        
        return dcc.Graph(figure=fig)
    
    def run_server(self, debug: bool = True, port: int = 8050):
        """Run the dashboard server."""
        self.app.run_server(debug=debug, port=port)


class BiomarkerVisualizationEngine:
    """Engine for creating biomarker visualizations."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_volcano_plot(self, results: List[BiomarkerResult]) -> go.Figure:
        """Create volcano plot for biomarker results."""
        if not results:
            return go.Figure()
        
        # Prepare data
        x_data = [np.log2(r.effect_size + 0.001) for r in results]
        y_data = [-np.log10(r.p_value + 1e-10) for r in results]
        text_data = [r.biomarker_name for r in results]
        
        # Color by significance
        colors = []
        for r in results:
            if r.p_value < 0.05 and r.effect_size > 0.2:
                colors.append('red')
            elif r.p_value < 0.05:
                colors.append('orange')
            else:
                colors.append('gray')
        
        fig = go.Figure(data=go.Scatter(
            x=x_data,
            y=y_data,
            mode='markers',
            marker=dict(color=colors, size=8, opacity=0.7),
            text=text_data,
            hovertemplate='<b>%{text}</b><br>Effect Size: %{x:.3f}<br>P-value: %{y:.3f}<extra></extra>'
        ))
        
        fig.update_layout(
            title='Volcano Plot: Effect Size vs P-value',
            xaxis_title='Log2 Effect Size',
            yaxis_title='-Log10 P-value',
            hovermode='closest'
        )
        
        return fig
    
    def create_manhattan_plot(self, results: List[BiomarkerResult]) -> go.Figure:
        """Create Manhattan plot for biomarker results."""
        if not results:
            return go.Figure()
        
        x_data = list(range(len(results)))
        y_data = [-np.log10(r.p_value + 1e-10) for r in results]
        text_data = [r.biomarker_name for r in results]
        
        fig = go.Figure(data=go.Scatter(
            x=x_data,
            y=y_data,
            mode='markers',
            marker=dict(color='blue', size=6, opacity=0.7),
            text=text_data,
            hovertemplate='<b>%{text}</b><br>P-value: %{y:.3f}<extra></extra>'
        ))
        
        # Add significance line
        fig.add_hline(y=-np.log10(0.05), line_dash="dash", line_color="red",
                     annotation_text="p = 0.05")
        
        fig.update_layout(
            title='Manhattan Plot: Biomarker Significance',
            xaxis_title='Biomarker Index',
            yaxis_title='-Log10 P-value',
            hovermode='closest'
        )
        
        return fig
    
    def create_roc_curves(self, results: List[BiomarkerResult], top_n: int = 5) -> go.Figure:
        """Create ROC curves for top biomarkers."""
        if not results:
            return go.Figure()
        
        fig = go.Figure()
        
        top_biomarkers = sorted(results, key=lambda x: x.auc_score, reverse=True)[:top_n]
        
        for result in top_biomarkers:
            # Generate mock ROC curve data
            fpr = np.linspace(0, 1, 100)
            tpr = np.linspace(0, 1, 100) * result.auc_score + np.random.normal(0, 0.05, 100)
            tpr = np.clip(tpr, 0, 1)
            
            fig.add_trace(go.Scatter(
                x=fpr,
                y=tpr,
                mode='lines',
                name=f'{result.biomarker_name} (AUC={result.auc_score:.3f})',
                line=dict(width=2)
            ))
        
        # Add diagonal line
        fig.add_trace(go.Scatter(
            x=[0, 1],
            y=[0, 1],
            mode='lines',
            name='Random Classifier',
            line=dict(dash='dash', color='gray')
        ))
        
        fig.update_layout(
            title='ROC Curves for Top Biomarkers',
            xaxis_title='False Positive Rate',
            yaxis_title='True Positive Rate',
            hovermode='closest'
        )
        
        return fig
