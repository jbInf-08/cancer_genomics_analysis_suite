"""`celery_worker` must expose the app, because that name is the worker entrypoint.

There is a ``celery_worker.py`` and a ``celery_worker/`` package side by side.
A package always wins over a module of the same name, so the ``celery`` defined
in the .py was never importable, and everything pointing at it failed:

* the seven task modules, each ``from celery_worker import celery`` -- which is
  how their ``@celery.task`` decorators attach;
* ``celery_config``'s ``include`` list, which imports those modules when the
  worker boots, so the worker could not start at all;
* ``celery -A celery_worker.celery worker`` in docker-compose.yml and in the
  k8s liveness and readiness probes, which would have restart-looped the pods.

These tests pin the entrypoint rather than the file layout, so they keep holding
if the .py is later removed or renamed.
"""

from __future__ import annotations

import importlib

import pytest

TASK_MODULES = [
    "data_processing",
    "expression_analysis",
    "integration_tasks",
    "md_workflow_tasks",
    "ml_prediction",
    "mutation_analysis",
    "reporting",
    "test_tasks",
]


def test_celery_worker_exposes_the_app():
    """The exact import all seven task modules perform."""
    from celery_worker import celery

    assert celery is not None
    assert hasattr(celery, "task"), "not a Celery app: no .task decorator"


def test_app_is_the_one_celery_config_builds():
    """It must be the configured app, not a fresh Celery()."""
    from celery_worker import celery

    from CancerGenomicsSuite.app.celery_config import celery_app

    assert celery is celery_app


@pytest.mark.parametrize("name", TASK_MODULES)
def test_each_task_module_imports(name):
    """celery_config's include= imports these at worker startup."""
    importlib.import_module(f"celery_worker.tasks.{name}")


def test_celery_dash_A_targets_resolve():
    """`celery -A <target>` resolution, as docker-compose and the probes use it.

    find_app is what the celery CLI calls, so this covers the deployed command
    rather than approximating it.
    """
    from celery.app.utils import find_app

    for target in ("celery_worker", "celery_worker.celery"):
        app = find_app(target)
        assert hasattr(app, "task"), f"-A {target} did not resolve to an app"


def test_include_list_matches_importable_modules():
    """Every module celery_config promises to load must actually load."""
    from CancerGenomicsSuite.app.celery_config import celery_app

    included = list(celery_app.conf.include or [])
    assert included, "celery_config declares no include list"
    for dotted in included:
        importlib.import_module(dotted)


def test_tasks_are_registered_after_importing_the_modules():
    from celery_worker import celery

    for name in TASK_MODULES:
        importlib.import_module(f"celery_worker.tasks.{name}")
    registered = [t for t in celery.tasks if not t.startswith("celery.")]
    assert registered, "no project tasks registered on the app"
