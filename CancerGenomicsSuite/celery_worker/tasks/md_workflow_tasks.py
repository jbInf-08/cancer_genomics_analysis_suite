"""
Celery tasks for molecular dynamics (GROMACS) workflows.

Queues long-running structure preparation and energy minimization off the
Dash web process. Requires a running Celery worker and compatible broker.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from celery_worker import celery

logger = logging.getLogger(__name__)


@celery.task(
    bind=True,
    name="celery_worker.tasks.md_workflow_tasks.run_md_workflow",
    time_limit=7200,
    soft_time_limit=7000,
)
def run_md_workflow(
    self,
    config: Dict[str, Any],
    workflow_name: str,
    work_dir: Optional[str] = None,
    history_persist_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run :meth:`WorkflowExecutor.run_molecular_dynamics_workflow` in a worker.

    Args:
        config: Passed through to :class:`MolecularDynamicsWorkflow`.
        workflow_name: Stable id for ``workflow_history`` / JSONL audit log.
        work_dir: Optional executor work directory (defaults to CWD/workflow_work).
        history_persist_path: Optional JSONL path (``None`` uses executor default).

    Returns:
        The MD workflow result dict (``success``, ``work_dir``, errors, etc.).
    """
    from CancerGenomicsSuite.modules.pipeline_orchestration.workflow_executor import (
        WorkflowExecutor,
    )

    self.update_state(
        state="PROGRESS",
        meta={"status": "starting_md", "workflow": workflow_name},
    )
    ex = WorkflowExecutor(
        work_dir=work_dir,
        history_persist_path=history_persist_path,
    )
    self.update_state(
        state="PROGRESS",
        meta={"status": "running_md", "workflow": workflow_name},
    )
    result = ex.run_molecular_dynamics_workflow(config, workflow_name=workflow_name)
    self.update_state(
        state="SUCCESS",
        meta={"status": "completed", "success": result.get("success"), "workflow": workflow_name},
    )
    logger.info("Celery MD task %s done: %s", workflow_name, result.get("success"))
    return result
