"""
Sequence Search Tool

This module provides the main alignment engine for sequence search and alignment,
integrating various alignment algorithms and providing comprehensive
sequence search capabilities for the Cancer Genomics Analysis Suite.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np
from pathlib import Path
import json
import re
from collections import defaultdict
import time

from Bio import pairwise2
from Bio.Seq import Seq
from Bio.SeqUtils import GC
from Bio.Align import substitution_matrices
from Bio.pairwise2 import format_alignment


@dataclass
class AlignmentConfig:
    """Configuration for sequence alignment."""
    # Alignment parameters
    match_score: int = 2
    mismatch_penalty: int = -1
    gap_open_penalty: int = -2
    gap_extend_penalty: int = -0.5
    
    # Search parameters
    min_alignment_length: int = 10
    max_alignments: int = 10
    e_value_threshold: float = 0.001
    identity_threshold: float = 0.7
    
    # Algorithm options
    alignment_type: str = "local"  # local, global, semiglobal
    substitution_matrix: str = "BLOSUM62"  # BLOSUM62, PAM250, etc.
    
    # Output options
    generate_alignments: bool = True
    calculate_statistics: bool = True
    export_results: bool = True
    output_format: str = "json"  # json, csv, both


class SequenceAligner:
    """
    Main sequence aligner for comprehensive sequence search and alignment.
    
    This class provides methods for aligning sequences, searching for patterns,
    and performing various sequence analysis operations.
    """
    
    def __init__(self, config: Optional[AlignmentConfig] = None):
        """
        Initialize the sequence aligner.
        
        Args:
            config (AlignmentConfig, optional): Alignment configuration
        """
        self.config = config or AlignmentConfig()
        self.logger = logging.getLogger(__name__)
        self.search_history = []
        self.sequence_database = {}
        
        # Load substitution matrices
        self.substitution_matrices = {
            'BLOSUM62': substitution_matrices.load('BLOSUM62'),
            'PAM250': substitution_matrices.load('PAM250'),
            'BLOSUM50': substitution_matrices.load('BLOSUM50')
        }
    
    def add_sequence_to_database(self, sequence_id: str, sequence: str, 
                                description: str = "") -> bool:
        """
        Add a sequence to the search database.
        
        Args:
            sequence_id (str): Unique identifier for the sequence
            sequence (str): DNA or protein sequence
            description (str): Optional description
            
        Returns:
            bool: Success status
        """
        try:
            # Validate sequence
            validation = self._validate_sequence(sequence)
            if not validation['valid']:
                self.logger.error(f"Invalid sequence for {sequence_id}: {validation['errors']}")
                return False
            
            # Clean and store sequence
            clean_sequence = validation['sequence']
            self.sequence_database[sequence_id] = {
                'sequence': clean_sequence,
                'description': description,
                'length': len(clean_sequence),
                'type': self._detect_sequence_type(clean_sequence),
                'gc_content': GC(clean_sequence) if self._detect_sequence_type(clean_sequence) == 'DNA' else None
            }
            
            self.logger.info(f"Added sequence {sequence_id} to database ({len(clean_sequence)} bp)")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding sequence {sequence_id}: {e}")
            return False
    
    def load_sequences_from_file(self, file_path: str, file_format: str = "fasta") -> Dict[str, Any]:
        """
        Load sequences from a file into the database.
        
        Args:
            file_path (str): Path to sequence file
            file_format (str): File format (fasta, genbank, etc.)
            
        Returns:
            Dict[str, Any]: Loading results
        """
        self.logger.info(f"Loading sequences from file: {file_path}")
        
        try:
            from Bio import SeqIO
            
            loaded_count = 0
            for record in SeqIO.parse(file_path, file_format):
                sequence_id = record.id
                sequence = str(record.seq)
                description = record.description
                
                if self.add_sequence_to_database(sequence_id, sequence, description):
                    loaded_count += 1
            
            self.logger.info(f"Loaded {loaded_count} sequences from file")
            return {
                'success': True,
                'loaded_sequences': loaded_count,
                'total_sequences': len(self.sequence_database)
            }
            
        except Exception as e:
            self.logger.error(f"Error loading sequences from file: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _validate_sequence(self, sequence: str) -> Dict[str, Any]:
        """Validate a sequence."""
        if not sequence:
            return {
                'valid': False,
                'errors': ['Empty sequence'],
                'warnings': [],
                'length': 0
            }
        
        sequence = sequence.upper().strip()
        errors = []
        warnings = []
        
        # Check for valid characters
        valid_dna = set('ATCGN')
        valid_protein = set('ACDEFGHIKLMNPQRSTVWY')
        
        dna_chars = set(sequence) - valid_dna
        protein_chars = set(sequence) - valid_protein
        
        if dna_chars and protein_chars:
            errors.append(f"Invalid characters found: {', '.join(dna_chars | protein_chars)}")
        elif len(dna_chars) > len(protein_chars):
            warnings.append(f"Non-DNA characters found: {', '.join(dna_chars)}")
        elif len(protein_chars) > len(dna_chars):
            warnings.append(f"Non-protein characters found: {', '.join(protein_chars)}")
        
        # Check sequence length
        if len(sequence) == 0:
            errors.append("Sequence is empty")
        elif len(sequence) < 5:
            warnings.append("Sequence is very short (< 5 characters)")
        elif len(sequence) > 1000000:
            warnings.append("Sequence is very long (> 1M characters)")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'length': len(sequence),
            'sequence': sequence
        }
    
    def _detect_sequence_type(self, sequence: str) -> str:
        """Detect if sequence is DNA or protein."""
        valid_dna = set('ATCGN')
        valid_protein = set('ACDEFGHIKLMNPQRSTVWY')
        
        sequence_chars = set(sequence.upper())
        
        if sequence_chars.issubset(valid_dna):
            return 'DNA'
        elif sequence_chars.issubset(valid_protein):
            return 'Protein'
        else:
            return 'Unknown'
    
    def search_sequence(self, query_sequence: str, query_name: str = "Query") -> Dict[str, Any]:
        """
        Search for a query sequence in the database.
        
        Args:
            query_sequence (str): Sequence to search for
            query_name (str): Name for the query sequence
            
        Returns:
            Dict[str, Any]: Search results
        """
        self.logger.info(f"Searching for sequence: {query_name}")
        
        # Validate query sequence
        validation = self._validate_sequence(query_sequence)
        if not validation['valid']:
            self.logger.error(f"Invalid query sequence: {validation['errors']}")
            return {
                'query_name': query_name,
                'valid': False,
                'errors': validation['errors']
            }
        
        query_sequence = validation['sequence']
        query_type = self._detect_sequence_type(query_sequence)
        
        if not self.sequence_database:
            return {
                'query_name': query_name,
                'valid': True,
                'error': 'No sequences in database'
            }
        
        # Perform search
        results = {
            'query_name': query_name,
            'query_sequence': query_sequence,
            'query_type': query_type,
            'query_length': len(query_sequence),
            'search_timestamp': pd.Timestamp.now().isoformat(),
            'valid': True,
            'matches': []
        }
        
        # Search against each sequence in database
        for seq_id, seq_data in self.sequence_database.items():
            if seq_data['type'] == query_type or seq_data['type'] == 'Unknown':
                match_result = self._align_sequences(
                    query_sequence, query_name,
                    seq_data['sequence'], seq_id,
                    seq_data['description']
                )
                
                if match_result['score'] > 0:
                    results['matches'].append(match_result)
        
        # Sort matches by score
        results['matches'].sort(key=lambda x: x['score'], reverse=True)
        
        # Limit number of results
        results['matches'] = results['matches'][:self.config.max_alignments]
        
        # Store in history
        self.search_history.append({
            'query_name': query_name,
            'timestamp': results['search_timestamp'],
            'matches_found': len(results['matches'])
        })
        
        self.logger.info(f"Found {len(results['matches'])} matches for {query_name}")
        return results
    
    def _align_sequences(self, query_seq: str, query_name: str,
                        target_seq: str, target_id: str, target_desc: str) -> Dict[str, Any]:
        """Align two sequences and return alignment results."""
        try:
            # Get substitution matrix
            matrix = self.substitution_matrices.get(self.config.substitution_matrix)
            
            # Perform alignment based on type
            if self.config.alignment_type == "local":
                alignments = pairwise2.align.localds(
                    query_seq, target_seq,
                    matrix, self.config.gap_open_penalty, self.config.gap_extend_penalty
                )
            elif self.config.alignment_type == "global":
                alignments = pairwise2.align.globalds(
                    query_seq, target_seq,
                    matrix, self.config.gap_open_penalty, self.config.gap_extend_penalty
                )
            else:  # semiglobal
                alignments = pairwise2.align.globalds(
                    query_seq, target_seq,
                    matrix, self.config.gap_open_penalty, self.config.gap_extend_penalty
                )
            
            if not alignments:
                return {
                    'target_id': target_id,
                    'target_description': target_desc,
                    'score': 0,
                    'identity': 0,
                    'coverage': 0,
                    'alignment': None
                }
            
            # Get best alignment
            best_alignment = alignments[0]
            aligned_query, aligned_target, score, start, end = best_alignment
            
            # Calculate statistics
            identity = self._calculate_identity(aligned_query, aligned_target)
            coverage = self._calculate_coverage(query_seq, aligned_query)
            
            # Check if alignment meets thresholds
            if (len(aligned_query) < self.config.min_alignment_length or
                identity < self.config.identity_threshold):
                return {
                    'target_id': target_id,
                    'target_description': target_desc,
                    'score': 0,
                    'identity': identity,
                    'coverage': coverage,
                    'alignment': None
                }
            
            # Format alignment
            alignment_text = None
            if self.config.generate_alignments:
                alignment_text = format_alignment(*best_alignment)
            
            return {
                'target_id': target_id,
                'target_description': target_desc,
                'score': score,
                'identity': identity,
                'coverage': coverage,
                'alignment_length': len(aligned_query),
                'query_start': start,
                'query_end': end,
                'alignment': alignment_text,
                'aligned_query': aligned_query,
                'aligned_target': aligned_target
            }
            
        except Exception as e:
            self.logger.error(f"Error aligning sequences: {e}")
            return {
                'target_id': target_id,
                'target_description': target_desc,
                'score': 0,
                'identity': 0,
                'coverage': 0,
                'alignment': None,
                'error': str(e)
            }
    
    def _calculate_identity(self, seq1: str, seq2: str) -> float:
        """Calculate sequence identity percentage."""
        if len(seq1) != len(seq2):
            return 0.0
        
        matches = sum(1 for a, b in zip(seq1, seq2) if a == b and a != '-' and b != '-')
        total = sum(1 for a, b in zip(seq1, seq2) if a != '-' or b != '-')
        
        return matches / total if total > 0 else 0.0
    
    def _calculate_coverage(self, original_seq: str, aligned_seq: str) -> float:
        """Calculate coverage percentage."""
        aligned_length = sum(1 for c in aligned_seq if c != '-')
        return aligned_length / len(original_seq) if len(original_seq) > 0 else 0.0
    
    def search_pattern(self, pattern: str, pattern_name: str = "Pattern") -> Dict[str, Any]:
        """
        Search for a pattern in all sequences in the database.
        
        Args:
            pattern (str): Pattern to search for (can include regex)
            pattern_name (str): Name for the pattern
            
        Returns:
            Dict[str, Any]: Pattern search results
        """
        self.logger.info(f"Searching for pattern: {pattern_name}")
        
        if not self.sequence_database:
            return {
                'pattern_name': pattern_name,
                'pattern': pattern,
                'error': 'No sequences in database'
            }
        
        results = {
            'pattern_name': pattern_name,
            'pattern': pattern,
            'search_timestamp': pd.Timestamp.now().isoformat(),
            'matches': []
        }
        
        # Compile regex pattern
        try:
            regex_pattern = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return {
                'pattern_name': pattern_name,
                'pattern': pattern,
                'error': f'Invalid regex pattern: {e}'
            }
        
        # Search in each sequence
        for seq_id, seq_data in self.sequence_database.items():
            sequence = seq_data['sequence']
            matches = list(regex_pattern.finditer(sequence))
            
            for match in matches:
                results['matches'].append({
                    'sequence_id': seq_id,
                    'sequence_description': seq_data['description'],
                    'start_position': match.start(),
                    'end_position': match.end(),
                    'matched_sequence': match.group(),
                    'context': sequence[max(0, match.start()-10):match.end()+10]
                })
        
        # Store in history
        self.search_history.append({
            'pattern_name': pattern_name,
            'timestamp': results['search_timestamp'],
            'matches_found': len(results['matches'])
        })
        
        self.logger.info(f"Found {len(results['matches'])} pattern matches for {pattern_name}")
        return results
    
    def compare_sequences(self, seq1_id: str, seq2_id: str) -> Dict[str, Any]:
        """
        Compare two sequences in the database.
        
        Args:
            seq1_id (str): First sequence ID
            seq2_id (str): Second sequence ID
            
        Returns:
            Dict[str, Any]: Comparison results
        """
        if seq1_id not in self.sequence_database:
            return {'error': f'Sequence {seq1_id} not found in database'}
        
        if seq2_id not in self.sequence_database:
            return {'error': f'Sequence {seq2_id} not found in database'}
        
        seq1_data = self.sequence_database[seq1_id]
        seq2_data = self.sequence_database[seq2_id]
        
        # Perform alignment
        alignment_result = self._align_sequences(
            seq1_data['sequence'], seq1_id,
            seq2_data['sequence'], seq2_id,
            seq2_data['description']
        )
        
        # Calculate additional statistics
        seq1 = seq1_data['sequence']
        seq2 = seq2_data['sequence']
        
        # GC content comparison (for DNA sequences)
        gc_comparison = {}
        if seq1_data['type'] == 'DNA' and seq2_data['type'] == 'DNA':
            gc_comparison = {
                'seq1_gc': GC(seq1),
                'seq2_gc': GC(seq2),
                'gc_difference': abs(GC(seq1) - GC(seq2))
            }
        
        return {
            'sequence1': {
                'id': seq1_id,
                'description': seq1_data['description'],
                'length': seq1_data['length'],
                'type': seq1_data['type']
            },
            'sequence2': {
                'id': seq2_id,
                'description': seq2_data['description'],
                'length': seq2_data['length'],
                'type': seq2_data['type']
            },
            'alignment': alignment_result,
            'gc_comparison': gc_comparison,
            'comparison_timestamp': pd.Timestamp.now().isoformat()
        }
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the sequence database.
        
        Returns:
            Dict[str, Any]: Database statistics
        """
        if not self.sequence_database:
            return {
                'total_sequences': 0,
                'total_length': 0,
                'sequence_types': {},
                'average_length': 0
            }
        
        total_length = sum(seq_data['length'] for seq_data in self.sequence_database.values())
        sequence_types = defaultdict(int)
        
        for seq_data in self.sequence_database.values():
            sequence_types[seq_data['type']] += 1
        
        return {
            'total_sequences': len(self.sequence_database),
            'total_length': total_length,
            'sequence_types': dict(sequence_types),
            'average_length': total_length / len(self.sequence_database),
            'sequence_ids': list(self.sequence_database.keys())
        }
    
    def export_database(self, output_path: str, format: str = "fasta") -> str:
        """
        Export the sequence database to a file.
        
        Args:
            output_path (str): Output file path
            format (str): Output format (fasta, genbank, etc.)
            
        Returns:
            str: Path to exported file
        """
        self.logger.info(f"Exporting database to: {output_path}")
        
        try:
            from Bio import SeqIO
            from Bio.Seq import Seq
            from Bio.SeqRecord import SeqRecord
            
            records = []
            for seq_id, seq_data in self.sequence_database.items():
                record = SeqRecord(
                    Seq(seq_data['sequence']),
                    id=seq_id,
                    description=seq_data['description']
                )
                records.append(record)
            
            SeqIO.write(records, output_path, format)
            
            self.logger.info(f"Exported {len(records)} sequences to {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error exporting database: {e}")
            raise
    
    def clear_database(self):
        """Clear the sequence database."""
        self.sequence_database.clear()
        self.logger.info("Sequence database cleared")
    
    def get_search_history(self) -> List[Dict[str, Any]]:
        """
        Get search history.
        
        Returns:
            List[Dict[str, Any]]: Search history
        """
        return self.search_history.copy()
    
    def clear_search_history(self):
        """Clear the search history."""
        self.search_history.clear()
        self.logger.info("Search history cleared")
