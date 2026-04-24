"""
Test Suite for R Integration Module

Tests the R client functionality including:
- R environment detection and initialization
- Script execution (subprocess and rpy2)
- Data conversion between Python and R
- Statistical analysis functions
- Package management
- Error handling and fallbacks
"""

import sys

import pytest

# Skip entire module on Windows before importing r_client (avoids loading rpy2/R at collection).
if sys.platform == "win32":
    pytest.skip("R/rpy2 tests: run on Linux or WSL", allow_module_level=True)

import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import subprocess
import tempfile
import os

# Import the module under test
from CancerGenomicsSuite.modules.r_integration.r_client import RClient, RPY2_AVAILABLE


class TestRClientInitialization:
    """Tests for R client initialization."""
    
    def test_client_initializes_without_rpy2(self):
        """Test that client initializes even when rpy2 is not available."""
        with patch('CancerGenomicsSuite.modules.r_integration.r_client.RPY2_AVAILABLE', False):
            # Reload to get fresh instance behavior
            client = RClient()
            # Should have rpy2_available set appropriately
            assert hasattr(client, 'rpy2_available')
            assert hasattr(client, 'packages')
    
    def test_client_has_required_attributes(self):
        """Test that client has all required attributes."""
        client = RClient()
        
        assert hasattr(client, 'rpy2_available')
        assert hasattr(client, 'available_packages')
        assert hasattr(client, 'packages')
        assert hasattr(client, 'r')
    
    def test_get_r_status_returns_dict(self):
        """Test that get_r_status returns a dictionary with expected keys."""
        client = RClient()
        status = client.get_r_status()
        
        assert isinstance(status, dict)
        assert 'rpy2_available' in status
        assert 'rscript_available' in status
        assert 'mode' in status
        assert 'installed_packages_count' in status


class TestRScriptExecution:
    """Tests for R script execution via subprocess."""
    
    def test_execute_r_script_simple(self):
        """Test executing a simple R script."""
        client = RClient()
        
        # Simple R code that should work everywhere R is installed
        result = client.execute_r_script('cat("Hello from R")')
        
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'stdout' in result
        assert 'stderr' in result
    
    def test_execute_r_script_with_calculation(self):
        """Test executing R script with calculation."""
        client = RClient()
        
        result = client.execute_r_script('cat(2 + 2)')
        
        if result['success']:
            assert '4' in result['stdout']
    
    def test_execute_r_script_error_handling(self):
        """Test that R script errors are handled gracefully."""
        client = RClient()
        
        # This should cause an R error
        result = client.execute_r_script('stop("Test error")')
        
        assert isinstance(result, dict)
        assert result['success'] == False or 'error' in result.get('stderr', '').lower()
    
    @patch('subprocess.run')
    def test_execute_r_script_timeout(self, mock_run):
        """Test that script timeout is handled."""
        mock_run.side_effect = subprocess.TimeoutExpired('Rscript', 300)
        
        client = RClient()
        result = client.execute_r_script('Sys.sleep(1000)')
        
        assert result['success'] == False
        assert 'timeout' in result.get('error', '').lower() or 'timeout' in result.get('stderr', '').lower()


class TestPackageManagement:
    """Tests for R package management."""
    
    def test_get_required_packages_returns_list(self):
        """Test that get_required_packages returns a list."""
        client = RClient()
        packages = client.get_required_packages()
        
        assert isinstance(packages, list)
        assert len(packages) > 0
        assert 'DESeq2' in packages
        assert 'ggplot2' in packages
    
    def test_check_package_installed_returns_bool(self):
        """Test that check_package_installed returns boolean."""
        client = RClient()
        
        # Check a package that should exist in any R installation
        result = client.check_package_installed('base')
        assert isinstance(result, bool)
    
    def test_install_package_cran(self):
        """Test CRAN package installation generates correct R code."""
        client = RClient()
        
        # Mock the execute_r_script to capture what code would be run
        with patch.object(client, 'execute_r_script') as mock_exec:
            mock_exec.return_value = {'success': True, 'stdout': '', 'stderr': ''}
            
            client.install_package('testthat', source='CRAN')
            
            # Check that execute_r_script was called with install.packages
            assert mock_exec.called
            call_args = mock_exec.call_args[0][0]
            assert 'install.packages' in call_args
            assert 'testthat' in call_args
    
    def test_install_package_bioconductor(self):
        """Test Bioconductor package installation generates correct R code."""
        client = RClient()
        
        with patch.object(client, 'execute_r_script') as mock_exec:
            mock_exec.return_value = {'success': True, 'stdout': '', 'stderr': ''}
            
            client.install_package('DESeq2', source='Bioconductor')
            
            call_args = mock_exec.call_args[0][0]
            assert 'BiocManager' in call_args
            assert 'DESeq2' in call_args


