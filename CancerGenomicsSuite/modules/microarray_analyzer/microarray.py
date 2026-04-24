"""
Microarray Analyzer Module

This module provides comprehensive functionality for analyzing microarray data,
including data preprocessing, normalization, differential expression analysis,
clustering, and pathway enrichment analysis.
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import json
from pathlib import Path
import warnings
from scipy import stats
from scipy.cluster.hierarchy import linkage, dendrogram
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import seaborn as sns

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MicroarrayData:
    """Represents microarray expression data with metadata."""
    expression_matrix: pd.DataFrame
    sample_metadata: pd.DataFrame
    gene_metadata: pd.DataFrame
    platform: str
    normalization_method: str
    quality_metrics: Dict[str, Any]
    timestamp: datetime
    
    def __post_init__(self):
        """Validate microarray data."""
        if self.expression_matrix.empty:
            raise ValueError("Expression matrix cannot be empty")
        if self.sample_metadata.empty:
            raise ValueError("Sample metadata cannot be empty")
        if self.gene_metadata.empty:
            raise ValueError("Gene metadata cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert microarray data to dictionary."""
        return {
            "expression_matrix": self.expression_matrix.to_dict(),
            "sample_metadata": self.sample_metadata.to_dict(),
            "gene_metadata": self.gene_metadata.to_dict(),
            "platform": self.platform,
            "normalization_method": self.normalization_method,
            "quality_metrics": self.quality_metrics,
            "timestamp": self.timestamp.isoformat()
        }
    
    def get_shape(self) -> Tuple[int, int]:
        """Get dimensions of expression matrix (genes, samples)."""
        return self.expression_matrix.shape
    
    def get_gene_count(self) -> int:
        """Get number of genes."""
        return self.expression_matrix.shape[0]
    
    def get_sample_count(self) -> int:
        """Get number of samples."""
        return self.expression_matrix.shape[1]


@dataclass
class DifferentialExpressionResult:
    """Represents results from differential expression analysis."""
    gene_id: str
    gene_symbol: str
    log2_fold_change: float
    p_value: float
    adjusted_p_value: float
    t_statistic: float
    mean_expression: float
    group1_mean: float
    group2_mean: float
    significant: bool
    effect_size: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return asdict(self)


