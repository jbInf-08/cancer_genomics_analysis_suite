"""
Mutation Effect Predictor Module

This module provides comprehensive mutation effect prediction functionality including:
- Core prediction algorithms (SIFT, PolyPhen-2, CADD, REVEL, etc.)
- Clinical significance assessment
- Consensus prediction analysis
- Interactive web interface for mutation analysis
- Batch processing capabilities
- Data export in multiple formats

Classes:
    MutationEffectPredictor: Main prediction engine
    Mutation: Represents genetic mutations
    PredictionResult: Stores prediction results
    MutationEffectDashboard: Dash-based web interface

Functions:
    create_sample_mutations: Create sample mutations for testing
    create_sample_predictor: Create predictor with sample data
    create_mutation_effect_dashboard: Create dashboard instance
"""

from .predictor import (
    MutationEffectPredictor,
    Mutation,
    PredictionResult,
    create_sample_mutations,
    create_sample_predictor
)

from .mutation_dash import (
    MutationEffectDashboard,
    create_mutation_effect_dashboard
)

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite"
__email__ = "support@cancergenomics.com"

# Module metadata
__all__ = [
    "MutationEffectPredictor",
    "Mutation",
    "PredictionResult",
    "MutationEffectDashboard",
    "create_sample_mutations",
    "create_sample_predictor",
    "create_mutation_effect_dashboard"
]

# Module description
__doc__ = """
Mutation Effect Predictor Module for Cancer Genomics Analysis Suite

This module provides a comprehensive solution for predicting the functional
impact of genetic mutations on protein structure, function, and disease
association. It integrates multiple prediction algorithms and provides both
programmatic and interactive web interfaces.

Key Features:
- Multiple prediction algorithms (SIFT, PolyPhen-2, CADD, REVEL, ClinVar, etc.)
- Consensus prediction analysis
- Clinical significance assessment
- Interactive web dashboard with real-time visualization
- Batch processing capabilities
- Data export in multiple formats (JSON, CSV, TSV)
- Caching for improved performance
- Extensible architecture for custom predictors

Supported Prediction Methods:
- SIFT: Sorting Intolerant From Tolerant
- PolyPhen-2: Polymorphism Phenotyping v2
- CADD: Combined Annotation Dependent Depletion
- REVEL: Rare Exome Variant Ensemble Learner
- ClinVar: Clinical significance database
- Conservation: Evolutionary conservation analysis
- Structural: Protein structure impact analysis

Usage Examples:

Basic mutation prediction:
    from CancerGenomicsSuite.modules.mutation_effect_predictor import Mutation, MutationEffectPredictor
    
    mutation = Mutation(
        gene_symbol="BRCA1",
        chromosome="chr17",
        position=43094695,
        ref_allele="G",
        alt_allele="A",
        mutation_type="SNP",
        protein_position=185,
        ref_amino_acid="G",
        alt_amino_acid="E"
    )
    
    predictor = MutationEffectPredictor()
    results = predictor.predict_mutation_effect(mutation)
    
    for result in results:
        print(f"{result.predictor_name}: {result.prediction_class} (score: {result.prediction_score:.3f})")

Interactive dashboard:
    from CancerGenomicsSuite.modules.mutation_effect_predictor import create_mutation_effect_dashboard
    
    dashboard = create_mutation_effect_dashboard()
    dashboard.run(port=8051)

Batch processing:
    mutations = [mutation1, mutation2, mutation3]
    batch_results = predictor.batch_predict(mutations)
    
    for mutation_key, results in batch_results.items():
        consensus = predictor.get_consensus_prediction(results)
        print(f"Consensus for {mutation_key}: {consensus['consensus_class']}")

Export results:
    results = predictor.predict_mutation_effect(mutation)
    exported_data = predictor.export_predictions(results, format="json")
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
    """Initialize the mutation effect predictor module."""
    logger.info("Initializing Mutation Effect Predictor module")
    
    # Check for required dependencies
    try:
        import numpy
        import pandas
        import dash
        import plotly
        import requests
        logger.info("All required dependencies found")
    except ImportError as e:
        logger.warning(f"Missing dependency: {e}")
        logger.warning("Some features may not be available")
    
    # Log available predictors
    available_predictors = [
        "SIFT", "PolyPhen-2", "CADD", "REVEL", "ClinVar", 
        "Conservation", "Structural"
    ]
    
    logger.info(f"Available predictors: {', '.join(available_predictors)}")
    
    # Log supported mutation types
    supported_types = ["SNP", "insertion", "deletion", "indel", "complex"]
    logger.info(f"Supported mutation types: {', '.join(supported_types)}")
    
    # Log prediction classes
    prediction_classes = [
        "pathogenic", "likely_pathogenic", "uncertain_significance",
        "likely_benign", "benign"
    ]
    logger.info(f"Prediction classes: {', '.join(prediction_classes)}")

# Run initialization
_initialize_module()

# Module constants
DEFAULT_PREDICTORS = ["sift", "polyphen2", "cadd", "revel"]
DEFAULT_DASHBOARD_PORT = 8051
MAX_BATCH_SIZE = 1000
CACHE_SIZE_LIMIT = 10000

# Prediction score thresholds
SIFT_THRESHOLD = 0.05  # < 0.05 is deleterious
POLYPHEN2_THRESHOLD = 0.5  # > 0.5 is probably damaging
CADD_THRESHOLD = 15.0  # > 15 is likely deleterious
REVEL_THRESHOLD = 0.5  # > 0.5 is likely pathogenic

# Export constants
__all__.extend([
    "DEFAULT_PREDICTORS",
    "DEFAULT_DASHBOARD_PORT",
    "MAX_BATCH_SIZE", 
    "CACHE_SIZE_LIMIT",
    "SIFT_THRESHOLD",
    "POLYPHEN2_THRESHOLD",
    "CADD_THRESHOLD",
    "REVEL_THRESHOLD"
])
