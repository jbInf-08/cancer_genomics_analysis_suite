"""Tests for Ensembl HTTP helpers and error payloads."""

import json
from unittest.mock import MagicMock, patch

from CancerGenomicsSuite.modules.gene_annotation.ensembl_api_utils import (
    build_ensembl_error_payload,
    ensembl_rest_base,
    http_get_with_errors,
    http_post_json,
    parse_retry_after,
    safe_response_json_list,
)


def test_ensembl_rest_base_hg19():
    assert "grch37" in ensembl_rest_base("hg19")


def test_parse_retry_after():
    r = MagicMock()
    r.headers = {"Retry-After": "120"}
    assert parse_retry_after(r) == 120


def test_http_get_429():
    resp = MagicMock()
    resp.ok = False
    resp.status_code = 429
    resp.reason = "Too Many Requests"
    resp.url = "https://rest.ensembl.org/overlap/region/human/1:1-100?feature=gene"
    resp.text = "rate limit"
    resp.headers = {"Retry-After": "60"}

    with patch(
        "CancerGenomicsSuite.modules.gene_annotation.ensembl_api_utils.requests.get",
        return_value=resp,
    ):
        out, err = http_get_with_errors(
            resp.url,
            headers={"User-Agent": "test"},
            timeout=5,
        )
    assert out is None
    assert err is not None
    assert err["error_kind"] == "http_error"
    assert err["retry_after_seconds"] == 60
    assert "429" in err["user_message"] or "rate" in err["user_message"].lower()


def test_safe_response_json_list_invalid_json():
    resp = MagicMock()
    resp.status_code = 200
    resp.url = "http://example"
    resp.json.side_effect = json.JSONDecodeError("bad json", "", 0)
    resp.text = "not json"
    data, err = safe_response_json_list(resp)
    assert data == []
    assert err and err["error_kind"] == "json_decode"


def test_http_post_json_ok():
    resp = MagicMock()
    resp.ok = True
    resp.status_code = 200
    resp.url = "https://rest.ensembl.org/vep/human/region"
    resp.text = "{}"
    with patch(
        "CancerGenomicsSuite.modules.gene_annotation.ensembl_api_utils.requests.post",
        return_value=resp,
    ):
        out, err = http_post_json(
            resp.url,
            json_body={"variants": ["17 43094695 . G A"]},
            headers={"Content-Type": "application/json"},
            timeout=5,
        )
    assert err is None
    assert out is resp


def test_http_post_json_400():
    resp = MagicMock()
    resp.ok = False
    resp.status_code = 400
    resp.reason = "Bad Request"
    resp.url = "https://rest.ensembl.org/vep/human/region"
    resp.text = "bad"
    with patch(
        "CancerGenomicsSuite.modules.gene_annotation.ensembl_api_utils.requests.post",
        return_value=resp,
    ):
        out, err = http_post_json(
            resp.url,
            json_body={"variants": []},
            headers={"User-Agent": "test"},
            timeout=5,
        )
    assert out is None
    assert err and err["error_kind"] == "http_error"


def test_build_ensembl_error_payload_shape():
    p = build_ensembl_error_payload(
        kind="test",
        status_code=500,
        url="http://x",
        message="fail",
    )
    assert p["error_kind"] == "test"
    assert p["user_message"]
