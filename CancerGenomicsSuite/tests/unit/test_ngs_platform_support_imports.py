"""The NGS platform package must import, along with the pipeline module it exports.

ngs_pipeline_integration.py sat at modules/ while everything that used it
expected modules/ngs_platform_support/ -- the package __init__ imported it as
``.ngs_pipeline_integration``, its own ``from .workflow_dispatcher import`` only
resolves from inside that package, and INTEGRATION_UPDATES.md documents it
there. It had been that way since the first commit, so the whole
ngs_platform_support package failed to import, taking pacbio_pipeline and
workflow_dispatcher with it, and the pipeline module itself could not load
where it stood.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

PACKAGE = "CancerGenomicsSuite.modules.ngs_platform_support"

EXPORTED_BY_PIPELINE_MODULE = [
    "EnhancedWorkflowDispatcher",
    "NGSPipelineManager",
    "PipelineDefinition",
    "PipelineExecution",
    "PipelineStatus",
    "PipelineStep",
    "PipelineStepExecutor",
    "PipelineType",
    "PipelineValidator",
]


def test_package_imports():
    importlib.import_module(PACKAGE)


@pytest.mark.parametrize(
    "submodule",
    [
        "ngs_pipeline_integration",
        "workflow_dispatcher",
        "pacbio_pipeline",
        "illumina_pipeline",
        "nanopore_pipeline",
        "ion_torrent_pipeline",
        "common_preprocessing",
    ],
)
def test_each_submodule_imports(submodule):
    importlib.import_module(f"{PACKAGE}.{submodule}")


@pytest.mark.parametrize("name", EXPORTED_BY_PIPELINE_MODULE)
def test_package_reexports_the_pipeline_names(name):
    pkg = importlib.import_module(PACKAGE)
    assert hasattr(pkg, name), f"{PACKAGE} does not export {name}"


def test_pipeline_module_lives_inside_the_package():
    """Pin the location the docs and the package __init__ both rely on."""
    modules_dir = Path(__file__).resolve().parents[2] / "modules"
    assert (
        modules_dir / "ngs_platform_support" / "ngs_pipeline_integration.py"
    ).is_file()
    assert not (modules_dir / "ngs_pipeline_integration.py").exists(), (
        "a copy at modules/ would shadow nothing and import nothing -- "
        "it is the misplaced original"
    )
