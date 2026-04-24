"""
Multi-Omics Integrator Module

This module provides comprehensive functionality for integrating and analyzing
multiple omics data types in cancer genomics research.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import seaborn as sns
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional, Any, Union
import json
import logging
from pathlib import Path
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA, ICA
from sklearn.manifold import TSNE, UMAP
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import silhouette_score
from scipy import stats
from scipy.cluster.hierarchy import dendrogram, linkage
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultiOmicsIntegrator:
    """
    A comprehensive class for integrating and analyzing multiple omics data types.
    """
    
    def __init__(self):
        """Initialize the multi-omics integrator."""
        self.omics_data = {}
        self.integrated_data = None
        self.sample_metadata = None
        self.feature_metadata = {}
        self.integration_results = {}
        self.scalers = {}
        
    def load_omics_data(self, data_type: str, file_path: str, 
                       sample_col: str = 'sample_id', 
                       feature_col: str = None) -> pd.DataFrame:
        """
        Load omics data from various file formats.
        
        Args:
            data_type: Type of omics data (e.g., 'expression', 'methylation', 'mutation')
            file_path: Path to the data file
            sample_col: Column name containing sample IDs
            feature_col: Column name containing feature IDs (genes, CpGs, etc.)
            
        Returns:
            DataFrame containing the loaded omics data
        """
        try:
            # Load data based on file extension
            if file_path.endswith('.csv'):
                data = pd.read_csv(file_path)
            elif file_path.endswith('.tsv'):
                data = pd.read_csv(file_path, sep='\t')
            elif file_path.endswith('.xlsx'):
                data = pd.read_excel(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_path}")
            
            # Set index if feature column is specified
            if feature_col and feature_col in data.columns:
                data = data.set_index(feature_col)
            
            # Store data
            self.omics_data[data_type] = data
            
            # Initialize feature metadata
            if data_type not in self.feature_metadata:
                self.feature_metadata[data_type] = {
                    'features': list(data.index) if feature_col else list(data.columns),
                    'samples': list(data.columns) if feature_col else list(data.index),
                    'data_type': data_type
                }
            
            logger.info(f"Loaded {data_type} data: {data.shape[0]} features, {data.shape[1]} samples")
            return data
            
        except Exception as e:
            logger.error(f"Error loading {data_type} data: {e}")
            raise
    
    def load_sample_metadata(self, file_path: str, sample_col: str = 'sample_id') -> pd.DataFrame:
        """
        Load sample metadata.
        
        Args:
            file_path: Path to the metadata file
            sample_col: Column name containing sample IDs
            
        Returns:
            DataFrame containing sample metadata
        """
        try:
            if file_path.endswith('.csv'):
                metadata = pd.read_csv(file_path)
            elif file_path.endswith('.tsv'):
                metadata = pd.read_csv(file_path, sep='\t')
            elif file_path.endswith('.xlsx'):
                metadata = pd.read_excel(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_path}")
            
            self.sample_metadata = metadata.set_index(sample_col)
            logger.info(f"Loaded sample metadata: {metadata.shape[0]} samples, {metadata.shape[1]} features")
            return self.sample_metadata
            
        except Exception as e:
            logger.error(f"Error loading sample metadata: {e}")
            raise
    
    def normalize_data(self, data_type: str, method: str = 'zscore') -> pd.DataFrame:
        """
        Normalize omics data using various methods.
        
        Args:
            data_type: Type of omics data to normalize
            method: Normalization method ('zscore', 'minmax', 'quantile', 'log2')
            
        Returns:
            Normalized DataFrame
        """
        if data_type not in self.omics_data:
            raise ValueError(f"Data type {data_type} not found")
        
        data = self.omics_data[data_type].copy()
        
        try:
            if method == 'zscore':
                scaler = StandardScaler()
                normalized_data = pd.DataFrame(
                    scaler.fit_transform(data.T).T,
                    index=data.index,
                    columns=data.columns
                )
                self.scalers[data_type] = scaler
                
            elif method == 'minmax':
                scaler = MinMaxScaler()
                normalized_data = pd.DataFrame(
                    scaler.fit_transform(data.T).T,
                    index=data.index,
                    columns=data.columns
                )
                self.scalers[data_type] = scaler
                
            elif method == 'quantile':
                # Quantile normalization
                normalized_data = data.rank(method='min').apply(
                    lambda x: stats.norm.ppf(x / (len(x) + 1))
                )
                
            elif method == 'log2':
                # Log2 transformation with pseudocount
                normalized_data = np.log2(data + 1)
                
            else:
                raise ValueError(f"Unknown normalization method: {method}")
            
            # Update stored data
            self.omics_data[data_type] = normalized_data
            
            logger.info(f"Normalized {data_type} data using {method} method")
            return normalized_data
            
        except Exception as e:
            logger.error(f"Error normalizing {data_type} data: {e}")
            raise
    
    def integrate_omics_data(self, integration_method: str = 'concatenation',
                           normalization: bool = True) -> pd.DataFrame:
        """
        Integrate multiple omics data types.
        
        Args:
            integration_method: Method for integration ('concatenation', 'pca', 'ica')
            normalization: Whether to normalize data before integration
            
        Returns:
            Integrated DataFrame
        """
        if not self.omics_data:
            raise ValueError("No omics data loaded")
        
        try:
            # Normalize data if requested
            if normalization:
                for data_type in self.omics_data.keys():
                    if data_type not in self.scalers:
                        self.normalize_data(data_type, method='zscore')
            
            if integration_method == 'concatenation':
                # Simple concatenation of features
                integrated_data = pd.concat(
                    [self.omics_data[data_type] for data_type in self.omics_data.keys()],
                    axis=0
                )
                
            elif integration_method == 'pca':
                # PCA-based integration
                integrated_data = self._pca_integration()
                
            elif integration_method == 'ica':
                # ICA-based integration
                integrated_data = self._ica_integration()
                
            else:
                raise ValueError(f"Unknown integration method: {integration_method}")
            
            self.integrated_data = integrated_data
            
            # Store integration results
            self.integration_results = {
                'method': integration_method,
                'normalization': normalization,
                'data_types': list(self.omics_data.keys()),
                'shape': integrated_data.shape
            }
            
            logger.info(f"Integrated omics data using {integration_method}: {integrated_data.shape}")
            return integrated_data
            
        except Exception as e:
            logger.error(f"Error integrating omics data: {e}")
            raise
    
    def _pca_integration(self) -> pd.DataFrame:
        """Perform PCA-based integration."""
        # Concatenate all data
        concatenated_data = pd.concat(
            [self.omics_data[data_type] for data_type in self.omics_data.keys()],
            axis=0
        )
        
        # Fill missing values
        concatenated_data = concatenated_data.fillna(concatenated_data.mean())
        
        # Perform PCA
        pca = PCA(n_components=min(50, concatenated_data.shape[0], concatenated_data.shape[1]))
        pca_result = pca.fit_transform(concatenated_data.T)
        
        # Create DataFrame
        pca_df = pd.DataFrame(
            pca_result.T,
            index=[f'PC{i+1}' for i in range(pca_result.shape[1])],
            columns=concatenated_data.columns
        )
        
        # Store PCA results
        self.integration_results['pca'] = {
            'explained_variance_ratio': pca.explained_variance_ratio_,
            'components': pca.components_,
            'n_components': pca.n_components_
        }
        
        return pca_df
    
    def _ica_integration(self) -> pd.DataFrame:
        """Perform ICA-based integration."""
        # Concatenate all data
        concatenated_data = pd.concat(
            [self.omics_data[data_type] for data_type in self.omics_data.keys()],
            axis=0
        )
        
        # Fill missing values
        concatenated_data = concatenated_data.fillna(concatenated_data.mean())
        
        # Perform ICA
        ica = ICA(n_components=min(50, concatenated_data.shape[0], concatenated_data.shape[1]))
        ica_result = ica.fit_transform(concatenated_data.T)
        
        # Create DataFrame
        ica_df = pd.DataFrame(
            ica_result.T,
            index=[f'IC{i+1}' for i in range(ica_result.shape[1])],
            columns=concatenated_data.columns
        )
        
        # Store ICA results
        self.integration_results['ica'] = {
            'mixing_matrix': ica.mixing_,
            'components': ica.components_,
            'n_components': ica.n_components_
        }
        
        return ica_df
    
    def perform_dimensionality_reduction(self, method: str = 'pca', 
                                       n_components: int = 2) -> pd.DataFrame:
        """
        Perform dimensionality reduction on integrated data.
        
        Args:
            method: Reduction method ('pca', 'tsne', 'umap')
            n_components: Number of components to reduce to
            
        Returns:
            DataFrame with reduced dimensions
        """
        if self.integrated_data is None:
            raise ValueError("No integrated data available. Run integrate_omics_data() first.")
        
        try:
            data = self.integrated_data.fillna(self.integrated_data.mean())
            
            if method == 'pca':
                reducer = PCA(n_components=n_components)
                reduced_data = reducer.fit_transform(data.T)
                
            elif method == 'tsne':
                reducer = TSNE(n_components=n_components, random_state=42)
                reduced_data = reducer.fit_transform(data.T)
                
            elif method == 'umap':
                reducer = UMAP(n_components=n_components, random_state=42)
                reduced_data = reducer.fit_transform(data.T)
                
            else:
                raise ValueError(f"Unknown reduction method: {method}")
            
            # Create DataFrame
            reduced_df = pd.DataFrame(
                reduced_data,
                index=data.columns,
                columns=[f'{method.upper()}_{i+1}' for i in range(n_components)]
            )
            
            # Store results
            if method not in self.integration_results:
                self.integration_results[method] = {}
            self.integration_results[method]['reduced_data'] = reduced_df
            
            logger.info(f"Performed {method} dimensionality reduction: {reduced_df.shape}")
            return reduced_df
            
        except Exception as e:
            logger.error(f"Error performing dimensionality reduction: {e}")
            raise
    
    def perform_clustering(self, method: str = 'kmeans', n_clusters: int = 3,
                          use_reduced_data: bool = True) -> Dict[str, Any]:
        """
        Perform clustering analysis on integrated data.
        
        Args:
            method: Clustering method ('kmeans', 'dbscan', 'hierarchical')
            n_clusters: Number of clusters (for kmeans)
            use_reduced_data: Whether to use dimensionality-reduced data
            
        Returns:
            Dictionary containing clustering results
        """
        try:
            if use_reduced_data and 'pca' in self.integration_results:
                data = self.integration_results['pca']['reduced_data']
            else:
                data = self.integrated_data.fillna(self.integrated_data.mean())
            
            if method == 'kmeans':
                clusterer = KMeans(n_clusters=n_clusters, random_state=42)
                cluster_labels = clusterer.fit_predict(data)
                
            elif method == 'dbscan':
                clusterer = DBSCAN(eps=0.5, min_samples=5)
                cluster_labels = clusterer.fit_predict(data)
                
            elif method == 'hierarchical':
                # Use linkage for hierarchical clustering
                linkage_matrix = linkage(data, method='ward')
                # For simplicity, use kmeans on the linkage matrix
                clusterer = KMeans(n_clusters=n_clusters, random_state=42)
                cluster_labels = clusterer.fit_predict(linkage_matrix)
                
            else:
                raise ValueError(f"Unknown clustering method: {method}")
            
            # Calculate silhouette score
            if len(set(cluster_labels)) > 1:
                silhouette_avg = silhouette_score(data, cluster_labels)
            else:
                silhouette_avg = 0
            
            # Create results
            clustering_results = {
                'method': method,
                'n_clusters': len(set(cluster_labels)),
                'cluster_labels': cluster_labels,
                'silhouette_score': silhouette_avg,
                'cluster_centers': clusterer.cluster_centers_ if hasattr(clusterer, 'cluster_centers_') else None
            }
            
            # Store results
            self.integration_results['clustering'] = clustering_results
            
            logger.info(f"Performed {method} clustering: {clustering_results['n_clusters']} clusters, "
                       f"silhouette score: {silhouette_avg:.3f}")
            
            return clustering_results
            
        except Exception as e:
            logger.error(f"Error performing clustering: {e}")
            raise
    
    def create_integration_visualization(self, method: str = 'pca') -> go.Figure:
        """
        Create visualization of integrated data.
        
        Args:
            method: Visualization method ('pca', 'tsne', 'umap')
            
        Returns:
            Plotly figure object
        """
        if method not in self.integration_results:
            raise ValueError(f"No {method} results available. Run perform_dimensionality_reduction() first.")
        
        try:
            reduced_data = self.integration_results[method]['reduced_data']
            
            # Get cluster labels if available
            cluster_labels = None
            if 'clustering' in self.integration_results:
                cluster_labels = self.integration_results['clustering']['cluster_labels']
            
            # Create scatter plot
            fig = go.Figure()
            
            if cluster_labels is not None:
                # Color by clusters
                unique_clusters = sorted(set(cluster_labels))
                colors = px.colors.qualitative.Set1
                
                for i, cluster in enumerate(unique_clusters):
                    mask = cluster_labels == cluster
                    fig.add_trace(go.Scatter(
                        x=reduced_data.iloc[mask, 0],
                        y=reduced_data.iloc[mask, 1],
                        mode='markers',
                        name=f'Cluster {cluster}',
                        marker=dict(color=colors[i % len(colors)], size=8),
                        text=reduced_data.index[mask],
                        hovertemplate='<b>%{text}</b><br>' +
                                    f'{method.upper()}_1: %{{x}}<br>' +
                                    f'{method.upper()}_2: %{{y}}<extra></extra>'
                    ))
            else:
                # Single color
                fig.add_trace(go.Scatter(
                    x=reduced_data.iloc[:, 0],
                    y=reduced_data.iloc[:, 1],
                    mode='markers',
                    name='Samples',
                    marker=dict(color='blue', size=8),
                    text=reduced_data.index,
                    hovertemplate='<b>%{text}</b><br>' +
                                f'{method.upper()}_1: %{{x}}<br>' +
                                f'{method.upper()}_2: %{{y}}<extra></extra>'
                ))
            
            # Update layout
            fig.update_layout(
                title=f'{method.upper()} Visualization of Integrated Omics Data',
                xaxis_title=f'{method.upper()}_1',
                yaxis_title=f'{method.upper()}_2',
                width=800,
                height=600,
                showlegend=True
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating visualization: {e}")
            raise
    
    def create_correlation_heatmap(self, data_types: List[str] = None) -> go.Figure:
        """
        Create correlation heatmap between different omics data types.
        
        Args:
            data_types: List of data types to include (default: all loaded)
            
        Returns:
            Plotly heatmap figure
        """
        if data_types is None:
            data_types = list(self.omics_data.keys())
        
        if len(data_types) < 2:
            raise ValueError("Need at least 2 data types for correlation analysis")
        
        try:
            # Calculate correlations between data types
            correlations = {}
            
            for i, data_type1 in enumerate(data_types):
                for j, data_type2 in enumerate(data_types):
                    if i < j:  # Only calculate upper triangle
                        data1 = self.omics_data[data_type1]
                        data2 = self.omics_data[data_type2]
                        
                        # Find common samples
                        common_samples = set(data1.columns) & set(data2.columns)
                        
                        if common_samples:
                            # Calculate mean correlation across features
                            corr_values = []
                            for feature1 in data1.index[:10]:  # Limit for performance
                                for feature2 in data2.index[:10]:
                                    if feature1 in data1.index and feature2 in data2.index:
                                        corr = data1.loc[feature1, common_samples].corr(
                                            data2.loc[feature2, common_samples]
                                        )
                                        if not np.isnan(corr):
                                            corr_values.append(corr)
                            
                            if corr_values:
                                correlations[f"{data_type1}-{data_type2}"] = np.mean(corr_values)
            
            # Create correlation matrix
            n_types = len(data_types)
            corr_matrix = np.eye(n_types)
            
            for i, data_type1 in enumerate(data_types):
                for j, data_type2 in enumerate(data_types):
                    if i != j:
                        key = f"{data_type1}-{data_type2}" if i < j else f"{data_type2}-{data_type1}"
                        if key in correlations:
                            corr_matrix[i, j] = correlations[key]
            
            # Create heatmap
            fig = go.Figure(data=go.Heatmap(
                z=corr_matrix,
                x=data_types,
                y=data_types,
                colorscale='RdBu',
                zmid=0,
                text=np.round(corr_matrix, 3),
                texttemplate="%{text}",
                textfont={"size": 10},
                hoverongaps=False
            ))
            
            fig.update_layout(
                title="Correlation Matrix Between Omics Data Types",
                width=600,
                height=600
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating correlation heatmap: {e}")
            raise
    
    def create_data_overview_plot(self) -> go.Figure:
        """
        Create an overview plot showing data distribution across omics types.
        
        Returns:
            Plotly figure with subplots
        """
        if not self.omics_data:
            raise ValueError("No omics data loaded")
        
        try:
            n_data_types = len(self.omics_data)
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=['Data Dimensions', 'Missing Values', 'Value Distribution', 'Sample Overview'],
                specs=[[{"type": "bar"}, {"type": "bar"}],
                       [{"type": "histogram"}, {"type": "bar"}]]
            )
            
            # Data dimensions
            data_types = list(self.omics_data.keys())
            n_features = [self.omics_data[dt].shape[0] for dt in data_types]
            n_samples = [self.omics_data[dt].shape[1] for dt in data_types]
            
            fig.add_trace(
                go.Bar(x=data_types, y=n_features, name='Features', marker_color='lightblue'),
                row=1, col=1
            )
            
            # Missing values
            missing_pct = [self.omics_data[dt].isnull().sum().sum() / 
                          (self.omics_data[dt].shape[0] * self.omics_data[dt].shape[1]) * 100
                          for dt in data_types]
            
            fig.add_trace(
                go.Bar(x=data_types, y=missing_pct, name='Missing %', marker_color='lightcoral'),
                row=1, col=2
            )
            
            # Value distribution (sample from first data type)
            first_data_type = data_types[0]
            sample_values = self.omics_data[first_data_type].values.flatten()
            sample_values = sample_values[~np.isnan(sample_values)][:1000]  # Sample for performance
            
            fig.add_trace(
                go.Histogram(x=sample_values, name=f'{first_data_type} values', nbinsx=30),
                row=2, col=1
            )
            
            # Sample overview
            sample_counts = [len(set(self.omics_data[dt].columns)) for dt in data_types]
            
            fig.add_trace(
                go.Bar(x=data_types, y=sample_counts, name='Unique Samples', marker_color='lightgreen'),
                row=2, col=2
            )
            
            fig.update_layout(
                title="Multi-Omics Data Overview",
                height=600,
                showlegend=False
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating overview plot: {e}")
            raise
    
    def export_integration_results(self, output_path: str) -> None:
        """
        Export integration results to JSON file.
        
        Args:
            output_path: Path to save the results
        """
        try:
            # Prepare results for export
            export_data = {
                'integration_results': self.integration_results,
                'feature_metadata': self.feature_metadata,
                'data_summary': {
                    data_type: {
                        'shape': data.shape,
                        'features': list(data.index),
                        'samples': list(data.columns)
                    }
                    for data_type, data in self.omics_data.items()
                }
            }
            
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Exported integration results to {output_path}")
            
        except Exception as e:
            logger.error(f"Error exporting results: {e}")
            raise
    
    def get_integration_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the integration results.
        
        Returns:
            Dictionary containing integration summary
        """
        summary = {
            'data_types': list(self.omics_data.keys()),
            'total_features': sum(data.shape[0] for data in self.omics_data.values()),
            'total_samples': len(set().union(*[set(data.columns) for data in self.omics_data.values()])),
            'integration_method': self.integration_results.get('method', 'None'),
            'has_clustering': 'clustering' in self.integration_results,
            'has_dimensionality_reduction': any(method in self.integration_results 
                                              for method in ['pca', 'tsne', 'umap'])
        }
        
        if 'clustering' in self.integration_results:
            summary['clustering'] = {
                'method': self.integration_results['clustering']['method'],
                'n_clusters': self.integration_results['clustering']['n_clusters'],
                'silhouette_score': self.integration_results['clustering']['silhouette_score']
            }
        
        return summary


