"""
Cancer Genomics Analysis Suite

A comprehensive, production-ready platform for cancer genomics analysis featuring 
real-time mutation detection, clinical data integration, machine learning-based 
outcome prediction, and multi-omics data analysis.

This package provides:
- Real-time mutation detection and analysis
- Clinical data integration capabilities
- Machine learning-based outcome prediction
- Multi-omics data analysis support
- Graph database analytics with Neo4j
- Stream processing with Apache Kafka
- Pipeline orchestration with Snakemake and Nextflow
- Container orchestration with Kubernetes
- Infrastructure as Code with Terraform
- GitOps deployment with ArgoCD
- Comprehensive monitoring with Prometheus and Grafana
- Security features including TLS encryption and RBAC
- Bioinformatics tools integration
- CLI support for all integrated tools
- Plugin system for modular architecture
"""

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite Team"
__email__ = "support@cancer-genomics.com"
__description__ = "A comprehensive platform for cancer genomics analysis"

# Import main components
from .config.settings import settings
from .plugin_registry import get_registered_plugins, get_plugins_by_category

# Version info
VERSION_INFO = {
    "version": __version__,
    "author": __author__,
    "email": __email__,
    "description": __description__
}

# Package metadata
__all__ = [
    "__version__",
    "__author__", 
    "__email__",
    "__description__",
    "settings",
    "get_registered_plugins",
    "get_plugins_by_category",
    "VERSION_INFO"
]
