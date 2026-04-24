"""
Report Dashboard Module

Provides interactive dashboard functionality for reporting in the Cancer Genomics Analysis Suite.
Supports real-time report generation, filtering, and visualization of analysis results.
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path
import json
import uuid
from datetime import datetime, timedelta
import base64
import io

logger = logging.getLogger(__name__)


class ReportWidgetType(Enum):
    """Types of report widgets."""
    SUMMARY = "summary"
    CHART = "chart"
    TABLE = "table"
    METRIC = "metric"
    FILTER = "filter"
    TIMELINE = "timeline"
    PROGRESS = "progress"
    ALERT = "alert"
    EXPORT = "export"
    COMPARISON = "comparison"


class ReportFilterType(Enum):
    """Types of report filters."""
    DATE_RANGE = "date_range"
    CATEGORY = "category"
    NUMERIC_RANGE = "numeric_range"
    MULTI_SELECT = "multi_select"
    TEXT_SEARCH = "text_search"
    BOOLEAN = "boolean"


@dataclass
class ReportFilter:
    """Represents a report filter."""
    id: str
    name: str
    filter_type: ReportFilterType
    options: List[Any] = field(default_factory=list)
    default_value: Any = None
    required: bool = False
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert filter to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'filter_type': self.filter_type.value,
            'options': self.options,
            'default_value': self.default_value,
            'required': self.required,
            'description': self.description,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReportFilter':
        """Create filter from dictionary."""
        data['filter_type'] = ReportFilterType(data['filter_type'])
        return cls(**data)


@dataclass
class ReportWidget:
    """Represents a report widget."""
    id: str
    widget_type: ReportWidgetType
    title: str
    data_source: str
    config: Dict[str, Any] = field(default_factory=dict)
    position: Tuple[int, int] = (0, 0)
    size: Tuple[int, int] = (1, 1)
    visible: bool = True
    refresh_interval: int = 0  # seconds, 0 for no auto-refresh
    filters: List[str] = field(default_factory=list)  # Filter IDs
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert widget to dictionary."""
        return {
            'id': self.id,
            'widget_type': self.widget_type.value,
            'title': self.title,
            'data_source': self.data_source,
            'config': self.config,
            'position': self.position,
            'size': self.size,
            'visible': self.visible,
            'refresh_interval': self.refresh_interval,
            'filters': self.filters,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReportWidget':
        """Create widget from dictionary."""
        data['widget_type'] = ReportWidgetType(data['widget_type'])
        return cls(**data)


class ReportDashboard:
    """
    Interactive dashboard for report generation and visualization.
    
    Features:
    - Real-time report generation
    - Interactive filtering and selection
    - Multiple widget types for different data views
    - Export functionality
    - Customizable layouts
    - Data source integration
    - Automated refresh capabilities
    """
    
    def __init__(self, app_name: str = "ReportDashboard"):
        """
        Initialize ReportDashboard.
        
        Args:
            app_name: Name of the Dash application
        """
        self.app_name = app_name
        self.app = dash.Dash(__name__)
        self.widgets = {}
        self.filters = {}
        self.data_sources = {}
        self.report_templates = {}
        self.callbacks_registered = set()
        
        # Configure app
        self.app.config.suppress_callback_exceptions = True
        
        # Set up default layout
        self._setup_default_layout()
    
    def _setup_default_layout(self):
        """Set up default dashboard layout."""
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1("Cancer Genomics Report Dashboard", className="dashboard-title"),
                html.Div([
                    html.Button("Generate Report", id="generate-report-btn", className="btn btn-primary"),
                    html.Button("Export Data", id="export-data-btn", className="btn btn-secondary"),
                    dcc.Download(id="download-data")
                ], className="header-buttons")
            ], className="dashboard-header"),
            
            # Filters section
            html.Div(id="filters-section", className="filters-section"),
            
            # Main content area
            html.Div(id="main-content", className="main-content"),
            
            # Status bar
            html.Div(id="status-bar", className="status-bar"),
            
            # Hidden divs for callbacks
            html.Div(id="hidden-div", style={"display": "none"}),
            dcc.Store(id="filter-store", data={}),
            dcc.Store(id="data-store", data={})
        ], className="dashboard-container")
        
        # Register default callbacks
        self._register_default_callbacks()
    
    def _register_default_callbacks(self):
        """Register default dashboard callbacks."""
        @self.app.callback(
            [Output("filters-section", "children"),
             Output("main-content", "children")],
            [Input("filter-store", "data")],
            prevent_initial_call=False
        )
        def update_dashboard(filter_data):
            """Update dashboard based on filter data."""
            filters_ui = self._create_filters_ui()
            content_ui = self._create_content_ui(filter_data)
            return filters_ui, content_ui
        
        @self.app.callback(
            Output("download-data", "data"),
            [Input("export-data-btn", "n_clicks")],
            [State("data-store", "data")],
            prevent_initial_call=True
        )
        def export_data(n_clicks, data_store):
            """Export dashboard data."""
            if n_clicks and data_store:
                # Create CSV from data store
                df = pd.DataFrame(data_store.get('data', []))
                csv_string = df.to_csv(index=False)
                return dict(content=csv_string, filename=f"report_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            return None
    
    def add_filter(self, filter_obj: ReportFilter):
        """
        Add a filter to the dashboard.
        
        Args:
            filter_obj: Filter object to add
        """
        self.filters[filter_obj.id] = filter_obj
        logger.info(f"Added filter: {filter_obj.name}")
    
    def add_widget(self, widget: ReportWidget):
        """
        Add a widget to the dashboard.
        
        Args:
            widget: Widget object to add
        """
        self.widgets[widget.id] = widget
        logger.info(f"Added widget: {widget.title}")
    
    def add_data_source(self, source_id: str, data: Any, refresh_func: Callable = None):
        """
        Add a data source for widgets.
        
        Args:
            source_id: Unique identifier for data source
            data: Data object
            refresh_func: Function to refresh data
        """
        self.data_sources[source_id] = {
            'data': data,
            'refresh_func': refresh_func,
            'last_updated': datetime.now()
        }
        logger.info(f"Added data source: {source_id}")
    
    def _create_filters_ui(self) -> html.Div:
        """Create filters user interface."""
        if not self.filters:
            return html.Div()
        
        filter_components = []
        
        for filter_id, filter_obj in self.filters.items():
            if filter_obj.filter_type == ReportFilterType.DATE_RANGE:
                component = dcc.DatePickerRange(
                    id=f"filter-{filter_id}",
                    start_date=filter_obj.default_value.get('start') if isinstance(filter_obj.default_value, dict) else None,
                    end_date=filter_obj.default_value.get('end') if isinstance(filter_obj.default_value, dict) else None,
                    display_format='YYYY-MM-DD'
                )
            elif filter_obj.filter_type == ReportFilterType.CATEGORY:
                component = dcc.Dropdown(
                    id=f"filter-{filter_id}",
                    options=[{'label': opt, 'value': opt} for opt in filter_obj.options],
                    value=filter_obj.default_value,
                    placeholder=f"Select {filter_obj.name}"
                )
            elif filter_obj.filter_type == ReportFilterType.NUMERIC_RANGE:
                component = dcc.RangeSlider(
                    id=f"filter-{filter_id}",
                    min=min(filter_obj.options) if filter_obj.options else 0,
                    max=max(filter_obj.options) if filter_obj.options else 100,
                    value=filter_obj.default_value or [min(filter_obj.options) if filter_obj.options else 0, 
                                                      max(filter_obj.options) if filter_obj.options else 100],
                    marks={i: str(i) for i in filter_obj.options[::len(filter_obj.options)//10] if filter_obj.options}
                )
            elif filter_obj.filter_type == ReportFilterType.MULTI_SELECT:
                component = dcc.Dropdown(
                    id=f"filter-{filter_id}",
                    options=[{'label': opt, 'value': opt} for opt in filter_obj.options],
                    value=filter_obj.default_value or [],
                    multi=True,
                    placeholder=f"Select {filter_obj.name}"
                )
            elif filter_obj.filter_type == ReportFilterType.TEXT_SEARCH:
                component = dcc.Input(
                    id=f"filter-{filter_id}",
                    type="text",
                    placeholder=f"Search {filter_obj.name}",
                    value=filter_obj.default_value or ""
                )
            elif filter_obj.filter_type == ReportFilterType.BOOLEAN:
                component = dcc.RadioItems(
                    id=f"filter-{filter_id}",
                    options=[
                        {'label': 'Yes', 'value': True},
                        {'label': 'No', 'value': False}
                    ],
                    value=filter_obj.default_value
                )
            else:
                component = html.Div(f"Unsupported filter type: {filter_obj.filter_type}")
            
            filter_components.append(
                html.Div([
                    html.Label(filter_obj.name, className="filter-label"),
                    component,
                    html.P(filter_obj.description, className="filter-description") if filter_obj.description else None
                ], className="filter-item")
            )
        
        return html.Div([
            html.H3("Filters", className="filters-title"),
            html.Div(filter_components, className="filters-grid")
        ], className="filters-container")
    
    def _create_content_ui(self, filter_data: Dict[str, Any]) -> html.Div:
        """Create main content user interface."""
        if not self.widgets:
            return html.Div("No widgets configured", className="no-widgets")
        
        widget_components = []
        
        for widget_id, widget in self.widgets.items():
            if not widget.visible:
                continue
            
            widget_content = self._create_widget_content(widget, filter_data)
            widget_components.append(
                html.Div([
                    html.H4(widget.title, className="widget-title"),
                    widget_content
                ], className=f"widget widget-{widget.widget_type.value}", id=f"widget-{widget_id}")
            )
        
        return html.Div(widget_components, className="widgets-grid")
    
    def _create_widget_content(self, widget: ReportWidget, filter_data: Dict[str, Any]) -> html.Div:
        """Create content for a specific widget."""
        # Get filtered data
        data = self._get_filtered_data(widget.data_source, filter_data, widget.filters)
        
        if widget.widget_type == ReportWidgetType.SUMMARY:
            return self._create_summary_widget(data, widget.config)
        elif widget.widget_type == ReportWidgetType.CHART:
            return self._create_chart_widget(data, widget.config)
        elif widget.widget_type == ReportWidgetType.TABLE:
            return self._create_table_widget(data, widget.config)
        elif widget.widget_type == ReportWidgetType.METRIC:
            return self._create_metric_widget(data, widget.config)
        elif widget.widget_type == ReportWidgetType.TIMELINE:
            return self._create_timeline_widget(data, widget.config)
        elif widget.widget_type == ReportWidgetType.PROGRESS:
            return self._create_progress_widget(data, widget.config)
        elif widget.widget_type == ReportWidgetType.ALERT:
            return self._create_alert_widget(data, widget.config)
        elif widget.widget_type == ReportWidgetType.EXPORT:
            return self._create_export_widget(data, widget.config)
        elif widget.widget_type == ReportWidgetType.COMPARISON:
            return self._create_comparison_widget(data, widget.config)
        else:
            return html.Div(f"Unsupported widget type: {widget.widget_type}")
    
    def _get_filtered_data(self, data_source: str, filter_data: Dict[str, Any], 
                          widget_filters: List[str]) -> Any:
        """Get filtered data for a widget."""
        if data_source not in self.data_sources:
            return None
        
        data = self.data_sources[data_source]['data']
        
        # Apply filters
        if isinstance(data, pd.DataFrame):
            filtered_data = data.copy()
            
            for filter_id in widget_filters:
                if filter_id in filter_data and filter_data[filter_id] is not None:
                    filter_obj = self.filters.get(filter_id)
                    if filter_obj:
                        if filter_obj.filter_type == ReportFilterType.DATE_RANGE:
                            if 'start' in filter_data[filter_id] and 'end' in filter_data[filter_id]:
                                date_col = filter_obj.metadata.get('date_column', 'date')
                                if date_col in filtered_data.columns:
                                    filtered_data = filtered_data[
                                        (filtered_data[date_col] >= filter_data[filter_id]['start']) &
                                        (filtered_data[date_col] <= filter_data[filter_id]['end'])
                                    ]
                        elif filter_obj.filter_type == ReportFilterType.CATEGORY:
                            category_col = filter_obj.metadata.get('category_column', filter_id)
                            if category_col in filtered_data.columns:
                                filtered_data = filtered_data[
                                    filtered_data[category_col] == filter_data[filter_id]
                                ]
                        elif filter_obj.filter_type == ReportFilterType.NUMERIC_RANGE:
                            numeric_col = filter_obj.metadata.get('numeric_column', filter_id)
                            if numeric_col in filtered_data.columns:
                                filtered_data = filtered_data[
                                    (filtered_data[numeric_col] >= filter_data[filter_id][0]) &
                                    (filtered_data[numeric_col] <= filter_data[filter_id][1])
                                ]
                        elif filter_obj.filter_type == ReportFilterType.MULTI_SELECT:
                            category_col = filter_obj.metadata.get('category_column', filter_id)
                            if category_col in filtered_data.columns:
                                filtered_data = filtered_data[
                                    filtered_data[category_col].isin(filter_data[filter_id])
                                ]
                        elif filter_obj.filter_type == ReportFilterType.TEXT_SEARCH:
                            text_col = filter_obj.metadata.get('text_column', filter_id)
                            if text_col in filtered_data.columns:
                                filtered_data = filtered_data[
                                    filtered_data[text_col].str.contains(
                                        filter_data[filter_id], case=False, na=False
                                    )
                                ]
                        elif filter_obj.filter_type == ReportFilterType.BOOLEAN:
                            bool_col = filter_obj.metadata.get('boolean_column', filter_id)
                            if bool_col in filtered_data.columns:
                                filtered_data = filtered_data[
                                    filtered_data[bool_col] == filter_data[filter_id]
                                ]
            
            return filtered_data
        
        return data
    
    def _create_summary_widget(self, data: Any, config: Dict[str, Any]) -> html.Div:
        """Create summary widget."""
        if isinstance(data, pd.DataFrame):
            summary_stats = {
                'Total Records': len(data),
                'Columns': len(data.columns),
                'Missing Values': data.isnull().sum().sum(),
                'Memory Usage': f"{data.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB"
            }
            
            return html.Div([
                html.Div([
                    html.H5(key, className="summary-label"),
                    html.P(str(value), className="summary-value")
                ], className="summary-item") for key, value in summary_stats.items()
            ], className="summary-widget")
        else:
            return html.Div("No data available", className="no-data")
    
    def _create_chart_widget(self, data: Any, config: Dict[str, Any]) -> html.Div:
        """Create chart widget."""
        if isinstance(data, pd.DataFrame) and not data.empty:
            chart_type = config.get('chart_type', 'bar')
            x_col = config.get('x_column', data.columns[0])
            y_col = config.get('y_column', data.columns[1])
            
            if chart_type == 'bar':
                fig = px.bar(data, x=x_col, y=y_col, title=config.get('title', ''))
            elif chart_type == 'line':
                fig = px.line(data, x=x_col, y=y_col, title=config.get('title', ''))
            elif chart_type == 'scatter':
                fig = px.scatter(data, x=x_col, y=y_col, title=config.get('title', ''))
            elif chart_type == 'pie':
                fig = px.pie(data, names=x_col, values=y_col, title=config.get('title', ''))
            else:
                fig = px.bar(data, x=x_col, y=y_col, title=config.get('title', ''))
            
            return dcc.Graph(figure=fig, config={'displayModeBar': True})
        else:
            return html.Div("No data available for chart", className="no-data")
    
    def _create_table_widget(self, data: Any, config: Dict[str, Any]) -> html.Div:
        """Create table widget."""
        if isinstance(data, pd.DataFrame) and not data.empty:
            max_rows = config.get('max_rows', 100)
            display_data = data.head(max_rows)
            
            return html.Div([
                html.Table([
                    html.Thead([
                        html.Tr([html.Th(col) for col in display_data.columns])
                    ]),
                    html.Tbody([
                        html.Tr([
                            html.Td(str(display_data.iloc[i][col])) 
                            for col in display_data.columns
                        ]) for i in range(len(display_data))
                    ])
                ], className="data-table"),
                html.P(f"Showing {len(display_data)} of {len(data)} rows", className="table-info")
            ])
        else:
            return html.Div("No data available for table", className="no-data")
    
    def _create_metric_widget(self, data: Any, config: Dict[str, Any]) -> html.Div:
        """Create metric widget."""
        if isinstance(data, pd.DataFrame) and not data.empty:
            metric_col = config.get('metric_column', data.columns[0])
            metric_value = data[metric_col].sum() if data[metric_col].dtype in ['int64', 'float64'] else len(data)
            metric_label = config.get('metric_label', metric_col)
            
            return html.Div([
                html.H2(str(metric_value), className="metric-value"),
                html.P(metric_label, className="metric-label")
            ], className="metric-widget")
        else:
            return html.Div("No data available", className="no-data")
    
    def _create_timeline_widget(self, data: Any, config: Dict[str, Any]) -> html.Div:
        """Create timeline widget."""
        if isinstance(data, pd.DataFrame) and not data.empty:
            date_col = config.get('date_column', 'date')
            event_col = config.get('event_column', 'event')
            
            if date_col in data.columns:
                # Create timeline chart
                fig = go.Figure()
                
                for event in data[event_col].unique() if event_col in data.columns else ['Event']:
                    event_data = data[data[event_col] == event] if event_col in data.columns else data
                    fig.add_trace(go.Scatter(
                        x=event_data[date_col],
                        y=[event] * len(event_data),
                        mode='markers',
                        name=event,
                        marker=dict(size=10)
                    ))
                
                fig.update_layout(
                    title=config.get('title', 'Timeline'),
                    xaxis_title='Date',
                    yaxis_title='Events',
                    height=400
                )
                
                return dcc.Graph(figure=fig)
            else:
                return html.Div("Date column not found", className="no-data")
        else:
            return html.Div("No data available for timeline", className="no-data")
    
    def _create_progress_widget(self, data: Any, config: Dict[str, Any]) -> html.Div:
        """Create progress widget."""
        if isinstance(data, pd.DataFrame) and not data.empty:
            progress_col = config.get('progress_column', data.columns[0])
            progress_value = data[progress_col].mean() if data[progress_col].dtype in ['int64', 'float64'] else 0
            
            return html.Div([
                html.Div([
                    html.Div(
                        className="progress-bar",
                        style={'width': f'{progress_value}%'}
                    ),
                    html.Span(f"{progress_value:.1f}%", className="progress-text")
                ], className="progress-container"),
                html.P(config.get('progress_label', 'Progress'), className="progress-label")
            ], className="progress-widget")
        else:
            return html.Div("No data available", className="no-data")
    
    def _create_alert_widget(self, data: Any, config: Dict[str, Any]) -> html.Div:
        """Create alert widget."""
        alert_type = config.get('alert_type', 'info')
        message = config.get('message', 'No alerts')
        
        if isinstance(data, pd.DataFrame) and not data.empty:
            # Check for alert conditions
            alert_conditions = config.get('alert_conditions', [])
            for condition in alert_conditions:
                column = condition.get('column')
                threshold = condition.get('threshold')
                operator = condition.get('operator', '>')
                
                if column in data.columns:
                    if operator == '>' and data[column].max() > threshold:
                        message = f"Alert: {column} exceeds {threshold}"
                        alert_type = 'warning'
                    elif operator == '<' and data[column].min() < threshold:
                        message = f"Alert: {column} below {threshold}"
                        alert_type = 'warning'
        
        return html.Div([
            html.Div([
                html.Strong("Alert"),
                html.P(message)
            ], className=f"alert alert-{alert_type}")
        ], className="alert-widget")
    
    def _create_export_widget(self, data: Any, config: Dict[str, Any]) -> html.Div:
        """Create export widget."""
        if isinstance(data, pd.DataFrame) and not data.empty:
            return html.Div([
                html.Button("Export CSV", id="export-csv-btn", className="btn btn-primary"),
                html.Button("Export Excel", id="export-excel-btn", className="btn btn-secondary"),
                html.Button("Export JSON", id="export-json-btn", className="btn btn-secondary"),
                dcc.Download(id="download-export")
            ], className="export-widget")
        else:
            return html.Div("No data to export", className="no-data")
    
    def _create_comparison_widget(self, data: Any, config: Dict[str, Any]) -> html.Div:
        """Create comparison widget."""
        if isinstance(data, pd.DataFrame) and not data.empty:
            compare_col = config.get('compare_column', data.columns[0])
            group_col = config.get('group_column', data.columns[1])
            
            if group_col in data.columns:
                comparison_data = data.groupby(group_col)[compare_col].agg(['mean', 'std', 'count']).reset_index()
                
                fig = px.bar(
                    comparison_data, 
                    x=group_col, 
                    y='mean',
                    error_y='std',
                    title=f"Comparison of {compare_col} by {group_col}"
                )
                
                return dcc.Graph(figure=fig)
            else:
                return html.Div("Group column not found", className="no-data")
        else:
            return html.Div("No data available for comparison", className="no-data")
    
    def register_callback(self, callback_func: Callable, inputs: List, outputs: List):
        """
        Register a custom callback.
        
        Args:
            callback_func: Callback function
            inputs: List of input components
            outputs: List of output components
        """
        self.app.callback(outputs, inputs)(callback_func)
        logger.info("Registered custom callback")
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics."""
        return {
            'total_widgets': len(self.widgets),
            'total_filters': len(self.filters),
            'data_sources': len(self.data_sources),
            'widget_types': {widget.widget_type.value: sum(1 for w in self.widgets.values() if w.widget_type == widget.widget_type) 
                           for widget in self.widgets.values()},
            'registered_callbacks': len(self.callbacks_registered)
        }
    
    def export_dashboard_config(self, format: str = "json") -> str:
        """
        Export dashboard configuration.
        
        Args:
            format: Export format (json, yaml)
            
        Returns:
            str: Exported configuration
        """
        config = {
            'widgets': [widget.to_dict() for widget in self.widgets.values()],
            'filters': [filter_obj.to_dict() for filter_obj in self.filters.values()],
            'data_sources': list(self.data_sources.keys()),
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'version': '1.0.0'
            }
        }
        
        if format == "json":
            return json.dumps(config, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def run_dashboard(self, host: str = "127.0.0.1", port: int = 8051, debug: bool = False):
        """
        Run the dashboard application.
        
        Args:
            host: Host to run on
            port: Port to run on
            debug: Enable debug mode
        """
        logger.info(f"Starting report dashboard on {host}:{port}")
        self.app.run_server(host=host, port=port, debug=debug)
