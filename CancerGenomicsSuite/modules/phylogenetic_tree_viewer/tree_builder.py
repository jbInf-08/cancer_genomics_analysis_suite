"""
Phylogenetic Tree Builder

This module provides the main tree construction engine for phylogenetic analysis,
integrating various tree building algorithms and providing comprehensive
phylogenetic analysis capabilities for the Cancer Genomics Analysis Suite.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np
from pathlib import Path
import json
import io
from collections import defaultdict
import time

from Bio import Phylo, AlignIO
from Bio.Phylo.TreeConstruction import DistanceCalculator, DistanceTreeConstructor
from Bio.Phylo.TreeConstruction import ParsimonyScorer, ParsimonyTreeConstructor
from Bio.Phylo.TreeConstruction import _Matrix
from Bio.Align import MultipleSeqAlignment
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.Phylo.Consensus import bootstrap_consensus, majority_consensus
from Bio.Phylo import draw_ascii
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch


@dataclass
class TreeConstructionConfig:
    """Configuration for phylogenetic tree construction."""
    # Tree building method
    method: str = "neighbor_joining"  # neighbor_joining, upgma, parsimony, maximum_likelihood
    
    # Distance calculation
    distance_model: str = "identity"  # identity, jukes_cantor, kimura, hamming
    
    # Parsimony settings
    parsimony_optimization: str = "sankoff"  # sankoff, fitch
    
    # Bootstrap settings
    bootstrap_replicates: int = 100
    bootstrap_threshold: float = 0.7
    
    # Tree optimization
    optimize_branch_lengths: bool = True
    optimize_topology: bool = True
    
    # Output options
    generate_consensus_tree: bool = True
    calculate_support_values: bool = True
    export_newick: bool = True
    export_nexus: bool = True
    
    # Visualization
    generate_plots: bool = True
    plot_format: str = "png"  # png, svg, pdf


class PhylogeneticTreeBuilder:
    """
    Main phylogenetic tree builder for comprehensive tree construction and analysis.
    
    This class provides methods for building phylogenetic trees from sequence data,
    including multiple sequence alignment, distance calculation, and tree construction.
    """
    
    def __init__(self, config: Optional[TreeConstructionConfig] = None):
        """
        Initialize the phylogenetic tree builder.
        
        Args:
            config (TreeConstructionConfig, optional): Tree construction configuration
        """
        self.config = config or TreeConstructionConfig()
        self.logger = logging.getLogger(__name__)
        self.construction_history = []
        self.sequence_alignment = None
        self.trees = {}
        
        # Distance calculators
        self.distance_calculators = {
            'identity': self._identity_distance,
            'hamming': self._hamming_distance,
            'jukes_cantor': self._jukes_cantor_distance,
            'kimura': self._kimura_distance
        }
    
    def load_sequences(self, sequences: Union[str, List[SeqRecord], MultipleSeqAlignment]) -> Dict[str, Any]:
        """
        Load sequences for phylogenetic analysis.
        
        Args:
            sequences: Sequence data (file path, list of SeqRecords, or MultipleSeqAlignment)
            
        Returns:
            Dict[str, Any]: Loading results
        """
        self.logger.info("Loading sequences for phylogenetic analysis...")
        
        try:
            if isinstance(sequences, str):
                # Load from file
                if sequences.endswith('.fasta') or sequences.endswith('.fa'):
                    alignment = AlignIO.read(sequences, 'fasta')
                elif sequences.endswith('.phylip'):
                    alignment = AlignIO.read(sequences, 'phylip')
                elif sequences.endswith('.clustal'):
                    alignment = AlignIO.read(sequences, 'clustal')
                else:
                    raise ValueError(f"Unsupported file format: {sequences}")
            elif isinstance(sequences, list):
                # Convert list of SeqRecords to MultipleSeqAlignment
                alignment = MultipleSeqAlignment(sequences)
            elif isinstance(sequences, MultipleSeqAlignment):
                alignment = sequences
            else:
                raise ValueError("Invalid sequence data type")
            
            # Validate alignment
            validation = self._validate_alignment(alignment)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': f"Invalid alignment: {validation['errors']}"
                }
            
            self.sequence_alignment = alignment
            
            self.logger.info(f"Loaded {len(alignment)} sequences, length {alignment.get_alignment_length()}")
            
            return {
                'success': True,
                'sequences': len(alignment),
                'alignment_length': alignment.get_alignment_length(),
                'sequence_names': [record.id for record in alignment],
                'validation': validation
            }
            
        except Exception as e:
            self.logger.error(f"Error loading sequences: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _validate_alignment(self, alignment: MultipleSeqAlignment) -> Dict[str, Any]:
        """Validate multiple sequence alignment."""
        errors = []
        warnings = []
        
        if len(alignment) < 3:
            errors.append("At least 3 sequences required for phylogenetic analysis")
        
        if alignment.get_alignment_length() == 0:
            errors.append("Empty alignment")
        
        # Check for identical sequences
        sequences = [str(record.seq) for record in alignment]
        if len(set(sequences)) < len(sequences):
            warnings.append("Some sequences are identical")
        
        # Check alignment length consistency
        lengths = [len(seq) for seq in sequences]
        if len(set(lengths)) > 1:
            errors.append("Sequences have different lengths")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def build_tree(self, tree_name: str = "phylogenetic_tree") -> Dict[str, Any]:
        """
        Build phylogenetic tree from loaded sequences.
        
        Args:
            tree_name (str): Name for the constructed tree
            
        Returns:
            Dict[str, Any]: Tree construction results
        """
        if self.sequence_alignment is None:
            return {
                'success': False,
                'error': 'No sequences loaded'
            }
        
        self.logger.info(f"Building phylogenetic tree using {self.config.method} method...")
        
        try:
            start_time = time.time()
            
            if self.config.method == "neighbor_joining":
                tree = self._build_neighbor_joining_tree()
            elif self.config.method == "upgma":
                tree = self._build_upgma_tree()
            elif self.config.method == "parsimony":
                tree = self._build_parsimony_tree()
            else:
                return {
                    'success': False,
                    'error': f"Unsupported tree building method: {self.config.method}"
                }
            
            construction_time = time.time() - start_time
            
            # Store tree
            self.trees[tree_name] = tree
            
            # Calculate tree statistics
            tree_stats = self._calculate_tree_statistics(tree)
            
            # Bootstrap analysis if requested
            bootstrap_results = None
            if self.config.bootstrap_replicates > 0:
                bootstrap_results = self._perform_bootstrap_analysis(tree_name)
            
            # Store in history
            self.construction_history.append({
                'tree_name': tree_name,
                'method': self.config.method,
                'timestamp': pd.Timestamp.now().isoformat(),
                'construction_time': construction_time,
                'sequences': len(self.sequence_alignment),
                'tree_length': tree_stats['tree_length']
            })
            
            self.logger.info(f"Tree construction completed in {construction_time:.2f} seconds")
            
            return {
                'success': True,
                'tree_name': tree_name,
                'method': self.config.method,
                'construction_time': construction_time,
                'tree_statistics': tree_stats,
                'bootstrap_results': bootstrap_results
            }
            
        except Exception as e:
            self.logger.error(f"Error building tree: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _build_neighbor_joining_tree(self):
        """Build tree using neighbor-joining method."""
        # Calculate distance matrix
        distance_matrix = self._calculate_distance_matrix()
        
        # Build tree
        constructor = DistanceTreeConstructor()
        tree = constructor.nj(distance_matrix)
        
        return tree
    
    def _build_upgma_tree(self):
        """Build tree using UPGMA method."""
        # Calculate distance matrix
        distance_matrix = self._calculate_distance_matrix()
        
        # Build tree
        constructor = DistanceTreeConstructor()
        tree = constructor.upgma(distance_matrix)
        
        return tree
    
    def _build_parsimony_tree(self):
        """Build tree using parsimony method."""
        # Create parsimony scorer
        scorer = ParsimonyScorer()
        
        # Build tree
        constructor = ParsimonyTreeConstructor(scorer)
        tree = constructor.build_tree(self.sequence_alignment)
        
        return tree
    
    def _calculate_distance_matrix(self):
        """Calculate distance matrix from alignment."""
        sequences = [str(record.seq) for record in self.sequence_alignment]
        n = len(sequences)
        
        # Initialize distance matrix
        distances = np.zeros((n, n))
        
        # Calculate pairwise distances
        for i in range(n):
            for j in range(i + 1, n):
                distance = self.distance_calculators[self.config.distance_model](
                    sequences[i], sequences[j]
                )
                distances[i, j] = distance
                distances[j, i] = distance
        
        # Create distance matrix object
        names = [record.id for record in self.sequence_alignment]
        distance_matrix = _Matrix(names, distances)
        
        return distance_matrix
    
    def _identity_distance(self, seq1: str, seq2: str) -> float:
        """Calculate identity-based distance."""
        if len(seq1) != len(seq2):
            return 1.0
        
        matches = sum(1 for a, b in zip(seq1, seq2) if a == b and a != '-' and b != '-')
        total = sum(1 for a, b in zip(seq1, seq2) if a != '-' or b != '-')
        
        return 1.0 - (matches / total) if total > 0 else 1.0
    
    def _hamming_distance(self, seq1: str, seq2: str) -> float:
        """Calculate Hamming distance."""
        if len(seq1) != len(seq2):
            return float('inf')
        
        return sum(1 for a, b in zip(seq1, seq2) if a != b)
    
    def _jukes_cantor_distance(self, seq1: str, seq2: str) -> float:
        """Calculate Jukes-Cantor distance."""
        if len(seq1) != len(seq2):
            return 1.0
        
        matches = sum(1 for a, b in zip(seq1, seq2) if a == b and a != '-' and b != '-')
        total = sum(1 for a, b in zip(seq1, seq2) if a != '-' or b != '-')
        
        if total == 0:
            return 1.0
        
        p = 1.0 - (matches / total)  # Proportion of differences
        
        if p >= 0.75:  # Jukes-Cantor correction breaks down at high divergence
            return 1.0
        
        # Jukes-Cantor formula
        d = -(3/4) * np.log(1 - (4/3) * p)
        return d
    
    def _kimura_distance(self, seq1: str, seq2: str) -> float:
        """Calculate Kimura 2-parameter distance."""
        if len(seq1) != len(seq2):
            return 1.0
        
        transitions = 0
        transversions = 0
        total = 0
        
        transition_pairs = [('A', 'G'), ('G', 'A'), ('T', 'C'), ('C', 'T')]
        
        for a, b in zip(seq1, seq2):
            if a != '-' and b != '-':
                total += 1
                if a == b:
                    continue
                elif (a, b) in transition_pairs:
                    transitions += 1
                else:
                    transversions += 1
        
        if total == 0:
            return 1.0
        
        P = transitions / total  # Transition rate
        Q = transversions / total  # Transversion rate
        
        if P + Q >= 0.5:  # Kimura correction breaks down at high divergence
            return 1.0
        
        # Kimura 2-parameter formula
        d = -(1/2) * np.log(1 - 2*P - Q) - (1/4) * np.log(1 - 2*Q)
        return d
    
    def _calculate_tree_statistics(self, tree) -> Dict[str, Any]:
        """Calculate tree statistics."""
        stats = {
            'tree_length': tree.total_branch_length(),
            'number_of_tips': len(tree.get_terminals()),
            'number_of_internal_nodes': len(tree.get_nonterminals()),
            'tree_height': tree.depths()[tree.root].values(),
            'average_branch_length': 0.0
        }
        
        # Calculate average branch length
        branch_lengths = []
        for clade in tree.find_clades():
            if clade.branch_length is not None:
                branch_lengths.append(clade.branch_length)
        
        if branch_lengths:
            stats['average_branch_length'] = np.mean(branch_lengths)
            stats['min_branch_length'] = min(branch_lengths)
            stats['max_branch_length'] = max(branch_lengths)
        
        return stats
    
    def _perform_bootstrap_analysis(self, tree_name: str) -> Dict[str, Any]:
        """Perform bootstrap analysis."""
        self.logger.info(f"Performing bootstrap analysis with {self.config.bootstrap_replicates} replicates...")
        
        try:
            # Generate bootstrap consensus tree
            consensus_tree = bootstrap_consensus(
                self.sequence_alignment,
                self.config.bootstrap_replicates,
                self._build_tree_for_bootstrap
            )
            
            # Store bootstrap tree
            bootstrap_name = f"{tree_name}_bootstrap"
            self.trees[bootstrap_name] = consensus_tree
            
            # Calculate bootstrap support
            support_values = self._calculate_bootstrap_support(consensus_tree)
            
            return {
                'bootstrap_replicates': self.config.bootstrap_replicates,
                'consensus_tree': bootstrap_name,
                'support_values': support_values,
                'high_support_nodes': len([s for s in support_values.values() if s >= self.config.bootstrap_threshold])
            }
            
        except Exception as e:
            self.logger.error(f"Error in bootstrap analysis: {e}")
            return {
                'error': str(e)
            }
    
    def _build_tree_for_bootstrap(self, alignment):
        """Build tree for bootstrap analysis."""
        if self.config.method == "neighbor_joining":
            distance_matrix = self._calculate_distance_matrix_from_alignment(alignment)
            constructor = DistanceTreeConstructor()
            return constructor.nj(distance_matrix)
        else:
            # For other methods, use neighbor-joining as default for bootstrap
            distance_matrix = self._calculate_distance_matrix_from_alignment(alignment)
            constructor = DistanceTreeConstructor()
            return constructor.nj(distance_matrix)
    
    def _calculate_distance_matrix_from_alignment(self, alignment):
        """Calculate distance matrix from alignment for bootstrap."""
        sequences = [str(record.seq) for record in alignment]
        n = len(sequences)
        
        distances = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i + 1, n):
                distance = self.distance_calculators[self.config.distance_model](
                    sequences[i], sequences[j]
                )
                distances[i, j] = distance
                distances[j, i] = distance
        
        names = [record.id for record in alignment]
        return _Matrix(names, distances)
    
    def _calculate_bootstrap_support(self, tree) -> Dict[str, float]:
        """Calculate bootstrap support values."""
        support_values = {}
        
        for clade in tree.find_clades():
            if clade.confidence is not None:
                support_values[str(clade)] = clade.confidence
        
        return support_values
    
    def compare_trees(self, tree1_name: str, tree2_name: str) -> Dict[str, Any]:
        """
        Compare two phylogenetic trees.
        
        Args:
            tree1_name (str): Name of first tree
            tree2_name (str): Name of second tree
            
        Returns:
            Dict[str, Any]: Tree comparison results
        """
        if tree1_name not in self.trees:
            return {'error': f'Tree {tree1_name} not found'}
        
        if tree2_name not in self.trees:
            return {'error': f'Tree {tree2_name} not found'}
        
        tree1 = self.trees[tree1_name]
        tree2 = self.trees[tree2_name]
        
        try:
            # Calculate Robinson-Foulds distance
            rf_distance = self._calculate_rf_distance(tree1, tree2)
            
            # Calculate tree statistics
            stats1 = self._calculate_tree_statistics(tree1)
            stats2 = self._calculate_tree_statistics(tree2)
            
            return {
                'tree1': {
                    'name': tree1_name,
                    'statistics': stats1
                },
                'tree2': {
                    'name': tree2_name,
                    'statistics': stats2
                },
                'robinson_foulds_distance': rf_distance,
                'comparison_timestamp': pd.Timestamp.now().isoformat()
            }
            
        except Exception as e:
            return {'error': f'Error comparing trees: {e}'}
    
    def _calculate_rf_distance(self, tree1, tree2) -> int:
        """Calculate Robinson-Foulds distance between two trees."""
        # Get all possible splits for each tree
        splits1 = self._get_tree_splits(tree1)
        splits2 = self._get_tree_splits(tree2)
        
        # Calculate symmetric difference
        rf_distance = len(splits1.symmetric_difference(splits2))
        
        return rf_distance
    
    def _get_tree_splits(self, tree) -> set:
        """Get all splits (bipartitions) from a tree."""
        splits = set()
        
        for clade in tree.find_clades():
            if not clade.is_terminal():
                # Get all terminal nodes under this clade
                terminals = [term.name for term in clade.get_terminals()]
                if len(terminals) > 1 and len(terminals) < len(tree.get_terminals()):
                    # Create split as frozenset
                    split = frozenset(terminals)
                    splits.add(split)
        
        return splits
    
    def export_tree(self, tree_name: str, output_path: str, format: str = "newick") -> str:
        """
        Export tree to file.
        
        Args:
            tree_name (str): Name of tree to export
            output_path (str): Output file path
            format (str): Export format (newick, nexus, phyloxml)
            
        Returns:
            str: Path to exported file
        """
        if tree_name not in self.trees:
            raise ValueError(f"Tree {tree_name} not found")
        
        tree = self.trees[tree_name]
        
        try:
            Phylo.write(tree, output_path, format)
            self.logger.info(f"Tree exported to {output_path}")
            return output_path
        except Exception as e:
            self.logger.error(f"Error exporting tree: {e}")
            raise
    
    def create_tree_visualization(self, tree_name: str, output_path: str = None) -> str:
        """
        Create tree visualization.
        
        Args:
            tree_name (str): Name of tree to visualize
            output_path (str): Output file path for plot
            
        Returns:
            str: Path to visualization file
        """
        if tree_name not in self.trees:
            raise ValueError(f"Tree {tree_name} not found")
        
        tree = self.trees[tree_name]
        
        try:
            # Create figure
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Draw tree
            Phylo.draw(tree, axes=ax, do_show=False)
            
            # Customize plot
            ax.set_title(f"Phylogenetic Tree: {tree_name}", fontsize=16, fontweight='bold')
            ax.set_xlabel("Branch Length", fontsize=12)
            
            # Save plot
            if output_path is None:
                output_path = f"{tree_name}_tree.{self.config.plot_format}"
            
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"Tree visualization saved to {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error creating tree visualization: {e}")
            raise
    
    def get_tree_summary(self) -> Dict[str, Any]:
        """
        Get summary of all constructed trees.
        
        Returns:
            Dict[str, Any]: Tree summary
        """
        return {
            'total_trees': len(self.trees),
            'tree_names': list(self.trees.keys()),
            'construction_history': self.construction_history,
            'current_alignment': {
                'sequences': len(self.sequence_alignment) if self.sequence_alignment else 0,
                'alignment_length': self.sequence_alignment.get_alignment_length() if self.sequence_alignment else 0
            },
            'config': {
                'method': self.config.method,
                'distance_model': self.config.distance_model,
                'bootstrap_replicates': self.config.bootstrap_replicates
            }
        }
    
    def clear_trees(self):
        """Clear all constructed trees."""
        self.trees.clear()
        self.logger.info("All trees cleared")
    
    def clear_construction_history(self):
        """Clear construction history."""
        self.construction_history.clear()
        self.logger.info("Construction history cleared")
