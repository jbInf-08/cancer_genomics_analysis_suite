"""Neither cloud SDK may be required to import cloud_storage, or to use the other.

gcs_client imported google-cloud-storage unconditionally and the package
__init__ imports gcs_client first, so without the Google SDK nothing in
cloud_storage loaded -- not the S3 client, and not base_storage, which uses no
third-party package at all. An AWS-only deployment could not reach its own
storage client. Neither SDK was declared as a dependency either.

The blocked-SDK cases run in a subprocess: blocking an import means replacing
sys.modules entries and re-importing the package, which must not leak into the
rest of the test session.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
PKG = "CancerGenomicsSuite.modules.cloud_storage"


def _run(blocked: list[str], body: str) -> subprocess.CompletedProcess:
    """Run `body` in a fresh interpreter with the given modules made unimportable."""
    prelude = "import sys, warnings\nwarnings.filterwarnings('ignore')\n"
    prelude += f"sys.path.insert(0, {str(REPO)!r})\n"
    for name in blocked:
        prelude += f"sys.modules[{name!r}] = None\n"
    return subprocess.run(
        [sys.executable, "-c", prelude + textwrap.dedent(body)],
        capture_output=True,
        text=True,
        timeout=300,
    )


GOOGLE = ["google.cloud", "google.cloud.storage", "google.cloud.exceptions"]
BOTO = ["boto3", "botocore", "botocore.exceptions"]


def test_package_imports_and_reports_availability():
    import importlib

    cs = importlib.import_module(PKG)
    assert isinstance(cs.S3_AVAILABLE, bool)
    assert isinstance(cs.GCS_AVAILABLE, bool)


def test_everything_imports_with_neither_sdk():
    proc = _run(
        GOOGLE + BOTO,
        f"""
        import importlib
        for m in ["", ".base_storage", ".s3_client", ".gcs_client", ".storage_factory"]:
            importlib.import_module("{PKG}" + m)
        import {PKG} as cs
        assert cs.S3_AVAILABLE is False and cs.GCS_AVAILABLE is False
        print("ok")
        """,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "ok" in proc.stdout


def test_s3_client_works_without_the_google_sdk():
    """The case that was actually broken for an AWS-only install."""
    pytest.importorskip("boto3")
    proc = _run(
        GOOGLE,
        f"""
        from {PKG} import StorageFactory, S3_AVAILABLE, GCS_AVAILABLE
        assert S3_AVAILABLE and not GCS_AVAILABLE
        client = StorageFactory.create_storage_client("s3", bucket_name="b", region="us-west-2")
        print(type(client).__name__, client.bucket.name)
        """,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "S3StorageClient b" in proc.stdout


@pytest.mark.parametrize(
    ("blocked", "provider", "extra"),
    [(GOOGLE, "gcs", "[gcs]"), (BOTO, "s3", "[s3]")],
)
def test_missing_sdk_is_reported_at_construction_with_the_extra(
    blocked, provider, extra
):
    proc = _run(
        blocked,
        f"""
        from {PKG} import StorageFactory
        try:
            StorageFactory.create_storage_client("{provider}", bucket_name="b")
        except ImportError as exc:
            print("IMPORTERROR:", exc)
        else:
            print("CONSTRUCTED")
        """,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "IMPORTERROR:" in proc.stdout
    assert extra in proc.stdout, "the message should name the extra to install"


@pytest.mark.parametrize(
    ("blocked", "module", "names"),
    [
        (GOOGLE, "gcs_client", ["GoogleCloudError", "NotFound"]),
        (BOTO, "s3_client", ["ClientError", "NoCredentialsError"]),
    ],
)
def test_stand_in_exceptions_are_not_catch_alls(blocked, module, names):
    """Aliasing them to Exception would make every except clause catch everything."""
    proc = _run(
        blocked,
        f"""
        import {PKG}.{module} as m
        for name in {names!r}:
            cls = getattr(m, name)
            assert cls is not Exception, name
            assert not issubclass(ValueError, cls), name
        print("ok")
        """,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "ok" in proc.stdout
