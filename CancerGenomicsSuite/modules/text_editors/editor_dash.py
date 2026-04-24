"""
Text Editors Integration Dashboard

Provides a Dash interface for file editing, text processing, and editor management.
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import json
import os
from typing import Dict, List, Any
import logging

from .editor_client import TextEditorClient

logger = logging.getLogger(__name__)

# Initialize text editor client
editor_client = TextEditorClient()

# Dashboard layout
layout = html.Div([
    html.Div([
        html.H2("📝 Text Editors", className="section-title"),
        html.P("File editing, text processing, and editor management", className="section-description"),
    ], className="section-header"),
    
    # Available Editors section
    html.Div([
        html.H3("Available Editors", className="subsection-title"),
        html.Div([
            html.Div([
                html.Span("System: ", className="status-label"),
                html.Span(id="system-info", className="status-value"),
            ], className="status-item"),
            html.Div([
                html.Span("Available Editors: ", className="status-label"),
                html.Span(id="available-editors", className="status-value"),
            ], className="status-item"),
        ], className="status-container"),
        html.Button("Refresh Editors", id="refresh-editors", className="button secondary"),
        html.Div(id="editors-list", className="editors-list"),
    ], className="editors-section"),
    
    # File Operations section
    html.Div([
        html.H3("File Operations", className="subsection-title"),
        dcc.Tabs(id="file-operations-tabs", value="open", children=[
            dcc.Tab(label="Open File", value="open"),
            dcc.Tab(label="Create File", value="create"),
            dcc.Tab(label="Edit Content", value="edit"),
            dcc.Tab(label="Search & Replace", value="search"),
        ]),
        html.Div(id="file-operations-content", className="file-operations-content"),
    ], className="file-operations-section"),
    
    # File Browser section
    html.Div([
        html.H3("File Browser", className="subsection-title"),
        html.Div([
            html.Div([
                html.Label("Current Directory:", className="input-label"),
                dcc.Input(
                    id="current-directory",
                    type="text",
                    value=os.getcwd(),
                    className="input-field"
                ),
            ], className="input-group"),
            html.Div([
                html.Button("Browse", id="browse-directory", className="button secondary"),
                html.Button("Refresh", id="refresh-directory", className="button secondary"),
            ], className="button-group"),
        ], className="directory-controls"),
        html.Div(id="file-browser", className="file-browser"),
    ], className="file-browser-section"),
    
    # Text Processing section
    html.Div([
        html.H3("Text Processing", className="subsection-title"),
        dcc.Tabs(id="text-processing-tabs", value="info", children=[
            dcc.Tab(label="File Info", value="info"),
            dcc.Tab(label="Search", value="search"),
            dcc.Tab(label="Replace", value="replace"),
            dcc.Tab(label="Preview", value="preview"),
        ]),
        html.Div(id="text-processing-content", className="text-processing-content"),
    ], className="text-processing-section"),
    
    # Results section
    html.Div([
        html.H3("Results", className="subsection-title"),
        html.Div(id="editor-results", className="results-container"),
    ], className="results-section"),
    
    # Hidden divs for storing data
    html.Div(id="editor-data", style={"display": "none"}),
])

def register_callbacks(app):
    """Register callbacks for the text editor dashboard"""
    
    @app.callback(
        [Output("system-info", "children"),
         Output("available-editors", "children"),
         Output("editors-list", "children")],
        [Input("refresh-editors", "n_clicks")]
    )
    def update_editors_info(n_clicks):
        import platform
        
        system = f"{platform.system()} {platform.release()}"
        available = ", ".join(editor_client.get_available_editors())
        
        # Create editor cards
        editor_cards = []
        for editor in editor_client.get_available_editors():
            editor_info = editor_client.get_editor_info(editor)
            if editor_info['success']:
                info = editor_info['info']
                card = html.Div([
                    html.H4(info['name'], className="editor-name"),
                    html.P(info['description'], className="editor-description"),
                    html.P(f"Type: {info['type']}", className="editor-type"),
                    html.P(f"Path: {info['path']}", className="editor-path"),
                    html.Div([
                        html.Span("Features:", className="features-label"),
                        html.Ul([html.Li(feature) for feature in info['features']], className="features-list")
                    ], className="editor-features"),
                ], className="editor-card")
                editor_cards.append(card)
        
        return system, available, editor_cards
    
    @app.callback(
        Output("file-operations-content", "children"),
        [Input("file-operations-tabs", "value")]
    )
    def update_file_operations_content(active_tab):
        if active_tab == "open":
            return html.Div([
                html.H4("Open File with Editor"),
                html.Div([
                    html.Label("File Path:", className="input-label"),
                    dcc.Input(
                        id="open-file-path",
                        type="text",
                        placeholder="/path/to/file.txt",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Editor:", className="input-label"),
                    dcc.Dropdown(
                        id="open-editor",
                        options=[{'label': editor, 'value': editor} for editor in editor_client.get_available_editors()],
                        value=editor_client.get_available_editors()[0] if editor_client.get_available_editors() else None,
                        className="dropdown"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Line Number (optional):", className="input-label"),
                    dcc.Input(
                        id="open-line-number",
                        type="number",
                        placeholder="1",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Button("Open File", id="open-file", className="button primary"),
                html.Div(id="open-file-results", className="operation-results"),
            ])
        
        elif active_tab == "create":
            return html.Div([
                html.H4("Create New File"),
                html.Div([
                    html.Label("File Path:", className="input-label"),
                    dcc.Input(
                        id="create-file-path",
                        type="text",
                        placeholder="/path/to/newfile.txt",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Initial Content:", className="input-label"),
                    dcc.Textarea(
                        id="create-file-content",
                        placeholder="Enter initial content here...",
                        style={'width': '100%', 'height': '200px'},
                        className="textarea-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Editor:", className="input-label"),
                    dcc.Dropdown(
                        id="create-editor",
                        options=[{'label': editor, 'value': editor} for editor in editor_client.get_available_editors()],
                        value=editor_client.get_available_editors()[0] if editor_client.get_available_editors() else None,
                        className="dropdown"
                    ),
                ], className="input-group"),
                html.Button("Create and Open", id="create-file", className="button primary"),
                html.Div(id="create-file-results", className="operation-results"),
            ])
        
        elif active_tab == "edit":
            return html.Div([
                html.H4("Edit File Content"),
                html.Div([
                    html.Label("File Path:", className="input-label"),
                    dcc.Input(
                        id="edit-file-path",
                        type="text",
                        placeholder="/path/to/file.txt",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("New Content:", className="input-label"),
                    dcc.Textarea(
                        id="edit-file-content",
                        placeholder="Enter new content here...",
                        style={'width': '100%', 'height': '300px'},
                        className="textarea-field"
                    ),
                ], className="input-group"),
                html.Div([
                    dcc.Checklist(
                        id="edit-backup",
                        options=[{'label': 'Create backup', 'value': 'backup'}],
                        value=['backup'],
                        className="checkbox"
                    ),
                ], className="input-group"),
                html.Button("Save Changes", id="edit-file", className="button primary"),
                html.Div(id="edit-file-results", className="operation-results"),
            ])
        
        elif active_tab == "search":
            return html.Div([
                html.H4("Search and Replace"),
                html.Div([
                    html.Label("File Path:", className="input-label"),
                    dcc.Input(
                        id="search-file-path",
                        type="text",
                        placeholder="/path/to/file.txt",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Search Term:", className="input-label"),
                    dcc.Input(
                        id="search-term",
                        type="text",
                        placeholder="text to search for",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Replace With:", className="input-label"),
                    dcc.Input(
                        id="replace-term",
                        type="text",
                        placeholder="replacement text",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    dcc.Checklist(
                        id="search-options",
                        options=[
                            {'label': 'Case sensitive', 'value': 'case_sensitive'},
                            {'label': 'Create backup', 'value': 'backup'}
                        ],
                        value=['backup'],
                        className="checkbox"
                    ),
                ], className="input-group"),
                html.Button("Replace All", id="replace-text", className="button primary"),
                html.Div(id="replace-results", className="operation-results"),
            ])
    
    @app.callback(
        Output("open-file-results", "children"),
        [Input("open-file", "n_clicks")],
        [State("open-file-path", "value"),
         State("open-editor", "value"),
         State("open-line-number", "value")]
    )
    def open_file(n_clicks, file_path, editor, line_number):
        if n_clicks is None or not file_path or not editor:
            return ""
        
        try:
            result = editor_client.open_file(file_path, editor, line_number)
            
            if result['success']:
                return html.Div([
                    html.H5("✅ File opened successfully"),
                    html.P(f"File: {result['file_path']}"),
                    html.P(f"Editor: {result['editor']}"),
                    html.P(f"Line: {line_number}" if line_number else "Line: Not specified"),
                ])
            else:
                return html.Div([
                    html.H5("❌ Failed to open file"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error opening file: {e}")
            return html.P(f"❌ Error: {str(e)}")
    
    @app.callback(
        Output("create-file-results", "children"),
        [Input("create-file", "n_clicks")],
        [State("create-file-path", "value"),
         State("create-file-content", "value"),
         State("create-editor", "value")]
    )
    def create_file(n_clicks, file_path, content, editor):
        if n_clicks is None or not file_path or not editor:
            return ""
        
        try:
            # Create file with content
            result = editor_client.edit_file_content(file_path, content or "", backup=False)
            
            if result['success']:
                # Open with editor
                open_result = editor_client.open_file(file_path, editor)
                
                if open_result['success']:
                    return html.Div([
                        html.H5("✅ File created and opened successfully"),
                        html.P(f"File: {file_path}"),
                        html.P(f"Editor: {editor}"),
                        html.P(f"Size: {len(content or '')} characters"),
                    ])
                else:
                    return html.Div([
                        html.H5("✅ File created but failed to open"),
                        html.P(f"File: {file_path}"),
                        html.P(f"Error opening: {open_result['error']}"),
                    ])
            else:
                return html.Div([
                    html.H5("❌ Failed to create file"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error creating file: {e}")
            return html.P(f"❌ Error: {str(e)}")
    
    @app.callback(
        Output("edit-file-results", "children"),
        [Input("edit-file", "n_clicks")],
        [State("edit-file-path", "value"),
         State("edit-file-content", "value"),
         State("edit-backup", "value")]
    )
    def edit_file(n_clicks, file_path, content, backup_options):
        if n_clicks is None or not file_path or not content:
            return ""
        
        try:
            backup = 'backup' in backup_options
            result = editor_client.edit_file_content(file_path, content, backup=backup)
            
            if result['success']:
                return html.Div([
                    html.H5("✅ File updated successfully"),
                    html.P(f"File: {result['file_path']}"),
                    html.P(f"Backup created: {'Yes' if result['backup_created'] else 'No'}"),
                    html.P(f"Size: {len(content)} characters"),
                ])
            else:
                return html.Div([
                    html.H5("❌ Failed to update file"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error editing file: {e}")
            return html.P(f"❌ Error: {str(e)}")
    
    @app.callback(
        Output("replace-results", "children"),
        [Input("replace-text", "n_clicks")],
        [State("search-file-path", "value"),
         State("search-term", "value"),
         State("replace-term", "value"),
         State("search-options", "value")]
    )
    def replace_text(n_clicks, file_path, search_term, replace_term, options):
        if n_clicks is None or not file_path or not search_term:
            return ""
        
        try:
            case_sensitive = 'case_sensitive' in options
            backup = 'backup' in options
            
            result = editor_client.replace_in_file(
                file_path, search_term, replace_term or "", 
                case_sensitive=case_sensitive, backup=backup
            )
            
            if result['success']:
                return html.Div([
                    html.H5("✅ Text replaced successfully"),
                    html.P(f"File: {result['file_path']}"),
                    html.P(f"Replacements: {result['replacements']}"),
                    html.P(f"Backup created: {'Yes' if result['backup_created'] else 'No'}"),
                ])
            else:
                return html.Div([
                    html.H5("❌ Failed to replace text"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error replacing text: {e}")
            return html.P(f"❌ Error: {str(e)}")
    
    @app.callback(
        Output("file-browser", "children"),
        [Input("browse-directory", "n_clicks"),
         Input("refresh-directory", "n_clicks")],
        [State("current-directory", "value")]
    )
    def update_file_browser(browse_clicks, refresh_clicks, directory):
        if not directory or not os.path.exists(directory):
            directory = os.getcwd()
        
        try:
            files = []
            directories = []
            
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isdir(item_path):
                    directories.append({
                        'name': item,
                        'path': item_path,
                        'type': 'directory',
                        'size': '-'
                    })
                else:
                    size = os.path.getsize(item_path)
                    files.append({
                        'name': item,
                        'path': item_path,
                        'type': 'file',
                        'size': editor_client._format_file_size(size)
                    })
            
            # Sort directories first, then files
            all_items = sorted(directories, key=lambda x: x['name'].lower()) + \
                       sorted(files, key=lambda x: x['name'].lower())
            
            # Create file browser items
            browser_items = []
            for item in all_items:
                icon = "📁" if item['type'] == 'directory' else "📄"
                item_div = html.Div([
                    html.Span(icon, className="file-icon"),
                    html.Span(item['name'], className="file-name"),
                    html.Span(item['size'], className="file-size"),
                    html.Button(
                        "Open",
                        id={"type": "open-file", "path": item['path']},
                        className="button small"
                    )
                ], className="file-item")
                browser_items.append(item_div)
            
            return html.Div([
                html.H4(f"Contents of {directory}"),
                html.Div(browser_items, className="file-list")
            ])
            
        except Exception as e:
            logger.error(f"Error browsing directory: {e}")
            return html.P(f"❌ Error: {str(e)}")
    
    @app.callback(
        Output("text-processing-content", "children"),
        [Input("text-processing-tabs", "value")]
    )
    def update_text_processing_content(active_tab):
        if active_tab == "info":
            return html.Div([
                html.H4("File Information"),
                html.Div([
                    html.Label("File Path:", className="input-label"),
                    dcc.Input(
                        id="info-file-path",
                        type="text",
                        placeholder="/path/to/file.txt",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Button("Get File Info", id="get-file-info", className="button primary"),
                html.Div(id="file-info-results", className="info-results"),
            ])
        
        elif active_tab == "search":
            return html.Div([
                html.H4("Search in File"),
                html.Div([
                    html.Label("File Path:", className="input-label"),
                    dcc.Input(
                        id="search-file-path-info",
                        type="text",
                        placeholder="/path/to/file.txt",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Search Term:", className="input-label"),
                    dcc.Input(
                        id="search-term-info",
                        type="text",
                        placeholder="text to search for",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    dcc.Checklist(
                        id="search-case-sensitive",
                        options=[{'label': 'Case sensitive', 'value': 'case_sensitive'}],
                        value=[],
                        className="checkbox"
                    ),
                ], className="input-group"),
                html.Button("Search", id="search-in-file", className="button primary"),
                html.Div(id="search-results", className="search-results"),
            ])
        
        elif active_tab == "preview":
            return html.Div([
                html.H4("File Preview"),
                html.Div([
                    html.Label("File Path:", className="input-label"),
                    dcc.Input(
                        id="preview-file-path",
                        type="text",
                        placeholder="/path/to/file.txt",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Button("Preview File", id="preview-file", className="button primary"),
                html.Div(id="preview-results", className="preview-results"),
            ])
    
    @app.callback(
        Output("file-info-results", "children"),
        [Input("get-file-info", "n_clicks")],
        [State("info-file-path", "value")]
    )
    def get_file_info(n_clicks, file_path):
        if n_clicks is None or not file_path:
            return ""
        
        try:
            result = editor_client.get_file_info(file_path)
            
            if result['success']:
                return html.Div([
                    html.H5("📄 File Information"),
                    html.Div([
                        html.P(f"Path: {result['file_path']}"),
                        html.P(f"Size: {result['size_human']} ({result['size']} bytes)"),
                        html.P(f"Lines: {result['lines']}"),
                        html.P(f"Encoding: {result['encoding']}"),
                        html.P(f"Text File: {'Yes' if result['is_text'] else 'No'}"),
                        html.P(f"Modified: {result['modified']}"),
                    ], className="file-info-details"),
                    html.Div([
                        html.H6("Preview:"),
                        html.Pre(result['preview'], className="file-preview")
                    ], className="file-preview-section")
                ])
            else:
                return html.Div([
                    html.H5("❌ Failed to get file info"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return html.P(f"❌ Error: {str(e)}")
    
    @app.callback(
        Output("search-results", "children"),
        [Input("search-in-file", "n_clicks")],
        [State("search-file-path-info", "value"),
         State("search-term-info", "value"),
         State("search-case-sensitive", "value")]
    )
    def search_in_file(n_clicks, file_path, search_term, options):
        if n_clicks is None or not file_path or not search_term:
            return ""
        
        try:
            case_sensitive = 'case_sensitive' in options
            result = editor_client.search_in_file(file_path, search_term, case_sensitive)
            
            if result['success']:
                matches = result['matches']
                if matches:
                    match_items = []
                    for match in matches[:20]:  # Show first 20 matches
                        match_item = html.Div([
                            html.Span(f"Line {match['line_number']}:", className="match-line"),
                            html.Span(match['line_content'], className="match-content"),
                        ], className="match-item")
                        match_items.append(match_item)
                    
                    return html.Div([
                        html.H5(f"🔍 Search Results ({result['total_matches']} matches)"),
                        html.P(f"Search term: '{result['search_term']}'"),
                        html.P(f"File: {result['file_path']}"),
                        html.Div(match_items, className="match-list")
                    ])
                else:
                    return html.Div([
                        html.H5("🔍 No matches found"),
                        html.P(f"Search term: '{search_term}'"),
                        html.P(f"File: {file_path}"),
                    ])
            else:
                return html.Div([
                    html.H5("❌ Search failed"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error searching in file: {e}")
            return html.P(f"❌ Error: {str(e)}")
    
    @app.callback(
        Output("preview-results", "children"),
        [Input("preview-file", "n_clicks")],
        [State("preview-file-path", "value")]
    )
    def preview_file(n_clicks, file_path):
        if n_clicks is None or not file_path:
            return ""
        
        try:
            result = editor_client.read_file_content(file_path)
            
            if result['success']:
                return html.Div([
                    html.H5("👁️ File Preview"),
                    html.Div([
                        html.P(f"File: {result['file_path']}"),
                        html.P(f"Size: {result['size']} bytes"),
                        html.P(f"Lines: {result['lines']}"),
                    ], className="preview-info"),
                    html.Div([
                        html.H6("Content:"),
                        html.Pre(result['content'], className="file-content")
                    ], className="preview-content")
                ])
            else:
                return html.Div([
                    html.H5("❌ Failed to preview file"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error previewing file: {e}")
            return html.P(f"❌ Error: {str(e)}")
