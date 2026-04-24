"""
PyMOL Integration Client

Provides functionality to interact with PyMOL for molecular visualization
and structure analysis operations.
"""

import os
import tempfile
import subprocess
import json
import base64
from typing import Dict, List, Optional, Any, Union
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class PyMOLClient:
    """Client for interacting with PyMOL for molecular visualization"""
    
    def __init__(self):
        """Initialize PyMOL client"""
        self.pymol_path = self._find_pymol()
        self.available_commands = self._get_available_commands()
        self.session_data = {}
    
    def _find_pymol(self) -> Optional[str]:
        """Find PyMOL installation path"""
        possible_paths = [
            'pymol',
            '/usr/bin/pymol',
            '/usr/local/bin/pymol',
            '/opt/pymol/bin/pymol',
            'C:\\Program Files\\PyMOL\\PyMOL.exe',
            'C:\\Program Files (x86)\\PyMOL\\PyMOL.exe'
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run([path, '--version'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    logger.info(f"Found PyMOL at: {path}")
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                continue
        
        logger.warning("PyMOL not found in standard locations")
        return None
    
    def _get_available_commands(self) -> List[str]:
        """Get list of available PyMOL commands"""
        return [
            'load', 'save', 'show', 'hide', 'select', 'color', 'zoom',
            'center', 'orient', 'rotate', 'translate', 'scale', 'ray',
            'png', 'png', 'set', 'get', 'help', 'quit', 'reinitialize',
            'fetch', 'align', 'super', 'rms', 'distance', 'angle',
            'dihedral', 'measure', 'mutate', 'mutagenesis', 'wizard'
        ]
    
    def is_available(self) -> bool:
        """Check if PyMOL is available"""
        return self.pymol_path is not None
    
    def execute_pymol_script(self, pymol_commands: str, 
                           output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute PyMOL commands and return results
        
        Args:
            pymol_commands: PyMOL commands to execute
            output_file: Optional output file for images
            
        Returns:
            Dictionary containing results and any errors
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'PyMOL not available',
                'output': '',
                'error_output': 'PyMOL not found in system'
            }
        
        try:
            # Create temporary script file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.pml', delete=False) as f:
                f.write(pymol_commands)
                if output_file:
                    f.write(f"\nray\npng {output_file}\n")
                f.write("\nquit\n")
                script_file = f.name
            
            # Execute PyMOL script
            result = subprocess.run(
                [self.pymol_path, '-c', '-q', script_file],
                capture_output=True,
                text=True,
                timeout=60  # 1 minute timeout
            )
            
            # Clean up script file
            os.unlink(script_file)
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error_output': result.stderr,
                'returncode': result.returncode,
                'output_file': output_file if output_file and os.path.exists(output_file) else None
            }
            
        except subprocess.TimeoutExpired:
            logger.error("PyMOL script execution timed out")
            return {
                'success': False,
                'error': 'Script execution timed out',
                'output': '',
                'error_output': 'Timeout after 1 minute'
            }
        except Exception as e:
            logger.error(f"Error executing PyMOL script: {e}")
            return {
                'success': False,
                'error': str(e),
                'output': '',
                'error_output': str(e)
            }
    
    def load_structure(self, structure_file: str, object_name: str = "mol") -> Dict[str, Any]:
        """
        Load molecular structure from file
        
        Args:
            structure_file: Path to structure file (PDB, SDF, etc.)
            object_name: Name for the loaded object
            
        Returns:
            Dictionary containing load results
        """
        if not os.path.exists(structure_file):
            return {
                'success': False,
                'error': f'Structure file not found: {structure_file}'
            }
        
        commands = f"load {structure_file}, {object_name}"
        result = self.execute_pymol_script(commands)
        
        if result['success']:
            self.session_data[object_name] = {
                'file': structure_file,
                'loaded': True
            }
        
        return result
    
    def fetch_structure(self, pdb_id: str, object_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch structure from PDB database
        
        Args:
            pdb_id: PDB identifier (e.g., '1CRN')
            object_name: Name for the fetched object
            
        Returns:
            Dictionary containing fetch results
        """
        if object_name is None:
            object_name = pdb_id.lower()
        
        commands = f"fetch {pdb_id}, {object_name}"
        result = self.execute_pymol_script(commands)
        
        if result['success']:
            self.session_data[object_name] = {
                'pdb_id': pdb_id,
                'loaded': True
            }
        
        return result
    
    def visualize_structure(self, object_name: str, 
                          style: str = "cartoon",
                          color: str = "spectrum",
                          output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Visualize molecular structure
        
        Args:
            object_name: Name of the object to visualize
            style: Visualization style (cartoon, stick, sphere, etc.)
            color: Color scheme (spectrum, rainbow, etc.)
            output_file: Optional output image file
            
        Returns:
            Dictionary containing visualization results
        """
        commands = f"""
show {style}, {object_name}
color {color}, {object_name}
zoom {object_name}
"""
        
        if output_file:
            commands += f"ray\npng {output_file}\n"
        
        return self.execute_pymol_script(commands)
    
    def align_structures(self, object1: str, object2: str, 
                        method: str = "align") -> Dict[str, Any]:
        """
        Align two molecular structures
        
        Args:
            object1: First structure object
            object2: Second structure object
            method: Alignment method (align, super, cealign)
            
        Returns:
            Dictionary containing alignment results
        """
        commands = f"{method} {object1}, {object2}"
        result = self.execute_pymol_script(commands)
        
        # Extract RMSD from output if available
        if result['success'] and 'RMSD' in result['output']:
            lines = result['output'].split('\n')
            for line in lines:
                if 'RMSD' in line:
                    try:
                        rmsd = float(line.split('RMSD')[1].split()[0])
                        result['rmsd'] = rmsd
                        break
                    except (IndexError, ValueError):
                        pass
        
        return result
    
    def calculate_distances(self, object_name: str, 
                          selection1: str, selection2: str) -> Dict[str, Any]:
        """
        Calculate distances between atoms or residues
        
        Args:
            object_name: Name of the object
            selection1: First selection (e.g., 'resi 10')
            selection2: Second selection (e.g., 'resi 20')
            
        Returns:
            Dictionary containing distance calculations
        """
        commands = f"""
distance dist_{object_name}, {object_name} and {selection1}, {object_name} and {selection2}
"""
        return self.execute_pymol_script(commands)
    
    def analyze_secondary_structure(self, object_name: str) -> Dict[str, Any]:
        """
        Analyze secondary structure elements
        
        Args:
            object_name: Name of the object to analyze
            
        Returns:
            Dictionary containing secondary structure analysis
        """
        commands = f"""
dss {object_name}
show cartoon, {object_name}
color ss, {object_name}
"""
        return self.execute_pymol_script(commands)
    
    def create_surface(self, object_name: str, 
                      surface_type: str = "surface",
                      transparency: float = 0.5) -> Dict[str, Any]:
        """
        Create molecular surface
        
        Args:
            object_name: Name of the object
            surface_type: Type of surface (surface, dots, mesh)
            transparency: Surface transparency (0-1)
            
        Returns:
            Dictionary containing surface creation results
        """
        commands = f"""
show {surface_type}, {object_name}
set transparency, {transparency}, {object_name}
"""
        return self.execute_pymol_script(commands)
    
    def mutate_residue(self, object_name: str, 
                      residue_number: int, 
                      new_residue: str) -> Dict[str, Any]:
        """
        Mutate a residue in the structure
        
        Args:
            object_name: Name of the object
            residue_number: Residue number to mutate
            new_residue: New residue type (3-letter code)
            
        Returns:
            Dictionary containing mutation results
        """
        commands = f"""
mutate {new_residue}, {object_name} and resi {residue_number}
"""
        return self.execute_pymol_script(commands)
    
    def create_ramachandran_plot(self, object_name: str, 
                               output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Create Ramachandran plot for the structure
        
        Args:
            object_name: Name of the object
            output_file: Optional output file for the plot
            
        Returns:
            Dictionary containing plot creation results
        """
        commands = f"""
ramachandran {object_name}
"""
        
        if output_file:
            commands += f"ray\npng {output_file}\n"
        
        return self.execute_pymol_script(commands)
    
    def export_structure(self, object_name: str, 
                        output_file: str, 
                        format: str = "pdb") -> Dict[str, Any]:
        """
        Export structure to file
        
        Args:
            object_name: Name of the object to export
            output_file: Output file path
            format: Export format (pdb, sdf, mol2, etc.)
            
        Returns:
            Dictionary containing export results
        """
        commands = f"save {output_file}, {object_name}"
        return self.execute_pymol_script(commands)
    
    def get_structure_info(self, object_name: str) -> Dict[str, Any]:
        """
        Get information about a loaded structure
        
        Args:
            object_name: Name of the object
            
        Returns:
            Dictionary containing structure information
        """
        commands = f"""
print "Object: {object_name}"
print "Atoms:", cmd.count_atoms("{object_name}")
print "Residues:", cmd.count_residues("{object_name}")
print "Chains:", cmd.count_chains("{object_name}")
"""
        return self.execute_pymol_script(commands)
    
    def create_animation(self, object_name: str, 
                        animation_type: str = "rotate",
                        frames: int = 36,
                        output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Create molecular animation
        
        Args:
            object_name: Name of the object
            animation_type: Type of animation (rotate, zoom, etc.)
            frames: Number of frames
            output_file: Optional output file for animation
            
        Returns:
            Dictionary containing animation creation results
        """
        if animation_type == "rotate":
            commands = f"""
mset 1 {frames}
mview store, 1
rotate y, 360
mview store, {frames}
mplay
"""
        elif animation_type == "zoom":
            commands = f"""
mset 1 {frames}
mview store, 1
zoom {object_name}, 0.5
mview store, {frames//2}
zoom {object_name}, 2.0
mview store, {frames}
mplay
"""
        else:
            return {'success': False, 'error': f'Unknown animation type: {animation_type}'}
        
        if output_file:
            commands += f"ray\npng {output_file}\n"
        
        return self.execute_pymol_script(commands)
    
    def get_version(self) -> str:
        """Get PyMOL version"""
        if not self.is_available():
            return "Not available"
        
        try:
            result = subprocess.run([self.pymol_path, '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return "Unknown"
        except Exception as e:
            logger.error(f"Error getting PyMOL version: {e}")
            return "Unknown"
    
    def cleanup_session(self):
        """Clean up PyMOL session data"""
        self.session_data.clear()
        logger.info("PyMOL session data cleaned up")
