"""
GROMACS Integration Client

Provides functionality to interact with GROMACS for molecular dynamics simulations.
"""

import os
import subprocess
import tempfile
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import logging
import platform

logger = logging.getLogger(__name__)

class GROMACSClient:
    """Client for interacting with GROMACS"""
    
    def __init__(self):
        """Initialize GROMACS client"""
        self.system = platform.system().lower()
        self.gromacs_path = self._find_gromacs()
        self.available_tools = self._get_available_tools()
    
    def _find_gromacs(self) -> Optional[str]:
        """Find GROMACS installation"""
        possible_paths = [
            'gmx',
            '/usr/bin/gmx',
            '/usr/local/bin/gmx',
            '/opt/gromacs/bin/gmx'
        ]
        
        for path in possible_paths:
            if shutil.which(path):
                logger.info(f"Found GROMACS at: {path}")
                return path
        
        logger.warning("GROMACS not found in standard locations")
        return None
    
    def _get_available_tools(self) -> List[str]:
        """Get list of available GROMACS tools"""
        return [
            'grompp', 'mdrun', 'editconf', 'genbox', 'genion',
            'pdb2gmx', 'gmxdump', 'gmxcheck', 'gmxenergy',
            'gmxrms', 'gmxrmsf', 'gmxgyrate', 'gmxmsd'
        ]
    
    def is_available(self) -> bool:
        """Check if GROMACS is available"""
        return self.gromacs_path is not None
    
    def run_simulation(self, input_files: Dict[str, str], 
                      parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Run a molecular dynamics simulation"""
        try:
            if not self.is_available():
                return {'success': False, 'error': 'GROMACS not available'}
            
            # Create temporary directory for simulation
            with tempfile.TemporaryDirectory() as temp_dir:
                # Copy input files (expects e.g. simulation.tpr in temp_dir root)
                for _file_type, file_path in input_files.items():
                    if os.path.exists(file_path):
                        shutil.copy2(file_path, temp_dir)
                
                # Run simulation
                cmd = [self.gromacs_path, 'mdrun', '-deffnm', 'simulation']
                result = subprocess.run(cmd, cwd=temp_dir, capture_output=True, text=True, timeout=3600)
                
                return {
                    'success': result.returncode == 0,
                    'output': result.stdout,
                    'error': result.stderr
                }
                
        except Exception as e:
            logger.error(f"Error running simulation: {e}")
            return {'success': False, 'error': str(e)}

    _EM_MDP = """integrator  = steep
nsteps      = 500
emtol       = 1000.0
emstep      = 0.01
nstxout     = 0
"""

    def run_energy_minimization_from_pdb(
        self, pdb_path: str, work_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run a short in-vacuum steepest-descent energy minimization from a PDB.

        Tries multiple force fields until ``pdb2gmx`` succeeds, then editconf,
        ``grompp``, and ``mdrun``.
        """
        if not self.is_available():
            return {"success": False, "error": "GROMACS not available"}

        work = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="gmx_em_"))
        work.mkdir(parents=True, exist_ok=True)
        pdb_in = Path(pdb_path)
        if not pdb_in.is_file():
            return {"success": False, "error": f"PDB not found: {pdb_path}"}

        shutil.copy2(pdb_in, work / "input.pdb")
        gmx = self.gromacs_path

        def _run(args: List[str], timeout: int = 600) -> subprocess.CompletedProcess:
            return subprocess.run(
                [gmx, *args],
                cwd=str(work),
                capture_output=True,
                text=True,
                timeout=timeout,
            )

        last_pdb2gmx_err = ""
        chosen_ff = None
        for ff in ("amber99sb-ildn", "oplsaa", "charmm27"):
            r = _run(
                [
                    "pdb2gmx",
                    "-f",
                    "input.pdb",
                    "-o",
                    "processed.gro",
                    "-p",
                    "topol.top",
                    "-ff",
                    ff,
                    "-water",
                    "tip3p",
                    "-ignh",
                ],
                timeout=120,
            )
            if r.returncode == 0:
                chosen_ff = ff
                break
            last_pdb2gmx_err = r.stderr or r.stdout or "unknown error"

        if not chosen_ff:
            return {
                "success": False,
                "error": f"pdb2gmx failed for all force fields: {last_pdb2gmx_err}",
            }

        r2 = _run(
            [
                "editconf",
                "-f",
                "processed.gro",
                "-o",
                "box.gro",
                "-c",
                "-d",
                "1.0",
                "-bt",
                "cubic",
            ],
            timeout=120,
        )
        if r2.returncode != 0:
            return {
                "success": False,
                "error": f"editconf failed: {r2.stderr}",
                "force_field": chosen_ff,
            }

        (work / "em.mdp").write_text(self._EM_MDP, encoding="utf-8")
        r3 = _run(
            [
                "grompp",
                "-f",
                "em.mdp",
                "-c",
                "box.gro",
                "-p",
                "topol.top",
                "-o",
                "em.tpr",
                "-maxwarn",
                "2",
            ],
            timeout=120,
        )
        if r3.returncode != 0:
            return {
                "success": False,
                "error": f"grompp failed: {r3.stderr}",
                "force_field": chosen_ff,
            }

        r4 = _run(["mdrun", "-deffnm", "em", "-ntmpi", "1"], timeout=600)
        return {
            "success": r4.returncode == 0,
            "output": r4.stdout,
            "error": r4.stderr if r4.returncode != 0 else "",
            "force_field": chosen_ff,
            "em_gro": str(work / "em.gro") if (work / "em.gro").is_file() else None,
            "em_tpr": str(work / "em.tpr") if (work / "em.tpr").is_file() else None,
            "work_dir": str(work),
        }

    def get_version(self) -> str:
        """Get GROMACS version"""
        if not self.is_available():
            return "Not available"
        
        try:
            result = subprocess.run([self.gromacs_path, '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return "Unknown"
        except Exception as e:
            logger.error(f"Error getting GROMACS version: {e}")
            return "Unknown"
