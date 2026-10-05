"""Constructing RClient must not import R packages.

RClient() used to importr() fourteen Bioconductor/tidyverse packages
(BiocManager, Biobase, limma, edgeR, DESeq2, ..., clusterProfiler,
org.Hs.eg.db). r_dash builds a client at import, so every app start paid about
a minute for packages nothing used: each analysis's R code calls library() for
what it needs. On a machine where one of them was defunct (org.Hs.eg.db's
PFAM map), loading it took the whole process down. They are now loaded only by
preload_common_packages().

rpy2 is simulated (module attributes patched) in a subprocess with the real
rpy2 blocked, so no R is started.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

BODY = f"""
    import sys, logging
    logging.disable(logging.CRITICAL)
    sys.modules["rpy2"] = None
    sys.path.insert(0, {str(REPO)!r})
    from unittest import mock
    import CancerGenomicsSuite.modules.r_integration.r_client as rc

    importr = mock.Mock(side_effect=lambda name: f"pkg:{{name}}")
    robjects = mock.MagicMock()
    with mock.patch.object(rc, "RPY2_AVAILABLE", True), \\
         mock.patch.object(rc, "robjects", robjects), \\
         mock.patch.object(rc, "importr", importr):
        client = rc.RClient()
        assert client.rpy2_available, "simulated rpy2 should be used"
        assert importr.call_count == 0, importr.call_args_list
        assert client.packages == {{}}

        client.preload_common_packages()
        names = [c.args[0] for c in importr.call_args_list]
        assert "DESeq2" in names and "limma" in names, names
        assert client.packages["DESeq2"] == "pkg:DESeq2"
    print("ok")
"""


def test_constructing_rclient_imports_no_r_packages():
    proc = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(BODY)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr[-3000:]
    assert proc.stdout.strip().endswith("ok")
