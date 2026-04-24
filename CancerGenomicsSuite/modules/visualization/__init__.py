"""
Visualization Module

This module provides comprehensive visualization capabilities for the Cancer Genomics Analysis Suite.
It includes plotting functionality, dashboard creation, and theme management for genomics data visualization.

Components:
- PlotManager: Handles various types of plots for genomics data
- DashboardBuilder: Creates and manages interactive dashboards
- ThemeManager: Manages visualization themes and styling
"""

from .plots import PlotManager, PlotType, PlotConfig
from .dashboards import DashboardBuilder, DashboardLayout, DashboardWidget
from .themes import ThemeManager, VisualizationTheme, ColorPalette

__all__ = [
    'PlotManager',
    'PlotType',
    'PlotConfig',
    'DashboardBuilder',
    'DashboardLayout',
    'DashboardWidget',
    'ThemeManager',
    'VisualizationTheme',
    'ColorPalette'
]

__version__ = '1.0.0'
__author__ = 'Cancer Genomics Analysis Suite'
