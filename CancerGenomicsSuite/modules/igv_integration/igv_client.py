"""
IGV Integration Client

Provides functionality to interact with IGV for genomic data visualization.
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

class IGVClient:
    """Client for interacting with IGV"""
    
    def __init__(self):
        """Initialize IGV client"""
        self.system = platform.system().lower()
        self.igv_path = self._find_igv()
        self.available_formats = ['bam', 'vcf', 'bed', 'gff', 'gtf', 'wig', 'bigwig']
    
    def _find_igv(self) -> Optional[str]:
        """Find IGV installation"""
        possible_paths = [
            'igv',
            '/usr/bin/igv',
            '/usr/local/bin/igv',
            '/opt/igv/bin/igv',
            'C:\\Program Files\\IGV\\igv.bat',
            'C:\\Program Files (x86)\\IGV\\igv.bat'
        ]
        
        for path in possible_paths:
            if shutil.which(path) or os.path.exists(path):
                logger.info(f"Found IGV at: {path}")
                return path
        
        logger.warning("IGV not found in standard locations")
        return None
    
    def is_available(self) -> bool:
        """Check if IGV is available"""
        return self.igv_path is not None
    
    def load_genome(self, genome_id: str) -> Dict[str, Any]:
        """Load a genome in IGV"""
        try:
            if not self.is_available():
                return {'success': False, 'error': 'IGV not available'}
            
            # Create IGV batch script
            script_content = f"genome {genome_id}\n"
            
            result = self._execute_igv_script(script_content)
            return result
            
        except Exception as e:
            logger.error(f"Error loading genome: {e}")
            return {'success': False, 'error': str(e)}
    
    def load_track(self, file_path: str, track_name: Optional[str] = None) -> Dict[str, Any]:
        """Load a data track in IGV"""
        try:
            if not os.path.exists(file_path):
                return {'success': False, 'error': f'File not found: {file_path}'}
            
            if track_name is None:
                track_name = os.path.basename(file_path)
            
            script_content = f"load {file_path}\n"
            result = self._execute_igv_script(script_content)
            
            if result['success']:
                result['track_name'] = track_name
                result['file_path'] = file_path
            
            return result
            
        except Exception as e:
            logger.error(f"Error loading track: {e}")
            return {'success': False, 'error': str(e)}
    
    def goto_locus(self, locus: str) -> Dict[str, Any]:
        """Navigate to a specific genomic locus"""
        try:
            script_content = f"goto {locus}\n"
            return self._execute_igv_script(script_content)
        except Exception as e:
            logger.error(f"Error navigating to locus: {e}")
            return {'success': False, 'error': str(e)}
    
    def snapshot(self, output_file: str) -> Dict[str, Any]:
        """Take a snapshot of the current IGV view"""
        try:
            script_content = f"snapshot {output_file}\n"
            return self._execute_igv_script(script_content)
        except Exception as e:
            logger.error(f"Error taking snapshot: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_igv_script(self, script_content: str) -> Dict[str, Any]:
        """Execute IGV batch script"""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(script_content)
                script_file = f.name
            
            # Execute IGV with batch script
            cmd = [self.igv_path, '-b', script_file]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Clean up script file
            os.unlink(script_file)
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr
            }
            
        except Exception as e:
            logger.error(f"Error executing IGV script: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_version(self) -> str:
        """Get IGV version"""
        if not self.is_available():
            return "Not available"
        
        try:
            result = subprocess.run([self.igv_path, '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return "Unknown"
        except Exception as e:
            logger.error(f"Error getting IGV version: {e}")
            return "Unknown"
