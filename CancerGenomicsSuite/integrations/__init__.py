"""
Integration module for linking Cancer Genomics Analysis Suite with external services.

This module provides integration capabilities for connecting CGAS with external
biomarker analysis services, particularly the biomarker_identifier project.
"""

# Import only the safe modules that don't have problematic dependencies
from .config import get_config, IntegrationConfig

# Try to import other modules, but don't fail if they have import issues
try:
    from .service_discovery import ServiceDiscovery
    _SERVICE_DISCOVERY_AVAILABLE = True
except ImportError as e:
    import logging
    logging.warning(f"ServiceDiscovery not available: {e}")
    _SERVICE_DISCOVERY_AVAILABLE = False
    ServiceDiscovery = None

try:
    from .biomarker_gateway import BiomarkerGateway
    _BIOMARKER_GATEWAY_AVAILABLE = True
except ImportError as e:
    import logging
    logging.warning(f"BiomarkerGateway not available: {e}")
    _BIOMARKER_GATEWAY_AVAILABLE = False
    BiomarkerGateway = None

try:
    from .biomarker_service import IntegratedBiomarkerService
    _BIOMARKER_SERVICE_AVAILABLE = True
except ImportError as e:
    import logging
    logging.warning(f"IntegratedBiomarkerService not available: {e}")
    _BIOMARKER_SERVICE_AVAILABLE = False
    IntegratedBiomarkerService = None

try:
    from .unified_interface import UnifiedBiomarkerInterface, BiomarkerAnalysisOptions
    _UNIFIED_INTERFACE_AVAILABLE = True
except ImportError as e:
    import logging
    logging.warning(f"UnifiedBiomarkerInterface not available: {e}")
    _UNIFIED_INTERFACE_AVAILABLE = False
    UnifiedBiomarkerInterface = None
    BiomarkerAnalysisOptions = None

try:
    from .compatibility import (
        ServiceCompatibilityManager, 
        discover_biomarkers_compatible,
        get_compatibility_manager
    )
    _COMPATIBILITY_AVAILABLE = True
except ImportError as e:
    import logging
    logging.warning(f"Compatibility module not available: {e}")
    _COMPATIBILITY_AVAILABLE = False
    ServiceCompatibilityManager = None
    discover_biomarkers_compatible = None
    get_compatibility_manager = None

# Build __all__ dynamically based on what's available
__all__ = ['get_config', 'IntegrationConfig']

if _SERVICE_DISCOVERY_AVAILABLE:
    __all__.append('ServiceDiscovery')

if _BIOMARKER_GATEWAY_AVAILABLE:
    __all__.append('BiomarkerGateway')

if _BIOMARKER_SERVICE_AVAILABLE:
    __all__.append('IntegratedBiomarkerService')

if _UNIFIED_INTERFACE_AVAILABLE:
    __all__.extend(['UnifiedBiomarkerInterface', 'BiomarkerAnalysisOptions'])

if _COMPATIBILITY_AVAILABLE:
    __all__.extend(['ServiceCompatibilityManager', 'discover_biomarkers_compatible', 'get_compatibility_manager'])
