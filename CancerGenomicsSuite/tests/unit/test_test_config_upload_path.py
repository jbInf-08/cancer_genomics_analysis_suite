"""Tests for TestConfig upload path behavior under pytest."""

import os

import pytest

from CancerGenomicsSuite.config.settings import TestConfig


def test_test_config_upload_folder_stable_when_env_set():
    root = os.environ.get("CGAS_TEST_UPLOAD_FOLDER")
    if not root:
        pytest.skip("Expected CGAS_TEST_UPLOAD_FOLDER from session autouse fixture")
    first = TestConfig().UPLOAD_FOLDER
    second = TestConfig().UPLOAD_FOLDER
    assert first == second == os.path.abspath(root)
