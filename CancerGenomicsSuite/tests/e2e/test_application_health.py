"""End-to-end style checks using the in-process test client (no live server)."""

import pytest

from CancerGenomicsSuite.app import create_app
from CancerGenomicsSuite.config.settings import TestConfig


@pytest.mark.e2e
@pytest.mark.critical
def test_application_health_workflow():
    app = create_app(TestConfig())
    client = app.test_client()
    health = client.get("/health")
    assert health.status_code == 200
    status = client.get("/api/status")
    assert status.status_code == 200
    body = status.get_json()
    assert body is not None
    assert "status" in body
