"""
Compatibility layer for integrating CGAS with biomarker_identifier.

This module provides compatibility functions and adapters to ensure
seamless integration between the two systems.
"""

import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class CGASCompatibilityAdapter:
    """Adapter for CGAS biomarker analysis compatibility."""
    
    def __init__(self):
        """Initialize the CGAS compatibility adapter."""
        self.cgas_available = False
        self.biomarker_analyzer = None
        self._initialize_cgas()
    
    def _initialize_cgas(self):
        """Initialize CGAS components if available."""
        try:
            # Add CGAS modules to path
            cgas_path = Path(__file__).parent.parent
            if str(cgas_path) not in sys.path:
                sys.path.insert(0, str(cgas_path))
            
            # Import CGAS biomarker modules
            from modules.biomarker_discovery.biomarker_analyzer import BiomarkerAnalyzer
            from modules.biomarker_discovery.statistical_biomarker_discovery import StatisticalBiomarkerDiscovery
            from modules.biomarker_discovery.ml_biomarker_discovery import MLBiomarkerDiscovery
            
            self.biomarker_analyzer = BiomarkerAnalyzer()
            self.cgas_available = True
            logger.info("CGAS biomarker modules loaded successfully")
            
        except ImportError as e:
            logger.warning(f"CGAS biomarker modules not available: {e}")
            self.cgas_available = False
        except Exception as e:
            logger.error(f"Error initializing CGAS: {e}")
            self.cgas_available = False
    
    def is_available(self) -> bool:
        """Check if CGAS is available."""
        return self.cgas_available
    
    def discover_biomarkers(self, 
                           data: Union[pd.DataFrame, Dict[str, Any]], 
                           labels: Union[pd.Series, List, np.ndarray],
                           biomarker_type: str = 'gene_expression',
                           **kwargs) -> List[Dict[str, Any]]:
        """
        Discover biomarkers using CGAS.
        
        Args:
            data: Feature matrix
            labels: Labels for analysis
            biomarker_type: Type of biomarker data
            **kwargs: Additional parameters
            
        Returns:
            List of discovered biomarkers
        """
        if not self.cgas_available:
            raise RuntimeError("CGAS is not available")
        
        try:
            # Convert data to CGAS format
            cgas_data = self._convert_to_cgas_format(data)
            cgas_labels = self._convert_labels_to_cgas_format(labels)
            
            # Perform analysis
            results = self.biomarker_analyzer.discover_biomarkers(
                cgas_data,
                cgas_labels,
                biomarker_type=biomarker_type,
                **kwargs
            )
            
            # Convert results to standard format
            return self._convert_cgas_results(results)
            
        except Exception as e:
            logger.error(f"CGAS biomarker discovery failed: {e}")
            raise
    
    def _convert_to_cgas_format(self, data: Union[pd.DataFrame, Dict[str, Any]]) -> pd.DataFrame:
        """Convert data to CGAS DataFrame format."""
        if isinstance(data, pd.DataFrame):
            return data
        elif isinstance(data, dict):
            return pd.DataFrame(data)
        elif isinstance(data, np.ndarray):
            return pd.DataFrame(data)
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
    
    def _convert_labels_to_cgas_format(self, labels: Union[pd.Series, List, np.ndarray]) -> pd.Series:
        """Convert labels to CGAS Series format."""
        if isinstance(labels, pd.Series):
            return labels
        elif isinstance(labels, (list, np.ndarray)):
            return pd.Series(labels)
        else:
            raise ValueError(f"Unsupported labels type: {type(labels)}")
    
    def _convert_cgas_results(self, results) -> List[Dict[str, Any]]:
        """Convert CGAS results to standard format."""
        converted_results = []
        
        for result in results:
            converted_result = {
                'id': getattr(result, 'biomarker_id', ''),
                'name': getattr(result, 'biomarker_name', ''),
                'type': getattr(result, 'biomarker_type', ''),
                'p_value': getattr(result, 'p_value', 1.0),
                'effect_size': getattr(result, 'effect_size', 0.0),
                'confidence_interval': getattr(result, 'confidence_interval', (0.0, 0.0)),
                'sensitivity': getattr(result, 'sensitivity', 0.0),
                'specificity': getattr(result, 'specificity', 0.0),
                'auc_score': getattr(result, 'auc_score', 0.5),
                'clinical_significance': getattr(result, 'clinical_significance', ''),
                'validation_status': getattr(result, 'validation_status', ''),
                'supporting_evidence': getattr(result, 'supporting_evidence', []),
                'metadata': getattr(result, 'metadata', {}),
                'source_service': 'cgas'
            }
            converted_results.append(converted_result)
        
        return converted_results


