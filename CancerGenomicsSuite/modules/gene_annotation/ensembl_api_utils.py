"""
Shared Ensembl REST helpers: host selection per assembly, HTTP error shaping,
and safe JSON parsing for dashboards and predictors.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# Primary GRCh38 service; use GRCh37 host for hg19 coordinates.
REFERENCE_TO_ENSEMBL_BASE: Dict[str, str] = {
    "hg38": "https://rest.ensembl.org",
    "hg19": "https://grch37.rest.ensembl.org",
    "mm10": "https://rest.ensembl.org",
    "mm9": "https://rest.ensembl.org",
    "dm6": "https://rest.ensembl.org",
    "ce11": "https://rest.ensembl.org",
}

REFERENCE_TO_SPECIES: Dict[str, str] = {
    "hg38": "human",
    "hg19": "human",
    "mm10": "mouse",
    "mm9": "mouse",
    "dm6": "drosophila_melanogaster",
    "ce11": "caenorhabditis_elegans",
}


def ensembl_rest_base(reference_genome: str) -> str:
    ref = (reference_genome or "hg38").lower()
    return REFERENCE_TO_ENSEMBL_BASE.get(ref, "https://rest.ensembl.org")


def species_for_reference(reference_genome: str) -> str:
    ref = (reference_genome or "hg38").lower()
    if ref not in REFERENCE_TO_SPECIES:
        logger.warning("Unknown reference %s; defaulting to human", reference_genome)
        return "human"
    return REFERENCE_TO_SPECIES[ref]


def parse_retry_after(response: requests.Response) -> Optional[int]:
    raw = response.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return int(float(raw))
    except ValueError:
        return None


def build_ensembl_error_payload(
    *,
    kind: str,
    status_code: Optional[int],
    url: str,
    message: str,
    response_text_snippet: str = "",
    retry_after: Optional[int] = None,
) -> Dict[str, Any]:
    snippet = (response_text_snippet or "")[:800]
    user = message
    if status_code == 429:
        user = (
            "Ensembl rate limit (HTTP 429). Wait and retry; reduce request frequency. "
            f"{message}"
        )
    elif status_code == 503:
        user = (
            "Ensembl service unavailable (HTTP 503). Retry later. "
            f"{message}"
        )
    elif status_code in (400, 404):
        user = (
            "Ensembl rejected the request (bad region, species, or assembly). "
            f"{message}"
        )
    return {
        "error": True,
        "error_kind": kind,
        "error_code": status_code,
        "message": message,
        "user_message": user,
        "url": url,
        "response_snippet": snippet,
        "retry_after_seconds": retry_after,
        "source": "ensembl",
    }


def safe_response_json_list(response: requests.Response) -> Tuple[List[Any], Optional[Dict[str, Any]]]:
    """
    Parse JSON body expected to be a list (overlap/region). On failure return ([], error_payload).
    """
    try:
        data = response.json()
    except (json.JSONDecodeError, ValueError) as e:
        err = build_ensembl_error_payload(
            kind="json_decode",
            status_code=response.status_code,
            url=response.url,
            message=f"Invalid JSON from Ensembl: {e}",
            response_text_snippet=response.text,
            retry_after=parse_retry_after(response),
        )
        return [], err
    if isinstance(data, dict) and "error" in data:
        err = build_ensembl_error_payload(
            kind="ensembl_api_error",
            status_code=response.status_code,
            url=response.url,
            message=str(data.get("error")),
            response_text_snippet=response.text,
            retry_after=parse_retry_after(response),
        )
        return [], err
    if not isinstance(data, list):
        err = build_ensembl_error_payload(
            kind="unexpected_shape",
            status_code=response.status_code,
            url=response.url,
            message=f"Expected JSON list, got {type(data).__name__}",
            response_text_snippet=response.text[:800],
            retry_after=parse_retry_after(response),
        )
        return [], err
    return data, None


def http_get_with_errors(
    url: str,
    *,
    headers: Dict[str, str],
    timeout: int,
    params: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[requests.Response], Optional[Dict[str, Any]]]:
    """
    Perform GET; on failure return (None, error_payload). Caller should not read resp if error.
    """
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
    except requests.Timeout as e:
        return None, build_ensembl_error_payload(
            kind="timeout",
            status_code=None,
            url=url,
            message=f"Request timed out after {timeout}s: {e}",
        )
    except requests.RequestException as e:
        return None, build_ensembl_error_payload(
            kind="network",
            status_code=None,
            url=url,
            message=str(e),
        )
    if not resp.ok:
        return None, build_ensembl_error_payload(
            kind="http_error",
            status_code=resp.status_code,
            url=resp.url,
            message=resp.reason or "HTTP error",
            response_text_snippet=resp.text,
            retry_after=parse_retry_after(resp),
        )
    return resp, None


def http_post_json(
    url: str,
    *,
    json_body: Any,
    headers: Dict[str, str],
    timeout: int,
) -> Tuple[Optional[requests.Response], Optional[Dict[str, Any]]]:
    """POST JSON body; on failure return (None, error_payload)."""
    try:
        resp = requests.post(
            url,
            json=json_body,
            headers=headers,
            timeout=timeout,
        )
    except requests.Timeout as e:
        return None, build_ensembl_error_payload(
            kind="timeout",
            status_code=None,
            url=url,
            message=f"POST timed out after {timeout}s: {e}",
        )
    except requests.RequestException as e:
        return None, build_ensembl_error_payload(
            kind="network",
            status_code=None,
            url=url,
            message=str(e),
        )
    if not resp.ok:
        return None, build_ensembl_error_payload(
            kind="http_error",
            status_code=resp.status_code,
            url=resp.url,
            message=resp.reason or "HTTP error",
            response_text_snippet=resp.text,
            retry_after=parse_retry_after(resp),
        )
    return resp, None


def sanitize_uniprot_accession(raw: str) -> Optional[str]:
    s = (raw or "").strip().upper()
    if not s:
        return None
    if re.match(r"^[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$", s):
        return s
    return None
