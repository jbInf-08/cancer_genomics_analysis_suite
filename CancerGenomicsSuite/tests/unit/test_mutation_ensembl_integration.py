"""
Integration-style tests: mutation analysis + Ensembl-style HTTP (mocked).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from CancerGenomicsSuite.modules.mutation_analysis.mutation_analyzer import (
    MutationAnalyzer,
)


@pytest.mark.integration
def test_fetch_external_ensembl_json():
    a = MutationAnalyzer()
    with patch(
        "CancerGenomicsSuite.modules.mutation_analysis.mutation_analyzer.requests.get"
    ) as m:
        mock_r = MagicMock()
        mock_r.status_code = 200
        mock_r.json.return_value = {"Xrefs": [], "id": "ENSG00000000001"}
        m.return_value = mock_r
        data = a.fetch_external_data("https://rest.ensembl.org/lookup/symbol/human/TP53")
    assert "id" in data


@pytest.mark.integration
def test_mutation_context_and_count():
    a = MutationAnalyzer()
    rec = {
        "gene": "TP53",
        "mutation": "R175H",
        "impact": "high",
        "chromosome": "17",
        "position": 7574003,
        "ref_allele": "C",
        "alt_allele": "T",
        "sample_id": "S1",
    }
    ctx = a.get_mutation_context(rec)
    assert "gene_function" in ctx
    out = a.analyze_mutations([rec])
    assert out["total_mutations"] == 1
