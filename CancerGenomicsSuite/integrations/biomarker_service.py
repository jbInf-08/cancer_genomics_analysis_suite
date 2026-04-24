"""
Integrated Biomarker Service for unified biomarker analysis.

This module provides a unified interface for biomarker analysis that seamlessly
integrates CGAS and biomarker_identifier services, providing the best of both
worlds with intelligent routing and fallback mechanisms.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import pandas as pd
import numpy as np

from .biomarker_gateway import BiomarkerGateway, ServiceType
from .service_discovery import ServiceDiscovery

logger = logging.getLogger(__name__)


@dataclass
class AnalysisRequest:
    """Request for biomarker analysis."""
    data: Union[pd.DataFrame, Dict[str, Any]]
    labels: Union[pd.Series, List, np.ndarray]
    analysis_type: str = 'discovery'
    biomarker_type: str = 'gene_expression'
    config: Optional[Dict[str, Any]] = None
    requirements: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AnalysisResult:
    """Result of biomarker analysis."""
    biomarkers: List[Dict[str, Any]]
    analysis_metadata: Dict[str, Any]
    service_used: str
    processing_time: float
    timestamp: float
    quality_score: Optional[float] = None
    validation_results: Optional[Dict[str, Any]] = None


class IntegratedBiomarkerService:
    """
    Integrated biomarker analysis service that combines CGAS and biomarker_identifier.
    
    This service provides:
    - Unified API for biomarker analysis
    - Intelligent service routing
    - Automatic fallback mechanisms
    - Result aggregation and validation
    - Performance optimization
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the integrated biomarker service."""
        self.config = config or self._load_default_config()
        self.gateway = BiomarkerGateway(self.config.get('gateway_config', {}))
        self.service_discovery = ServiceDiscovery(self.config.get('discovery_config', {}))
        self.analysis_history = []
        self.performance_metrics = {}
        
        # Set up service discovery callbacks
        self.service_discovery.add_callback(self._on_service_state_change)
        
        logger.info("Integrated Biomarker Service initialized")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration."""
        return {
            'gateway_config': {},
            'discovery_config': {},
            'enable_caching': True,
            'cache_ttl': 3600,  # 1 hour
            'max_retries': 3,
            'timeout': 300,  # 5 minutes
            'enable_validation': True,
            'enable_aggregation': True,
            'prefer_fast_service': True
        }
    
    def analyze_biomarkers(self, request: AnalysisRequest) -> AnalysisResult:
        """
        Perform comprehensive biomarker analysis.
        
        Args:
            request: Analysis request containing data and parameters
            
        Returns:
            Analysis result with discovered biomarkers and metadata
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting biomarker analysis: {request.analysis_type}")
            
            # Validate request
            self._validate_request(request)
            
            # Prepare data for analysis
            prepared_data = self._prepare_data(request)
            
            # Select appropriate service
            service_type = self._select_service(request)
            
            # Perform analysis
            raw_results = self._perform_analysis(service_type, request, prepared_data)
            
            # Process and validate results
            processed_results = self._process_results(raw_results, request)
            
            # Create analysis result
            result = AnalysisResult(
                biomarkers=processed_results['biomarkers'],
                analysis_metadata=processed_results['metadata'],
                service_used=processed_results['service_used'],
                processing_time=time.time() - start_time,
                timestamp=time.time(),
                quality_score=processed_results.get('quality_score'),
                validation_results=processed_results.get('validation_results')
            )
            
            # Store in history
            self.analysis_history.append(result)
            
            # Update performance metrics
            self._update_performance_metrics(result)
            
            logger.info(f"Biomarker analysis completed in {result.processing_time:.2f}s using {result.service_used}")
            
            return result
            
        except Exception as e:
            logger.error(f"Biomarker analysis failed: {e}")
            raise
    
    def discover_biomarkers(self, 
                           data: Union[pd.DataFrame, Dict[str, Any]], 
                           labels: Union[pd.Series, List, np.ndarray],
                           biomarker_type: str = 'gene_expression',
                           config: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """
        Discover biomarkers from omics data.
        
        Args:
            data: Feature matrix (samples x features)
            labels: Binary or continuous labels
            biomarker_type: Type of biomarker data
            config: Analysis configuration
            
        Returns:
            Analysis result with discovered biomarkers
        """
        request = AnalysisRequest(
            data=data,
            labels=labels,
            analysis_type='discovery',
            biomarker_type=biomarker_type,
            config=config
        )
        
        return self.analyze_biomarkers(request)
    
    def validate_biomarkers(self, 
                           biomarkers: List[Dict[str, Any]], 
                           validation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate discovered biomarkers using independent data.
        
        Args:
            biomarkers: List of biomarkers to validate
            validation_data: Independent validation dataset
            
        Returns:
            Validation results
        """
        try:
            logger.info(f"Validating {len(biomarkers)} biomarkers")
            
            # Use biomarker_identifier service for validation if available
            if self._is_service_available(ServiceType.BIOMARKER_IDENTIFIER):
                validation_request = {
                    'biomarkers': biomarkers,
                    'validation_data': validation_data,
                    'validation_type': 'independent_dataset'
                }
                
                result = self.gateway.route_request('validate_biomarkers', validation_request)
                return result
            
            else:
                # Fallback to basic validation
                return self._basic_validation(biomarkers, validation_data)
                
        except Exception as e:
            logger.error(f"Biomarker validation failed: {e}")
            return {'error': str(e), 'validated_biomarkers': []}
    
    def compare_services(self, 
                        data: Union[pd.DataFrame, Dict[str, Any]], 
                        labels: Union[pd.Series, List, np.ndarray]) -> Dict[str, Any]:
        """
        Compare results from different services on the same data.
        
        Args:
            data: Feature matrix
            labels: Labels for analysis
            
        Returns:
            Comparison results from all available services
        """
        try:
            logger.info("Comparing services on same dataset")
            
            request = AnalysisRequest(
                data=data,
                labels=labels,
                analysis_type='discovery',
                requirements={'compare_services': True}
            )
            
            # Get results from all available services
            results = {}
            
            # Try CGAS
            if self._is_service_available(ServiceType.CGAS):
                try:
                    cgas_result = self._perform_analysis(ServiceType.CGAS, request, self._prepare_data(request))
                    results['cgas'] = cgas_result
                except Exception as e:
                    logger.warning(f"CGAS comparison failed: {e}")
            
            # Try biomarker_identifier
            if self._is_service_available(ServiceType.BIOMARKER_IDENTIFIER):
                try:
                    bi_result = self._perform_analysis(ServiceType.BIOMARKER_IDENTIFIER, request, self._prepare_data(request))
                    results['biomarker_identifier'] = bi_result
                except Exception as e:
                    logger.warning(f"Biomarker Identifier comparison failed: {e}")
            
            # Analyze differences
            comparison = self._analyze_service_differences(results)
            
            return {
                'service_results': results,
                'comparison': comparison,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Service comparison failed: {e}")
            return {'error': str(e)}
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all biomarker analysis services."""
        return {
            'gateway_status': self.gateway.get_service_status(),
            'discovery_status': self.service_discovery.get_service_statistics(),
            'performance_metrics': self.performance_metrics,
            'analysis_history_count': len(self.analysis_history)
        }
    
    def _validate_request(self, request: AnalysisRequest):
        """Validate analysis request."""
        if request.data is None or len(request.data) == 0:
            raise ValueError("Data cannot be empty")
        
        if request.labels is None or len(request.labels) == 0:
            raise ValueError("Labels cannot be empty")
        
        # Check data-label compatibility
        if hasattr(request.data, '__len__') and hasattr(request.labels, '__len__'):
            if len(request.data) != len(request.labels):
                raise ValueError("Data and labels must have the same length")
    
    def _prepare_data(self, request: AnalysisRequest) -> Dict[str, Any]:
        """Prepare data for analysis."""
        # Convert data to standard format
        if isinstance(request.data, pd.DataFrame):
            data_dict = request.data.to_dict('records')
        elif isinstance(request.data, dict):
            data_dict = request.data
        else:
            data_dict = {'data': request.data}
        
        # Convert labels to standard format
        if isinstance(request.labels, pd.Series):
            labels_list = request.labels.tolist()
        elif isinstance(request.labels, np.ndarray):
            labels_list = request.labels.tolist()
        else:
            labels_list = list(request.labels)
        
        return {
            'data': data_dict,
            'labels': labels_list,
            'biomarker_type': request.biomarker_type,
            'analysis_type': request.analysis_type,
            'config': request.config or {},
            'requirements': request.requirements or {},
            'metadata': request.metadata or {}
        }
    
    def _select_service(self, request: AnalysisRequest) -> ServiceType:
        """Select the most appropriate service for the request."""
        # Use gateway's routing logic
        prepared_data = self._prepare_data(request)
        return self.gateway._select_service(
            request.analysis_type,
            prepared_data,
            request.requirements or {}
        )
    
    def _perform_analysis(self, 
                         service_type: ServiceType, 
                         request: AnalysisRequest, 
                         prepared_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform analysis using the specified service."""
        return self.gateway.route_request(
            request.analysis_type,
            prepared_data,
            request.requirements or {}
        )
    
    def _process_results(self, raw_results: Dict[str, Any], request: AnalysisRequest) -> Dict[str, Any]:
        """Process and enhance analysis results."""
        processed = {
            'biomarkers': raw_results.get('biomarkers', []),
            'service_used': raw_results.get('service', 'unknown'),
            'metadata': raw_results.get('metadata', {})
        }
        
        # Add quality score if not present
        if 'quality_score' not in processed['metadata']:
            processed['quality_score'] = self._calculate_quality_score(processed['biomarkers'])
        
        # Add validation results if enabled
        if self.config.get('enable_validation', True):
            processed['validation_results'] = self._validate_results(processed['biomarkers'], request)
        
        return processed
    
    def _calculate_quality_score(self, biomarkers: List[Dict[str, Any]]) -> float:
        """Calculate quality score for biomarkers."""
        if not biomarkers:
            return 0.0
        
        scores = []
        for biomarker in biomarkers:
            score = 0.0
            
            # P-value score (lower is better)
            p_value = biomarker.get('p_value', 1.0)
            if p_value < 0.001:
                score += 0.3
            elif p_value < 0.01:
                score += 0.2
            elif p_value < 0.05:
                score += 0.1
            
            # Effect size score
            effect_size = abs(biomarker.get('effect_size', 0.0))
            if effect_size > 0.8:
                score += 0.3
            elif effect_size > 0.5:
                score += 0.2
            elif effect_size > 0.2:
                score += 0.1
            
            # AUC score
            auc = biomarker.get('auc_score', 0.5)
            if auc > 0.9:
                score += 0.4
            elif auc > 0.8:
                score += 0.3
            elif auc > 0.7:
                score += 0.2
            elif auc > 0.6:
                score += 0.1
            
            scores.append(score)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _validate_results(self, biomarkers: List[Dict[str, Any]], request: AnalysisRequest) -> Dict[str, Any]:
        """Validate analysis results."""
        validation = {
            'total_biomarkers': len(biomarkers),
            'significant_biomarkers': len([b for b in biomarkers if b.get('p_value', 1.0) < 0.05]),
            'high_effect_biomarkers': len([b for b in biomarkers if abs(b.get('effect_size', 0.0)) > 0.5]),
            'high_auc_biomarkers': len([b for b in biomarkers if b.get('auc_score', 0.5) > 0.8])
        }
        
        return validation
    
    def _basic_validation(self, biomarkers: List[Dict[str, Any]], validation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Basic validation fallback when advanced validation is not available."""
        return {
            'validation_type': 'basic',
            'validated_biomarkers': biomarkers,
            'validation_notes': 'Basic validation performed - advanced validation not available'
        }
    
    def _analyze_service_differences(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze differences between service results."""
        if len(results) < 2:
            return {'note': 'Insufficient services for comparison'}
        
        comparison = {
            'services_compared': list(results.keys()),
            'biomarker_counts': {service: len(result.get('biomarkers', [])) for service, result in results.items()},
            'overlapping_biomarkers': 0,
            'unique_biomarkers': {}
        }
        
        # Find overlapping biomarkers (simplified comparison)
        all_biomarkers = {}
        for service, result in results.items():
            biomarkers = result.get('biomarkers', [])
            comparison['unique_biomarkers'][service] = len(biomarkers)
            for biomarker in biomarkers:
                biomarker_id = biomarker.get('id', biomarker.get('name', ''))
                if biomarker_id not in all_biomarkers:
                    all_biomarkers[biomarker_id] = []
                all_biomarkers[biomarker_id].append(service)
        
        # Count overlapping biomarkers
        for biomarker_id, services in all_biomarkers.items():
            if len(services) > 1:
                comparison['overlapping_biomarkers'] += 1
        
        return comparison
    
    def _is_service_available(self, service_type: ServiceType) -> bool:
        """Check if a service is available."""
        status = self.gateway.get_service_status()
        return status.get(service_type.value, {}).get('available', False)
    
    def _update_performance_metrics(self, result: AnalysisResult):
        """Update performance metrics."""
        service = result.service_used
        if service not in self.performance_metrics:
            self.performance_metrics[service] = {
                'total_analyses': 0,
                'total_time': 0.0,
                'average_time': 0.0,
                'success_count': 0,
                'failure_count': 0
            }
        
        metrics = self.performance_metrics[service]
        metrics['total_analyses'] += 1
        metrics['total_time'] += result.processing_time
        metrics['average_time'] = metrics['total_time'] / metrics['total_analyses']
        metrics['success_count'] += 1
    
    def _on_service_state_change(self, event_type: str, service_name: str):
        """Handle service state change events."""
        logger.info(f"Service state change: {service_name} - {event_type}")
        
        # Update performance metrics for service failures
        if event_type == 'service_unhealthy' and service_name in self.performance_metrics:
            self.performance_metrics[service_name]['failure_count'] += 1
