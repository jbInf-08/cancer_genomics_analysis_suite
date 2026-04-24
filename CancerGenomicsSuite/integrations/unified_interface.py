"""
Unified Interface for Biomarker Analysis.

This module provides a unified interface that seamlessly integrates CGAS
and biomarker_identifier services, allowing users to work with both systems
through a single, consistent API.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
import time

from .biomarker_service import IntegratedBiomarkerService, AnalysisRequest, AnalysisResult
from .config import get_config

logger = logging.getLogger(__name__)


@dataclass
class BiomarkerAnalysisOptions:
    """Options for biomarker analysis."""
    # Analysis parameters
    p_value_threshold: float = 0.05
    effect_size_threshold: float = 0.2
    auc_threshold: float = 0.7
    multiple_testing_correction: str = 'fdr_bh'
    
    # Service selection
    prefer_service: Optional[str] = None  # 'cgas', 'biomarker_identifier', or None for auto
    force_service: Optional[str] = None   # Force specific service
    
    # Analysis type
    analysis_type: str = 'discovery'  # 'discovery', 'validation', 'comparison'
    biomarker_type: str = 'gene_expression'
    
    # Advanced options
    enable_validation: bool = True
    enable_cross_validation: bool = True
    cross_validation_folds: int = 5
    random_state: int = 42
    
    # Performance options
    max_features: Optional[int] = None
    feature_selection_method: str = 'mutual_info'
    n_top_features: int = 100


class UnifiedBiomarkerInterface:
    """
    Unified interface for biomarker analysis across CGAS and biomarker_identifier.
    
    This class provides a single, consistent API for biomarker analysis that
    automatically routes requests to the most appropriate service and handles
    all the complexity of service integration behind the scenes.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the unified biomarker interface."""
        self.config = config or get_config().to_dict()
        self.service = IntegratedBiomarkerService(self.config)
        self.analysis_history = []
        
        logger.info("Unified Biomarker Interface initialized")
    
    def discover_biomarkers(self, 
                           data: Union[pd.DataFrame, np.ndarray, Dict[str, Any]], 
                           labels: Union[pd.Series, np.ndarray, List],
                           options: Optional[BiomarkerAnalysisOptions] = None,
                           **kwargs) -> Dict[str, Any]:
        """
        Discover biomarkers from omics data.
        
        Args:
            data: Feature matrix (samples x features) or data dictionary
            labels: Binary or continuous labels
            options: Analysis options
            **kwargs: Additional parameters
            
        Returns:
            Dictionary containing discovered biomarkers and analysis metadata
        """
        options = options or BiomarkerAnalysisOptions()
        
        # Merge kwargs into options
        for key, value in kwargs.items():
            if hasattr(options, key):
                setattr(options, key, value)
        
        logger.info(f"Starting biomarker discovery with {len(data)} samples")
        
        # Prepare analysis request
        request = AnalysisRequest(
            data=data,
            labels=labels,
            analysis_type=options.analysis_type,
            biomarker_type=options.biomarker_type,
            config=self._prepare_config(options),
            requirements=self._prepare_requirements(options)
        )
        
        # Perform analysis
        result = self.service.analyze_biomarkers(request)
        
        # Store in history
        self.analysis_history.append({
            'timestamp': time.time(),
            'type': 'discovery',
            'result': result,
            'options': options
        })
        
        # Format results for user
        return self._format_discovery_results(result)
    
    def validate_biomarkers(self, 
                           biomarkers: List[Dict[str, Any]], 
                           validation_data: Union[pd.DataFrame, Dict[str, Any]],
                           validation_labels: Union[pd.Series, np.ndarray, List],
                           options: Optional[BiomarkerAnalysisOptions] = None) -> Dict[str, Any]:
        """
        Validate discovered biomarkers using independent data.
        
        Args:
            biomarkers: List of biomarkers to validate
            validation_data: Independent validation dataset
            validation_labels: Labels for validation data
            options: Validation options
            
        Returns:
            Validation results
        """
        options = options or BiomarkerAnalysisOptions()
        
        logger.info(f"Validating {len(biomarkers)} biomarkers")
        
        # Prepare validation data
        validation_request = {
            'biomarkers': biomarkers,
            'validation_data': validation_data,
            'validation_labels': validation_labels,
            'validation_type': 'independent_dataset'
        }
        
        # Perform validation
        validation_results = self.service.validate_biomarkers(biomarkers, validation_request)
        
        # Store in history
        self.analysis_history.append({
            'timestamp': time.time(),
            'type': 'validation',
            'biomarkers': biomarkers,
            'validation_results': validation_results,
            'options': options
        })
        
        return validation_results
    
    def compare_services(self, 
                        data: Union[pd.DataFrame, np.ndarray, Dict[str, Any]], 
                        labels: Union[pd.Series, np.ndarray, List],
                        options: Optional[BiomarkerAnalysisOptions] = None) -> Dict[str, Any]:
        """
        Compare results from different services on the same data.
        
        Args:
            data: Feature matrix
            labels: Labels for analysis
            options: Analysis options
            
        Returns:
            Comparison results from all available services
        """
        options = options or BiomarkerAnalysisOptions()
        
        logger.info("Comparing services on same dataset")
        
        # Perform comparison
        comparison_results = self.service.compare_services(data, labels)
        
        # Store in history
        self.analysis_history.append({
            'timestamp': time.time(),
            'type': 'comparison',
            'comparison_results': comparison_results,
            'options': options
        })
        
        return comparison_results
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all biomarker analysis services."""
        return self.service.get_service_status()
    
    def get_analysis_history(self) -> List[Dict[str, Any]]:
        """Get history of all analyses performed."""
        return self.analysis_history
    
    def clear_history(self):
        """Clear analysis history."""
        self.analysis_history.clear()
        logger.info("Analysis history cleared")
    
    def export_results(self, 
                      analysis_id: Optional[int] = None, 
                      format: str = 'json',
                      filepath: Optional[str] = None) -> Union[Dict[str, Any], str]:
        """
        Export analysis results.
        
        Args:
            analysis_id: ID of analysis to export (None for latest)
            format: Export format ('json', 'csv', 'excel')
            filepath: Optional file path to save results
            
        Returns:
            Exported results or file path if saved
        """
        if not self.analysis_history:
            raise ValueError("No analysis history available")
        
        # Get analysis to export
        if analysis_id is None:
            analysis = self.analysis_history[-1]
        else:
            if analysis_id >= len(self.analysis_history):
                raise ValueError(f"Analysis ID {analysis_id} not found")
            analysis = self.analysis_history[analysis_id]
        
        # Export based on format
        if format == 'json':
            results = self._export_json(analysis)
        elif format == 'csv':
            results = self._export_csv(analysis)
        elif format == 'excel':
            results = self._export_excel(analysis)
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        # Save to file if requested
        if filepath:
            if format == 'json':
                import json
                with open(filepath, 'w') as f:
                    json.dump(results, f, indent=2)
            elif format == 'csv':
                results.to_csv(filepath, index=False)
            elif format == 'excel':
                results.to_excel(filepath, index=False)
            
            logger.info(f"Results exported to {filepath}")
            return filepath
        
        return results
    
    def _prepare_config(self, options: BiomarkerAnalysisOptions) -> Dict[str, Any]:
        """Prepare configuration for analysis."""
        return {
            'p_value_threshold': options.p_value_threshold,
            'effect_size_threshold': options.effect_size_threshold,
            'auc_threshold': options.auc_threshold,
            'multiple_testing_correction': options.multiple_testing_correction,
            'cross_validation_folds': options.cross_validation_folds,
            'random_state': options.random_state,
            'max_features': options.max_features,
            'feature_selection_method': options.feature_selection_method,
            'n_top_features': options.n_top_features
        }
    
    def _prepare_requirements(self, options: BiomarkerAnalysisOptions) -> Dict[str, Any]:
        """Prepare requirements for service selection."""
        requirements = {
            'enable_validation': options.enable_validation,
            'enable_cross_validation': options.enable_cross_validation
        }
        
        # Service selection preferences
        if options.force_service:
            requirements['force_service'] = options.force_service
        elif options.prefer_service:
            requirements['prefer_service'] = options.prefer_service
        
        return requirements
    
    def _format_discovery_results(self, result: AnalysisResult) -> Dict[str, Any]:
        """Format discovery results for user consumption."""
        return {
            'biomarkers': result.biomarkers,
            'summary': {
                'total_biomarkers': len(result.biomarkers),
                'significant_biomarkers': len([b for b in result.biomarkers if b.get('p_value', 1.0) < 0.05]),
                'high_effect_biomarkers': len([b for b in result.biomarkers if abs(b.get('effect_size', 0.0)) > 0.5]),
                'high_auc_biomarkers': len([b for b in result.biomarkers if b.get('auc_score', 0.5) > 0.8])
            },
            'metadata': {
                'service_used': result.service_used,
                'processing_time': result.processing_time,
                'quality_score': result.quality_score,
                'timestamp': result.timestamp
            },
            'validation_results': result.validation_results
        }
    
    def _export_json(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Export analysis results as JSON."""
        return {
            'analysis_type': analysis['type'],
            'timestamp': analysis['timestamp'],
            'options': analysis['options'].__dict__ if hasattr(analysis['options'], '__dict__') else analysis['options'],
            'result': analysis.get('result', {}).__dict__ if hasattr(analysis.get('result', {}), '__dict__') else analysis.get('result', {})
        }
    
    def _export_csv(self, analysis: Dict[str, Any]) -> pd.DataFrame:
        """Export analysis results as CSV."""
        if analysis['type'] == 'discovery' and 'result' in analysis:
            biomarkers = analysis['result'].biomarkers
            if biomarkers:
                return pd.DataFrame(biomarkers)
        
        # Fallback to empty DataFrame
        return pd.DataFrame()
    
    def _export_excel(self, analysis: Dict[str, Any]) -> pd.DataFrame:
        """Export analysis results as Excel."""
        return self._export_csv(analysis)  # Same as CSV for now


# Convenience functions for easy usage
def discover_biomarkers(data: Union[pd.DataFrame, np.ndarray, Dict[str, Any]], 
                       labels: Union[pd.Series, np.ndarray, List],
                       **kwargs) -> Dict[str, Any]:
    """
    Convenience function for biomarker discovery.
    
    Args:
        data: Feature matrix or data dictionary
        labels: Labels for analysis
        **kwargs: Additional options
        
    Returns:
        Discovery results
    """
    interface = UnifiedBiomarkerInterface()
    options = BiomarkerAnalysisOptions(**kwargs)
    return interface.discover_biomarkers(data, labels, options)


def validate_biomarkers(biomarkers: List[Dict[str, Any]], 
                       validation_data: Union[pd.DataFrame, Dict[str, Any]],
                       validation_labels: Union[pd.Series, np.ndarray, List],
                       **kwargs) -> Dict[str, Any]:
    """
    Convenience function for biomarker validation.
    
    Args:
        biomarkers: Biomarkers to validate
        validation_data: Validation dataset
        validation_labels: Validation labels
        **kwargs: Additional options
        
    Returns:
        Validation results
    """
    interface = UnifiedBiomarkerInterface()
    options = BiomarkerAnalysisOptions(**kwargs)
    return interface.validate_biomarkers(biomarkers, validation_data, validation_labels, options)


def compare_services(data: Union[pd.DataFrame, np.ndarray, Dict[str, Any]], 
                    labels: Union[pd.Series, np.ndarray, List],
                    **kwargs) -> Dict[str, Any]:
    """
    Convenience function for service comparison.
    
    Args:
        data: Feature matrix
        labels: Labels for analysis
        **kwargs: Additional options
        
    Returns:
        Comparison results
    """
    interface = UnifiedBiomarkerInterface()
    options = BiomarkerAnalysisOptions(**kwargs)
    return interface.compare_services(data, labels, options)
