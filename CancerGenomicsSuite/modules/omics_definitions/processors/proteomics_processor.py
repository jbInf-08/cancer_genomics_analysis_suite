"""
Proteomics Data Processor

This module provides specialized processing capabilities for proteomics data,
including protein identification, quantification, and functional analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union, Tuple
import logging
from pathlib import Path
import json
import warnings
warnings.filterwarnings('ignore')

from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.decomposition import PCA, FastICA
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import silhouette_score
from scipy import stats
from scipy.stats import ttest_ind, mannwhitneyu
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from ..omics_processor import OmicsDataProcessor, ProcessingResult, QualityControlMetrics
from ..omics_registry import OmicsFieldRegistry

logger = logging.getLogger(__name__)


class ProteomicsProcessor(OmicsDataProcessor):
    """Specialized processor for proteomics data."""
    
    def __init__(self, registry: OmicsFieldRegistry):
        """Initialize the proteomics processor."""
        super().__init__(registry)
        self.field_definition = registry.get_field('proteomics')
        
    def load_data(self, file_path: str, **kwargs) -> ProcessingResult:
        """Load proteomics data from various formats."""
        try:
            file_path = Path(file_path)
            processing_log = [f"Loading proteomics data from {file_path}"]
            
            if file_path.suffix.lower() in ['.csv', '.tsv']:
                data = self._load_quantification_file(file_path, **kwargs)
                processing_log.append("Loaded protein quantification file")
            elif file_path.suffix.lower() in ['.mzml', '.mzxml']:
                data = self._load_mass_spec_file(file_path, **kwargs)
                processing_log.append("Loaded mass spectrometry file")
            else:
                raise ValueError(f"Unsupported file format: {file_path.suffix}")
            
            # Create metadata
            metadata = {
                'samples': list(data.columns),
                'features': list(data.index),
                'data_type': 'proteomics',
                'file_path': str(file_path),
                'file_format': file_path.suffix,
                'protein_features': self._extract_protein_features(data)
            }
            
            # Validate data
            is_valid, errors = self.validate_data(data, 'proteomics')
            if not is_valid:
                return ProcessingResult(
                    data=pd.DataFrame(),
                    metadata={},
                    quality_metrics={},
                    processing_log=processing_log + errors,
                    success=False,
                    error_message="; ".join(errors)
                )
            
            # Quality control
            quality_metrics = self.quality_control(data, 'proteomics')
            
            return ProcessingResult(
                data=data,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error loading proteomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )
    
    def _load_quantification_file(self, file_path: Path, **kwargs) -> pd.DataFrame:
        """Load protein quantification data from CSV/TSV file."""
        if file_path.suffix.lower() == '.tsv':
            data = pd.read_csv(file_path, sep='\t', index_col=0, **kwargs)
        else:
            data = pd.read_csv(file_path, index_col=0, **kwargs)
        
        return data
    
    def _load_mass_spec_file(self, file_path: Path, **kwargs) -> pd.DataFrame:
        """Load mass spectrometry data (simplified implementation)."""
        # This is a placeholder - in practice, you'd use pyteomics or similar
        # For demonstration, create mock protein quantification data
        n_proteins = kwargs.get('n_proteins', 5000)
        n_samples = kwargs.get('n_samples', 50)
        
        proteins = [f"PROTEIN_{i:05d}" for i in range(n_proteins)]
        samples = [f"sample_{i:03d}" for i in range(n_samples)]
        
        # Generate log-normal protein abundance data
        data = np.random.lognormal(mean=8, sigma=1, size=(n_proteins, n_samples))
        
        return pd.DataFrame(data, index=proteins, columns=samples)
    
    def _extract_protein_features(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Extract protein-specific features from data."""
        features = {
            'total_proteins': data.shape[0],
            'total_samples': data.shape[1],
            'abundance_stats': self._calculate_abundance_stats(data),
            'protein_categories': self._categorize_proteins(data),
            'sample_characteristics': self._analyze_sample_characteristics(data)
        }
        return features
    
    def _calculate_abundance_stats(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate protein abundance statistics."""
        return {
            'mean_abundance': float(data.mean().mean()),
            'median_abundance': float(data.median().median()),
            'std_abundance': float(data.std().mean()),
            'min_abundance': float(data.min().min()),
            'max_abundance': float(data.max().max()),
            'missing_value_rate': float(data.isnull().sum().sum() / data.size)
        }
    
    def _categorize_proteins(self, data: pd.DataFrame) -> Dict[str, int]:
        """Categorize proteins by abundance level."""
        mean_abundance = data.mean(axis=1)
        
        categories = {
            'high_abundance': sum(mean_abundance > mean_abundance.quantile(0.8)),
            'moderate_abundance': sum((mean_abundance >= mean_abundance.quantile(0.2)) & 
                                    (mean_abundance <= mean_abundance.quantile(0.8))),
            'low_abundance': sum(mean_abundance < mean_abundance.quantile(0.2)),
            'not_detected': sum(mean_abundance == 0)
        }
        
        return categories
    
    def _analyze_sample_characteristics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze sample characteristics."""
        sample_stats = {
            'mean_abundance_per_sample': data.mean(axis=0).to_dict(),
            'total_abundance_per_sample': data.sum(axis=0).to_dict(),
            'detected_proteins_per_sample': (data > 0).sum(axis=0).to_dict()
        }
        
        return sample_stats
    
    def preprocess_data(self, data: pd.DataFrame, **kwargs) -> ProcessingResult:
        """Preprocess proteomics data."""
        try:
            processing_log = ["Starting proteomics preprocessing"]
            original_shape = data.shape
            
            # Handle missing values
            missing_strategy = kwargs.get('missing_value_strategy', 'remove')
            if missing_strategy == 'remove':
                # Remove proteins with too many missing values
                max_missing_rate = kwargs.get('max_missing_rate', 0.5)
                missing_rate = data.isnull().sum(axis=1) / data.shape[1]
                data = data[missing_rate <= max_missing_rate]
                processing_log.append(f"Removed proteins with missing rate > {max_missing_rate}")
                
            elif missing_strategy == 'impute':
                # Impute missing values
                impute_method = kwargs.get('impute_method', 'median')
                if impute_method == 'median':
                    data = data.fillna(data.median())
                elif impute_method == 'mean':
                    data = data.fillna(data.mean())
                elif impute_method == 'min':
                    data = data.fillna(data.min())
                processing_log.append(f"Imputed missing values using {impute_method}")
            
            # Filter low abundance proteins
            if 'min_abundance' in kwargs:
                min_abundance = kwargs['min_abundance']
                data = data[data.mean(axis=1) >= min_abundance]
                processing_log.append(f"Filtered proteins with abundance < {min_abundance}")
            
            # Filter proteins with low variance
            if 'min_variance' in kwargs:
                min_variance = kwargs['min_variance']
                data = data[data.var(axis=1) >= min_variance]
                processing_log.append(f"Filtered proteins with variance < {min_variance}")
            
            # Filter proteins with low detection rate
            if 'min_detection_rate' in kwargs:
                min_detection_rate = kwargs['min_detection_rate']
                detection_rate = (data > 0).sum(axis=1) / data.shape[1]
                data = data[detection_rate >= min_detection_rate]
                processing_log.append(f"Filtered proteins with detection rate < {min_detection_rate}")
            
            # Remove samples with too many missing values
            if 'max_sample_missing_rate' in kwargs:
                max_sample_missing_rate = kwargs['max_sample_missing_rate']
                sample_missing_rate = data.isnull().sum(axis=0) / data.shape[0]
                data = data.loc[:, sample_missing_rate <= max_sample_missing_rate]
                processing_log.append(f"Filtered samples with missing rate > {max_sample_missing_rate}")
            
            # Log transformation
            if kwargs.get('log_transform', True):
                data = np.log2(data + 1)  # Add pseudocount to avoid log(0)
                processing_log.append("Applied log2 transformation")
            
            # Create metadata
            metadata = {
                'samples': list(data.columns),
                'features': list(data.index),
                'data_type': 'proteomics',
                'preprocessing_steps': processing_log,
                'original_shape': original_shape,
                'processed_shape': data.shape,
                'filtered_proteins': original_shape[0] - data.shape[0],
                'filtered_samples': original_shape[1] - data.shape[1]
            }
            
            # Quality control
            quality_metrics = self.quality_control(data, 'proteomics')
            
            return ProcessingResult(
                data=data,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error preprocessing proteomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )
    
    def normalize_data(self, data: pd.DataFrame, method: str, **kwargs) -> ProcessingResult:
        """Normalize proteomics data."""
        try:
            processing_log = [f"Starting proteomics normalization with method: {method}"]
            
            if method == 'median_normalization':
                # Median normalization
                data_normalized = self._apply_median_normalization(data)
                processing_log.append("Applied median normalization")
                
            elif method == 'quantile':
                # Quantile normalization
                data_normalized = self._apply_quantile_normalization(data)
                processing_log.append("Applied quantile normalization")
                
            elif method == 'loess':
                # LOESS normalization (simplified)
                data_normalized = self._apply_loess_normalization(data)
                processing_log.append("Applied LOESS normalization")
                
            elif method == 'vsn':
                # Variance stabilizing normalization (simplified)
                data_normalized = self._apply_vsn_normalization(data)
                processing_log.append("Applied VSN normalization")
                
            elif method == 'cyclic_loess':
                # Cyclic LOESS normalization (simplified)
                data_normalized = self._apply_cyclic_loess_normalization(data)
                processing_log.append("Applied cyclic LOESS normalization")
                
            elif method == 'protein_median':
                # Protein median normalization
                data_normalized = self._apply_protein_median_normalization(data)
                processing_log.append("Applied protein median normalization")
                
            else:
                raise ValueError(f"Unsupported normalization method: {method}")
            
            # Create metadata
            metadata = {
                'samples': list(data_normalized.columns),
                'features': list(data_normalized.index),
                'data_type': 'proteomics',
                'normalization_method': method,
                'normalization_parameters': kwargs
            }
            
            # Quality control
            quality_metrics = self.quality_control(data_normalized, 'proteomics')
            
            return ProcessingResult(
                data=data_normalized,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error normalizing proteomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )
    
    def _apply_median_normalization(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply median normalization."""
        # Calculate median for each sample
        sample_medians = data.median(axis=0)
        
        # Calculate global median
        global_median = sample_medians.median()
        
        # Calculate normalization factors
        normalization_factors = global_median / sample_medians
        
        # Apply normalization
        data_normalized = data.multiply(normalization_factors, axis=1)
        
        return data_normalized
    
    def _apply_quantile_normalization(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply quantile normalization."""
        # Rank data
        ranked_data = data.rank(axis=1, method='average')
        
        # Calculate quantiles
        quantiles = ranked_data.mean(axis=1)
        
        # Apply quantile normalization
        data_normalized = ranked_data.apply(lambda x: quantiles, axis=0)
        
        return data_normalized
    
    def _apply_loess_normalization(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply LOESS normalization (simplified implementation)."""
        # This is a simplified implementation
        # In practice, you'd use more sophisticated LOESS methods
        
        # Calculate mean and variance for each protein
        mean_abundance = data.mean(axis=1)
        variance = data.var(axis=1)
        
        # Simple LOESS-like normalization
        data_normalized = data.copy()
        for sample in data.columns:
            sample_data = data[sample]
            # Apply simple trend correction
            trend = np.polyfit(mean_abundance, sample_data, 1)
            corrected = sample_data - np.polyval(trend, mean_abundance) + mean_abundance
            data_normalized[sample] = corrected
        
        return data_normalized
    
    def _apply_vsn_normalization(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply variance stabilizing normalization (simplified implementation)."""
        # This is a simplified implementation
        # In practice, you'd use the VSN package
        
        # Apply arcsinh transformation
        data_normalized = np.arcsinh(data)
        
        return data_normalized
    
    def _apply_cyclic_loess_normalization(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply cyclic LOESS normalization (simplified implementation)."""
        # This is a simplified implementation
        # In practice, you'd use the limma package
        
        # Apply median normalization as a proxy
        return self._apply_median_normalization(data)
    
    def _apply_protein_median_normalization(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply protein median normalization."""
        # Calculate median for each protein across samples
        protein_medians = data.median(axis=1)
        
        # Calculate global median
        global_median = protein_medians.median()
        
        # Calculate normalization factors
        normalization_factors = global_median / protein_medians
        
        # Apply normalization
        data_normalized = data.multiply(normalization_factors, axis=0)
        
        return data_normalized
    
    def perform_differential_protein_analysis(self, data: pd.DataFrame, 
                                            group1_samples: List[str], 
                                            group2_samples: List[str],
                                            method: str = 'ttest', **kwargs) -> Dict[str, Any]:
        """Perform differential protein analysis."""
        try:
            # Prepare data
            group1_data = data[group1_samples]
            group2_data = data[group2_samples]
            
            results = {}
            
            if method == 'ttest':
                results = self._perform_ttest_dpa(group1_data, group2_data)
            elif method == 'mannwhitney':
                results = self._perform_mannwhitney_dpa(group1_data, group2_data)
            elif method == 'fold_change':
                results = self._perform_fold_change_dpa(group1_data, group2_data)
            else:
                raise ValueError(f"Unsupported DPA method: {method}")
            
            # Add additional statistics
            results['summary'] = self._summarize_dpa_results(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in differential protein analysis: {e}")
            return {'error': str(e)}
    
    def _perform_ttest_dpa(self, group1_data: pd.DataFrame, group2_data: pd.DataFrame) -> Dict[str, Any]:
        """Perform t-test for differential protein analysis."""
        results = {
            'protein_id': [],
            'group1_mean': [],
            'group2_mean': [],
            'log2_fold_change': [],
            'p_value': [],
            'adjusted_p_value': []
        }
        
        for protein in group1_data.index:
            group1_values = group1_data.loc[protein].dropna()
            group2_values = group2_data.loc[protein].dropna()
            
            if len(group1_values) > 1 and len(group2_values) > 1:
                # Calculate means
                group1_mean = group1_values.mean()
                group2_mean = group2_values.mean()
                
                # Calculate log2 fold change
                if group1_mean > 0 and group2_mean > 0:
                    log2_fc = np.log2(group2_mean / group1_mean)
                else:
                    log2_fc = 0
                
                # Perform t-test
                try:
                    t_stat, p_value = ttest_ind(group1_values, group2_values)
                except:
                    p_value = 1.0
                
                results['protein_id'].append(protein)
                results['group1_mean'].append(group1_mean)
                results['group2_mean'].append(group2_mean)
                results['log2_fold_change'].append(log2_fc)
                results['p_value'].append(p_value)
                results['adjusted_p_value'].append(p_value)
        
        # Adjust p-values
        p_values = np.array(results['p_value'])
        adjusted_p_values = self._adjust_p_values(p_values)
        results['adjusted_p_value'] = adjusted_p_values.tolist()
        
        return results
    
    def _perform_mannwhitney_dpa(self, group1_data: pd.DataFrame, group2_data: pd.DataFrame) -> Dict[str, Any]:
        """Perform Mann-Whitney U test for differential protein analysis."""
        results = {
            'protein_id': [],
            'group1_median': [],
            'group2_median': [],
            'log2_fold_change': [],
            'p_value': [],
            'adjusted_p_value': []
        }
        
        for protein in group1_data.index:
            group1_values = group1_data.loc[protein].dropna()
            group2_values = group2_data.loc[protein].dropna()
            
            if len(group1_values) > 0 and len(group2_values) > 0:
                # Calculate medians
                group1_median = group1_values.median()
                group2_median = group2_values.median()
                
                # Calculate log2 fold change
                if group1_median > 0 and group2_median > 0:
                    log2_fc = np.log2(group2_median / group1_median)
                else:
                    log2_fc = 0
                
                # Perform Mann-Whitney U test
                try:
                    u_stat, p_value = mannwhitneyu(group1_values, group2_values, alternative='two-sided')
                except:
                    p_value = 1.0
                
                results['protein_id'].append(protein)
                results['group1_median'].append(group1_median)
                results['group2_median'].append(group2_median)
                results['log2_fold_change'].append(log2_fc)
                results['p_value'].append(p_value)
                results['adjusted_p_value'].append(p_value)
        
        # Adjust p-values
        p_values = np.array(results['p_value'])
        adjusted_p_values = self._adjust_p_values(p_values)
        results['adjusted_p_value'] = adjusted_p_values.tolist()
        
        return results
    
    def _perform_fold_change_dpa(self, group1_data: pd.DataFrame, group2_data: pd.DataFrame) -> Dict[str, Any]:
        """Perform fold change analysis for proteins."""
        results = {
            'protein_id': [],
            'group1_mean': [],
            'group2_mean': [],
            'fold_change': [],
            'log2_fold_change': []
        }
        
        for protein in group1_data.index:
            group1_mean = group1_data.loc[protein].mean()
            group2_mean = group2_data.loc[protein].mean()
            
            # Calculate fold change
            if group1_mean > 0:
                fold_change = group2_mean / group1_mean
                log2_fc = np.log2(fold_change)
            else:
                fold_change = float('inf') if group2_mean > 0 else 1.0
                log2_fc = float('inf') if group2_mean > 0 else 0.0
            
            results['protein_id'].append(protein)
            results['group1_mean'].append(group1_mean)
            results['group2_mean'].append(group2_mean)
            results['fold_change'].append(fold_change)
            results['log2_fold_change'].append(log2_fc)
        
        return results
    
    def _adjust_p_values(self, p_values: np.ndarray) -> np.ndarray:
        """Adjust p-values using Benjamini-Hochberg method."""
        # Sort p-values
        sorted_indices = np.argsort(p_values)
        sorted_p_values = p_values[sorted_indices]
        
        # Apply Benjamini-Hochberg correction
        m = len(p_values)
        adjusted_p_values = np.zeros_like(p_values)
        
        for i, p_val in enumerate(sorted_p_values):
            adjusted_p_values[sorted_indices[i]] = min(1.0, p_val * m / (i + 1))
        
        return adjusted_p_values
    
    def _summarize_dpa_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize differential protein analysis results."""
        if 'p_value' in results:
            p_values = np.array(results['p_value'])
            adjusted_p_values = np.array(results['adjusted_p_value'])
            
            summary = {
                'total_proteins': len(results['protein_id']),
                'significant_proteins_p05': sum(adjusted_p_values < 0.05),
                'significant_proteins_p01': sum(adjusted_p_values < 0.01),
                'significant_proteins_p001': sum(adjusted_p_values < 0.001),
                'upregulated': 0,
                'downregulated': 0
            }
            
            if 'log2_fold_change' in results:
                log2_fc = np.array(results['log2_fold_change'])
                significant_mask = adjusted_p_values < 0.05
                
                summary['upregulated'] = sum((log2_fc > 1) & significant_mask)
                summary['downregulated'] = sum((log2_fc < -1) & significant_mask)
        else:
            summary = {
                'total_proteins': len(results['protein_id']),
                'upregulated': 0,
                'downregulated': 0
            }
        
        return summary
    
    def perform_protein_functional_analysis(self, dpa_results: Dict[str, Any], 
                                          functional_database: str = 'go', **kwargs) -> Dict[str, Any]:
        """Perform protein functional analysis (simplified implementation)."""
        try:
            # This is a simplified implementation
            # In practice, you'd use tools like DAVID, STRING, or similar
            
            functional_results = {
                'enriched_functions': [],
                'protein_networks': {},
                'pathway_enrichment': {}
            }
            
            # Mock functional analysis
            if 'log2_fold_change' in dpa_results and 'adjusted_p_value' in dpa_results:
                significant_proteins = []
                for i, protein in enumerate(dpa_results['protein_id']):
                    if dpa_results['adjusted_p_value'][i] < 0.05:
                        significant_proteins.append(protein)
                
                # Mock functional enrichment
                mock_functions = [
                    'Protein binding', 'Enzyme activity', 'Signal transduction',
                    'Metabolic process', 'Cell cycle', 'Apoptosis', 'Immune response'
                ]
                
                for function_name in mock_functions:
                    # Mock enrichment statistics
                    function_proteins = significant_proteins[:np.random.randint(3, 15)]
                    p_value = np.random.random() * 0.05  # Significant functions
                    
                    functional_results['enriched_functions'].append({
                        'function': function_name,
                        'proteins': function_proteins,
                        'p_value': p_value,
                        'protein_count': len(function_proteins)
                    })
                    
                    functional_results['protein_networks'][function_name] = function_proteins
            
            return functional_results
            
        except Exception as e:
            logger.error(f"Error in protein functional analysis: {e}")
            return {'error': str(e)}
    
    def generate_proteomics_report(self, data: pd.DataFrame, 
                                 analysis_results: Dict[str, Any]) -> str:
        """Generate comprehensive proteomics analysis report."""
        report = f"""
# Proteomics Analysis Report
Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

## Data Summary
- Total proteins: {data.shape[0]}
- Total samples: {data.shape[1]}
- Data completeness: {(1 - data.isnull().sum().sum() / data.size):.2%}

## Protein Abundance Analysis
"""
        
        # Abundance statistics
        mean_abundance = data.mean().mean()
        median_abundance = data.median().median()
        report += f"- Mean abundance: {mean_abundance:.2f}\n"
        report += f"- Median abundance: {median_abundance:.2f}\n"
        report += f"- Abundance range: [{data.min().min():.2f}, {data.max().max():.2f}]\n"
        
        # Protein categories
        mean_abundance_per_protein = data.mean(axis=1)
        high_abundance = sum(mean_abundance_per_protein > mean_abundance_per_protein.quantile(0.8))
        low_abundance = sum(mean_abundance_per_protein < mean_abundance_per_protein.quantile(0.2))
        
        report += f"- High abundance proteins: {high_abundance}\n"
        report += f"- Low abundance proteins: {low_abundance}\n"
        
        # Differential protein analysis results
        if 'differential_protein_analysis' in analysis_results:
            dpa_results = analysis_results['differential_protein_analysis']
            if 'summary' in dpa_results:
                summary = dpa_results['summary']
                report += f"""
## Differential Protein Analysis
- Total proteins analyzed: {summary['total_proteins']}
- Significant proteins (p < 0.05): {summary['significant_proteins_p05']}
- Significant proteins (p < 0.01): {summary['significant_proteins_p01']}
- Upregulated proteins: {summary['upregulated']}
- Downregulated proteins: {summary['downregulated']}
"""
        
        # Functional analysis results
        if 'protein_functional_analysis' in analysis_results:
            functional_results = analysis_results['protein_functional_analysis']
            if 'enriched_functions' in functional_results:
                report += f"""
## Protein Functional Analysis
- Enriched functions: {len(functional_results['enriched_functions'])}
"""
                for function in functional_results['enriched_functions'][:5]:  # Show top 5
                    report += f"- {function['function']}: {function['protein_count']} proteins (p = {function['p_value']:.3f})\n"
        
        return report
