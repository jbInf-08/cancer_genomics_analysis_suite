"""Shared Dash/HTML rendering for WorkflowExecutor MD workflow results."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from dash import html


def md_workflow_result_to_div(
    result: Dict[str, Any],
    workflow_name: str,
    structured_error_to_dash: Callable[[Dict[str, Any]], Any],
) -> html.Div:
    """Build a summary :class:`html.Div` from an MD workflow result dict."""
    ok = result.get("success")
    lines: List[Any] = [
        html.P(
            [
                html.Strong("Status: "),
                "completed" if ok else "failed",
            ]
        ),
        html.P(
            [
                html.Strong("Workflow log ID: "),
                workflow_name,
                " (JSONL if persistence enabled — see docs)",
            ]
        ),
    ]
    if result.get("structure_source"):
        lines.append(
            html.P([html.Strong("Structure source: "), result["structure_source"]])
        )
    if result.get("resolved_uniprot"):
        lines.append(
            html.P(
                [
                    html.Strong("Resolved UniProt: "),
                    result["resolved_uniprot"],
                ]
            )
        )
    if result.get("force_field"):
        lines.append(html.P([html.Strong("Force field: "), result["force_field"]]))
    if result.get("work_dir"):
        lines.append(html.P([html.Strong("Work directory: "), result["work_dir"]]))
    if result.get("error_detail"):
        lines.append(structured_error_to_dash(result["error_detail"]))
    if result.get("error"):
        lines.append(
            html.Pre(
                str(result.get("error"))[:4000],
                className="export-data",
            )
        )
    if result.get("hint"):
        lines.append(html.P([html.Strong("Hint: "), result["hint"]]))
    return html.Div(lines)
