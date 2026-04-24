"""Optional Celery result-backend polling for long-running MD workflow tasks."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional, Tuple

from dash import html

from CancerGenomicsSuite.modules.pipeline_orchestration.md_workflow_dash_display import (
    md_workflow_result_to_div,
)

logger = logging.getLogger(__name__)

# Stop polling after this wall-clock time (seconds) from task submit.
_DEFAULT_MAX_POLL_SECONDS = 45 * 60


def get_celery_app():
    """Return the suite Celery app, or None if import fails (Dash without worker on path)."""
    try:
        from celery_worker import celery as app  # type: ignore

        return app
    except Exception as e:  # pragma: no cover - import path varies
        logger.debug("Celery app not importable: %s", e)
        return None


def poll_md_async_result(
    task_id: str,
    workflow_name: str,
    *,
    structured_error_to_dash: Any,
    started_monotonic: Optional[float] = None,
    max_poll_seconds: float = _DEFAULT_MAX_POLL_SECONDS,
) -> Tuple[html.Div, bool]:
    """
    Read task state from the result backend and return UI + whether polling should stop.

    Returns:
        (children_div, stop_polling)
    """
    app = get_celery_app()
    if app is None:
        return (
            html.Div(
                [
                    html.P(
                        "Cannot import Celery app to poll task status. "
                        "Check PYTHONPATH and celery_worker package.",
                        className="error-message",
                    ),
                    html.P(["Task id: ", html.Code(task_id, style={"wordBreak": "break-all"})]),
                ]
            ),
            True,
        )

    if started_monotonic is not None and (time.monotonic() - started_monotonic) > max_poll_seconds:
        return (
            html.Div(
                [
                    html.P(
                        "Stopped polling after the configured time limit. "
                        "The worker may still be running — check Flower or worker logs.",
                        className="error-message",
                    ),
                    html.P(["Task id: ", html.Code(task_id, style={"wordBreak": "break-all"})]),
                    html.P(f"Workflow: {workflow_name}", style={"fontSize": "0.95em"}),
                ]
            ),
            True,
        )

    try:
        from celery.result import AsyncResult
    except Exception as e:  # pragma: no cover
        return (
            html.Div(
                [
                    html.P(f"Celery AsyncResult unavailable: {e}", className="error-message"),
                    html.P(["Task id: ", html.Code(task_id, style={"wordBreak": "break-all"})]),
                ]
            ),
            True,
        )

    ar = AsyncResult(task_id, app=app)
    state = ar.state or "UNKNOWN"
    info = ar.info
    meta: Dict[str, Any] = info if isinstance(info, dict) else {}

    if state == "PENDING":
        body = [
            html.P([html.Strong("Celery task queued (PENDING)")]),
            html.P(["Task id: ", html.Code(task_id, style={"wordBreak": "break-all"})]),
            html.P(f"Workflow: {workflow_name}", style={"fontSize": "0.95em"}),
        ]
        return html.Div(body), False

    if state == "PROGRESS":
        status = meta.get("status", "running")
        body = [
            html.P([html.Strong("Celery task in progress")]),
            html.P(["State: ", html.Code(state)]),
            html.P(["Meta: ", html.Code(str(meta)[:800], style={"wordBreak": "break-all"})]),
            html.P(["Task id: ", html.Code(task_id, style={"wordBreak": "break-all"})]),
            html.P(f"Workflow: {workflow_name}", style={"fontSize": "0.95em"}),
            html.P(f"Worker status: {status}", style={"fontSize": "0.9em"}),
        ]
        return html.Div(body), False

    if ar.successful():
        try:
            result = ar.result
        except Exception as e:  # pragma: no cover - backend / deserial edge cases
            logger.warning("Could not read Celery task result for %s: %s", task_id, e)
            return (
                html.Div(
                    [
                        html.P(
                            f"Task reported success but the result could not be read: {e}",
                            className="error-message",
                        ),
                        html.P(["Task id: ", html.Code(task_id, style={"wordBreak": "break-all"})]),
                    ]
                ),
                True,
            )
        if not isinstance(result, dict):
            result = {"success": False, "error": f"Unexpected result type: {type(result).__name__}"}
        return (
            md_workflow_result_to_div(result, workflow_name, structured_error_to_dash),
            True,
        )

    if ar.failed():
        err = str(ar.result) if ar.result is not None else "unknown error"
        tb = ""
        try:
            tb = str(ar.traceback or "")[:3000]
        except Exception:
            pass
        return (
            html.Div(
                [
                    html.P([html.Strong("Celery task failed"), f" ({state})"]),
                    html.P(["Task id: ", html.Code(task_id, style={"wordBreak": "break-all"})]),
                    html.P(err, className="error-message"),
                    html.Pre(tb, className="export-data") if tb else html.Div(),
                ]
            ),
            True,
        )

    # REVOKED, RETRY, etc.
    return (
        html.Div(
            [
                html.P([html.Strong("Celery task finished"), f" — state {state}"]),
                html.P(["Task id: ", html.Code(task_id, style={"wordBreak": "break-all"})]),
                html.Pre(str(info)[:2000], className="export-data"),
            ]
        ),
        True,
    )
