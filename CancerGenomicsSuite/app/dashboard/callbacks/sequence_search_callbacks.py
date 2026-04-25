"""
Sequence Search and Analysis Callbacks

This module contains all Dash callbacks related to sequence search and analysis,
including DNA/RNA sequence searching, pattern matching, and sequence comparison tools.

Features:
- Sequence search and pattern matching
- BLAST-like sequence alignment
- Sequence similarity analysis
- Motif discovery and analysis
- Sequence annotation and visualization
- Interactive sequence browser
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context, no_update
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import logging
import re
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqUtils import GC, molecular_weight
from Bio.SeqUtils.ProtParam import ProteinAnalysis

# Import database models and utilities
from ...orm.models import DataFile
from ...orm import db

logger = logging.getLogger(__name__)


def register_sequence_search_callbacks(app):
    """
    Register all sequence search related callbacks with the Dash app.
    
    Args:
        app: Dash application instance
    """
    
    @app.callback(
        [Output('sequence-search-results', 'children'),
         Output('sequence-search-stats', 'children'),
         Output('sequence-search-loading', 'children')],
        [Input('sequence-search-btn', 'n_clicks')],
        [State('sequence-search-input', 'value'),
         State('sequence-search-type', 'value'),
         State('sequence-search-database', 'value'),
         State('sequence-search-parameters', 'value')]
    )
    def perform_sequence_search(n_clicks, sequence_input, search_type, database, parameters):
        """
        Perform sequence search based on user input.
        
        Args:
            n_clicks: Number of search button clicks
            sequence_input: Input sequence to search
            search_type: Type of search (exact, fuzzy, pattern)
            database: Database to search against
            parameters: Search parameters (JSON string)
            
        Returns:
            Tuple of (results_html, stats_html, loading_component)
        """
        if not n_clicks or not sequence_input:
            return "Enter a sequence to search", "No search performed", no_update
        
        try:
            # Validate sequence input
            sequence = sequence_input.strip().upper()
            if not is_valid_sequence(sequence, search_type):
                return "Invalid sequence format", "Invalid input", no_update
            
            # Perform search based on type
            if search_type == 'exact':
                results = perform_exact_search(sequence, database)
            elif search_type == 'fuzzy':
                results = perform_fuzzy_search(sequence, database, parameters)
            elif search_type == 'pattern':
                results = perform_pattern_search(sequence, database)
            else:
                results = perform_exact_search(sequence, database)
            
            # Generate results HTML
            results_html = generate_search_results_html(results)
            
            # Generate statistics
            stats_html = generate_sequence_stats(sequence, results)
            
            return results_html, stats_html, no_update
            
        except Exception as e:
            logger.error(f"Error performing sequence search: {e}")
            return f"Error: {str(e)}", "Search failed", no_update
    
    @app.callback(
        Output('sequence-analysis-results', 'children'),
        [Input('sequence-analyze-btn', 'n_clicks')],
        [State('sequence-analyze-input', 'value'),
         State('sequence-analyze-type', 'value')]
    )
    def analyze_sequence(n_clicks, sequence_input, analysis_type):
        """
        Analyze sequence properties and characteristics.
        
        Args:
            n_clicks: Number of analyze button clicks
            sequence_input: Input sequence to analyze
            analysis_type: Type of analysis (DNA, RNA, protein)
            
        Returns:
            HTML content with analysis results
        """
        if not n_clicks or not sequence_input:
            return "Enter a sequence to analyze"
        
        try:
            sequence = sequence_input.strip().upper()
            
            if analysis_type == 'DNA':
                analysis_results = analyze_dna_sequence(sequence)
            elif analysis_type == 'RNA':
                analysis_results = analyze_rna_sequence(sequence)
            elif analysis_type == 'protein':
                analysis_results = analyze_protein_sequence(sequence)
            else:
                analysis_results = analyze_dna_sequence(sequence)
            
            return generate_analysis_results_html(analysis_results, analysis_type)
            
        except Exception as e:
            logger.error(f"Error analyzing sequence: {e}")
            return f"Error: {str(e)}"
    
    @app.callback(
        [Output('sequence-alignment-results', 'children'),
         Output('sequence-alignment-plot', 'figure')],
        [Input('sequence-align-btn', 'n_clicks')],
        [State('sequence-align-input1', 'value'),
         State('sequence-align-input2', 'value'),
         State('sequence-align-method', 'value')]
    )
    def align_sequences(n_clicks, sequence1, sequence2, method):
        """
        Perform sequence alignment between two sequences.
        
        Args:
            n_clicks: Number of align button clicks
            sequence1: First sequence to align
            sequence2: Second sequence to align
            method: Alignment method (global, local, semiglobal)
            
        Returns:
            Tuple of (alignment_html, alignment_plot)
        """
        if not n_clicks or not sequence1 or not sequence2:
            return "Enter two sequences to align", go.Figure()
        
        try:
            seq1 = sequence1.strip().upper()
            seq2 = sequence2.strip().upper()
            
            # Perform alignment
            alignment_result = perform_sequence_alignment(seq1, seq2, method)
            
            # Generate alignment HTML
            alignment_html = generate_alignment_html(alignment_result)
            
            # Generate alignment visualization
            alignment_plot = create_alignment_plot(alignment_result)
            
            return alignment_html, alignment_plot
            
        except Exception as e:
            logger.error(f"Error aligning sequences: {e}")
            return f"Error: {str(e)}", go.Figure()
    
    @app.callback(
        Output('sequence-motif-results', 'children'),
        [Input('sequence-motif-btn', 'n_clicks')],
        [State('sequence-motif-input', 'value'),
         State('sequence-motif-pattern', 'value'),
         State('sequence-motif-parameters', 'value')]
    )
    def find_motifs(n_clicks, sequence_input, motif_pattern, parameters):
        """
        Find motifs in sequence.
        
        Args:
            n_clicks: Number of motif search button clicks
            sequence_input: Input sequence to search
            motif_pattern: Motif pattern to find
            parameters: Search parameters
            
        Returns:
            HTML content with motif results
        """
        if not n_clicks or not sequence_input:
            return "Enter a sequence to search for motifs"
        
        try:
            sequence = sequence_input.strip().upper()
            
            # Find motifs
            motif_results = find_sequence_motifs(sequence, motif_pattern, parameters)
            
            return generate_motif_results_html(motif_results)
            
        except Exception as e:
            logger.error(f"Error finding motifs: {e}")
            return f"Error: {str(e)}"
    
    @app.callback(
        [Output('sequence-download-results', 'data'),
         Output('sequence-download-trigger', 'children')],
        [Input('sequence-download-btn', 'n_clicks')],
        [State('sequence-search-results', 'children'),
         State('sequence-analysis-results', 'children')]
    )
    def download_sequence_results(n_clicks, search_results, analysis_results):
        """
        Download sequence analysis results.
        
        Args:
            n_clicks: Number of download button clicks
            search_results: Search results HTML
            analysis_results: Analysis results HTML
            
        Returns:
            Tuple of (download_data, trigger_children)
        """
        if not n_clicks:
            return no_update, no_update
        
        try:
            # Combine results into downloadable format
            results_text = f"Search Results:\n{search_results}\n\nAnalysis Results:\n{analysis_results}"
            
            return dict(content=results_text, filename="sequence_analysis_results.txt"), no_update
            
        except Exception as e:
            logger.error(f"Error downloading sequence results: {e}")
            return no_update, f"Error: {str(e)}"


def is_valid_sequence(sequence: str, sequence_type: str) -> bool:
    """
    Validate sequence format based on type.
    
    Args:
        sequence: Input sequence
        sequence_type: Type of sequence (DNA, RNA, protein)
        
    Returns:
        Boolean indicating if sequence is valid
    """
    if sequence_type == 'DNA':
        return all(base in 'ATCGN' for base in sequence)
    elif sequence_type == 'RNA':
        return all(base in 'AUCGN' for base in sequence)
    elif sequence_type == 'protein':
        return all(aa in 'ACDEFGHIKLMNPQRSTVWY' for aa in sequence)
    else:
        return len(sequence) > 0


def perform_exact_search(sequence: str, database: str) -> List[Dict]:
    """
    Perform exact sequence search.
    
    Args:
        sequence: Sequence to search
        database: Database to search against
        
    Returns:
        List of search results
    """
    # This would integrate with actual database search
    # For now, return mock results
    return [
        {
            'id': '1',
            'sequence': sequence,
            'match_position': 0,
            'match_length': len(sequence),
            'identity': 100.0,
            'description': 'Exact match found'
        }
    ]


def perform_fuzzy_search(sequence: str, database: str, parameters: str) -> List[Dict]:
    """
    Perform fuzzy sequence search.
    
    Args:
        sequence: Sequence to search
        database: Database to search against
        parameters: Search parameters
        
    Returns:
        List of search results
    """
    # This would integrate with actual fuzzy search algorithm
    # For now, return mock results
    return [
        {
            'id': '1',
            'sequence': sequence,
            'match_position': 0,
            'match_length': len(sequence),
            'identity': 95.0,
            'description': 'Fuzzy match found'
        }
    ]


def perform_pattern_search(sequence: str, database: str) -> List[Dict]:
    """
    Perform pattern-based sequence search.
    
    Args:
        sequence: Pattern to search
        database: Database to search against
        
    Returns:
        List of search results
    """
    # This would integrate with actual pattern matching
    # For now, return mock results
    return [
        {
            'id': '1',
            'sequence': sequence,
            'match_position': 0,
            'match_length': len(sequence),
            'identity': 100.0,
            'description': 'Pattern match found'
        }
    ]


def analyze_dna_sequence(sequence: str) -> Dict[str, Any]:
    """
    Analyze DNA sequence properties.
    
    Args:
        sequence: DNA sequence to analyze
        
    Returns:
        Dictionary with analysis results
    """
    seq = Seq(sequence)
    
    return {
        'length': len(sequence),
        'gc_content': GC(seq),
        'molecular_weight': molecular_weight(seq, seq_type='DNA'),
        'base_composition': {
            'A': sequence.count('A'),
            'T': sequence.count('T'),
            'C': sequence.count('C'),
            'G': sequence.count('G')
        }
    }


def analyze_rna_sequence(sequence: str) -> Dict[str, Any]:
    """
    Analyze RNA sequence properties.
    
    Args:
        sequence: RNA sequence to analyze
        
    Returns:
        Dictionary with analysis results
    """
    seq = Seq(sequence)
    
    return {
        'length': len(sequence),
        'gc_content': GC(seq),
        'molecular_weight': molecular_weight(seq, seq_type='RNA'),
        'base_composition': {
            'A': sequence.count('A'),
            'U': sequence.count('U'),
            'C': sequence.count('C'),
            'G': sequence.count('G')
        }
    }


def analyze_protein_sequence(sequence: str) -> Dict[str, Any]:
    """
    Analyze protein sequence properties.
    
    Args:
        sequence: Protein sequence to analyze
        
    Returns:
        Dictionary with analysis results
    """
    try:
        analysis = ProteinAnalysis(sequence)
        
        return {
            'length': len(sequence),
            'molecular_weight': analysis.molecular_weight(),
            'isoelectric_point': analysis.isoelectric_point(),
            'amino_acid_composition': analysis.get_amino_acids_percent(),
            'instability_index': analysis.instability_index(),
            'aromaticity': analysis.aromaticity()
        }
    except Exception as e:
        logger.error(f"Error analyzing protein sequence: {e}")
        return {'error': str(e)}


def perform_sequence_alignment(seq1: str, seq2: str, method: str) -> Dict[str, Any]:
    """
    Perform sequence alignment.
    
    Args:
        seq1: First sequence
        seq2: Second sequence
        method: Alignment method
        
    Returns:
        Dictionary with alignment results
    """
    # This would integrate with actual alignment algorithm
    # For now, return mock results
    return {
        'seq1': seq1,
        'seq2': seq2,
        'alignment1': seq1,
        'alignment2': seq2,
        'score': 100,
        'identity': 100.0,
        'gaps': 0
    }


def find_sequence_motifs(sequence: str, pattern: str, parameters: str) -> List[Dict]:
    """
    Find motifs in sequence.
    
    Args:
        sequence: Sequence to search
        pattern: Motif pattern
        parameters: Search parameters
        
    Returns:
        List of motif matches
    """
    matches = []
    for match in re.finditer(pattern, sequence, re.IGNORECASE):
        matches.append({
            'start': match.start(),
            'end': match.end(),
            'sequence': match.group(),
            'pattern': pattern
        })
    
    return matches


def generate_search_results_html(results: List[Dict]) -> html.Div:
    """
    Generate HTML for search results.
    
    Args:
        results: List of search results
        
    Returns:
        HTML div with results
    """
    if not results:
        return html.Div("No results found")
    
    result_items = []
    for result in results:
        result_items.append(html.Div([
            html.H5(f"Match {result['id']}"),
            html.P(f"Position: {result['match_position']}"),
            html.P(f"Length: {result['match_length']}"),
            html.P(f"Identity: {result['identity']}%"),
            html.P(f"Description: {result['description']}"),
            html.Hr()
        ]))
    
    return html.Div([
        html.H4("Search Results"),
        html.Div(result_items)
    ])


def generate_sequence_stats(sequence: str, results: List[Dict]) -> html.Div:
    """
    Generate statistics HTML for sequence search.
    
    Args:
        sequence: Input sequence
        results: Search results
        
    Returns:
        HTML div with statistics
    """
    stats = {
        'Sequence Length': len(sequence),
        'Number of Matches': len(results),
        'Average Identity': np.mean([r['identity'] for r in results]) if results else 0
    }
    
    stats_items = [
        html.Div([
            html.Strong(f"{key}: "),
            html.Span(f"{value:.2f}" if isinstance(value, float) else str(value))
        ], style={'margin': '5px 0'})
        for key, value in stats.items()
    ]
    
    return html.Div([
        html.H4("Search Statistics"),
        html.Div(stats_items)
    ])


def generate_analysis_results_html(results: Dict[str, Any], analysis_type: str) -> html.Div:
    """
    Generate HTML for sequence analysis results.
    
    Args:
        results: Analysis results
        analysis_type: Type of analysis performed
        
    Returns:
        HTML div with results
    """
    if 'error' in results:
        return html.Div(f"Error: {results['error']}")
    
    result_items = []
    for key, value in results.items():
        if isinstance(value, dict):
            result_items.append(html.Div([
                html.Strong(f"{key}: "),
                html.Div([
                    html.P(f"{k}: {v}")
                    for k, v in value.items()
                ])
            ]))
        else:
            result_items.append(html.Div([
                html.Strong(f"{key}: "),
                html.Span(f"{value:.3f}" if isinstance(value, float) else str(value))
            ]))
    
    return html.Div([
        html.H4(f"{analysis_type} Analysis Results"),
        html.Div(result_items)
    ])


def generate_alignment_html(alignment_result: Dict[str, Any]) -> html.Div:
    """
    Generate HTML for sequence alignment results.
    
    Args:
        alignment_result: Alignment results
        
    Returns:
        HTML div with alignment
    """
    return html.Div([
        html.H4("Sequence Alignment"),
        html.Pre(f"Sequence 1: {alignment_result['alignment1']}"),
        html.Pre(f"Sequence 2: {alignment_result['alignment2']}"),
        html.P(f"Score: {alignment_result['score']}"),
        html.P(f"Identity: {alignment_result['identity']}%"),
        html.P(f"Gaps: {alignment_result['gaps']}")
    ])


def create_alignment_plot(alignment_result: Dict[str, Any]) -> go.Figure:
    """
    Create visualization for sequence alignment.
    
    Args:
        alignment_result: Alignment results
        
    Returns:
        Plotly figure object
    """
    fig = go.Figure()
    
    # Add alignment visualization
    fig.add_trace(go.Scatter(
        x=list(range(len(alignment_result['alignment1']))),
        y=[1] * len(alignment_result['alignment1']),
        mode='markers',
        name='Sequence 1',
        text=list(alignment_result['alignment1']),
        textposition='middle center'
    ))
    
    fig.add_trace(go.Scatter(
        x=list(range(len(alignment_result['alignment2']))),
        y=[0] * len(alignment_result['alignment2']),
        mode='markers',
        name='Sequence 2',
        text=list(alignment_result['alignment2']),
        textposition='middle center'
    ))
    
    fig.update_layout(
        title="Sequence Alignment Visualization",
        xaxis_title="Position",
        yaxis_title="Sequence",
        yaxis=dict(tickmode='array', tickvals=[0, 1], ticktext=['Sequence 2', 'Sequence 1'])
    )
    
    return fig


def generate_motif_results_html(motif_results: List[Dict]) -> html.Div:
    """
    Generate HTML for motif search results.
    
    Args:
        motif_results: List of motif matches
        
    Returns:
        HTML div with results
    """
    if not motif_results:
        return html.Div("No motifs found")
    
    result_items = []
    for i, motif in enumerate(motif_results):
        result_items.append(html.Div([
            html.H5(f"Motif {i+1}"),
            html.P(f"Position: {motif['start']}-{motif['end']}"),
            html.P(f"Sequence: {motif['sequence']}"),
            html.P(f"Pattern: {motif['pattern']}"),
            html.Hr()
        ]))
    
    return html.Div([
        html.H4("Motif Search Results"),
        html.Div(result_items)
    ])


# Export the registration function
__all__ = ['register_sequence_search_callbacks']
