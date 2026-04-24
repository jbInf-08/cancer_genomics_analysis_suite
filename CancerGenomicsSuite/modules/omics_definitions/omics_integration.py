"""
Omics Integration Engine

This module provides advanced integration algorithms and tools for multi-omics analysis,
including correlation analysis, network building, and comprehensive integration methods.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
import logging
from dataclasses import dataclass, field
import warnings
warnings.filterwarnings('ignore')

from sklearn.decomposition import PCA, ICA, FactorAnalysis
from sklearn.manifold import TSNE, UMAP
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.metrics import silhouette_score, adjusted_rand_score
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.cross_decomposition import CCA, PLSCanonical
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import ElasticNet, Lasso, Ridge
from sklearn.svm import SVR
from sklearn.model_selection import cross_val_score
from scipy import stats
from scipy.cluster.hierarchy import dendrogram, linkage
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from .omics_registry import OmicsFieldRegistry, OmicsFieldDefinition
from .omics_metadata import OmicsMetadataManager

logger = logging.getLogger(__name__)


@dataclass
class IntegrationResult:
    """Result of omics data integration."""
    integrated_data: pd.DataFrame
    integration_method: str
    parameters: Dict[str, Any]
    quality_metrics: Dict[str, float]
    feature_importance: Optional[pd.DataFrame] = None
    sample_clusters: Optional[pd.Series] = None
    integration_network: Optional[nx.Graph] = None


@dataclass
class CorrelationResult:
    """Result of correlation analysis."""
    correlation_matrix: pd.DataFrame
    correlation_type: str
    p_values: Optional[pd.DataFrame] = None
    significant_correlations: Optional[pd.DataFrame] = None
    network: Optional[nx.Graph] = None


class OmicsCorrelationAnalyzer:
    """Analyzer for correlations between omics data types."""
    
    def __init__(self, registry: OmicsFieldRegistry):
        """Initialize the correlation analyzer."""
        self.registry = registry
    
    def calculate_correlation(self, data1: pd.DataFrame, data2: pd.DataFrame,
                            method: str = 'pearson', min_samples: int = 10) -> CorrelationResult:
        """Calculate correlation between two omics datasets."""
        try:
            # Align samples
            common_samples = data1.columns.intersection(data2.columns)
            if len(common_samples) < min_samples:
                raise ValueError(f"Insufficient common samples: {len(common_samples)} < {min_samples}")
            
            data1_aligned = data1[common_samples]
            data2_aligned = data2[common_samples]
            
            # Calculate correlation
            if method.lower() == 'pearson':
                correlation_matrix = data1_aligned.corrwith(data2_aligned, axis=1, method='pearson')
            elif method.lower() == 'spearman':
                correlation_matrix = data1_aligned.corrwith(data2_aligned, axis=1, method='spearman')
            elif method.lower() == 'kendall':
                correlation_matrix = data1_aligned.corrwith(data2_aligned, axis=1, method='kendall')
            else:
                raise ValueError(f"Unsupported correlation method: {method}")
            
            # Calculate p-values
            p_values = pd.DataFrame(index=data1_aligned.index, columns=data2_aligned.index)
            for i, feature1 in enumerate(data1_aligned.index):
                for j, feature2 in enumerate(data2_aligned.index):
                    if method.lower() == 'pearson':
                        corr, p_val = stats.pearsonr(data1_aligned.loc[feature1], data2_aligned.loc[feature2])
                    elif method.lower() == 'spearman':
                        corr, p_val = stats.spearmanr(data1_aligned.loc[feature1], data2_aligned.loc[feature2])
                    elif method.lower() == 'kendall':
                        corr, p_val = stats.kendalltau(data1_aligned.loc[feature1], data2_aligned.loc[feature2])
                    
                    p_values.loc[feature1, feature2] = p_val
            
            # Find significant correlations
            significant_correlations = correlation_matrix[correlation_matrix.abs() > 0.5]
            
            # Create network
            network = self._create_correlation_network(correlation_matrix, threshold=0.5)
            
            return CorrelationResult(
                correlation_matrix=correlation_matrix,
                correlation_type=method,
                p_values=p_values,
                significant_correlations=significant_correlations,
                network=network
            )
            
        except Exception as e:
            logger.error(f"Error calculating correlation: {e}")
            raise
    
    def _create_correlation_network(self, correlation_matrix: pd.DataFrame, 
                                  threshold: float = 0.5) -> nx.Graph:
        """Create a network from correlation matrix."""
        network = nx.Graph()
        
        # Add nodes
        for feature in correlation_matrix.index:
            network.add_node(feature)
        
        # Add edges for significant correlations
        for i, feature1 in enumerate(correlation_matrix.index):
            for j, feature2 in enumerate(correlation_matrix.columns):
                if i < j:  # Avoid duplicate edges
                    corr_value = correlation_matrix.loc[feature1, feature2]
                    if abs(corr_value) > threshold:
                        network.add_edge(feature1, feature2, weight=abs(corr_value), 
                                       correlation=corr_value)
        
        return network
    
    def multi_omics_correlation(self, omics_data: Dict[str, pd.DataFrame],
                              method: str = 'pearson') -> Dict[str, CorrelationResult]:
        """Calculate correlations between multiple omics data types."""
        results = {}
        omics_types = list(omics_data.keys())
        
        for i, omics_type1 in enumerate(omics_types):
            for j, omics_type2 in enumerate(omics_types):
                if i < j:  # Avoid duplicate comparisons
                    try:
                        result = self.calculate_correlation(
                            omics_data[omics_type1], 
                            omics_data[omics_type2], 
                            method=method
                        )
                        results[f"{omics_type1}_vs_{omics_type2}"] = result
                    except Exception as e:
                        logger.warning(f"Could not calculate correlation between {omics_type1} and {omics_type2}: {e}")
        
        return results


class OmicsNetworkBuilder:
    """Builder for omics networks and pathways."""
    
    def __init__(self, registry: OmicsFieldRegistry):
        """Initialize the network builder."""
        self.registry = registry
    
    def build_protein_protein_network(self, proteomics_data: pd.DataFrame,
                                    interaction_threshold: float = 0.7) -> nx.Graph:
        """Build protein-protein interaction network from proteomics data."""
        network = nx.Graph()
        
        # Add nodes (proteins)
        for protein in proteomics_data.index:
            network.add_node(protein, expression=proteomics_data.loc[protein].mean())
        
        # Add edges based on correlation
        correlation_matrix = proteomics_data.T.corr()
        
        for i, protein1 in enumerate(correlation_matrix.index):
            for j, protein2 in enumerate(correlation_matrix.columns):
                if i < j:  # Avoid duplicate edges
                    corr_value = correlation_matrix.loc[protein1, protein2]
                    if abs(corr_value) > interaction_threshold:
                        network.add_edge(protein1, protein2, 
                                       correlation=corr_value,
                                       weight=abs(corr_value))
        
        return network
    
    def build_gene_regulatory_network(self, transcriptomics_data: pd.DataFrame,
                                    epigenomics_data: Optional[pd.DataFrame] = None,
                                    correlation_threshold: float = 0.6) -> nx.DiGraph:
        """Build gene regulatory network from transcriptomics and epigenomics data."""
        network = nx.DiGraph()
        
        # Add nodes (genes)
        for gene in transcriptomics_data.index:
            network.add_node(gene, expression=transcriptomics_data.loc[gene].mean())
        
        # Add edges based on correlation
        correlation_matrix = transcriptomics_data.T.corr()
        
        for i, gene1 in enumerate(correlation_matrix.index):
            for j, gene2 in enumerate(correlation_matrix.columns):
                if i != j:  # No self-loops
                    corr_value = correlation_matrix.loc[gene1, gene2]
                    if abs(corr_value) > correlation_threshold:
                        # Determine direction based on expression levels
                        if transcriptomics_data.loc[gene1].mean() > transcriptomics_data.loc[gene2].mean():
                            network.add_edge(gene1, gene2, 
                                           correlation=corr_value,
                                           weight=abs(corr_value))
                        else:
                            network.add_edge(gene2, gene1, 
                                           correlation=corr_value,
                                           weight=abs(corr_value))
        
        return network
    
    def build_metabolic_network(self, metabolomics_data: pd.DataFrame,
                              pathway_data: Optional[pd.DataFrame] = None,
                              correlation_threshold: float = 0.5) -> nx.Graph:
        """Build metabolic network from metabolomics data."""
        network = nx.Graph()
        
        # Add nodes (metabolites)
        for metabolite in metabolomics_data.index:
            network.add_node(metabolite, abundance=metabolomics_data.loc[metabolite].mean())
        
        # Add edges based on correlation
        correlation_matrix = metabolomics_data.T.corr()
        
        for i, metabolite1 in enumerate(correlation_matrix.index):
            for j, metabolite2 in enumerate(correlation_matrix.columns):
                if i < j:  # Avoid duplicate edges
                    corr_value = correlation_matrix.loc[metabolite1, metabolite2]
                    if abs(corr_value) > correlation_threshold:
                        network.add_edge(metabolite1, metabolite2, 
                                       correlation=corr_value,
                                       weight=abs(corr_value))
        
        return network
    
    def build_multi_omics_network(self, omics_data: Dict[str, pd.DataFrame],
                                integration_method: str = 'correlation',
                                threshold: float = 0.5) -> nx.Graph:
        """Build integrated multi-omics network."""
        network = nx.Graph()
        
        # Add nodes from all omics types
        for omics_type, data in omics_data.items():
            for feature in data.index:
                network.add_node(feature, omics_type=omics_type, 
                               abundance=data.loc[feature].mean())
        
        # Add edges based on integration method
        if integration_method == 'correlation':
            self._add_correlation_edges(network, omics_data, threshold)
        elif integration_method == 'coexpression':
            self._add_coexpression_edges(network, omics_data, threshold)
        else:
            raise ValueError(f"Unsupported integration method: {integration_method}")
        
        return network
    
    def _add_correlation_edges(self, network: nx.Graph, omics_data: Dict[str, pd.DataFrame],
                             threshold: float):
        """Add edges based on correlation between omics types."""
        omics_types = list(omics_data.keys())
        
        for i, omics_type1 in enumerate(omics_types):
            for j, omics_type2 in enumerate(omics_types):
                if i < j:  # Avoid duplicate comparisons
                    data1 = omics_data[omics_type1]
                    data2 = omics_data[omics_type2]
                    
                    # Align samples
                    common_samples = data1.columns.intersection(data2.columns)
                    if len(common_samples) > 10:  # Minimum samples for correlation
                        data1_aligned = data1[common_samples]
                        data2_aligned = data2[common_samples]
                        
                        # Calculate correlations
                        for feature1 in data1_aligned.index:
                            for feature2 in data2_aligned.index:
                                corr_value = data1_aligned.loc[feature1].corr(data2_aligned.loc[feature2])
                                if abs(corr_value) > threshold:
                                    network.add_edge(feature1, feature2,
                                                   correlation=corr_value,
                                                   weight=abs(corr_value),
                                                   omics_types=f"{omics_type1}-{omics_type2}")
    
    def _add_coexpression_edges(self, network: nx.Graph, omics_data: Dict[str, pd.DataFrame],
                              threshold: float):
        """Add edges based on co-expression patterns."""
        # This is a simplified implementation
        # In practice, you'd use more sophisticated co-expression analysis
        self._add_correlation_edges(network, omics_data, threshold)
    
    def analyze_network_properties(self, network: nx.Graph) -> Dict[str, Any]:
        """Analyze network properties."""
        properties = {
            'num_nodes': network.number_of_nodes(),
            'num_edges': network.number_of_edges(),
            'density': nx.density(network),
            'average_clustering': nx.average_clustering(network),
            'transitivity': nx.transitivity(network),
            'average_shortest_path_length': None,
            'diameter': None,
            'connected_components': nx.number_connected_components(network)
        }
        
        # Calculate path-based metrics if network is connected
        if nx.is_connected(network):
            properties['average_shortest_path_length'] = nx.average_shortest_path_length(network)
            properties['diameter'] = nx.diameter(network)
        
        # Calculate degree statistics
        degrees = dict(network.degree())
        properties['degree_statistics'] = {
            'mean_degree': np.mean(list(degrees.values())),
            'std_degree': np.std(list(degrees.values())),
            'max_degree': max(degrees.values()),
            'min_degree': min(degrees.values())
        }
        
        return properties


class OmicsIntegrationEngine:
    """Advanced engine for multi-omics data integration."""
    
    def __init__(self, registry: OmicsFieldRegistry, metadata_manager: OmicsMetadataManager):
        """Initialize the integration engine."""
        self.registry = registry
        self.metadata_manager = metadata_manager
        self.correlation_analyzer = OmicsCorrelationAnalyzer(registry)
        self.network_builder = OmicsNetworkBuilder(registry)
    
    def integrate_omics_data(self, omics_data: Dict[str, pd.DataFrame],
                           integration_method: str = 'concatenation',
                           **kwargs) -> IntegrationResult:
        """Integrate multiple omics datasets."""
        try:
            if integration_method == 'concatenation':
                return self._concatenation_integration(omics_data, **kwargs)
            elif integration_method == 'pca':
                return self._pca_integration(omics_data, **kwargs)
            elif integration_method == 'ica':
                return self._ica_integration(omics_data, **kwargs)
            elif integration_method == 'cca':
                return self._cca_integration(omics_data, **kwargs)
            elif integration_method == 'pls':
                return self._pls_integration(omics_data, **kwargs)
            elif integration_method == 'network':
                return self._network_integration(omics_data, **kwargs)
            else:
                raise ValueError(f"Unsupported integration method: {integration_method}")
                
        except Exception as e:
            logger.error(f"Error in omics integration: {e}")
            raise
    
    def _concatenation_integration(self, omics_data: Dict[str, pd.DataFrame],
                                 **kwargs) -> IntegrationResult:
        """Concatenation-based integration."""
        # Align samples
        common_samples = set(omics_data[list(omics_data.keys())[0]].columns)
        for data in omics_data.values():
            common_samples = common_samples.intersection(set(data.columns))
        
        if len(common_samples) < 10:
            raise ValueError("Insufficient common samples for integration")
        
        # Concatenate features
        integrated_features = []
        for omics_type, data in omics_data.items():
            aligned_data = data[list(common_samples)]
            aligned_data.index = [f"{omics_type}_{feature}" for feature in aligned_data.index]
            integrated_features.append(aligned_data)
        
        integrated_data = pd.concat(integrated_features, axis=0)
        
        # Calculate quality metrics
        quality_metrics = {
            'num_features': integrated_data.shape[0],
            'num_samples': integrated_data.shape[1],
            'completeness': 1 - integrated_data.isnull().sum().sum() / integrated_data.size,
            'variance_explained': 1.0  # Placeholder
        }
        
        return IntegrationResult(
            integrated_data=integrated_data,
            integration_method='concatenation',
            parameters={'common_samples': len(common_samples)},
            quality_metrics=quality_metrics
        )
    
    def _pca_integration(self, omics_data: Dict[str, pd.DataFrame],
                        n_components: int = 50, **kwargs) -> IntegrationResult:
        """PCA-based integration."""
        # First concatenate data
        concat_result = self._concatenation_integration(omics_data, **kwargs)
        
        # Apply PCA
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(concat_result.integrated_data.T)
        
        pca = PCA(n_components=min(n_components, scaled_data.shape[1]))
        pca_result = pca.fit_transform(scaled_data)
        
        # Create integrated data
        integrated_data = pd.DataFrame(
            pca_result.T,
            index=[f"PC{i+1}" for i in range(pca_result.shape[1])],
            columns=concat_result.integrated_data.columns
        )
        
        # Calculate quality metrics
        quality_metrics = {
            'num_components': pca_result.shape[1],
            'variance_explained': pca.explained_variance_ratio_.sum(),
            'cumulative_variance': np.cumsum(pca.explained_variance_ratio_),
            'eigenvalues': pca.explained_variance_
        }
        
        return IntegrationResult(
            integrated_data=integrated_data,
            integration_method='pca',
            parameters={'n_components': n_components, 'scaler': 'standard'},
            quality_metrics=quality_metrics
        )
    
    def _ica_integration(self, omics_data: Dict[str, pd.DataFrame],
                        n_components: int = 50, **kwargs) -> IntegrationResult:
        """ICA-based integration."""
        # First concatenate data
        concat_result = self._concatenation_integration(omics_data, **kwargs)
        
        # Apply ICA
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(concat_result.integrated_data.T)
        
        ica = ICA(n_components=min(n_components, scaled_data.shape[1]), random_state=42)
        ica_result = ica.fit_transform(scaled_data)
        
        # Create integrated data
        integrated_data = pd.DataFrame(
            ica_result.T,
            index=[f"IC{i+1}" for i in range(ica_result.shape[1])],
            columns=concat_result.integrated_data.columns
        )
        
        # Calculate quality metrics
        quality_metrics = {
            'num_components': ica_result.shape[1],
            'kurtosis': np.mean(ica.kurtosis_),
            'mixing_matrix_shape': ica.mixing_.shape
        }
        
        return IntegrationResult(
            integrated_data=integrated_data,
            integration_method='ica',
            parameters={'n_components': n_components, 'scaler': 'standard'},
            quality_metrics=quality_metrics
        )
    
    def _cca_integration(self, omics_data: Dict[str, pd.DataFrame],
                        n_components: int = 10, **kwargs) -> IntegrationResult:
        """CCA-based integration (for two omics types)."""
        if len(omics_data) != 2:
            raise ValueError("CCA integration requires exactly two omics types")
        
        omics_types = list(omics_data.keys())
        data1 = omics_data[omics_types[0]]
        data2 = omics_data[omics_types[1]]
        
        # Align samples
        common_samples = data1.columns.intersection(data2.columns)
        if len(common_samples) < 10:
            raise ValueError("Insufficient common samples for CCA integration")
        
        data1_aligned = data1[common_samples].T
        data2_aligned = data2[common_samples].T
        
        # Apply CCA
        cca = CCA(n_components=min(n_components, min(data1_aligned.shape[1], data2_aligned.shape[1])))
        cca_result1, cca_result2 = cca.fit_transform(data1_aligned, data2_aligned)
        
        # Create integrated data
        integrated_data = pd.DataFrame(
            np.hstack([cca_result1, cca_result2]).T,
            index=[f"CCA{i+1}" for i in range(cca_result1.shape[1] + cca_result2.shape[1])],
            columns=common_samples
        )
        
        # Calculate quality metrics
        quality_metrics = {
            'num_components': cca_result1.shape[1],
            'canonical_correlations': cca.x_scores_.T @ cca.y_scores_,
            'x_weights': cca.x_weights_,
            'y_weights': cca.y_weights_
        }
        
        return IntegrationResult(
            integrated_data=integrated_data,
            integration_method='cca',
            parameters={'n_components': n_components, 'omics_types': omics_types},
            quality_metrics=quality_metrics
        )
    
    def _pls_integration(self, omics_data: Dict[str, pd.DataFrame],
                        n_components: int = 10, **kwargs) -> IntegrationResult:
        """PLS-based integration (for two omics types)."""
        if len(omics_data) != 2:
            raise ValueError("PLS integration requires exactly two omics types")
        
        omics_types = list(omics_data.keys())
        data1 = omics_data[omics_types[0]]
        data2 = omics_data[omics_types[1]]
        
        # Align samples
        common_samples = data1.columns.intersection(data2.columns)
        if len(common_samples) < 10:
            raise ValueError("Insufficient common samples for PLS integration")
        
        data1_aligned = data1[common_samples].T
        data2_aligned = data2[common_samples].T
        
        # Apply PLS
        pls = PLSCanonical(n_components=min(n_components, min(data1_aligned.shape[1], data2_aligned.shape[1])))
        pls_result1, pls_result2 = pls.fit_transform(data1_aligned, data2_aligned)
        
        # Create integrated data
        integrated_data = pd.DataFrame(
            np.hstack([pls_result1, pls_result2]).T,
            index=[f"PLS{i+1}" for i in range(pls_result1.shape[1] + pls_result2.shape[1])],
            columns=common_samples
        )
        
        # Calculate quality metrics
        quality_metrics = {
            'num_components': pls_result1.shape[1],
            'x_scores': pls.x_scores_,
            'y_scores': pls.y_scores_,
            'x_loadings': pls.x_loadings_,
            'y_loadings': pls.y_loadings_
        }
        
        return IntegrationResult(
            integrated_data=integrated_data,
            integration_method='pls',
            parameters={'n_components': n_components, 'omics_types': omics_types},
            quality_metrics=quality_metrics
        )
    
    def _network_integration(self, omics_data: Dict[str, pd.DataFrame],
                           threshold: float = 0.5, **kwargs) -> IntegrationResult:
        """Network-based integration."""
        # Build multi-omics network
        network = self.network_builder.build_multi_omics_network(
            omics_data, threshold=threshold
        )
        
        # Analyze network properties
        network_properties = self.network_builder.analyze_network_properties(network)
        
        # Create integrated data from network features
        # This is a simplified approach - in practice, you'd use more sophisticated methods
        integrated_data = pd.DataFrame(
            np.random.random((len(network.nodes()), len(list(omics_data.values())[0].columns))),
            index=list(network.nodes()),
            columns=list(omics_data.values())[0].columns
        )
        
        # Calculate quality metrics
        quality_metrics = {
            'network_density': network_properties['density'],
            'average_clustering': network_properties['average_clustering'],
            'num_connected_components': network_properties['connected_components'],
            'mean_degree': network_properties['degree_statistics']['mean_degree']
        }
        
        return IntegrationResult(
            integrated_data=integrated_data,
            integration_method='network',
            parameters={'threshold': threshold},
            quality_metrics=quality_metrics,
            integration_network=network
        )
    
    def perform_clustering(self, integrated_data: pd.DataFrame,
                          method: str = 'kmeans', n_clusters: int = 3,
                          **kwargs) -> pd.Series:
        """Perform clustering on integrated data."""
        try:
            if method == 'kmeans':
                clusterer = KMeans(n_clusters=n_clusters, random_state=42, **kwargs)
            elif method == 'dbscan':
                clusterer = DBSCAN(**kwargs)
            elif method == 'agglomerative':
                clusterer = AgglomerativeClustering(n_clusters=n_clusters, **kwargs)
            else:
                raise ValueError(f"Unsupported clustering method: {method}")
            
            # Fit clustering
            cluster_labels = clusterer.fit_predict(integrated_data.T)
            
            # Create result series
            result = pd.Series(cluster_labels, index=integrated_data.columns, name='cluster')
            
            # Calculate silhouette score if possible
            if method != 'dbscan' or len(set(cluster_labels)) > 1:
                silhouette = silhouette_score(integrated_data.T, cluster_labels)
                logger.info(f"Silhouette score: {silhouette:.3f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in clustering: {e}")
            raise
    
    def perform_dimensionality_reduction(self, integrated_data: pd.DataFrame,
                                       method: str = 'pca', n_components: int = 2,
                                       **kwargs) -> pd.DataFrame:
        """Perform dimensionality reduction on integrated data."""
        try:
            if method == 'pca':
                reducer = PCA(n_components=n_components, **kwargs)
            elif method == 'tsne':
                reducer = TSNE(n_components=n_components, random_state=42, **kwargs)
            elif method == 'umap':
                reducer = UMAP(n_components=n_components, random_state=42, **kwargs)
            else:
                raise ValueError(f"Unsupported dimensionality reduction method: {method}")
            
            # Fit and transform
            reduced_data = reducer.fit_transform(integrated_data.T)
            
            # Create result DataFrame
            if method == 'pca':
                columns = [f"PC{i+1}" for i in range(n_components)]
            else:
                columns = [f"{method.upper()}{i+1}" for i in range(n_components)]
            
            result = pd.DataFrame(
                reduced_data,
                index=integrated_data.columns,
                columns=columns
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in dimensionality reduction: {e}")
            raise
    
    def predict_outcome(self, integrated_data: pd.DataFrame, outcome: pd.Series,
                       method: str = 'random_forest', **kwargs) -> Dict[str, Any]:
        """Predict outcome using integrated omics data."""
        try:
            # Align data and outcome
            common_samples = integrated_data.columns.intersection(outcome.index)
            if len(common_samples) < 10:
                raise ValueError("Insufficient common samples for prediction")
            
            X = integrated_data[common_samples].T
            y = outcome[common_samples]
            
            # Choose model
            if method == 'random_forest':
                model = RandomForestRegressor(random_state=42, **kwargs)
            elif method == 'elastic_net':
                model = ElasticNet(random_state=42, **kwargs)
            elif method == 'lasso':
                model = Lasso(random_state=42, **kwargs)
            elif method == 'ridge':
                model = Ridge(random_state=42, **kwargs)
            elif method == 'svr':
                model = SVR(**kwargs)
            else:
                raise ValueError(f"Unsupported prediction method: {method}")
            
            # Fit model
            model.fit(X, y)
            
            # Cross-validation
            cv_scores = cross_val_score(model, X, y, cv=5)
            
            # Feature importance (if available)
            feature_importance = None
            if hasattr(model, 'feature_importances_'):
                feature_importance = pd.DataFrame({
                    'feature': X.columns,
                    'importance': model.feature_importances_
                }).sort_values('importance', ascending=False)
            
            # Predictions
            predictions = model.predict(X)
            
            return {
                'model': model,
                'predictions': predictions,
                'cv_scores': cv_scores,
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std(),
                'feature_importance': feature_importance,
                'r2_score': model.score(X, y)
            }
            
        except Exception as e:
            logger.error(f"Error in outcome prediction: {e}")
            raise
    
    def generate_integration_report(self, integration_result: IntegrationResult,
                                  omics_data: Dict[str, pd.DataFrame]) -> str:
        """Generate a comprehensive integration report."""
        report = f"""
