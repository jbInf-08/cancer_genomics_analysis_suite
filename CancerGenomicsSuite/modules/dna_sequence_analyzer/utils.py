"""
DNA Sequence Analyzer Utilities

This module provides utility functions for DNA sequence analysis including
sequence validation, manipulation, statistics, and common bioinformatics
operations for the Cancer Genomics Analysis Suite.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from collections import Counter, defaultdict
import numpy as np
import pandas as pd
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqUtils import GC, molecular_weight
from Bio.SeqUtils.ProtParam import ProteinAnalysis
from Bio.Data import CodonTable
import matplotlib.pyplot as plt
import seaborn as sns


class DNAUtils:
    """
    Utility class for DNA sequence analysis operations.
    
    This class provides methods for sequence validation, manipulation,
    statistics calculation, and common bioinformatics operations.
    """
    
    def __init__(self):
        """Initialize the DNA utilities."""
        self.logger = logging.getLogger(__name__)
        
        # Standard genetic code
        self.genetic_code = CodonTable.standard_dna_table
        
        # Valid DNA nucleotides
        self.valid_nucleotides = set('ATCGN')
        
        # IUPAC ambiguity codes
        self.iupac_codes = {
            'A': 'A', 'T': 'T', 'C': 'C', 'G': 'G',
            'N': 'ATCG', 'R': 'AG', 'Y': 'TC', 'S': 'GC',
            'W': 'AT', 'K': 'GT', 'M': 'AC', 'B': 'TCG',
            'D': 'ATG', 'H': 'ATC', 'V': 'ACG'
        }
    
    def validate_sequence(self, sequence: str, strict: bool = True) -> Dict[str, Any]:
        """
        Validate a DNA sequence.
        
        Args:
            sequence (str): DNA sequence to validate
            strict (bool): Whether to use strict validation (only ATCG)
            
        Returns:
            Dict[str, Any]: Validation results
        """
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
        
        # Check for invalid characters
        if strict:
            invalid_chars = set(sequence) - self.valid_nucleotides
            if invalid_chars:
                errors.append(f"Invalid characters found: {', '.join(invalid_chars)}")
        else:
            # Allow IUPAC codes
            valid_chars = set(self.iupac_codes.keys())
            invalid_chars = set(sequence) - valid_chars
            if invalid_chars:
                errors.append(f"Invalid characters found: {', '.join(invalid_chars)}")
        
        # Check sequence length
        if len(sequence) == 0:
            errors.append("Sequence is empty")
        elif len(sequence) < 10:
            warnings.append("Sequence is very short (< 10 bp)")
        elif len(sequence) > 1000000:
            warnings.append("Sequence is very long (> 1M bp)")
        
        # Check for ambiguous bases
        ambiguous_bases = set(sequence) - set('ATCG')
        if ambiguous_bases:
            warnings.append(f"Ambiguous bases found: {', '.join(ambiguous_bases)}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'length': len(sequence),
            'sequence': sequence
        }
    
    def calculate_sequence_statistics(self, sequence: str) -> Dict[str, Any]:
        """
        Calculate comprehensive sequence statistics.
        
        Args:
            sequence (str): DNA sequence
            
        Returns:
            Dict[str, Any]: Sequence statistics
        """
        if not sequence:
            return {}
        
        sequence = sequence.upper().strip()
        
        # Basic statistics
        length = len(sequence)
        nucleotide_counts = Counter(sequence)
        
        # GC content
        gc_content = GC(sequence)
        
        # Molecular weight
        try:
            mol_weight = molecular_weight(sequence, seq_type='DNA')
        except:
            mol_weight = None
        
        # Dinucleotide frequencies
        dinucleotides = [sequence[i:i+2] for i in range(len(sequence)-1)]
        dinucleotide_counts = Counter(dinucleotides)
        
        # Trinucleotide frequencies
        trinucleotides = [sequence[i:i+3] for i in range(len(sequence)-2)]
        trinucleotide_counts = Counter(trinucleotides)
        
        # Codon frequencies (if length is multiple of 3)
        codon_counts = {}
        if length % 3 == 0:
            codons = [sequence[i:i+3] for i in range(0, length, 3)]
            codon_counts = Counter(codons)
        
        # Complexity (Shannon entropy)
        complexity = self._calculate_complexity(sequence)
        
        # Palindrome detection
        palindromes = self._find_palindromes(sequence)
        
        # Repeat detection
        repeats = self._find_repeats(sequence)
        
        return {
            'length': length,
            'nucleotide_counts': dict(nucleotide_counts),
            'nucleotide_frequencies': {
                base: count/length for base, count in nucleotide_counts.items()
            },
            'gc_content': gc_content,
            'at_content': 100 - gc_content,
            'molecular_weight': mol_weight,
            'dinucleotide_counts': dict(dinucleotide_counts),
            'trinucleotide_counts': dict(trinucleotide_counts),
            'codon_counts': dict(codon_counts),
            'complexity': complexity,
            'palindromes': palindromes,
            'repeats': repeats
        }
    
    def _calculate_complexity(self, sequence: str) -> float:
        """Calculate sequence complexity using Shannon entropy."""
        if not sequence:
            return 0.0
        
        counts = Counter(sequence)
        total = len(sequence)
        
        entropy = 0.0
        for count in counts.values():
            p = count / total
            if p > 0:
                entropy -= p * np.log2(p)
        
        return entropy
    
    def _find_palindromes(self, sequence: str, min_length: int = 4) -> List[Dict[str, Any]]:
        """Find palindromic sequences."""
        palindromes = []
        
        for i in range(len(sequence) - min_length + 1):
            for j in range(i + min_length, len(sequence) + 1):
                subseq = sequence[i:j]
                if subseq == self._reverse_complement(subseq):
                    palindromes.append({
                        'start': i,
                        'end': j,
                        'length': j - i,
                        'sequence': subseq
                    })
        
        return palindromes
    
    def _find_repeats(self, sequence: str, min_length: int = 3) -> List[Dict[str, Any]]:
        """Find repeated sequences."""
        repeats = []
        
        for length in range(min_length, len(sequence) // 2 + 1):
            for i in range(len(sequence) - length + 1):
                pattern = sequence[i:i+length]
                positions = []
                
                # Find all occurrences of the pattern
                for j in range(len(sequence) - length + 1):
                    if sequence[j:j+length] == pattern:
                        positions.append(j)
                
                # If pattern appears more than once, it's a repeat
                if len(positions) > 1:
                    repeats.append({
                        'pattern': pattern,
                        'length': length,
                        'count': len(positions),
                        'positions': positions
                    })
        
        return repeats
    
    def reverse_complement(self, sequence: str) -> str:
        """
        Get reverse complement of DNA sequence.
        
        Args:
            sequence (str): DNA sequence
            
        Returns:
            str: Reverse complement sequence
        """
        complement_map = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C', 'N': 'N'}
        complement = ''.join(complement_map.get(base, 'N') for base in sequence.upper())
        return complement[::-1]
    
    def _reverse_complement(self, sequence: str) -> str:
        """Internal method for reverse complement."""
        return self.reverse_complement(sequence)
    
    def translate_sequence(self, sequence: str, reading_frame: int = 0) -> Dict[str, Any]:
        """
        Translate DNA sequence to protein.
        
        Args:
            sequence (str): DNA sequence
            reading_frame (int): Reading frame (0, 1, or 2)
            
        Returns:
            Dict[str, Any]: Translation results
        """
        if not sequence:
            return {}
        
        sequence = sequence.upper().strip()
        
        # Adjust sequence for reading frame
        if reading_frame > 0:
            sequence = sequence[reading_frame:]
        
        # Ensure sequence length is multiple of 3
        if len(sequence) % 3 != 0:
            sequence = sequence[:-(len(sequence) % 3)]
        
        if len(sequence) < 3:
            return {'error': 'Sequence too short for translation'}
        
        try:
            # Create BioPython Seq object
            dna_seq = Seq(sequence)
            protein_seq = dna_seq.translate()
            
            # Calculate protein statistics
            protein_stats = self._analyze_protein_sequence(str(protein_seq))
            
            return {
                'dna_sequence': sequence,
                'protein_sequence': str(protein_seq),
                'reading_frame': reading_frame,
                'codon_count': len(sequence) // 3,
                'protein_length': len(protein_seq),
                'protein_stats': protein_stats
            }
        
        except Exception as e:
            return {'error': f'Translation failed: {str(e)}'}
    
    def _analyze_protein_sequence(self, protein_sequence: str) -> Dict[str, Any]:
        """Analyze protein sequence properties."""
        if not protein_sequence:
            return {}
        
        try:
            # Remove stop codons (*)
            clean_sequence = protein_sequence.replace('*', '')
            
            if not clean_sequence:
                return {}
            
            # Use BioPython ProteinAnalysis
            analysis = ProteinAnalysis(clean_sequence)
            
            return {
                'length': len(clean_sequence),
                'molecular_weight': analysis.molecular_weight(),
                'isoelectric_point': analysis.isoelectric_point(),
                'amino_acid_counts': analysis.count_amino_acids(),
                'amino_acid_percentages': analysis.get_amino_acids_percent(),
                'aromaticity': analysis.aromaticity(),
                'instability_index': analysis.instability_index(),
                'gravy': analysis.gravy()
            }
        
        except Exception as e:
            self.logger.warning(f"Protein analysis failed: {e}")
            return {}
    
    def find_restriction_sites(self, sequence: str, enzyme_list: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Find restriction enzyme cutting sites.
        
        Args:
            sequence (str): DNA sequence
            enzyme_list (List[str], optional): List of enzyme names to search for
            
        Returns:
            List[Dict[str, Any]]: Restriction sites found
        """
        # Common restriction enzymes and their recognition sequences
        restriction_enzymes = {
            'EcoRI': 'GAATTC',
            'BamHI': 'GGATCC',
            'HindIII': 'AAGCTT',
            'XbaI': 'TCTAGA',
            'SalI': 'GTCGAC',
            'PstI': 'CTGCAG',
            'KpnI': 'GGTACC',
            'SacI': 'GAGCTC',
            'XhoI': 'CTCGAG',
            'NotI': 'GCGGCCGC'
        }
        
        if enzyme_list:
            restriction_enzymes = {k: v for k, v in restriction_enzymes.items() if k in enzyme_list}
        
        sites = []
        sequence = sequence.upper()
        
        for enzyme, recognition_seq in restriction_enzymes.items():
            pattern = recognition_seq
            for i in range(len(sequence) - len(pattern) + 1):
                if sequence[i:i+len(pattern)] == pattern:
                    sites.append({
                        'enzyme': enzyme,
                        'recognition_sequence': recognition_seq,
                        'position': i,
                        'cut_position': i + len(pattern) // 2,
                        'context': sequence[max(0, i-5):i+len(pattern)+5]
                    })
        
        return sites
    
    def find_orfs(self, sequence: str, min_length: int = 150) -> List[Dict[str, Any]]:
        """
        Find open reading frames (ORFs).
        
        Args:
            sequence (str): DNA sequence
            min_length (int): Minimum ORF length in nucleotides
            
        Returns:
            List[Dict[str, Any]]: ORFs found
        """
        orfs = []
        sequence = sequence.upper()
        
        # Start and stop codons
        start_codons = ['ATG']
        stop_codons = ['TAA', 'TAG', 'TGA']
        
        # Search in all three reading frames
        for frame in range(3):
            frame_sequence = sequence[frame:]
            
            # Find all start and stop codons
            starts = []
            stops = []
            
            for i in range(0, len(frame_sequence) - 2, 3):
                codon = frame_sequence[i:i+3]
                if codon in start_codons:
                    starts.append(i)
                elif codon in stop_codons:
                    stops.append(i)
            
            # Find ORFs
            for start in starts:
                for stop in stops:
                    if stop > start and (stop - start) >= min_length:
                        orf_sequence = frame_sequence[start:stop+3]
                        protein = self.translate_sequence(orf_sequence, 0)
                        
                        orfs.append({
                            'frame': frame,
                            'start': frame + start,
                            'end': frame + stop + 3,
                            'length': stop - start + 3,
                            'dna_sequence': orf_sequence,
                            'protein_sequence': protein.get('protein_sequence', ''),
                            'start_codon': orf_sequence[:3],
                            'stop_codon': orf_sequence[-3:]
                        })
        
        # Sort by length (longest first)
        orfs.sort(key=lambda x: x['length'], reverse=True)
        
        return orfs
    
    def calculate_codon_usage(self, sequence: str) -> Dict[str, Any]:
        """
        Calculate codon usage statistics.
        
        Args:
            sequence (str): DNA sequence
            
        Returns:
            Dict[str, Any]: Codon usage statistics
        """
        if not sequence or len(sequence) % 3 != 0:
            return {'error': 'Sequence length must be multiple of 3'}
        
        sequence = sequence.upper()
        codons = [sequence[i:i+3] for i in range(0, len(sequence), 3)]
        codon_counts = Counter(codons)
        
        # Calculate relative synonymous codon usage (RSCU)
        rscu = {}
        amino_acid_codons = defaultdict(list)
        
        # Group codons by amino acid
        for codon in codon_counts.keys():
            try:
                amino_acid = self.genetic_code.forward_table[codon]
                amino_acid_codons[amino_acid].append(codon)
            except KeyError:
                continue
        
        # Calculate RSCU for each codon
        for amino_acid, codon_list in amino_acid_codons.items():
            total_count = sum(codon_counts[codon] for codon in codon_list)
            synonymous_codons = len(codon_list)
            
            for codon in codon_list:
                observed = codon_counts[codon]
                expected = total_count / synonymous_codons
                rscu[codon] = observed / expected if expected > 0 else 0
        
        return {
            'codon_counts': dict(codon_counts),
            'total_codons': len(codons),
            'rscu': rscu,
            'amino_acid_codons': dict(amino_acid_codons)
        }
    
    def create_sequence_plots(self, sequence: str, output_dir: str = "outputs/plots") -> List[str]:
        """
        Create visualization plots for sequence analysis.
        
        Args:
            sequence (str): DNA sequence
            output_dir (str): Output directory for plots
            
        Returns:
            List[str]: List of created plot file paths
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        plot_files = []
        stats = self.calculate_sequence_statistics(sequence)
        
        # 1. Nucleotide composition bar plot
        if 'nucleotide_counts' in stats:
            plt.figure(figsize=(10, 6))
            nucleotides = list(stats['nucleotide_counts'].keys())
            counts = list(stats['nucleotide_counts'].values())
            
            plt.bar(nucleotides, counts, color=['red', 'blue', 'green', 'orange'])
            plt.title('Nucleotide Composition')
            plt.xlabel('Nucleotide')
            plt.ylabel('Count')
            plt.tight_layout()
            
            plot_file = os.path.join(output_dir, 'nucleotide_composition.png')
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            plt.close()
            plot_files.append(plot_file)
        
        # 2. Dinucleotide frequency heatmap
        if 'dinucleotide_counts' in stats:
            dinucleotides = list(stats['dinucleotide_counts'].keys())
            if dinucleotides:
                # Create matrix for heatmap
                matrix = np.zeros((4, 4))
                nucleotides = ['A', 'T', 'C', 'G']
                nuc_to_idx = {nuc: i for i, nuc in enumerate(nucleotides)}
                
                for dinuc, count in stats['dinucleotide_counts'].items():
                    if len(dinuc) == 2:
                        i, j = nuc_to_idx.get(dinuc[0], 0), nuc_to_idx.get(dinuc[1], 0)
                        matrix[i, j] = count
                
                plt.figure(figsize=(8, 6))
                sns.heatmap(matrix, annot=True, fmt='.0f', 
                           xticklabels=nucleotides, yticklabels=nucleotides,
                           cmap='Blues')
                plt.title('Dinucleotide Frequencies')
                plt.xlabel('Second Nucleotide')
                plt.ylabel('First Nucleotide')
                plt.tight_layout()
                
                plot_file = os.path.join(output_dir, 'dinucleotide_heatmap.png')
                plt.savefig(plot_file, dpi=300, bbox_inches='tight')
                plt.close()
                plot_files.append(plot_file)
        
        # 3. GC content sliding window
        if len(sequence) > 100:
            window_size = min(100, len(sequence) // 10)
            gc_content_window = []
            positions = []
            
            for i in range(0, len(sequence) - window_size + 1, window_size // 2):
                window_seq = sequence[i:i+window_size]
                gc_content = GC(window_seq)
                gc_content_window.append(gc_content)
                positions.append(i + window_size // 2)
            
            plt.figure(figsize=(12, 6))
            plt.plot(positions, gc_content_window, 'b-', linewidth=2)
            plt.axhline(y=50, color='r', linestyle='--', alpha=0.7, label='50% GC')
            plt.title(f'GC Content Sliding Window (window size: {window_size})')
            plt.xlabel('Position')
            plt.ylabel('GC Content (%)')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            plot_file = os.path.join(output_dir, 'gc_content_sliding_window.png')
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            plt.close()
            plot_files.append(plot_file)
        
        return plot_files
    
    def export_analysis_results(self, sequence: str, analysis_results: Dict[str, Any], 
                               output_file: str) -> str:
        """
        Export analysis results to file.
        
        Args:
            sequence (str): Original DNA sequence
            analysis_results (Dict[str, Any]): Analysis results
            output_file (str): Output file path
            
        Returns:
            str: Path to exported file
        """
        import json
        
        export_data = {
            'sequence_info': {
                'length': len(sequence),
                'sequence': sequence
            },
            'analysis_results': analysis_results,
            'timestamp': pd.Timestamp.now().isoformat()
        }
        
        if output_file.endswith('.json'):
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2)
        elif output_file.endswith('.csv'):
            # Flatten results for CSV export
            flat_data = []
            for key, value in analysis_results.items():
                if isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        flat_data.append({
                            'category': key,
                            'metric': subkey,
                            'value': subvalue
                        })
                else:
                    flat_data.append({
                        'category': 'general',
                        'metric': key,
                        'value': value
                    })
            
            df = pd.DataFrame(flat_data)
            df.to_csv(output_file, index=False)
        else:
            # Default to JSON
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2)
        
        self.logger.info(f"Analysis results exported to: {output_file}")
        return output_file
