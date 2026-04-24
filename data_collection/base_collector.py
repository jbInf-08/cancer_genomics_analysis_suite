"""
Base Data Collector Framework

This module provides the foundational framework for all data collectors in the system.
It defines the common interface, error handling, logging, and utility functions
that all individual collectors inherit from.
"""

import os
import json
import logging
import time
import requests
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Callable
from pathlib import Path
from datetime import datetime
import hashlib
import urllib.parse
from functools import wraps


class AuthenticationManager:
    """
    Manages authentication credentials for API access.
    
    Supports multiple authentication methods:
    - API keys (query parameter or header)
    - Bearer tokens
    - Basic authentication
    - OAuth2
    - Custom authentication handlers
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize authentication manager.
        
        Args:
            config: Authentication configuration dictionary
        """
        self.config = config or {}
        self._credentials_cache = {}
        self._load_credentials_from_env()
    
    def _load_credentials_from_env(self):
        """Load credentials from environment variables."""
        # Common API keys from environment
        env_mappings = {
            'NCBI_API_KEY': 'ncbi',
            'COSMIC_API_KEY': 'cosmic',
            'CLINVAR_API_KEY': 'clinvar',
            'ENSEMBL_API_KEY': 'ensembl',
            'UNIPROT_API_KEY': 'uniprot',
            'ONCOKB_API_TOKEN': 'oncokb',
            'CBIOPORTAL_API_KEY': 'cbioportal',
            'KEGG_API_KEY': 'kegg',
            'DRUGBANK_API_KEY': 'drugbank',
            'CHEMBL_API_KEY': 'chembl',
            'PUBMED_API_KEY': 'pubmed',
        }
        
        for env_var, source_name in env_mappings.items():
            value = os.environ.get(env_var)
            if value:
                self._credentials_cache[source_name] = {'api_key': value}
    
    def get_api_key(self, source: str) -> Optional[str]:
        """
        Get API key for a specific data source.
        
        Args:
            source: Name of the data source
            
        Returns:
            API key if available, None otherwise
        """
        # Check config first
        if source in self.config:
            return self.config[source].get('api_key')
        
        # Check credentials cache (from environment)
        if source in self._credentials_cache:
            return self._credentials_cache[source].get('api_key')
        
        return None
    
    def get_bearer_token(self, source: str) -> Optional[str]:
        """Get bearer token for a specific source."""
        if source in self.config:
            return self.config[source].get('bearer_token')
        if source in self._credentials_cache:
            return self._credentials_cache[source].get('bearer_token')
        return None
    
    def get_basic_auth(self, source: str) -> Optional[tuple]:
        """Get basic auth credentials (username, password) for a source."""
        creds = self.config.get(source, {})
        if 'username' in creds and 'password' in creds:
            return (creds['username'], creds['password'])
        return None
    
    def apply_auth_to_request(self, 
                              source: str,
                              headers: Dict,
                              params: Dict,
                              auth_type: str = 'auto') -> tuple:
        """
        Apply authentication to request headers and params.
        
        Args:
            source: Name of the data source
            headers: Request headers dict (modified in place)
            params: Request params dict (modified in place)
            auth_type: Type of auth ('api_key_param', 'api_key_header', 
                      'bearer', 'basic', 'auto')
            
        Returns:
            Tuple of (headers, params, auth) for requests
        """
        auth = None
        
        if auth_type == 'auto':
            # Try to detect the best auth method
            if self.get_bearer_token(source):
                auth_type = 'bearer'
            elif self.get_api_key(source):
                # Default to param for NCBI-style APIs
                if source.lower() in ['ncbi', 'clinvar', 'pubmed', 'geo']:
                    auth_type = 'api_key_param'
                else:
                    auth_type = 'api_key_header'
            elif self.get_basic_auth(source):
                auth_type = 'basic'
        
        if auth_type == 'api_key_param':
            api_key = self.get_api_key(source)
            if api_key:
                params['api_key'] = api_key
                
        elif auth_type == 'api_key_header':
            api_key = self.get_api_key(source)
            if api_key:
                headers['X-API-Key'] = api_key
                
        elif auth_type == 'bearer':
            token = self.get_bearer_token(source)
            if token:
                headers['Authorization'] = f'Bearer {token}'
                
        elif auth_type == 'basic':
            auth = self.get_basic_auth(source)
        
        return headers, params, auth
    
    def set_credentials(self, source: str, credentials: Dict):
        """
        Set credentials for a data source.
        
        Args:
            source: Name of the data source
            credentials: Dictionary with authentication details
        """
        self._credentials_cache[source] = credentials
    
    def has_credentials(self, source: str) -> bool:
        """Check if credentials exist for a source."""
        return (source in self.config or 
                source in self._credentials_cache)


