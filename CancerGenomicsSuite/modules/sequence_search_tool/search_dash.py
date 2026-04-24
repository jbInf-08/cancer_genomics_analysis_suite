"""
Sequence Search Tool Dashboard

This module provides an interactive dashboard for sequence search and alignment,
allowing users to upload sequences, perform searches, and visualize results
through a web-based interface.
"""

import logging
from typing import Dict, List, Any, Optional
import dash
from dash import html, dcc, dash_table, Input, Output, State, callback_context
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import json
import base64
import io

from .aligner import SequenceAligner, AlignmentConfig


class SearchDashboard:
    """
    Interactive dashboard for sequence search and alignment.
    
    This class provides methods to create and manage an interactive
    web-based dashboard for sequence search operations.
    """
    
    def __init__(self, app: dash.Dash):
        """
        Initialize the search dashboard.
        
        Args:
            app (dash.Dash): Dash application instance
        """
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.aligner = SequenceAligner()
        
        # Register callbacks
        self._register_callbacks()
    
    def get_layout(self) -> html.Div:
        """
        Get the dashboard layout.
        
        Returns:
            html.Div: Dashboard layout
        """
        return html.Div([
            # Header
            html.Div([
                html.H1("Sequence Search Tool", className="text-center mb-4"),
                html.P("Comprehensive sequence search and alignment tools for cancer genomics research", 
                       className="text-center text-muted")
            ], className="jumbotron"),
            
            # Main content
            html.Div([
                # Database management section
                html.Div([
                    html.H3("Sequence Database"),
                    html.Div([
                        html.Label("Upload Sequence File (FASTA/GenBank):", className="form-label"),
                        dcc.Upload(
                            id='upload-sequence-file',
                            children=html.Div([
                                'Drag and Drop or ',
                                html.A('Select Sequence File')
                            ]),
                            style={
                                'width': '100%', 'height': '60px', 'lineHeight': '60px',
                                'borderWidth': '1px', 'borderStyle': 'dashed',
                                'borderRadius': '5px', 'textAlign': 'center'
                            },
                            multiple=False
                        ),
                        html.Br(),
                        html.Div([
                            html.Button('Clear Database', id='clear-database-btn', 
                                      className="btn btn-danger me-2"),
                            html.Button('Export Database', id='export-database-btn', 
                                      className="btn btn-success")
                        ], className="mt-2")
                    ])
                ], className="card mb-4"),
                
                # Manual sequence input
                html.Div([
                    html.H3("Add Sequence Manually"),
                    html.Div([
                        html.Div([
                            html.Label("Sequence ID:", className="form-label"),
                            dcc.Input(
                                id='sequence-id',
                                type='text',
                                placeholder='Enter sequence ID...',
                                className="form-control mb-2"
                            ),
                            html.Label("Description:", className="form-label"),
                            dcc.Input(
                                id='sequence-description',
                                type='text',
                                placeholder='Enter description...',
                                className="form-control mb-2"
                            ),
                            html.Label("Sequence:", className="form-label"),
                            dcc.Textarea(
                                id='manual-sequence',
                                placeholder='Enter DNA or protein sequence...',
                                style={'width': '100%', 'height': 150},
                                className="form-control mb-2"
                            ),
                            html.Button('Add Sequence', id='add-sequence-btn', 
                                      className="btn btn-primary")
                        ], className="col-md-6"),
                        html.Div([
                            html.H5("Database Statistics"),
                            html.Div(id='database-stats')
                        ], className="col-md-6")
                    ], className="row")
                ], className="card mb-4"),
                
                # Search configuration
                html.Div([
                    html.H3("Search Configuration"),
                    html.Div([
                        html.Div([
                            html.Label("Alignment Type:", className="form-label"),
                            dcc.Dropdown(
                                id='alignment-type',
                                options=[
                                    {'label': 'Local', 'value': 'local'},
                                    {'label': 'Global', 'value': 'global'},
                                    {'label': 'Semi-global', 'value': 'semiglobal'}
                                ],
                                value='local',
                                className="mb-2"
                            ),
                            html.Label("Substitution Matrix:", className="form-label"),
                            dcc.Dropdown(
                                id='substitution-matrix',
                                options=[
                                    {'label': 'BLOSUM62', 'value': 'BLOSUM62'},
                                    {'label': 'PAM250', 'value': 'PAM250'},
                                    {'label': 'BLOSUM50', 'value': 'BLOSUM50'}
                                ],
                                value='BLOSUM62',
                                className="mb-2"
                            )
                        ], className="col-md-4"),
                        html.Div([
                            html.Label("Match Score:", className="form-label"),
                            dcc.Input(
                                id='match-score',
                                type='number',
                                value=2,
                                className="form-control mb-2"
                            ),
                            html.Label("Mismatch Penalty:", className="form-label"),
                            dcc.Input(
                                id='mismatch-penalty',
                                type='number',
                                value=-1,
                                className="form-control mb-2"
                            )
                        ], className="col-md-4"),
                        html.Div([
                            html.Label("Gap Open Penalty:", className="form-label"),
                            dcc.Input(
                                id='gap-open-penalty',
                                type='number',
                                value=-2,
                                className="form-control mb-2"
                            ),
                            html.Label("Gap Extend Penalty:", className="form-label"),
                            dcc.Input(
                                id='gap-extend-penalty',
                                type='number',
                                value=-0.5,
                                step=0.1,
                                className="form-control mb-2"
                            )
                        ], className="col-md-4")
                    ], className="row")
                ], className="card mb-4"),
                
                # Sequence search
                html.Div([
                    html.H3("Sequence Search"),
                    html.Div([
                        html.Label("Query Sequence:", className="form-label"),
                        dcc.Textarea(
                            id='query-sequence',
                            placeholder='Enter query sequence to search...',
                            style={'width': '100%', 'height': 150},
                            className="form-control mb-3"
                        ),
                        html.Div([
                            html.Button('Search Sequence', id='search-sequence-btn', 
                                      className="btn btn-primary me-2"),
                            html.Button('Clear Query', id='clear-query-btn', 
                                      className="btn btn-secondary")
                        ])
                    ])
                ], className="card mb-4"),
                
                # Pattern search
                html.Div([
                    html.H3("Pattern Search"),
                    html.Div([
                        html.Label("Search Pattern (Regex):", className="form-label"),
                        dcc.Input(
                            id='search-pattern',
                            type='text',
                            placeholder='Enter regex pattern...',
                            className="form-control mb-3"
                        ),
                        html.Button('Search Pattern', id='search-pattern-btn', 
                                  className="btn btn-primary")
                    ])
                ], className="card mb-4"),
                
                # Search results
                html.Div([
                    html.H3("Search Results"),
                    html.Div(id='search-results')
                ], className="card mb-4"),
                
                # Visualizations
                html.Div([
                    html.H3("Visualizations"),
                    html.Div(id='search-visualizations')
                ], className="card mb-4")
                
            ], className="container-fluid")
        ])
    
    def _register_callbacks(self):
        """Register dashboard callbacks."""
        
        @self.app.callback(
            [Output('database-stats', 'children')],
            [Input('upload-sequence-file', 'contents'),
             Input('add-sequence-btn', 'n_clicks'),
             Input('clear-database-btn', 'n_clicks')]
        )
        def update_database_stats(upload_contents, add_clicks, clear_clicks):
            """Update database statistics display."""
            stats = self.aligner.get_database_statistics()
            
            stats_display = [
                html.P(f"Total Sequences: {stats['total_sequences']}"),
                html.P(f"Total Length: {stats['total_length']:,} bp"),
                html.P(f"Average Length: {stats['average_length']:.1f} bp"),
                html.P(f"Sequence Types: {', '.join(f'{k}: {v}' for k, v in stats['sequence_types'].items())}")
            ]
            
            return [html.Div(stats_display)]
        
        @self.app.callback(
            [Output('upload-sequence-file', 'contents')],
            [Input('upload-sequence-file', 'contents')],
            [State('upload-sequence-file', 'filename')]
        )
        def handle_sequence_upload(contents, filename):
            """Handle sequence file upload."""
            if contents:
                try:
                    content_type, content_string = contents.split(',')
                    decoded = base64.b64decode(content_string)
                    
                    # Determine file format
                    if filename.endswith('.fa') or filename.endswith('.fasta'):
                        file_format = 'fasta'
                    elif filename.endswith('.gb') or filename.endswith('.genbank'):
                        file_format = 'genbank'
                    else:
                        file_format = 'fasta'  # default
                    
                    # Save to temporary file
                    temp_file = f"temp_{filename}"
                    with open(temp_file, 'wb') as f:
                        f.write(decoded)
                    
                    # Load sequences
                    result = self.aligner.load_sequences_from_file(temp_file, file_format)
                    
                    # Clean up temp file
                    import os
                    os.remove(temp_file)
                    
                    if result['success']:
                        self.logger.info(f"Loaded {result['loaded_sequences']} sequences")
                    else:
                        self.logger.error(f"Error loading sequences: {result['error']}")
                
                except Exception as e:
                    self.logger.error(f"Error processing uploaded file: {e}")
            
            return [None]  # Clear upload component
        
        @self.app.callback(
            [Output('sequence-id', 'value'),
             Output('sequence-description', 'value'),
             Output('manual-sequence', 'value')],
            [Input('add-sequence-btn', 'n_clicks')],
            [State('sequence-id', 'value'),
             State('sequence-description', 'value'),
             State('manual-sequence', 'value')]
        )
        def add_sequence(n_clicks, seq_id, description, sequence):
            """Add sequence manually to database."""
            if n_clicks and seq_id and sequence:
                success = self.aligner.add_sequence_to_database(
                    seq_id, sequence, description or ""
                )
                if success:
                    return "", "", ""  # Clear inputs
            return dash.no_update, dash.no_update, dash.no_update
        
        @self.app.callback(
            [Output('search-results', 'children'),
             Output('search-visualizations', 'children')],
            [Input('search-sequence-btn', 'n_clicks'),
             Input('search-pattern-btn', 'n_clicks')],
            [State('query-sequence', 'value'),
             State('search-pattern', 'value'),
             State('alignment-type', 'value'),
             State('substitution-matrix', 'value'),
             State('match-score', 'value'),
             State('mismatch-penalty', 'value'),
             State('gap-open-penalty', 'value'),
             State('gap-extend-penalty', 'value')]
        )
        def perform_search(seq_clicks, pattern_clicks, query_seq, pattern, 
                          align_type, matrix, match_score, mismatch_penalty,
                          gap_open, gap_extend):
            """Perform sequence or pattern search."""
            ctx = callback_context
            if not ctx.triggered:
                return html.P("Configure search parameters and click search"), html.Div()
            
            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
            
            # Update aligner configuration
            config = AlignmentConfig(
                alignment_type=align_type or 'local',
                substitution_matrix=matrix or 'BLOSUM62',
                match_score=match_score or 2,
                mismatch_penalty=mismatch_penalty or -1,
                gap_open_penalty=gap_open or -2,
                gap_extend_penalty=gap_extend or -0.5
            )
            self.aligner.config = config
            
            try:
                if trigger_id == 'search-sequence-btn' and query_seq:
                    # Perform sequence search
                    results = self.aligner.search_sequence(query_seq, "Query")
                    results_display = self._create_sequence_search_results(results)
                    visualizations = self._create_sequence_visualizations(results)
                    return results_display, visualizations
                
                elif trigger_id == 'search-pattern-btn' and pattern:
                    # Perform pattern search
                    results = self.aligner.search_pattern(pattern, "Pattern")
                    results_display = self._create_pattern_search_results(results)
                    visualizations = self._create_pattern_visualizations(results)
                    return results_display, visualizations
                
                else:
                    return html.P("Enter query sequence or pattern and click search"), html.Div()
                    
            except Exception as e:
                error_msg = f"Search failed: {str(e)}"
                self.logger.error(error_msg)
                return html.Div([
                    html.H4("Search Error", className="text-danger"),
                    html.P(error_msg)
                ]), html.Div()
        
        @self.app.callback(
            [Output('query-sequence', 'value'),
             Output('search-pattern', 'value')],
            [Input('clear-query-btn', 'n_clicks')]
        )
        def clear_query(n_clicks):
            """Clear query inputs."""
            if n_clicks:
                return "", ""
            return dash.no_update, dash.no_update
    
    def _create_sequence_search_results(self, results: Dict[str, Any]) -> html.Div:
        """Create sequence search results display."""
        if not results.get('valid', False):
            return html.Div([
                html.H4("Search Error", className="text-danger"),
                html.P(f"Errors: {', '.join(results.get('errors', []))}")
            ])
        
        components = []
        
        # Query information
        components.append(html.H4("Query Information"))
        components.append(html.P(f"Query: {results.get('query_name', 'Unknown')}"))
        components.append(html.P(f"Type: {results.get('query_type', 'Unknown')}"))
        components.append(html.P(f"Length: {results.get('query_length', 0)} bp"))
        
        # Matches
        matches = results.get('matches', [])
        if matches:
            components.append(html.H4(f"Found {len(matches)} Matches"))
            
            # Create matches table
            matches_data = []
            for match in matches:
                matches_data.append({
                    'Target ID': match['target_id'],
                    'Description': match['target_description'][:50] + '...' if len(match['target_description']) > 50 else match['target_description'],
                    'Score': f"{match['score']:.1f}",
                    'Identity': f"{match['identity']*100:.1f}%",
                    'Coverage': f"{match['coverage']*100:.1f}%",
                    'Length': match['alignment_length']
                })
            
            components.append(dash_table.DataTable(
                data=matches_data,
                columns=[{"name": i, "id": i} for i in matches_data[0].keys()],
                style_cell={'textAlign': 'left', 'fontSize': 12},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                page_size=10
            ))
            
            # Show detailed alignments
            components.append(html.H4("Detailed Alignments"))
            for i, match in enumerate(matches[:3]):  # Show top 3 alignments
                if match['alignment']:
                    components.append(html.Div([
                        html.H5(f"Match {i+1}: {match['target_id']}"),
                        html.Pre(match['alignment'], style={'fontSize': 10, 'whiteSpace': 'pre-wrap'})
                    ]))
        else:
            components.append(html.P("No matches found"))
        
        return html.Div(components)
    
    def _create_pattern_search_results(self, results: Dict[str, Any]) -> html.Div:
        """Create pattern search results display."""
        if 'error' in results:
            return html.Div([
                html.H4("Pattern Search Error", className="text-danger"),
                html.P(results['error'])
            ])
        
        components = []
        
        # Pattern information
        components.append(html.H4("Pattern Information"))
        components.append(html.P(f"Pattern: {results.get('pattern', 'Unknown')}"))
        
        # Matches
        matches = results.get('matches', [])
        if matches:
            components.append(html.H4(f"Found {len(matches)} Matches"))
            
            # Create matches table
            matches_data = []
            for match in matches:
                matches_data.append({
                    'Sequence ID': match['sequence_id'],
                    'Description': match['sequence_description'][:50] + '...' if len(match['sequence_description']) > 50 else match['sequence_description'],
                    'Position': f"{match['start_position']}-{match['end_position']}",
                    'Matched Sequence': match['matched_sequence'],
                    'Context': match['context']
                })
            
            components.append(dash_table.DataTable(
                data=matches_data,
                columns=[{"name": i, "id": i} for i in matches_data[0].keys()],
                style_cell={'textAlign': 'left', 'fontSize': 12},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                page_size=10
            ))
        else:
            components.append(html.P("No pattern matches found"))
        
        return html.Div(components)
    
    def _create_sequence_visualizations(self, results: Dict[str, Any]) -> html.Div:
        """Create visualizations for sequence search results."""
        components = []
        
        matches = results.get('matches', [])
        if not matches:
            return html.Div()
        
        # Score distribution
        scores = [match['score'] for match in matches]
        identities = [match['identity'] * 100 for match in matches]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=scores,
            y=identities,
            mode='markers',
            text=[match['target_id'] for match in matches],
            marker=dict(
                size=10,
                color=identities,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Identity %")
            ),
            name='Matches'
        ))
        
        fig.update_layout(
            title="Alignment Score vs Identity",
            xaxis_title="Alignment Score",
            yaxis_title="Identity (%)"
        )
        
        components.append(dcc.Graph(figure=fig))
        
        # Top matches bar chart
        top_matches = matches[:10]  # Top 10 matches
        match_names = [match['target_id'][:20] + '...' if len(match['target_id']) > 20 else match['target_id'] for match in top_matches]
        match_scores = [match['score'] for match in top_matches]
        
        fig2 = go.Figure(data=[
            go.Bar(x=match_names, y=match_scores, marker_color='lightblue')
        ])
        fig2.update_layout(
            title="Top 10 Alignment Scores",
            xaxis_title="Target Sequence",
            yaxis_title="Alignment Score",
            xaxis_tickangle=-45
        )
        
        components.append(dcc.Graph(figure=fig2))
        
        return html.Div(components)
    
    def _create_pattern_visualizations(self, results: Dict[str, Any]) -> html.Div:
        """Create visualizations for pattern search results."""
        components = []
        
        matches = results.get('matches', [])
        if not matches:
            return html.Div()
        
        # Matches per sequence
        sequence_counts = {}
        for match in matches:
            seq_id = match['sequence_id']
            sequence_counts[seq_id] = sequence_counts.get(seq_id, 0) + 1
        
        if sequence_counts:
            fig = go.Figure(data=[
                go.Bar(x=list(sequence_counts.keys()), y=list(sequence_counts.values()),
                      marker_color='lightgreen')
            ])
            fig.update_layout(
                title="Pattern Matches per Sequence",
                xaxis_title="Sequence ID",
                yaxis_title="Number of Matches",
                xaxis_tickangle=-45
            )
            
            components.append(dcc.Graph(figure=fig))
        
        return html.Div(components)


# Legacy function for backward compatibility
def register_callbacks(app):
    """Register callbacks for this module (legacy function)."""
    dashboard = SearchDashboard(app)
    return dashboard

# Legacy layout for backward compatibility
layout = html.Div([
    html.H1("Sequence Search Tool"),
    html.P("This module provides sequence search and alignment tools."),
    html.Div([
        html.Label("Upload Sequence File:"),
        dcc.Upload(
            id='upload-data',
            children=html.Div(['Drag and Drop or ', html.A('Select Files')]),
            style={'width': '100%', 'height': '60px', 'lineHeight': '60px', 'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px', 'textAlign': 'center'},
            multiple=False
        ),
        html.Div(id='search-output')
    ])
])
