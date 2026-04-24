"""
Unit tests for the MutationAnalyzer class.

This module tests the MutationAnalyzer functionality in isolation,
using mocked dependencies.
"""

import time

import numpy as np
import pandas as pd
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

from CancerGenomicsSuite.modules.mutation_analysis import MutationAnalyzer


class TestMutationAnalyzer:
    """Test cases for MutationAnalyzer class."""
    
    @pytest.fixture
    def analyzer(self):
        """Create a MutationAnalyzer instance for testing."""
        return MutationAnalyzer()
    
    @pytest.fixture
    def sample_mutations(self):
        """Sample mutation data for testing."""
        return [
            {
                "gene": "TP53",
                "mutation": "R175H",
                "impact": "high",
                "chromosome": "17",
                "position": 7574003,
                "ref_allele": "C",
                "alt_allele": "T",
                "sample_id": "SAMPLE_001"
            },
            {
                "gene": "KRAS",
                "mutation": "G12D",
                "impact": "high",
                "chromosome": "12",
                "position": 25398284,
                "ref_allele": "G",
                "alt_allele": "A",
                "sample_id": "SAMPLE_001"
            },
            {
                "gene": "EGFR",
                "mutation": "L858R",
                "impact": "moderate",
                "chromosome": "7",
                "position": 55241707,
                "ref_allele": "T",
                "alt_allele": "G",
                "sample_id": "SAMPLE_002"
            }
        ]
    
    @pytest.mark.critical
    def test_analyze_mutations_success(self, analyzer, sample_mutations):
        """Test successful mutation analysis."""
        result = analyzer.analyze_mutations(sample_mutations)
        
        assert result is not None
        assert isinstance(result, dict)
        assert "total_mutations" in result
        assert "high_impact_count" in result
        assert "moderate_impact_count" in result
        assert "low_impact_count" in result
        assert result["total_mutations"] == 3
        assert result["high_impact_count"] == 2
        assert result["moderate_impact_count"] == 1
        assert result["low_impact_count"] == 0
    
    def test_analyze_mutations_empty_input(self, analyzer):
        """Test mutation analysis with empty input."""
        result = analyzer.analyze_mutations([])
        
        assert result is not None
        assert result["total_mutations"] == 0
        assert result["high_impact_count"] == 0
        assert result["moderate_impact_count"] == 0
        assert result["low_impact_count"] == 0
    
    @pytest.mark.parametrize("invalid_input", [None, "string", 123, {"invalid": "data"}])
    def test_analyze_mutations_invalid_input(self, analyzer, invalid_input):
        """Test mutation analysis with invalid input."""
        with pytest.raises(ValueError, match="Invalid input"):
            analyzer.analyze_mutations(invalid_input)
    
    def test_analyze_mutations_missing_fields(self, analyzer):
        """Test mutation analysis with missing required fields."""
        incomplete_mutations = [
            {"gene": "TP53", "mutation": "R175H"}  # Missing other required fields
        ]
        
        with pytest.raises(ValueError, match="Missing required fields"):
            analyzer.analyze_mutations(incomplete_mutations)
    
    def test_filter_mutations_by_impact(self, analyzer, sample_mutations):
        """Test filtering mutations by impact level."""
        high_impact = analyzer.filter_mutations_by_impact(sample_mutations, "high")
        
        assert len(high_impact) == 2
        assert all(mutation["impact"] == "high" for mutation in high_impact)
        assert all(mutation["gene"] in ["TP53", "KRAS"] for mutation in high_impact)
    
    def test_filter_mutations_by_gene(self, analyzer, sample_mutations):
        """Test filtering mutations by gene."""
        tp53_mutations = analyzer.filter_mutations_by_gene(sample_mutations, "TP53")
        
        assert len(tp53_mutations) == 1
        assert tp53_mutations[0]["gene"] == "TP53"
        assert tp53_mutations[0]["mutation"] == "R175H"
    
    def test_filter_mutations_by_sample(self, analyzer, sample_mutations):
        """Test filtering mutations by sample ID."""
        sample_001_mutations = analyzer.filter_mutations_by_sample(sample_mutations, "SAMPLE_001")
        
        assert len(sample_001_mutations) == 2
        assert all(mutation["sample_id"] == "SAMPLE_001" for mutation in sample_001_mutations)
    
    def test_calculate_mutation_frequency(self, analyzer, sample_mutations):
        """Test calculating mutation frequency."""
        frequency = analyzer.calculate_mutation_frequency(sample_mutations)
        
        assert isinstance(frequency, dict)
        assert "TP53" in frequency
        assert "KRAS" in frequency
        assert "EGFR" in frequency
        assert frequency["TP53"] == 1
        assert frequency["KRAS"] == 1
        assert frequency["EGFR"] == 1
    
    def test_get_mutation_summary(self, analyzer, sample_mutations):
        """Test getting mutation summary statistics."""
        summary = analyzer.get_mutation_summary(sample_mutations)
        
        assert isinstance(summary, dict)
        assert "total_mutations" in summary
        assert "unique_genes" in summary
        assert "unique_samples" in summary
        assert "impact_distribution" in summary
        assert summary["total_mutations"] == 3
        assert summary["unique_genes"] == 3
        assert summary["unique_samples"] == 2
    
    @patch(
        "CancerGenomicsSuite.modules.mutation_analysis.mutation_analyzer.requests.get"
    )
    def test_fetch_external_data(self, mock_get, analyzer):
        """Test fetching external data with mocked requests."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = analyzer.fetch_external_data("test_url")
        
        assert result == {"data": "test"}
        mock_get.assert_called_once_with("test_url", timeout=30)
    
    @patch(
        "CancerGenomicsSuite.modules.mutation_analysis.mutation_analyzer.requests.get"
    )
    def test_fetch_external_data_error(self, mock_get, analyzer):
        """Test fetching external data with error response."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        with pytest.raises(Exception, match="Failed to fetch data"):
            analyzer.fetch_external_data("test_url")
    
    def test_validate_mutation_format(self, analyzer):
        """Test mutation format validation."""
        valid_mutation = {
            "gene": "TP53",
            "mutation": "R175H",
            "impact": "high",
            "chromosome": "17",
            "position": 7574003,
            "ref_allele": "C",
            "alt_allele": "T",
            "sample_id": "SAMPLE_001"
        }
        
        assert analyzer.validate_mutation_format(valid_mutation) is True
        
        invalid_mutation = {"gene": "TP53"}  # Missing required fields
        assert analyzer.validate_mutation_format(invalid_mutation) is False
    
    def test_convert_to_dataframe(self, analyzer, sample_mutations):
        """Test converting mutations to DataFrame."""
        df = analyzer.convert_to_dataframe(sample_mutations)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert "gene" in df.columns
        assert "mutation" in df.columns
        assert "impact" in df.columns
        assert "sample_id" in df.columns
    
    def test_export_mutations(self, analyzer, sample_mutations, temp_file):
        """Test exporting mutations to file."""
        analyzer.export_mutations(sample_mutations, temp_file)
        
        assert temp_file.exists()
        assert temp_file.stat().st_size > 0
    
    def test_import_mutations(self, analyzer, temp_file):
        """Test importing mutations from file."""
        # First create a test file
        test_data = [
            {"gene": "TP53", "mutation": "R175H", "impact": "high", "sample_id": "SAMPLE_001"}
        ]
        analyzer.export_mutations(test_data, temp_file)
        
        # Then import it
        imported_data = analyzer.import_mutations(temp_file)
        
        assert len(imported_data) == 1
        assert imported_data[0]["gene"] == "TP53"
        assert imported_data[0]["mutation"] == "R175H"
    
    def test_compare_mutations(self, analyzer):
        """Test comparing two sets of mutations."""
        mutations1 = [
            {"gene": "TP53", "mutation": "R175H", "impact": "high", "sample_id": "SAMPLE_001"}
        ]
        mutations2 = [
            {"gene": "TP53", "mutation": "R175H", "impact": "high", "sample_id": "SAMPLE_001"},
            {"gene": "KRAS", "mutation": "G12D", "impact": "high", "sample_id": "SAMPLE_002"}
        ]
        
        comparison = analyzer.compare_mutations(mutations1, mutations2)
        
        assert isinstance(comparison, dict)
        assert "common_mutations" in comparison
        assert "unique_to_first" in comparison
        assert "unique_to_second" in comparison
        assert len(comparison["common_mutations"]) == 1
        assert len(comparison["unique_to_first"]) == 0
        assert len(comparison["unique_to_second"]) == 1
    
    def test_analyze_mutation_patterns(self, analyzer, sample_mutations):
        """Test analyzing mutation patterns."""
        patterns = analyzer.analyze_mutation_patterns(sample_mutations)
        
        assert isinstance(patterns, dict)
        assert "hotspot_genes" in patterns
        assert "mutation_types" in patterns
        assert "chromosome_distribution" in patterns
    
    def test_predict_mutation_impact(self, analyzer):
        """Test predicting mutation impact."""
        mutation = {
            "gene": "TP53",
            "mutation": "R175H",
            "chromosome": "17",
            "position": 7574003,
            "ref_allele": "C",
            "alt_allele": "T"
        }
        
        impact = analyzer.predict_mutation_impact(mutation)
        
        assert isinstance(impact, str)
        assert impact in ["high", "moderate", "low", "unknown"]
    
    def test_get_mutation_context(self, analyzer, sample_mutations):
        """Test getting mutation context information."""
        context = analyzer.get_mutation_context(sample_mutations[0])
        
        assert isinstance(context, dict)
        assert "gene_function" in context
        assert "protein_domain" in context
        assert "conservation_score" in context
    
    def test_analyze_mutation_cooccurrence(self, analyzer, sample_mutations):
        """Test analyzing mutation co-occurrence."""
        cooccurrence = analyzer.analyze_mutation_cooccurrence(sample_mutations)
        
        assert isinstance(cooccurrence, dict)
        assert "cooccurring_pairs" in cooccurrence
        assert "cooccurrence_matrix" in cooccurrence
    
    def test_generate_mutation_report(self, analyzer, sample_mutations):
        """Test generating mutation report."""
        report = analyzer.generate_mutation_report(sample_mutations)
        
        assert isinstance(report, dict)
        assert "summary" in report
        assert "detailed_analysis" in report
        assert "recommendations" in report
    
    def test_analyze_mutation_network(self, analyzer, sample_mutations):
        """Test analyzing mutation network."""
        network = analyzer.analyze_mutation_network(sample_mutations)
        
        assert isinstance(network, dict)
        assert "nodes" in network
        assert "edges" in network
        assert "network_metrics" in network
    
    def test_benchmark_performance(self, analyzer):
        """Test benchmarking mutation analysis performance."""
        # Create a large dataset for performance testing
        large_dataset = []
        for i in range(1000):
            large_dataset.append({
                "gene": f"GENE_{i % 100}",
                "mutation": f"MUT_{i}",
                "impact": "high" if i % 3 == 0 else "moderate",
                "chromosome": str(i % 23 + 1),
                "position": i * 1000,
                "ref_allele": "A",
                "alt_allele": "T",
                "sample_id": f"SAMPLE_{i % 50}"
            })
        
        start_time = time.time()
        result = analyzer.analyze_mutations(large_dataset)
        end_time = time.time()
        
        assert result is not None
        assert (end_time - start_time) < 5.0  # Should complete within 5 seconds
    
    def test_error_handling(self, analyzer):
        """Test error handling in various scenarios."""
        # Test with malformed data
        malformed_data = [
            {"gene": "TP53", "mutation": "R175H", "impact": "invalid_impact"}
        ]
        
        with pytest.raises(ValueError):
            analyzer.analyze_mutations(malformed_data)
        
        # Test with missing chromosome data
        incomplete_data = [
            {"gene": "TP53", "mutation": "R175H", "impact": "high", "sample_id": "SAMPLE_001"}
        ]
        
        with pytest.raises(ValueError):
            analyzer.analyze_mutations(incomplete_data)
    
    def test_memory_usage(self, analyzer):
        """Test memory usage with large datasets."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create a large dataset
        large_dataset = []
        for i in range(10000):
            large_dataset.append({
                "gene": f"GENE_{i % 1000}",
                "mutation": f"MUT_{i}",
                "impact": "high",
                "chromosome": str(i % 23 + 1),
                "position": i * 1000,
                "ref_allele": "A",
                "alt_allele": "T",
                "sample_id": f"SAMPLE_{i % 100}"
            })
        
        result = analyzer.analyze_mutations(large_dataset)
        final_memory = process.memory_info().rss
        
        # Memory usage should not increase dramatically
        memory_increase = final_memory - initial_memory
        assert memory_increase < 100 * 1024 * 1024  # Less than 100MB increase
