"""
Configuration for biomarker integration services.

This module provides configuration management for the integration between
CGAS and biomarker_identifier services.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class BiomarkerIdentifierConfig:
    """Configuration for biomarker_identifier service."""
    url: str = "http://localhost:8000"
    timeout: int = 30
    retries: int = 3
    health_endpoint: str = "/health"
    api_endpoint: str = "/api/analyze"
    enabled: bool = True


@dataclass
class CGASConfig:
    """Configuration for CGAS biomarker service."""
    enabled: bool = True
    max_samples: int = 5000
    max_features: int = 20000
    timeout: int = 60


@dataclass
class ServiceDiscoveryConfig:
    """Configuration for service discovery."""
    auto_monitoring: bool = True
    monitoring_interval: int = 30
    health_check_timeout: int = 5
    max_consecutive_failures: int = 3
    load_balancing_strategy: str = "round_robin"


@dataclass
class IntegrationConfig:
    """Main integration configuration."""
    biomarker_identifier: BiomarkerIdentifierConfig = field(default_factory=BiomarkerIdentifierConfig)
    cgas: CGASConfig = field(default_factory=CGASConfig)
    service_discovery: ServiceDiscoveryConfig = field(default_factory=ServiceDiscoveryConfig)
    
    # Integration settings
    enable_caching: bool = True
    cache_ttl: int = 3600
    enable_validation: bool = True
    enable_aggregation: bool = True
    prefer_fast_service: bool = True
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # Performance
    max_concurrent_requests: int = 10
    request_timeout: int = 300
    
    @classmethod
    def from_env(cls) -> 'IntegrationConfig':
        """Create configuration from environment variables."""
        return cls(
            biomarker_identifier=BiomarkerIdentifierConfig(
                url=os.getenv('BIOMARKER_IDENTIFIER_URL', 'http://localhost:8000'),
                timeout=int(os.getenv('BIOMARKER_IDENTIFIER_TIMEOUT', '30')),
                retries=int(os.getenv('BIOMARKER_IDENTIFIER_RETRIES', '3')),
                health_endpoint=os.getenv('BIOMARKER_IDENTIFIER_HEALTH_ENDPOINT', '/health'),
                api_endpoint=os.getenv('BIOMARKER_IDENTIFIER_API_ENDPOINT', '/api/analyze'),
                enabled=os.getenv('BIOMARKER_IDENTIFIER_ENABLED', 'true').lower() == 'true'
            ),
            cgas=CGASConfig(
                enabled=os.getenv('CGAS_BIOMARKER_ENABLED', 'true').lower() == 'true',
                max_samples=int(os.getenv('CGAS_MAX_SAMPLES', '5000')),
                max_features=int(os.getenv('CGAS_MAX_FEATURES', '20000')),
                timeout=int(os.getenv('CGAS_TIMEOUT', '60'))
            ),
            service_discovery=ServiceDiscoveryConfig(
                auto_monitoring=os.getenv('SERVICE_DISCOVERY_AUTO_MONITORING', 'true').lower() == 'true',
                monitoring_interval=int(os.getenv('SERVICE_DISCOVERY_INTERVAL', '30')),
                health_check_timeout=int(os.getenv('HEALTH_CHECK_TIMEOUT', '5')),
                max_consecutive_failures=int(os.getenv('MAX_CONSECUTIVE_FAILURES', '3')),
                load_balancing_strategy=os.getenv('LOAD_BALANCING_STRATEGY', 'round_robin')
            ),
            enable_caching=os.getenv('INTEGRATION_ENABLE_CACHING', 'true').lower() == 'true',
            cache_ttl=int(os.getenv('INTEGRATION_CACHE_TTL', '3600')),
            enable_validation=os.getenv('INTEGRATION_ENABLE_VALIDATION', 'true').lower() == 'true',
            enable_aggregation=os.getenv('INTEGRATION_ENABLE_AGGREGATION', 'true').lower() == 'true',
            prefer_fast_service=os.getenv('INTEGRATION_PREFER_FAST_SERVICE', 'true').lower() == 'true',
            log_level=os.getenv('INTEGRATION_LOG_LEVEL', 'INFO'),
            log_file=os.getenv('INTEGRATION_LOG_FILE'),
            max_concurrent_requests=int(os.getenv('INTEGRATION_MAX_CONCURRENT_REQUESTS', '10')),
            request_timeout=int(os.getenv('INTEGRATION_REQUEST_TIMEOUT', '300'))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'biomarker_identifier': {
                'url': self.biomarker_identifier.url,
                'timeout': self.biomarker_identifier.timeout,
                'retries': self.biomarker_identifier.retries,
                'health_endpoint': self.biomarker_identifier.health_endpoint,
                'api_endpoint': self.biomarker_identifier.api_endpoint,
                'enabled': self.biomarker_identifier.enabled
            },
            'cgas': {
                'enabled': self.cgas.enabled,
                'max_samples': self.cgas.max_samples,
                'max_features': self.cgas.max_features,
                'timeout': self.cgas.timeout
            },
            'service_discovery': {
                'auto_monitoring': self.service_discovery.auto_monitoring,
                'monitoring_interval': self.service_discovery.monitoring_interval,
                'health_check_timeout': self.service_discovery.health_check_timeout,
                'max_consecutive_failures': self.service_discovery.max_consecutive_failures,
                'load_balancing_strategy': self.service_discovery.load_balancing_strategy
            },
            'enable_caching': self.enable_caching,
            'cache_ttl': self.cache_ttl,
            'enable_validation': self.enable_validation,
            'enable_aggregation': self.enable_aggregation,
            'prefer_fast_service': self.prefer_fast_service,
            'log_level': self.log_level,
            'log_file': self.log_file,
            'max_concurrent_requests': self.max_concurrent_requests,
            'request_timeout': self.request_timeout
        }


# Default configuration instance
DEFAULT_CONFIG = IntegrationConfig.from_env()


def get_config() -> IntegrationConfig:
    """Get the current integration configuration."""
    return DEFAULT_CONFIG


def update_config(config_dict: Dict[str, Any]) -> IntegrationConfig:
    """Update configuration with new values."""
    global DEFAULT_CONFIG
    
    # Update biomarker_identifier config
    if 'biomarker_identifier' in config_dict:
        bi_config = config_dict['biomarker_identifier']
        DEFAULT_CONFIG.biomarker_identifier = BiomarkerIdentifierConfig(**bi_config)
    
    # Update CGAS config
    if 'cgas' in config_dict:
        cgas_config = config_dict['cgas']
        DEFAULT_CONFIG.cgas = CGASConfig(**cgas_config)
    
    # Update service discovery config
    if 'service_discovery' in config_dict:
        sd_config = config_dict['service_discovery']
        DEFAULT_CONFIG.service_discovery = ServiceDiscoveryConfig(**sd_config)
    
    # Update other settings
    for key, value in config_dict.items():
        if hasattr(DEFAULT_CONFIG, key) and key not in ['biomarker_identifier', 'cgas', 'service_discovery']:
            setattr(DEFAULT_CONFIG, key, value)
    
    return DEFAULT_CONFIG