def create_mock_omics_data() -> Dict[str, pd.DataFrame]:
    """
    Create mock multi-omics data for testing and demonstration.
    
    Returns:
        Dictionary containing mock omics data
    """
    np.random.seed(42)
    n_samples = 50
    n_genes = 100
    n_cpgs = 80
    n_proteins = 60
    
    # Sample IDs
    sample_ids = [f'Sample_{i:03d}' for i in range(n_samples)]
    
    # Gene expression data
    expression_data = pd.DataFrame(
        np.random.normal(0, 1, (n_genes, n_samples)),
        index=[f'Gene_{i:03d}' for i in range(n_genes)],
        columns=sample_ids
    )
    
    # DNA methylation data
    methylation_data = pd.DataFrame(
        np.random.beta(2, 2, (n_cpgs, n_samples)),
        index=[f'CpG_{i:03d}' for i in range(n_cpgs)],
        columns=sample_ids
    )
    
    # Protein expression data
    protein_data = pd.DataFrame(
        np.random.lognormal(0, 1, (n_proteins, n_samples)),
        index=[f'Protein_{i:03d}' for i in range(n_proteins)],
        columns=sample_ids
    )
    
    # Copy number variation data
    cnv_data = pd.DataFrame(
        np.random.choice([-2, -1, 0, 1, 2], (n_genes, n_samples), p=[0.05, 0.1, 0.7, 0.1, 0.05]),
        index=[f'Gene_{i:03d}' for i in range(n_genes)],
        columns=sample_ids
    )
    
    return {
        'expression': expression_data,
        'methylation': methylation_data,
        'protein': protein_data,
        'cnv': cnv_data
    }


def main():
    """Main function for testing the multi-omics integrator."""
    # Create integrator instance
    integrator = MultiOmicsIntegrator()
    
    # Create mock data
    mock_data = create_mock_omics_data()
    
    # Load mock data
    for data_type, data in mock_data.items():
        integrator.omics_data[data_type] = data
        integrator.feature_metadata[data_type] = {
            'features': list(data.index),
            'samples': list(data.columns),
            'data_type': data_type
        }
    
    # Normalize data
    for data_type in integrator.omics_data.keys():
        integrator.normalize_data(data_type, method='zscore')
    
    # Integrate data
    integrated_data = integrator.integrate_omics_data(integration_method='concatenation')
    
    # Perform dimensionality reduction
    reduced_data = integrator.perform_dimensionality_reduction(method='pca', n_components=2)
    
    # Perform clustering
    clustering_results = integrator.perform_clustering(method='kmeans', n_clusters=3)
    
    # Get summary
    summary = integrator.get_integration_summary()
    print("Integration Summary:")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
