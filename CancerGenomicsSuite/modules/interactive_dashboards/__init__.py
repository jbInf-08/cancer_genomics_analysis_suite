"""
Interactive Dashboards Module

This module provides comprehensive interactive dashboard capabilities for the Cancer Genomics Analysis Suite.
It includes dashboard loading, live controls, and real-time data visualization.

Components:
- DashboardLoader: Handles dynamic dashboard loading and management
- LiveControls: Provides real-time control and interaction capabilities
"""

from .dashboard_loader import DashboardLoader, DashboardConfig, DashboardType, DashboardWidget
from .live_controls import LiveControls, ControlType, ControlWidget, LiveDataStream

__all__ = [
    'DashboardLoader',
    'DashboardConfig',
    'DashboardType',
    'DashboardWidget',
    'LiveControls',
    'ControlType',
    'ControlWidget',
    'LiveDataStream'
]

__version__ = '1.0.0'
__author__ = 'Cancer Genomics Analysis Suite'
