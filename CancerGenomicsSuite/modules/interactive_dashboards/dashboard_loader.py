"""
Dashboard Loader Module

Provides dynamic dashboard loading and management capabilities for the Cancer Genomics Analysis Suite.
Supports multiple dashboard types, widget management, and real-time configuration updates.
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
import yaml
import importlib
import inspect
import threading
import time
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class DashboardType(Enum):
    """Types of dashboards."""
    ANALYSIS = "analysis"
    MONITORING = "monitoring"
    EXPLORATION = "exploration"
    REPORTING = "reporting"
    CUSTOM = "custom"


class WidgetType(Enum):
    """Types of dashboard widgets."""
    CHART = "chart"
    TABLE = "table"
    METRIC = "metric"
    FILTER = "filter"
    TEXT = "text"
    IMAGE = "image"
    PROGRESS = "progress"
    ALERT = "alert"
    TIMELINE = "timeline"
    HEATMAP = "heatmap"
    NETWORK = "network"
    MAP = "map"
    CUSTOM = "custom"


@dataclass
class DashboardWidget:
    """Represents a dashboard widget."""
    id: str
    widget_type: WidgetType
    title: str
    position: Tuple[int, int]
    size: Tuple[int, int]
    config: Dict[str, Any] = field(default_factory=dict)
    data_source: str = ""
    refresh_interval: int = 0
    visible: bool = True
    dependencies: List[str] = field(default_factory=list)
    callbacks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert widget to dictionary."""
        return {
            'id': self.id,
            'widget_type': self.widget_type.value,
            'title': self.title,
            'position': self.position,
            'size': self.size,
            'config': self.config,
            'data_source': self.data_source,
            'refresh_interval': self.refresh_interval,
            'visible': self.visible,
            'dependencies': self.dependencies,
            'callbacks': self.callbacks,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DashboardWidget':
        """Create widget from dictionary."""
        data['widget_type'] = WidgetType(data['widget_type'])
        return cls(**data)


@dataclass
class DashboardConfig:
    """Configuration for a dashboard."""
    id: str
    name: str
    dashboard_type: DashboardType
    title: str
    description: str = ""
    widgets: List[DashboardWidget] = field(default_factory=list)
    layout: Dict[str, Any] = field(default_factory=dict)
    theme: str = "default"
    refresh_interval: int = 0
    auto_save: bool = True
    permissions: Dict[str, List[str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'dashboard_type': self.dashboard_type.value,
            'title': self.title,
            'description': self.description,
            'widgets': [widget.to_dict() for widget in self.widgets],
            'layout': self.layout,
            'theme': self.theme,
            'refresh_interval': self.refresh_interval,
            'auto_save': self.auto_save,
            'permissions': self.permissions,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DashboardConfig':
        """Create config from dictionary."""
        data['dashboard_type'] = DashboardType(data['dashboard_type'])
        data['widgets'] = [DashboardWidget.from_dict(widget) for widget in data['widgets']]
        return cls(**data)


class DashboardLoader:
    """
    Manages dynamic dashboard loading and configuration.
    
    Features:
    - Dynamic dashboard loading from configuration files
    - Widget management and placement
    - Real-time configuration updates
    - Dashboard templates and presets
    - Plugin system for custom widgets
    - Layout management and responsive design
    """
    
    def __init__(self, config_dir: str = None, templates_dir: str = None):
        """
        Initialize DashboardLoader.
        
        Args:
            config_dir: Directory containing dashboard configurations
            templates_dir: Directory containing dashboard templates
        """
        self.config_dir = Path(config_dir) if config_dir else Path("configs/dashboards")
        self.templates_dir = Path(templates_dir) if templates_dir else Path("templates/dashboards")
        
        # Create directories if they don't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Dashboard registry
        self.dashboards = {}
        self.templates = {}
        self.widget_registry = {}
        self.data_sources = {}
        
        # Load existing configurations
        self._load_dashboard_configs()
        self._load_dashboard_templates()
        self._register_default_widgets()
    
    def _load_dashboard_configs(self):
        """Load dashboard configurations from files."""
        for config_file in self.config_dir.glob("*.json"):
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                    config = DashboardConfig.from_dict(config_data)
                    self.dashboards[config.id] = config
                    logger.info(f"Loaded dashboard config: {config.name}")
            except Exception as e:
                logger.error(f"Failed to load dashboard config {config_file}: {e}")
        
        for config_file in self.config_dir.glob("*.yaml"):
            try:
                with open(config_file, 'r') as f:
                    config_data = yaml.safe_load(f)
                    config = DashboardConfig.from_dict(config_data)
                    self.dashboards[config.id] = config
                    logger.info(f"Loaded dashboard config: {config.name}")
            except Exception as e:
                logger.error(f"Failed to load dashboard config {config_file}: {e}")
    
    def _load_dashboard_templates(self):
        """Load dashboard templates."""
        for template_file in self.templates_dir.glob("*.json"):
            try:
                with open(template_file, 'r') as f:
                    template_data = json.load(f)
                    self.templates[template_file.stem] = template_data
                    logger.info(f"Loaded dashboard template: {template_file.stem}")
            except Exception as e:
                logger.error(f"Failed to load template {template_file}: {e}")
    
    def _register_default_widgets(self):
        """Register default widget types."""
        self.widget_registry = {
            WidgetType.CHART: self._create_chart_widget,
            WidgetType.TABLE: self._create_table_widget,
            WidgetType.METRIC: self._create_metric_widget,
            WidgetType.FILTER: self._create_filter_widget,
            WidgetType.TEXT: self._create_text_widget,
            WidgetType.IMAGE: self._create_image_widget,
            WidgetType.PROGRESS: self._create_progress_widget,
            WidgetType.ALERT: self._create_alert_widget,
            WidgetType.TIMELINE: self._create_timeline_widget,
            WidgetType.HEATMAP: self._create_heatmap_widget,
            WidgetType.NETWORK: self._create_network_widget,
            WidgetType.MAP: self._create_map_widget
        }
    
    def create_dashboard(self, config: DashboardConfig) -> str:
        """
        Create a new dashboard.
        
        Args:
            config: Dashboard configuration
            
        Returns:
            str: Dashboard ID
        """
        self.dashboards[config.id] = config
        self._save_dashboard_config(config)
        logger.info(f"Created dashboard: {config.name}")
        return config.id
    
    def load_dashboard(self, dashboard_id: str) -> Optional[DashboardConfig]:
        """
        Load a dashboard configuration.
        
        Args:
            dashboard_id: Dashboard ID
            
        Returns:
            DashboardConfig or None
        """
        return self.dashboards.get(dashboard_id)
    
    def save_dashboard(self, dashboard_id: str) -> bool:
        """
        Save a dashboard configuration.
        
        Args:
            dashboard_id: Dashboard ID
            
        Returns:
            bool: Success status
        """
        config = self.dashboards.get(dashboard_id)
        if config:
            self._save_dashboard_config(config)
            return True
        return False
    
    def _save_dashboard_config(self, config: DashboardConfig):
        """Save dashboard configuration to file."""
        config_file = self.config_dir / f"{config.id}.json"
        with open(config_file, 'w') as f:
            json.dump(config.to_dict(), f, indent=2)
    
    def create_dashboard_from_template(self, template_name: str, dashboard_id: str, 
                                     dashboard_name: str, **kwargs) -> str:
        """
        Create a dashboard from a template.
        
        Args:
            template_name: Name of the template
            dashboard_id: New dashboard ID
            dashboard_name: New dashboard name
            **kwargs: Template parameters
            
        Returns:
            str: Dashboard ID
        """
        if template_name not in self.templates:
            raise ValueError(f"Template {template_name} not found")
        
        template = self.templates[template_name]
        
        # Create config from template
        config_data = template.copy()
        config_data['id'] = dashboard_id
        config_data['name'] = dashboard_name
        
        # Apply template parameters
        for key, value in kwargs.items():
            if key in config_data:
                config_data[key] = value
        
        config = DashboardConfig.from_dict(config_data)
        return self.create_dashboard(config)
    
    def add_widget(self, dashboard_id: str, widget: DashboardWidget) -> str:
        """
        Add a widget to a dashboard.
        
        Args:
            dashboard_id: Dashboard ID
            widget: Widget to add
            
        Returns:
            str: Widget ID
        """
        config = self.dashboards.get(dashboard_id)
        if not config:
            raise ValueError(f"Dashboard {dashboard_id} not found")
        
        config.widgets.append(widget)
        
        if config.auto_save:
            self._save_dashboard_config(config)
        
        logger.info(f"Added widget {widget.title} to dashboard {config.name}")
        return widget.id
    
    def remove_widget(self, dashboard_id: str, widget_id: str) -> bool:
        """
        Remove a widget from a dashboard.
        
        Args:
            dashboard_id: Dashboard ID
            widget_id: Widget ID
            
        Returns:
            bool: Success status
        """
        config = self.dashboards.get(dashboard_id)
        if not config:
            return False
        
        config.widgets = [w for w in config.widgets if w.id != widget_id]
        
        if config.auto_save:
            self._save_dashboard_config(config)
        
        logger.info(f"Removed widget {widget_id} from dashboard {config.name}")
        return True
    
    def update_widget(self, dashboard_id: str, widget_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a widget configuration.
        
        Args:
            dashboard_id: Dashboard ID
            widget_id: Widget ID
            updates: Updates to apply
            
        Returns:
            bool: Success status
        """
        config = self.dashboards.get(dashboard_id)
        if not config:
            return False
        
        for widget in config.widgets:
            if widget.id == widget_id:
                for key, value in updates.items():
                    if hasattr(widget, key):
                        setattr(widget, key, value)
                
                if config.auto_save:
                    self._save_dashboard_config(config)
                
                logger.info(f"Updated widget {widget_id} in dashboard {config.name}")
                return True
        
        return False
    
    def register_widget_type(self, widget_type: WidgetType, widget_creator: Callable):
        """
        Register a custom widget type.
        
        Args:
            widget_type: Widget type
            widget_creator: Function to create the widget
        """
        self.widget_registry[widget_type] = widget_creator
        logger.info(f"Registered custom widget type: {widget_type.value}")
    
    def register_data_source(self, source_id: str, data_source: Any):
        """
        Register a data source.
        
        Args:
            source_id: Data source identifier
            data_source: Data source object
        """
        self.data_sources[source_id] = data_source
        logger.info(f"Registered data source: {source_id}")
    
    def create_dash_app(self, dashboard_id: str) -> dash.Dash:
        """
        Create a Dash application for a dashboard.
        
        Args:
            dashboard_id: Dashboard ID
            
        Returns:
            dash.Dash: Dash application
        """
        config = self.dashboards.get(dashboard_id)
        if not config:
            raise ValueError(f"Dashboard {dashboard_id} not found")
        
        app = dash.Dash(__name__)
        app.title = config.title
        
        # Create layout
        app.layout = self._create_dashboard_layout(config)
        
        # Register callbacks
        self._register_dashboard_callbacks(app, config)
        
        return app
    
    def _create_dashboard_layout(self, config: DashboardConfig) -> html.Div:
        """Create dashboard layout."""
        # Header
        header = html.Div([
            html.H1(config.title, className="dashboard-title"),
            html.P(config.description, className="dashboard-description") if config.description else None,
            html.Div([
                html.Button("Refresh", id="refresh-btn", className="btn btn-primary"),
                html.Button("Settings", id="settings-btn", className="btn btn-secondary"),
                dcc.Interval(
                    id="refresh-interval",
                    interval=config.refresh_interval * 1000 if config.refresh_interval > 0 else None,
                    n_intervals=0
                )
            ], className="header-controls")
        ], className="dashboard-header")
        
        # Widgets
        widgets = []
        for widget in config.widgets:
            if widget.visible:
                widget_component = self._create_widget_component(widget)
                widgets.append(
                    html.Div(
                        widget_component,
                        className="widget-container",
                        id=f"widget-{widget.id}",
                        style={
                            'grid-column': f"span {widget.size[0]}",
                            'grid-row': f"span {widget.size[1]}"
                        }
                    )
                )
        
        # Main content
        content = html.Div(
            widgets,
            className="dashboard-content",
            style={
                'display': 'grid',
                'grid-template-columns': 'repeat(12, 1fr)',
                'gap': '20px',
                'padding': '20px'
            }
        )
        
        return html.Div([header, content], className="dashboard-container")
    
    def _create_widget_component(self, widget: DashboardWidget) -> html.Div:
        """Create a widget component."""
        widget_creator = self.widget_registry.get(widget.widget_type)
        if not widget_creator:
            return html.Div(f"Unknown widget type: {widget.widget_type}")
        
        return widget_creator(widget)
    
    def _create_chart_widget(self, widget: DashboardWidget) -> html.Div:
        """Create a chart widget."""
        data = self._get_widget_data(widget)
        
        if data is not None and not data.empty:
            chart_type = widget.config.get('chart_type', 'bar')
            
            if chart_type == 'bar':
                fig = px.bar(data, x=data.columns[0], y=data.columns[1])
            elif chart_type == 'line':
                fig = px.line(data, x=data.columns[0], y=data.columns[1])
            elif chart_type == 'scatter':
                fig = px.scatter(data, x=data.columns[0], y=data.columns[1])
            elif chart_type == 'pie':
                fig = px.pie(data, names=data.columns[0], values=data.columns[1])
            else:
                fig = px.bar(data, x=data.columns[0], y=data.columns[1])
            
            fig.update_layout(title=widget.title)
            
            return html.Div([
                html.H3(widget.title, className="widget-title"),
                dcc.Graph(figure=fig, id=f"chart-{widget.id}")
            ], className="chart-widget")
        else:
            return html.Div([
                html.H3(widget.title, className="widget-title"),
                html.P("No data available", className="no-data")
            ], className="chart-widget")
    
    def _create_table_widget(self, widget: DashboardWidget) -> html.Div:
        """Create a table widget."""
        data = self._get_widget_data(widget)
        
        if data is not None and not data.empty:
            max_rows = widget.config.get('max_rows', 100)
            display_data = data.head(max_rows)
            
            return html.Div([
                html.H3(widget.title, className="widget-title"),
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
            ], className="table-widget")
        else:
            return html.Div([
                html.H3(widget.title, className="widget-title"),
                html.P("No data available", className="no-data")
            ], className="table-widget")
    
    def _create_metric_widget(self, widget: DashboardWidget) -> html.Div:
        """Create a metric widget."""
        data = self._get_widget_data(widget)
        
        if data is not None and not data.empty:
            metric_col = widget.config.get('metric_column', data.columns[0])
            metric_value = data[metric_col].sum() if data[metric_col].dtype in ['int64', 'float64'] else len(data)
            
            return html.Div([
                html.H3(widget.title, className="widget-title"),
                html.H2(str(metric_value), className="metric-value"),
                html.P(metric_col, className="metric-label")
            ], className="metric-widget")
        else:
            return html.Div([
                html.H3(widget.title, className="widget-title"),
                html.P("No data available", className="no-data")
            ], className="metric-widget")
    
    def _create_filter_widget(self, widget: DashboardWidget) -> html.Div:
        """Create a filter widget."""
        filter_type = widget.config.get('filter_type', 'dropdown')
        options = widget.config.get('options', [])
        
        if filter_type == 'dropdown':
            component = dcc.Dropdown(
                id=f"filter-{widget.id}",
                options=[{'label': opt, 'value': opt} for opt in options],
                placeholder=f"Select {widget.title}",
                multi=True
            )
        elif filter_type == 'slider':
            component = dcc.RangeSlider(
                id=f"filter-{widget.id}",
                min=min(options) if options else 0,
                max=max(options) if options else 100,
                value=[min(options) if options else 0, max(options) if options else 100],
                marks={i: str(i) for i in options[::len(options)//10] if options}
            )
        else:
            component = html.Div(f"Unsupported filter type: {filter_type}")
        
        return html.Div([
            html.H3(widget.title, className="widget-title"),
            component
        ], className="filter-widget")
    
    def _create_text_widget(self, widget: DashboardWidget) -> html.Div:
        """Create a text widget."""
        content = widget.config.get('content', 'No content')
        
        return html.Div([
            html.H3(widget.title, className="widget-title"),
            html.Div(content, className="text-content")
        ], className="text-widget")
    
    def _create_image_widget(self, widget: DashboardWidget) -> html.Div:
        """Create an image widget."""
        image_path = widget.config.get('image_path', '')
        
        return html.Div([
            html.H3(widget.title, className="widget-title"),
            html.Img(src=image_path, alt=widget.title, className="widget-image") if image_path else html.P("No image")
        ], className="image-widget")
    
    def _create_progress_widget(self, widget: DashboardWidget) -> html.Div:
        """Create a progress widget."""
        progress_value = widget.config.get('progress_value', 0)
        
        return html.Div([
            html.H3(widget.title, className="widget-title"),
            html.Div([
                html.Div(
                    className="progress-bar",
                    style={'width': f'{progress_value}%'}
                ),
                html.Span(f"{progress_value}%", className="progress-text")
            ], className="progress-container")
        ], className="progress-widget")
    
    def _create_alert_widget(self, widget: DashboardWidget) -> html.Div:
        """Create an alert widget."""
        alert_type = widget.config.get('alert_type', 'info')
        message = widget.config.get('message', 'No message')
        
        return html.Div([
            html.Div([
                html.Strong("Alert"),
                html.P(message)
            ], className=f"alert alert-{alert_type}")
        ], className="alert-widget")
    
    def _create_timeline_widget(self, widget: DashboardWidget) -> html.Div:
        """Create a timeline widget."""
        data = self._get_widget_data(widget)
        
        if data is not None and not data.empty:
            date_col = widget.config.get('date_column', 'date')
            event_col = widget.config.get('event_column', 'event')
            
            if date_col in data.columns:
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
                    title=widget.title,
                    xaxis_title='Date',
                    yaxis_title='Events',
                    height=400
                )
                
                return html.Div([
                    html.H3(widget.title, className="widget-title"),
                    dcc.Graph(figure=fig, id=f"timeline-{widget.id}")
                ], className="timeline-widget")
        
        return html.Div([
            html.H3(widget.title, className="widget-title"),
            html.P("No data available", className="no-data")
        ], className="timeline-widget")
    
    def _create_heatmap_widget(self, widget: DashboardWidget) -> html.Div:
        """Create a heatmap widget."""
        data = self._get_widget_data(widget)
        
        if data is not None and not data.empty:
            fig = go.Figure(data=go.Heatmap(
                z=data.values,
                x=data.columns,
                y=data.index,
                colorscale='Viridis'
            ))
            
            fig.update_layout(title=widget.title)
            
            return html.Div([
                html.H3(widget.title, className="widget-title"),
                dcc.Graph(figure=fig, id=f"heatmap-{widget.id}")
            ], className="heatmap-widget")
        else:
            return html.Div([
                html.H3(widget.title, className="widget-title"),
                html.P("No data available", className="no-data")
            ], className="heatmap-widget")
    
    def _create_network_widget(self, widget: DashboardWidget) -> html.Div:
        """Create a network widget."""
        # Placeholder for network visualization
        return html.Div([
            html.H3(widget.title, className="widget-title"),
            html.P("Network visualization not implemented", className="no-data")
        ], className="network-widget")
    
    def _create_map_widget(self, widget: DashboardWidget) -> html.Div:
        """Create a map widget."""
        # Placeholder for map visualization
        return html.Div([
            html.H3(widget.title, className="widget-title"),
            html.P("Map visualization not implemented", className="no-data")
        ], className="map-widget")
    
    def _get_widget_data(self, widget: DashboardWidget) -> Optional[pd.DataFrame]:
        """Get data for a widget."""
        if widget.data_source and widget.data_source in self.data_sources:
            return self.data_sources[widget.data_source]
        return None
    
    def _register_dashboard_callbacks(self, app: dash.Dash, config: DashboardConfig):
        """Register callbacks for a dashboard."""
        # Placeholder for callback registration
        pass
    
    def list_dashboards(self) -> List[Dict[str, Any]]:
        """List all available dashboards."""
        return [
            {
                'id': config.id,
                'name': config.name,
                'type': config.dashboard_type.value,
                'title': config.title,
                'widget_count': len(config.widgets),
                'description': config.description
            }
            for config in self.dashboards.values()
        ]
    
    def get_dashboard_info(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a dashboard."""
        config = self.dashboards.get(dashboard_id)
        if not config:
            return None
        
        return {
            'id': config.id,
            'name': config.name,
            'type': config.dashboard_type.value,
            'title': config.title,
            'description': config.description,
            'widget_count': len(config.widgets),
            'theme': config.theme,
            'refresh_interval': config.refresh_interval,
            'auto_save': config.auto_save,
            'metadata': config.metadata
        }
    
    def delete_dashboard(self, dashboard_id: str) -> bool:
        """Delete a dashboard."""
        if dashboard_id in self.dashboards:
            del self.dashboards[dashboard_id]
            
            # Remove config file
            config_file = self.config_dir / f"{dashboard_id}.json"
            if config_file.exists():
                config_file.unlink()
            
            logger.info(f"Deleted dashboard: {dashboard_id}")
            return True
        return False
