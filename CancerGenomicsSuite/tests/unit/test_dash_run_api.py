"""Dash apps are started with app.run; app.run_server no longer exists.

Dash removed run_server in 3.0. Since then it is an obsolete attribute that
raises "app.run_server has been replaced by app.run". pyproject does not cap
dash, so CI installs 4.x, where main_dashboard.main() -- the `cancer-genomics`
console script -- failed the moment it tried to start the server. So did the
standalone entry point of every dashboard that has one. app.run exists across
the whole supported range (dash>=2.15), so the old name buys nothing.

biomarker_dashboard and drug_dashboard define their own run_server methods on
their wrapper classes; those are this project's API and stay. Only calls on a
Dash app (`app.run_server(` / `self.app.run_server(`) are rejected.
"""

from __future__ import annotations

import ast
import subprocess
import sys
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SUITE = REPO / "CancerGenomicsSuite"


def _is_app(node: ast.expr) -> bool:
    return (isinstance(node, ast.Name) and node.id == "app") or (
        isinstance(node, ast.Attribute) and node.attr == "app"
    )


def test_no_dash_app_calls_run_server():
    offenders = []
    for path in SUITE.rglob("*.py"):
        if "tests" in path.relative_to(SUITE).parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "run_server"
                and _is_app(node.func.value)
            ):
                offenders.append(f"{path.relative_to(REPO)}:{node.lineno}")
    assert not offenders, "use app.run, not app.run_server:\n  " + "\n  ".join(
        offenders
    )


def test_main_dashboard_main_starts_the_server_with_settings():
    """The console-script entry point reaches app.run with the configured values.

    Runs in a subprocess: importing main_dashboard loads every plugin and needs
    the suite directory on sys.path, as when the app is started for real.
    """
    body = f"""
        import sys, warnings, io, contextlib
        warnings.filterwarnings("ignore")
        sys.path.insert(0, {str(SUITE)!r})
        with contextlib.redirect_stdout(io.StringIO()):
            import main_dashboard as md
        calls = []
        md.app.run = lambda *a, **kw: calls.append(kw)
        with contextlib.redirect_stdout(io.StringIO()):
            md.main()
        s = md.settings
        assert calls == [dict(debug=s.dash_debug_mode, host=s.host, port=s.port)], calls
        print("ok")
    """
    proc = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(body)],
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stderr[-3000:]
    assert proc.stdout.strip().endswith("ok")
