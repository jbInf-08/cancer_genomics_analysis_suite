"""
Cancer Genomics Analysis Suite - Celery Worker Tasks

This package contains all Celery task definitions for distributed processing
in the cancer genomics analysis suite.

It also exposes the configured Celery application as ``celery``, because this
package is what the name ``celery_worker`` actually resolves to.

There is a ``celery_worker.py`` beside this directory that binds the same name.
A package always wins over a module of the same name, so that file is
unreachable as ``celery_worker`` and the ``celery`` it defines was never
importable. Everything that referred to it broke:

* the seven task modules in ``tasks/``, each doing ``from celery_worker import
  celery``, which is how their ``@celery.task`` decorators are applied;
* ``celery_config``'s ``include`` list, which imports those task modules at
  worker startup, so the worker could not start;
* ``celery -A celery_worker.celery worker`` in docker-compose.yml, and the same
  invocation in the k8s liveness and readiness probes.

Defining it here rather than there is what makes those work, since this is the
module the name resolves to.
"""

import sys
from pathlib import Path

# Repo root on path so `CancerGenomicsSuite` resolves when not installed
# editable. Mirrors what celery_worker.py did, and is needed for the same
# reason: the worker is started from inside CancerGenomicsSuite/.
_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from CancerGenomicsSuite.app.celery_config import celery_app as celery  # noqa: E402

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite Team"

__all__ = ["celery"]
