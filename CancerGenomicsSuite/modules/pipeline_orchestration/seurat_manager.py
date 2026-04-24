#!/usr/bin/env python3
"""
Seurat Pipeline Manager

Executes R scripts (e.g., Seurat workflows) using Rscript and tracks status.
"""

import os
import logging
import subprocess
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class SeuratManager:
    def __init__(self, work_dir: Optional[str] = None):
        self.work_dir = Path(work_dir) if work_dir else Path.cwd() / "seurat_work"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.active_pipelines: Dict[str, Dict[str, Any]] = {}
        self.pipeline_history: List[Dict[str, Any]] = []

    def execute_pipeline(
        self,
        script_path: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        pipeline_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        script_path = str(script_path)
        pipeline_name = pipeline_name or Path(script_path).stem + "_" + datetime.now().strftime("%Y%m%d_%H%M%S")

        exec_dir = self.work_dir / pipeline_name
        exec_dir.mkdir(parents=True, exist_ok=True)

        cmd = ["Rscript", script_path]
        if args:
            cmd.extend(args)

        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        logger.info("Executing Seurat/R pipeline %s", pipeline_name)
        logger.info("Command: %s", " ".join(cmd))

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(exec_dir),
                env=merged_env,
            )

            pipeline_info: Dict[str, Any] = {
                "name": pipeline_name,
                "script": script_path,
                "args": args or [],
                "exec_dir": str(exec_dir),
                "process": process,
                "start_time": datetime.now(),
                "status": "running",
            }
            self.active_pipelines[pipeline_name] = pipeline_info

            stdout, stderr = process.communicate()
            pipeline_info.update(
                {
                    "end_time": datetime.now(),
                    "status": "completed" if process.returncode == 0 else "failed",
                    "return_code": process.returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                }
            )
            self.pipeline_history.append(pipeline_info)
            del self.active_pipelines[pipeline_name]

            logger.info("Seurat/R pipeline %s finished with status %s", pipeline_name, pipeline_info["status"])
            return pipeline_info

        except Exception as exc:
            logger.error("Failed to execute Seurat/R pipeline %s: %s", pipeline_name, exc)
            if pipeline_name in self.active_pipelines:
                self.active_pipelines[pipeline_name].update(
                    {"end_time": datetime.now(), "status": "error", "error": str(exc)}
                )
                self.pipeline_history.append(self.active_pipelines[pipeline_name])
                del self.active_pipelines[pipeline_name]
            raise

    def get_pipeline_status(self, pipeline_name: str) -> Optional[Dict[str, Any]]:
        if pipeline_name in self.active_pipelines:
            info = self.active_pipelines[pipeline_name].copy()
            info["duration"] = (datetime.now() - info["start_time"]).total_seconds()
            return info
        for p in self.pipeline_history:
            if p["name"] == pipeline_name:
                return p
        return None

    def stop_pipeline(self, pipeline_name: str) -> bool:
        if pipeline_name not in self.active_pipelines:
            return False
        info = self.active_pipelines[pipeline_name]
        process = info.get("process")
        if process and process.poll() is None:
            process.terminate()
            info.update({"end_time": datetime.now(), "status": "stopped"})
            self.pipeline_history.append(info)
            del self.active_pipelines[pipeline_name]
            logger.info("Seurat/R pipeline %s stopped", pipeline_name)
            return True
        return False

    def list_pipelines(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        pipelines = list(self.active_pipelines.values()) + self.pipeline_history
        if status:
            pipelines = [p for p in pipelines if p.get("status") == status]
        return pipelines

    def get_pipeline_outputs(self, pipeline_name: str) -> Dict[str, Any]:
        info = self.get_pipeline_status(pipeline_name)
        if not info or info.get("status") not in ["completed", "failed", "stopped"]:
            return {}
        exec_dir = Path(info["exec_dir"])
        files: List[Dict[str, Any]] = []
        for path in exec_dir.rglob("*"):
            if path.is_file():
                files.append(
                    {
                        "path": str(path.relative_to(exec_dir)),
                        "size": path.stat().st_size,
                        "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                    }
                )
        return {"execution_directory": str(exec_dir), "files": files}