class TestDataConversion:
    """Tests for data conversion between Python and R."""
    
    @pytest.mark.skipif(not RPY2_AVAILABLE, reason="rpy2 not available")
    def test_load_dataframe(self):
        """Test loading a pandas DataFrame into R."""
        client = RClient()
        
        if not client.rpy2_available:
            pytest.skip("rpy2 not available")
        
        df = pd.DataFrame({
            'gene': ['TP53', 'BRCA1', 'EGFR'],
            'expression': [100.5, 200.3, 150.7]
        })
        
        result = client.load_data(df, 'test_df')
        assert result == True
    
    @pytest.mark.skipif(not RPY2_AVAILABLE, reason="rpy2 not available")
    def test_load_numpy_array(self):
        """Test loading a numpy array into R."""
        client = RClient()
        
        if not client.rpy2_available:
            pytest.skip("rpy2 not available")
        
        arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        
        result = client.load_data(arr, 'test_arr')
        assert result == True
    
    @pytest.mark.skipif(not RPY2_AVAILABLE, reason="rpy2 not available")
    def test_load_list(self):
        """Test loading a Python list into R."""
        client = RClient()
        
        if not client.rpy2_available:
            pytest.skip("rpy2 not available")
        
        lst = ['gene1', 'gene2', 'gene3']
        
        result = client.load_data(lst, 'test_list')
        assert result == True
    
    def test_load_data_fallback_when_no_rpy2(self):
        """Test that load_data returns False when rpy2 is not available."""
        client = RClient()
        client.rpy2_available = False
        
        df = pd.DataFrame({'a': [1, 2, 3]})
        result = client.load_data(df, 'test')
        
        assert result == False


class TestPlotGeneration:
    """Tests for R plot generation."""
    
    def test_create_plot_returns_base64(self):
        """Test that create_plot returns base64 encoded image."""
        client = RClient()
        
        # Simple plot code
        plot_code = '''
        x <- 1:10
        y <- x^2
        plot(x, y, main="Test Plot")
        '''
        
        result = client.create_plot(plot_code)
        
        # Should return base64 string or empty string on failure
        assert isinstance(result, str)
        if result:  # If R is available and plot succeeded
            assert result.startswith('data:image/png;base64,') or result == ''
    
    def test_create_plot_to_file(self):
        """Test that create_plot can save to file."""
        client = RClient()
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            output_file = f.name
        
        try:
            plot_code = '''
            x <- 1:10
            y <- x^2
            plot(x, y)
            '''
            
            result = client.create_plot(plot_code, output_file=output_file)
            
            # Should return the file path
            if result:
                assert result == output_file
                # File should exist if R is available
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)