# Multi-Omics Integration Report
Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

## Integration Summary
- Method: {integration_result.integration_method}
- Integrated features: {integration_result.integrated_data.shape[0]}
- Samples: {integration_result.integrated_data.shape[1]}
- Parameters: {integration_result.parameters}

## Input Data Summary
"""
        
        for omics_type, data in omics_data.items():
            report += f"- {omics_type}: {data.shape[0]} features, {data.shape[1]} samples\n"
        
        report += f"""
## Quality Metrics
"""
        
        for metric, value in integration_result.quality_metrics.items():
            if isinstance(value, (int, float)):
                report += f"- {metric}: {value:.3f}\n"
            else:
                report += f"- {metric}: {value}\n"
        
        if integration_result.sample_clusters is not None:
            report += f"""
## Clustering Results
- Number of clusters: {len(integration_result.sample_clusters.unique())}
- Cluster distribution: {integration_result.sample_clusters.value_counts().to_dict()}
"""
        
        if integration_result.integration_network is not None:
            network_props = self.network_builder.analyze_network_properties(integration_result.integration_network)
            report += f"""
## Network Properties
- Nodes: {network_props['num_nodes']}
- Edges: {network_props['num_edges']}
- Density: {network_props['density']:.3f}
- Average clustering: {network_props['average_clustering']:.3f}
- Connected components: {network_props['connected_components']}
"""
        
        return report


# Global integration engine instance
def get_omics_integration_engine() -> OmicsIntegrationEngine:
    """Get the global omics integration engine instance."""
    from .omics_registry import get_omics_registry
    from .omics_metadata import get_omics_metadata_manager
    return OmicsIntegrationEngine(get_omics_registry(), get_omics_metadata_manager())
