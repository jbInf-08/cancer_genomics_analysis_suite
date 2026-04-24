"""
DNA Sequence Analyzer

This module provides the main analysis engine for DNA sequence analysis,
integrating various bioinformatics tools and providing comprehensive
sequence analysis capabilities for the Cancer Genomics Analysis Suite.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import pandas as pd
import numpy as np
from pathlib import Path
import json

from .utils import DNAUtils


@dataclass
class AnalysisConfig:
    """Configuration for DNA sequence analysis."""
    # Analysis options
    calculate_statistics: bool = True
    find_orfs: bool = True
    translate_sequences: bool = True
    find_restriction_sites: bool = True
    calculate_codon_usage: bool = True
    
    # Parameters
    min_orf_length: int = 150
    reading_frames: List[int] = None
    restriction_enzymes: Optional[List[str]] = None
    
    # Output options
    generate_plots: bool = True
    export_results: bool = True
    output_format: str = "json"  # json, csv, both
    
    def __post_init__(self):
        if self.reading_frames is None:
            self.reading_frames = [0, 1, 2]
        if self.restriction_enzymes is None:
            self.restriction_enzymes = ['EcoRI', 'BamHI', 'HindIII', 'XbaI']


class DNAAnalyzer:
    """
    Main DNA sequence analyzer for comprehensive sequence analysis.
    
    This class provides methods for analyzing DNA sequences including
    statistics calculation, ORF finding, translation, and restriction
    site analysis.
    """
    
    def __init__(self, config: Optional[AnalysisConfig] = None):
        """
        Initialize the DNA analyzer.
        
        Args:
            config (AnalysisConfig, optional): Analysis configuration
        """
        self.config = config or AnalysisConfig()
        self.logger = logging.getLogger(__name__)
        self.utils = DNAUtils()
        self.analysis_history = []
    
    def analyze_sequence(self, sequence: str, sequence_name: str = "Unknown") -> Dict[str, Any]:
        """
        Perform comprehensive analysis of a DNA sequence.
        
        Args:
            sequence (str): DNA sequence to analyze
            sequence_name (str): Name/identifier for the sequence
            
        Returns:
            Dict[str, Any]: Comprehensive analysis results
        """
        self.logger.info(f"Starting analysis of sequence: {sequence_name}")
        
        # Validate sequence
        validation = self.utils.validate_sequence(sequence)
        if not validation['valid']:
            self.logger.error(f"Invalid sequence: {validation['errors']}")
            return {
                'sequence_name': sequence_name,
                'valid': False,
                'errors': validation['errors'],
                'warnings': validation['warnings']
            }
        
        # Clean sequence
        clean_sequence = validation['sequence']
        
        # Initialize results
        results = {
            'sequence_name': sequence_name,
            'valid': True,
            'warnings': validation['warnings'],
            'sequence_length': len(clean_sequence),
            'analysis_timestamp': pd.Timestamp.now().isoformat()
        }
        
        # Calculate basic statistics
        if self.config.calculate_statistics:
            self.logger.info("Calculating sequence statistics...")
            stats = self.utils.calculate_sequence_statistics(clean_sequence)
            results['statistics'] = stats
        
        # Find ORFs
        if self.config.find_orfs:
            self.logger.info("Finding open reading frames...")
            orfs = self.utils.find_orfs(clean_sequence, self.config.min_orf_length)
            results['orfs'] = orfs
        
        # Translate sequences
        if self.config.translate_sequences:
            self.logger.info("Translating sequences...")
            translations = {}
            for frame in self.config.reading_frames:
                translation = self.utils.translate_sequence(clean_sequence, frame)
                if 'error' not in translation:
                    translations[f'frame_{frame}'] = translation
            results['translations'] = translations
        
        # Find restriction sites
        if self.config.find_restriction_sites:
            self.logger.info("Finding restriction sites...")
            restriction_sites = self.utils.find_restriction_sites(
                clean_sequence, self.config.restriction_enzymes
            )
            results['restriction_sites'] = restriction_sites
        
        # Calculate codon usage
        if self.config.calculate_codon_usage and len(clean_sequence) % 3 == 0:
            self.logger.info("Calculating codon usage...")
            codon_usage = self.utils.calculate_codon_usage(clean_sequence)
            results['codon_usage'] = codon_usage
        
        # Store in history
        self.analysis_history.append({
            'sequence_name': sequence_name,
            'timestamp': results['analysis_timestamp'],
            'sequence_length': len(clean_sequence)
        })
        
        self.logger.info(f"Analysis completed for sequence: {sequence_name}")
        return results
    
    def analyze_multiple_sequences(self, sequences: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        """
        Analyze multiple DNA sequences.
        
        Args:
            sequences (Dict[str, str]): Dictionary mapping sequence names to sequences
            
        Returns:
            Dict[str, Dict[str, Any]]: Analysis results for each sequence
        """
        self.logger.info(f"Analyzing {len(sequences)} sequences...")
        
        results = {}
        for name, sequence in sequences.items():
            try:
                results[name] = self.analyze_sequence(sequence, name)
            except Exception as e:
                self.logger.error(f"Error analyzing sequence {name}: {e}")
                results[name] = {
                    'sequence_name': name,
                    'valid': False,
                    'error': str(e)
                }
        
        return results
    
    def analyze_sequence_file(self, file_path: str, file_format: str = "fasta") -> Dict[str, Any]:
        """
        Analyze sequences from a file.
        
        Args:
            file_path (str): Path to sequence file
            file_format (str): File format (fasta, genbank, etc.)
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        self.logger.info(f"Loading sequences from file: {file_path}")
        
        try:
            from Bio import SeqIO
            
            sequences = {}
            for record in SeqIO.parse(file_path, file_format):
                sequences[record.id] = str(record.seq)
            
            self.logger.info(f"Loaded {len(sequences)} sequences from file")
            return self.analyze_multiple_sequences(sequences)
            
        except Exception as e:
            self.logger.error(f"Error loading sequences from file: {e}")
            return {'error': str(e)}
    
    def compare_sequences(self, sequences: Dict[str, str]) -> Dict[str, Any]:
        """
        Compare multiple sequences for similarities and differences.
        
        Args:
            sequences (Dict[str, str]): Dictionary mapping sequence names to sequences
            
        Returns:
            Dict[str, Any]: Comparison results
        """
        self.logger.info(f"Comparing {len(sequences)} sequences...")
        
        # Analyze each sequence
        analysis_results = self.analyze_multiple_sequences(sequences)
        
        # Compare statistics
        comparison = {
            'sequence_count': len(sequences),
            'comparison_timestamp': pd.Timestamp.now().isoformat(),
            'individual_analyses': analysis_results
        }
        
        # Compare GC content
        gc_contents = {}
        for name, results in analysis_results.items():
            if results.get('valid') and 'statistics' in results:
                gc_contents[name] = results['statistics'].get('gc_content', 0)
        
        if gc_contents:
            comparison['gc_content_comparison'] = {
                'values': gc_contents,
                'mean': np.mean(list(gc_contents.values())),
                'std': np.std(list(gc_contents.values())),
                'min': min(gc_contents.values()),
                'max': max(gc_contents.values())
            }
        
        # Compare lengths
        lengths = {}
        for name, results in analysis_results.items():
            if results.get('valid'):
                lengths[name] = results.get('sequence_length', 0)
        
        if lengths:
            comparison['length_comparison'] = {
                'values': lengths,
                'mean': np.mean(list(lengths.values())),
                'std': np.std(list(lengths.values())),
                'min': min(lengths.values()),
                'max': max(lengths.values())
            }
        
        # Compare ORF counts
        orf_counts = {}
        for name, results in analysis_results.items():
            if results.get('valid') and 'orfs' in results:
                orf_counts[name] = len(results['orfs'])
        
        if orf_counts:
            comparison['orf_count_comparison'] = {
                'values': orf_counts,
                'mean': np.mean(list(orf_counts.values())),
                'std': np.std(list(orf_counts.values())),
                'min': min(orf_counts.values()),
                'max': max(orf_counts.values())
            }
        
        return comparison
    
    def generate_analysis_report(self, results: Dict[str, Any], output_path: str) -> str:
        """
        Generate a comprehensive analysis report.
        
        Args:
            results (Dict[str, Any]): Analysis results
            output_path (str): Output file path
            
        Returns:
            str: Path to generated report
        """
        self.logger.info(f"Generating analysis report: {output_path}")
        
        # Create report content
        report_content = {
            'report_metadata': {
                'generated_by': 'Cancer Genomics Analysis Suite - DNA Analyzer',
                'generation_timestamp': pd.Timestamp.now().isoformat(),
                'analysis_config': {
                    'calculate_statistics': self.config.calculate_statistics,
                    'find_orfs': self.config.find_orfs,
                    'translate_sequences': self.config.translate_sequences,
                    'find_restriction_sites': self.config.find_restriction_sites,
                    'calculate_codon_usage': self.config.calculate_codon_usage,
                    'min_orf_length': self.config.min_orf_length
                }
            },
            'analysis_results': results
        }
        
        # Save report
        if output_path.endswith('.json'):
            with open(output_path, 'w') as f:
                json.dump(report_content, f, indent=2)
        else:
            # Default to JSON
            with open(output_path, 'w') as f:
                json.dump(report_content, f, indent=2)
        
        self.logger.info(f"Analysis report saved to: {output_path}")
        return output_path
    
    def create_visualization_plots(self, results: Dict[str, Any], output_dir: str) -> List[str]:
        """
        Create visualization plots for analysis results.
        
        Args:
            results (Dict[str, Any]): Analysis results
            output_dir (str): Output directory for plots
            
        Returns:
            List[str]: List of created plot file paths
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        plot_files = []
        
        # If results contain individual sequence analyses
        if 'individual_analyses' in results:
            for seq_name, seq_results in results['individual_analyses'].items():
                if seq_results.get('valid') and 'statistics' in seq_results:
                    # Get the original sequence (we'll need to store it)
                    # For now, we'll create plots based on statistics
                    self._create_sequence_plots(seq_results, seq_name, output_dir, plot_files)
        
        # Create comparison plots if multiple sequences
        if 'sequence_count' in results and results['sequence_count'] > 1:
            self._create_comparison_plots(results, output_dir, plot_files)
        
        return plot_files
    
    def _create_sequence_plots(self, seq_results: Dict[str, Any], seq_name: str, 
                              output_dir: str, plot_files: List[str]):
        """Create plots for individual sequence analysis."""
        import os
        import matplotlib.pyplot as plt
        
        # GC content plot
        if 'statistics' in seq_results and 'gc_content' in seq_results['statistics']:
            plt.figure(figsize=(8, 6))
            gc_content = seq_results['statistics']['gc_content']
            plt.bar(['GC Content'], [gc_content], color='skyblue')
            plt.axhline(y=50, color='red', linestyle='--', alpha=0.7, label='50% GC')
            plt.title(f'GC Content - {seq_name}')
            plt.ylabel('GC Content (%)')
            plt.legend()
            plt.tight_layout()
            
            plot_file = os.path.join(output_dir, f'{seq_name}_gc_content.png')
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            plt.close()
            plot_files.append(plot_file)
        
        # ORF length distribution
        if 'orfs' in seq_results and seq_results['orfs']:
            orf_lengths = [orf['length'] for orf in seq_results['orfs']]
            
            plt.figure(figsize=(10, 6))
            plt.hist(orf_lengths, bins=20, alpha=0.7, color='lightgreen')
            plt.title(f'ORF Length Distribution - {seq_name}')
            plt.xlabel('ORF Length (bp)')
            plt.ylabel('Frequency')
            plt.tight_layout()
            
            plot_file = os.path.join(output_dir, f'{seq_name}_orf_distribution.png')
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            plt.close()
            plot_files.append(plot_file)
    
    def _create_comparison_plots(self, results: Dict[str, Any], output_dir: str, plot_files: List[str]):
        """Create comparison plots for multiple sequences."""
        import os
        import matplotlib.pyplot as plt
        
        # GC content comparison
        if 'gc_content_comparison' in results:
            gc_data = results['gc_content_comparison']['values']
            
            plt.figure(figsize=(12, 6))
            sequences = list(gc_data.keys())
            gc_values = list(gc_data.values())
            
            plt.bar(sequences, gc_values, color='lightcoral')
            plt.axhline(y=50, color='red', linestyle='--', alpha=0.7, label='50% GC')
            plt.title('GC Content Comparison')
            plt.xlabel('Sequence')
            plt.ylabel('GC Content (%)')
            plt.xticks(rotation=45)
            plt.legend()
            plt.tight_layout()
            
            plot_file = os.path.join(output_dir, 'gc_content_comparison.png')
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            plt.close()
            plot_files.append(plot_file)
        
        # Length comparison
        if 'length_comparison' in results:
            length_data = results['length_comparison']['values']
            
            plt.figure(figsize=(12, 6))
            sequences = list(length_data.keys())
            lengths = list(length_data.values())
            
            plt.bar(sequences, lengths, color='lightblue')
            plt.title('Sequence Length Comparison')
            plt.xlabel('Sequence')
            plt.ylabel('Length (bp)')
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            plot_file = os.path.join(output_dir, 'length_comparison.png')
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            plt.close()
            plot_files.append(plot_file)
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """
        Get summary of all analyses performed.
        
        Returns:
            Dict[str, Any]: Analysis summary
        """
        return {
            'total_analyses': len(self.analysis_history),
            'analysis_history': self.analysis_history,
            'config': {
                'calculate_statistics': self.config.calculate_statistics,
                'find_orfs': self.config.find_orfs,
                'translate_sequences': self.config.translate_sequences,
                'find_restriction_sites': self.config.find_restriction_sites,
                'calculate_codon_usage': self.config.calculate_codon_usage,
                'min_orf_length': self.config.min_orf_length
            }
        }
    
    def clear_analysis_history(self):
        """Clear the analysis history."""
        self.analysis_history = []
        self.logger.info("Analysis history cleared")
