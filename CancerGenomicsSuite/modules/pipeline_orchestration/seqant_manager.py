#!/usr/bin/env python3
"""
SeqAnt Pipeline Manager

Executes SeqAnt scripts (Python/Perl shebang) by invoking interpreter or script directly.
"""

import os
import logging
import subprocess
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class SeqAntManager:
    def __init__(self, work_dir: Optional[str] = None):
        self.work_dir = Path(work_dir) if work_dir else Path.cwd() / "seqant_work"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        self.job_history: List[Dict[str, Any]] = []

    def execute_job(
        self,
        script_path: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        job_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        script_path = str(script_path)
        job_name = job_name or Path(script_path).stem + "_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        exec_dir = self.work_dir / job_name
        exec_dir.mkdir(parents=True, exist_ok=True)

        # Detect interpreter from extension or shebang
        interpreter: Optional[str] = None
        suffix = Path(script_path).suffix.lower()
        if suffix in (".py", ".pyw"):
            interpreter = "python3"
        elif suffix == ".pl":
            interpreter = "perl"
        else:
            try:
                with open(script_path, "r", encoding="utf-8", errors="ignore") as f:
                    first_line = f.readline()
                if "python" in first_line:
                    interpreter = "python3"
                elif "perl" in first_line:
                    interpreter = "perl"
            except Exception:
                interpreter = None

        cmd: List[str]
        if interpreter:
            cmd = [interpreter, script_path]
        else:
            cmd = [script_path]
        if args:
            cmd.extend(args)

        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        logger.info("Executing SeqAnt job %s", job_name)
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

            job_info: Dict[str, Any] = {
                "name": job_name,
                "script": script_path,
                "args": args or [],
                "exec_dir": str(exec_dir),
                "process": process,
                "start_time": datetime.now(),
                "status": "running",
            }
            self.active_jobs[job_name] = job_info

            stdout, stderr = process.communicate()
            job_info.update(
                {
                    "end_time": datetime.now(),
                    "status": "completed" if process.returncode == 0 else "failed",
                    "return_code": process.returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                }
            )
            self.job_history.append(job_info)
            del self.active_jobs[job_name]

            logger.info("SeqAnt job %s finished with status %s", job_name, job_info["status"])
            return job_info

        except Exception as exc:
            logger.error("Failed to execute SeqAnt job %s: %s", job_name, exc)
            if job_name in self.active_jobs:
                self.active_jobs[job_name].update(
                    {"end_time": datetime.now(), "status": "error", "error": str(exc)}
                )
                self.job_history.append(self.active_jobs[job_name])
                del self.active_jobs[job_name]
            raise

    def get_job_status(self, job_name: str) -> Optional[Dict[str, Any]]:
        if job_name in self.active_jobs:
            info = self.active_jobs[job_name].copy()
            info["duration"] = (datetime.now() - info["start_time"]).total_seconds()
            return info
        for j in self.job_history:
            if j["name"] == job_name:
                return j
        return None

    def stop_job(self, job_name: str) -> bool:
        if job_name not in self.active_jobs:
            return False
        info = self.active_jobs[job_name]
        process = info.get("process")
        if process and process.poll() is None:
            process.terminate()
            info.update({"end_time": datetime.now(), "status": "stopped"})
            self.job_history.append(info)
            del self.active_jobs[job_name]
            logger.info("SeqAnt job %s stopped", job_name)
            return True
        return False

    def get_outputs(self, job_name: str) -> Dict[str, Any]:
        info = self.get_job_status(job_name)
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


