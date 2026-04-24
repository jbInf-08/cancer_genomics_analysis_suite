"""
Protein Sequence Viewer

This module provides the main analysis engine for protein sequence analysis,
integrating various bioinformatics tools and providing comprehensive
protein analysis capabilities for the Cancer Genomics Analysis Suite.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np
from pathlib import Path
import json
import re
from collections import Counter, defaultdict

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqUtils.ProtParam import ProteinAnalysis
from Bio.SeqUtils import molecular_weight
from Bio.ExPASy import Prosite, Prodoc
import requests


@dataclass
class ProteinAnalysisConfig:
    """Configuration for protein sequence analysis."""
    # Analysis options
    calculate_statistics: bool = True
    find_motifs: bool = True
    predict_secondary_structure: bool = True
    calculate_hydrophobicity: bool = True
    find_disulfide_bonds: bool = True
    analyze_amino_acid_composition: bool = True
    
    # Parameters
    min_motif_length: int = 3
    max_motif_length: int = 20
    hydrophobicity_window: int = 9
    secondary_structure_method: str = "chou_fasman"  # chou_fasman, garnier
    
    # Output options
    generate_plots: bool = True
    export_results: bool = True
    output_format: str = "json"  # json, csv, both


class ProteinViewer:
    """
    Main protein sequence analyzer for comprehensive protein analysis.
    
    This class provides methods for analyzing protein sequences including
    statistics calculation, motif finding, secondary structure prediction,
    and domain analysis.
    """
    
    def __init__(self, config: Optional[ProteinAnalysisConfig] = None):
        """
        Initialize the protein viewer.
        
        Args:
            config (ProteinAnalysisConfig, optional): Analysis configuration
        """
        self.config = config or ProteinAnalysisConfig()
        self.logger = logging.getLogger(__name__)
        self.analysis_history = []
        
        # Amino acid properties
        self.amino_acid_properties = {
            'A': {'hydrophobicity': 1.8, 'charge': 0, 'polarity': 'nonpolar'},
            'R': {'hydrophobicity': -4.5, 'charge': 1, 'polarity': 'polar'},
            'N': {'hydrophobicity': -3.5, 'charge': 0, 'polarity': 'polar'},
            'D': {'hydrophobicity': -3.5, 'charge': -1, 'polarity': 'polar'},
            'C': {'hydrophobicity': 2.5, 'charge': 0, 'polarity': 'nonpolar'},
            'Q': {'hydrophobicity': -3.5, 'charge': 0, 'polarity': 'polar'},
            'E': {'hydrophobicity': -3.5, 'charge': -1, 'polarity': 'polar'},
            'G': {'hydrophobicity': -0.4, 'charge': 0, 'polarity': 'nonpolar'},
            'H': {'hydrophobicity': -3.2, 'charge': 0.5, 'polarity': 'polar'},
            'I': {'hydrophobicity': 4.5, 'charge': 0, 'polarity': 'nonpolar'},
            'L': {'hydrophobicity': 3.8, 'charge': 0, 'polarity': 'nonpolar'},
            'K': {'hydrophobicity': -3.9, 'charge': 1, 'polarity': 'polar'},
            'M': {'hydrophobicity': 1.9, 'charge': 0, 'polarity': 'nonpolar'},
            'F': {'hydrophobicity': 2.8, 'charge': 0, 'polarity': 'nonpolar'},
            'P': {'hydrophobicity': -1.6, 'charge': 0, 'polarity': 'nonpolar'},
            'S': {'hydrophobicity': -0.8, 'charge': 0, 'polarity': 'polar'},
            'T': {'hydrophobicity': -0.7, 'charge': 0, 'polarity': 'polar'},
            'W': {'hydrophobicity': -0.9, 'charge': 0, 'polarity': 'nonpolar'},
            'Y': {'hydrophobicity': -1.3, 'charge': 0, 'polarity': 'polar'},
            'V': {'hydrophobicity': 4.2, 'charge': 0, 'polarity': 'nonpolar'}
        }
    
    def analyze_sequence(self, sequence: str, sequence_name: str = "Unknown") -> Dict[str, Any]:
        """
        Perform comprehensive analysis of a protein sequence.
        
        Args:
            sequence (str): Protein sequence to analyze
            sequence_name (str): Name/identifier for the sequence
            
        Returns:
            Dict[str, Any]: Comprehensive analysis results
        """
        self.logger.info(f"Starting analysis of protein sequence: {sequence_name}")
        
        # Validate sequence
        validation = self._validate_sequence(sequence)
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
            self.logger.info("Calculating protein statistics...")
            stats = self._calculate_protein_statistics(clean_sequence)
            results['statistics'] = stats
        
        # Find motifs
        if self.config.find_motifs:
            self.logger.info("Finding protein motifs...")
            motifs = self._find_protein_motifs(clean_sequence)
            results['motifs'] = motifs
        
        # Predict secondary structure
        if self.config.predict_secondary_structure:
            self.logger.info("Predicting secondary structure...")
            secondary_structure = self._predict_secondary_structure(clean_sequence)
            results['secondary_structure'] = secondary_structure
        
        # Calculate hydrophobicity
        if self.config.calculate_hydrophobicity:
            self.logger.info("Calculating hydrophobicity profile...")
            hydrophobicity = self._calculate_hydrophobicity_profile(clean_sequence)
            results['hydrophobicity'] = hydrophobicity
        
        # Find disulfide bonds
        if self.config.find_disulfide_bonds:
            self.logger.info("Finding potential disulfide bonds...")
            disulfide_bonds = self._find_disulfide_bonds(clean_sequence)
            results['disulfide_bonds'] = disulfide_bonds
        
        # Analyze amino acid composition
        if self.config.analyze_amino_acid_composition:
            self.logger.info("Analyzing amino acid composition...")
            composition = self._analyze_amino_acid_composition(clean_sequence)
            results['amino_acid_composition'] = composition
        
        # Store in history
        self.analysis_history.append({
            'sequence_name': sequence_name,
            'timestamp': results['analysis_timestamp'],
            'sequence_length': len(clean_sequence)
        })
        
        self.logger.info(f"Analysis completed for protein sequence: {sequence_name}")
        return results
    
    def _validate_sequence(self, sequence: str) -> Dict[str, Any]:
        """Validate a protein sequence."""
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
        
        # Valid amino acids
        valid_aa = set('ACDEFGHIKLMNPQRSTVWY')
        invalid_chars = set(sequence) - valid_aa
        
        if invalid_chars:
            errors.append(f"Invalid amino acids found: {', '.join(invalid_chars)}")
        
        # Check sequence length
        if len(sequence) == 0:
            errors.append("Sequence is empty")
        elif len(sequence) < 5:
            warnings.append("Sequence is very short (< 5 amino acids)")
        elif len(sequence) > 10000:
            warnings.append("Sequence is very long (> 10k amino acids)")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'length': len(sequence),
            'sequence': sequence
        }
    
    def _calculate_protein_statistics(self, sequence: str) -> Dict[str, Any]:
        """Calculate comprehensive protein statistics."""
        try:
            # Use BioPython ProteinAnalysis
            analysis = ProteinAnalysis(sequence)
            
            # Basic statistics
            stats = {
                'length': len(sequence),
                'molecular_weight': analysis.molecular_weight(),
                'isoelectric_point': analysis.isoelectric_point(),
                'aromaticity': analysis.aromaticity(),
                'instability_index': analysis.instability_index(),
                'gravy': analysis.gravy(),
                'amino_acid_counts': analysis.count_amino_acids(),
                'amino_acid_percentages': analysis.get_amino_acids_percent()
            }
            
            # Additional calculations
            stats['charge_at_ph7'] = self._calculate_net_charge(sequence, 7.0)
            stats['extinction_coefficient'] = self._calculate_extinction_coefficient(sequence)
            stats['half_life'] = self._estimate_half_life(sequence)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error calculating protein statistics: {e}")
            return {'error': str(e)}
    
    def _calculate_net_charge(self, sequence: str, ph: float = 7.0) -> float:
        """Calculate net charge at given pH."""
        # Simplified charge calculation
        positive_aa = ['K', 'R', 'H']
        negative_aa = ['D', 'E']
        
        positive_count = sum(sequence.count(aa) for aa in positive_aa)
        negative_count = sum(sequence.count(aa) for aa in negative_aa)
        
        # Simplified pH-dependent charge (basic implementation)
        if ph < 6.0:
            histidine_charge = sequence.count('H') * 0.5
        else:
            histidine_charge = 0
        
        net_charge = positive_count + histidine_charge - negative_count
        return net_charge
    
    def _calculate_extinction_coefficient(self, sequence: str) -> float:
        """Calculate extinction coefficient at 280 nm."""
        # Extinction coefficients for aromatic amino acids
        extinction_coeffs = {'W': 5500, 'Y': 1490, 'C': 125}
        
        total_extinction = sum(sequence.count(aa) * coeff for aa, coeff in extinction_coeffs.items())
        return total_extinction
    
    def _estimate_half_life(self, sequence: str) -> str:
        """Estimate protein half-life based on N-terminal amino acid."""
        n_terminal = sequence[0] if sequence else 'X'
        
        # N-end rule (simplified)
        half_life_map = {
            'M': '>20 hours',
            'A': '>20 hours',
            'S': '>20 hours',
            'T': '>20 hours',
            'V': '>20 hours',
            'G': '>20 hours',
            'P': '>20 hours',
            'R': '2 minutes',
            'L': '2 minutes',
            'K': '3 minutes',
            'F': '2 minutes',
            'Y': '10 minutes',
            'W': '2 minutes',
            'I': '2 minutes',
            'N': '3 minutes',
            'Q': '10 minutes',
            'H': '10 minutes',
            'E': '30 minutes',
            'D': '3 minutes',
            'C': '>20 hours'
        }
        
        return half_life_map.get(n_terminal, 'Unknown')
    
    def _find_protein_motifs(self, sequence: str) -> List[Dict[str, Any]]:
        """Find common protein motifs."""
        motifs = []
        
        # Common motifs patterns
        motif_patterns = {
            'N-glycosylation': r'N[^P][ST]',
            'O-glycosylation': r'[ST]',
            'Phosphorylation': r'[ST]',
            'Myristoylation': r'G[^EDRKHPFYW]',
            'Palmitoylation': r'C',
            'Farnesylation': r'C[^P]',
            'Nuclear localization': r'[KR][^P][KR]',
            'Leucine zipper': r'L[^P]{6}L[^P]{6}L',
            'Zinc finger': r'C[^P]{2,4}C[^P]{12,14}H[^P]{3,5}H'
        }
        
        for motif_name, pattern in motif_patterns.items():
            matches = list(re.finditer(pattern, sequence))
            for match in matches:
                motifs.append({
                    'name': motif_name,
                    'pattern': pattern,
                    'start': match.start(),
                    'end': match.end(),
                    'sequence': match.group(),
                    'confidence': 'high' if motif_name in ['N-glycosylation', 'Phosphorylation'] else 'medium'
                })
        
        return motifs
    
    def _predict_secondary_structure(self, sequence: str) -> Dict[str, Any]:
        """Predict secondary structure using Chou-Fasman method."""
        if self.config.secondary_structure_method == "chou_fasman":
            return self._chou_fasman_prediction(sequence)
        else:
            return self._garnier_prediction(sequence)
    
    def _chou_fasman_prediction(self, sequence: str) -> Dict[str, Any]:
        """Chou-Fasman secondary structure prediction."""
        # Chou-Fasman parameters (simplified)
        alpha_helix_propensities = {
            'A': 1.42, 'R': 0.98, 'N': 0.67, 'D': 1.01, 'C': 0.70,
            'Q': 1.11, 'E': 1.51, 'G': 0.57, 'H': 1.00, 'I': 1.08,
            'L': 1.21, 'K': 1.16, 'M': 1.45, 'F': 1.13, 'P': 0.57,
            'S': 0.77, 'T': 0.83, 'W': 1.08, 'Y': 0.69, 'V': 1.06
        }
        
        beta_sheet_propensities = {
            'A': 0.83, 'R': 0.93, 'N': 0.54, 'D': 0.51, 'C': 1.19,
            'Q': 1.10, 'E': 0.37, 'G': 0.75, 'H': 0.87, 'I': 1.60,
            'L': 1.30, 'K': 0.74, 'M': 1.05, 'F': 1.38, 'P': 0.55,
            'S': 0.75, 'T': 1.19, 'W': 1.37, 'Y': 1.47, 'V': 1.70
        }
        
        # Calculate average propensities
        alpha_avg = np.mean([alpha_helix_propensities.get(aa, 1.0) for aa in sequence])
        beta_avg = np.mean([beta_sheet_propensities.get(aa, 1.0) for aa in sequence])
        
        # Simple prediction based on average propensities
        if alpha_avg > 1.1 and alpha_avg > beta_avg:
            predicted_structure = 'alpha-helix'
        elif beta_avg > 1.1 and beta_avg > alpha_avg:
            predicted_structure = 'beta-sheet'
        else:
            predicted_structure = 'random-coil'
        
        return {
            'method': 'chou_fasman',
            'predicted_structure': predicted_structure,
            'alpha_helix_propensity': alpha_avg,
            'beta_sheet_propensity': beta_avg,
            'confidence': 'medium'
        }
    
    def _garnier_prediction(self, sequence: str) -> Dict[str, Any]:
        """Garnier secondary structure prediction (simplified)."""
        # Simplified Garnier method
        helix_formers = ['A', 'E', 'L', 'M']
        sheet_formers = ['V', 'I', 'Y', 'F', 'W']
        
        helix_score = sum(sequence.count(aa) for aa in helix_formers) / len(sequence)
        sheet_score = sum(sequence.count(aa) for aa in sheet_formers) / len(sequence)
        
        if helix_score > 0.3 and helix_score > sheet_score:
            predicted_structure = 'alpha-helix'
        elif sheet_score > 0.3 and sheet_score > helix_score:
            predicted_structure = 'beta-sheet'
        else:
            predicted_structure = 'random-coil'
        
        return {
            'method': 'garnier',
            'predicted_structure': predicted_structure,
            'helix_score': helix_score,
            'sheet_score': sheet_score,
            'confidence': 'low'
        }
    
    def _calculate_hydrophobicity_profile(self, sequence: str) -> Dict[str, Any]:
        """Calculate hydrophobicity profile using sliding window."""
        window_size = self.config.hydrophobicity_window
        hydrophobicity_values = []
        positions = []
        
        for i in range(len(sequence) - window_size + 1):
            window = sequence[i:i+window_size]
            avg_hydrophobicity = np.mean([
                self.amino_acid_properties.get(aa, {}).get('hydrophobicity', 0)
                for aa in window
            ])
            hydrophobicity_values.append(avg_hydrophobicity)
            positions.append(i + window_size // 2)
        
        return {
            'window_size': window_size,
            'positions': positions,
            'hydrophobicity_values': hydrophobicity_values,
            'mean_hydrophobicity': np.mean(hydrophobicity_values),
            'max_hydrophobicity': max(hydrophobicity_values),
            'min_hydrophobicity': min(hydrophobicity_values)
        }
    
    def _find_disulfide_bonds(self, sequence: str) -> List[Dict[str, Any]]:
        """Find potential disulfide bonds between cysteine residues."""
        cysteine_positions = [i for i, aa in enumerate(sequence) if aa == 'C']
        
        disulfide_bonds = []
        if len(cysteine_positions) >= 2:
            # Simple pairing of adjacent cysteines (more sophisticated algorithms exist)
            for i in range(0, len(cysteine_positions) - 1, 2):
                if i + 1 < len(cysteine_positions):
                    disulfide_bonds.append({
                        'cys1_position': cysteine_positions[i],
                        'cys2_position': cysteine_positions[i + 1],
                        'distance': cysteine_positions[i + 1] - cysteine_positions[i],
                        'confidence': 'medium'
                    })
        
        return disulfide_bonds
    
    def _analyze_amino_acid_composition(self, sequence: str) -> Dict[str, Any]:
        """Analyze amino acid composition and properties."""
        aa_counts = Counter(sequence)
        total_aa = len(sequence)
        
        # Calculate percentages
        aa_percentages = {aa: (count / total_aa) * 100 for aa, count in aa_counts.items()}
        
        # Group by properties
        property_groups = {
            'hydrophobic': ['A', 'I', 'L', 'M', 'F', 'W', 'Y', 'V'],
            'hydrophilic': ['R', 'N', 'D', 'Q', 'E', 'H', 'K', 'S', 'T'],
            'charged': ['R', 'D', 'E', 'H', 'K'],
            'aromatic': ['F', 'W', 'Y', 'H'],
            'small': ['A', 'G', 'S'],
            'large': ['F', 'W', 'Y', 'R', 'K']
        }
        
        property_percentages = {}
        for property_name, aa_list in property_groups.items():
            percentage = sum(aa_percentages.get(aa, 0) for aa in aa_list)
            property_percentages[property_name] = percentage
        
        return {
            'amino_acid_counts': dict(aa_counts),
            'amino_acid_percentages': aa_percentages,
            'property_percentages': property_percentages,
            'total_amino_acids': total_aa
        }
    
    def analyze_multiple_sequences(self, sequences: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        """
        Analyze multiple protein sequences.
        
        Args:
            sequences (Dict[str, str]): Dictionary mapping sequence names to sequences
            
        Returns:
            Dict[str, Dict[str, Any]]: Analysis results for each sequence
        """
        self.logger.info(f"Analyzing {len(sequences)} protein sequences...")
        
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
    
    def compare_sequences(self, sequences: Dict[str, str]) -> Dict[str, Any]:
        """
        Compare multiple protein sequences for similarities and differences.
        
        Args:
            sequences (Dict[str, str]): Dictionary mapping sequence names to sequences
            
        Returns:
            Dict[str, Any]: Comparison results
        """
        self.logger.info(f"Comparing {len(sequences)} protein sequences...")
        
        # Analyze each sequence
        analysis_results = self.analyze_multiple_sequences(sequences)
        
        # Compare statistics
        comparison = {
            'sequence_count': len(sequences),
            'comparison_timestamp': pd.Timestamp.now().isoformat(),
            'individual_analyses': analysis_results
        }
        
        # Compare molecular weights
        molecular_weights = {}
        for name, results in analysis_results.items():
            if results.get('valid') and 'statistics' in results:
                molecular_weights[name] = results['statistics'].get('molecular_weight', 0)
        
        if molecular_weights:
            comparison['molecular_weight_comparison'] = {
                'values': molecular_weights,
                'mean': np.mean(list(molecular_weights.values())),
                'std': np.std(list(molecular_weights.values())),
                'min': min(molecular_weights.values()),
                'max': max(molecular_weights.values())
            }
        
        # Compare isoelectric points
        pi_values = {}
        for name, results in analysis_results.items():
            if results.get('valid') and 'statistics' in results:
                pi_values[name] = results['statistics'].get('isoelectric_point', 0)
        
        if pi_values:
            comparison['pi_comparison'] = {
                'values': pi_values,
                'mean': np.mean(list(pi_values.values())),
                'std': np.std(list(pi_values.values())),
                'min': min(pi_values.values()),
                'max': max(pi_values.values())
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
                'generated_by': 'Cancer Genomics Analysis Suite - Protein Viewer',
                'generation_timestamp': pd.Timestamp.now().isoformat(),
                'analysis_config': {
                    'calculate_statistics': self.config.calculate_statistics,
                    'find_motifs': self.config.find_motifs,
                    'predict_secondary_structure': self.config.predict_secondary_structure,
                    'calculate_hydrophobicity': self.config.calculate_hydrophobicity,
                    'find_disulfide_bonds': self.config.find_disulfide_bonds,
                    'analyze_amino_acid_composition': self.config.analyze_amino_acid_composition
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
                'find_motifs': self.config.find_motifs,
                'predict_secondary_structure': self.config.predict_secondary_structure,
                'calculate_hydrophobicity': self.config.calculate_hydrophobicity,
                'find_disulfide_bonds': self.config.find_disulfide_bonds,
                'analyze_amino_acid_composition': self.config.analyze_amino_acid_composition
            }
        }
    
    def clear_analysis_history(self):
        """Clear the analysis history."""
        self.analysis_history = []
        self.logger.info("Analysis history cleared")
