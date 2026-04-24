"""Basic configuration hygiene checks (complement static tools like bandit/safety)."""

import pytest

from CancerGenomicsSuite.config.settings import TestConfig


@pytest.mark.security
@pytest.mark.critical
def test_test_config_has_reasonable_secret_length():
    cfg = TestConfig()
    assert isinstance(cfg.SECRET_KEY, str)
    assert len(cfg.SECRET_KEY) >= 16
