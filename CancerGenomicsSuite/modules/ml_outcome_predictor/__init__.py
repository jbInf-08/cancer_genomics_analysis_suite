"""
ML Outcome Predictor Module

This module provides machine learning capabilities for predicting cancer treatment outcomes
based on genomic and clinical data. It includes models for survival prediction, drug response
prediction, and treatment outcome classification.

Components:
- ml_engine: Core machine learning models and training pipelines
- outcome_utils: Utility functions for data preprocessing and validation
- ml_dash: Interactive dashboard for model training and prediction visualization
"""

from .ml_engine import (
    MLOutcomePredictor,
    SurvivalPredictor,
    DrugResponsePredictor,
    TreatmentOutcomeClassifier,
    ModelTrainer,
    PredictionPipeline
)

from .outcome_utils import (
    DataPreprocessor,
    FeatureSelector,
    ModelValidator,
    OutcomeMetrics,
    DataValidator,
    FeatureEngineering
)

from .ml_dash import (
    MLOutcomeDashboard,
    create_ml_dashboard,
    register_ml_routes
)

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite"

__all__ = [
    # ML Engine components
    "MLOutcomePredictor",
    "SurvivalPredictor", 
    "DrugResponsePredictor",
    "TreatmentOutcomeClassifier",
    "ModelTrainer",
    "PredictionPipeline",
    
    # Utility components
    "DataPreprocessor",
    "FeatureSelector",
    "ModelValidator",
    "OutcomeMetrics",
    "DataValidator",
    "FeatureEngineering",
    
    # Dashboard components
    "MLOutcomeDashboard",
    "create_ml_dashboard",
    "register_ml_routes"
]
