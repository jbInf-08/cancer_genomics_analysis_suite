"""
AI Integration Configuration for Cancer Genomics Analysis Suite

This module provides configuration settings for all AI, LLM, and deep learning
components integrated into the cancer genomics analysis platform.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AIConfig:
    """Main AI configuration class."""
    
    # API Keys and Authentication
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv('OPENAI_API_KEY'))
    anthropic_api_key: Optional[str] = field(default_factory=lambda: os.getenv('ANTHROPIC_API_KEY'))
    huggingface_token: Optional[str] = field(default_factory=lambda: os.getenv('HUGGINGFACE_TOKEN'))
    
    # Model Configurations
    default_llm_model: str = "gpt-3.5-turbo"
    default_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    default_vision_model: str = "openai/clip-vit-base-patch32"
    
    # Deep Learning Models
    deep_learning_config: Dict[str, Any] = field(default_factory=lambda: {
        'device': 'auto',  # auto, cpu, cuda
        'batch_size': 32,
        'learning_rate': 0.001,
        'max_epochs': 100,
        'early_stopping_patience': 10,
        'model_checkpointing': True,
        'mixed_precision': True
    })
    
    # LLM Configuration
    llm_config: Dict[str, Any] = field(default_factory=lambda: {
        'max_tokens': 2000,
        'temperature': 0.7,
        'top_p': 1.0,
        'frequency_penalty': 0.0,
        'presence_penalty': 0.0,
        'chunk_size': 1000,
        'chunk_overlap': 200,
        'context_window': 10
    })
    
    # Data Processing Configuration
    data_processing_config: Dict[str, Any] = field(default_factory=lambda: {
        'missing_value_threshold': 0.3,
        'outlier_detection_method': 'isolation_forest',
        'feature_selection_method': 'random_forest',
        'n_features_to_select': 100,
        'scaling_method': 'robust',
        'imputation_method': 'knn',
        'anomaly_threshold': 0.1,
        'quality_threshold': 0.8
    })
    
    # Visualization Configuration
    visualization_config: Dict[str, Any] = field(default_factory=lambda: {
        'default_style': 'plotly',
        'color_palette': 'viridis',
        'figure_size': (12, 8),
        'dpi': 300,
        'interactive': True,
        'auto_insights': True,
        'pattern_detection': True,
        'clustering_method': 'kmeans',
        'dimensionality_reduction': 'pca'
    })
    
    # Chatbot Configuration
    chatbot_config: Dict[str, Any] = field(default_factory=lambda: {
        'model_name': 'gpt-3.5-turbo',
        'max_tokens': 1000,
        'temperature': 0.7,
        'memory_type': 'buffer',  # buffer, summary
        'context_window': 10,
        'response_style': 'professional'  # professional, casual, technical
    })
    
    # Predictive Analytics Configuration
    predictive_config: Dict[str, Any] = field(default_factory=lambda: {
        'task_type': 'classification',  # classification, regression, survival
        'test_size': 0.2,
        'random_state': 42,
        'cv_folds': 5,
        'scoring_metric': 'auto',
        'feature_selection': True,
        'n_features': 100,
        'hyperparameter_optimization': True,
        'n_trials': 100,
        'model_interpretability': True
    })
    
    # File Paths
    paths: Dict[str, str] = field(default_factory=lambda: {
        'knowledge_base': './knowledge_base',
        'vector_db': './vector_db',
        'model_cache': './model_cache',
        'reports': './reports',
        'logs': './logs',
        'data': './data',
        'outputs': './outputs'
    })
    
    # Performance Configuration
    performance_config: Dict[str, Any] = field(default_factory=lambda: {
        'max_workers': 4,
        'memory_limit_gb': 8,
        'gpu_memory_fraction': 0.8,
        'enable_caching': True,
        'cache_size_mb': 1000,
        'parallel_processing': True
    })
    
    # Security Configuration
    security_config: Dict[str, Any] = field(default_factory=lambda: {
        'encrypt_sensitive_data': True,
        'log_api_calls': False,
        'rate_limiting': True,
        'max_requests_per_minute': 60,
        'data_anonymization': True
    })
    
    # Monitoring Configuration
    monitoring_config: Dict[str, Any] = field(default_factory=lambda: {
        'enable_logging': True,
        'log_level': 'INFO',
        'enable_metrics': True,
        'enable_tracing': False,
        'alert_thresholds': {
            'error_rate': 0.05,
            'response_time_ms': 5000,
            'memory_usage_percent': 80
        }
    })


@dataclass
class ModelConfig:
    """Configuration for specific AI models."""
    
    # Genomic Sequence Analysis
    genomic_sequence_config: Dict[str, Any] = field(default_factory=lambda: {
        'sequence_length': 1000,
        'embedding_dim': 128,
        'hidden_dim': 256,
        'num_layers': 3,
        'dropout': 0.3,
        'model_type': 'cnn'  # cnn, lstm, transformer
    })
    
    # Mutation Effect Prediction
    mutation_prediction_config: Dict[str, Any] = field(default_factory=lambda: {
        'prediction_classes': [
            'pathogenic', 'likely_pathogenic', 'uncertain_significance',
            'likely_benign', 'benign'
        ],
        'conservation_threshold': 0.5,
        'functional_threshold': 0.7
    })
    
    # Drug Response Prediction
    drug_response_config: Dict[str, Any] = field(default_factory=lambda: {
        'response_categories': ['Resistant', 'Moderate', 'Sensitive'],
        'confidence_threshold': 0.7,
        'feature_importance_threshold': 0.1
    })
    
    # Survival Analysis
    survival_analysis_config: Dict[str, Any] = field(default_factory=lambda: {
        'risk_categories': ['Low Risk', 'Medium Risk', 'High Risk'],
        'time_horizon_months': 60,
        'censoring_threshold': 0.1
    })
    
    # Multi-omics Integration
    multi_omics_config: Dict[str, Any] = field(default_factory=lambda: {
        'omics_types': ['genomics', 'transcriptomics', 'proteomics', 'metabolomics'],
        'integration_method': 'concatenation',  # concatenation, pca, ica, cca, pls, network
        'missing_data_strategy': 'impute',  # impute, remove, model
        'normalization_method': 'quantile'
    })


@dataclass
class LLMConfig:
    """Configuration for Large Language Models."""
    
    # OpenAI Configuration
    openai_config: Dict[str, Any] = field(default_factory=lambda: {
        'model': 'gpt-3.5-turbo',
        'max_tokens': 2000,
        'temperature': 0.7,
        'top_p': 1.0,
        'frequency_penalty': 0.0,
        'presence_penalty': 0.0,
        'timeout': 30
    })
    
    # Anthropic Configuration
    anthropic_config: Dict[str, Any] = field(default_factory=lambda: {
        'model': 'claude-2',
        'max_tokens': 2000,
        'temperature': 0.7,
        'timeout': 30
    })
    
    # Hugging Face Configuration
    huggingface_config: Dict[str, Any] = field(default_factory=lambda: {
        'model_name': 'microsoft/DialoGPT-medium',
        'max_length': 1000,
        'temperature': 0.7,
        'do_sample': True,
        'pad_token_id': 50256
    })
    
    # Embedding Configuration
    embedding_config: Dict[str, Any] = field(default_factory=lambda: {
        'model_name': 'sentence-transformers/all-MiniLM-L6-v2',
        'batch_size': 32,
        'device': 'auto',
        'normalize_embeddings': True
    })
    
    # Vector Database Configuration
    vector_db_config: Dict[str, Any] = field(default_factory=lambda: {
        'type': 'chroma',  # chroma, faiss, pinecone
        'persist_directory': './vector_db',
        'collection_name': 'genomic_knowledge',
        'distance_metric': 'cosine',
        'n_results': 5
    })


@dataclass
class VisualizationConfig:
    """Configuration for AI-powered visualizations."""
    
    # Plot Configuration
    plot_config: Dict[str, Any] = field(default_factory=lambda: {
        'style': 'plotly',
        'theme': 'plotly_white',
        'color_palette': 'viridis',
        'figure_size': (12, 8),
        'dpi': 300,
        'transparent': False
    })
    
    # Interactive Features
    interactive_config: Dict[str, Any] = field(default_factory=lambda: {
        'enable_zoom': True,
        'enable_pan': True,
        'enable_hover': True,
        'enable_click': True,
        'enable_brush': True,
        'enable_lasso': True
    })
    
    # AI Features
    ai_features_config: Dict[str, Any] = field(default_factory=lambda: {
        'auto_insights': True,
        'pattern_detection': True,
        'anomaly_highlighting': True,
        'smart_filtering': True,
        'dynamic_recommendations': True,
        'contextual_help': True
    })
    
    # Dashboard Configuration
    dashboard_config: Dict[str, Any] = field(default_factory=lambda: {
        'layout': 'grid',  # grid, sidebar, tabs
        'responsive': True,
        'auto_refresh': False,
        'refresh_interval': 30,  # seconds
        'max_components': 20
    })


def load_ai_config(config_path: Optional[str] = None) -> AIConfig:
    """Load AI configuration from file or environment."""
    if config_path and Path(config_path).exists():
        import json
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        return AIConfig(**config_data)
    else:
        return AIConfig()


def save_ai_config(config: AIConfig, config_path: str):
    """Save AI configuration to file."""
    import json
    from dataclasses import asdict
    
    config_dict = asdict(config)
    with open(config_path, 'w') as f:
        json.dump(config_dict, f, indent=2)


def get_model_config(model_type: str) -> Dict[str, Any]:
    """Get configuration for specific model type."""
    model_config = ModelConfig()
    
    if model_type == 'genomic_sequence':
        return model_config.genomic_sequence_config
    elif model_type == 'mutation_prediction':
        return model_config.mutation_prediction_config
    elif model_type == 'drug_response':
        return model_config.drug_response_config
    elif model_type == 'survival_analysis':
        return model_config.survival_analysis_config
    elif model_type == 'multi_omics':
        return model_config.multi_omics_config
    else:
        return {}


def get_llm_config(provider: str) -> Dict[str, Any]:
    """Get configuration for specific LLM provider."""
    llm_config = LLMConfig()
    
    if provider == 'openai':
        return llm_config.openai_config
    elif provider == 'anthropic':
        return llm_config.anthropic_config
    elif provider == 'huggingface':
        return llm_config.huggingface_config
    elif provider == 'embedding':
        return llm_config.embedding_config
    elif provider == 'vector_db':
        return llm_config.vector_db_config
    else:
        return {}


def get_visualization_config() -> Dict[str, Any]:
    """Get visualization configuration."""
    viz_config = VisualizationConfig()
    return {
        'plot': viz_config.plot_config,
        'interactive': viz_config.interactive_config,
        'ai_features': viz_config.ai_features_config,
        'dashboard': viz_config.dashboard_config
    }


# Environment-specific configurations
class DevelopmentConfig(AIConfig):
    """Development environment configuration."""
    
    def __init__(self):
        super().__init__()
        self.monitoring_config['log_level'] = 'DEBUG'
        self.performance_config['max_workers'] = 2
        self.performance_config['memory_limit_gb'] = 4


class ProductionConfig(AIConfig):
    """Production environment configuration."""
    
    def __init__(self):
        super().__init__()
        self.monitoring_config['log_level'] = 'INFO'
        self.performance_config['max_workers'] = 8
        self.performance_config['memory_limit_gb'] = 16
        self.security_config['encrypt_sensitive_data'] = True
        self.security_config['log_api_calls'] = True


class TestingConfig(AIConfig):
    """Testing environment configuration."""
    
    def __init__(self):
        super().__init__()
        self.monitoring_config['log_level'] = 'WARNING'
        self.performance_config['max_workers'] = 1
        self.performance_config['memory_limit_gb'] = 2
        self.predictive_config['n_trials'] = 10  # Reduced for faster testing


def get_config(environment: str = 'development') -> AIConfig:
    """Get configuration for specific environment."""
    if environment == 'development':
        return DevelopmentConfig()
    elif environment == 'production':
        return ProductionConfig()
    elif environment == 'testing':
        return TestingConfig()
    else:
        return AIConfig()


# Default configuration instance
default_config = AIConfig()
