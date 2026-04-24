"""
Lightweight workflow state machine (steps + orchestration) used by tests and tooling.

``CancerGenomicsWorkflowSimulator`` in ``simulate_workflow.py`` runs heavy simulations;
this module models workflow *metadata* and execution state for the API surface expected
by ``test_workflow_simulation.py``.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional, Union


def _uid() -> str:
    return str(uuid.uuid4())


class WorkflowStep:
    """A single step in a workflow (pending → running → completed|failed)."""

    def __init__(
        self,
        step_id: str,
        name: str,
        step_type: str,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        self.step_id = step_id
        self.name = name
        self.step_type = step_type
        self.parameters = parameters or {}
        self.status: str = "pending"
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.error_message: Optional[str] = None
        self.result: Any = None

    def start_execution(self) -> None:
        if self.status != "pending":
            raise ValueError("Step already started or finished")
        self.status = "running"
        self.start_time = time.time()

    def complete_execution(self, result: Any) -> None:
        if self.status != "running":
            raise ValueError("Step is not running")
        self.status = "completed"
        self.end_time = time.time()
        self.result = result
        self.error_message = None

    def fail_execution(self, error_msg: str) -> None:
        if self.status != "running":
            raise ValueError("Step is not running")
        self.status = "failed"
        self.end_time = time.time()
        self.error_message = error_msg

    def get_duration(self) -> Optional[float]:
        if self.start_time is None or self.end_time is None:
            return None
        return self.end_time - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "name": self.name,
            "step_type": self.step_type,
            "parameters": self.parameters,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.get_duration(),
            "error_message": self.error_message,
            "result": self.result,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WorkflowStep":
        step = cls(
            d["step_id"],
            d["name"],
            d["step_type"],
            d.get("parameters", {}),
        )
        step.status = d.get("status", "pending")
        step.start_time = d.get("start_time")
        step.end_time = d.get("end_time")
        step.error_message = d.get("error_message")
        step.result = d.get("result")
        return step


class WorkflowSimulator:
    """
    A workflow is a list of :class:`WorkflowStep` with aggregate status
    and optional JSON persistence.
    """

    def __init__(self) -> None:
        self.workflow_id: str = _uid()
        self.steps: List[WorkflowStep] = []
        self.status: str = "pending"
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.error_message: Optional[str] = None

    def add_step(self, step: WorkflowStep) -> None:
        self.steps.append(step)

    def get_step_by_id(self, step_id: str) -> Optional[WorkflowStep]:
        for s in self.steps:
            if s.step_id == step_id:
                return s
        return None

    def get_steps_by_status(self, status: str) -> List[WorkflowStep]:
        return [s for s in self.steps if s.status == status]

    def get_workflow_progress(self) -> Dict[str, Any]:
        total = len(self.steps)
        if total == 0:
            return {
                "total_steps": 0,
                "completed_steps": 0,
                "failed_steps": 0,
                "pending_steps": 0,
                "running_steps": 0,
                "completion_percentage": 0.0,
            }
        by = {s: 0 for s in ("completed", "failed", "pending", "running")}
        for s in self.steps:
            st = s.status
            if st in by:
                by[st] += 1
        completed = by["completed"]
        return {
            "total_steps": total,
            "completed_steps": completed,
            "failed_steps": by["failed"],
            "pending_steps": by["pending"],
            "running_steps": by["running"],
            "completion_percentage": round(100.0 * completed / total, 2),
        }

    def start_workflow(self) -> None:
        if self.status not in ("pending",):
            return
        self.status = "running"
        self.start_time = time.time()
        self.error_message = None

    def complete_workflow(self) -> None:
        self.end_time = time.time()
        self.status = "completed"
        self.error_message = None

    def fail_workflow(self, message: str) -> None:
        self.end_time = time.time()
        self.status = "failed"
        self.error_message = message

    def get_workflow_duration(self) -> Optional[float]:
        if self.start_time is None or self.end_time is None:
            return None
        return self.end_time - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "status": self.status,
            "steps": [s.to_dict() for s in self.steps],
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.get_workflow_duration(),
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WorkflowSimulator":
        w = cls()
        w.workflow_id = d.get("workflow_id", w.workflow_id)
        w.status = d.get("status", "pending")
        w.start_time = d.get("start_time")
        w.end_time = d.get("end_time")
        w.error_message = d.get("error_message")
        w.steps = [WorkflowStep.from_dict(s) for s in d.get("steps", [])]
        return w

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str, indent=2)

    @classmethod
    def from_json(cls, js: str) -> "WorkflowSimulator":
        return cls.from_dict(json.loads(js))

    def save_to_file(self, file_path: str) -> bool:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.to_json())
        return True

    @classmethod
    def load_from_file(cls, file_path: str) -> "WorkflowSimulator":
        with open(file_path, encoding="utf-8") as f:
            return cls.from_json(f.read())


class WorkflowEngine:
    """Registry of :class:`WorkflowSimulator` runs."""

    def __init__(self, max_concurrent_workflows: int = 5) -> None:
        self.max_concurrent_workflows = max_concurrent_workflows
        self.workflows: Dict[str, WorkflowSimulator] = {}

    def create_workflow(self) -> str:
        w = WorkflowSimulator()
        self.workflows[w.workflow_id] = w
        return w.workflow_id

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowSimulator]:
        return self.workflows.get(workflow_id)

    def list_workflows(self) -> List[str]:
        return list(self.workflows.keys())

    def delete_workflow(self, workflow_id: str) -> bool:
        if workflow_id in self.workflows:
            del self.workflows[workflow_id]
            return True
        return False

    def get_workflow_status(self, workflow_id: str) -> str:
        w = self.get_workflow(workflow_id)
        if w is None:
            return "not_found"
        return w.status

    def get_workflow_progress(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        w = self.get_workflow(workflow_id)
        if w is None:
            return None
        return w.get_workflow_progress()
