"""
Gene Expression Plotter

This module provides the main analysis engine for gene expression data analysis,
integrating various statistical methods and providing comprehensive
expression analysis capabilities for the Cancer Genomics Analysis Suite.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np
from pathlib import Path
import json
import warnings
from scipy import stats
from scipy.cluster.hierarchy import linkage, dendrogram
from scipy.spatial.distance import pdist
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings('ignore')


@dataclass
class ExpressionAnalysisConfig:
    """Configuration for gene expression analysis."""
    # Analysis options
    normalize_data: bool = True
    log_transform: bool = True
    filter_low_expression: bool = True
    perform_clustering: bool = True
    perform_pca: bool = True
    calculate_correlations: bool = True
    
    # Parameters
    min_expression_threshold: float = 1.0
    min_samples_with_expression: int = 3
    log_base: float = 2.0
    pca_components: int = 2
    clustering_method: str = "kmeans"  # kmeans, hierarchical
    n_clusters: int = 3
    
    # Statistical tests
    perform_differential_expression: bool = True
    alpha: float = 0.05
    fold_change_threshold: float = 2.0
    
    # Output options
    generate_plots: bool = True
    export_results: bool = True
    output_format: str = "json"  # json, csv, both


class GeneExpressionPlotter:
    """
    Main gene expression analyzer for comprehensive expression data analysis.
    
    This class provides methods for analyzing gene expression data including
    normalization, statistical analysis, clustering, and visualization.
    """
    
    def __init__(self, config: Optional[ExpressionAnalysisConfig] = None):
        """
        Initialize the gene expression plotter.
        
        Args:
            config (ExpressionAnalysisConfig, optional): Analysis configuration
        """
        self.config = config or ExpressionAnalysisConfig()
        self.logger = logging.getLogger(__name__)
        self.analysis_history = []
        self.expression_data = None
        self.metadata = None
        
    def load_expression_data(self, data: Union[str, pd.DataFrame], 
                           metadata: Optional[Union[str, pd.DataFrame]] = None) -> Dict[str, Any]:
        """
        Load gene expression data from file or DataFrame.
        
        Args:
            data (Union[str, pd.DataFrame]): Expression data file path or DataFrame
            metadata (Union[str, pd.DataFrame], optional): Sample metadata
            
        Returns:
            Dict[str, Any]: Loading results
        """
        self.logger.info("Loading gene expression data...")
        
        try:
            # Load expression data
            if isinstance(data, str):
                if data.endswith('.csv'):
                    self.expression_data = pd.read_csv(data, index_col=0)
                elif data.endswith('.tsv'):
                    self.expression_data = pd.read_csv(data, sep='\t', index_col=0)
                elif data.endswith('.xlsx'):
                    self.expression_data = pd.read_excel(data, index_col=0)
                else:
                    raise ValueError(f"Unsupported file format: {data}")
            else:
                self.expression_data = data.copy()
            
            # Load metadata if provided
            if metadata is not None:
                if isinstance(metadata, str):
                    if metadata.endswith('.csv'):
                        self.metadata = pd.read_csv(metadata, index_col=0)
                    elif metadata.endswith('.tsv'):
                        self.metadata = pd.read_csv(metadata, sep='\t', index_col=0)
                    else:
                        raise ValueError(f"Unsupported metadata file format: {metadata}")
                else:
                    self.metadata = metadata.copy()
            
            # Basic data validation
            validation_results = self._validate_expression_data()
            
            self.logger.info(f"Loaded expression data: {self.expression_data.shape[0]} genes, {self.expression_data.shape[1]} samples")
            
            return {
                'success': True,
                'genes': self.expression_data.shape[0],
                'samples': self.expression_data.shape[1],
                'validation': validation_results
            }
            
        except Exception as e:
            self.logger.error(f"Error loading expression data: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _validate_expression_data(self) -> Dict[str, Any]:
        """Validate expression data quality."""
        if self.expression_data is None:
            return {'valid': False, 'errors': ['No data loaded']}
        
        errors = []
        warnings = []
        
        # Check for missing values
        missing_count = self.expression_data.isnull().sum().sum()
        if missing_count > 0:
            warnings.append(f"Found {missing_count} missing values")
        
        # Check for negative values
        negative_count = (self.expression_data < 0).sum().sum()
        if negative_count > 0:
            warnings.append(f"Found {negative_count} negative values")
        
        # Check data types
        non_numeric_cols = self.expression_data.select_dtypes(exclude=[np.number]).columns
        if len(non_numeric_cols) > 0:
            errors.append(f"Non-numeric columns found: {list(non_numeric_cols)}")
        
        # Check for very low expression
        low_expression_genes = (self.expression_data.max(axis=1) < self.config.min_expression_threshold).sum()
        if low_expression_genes > 0:
            warnings.append(f"{low_expression_genes} genes with very low expression")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'missing_values': missing_count,
            'negative_values': negative_count,
            'low_expression_genes': low_expression_genes
        }
    
    def preprocess_data(self) -> Dict[str, Any]:
        """
        Preprocess expression data (normalization, filtering, transformation).
        
        Returns:
            Dict[str, Any]: Preprocessing results
        """
        if self.expression_data is None:
            return {'success': False, 'error': 'No data loaded'}
        
        self.logger.info("Preprocessing expression data...")
        
        try:
            original_shape = self.expression_data.shape
            processed_data = self.expression_data.copy()
            
            # Handle missing values
            processed_data = processed_data.fillna(0)
            
            # Filter low expression genes
            if self.config.filter_low_expression:
                min_samples = self.config.min_samples_with_expression
                min_threshold = self.config.min_expression_threshold
                
                # Keep genes expressed above threshold in at least min_samples
                mask = (processed_data >= min_threshold).sum(axis=1) >= min_samples
                processed_data = processed_data[mask]
                
                self.logger.info(f"Filtered {original_shape[0] - processed_data.shape[0]} low expression genes")
            
            # Log transformation
            if self.config.log_transform:
                # Add pseudocount to avoid log(0)
                processed_data = np.log2(processed_data + 1)
                self.logger.info("Applied log2 transformation")
            
            # Normalization
            if self.config.normalize_data:
                # Quantile normalization
                processed_data = self._quantile_normalize(processed_data)
                self.logger.info("Applied quantile normalization")
            
            self.expression_data = processed_data
            
            return {
                'success': True,
                'original_shape': original_shape,
                'processed_shape': processed_data.shape,
                'genes_filtered': original_shape[0] - processed_data.shape[0]
            }
            
        except Exception as e:
            self.logger.error(f"Error preprocessing data: {e}")
            return {'success': False, 'error': str(e)}
    
    def _quantile_normalize(self, data: pd.DataFrame) -> pd.DataFrame:
        """Perform quantile normalization."""
        # Sort each column
        sorted_data = np.sort(data.values, axis=0)
        
        # Calculate mean across rows
        mean_values = np.mean(sorted_data, axis=1)
        
        # Create rank matrix
        rank_matrix = np.zeros_like(data.values)
        for i in range(data.shape[1]):
            ranks = stats.rankdata(data.iloc[:, i], method='average')
            rank_matrix[:, i] = ranks - 1  # Convert to 0-based indexing
        
        # Replace values with quantile means
        normalized_data = np.zeros_like(data.values)
        for i in range(data.shape[1]):
            normalized_data[:, i] = mean_values[rank_matrix[:, i].astype(int)]
        
        return pd.DataFrame(normalized_data, index=data.index, columns=data.columns)
    
    def analyze_expression(self) -> Dict[str, Any]:
        """
        Perform comprehensive gene expression analysis.
        
        Returns:
            Dict[str, Any]: Analysis results
        """
        if self.expression_data is None:
            return {'success': False, 'error': 'No data loaded'}
        
        self.logger.info("Performing gene expression analysis...")
        
        try:
            results = {
                'analysis_timestamp': pd.Timestamp.now().isoformat(),
                'data_shape': self.expression_data.shape,
                'genes': list(self.expression_data.index),
                'samples': list(self.expression_data.columns)
            }
            
            # Basic statistics
            results['basic_statistics'] = self._calculate_basic_statistics()
            
            # Correlation analysis
            if self.config.calculate_correlations:
                results['correlations'] = self._calculate_correlations()
            
            # Principal Component Analysis
            if self.config.perform_pca:
                results['pca'] = self._perform_pca()
            
            # Clustering analysis
            if self.config.perform_clustering:
                results['clustering'] = self._perform_clustering()
            
            # Differential expression (if metadata available)
            if self.config.perform_differential_expression and self.metadata is not None:
                results['differential_expression'] = self._perform_differential_expression()
            
            # Store in history
            self.analysis_history.append({
                'timestamp': results['analysis_timestamp'],
                'genes': len(results['genes']),
                'samples': len(results['samples'])
            })
            
            self.logger.info("Gene expression analysis completed")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in expression analysis: {e}")
            return {'success': False, 'error': str(e)}
    
    def _calculate_basic_statistics(self) -> Dict[str, Any]:
        """Calculate basic expression statistics."""
        stats_dict = {
            'mean_expression': float(self.expression_data.mean().mean()),
            'median_expression': float(self.expression_data.median().median()),
            'std_expression': float(self.expression_data.std().mean()),
            'min_expression': float(self.expression_data.min().min()),
            'max_expression': float(self.expression_data.max().max()),
            'zero_expression_percentage': float((self.expression_data == 0).sum().sum() / self.expression_data.size * 100)
        }
        
        # Per-gene statistics
        gene_stats = {
            'mean': self.expression_data.mean(axis=1).to_dict(),
            'std': self.expression_data.std(axis=1).to_dict(),
            'cv': (self.expression_data.std(axis=1) / (self.expression_data.mean(axis=1) + 1e-10)).to_dict()
        }
        
        # Per-sample statistics
        sample_stats = {
            'mean': self.expression_data.mean(axis=0).to_dict(),
            'std': self.expression_data.std(axis=0).to_dict(),
            'total_reads': self.expression_data.sum(axis=0).to_dict()
        }
        
        return {
            'overall': stats_dict,
            'per_gene': gene_stats,
            'per_sample': sample_stats
        }
    
    def _calculate_correlations(self) -> Dict[str, Any]:
        """Calculate correlation matrices."""
        # Gene-gene correlations
        gene_corr = self.expression_data.T.corr()
        
        # Sample-sample correlations
        sample_corr = self.expression_data.corr()
        
        return {
            'gene_correlations': {
                'matrix': gene_corr.to_dict(),
                'mean_correlation': float(gene_corr.values[np.triu_indices_from(gene_corr.values, k=1)].mean())
            },
            'sample_correlations': {
                'matrix': sample_corr.to_dict(),
                'mean_correlation': float(sample_corr.values[np.triu_indices_from(sample_corr.values, k=1)].mean())
            }
        }
    
    def _perform_pca(self) -> Dict[str, Any]:
        """Perform Principal Component Analysis."""
        # Standardize data
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(self.expression_data.T)
        
        # Perform PCA
        pca = PCA(n_components=min(self.config.pca_components, scaled_data.shape[1]))
        pca_result = pca.fit_transform(scaled_data)
        
        # Create results
        pca_df = pd.DataFrame(
            pca_result,
            index=self.expression_data.columns,
            columns=[f'PC{i+1}' for i in range(pca_result.shape[1])]
        )
        
        return {
            'components': pca_df.to_dict(),
            'explained_variance_ratio': pca.explained_variance_ratio_.tolist(),
            'cumulative_variance_ratio': np.cumsum(pca.explained_variance_ratio_).tolist(),
            'loadings': pd.DataFrame(
                pca.components_.T,
                index=self.expression_data.index,
                columns=[f'PC{i+1}' for i in range(pca.components_.shape[0])]
            ).to_dict()
        }
    
    def _perform_clustering(self) -> Dict[str, Any]:
        """Perform clustering analysis."""
        if self.config.clustering_method == "kmeans":
            return self._kmeans_clustering()
        else:
            return self._hierarchical_clustering()
    
    def _kmeans_clustering(self) -> Dict[str, Any]:
        """Perform K-means clustering."""
        # Cluster samples
        kmeans = KMeans(n_clusters=self.config.n_clusters, random_state=42)
        sample_clusters = kmeans.fit_predict(self.expression_data.T)
        
        # Cluster genes
        gene_kmeans = KMeans(n_clusters=self.config.n_clusters, random_state=42)
        gene_clusters = gene_kmeans.fit_predict(self.expression_data)
        
        return {
            'method': 'kmeans',
            'n_clusters': self.config.n_clusters,
            'sample_clusters': {
                sample: int(cluster) for sample, cluster in zip(self.expression_data.columns, sample_clusters)
            },
            'gene_clusters': {
                gene: int(cluster) for gene, cluster in zip(self.expression_data.index, gene_clusters)
            },
            'inertia': float(kmeans.inertia_)
        }
    
    def _hierarchical_clustering(self) -> Dict[str, Any]:
        """Perform hierarchical clustering."""
        # Sample clustering
        sample_distances = pdist(self.expression_data.T, metric='correlation')
        sample_linkage = linkage(sample_distances, method='ward')
        
        # Gene clustering
        gene_distances = pdist(self.expression_data, metric='correlation')
        gene_linkage = linkage(gene_distances, method='ward')
        
        return {
            'method': 'hierarchical',
            'sample_linkage': sample_linkage.tolist(),
            'gene_linkage': gene_linkage.tolist(),
            'sample_distances': sample_distances.tolist(),
            'gene_distances': gene_distances.tolist()
        }
    
    def _perform_differential_expression(self) -> Dict[str, Any]:
        """Perform differential expression analysis."""
        if self.metadata is None:
            return {'error': 'No metadata available for differential expression analysis'}
        
        # Simple t-test between groups (assuming binary groups)
        # This is a simplified implementation
        group_column = self.metadata.columns[0]  # Use first column as group
        groups = self.metadata[group_column].unique()
        
        if len(groups) != 2:
            return {'error': f'Expected 2 groups, found {len(groups)}'}
        
        group1_samples = self.metadata[self.metadata[group_column] == groups[0]].index
        group2_samples = self.metadata[self.metadata[group_column] == groups[1]].index
        
        # Filter samples that exist in expression data
        group1_samples = [s for s in group1_samples if s in self.expression_data.columns]
        group2_samples = [s for s in group2_samples if s in self.expression_data.columns]
        
        if len(group1_samples) == 0 or len(group2_samples) == 0:
            return {'error': 'No samples found in expression data for differential expression'}
        
        # Perform t-tests
        results = []
        for gene in self.expression_data.index:
            group1_expr = self.expression_data.loc[gene, group1_samples]
            group2_expr = self.expression_data.loc[gene, group2_samples]
            
            try:
                t_stat, p_value = stats.ttest_ind(group1_expr, group2_expr)
                fold_change = np.log2(group2_expr.mean() / (group1_expr.mean() + 1e-10))
                
                results.append({
                    'gene': gene,
                    'group1_mean': float(group1_expr.mean()),
                    'group2_mean': float(group2_expr.mean()),
                    'fold_change': float(fold_change),
                    'log2_fold_change': float(fold_change),
                    't_statistic': float(t_stat),
                    'p_value': float(p_value),
                    'significant': p_value < self.config.alpha and abs(fold_change) > np.log2(self.config.fold_change_threshold)
                })
            except:
                results.append({
                    'gene': gene,
                    'group1_mean': float(group1_expr.mean()),
                    'group2_mean': float(group2_expr.mean()),
                    'fold_change': 0.0,
                    'log2_fold_change': 0.0,
                    't_statistic': 0.0,
                    'p_value': 1.0,
                    'significant': False
                })
        
        # Convert to DataFrame for easier handling
        de_results = pd.DataFrame(results)
        
        # Calculate adjusted p-values (Bonferroni correction)
        de_results['adjusted_p_value'] = de_results['p_value'] * len(de_results)
        de_results['adjusted_p_value'] = np.minimum(de_results['adjusted_p_value'], 1.0)
        
        return {
            'comparison': f"{groups[0]} vs {groups[1]}",
            'group1': groups[0],
            'group2': groups[1],
            'group1_samples': group1_samples,
            'group2_samples': group2_samples,
            'results': de_results.to_dict('records'),
            'significant_genes': int(de_results['significant'].sum()),
            'total_genes': len(de_results)
        }
    
    def create_visualizations(self, output_dir: str = "outputs/plots") -> List[str]:
        """
        Create visualization plots for expression analysis.
        
        Args:
            output_dir (str): Output directory for plots
            
        Returns:
            List[str]: List of created plot file paths
        """
        if self.expression_data is None:
            return []
        
        import os
        os.makedirs(output_dir, exist_ok=True)
        plot_files = []
        
        try:
            # 1. Expression distribution
            plt.figure(figsize=(12, 8))
            plt.subplot(2, 2, 1)
            plt.hist(self.expression_data.values.flatten(), bins=50, alpha=0.7)
            plt.title('Expression Value Distribution')
            plt.xlabel('Expression Value')
            plt.ylabel('Frequency')
            
            # 2. Sample correlation heatmap
            plt.subplot(2, 2, 2)
            sample_corr = self.expression_data.corr()
            sns.heatmap(sample_corr, cmap='coolwarm', center=0, square=True)
            plt.title('Sample Correlation Heatmap')
            
            # 3. Gene expression heatmap (top variable genes)
            plt.subplot(2, 2, 3)
            gene_vars = self.expression_data.var(axis=1).sort_values(ascending=False)
            top_genes = gene_vars.head(50).index
            top_data = self.expression_data.loc[top_genes]
            sns.heatmap(top_data, cmap='viridis', cbar_kws={'label': 'Expression'})
            plt.title('Top 50 Most Variable Genes')
            plt.xlabel('Samples')
            plt.ylabel('Genes')
            
            # 4. PCA plot
            plt.subplot(2, 2, 4)
            if hasattr(self, '_pca_result'):
                pca_df = pd.DataFrame(self._pca_result, index=self.expression_data.columns)
                plt.scatter(pca_df.iloc[:, 0], pca_df.iloc[:, 1], alpha=0.7)
                plt.xlabel('PC1')
                plt.ylabel('PC2')
                plt.title('PCA Plot')
            
            plt.tight_layout()
            plot_file = os.path.join(output_dir, 'expression_overview.png')
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            plt.close()
            plot_files.append(plot_file)
            
        except Exception as e:
            self.logger.error(f"Error creating visualizations: {e}")
        
        return plot_files
    
    def export_results(self, results: Dict[str, Any], output_path: str) -> str:
        """
        Export analysis results to file.
        
        Args:
            results (Dict[str, Any]): Analysis results
            output_path (str): Output file path
            
        Returns:
            str: Path to exported file
        """
        self.logger.info(f"Exporting results to: {output_path}")
        
        if output_path.endswith('.json'):
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
        elif output_path.endswith('.csv'):
            # Export differential expression results if available
            if 'differential_expression' in results:
                de_df = pd.DataFrame(results['differential_expression']['results'])
                de_df.to_csv(output_path, index=False)
            else:
                # Export basic statistics
                stats_df = pd.DataFrame([results['basic_statistics']['overall']])
                stats_df.to_csv(output_path, index=False)
        else:
            # Default to JSON
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
        
        self.logger.info(f"Results exported to: {output_path}")
        return output_path
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """
        Get summary of all analyses performed.
        
        Returns:
            Dict[str, Any]: Analysis summary
        """
        return {
            'total_analyses': len(self.analysis_history),
            'analysis_history': self.analysis_history,
            'current_data_shape': self.expression_data.shape if self.expression_data is not None else None,
            'config': {
                'normalize_data': self.config.normalize_data,
                'log_transform': self.config.log_transform,
                'filter_low_expression': self.config.filter_low_expression,
                'perform_clustering': self.config.perform_clustering,
                'perform_pca': self.config.perform_pca,
                'calculate_correlations': self.config.calculate_correlations,
                'perform_differential_expression': self.config.perform_differential_expression
            }
        }
    
    def clear_analysis_history(self):
        """Clear the analysis history."""
        self.analysis_history = []
        self.logger.info("Analysis history cleared")
