"""
Service Discovery for biomarker analysis services.

This module provides automatic discovery, health monitoring, and load balancing
for biomarker analysis services including CGAS and biomarker_identifier.
"""

import time
import threading
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import requests
import json
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)


class ServiceState(Enum):
    """Service states."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    STARTING = "starting"
    STOPPING = "stopping"


@dataclass
class ServiceEndpoint:
    """Service endpoint configuration."""
    name: str
    url: str
    health_endpoint: str = "/health"
    weight: int = 1
    timeout: int = 5
    retries: int = 3
    tags: List[str] = field(default_factory=list)


@dataclass
class ServiceHealth:
    """Service health information."""
    endpoint: ServiceEndpoint
    state: ServiceState
    last_check: datetime
    response_time: float
    error_count: int = 0
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ServiceDiscovery:
    """
    Service discovery and health monitoring for biomarker analysis services.
    
    This class provides:
    - Automatic service discovery
    - Health monitoring and status tracking
    - Load balancing across healthy services
    - Service registration and deregistration
    - Failure detection and recovery
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize service discovery."""
        self.config = config or self._load_default_config()
        self.services: Dict[str, ServiceHealth] = {}
        self.discovery_callbacks: List[Callable] = []
        self.monitoring_thread = None
        self.monitoring_active = False
        self.lock = threading.Lock()
        
        # Load default services
        self._load_default_services()
        
        # Start monitoring if enabled
        if self.config.get('auto_monitoring', True):
            self.start_monitoring()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration."""
        return {
            'auto_monitoring': os.getenv('SERVICE_DISCOVERY_AUTO_MONITORING', 'true').lower() == 'true',
            'monitoring_interval': int(os.getenv('SERVICE_DISCOVERY_INTERVAL', '30')),
            'health_check_timeout': int(os.getenv('HEALTH_CHECK_TIMEOUT', '5')),
            'max_consecutive_failures': int(os.getenv('MAX_CONSECUTIVE_FAILURES', '3')),
            'service_registration_timeout': int(os.getenv('SERVICE_REGISTRATION_TIMEOUT', '10')),
            'load_balancing_strategy': os.getenv('LOAD_BALANCING_STRATEGY', 'round_robin')
        }
    
    def _load_default_services(self):
        """Load default service endpoints."""
        # CGAS service (local)
        cgas_endpoint = ServiceEndpoint(
            name="cgas",
            url="http://localhost:8050",
            health_endpoint="/api/health",
            weight=1,
            tags=["local", "cgas", "biomarker"]
        )
        self.register_service(cgas_endpoint)
        
        # Biomarker Identifier service
        bi_endpoint = ServiceEndpoint(
            name="biomarker_identifier",
            url=os.getenv('BIOMARKER_IDENTIFIER_URL', 'http://localhost:8000'),
            health_endpoint="/health",
            weight=2,
            tags=["external", "biomarker_identifier", "ml"]
        )
        self.register_service(bi_endpoint)
    
    def register_service(self, endpoint: ServiceEndpoint) -> bool:
        """
        Register a new service endpoint.
        
        Args:
            endpoint: Service endpoint configuration
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            with self.lock:
                # Check if service is reachable
                if self._check_service_health(endpoint):
                    self.services[endpoint.name] = ServiceHealth(
                        endpoint=endpoint,
                        state=ServiceState.HEALTHY,
                        last_check=datetime.now(),
                        response_time=0.0
                    )
                    logger.info(f"Registered service: {endpoint.name} at {endpoint.url}")
                    self._notify_callbacks('service_registered', endpoint.name)
                    return True
                else:
                    self.services[endpoint.name] = ServiceHealth(
                        endpoint=endpoint,
                        state=ServiceState.UNHEALTHY,
                        last_check=datetime.now(),
                        response_time=0.0,
                        consecutive_failures=1
                    )
                    logger.warning(f"Registered unhealthy service: {endpoint.name} at {endpoint.url}")
                    return False
        except Exception as e:
            logger.error(f"Failed to register service {endpoint.name}: {e}")
            return False
    
    def deregister_service(self, service_name: str) -> bool:
        """
        Deregister a service endpoint.
        
        Args:
            service_name: Name of the service to deregister
            
        Returns:
            True if deregistration successful, False otherwise
        """
        try:
            with self.lock:
                if service_name in self.services:
                    del self.services[service_name]
                    logger.info(f"Deregistered service: {service_name}")
                    self._notify_callbacks('service_deregistered', service_name)
                    return True
                else:
                    logger.warning(f"Service not found for deregistration: {service_name}")
                    return False
        except Exception as e:
            logger.error(f"Failed to deregister service {service_name}: {e}")
            return False
    
    def get_healthy_services(self, tags: Optional[List[str]] = None) -> List[ServiceHealth]:
        """
        Get list of healthy services, optionally filtered by tags.
        
        Args:
            tags: Optional list of tags to filter services
            
        Returns:
            List of healthy services
        """
        with self.lock:
            healthy_services = [
                service for service in self.services.values()
                if service.state == ServiceState.HEALTHY
            ]
            
            if tags:
                healthy_services = [
                    service for service in healthy_services
                    if any(tag in service.endpoint.tags for tag in tags)
                ]
            
            return healthy_services
    
    def get_service(self, service_name: str) -> Optional[ServiceHealth]:
        """
        Get a specific service by name.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service health information or None if not found
        """
        with self.lock:
            return self.services.get(service_name)
    
    def select_service(self, 
                      tags: Optional[List[str]] = None,
                      strategy: Optional[str] = None) -> Optional[ServiceHealth]:
        """
        Select a service using load balancing strategy.
        
        Args:
            tags: Optional tags to filter services
            strategy: Load balancing strategy (round_robin, weighted, random)
            
        Returns:
            Selected service or None if no healthy services available
        """
        healthy_services = self.get_healthy_services(tags)
        
        if not healthy_services:
            return None
        
        strategy = strategy or self.config.get('load_balancing_strategy', 'round_robin')
        
        if strategy == 'round_robin':
            return self._round_robin_selection(healthy_services)
        elif strategy == 'weighted':
            return self._weighted_selection(healthy_services)
        elif strategy == 'random':
            return self._random_selection(healthy_services)
        else:
            logger.warning(f"Unknown load balancing strategy: {strategy}, using round_robin")
            return self._round_robin_selection(healthy_services)
    
    def _round_robin_selection(self, services: List[ServiceHealth]) -> ServiceHealth:
        """Round-robin service selection."""
        if not hasattr(self, '_round_robin_index'):
            self._round_robin_index = 0
        
        selected = services[self._round_robin_index % len(services)]
        self._round_robin_index += 1
        return selected
    
    def _weighted_selection(self, services: List[ServiceHealth]) -> ServiceHealth:
        """Weighted service selection based on service weights."""
        import random
        
        total_weight = sum(service.endpoint.weight for service in services)
        if total_weight == 0:
            return random.choice(services)
        
        target = random.uniform(0, total_weight)
        current_weight = 0
        
        for service in services:
            current_weight += service.endpoint.weight
            if current_weight >= target:
                return service
        
        return services[-1]  # Fallback
    
    def _random_selection(self, services: List[ServiceHealth]) -> ServiceHealth:
        """Random service selection."""
        import random
        return random.choice(services)
    
    def start_monitoring(self):
        """Start automatic service monitoring."""
        if self.monitoring_active:
            logger.warning("Service monitoring is already active")
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("Started service monitoring")
    
    def stop_monitoring(self):
        """Stop automatic service monitoring."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Stopped service monitoring")
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                self._check_all_services()
                time.sleep(self.config.get('monitoring_interval', 30))
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)  # Short sleep on error
    
    def _check_all_services(self):
        """Check health of all registered services."""
        with self.lock:
            for service_name, service_health in self.services.items():
                try:
                    self._check_service_health(service_health.endpoint, service_health)
                except Exception as e:
                    logger.error(f"Error checking service {service_name}: {e}")
    
    def _check_service_health(self, 
                             endpoint: ServiceEndpoint, 
                             service_health: Optional[ServiceHealth] = None) -> bool:
        """
        Check health of a specific service.
        
        Args:
            endpoint: Service endpoint to check
            service_health: Optional existing service health object to update
            
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            start_time = time.time()
            
            response = requests.get(
                f"{endpoint.url}{endpoint.health_endpoint}",
                timeout=endpoint.timeout
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            is_healthy = response.status_code == 200
            
            if service_health:
                service_health.last_check = datetime.now()
                service_health.response_time = response_time
                
                if is_healthy:
                    if service_health.state != ServiceState.HEALTHY:
                        logger.info(f"Service {endpoint.name} became healthy")
                        self._notify_callbacks('service_healthy', endpoint.name)
                    service_health.state = ServiceState.HEALTHY
                    service_health.consecutive_failures = 0
                    service_health.last_error = None
                else:
                    service_health.consecutive_failures += 1
                    service_health.error_count += 1
                    service_health.last_error = f"HTTP {response.status_code}"
                    
                    if service_health.consecutive_failures >= self.config.get('max_consecutive_failures', 3):
                        if service_health.state != ServiceState.UNHEALTHY:
                            logger.warning(f"Service {endpoint.name} became unhealthy")
                            self._notify_callbacks('service_unhealthy', endpoint.name)
                        service_health.state = ServiceState.UNHEALTHY
            
            return is_healthy
            
        except requests.exceptions.RequestException as e:
            if service_health:
                service_health.consecutive_failures += 1
                service_health.error_count += 1
                service_health.last_error = str(e)
                service_health.response_time = 0
                
                if service_health.consecutive_failures >= self.config.get('max_consecutive_failures', 3):
                    if service_health.state != ServiceState.UNHEALTHY:
                        logger.warning(f"Service {endpoint.name} became unhealthy: {e}")
                        self._notify_callbacks('service_unhealthy', endpoint.name)
                    service_health.state = ServiceState.UNHEALTHY
            
            return False
    
    def add_callback(self, callback: Callable):
        """
        Add a callback function for service state changes.
        
        Args:
            callback: Function to call on service state changes
                     Should accept (event_type: str, service_name: str) parameters
        """
        self.discovery_callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """
        Remove a callback function.
        
        Args:
            callback: Callback function to remove
        """
        if callback in self.discovery_callbacks:
            self.discovery_callbacks.remove(callback)
    
    def _notify_callbacks(self, event_type: str, service_name: str):
        """Notify all registered callbacks of a service state change."""
        for callback in self.discovery_callbacks:
            try:
                callback(event_type, service_name)
            except Exception as e:
                logger.error(f"Error in service discovery callback: {e}")
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """Get statistics about all services."""
        with self.lock:
            stats = {
                'total_services': len(self.services),
                'healthy_services': len([s for s in self.services.values() if s.state == ServiceState.HEALTHY]),
                'unhealthy_services': len([s for s in self.services.values() if s.state == ServiceState.UNHEALTHY]),
                'services': {}
            }
            
            for name, service in self.services.items():
                stats['services'][name] = {
                    'state': service.state.value,
                    'response_time': service.response_time,
                    'error_count': service.error_count,
                    'consecutive_failures': service.consecutive_failures,
                    'last_check': service.last_check.isoformat(),
                    'url': service.endpoint.url,
                    'tags': service.endpoint.tags
                }
            
            return stats
    
    def discover_services(self, discovery_config: Dict[str, Any]) -> List[str]:
        """
        Discover services using various discovery mechanisms.
        
        Args:
            discovery_config: Configuration for service discovery
            
        Returns:
            List of discovered service names
        """
        discovered = []
        
        # DNS-based discovery
        if discovery_config.get('dns_discovery', False):
            discovered.extend(self._discover_via_dns(discovery_config.get('dns_config', {})))
        
        # Consul discovery
        if discovery_config.get('consul_discovery', False):
            discovered.extend(self._discover_via_consul(discovery_config.get('consul_config', {})))
        
        # Static configuration discovery
        if discovery_config.get('static_discovery', False):
            discovered.extend(self._discover_via_static(discovery_config.get('static_config', {})))
        
        return discovered
    
    def _discover_via_dns(self, dns_config: Dict[str, Any]) -> List[str]:
        """Discover services via DNS SRV records."""
        # Implementation would depend on specific DNS discovery requirements
        logger.info("DNS-based service discovery not implemented")
        return []
    
    def _discover_via_consul(self, consul_config: Dict[str, Any]) -> List[str]:
        """Discover services via Consul."""
        # Implementation would depend on Consul integration requirements
        logger.info("Consul-based service discovery not implemented")
        return []
    
    def _discover_via_static(self, static_config: Dict[str, Any]) -> List[str]:
        """Discover services via static configuration."""
        discovered = []
        
        for service_config in static_config.get('services', []):
            endpoint = ServiceEndpoint(
                name=service_config['name'],
                url=service_config['url'],
                health_endpoint=service_config.get('health_endpoint', '/health'),
                weight=service_config.get('weight', 1),
                tags=service_config.get('tags', [])
            )
            
            if self.register_service(endpoint):
                discovered.append(endpoint.name)
        
        return discovered
