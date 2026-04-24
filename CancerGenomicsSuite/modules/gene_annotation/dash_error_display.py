"""Dash ``html`` helpers for structured API error payloads (Ensembl, RCSB, etc.)."""

from __future__ import annotations

from typing import Any, Dict, List

from dash import html


def structured_error_to_dash(err: Dict[str, Any]) -> html.Div:
    """Render ``build_ensembl_error_payload`` / ``error_detail`` dicts in Dash."""
    msg = err.get("user_message") or err.get("message") or str(err)
    parts: List[Any] = [html.P(msg)]
    ra = err.get("retry_after_seconds")
    if ra is not None:
        parts.append(html.P(f"Retry after: {ra} s (from Retry-After header when provided)."))
    code = err.get("error_code") if err.get("error_code") is not None else err.get("http_status")
    if code is not None:
        parts.append(html.P(f"HTTP / status: {code}"))
    kind = err.get("error_kind")
    if kind:
        parts.append(html.P(f"Kind: {kind}", style={"fontSize": "0.9em"}))
    url = err.get("url")
    if url:
        parts.append(
            html.P(
                [html.Strong("URL: "), html.Code(url, style={"wordBreak": "break-all"})]
            )
        )
    snip = err.get("response_snippet")
    if snip:
        parts.append(html.Pre(str(snip)[:2500], className="export-data"))
    return html.Div(parts, className="error-message")
