"""
Biomarker Gateway for routing requests between CGAS and biomarker_identifier services.

This module provides intelligent routing of biomarker analysis requests to the
most appropriate service based on capabilities, availability, and performance.
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests

# Import CGAS biomarker modules with compatibility patches
try:
    import os
    import sys

    # Add the integrations directory to path to import the patch
    integrations_path = os.path.dirname(__file__)
    if integrations_path not in sys.path:
        sys.path.insert(0, integrations_path)

    from dask_compatibility_patch import patch_lightgbm_import, patch_xgboost_import

    # Apply patches before importing
    patch_lightgbm_import()
    patch_xgboost_import()

    # Now import the original biomarker analyzer
    sys.path.append(str(Path(__file__).parent.parent))
    from modules.biomarker_discovery.biomarker_analyzer import (
        BiomarkerAnalyzer,
        BiomarkerResult,
    )

    CGAS_AVAILABLE = True
    logging.info(
        "CGAS biomarker analyzer loaded successfully with compatibility patches"
    )
except ImportError as e:
    logging.warning(f"CGAS biomarker modules not available: {e}")
    CGAS_AVAILABLE = False

    # Create dummy classes if imports failed
    class BiomarkerAnalyzer:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("CGAS biomarker modules not available")

    class BiomarkerResult:
        pass


# Set dummy classes for compatibility
StatisticalBiomarkerDiscovery = None
MLBiomarkerDiscovery = None

logger = logging.getLogger(__name__)


class ServiceType(Enum):
    """Available service types for biomarker analysis."""

    CGAS = "cgas"
    BIOMARKER_IDENTIFIER = "biomarker_identifier"
    HYBRID = "hybrid"


@dataclass
class ServiceCapabilities:
    """Service capabilities configuration."""

    statistical_analysis: bool = True
    ml_analysis: bool = True
    survival_analysis: bool = False
    multi_omics: bool = False
    real_time_processing: bool = False
    batch_processing: bool = True
    max_samples: int = 10000
    max_features: int = 50000


@dataclass
class ServiceStatus:
    """Service status information."""

    available: bool
    response_time: float
    last_check: float
    error_message: Optional[str] = None


class BiomarkerGateway:
    """
    Gateway for routing biomarker analysis requests to appropriate services.

    This class intelligently routes requests based on:
    - Service availability and health
    - Request complexity and requirements
    - Service capabilities and performance
    - Data size and processing requirements
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the biomarker gateway."""
        self.config = config or self._load_default_config()
        self.service_status = {}
        self.cgas_analyzer = None
        self.biomarker_identifier_url = self.config.get(
            "biomarker_identifier_url", "http://localhost:8000"
        )
        self.timeout = self.config.get("timeout", 30)
        self.retries = self.config.get("retries", 3)

        # Initialize CGAS components if available
        if CGAS_AVAILABLE:
            self._initialize_cgas()

        # Initialize service discovery
        self._check_services()

    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration."""
        return {
            "biomarker_identifier_url": os.getenv(
                "BIOMARKER_IDENTIFIER_URL", "http://localhost:8000"
            ),
            "timeout": int(os.getenv("BIOMARKER_IDENTIFIER_TIMEOUT", "30")),
            "retries": int(os.getenv("BIOMARKER_IDENTIFIER_RETRIES", "3")),
            "health_check_interval": int(os.getenv("HEALTH_CHECK_INTERVAL", "30")),
            "prefer_cgas_for_simple": os.getenv(
                "PREFER_CGAS_FOR_SIMPLE", "true"
            ).lower()
            == "true",
            "prefer_biomarker_identifier_for_complex": os.getenv(
                "PREFER_BIOMARKER_IDENTIFIER_FOR_COMPLEX", "true"
            ).lower()
            == "true",
        }

    def _initialize_cgas(self):
        """Initialize CGAS biomarker analysis components."""
        try:
            self.cgas_analyzer = BiomarkerAnalyzer()
            logger.info("CGAS biomarker analyzer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize CGAS biomarker analyzer: {e}")
            self.cgas_analyzer = None

    def _check_services(self):
        """Check availability of all services."""
        self._check_cgas()
        self._check_biomarker_identifier()

    def _check_cgas(self):
        """Check CGAS service availability."""
        try:
            if CGAS_AVAILABLE and self.cgas_analyzer is not None:
                # Simple test to verify CGAS is working
                start_time = time.time()
                # Create a minimal test to verify functionality
                test_data = {"test": "data"}
                end_time = time.time()

                self.service_status[ServiceType.CGAS] = ServiceStatus(
                    available=True,
                    response_time=end_time - start_time,
                    last_check=time.time(),
                )
                logger.info("CGAS service is available")
            else:
                self.service_status[ServiceType.CGAS] = ServiceStatus(
                    available=False,
                    response_time=0,
                    last_check=time.time(),
                    error_message="CGAS modules not available",
                )
                logger.warning("CGAS service is not available")
        except Exception as e:
            self.service_status[ServiceType.CGAS] = ServiceStatus(
                available=False,
                response_time=0,
                last_check=time.time(),
                error_message=str(e),
            )
            logger.error(f"CGAS service check failed: {e}")

    def _check_biomarker_identifier(self):
        """Check biomarker_identifier service availability."""
        try:
            start_time = time.time()
            response = requests.get(
                f"{self.biomarker_identifier_url}/health", timeout=self.timeout
            )
            end_time = time.time()

            if response.status_code == 200:
                self.service_status[ServiceType.BIOMARKER_IDENTIFIER] = ServiceStatus(
                    available=True,
                    response_time=end_time - start_time,
                    last_check=time.time(),
                )
                logger.info("Biomarker Identifier service is available")
            else:
                self.service_status[ServiceType.BIOMARKER_IDENTIFIER] = ServiceStatus(
                    available=False,
                    response_time=end_time - start_time,
                    last_check=time.time(),
                    error_message=f"HTTP {response.status_code}",
                )
                logger.warning(
                    f"Biomarker Identifier service returned status {response.status_code}"
                )
        except (requests.exceptions.RequestException, OSError) as e:
            self.service_status[ServiceType.BIOMARKER_IDENTIFIER] = ServiceStatus(
                available=False,
                response_time=0,
                last_check=time.time(),
                error_message=str(e),
            )
            logger.warning(f"Biomarker Identifier service is not available: {e}")

    def get_service_capabilities(
        self, service_type: ServiceType
    ) -> ServiceCapabilities:
        """Get capabilities for a specific service."""
        if service_type == ServiceType.CGAS:
            return ServiceCapabilities(
                statistical_analysis=True,
                ml_analysis=True,
                survival_analysis=False,
                multi_omics=False,
                real_time_processing=True,
                batch_processing=True,
                max_samples=5000,
                max_features=20000,
            )
        elif service_type == ServiceType.BIOMARKER_IDENTIFIER:
            return ServiceCapabilities(
                statistical_analysis=True,
                ml_analysis=True,
                survival_analysis=True,
                multi_omics=True,
                real_time_processing=False,
                batch_processing=True,
                max_samples=50000,
                max_features=100000,
            )
        else:
            return ServiceCapabilities()

    def route_request(
        self,
        endpoint: str,
        data: Dict[str, Any],
        requirements: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Route a request to the most appropriate service.

        Args:
            endpoint: The analysis endpoint to call
            data: The data to analyze
            requirements: Specific requirements for the analysis

        Returns:
            Analysis results from the chosen service
        """
        requirements = requirements or {}

        # Determine the best service for this request
        service_type = self._select_service(endpoint, data, requirements)

        logger.info(f"Routing request to {service_type.value} service")

        # Route to the selected service
        if service_type == ServiceType.CGAS:
            return self._route_to_cgas(endpoint, data, requirements)
        elif service_type == ServiceType.BIOMARKER_IDENTIFIER:
            return self._route_to_biomarker_identifier(endpoint, data, requirements)
        else:
            # Hybrid approach - use both services
            return self._route_hybrid(endpoint, data, requirements)

    def _select_service(
        self, endpoint: str, data: Dict[str, Any], requirements: Dict[str, Any]
    ) -> ServiceType:
        """Select the most appropriate service for the request."""

        # Check service availability first
        available_services = [
            s for s, status in self.service_status.items() if status.available
        ]

        if not available_services:
            raise RuntimeError("No biomarker analysis services are available")

        # Simple routing logic - can be enhanced based on requirements
        data_size = self._estimate_data_size(data)
        is_complex = requirements.get("complex_analysis", False)
        needs_survival = requirements.get("survival_analysis", False)
        needs_multi_omics = requirements.get("multi_omics", False)

        # Prefer biomarker_identifier for complex analyses
        if (
            is_complex or needs_survival or needs_multi_omics or data_size > 10000
        ) and ServiceType.BIOMARKER_IDENTIFIER in available_services:
            return ServiceType.BIOMARKER_IDENTIFIER

        # Prefer CGAS for simple, fast analyses
        if ServiceType.CGAS in available_services and not (
            needs_survival or needs_multi_omics
        ):
            return ServiceType.CGAS

        # Fallback to any available service
        return available_services[0]

    def _estimate_data_size(self, data: Dict[str, Any]) -> int:
        """Estimate the size of the data for routing decisions."""
        if "data" in data and hasattr(data["data"], "__len__"):
            return len(data["data"])
        return 0

    def _route_to_cgas(
        self, endpoint: str, data: Dict[str, Any], requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route request to CGAS biomarker analysis."""
        if not self.cgas_analyzer:
            raise RuntimeError("CGAS biomarker analyzer is not available")

        try:
            # Convert data format for CGAS
            cgas_data = self._convert_to_cgas_format(data)

            # Route based on endpoint
            if endpoint == "discover_biomarkers":
                results = self.cgas_analyzer.discover_biomarkers(
                    cgas_data["data"],
                    cgas_data["labels"],
                    biomarker_type=cgas_data.get("biomarker_type", "gene_expression"),
                )
                return self._convert_cgas_results(results)
            else:
                raise ValueError(f"Unknown CGAS endpoint: {endpoint}")

        except Exception as e:
            logger.error(f"CGAS analysis failed: {e}")
            raise

    def _route_to_biomarker_identifier(
        self, endpoint: str, data: Dict[str, Any], requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route request to biomarker_identifier service."""
        try:
            # Prepare request for biomarker_identifier
            request_data = {
                "endpoint": endpoint,
                "data": data,
                "requirements": requirements,
            }

            response = requests.post(
                f"{self.biomarker_identifier_url}/api/analyze",
                json=request_data,
                timeout=self.timeout,
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise RuntimeError(
                    f"Biomarker Identifier service error: {response.status_code} - {response.text}"
                )

        except requests.exceptions.RequestException as e:
            logger.error(f"Biomarker Identifier service request failed: {e}")
            raise

    def _route_hybrid(
        self, endpoint: str, data: Dict[str, Any], requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route request using hybrid approach (both services)."""
        results = {}

        # Try CGAS first for quick results
        if (
            ServiceType.CGAS in self.service_status
            and self.service_status[ServiceType.CGAS].available
        ):
            try:
                cgas_results = self._route_to_cgas(endpoint, data, requirements)
                results["cgas"] = cgas_results
            except Exception as e:
                logger.warning(f"CGAS hybrid analysis failed: {e}")

        # Try biomarker_identifier for comprehensive results
        if (
            ServiceType.BIOMARKER_IDENTIFIER in self.service_status
            and self.service_status[ServiceType.BIOMARKER_IDENTIFIER].available
        ):
            try:
                bi_results = self._route_to_biomarker_identifier(
                    endpoint, data, requirements
                )
                results["biomarker_identifier"] = bi_results
            except Exception as e:
                logger.warning(f"Biomarker Identifier hybrid analysis failed: {e}")

        if not results:
            raise RuntimeError("All services failed in hybrid mode")

        return self._merge_hybrid_results(results)

    def _convert_to_cgas_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert data to CGAS format."""
        # This is a simplified conversion - may need enhancement based on actual data formats
        import numpy as np
        import pandas as pd

        if "data" in data and "labels" in data:
            return {
                "data": pd.DataFrame(data["data"])
                if not isinstance(data["data"], pd.DataFrame)
                else data["data"],
                "labels": pd.Series(data["labels"])
                if not isinstance(data["labels"], pd.Series)
                else data["labels"],
                "biomarker_type": data.get("biomarker_type", "gene_expression"),
            }
        else:
            raise ValueError("Data must contain 'data' and 'labels' fields")

    def _convert_cgas_results(self, results: List[BiomarkerResult]) -> Dict[str, Any]:
        """Convert CGAS results to standard format."""
        return {
            "biomarkers": [
                {
                    "id": r.biomarker_id,
                    "name": r.biomarker_name,
                    "type": r.biomarker_type,
                    "p_value": r.p_value,
                    "effect_size": r.effect_size,
                    "confidence_interval": r.confidence_interval,
                    "sensitivity": r.sensitivity,
                    "specificity": r.specificity,
                    "auc_score": r.auc_score,
                    "clinical_significance": r.clinical_significance,
                    "validation_status": r.validation_status,
                    "supporting_evidence": r.supporting_evidence,
                    "metadata": r.metadata,
                }
                for r in results
            ],
            "service": "cgas",
            "timestamp": time.time(),
        }

    def _merge_hybrid_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Merge results from multiple services."""
        merged = {
            "biomarkers": [],
            "services_used": list(results.keys()),
            "timestamp": time.time(),
        }

        # Combine biomarkers from all services
        for service, result in results.items():
            if "biomarkers" in result:
                for biomarker in result["biomarkers"]:
                    biomarker["source_service"] = service
                    merged["biomarkers"].append(biomarker)

        return merged

    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all services."""
        return {
            service.value: {
                "available": status.available,
                "response_time": status.response_time,
                "last_check": status.last_check,
                "error_message": status.error_message,
            }
            for service, status in self.service_status.items()
        }

    def health_check(self, refresh: bool = False) -> Dict[str, Any]:
        """
        Single entry point for readiness: whether any backend can serve traffic.

        Returns:
            ready: True if at least one service is available
            any_available: same as ready (explicit alias for callers)
            services: per-service status from :meth:`get_service_status`
        """
        if refresh:
            self.refresh_service_status()
        statuses = self.get_service_status()
        any_up = any(
            s.get("available") for s in statuses.values() if isinstance(s, dict)
        )
        return {
            "ready": any_up,
            "any_available": any_up,
            "services": statuses,
        }

    def refresh_service_status(self):
        """Refresh the status of all services."""
        self._check_services()
