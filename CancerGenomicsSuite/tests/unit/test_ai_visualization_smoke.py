"""Smoke tests for the AI visualization module (optional heavy dependencies)."""

import importlib

import pandas as pd
import pytest


def _import_ai_visualization():
    """Import the module, skipping only when a third-party package is absent.

    These tests used to skip on any ImportError. That hid a real defect for as
    long as it existed: ai_data_processing imported sklearn's IterativeImputer
    without the experimental enabler scikit-learn requires, which raises a plain
    ImportError, and the suite reported it as "optional dependencies missing".

    A missing package raises ModuleNotFoundError naming that package, so skip on
    that alone -- and only when the missing module is not part of this project.
    Anything else, including a broken import inside our own code, fails.
    """
    try:
        return importlib.import_module(
            "CancerGenomicsSuite.modules.ai_integration.ai_visualization"
        )
    except ModuleNotFoundError as exc:
        missing = exc.name or ""
        if missing.split(".")[0] == "CancerGenomicsSuite":
            raise
        pytest.skip(f"AI visualization optional dependency missing: {missing}")


def test_ai_visualization_module_imports():
    mod = _import_ai_visualization()
    assert hasattr(mod, "VisualizationConfig")
    assert hasattr(mod, "AIInsightGenerator")


def test_ai_insight_generator_basic():
    mod = _import_ai_visualization()
    gen = mod.AIInsightGenerator(mod.VisualizationConfig())
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [3.0, 2.0, 1.0]})
    insights = gen.generate_insights(df)
    assert isinstance(insights, list)
