"""
Tamarind Bio Integration Client

Provides functionality to interact with Tamarind Bio for bioinformatics workflows.
"""

import os
import subprocess
import tempfile
import json
import shutil
from typing import Dict, List, Optional, Any, Union
import logging
import platform

logger = logging.getLogger(__name__)

class TamarindClient:
    """Client for interacting with Tamarind Bio"""
    
    def __init__(self):
        """Initialize Tamarind client"""
        self.system = platform.system().lower()
        self.tamarind_path = self._find_tamarind()
    
    def _find_tamarind(self) -> Optional[str]:
        """Find Tamarind Bio installation"""
        possible_paths = [
            'tamarind',
            '/usr/bin/tamarind',
            '/usr/local/bin/tamarind',
            '/opt/tamarind/bin/tamarind'
        ]
        
        for path in possible_paths:
            if shutil.which(path):
                logger.info(f"Found Tamarind Bio at: {path}")
                return path
        
        logger.warning("Tamarind Bio not found in standard locations")
        return None
    
    def is_available(self) -> bool:
        """Check if Tamarind Bio is available"""
        return self.tamarind_path is not None
    
    def run_workflow(self, workflow_file: str, input_data: Dict[str, str]) -> Dict[str, Any]:
        """Run a bioinformatics workflow using Tamarind Bio"""
        try:
            if not self.is_available():
                return {'success': False, 'error': 'Tamarind Bio not available'}
            
            if not os.path.exists(workflow_file):
                return {'success': False, 'error': f'Workflow file not found: {workflow_file}'}
            
            # Run workflow
            cmd = [self.tamarind_path, '--workflow', workflow_file]
            for key, value in input_data.items():
                cmd.extend(['--input', f'{key}={value}'])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr
            }
            
        except Exception as e:
            logger.error(f"Error running workflow: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_version(self) -> str:
        """Get Tamarind Bio version"""
        if not self.is_available():
            return "Not available"
        
        try:
            result = subprocess.run([self.tamarind_path, '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return "Unknown"
        except Exception as e:
            logger.error(f"Error getting Tamarind Bio version: {e}")
            return "Unknown"
