"""
Interactive Dashboard for ML Outcome Prediction

This module provides a comprehensive dashboard for machine learning-based
cancer outcome prediction, including model training, validation, and visualization.
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import json
import base64
import io
import logging

from .ml_engine import (
    MLOutcomePredictor, SurvivalPredictor, DrugResponsePredictor, 
    TreatmentOutcomeClassifier, ModelTrainer, PredictionPipeline
)
from .outcome_utils import (
    DataPreprocessor, FeatureSelector, ModelValidator, 
    OutcomeMetrics, DataValidator, FeatureEngineering
)

logger = logging.getLogger(__name__)


class MLOutcomeDashboard:
    """
    Main dashboard class for ML outcome prediction.
    """
    
    def __init__(self, app: dash.Dash = None):
        """
        Initialize the ML outcome prediction dashboard.
        
        Args:
            app: Dash app instance (optional)
        """
        self.app = app or dash.Dash(__name__)
        self.data = None
        self.target = None
        self.models = {}
        self.preprocessor = DataPreprocessor()
        self.feature_selector = FeatureSelector()
        self.validator = ModelValidator()
        self.trainer = ModelTrainer()
        self.pipeline = PredictionPipeline()
        
        self._setup_layout()
        self._setup_callbacks()
    
    def _setup_layout(self):
        """Setup the dashboard layout."""
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1("ML Outcome Predictor Dashboard", className="header-title"),
                html.P("Machine Learning for Cancer Treatment Outcome Prediction", className="header-subtitle")
            ], className="header"),
            
            # Main content
            html.Div([
                # Sidebar
                html.Div([
                    # Data Upload Section
                    html.Div([
                        html.H3("Data Upload", className="section-title"),
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
                            multiple=False
                        ),
                        html.Div(id='upload-status')
                    ], className="upload-section"),
                    
                    # Model Configuration
                    html.Div([
                        html.H3("Model Configuration", className="section-title"),
                        
                        # Model Type Selection
                        html.Div([
                            html.Label("Model Type:"),
                            dcc.Dropdown(
                                id='model-type',
                                options=[
                                    {'label': 'Random Forest', 'value': 'random_forest'},
                                    {'label': 'Support Vector Machine', 'value': 'svm'},
                                    {'label': 'Logistic Regression', 'value': 'logistic'},
                                    {'label': 'Neural Network', 'value': 'neural_network'}
                                ],
                                value='random_forest'
                            )
                        ], className="config-item"),
                        
                        # Task Type Selection
                        html.Div([
                            html.Label("Task Type:"),
                            dcc.Dropdown(
                                id='task-type',
                                options=[
                                    {'label': 'Classification', 'value': 'classification'},
                                    {'label': 'Regression', 'value': 'regression'},
                                    {'label': 'Survival Analysis', 'value': 'survival'},
                                    {'label': 'Drug Response', 'value': 'drug_response'},
                                    {'label': 'Treatment Outcome', 'value': 'outcome_classification'}
                                ],
                                value='classification'
                            )
                        ], className="config-item"),
                        
                        # Feature Selection
                        html.Div([
                            html.Label("Feature Selection Method:"),
                            dcc.Dropdown(
                                id='feature-selection',
                                options=[
                                    {'label': 'None', 'value': 'none'},
                                    {'label': 'Mutual Information', 'value': 'mutual_info'},
                                    {'label': 'F-Score', 'value': 'f_score'},
                                    {'label': 'Random Forest', 'value': 'random_forest'},
                                    {'label': 'RFE', 'value': 'rfe'},
                                    {'label': 'Correlation', 'value': 'correlation'}
                                ],
                                value='none'
                            )
                        ], className="config-item"),
                        
                        # Number of Features
                        html.Div([
                            html.Label("Number of Features:"),
                            dcc.Input(
                                id='n-features',
                                type='number',
                                value=50,
                                min=1,
                                max=1000
                            )
                        ], className="config-item"),
                        
                        # Training Controls
                        html.Div([
                            html.Button('Train Model', id='train-button', className="train-button"),
                            html.Button('Validate Model', id='validate-button', className="validate-button"),
                            html.Button('Make Predictions', id='predict-button', className="predict-button")
                        ], className="button-group")
                        
                    ], className="config-section"),
                    
                    # Model Status
                    html.Div([
                        html.H3("Model Status", className="section-title"),
                        html.Div(id='model-status', className="status-display")
                    ], className="status-section")
                    
                ], className="sidebar"),
                
                # Main Content Area
                html.Div([
                    # Tabs
                    dcc.Tabs(id='main-tabs', value='data-tab', children=[
                        # Data Tab
                        dcc.Tab(label='Data Overview', value='data-tab', children=[
                            html.Div([
                                html.H3("Dataset Overview"),
                                html.Div(id='data-overview'),
                                html.H3("Data Quality Report"),
                                html.Div(id='data-quality'),
                                html.H3("Feature Distribution"),
                                dcc.Graph(id='feature-distribution')
                            ])
                        ]),
                        
                        # Training Tab
                        dcc.Tab(label='Model Training', value='training-tab', children=[
                            html.Div([
                                html.H3("Training Results"),
                                html.Div(id='training-results'),
                                html.H3("Model Performance"),
                                dcc.Graph(id='performance-metrics'),
                                html.H3("Feature Importance"),
                                dcc.Graph(id='feature-importance')
                            ])
                        ]),
                        
                        # Validation Tab
                        dcc.Tab(label='Model Validation', value='validation-tab', children=[
                            html.Div([
                                html.H3("Cross-Validation Results"),
                                html.Div(id='cv-results'),
                                html.H3("Learning Curves"),
                                dcc.Graph(id='learning-curves'),
                                html.H3("Confusion Matrix"),
                                dcc.Graph(id='confusion-matrix')
                            ])
                        ]),
                        
                        # Prediction Tab
                        dcc.Tab(label='Predictions', value='prediction-tab', children=[
                            html.Div([
                                html.H3("Make Predictions"),
                                html.Div([
                                    html.Label("Upload prediction data:"),
                                    dcc.Upload(
                                        id='upload-prediction-data',
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
                                        }
                                    )
                                ]),
                                html.Div(id='prediction-results'),
                                html.H3("Prediction Visualization"),
                                dcc.Graph(id='prediction-visualization')
                            ])
                        ])
                    ])
                ], className="main-content")
            ], className="main-container")
        ])
    
    def _setup_callbacks(self):
        """Setup dashboard callbacks."""
        
        # Data upload callback
        @self.app.callback(
            [Output('upload-status', 'children'),
             Output('data-overview', 'children'),
             Output('data-quality', 'children')],
            [Input('upload-data', 'contents')],
            [State('upload-data', 'filename')]
        )
        def handle_data_upload(contents, filename):
            if contents is None:
                return "", "", ""
            
            try:
                # Parse uploaded file
                content_type, content_string = contents.split(',')
                decoded = base64.b64decode(content_string)
                
                if filename.endswith('.csv'):
                    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
                elif filename.endswith('.xlsx'):
                    df = pd.read_excel(io.BytesIO(decoded))
                else:
                    return "Unsupported file format", "", ""
                
                # Store data
                self.data = df
                
                # Generate overview
                overview = self._generate_data_overview(df)
                
                # Generate quality report
                quality_report = self._generate_quality_report(df)
                
                return f"Successfully loaded {filename} with {len(df)} rows and {len(df.columns)} columns", overview, quality_report
                
            except Exception as e:
                return f"Error loading file: {str(e)}", "", ""
        
        # Model training callback
        @self.app.callback(
            [Output('training-results', 'children'),
             Output('performance-metrics', 'figure'),
             Output('feature-importance', 'figure'),
             Output('model-status', 'children')],
            [Input('train-button', 'n_clicks')],
            [State('model-type', 'value'),
             State('task-type', 'value'),
             State('feature-selection', 'value'),
             State('n-features', 'value')]
        )
        def train_model(n_clicks, model_type, task_type, feature_selection, n_features):
            if n_clicks is None or self.data is None:
                return "", {}, {}, "No data loaded"
            
            try:
                # Prepare data
                X = self.data.select_dtypes(include=[np.number])
                y = self.data.iloc[:, -1]  # Assume last column is target
                
                # Feature selection
                if feature_selection != 'none':
                    X = self.feature_selector.select_features(X, y, feature_selection, n_features, task_type)
                
                # Initialize and train model
                if task_type == 'survival':
                    model = SurvivalPredictor()
                    # For demo, use first column as duration, second as event
                    duration = X.iloc[:, 0] if len(X.columns) > 0 else pd.Series([1] * len(X))
                    event = pd.Series([1] * len(X))  # Dummy event data
                    result = model.train(X, duration, event)
                elif task_type == 'drug_response':
                    model = DrugResponsePredictor(model_type)
                    result = model.train_drug_response(X, y)
                elif task_type == 'outcome_classification':
                    model = TreatmentOutcomeClassifier(model_type)
                    result = model.train_outcome_classification(X, y)
                else:
                    model = MLOutcomePredictor(model_type)
                    result = model.train(X, y, task_type)
                
                # Store model
                self.models[task_type] = model
                
                # Generate results display
                results_display = self._generate_training_results(result)
                
                # Generate performance metrics plot
                metrics_fig = self._generate_metrics_plot(result)
                
                # Generate feature importance plot
                importance_fig = self._generate_importance_plot(model, X.columns)
                
                status = f"Model trained successfully - {model_type} for {task_type}"
                
                return results_display, metrics_fig, importance_fig, status
                
            except Exception as e:
                return f"Training error: {str(e)}", {}, {}, f"Error: {str(e)}"
        
        # Model validation callback
        @self.app.callback(
            [Output('cv-results', 'children'),
             Output('learning-curves', 'figure'),
             Output('confusion-matrix', 'figure')],
            [Input('validate-button', 'n_clicks')],
            [State('task-type', 'value')]
        )
        def validate_model(n_clicks, task_type):
            if n_clicks is None or task_type not in self.models:
                return "", {}, {}
            
            try:
                model = self.models[task_type]
                X = self.data.select_dtypes(include=[np.number])
                y = self.data.iloc[:, -1]
                
                # Cross-validation
                cv_result = self.validator.cross_validate_model(model, X, y, task_type=task_type)
                
                # Learning curves
                lc_result = self.validator.learning_curve_analysis(model, X, y, task_type=task_type)
                
                # Generate displays
                cv_display = self._generate_cv_results(cv_result)
                lc_fig = self._generate_learning_curve_plot(lc_result)
                cm_fig = self._generate_confusion_matrix_plot(model, X, y)
                
                return cv_display, lc_fig, cm_fig
                
            except Exception as e:
                return f"Validation error: {str(e)}", {}, {}
        
        # Prediction callback
        @self.app.callback(
            [Output('prediction-results', 'children'),
             Output('prediction-visualization', 'figure')],
            [Input('predict-button', 'n_clicks'),
             Input('upload-prediction-data', 'contents')],
            [State('upload-prediction-data', 'filename'),
             State('task-type', 'value')]
        )
        def make_predictions(n_clicks, contents, filename, task_type):
            if (n_clicks is None and contents is None) or task_type not in self.models:
                return "", {}
            
            try:
                model = self.models[task_type]
                
                # Use uploaded data or original data for prediction
                if contents is not None:
                    content_type, content_string = contents.split(',')
                    decoded = base64.b64decode(content_string)
                    
                    if filename.endswith('.csv'):
                        pred_data = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
                    else:
                        pred_data = self.data.select_dtypes(include=[np.number])
                else:
                    pred_data = self.data.select_dtypes(include=[np.number])
                
                # Make predictions
                if task_type == 'survival':
                    predictions = model.predict_survival(pred_data)
                    pred_results = {
                        "predictions": predictions.tolist(),
                        "model_type": "survival"
                    }
                elif task_type == 'drug_response':
                    pred_results = model.predict_drug_response(pred_data)
                elif task_type == 'outcome_classification':
                    pred_results = model.predict_outcome_with_confidence(pred_data)
                else:
                    predictions = model.predict(pred_data)
                    pred_results = {
                        "predictions": predictions.tolist(),
                        "model_type": model.model_type
                    }
                
                # Generate results display
                results_display = self._generate_prediction_results(pred_results)
                
                # Generate visualization
                viz_fig = self._generate_prediction_visualization(pred_results, pred_data)
                
                return results_display, viz_fig
                
            except Exception as e:
                return f"Prediction error: {str(e)}", {}
        
        # Feature distribution callback
        @self.app.callback(
            Output('feature-distribution', 'figure'),
            [Input('upload-data', 'contents')]
        )
        def update_feature_distribution(contents):
            if contents is None or self.data is None:
                return {}
            
            try:
                # Select numeric columns for distribution plot
                numeric_cols = self.data.select_dtypes(include=[np.number]).columns[:10]  # Limit to 10 columns
                
                if len(numeric_cols) == 0:
                    return {}
                
                # Create subplots
                from plotly.subplots import make_subplots
                fig = make_subplots(
                    rows=2, cols=5,
                    subplot_titles=numeric_cols.tolist(),
                    vertical_spacing=0.1
                )
                
                for i, col in enumerate(numeric_cols):
                    row = (i // 5) + 1
                    col_idx = (i % 5) + 1
                    
                    fig.add_trace(
                        go.Histogram(x=self.data[col], name=col, showlegend=False),
                        row=row, col=col_idx
                    )
                
                fig.update_layout(
                    title="Feature Distributions",
                    height=600,
                    showlegend=False
                )
                
                return fig
                
            except Exception as e:
                return {}
    
    def _generate_data_overview(self, df: pd.DataFrame) -> html.Div:
        """Generate data overview display."""
        overview_data = {
            'Dataset Shape': f"{df.shape[0]} rows × {df.shape[1]} columns",
            'Memory Usage': f"{df.memory_usage(deep=True).sum() / 1024**2:.2f} MB",
            'Missing Values': f"{df.isnull().sum().sum()} total",
            'Duplicate Rows': f"{df.duplicated().sum()}",
            'Data Types': df.dtypes.value_counts().to_dict()
        }
        
        return html.Div([
            html.Div([
                html.Strong(f"{key}:"),
                html.Span(f" {value}")
            ], className="overview-item") for key, value in overview_data.items()
        ])
    
    def _generate_quality_report(self, df: pd.DataFrame) -> html.Div:
        """Generate data quality report."""
        validator = DataValidator()
        quality_report = validator.validate_dataset(df)
        
        return html.Div([
            html.H4("Quality Assessment"),
            html.Div([
                html.Strong("Status: "),
                html.Span(quality_report['status'], className="status-success" if quality_report['status'] == 'success' else "status-error")
            ]),
            html.H5("Warnings:"),
            html.Ul([html.Li(warning) for warning in quality_report['warnings']]) if quality_report['warnings'] else html.P("No warnings"),
            html.H5("Dataset Info:"),
            html.Pre(json.dumps(quality_report['dataset_info'], indent=2))
        ])
    
    def _generate_training_results(self, result: Dict[str, Any]) -> html.Div:
        """Generate training results display."""
        if result['status'] == 'error':
            return html.Div([
                html.H4("Training Failed"),
                html.P(f"Error: {result['error']}")
            ], className="error-message")
        
        metrics = result.get('metrics', {})
        
        return html.Div([
            html.H4("Training Results"),
            html.Div([
                html.Strong("Model Type: "),
                html.Span(result.get('model_type', 'Unknown'))
            ]),
            html.Div([
                html.Strong("Task Type: "),
                html.Span(result.get('task_type', 'Unknown'))
            ]),
            html.Div([
                html.Strong("Feature Count: "),
                html.Span(str(result.get('feature_count', 0)))
            ]),
            html.Div([
                html.Strong("Training Samples: "),
                html.Span(str(result.get('training_samples', 0)))
            ]),
            html.Div([
                html.Strong("Test Samples: "),
                html.Span(str(result.get('test_samples', 0)))
            ]),
            html.H5("Performance Metrics:"),
            html.Div([
                html.Div([
                    html.Strong(f"{metric.replace('_', ' ').title()}: "),
                    html.Span(f"{value:.4f}")
                ], className="metric-item") for metric, value in metrics.items()
            ])
        ])
    
    def _generate_metrics_plot(self, result: Dict[str, Any]) -> go.Figure:
        """Generate performance metrics plot."""
        metrics = result.get('metrics', {})
        
        if not metrics:
            return {}
        
        fig = go.Figure(data=[
            go.Bar(
                x=list(metrics.keys()),
                y=list(metrics.values()),
                marker_color='lightblue'
            )
        ])
        
        fig.update_layout(
            title="Model Performance Metrics",
            xaxis_title="Metrics",
            yaxis_title="Score",
            height=400
        )
        
        return fig
    
    def _generate_importance_plot(self, model, feature_names) -> go.Figure:
        """Generate feature importance plot."""
        try:
            if hasattr(model, 'model') and hasattr(model.model, 'feature_importances_'):
                importances = model.model.feature_importances_
                
                # Sort features by importance
                indices = np.argsort(importances)[::-1][:20]  # Top 20 features
                
                fig = go.Figure(data=[
                    go.Bar(
                        x=[feature_names[i] for i in indices],
                        y=importances[indices],
                        marker_color='lightgreen'
                    )
                ])
                
                fig.update_layout(
                    title="Top 20 Feature Importances",
                    xaxis_title="Features",
                    yaxis_title="Importance",
                    height=400,
                    xaxis={'tickangle': 45}
                )
                
                return fig
        except:
            pass
        
        return {}
    
    def _generate_cv_results(self, cv_result: Dict[str, Any]) -> html.Div:
        """Generate cross-validation results display."""
        if cv_result['status'] == 'error':
            return html.Div([
                html.H4("Cross-Validation Failed"),
                html.P(f"Error: {cv_result['error']}")
            ], className="error-message")
        
        cv_scores = cv_result.get('cv_scores', {})
        
        return html.Div([
            html.H4("Cross-Validation Results"),
            html.Div([
                html.Div([
                    html.Strong(f"{score.replace('_', ' ').title()}: "),
                    html.Span(f"{data['mean']:.4f} ± {data['std']:.4f}")
                ], className="cv-metric") for score, data in cv_scores.items()
            ])
        ])
    
    def _generate_learning_curve_plot(self, lc_result: Dict[str, Any]) -> go.Figure:
        """Generate learning curve plot."""
        if lc_result['status'] == 'error':
            return {}
        
        fig = go.Figure()
        
        # Training scores
        fig.add_trace(go.Scatter(
            x=lc_result['train_sizes'],
            y=lc_result['train_scores_mean'],
            mode='lines+markers',
            name='Training Score',
            line=dict(color='blue')
        ))
        
        # Validation scores
        fig.add_trace(go.Scatter(
            x=lc_result['train_sizes'],
            y=lc_result['val_scores_mean'],
            mode='lines+markers',
            name='Validation Score',
            line=dict(color='red')
        ))
        
        fig.update_layout(
            title="Learning Curves",
            xaxis_title="Training Set Size",
            yaxis_title="Score",
            height=400
        )
        
        return fig
    
    def _generate_confusion_matrix_plot(self, model, X, y) -> go.Figure:
        """Generate confusion matrix plot."""
        try:
            from sklearn.model_selection import train_test_split
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            y_pred = model.predict(X_test)
            
            from sklearn.metrics import confusion_matrix
            cm = confusion_matrix(y_test, y_pred)
            
            fig = go.Figure(data=go.Heatmap(
                z=cm,
                colorscale='Blues',
                showscale=True
            ))
            
            fig.update_layout(
                title="Confusion Matrix",
                xaxis_title="Predicted",
                yaxis_title="Actual",
                height=400
            )
            
            return fig
        except:
            return {}
    
    def _generate_prediction_results(self, pred_results: Dict[str, Any]) -> html.Div:
        """Generate prediction results display."""
        if 'error' in pred_results:
            return html.Div([
                html.H4("Prediction Failed"),
                html.P(f"Error: {pred_results['error']}")
            ], className="error-message")
        
        return html.Div([
            html.H4("Prediction Results"),
            html.Div([
                html.Strong("Model Type: "),
                html.Span(pred_results.get('model_type', 'Unknown'))
            ]),
            html.Div([
                html.Strong("Number of Predictions: "),
                html.Span(str(len(pred_results.get('predictions', []))))
            ]),
            html.H5("Sample Predictions:"),
            html.Pre(json.dumps(pred_results.get('predictions', [])[:10], indent=2))
        ])
    
    def _generate_prediction_visualization(self, pred_results: Dict[str, Any], pred_data: pd.DataFrame) -> go.Figure:
        """Generate prediction visualization."""
        predictions = pred_results.get('predictions', [])
        
        if not predictions:
            return {}
        
        # Create histogram of predictions
        fig = go.Figure(data=[
            go.Histogram(
                x=predictions,
                nbinsx=20,
                marker_color='lightcoral'
            )
        ])
        
        fig.update_layout(
            title="Prediction Distribution",
            xaxis_title="Predicted Values",
            yaxis_title="Frequency",
            height=400
        )
        
        return fig


def create_ml_dashboard(app: dash.Dash = None) -> MLOutcomeDashboard:
    """
    Create and return an ML outcome prediction dashboard.
    
    Args:
        app: Dash app instance (optional)
        
    Returns:
        MLOutcomeDashboard instance
    """
    return MLOutcomeDashboard(app)


def register_ml_routes(app: dash.Dash, url_prefix: str = "/ml-outcome"):
    """
    Register ML outcome prediction routes with the main app.
    
    Args:
        app: Main Dash app instance
        url_prefix: URL prefix for ML routes
    """
    # Create ML dashboard
    ml_dashboard = create_ml_dashboard(app)
    
    # Register routes
    @app.callback(
        Output('ml-outcome-content', 'children'),
        [Input('ml-outcome-tab', 'n_clicks')]
    )
    def display_ml_outcome(n_clicks):
        if n_clicks:
            return ml_dashboard.app.layout
    
    logger.info(f"ML outcome prediction routes registered at {url_prefix}")


# CSS Styles for the dashboard
dashboard_styles = """
.header {
    background-color: #2c3e50;
    color: white;
    padding: 20px;
    text-align: center;
    margin-bottom: 20px;
}