class DataCollectorBase(ABC):
    """
    Base class for all data collectors in the system.
    
    This class provides:
    - Common interface for all collectors
    - Error handling and retry logic
    - Logging and progress tracking
    - Data validation and quality control
    - File I/O utilities
    - Rate limiting and API management
    - Authentication management
    """
    
    # Class-level authentication manager (shared across collectors)
    _auth_manager = None
    
    def __init__(self, 
                 output_dir: str = "data/external_sources",
                 config: Optional[Dict] = None,
                 logger: Optional[logging.Logger] = None,
                 auth_config: Optional[Dict] = None):
        """
        Initialize the base collector.
        
        Args:
            output_dir: Directory to save collected data
            config: Configuration dictionary for this collector
            logger: Optional logger instance
            auth_config: Authentication configuration
        """
        self.output_dir = Path(output_dir)
        self.config = config or {}
        self.logger = logger or self._setup_logger()
        
        # Initialize or use shared authentication manager
        if DataCollectorBase._auth_manager is None:
            DataCollectorBase._auth_manager = AuthenticationManager(auth_config)
        self.auth_manager = DataCollectorBase._auth_manager
        
        # Source name for authentication (derived from class name)
        self.source_name = self.__class__.__name__.replace("Collector", "").lower()
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Collection metadata
        self.collection_metadata = {
            "collector_name": self.__class__.__name__,
            "start_time": None,
            "end_time": None,
            "samples_collected": 0,
            "files_created": [],
            "errors": [],
            "warnings": []
        }
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = self.config.get("min_request_interval", 1.0)
        
        # Retry configuration
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 5)
        
    def _setup_logger(self) -> logging.Logger:
        """Set up logger for this collector."""
        logger = logging.getLogger(f"{self.__class__.__name__}")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    @abstractmethod
    def collect_data(self, **kwargs) -> Dict[str, Any]:
        """
        Collect data from the source.
        
        This method must be implemented by all subclasses.
        
        Returns:
            Dictionary containing collection results and metadata
        """
        pass
    
    @abstractmethod
    def get_available_datasets(self) -> List[Dict[str, Any]]:
        """
        Get list of available datasets from the source.
        
        Returns:
            List of dictionaries containing dataset information
        """
        pass
    
    def make_request(self, 
                    url: str, 
                    method: str = "GET",
                    params: Optional[Dict] = None,
                    headers: Optional[Dict] = None,
                    data: Optional[Dict] = None,
                    json_data: Optional[Dict] = None,
                    timeout: int = 30,
                    auth_type: str = 'auto',
                    source_override: Optional[str] = None) -> requests.Response:
        """
        Make HTTP request with rate limiting, retry logic, and authentication.
        
        Args:
            url: URL to request
            method: HTTP method
            params: Query parameters
            headers: Request headers
            data: Request data (form data)
            json_data: JSON request data
            timeout: Request timeout
            auth_type: Authentication type ('auto', 'api_key_param', 
                      'api_key_header', 'bearer', 'basic', 'none')
            source_override: Override the source name for authentication
            
        Returns:
            Response object
            
        Raises:
            requests.RequestException: If request fails after retries
        """
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        
        # Initialize params and headers
        params = params or {}
        headers = headers or {}
        
        # Default headers
        if "User-Agent" not in headers:
            headers["User-Agent"] = "CancerGenomicsAnalysisSuite/1.0.0"
        if "Accept" not in headers:
            headers["Accept"] = "application/json"
        
        # Apply authentication
        auth = None
        if auth_type != 'none':
            source = source_override or self.source_name
            headers, params, auth = self.auth_manager.apply_auth_to_request(
                source, headers, params, auth_type
            )
        
        # SSL verification - try to handle certificate issues on Windows
        verify_ssl = True
        try:
            import certifi
            verify_ssl = certifi.where()
        except ImportError:
            # If certifi not available, try system certs
            pass
        
        # Retry logic
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                response = requests.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=headers,
                    data=data,
                    json=json_data,
                    auth=auth,
                    timeout=timeout,
                    verify=verify_ssl
                )
                
                self.last_request_time = time.time()
                response.raise_for_status()
                return response
                
            except requests.RequestException as e:
                if attempt == self.max_retries:
                    self.logger.error(f"Request failed after {self.max_retries + 1} attempts: {e}")
                    raise
                
                self.logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
    
    def save_data(self, 
                  data: Union[pd.DataFrame, Dict, List],
                  filename: str,
                  format: str = "csv") -> str:
        """
        Save data to file in specified format.
        
        Args:
            data: Data to save
            filename: Output filename
            format: Output format (csv, json, parquet, tsv)
            
        Returns:
            Path to saved file
        """
        # Ensure filename has proper extension
        if not filename.endswith(f".{format}"):
            filename = f"{filename}.{format}"
        
        filepath = self.output_dir / filename
        
        try:
            if isinstance(data, pd.DataFrame):
                if format == "csv":
                    data.to_csv(filepath, index=False)
                elif format == "tsv":
                    data.to_csv(filepath, sep="\t", index=False)
                elif format == "parquet":
                    data.to_parquet(filepath, index=False)
                else:
                    raise ValueError(f"Unsupported format for DataFrame: {format}")
                    
            elif isinstance(data, (dict, list)):
                if format == "json":
                    with open(filepath, 'w') as f:
                        json.dump(data, f, indent=2, default=str)
                else:
                    raise ValueError(f"Unsupported format for dict/list: {format}")
            
            self.logger.info(f"Saved data to {filepath}")
            self.collection_metadata["files_created"].append(str(filepath))
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Failed to save data to {filepath}: {e}")
            raise
    
    def validate_data(self, data: Union[pd.DataFrame, Dict, List]) -> Dict[str, Any]:
        """
        Validate collected data for quality and completeness.
        
        Args:
            data: Data to validate
            
        Returns:
            Dictionary containing validation results
        """
        validation_results = {
            "is_valid": True,
            "issues": [],
            "statistics": {}
        }
        
        try:
            if isinstance(data, pd.DataFrame):
                validation_results["statistics"] = {
                    "rows": len(data),
                    "columns": len(data.columns),
                    "missing_values": data.isnull().sum().sum(),
                    "duplicate_rows": data.duplicated().sum()
                }
                
                # Check for empty DataFrame
                if len(data) == 0:
                    validation_results["is_valid"] = False
                    validation_results["issues"].append("DataFrame is empty")
                
                # Check for excessive missing values
                missing_pct = validation_results["statistics"]["missing_values"] / (len(data) * len(data.columns))
                if missing_pct > 0.5:
                    validation_results["issues"].append(f"High missing value percentage: {missing_pct:.2%}")
                
            elif isinstance(data, (dict, list)):
                validation_results["statistics"] = {
                    "items": len(data)
                }
                
                if len(data) == 0:
                    validation_results["is_valid"] = False
                    validation_results["issues"].append("Data structure is empty")
            
            if validation_results["issues"]:
                validation_results["is_valid"] = False
                
        except Exception as e:
            validation_results["is_valid"] = False
            validation_results["issues"].append(f"Validation error: {e}")
        
        return validation_results
    
    def log_collection_start(self):
        """Log the start of data collection."""
        self.collection_metadata["start_time"] = datetime.now().isoformat()
        self.logger.info(f"Starting data collection with {self.__class__.__name__}")
    
    def log_collection_end(self, results: Dict[str, Any]):
        """Log the end of data collection."""
        self.collection_metadata["end_time"] = datetime.now().isoformat()
        self.collection_metadata.update(results)
        
        duration = self._calculate_duration()
        self.logger.info(
            f"Completed data collection with {self.__class__.__name__}. "
            f"Duration: {duration}, Files created: {len(self.collection_metadata['files_created'])}"
        )
    
    def _calculate_duration(self) -> str:
        """Calculate collection duration."""
        if not self.collection_metadata["start_time"] or not self.collection_metadata["end_time"]:
            return "Unknown"
        
        start = datetime.fromisoformat(self.collection_metadata["start_time"])
        end = datetime.fromisoformat(self.collection_metadata["end_time"])
        duration = end - start
        
        return str(duration)
    
    def get_collection_summary(self) -> Dict[str, Any]:
        """Get summary of collection results."""
        return {
            "collector": self.__class__.__name__,
            "duration": self._calculate_duration(),
            "files_created": len(self.collection_metadata["files_created"]),
            "samples_collected": self.collection_metadata["samples_collected"],
            "errors": len(self.collection_metadata["errors"]),
            "warnings": len(self.collection_metadata["warnings"]),
            "files": self.collection_metadata["files_created"]
        }
    
    def generate_filename(self, 
                         data_type: str,
                         cancer_type: Optional[str] = None,
                         sample_count: Optional[int] = None,
                         timestamp: bool = True) -> str:
        """
        Generate standardized filename for collected data.
        
        Args:
            data_type: Type of data (e.g., 'gene_expression', 'mutations')
            cancer_type: Cancer type (e.g., 'BRCA', 'LUAD')
            sample_count: Number of samples
            timestamp: Whether to include timestamp
            
        Returns:
            Generated filename
        """
        # Get collector name (remove 'Collector' suffix)
        collector_name = self.__class__.__name__.replace("Collector", "").lower()
        
        # Build filename components
        parts = [collector_name, data_type]
        
        if cancer_type:
            parts.append(cancer_type)
        
        if sample_count:
            parts.append(f"{sample_count}_samples")
        
        if timestamp:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            parts.append(timestamp_str)
        
        return "_".join(parts)
    
    def __enter__(self):
        """Context manager entry."""
        self.log_collection_start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type is not None:
            self.logger.error(f"Collection failed with exception: {exc_val}")
            self.collection_metadata["errors"].append(str(exc_val))
        
        # Save collection metadata
        metadata_file = self.output_dir / f"{self.__class__.__name__.lower()}_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(self.collection_metadata, f, indent=2, default=str)
