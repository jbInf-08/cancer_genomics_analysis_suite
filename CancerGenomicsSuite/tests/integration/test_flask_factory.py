"""Integration tests for the Flask application factory and core HTTP routes."""

import pytest

from CancerGenomicsSuite.app import create_app
from CancerGenomicsSuite.config.settings import TestConfig


@pytest.mark.integration
@pytest.mark.critical
def test_create_app_with_test_config():
    app = create_app(TestConfig())
    assert app is not None
    assert app.config.get("TESTING") is True


@pytest.mark.integration
@pytest.mark.critical
def test_health_endpoint_json():
    app = create_app(TestConfig())
    client = app.test_client()
    rv = client.get("/health")
    assert rv.status_code == 200
    data = rv.get_json()
    assert data is not None
    assert data.get("status") == "healthy"
