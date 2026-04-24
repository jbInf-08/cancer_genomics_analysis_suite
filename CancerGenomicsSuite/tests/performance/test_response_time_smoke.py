"""Lightweight timing smoke tests (in-process; not a load benchmark)."""

import time

import pytest

from CancerGenomicsSuite.app import create_app
from CancerGenomicsSuite.config.settings import TestConfig


@pytest.mark.performance
def test_health_endpoint_responds_quickly():
    app = create_app(TestConfig())
    client = app.test_client()
    start = time.perf_counter()
    rv = client.get("/health")
    elapsed = time.perf_counter() - start
    assert rv.status_code == 200
    assert elapsed < 5.0, "health check took unexpectedly long"
