"""
WGSIM Tools Integration Client

Provides functionality to interact with wgsim and dwgsim tools for read simulation.
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

class WGSIMClient:
    """Client for interacting with wgsim and dwgsim tools"""
    
    def __init__(self):
        """Initialize WGSIM client"""
        self.system = platform.system().lower()
        self.wgsim_path = self._find_wgsim()
        self.dwgsim_path = self._find_dwgsim()
    
    def _find_wgsim(self) -> Optional[str]:
        """Find wgsim installation"""
        possible_paths = [
            'wgsim',
            '/usr/bin/wgsim',
            '/usr/local/bin/wgsim',
            '/opt/wgsim/bin/wgsim'
        ]
        
        for path in possible_paths:
            if shutil.which(path):
                logger.info(f"Found wgsim at: {path}")
                return path
        
        logger.warning("wgsim not found in standard locations")
        return None
    
    def _find_dwgsim(self) -> Optional[str]:
        """Find dwgsim installation"""
        possible_paths = [
            'dwgsim',
            '/usr/bin/dwgsim',
            '/usr/local/bin/dwgsim',
            '/opt/dwgsim/bin/dwgsim'
        ]
        
        for path in possible_paths:
            if shutil.which(path):
                logger.info(f"Found dwgsim at: {path}")
                return path
        
        logger.warning("dwgsim not found in standard locations")
        return None
    
    def is_wgsim_available(self) -> bool:
        """Check if wgsim is available"""
        return self.wgsim_path is not None
    
    def is_dwgsim_available(self) -> bool:
        """Check if dwgsim is available"""
        return self.dwgsim_path is not None
    
    def simulate_reads(self, reference_file: str, output_prefix: str,
                      num_reads: int = 1000000, read_length: int = 100,
                      error_rate: float = 0.02, mutation_rate: float = 0.001,
                      indel_rate: float = 0.0001, tool: str = 'wgsim') -> Dict[str, Any]:
        """
        Simulate reads using wgsim or dwgsim
        
        Args:
            reference_file: Path to reference genome
            output_prefix: Output file prefix
            num_reads: Number of reads to simulate
            read_length: Length of reads
            error_rate: Sequencing error rate
            mutation_rate: Mutation rate
            indel_rate: Indel rate
            tool: Tool to use ('wgsim' or 'dwgsim')
            
        Returns:
            Dictionary containing simulation results
        """
        try:
            if tool == 'wgsim' and not self.is_wgsim_available():
                return {'success': False, 'error': 'wgsim not available'}
            elif tool == 'dwgsim' and not self.is_dwgsim_available():
                return {'success': False, 'error': 'dwgsim not available'}
            
            if not os.path.exists(reference_file):
                return {'success': False, 'error': f'Reference file not found: {reference_file}'}
            
            # Build command
            if tool == 'wgsim':
                cmd = [
                    self.wgsim_path,
                    '-e', str(error_rate),
                    '-r', str(mutation_rate),
                    '-R', str(indel_rate),
                    '-N', str(num_reads),
                    '-1', str(read_length),
                    '-2', str(read_length),
                    reference_file,
                    f'{output_prefix}_1.fastq',
                    f'{output_prefix}_2.fastq'
                ]
            else:  # dwgsim
                cmd = [
                    self.dwgsim_path,
                    '-e', str(error_rate),
                    '-r', str(mutation_rate),
                    '-R', str(indel_rate),
                    '-N', str(num_reads),
                    '-1', str(read_length),
                    '-2', str(read_length),
                    reference_file,
                    output_prefix
                ]
            
            # Run simulation
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr,
                'tool': tool,
                'num_reads': num_reads,
                'read_length': read_length
            }
            
        except Exception as e:
            logger.error(f"Error simulating reads: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_version(self, tool: str = 'wgsim') -> str:
        """Get version of wgsim or dwgsim"""
        if tool == 'wgsim' and not self.is_wgsim_available():
            return "Not available"
        elif tool == 'dwgsim' and not self.is_dwgsim_available():
            return "Not available"
        
        try:
            path = self.wgsim_path if tool == 'wgsim' else self.dwgsim_path
            result = subprocess.run([path, '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return "Unknown"
        except Exception as e:
            logger.error(f"Error getting {tool} version: {e}")
            return "Unknown"
