"""Packages imported at module level must be declared, or the import made optional.

Four modules imported packages nothing declared: beautifulsoup4 and feedparser
(article scraper), lifelines (clinical data dashboard), pika and pyzmq
(interactive dashboards' live controls) and schedule (tasks/reporting_pipeline,
which tasks/__init__ imports). pyproject installs none of them, so in CI and in
the image built from pyproject those modules could not import; plugin_registry
catches the ImportError and only logs a warning. They imported only on machines
that happened to have the packages.

The MATLAB client imported the MATLAB engine unconditionally, which took the
MATLAB dashboard and cli_bioinformatics_tools down with it. The engine installs
only from a local MATLAB and cannot be declared, so it is optional instead.

Imports run in subprocesses: blocking a package means editing sys.modules, and
dashboards register callbacks at import; neither should leak into the session.
"""

from __future__ import annotations

import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from packaging.requirements import Requirement

try:
    import tomllib
except ImportError:  # Python < 3.11
    tomllib = pytest.importorskip("tomli")

REPO = Path(__file__).resolve().parents[3]
SUITE = REPO / "CancerGenomicsSuite"


def _run(body: str, blocked: tuple[str, ...] = ()) -> subprocess.CompletedProcess:
    """Run `body` with the repo on sys.path, and the suite dir as plugin_registry has it."""
    prelude = "import sys, warnings, logging\nwarnings.filterwarnings('ignore')\n"
    prelude += f"sys.path.insert(0, {str(REPO)!r})\n"
    prelude += f"sys.path.insert(0, {str(SUITE)!r})\n"
    for name in blocked:
        prelude += f"sys.modules[{name!r}] = None\n"
    return subprocess.run(
        [sys.executable, "-c", prelude + textwrap.dedent(body)],
        capture_output=True,
        text=True,
        timeout=600,
    )


def _core_dependencies() -> set[str]:
    project = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    return {
        re.sub(r"[-_.]+", "-", Requirement(r).name).lower()
        for r in project["project"]["dependencies"]
    }


@pytest.mark.parametrize(
    ("distribution", "imported_by"),
    [
        ("beautifulsoup4", "modules/article_scraper/scraper.py"),
        ("feedparser", "modules/article_scraper/scraper.py"),
        ("lifelines", "modules/clinical_data_dashboard/dashboard.py"),
        ("pika", "modules/interactive_dashboards/live_controls.py"),
        ("pyzmq", "modules/interactive_dashboards/live_controls.py"),
        ("schedule", "tasks/reporting_pipeline.py"),
    ],
)
def test_module_level_import_is_a_core_dependency(distribution, imported_by):
    assert (SUITE / imported_by).is_file(), imported_by
    assert distribution in _core_dependencies(), (
        f"{imported_by} imports {distribution} at module level, "
        "but pyproject.toml does not declare it"
    )


@pytest.mark.parametrize(
    "module",
    [
        "modules.article_scraper.scraper_dash",
        "modules.clinical_data_dashboard.clinical_dash",
        "modules.interactive_dashboards.dashboard_loader",
        # By its full name: reporting_pipeline imports ..reporting_engine.
        "CancerGenomicsSuite.tasks",
    ],
)
def test_module_imports(module):
    """In an environment built from pyproject -- CI -- these could not import.

    The dashboards are imported by the names plugin_registry uses.
    """
    proc = _run(f"import importlib; importlib.import_module({module!r}); print('ok')")
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert proc.stdout.strip().endswith("ok")


MATLAB_CHECK = """
    import importlib
    client_mod = importlib.import_module("modules.matlab_integration.matlab_client")
    assert client_mod.MATLAB_AVAILABLE is False
    client = client_mod.MATLABClient()
    assert client.engine is None and not client.is_available()
    result = client.execute_matlab_script("x = 1;")
    assert result["success"] is False, result
    importlib.import_module("modules.matlab_integration.matlab_dash")
    importlib.import_module("cli_bioinformatics_tools")
    print("ok")
"""


def test_matlab_modules_import_without_the_engine():
    proc = _run(MATLAB_CHECK, blocked=("matlab", "matlab.engine"))
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert proc.stdout.strip().endswith("ok")


def test_unrelated_matlab_package_is_not_mistaken_for_the_engine():
    """PyPI's `matlab` is an unrelated single-module project with no .engine."""
    fake = (
        "import types\n"
        "sys.modules['matlab'] = types.ModuleType('matlab')\n"
        "sys.modules.pop('matlab.engine', None)\n"
    )
    proc = _run(fake + textwrap.dedent(MATLAB_CHECK))
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert proc.stdout.strip().endswith("ok")
