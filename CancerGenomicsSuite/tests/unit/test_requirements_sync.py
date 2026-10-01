"""requirements.txt must stay a pinned image of what pyproject.toml declares.

pyproject.toml is what CI installs and tests. CancerGenomicsSuite/requirements.txt
is what the compose image (CancerGenomicsSuite/Dockerfile) installs and what the
dependency audit in security.yml scans. The two drifted apart:

- pyproject's security floors (cryptography, gunicorn, lightgbm, pillow,
  python-jose, nltk) were raised, while requirements.txt kept the vulnerable pins;
- requirements.txt pinned versions that were never published (py2neo 2021.2.3,
  bioblend 3.2.0, neptune 1.8.15, pymol-open-source 2.5.0), so it could not be
  installed at all -- the compose build failed, and pip-audit, unable to resolve
  it, fell back to an empty report every run;
- it listed `matlab`, an unrelated PyPI project, not MathWorks' engine.

These checks are offline. Whether each pin exists on PyPI is left to the
audit step, which now fails when it cannot resolve the file.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from packaging.requirements import Requirement

try:
    import tomllib
except ImportError:  # Python < 3.11
    tomllib = pytest.importorskip("tomli")

REPO = Path(__file__).resolve().parents[3]
PYPROJECT = REPO / "pyproject.toml"
REQUIREMENTS = REPO / "CancerGenomicsSuite" / "requirements.txt"
SELF = "cancer-genomics-analysis-suite"


def _canon(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _pyproject():
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    core = {
        _canon(Requirement(r).name): Requirement(r) for r in project["dependencies"]
    }
    extras: dict[str, list[Requirement]] = {}
    for reqs in project["optional-dependencies"].values():
        for r in reqs:
            req = Requirement(r)
            if _canon(req.name) != SELF:
                extras.setdefault(_canon(req.name), []).append(req)
    return core, extras


def _requirements() -> list[Requirement]:
    reqs = []
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            reqs.append(Requirement(line))
    return reqs


def _pinned_version(req: Requirement) -> str:
    (spec,) = req.specifier
    return spec.version


def test_every_requirement_is_an_exact_pin_listed_once():
    seen = set()
    for req in _requirements():
        specs = list(req.specifier)
        assert (
            len(specs) == 1 and specs[0].operator == "=="
        ), f"{req} is not an exact pin"
        assert _canon(req.name) not in seen, f"{req.name} is pinned twice"
        seen.add(_canon(req.name))


def test_every_core_dependency_is_pinned():
    core, _ = _pyproject()
    pinned = {_canon(r.name) for r in _requirements()}
    missing = sorted(core[n].name for n in core if n not in pinned)
    assert not missing, f"core dependencies missing from requirements.txt: {missing}"


def test_nothing_is_pinned_that_pyproject_does_not_declare():
    core, extras = _pyproject()
    undeclared = sorted(
        r.name
        for r in _requirements()
        if _canon(r.name) not in core and _canon(r.name) not in extras
    )
    assert (
        not undeclared
    ), f"pinned in requirements.txt but not declared in pyproject.toml: {undeclared}"


def test_every_pin_satisfies_the_pyproject_specifier():
    """A pin below a floor means the compose image ships what pyproject ruled out."""
    core, extras = _pyproject()
    violations = []
    for req in _requirements():
        n = _canon(req.name)
        version = _pinned_version(req)
        declared = [core[n]] if n in core else extras.get(n, [])
        for dep in declared:
            if not dep.specifier.contains(version, prereleases=True):
                violations.append(f"{req.name}=={version} vs pyproject {dep}")
    assert not violations, "pins outside pyproject's range:\n  " + "\n  ".join(
        violations
    )


def test_pins_keep_the_extras_pyproject_asks_for():
    """e.g. python-jose[cryptography]: dropping the extra changes what gets installed."""
    core, _ = _pyproject()
    lost = []
    for req in _requirements():
        dep = core.get(_canon(req.name))
        if dep is not None and not dep.extras <= req.extras:
            lost.append(f"{req} lacks {sorted(dep.extras - req.extras)}")
    assert not lost, lost
