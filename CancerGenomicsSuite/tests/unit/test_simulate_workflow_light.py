"""Lightweight tests for simulate_workflow (sleeps patched)."""

from unittest.mock import patch

import pytest


@pytest.fixture
def sim(tmp_path):
    from CancerGenomicsSuite.simulate_workflow import CancerGenomicsWorkflowSimulator

    return CancerGenomicsWorkflowSimulator(output_dir=str(tmp_path / "wf"), verbose=False)


@patch("time.sleep", lambda *a, **k: None)
def test_simulate_data_loading_returns_types(sim):
    data = sim.simulate_data_loading(num_samples=3, num_genes=10)
    assert "gene_expression" in data
    assert data["gene_expression"]["samples"] == 3


@patch("time.sleep", lambda *a, **k: None)
def test_log_verbose_and_error(sim, capsys):
    sim.verbose = True
    sim.log("hello", level="INFO")
    out = capsys.readouterr().out
    assert "hello" in out
    sim.verbose = False
    sim.log("oops", level="ERROR")
    out2 = capsys.readouterr().out
    assert "oops" in out2
