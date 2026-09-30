"""The biomarker/drug REST APIs must be importable and reachable via `modules`.

biomarker_drug_api/__init__.py imported from `.api_models` and `.api_utils`,
neither of which has ever existed in this repository. The package therefore
could not import. modules/__init__.py catches that ImportError, sets all four
route factories to None and prints a warning -- so the four working API
blueprints in api_routes.py were silently unavailable, with nothing failing.

These tests check the outcome that was lost, not just the import: the factories
are real at the `modules` level and each yields a blueprint with routes.
"""

from __future__ import annotations

import pytest

FACTORIES = [
    "create_biomarker_api",
    "create_drug_api",
    "create_integration_api",
    "create_clinical_api",
]


def test_package_imports():
    import CancerGenomicsSuite.modules.biomarker_drug_api  # noqa: F401


def test_modules_package_reports_the_apis_available():
    import CancerGenomicsSuite.modules as modules

    assert modules._API_MODULES_AVAILABLE is True


@pytest.mark.parametrize("name", FACTORIES)
def test_factory_is_real_at_the_modules_level(name):
    """The failure mode was these being None, not missing."""
    import CancerGenomicsSuite.modules as modules

    assert callable(getattr(modules, name)), f"modules.{name} is not callable"


@pytest.mark.parametrize("name", FACTORIES)
def test_each_factory_registers_routes(name):
    flask = pytest.importorskip("flask")
    import CancerGenomicsSuite.modules.biomarker_drug_api as api

    app = flask.Flask("probe")
    before = len(list(app.url_map.iter_rules()))
    app.register_blueprint(getattr(api, name)())
    assert len(list(app.url_map.iter_rules())) > before, f"{name} added no routes"


def test_no_phantom_names_are_exported():
    """__all__ must list only names the package actually defines."""
    import CancerGenomicsSuite.modules.biomarker_drug_api as api

    missing = [n for n in api.__all__ if not hasattr(api, n)]
    assert not missing, f"__all__ advertises names that do not exist: {missing}"
