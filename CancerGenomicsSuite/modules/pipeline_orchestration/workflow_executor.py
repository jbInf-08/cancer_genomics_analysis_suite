#!/usr/bin/env python3
"""
Workflow Executor

This module provides a unified interface for executing workflows
using different pipeline orchestration systems (Nextflow, Snakemake).
"""

import json
import logging
import os
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime
import asyncio
import concurrent.futures

from .nextflow_manager import NextflowManager
from .snakemake_manager import SnakemakeManager
from .perl_manager import PerlManager
from .seurat_manager import SeuratManager
from .hdock_manager import HDOCKManager
from .haddock_manager import HADDOCKManager
from .saturn_manager import SATurnManager
from .seqant_manager import SeqAntManager
from .pipeline_registry import PipelineRegistry

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """
    Unified workflow executor for cancer genomics analysis pipelines.
    
    Provides functionality to:
    - Execute workflows using different orchestration systems
    - Monitor workflow progress
    - Manage workflow resources
    - Handle workflow dependencies
    """
    
    def __init__(
        self,
        work_dir: Optional[str] = None,
        registry_file: Optional[str] = None,
        max_concurrent_workflows: int = 5,
        history_persist_path: Optional[Union[str, Path]] = None,
    ):
        """
        Initialize workflow executor.
        
        Args:
            work_dir: Working directory for workflow execution
            registry_file: Path to pipeline registry file
            max_concurrent_workflows: Maximum number of concurrent workflows
            history_persist_path: JSONL file to append completed workflow records.
                ``None`` uses ``<work_dir>/workflow_history.jsonl``. Set to ``""``
                to disable. May be overridden by env ``WORKFLOW_HISTORY_JSONL``.
        """
        self.work_dir = Path(work_dir) if work_dir else Path.cwd() / "workflow_work"
        self.work_dir.mkdir(parents=True, exist_ok=True)

        env_hist = os.environ.get("WORKFLOW_HISTORY_JSONL", "").strip()
        if env_hist:
            self.history_persist_path: Optional[Path] = Path(env_hist)
        elif history_persist_path == "":
            self.history_persist_path = None
        elif history_persist_path is not None:
            self.history_persist_path = Path(history_persist_path)
        else:
            self.history_persist_path = self.work_dir / "workflow_history.jsonl"
        
        # Initialize managers
        self.nextflow_manager = NextflowManager(
            work_dir=str(self.work_dir / "nextflow")
        )
        self.snakemake_manager = SnakemakeManager(
            work_dir=str(self.work_dir / "snakemake")
        )
        self.perl_manager = PerlManager(
            work_dir=str(self.work_dir / "perl")
        )
        self.seurat_manager = SeuratManager(
            work_dir=str(self.work_dir / "seurat")
        )
        self.hdock_manager = HDOCKManager(
            work_dir=str(self.work_dir / "hdock")
        )
        self.haddock_manager = HADDOCKManager(
            work_dir=str(self.work_dir / "haddock")
        )
        self.saturn_manager = SATurnManager(
            work_dir=str(self.work_dir / "saturn")
        )
        self.seqant_manager = SeqAntManager(
            work_dir=str(self.work_dir / "seqant")
        )
        
        # Initialize registry
        self.registry = PipelineRegistry(registry_file)
        
        # Workflow management
        self.max_concurrent_workflows = max_concurrent_workflows
        self.active_workflows: Dict[str, Dict] = {}
        self.workflow_history: List[Dict] = []
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent_workflows)
        
        # Workflow queue
        self.workflow_queue: List[Dict] = []

        self._load_persisted_history()

    def _json_for_history(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: self._json_for_history(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._json_for_history(v) for v in obj]
        return obj

    def _append_history(self, entry: Dict[str, Any]) -> None:
        """Append to in-memory history and optional JSONL audit log."""
        self.workflow_history.append(entry)
        if not self.history_persist_path:
            return
        path = Path(self.history_persist_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(self._json_for_history(entry), default=str)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError as e:
            logger.warning("Could not persist workflow history to %s: %s", path, e)

    def _load_persisted_history(self) -> None:
        """Load prior JSONL records (bounded) so history survives process restarts."""
        if not self.history_persist_path:
            return
        path = Path(self.history_persist_path)
        if not path.is_file():
            return
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as e:
            logger.warning("Could not read workflow history %s: %s", path, e)
            return
        cap = 5000
        for line in lines[-cap:]:
            line = line.strip()
            if not line:
                continue
            try:
                self.workflow_history.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed workflow history line in %s", path)
    
    def execute_workflow(
        self,
        pipeline_name: str,
        config: Optional[Dict] = None,
        workflow_name: Optional[str] = None,
        priority: int = 0,
        dependencies: Optional[List[str]] = None
    ) -> str:
        """
        Execute a workflow using the appropriate orchestration system.
        
        Args:
            pipeline_name: Name of the pipeline to execute
            config: Workflow configuration
            workflow_name: Name for the workflow execution
            priority: Workflow priority (higher = more priority)
            dependencies: List of workflow names this depends on
            
        Returns:
            Workflow execution ID
        """
        # Get pipeline information
        pipeline_info = self.registry.get_pipeline(pipeline_name)
        if not pipeline_info:
            raise ValueError(f"Pipeline {pipeline_name} not found in registry")
        
        # Generate workflow name
        workflow_name = workflow_name or f"{pipeline_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Check dependencies
        if dependencies:
            for dep in dependencies:
                if dep not in [w["name"] for w in self.workflow_history]:
                    raise ValueError(f"Dependency {dep} not found in completed workflows")
        
        # Create workflow info
        workflow_info = {
            "name": workflow_name,
            "pipeline_name": pipeline_name,
            "pipeline_info": pipeline_info,
            "config": config or {},
            "priority": priority,
            "dependencies": dependencies or [],
            "status": "queued",
            "created_at": datetime.now(),
            "started_at": None,
            "completed_at": None,
            "execution_id": None,
            "orchestration_system": None,
            "results": {}
        }
        
        # Add to queue
        self.workflow_queue.append(workflow_info)
        
        # Sort queue by priority
        self.workflow_queue.sort(key=lambda x: x["priority"], reverse=True)
        
        # Start workflow if possible
        self._process_queue()
        
        logger.info(f"Workflow {workflow_name} queued for execution")
        return workflow_name
    
    def get_workflow_status(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a workflow execution.
        
        Args:
            workflow_name: Name of the workflow
            
        Returns:
            Workflow status information or None if not found
        """
        # Check active workflows
        if workflow_name in self.active_workflows:
            workflow_info = self.active_workflows[workflow_name].copy()
            if workflow_info["started_at"]:
                workflow_info["duration"] = (datetime.now() - workflow_info["started_at"]).total_seconds()
            return workflow_info
        
        # Check history
        for workflow in self.workflow_history:
            if workflow["name"] == workflow_name:
                return workflow
        
        # Check queue
        for workflow in self.workflow_queue:
            if workflow["name"] == workflow_name:
                return workflow
        
        return None
    
    def list_workflows(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all workflows with optional status filter.
        
        Args:
            status: Filter by status (queued, running, completed, failed, error)
            
        Returns:
            List of workflow information dictionaries
        """
        all_workflows = (
            list(self.active_workflows.values()) +
            self.workflow_history +
            self.workflow_queue
        )
        
        if status:
            all_workflows = [w for w in all_workflows if w.get("status") == status]
        
        return all_workflows
    
    def stop_workflow(self, workflow_name: str) -> bool:
        """
        Stop a running workflow.
        
        Args:
            workflow_name: Name of the workflow to stop
            
        Returns:
            True if workflow was stopped successfully
        """
        if workflow_name not in self.active_workflows:
            return False
        
        workflow_info = self.active_workflows[workflow_name]
        orchestration_system = workflow_info["orchestration_system"]
        execution_id = workflow_info["execution_id"]
        
        # Stop using appropriate manager
        if orchestration_system == "nextflow":
            success = self.nextflow_manager.stop_pipeline(execution_id)
        elif orchestration_system == "snakemake":
            success = self.snakemake_manager.stop_pipeline(execution_id)
        else:
            success = False
        
        if success:
            workflow_info.update({
                "status": "stopped",
                "completed_at": datetime.now()
            })
            
            # Move to history
            self._append_history(workflow_info)
            del self.active_workflows[workflow_name]
            
            logger.info(f"Workflow {workflow_name} stopped")
        
        return success
    
    def get_workflow_results(self, workflow_name: str) -> Dict[str, Any]:
        """
        Get results from a completed workflow.
        
        Args:
            workflow_name: Name of the workflow
            
        Returns:
            Dictionary with workflow results
        """
        workflow_info = self.get_workflow_status(workflow_name)
        if not workflow_info or workflow_info["status"] not in ["completed", "failed"]:
            return {}
        
        orchestration_system = workflow_info["orchestration_system"]
        execution_id = workflow_info["execution_id"]
        
        # Get results using appropriate manager
        if orchestration_system == "nextflow":
            results = self.nextflow_manager.get_pipeline_outputs(execution_id)
        elif orchestration_system == "snakemake":
            results = self.snakemake_manager.get_pipeline_outputs(execution_id)
        else:
            results = {}
        
        return results
    
    def _process_queue(self):
        """Process the workflow queue."""
        while (self.workflow_queue and 
               len(self.active_workflows) < self.max_concurrent_workflows):
            
            workflow_info = self.workflow_queue.pop(0)
            self._start_workflow(workflow_info)
    
    def _start_workflow(self, workflow_info: Dict):
        """
        Start a workflow execution.
        
        Args:
            workflow_info: Workflow information dictionary
        """
        workflow_name = workflow_info["name"]
        pipeline_info = workflow_info["pipeline_info"]
        config = workflow_info["config"]
        
        try:
            # Determine orchestration system
            script_path = Path(pipeline_info["script_path"])
            orchestration_system = self._detect_orchestration_system(script_path)
            
            # Update workflow info
            workflow_info.update({
                "status": "running",
                "started_at": datetime.now(),
                "orchestration_system": orchestration_system
            })
            
            # Add to active workflows
            self.active_workflows[workflow_name] = workflow_info
            
            # Execute workflow
            if orchestration_system == "nextflow":
                execution_id = self._execute_nextflow_workflow(workflow_info)
            elif orchestration_system == "snakemake":
                execution_id = self._execute_snakemake_workflow(workflow_info)
            elif orchestration_system == "perl":
                execution_id = self._execute_perl_workflow(workflow_info)
            elif orchestration_system == "seurat":
                execution_id = self._execute_seurat_workflow(workflow_info)
            elif orchestration_system == "hdock":
                execution_id = self._execute_hdock_workflow(workflow_info)
            elif orchestration_system == "haddock":
                execution_id = self._execute_haddock_workflow(workflow_info)
            elif orchestration_system == "saturn":
                execution_id = self._execute_saturn_workflow(workflow_info)
            elif orchestration_system == "seqant":
                execution_id = self._execute_seqant_workflow(workflow_info)
            else:
                raise ValueError(f"Unsupported orchestration system: {orchestration_system}")
            
            workflow_info["execution_id"] = execution_id
            
            # Submit to executor for monitoring
            future = self.executor.submit(self._monitor_workflow, workflow_name)
            
            logger.info(f"Workflow {workflow_name} started with {orchestration_system}")
            
        except Exception as e:
            logger.error(f"Failed to start workflow {workflow_name}: {e}")
            workflow_info.update({
                "status": "error",
                "error": str(e),
                "completed_at": datetime.now()
            })
            self._append_history(workflow_info)
    
    def _detect_orchestration_system(self, script_path: Path) -> str:
        """
        Detect the orchestration system from script path.
        
        Args:
            script_path: Path to the pipeline script
            
        Returns:
            Orchestration system name
        """
        if script_path.suffix == ".nf":
            return "nextflow"
        elif script_path.suffix == ".smk":
            return "snakemake"
        elif script_path.suffix == ".pl":
            return "perl"
        elif script_path.suffix.lower() == ".r":
            return "seurat"
        else:
            # Try to detect from file content
            try:
                with open(script_path, 'r') as f:
                    content = f.read(1000)  # Read first 1000 characters
                
                if "#!/usr/bin/env nextflow" in content or "nextflow" in content.lower():
                    return "nextflow"
                elif "rule" in content and "input:" in content and "output:" in content:
                    return "snakemake"
                elif "#!/usr/bin/env perl" in content or content.strip().startswith("#!/usr/bin/perl"):
                    return "perl"
                elif "library(Seurat" in content or "Seurat::" in content:
                    return "seurat"
                elif "hdock" in content.lower():
                    return "hdock"
                elif "haddock" in content.lower():
                    return "haddock"
                elif "saturn" in content.lower():
                    return "saturn"
                elif "seqant" in content.lower():
                    return "seqant"
                else:
                    return "unknown"
            except Exception:
                return "unknown"
    
    def _execute_nextflow_workflow(self, workflow_info: Dict) -> str:
        """
        Execute a Nextflow workflow.
        
        Args:
            workflow_info: Workflow information dictionary
            
        Returns:
            Execution ID
        """
        pipeline_info = workflow_info["pipeline_info"]
        config = workflow_info["config"]
        
        # Execute pipeline
        result = self.nextflow_manager.execute_pipeline(
            pipeline_script=pipeline_info["script_path"],
            params=config.get("params", {}),
            profile=config.get("profile"),
            config=config.get("nextflow_config"),
            pipeline_name=workflow_info["name"]
        )
        
        return result["name"]
    
    def _execute_snakemake_workflow(self, workflow_info: Dict) -> str:
        """
        Execute a Snakemake workflow.
        
        Args:
            workflow_info: Workflow information dictionary
            
        Returns:
            Execution ID
        """
        pipeline_info = workflow_info["pipeline_info"]
        config = workflow_info["config"]
        
        # Execute pipeline
        result = self.snakemake_manager.execute_pipeline(
            snakefile=pipeline_info["script_path"],
            targets=config.get("targets"),
            config=config.get("snakemake_config"),
            profile=config.get("profile"),
            pipeline_name=workflow_info["name"],
            dry_run=config.get("dry_run", False)
        )
        
        return result["name"]

    def _execute_perl_workflow(self, workflow_info: Dict) -> str:
        """
        Execute a Perl workflow.
        """
        pipeline_info = workflow_info["pipeline_info"]
        config = workflow_info["config"]

        perl_args = config.get("perl_args", [])
        perl_env = config.get("perl_env", {})

        result = self.perl_manager.execute_pipeline(
            script_path=pipeline_info["script_path"],
            args=perl_args,
            env=perl_env,
            pipeline_name=workflow_info["name"],
        )

        return result["name"]

    def _execute_seurat_workflow(self, workflow_info: Dict) -> str:
        pipeline_info = workflow_info["pipeline_info"]
        config = workflow_info["config"]

        r_args = config.get("r_args", [])
        r_env = config.get("r_env", {})

        result = self.seurat_manager.execute_pipeline(
            script_path=pipeline_info["script_path"],
            args=r_args,
            env=r_env,
            pipeline_name=workflow_info["name"],
        )
        return result["name"]

    def _execute_hdock_workflow(self, workflow_info: Dict) -> str:
        pipeline_info = workflow_info["pipeline_info"]
        config = workflow_info["config"]

        receptor = config.get("receptor") or pipeline_info.get("metadata", {}).get("receptor")
        ligand = config.get("ligand") or pipeline_info.get("metadata", {}).get("ligand")
        hdock_args = config.get("hdock_args", [])
        env = config.get("hdock_env", {})

        result = self.hdock_manager.execute_job(
            receptor=receptor,
            ligand=ligand,
            hdock_args=hdock_args,
            env=env,
            job_name=workflow_info["name"],
        )
        return result["name"]

    def _execute_haddock_workflow(self, workflow_info: Dict) -> str:
        pipeline_info = workflow_info["pipeline_info"]
        config = workflow_info["config"]

        project_dir = config.get("project_dir") or pipeline_info.get("metadata", {}).get("project_dir") or str(Path(pipeline_info["script_path"]).parent)
        config_file = config.get("haddock_config")
        haddock_args = config.get("haddock_args", [])
        env = config.get("haddock_env", {})

        result = self.haddock_manager.execute_job(
            project_dir=project_dir,
            config_file=config_file,
            haddock_args=haddock_args,
            env=env,
            job_name=workflow_info["name"],
        )
        return result["name"]

    def _execute_saturn_workflow(self, workflow_info: Dict) -> str:
        pipeline_info = workflow_info["pipeline_info"]
        config = workflow_info["config"]

        workflow_file = pipeline_info["script_path"]
        saturn_args = config.get("saturn_args", [])
        env = config.get("saturn_env", {})

        result = self.saturn_manager.execute_job(
            workflow_file=workflow_file,
            saturn_args=saturn_args,
            env=env,
            job_name=workflow_info["name"],
        )
        return result["name"]

    def _execute_seqant_workflow(self, workflow_info: Dict) -> str:
        pipeline_info = workflow_info["pipeline_info"]
        config = workflow_info["config"]

        args = config.get("seqant_args", [])
        env = config.get("seqant_env", {})

        result = self.seqant_manager.execute_job(
            script_path=pipeline_info["script_path"],
            args=args,
            env=env,
            job_name=workflow_info["name"],
        )
        return result["name"]
    
    def _monitor_workflow(self, workflow_name: str):
        """
        Monitor a workflow execution.
        
        Args:
            workflow_name: Name of the workflow to monitor
        """
        if workflow_name not in self.active_workflows:
            return
        
        workflow_info = self.active_workflows[workflow_name]
        orchestration_system = workflow_info["orchestration_system"]
        execution_id = workflow_info["execution_id"]
        
        try:
            # Get status from appropriate manager
            if orchestration_system == "nextflow":
                status_info = self.nextflow_manager.get_pipeline_status(execution_id)
            elif orchestration_system == "snakemake":
                status_info = self.snakemake_manager.get_pipeline_status(execution_id)
            elif orchestration_system == "perl":
                status_info = self.perl_manager.get_pipeline_status(execution_id)
            elif orchestration_system == "seurat":
                status_info = self.seurat_manager.get_pipeline_status(execution_id)
            elif orchestration_system == "hdock":
                status_info = self.hdock_manager.get_job_status(execution_id)
            elif orchestration_system == "haddock":
                status_info = self.haddock_manager.get_job_status(execution_id)
            elif orchestration_system == "saturn":
                status_info = self.saturn_manager.get_job_status(execution_id)
            elif orchestration_system == "seqant":
                status_info = self.seqant_manager.get_job_status(execution_id)
            else:
                status_info = None
            
            if status_info and status_info["status"] in ["completed", "failed", "error"]:
                # Workflow completed
                workflow_info.update({
                    "status": status_info["status"],
                    "completed_at": datetime.now(),
                    "results": status_info
                })
                
                # Move to history
                self._append_history(workflow_info)
                del self.active_workflows[workflow_name]
                
                logger.info(f"Workflow {workflow_name} completed with status: {status_info['status']}")
                
                # Process queue for next workflow
                self._process_queue()
        
        except Exception as e:
            logger.error(f"Error monitoring workflow {workflow_name}: {e}")
            workflow_info.update({
                "status": "error",
                "error": str(e),
                "completed_at": datetime.now()
            })
            self._append_history(workflow_info)
            del self.active_workflows[workflow_name]
    
    def create_cancer_genomics_workflow(
        self,
        workflow_type: str,
        data_paths: Dict[str, str],
        output_dir: str,
        config_overrides: Optional[Dict] = None
    ) -> str:
        """
        Create and execute a cancer genomics workflow.
        
        Args:
            workflow_type: Type of workflow (variant_calling, expression_analysis, multi_omics)
            data_paths: Dictionary mapping data types to file paths
            output_dir: Output directory for results
            config_overrides: Configuration overrides
            
        Returns:
            Workflow execution ID
        """
        # Create pipeline if it doesn't exist
        pipeline_name = f"cancer_genomics_{workflow_type}"
        
        if not self.registry.get_pipeline(pipeline_name):
            if workflow_type == "variant_calling":
                script_path = self.nextflow_manager.create_cancer_genomics_pipeline("variant_calling")
                orchestration_system = "nextflow"
            elif workflow_type == "expression_analysis":
                script_path = self.snakemake_manager.create_cancer_genomics_snakefile("expression_analysis")
                orchestration_system = "snakemake"
            elif workflow_type == "multi_omics":
                script_path = self.nextflow_manager.create_cancer_genomics_pipeline("multi_omics")
                orchestration_system = "nextflow"
            else:
                raise ValueError(f"Unknown workflow type: {workflow_type}")
            
            # Register pipeline
            self.registry.register_pipeline(
                name=pipeline_name,
                pipeline_type=workflow_type,
                description=f"Cancer genomics {workflow_type} workflow",
                script_path=script_path,
                config_template={
                    "defaults": {
                        "output_dir": output_dir,
                        "data_paths": data_paths
                    },
                    "required": ["output_dir", "data_paths"]
                },
                requirements=["bwa", "samtools", "gatk", "fastqc"],
                tags=["cancer", "genomics", workflow_type],
                author="Cancer Genomics Analysis Suite"
            )
        
        # Create configuration
        config = {
            "output_dir": output_dir,
            "data_paths": data_paths,
            **(config_overrides or {})
        }
        
        # Execute workflow
        return self.execute_workflow(
            pipeline_name=pipeline_name,
            config=config
        )
    
    def run_molecular_dynamics_workflow(
        self,
        config: Optional[Dict[str, Any]] = None,
        workflow_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run the built-in GROMACS workflow (PDB fetch + vacuum energy minimization
        or mdrun from a provided .tpr). Result is appended to ``workflow_history``.

        Args:
            config: Passed to :class:`MolecularDynamicsWorkflow`, including any of
                ``pdb_id``, ``pdb_path``, ``alphafold_uniprot``, ``alphafold_gene_symbol``,
                ``alphafold_organism_id``, ``tpr_path``, ``gene_symbol``, ``mutation_summary``,
                ``keep_workdir``, download timeouts, etc. See ``docs/MD_GROMACS_AND_ENSEMBL.md``.
            workflow_name: Optional label for history entry.

        Returns:
            Workflow result dict from the MD runner (includes ``success``).
        """
        from .md_workflow import MolecularDynamicsWorkflow

        name = workflow_name or f"md_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        md = MolecularDynamicsWorkflow(work_root=str(self.work_dir / "md_runs"))
        result = md.run(config or {})

        entry: Dict[str, Any] = {
            "name": name,
            "pipeline_name": "molecular_dynamics",
            "pipeline_info": {
                "pipeline_type": "molecular_dynamics",
                "description": "GROMACS MD / energy minimization",
            },
            "config": dict(config or {}),
            "status": "completed" if result.get("success") else "failed",
            "created_at": datetime.now(),
            "started_at": datetime.now(),
            "completed_at": datetime.now(),
            "execution_id": None,
            "orchestration_system": "gromacs",
            "results": result,
        }
        self._append_history(entry)
        logger.info("Molecular dynamics workflow %s finished: %s", name, entry["status"])
        return result

    def get_workflow_statistics(self) -> Dict[str, Any]:
        """
        Get workflow execution statistics.
        
        Returns:
            Dictionary with workflow statistics
        """
        stats = {
            "total_workflows": len(self.workflow_history) + len(self.active_workflows),
            "active_workflows": len(self.active_workflows),
            "queued_workflows": len(self.workflow_queue),
            "completed_workflows": len([w for w in self.workflow_history if w["status"] == "completed"]),
            "failed_workflows": len([w for w in self.workflow_history if w["status"] in ["failed", "error"]]),
            "orchestration_systems": {},
            "pipeline_types": {},
            "average_execution_time": 0
        }
        
        # Count by orchestration system
        for workflow in self.workflow_history + list(self.active_workflows.values()):
            system = workflow.get("orchestration_system", "unknown")
            stats["orchestration_systems"][system] = stats["orchestration_systems"].get(system, 0) + 1
        
        # Count by pipeline type
        for workflow in self.workflow_history + list(self.active_workflows.values()):
            pipeline_type = workflow.get("pipeline_info", {}).get("pipeline_type", "unknown")
            stats["pipeline_types"][pipeline_type] = stats["pipeline_types"].get(pipeline_type, 0) + 1
        
        # Calculate average execution time
        completed_workflows = [w for w in self.workflow_history if w["status"] == "completed" and w.get("started_at") and w.get("completed_at")]
        if completed_workflows:
            total_time = sum(
                (w["completed_at"] - w["started_at"]).total_seconds()
                for w in completed_workflows
            )
            stats["average_execution_time"] = total_time / len(completed_workflows)
        
        return stats
    
    def cleanup(self):
        """Clean up resources."""
        # Stop all active workflows
        for workflow_name in list(self.active_workflows.keys()):
            self.stop_workflow(workflow_name)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.info("Workflow executor cleaned up")