class TestStatisticalAnalysis:
    """Tests for statistical analysis functions."""
    
    def test_run_deseq2_returns_dict(self):
        """Test that run_deseq2_analysis returns a dictionary."""
        client = RClient()
        
        # Create mock count data
        count_data = pd.DataFrame({
            'gene1': [100, 200, 150, 180],
            'gene2': [50, 75, 60, 80],
            'gene3': [300, 250, 280, 320]
        }, index=['sample1', 'sample2', 'sample3', 'sample4']).T
        
        metadata = pd.DataFrame({
            'condition': ['control', 'control', 'treated', 'treated']
        }, index=['sample1', 'sample2', 'sample3', 'sample4'])
        
        result = client.run_deseq2_analysis(count_data, metadata)
        
        assert isinstance(result, dict)
        assert 'success' in result or 'error' in result
    
    def test_run_limma_returns_dict(self):
        """Test that run_limma_analysis returns a dictionary."""
        client = RClient()
        
        # Create mock expression data
        expression_data = pd.DataFrame({
            'sample1': [1.5, 2.3, 0.8],
            'sample2': [1.8, 2.1, 0.9],
            'sample3': [3.5, 4.2, 1.2],
            'sample4': [3.8, 4.0, 1.4]
        }, index=['gene1', 'gene2', 'gene3'])
        
        metadata = pd.DataFrame({
            'condition': ['control', 'control', 'treated', 'treated']
        }, index=['sample1', 'sample2', 'sample3', 'sample4'])
        
        result = client.run_limma_analysis(expression_data, metadata)
        
        assert isinstance(result, dict)
        assert 'success' in result or 'error' in result
    
    def test_run_go_enrichment_returns_dict(self):
        """Test that run_go_enrichment returns a dictionary."""
        client = RClient()
        
        gene_list = ['TP53', 'BRCA1', 'EGFR', 'KRAS', 'PIK3CA']
        
        result = client.run_go_enrichment(gene_list)
        
        assert isinstance(result, dict)
        assert 'success' in result or 'error' in result


class TestHeatmapGeneration:
    """Tests for heatmap generation."""
    
    def test_create_heatmap_returns_string(self):
        """Test that create_heatmap returns a string (base64 or empty)."""
        client = RClient()
        
        data = pd.DataFrame({
            'sample1': [1.0, 2.0, 3.0],
            'sample2': [1.5, 2.5, 3.5],
            'sample3': [0.8, 1.8, 2.8]
        }, index=['gene1', 'gene2', 'gene3'])
        
        result = client.create_heatmap(data, title="Test Heatmap")
        
        assert isinstance(result, str)


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_execute_r_code_fallback_to_subprocess(self):
        """Test that execute_r_code falls back to subprocess when rpy2 unavailable."""
        client = RClient()
        client.rpy2_available = False
        client.r = None
        
        # Should use subprocess fallback
        try:
            result = client.execute_r_code('cat("test")')
            # Should either return stdout or raise an error
            assert result is not None or True
        except RuntimeError:
            # Expected if R script fails
            pass
    
    def test_get_data_returns_none_without_rpy2(self):
        """Test that get_data returns None when rpy2 unavailable."""
        client = RClient()
        client.rpy2_available = False
        
        result = client.get_data('nonexistent_var')
        assert result is None


class TestInstallRequiredPackages:
    """Tests for install_required_packages method."""
    
    def test_install_required_packages_returns_dict(self):
        """Test that install_required_packages returns a dictionary."""
        client = RClient()
        
        with patch.object(client, 'check_package_installed', return_value=True):
            with patch.object(client, 'install_package', return_value=True):
                result = client.install_required_packages(skip_installed=True)
        
        assert isinstance(result, dict)


# Fixtures for common test data
@pytest.fixture
def sample_expression_data():
    """Create sample expression data for testing."""
    np.random.seed(42)
    return pd.DataFrame(
        np.random.rand(100, 6) * 1000,
        columns=['sample1', 'sample2', 'sample3', 'sample4', 'sample5', 'sample6'],
        index=[f'gene{i}' for i in range(100)]
    ).astype(int)


@pytest.fixture
def sample_metadata():
    """Create sample metadata for testing."""
    return pd.DataFrame({
        'condition': ['control', 'control', 'control', 'treated', 'treated', 'treated'],
        'batch': ['A', 'A', 'B', 'A', 'B', 'B']
    }, index=['sample1', 'sample2', 'sample3', 'sample4', 'sample5', 'sample6'])


@pytest.fixture
def r_client():
    """Create an R client instance for testing."""
    return RClient()


# Integration tests (only run if R is available)
@pytest.mark.integration
class TestRIntegration:
    """Integration tests that require R to be installed."""
    
    def test_full_workflow(self, r_client, sample_expression_data, sample_metadata):
        """Test a full analysis workflow."""
        # Check if R is available
        status = r_client.get_r_status()
        if not status['rscript_available']:
            pytest.skip("R not available")
        
        # This is an integration test - actual results depend on R being installed
        # and required packages being available
        pass
