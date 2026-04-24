#!/usr/bin/env python3
"""
Startup script for integrated biomarker analysis services.

This script helps users start both CGAS and biomarker_identifier services
and provides options for different startup configurations.
"""

import os
import sys
import subprocess
import argparse
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Add the parent directory to the path to import CGAS modules
sys.path.append(str(Path(__file__).parent.parent))

from integrations.service_discovery import ServiceDiscovery
from integrations.config import get_config

logger = logging.getLogger(__name__)


class IntegratedServicesManager:
    """Manager for starting and monitoring integrated services."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the services manager."""
        self.config_path = config_path
        self.config = self._load_config()
        self.processes = {}
        self.service_discovery = None
        
        # Set up logging
        self._setup_logging()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        if self.config_path and os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        else:
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'services': {
                'cgas': {
                    'enabled': True,
                    'command': 'python main_dashboard.py',
                    'working_directory': str(Path(__file__).parent.parent),
                    'port': 8050,
                    'health_endpoint': '/api/health',
                    'startup_timeout': 30
                },
                'biomarker_identifier': {
                    'enabled': True,
                    'command': 'docker-compose up',
                    'working_directory': os.path.expanduser('~/biomarker_identifier'),
                    'port': 8000,
                    'health_endpoint': '/health',
                    'startup_timeout': 60
                }
            },
            'monitoring': {
                'enabled': True,
                'interval': 30,
                'timeout': 5
            }
        }
    
    def _setup_logging(self):
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('integrated_services.log')
            ]
        )
    
    def start_services(self, 
                      cgas_only: bool = False, 
                      biomarker_only: bool = False,
                      wait_for_ready: bool = True) -> bool:
        """
        Start the integrated services.
        
        Args:
            cgas_only: Start only CGAS service
            biomarker_only: Start only biomarker_identifier service
            wait_for_ready: Wait for services to be ready before returning
            
        Returns:
            True if all requested services started successfully
        """
        logger.info("Starting integrated biomarker analysis services")
        
        success = True
        
        # Start CGAS
        if not biomarker_only and self.config['services']['cgas']['enabled']:
            if self._start_cgas():
                logger.info("CGAS service started successfully")
            else:
                logger.error("Failed to start CGAS service")
                success = False
        
        # Start biomarker_identifier
        if not cgas_only and self.config['services']['biomarker_identifier']['enabled']:
            if self._start_biomarker_identifier():
                logger.info("Biomarker Identifier service started successfully")
            else:
                logger.error("Failed to start Biomarker Identifier service")
                success = False
        
        # Wait for services to be ready
        if wait_for_ready and success:
            success = self._wait_for_services_ready()
        
        # Start monitoring if enabled
        if success and self.config['monitoring']['enabled']:
            self._start_monitoring()
        
        return success
    
    def _start_cgas(self) -> bool:
        """Start CGAS service."""
        try:
            cgas_config = self.config['services']['cgas']
            working_dir = cgas_config['working_directory']
            command = cgas_config['command']
            
            logger.info(f"Starting CGAS service in {working_dir}")
            
            # Start the process
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes['cgas'] = process
            return True
            
        except Exception as e:
            logger.error(f"Failed to start CGAS service: {e}")
            return False
    
    def _start_biomarker_identifier(self) -> bool:
        """Start biomarker_identifier service."""
        try:
            bi_config = self.config['services']['biomarker_identifier']
            working_dir = bi_config['working_directory']
            command = bi_config['command']
            
            # Check if working directory exists
            if not os.path.exists(working_dir):
                logger.error(f"Biomarker Identifier directory not found: {working_dir}")
                return False
            
            logger.info(f"Starting Biomarker Identifier service in {working_dir}")
            
            # Start the process
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes['biomarker_identifier'] = process
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Biomarker Identifier service: {e}")
            return False
    
    def _wait_for_services_ready(self) -> bool:
        """Wait for services to be ready."""
        logger.info("Waiting for services to be ready...")
        
        all_ready = True
        
        for service_name, process in self.processes.items():
            config = self.config['services'][service_name]
            timeout = config.get('startup_timeout', 30)
            
            if self._wait_for_service_ready(service_name, timeout):
                logger.info(f"{service_name} service is ready")
            else:
                logger.error(f"{service_name} service failed to become ready")
                all_ready = False
        
        return all_ready
    
    def _wait_for_service_ready(self, service_name: str, timeout: int) -> bool:
        """Wait for a specific service to be ready."""
        config = self.config['services'][service_name]
        port = config['port']
        health_endpoint = config['health_endpoint']
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                import requests
                response = requests.get(
                    f"http://localhost:{port}{health_endpoint}",
                    timeout=5
                )
                if response.status_code == 200:
                    return True
            except:
                pass
            
            time.sleep(2)
        
        return False
    
    def _start_monitoring(self):
        """Start service monitoring."""
        try:
            self.service_discovery = ServiceDiscovery()
            self.service_discovery.start_monitoring()
            logger.info("Service monitoring started")
        except Exception as e:
            logger.error(f"Failed to start service monitoring: {e}")
    
    def stop_services(self):
        """Stop all running services."""
        logger.info("Stopping integrated services")
        
        # Stop monitoring
        if self.service_discovery:
            self.service_discovery.stop_monitoring()
        
        # Stop processes
        for service_name, process in self.processes.items():
            try:
                logger.info(f"Stopping {service_name} service")
                process.terminate()
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing {service_name} service")
                process.kill()
            except Exception as e:
                logger.error(f"Error stopping {service_name} service: {e}")
        
        self.processes.clear()
        logger.info("All services stopped")
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all services."""
        status = {
            'services': {},
            'monitoring': {
                'enabled': self.service_discovery is not None,
                'active': self.service_discovery.monitoring_active if self.service_discovery else False
            }
        }
        
        for service_name, process in self.processes.items():
            status['services'][service_name] = {
                'running': process.poll() is None,
                'pid': process.pid,
                'return_code': process.returncode
            }
        
        return status
    
    def check_service_health(self) -> Dict[str, Any]:
        """Check health of all services."""
        health_status = {}
        
        for service_name, config in self.config['services'].items():
            if not config['enabled']:
                continue
                
            try:
                import requests
                port = config['port']
                health_endpoint = config['health_endpoint']
                
                response = requests.get(
                    f"http://localhost:{port}{health_endpoint}",
                    timeout=5
                )
                
                health_status[service_name] = {
                    'healthy': response.status_code == 200,
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds()
                }
                
            except Exception as e:
                health_status[service_name] = {
                    'healthy': False,
                    'error': str(e)
                }
        
        return health_status


def main():
    """Main function for the startup script."""
    parser = argparse.ArgumentParser(description='Start integrated biomarker analysis services')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--cgas-only', action='store_true', help='Start only CGAS service')
    parser.add_argument('--biomarker-only', action='store_true', help='Start only Biomarker Identifier service')
    parser.add_argument('--no-wait', action='store_true', help='Do not wait for services to be ready')
    parser.add_argument('--status', action='store_true', help='Check service status')
    parser.add_argument('--health', action='store_true', help='Check service health')
    parser.add_argument('--stop', action='store_true', help='Stop all services')
    
    args = parser.parse_args()
    
    # Create services manager
    manager = IntegratedServicesManager(args.config)
    
    try:
        if args.status:
            status = manager.get_service_status()
            print(json.dumps(status, indent=2))
            return
        
        if args.health:
            health = manager.check_service_health()
            print(json.dumps(health, indent=2))
            return
        
        if args.stop:
            manager.stop_services()
            return
        
        # Start services
        success = manager.start_services(
            cgas_only=args.cgas_only,
            biomarker_only=args.biomarker_only,
            wait_for_ready=not args.no_wait
        )
        
        if success:
            print("✅ All services started successfully!")
            print("\nService URLs:")
            if not args.biomarker_only:
                print("  - CGAS Dashboard: http://localhost:8050")
            if not args.cgas_only:
                print("  - Biomarker Identifier API: http://localhost:8000")
                print("  - API Documentation: http://localhost:8000/docs")
            
            print("\nPress Ctrl+C to stop all services")
            
            # Keep running until interrupted
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Stopping services...")
                manager.stop_services()
        else:
            print("❌ Failed to start some services")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
