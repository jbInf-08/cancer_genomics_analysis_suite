"""
Live Controls Module

Provides real-time control and interaction capabilities for the Cancer Genomics Analysis Suite.
Supports live data streaming, interactive controls, and real-time parameter adjustment.
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
import threading
import time
import queue
import websocket
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import zmq
import redis
import pika

logger = logging.getLogger(__name__)


class ControlType(Enum):
    """Types of live controls."""
    SLIDER = "slider"
    BUTTON = "button"
    DROPDOWN = "dropdown"
    TEXT_INPUT = "text_input"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    RANGE_SLIDER = "range_slider"
    TOGGLE = "toggle"
    KNOB = "knob"
    JOYSTICK = "joystick"
    CUSTOM = "custom"


class StreamType(Enum):
    """Types of data streams."""
    WEBSOCKET = "websocket"
    HTTP_POLLING = "http_polling"
    ZMQ = "zmq"
    REDIS = "redis"
    RABBITMQ = "rabbitmq"
    FILE_WATCH = "file_watch"
    DATABASE = "database"
    CUSTOM = "custom"


@dataclass
class ControlWidget:
    """Represents a live control widget."""
    id: str
    control_type: ControlType
    label: str
    value: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    options: List[Any] = field(default_factory=list)
    callback: Optional[Callable] = None
    update_interval: int = 100  # milliseconds
    enabled: bool = True
    visible: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert control to dictionary."""
        return {
            'id': self.id,
            'control_type': self.control_type.value,
            'label': self.label,
            'value': self.value,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'step': self.step,
            'options': self.options,
            'update_interval': self.update_interval,
            'enabled': self.enabled,
            'visible': self.visible,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ControlWidget':
        """Create control from dictionary."""
        data['control_type'] = ControlType(data['control_type'])
        return cls(**data)


@dataclass
class LiveDataStream:
    """Represents a live data stream."""
    id: str
    stream_type: StreamType
    source: str
    update_interval: int = 1000  # milliseconds
    buffer_size: int = 1000
    active: bool = True
    callback: Optional[Callable] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stream to dictionary."""
        return {
            'id': self.id,
            'stream_type': self.stream_type.value,
            'source': self.source,
            'update_interval': self.update_interval,
            'buffer_size': self.buffer_size,
            'active': self.active,
            'parameters': self.parameters,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LiveDataStream':
        """Create stream from dictionary."""
        data['stream_type'] = StreamType(data['stream_type'])
        return cls(**data)


class LiveControls:
    """
    Manages live controls and real-time data streaming.
    
    Features:
    - Real-time control widgets
    - Live data streaming from multiple sources
    - WebSocket and HTTP polling support
    - Message queue integration (ZMQ, Redis, RabbitMQ)
    - File watching and database monitoring
    - Custom control callbacks
    - Data buffering and processing
    """
    
    def __init__(self, app: dash.Dash = None, max_workers: int = 4):
        """
        Initialize LiveControls.
        
        Args:
            app: Dash application instance
            max_workers: Maximum number of worker threads
        """
        self.app = app
        self.max_workers = max_workers
        
        # Control and stream management
        self.controls = {}
        self.streams = {}
        self.data_buffers = {}
        self.callbacks = {}
        
        # Threading and async support
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.is_running = False
        self.worker_threads = {}
        
        # Message queue connections
        self.zmq_context = None
        self.redis_client = None
        self.rabbitmq_connection = None
        
        # WebSocket connections
        self.websocket_connections = {}
        
        # Initialize default controls
        self._initialize_default_controls()
    
    def _initialize_default_controls(self):
        """Initialize default control types."""
        self.control_creators = {
            ControlType.SLIDER: self._create_slider_control,
            ControlType.BUTTON: self._create_button_control,
            ControlType.DROPDOWN: self._create_dropdown_control,
            ControlType.TEXT_INPUT: self._create_text_input_control,
            ControlType.CHECKBOX: self._create_checkbox_control,
            ControlType.RADIO: self._create_radio_control,
            ControlType.RANGE_SLIDER: self._create_range_slider_control,
            ControlType.TOGGLE: self._create_toggle_control,
            ControlType.KNOB: self._create_knob_control,
            ControlType.JOYSTICK: self._create_joystick_control
        }
        
        self.stream_handlers = {
            StreamType.WEBSOCKET: self._handle_websocket_stream,
            StreamType.HTTP_POLLING: self._handle_http_polling_stream,
            StreamType.ZMQ: self._handle_zmq_stream,
            StreamType.REDIS: self._handle_redis_stream,
            StreamType.RABBITMQ: self._handle_rabbitmq_stream,
            StreamType.FILE_WATCH: self._handle_file_watch_stream,
            StreamType.DATABASE: self._handle_database_stream
        }
    
    def add_control(self, control: ControlWidget) -> str:
        """
        Add a live control widget.
        
        Args:
            control: Control widget to add
            
        Returns:
            str: Control ID
        """
        self.controls[control.id] = control
        
        # Register callback if provided
        if control.callback and self.app:
            self._register_control_callback(control)
        
        logger.info(f"Added live control: {control.label}")
        return control.id
    
    def remove_control(self, control_id: str) -> bool:
        """
        Remove a live control widget.
        
        Args:
            control_id: Control ID to remove
            
        Returns:
            bool: Success status
        """
        if control_id in self.controls:
            del self.controls[control_id]
            logger.info(f"Removed live control: {control_id}")
            return True
        return False
    
    def update_control_value(self, control_id: str, value: Any) -> bool:
        """
        Update a control's value.
        
        Args:
            control_id: Control ID
            value: New value
            
        Returns:
            bool: Success status
        """
        if control_id in self.controls:
            self.controls[control_id].value = value
            logger.info(f"Updated control {control_id} value to {value}")
            return True
        return False
    
    def add_data_stream(self, stream: LiveDataStream) -> str:
        """
        Add a live data stream.
        
        Args:
            stream: Data stream to add
            
        Returns:
            str: Stream ID
        """
        self.streams[stream.id] = stream
        self.data_buffers[stream.id] = []
        
        # Start stream handler if active
        if stream.active:
            self._start_stream_handler(stream)
        
        logger.info(f"Added data stream: {stream.id}")
        return stream.id
    
    def remove_data_stream(self, stream_id: str) -> bool:
        """
        Remove a live data stream.
        
        Args:
            stream_id: Stream ID to remove
            
        Returns:
            bool: Success status
        """
        if stream_id in self.streams:
            stream = self.streams[stream_id]
            stream.active = False
            
            # Stop stream handler
            if stream_id in self.worker_threads:
                self.worker_threads[stream_id].join(timeout=1)
                del self.worker_threads[stream_id]
            
            del self.streams[stream_id]
            del self.data_buffers[stream_id]
            
            logger.info(f"Removed data stream: {stream_id}")
            return True
        return False
    
    def start_live_controls(self):
        """Start live controls and data streaming."""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start all active streams
        for stream in self.streams.values():
            if stream.active:
                self._start_stream_handler(stream)
        
        logger.info("Started live controls")
    
    def stop_live_controls(self):
        """Stop live controls and data streaming."""
        self.is_running = False
        
        # Stop all streams
        for stream in self.streams.values():
            stream.active = False
        
        # Wait for worker threads to finish
        for thread in self.worker_threads.values():
            thread.join(timeout=2)
        
        self.worker_threads.clear()
        
        logger.info("Stopped live controls")
    
    def _register_control_callback(self, control: ControlWidget):
        """Register a callback for a control."""
        if not self.app or not control.callback:
            return
        
        # Create callback function
        def callback_wrapper(*args, **kwargs):
            try:
                result = control.callback(*args, **kwargs)
                return result
            except Exception as e:
                logger.error(f"Control callback error for {control.id}: {e}")
                return None
        
        # Register with Dash app
        self.app.callback(
            Output(f"control-output-{control.id}", "children"),
            [Input(f"control-{control.id}", "value")]
        )(callback_wrapper)
    
    def _start_stream_handler(self, stream: LiveDataStream):
        """Start a stream handler thread."""
        if stream.id in self.worker_threads:
            return
        
        handler = self.stream_handlers.get(stream.stream_type)
        if not handler:
            logger.error(f"No handler for stream type: {stream.stream_type}")
            return
        
        # Start handler in separate thread
        thread = threading.Thread(
            target=handler,
            args=(stream,),
            name=f"stream-{stream.id}",
            daemon=True
        )
        thread.start()
        self.worker_threads[stream.id] = thread
    
    def _handle_websocket_stream(self, stream: LiveDataStream):
        """Handle WebSocket data stream."""
        try:
            import websocket
            
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    self._process_stream_data(stream.id, data)
                except Exception as e:
                    logger.error(f"WebSocket message processing error: {e}")
            
            def on_error(ws, error):
                logger.error(f"WebSocket error: {error}")
            
            def on_close(ws, close_status_code, close_msg):
                logger.info("WebSocket connection closed")
            
            def on_open(ws):
                logger.info("WebSocket connection opened")
            
            ws = websocket.WebSocketApp(
                stream.source,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            
            while stream.active and self.is_running:
                ws.run_forever()
                time.sleep(stream.update_interval / 1000)
                
        except Exception as e:
            logger.error(f"WebSocket stream error: {e}")
    
    def _handle_http_polling_stream(self, stream: LiveDataStream):
        """Handle HTTP polling data stream."""
        try:
            import requests
            
            while stream.active and self.is_running:
                try:
                    response = requests.get(stream.source, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        self._process_stream_data(stream.id, data)
                except Exception as e:
                    logger.error(f"HTTP polling error: {e}")
                
                time.sleep(stream.update_interval / 1000)
                
        except Exception as e:
            logger.error(f"HTTP polling stream error: {e}")
    
    def _handle_zmq_stream(self, stream: LiveDataStream):
        """Handle ZeroMQ data stream."""
        try:
            if not self.zmq_context:
                self.zmq_context = zmq.Context()
            
            socket = self.zmq_context.socket(zmq.SUB)
            socket.connect(stream.source)
            socket.setsockopt(zmq.SUBSCRIBE, b"")
            
            while stream.active and self.is_running:
                try:
                    message = socket.recv_string(zmq.NOBLOCK)
                    data = json.loads(message)
                    self._process_stream_data(stream.id, data)
                except zmq.Again:
                    time.sleep(0.01)
                except Exception as e:
                    logger.error(f"ZMQ stream error: {e}")
                    time.sleep(1)
            
            socket.close()
            
        except Exception as e:
            logger.error(f"ZMQ stream error: {e}")
    
    def _handle_redis_stream(self, stream: LiveDataStream):
        """Handle Redis data stream."""
        try:
            if not self.redis_client:
                self.redis_client = redis.Redis.from_url(stream.source)
            
            while stream.active and self.is_running:
                try:
                    # Get data from Redis
                    data = self.redis_client.get(stream.parameters.get('key', 'data'))
                    if data:
                        data = json.loads(data)
                        self._process_stream_data(stream.id, data)
                except Exception as e:
                    logger.error(f"Redis stream error: {e}")
                
                time.sleep(stream.update_interval / 1000)
                
        except Exception as e:
            logger.error(f"Redis stream error: {e}")
    
    def _handle_rabbitmq_stream(self, stream: LiveDataStream):
        """Handle RabbitMQ data stream."""
        try:
            if not self.rabbitmq_connection:
                self.rabbitmq_connection = pika.BlockingConnection(
                    pika.URLParameters(stream.source)
                )
            
            channel = self.rabbitmq_connection.channel()
            queue_name = stream.parameters.get('queue', 'data_queue')
            
            def callback(ch, method, properties, body):
                try:
                    data = json.loads(body)
                    self._process_stream_data(stream.id, data)
                except Exception as e:
                    logger.error(f"RabbitMQ message processing error: {e}")
            
            channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=True
            )
            
            while stream.active and self.is_running:
                try:
                    self.rabbitmq_connection.process_data_events(time_limit=1)
                except Exception as e:
                    logger.error(f"RabbitMQ stream error: {e}")
                    time.sleep(1)
            
            channel.stop_consuming()
            
        except Exception as e:
            logger.error(f"RabbitMQ stream error: {e}")
    
    def _handle_file_watch_stream(self, stream: LiveDataStream):
        """Handle file watching data stream."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            
            class FileHandler(FileSystemEventHandler):
                def __init__(self, live_controls, stream_id):
                    self.live_controls = live_controls
                    self.stream_id = stream_id
                
                def on_modified(self, event):
                    if not event.is_directory:
                        try:
                            with open(event.src_path, 'r') as f:
                                data = json.load(f)
                                self.live_controls._process_stream_data(self.stream_id, data)
                        except Exception as e:
                            logger.error(f"File watch processing error: {e}")
            
            observer = Observer()
            observer.schedule(
                FileHandler(self, stream.id),
                stream.source,
                recursive=False
            )
            observer.start()
            
            while stream.active and self.is_running:
                time.sleep(1)
            
            observer.stop()
            observer.join()
            
        except Exception as e:
            logger.error(f"File watch stream error: {e}")
    
    def _handle_database_stream(self, stream: LiveDataStream):
        """Handle database monitoring data stream."""
        try:
            db_path = stream.parameters.get('db_path', stream.source)
            table_name = stream.parameters.get('table', 'data')
            last_id = 0
            
            while stream.active and self.is_running:
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # Get new records
                    cursor.execute(
                        f"SELECT * FROM {table_name} WHERE id > ? ORDER BY id",
                        (last_id,)
                    )
                    
                    rows = cursor.fetchall()
                    if rows:
                        # Get column names
                        cursor.execute(f"PRAGMA table_info({table_name})")
                        columns = [col[1] for col in cursor.fetchall()]
                        
                        # Convert to DataFrame
                        data = pd.DataFrame(rows, columns=columns)
                        self._process_stream_data(stream.id, data.to_dict('records'))
                        
                        # Update last ID
                        last_id = rows[-1][0]
                    
                    conn.close()
                    
                except Exception as e:
                    logger.error(f"Database stream error: {e}")
                
                time.sleep(stream.update_interval / 1000)
                
        except Exception as e:
            logger.error(f"Database stream error: {e}")
    
    def _process_stream_data(self, stream_id: str, data: Any):
        """Process incoming stream data."""
        try:
            # Add to buffer
            buffer = self.data_buffers.get(stream_id, [])
            buffer.append({
                'timestamp': datetime.now(),
                'data': data
            })
            
            # Maintain buffer size
            stream = self.streams.get(stream_id)
            if stream and len(buffer) > stream.buffer_size:
                buffer.pop(0)
            
            self.data_buffers[stream_id] = buffer
            
            # Call stream callback if provided
            if stream and stream.callback:
                try:
                    stream.callback(stream_id, data)
                except Exception as e:
                    logger.error(f"Stream callback error: {e}")
            
        except Exception as e:
            logger.error(f"Stream data processing error: {e}")
    
    def get_stream_data(self, stream_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """Get data from a stream buffer."""
        buffer = self.data_buffers.get(stream_id, [])
        if limit:
            return buffer[-limit:]
        return buffer
    
    def create_control_dashboard(self) -> html.Div:
        """Create a dashboard with live controls."""
        control_components = []
        
        for control in self.controls.values():
            if control.visible:
                component = self._create_control_component(control)
                control_components.append(
                    html.Div([
                        html.Label(control.label, className="control-label"),
                        component,
                        html.Div(id=f"control-output-{control.id}", className="control-output")
                    ], className="control-item")
                )
        
        return html.Div([
            html.H2("Live Controls", className="controls-title"),
            html.Div(control_components, className="controls-grid")
        ], className="controls-dashboard")
    
    def _create_control_component(self, control: ControlWidget) -> html.Div:
        """Create a control component."""
        creator = self.control_creators.get(control.control_type)
        if creator:
            return creator(control)
        else:
            return html.Div(f"Unknown control type: {control.control_type}")
    
    def _create_slider_control(self, control: ControlWidget) -> dcc.Slider:
        """Create a slider control."""
        return dcc.Slider(
            id=f"control-{control.id}",
            min=control.min_value or 0,
            max=control.max_value or 100,
            step=control.step or 1,
            value=control.value,
            disabled=not control.enabled,
            marks={i: str(i) for i in range(int(control.min_value or 0), int(control.max_value or 100) + 1, 10)}
        )
    
    def _create_button_control(self, control: ControlWidget) -> html.Button:
        """Create a button control."""
        return html.Button(
            control.label,
            id=f"control-{control.id}",
            className="btn btn-primary",
            disabled=not control.enabled
        )
    
    def _create_dropdown_control(self, control: ControlWidget) -> dcc.Dropdown:
        """Create a dropdown control."""
        return dcc.Dropdown(
            id=f"control-{control.id}",
            options=[{'label': opt, 'value': opt} for opt in control.options],
            value=control.value,
            disabled=not control.enabled
        )
    
    def _create_text_input_control(self, control: ControlWidget) -> dcc.Input:
        """Create a text input control."""
        return dcc.Input(
            id=f"control-{control.id}",
            type="text",
            value=control.value,
            disabled=not control.enabled
        )
    
    def _create_checkbox_control(self, control: ControlWidget) -> dcc.Checklist:
        """Create a checkbox control."""
        return dcc.Checklist(
            id=f"control-{control.id}",
            options=[{'label': opt, 'value': opt} for opt in control.options],
            value=control.value if isinstance(control.value, list) else [control.value],
            disabled=not control.enabled
        )
    
    def _create_radio_control(self, control: ControlWidget) -> dcc.RadioItems:
        """Create a radio control."""
        return dcc.RadioItems(
            id=f"control-{control.id}",
            options=[{'label': opt, 'value': opt} for opt in control.options],
            value=control.value,
            disabled=not control.enabled
        )
    
    def _create_range_slider_control(self, control: ControlWidget) -> dcc.RangeSlider:
        """Create a range slider control."""
        return dcc.RangeSlider(
            id=f"control-{control.id}",
            min=control.min_value or 0,
            max=control.max_value or 100,
            step=control.step or 1,
            value=control.value if isinstance(control.value, list) else [control.min_value or 0, control.max_value or 100],
            disabled=not control.enabled,
            marks={i: str(i) for i in range(int(control.min_value or 0), int(control.max_value or 100) + 1, 10)}
        )
    
    def _create_toggle_control(self, control: ControlWidget) -> dcc.Checklist:
        """Create a toggle control."""
        return dcc.Checklist(
            id=f"control-{control.id}",
            options=[{'label': '', 'value': 'on'}],
            value=['on'] if control.value else [],
            disabled=not control.enabled,
            style={'display': 'inline-block'}
        )
    
    def _create_knob_control(self, control: ControlWidget) -> html.Div:
        """Create a knob control (placeholder)."""
        return html.Div([
            html.Div(
                f"{control.value}",
                className="knob-display",
                style={'text-align': 'center', 'font-size': '24px'}
            ),
            dcc.Slider(
                id=f"control-{control.id}",
                min=control.min_value or 0,
                max=control.max_value or 100,
                step=control.step or 1,
                value=control.value,
                disabled=not control.enabled,
                vertical=True,
                style={'height': '200px'}
            )
        ], className="knob-control")
    
    def _create_joystick_control(self, control: ControlWidget) -> html.Div:
        """Create a joystick control (placeholder)."""
        return html.Div([
            html.Div(
                "Joystick Control",
                className="joystick-display",
                style={'text-align': 'center', 'padding': '20px', 'border': '1px solid #ccc', 'border-radius': '50%', 'width': '100px', 'height': '100px'}
            )
        ], className="joystick-control")
    
    def get_control_value(self, control_id: str) -> Any:
        """Get the current value of a control."""
        control = self.controls.get(control_id)
        return control.value if control else None
    
    def get_stream_statistics(self) -> Dict[str, Any]:
        """Get statistics about active streams."""
        stats = {
            'total_streams': len(self.streams),
            'active_streams': sum(1 for s in self.streams.values() if s.active),
            'total_controls': len(self.controls),
            'enabled_controls': sum(1 for c in self.controls.values() if c.enabled),
            'buffer_sizes': {stream_id: len(buffer) for stream_id, buffer in self.data_buffers.items()},
            'is_running': self.is_running
        }
        
        return stats
