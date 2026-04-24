"""
AI Integration Module for Cancer Genomics Analysis Suite

This module provides comprehensive AI, LLM, and deep learning capabilities
for advanced cancer genomics analysis including:

- Deep learning models for genomic sequence analysis
- Large Language Model integration for scientific literature processing
- AI-powered data preprocessing and feature engineering
- Intelligent visualization and automated insights
- Natural language query interface
- Predictive analytics with advanced architectures
"""

from .deep_learning_models import (
    GenomicSequenceAnalyzer,
    MutationEffectPredictor,
    DrugResponsePredictor,
    SurvivalAnalysisModel,
    MultiOmicsIntegrator
)

from .llm_integration import (
    ScientificLiteratureProcessor,
    ClinicalNotesAnalyzer,
    GenomicQueryEngine,
    ReportGenerator
)

from .ai_data_processing import (
    IntelligentDataPreprocessor,
    FeatureEngineeringEngine,
    QualityControlAI,
    AnomalyDetector
)

from .ai_visualization import (
    AIInsightGenerator,
    AutomatedReportBuilder,
    InteractiveVisualizationAI,
    PatternRecognitionEngine
)

from .ai_chatbot import (
    GenomicAnalysisAssistant,
    QueryProcessor,
    ContextManager
)

from .predictive_analytics import (
    AdvancedMLPipeline,
    EnsemblePredictor,
    HyperparameterOptimizer,
    ModelInterpretabilityEngine
)

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite AI Team"

__all__ = [
    # Deep Learning Models
    "GenomicSequenceAnalyzer",
    "MutationEffectPredictor", 
    "DrugResponsePredictor",
    "SurvivalAnalysisModel",
    "MultiOmicsIntegrator",
    
    # LLM Integration
    "ScientificLiteratureProcessor",
    "ClinicalNotesAnalyzer",
    "GenomicQueryEngine",
    "ReportGenerator",
    
    # AI Data Processing
    "IntelligentDataPreprocessor",
    "FeatureEngineeringEngine",
    "QualityControlAI",
    "AnomalyDetector",
    
    # AI Visualization
    "AIInsightGenerator",
    "AutomatedReportBuilder",
    "InteractiveVisualizationAI",
    "PatternRecognitionEngine",
    
    # AI Chatbot
    "GenomicAnalysisAssistant",
    "QueryProcessor",
    "ContextManager",
    
    # Predictive Analytics
    "AdvancedMLPipeline",
    "EnsemblePredictor",
    "HyperparameterOptimizer",
    "ModelInterpretabilityEngine"
]
