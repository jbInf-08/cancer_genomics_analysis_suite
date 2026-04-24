"""
A Plasmid Editor (APE) Integration Client

Provides functionality to interact with A Plasmid Editor for plasmid design
and analysis operations.
"""

import os
import subprocess
import tempfile
import json
import shutil
from typing import Dict, List, Optional, Any, Union
import logging
import platform
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class APEClient:
    """Client for interacting with A Plasmid Editor"""
    
    def __init__(self):
        """Initialize APE client"""
        self.system = platform.system().lower()
        self.ape_path = self._find_ape()
        self.available_features = self._get_available_features()
    
    def _find_ape(self) -> Optional[str]:
        """Find A Plasmid Editor installation"""
        possible_paths = [
            'ape',
            '/usr/bin/ape',
            '/usr/local/bin/ape',
            '/opt/ape/bin/ape',
            'C:\\Program Files\\A Plasmid Editor\\ape.exe',
            'C:\\Program Files (x86)\\A Plasmid Editor\\ape.exe'
        ]
        
        for path in possible_paths:
            if shutil.which(path) or os.path.exists(path):
                logger.info(f"Found APE at: {path}")
                return path
        
        logger.warning("A Plasmid Editor not found in standard locations")
        return None
    
    def _get_available_features(self) -> List[str]:
        """Get list of available APE features"""
        return [
            'plasmid_design', 'sequence_editing', 'feature_annotation',
            'restriction_sites', 'primer_design', 'sequence_analysis',
            'export_formats', 'visualization', 'cloning_simulation'
        ]
    
    def is_available(self) -> bool:
        """Check if APE is available"""
        return self.ape_path is not None
    
    def create_plasmid(self, name: str, sequence: str, 
                      features: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Create a new plasmid
        
        Args:
            name: Name of the plasmid
            sequence: DNA sequence
            features: Optional list of features
            
        Returns:
            Dictionary containing creation results
        """
        try:
            # Create temporary APE file
            ape_data = {
                'name': name,
                'sequence': sequence,
                'features': features or [],
                'metadata': {
                    'created_by': 'Cancer Genomics Analysis Suite',
                    'version': '1.0'
                }
            }
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ape', delete=False) as f:
                json.dump(ape_data, f, indent=2)
                temp_file = f.name
            
            return {
                'success': True,
                'message': f'Plasmid {name} created successfully',
                'file_path': temp_file,
                'plasmid_name': name,
                'sequence_length': len(sequence)
            }
            
        except Exception as e:
            logger.error(f"Error creating plasmid: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def load_plasmid(self, file_path: str) -> Dict[str, Any]:
        """
        Load plasmid from file
        
        Args:
            file_path: Path to plasmid file
            
        Returns:
            Dictionary containing plasmid data
        """
        try:
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'error': f'File not found: {file_path}'
                }
            
            # Read plasmid file
            with open(file_path, 'r') as f:
                if file_path.endswith('.ape'):
                    data = json.load(f)
                elif file_path.endswith('.gb') or file_path.endswith('.genbank'):
                    data = self._parse_genbank_file(file_path)
                elif file_path.endswith('.fasta') or file_path.endswith('.fa'):
                    data = self._parse_fasta_file(file_path)
                else:
                    return {
                        'success': False,
                        'error': f'Unsupported file format: {file_path}'
                    }
            
            return {
                'success': True,
                'plasmid_data': data,
                'file_path': file_path
            }
            
        except Exception as e:
            logger.error(f"Error loading plasmid: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _parse_genbank_file(self, file_path: str) -> Dict[str, Any]:
        """Parse GenBank file format"""
        # Simplified GenBank parser
        with open(file_path, 'r') as f:
            content = f.read()
        
        lines = content.split('\n')
        data = {
            'name': 'Unknown',
            'sequence': '',
            'features': [],
            'metadata': {}
        }
        
        in_sequence = False
        sequence_lines = []
        
        for line in lines:
            if line.startswith('LOCUS'):
                parts = line.split()
                if len(parts) > 1:
                    data['name'] = parts[1]
            elif line.startswith('FEATURES'):
                # Parse features (simplified)
                pass
            elif line.startswith('ORIGIN'):
                in_sequence = True
            elif in_sequence and line.strip():
                # Extract sequence from GenBank format
                seq_part = ''.join(line.split()[1:]).upper()
                sequence_lines.append(seq_part)
        
        data['sequence'] = ''.join(sequence_lines)
        return data
    
    def _parse_fasta_file(self, file_path: str) -> Dict[str, Any]:
        """Parse FASTA file format"""
        with open(file_path, 'r') as f:
            content = f.read()
        
        lines = content.split('\n')
        data = {
            'name': 'Unknown',
            'sequence': '',
            'features': [],
            'metadata': {}
        }
        
        sequence_lines = []
        for line in lines:
            if line.startswith('>'):
                data['name'] = line[1:].strip()
            else:
                sequence_lines.append(line.strip())
        
        data['sequence'] = ''.join(sequence_lines)
        return data
    
    def add_feature(self, plasmid_data: Dict, feature: Dict) -> Dict[str, Any]:
        """
        Add a feature to plasmid
        
        Args:
            plasmid_data: Plasmid data dictionary
            feature: Feature dictionary with name, start, end, type, etc.
            
        Returns:
            Dictionary containing updated plasmid data
        """
        try:
            if 'features' not in plasmid_data:
                plasmid_data['features'] = []
            
            # Validate feature
            if not all(key in feature for key in ['name', 'start', 'end', 'type']):
                return {
                    'success': False,
                    'error': 'Feature must contain name, start, end, and type'
                }
            
            # Add feature
            plasmid_data['features'].append(feature)
            
            return {
                'success': True,
                'message': f'Feature {feature["name"]} added successfully',
                'plasmid_data': plasmid_data
            }
            
        except Exception as e:
            logger.error(f"Error adding feature: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def find_restriction_sites(self, sequence: str, 
                             enzymes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Find restriction sites in sequence
        
        Args:
            sequence: DNA sequence
            enzymes: Optional list of restriction enzymes
            
        Returns:
            Dictionary containing restriction sites
        """
        try:
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
            
            if enzymes:
                restriction_enzymes = {k: v for k, v in restriction_enzymes.items() if k in enzymes}
            
            sites = []
            sequence_upper = sequence.upper()
            
            for enzyme, recognition_seq in restriction_enzymes.items():
                start = 0
                while True:
                    pos = sequence_upper.find(recognition_seq, start)
                    if pos == -1:
                        break
                    
                    sites.append({
                        'enzyme': enzyme,
                        'position': pos + 1,  # 1-based indexing
                        'sequence': recognition_seq,
                        'cut_position': pos + len(recognition_seq) // 2
                    })
                    start = pos + 1
            
            return {
                'success': True,
                'sites': sites,
                'total_sites': len(sites),
                'sequence_length': len(sequence)
            }
            
        except Exception as e:
            logger.error(f"Error finding restriction sites: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def design_primers(self, sequence: str, target_region: tuple,
                      primer_length: int = 20,
                      tm_range: tuple = (55, 65)) -> Dict[str, Any]:
        """
        Design primers for a target region
        
        Args:
            sequence: DNA sequence
            target_region: Tuple of (start, end) positions
            primer_length: Length of primers
            tm_range: Melting temperature range (min, max)
            
        Returns:
            Dictionary containing primer designs
        """
        try:
            start, end = target_region
            target_seq = sequence[start-1:end].upper()
            
            # Simple primer design (in practice, use more sophisticated algorithms)
            forward_primer = target_seq[:primer_length]
            reverse_primer = self._reverse_complement(target_seq[-primer_length:])
            
            # Calculate basic properties
            forward_tm = self._calculate_tm(forward_primer)
            reverse_tm = self._calculate_tm(reverse_primer)
            
            primers = {
                'forward': {
                    'sequence': forward_primer,
                    'position': start,
                    'length': len(forward_primer),
                    'tm': forward_tm,
                    'gc_content': self._calculate_gc_content(forward_primer)
                },
                'reverse': {
                    'sequence': reverse_primer,
                    'position': end - len(reverse_primer) + 1,
                    'length': len(reverse_primer),
                    'tm': reverse_tm,
                    'gc_content': self._calculate_gc_content(reverse_primer)
                }
            }
            
            return {
                'success': True,
                'primers': primers,
                'target_region': target_region,
                'target_sequence': target_seq
            }
            
        except Exception as e:
            logger.error(f"Error designing primers: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _reverse_complement(self, sequence: str) -> str:
        """Get reverse complement of DNA sequence"""
        complement = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G'}
        return ''.join(complement.get(base, base) for base in sequence[::-1])
    
    def _calculate_tm(self, sequence: str) -> float:
        """Calculate melting temperature (simplified)"""
        # Simple Tm calculation: 4*(G+C) + 2*(A+T)
        gc_count = sequence.count('G') + sequence.count('C')
        at_count = sequence.count('A') + sequence.count('T')
        return 4 * gc_count + 2 * at_count
    
    def _calculate_gc_content(self, sequence: str) -> float:
        """Calculate GC content percentage"""
        gc_count = sequence.count('G') + sequence.count('C')
        return (gc_count / len(sequence)) * 100 if sequence else 0
    
    def simulate_cloning(self, vector_sequence: str, insert_sequence: str,
                        restriction_sites: tuple) -> Dict[str, Any]:
        """
        Simulate cloning experiment
        
        Args:
            vector_sequence: Vector DNA sequence
            insert_sequence: Insert DNA sequence
            restriction_sites: Tuple of (vector_site, insert_site) positions
            
        Returns:
            Dictionary containing cloning simulation results
        """
        try:
            vector_site, insert_site = restriction_sites
            
            # Simulate restriction digestion
            vector_cut = vector_sequence[:vector_site] + vector_sequence[vector_site:]
            insert_cut = insert_sequence[:insert_site] + insert_sequence[insert_site:]
            
            # Simulate ligation
            recombinant_sequence = vector_cut + insert_cut
            
            # Calculate properties
            result = {
                'success': True,
                'vector_length': len(vector_sequence),
                'insert_length': len(insert_sequence),
                'recombinant_length': len(recombinant_sequence),
                'vector_site': vector_site,
                'insert_site': insert_site,
                'recombinant_sequence': recombinant_sequence
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error simulating cloning: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def export_plasmid(self, plasmid_data: Dict, format: str = 'genbank',
                      output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Export plasmid in various formats
        
        Args:
            plasmid_data: Plasmid data dictionary
            format: Export format (genbank, fasta, ape)
            output_file: Optional output file path
            
        Returns:
            Dictionary containing export results
        """
        try:
            if output_file is None:
                with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{format}', delete=False) as f:
                    output_file = f.name
            
            if format == 'genbank':
                content = self._export_genbank(plasmid_data)
            elif format == 'fasta':
                content = self._export_fasta(plasmid_data)
            elif format == 'ape':
                content = json.dumps(plasmid_data, indent=2)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported export format: {format}'
                }
            
            with open(output_file, 'w') as f:
                f.write(content)
            
            return {
                'success': True,
                'message': f'Plasmid exported to {format} format',
                'output_file': output_file,
                'format': format
            }
            
        except Exception as e:
            logger.error(f"Error exporting plasmid: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _export_genbank(self, plasmid_data: Dict) -> str:
        """Export plasmid in GenBank format"""
        name = plasmid_data.get('name', 'Unknown')
        sequence = plasmid_data.get('sequence', '')
        features = plasmid_data.get('features', [])
        
        lines = [
            f'LOCUS       {name:<16} {len(sequence):>8} bp    DNA     linear   UNK 01-JAN-1980',
            'DEFINITION  .',
            'ACCESSION   .',
            'VERSION     .',
            'KEYWORDS    .',
            'SOURCE      .',
            '  ORGANISM  .',
            'FEATURES             Location/Qualifiers',
        ]
        
        for feature in features:
            start = feature.get('start', 1)
            end = feature.get('end', len(sequence))
            feature_type = feature.get('type', 'misc_feature')
            feature_name = feature.get('name', '')
            
            lines.append(f'     {feature_type:<16} {start}..{end}')
            if feature_name:
                lines.append(f'                     /label="{feature_name}"')
        
        lines.extend([
            'ORIGIN',
        ])
        
        # Add sequence in GenBank format
        for i in range(0, len(sequence), 60):
            line_start = i + 1
            line_seq = sequence[i:i+60]
            formatted_seq = ' '.join([line_seq[j:j+10] for j in range(0, len(line_seq), 10)])
            lines.append(f'{line_start:>9} {formatted_seq}')
        
        lines.append('//')
        
        return '\n'.join(lines)
    
    def _export_fasta(self, plasmid_data: Dict) -> str:
        """Export plasmid in FASTA format"""
        name = plasmid_data.get('name', 'Unknown')
        sequence = plasmid_data.get('sequence', '')
        
        lines = [f'>{name}']
        
        # Add sequence in 80-character lines
        for i in range(0, len(sequence), 80):
            lines.append(sequence[i:i+80])
        
        return '\n'.join(lines)
    
    def get_version(self) -> str:
        """Get APE version"""
        if not self.is_available():
            return "Not available"
        
        try:
            result = subprocess.run([self.ape_path, '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return "Unknown"
        except Exception as e:
            logger.error(f"Error getting APE version: {e}")
            return "Unknown"
