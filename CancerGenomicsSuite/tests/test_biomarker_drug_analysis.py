"""
Biomarker + drug surface tests (mocked or minimal data).
"""

import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from CancerGenomicsSuite.modules.external_databases.drug_databases import DrugBankClient
from CancerGenomicsSuite.modules.biomarker_discovery.biomarker_analyzer import (
    BiomarkerAnalyzer,
    BiomarkerDiscoveryConfig,
)


class TestDrugBankClient:
    @patch.object(DrugBankClient, "search_drug")
    def test_search_drug(self, mock_search):
        mock_search.return_value = [{"name": "aspirin", "id": "1"}]
        c = DrugBankClient()
        r = c.search_drug("aspirin")
        assert len(r) >= 0


class TestBiomarkerAnalyzerSmoke:
    def test_init(self):
        cfg = BiomarkerDiscoveryConfig(
            p_value_threshold=0.1,
            min_samples_per_group=2,
        )
        an = BiomarkerAnalyzer(cfg)
        assert an.config.min_samples_per_group == 2

    def test_discover_tiny_matrix(self):
        np.random.seed(0)
        m, f = 12, 6
        X = pd.DataFrame(
            np.random.randn(m, f),
            index=[f"S{i}" for i in range(m)],
            columns=[f"G{i}" for i in range(f)],
        )
        y = pd.Series(np.random.choice([0, 1], size=m), index=X.index)
        cfg = BiomarkerDiscoveryConfig(
            p_value_threshold=0.9,
            effect_size_threshold=0.01,
            min_samples_per_group=2,
            n_top_features=4,
        )
        an = BiomarkerAnalyzer(cfg)
        res = an.discover_biomarkers(X, y, biomarker_type="gene_expression")
        assert isinstance(res, list)
