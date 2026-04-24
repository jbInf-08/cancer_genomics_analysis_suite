"""
Protein Structure Visualizer Module

This module provides comprehensive protein structure visualization and analysis functionality including:
- 3D structure loading and parsing (PDB, CIF formats)
- Interactive 3D visualization with multiple representations
- Structural analysis and feature identification
- Distance calculations and nearby residue analysis
- Secondary structure prediction and analysis
- Domain and binding site annotation
- Export capabilities in multiple formats

Classes:
    ProteinStructureVisualizer: Main visualization engine
    ProteinStructure: Data structure for protein structures
    Atom: Represents individual atoms
    Residue: Represents protein residues
    StructuralFeature: Represents structural features (domains, binding sites)
    ProteinStructureDashboard: Dash-based web interface

Functions:
    create_sample_protein_structure: Create sample structure for testing
    create_sample_visualizer: Create visualizer with sample data
    create_protein_structure_dashboard: Create dashboard instance
"""

from .visualizer import (
    ProteinStructureVisualizer,
    ProteinStructure,
    Atom,
    Residue,
    StructuralFeature,
    create_sample_protein_structure,
    create_sample_visualizer
)

from .structure_dash import (
    ProteinStructureDashboard,
    create_protein_structure_dashboard
)

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite"
__email__ = "support@cancergenomics.com"

# Module metadata
__all__ = [
    "ProteinStructureVisualizer",
    "ProteinStructure",
    "Atom",
    "Residue",
    "StructuralFeature",
    "ProteinStructureDashboard",
    "create_sample_protein_structure",
    "create_sample_visualizer",
    "create_protein_structure_dashboard"
]

# Module description
__doc__ = """
Protein Structure Visualizer Module for Cancer Genomics Analysis Suite

This module provides a comprehensive solution for protein structure visualization
and analysis, including 3D structure loading, interactive visualization, structural
analysis, and feature identification. It offers both programmatic and interactive
web interfaces for analyzing protein structures.

Key Features:
- Multiple file format support (PDB, CIF, MMCIF)
- Interactive 3D visualization with multiple representations
- Structural analysis and feature identification
- Distance calculations and geometric analysis
- Secondary structure prediction and analysis
- Domain and binding site annotation
- Export capabilities in multiple formats
- Web-based dashboard with real-time visualization

Supported File Formats:
- PDB (Protein Data Bank)
- CIF (Crystallographic Information File)
- MMCIF (Macromolecular Crystallographic Information File)

Visualization Representations:
- Cartoon (backbone trace)
- Stick (atomic bonds)
- Sphere (atomic spheres)
- Surface (molecular surface)
- Ribbon (secondary structure ribbon)

Color Schemes:
- Chain-based coloring
- Secondary structure coloring
- Residue type coloring
- B-factor coloring
- Hydrophobicity coloring

Analysis Capabilities:
- Distance calculations between atoms/residues
- Nearby residue identification
- Secondary structure prediction
- Structural feature annotation
- Chain statistics and properties
- Geometric analysis

Usage Examples:

Basic structure loading and visualization:
    from CancerGenomicsSuite.modules.protein_structure_visualizer import ProteinStructureVisualizer
    
    visualizer = ProteinStructureVisualizer()
    structure = visualizer.load_structure("protein.pdb", "1CRN")
    
    # Calculate distance between residues
    distance = visualizer.calculate_distances("1CRN", "A", 10, 20)
    print(f"Distance between residues 10 and 20: {distance:.2f} Å")
    
    # Find nearby residues
    nearby = visualizer.find_nearby_residues("1CRN", "A", 15, distance_cutoff=5.0)
    print(f"Found {len(nearby)} nearby residues")

Interactive dashboard:
    from CancerGenomicsSuite.modules.protein_structure_visualizer import create_protein_structure_dashboard
    
    dashboard = create_protein_structure_dashboard()
    dashboard.run(port=8053)

Structural analysis:
    # Get chain statistics
    stats = visualizer.get_chain_statistics("1CRN", "A")
    print(f"Chain A has {stats['total_residues']} residues")
    
    # Predict secondary structure
    secondary_structure = visualizer.get_secondary_structure("1CRN", "A")
    print(f"Secondary structure: {secondary_structure}")
    
    # Add structural features
    domain = StructuralFeature(
        feature_type="domain",
        name="Catalytic Domain",
        description="Enzymatic active site",
        chain_id="A",
        start_residue=50,
        end_residue=150,
        confidence=0.9,
        properties={"function": "catalysis"}
    )
    visualizer.add_structural_feature("1CRN", domain)

Export structure data:
    # Export in different formats
    json_data = visualizer.export_structure("1CRN", "json")
    pdb_data = visualizer.export_structure("1CRN", "pdb")
    xyz_data = visualizer.export_structure("1CRN", "xyz")
"""

# Initialize module logging
import logging

# Create module logger
logger = logging.getLogger(__name__)

# Set default logging level
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Module initialization
def _initialize_module():
    """Initialize the protein structure visualizer module."""
    logger.info("Initializing Protein Structure Visualizer module")
    
    # Check for required dependencies
    try:
        import numpy
        import pandas
        import plotly
        import dash
        logger.info("All required dependencies found")
    except ImportError as e:
        logger.warning(f"Missing dependency: {e}")
        logger.warning("Some features may not be available")
    
    # Log supported file formats
    supported_formats = ["pdb", "cif", "mmcif"]
    logger.info(f"Supported file formats: {', '.join(supported_formats)}")
    
    # Log visualization representations
    representations = ["cartoon", "stick", "sphere", "surface", "ribbon"]
    logger.info(f"Visualization representations: {', '.join(representations)}")
    
    # Log color schemes
    color_schemes = ["chain", "secondary", "residue", "bfactor", "hydrophobicity"]
    logger.info(f"Color schemes: {', '.join(color_schemes)}")
    
    # Log analysis capabilities
    analysis_capabilities = [
        "distance_calculation", "nearby_residues", "secondary_structure",
        "structural_features", "chain_statistics", "geometric_analysis"
    ]
    logger.info(f"Analysis capabilities: {', '.join(analysis_capabilities)}")

# Run initialization
_initialize_module()

# Module constants
DEFAULT_DASHBOARD_PORT = 8053
DEFAULT_DISTANCE_CUTOFF = 5.0
DEFAULT_REPRESENTATION = "cartoon"
DEFAULT_COLOR_SCHEME = "chain"

# Visualization parameters
DEFAULT_ATOM_SIZE = 3
DEFAULT_BOND_WIDTH = 8
DEFAULT_SURFACE_OPACITY = 0.7

# Analysis parameters
DEFAULT_CONFIDENCE_THRESHOLD = 0.5
DEFAULT_FEATURE_TYPES = ["domain", "binding_site", "active_site", "secondary_structure"]

# Export constants
__all__.extend([
    "DEFAULT_DASHBOARD_PORT",
    "DEFAULT_DISTANCE_CUTOFF",
    "DEFAULT_REPRESENTATION",
    "DEFAULT_COLOR_SCHEME",
    "DEFAULT_ATOM_SIZE",
    "DEFAULT_BOND_WIDTH",
    "DEFAULT_SURFACE_OPACITY",
    "DEFAULT_CONFIDENCE_THRESHOLD",
    "DEFAULT_FEATURE_TYPES"
])