.header-title {
    margin: 0;
    font-size: 2.5em;
}

.header-subtitle {
    margin: 10px 0 0 0;
    font-size: 1.2em;
    opacity: 0.8;
}

.main-container {
    display: flex;
    min-height: 800px;
}

.sidebar {
    width: 300px;
    background-color: #f8f9fa;
    padding: 20px;
    border-right: 1px solid #dee2e6;
}

.main-content {
    flex: 1;
    padding: 20px;
}

.section-title {
    color: #2c3e50;
    border-bottom: 2px solid #3498db;
    padding-bottom: 10px;
    margin-bottom: 20px;
}

.config-item {
    margin-bottom: 15px;
}

.config-item label {
    display: block;
    margin-bottom: 5px;
    font-weight: bold;
    color: #2c3e50;
}

.button-group {
    margin-top: 20px;
}

.train-button, .validate-button, .predict-button {
    background-color: #3498db;
    color: white;
    border: none;
    padding: 10px 20px;
    margin: 5px;
    border-radius: 5px;
    cursor: pointer;
    font-size: 14px;
}

.train-button:hover, .validate-button:hover, .predict-button:hover {
    background-color: #2980b9;
}

.status-display {
    background-color: #e8f5e8;
    border: 1px solid #4caf50;
    padding: 10px;
    border-radius: 5px;
    margin-top: 10px;
}

.overview-item {
    margin-bottom: 10px;
    padding: 5px;
    background-color: #f8f9fa;
    border-radius: 3px;
}

.metric-item {
    margin-bottom: 5px;
    padding: 3px;
}

.cv-metric {
    margin-bottom: 5px;
    padding: 3px;
}

.error-message {
    background-color: #f8d7da;
    color: #721c24;
    padding: 10px;
    border-radius: 5px;
    border: 1px solid #f5c6cb;
}

.status-success {
    color: #28a745;
    font-weight: bold;
}

.status-error {
    color: #dc3545;
    font-weight: bold;
}
"""

# Add styles to the app
if __name__ == "__main__":
    app = dash.Dash(__name__)
    app.index_string = f"""
    <!DOCTYPE html>
    <html>
        <head>
            {{%metas%}}
            <title>{{%title%}}</title>
            {{%favicon%}}
            {{%css%}}
            <style>{dashboard_styles}</style>
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
    
    dashboard = create_ml_dashboard(app)
    app.run_server(debug=True)
