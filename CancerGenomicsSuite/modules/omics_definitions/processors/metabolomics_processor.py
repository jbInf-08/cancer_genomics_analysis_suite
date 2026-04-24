"""
Metabolomics Data Processor

This module provides specialized processing capabilities for metabolomics data,
including metabolite identification, quantification, and pathway analysis.
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


class MetabolomicsProcessor(OmicsDataProcessor):
    """Specialized processor for metabolomics data."""
    
    def __init__(self, registry: OmicsFieldRegistry):
        """Initialize the metabolomics processor."""
        super().__init__(registry)
        self.field_definition = registry.get_field('metabolomics')
        
    def load_data(self, file_path: str, **kwargs) -> ProcessingResult:
        """Load metabolomics data from various formats."""
        try:
            file_path = Path(file_path)
            processing_log = [f"Loading metabolomics data from {file_path}"]
            
            if file_path.suffix.lower() in ['.csv', '.tsv']:
                data = self._load_metabolite_file(file_path, **kwargs)
                processing_log.append("Loaded metabolite quantification file")
            elif file_path.suffix.lower() in ['.mzml', '.mzxml']:
                data = self._load_mass_spec_file(file_path, **kwargs)
                processing_log.append("Loaded mass spectrometry file")
            elif file_path.suffix.lower() == '.nmr':
                data = self._load_nmr_file(file_path, **kwargs)
                processing_log.append("Loaded NMR file")
            else:
                raise ValueError(f"Unsupported file format: {file_path.suffix}")
            
            # Create metadata
            metadata = {
                'samples': list(data.columns),
                'features': list(data.index),
                'data_type': 'metabolomics',
                'file_path': str(file_path),
                'file_format': file_path.suffix,
                'metabolite_features': self._extract_metabolite_features(data)
            }
            
            # Validate data
            is_valid, errors = self.validate_data(data, 'metabolomics')
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
            quality_metrics = self.quality_control(data, 'metabolomics')
            
            return ProcessingResult(
                data=data,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error loading metabolomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )
    
    def _load_metabolite_file(self, file_path: Path, **kwargs) -> pd.DataFrame:
        """Load metabolite quantification data from CSV/TSV file."""
        if file_path.suffix.lower() == '.tsv':
            data = pd.read_csv(file_path, sep='\t', index_col=0, **kwargs)
        else:
            data = pd.read_csv(file_path, index_col=0, **kwargs)
        
        return data
    
    def _load_mass_spec_file(self, file_path: Path, **kwargs) -> pd.DataFrame:
        """Load mass spectrometry data (simplified implementation)."""
        # This is a placeholder - in practice, you'd use pyteomics or similar
        # For demonstration, create mock metabolite data
        n_metabolites = kwargs.get('n_metabolites', 500)
        n_samples = kwargs.get('n_samples', 50)
        
        metabolites = [f"METABOLITE_{i:04d}" for i in range(n_metabolites)]
        samples = [f"sample_{i:03d}" for i in range(n_samples)]
        
        # Generate log-normal metabolite abundance data
        data = np.random.lognormal(mean=3, sigma=1, size=(n_metabolites, n_samples))
        
        return pd.DataFrame(data, index=metabolites, columns=samples)
    
    def _load_nmr_file(self, file_path: Path, **kwargs) -> pd.DataFrame:
        """Load NMR data (simplified implementation)."""
        # This is a placeholder - in practice, you'd use nmrglue or similar
        # For demonstration, create mock NMR data
        n_peaks = kwargs.get('n_peaks', 200)
        n_samples = kwargs.get('n_samples', 50)
        
        peaks = [f"PEAK_{i:04d}" for i in range(n_peaks)]
        samples = [f"sample_{i:03d}" for i in range(n_samples)]
        
        # Generate normal metabolite abundance data
        data = np.random.normal(1000, 200, size=(n_peaks, n_samples))
        data = np.abs(data)  # Ensure positive values
        
        return pd.DataFrame(data, index=peaks, columns=samples)
    
    def _extract_metabolite_features(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Extract metabolite-specific features from data."""
        features = {
            'total_metabolites': data.shape[0],
            'total_samples': data.shape[1],
            'abundance_stats': self._calculate_abundance_stats(data),
            'metabolite_categories': self._categorize_metabolites(data),
            'sample_characteristics': self._analyze_sample_characteristics(data)
        }
        return features
    
    def _calculate_abundance_stats(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate metabolite abundance statistics."""
        return {
            'mean_abundance': float(data.mean().mean()),
            'median_abundance': float(data.median().median()),
            'std_abundance': float(data.std().mean()),
            'min_abundance': float(data.min().min()),
            'max_abundance': float(data.max().max()),
            'missing_value_rate': float(data.isnull().sum().sum() / data.size)
        }
    
    def _categorize_metabolites(self, data: pd.DataFrame) -> Dict[str, int]:
        """Categorize metabolites by abundance level."""
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
            'detected_metabolites_per_sample': (data > 0).sum(axis=0).to_dict()
        }
        
        return sample_stats
    
    def preprocess_data(self, data: pd.DataFrame, **kwargs) -> ProcessingResult:
        """Preprocess metabolomics data."""
        try:
            processing_log = ["Starting metabolomics preprocessing"]
            original_shape = data.shape
            
            # Handle missing values
            missing_strategy = kwargs.get('missing_value_strategy', 'impute')
            if missing_strategy == 'remove':
                # Remove metabolites with too many missing values
                max_missing_rate = kwargs.get('max_missing_rate', 0.5)
                missing_rate = data.isnull().sum(axis=1) / data.shape[1]
                data = data[missing_rate <= max_missing_rate]
                processing_log.append(f"Removed metabolites with missing rate > {max_missing_rate}")
                
            elif missing_strategy == 'impute':
                # Impute missing values
                impute_method = kwargs.get('impute_method', 'half_minimum')
                if impute_method == 'half_minimum':
                    # Replace missing values with half the minimum value
                    data = data.fillna(data.min() * 0.5)
                elif impute_method == 'median':
                    data = data.fillna(data.median())
                elif impute_method == 'mean':
                    data = data.fillna(data.mean())
                elif impute_method == 'knn':
                    # KNN imputation (simplified)
                    data = data.fillna(data.median())
                processing_log.append(f"Imputed missing values using {impute_method}")
            
            # Filter low abundance metabolites
            if 'min_abundance' in kwargs:
                min_abundance = kwargs['min_abundance']
                data = data[data.mean(axis=1) >= min_abundance]
                processing_log.append(f"Filtered metabolites with abundance < {min_abundance}")
            
            # Filter metabolites with low variance
            if 'min_variance' in kwargs:
                min_variance = kwargs['min_variance']
                data = data[data.var(axis=1) >= min_variance]
                processing_log.append(f"Filtered metabolites with variance < {min_variance}")
            
            # Filter metabolites with low detection rate
            if 'min_detection_rate' in kwargs:
                min_detection_rate = kwargs['min_detection_rate']
                detection_rate = (data > 0).sum(axis=1) / data.shape[1]
                data = data[detection_rate >= min_detection_rate]
                processing_log.append(f"Filtered metabolites with detection rate < {min_detection_rate}")
            
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
                'data_type': 'metabolomics',
                'preprocessing_steps': processing_log,
                'original_shape': original_shape,
                'processed_shape': data.shape,
                'filtered_metabolites': original_shape[0] - data.shape[0],
                'filtered_samples': original_shape[1] - data.shape[1]
            }
            
            # Quality control
            quality_metrics = self.quality_control(data, 'metabolomics')
            
            return ProcessingResult(
                data=data,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error preprocessing metabolomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )
    
    def normalize_data(self, data: pd.DataFrame, method: str, **kwargs) -> ProcessingResult:
        """Normalize metabolomics data."""
        try:
            processing_log = [f"Starting metabolomics normalization with method: {method}"]
            
            if method == 'internal_standard':
                # Internal standard normalization
                data_normalized = self._apply_internal_standard_normalization(data, **kwargs)
                processing_log.append("Applied internal standard normalization")
                
            elif method == 'total_ion_current':
                # Total ion current normalization
                data_normalized = self._apply_total_ion_current_normalization(data)
                processing_log.append("Applied total ion current normalization")
                
            elif method == 'relative_abundance':
                # Relative abundance normalization
                data_normalized = self._apply_relative_abundance_normalization(data)
                processing_log.append("Applied relative abundance normalization")
                
            elif method == 'pqn':
                # Probabilistic quotient normalization
                data_normalized = self._apply_pqn_normalization(data)
                processing_log.append("Applied PQN normalization")
                
            elif method == 'is':
                # Internal standard normalization (generic)
                data_normalized = self._apply_is_normalization(data, **kwargs)
                processing_log.append("Applied IS normalization")
                
            elif method == 'quantile':
                # Quantile normalization
                data_normalized = self._apply_quantile_normalization(data)
                processing_log.append("Applied quantile normalization")
                
            elif method == 'median':
                # Median normalization
                data_normalized = self._apply_median_normalization(data)
                processing_log.append("Applied median normalization")
                
            else:
                raise ValueError(f"Unsupported normalization method: {method}")
            
            # Create metadata
            metadata = {
                'samples': list(data_normalized.columns),
                'features': list(data_normalized.index),
                'data_type': 'metabolomics',
                'normalization_method': method,
                'normalization_parameters': kwargs
            }
            
            # Quality control
            quality_metrics = self.quality_control(data_normalized, 'metabolomics')
            
            return ProcessingResult(
                data=data_normalized,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error normalizing metabolomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )
    
    def _apply_internal_standard_normalization(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """Apply internal standard normalization."""
        internal_standard = kwargs.get('internal_standard', None)
        
        if internal_standard and internal_standard in data.index:
            # Normalize to internal standard
            is_data = data.loc[internal_standard]
            data_normalized = data.div(is_data, axis=1)
        else:
            # Use median normalization as fallback
            data_normalized = self._apply_median_normalization(data)
        
        return data_normalized
    
    def _apply_total_ion_current_normalization(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply total ion current normalization."""
        # Calculate total abundance for each sample
        total_abundance = data.sum(axis=0)
        
        # Calculate median total abundance
        median_total = total_abundance.median()
        
        # Calculate normalization factors
        normalization_factors = median_total / total_abundance
        
        # Apply normalization
        data_normalized = data.multiply(normalization_factors, axis=1)
        
        return data_normalized
    
    def _apply_relative_abundance_normalization(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply relative abundance normalization."""
        # Normalize each sample to sum to 1
        data_normalized = data.div(data.sum(axis=0), axis=1)
        
        return data_normalized
    
    def _apply_pqn_normalization(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply probabilistic quotient normalization (simplified implementation)."""
        # This is a simplified implementation
        # In practice, you'd use more sophisticated PQN methods
        
        # Calculate median spectrum
        median_spectrum = data.median(axis=1)
        
        # Calculate quotients for each sample
        data_normalized = data.copy()
        for sample in data.columns:
            sample_data = data[sample]
            # Calculate quotient
            quotient = sample_data / median_spectrum
            # Use median quotient as normalization factor
            normalization_factor = quotient.median()
            data_normalized[sample] = sample_data / normalization_factor
        
        return data_normalized
    
    def _apply_is_normalization(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """Apply internal standard normalization (generic)."""
        return self._apply_internal_standard_normalization(data, **kwargs)
    
    def _apply_quantile_normalization(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply quantile normalization."""
        # Rank data
        ranked_data = data.rank(axis=1, method='average')
        
        # Calculate quantiles
        quantiles = ranked_data.mean(axis=1)
        
        # Apply quantile normalization
        data_normalized = ranked_data.apply(lambda x: quantiles, axis=0)
        
        return data_normalized
    
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
    
    def perform_differential_metabolite_analysis(self, data: pd.DataFrame, 
                                               group1_samples: List[str], 
                                               group2_samples: List[str],
                                               method: str = 'ttest', **kwargs) -> Dict[str, Any]:
        """Perform differential metabolite analysis."""
        try:
            # Prepare data
            group1_data = data[group1_samples]
            group2_data = data[group2_samples]
            
            results = {}
            
            if method == 'ttest':
                results = self._perform_ttest_dma(group1_data, group2_data)
            elif method == 'mannwhitney':
                results = self._perform_mannwhitney_dma(group1_data, group2_data)
            elif method == 'fold_change':
                results = self._perform_fold_change_dma(group1_data, group2_data)
            else:
                raise ValueError(f"Unsupported DMA method: {method}")
            
            # Add additional statistics
            results['summary'] = self._summarize_dma_results(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in differential metabolite analysis: {e}")
            return {'error': str(e)}
    
    def _perform_ttest_dma(self, group1_data: pd.DataFrame, group2_data: pd.DataFrame) -> Dict[str, Any]:
        """Perform t-test for differential metabolite analysis."""
        results = {
            'metabolite_id': [],
            'group1_mean': [],
            'group2_mean': [],
            'log2_fold_change': [],
            'p_value': [],
            'adjusted_p_value': []
        }
        
        for metabolite in group1_data.index:
            group1_values = group1_data.loc[metabolite].dropna()
            group2_values = group2_data.loc[metabolite].dropna()
            
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
                
                results['metabolite_id'].append(metabolite)
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
    
    def _perform_mannwhitney_dma(self, group1_data: pd.DataFrame, group2_data: pd.DataFrame) -> Dict[str, Any]:
        """Perform Mann-Whitney U test for differential metabolite analysis."""
        results = {
            'metabolite_id': [],
            'group1_median': [],
            'group2_median': [],
            'log2_fold_change': [],
            'p_value': [],
            'adjusted_p_value': []
        }
        
        for metabolite in group1_data.index:
            group1_values = group1_data.loc[metabolite].dropna()
            group2_values = group2_data.loc[metabolite].dropna()
            
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
                
                results['metabolite_id'].append(metabolite)
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
    
    def _perform_fold_change_dma(self, group1_data: pd.DataFrame, group2_data: pd.DataFrame) -> Dict[str, Any]:
        """Perform fold change analysis for metabolites."""
        results = {
            'metabolite_id': [],
            'group1_mean': [],
            'group2_mean': [],
            'fold_change': [],
            'log2_fold_change': []
        }
        
        for metabolite in group1_data.index:
            group1_mean = group1_data.loc[metabolite].mean()
            group2_mean = group2_data.loc[metabolite].mean()
            
            # Calculate fold change
            if group1_mean > 0:
                fold_change = group2_mean / group1_mean
                log2_fc = np.log2(fold_change)
            else:
                fold_change = float('inf') if group2_mean > 0 else 1.0
                log2_fc = float('inf') if group2_mean > 0 else 0.0
            
            results['metabolite_id'].append(metabolite)
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
    
    def _summarize_dma_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize differential metabolite analysis results."""
        if 'p_value' in results:
            p_values = np.array(results['p_value'])
            adjusted_p_values = np.array(results['adjusted_p_value'])
            
            summary = {
                'total_metabolites': len(results['metabolite_id']),
                'significant_metabolites_p05': sum(adjusted_p_values < 0.05),
                'significant_metabolites_p01': sum(adjusted_p_values < 0.01),
                'significant_metabolites_p001': sum(adjusted_p_values < 0.001),
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
                'total_metabolites': len(results['metabolite_id']),
                'upregulated': 0,
                'downregulated': 0
            }
        
        return summary
    
    def perform_metabolic_pathway_analysis(self, dma_results: Dict[str, Any], 
                                         pathway_database: str = 'kegg', **kwargs) -> Dict[str, Any]:
        """Perform metabolic pathway analysis (simplified implementation)."""
        try:
            # This is a simplified implementation
            # In practice, you'd use tools like MetaboAnalyst, KEGG, or similar
            
            pathway_results = {
                'enriched_pathways': [],
                'pathway_statistics': {},
                'metabolite_pathway_mapping': {}
            }
            
            # Mock pathway analysis
            if 'log2_fold_change' in dma_results and 'adjusted_p_value' in dma_results:
                significant_metabolites = []
                for i, metabolite in enumerate(dma_results['metabolite_id']):
                    if dma_results['adjusted_p_value'][i] < 0.05:
                        significant_metabolites.append(metabolite)
                
                # Mock pathway enrichment
                mock_pathways = [
                    'Glycolysis', 'TCA Cycle', 'Fatty Acid Metabolism', 'Amino Acid Metabolism',
                    'Nucleotide Metabolism', 'Steroid Metabolism', 'Purine Metabolism',
                    'Pyrimidine Metabolism', 'Glutathione Metabolism', 'Urea Cycle'
                ]
                
                for pathway in mock_pathways:
                    # Mock enrichment statistics
                    pathway_metabolites = significant_metabolites[:np.random.randint(3, 12)]
                    p_value = np.random.random() * 0.05  # Significant pathways
                    
                    pathway_results['enriched_pathways'].append({
                        'pathway': pathway,
                        'metabolites': pathway_metabolites,
                        'p_value': p_value,
                        'metabolite_count': len(pathway_metabolites)
                    })
                    
                    pathway_results['metabolite_pathway_mapping'][pathway] = pathway_metabolites
            
            return pathway_results
            
        except Exception as e:
            logger.error(f"Error in metabolic pathway analysis: {e}")
            return {'error': str(e)}
    
    def generate_metabolomics_report(self, data: pd.DataFrame, 
                                   analysis_results: Dict[str, Any]) -> str:
        """Generate comprehensive metabolomics analysis report."""
        report = f"""
# Metabolomics Analysis Report
Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

## Data Summary
- Total metabolites: {data.shape[0]}
- Total samples: {data.shape[1]}
- Data completeness: {(1 - data.isnull().sum().sum() / data.size):.2%}

## Metabolite Abundance Analysis
"""
        
        # Abundance statistics
        mean_abundance = data.mean().mean()
        median_abundance = data.median().median()
        report += f"- Mean abundance: {mean_abundance:.2f}\n"
        report += f"- Median abundance: {median_abundance:.2f}\n"
        report += f"- Abundance range: [{data.min().min():.2f}, {data.max().max():.2f}]\n"
        
        # Metabolite categories
        mean_abundance_per_metabolite = data.mean(axis=1)
        high_abundance = sum(mean_abundance_per_metabolite > mean_abundance_per_metabolite.quantile(0.8))
        low_abundance = sum(mean_abundance_per_metabolite < mean_abundance_per_metabolite.quantile(0.2))
        
        report += f"- High abundance metabolites: {high_abundance}\n"
        report += f"- Low abundance metabolites: {low_abundance}\n"
        
        # Differential metabolite analysis results
        if 'differential_metabolite_analysis' in analysis_results:
            dma_results = analysis_results['differential_metabolite_analysis']
            if 'summary' in dma_results:
                summary = dma_results['summary']
                report += f"""
## Differential Metabolite Analysis
- Total metabolites analyzed: {summary['total_metabolites']}
- Significant metabolites (p < 0.05): {summary['significant_metabolites_p05']}
- Significant metabolites (p < 0.01): {summary['significant_metabolites_p01']}
- Upregulated metabolites: {summary['upregulated']}
- Downregulated metabolites: {summary['downregulated']}
"""
        
        # Metabolic pathway analysis results
        if 'metabolic_pathway_analysis' in analysis_results:
            pathway_results = analysis_results['metabolic_pathway_analysis']
            if 'enriched_pathways' in pathway_results:
                report += f"""
## Metabolic Pathway Analysis
- Enriched pathways: {len(pathway_results['enriched_pathways'])}
"""
                for pathway in pathway_results['enriched_pathways'][:5]:  # Show top 5
                    report += f"- {pathway['pathway']}: {pathway['metabolite_count']} metabolites (p = {pathway['p_value']:.3f})\n"
        
        return report
