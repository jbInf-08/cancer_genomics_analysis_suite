"""Unit tests for BiomarkerGateway (mocked HTTP)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from CancerGenomicsSuite.integrations.biomarker_gateway import (
    BiomarkerGateway,
    ServiceType,
)


@patch("CancerGenomicsSuite.integrations.biomarker_gateway.CGAS_AVAILABLE", False)
@patch("CancerGenomicsSuite.integrations.biomarker_gateway.requests.get")
def test_biomark_remote_health_200(mock_get, monkeypatch):
    r = MagicMock()
    r.status_code = 200
    mock_get.return_value = r
    g = BiomarkerGateway(
        {
            "biomarker_identifier_url": "http://test.example:9999",
            "timeout": 2,
        }
    )
    assert g.service_status[ServiceType.BIOMARKER_IDENTIFIER].available is True
    h = g.health_check()
    assert h["ready"] is True
    assert h["any_available"] is True
    assert "biomarker_identifier" in h["services"]


@patch("CancerGenomicsSuite.integrations.biomarker_gateway.CGAS_AVAILABLE", False)
@patch("CancerGenomicsSuite.integrations.biomarker_gateway.requests.get")
@patch("CancerGenomicsSuite.integrations.biomarker_gateway.requests.post")
def test_route_to_biomark_identifier_post(mock_post, mock_get, monkeypatch):
    mock_get.return_value = MagicMock(status_code=200)
    mock_post.return_value = MagicMock(
        status_code=200, json=lambda: {"biomarkers": [], "ok": True}
    )
    g = BiomarkerGateway(
        {"biomarker_identifier_url": "http://test.example:9999", "timeout": 2}
    )
    out = g._route_to_biomarker_identifier("discover", {"data": {}}, {})
    assert out.get("ok") is True
    assert mock_post.called


@patch("CancerGenomicsSuite.integrations.biomarker_gateway.CGAS_AVAILABLE", False)
@patch(
    "CancerGenomicsSuite.integrations.biomarker_gateway.requests.get",
    side_effect=OSError("down"),
)
def test_biomark_remote_unavailable(mock_get, monkeypatch):
    g = BiomarkerGateway({"biomarker_identifier_url": "http://nope", "timeout": 1})
    st = g.service_status.get(ServiceType.BIOMARKER_IDENTIFIER)
    assert st is not None
    assert st.available is False
    h = g.health_check()
    assert h["ready"] is False


@patch("CancerGenomicsSuite.integrations.biomarker_gateway.CGAS_AVAILABLE", False)
@patch("CancerGenomicsSuite.integrations.biomarker_gateway.requests.get")
def test_no_services_available_raises_on_route(mock_get, monkeypatch):
    mock_get.side_effect = OSError("down")
    g = BiomarkerGateway({"biomarker_identifier_url": "http://nope", "timeout": 1})
    with pytest.raises(
        RuntimeError, match="No biomarker analysis services are available"
    ):
        g.route_request("x", {"data": []}, {})
