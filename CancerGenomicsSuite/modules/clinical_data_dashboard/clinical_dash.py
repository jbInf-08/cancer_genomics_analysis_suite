"""
Clinical Dashboard Module

This module provides a comprehensive Dash-based dashboard for clinical data
analysis, survival analysis, and visualization.
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import json
from typing import Dict, List, Any, Optional
import logging
import base64
import io

from .dashboard import ClinicalDataAnalyzer, create_mock_clinical_data, create_mock_survival_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClinicalDashboard:
    """
    A comprehensive dashboard for clinical data analysis and survival analysis.
    """
    
    def __init__(self, app: dash.Dash):
        """
        Initialize the clinical dashboard.
        
        Args:
            app: Dash application instance
        """
        self.app = app
        self.analyzer = ClinicalDataAnalyzer()
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
                html.H1("Clinical Data Analysis Dashboard", 
                       className="text-center mb-4"),
                html.P("Comprehensive analysis and visualization of clinical data in cancer genomics",
                      className="text-center text-muted mb-4")
            ], className="container-fluid"),
            
            # Control Panel
            html.Div([
                html.Div([
                    html.H4("Data Upload & Configuration", className="card-title"),
                    
                    # File upload section
                    html.Div([
                        html.Label("Upload Clinical Data:"),
                        dcc.Upload(
                            id='upload-clinical-data',
                            children=html.Div([
                                'Drag and Drop or ',
                                html.A('Select Clinical Data File')
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
                        html.Small("Supported formats: CSV, TSV, Excel", className="text-muted")
                    ], className="mb-3"),
                    
                    html.Div([
                        html.Label("Upload Survival Data:"),
                        dcc.Upload(
                            id='upload-survival-data',
                            children=html.Div([
                                'Drag and Drop or ',
                                html.A('Select Survival Data File')
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
                        html.Small("Required columns: survival_time, death", className="text-muted")
                    ], className="mb-3"),
                    
                    # Analysis configuration
                    html.Div([
                        html.Label("Analysis Configuration:"),
                        html.Div([
                            html.Label("Patient ID Column:"),
                            dcc.Input(
                                id='patient-id-col',
                                type='text',
                                value='patient_id',
                                className="form-control mb-2"
                            ),
                            html.Label("Survival Time Column:"),
                            dcc.Input(
                                id='survival-time-col',
                                type='text',
                                value='survival_time',
                                className="form-control mb-2"
                            ),
                            html.Label("Death Event Column:"),
                            dcc.Input(
                                id='death-event-col',
                                type='text',
                                value='death',
                                className="form-control mb-2"
                            )
                        ], className="row")
                    ], className="mb-3"),
                    
                    # Action buttons
                    html.Div([
                        html.Button('Load Mock Data', id='load-mock-data', 
                                  className='btn btn-primary me-2'),
                        html.Button('Preprocess Data', id='preprocess-data', 
                                  className='btn btn-success me-2'),
                        html.Button('Run Survival Analysis', id='run-survival', 
                                  className='btn btn-info me-2'),
                        html.Button('Run Clinical Analysis', id='run-clinical', 
                                  className='btn btn-warning me-2'),
                        html.Button('Export Results', id='export-results', 
                                  className='btn btn-secondary')
                    ], className="d-flex flex-wrap gap-2")
                    
                ], className="card-body")
            ], className="card mb-4"),
            
            # Main content area
            html.Div([
                # Tabs for different views
                dcc.Tabs(id="main-tabs", value="overview", children=[
                    dcc.Tab(label="Data Overview", value="overview"),
                    dcc.Tab(label="Survival Analysis", value="survival"),
                    dcc.Tab(label="Clinical Correlations", value="correlations"),
                    dcc.Tab(label="Clinical Associations", value="associations"),
                    dcc.Tab(label="Predictive Modeling", value="modeling"),
                    dcc.Tab(label="Visualizations", value="visualizations")
                ]),
                
                # Tab content
                html.Div(id="clinical-tab-content", className="mt-3")
                
            ], className="container-fluid"),
            
            # Hidden divs for storing data
            html.Div(id='clinical-data', style={'display': 'none'}),
            html.Div(id='survival-data', style={'display': 'none'}),
            html.Div(id='clinical-analysis-results', style={'display': 'none'}),
            
            # Download components
            dcc.Download(id="clinical-download-results"),
            dcc.Download(id="download-data")
        ])
    
    def create_overview_tab(self) -> html.Div:
        """Create the data overview tab content."""
        return html.Div([
            html.Div([
                html.H4("Clinical Data Overview"),
                dcc.Graph(id="clinical-overview-plot")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Data Quality Metrics"),
                html.Div(id="quality-metrics", className="row")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Data Summary"),
                html.Div(id="data-summary")
            ], className="card")
        ])
    
    def create_survival_tab(self) -> html.Div:
        """Create the survival analysis tab content."""
        return html.Div([
            html.Div([
                html.H4("Survival Analysis Configuration"),
                html.Div([
                    html.Label("Group by Variable (optional):"),
                    dcc.Dropdown(
                        id="survival-group-col",
                        placeholder="Select grouping variable...",
                        className="mb-2"
                    ),
                    html.Button("Run Survival Analysis", id="run-survival-analysis", 
                              className="btn btn-primary")
                ], className="mb-3")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Kaplan-Meier Survival Curves"),
                dcc.Graph(id="survival-plot")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Survival Analysis Results"),
                html.Div(id="survival-results")
            ], className="card")
        ])
    
    def create_correlations_tab(self) -> html.Div:
        """Create the correlations tab content."""
        return html.Div([
            html.Div([
                html.H4("Clinical Correlations"),
                html.Div([
                    html.Label("Correlation Method:"),
                    dcc.Dropdown(
                        id="correlation-method",
                        options=[
                            {'label': 'Pearson', 'value': 'pearson'},
                            {'label': 'Spearman', 'value': 'spearman'},
                            {'label': 'Kendall', 'value': 'kendall'}
                        ],
                        value='pearson',
                        className="mb-2"
                    ),
                    html.Label("Target Variable (optional):"),
                    dcc.Dropdown(
                        id="correlation-target",
                        placeholder="Select target variable...",
                        className="mb-2"
                    ),
                    html.Button("Run Correlation Analysis", id="run-correlation", 
                              className="btn btn-primary")
                ], className="mb-3")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Correlation Heatmap"),
                dcc.Graph(id="correlation-heatmap")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Correlation Results"),
                html.Div(id="correlation-results")
            ], className="card")
        ])
    
    def create_associations_tab(self) -> html.Div:
        """Create the associations tab content."""
        return html.Div([
            html.Div([
                html.H4("Clinical Associations"),
                html.Div([
                    html.Label("Select Variables for Association Analysis:"),
                    dcc.Checklist(
                        id="association-variables",
                        options=[],
                        value=[],
                        className="mb-2"
                    ),
                    html.Button("Run Association Analysis", id="run-association", 
                              className="btn btn-primary")
                ], className="mb-3")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Association Results"),
                html.Div(id="association-results")
            ], className="card")
        ])
    
    def create_modeling_tab(self) -> html.Div:
        """Create the predictive modeling tab content."""
        return html.Div([
            html.Div([
                html.H4("Predictive Modeling"),
                html.Div([
                    html.Label("Target Variable:"),
                    dcc.Dropdown(
                        id="model-target",
                        placeholder="Select target variable...",
                        className="mb-2"
                    ),
                    html.Label("Model Type:"),
                    dcc.Dropdown(
                        id="model-type",
                        options=[
                            {'label': 'Classification', 'value': 'classification'},
                            {'label': 'Regression', 'value': 'regression'}
                        ],
                        value='classification',
                        className="mb-2"
                    ),
                    html.Label("Test Size:"),
                    dcc.Slider(
                        id='test-size',
                        min=0.1,
                        max=0.5,
                        step=0.05,
                        value=0.2,
                        marks={i/10: f'{i/10:.1f}' for i in range(1, 6)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                    html.Button("Build Model", id="build-model", 
                              className="btn btn-primary mt-2")
                ], className="mb-3")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Model Performance"),
                html.Div(id="model-performance")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Feature Importance"),
                dcc.Graph(id="feature-importance-plot")
            ], className="card")
        ])
    
    def create_visualizations_tab(self) -> html.Div:
        """Create the visualizations tab content."""
        return html.Div([
            html.Div([
                html.H4("Interactive Visualizations"),
                html.Div([
                    html.Label("Visualization Type:"),
                    dcc.Dropdown(
                        id="visualization-type",
                        options=[
                            {'label': 'Survival Curves', 'value': 'survival'},
                            {'label': 'Correlation Heatmap', 'value': 'correlation'},
                            {'label': 'Clinical Overview', 'value': 'overview'},
                            {'label': 'Box Plots', 'value': 'boxplot'},
                            {'label': 'Distribution Plots', 'value': 'distribution'}
                        ],
                        value='survival',
                        className="mb-2"
                    ),
                    html.Label("Group by (optional):"),
                    dcc.Dropdown(
                        id="viz-group-by",
                        placeholder="Select grouping variable...",
                        className="mb-2"
                    )
                ], className="mb-3"),
                dcc.Graph(id="main-visualization", style={'height': '600px'})
            ], className="card")
        ])
    
    def setup_callbacks(self):
        """Set up all dashboard callbacks."""
        
        @self.app.callback(
            [Output('clinical-data', 'children'),
             Output('survival-data', 'children'),
             Output('data-summary', 'children')],
            [Input('load-mock-data', 'n_clicks')]
        )
        def load_mock_data(n_clicks):
            """Load mock data and create summary."""
            if n_clicks:
                try:
                    # Create mock data
                    clinical_data = create_mock_clinical_data()
                    survival_data = create_mock_survival_data()
                    
                    # Store data
                    clinical_json = json.dumps(clinical_data.to_dict())
                    survival_json = json.dumps(survival_data.to_dict())
                    
                    # Create summary
                    summary_children = self.create_data_summary_display(clinical_data, survival_data)
                    
                    return clinical_json, survival_json, summary_children
                    
                except Exception as e:
                    logger.error(f"Error loading mock data: {e}")
                    return "", "", html.Div(f"Error: {str(e)}", className="alert alert-danger")
            
            return "", "", html.Div("Click 'Load Mock Data' to begin", className="text-muted")
        
        @self.app.callback(
            [Output('clinical-analysis-results', 'children'),
             Output('survival-results', 'children')],
            [Input('run-survival-analysis', 'n_clicks')],
            [State('survival-data', 'children'),
             State('survival-group-col', 'value')]
        )
        def run_survival_analysis(n_clicks, survival_data_json, group_col):
            """Run survival analysis."""
            if n_clicks and survival_data_json:
                try:
                    # Load survival data
                    survival_dict = json.loads(survival_data_json)
                    survival_data = pd.DataFrame(survival_dict)
                    
                    # Set up analyzer
                    self.analyzer.survival_data = survival_data
                    
                    # Run survival analysis
                    results = self.analyzer.perform_survival_analysis(group_col=group_col)
                    
                    # Create results display
                    results_children = self.create_survival_results_display(results)
                    
                    # Store results
                    results_json = json.dumps(results, default=str)
                    
                    return results_json, results_children
                    
                except Exception as e:
                    logger.error(f"Error in survival analysis: {e}")
                    return "", html.Div(f"Error: {str(e)}", className="alert alert-danger")
            
            return "", html.Div("Click 'Run Survival Analysis' to begin", className="text-muted")
        
        @self.app.callback(
            [Output('correlation-heatmap', 'figure'),
             Output('correlation-results', 'children')],
            [Input('run-correlation', 'n_clicks')],
            [State('clinical-data', 'children'),
             State('correlation-method', 'value'),
             State('correlation-target', 'value')]
        )
        def run_correlation_analysis(n_clicks, clinical_data_json, method, target):
            """Run correlation analysis."""
            if n_clicks and clinical_data_json:
                try:
                    # Load clinical data
                    clinical_dict = json.loads(clinical_data_json)
                    clinical_data = pd.DataFrame(clinical_dict)
                    
                    # Set up analyzer
                    self.analyzer.clinical_data = clinical_data
                    
                    # Run correlation analysis
                    results = self.analyzer.perform_clinical_correlations(
                        target_col=target, method=method
                    )
                    
                    # Create heatmap
                    fig = self.analyzer.create_correlation_heatmap(method=method)
                    
                    # Create results display
                    results_children = self.create_correlation_results_display(results)
                    
                    return fig, results_children
                    
                except Exception as e:
                    logger.error(f"Error in correlation analysis: {e}")
                    return go.Figure(), html.Div(f"Error: {str(e)}", className="alert alert-danger")
            
            return go.Figure(), html.Div("Click 'Run Correlation Analysis' to begin", className="text-muted")
        
        @self.app.callback(
            Output('clinical-tab-content', 'children'),
            [Input('main-tabs', 'value')]
        )
        def render_tab_content(active_tab):
            """Render content based on active tab."""
            if active_tab == 'overview':
                return self.create_overview_tab()
            elif active_tab == 'survival':
                return self.create_survival_tab()
            elif active_tab == 'correlations':
                return self.create_correlations_tab()
            elif active_tab == 'associations':
                return self.create_associations_tab()
            elif active_tab == 'modeling':
                return self.create_modeling_tab()
            elif active_tab == 'visualizations':
                return self.create_visualizations_tab()
            else:
                return html.Div("Select a tab to view content")
        
        @self.app.callback(
            Output('survival-plot', 'figure'),
            [Input('survival-results', 'children')]
        )
        def update_survival_plot(survival_results_children):
            """Update survival plot based on analysis results."""
            if survival_results_children and self.analyzer.survival_data is not None:
                try:
                    fig = self.analyzer.create_survival_plot()
                    return fig
                except Exception as e:
                    logger.error(f"Error creating survival plot: {e}")
                    return go.Figure()
            
            return go.Figure()
        
        @self.app.callback(
            Output('clinical-overview-plot', 'figure'),
            [Input('clinical-data', 'children')]
        )
        def update_clinical_overview(clinical_data_json):
            """Update clinical overview plot."""
            if clinical_data_json:
                try:
                    # Load clinical data
                    clinical_dict = json.loads(clinical_data_json)
                    clinical_data = pd.DataFrame(clinical_dict)
                    
                    # Set up analyzer
                    self.analyzer.clinical_data = clinical_data
                    
                    fig = self.analyzer.create_clinical_overview_plot()
                    return fig
                except Exception as e:
                    logger.error(f"Error creating overview plot: {e}")
                    return go.Figure()
            
            return go.Figure()
    
    def create_data_summary_display(self, clinical_data: pd.DataFrame, 
                                  survival_data: pd.DataFrame) -> html.Div:
        """Create display for data summary."""
        cards = []
        
        # Clinical data summary
        clinical_metrics = [
            ('Patients', len(clinical_data), 'primary'),
            ('Features', len(clinical_data.columns), 'success'),
            ('Categorical', len(clinical_data.select_dtypes(include=['object', 'category']).columns), 'info'),
            ('Numerical', len(clinical_data.select_dtypes(include=[np.number]).columns), 'warning')
        ]
        
        for title, value, color in clinical_metrics:
            card = html.Div([
                html.Div([
                    html.H5(str(value), className="card-title"),
                    html.P(f"Clinical {title}", className="card-text")
                ], className="card-body text-center")
            ], className=f"card border-{color} mb-2")
            cards.append(html.Div(card, className="col-md-3"))
        
        # Survival data summary
        survival_metrics = [
            ('Patients', len(survival_data), 'primary'),
            ('Events', survival_data['death'].sum(), 'danger'),
            ('Median Survival', f"{survival_data['survival_time'].median():.1f} months", 'info'),
            ('Censoring Rate', f"{(1 - survival_data['death'].mean()) * 100:.1f}%", 'warning')
        ]
        
        for title, value, color in survival_metrics:
            card = html.Div([
                html.Div([
                    html.H5(str(value), className="card-title"),
                    html.P(f"Survival {title}", className="card-text")
                ], className="card-body text-center")
            ], className=f"card border-{color} mb-2")
            cards.append(html.Div(card, className="col-md-3"))
        
        return html.Div(cards, className="row")
    
    def create_survival_results_display(self, results: Dict[str, Any]) -> html.Div:
        """Create display for survival analysis results."""
        if 'logrank_test' in results:
            logrank = results['logrank_test']
            return html.Div([
                html.Div([
                    html.H5("Log-Rank Test Results"),
                    html.P(f"Test Statistic: {logrank['test_statistic']:.4f}"),
                    html.P(f"P-value: {logrank['p_value']:.4f}"),
                    html.P(f"Significant: {'Yes' if logrank['p_value'] < 0.05 else 'No'}")
                ], className="card-body")
            ], className="card")
        else:
            return html.Div([
                html.Div([
                    html.H5("Survival Analysis Results"),
                    html.P("Overall survival analysis completed successfully.")
                ], className="card-body")
            ], className="card")
    
    def create_correlation_results_display(self, results: Dict[str, Any]) -> html.Div:
        """Create display for correlation analysis results."""
        if 'target_correlations' in results:
            target_corr = results['target_correlations']
            return html.Div([
                html.Div([
                    html.H5(f"Correlations with {target_corr['target']}"),
                    html.P("Top Positive Correlations:"),
                    html.Ul([html.Li(f"{var}: {corr:.3f}") 
                            for var, corr in list(target_corr['top_positive'].items())[:5]]),
                    html.P("Top Negative Correlations:"),
                    html.Ul([html.Li(f"{var}: {corr:.3f}") 
                            for var, corr in list(target_corr['top_negative'].items())[:5]])
                ], className="card-body")
            ], className="card")
        else:
            return html.Div([
                html.Div([
                    html.H5("Correlation Analysis Results"),
                    html.P("Correlation matrix analysis completed successfully.")
                ], className="card-body")
            ], className="card")


def create_clinical_dashboard(app: dash.Dash) -> ClinicalDashboard:
    """
    Create and configure a clinical data analysis dashboard.
    
    Args:
        app: Dash application instance
        
    Returns:
        Configured ClinicalDashboard instance
    """
    dashboard = ClinicalDashboard(app)
    return dashboard


def main():
    """Main function for testing the dashboard."""
    app = dash.Dash(__name__)
    dashboard = create_clinical_dashboard(app)
    app.layout = dashboard.create_layout()
    
    if __name__ == "__main__":
        app.run_server(debug=True)


if __name__ == "__main__":
    main()
