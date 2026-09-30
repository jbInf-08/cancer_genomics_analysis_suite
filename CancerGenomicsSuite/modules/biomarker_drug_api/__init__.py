"""
Biomarker and Drug Analysis API Module for Cancer Genomics Analysis Suite

This module provides REST API endpoints for biomarker discovery and drug analysis including:
- Biomarker discovery endpoints
- Drug analysis endpoints
- Drug-biomarker integration endpoints
- Clinical decision support endpoints
- Data export and import endpoints

Only api_routes is imported here. This file used to also import request/response
models from `.api_models` (BiomarkerRequest, DrugRequest, IntegrationRequest,
ClinicalRequest, AnalysisResponse) and helpers from `.api_utils`
(validate_request_data, format_response, handle_api_errors). Neither module has
ever existed in this repository, and none of those eight names is used anywhere
else in it.

Because the import ran first and failed, the whole package was unimportable --
and modules/__init__.py wraps this import in `except ImportError`, setting all
four route factories to None and printing a warning. So the four real API
blueprints below were silently unavailable through the modules package.
"""

from .api_routes import (
    create_biomarker_api,
    create_clinical_api,
    create_drug_api,
    create_integration_api,
)

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite Team"

__all__ = [
    "create_biomarker_api",
    "create_drug_api",
    "create_integration_api",
    "create_clinical_api",
]
