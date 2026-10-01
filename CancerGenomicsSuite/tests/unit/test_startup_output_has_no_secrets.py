"""Starting the dashboard must not write secrets to its output.

main_dashboard.main() printed the whole settings object on every start. Its
repr includes security.secret_key (Flask session signing), oauth2's
jwt_secret_key and service passwords, so they went to stdout and from there to
container and gunicorn logs.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SUITE = REPO / "CancerGenomicsSuite"

FLASK_SECRET = "flask-secret-sentinel-3f9a"
JWT_SECRET = "jwt-secret-sentinel-7c21"


def test_main_prints_no_secrets(tmp_path):
    body = f"""
        import sys, warnings
        warnings.filterwarnings("ignore")
        sys.path.insert(0, {str(SUITE)!r})
        import main_dashboard as md
        assert md.settings.security.secret_key == {FLASK_SECRET!r}
        assert md.settings.oauth2.jwt_secret_key == {JWT_SECRET!r}
        md.app.run = lambda *a, **kw: print("RUN CALLED")
        md.main()
    """
    env = dict(os.environ, SECRET_KEY=FLASK_SECRET, JWT_SECRET_KEY=JWT_SECRET)
    proc = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(body)],
        capture_output=True,
        text=True,
        timeout=900,
        env=env,
        cwd=tmp_path,
    )
    assert proc.returncode == 0, proc.stderr[-3000:]
    assert "RUN CALLED" in proc.stdout
    output = proc.stdout + proc.stderr
    assert FLASK_SECRET not in output
    assert JWT_SECRET not in output
