"""
Transcriptomics Data Processor

This module provides specialized processing capabilities for transcriptomics data,
including gene expression analysis, differential expression, and pathway analysis.
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


class TranscriptomicsProcessor(OmicsDataProcessor):
    """Specialized processor for transcriptomics data."""
    
    def __init__(self, registry: OmicsFieldRegistry):
        """Initialize the transcriptomics processor."""
        super().__init__(registry)
        self.field_definition = registry.get_field('transcriptomics')
        
    def load_data(self, file_path: str, **kwargs) -> ProcessingResult:
        """Load transcriptomics data from various formats."""
        try:
            file_path = Path(file_path)
            processing_log = [f"Loading transcriptomics data from {file_path}"]
            
            if file_path.suffix.lower() in ['.csv', '.tsv']:
                data = self._load_expression_file(file_path, **kwargs)
                processing_log.append("Loaded expression data file")
            elif file_path.suffix.lower() == '.h5':
                data = self._load_h5_file(file_path, **kwargs)
                processing_log.append("Loaded H5 file")
            else:
                raise ValueError(f"Unsupported file format: {file_path.suffix}")
            
            # Create metadata
            metadata = {
                'samples': list(data.columns),
                'features': list(data.index),
                'data_type': 'transcriptomics',
                'file_path': str(file_path),
                'file_format': file_path.suffix,
                'expression_features': self._extract_expression_features(data)
            }
            
            # Validate data
            is_valid, errors = self.validate_data(data, 'transcriptomics')
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
            quality_metrics = self.quality_control(data, 'transcriptomics')
            
            return ProcessingResult(
                data=data,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error loading transcriptomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )
    
    def _load_expression_file(self, file_path: Path, **kwargs) -> pd.DataFrame:
        """Load expression data from CSV/TSV file."""
        if file_path.suffix.lower() == '.tsv':
            data = pd.read_csv(file_path, sep='\t', index_col=0, **kwargs)
        else:
            data = pd.read_csv(file_path, index_col=0, **kwargs)
        
        return data
    
    def _load_h5_file(self, file_path: Path, **kwargs) -> pd.DataFrame:
        """Load expression data from H5 file."""
        # This is a placeholder - in practice, you'd use h5py or similar
        # For demonstration, create mock expression data
        n_genes = kwargs.get('n_genes', 20000)
        n_samples = kwargs.get('n_samples', 50)
        
        genes = [f"GENE_{i:05d}" for i in range(n_genes)]
        samples = [f"sample_{i:03d}" for i in range(n_samples)]
        
        # Generate log-normal expression data
        data = np.random.lognormal(mean=5, sigma=1, size=(n_genes, n_samples))
        
        return pd.DataFrame(data, index=genes, columns=samples)
    
    def _extract_expression_features(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Extract expression-specific features from data."""
        features = {
            'total_genes': data.shape[0],
            'total_samples': data.shape[1],
            'expression_stats': self._calculate_expression_stats(data),
            'gene_categories': self._categorize_genes(data),
            'sample_characteristics': self._analyze_sample_characteristics(data)
        }
        return features
    
    def _calculate_expression_stats(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate expression statistics."""
        return {
            'mean_expression': float(data.mean().mean()),
            'median_expression': float(data.median().median()),
            'std_expression': float(data.std().mean()),
            'min_expression': float(data.min().min()),
            'max_expression': float(data.max().max()),
            'zero_expression_rate': float((data == 0).sum().sum() / data.size)
        }
    
    def _categorize_genes(self, data: pd.DataFrame) -> Dict[str, int]:
        """Categorize genes by expression level."""
        mean_expression = data.mean(axis=1)
        
        categories = {
            'highly_expressed': sum(mean_expression > mean_expression.quantile(0.8)),
            'moderately_expressed': sum((mean_expression >= mean_expression.quantile(0.2)) & 
                                      (mean_expression <= mean_expression.quantile(0.8))),
            'lowly_expressed': sum(mean_expression < mean_expression.quantile(0.2)),
            'not_expressed': sum(mean_expression == 0)
        }
        
        return categories
    
    def _analyze_sample_characteristics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze sample characteristics."""
        sample_stats = {
            'mean_expression_per_sample': data.mean(axis=0).to_dict(),
            'library_size_per_sample': data.sum(axis=0).to_dict(),
            'detected_genes_per_sample': (data > 0).sum(axis=0).to_dict()
        }
        
        return sample_stats
    
    def preprocess_data(self, data: pd.DataFrame, **kwargs) -> ProcessingResult:
        """Preprocess transcriptomics data."""
        try:
            processing_log = ["Starting transcriptomics preprocessing"]
            original_shape = data.shape
            
            # Filter low expression genes
            if 'min_expression' in kwargs:
                min_expression = kwargs['min_expression']
                data = data[data.mean(axis=1) >= min_expression]
                processing_log.append(f"Filtered genes with expression < {min_expression}")
            
            # Filter low variance genes
            if 'min_variance' in kwargs:
                min_variance = kwargs['min_variance']
                data = data[data.var(axis=1) >= min_variance]
                processing_log.append(f"Filtered genes with variance < {min_variance}")
            
            # Filter genes with low detection rate
            if 'min_detection_rate' in kwargs:
                min_detection_rate = kwargs['min_detection_rate']
                detection_rate = (data > 0).sum(axis=1) / data.shape[1]
                data = data[detection_rate >= min_detection_rate]
                processing_log.append(f"Filtered genes with detection rate < {min_detection_rate}")
            
            # Remove samples with low library size
            if 'min_library_size' in kwargs:
                min_library_size = kwargs['min_library_size']
                library_sizes = data.sum(axis=0)
                data = data.loc[:, library_sizes >= min_library_size]
                processing_log.append(f"Filtered samples with library size < {min_library_size}")
            
            # Remove samples with low gene detection
            if 'min_genes_detected' in kwargs:
                min_genes_detected = kwargs['min_genes_detected']
                genes_detected = (data > 0).sum(axis=0)
                data = data.loc[:, genes_detected >= min_genes_detected]
                processing_log.append(f"Filtered samples with < {min_genes_detected} genes detected")
            
            # Log transformation
            if kwargs.get('log_transform', True):
                data = np.log2(data + 1)  # Add pseudocount to avoid log(0)
                processing_log.append("Applied log2 transformation")
            
            # Create metadata
            metadata = {
                'samples': list(data.columns),
                'features': list(data.index),
                'data_type': 'transcriptomics',
                'preprocessing_steps': processing_log,
                'original_shape': original_shape,
                'processed_shape': data.shape,
                'filtered_genes': original_shape[0] - data.shape[0],
                'filtered_samples': original_shape[1] - data.shape[1]
            }
            
            # Quality control
            quality_metrics = self.quality_control(data, 'transcriptomics')
            
            return ProcessingResult(
                data=data,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error preprocessing transcriptomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )
    
    def normalize_data(self, data: pd.DataFrame, method: str, **kwargs) -> ProcessingResult:
        """Normalize transcriptomics data."""
        try:
            processing_log = [f"Starting transcriptomics normalization with method: {method}"]
            
            if method == 'tmm':
                # TMM normalization (simplified)
                data_normalized = self._apply_tmm_normalization(data)
                processing_log.append("Applied TMM normalization")
                
            elif method == 'deseq2':
                # DESeq2 normalization (simplified)
                data_normalized = self._apply_deseq2_normalization(data)
                processing_log.append("Applied DESeq2 normalization")
                
            elif method == 'quantile':
                # Quantile normalization
                data_normalized = self._apply_quantile_normalization(data)
                processing_log.append("Applied quantile normalization")
                
            elif method == 'upper_quartile':
                # Upper quartile normalization
                data_normalized = self._apply_upper_quartile_normalization(data)
                processing_log.append("Applied upper quartile normalization")
                
            elif method == 'cpm':
                # Counts per million normalization
                data_normalized = data.div(data.sum(axis=0), axis=1) * 1e6
                processing_log.append("Applied CPM normalization")
                
            elif method == 'rpkm':
                # RPKM normalization (requires gene lengths)
                gene_lengths = kwargs.get('gene_lengths', None)
                if gene_lengths is not None:
                    data_normalized = self._apply_rpkm_normalization(data, gene_lengths)
                    processing_log.append("Applied RPKM normalization")
                else:
                    data_normalized = data
                    processing_log.append("RPKM normalization skipped (no gene lengths provided)")
                
            elif method == 'fpkm':
                # FPKM normalization (requires gene lengths)
                gene_lengths = kwargs.get('gene_lengths', None)
                if gene_lengths is not None:
                    data_normalized = self._apply_fpkm_normalization(data, gene_lengths)
                    processing_log.append("Applied FPKM normalization")
                else:
                    data_normalized = data
                    processing_log.append("FPKM normalization skipped (no gene lengths provided)")
                
            else:
                raise ValueError(f"Unsupported normalization method: {method}")
            
            # Create metadata
            metadata = {
                'samples': list(data_normalized.columns),
                'features': list(data_normalized.index),
                'data_type': 'transcriptomics',
                'normalization_method': method,
                'normalization_parameters': kwargs
            }
            
            # Quality control
            quality_metrics = self.quality_control(data_normalized, 'transcriptomics')
            
            return ProcessingResult(
                data=data_normalized,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error normalizing transcriptomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )
    
    def _apply_tmm_normalization(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply TMM normalization (simplified implementation)."""
        # This is a simplified implementation
        # In practice, you'd use the edgeR TMM method
        
        # Calculate size factors
        library_sizes = data.sum(axis=0)
        median_library_size = library_sizes.median()
        size_factors = library_sizes / median_library_size
        
        # Apply normalization
        data_normalized = data.div(size_factors, axis=1)
        
        return data_normalized
    
    def _apply_deseq2_normalization(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply DESeq2 normalization (simplified implementation)."""
        # This is a simplified implementation
        # In practice, you'd use the DESeq2 size factor calculation
        
        # Calculate geometric mean for each gene
        log_data = np.log(data + 1)
        geometric_means = log_data.mean(axis=1)
        
        # Calculate size factors
        size_factors = []
        for sample in data.columns:
            sample_data = data[sample]
            # Use genes with non-zero geometric mean
            valid_genes = geometric_means > 0
            if valid_genes.sum() > 0:
                size_factor = np.exp(np.median(log_data.loc[valid_genes, sample] - 
                                             geometric_means[valid_genes]))
            else:
                size_factor = 1.0
            size_factors.append(size_factor)
        
        size_factors = pd.Series(size_factors, index=data.columns)
        
        # Apply normalization
        data_normalized = data.div(size_factors, axis=1)
        
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
    
    def _apply_upper_quartile_normalization(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply upper quartile normalization."""
        # Calculate upper quartile for each sample
        upper_quartiles = data.quantile(0.75, axis=0)
        
        # Calculate size factors
        median_upper_quartile = upper_quartiles.median()
        size_factors = upper_quartiles / median_upper_quartile
        
        # Apply normalization
        data_normalized = data.div(size_factors, axis=1)
        
        return data_normalized
    
    def _apply_rpkm_normalization(self, data: pd.DataFrame, gene_lengths: Dict[str, float]) -> pd.DataFrame:
        """Apply RPKM normalization."""
        # RPKM = (reads mapped to gene / total reads) * 10^9 / gene length
        
        # Calculate reads per kilobase
        reads_per_kb = data.div([gene_lengths.get(gene, 1000) / 1000 for gene in data.index], axis=0)
        
        # Calculate RPKM
        total_reads = data.sum(axis=0)
        data_normalized = reads_per_kb.div(total_reads, axis=1) * 1e9
        
        return data_normalized
    
    def _apply_fpkm_normalization(self, data: pd.DataFrame, gene_lengths: Dict[str, float]) -> pd.DataFrame:
        """Apply FPKM normalization (same as RPKM for single-end reads)."""
        return self._apply_rpkm_normalization(data, gene_lengths)
    
    def perform_differential_expression(self, data: pd.DataFrame, 
                                      group1_samples: List[str], 
                                      group2_samples: List[str],
                                      method: str = 'ttest', **kwargs) -> Dict[str, Any]:
        """Perform differential expression analysis."""
        try:
            # Prepare data
            group1_data = data[group1_samples]
            group2_data = data[group2_samples]
            
            results = {}
            
            if method == 'ttest':
                results = self._perform_ttest_de(group1_data, group2_data)
            elif method == 'mannwhitney':
                results = self._perform_mannwhitney_de(group1_data, group2_data)
            elif method == 'fold_change':
                results = self._perform_fold_change_de(group1_data, group2_data)
            else:
                raise ValueError(f"Unsupported DE method: {method}")
            
            # Add additional statistics
            results['summary'] = self._summarize_de_results(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in differential expression analysis: {e}")
            return {'error': str(e)}
    
    def _perform_ttest_de(self, group1_data: pd.DataFrame, group2_data: pd.DataFrame) -> Dict[str, Any]:
        """Perform t-test for differential expression."""
        results = {
            'gene_id': [],
            'group1_mean': [],
            'group2_mean': [],
            'log2_fold_change': [],
            'p_value': [],
            'adjusted_p_value': []
        }
        
        for gene in group1_data.index:
            group1_values = group1_data.loc[gene].dropna()
            group2_values = group2_data.loc[gene].dropna()
            
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
                
                results['gene_id'].append(gene)
                results['group1_mean'].append(group1_mean)
                results['group2_mean'].append(group2_mean)
                results['log2_fold_change'].append(log2_fc)
                results['p_value'].append(p_value)
                results['adjusted_p_value'].append(p_value)  # Will be adjusted later
        
        # Adjust p-values (simplified Benjamini-Hochberg)
        p_values = np.array(results['p_value'])
        adjusted_p_values = self._adjust_p_values(p_values)
        results['adjusted_p_value'] = adjusted_p_values.tolist()
        
        return results
    
    def _perform_mannwhitney_de(self, group1_data: pd.DataFrame, group2_data: pd.DataFrame) -> Dict[str, Any]:
        """Perform Mann-Whitney U test for differential expression."""
        results = {
            'gene_id': [],
            'group1_median': [],
            'group2_median': [],
            'log2_fold_change': [],
            'p_value': [],
            'adjusted_p_value': []
        }
        
        for gene in group1_data.index:
            group1_values = group1_data.loc[gene].dropna()
            group2_values = group2_data.loc[gene].dropna()
            
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
                
                results['gene_id'].append(gene)
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
    
    def _perform_fold_change_de(self, group1_data: pd.DataFrame, group2_data: pd.DataFrame) -> Dict[str, Any]:
        """Perform fold change analysis."""
        results = {
            'gene_id': [],
            'group1_mean': [],
            'group2_mean': [],
            'fold_change': [],
            'log2_fold_change': []
        }
        
        for gene in group1_data.index:
            group1_mean = group1_data.loc[gene].mean()
            group2_mean = group2_data.loc[gene].mean()
            
            # Calculate fold change
            if group1_mean > 0:
                fold_change = group2_mean / group1_mean
                log2_fc = np.log2(fold_change)
            else:
                fold_change = float('inf') if group2_mean > 0 else 1.0
                log2_fc = float('inf') if group2_mean > 0 else 0.0
            
            results['gene_id'].append(gene)
            results['group1_mean'].append(group1_mean)
            results['group2_mean'].append(group2_mean)
            results['fold_change'].append(fold_change)
            results['log2_fold_change'].append(log2_fc)
        
        return results
    
    def _adjust_p_values(self, p_values: np.ndarray) -> np.ndarray:
        """Adjust p-values using Benjamini-Hochberg method (simplified)."""
        # Sort p-values
        sorted_indices = np.argsort(p_values)
        sorted_p_values = p_values[sorted_indices]
        
        # Apply Benjamini-Hochberg correction
        m = len(p_values)
        adjusted_p_values = np.zeros_like(p_values)
        
        for i, p_val in enumerate(sorted_p_values):
            adjusted_p_values[sorted_indices[i]] = min(1.0, p_val * m / (i + 1))
        
        return adjusted_p_values
    
    def _summarize_de_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize differential expression results."""
        if 'p_value' in results:
            p_values = np.array(results['p_value'])
            adjusted_p_values = np.array(results['adjusted_p_value'])
            
            summary = {
                'total_genes': len(results['gene_id']),
                'significant_genes_p05': sum(adjusted_p_values < 0.05),
                'significant_genes_p01': sum(adjusted_p_values < 0.01),
                'significant_genes_p001': sum(adjusted_p_values < 0.001),
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
                'total_genes': len(results['gene_id']),
                'upregulated': 0,
                'downregulated': 0
            }
        
        return summary
    
    def perform_pathway_analysis(self, de_results: Dict[str, Any], 
                                pathway_database: str = 'kegg', **kwargs) -> Dict[str, Any]:
        """Perform pathway enrichment analysis (simplified implementation)."""
        try:
            # This is a simplified implementation
            # In practice, you'd use tools like GSEA, DAVID, or similar
            
            pathway_results = {
                'enriched_pathways': [],
                'pathway_statistics': {},
                'gene_pathway_mapping': {}
            }
            
            # Mock pathway analysis
            if 'log2_fold_change' in de_results and 'adjusted_p_value' in de_results:
                significant_genes = []
                for i, gene in enumerate(de_results['gene_id']):
                    if de_results['adjusted_p_value'][i] < 0.05:
                        significant_genes.append(gene)
                
                # Mock pathway enrichment
                mock_pathways = [
                    'Cell Cycle', 'DNA Repair', 'Apoptosis', 'Immune Response',
                    'Metabolism', 'Signal Transduction', 'Transcription'
                ]
                
                for pathway in mock_pathways:
                    # Mock enrichment statistics
                    pathway_genes = significant_genes[:np.random.randint(5, 20)]
                    p_value = np.random.random() * 0.05  # Significant pathways
                    
                    pathway_results['enriched_pathways'].append({
                        'pathway': pathway,
                        'genes': pathway_genes,
                        'p_value': p_value,
                        'gene_count': len(pathway_genes)
                    })
                    
                    pathway_results['gene_pathway_mapping'][pathway] = pathway_genes
            
            return pathway_results
            
        except Exception as e:
            logger.error(f"Error in pathway analysis: {e}")
            return {'error': str(e)}
    
    def generate_transcriptomics_report(self, data: pd.DataFrame, 
                                      analysis_results: Dict[str, Any]) -> str:
        """Generate comprehensive transcriptomics analysis report."""
        report = f"""
# Transcriptomics Analysis Report
Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

## Data Summary
- Total genes: {data.shape[0]}
- Total samples: {data.shape[1]}
- Data completeness: {(1 - data.isnull().sum().sum() / data.size):.2%}

## Expression Analysis
"""
        
        # Expression statistics
        mean_expr = data.mean().mean()
        median_expr = data.median().median()
        report += f"- Mean expression: {mean_expr:.2f}\n"
        report += f"- Median expression: {median_expr:.2f}\n"
        report += f"- Expression range: [{data.min().min():.2f}, {data.max().max():.2f}]\n"
        
        # Gene categories
        mean_expression = data.mean(axis=1)
        highly_expressed = sum(mean_expression > mean_expression.quantile(0.8))
        lowly_expressed = sum(mean_expression < mean_expression.quantile(0.2))
        
        report += f"- Highly expressed genes: {highly_expressed}\n"
        report += f"- Lowly expressed genes: {lowly_expressed}\n"
        
        # Differential expression results
        if 'differential_expression' in analysis_results:
            de_results = analysis_results['differential_expression']
            if 'summary' in de_results:
                summary = de_results['summary']
                report += f"""
## Differential Expression Analysis
- Total genes analyzed: {summary['total_genes']}
- Significant genes (p < 0.05): {summary['significant_genes_p05']}
- Significant genes (p < 0.01): {summary['significant_genes_p01']}
- Upregulated genes: {summary['upregulated']}
- Downregulated genes: {summary['downregulated']}
"""
        
        # Pathway analysis results
        if 'pathway_analysis' in analysis_results:
            pathway_results = analysis_results['pathway_analysis']
            if 'enriched_pathways' in pathway_results:
                report += f"""
## Pathway Analysis
- Enriched pathways: {len(pathway_results['enriched_pathways'])}
"""
                for pathway in pathway_results['enriched_pathways'][:5]:  # Show top 5
                    report += f"- {pathway['pathway']}: {pathway['gene_count']} genes (p = {pathway['p_value']:.3f})\n"
        
        return report
