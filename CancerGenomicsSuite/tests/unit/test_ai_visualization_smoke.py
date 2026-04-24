"""Smoke tests for the AI visualization module (optional heavy dependencies)."""

import importlib

import pandas as pd
import pytest


def test_ai_visualization_module_imports():
    try:
        mod = importlib.import_module(
            "CancerGenomicsSuite.modules.ai_integration.ai_visualization"
        )
    except ImportError as exc:
        pytest.skip(f"AI visualization optional dependencies missing: {exc}")
    assert hasattr(mod, "VisualizationConfig")
    assert hasattr(mod, "AIInsightGenerator")


def test_ai_insight_generator_basic():
    try:
        mod = importlib.import_module(
            "CancerGenomicsSuite.modules.ai_integration.ai_visualization"
        )
    except ImportError as exc:
        pytest.skip(f"AI visualization optional dependencies missing: {exc}")
    gen = mod.AIInsightGenerator(mod.VisualizationConfig())
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [3.0, 2.0, 1.0]})
    insights = gen.generate_insights(df)
    assert isinstance(insights, list)
