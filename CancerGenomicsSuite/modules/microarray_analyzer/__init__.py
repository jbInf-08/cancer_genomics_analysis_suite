"""
Microarray Analyzer Module

This module provides comprehensive microarray data analysis functionality including:
- Data loading and preprocessing
- Multiple normalization methods
- Differential expression analysis
- Clustering and dimensionality reduction
- Interactive web interface for analysis
- Quality control and visualization
- Export capabilities

Classes:
    MicroarrayAnalyzer: Main analysis engine
    MicroarrayData: Data structure for microarray data
    DifferentialExpressionResult: Results from differential expression analysis
    ClusteringResult: Results from clustering analysis
    MicroarrayDashboard: Dash-based web interface

Functions:
    create_sample_microarray_data: Create sample data for testing
    create_sample_analyzer: Create analyzer with sample data
    create_microarray_dashboard: Create dashboard instance
"""

from .microarray import (
    MicroarrayAnalyzer,
    MicroarrayData,
    DifferentialExpressionResult,
    ClusteringResult,
    create_sample_microarray_data,
    create_sample_analyzer
)

from .microarray_dash import (
    MicroarrayDashboard,
    create_microarray_dashboard
)

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite"
__email__ = "support@cancergenomics.com"

# Module metadata
__all__ = [
    "MicroarrayAnalyzer",
    "MicroarrayData",
    "DifferentialExpressionResult",
    "ClusteringResult",
    "MicroarrayDashboard",
    "create_sample_microarray_data",
    "create_sample_analyzer",
    "create_microarray_dashboard"
]

# Module description
__doc__ = """
Microarray Analyzer Module for Cancer Genomics Analysis Suite

This module provides a comprehensive solution for microarray data analysis,
including data preprocessing, normalization, differential expression analysis,
clustering, and visualization. It offers both programmatic and interactive
web interfaces for analyzing gene expression data.

Key Features:
- Multiple data loading formats (CSV, TSV)
- Various normalization methods (Quantile, RMA, LOESS, VSN)
- Differential expression analysis with statistical testing
- Clustering algorithms (K-means, Hierarchical)
- Principal Component Analysis (PCA)
- Quality control metrics and visualization
- Interactive web dashboard with real-time analysis
- Export capabilities in multiple formats
- Support for multiple microarray platforms

Supported Platforms:
- Affymetrix
- Illumina
- Agilent
- NimbleGen
- Custom platforms

Normalization Methods:
- Quantile normalization
- RMA (Robust Multi-array Average)
- LOESS normalization
- VSN (Variance Stabilizing Normalization)
- No normalization

Analysis Capabilities:
- Differential expression analysis (t-test, fold change)
- Multiple testing correction (Benjamini-Hochberg)
- Clustering analysis (K-means, Hierarchical)
- Principal Component Analysis
- Quality control metrics
- Expression heatmaps
- Volcano plots
- PCA plots

Usage Examples:

Basic microarray analysis:
    from CancerGenomicsSuite.modules.microarray_analyzer import MicroarrayAnalyzer
    
    analyzer = MicroarrayAnalyzer()
    data = analyzer.load_data("expression.csv", "samples.csv", "genes.csv")
    analyzer.normalize_data("quantile")
    results = analyzer.perform_differential_expression("group", "Control", "Treatment")
    
    top_genes = analyzer.get_top_differentially_expressed(n=100)

Interactive dashboard:
    from CancerGenomicsSuite.modules.microarray_analyzer import create_microarray_dashboard
    
    dashboard = create_microarray_dashboard()
    dashboard.run(port=8052)

Clustering analysis:
    analyzer.perform_clustering("kmeans", n_clusters=3)
    clustering_results = analyzer.clustering_results
    
    print(f"Silhouette score: {clustering_results.silhouette_score}")

PCA analysis:
    pca_results = analyzer.perform_pca(n_components=2)
    print(f"Explained variance: {pca_results['explained_variance_ratio']}")

Export results:
    exported_data = analyzer.export_results(format="json")
    print(exported_data)
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
    """Initialize the microarray analyzer module."""
    logger.info("Initializing Microarray Analyzer module")
    
    # Check for required dependencies
    try:
        import numpy
        import pandas
        import scipy
        import sklearn
        import matplotlib
        import seaborn
        import dash
        import plotly
        logger.info("All required dependencies found")
    except ImportError as e:
        logger.warning(f"Missing dependency: {e}")
        logger.warning("Some features may not be available")
    
    # Log supported platforms
    supported_platforms = [
        "Affymetrix", "Illumina", "Agilent", "NimbleGen", "Custom"
    ]
    logger.info(f"Supported platforms: {', '.join(supported_platforms)}")
    
    # Log normalization methods
    normalization_methods = [
        "quantile", "rma", "gcrma", "mas5", "loess", "vsn", "none"
    ]
    logger.info(f"Normalization methods: {', '.join(normalization_methods)}")
    
    # Log analysis capabilities
    analysis_capabilities = [
        "differential_expression", "clustering", "pca", "quality_control"
    ]
    logger.info(f"Analysis capabilities: {', '.join(analysis_capabilities)}")

# Run initialization
_initialize_module()

# Module constants
DEFAULT_NORMALIZATION_METHOD = "quantile"
DEFAULT_DASHBOARD_PORT = 8052
DEFAULT_FOLD_CHANGE_THRESHOLD = 1.5
DEFAULT_P_VALUE_THRESHOLD = 0.05
DEFAULT_ADJUSTED_P_VALUE_THRESHOLD = 0.05
DEFAULT_N_CLUSTERS = 3
DEFAULT_PCA_COMPONENTS = 2

# Quality control thresholds
MIN_EXPRESSION_THRESHOLD = 0.1
MAX_MISSING_PERCENTAGE = 0.2
MIN_CV_THRESHOLD = 0.1
MAX_CV_THRESHOLD = 2.0

# Export constants
__all__.extend([
    "DEFAULT_NORMALIZATION_METHOD",
    "DEFAULT_DASHBOARD_PORT",
    "DEFAULT_FOLD_CHANGE_THRESHOLD",
    "DEFAULT_P_VALUE_THRESHOLD",
    "DEFAULT_ADJUSTED_P_VALUE_THRESHOLD",
    "DEFAULT_N_CLUSTERS",
    "DEFAULT_PCA_COMPONENTS",
    "MIN_EXPRESSION_THRESHOLD",
    "MAX_MISSING_PERCENTAGE",
    "MIN_CV_THRESHOLD",
    "MAX_CV_THRESHOLD"
])
