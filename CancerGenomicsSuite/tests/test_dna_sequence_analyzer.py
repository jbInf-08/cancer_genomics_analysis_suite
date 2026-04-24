"""
Tests for DNA sequence analyzer (current ``analyzer`` / ``utils`` API).
"""

import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from CancerGenomicsSuite.modules.dna_sequence_analyzer.analyzer import (
    DNAAnalyzer,
    AnalysisConfig,
)
from CancerGenomicsSuite.modules.dna_sequence_analyzer.utils import DNAUtils


class TestDNAUtils:
    def test_validate_sequence(self):
        u = DNAUtils()
        r = u.validate_sequence("ATCGATCG", strict=True)
        assert r["valid"] is True

    def test_validate_empty(self):
        u = DNAUtils()
        r = u.validate_sequence("", strict=True)
        assert r["valid"] is False


class TestDNAAnalyzer:
    def test_analyze_short_sequence(self):
        a = DNAAnalyzer(AnalysisConfig(find_orfs=False, find_restriction_sites=False))
        r = a.analyze_sequence("ATCGATCG", "s1")
        assert r.get("valid", True) is not False
        assert "statistics" in r
