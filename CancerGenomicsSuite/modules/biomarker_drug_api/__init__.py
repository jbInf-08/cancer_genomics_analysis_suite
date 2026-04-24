"""
Biomarker and Drug Analysis API Module for Cancer Genomics Analysis Suite

This module provides REST API endpoints for biomarker discovery and drug analysis including:
- Biomarker discovery endpoints
- Drug analysis endpoints
- Drug-biomarker integration endpoints
- Clinical decision support endpoints
- Data export and import endpoints
"""

from .api_routes import (
    create_biomarker_api,
    create_drug_api,
    create_integration_api,
    create_clinical_api
)

from .api_models import (
    BiomarkerRequest,
    DrugRequest,
    IntegrationRequest,
    ClinicalRequest,
    AnalysisResponse
)

from .api_utils import (
    validate_request_data,
    format_response,
    handle_api_errors
)

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite Team"

__all__ = [
    # API Routes
    "create_biomarker_api",
    "create_drug_api", 
    "create_integration_api",
    "create_clinical_api",
    
    # API Models
    "BiomarkerRequest",
    "DrugRequest",
    "IntegrationRequest",
    "ClinicalRequest",
    "AnalysisResponse",
    
    # API Utils
    "validate_request_data",
    "format_response",
    "handle_api_errors"
]
