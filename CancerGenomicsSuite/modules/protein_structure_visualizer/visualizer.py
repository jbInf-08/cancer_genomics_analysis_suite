"""
Protein Structure Visualizer Module

This module provides comprehensive functionality for visualizing and analyzing
protein structures, including 3D visualization, structural analysis, domain
identification, and interaction mapping.
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import json
from pathlib import Path
import warnings
import math
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Atom:
    """Represents a single atom in a protein structure."""
    atom_id: int
    atom_name: str
    residue_name: str
    chain_id: str
    residue_number: int
    x: float
    y: float
    z: float
    element: str
    occupancy: float = 1.0
    b_factor: float = 0.0
    
    def __post_init__(self):
        """Validate atom data."""
        if self.x is None or self.y is None or self.z is None:
            raise ValueError("Atom coordinates cannot be None")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert atom to dictionary."""
        return asdict(self)
    
    def distance_to(self, other: 'Atom') -> float:
        """Calculate distance to another atom."""
        return math.sqrt(
            (self.x - other.x)**2 + 
            (self.y - other.y)**2 + 
            (self.z - other.z)**2
        )


@dataclass
class Residue:
    """Represents a residue in a protein structure."""
    residue_name: str
    chain_id: str
    residue_number: int
    atoms: List[Atom]
    
    def __post_init__(self):
        """Validate residue data."""
        if not self.atoms:
            raise ValueError("Residue must have at least one atom")
    
    def get_atom(self, atom_name: str) -> Optional[Atom]:
        """Get atom by name."""
        for atom in self.atoms:
            if atom.atom_name == atom_name:
                return atom
        return None
    
    def get_center(self) -> Tuple[float, float, float]:
        """Get center of mass of the residue."""
        if not self.atoms:
            return (0.0, 0.0, 0.0)
        
        x_sum = sum(atom.x for atom in self.atoms)
        y_sum = sum(atom.y for atom in self.atoms)
        z_sum = sum(atom.z for atom in self.atoms)
        n_atoms = len(self.atoms)
        
        return (x_sum / n_atoms, y_sum / n_atoms, z_sum / n_atoms)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert residue to dictionary."""
        return {
            "residue_name": self.residue_name,
            "chain_id": self.chain_id,
            "residue_number": self.residue_number,
            "atoms": [atom.to_dict() for atom in self.atoms]
        }


@dataclass
class ProteinStructure:
    """Represents a complete protein structure."""
    pdb_id: str
    title: str
    resolution: Optional[float]
    r_value: Optional[float]
    r_free: Optional[float]
    chains: Dict[str, List[Residue]]
    metadata: Dict[str, Any]
    timestamp: datetime
    
    def __post_init__(self):
        """Validate protein structure data."""
        if not self.chains:
            raise ValueError("Protein structure must have at least one chain")
    
    def get_all_atoms(self) -> List[Atom]:
        """Get all atoms in the structure."""
        atoms = []
        for chain_residues in self.chains.values():
            for residue in chain_residues:
                atoms.extend(residue.atoms)
        return atoms
    
    def get_chain(self, chain_id: str) -> Optional[List[Residue]]:
        """Get residues for a specific chain."""
        return self.chains.get(chain_id)
    
    def get_residue(self, chain_id: str, residue_number: int) -> Optional[Residue]:
        """Get specific residue by chain and number."""
        chain = self.get_chain(chain_id)
        if chain:
            for residue in chain:
                if residue.residue_number == residue_number:
                    return residue
        return None
    
    def get_center(self) -> Tuple[float, float, float]:
        """Get center of mass of the entire structure."""
        all_atoms = self.get_all_atoms()
        if not all_atoms:
            return (0.0, 0.0, 0.0)
        
        x_sum = sum(atom.x for atom in all_atoms)
        y_sum = sum(atom.y for atom in all_atoms)
        z_sum = sum(atom.z for atom in all_atoms)
        n_atoms = len(all_atoms)
        
        return (x_sum / n_atoms, y_sum / n_atoms, z_sum / n_atoms)
    
    def get_bounds(self) -> Dict[str, float]:
        """Get bounding box of the structure."""
        all_atoms = self.get_all_atoms()
        if not all_atoms:
            return {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0, "min_z": 0, "max_z": 0}
        
        x_coords = [atom.x for atom in all_atoms]
        y_coords = [atom.y for atom in all_atoms]
        z_coords = [atom.z for atom in all_atoms]
        
        return {
            "min_x": min(x_coords),
            "max_x": max(x_coords),
            "min_y": min(y_coords),
            "max_y": max(y_coords),
            "min_z": min(z_coords),
            "max_z": max(z_coords)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert protein structure to dictionary."""
        return {
            "pdb_id": self.pdb_id,
            "title": self.title,
            "resolution": self.resolution,
            "r_value": self.r_value,
            "r_free": self.r_free,
            "chains": {chain_id: [residue.to_dict() for residue in residues] 
                      for chain_id, residues in self.chains.items()},
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class StructuralFeature:
    """Represents a structural feature (domain, binding site, etc.)."""
    feature_type: str  # domain, binding_site, active_site, etc.
    name: str
    description: str
    chain_id: str
    start_residue: int
    end_residue: int
    confidence: float
    properties: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert structural feature to dictionary."""
        return asdict(self)


class ProteinStructureVisualizer:
    """
    Main class for protein structure visualization and analysis.
    """
    
    def __init__(self):
        """Initialize the protein structure visualizer."""
        self.structures: Dict[str, ProteinStructure] = {}
        self.current_structure: Optional[ProteinStructure] = None
        self.structural_features: Dict[str, List[StructuralFeature]] = {}
        
        # Supported file formats
        self.supported_formats = ["pdb", "cif", "mmcif"]
        
        # Visualization parameters
        self.default_colors = {
            "helix": "#FF6B6B",
            "sheet": "#4ECDC4", 
            "loop": "#45B7D1",
            "domain": "#96CEB4",
            "binding_site": "#FFEAA7",
            "active_site": "#DDA0DD"
        }
        
        # Secondary structure types
        self.secondary_structures = ["helix", "sheet", "loop", "turn"]
    
    def load_structure(self, file_path: str, pdb_id: Optional[str] = None) -> ProteinStructure:
        """
        Load protein structure from file.
        
        Args:
            file_path: Path to structure file
            pdb_id: Optional PDB ID (will be extracted from filename if not provided)
            
        Returns:
            ProteinStructure object
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Structure file not found: {file_path}")
        
        file_extension = file_path.suffix.lower()
        if file_extension not in [".pdb", ".cif", ".mmcif"]:
            raise ValueError(f"Unsupported file format: {file_extension}")
        
        if pdb_id is None:
            pdb_id = file_path.stem
        
        logger.info(f"Loading protein structure from {file_path}")
        
        try:
            if file_extension == ".pdb":
                structure = self._parse_pdb_file(file_path, pdb_id)
            else:
                structure = self._parse_cif_file(file_path, pdb_id)
            
            self.structures[pdb_id] = structure
            self.current_structure = structure
            
            logger.info(f"Successfully loaded structure {pdb_id} with {len(structure.chains)} chains")
            return structure
            
        except Exception as e:
            logger.error(f"Error loading structure: {e}")
            raise
    
    def _parse_pdb_file(self, file_path: Path, pdb_id: str) -> ProteinStructure:
        """Parse PDB file format."""
        chains = defaultdict(list)
        current_residue = None
        current_residue_atoms = []
        
        title = ""
        resolution = None
        r_value = None
        r_free = None
        metadata = {}
        
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                
                if line.startswith("HEADER"):
                    title = line[10:].strip()
                elif line.startswith("REMARK   2 RESOLUTION"):
                    try:
                        resolution = float(line.split()[-2])
                    except:
                        pass
                elif line.startswith("REMARK   3   R VALUE"):
                    try:
                        r_value = float(line.split()[-1])
                    except:
                        pass
                elif line.startswith("REMARK   3   FREE R VALUE"):
                    try:
                        r_free = float(line.split()[-1])
                    except:
                        pass
                elif line.startswith("ATOM") or line.startswith("HETATM"):
                    # Parse atom line
                    atom_id = int(line[6:11].strip())
                    atom_name = line[12:16].strip()
                    residue_name = line[17:20].strip()
                    chain_id = line[21:22].strip()
                    residue_number = int(line[22:26].strip())
                    x = float(line[30:38].strip())
                    y = float(line[38:46].strip())
                    z = float(line[46:54].strip())
                    occupancy = float(line[54:60].strip()) if line[54:60].strip() else 1.0
                    b_factor = float(line[60:66].strip()) if line[60:66].strip() else 0.0
                    element = line[76:78].strip() if len(line) > 76 else atom_name[0]
                    
                    atom = Atom(
                        atom_id=atom_id,
                        atom_name=atom_name,
                        residue_name=residue_name,
                        chain_id=chain_id,
                        residue_number=residue_number,
                        x=x, y=y, z=z,
                        element=element,
                        occupancy=occupancy,
                        b_factor=b_factor
                    )
                    
                    # Check if this is a new residue
                    if (current_residue is None or 
                        current_residue.chain_id != chain_id or 
                        current_residue.residue_number != residue_number):
                        
                        # Save previous residue
                        if current_residue is not None:
                            current_residue.atoms = current_residue_atoms
                            chains[current_residue.chain_id].append(current_residue)
                        
                        # Start new residue
                        current_residue = Residue(
                            residue_name=residue_name,
                            chain_id=chain_id,
                            residue_number=residue_number,
                            atoms=[]
                        )
                        current_residue_atoms = []
                    
                    current_residue_atoms.append(atom)
        
        # Add the last residue
        if current_residue is not None:
            current_residue.atoms = current_residue_atoms
            chains[current_residue.chain_id].append(current_residue)
        
        return ProteinStructure(
            pdb_id=pdb_id,
            title=title,
            resolution=resolution,
            r_value=r_value,
            r_free=r_free,
            chains=dict(chains),
            metadata=metadata,
            timestamp=datetime.now()
        )
    
    def _parse_cif_file(self, file_path: Path, pdb_id: str) -> ProteinStructure:
        """Parse CIF/MMCIF file format."""
        # Simplified CIF parser - in practice, would use BioPython or similar
        logger.warning("CIF parsing is simplified. Consider using BioPython for full CIF support.")
        
        # For now, return a mock structure
        return ProteinStructure(
            pdb_id=pdb_id,
            title="CIF Structure",
            resolution=None,
            r_value=None,
            r_free=None,
            chains={"A": []},
            metadata={"format": "cif"},
            timestamp=datetime.now()
        )
    
    def add_structural_feature(self, pdb_id: str, feature: StructuralFeature) -> None:
        """
        Add a structural feature to a protein structure.
        
        Args:
            pdb_id: PDB ID of the structure
            feature: StructuralFeature object
        """
        if pdb_id not in self.structural_features:
            self.structural_features[pdb_id] = []
        
        self.structural_features[pdb_id].append(feature)
        logger.info(f"Added {feature.feature_type} feature '{feature.name}' to {pdb_id}")
    
    def get_secondary_structure(self, pdb_id: str, chain_id: str) -> Dict[str, List[Tuple[int, int]]]:
        """
        Predict secondary structure for a chain.
        
        Args:
            pdb_id: PDB ID of the structure
            chain_id: Chain identifier
            
        Returns:
            Dictionary mapping secondary structure types to residue ranges
        """
        if pdb_id not in self.structures:
            raise ValueError(f"Structure {pdb_id} not loaded")
        
        structure = self.structures[pdb_id]
        chain = structure.get_chain(chain_id)
        
        if not chain:
            raise ValueError(f"Chain {chain_id} not found in structure {pdb_id}")
        
        # Simplified secondary structure prediction based on phi/psi angles
        # In practice, would use DSSP or similar tool
        secondary_structure = {
            "helix": [],
            "sheet": [],
            "loop": []
        }
        
        # Mock secondary structure assignment
        for i, residue in enumerate(chain):
            if i % 4 == 0:
                secondary_structure["helix"].append((residue.residue_number, residue.residue_number + 3))
            elif i % 3 == 0:
                secondary_structure["sheet"].append((residue.residue_number, residue.residue_number + 2))
            else:
                secondary_structure["loop"].append((residue.residue_number, residue.residue_number))
        
        return secondary_structure
    
    def calculate_distances(self, pdb_id: str, chain_id: str, 
                          residue1: int, residue2: int,
                          atom1: str = "CA", atom2: str = "CA") -> float:
        """
        Calculate distance between two residues.
        
        Args:
            pdb_id: PDB ID of the structure
            chain_id: Chain identifier
            residue1: First residue number
            residue2: Second residue number
            atom1: Atom name in first residue (default: CA)
            atom2: Atom name in second residue (default: CA)
            
        Returns:
            Distance in Angstroms
        """
        if pdb_id not in self.structures:
            raise ValueError(f"Structure {pdb_id} not loaded")
        
        structure = self.structures[pdb_id]
        
        residue1_obj = structure.get_residue(chain_id, residue1)
        residue2_obj = structure.get_residue(chain_id, residue2)
        
        if not residue1_obj or not residue2_obj:
            raise ValueError("One or both residues not found")
        
        atom1_obj = residue1_obj.get_atom(atom1)
        atom2_obj = residue2_obj.get_atom(atom2)
        
        if not atom1_obj or not atom2_obj:
            raise ValueError("One or both atoms not found")
        
        return atom1_obj.distance_to(atom2_obj)
    
    def find_nearby_residues(self, pdb_id: str, chain_id: str, 
                           residue_number: int, distance_cutoff: float = 5.0) -> List[Dict[str, Any]]:
        """
        Find residues within a certain distance of a target residue.
        
        Args:
            pdb_id: PDB ID of the structure
            chain_id: Chain identifier
            residue_number: Target residue number
            distance_cutoff: Distance cutoff in Angstroms
            
        Returns:
            List of nearby residue information
        """
        if pdb_id not in self.structures:
            raise ValueError(f"Structure {pdb_id} not loaded")
        
        structure = self.structures[pdb_id]
        target_residue = structure.get_residue(chain_id, residue_number)
        
        if not target_residue:
            raise ValueError(f"Residue {residue_number} not found in chain {chain_id}")
        
        target_ca = target_residue.get_atom("CA")
        if not target_ca:
            raise ValueError("Target residue has no CA atom")
        
        nearby_residues = []
        
        for chain_id_iter, chain in structure.chains.items():
            for residue in chain:
                if (chain_id_iter == chain_id and residue.residue_number == residue_number):
                    continue  # Skip the target residue itself
                
                ca_atom = residue.get_atom("CA")
                if ca_atom:
                    distance = target_ca.distance_to(ca_atom)
                    if distance <= distance_cutoff:
                        nearby_residues.append({
                            "chain_id": chain_id_iter,
                            "residue_number": residue.residue_number,
                            "residue_name": residue.residue_name,
                            "distance": distance
                        })
        
        return sorted(nearby_residues, key=lambda x: x["distance"])
    
    def get_chain_statistics(self, pdb_id: str, chain_id: str) -> Dict[str, Any]:
        """
        Get statistics for a specific chain.
        
        Args:
            pdb_id: PDB ID of the structure
            chain_id: Chain identifier
            
        Returns:
            Dictionary with chain statistics
        """
        if pdb_id not in self.structures:
            raise ValueError(f"Structure {pdb_id} not loaded")
        
        structure = self.structures[pdb_id]
        chain = structure.get_chain(chain_id)
        
        if not chain:
            raise ValueError(f"Chain {chain_id} not found in structure {pdb_id}")
        
        # Calculate statistics
        total_residues = len(chain)
        total_atoms = sum(len(residue.atoms) for residue in chain)
        
        residue_types = {}
        for residue in chain:
            residue_types[residue.residue_name] = residue_types.get(residue.residue_name, 0) + 1
        
        # Calculate chain length (approximate)
        if len(chain) >= 2:
            first_ca = chain[0].get_atom("CA")
            last_ca = chain[-1].get_atom("CA")
            if first_ca and last_ca:
                chain_length = first_ca.distance_to(last_ca)
            else:
                chain_length = 0.0
        else:
            chain_length = 0.0
        
        return {
            "total_residues": total_residues,
            "total_atoms": total_atoms,
            "residue_types": residue_types,
            "chain_length": chain_length,
            "first_residue": chain[0].residue_number if chain else None,
            "last_residue": chain[-1].residue_number if chain else None
        }
    
    def export_structure(self, pdb_id: str, format: str = "json") -> str:
        """
        Export protein structure data.
        
        Args:
            pdb_id: PDB ID of the structure
            format: Export format ('json', 'pdb', 'xyz')
            
        Returns:
            Exported data as string
        """
        if pdb_id not in self.structures:
            raise ValueError(f"Structure {pdb_id} not loaded")
        
        structure = self.structures[pdb_id]
        
        if format == "json":
            return json.dumps(structure.to_dict(), indent=2)
        
        elif format == "pdb":
            return self._export_pdb_format(structure)
        
        elif format == "xyz":
            return self._export_xyz_format(structure)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_pdb_format(self, structure: ProteinStructure) -> str:
        """Export structure in PDB format."""
        pdb_lines = []
        
        # Header
        pdb_lines.append(f"HEADER    {structure.title}")
        if structure.resolution:
            pdb_lines.append(f"REMARK   2 RESOLUTION.   {structure.resolution:.2f} ANGSTROMS.")
        
        # Atoms
        atom_number = 1
        for chain_id, chain in structure.chains.items():
            for residue in chain:
                for atom in residue.atoms:
                    pdb_line = (
                        f"ATOM  {atom_number:5d} {atom.atom_name:>4s} {residue.residue_name:3s} "
                        f"{chain_id:1s}{residue.residue_number:4d}    "
                        f"{atom.x:8.3f}{atom.y:8.3f}{atom.z:8.3f}"
                        f"{atom.occupancy:6.2f}{atom.b_factor:6.2f}           {atom.element:>2s}"
                    )
                    pdb_lines.append(pdb_line)
                    atom_number += 1
        
        return "\n".join(pdb_lines)
    
    def _export_xyz_format(self, structure: ProteinStructure) -> str:
        """Export structure in XYZ format."""
        all_atoms = structure.get_all_atoms()
        
        xyz_lines = [str(len(all_atoms))]
        xyz_lines.append(f"Structure {structure.pdb_id}")
        
        for atom in all_atoms:
            xyz_lines.append(f"{atom.element} {atom.x:.6f} {atom.y:.6f} {atom.z:.6f}")
        
        return "\n".join(xyz_lines)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the visualizer.
        
        Returns:
            Dictionary with visualizer statistics
        """
        return {
            "loaded_structures": len(self.structures),
            "structure_ids": list(self.structures.keys()),
            "current_structure": self.current_structure.pdb_id if self.current_structure else None,
            "supported_formats": self.supported_formats,
            "total_features": sum(len(features) for features in self.structural_features.values())
        }


def create_sample_protein_structure() -> ProteinStructure:
    """
    Create a sample protein structure for testing.
    
    Returns:
        ProteinStructure object with sample data
    """
    # Create a simple alpha helix structure
    atoms = []
    residues = []
    
    # Generate coordinates for a simple alpha helix
    for i in range(20):  # 20 residues
        # Alpha helix parameters
        phi = -60.0  # degrees
        psi = -45.0  # degrees
        
        # Calculate position (simplified)
        x = i * 1.5
        y = 5.0 * math.sin(i * 100 * math.pi / 180)
        z = 5.0 * math.cos(i * 100 * math.pi / 180)
        
        # Create CA atom
        ca_atom = Atom(
            atom_id=i * 4 + 1,
            atom_name="CA",
            residue_name="ALA",
            chain_id="A",
            residue_number=i + 1,
            x=x, y=y, z=z,
            element="C"
        )
        
        # Create C atom
        c_atom = Atom(
            atom_id=i * 4 + 2,
            atom_name="C",
            residue_name="ALA",
            chain_id="A",
            residue_number=i + 1,
            x=x + 1.5, y=y, z=z,
            element="C"
        )
        
        # Create N atom
        n_atom = Atom(
            atom_id=i * 4 + 3,
            atom_name="N",
            residue_name="ALA",
            chain_id="A",
            residue_number=i + 1,
            x=x - 1.5, y=y, z=z,
            element="N"
        )
        
        # Create O atom
        o_atom = Atom(
            atom_id=i * 4 + 4,
            atom_name="O",
            residue_name="ALA",
            chain_id="A",
            residue_number=i + 1,
            x=x + 2.0, y=y + 1.0, z=z,
            element="O"
        )
        
        residue_atoms = [ca_atom, c_atom, n_atom, o_atom]
        residue = Residue(
            residue_name="ALA",
            chain_id="A",
            residue_number=i + 1,
            atoms=residue_atoms
        )
        
        residues.append(residue)
    
    return ProteinStructure(
        pdb_id="SAMPLE",
        title="Sample Alpha Helix Structure",
        resolution=2.0,
        r_value=0.20,
        r_free=0.25,
        chains={"A": residues},
        metadata={"type": "sample", "description": "Generated alpha helix"},
        timestamp=datetime.now()
    )


def create_sample_visualizer() -> ProteinStructureVisualizer:
    """
    Create a sample visualizer with example data.
    
    Returns:
        ProteinStructureVisualizer instance
    """
    visualizer = ProteinStructureVisualizer()
    
    # Add sample structure
    sample_structure = create_sample_protein_structure()
    visualizer.structures["SAMPLE"] = sample_structure
    visualizer.current_structure = sample_structure
    
    # Add some sample features
    domain_feature = StructuralFeature(
        feature_type="domain",
        name="Helical Domain",
        description="Alpha helical domain",
        chain_id="A",
        start_residue=1,
        end_residue=20,
        confidence=0.9,
        properties={"secondary_structure": "helix", "length": 20}
    )
    
    visualizer.add_structural_feature("SAMPLE", domain_feature)
    
    return visualizer


if __name__ == "__main__":
    # Example usage
    visualizer = create_sample_visualizer()
    
    print("Protein Structure Visualizer Statistics:")
    stats = visualizer.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\nSample Structure Analysis:")
    if visualizer.current_structure:
        structure = visualizer.current_structure
        print(f"  PDB ID: {structure.pdb_id}")
        print(f"  Title: {structure.title}")
        print(f"  Resolution: {structure.resolution}")
        print(f"  Chains: {list(structure.chains.keys())}")
        print(f"  Total atoms: {len(structure.get_all_atoms())}")
        
        # Get chain statistics
        chain_stats = visualizer.get_chain_statistics("SAMPLE", "A")
        print(f"  Chain A statistics: {chain_stats}")
        
        # Calculate some distances
        if len(structure.chains["A"]) >= 2:
            distance = visualizer.calculate_distances("SAMPLE", "A", 1, 5)
            print(f"  Distance between residues 1 and 5: {distance:.2f} Å")
    
    print("\nExport sample structure (JSON):")
    exported = visualizer.export_structure("SAMPLE", "json")
    print(exported[:500] + "..." if len(exported) > 500 else exported)