@dataclass
class ClusteringResult:
    """Represents clustering analysis results."""
    cluster_labels: List[int]
    cluster_centers: Optional[np.ndarray]
    silhouette_score: float
    method: str
    parameters: Dict[str, Any]
    gene_clusters: Dict[int, List[str]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert clustering result to dictionary."""
        return {
            "cluster_labels": self.cluster_labels,
            "cluster_centers": self.cluster_centers.tolist() if self.cluster_centers is not None else None,
            "silhouette_score": self.silhouette_score,
            "method": self.method,
            "parameters": self.parameters,
            "gene_clusters": self.gene_clusters
        }


class MicroarrayAnalyzer:
    """
    Main class for microarray data analysis.
    """
    
    def __init__(self, data: Optional[MicroarrayData] = None):
        """
        Initialize the microarray analyzer.
        
        Args:
            data: MicroarrayData object to analyze
        """
        self.data = data
        self.normalized_data: Optional[MicroarrayData] = None
        self.differential_results: List[DifferentialExpressionResult] = []
        self.clustering_results: Optional[ClusteringResult] = None
        self.pca_results: Optional[Dict[str, Any]] = None
        
        # Analysis parameters
        self.fold_change_threshold = 1.5
        self.p_value_threshold = 0.05
        self.adjusted_p_value_threshold = 0.05
        
        # Supported platforms
        self.supported_platforms = [
            "Affymetrix", "Illumina", "Agilent", "NimbleGen", "Custom"
        ]
        
        # Supported normalization methods
        self.normalization_methods = [
            "quantile", "rma", "gcrma", "mas5", "loess", "vsn", "none"
        ]
    
    def load_data(self, expression_file: str, sample_metadata_file: str, 
                  gene_metadata_file: str, platform: str = "Custom") -> MicroarrayData:
        """
        Load microarray data from files.
        
        Args:
            expression_file: Path to expression matrix file
            sample_metadata_file: Path to sample metadata file
            gene_metadata_file: Path to gene metadata file
            platform: Microarray platform name
            
        Returns:
            MicroarrayData object
        """
        try:
            # Load expression matrix
            if expression_file.endswith('.csv'):
                expression_matrix = pd.read_csv(expression_file, index_col=0)
            elif expression_file.endswith('.tsv'):
                expression_matrix = pd.read_csv(expression_file, sep='\t', index_col=0)
            else:
                raise ValueError("Unsupported file format. Use CSV or TSV.")
            
            # Load sample metadata
            if sample_metadata_file.endswith('.csv'):
                sample_metadata = pd.read_csv(sample_metadata_file, index_col=0)
            elif sample_metadata_file.endswith('.tsv'):
                sample_metadata = pd.read_csv(sample_metadata_file, sep='\t', index_col=0)
            else:
                raise ValueError("Unsupported file format. Use CSV or TSV.")
            
            # Load gene metadata
            if gene_metadata_file.endswith('.csv'):
                gene_metadata = pd.read_csv(gene_metadata_file, index_col=0)
            elif gene_metadata_file.endswith('.tsv'):
                gene_metadata = pd.read_csv(gene_metadata_file, sep='\t', index_col=0)
            else:
                raise ValueError("Unsupported file format. Use CSV or TSV.")
            
            # Validate data consistency
            if expression_matrix.shape[1] != sample_metadata.shape[0]:
                raise ValueError("Number of samples in expression matrix and metadata don't match")
            
            if expression_matrix.shape[0] != gene_metadata.shape[0]:
                raise ValueError("Number of genes in expression matrix and metadata don't match")
            
            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(expression_matrix)
            
            self.data = MicroarrayData(
                expression_matrix=expression_matrix,
                sample_metadata=sample_metadata,
                gene_metadata=gene_metadata,
                platform=platform,
                normalization_method="none",
                quality_metrics=quality_metrics,
                timestamp=datetime.now()
            )
            
            logger.info(f"Loaded microarray data: {expression_matrix.shape[0]} genes, {expression_matrix.shape[1]} samples")
            return self.data
            
        except Exception as e:
            logger.error(f"Error loading microarray data: {e}")
            raise
    
    def _calculate_quality_metrics(self, expression_matrix: pd.DataFrame) -> Dict[str, Any]:
        """Calculate quality metrics for the expression matrix."""
        metrics = {
            "mean_expression": float(expression_matrix.mean().mean()),
            "median_expression": float(expression_matrix.median().median()),
            "std_expression": float(expression_matrix.std().mean()),
            "missing_values": int(expression_matrix.isnull().sum().sum()),
            "zero_values": int((expression_matrix == 0).sum().sum()),
            "negative_values": int((expression_matrix < 0).sum().sum()),
            "min_value": float(expression_matrix.min().min()),
            "max_value": float(expression_matrix.max().max()),
            "cv_mean": float((expression_matrix.std() / expression_matrix.mean()).mean())
        }
        return metrics
    
    def normalize_data(self, method: str = "quantile", **kwargs) -> MicroarrayData:
        """
        Normalize microarray data using specified method.
        
        Args:
            method: Normalization method to use
            **kwargs: Additional parameters for normalization
            
        Returns:
            Normalized MicroarrayData object
        """
        if self.data is None:
            raise ValueError("No data loaded. Load data first.")
        
        if method not in self.normalization_methods:
            raise ValueError(f"Unsupported normalization method: {method}")
        
        logger.info(f"Normalizing data using {method} method")
        
        expression_matrix = self.data.expression_matrix.copy()
        
        if method == "quantile":
            normalized_matrix = self._quantile_normalize(expression_matrix)
        elif method == "rma":
            normalized_matrix = self._rma_normalize(expression_matrix)
        elif method == "loess":
            normalized_matrix = self._loess_normalize(expression_matrix)
        elif method == "vsn":
            normalized_matrix = self._vsn_normalize(expression_matrix)
        elif method == "none":
            normalized_matrix = expression_matrix
        else:
            # Default to quantile normalization
            normalized_matrix = self._quantile_normalize(expression_matrix)
        
        # Calculate quality metrics for normalized data
        quality_metrics = self._calculate_quality_metrics(normalized_matrix)
        
        self.normalized_data = MicroarrayData(
            expression_matrix=normalized_matrix,
            sample_metadata=self.data.sample_metadata,
            gene_metadata=self.data.gene_metadata,
            platform=self.data.platform,
            normalization_method=method,
            quality_metrics=quality_metrics,
            timestamp=datetime.now()
        )
        
        logger.info("Data normalization completed")
        return self.normalized_data
    
    def _quantile_normalize(self, expression_matrix: pd.DataFrame) -> pd.DataFrame:
        """Perform quantile normalization."""
        # Convert to numpy array for processing
        data = expression_matrix.values
        
        # Sort each column
        sorted_data = np.sort(data, axis=0)
        
        # Calculate mean of each row
        mean_values = np.mean(sorted_data, axis=1)
        
        # Get ranks for each column
        ranks = np.zeros_like(data)
        for i in range(data.shape[1]):
            ranks[:, i] = stats.rankdata(data[:, i], method='average')
        
        # Replace values with quantile means
        normalized_data = np.zeros_like(data)
        for i in range(data.shape[1]):
            normalized_data[:, i] = mean_values[ranks[:, i].astype(int) - 1]
        
        return pd.DataFrame(normalized_data, 
                          index=expression_matrix.index, 
                          columns=expression_matrix.columns)
    
    def _rma_normalize(self, expression_matrix: pd.DataFrame) -> pd.DataFrame:
        """Perform RMA (Robust Multi-array Average) normalization."""
        # Simplified RMA normalization
        # In practice, this would involve background correction and summarization
        log_data = np.log2(expression_matrix + 1)
        return self._quantile_normalize(log_data)
    
    def _loess_normalize(self, expression_matrix: pd.DataFrame) -> pd.DataFrame:
        """Perform LOESS normalization."""
        # Simplified LOESS normalization
        # In practice, this would involve fitting LOESS curves
        normalized_data = expression_matrix.copy()
        for col in expression_matrix.columns:
            # Simple linear normalization as approximation
            col_data = expression_matrix[col]
            normalized_data[col] = (col_data - col_data.mean()) / col_data.std()
        return normalized_data
    
    def _vsn_normalize(self, expression_matrix: pd.DataFrame) -> pd.DataFrame:
        """Perform VSN (Variance Stabilizing Normalization)."""
        # Simplified VSN normalization
        # In practice, this would use the vsn package
        log_data = np.log2(expression_matrix + 1)
        return log_data
    
    def perform_differential_expression(self, group_column: str, 
                                      group1: str, group2: str,
                                      use_normalized: bool = True) -> List[DifferentialExpressionResult]:
        """
        Perform differential expression analysis between two groups.
        
        Args:
            group_column: Column name in sample metadata for grouping
            group1: Name of first group
            group2: Name of second group
            use_normalized: Whether to use normalized data
            
        Returns:
            List of DifferentialExpressionResult objects
        """
        if self.data is None:
            raise ValueError("No data loaded. Load data first.")
        
        data_to_use = self.normalized_data if use_normalized and self.normalized_data is not None else self.data
        
        if group_column not in data_to_use.sample_metadata.columns:
            raise ValueError(f"Group column '{group_column}' not found in sample metadata")
        
        # Get sample indices for each group
        group1_samples = data_to_use.sample_metadata[
            data_to_use.sample_metadata[group_column] == group1
        ].index.tolist()
        
        group2_samples = data_to_use.sample_metadata[
            data_to_use.sample_metadata[group_column] == group2
        ].index.tolist()
        
        if not group1_samples or not group2_samples:
            raise ValueError(f"Groups '{group1}' or '{group2}' not found in metadata")
        
        logger.info(f"Performing differential expression analysis: {group1} vs {group2}")
        logger.info(f"Group 1 samples: {len(group1_samples)}, Group 2 samples: {len(group2_samples)}")
        
        results = []
        expression_matrix = data_to_use.expression_matrix
        
        for gene_id in expression_matrix.index:
            gene_symbol = data_to_use.gene_metadata.loc[gene_id, 'gene_symbol'] if 'gene_symbol' in data_to_use.gene_metadata.columns else gene_id
            
            # Get expression values for each group
            group1_values = expression_matrix.loc[gene_id, group1_samples].values
            group2_values = expression_matrix.loc[gene_id, group2_samples].values
            
            # Calculate statistics
            group1_mean = np.mean(group1_values)
            group2_mean = np.mean(group2_values)
            mean_expression = np.mean([group1_mean, group2_mean])
            
            # Calculate fold change
            if group1_mean > 0 and group2_mean > 0:
                fold_change = group2_mean / group1_mean
                log2_fold_change = np.log2(fold_change)
            else:
                log2_fold_change = 0.0
            
            # Perform t-test
            try:
                t_stat, p_value = stats.ttest_ind(group1_values, group2_values)
            except:
                t_stat, p_value = 0.0, 1.0
            
            # Calculate effect size (Cohen's d)
            pooled_std = np.sqrt(((len(group1_values) - 1) * np.var(group1_values, ddof=1) + 
                                 (len(group2_values) - 1) * np.var(group2_values, ddof=1)) / 
                                (len(group1_values) + len(group2_values) - 2))
            
            if pooled_std > 0:
                effect_size = (group2_mean - group1_mean) / pooled_std
            else:
                effect_size = 0.0
            
            # Determine significance
            significant = (abs(log2_fold_change) >= np.log2(self.fold_change_threshold) and 
                          p_value < self.p_value_threshold)
            
            result = DifferentialExpressionResult(
                gene_id=gene_id,
                gene_symbol=gene_symbol,
                log2_fold_change=log2_fold_change,
                p_value=p_value,
                adjusted_p_value=p_value,  # Will be adjusted later
                t_statistic=t_stat,
                mean_expression=mean_expression,
                group1_mean=group1_mean,
                group2_mean=group2_mean,
                significant=significant,
                effect_size=effect_size
            )
            
            results.append(result)
        
        # Adjust p-values using Benjamini-Hochberg method
        p_values = [r.p_value for r in results]
        adjusted_p_values = self._adjust_p_values(p_values)
        
        for i, result in enumerate(results):
            result.adjusted_p_value = adjusted_p_values[i]
            result.significant = (abs(result.log2_fold_change) >= np.log2(self.fold_change_threshold) and 
                                result.adjusted_p_value < self.adjusted_p_value_threshold)
        
        self.differential_results = results
        
        significant_count = sum(1 for r in results if r.significant)
        logger.info(f"Differential expression analysis completed. {significant_count} significant genes found.")
        
        return results
    
    def _adjust_p_values(self, p_values: List[float]) -> List[float]:
        """Adjust p-values using Benjamini-Hochberg method."""
        from statsmodels.stats.multitest import multipletests
        _, adjusted_p_values, _, _ = multipletests(p_values, method='fdr_bh')
        return adjusted_p_values.tolist()
    
    def perform_clustering(self, method: str = "kmeans", n_clusters: int = 3,
                          use_normalized: bool = True, **kwargs) -> ClusteringResult:
        """
        Perform clustering analysis on gene expression data.
        
        Args:
            method: Clustering method ('kmeans', 'hierarchical')
            n_clusters: Number of clusters
            use_normalized: Whether to use normalized data
            **kwargs: Additional parameters for clustering
            
        Returns:
            ClusteringResult object
        """
        if self.data is None:
            raise ValueError("No data loaded. Load data first.")
        
        data_to_use = self.normalized_data if use_normalized and self.normalized_data is not None else self.data
        
        logger.info(f"Performing {method} clustering with {n_clusters} clusters")
        
        expression_matrix = data_to_use.expression_matrix
        
        # Standardize data for clustering
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(expression_matrix.T)  # Transpose for sample clustering
        
        if method == "kmeans":
            clusterer = KMeans(n_clusters=n_clusters, random_state=42, **kwargs)
            cluster_labels = clusterer.fit_predict(scaled_data)
            cluster_centers = clusterer.cluster_centers_
            
        elif method == "hierarchical":
            linkage_matrix = linkage(scaled_data, method='ward')
            # For hierarchical clustering, we need to cut the tree
            from scipy.cluster.hierarchy import fcluster
            cluster_labels = fcluster(linkage_matrix, n_clusters, criterion='maxclust') - 1
            cluster_centers = None
            
        else:
            raise ValueError(f"Unsupported clustering method: {method}")
        
        # Calculate silhouette score
        from sklearn.metrics import silhouette_score
        silhouette_avg = silhouette_score(scaled_data, cluster_labels)
        
        # Group genes by cluster
        gene_clusters = {}
        for i, label in enumerate(cluster_labels):
            if label not in gene_clusters:
                gene_clusters[label] = []
            gene_clusters[label].append(expression_matrix.columns[i])
        
        self.clustering_results = ClusteringResult(
            cluster_labels=cluster_labels.tolist(),
            cluster_centers=cluster_centers,
            silhouette_score=silhouette_avg,
            method=method,
            parameters={"n_clusters": n_clusters, **kwargs},
            gene_clusters=gene_clusters
        )
        
        logger.info(f"Clustering completed. Silhouette score: {silhouette_avg:.3f}")
        return self.clustering_results
    
    def perform_pca(self, n_components: int = 2, use_normalized: bool = True) -> Dict[str, Any]:
        """
        Perform Principal Component Analysis.
        
        Args:
            n_components: Number of principal components
            use_normalized: Whether to use normalized data
            
        Returns:
            Dictionary with PCA results
        """
        if self.data is None:
            raise ValueError("No data loaded. Load data first.")
        
        data_to_use = self.normalized_data if use_normalized and self.normalized_data is not None else self.data
        
        logger.info(f"Performing PCA with {n_components} components")
        
        expression_matrix = data_to_use.expression_matrix
        
        # Standardize data
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(expression_matrix.T)  # Transpose for sample PCA
        
        # Perform PCA
        pca = PCA(n_components=n_components)
        pca_result = pca.fit_transform(scaled_data)
        
        # Calculate explained variance
        explained_variance_ratio = pca.explained_variance_ratio_
        cumulative_variance = np.cumsum(explained_variance_ratio)
        
        self.pca_results = {
            "components": pca_result.tolist(),
            "explained_variance_ratio": explained_variance_ratio.tolist(),
            "cumulative_variance": cumulative_variance.tolist(),
            "feature_names": expression_matrix.columns.tolist(),
            "n_components": n_components
        }
        
        logger.info(f"PCA completed. Explained variance: {explained_variance_ratio}")
        return self.pca_results
    
    def get_top_differentially_expressed(self, n: int = 100, 
                                       sort_by: str = "p_value") -> List[DifferentialExpressionResult]:
        """
        Get top differentially expressed genes.
        
        Args:
            n: Number of top genes to return
            sort_by: Sort criteria ('p_value', 'fold_change', 'effect_size')
            
        Returns:
            List of top DifferentialExpressionResult objects
        """
        if not self.differential_results:
            raise ValueError("No differential expression results available. Run analysis first.")
        
        if sort_by == "p_value":
            sorted_results = sorted(self.differential_results, key=lambda x: x.p_value)
        elif sort_by == "fold_change":
            sorted_results = sorted(self.differential_results, key=lambda x: abs(x.log2_fold_change), reverse=True)
        elif sort_by == "effect_size":
            sorted_results = sorted(self.differential_results, key=lambda x: abs(x.effect_size), reverse=True)
        else:
            raise ValueError(f"Unsupported sort criteria: {sort_by}")
        
        return sorted_results[:n]
    
    def export_results(self, format: str = "json") -> str:
        """
        Export analysis results.
        
        Args:
            format: Export format ('json', 'csv', 'tsv')
            
        Returns:
            Exported data as string
        """
        results = {
            "differential_expression": [r.to_dict() for r in self.differential_results],
            "clustering": self.clustering_results.to_dict() if self.clustering_results else None,
            "pca": self.pca_results,
            "export_timestamp": datetime.now().isoformat()
        }
        
        if format == "json":
            return json.dumps(results, indent=2)
        elif format == "csv":
            if self.differential_results:
                df = pd.DataFrame([r.to_dict() for r in self.differential_results])
                return df.to_csv(index=False)
            else:
                return "No differential expression results to export"
        elif format == "tsv":
            if self.differential_results:
                df = pd.DataFrame([r.to_dict() for r in self.differential_results])
                return df.to_csv(index=False, sep='\t')
            else:
                return "No differential expression results to export"
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the analyzer and data.
        
        Returns:
            Dictionary with analyzer statistics
        """
        stats = {
            "data_loaded": self.data is not None,
            "normalized_data_available": self.normalized_data is not None,
            "differential_results_count": len(self.differential_results),
            "clustering_performed": self.clustering_results is not None,
            "pca_performed": self.pca_results is not None,
            "supported_platforms": self.supported_platforms,
            "normalization_methods": self.normalization_methods
        }
        
        if self.data:
            stats.update({
                "data_shape": self.data.get_shape(),
                "platform": self.data.platform,
                "normalization_method": self.data.normalization_method,
                "quality_metrics": self.data.quality_metrics
            })
        
        return stats


def create_sample_microarray_data() -> MicroarrayData:
    """
    Create sample microarray data for testing.
    
    Returns:
        MicroarrayData object with sample data
    """
    # Generate sample expression data
    np.random.seed(42)
    n_genes = 1000
    n_samples = 20
    
    # Create expression matrix
    expression_matrix = pd.DataFrame(
        np.random.lognormal(mean=5, sigma=1, size=(n_genes, n_samples)),
        index=[f"Gene_{i:04d}" for i in range(n_genes)],
        columns=[f"Sample_{i:02d}" for i in range(n_samples)]
    )
    
    # Create sample metadata
    sample_metadata = pd.DataFrame({
        'group': ['Control'] * 10 + ['Treatment'] * 10,
        'batch': ['Batch1'] * 5 + ['Batch2'] * 5 + ['Batch1'] * 5 + ['Batch2'] * 5,
        'age': np.random.randint(20, 80, n_samples),
        'gender': np.random.choice(['M', 'F'], n_samples)
    }, index=expression_matrix.columns)
    
    # Create gene metadata
    gene_metadata = pd.DataFrame({
        'gene_symbol': [f"GENE_{i:04d}" for i in range(n_genes)],
        'chromosome': np.random.choice([f"chr{i}" for i in range(1, 23)] + ['chrX', 'chrY'], n_genes),
        'gene_type': np.random.choice(['protein_coding', 'lncRNA', 'miRNA'], n_genes),
        'description': [f"Description for gene {i}" for i in range(n_genes)]
    }, index=expression_matrix.index)
    
    # Calculate quality metrics
    quality_metrics = {
        "mean_expression": float(expression_matrix.mean().mean()),
        "median_expression": float(expression_matrix.median().median()),
        "std_expression": float(expression_matrix.std().mean()),
        "missing_values": 0,
        "zero_values": 0,
        "negative_values": 0,
        "min_value": float(expression_matrix.min().min()),
        "max_value": float(expression_matrix.max().max()),
        "cv_mean": float((expression_matrix.std() / expression_matrix.mean()).mean())
    }
    
    return MicroarrayData(
        expression_matrix=expression_matrix,
        sample_metadata=sample_metadata,
        gene_metadata=gene_metadata,
        platform="Custom",
        normalization_method="none",
        quality_metrics=quality_metrics,
        timestamp=datetime.now()
    )


def create_sample_analyzer() -> MicroarrayAnalyzer:
    """
    Create a sample analyzer with example data.
    
    Returns:
        MicroarrayAnalyzer instance
    """
    analyzer = MicroarrayAnalyzer()
    sample_data = create_sample_microarray_data()
    analyzer.data = sample_data
    
    # Perform some sample analyses
    analyzer.normalize_data("quantile")
    analyzer.perform_differential_expression("group", "Control", "Treatment")
    analyzer.perform_clustering("kmeans", n_clusters=3)
    analyzer.perform_pca(n_components=2)
    
    return analyzer


if __name__ == "__main__":
    # Example usage
    analyzer = create_sample_analyzer()
    
    print("Microarray Analyzer Statistics:")
    stats = analyzer.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\nTop 10 Differentially Expressed Genes:")
    top_genes = analyzer.get_top_differentially_expressed(n=10, sort_by="p_value")
    for gene in top_genes:
        print(f"  {gene.gene_symbol}: FC={gene.log2_fold_change:.3f}, p={gene.p_value:.3e}, significant={gene.significant}")
    
    print("\nClustering Results:")
    if analyzer.clustering_results:
        print(f"  Method: {analyzer.clustering_results.method}")
        print(f"  Silhouette Score: {analyzer.clustering_results.silhouette_score:.3f}")
        print(f"  Number of clusters: {len(set(analyzer.clustering_results.cluster_labels))}")
    
    print("\nPCA Results:")
    if analyzer.pca_results:
        print(f"  Explained variance: {analyzer.pca_results['explained_variance_ratio']}")
        print(f"  Cumulative variance: {analyzer.pca_results['cumulative_variance']}")
