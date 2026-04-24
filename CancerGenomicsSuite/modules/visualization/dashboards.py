"""
Dashboards Module

Provides comprehensive dashboard creation and management for the Cancer Genomics Analysis Suite.
Supports interactive dashboards with multiple widgets, layouts, and real-time updates.
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

logger = logging.getLogger(__name__)


class WidgetType(Enum):
    """Types of dashboard widgets."""
    PLOT = "plot"
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


class LayoutType(Enum):
    """Dashboard layout types."""
    GRID = "grid"
    ROW = "row"
    COLUMN = "column"
    TAB = "tab"
    ACCORDION = "accordion"
    MODAL = "modal"


@dataclass
class DashboardWidget:
    """Represents a dashboard widget."""
    id: str
    widget_type: WidgetType
    title: str
    data: Any = None
    config: Dict[str, Any] = field(default_factory=dict)
    position: Tuple[int, int] = (0, 0)
    size: Tuple[int, int] = (1, 1)
    visible: bool = True
    refresh_interval: int = 0  # seconds, 0 for no auto-refresh
    callbacks: List[Callable] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert widget to dictionary."""
        return {
            'id': self.id,
            'widget_type': self.widget_type.value,
            'title': self.title,
            'config': self.config,
            'position': self.position,
            'size': self.size,
            'visible': self.visible,
            'refresh_interval': self.refresh_interval,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DashboardWidget':
        """Create widget from dictionary."""
        data['widget_type'] = WidgetType(data['widget_type'])
        return cls(**data)


@dataclass
class DashboardLayout:
    """Represents a dashboard layout configuration."""
    id: str
    name: str
    layout_type: LayoutType
    widgets: List[DashboardWidget] = field(default_factory=list)
    grid_size: Tuple[int, int] = (12, 12)
    theme: str = "default"
    title: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert layout to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'layout_type': self.layout_type.value,
            'widgets': [widget.to_dict() for widget in self.widgets],
            'grid_size': self.grid_size,
            'theme': self.theme,
            'title': self.title,
            'description': self.description,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DashboardLayout':
        """Create layout from dictionary."""
        data['layout_type'] = LayoutType(data['layout_type'])
        data['widgets'] = [DashboardWidget.from_dict(widget) for widget in data['widgets']]
        return cls(**data)


class DashboardBuilder:
    """
    Builds and manages interactive dashboards for genomics data.
    
    Features:
    - Multiple widget types (plots, tables, metrics, filters)
    - Flexible layouts (grid, tabs, accordions)
    - Real-time data updates
    - Interactive filtering and selection
    - Custom styling and themes
    - Export functionality
    - Responsive design
    """
    
    def __init__(self, app_name: str = "CancerGenomicsDashboard"):
        """
        Initialize DashboardBuilder.
        
        Args:
            app_name: Name of the Dash application
        """
        self.app_name = app_name
        self.app = dash.Dash(__name__)
        self.layouts = {}
        self.current_layout = None
        self.widget_registry = {}
        self.data_sources = {}
        self.callbacks_registered = set()
        
        # Configure app
        self.app.config.suppress_callback_exceptions = True
        
        # Set up default layout
        self._setup_default_layout()
    
    def _setup_default_layout(self):
        """Set up default dashboard layout."""
        default_layout = DashboardLayout(
            id="default",
            name="Default Layout",
            layout_type=LayoutType.GRID,
            title="Cancer Genomics Analysis Dashboard",
            description="Interactive dashboard for genomics data analysis"
        )
        self.layouts["default"] = default_layout
        self.current_layout = default_layout
    
    def create_layout(self, layout_id: str, name: str, layout_type: LayoutType = LayoutType.GRID,
                     title: str = "", description: str = "") -> DashboardLayout:
        """
        Create a new dashboard layout.
        
        Args:
            layout_id: Unique identifier for the layout
            name: Display name for the layout
            layout_type: Type of layout
            title: Layout title
            description: Layout description
            
        Returns:
            DashboardLayout: Created layout
        """
        layout = DashboardLayout(
            id=layout_id,
            name=name,
            layout_type=layout_type,
            title=title,
            description=description
        )
        
        self.layouts[layout_id] = layout
        return layout
    
    def add_widget(self, layout_id: str, widget: DashboardWidget) -> str:
        """
        Add a widget to a layout.
        
        Args:
            layout_id: Layout to add widget to
            widget: Widget to add
            
        Returns:
            str: Widget ID
        """
        if layout_id not in self.layouts:
            raise ValueError(f"Layout {layout_id} not found")
        
        layout = self.layouts[layout_id]
        layout.widgets.append(widget)
        
        # Register widget
        self.widget_registry[widget.id] = widget
        
        logger.info(f"Added widget {widget.id} to layout {layout_id}")
        return widget.id
    
    def create_plot_widget(self, widget_id: str, title: str, plot_type: str,
                          data: Any, config: Dict[str, Any] = None) -> DashboardWidget:
        """
        Create a plot widget.
        
        Args:
            widget_id: Unique widget identifier
            title: Widget title
            plot_type: Type of plot
            data: Data for the plot
            config: Plot configuration
            
        Returns:
            DashboardWidget: Created widget
        """
        widget = DashboardWidget(
            id=widget_id,
            widget_type=WidgetType.PLOT,
            title=title,
            data=data,
            config=config or {},
            metadata={'plot_type': plot_type}
        )
        
        return widget
    
    def create_table_widget(self, widget_id: str, title: str, data: pd.DataFrame,
                           config: Dict[str, Any] = None) -> DashboardWidget:
        """
        Create a table widget.
        
        Args:
            widget_id: Unique widget identifier
            title: Widget title
            data: DataFrame to display
            config: Table configuration
            
        Returns:
            DashboardWidget: Created widget
        """
        widget = DashboardWidget(
            id=widget_id,
            widget_type=WidgetType.TABLE,
            title=title,
            data=data,
            config=config or {},
            metadata={'columns': list(data.columns)}
        )
        
        return widget
    
    def create_metric_widget(self, widget_id: str, title: str, value: Union[int, float, str],
                           config: Dict[str, Any] = None) -> DashboardWidget:
        """
        Create a metric widget.
        
        Args:
            widget_id: Unique widget identifier
            title: Widget title
            value: Metric value
            config: Metric configuration
            
        Returns:
            DashboardWidget: Created widget
        """
        widget = DashboardWidget(
            id=widget_id,
            widget_type=WidgetType.METRIC,
            title=title,
            data=value,
            config=config or {},
            metadata={'value_type': type(value).__name__}
        )
        
        return widget
    
    def create_filter_widget(self, widget_id: str, title: str, filter_type: str,
                           options: List[str], config: Dict[str, Any] = None) -> DashboardWidget:
        """
        Create a filter widget.
        
        Args:
            widget_id: Unique widget identifier
            title: Widget title
            filter_type: Type of filter (dropdown, slider, etc.)
            options: Available options
            config: Filter configuration
            
        Returns:
            DashboardWidget: Created widget
        """
        widget = DashboardWidget(
            id=widget_id,
            widget_type=WidgetType.FILTER,
            title=title,
            data=options,
            config=config or {},
            metadata={'filter_type': filter_type}
        )
        
        return widget
    
    def _generate_dash_layout(self, layout: DashboardLayout) -> html.Div:
        """Generate Dash layout from DashboardLayout."""
        if layout.layout_type == LayoutType.GRID:
            return self._generate_grid_layout(layout)
        elif layout.layout_type == LayoutType.TAB:
            return self._generate_tab_layout(layout)
        elif layout.layout_type == LayoutType.ROW:
            return self._generate_row_layout(layout)
        else:
            return self._generate_grid_layout(layout)
    
    def _generate_grid_layout(self, layout: DashboardLayout) -> html.Div:
        """Generate grid-based layout."""
        children = []
        
        # Dashboard header
        if layout.title:
            children.append(
                html.H1(layout.title, className="dashboard-title")
            )
        
        if layout.description:
            children.append(
                html.P(layout.description, className="dashboard-description")
            )
        
        # Create grid container
        grid_children = []
        
        for widget in layout.widgets:
            if widget.visible:
                widget_component = self._create_widget_component(widget)
                grid_children.append(
                    html.Div(
                        widget_component,
                        className=f"grid-item",
                        style={
                            'grid-column': f"span {widget.size[0]}",
                            'grid-row': f"span {widget.size[1]}"
                        }
                    )
                )
        
        children.append(
            html.Div(
                grid_children,
                className="dashboard-grid",
                style={
                    'display': 'grid',
                    'grid-template-columns': f"repeat({layout.grid_size[0]}, 1fr)",
                    'gap': '20px',
                    'padding': '20px'
                }
            )
        )
        
        return html.Div(children, className="dashboard-container")
    
    def _generate_tab_layout(self, layout: DashboardLayout) -> html.Div:
        """Generate tab-based layout."""
        tabs = []
        
        # Group widgets by tab (assuming metadata contains tab info)
        tab_groups = {}
        for widget in layout.widgets:
            if widget.visible:
                tab_name = widget.metadata.get('tab', 'Default')
                if tab_name not in tab_groups:
                    tab_groups[tab_name] = []
                tab_groups[tab_name].append(widget)
        
        for tab_name, widgets in tab_groups.items():
            tab_content = []
            for widget in widgets:
                widget_component = self._create_widget_component(widget)
                tab_content.append(
                    html.Div(
                        widget_component,
                        className="tab-widget"
                    )
                )
            
            tabs.append(
                dcc.Tab(
                    label=tab_name,
                    children=tab_content,
                    className="tab-content"
                )
            )
        
        return html.Div([
            html.H1(layout.title, className="dashboard-title") if layout.title else None,
            dcc.Tabs(tabs, className="dashboard-tabs")
        ], className="dashboard-container")
    
    def _generate_row_layout(self, layout: DashboardLayout) -> html.Div:
        """Generate row-based layout."""
        children = []
        
        if layout.title:
            children.append(
                html.H1(layout.title, className="dashboard-title")
            )
        
        for widget in layout.widgets:
            if widget.visible:
                widget_component = self._create_widget_component(widget)
                children.append(
                    html.Div(
                        widget_component,
                        className="row-widget",
                        style={'margin-bottom': '20px'}
                    )
                )
        
        return html.Div(children, className="dashboard-container")
    
    def _create_widget_component(self, widget: DashboardWidget) -> html.Div:
        """Create Dash component for a widget."""
        widget_content = []
        
        # Widget title
        if widget.title:
            widget_content.append(
                html.H3(widget.title, className="widget-title")
            )
        
        # Widget content based on type
        if widget.widget_type == WidgetType.PLOT:
            widget_content.append(
                dcc.Graph(
                    id=f"graph-{widget.id}",
                    figure=self._create_plot_figure(widget),
                    config={'displayModeBar': True}
                )
            )
        elif widget.widget_type == WidgetType.TABLE:
            widget_content.append(
                html.Div([
                    html.Table([
                        html.Thead([
                            html.Tr([html.Th(col) for col in widget.data.columns])
                        ]),
                        html.Tbody([
                            html.Tr([
                                html.Td(widget.data.iloc[i][col]) 
                                for col in widget.data.columns
                            ]) for i in range(min(10, len(widget.data)))  # Show first 10 rows
                        ])
                    ], className="data-table")
                ])
            )
        elif widget.widget_type == WidgetType.METRIC:
            widget_content.append(
                html.Div([
                    html.H2(str(widget.data), className="metric-value"),
                    html.P(widget.title, className="metric-label")
                ], className="metric-widget")
            )
        elif widget.widget_type == WidgetType.FILTER:
            filter_type = widget.metadata.get('filter_type', 'dropdown')
            if filter_type == 'dropdown':
                widget_content.append(
                    dcc.Dropdown(
                        id=f"filter-{widget.id}",
                        options=[{'label': opt, 'value': opt} for opt in widget.data],
                        placeholder=f"Select {widget.title}",
                        multi=True
                    )
                )
            elif filter_type == 'slider':
                widget_content.append(
                    dcc.RangeSlider(
                        id=f"filter-{widget.id}",
                        min=min(widget.data),
                        max=max(widget.data),
                        value=[min(widget.data), max(widget.data)],
                        marks={i: str(i) for i in widget.data[::len(widget.data)//10]}
                    )
                )
        elif widget.widget_type == WidgetType.TEXT:
            widget_content.append(
                html.Div(
                    widget.data,
                    className="text-widget"
                )
            )
        elif widget.widget_type == WidgetType.PROGRESS:
            progress_value = widget.data if isinstance(widget.data, (int, float)) else 0
            widget_content.append(
                html.Div([
                    html.Div(
                        className="progress-bar",
                        style={'width': f'{progress_value}%'}
                    ),
                    html.Span(f"{progress_value}%", className="progress-text")
                ], className="progress-widget")
            )
        
        # Auto-refresh if configured
        if widget.refresh_interval > 0:
            widget_content.append(
                dcc.Interval(
                    id=f"interval-{widget.id}",
                    interval=widget.refresh_interval * 1000,
                    n_intervals=0
                )
            )
        
        return html.Div(
            widget_content,
            className=f"widget widget-{widget.widget_type.value}",
            id=f"widget-{widget.id}"
        )
    
    def _create_plot_figure(self, widget: DashboardWidget) -> go.Figure:
        """Create plotly figure for plot widget."""
        plot_type = widget.metadata.get('plot_type', 'scatter')
        data = widget.data
        
        if plot_type == 'scatter':
            if isinstance(data, pd.DataFrame):
                fig = px.scatter(data, x=data.columns[0], y=data.columns[1])
            else:
                fig = go.Figure(data=go.Scatter(y=data, mode='markers'))
        elif plot_type == 'line':
            if isinstance(data, pd.DataFrame):
                fig = px.line(data, x=data.columns[0], y=data.columns[1])
            else:
                fig = go.Figure(data=go.Scatter(y=data, mode='lines'))
        elif plot_type == 'bar':
            if isinstance(data, pd.DataFrame):
                fig = px.bar(data, x=data.columns[0], y=data.columns[1])
            else:
                fig = go.Figure(data=go.Bar(y=data))
        elif plot_type == 'heatmap':
            if isinstance(data, pd.DataFrame):
                fig = go.Figure(data=go.Heatmap(z=data.values, x=data.columns, y=data.index))
            else:
                fig = go.Figure(data=go.Heatmap(z=data))
        else:
            # Default to scatter plot
            fig = go.Figure(data=go.Scatter(y=data, mode='markers'))
        
        fig.update_layout(
            title=widget.title,
            showlegend=True,
            template="plotly_white"
        )
        
        return fig
    
    def register_callback(self, widget_id: str, callback_func: Callable):
        """
        Register a callback for a widget.
        
        Args:
            widget_id: Widget ID
            callback_func: Callback function
        """
        if widget_id in self.widget_registry:
            widget = self.widget_registry[widget_id]
            widget.callbacks.append(callback_func)
            
            # Register with Dash app
            callback_id = f"callback-{widget_id}-{len(widget.callbacks)}"
            if callback_id not in self.callbacks_registered:
                self.app.callback(
                    Output(f"widget-{widget_id}", "children"),
                    [Input(f"filter-{widget_id}", "value")],
                    prevent_initial_call=False
                )(callback_func)
                self.callbacks_registered.add(callback_id)
    
    def set_current_layout(self, layout_id: str):
        """Set the current active layout."""
        if layout_id in self.layouts:
            self.current_layout = self.layouts[layout_id]
            self._update_app_layout()
        else:
            raise ValueError(f"Layout {layout_id} not found")
    
    def _update_app_layout(self):
        """Update the Dash app layout."""
        if self.current_layout:
            self.app.layout = self._generate_dash_layout(self.current_layout)
    
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
    
    def refresh_data_source(self, source_id: str):
        """Refresh a data source."""
        if source_id in self.data_sources:
            source = self.data_sources[source_id]
            if source['refresh_func']:
                source['data'] = source['refresh_func']()
                source['last_updated'] = datetime.now()
                logger.info(f"Refreshed data source {source_id}")
    
    def export_layout(self, layout_id: str, format: str = "json") -> str:
        """
        Export layout configuration.
        
        Args:
            layout_id: Layout to export
            format: Export format (json, yaml)
            
        Returns:
            str: Exported configuration
        """
        if layout_id not in self.layouts:
            raise ValueError(f"Layout {layout_id} not found")
        
        layout = self.layouts[layout_id]
        
        if format == "json":
            return json.dumps(layout.to_dict(), indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def import_layout(self, config: str, format: str = "json") -> str:
        """
        Import layout configuration.
        
        Args:
            config: Configuration string
            format: Import format (json, yaml)
            
        Returns:
            str: Layout ID
        """
        if format == "json":
            layout_data = json.loads(config)
            layout = DashboardLayout.from_dict(layout_data)
            self.layouts[layout.id] = layout
            return layout.id
        else:
            raise ValueError(f"Unsupported import format: {format}")
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics."""
        total_widgets = sum(len(layout.widgets) for layout in self.layouts.values())
        widget_types = {}
        
        for layout in self.layouts.values():
            for widget in layout.widgets:
                widget_type = widget.widget_type.value
                widget_types[widget_type] = widget_types.get(widget_type, 0) + 1
        
        return {
            'total_layouts': len(self.layouts),
            'total_widgets': total_widgets,
            'widget_types': widget_types,
            'data_sources': len(self.data_sources),
            'registered_callbacks': len(self.callbacks_registered)
        }
    
    def run_dashboard(self, host: str = "127.0.0.1", port: int = 8050, debug: bool = False):
        """
        Run the dashboard application.
        
        Args:
            host: Host to run on
            port: Port to run on
            debug: Enable debug mode
        """
        if not self.current_layout:
            self.set_current_layout("default")
        
        logger.info(f"Starting dashboard on {host}:{port}")
        self.app.run_server(host=host, port=port, debug=debug)
