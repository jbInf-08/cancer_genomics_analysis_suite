"""
Genome Browser Module

This module provides comprehensive genome browser functionality including:
- Core genome browser classes for data management and navigation
- Interactive Dash-based web interface
- Support for multiple reference genomes
- Feature visualization and annotation
- Data export capabilities
- UCSC Genome Browser integration

Classes:
    GenomeBrowser: Main genome browser class
    UCSCGenomeBrowser: Genome browser with UCSC integration
    GenomeBrowserDashboard: Dash-based web interface
    GenomicRegion: Represents genomic coordinates
    GenomicFeature: Represents annotated genomic features

Functions:
    create_sample_genome_browser: Create browser with sample data
    create_genome_browser_dashboard: Create dashboard instance
"""

from .browser import (
    GenomeBrowser,
    UCSCGenomeBrowser,
    GenomicRegion,
    GenomicFeature,
    create_sample_genome_browser
)

from .browser_dash import (
    GenomeBrowserDashboard,
    create_genome_browser_dashboard
)

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite"
__email__ = "support@cancergenomics.com"

# Module metadata
__all__ = [
    "GenomeBrowser",
    "UCSCGenomeBrowser", 
    "GenomeBrowserDashboard",
    "GenomicRegion",
    "GenomicFeature",
    "create_sample_genome_browser",
    "create_genome_browser_dashboard"
]

# Module description
__doc__ = """
Genome Browser Module for Cancer Genomics Analysis Suite

This module provides a comprehensive genome browser solution with both
programmatic and interactive web interfaces. It supports multiple reference
genomes, feature annotation, data visualization, and integration with
external data sources like UCSC Genome Browser.

Key Features:
- Interactive genomic region navigation (zoom, pan, search)
- Support for multiple reference genomes (hg38, hg19, mm10, etc.)
- Feature annotation and visualization
- Data export in multiple formats (JSON, BED, GFF3)
- Web-based dashboard with real-time updates
- UCSC Genome Browser API integration
- Extensible architecture for custom features

Usage Examples:

Basic genome browser:
    from CancerGenomicsSuite.modules.genome_browser import GenomeBrowser
    
    browser = GenomeBrowser("hg38")
    browser.set_region("chr17", 43000000, 43100000)
    features = browser.get_features_in_region()

Interactive dashboard:
    from CancerGenomicsSuite.modules.genome_browser import create_genome_browser_dashboard
    
    dashboard = create_genome_browser_dashboard()
    dashboard.run(port=8050)

UCSC integration:
    from CancerGenomicsSuite.modules.genome_browser import UCSCGenomeBrowser
    
    ucsc_browser = UCSCGenomeBrowser("hg38")
    tracks = ucsc_browser.get_ucsc_tracks()
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
    """Initialize the genome browser module."""
    logger.info("Initializing Genome Browser module")
    
    # Check for required dependencies
    try:
        import dash
        import plotly
        import pandas
        import requests
        logger.info("All required dependencies found")
    except ImportError as e:
        logger.warning(f"Missing dependency: {e}")
        logger.warning("Some features may not be available")
    
    # Log supported reference genomes
    supported_genomes = {
        "hg38": "Human (GRCh38)",
        "hg19": "Human (GRCh37)", 
        "mm10": "Mouse (GRCm38)",
        "mm9": "Mouse (NCBIM37)",
        "dm6": "Drosophila (BDGP6)",
        "ce11": "C. elegans (WBcel235)"
    }
    
    logger.info(f"Supported reference genomes: {list(supported_genomes.keys())}")

# Run initialization
_initialize_module()

# Module constants
DEFAULT_REFERENCE_GENOME = "hg38"
DEFAULT_DASHBOARD_PORT = 8050
MAX_FEATURES_DISPLAY = 1000
DEFAULT_ZOOM_FACTOR = 2.0
DEFAULT_PAN_DISTANCE = 10000

# Export constants
__all__.extend([
    "DEFAULT_REFERENCE_GENOME",
    "DEFAULT_DASHBOARD_PORT", 
    "MAX_FEATURES_DISPLAY",
    "DEFAULT_ZOOM_FACTOR",
    "DEFAULT_PAN_DISTANCE"
])
