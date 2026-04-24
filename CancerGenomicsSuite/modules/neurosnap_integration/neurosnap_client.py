"""
Neurosnap Integration Client

Provides functionality to interact with Neurosnap for neuroscience data analysis.
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

class NeurosnapClient:
    """Client for interacting with Neurosnap"""
    
    def __init__(self):
        """Initialize Neurosnap client"""
        self.system = platform.system().lower()
        self.neurosnap_path = self._find_neurosnap()
    
    def _find_neurosnap(self) -> Optional[str]:
        """Find Neurosnap installation"""
        possible_paths = [
            'neurosnap',
            '/usr/bin/neurosnap',
            '/usr/local/bin/neurosnap',
            '/opt/neurosnap/bin/neurosnap'
        ]
        
        for path in possible_paths:
            if shutil.which(path):
                logger.info(f"Found Neurosnap at: {path}")
                return path
        
        logger.warning("Neurosnap not found in standard locations")
        return None
    
    def is_available(self) -> bool:
        """Check if Neurosnap is available"""
        return self.neurosnap_path is not None
    
    def analyze_neural_data(self, data_file: str, analysis_type: str = "spike_detection") -> Dict[str, Any]:
        """Analyze neural data using Neurosnap"""
        try:
            if not self.is_available():
                return {'success': False, 'error': 'Neurosnap not available'}
            
            if not os.path.exists(data_file):
                return {'success': False, 'error': f'Data file not found: {data_file}'}
            
            # Run analysis
            cmd = [self.neurosnap_path, '--input', data_file, '--analysis', analysis_type]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr,
                'analysis_type': analysis_type
            }
            
        except Exception as e:
            logger.error(f"Error analyzing neural data: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_version(self) -> str:
        """Get Neurosnap version"""
        if not self.is_available():
            return "Not available"
        
        try:
            result = subprocess.run([self.neurosnap_path, '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return "Unknown"
        except Exception as e:
            logger.error(f"Error getting Neurosnap version: {e}")
            return "Unknown"
