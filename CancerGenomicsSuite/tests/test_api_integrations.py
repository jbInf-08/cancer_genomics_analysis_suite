"""
Tests for API integration clients (mocked network).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

# Package root = CancerGenomicsSuite
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from api_integrations.clinvar_sync import ClinVarSync
from api_integrations.cosmic_fetcher import CosmicFetcher
from api_integrations.encode_downloader import EncodeDownloader
from api_integrations.scopus_client import ScopusClient


class TestClinVarSync:
    def test_init(self):
        c = ClinVarSync()
        assert c.BASE_URL.startswith("https://")
        assert c.api_key is None

    @patch.object(ClinVarSync, "_make_request")
    def test_search_variants_parses_ids(self, mock_make):
        xml = """<?xml version="1.0"?>
        <eSearchResult><IdList><Id>9</Id><Id>10</Id></IdList></eSearchResult>"""
        mock_make.return_value = xml
        c = ClinVarSync()
        result = c.search_variants("BRCA1", 10)
        assert result == ["9", "10"]


class TestCosmicFetcher:
    def test_init(self):
        c = CosmicFetcher()
        assert c.base_url == CosmicFetcher.BASE_URL
        assert c.api_key is None

    @patch.object(CosmicFetcher, "_make_request")
    def test_fetch_mutations_by_gene(self, mock_make):
        mock_make.return_value = {"mutations": [{"gene_name": "BRCA1", "id": 1}]}
        c = CosmicFetcher()
        r = c.fetch_mutations_by_gene("BRCA1")
        assert r["status"] == "success"
        assert len(r["mutations"]) == 1

    def test_parse_mutation_data(self):
        c = CosmicFetcher()
        raw = {
            "mutations": [
                {
                    "gene_name": "BRCA1",
                    "mutation_id": "COSM12345",
                    "mutation_cds": "c.1A>T",
                    "mutation_aa": "p.M1L",
                    "tumour_site": "breast",
                }
            ]
        }
        p = c.parse_mutation_data(raw)
        assert p[0]["gene"] == "BRCA1"
        assert p[0]["mutation_id"] == "COSM12345"

    @patch.object(
        CosmicFetcher, "_make_request", side_effect=requests.Timeout("timeout")
    )
    def test_fetch_mutations_timeout(self, _mock):
        c = CosmicFetcher()
        r = c.fetch_mutations_by_gene("BRCA1")
        assert r["status"] == "error"
        assert "timeout" in r["error"].lower()


class TestEncodeDownloader:
    def test_init(self):
        e = EncodeDownloader()
        assert e.base_url == EncodeDownloader.BASE_URL
        assert e.api_key is None

    @patch.object(EncodeDownloader, "search_datasets", return_value=[])
    def test_search_experiments(self, _):
        e = EncodeDownloader()
        r = e.search_experiments("H3K4me3", "K562")
        assert r["status"] == "success"

    @patch.object(EncodeDownloader, "get_file_metadata", return_value={"id": "ENCFF1"})
    def test_get_file_info(self, _):
        e = EncodeDownloader()
        r = e.get_file_info("ENCFF1")
        assert r["status"] == "success"

    def test_parse_experiment_data(self):
        e = EncodeDownloader()
        raw = {
            "@graph": [
                {
                    "@id": "/experiments/ENCSR12345/",
                    "accession": "ENCSR12345",
                    "biosample_term_name": "K562",
                    "target": {"label": "H3K4me3"},
                }
            ]
        }
        p = e.parse_experiment_data(raw)
        assert p[0]["accession"] == "ENCSR12345"
        assert p[0]["cell_line"] == "K562"


class TestScopusClient:
    def test_init(self):
        s = ScopusClient()
        assert s.api_key is None
        assert "elsevier" in s.base_url.lower()

    @patch.object(ScopusClient, "_make_request")
    def test_search_articles(self, mock_make):
        mock_make.return_value = {
            "search-results": {"entry": []},
        }
        s = ScopusClient(api_key="x")
        out = s.search_articles("cancer", max_results=2)
        assert out == []


class TestClinVarUtils:
    def test_build_query_params(self):
        c = ClinVarSync()
        p = c._build_query_params({"term": "BRCA1", "retmax": 2})
        assert p["retmax"] == 2
