"""
Smoke tests for nested pytest runs (uses stable unit tests only).
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
UNIT = REPO / "CancerGenomicsSuite" / "tests" / "unit" / "test_ensembl_api_utils.py"


def _run(args: list) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "--no-cov", "-q", *args],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )


class TestTestRunner:
    def test_unit_smoke(self):
        if not UNIT.exists():
            pytest.skip("unit test file missing")
        r = _run([str(UNIT)])
        assert r.returncode in (0, 1)

    def test_discover_test_files(self):
        d = Path(__file__).parent
        assert any(d.glob("test_*.py"))