class BiomarkerIdentifierCompatibilityAdapter:
    """Adapter for biomarker_identifier service compatibility."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the biomarker_identifier compatibility adapter."""
        self.base_url = base_url
        self.available = False
        self._check_availability()
    
    def _check_availability(self):
        """Check if biomarker_identifier service is available."""
        try:
            import requests
            response = requests.get(f"{self.base_url}/health", timeout=5)
            self.available = response.status_code == 200
            if self.available:
                logger.info("Biomarker Identifier service is available")
            else:
                logger.warning(f"Biomarker Identifier service returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"Biomarker Identifier service is not available: {e}")
            self.available = False
    
    def is_available(self) -> bool:
        """Check if biomarker_identifier service is available."""
        return self.available
    
    def discover_biomarkers(self, 
                           data: Union[pd.DataFrame, Dict[str, Any]], 
                           labels: Union[pd.Series, List, np.ndarray],
                           biomarker_type: str = 'gene_expression',
                           **kwargs) -> List[Dict[str, Any]]:
        """
        Discover biomarkers using biomarker_identifier service.
        
        Args:
            data: Feature matrix
            labels: Labels for analysis
            biomarker_type: Type of biomarker data
            **kwargs: Additional parameters
            
        Returns:
            List of discovered biomarkers
        """
        if not self.available:
            raise RuntimeError("Biomarker Identifier service is not available")
        
        try:
            import requests
            
            # Prepare request data
            request_data = {
                'data': self._convert_to_bi_format(data),
                'labels': self._convert_labels_to_bi_format(labels),
                'biomarker_type': biomarker_type,
                'analysis_type': 'discovery',
                'config': kwargs
            }
            
            # Make request to biomarker_identifier service
            response = requests.post(
                f"{self.base_url}/api/analyze",
                json=request_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('biomarkers', [])
            else:
                raise RuntimeError(f"Biomarker Identifier service error: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Biomarker Identifier discovery failed: {e}")
            raise
    
    def _convert_to_bi_format(self, data: Union[pd.DataFrame, Dict[str, Any]]) -> Dict[str, Any]:
        """Convert data to biomarker_identifier format."""
        if isinstance(data, pd.DataFrame):
            return {
                'data': data.to_dict('records'),
                'columns': data.columns.tolist(),
                'index': data.index.tolist()
            }
        elif isinstance(data, dict):
            return data
        elif isinstance(data, np.ndarray):
            return {
                'data': data.tolist(),
                'shape': data.shape
            }
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
    
    def _convert_labels_to_bi_format(self, labels: Union[pd.Series, List, np.ndarray]) -> List:
        """Convert labels to biomarker_identifier format."""
        if isinstance(labels, pd.Series):
            return labels.tolist()
        elif isinstance(labels, np.ndarray):
            return labels.tolist()
        elif isinstance(labels, list):
            return labels
        else:
            raise ValueError(f"Unsupported labels type: {type(labels)}")


class DataFormatConverter:
    """Converter for data formats between different services."""
    
    @staticmethod
    def to_standard_format(data: Any, labels: Any) -> Dict[str, Any]:
        """Convert data to standard format."""
        return {
            'data': DataFormatConverter._convert_data(data),
            'labels': DataFormatConverter._convert_labels(labels),
            'metadata': {
                'data_type': type(data).__name__,
                'labels_type': type(labels).__name__,
                'data_shape': getattr(data, 'shape', None),
                'labels_length': len(labels) if hasattr(labels, '__len__') else None
            }
        }
    
    @staticmethod
    def _convert_data(data: Any) -> Any:
        """Convert data to a standard format."""
        if isinstance(data, pd.DataFrame):
            return data.to_dict('records')
        elif isinstance(data, np.ndarray):
            return data.tolist()
        elif isinstance(data, dict):
            return data
        else:
            return data
    
    @staticmethod
    def _convert_labels(labels: Any) -> List:
        """Convert labels to a standard format."""
        if isinstance(labels, pd.Series):
            return labels.tolist()
        elif isinstance(labels, np.ndarray):
            return labels.tolist()
        elif isinstance(labels, list):
            return labels
        else:
            return list(labels)


class ServiceCompatibilityManager:
    """Manager for service compatibility and integration."""
    
    def __init__(self):
        """Initialize the compatibility manager."""
        self.cgas_adapter = CGASCompatibilityAdapter()
        self.bi_adapter = BiomarkerIdentifierCompatibilityAdapter()
        self.converter = DataFormatConverter()
    
    def get_available_services(self) -> List[str]:
        """Get list of available services."""
        available = []
        
        if self.cgas_adapter.is_available():
            available.append('cgas')
        
        if self.bi_adapter.is_available():
            available.append('biomarker_identifier')
        
        return available
    
    def discover_biomarkers(self, 
                           data: Union[pd.DataFrame, Dict[str, Any]], 
                           labels: Union[pd.Series, List, np.ndarray],
                           service: Optional[str] = None,
                           **kwargs) -> List[Dict[str, Any]]:
        """
        Discover biomarkers using the specified service or auto-select.
        
        Args:
            data: Feature matrix
            labels: Labels for analysis
            service: Specific service to use ('cgas' or 'biomarker_identifier')
            **kwargs: Additional parameters
            
        Returns:
            List of discovered biomarkers
        """
        available_services = self.get_available_services()
        
        if not available_services:
            raise RuntimeError("No biomarker analysis services are available")
        
        # Select service
        if service:
            if service not in available_services:
                raise ValueError(f"Service '{service}' is not available. Available: {available_services}")
            selected_service = service
        else:
            # Auto-select based on data size and complexity
            selected_service = self._select_best_service(data, labels, available_services)
        
        logger.info(f"Using service: {selected_service}")
        
        # Perform analysis
        if selected_service == 'cgas':
            return self.cgas_adapter.discover_biomarkers(data, labels, **kwargs)
        elif selected_service == 'biomarker_identifier':
            return self.bi_adapter.discover_biomarkers(data, labels, **kwargs)
        else:
            raise ValueError(f"Unknown service: {selected_service}")
    
    def _select_best_service(self, 
                           data: Union[pd.DataFrame, Dict[str, Any]], 
                           labels: Union[pd.Series, List, np.ndarray],
                           available_services: List[str]) -> str:
        """Select the best service for the given data."""
        # Simple selection logic - can be enhanced
        data_size = self._estimate_data_size(data)
        
        # Prefer biomarker_identifier for large datasets
        if data_size > 10000 and 'biomarker_identifier' in available_services:
            return 'biomarker_identifier'
        
        # Prefer CGAS for smaller datasets
        if 'cgas' in available_services:
            return 'cgas'
        
        # Fallback to any available service
        return available_services[0]
    
    def _estimate_data_size(self, data: Union[pd.DataFrame, Dict[str, Any]]) -> int:
        """Estimate the size of the data."""
        if isinstance(data, pd.DataFrame):
            return len(data) * len(data.columns)
        elif isinstance(data, dict):
            return sum(len(v) if hasattr(v, '__len__') else 1 for v in data.values())
        else:
            return 0


# Global compatibility manager instance
compatibility_manager = ServiceCompatibilityManager()


def get_compatibility_manager() -> ServiceCompatibilityManager:
    """Get the global compatibility manager instance."""
    return compatibility_manager


def discover_biomarkers_compatible(data: Union[pd.DataFrame, Dict[str, Any]], 
                                 labels: Union[pd.Series, List, np.ndarray],
                                 service: Optional[str] = None,
                                 **kwargs) -> List[Dict[str, Any]]:
    """
    Compatible biomarker discovery function that works with both services.
    
    Args:
        data: Feature matrix
        labels: Labels for analysis
        service: Specific service to use
        **kwargs: Additional parameters
        
    Returns:
        List of discovered biomarkers
    """
    return compatibility_manager.discover_biomarkers(data, labels, service, **kwargs)
