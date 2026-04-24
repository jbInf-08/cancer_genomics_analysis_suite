"""
AI-Powered Visualization and Insight Generation

This module provides intelligent visualization capabilities, automated insight generation,
pattern recognition, and interactive visualizations for cancer genomics analysis.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
from dataclasses import dataclass
import json
import warnings
warnings.filterwarnings('ignore')

# Visualization libraries
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
from plotly.offline import plot
import bokeh.plotting as bk
from bokeh.models import HoverTool, ColumnDataSource
from bokeh.layouts import column, row
import altair as alt

# Machine Learning for pattern recognition
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, calinski_harabasz_score
from sklearn.feature_selection import SelectKBest, f_classif

# Deep Learning for pattern recognition
import torch
import torch.nn as nn
import torch.nn.functional as F

# Statistical analysis
import scipy.stats as stats
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import pdist, squareform

# Natural Language Processing for insights
from textblob import TextBlob
import re

# Time series analysis
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller

logger = logging.getLogger(__name__)


@dataclass
class VisualizationConfig:
    """Configuration for AI visualization."""
    default_style: str = "plotly"
    color_palette: str = "viridis"
    figure_size: Tuple[int, int] = (12, 8)
    dpi: int = 300
    interactive: bool = True
    auto_insights: bool = True
    pattern_detection: bool = True
    clustering_method: str = "kmeans"
    dimensionality_reduction: str = "pca"


class AIInsightGenerator:
    """Generate AI-powered insights from data visualizations."""
    
    def __init__(self, config: VisualizationConfig = None):
        self.config = config or VisualizationConfig()
        self.insight_templates = self._load_insight_templates()
        
    def _load_insight_templates(self) -> Dict[str, str]:
        """Load templates for generating insights."""
        return {
            'correlation': "Strong {correlation_type} correlation ({strength}) found between {var1} and {var2}",
            'trend': "{trend_type} trend detected in {variable} over {time_period}",
            'cluster': "Data shows {cluster_count} distinct clusters with {cluster_characteristics}",
            'outlier': "Outlier detected: {outlier_description}",
            'distribution': "Data distribution shows {distribution_type} with {statistics}",
            'pattern': "Pattern identified: {pattern_description}",
            'comparison': "Significant difference found between {groups} in {metric}"
        }
    
    def generate_insights(self, data: pd.DataFrame, 
                         visualization_type: str = "auto") -> List[Dict[str, Any]]:
        """Generate insights from data analysis."""
        logger.info(f"Generating insights for {visualization_type} visualization")
        
        insights = []
        
        # Statistical insights
        insights.extend(self._generate_statistical_insights(data))
        
        # Correlation insights
        insights.extend(self._generate_correlation_insights(data))
        
        # Distribution insights
        insights.extend(self._generate_distribution_insights(data))
        
        # Pattern insights
        if self.config.pattern_detection:
            insights.extend(self._generate_pattern_insights(data))
        
        # Clustering insights
        insights.extend(self._generate_clustering_insights(data))
        
        # Rank insights by importance
        insights = self._rank_insights(insights)
        
        return insights
    
    def _generate_statistical_insights(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generate statistical insights."""
        insights = []
        numeric_data = data.select_dtypes(include=[np.number])
        
        if numeric_data.empty:
            return insights
        
        for col in numeric_data.columns:
            values = numeric_data[col].dropna()
            if len(values) == 0:
                continue
            
            # Basic statistics
            mean_val = values.mean()
            std_val = values.std()
            median_val = values.median()
            
            # Skewness and kurtosis
            skewness = values.skew()
            kurtosis = values.kurtosis()
            
            # Generate insights based on statistics
            if abs(skewness) > 1:
                skew_type = "right-skewed" if skewness > 0 else "left-skewed"
                insights.append({
                    'type': 'distribution',
                    'importance': 'medium',
                    'description': f"{col} shows {skew_type} distribution (skewness: {skewness:.2f})",
                    'metric': 'skewness',
                    'value': skewness,
                    'variable': col
                })
            
            if abs(kurtosis) > 3:
                kurt_type = "heavy-tailed" if kurtosis > 0 else "light-tailed"
                insights.append({
                    'type': 'distribution',
                    'importance': 'low',
                    'description': f"{col} shows {kurt_type} distribution (kurtosis: {kurtosis:.2f})",
                    'metric': 'kurtosis',
                    'value': kurtosis,
                    'variable': col
                })
            
            # Coefficient of variation
            cv = std_val / mean_val if mean_val != 0 else 0
            if cv > 1:
                insights.append({
                    'type': 'variability',
                    'importance': 'medium',
                    'description': f"{col} shows high variability (CV: {cv:.2f})",
                    'metric': 'coefficient_of_variation',
                    'value': cv,
                    'variable': col
                })
        
        return insights
    
    def _generate_correlation_insights(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generate correlation insights."""
        insights = []
        numeric_data = data.select_dtypes(include=[np.number])
        
        if numeric_data.shape[1] < 2:
            return insights
        
        corr_matrix = numeric_data.corr()
        
        # Find strong correlations
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                corr_value = corr_matrix.iloc[i, j]
                if abs(corr_value) > 0.7:
                    var1 = corr_matrix.columns[i]
                    var2 = corr_matrix.columns[j]
                    
                    correlation_type = "positive" if corr_value > 0 else "negative"
                    strength = "strong" if abs(corr_value) > 0.8 else "moderate"
                    
                    insights.append({
                        'type': 'correlation',
                        'importance': 'high' if abs(corr_value) > 0.8 else 'medium',
                        'description': f"Strong {correlation_type} correlation ({strength}) between {var1} and {var2} (r={corr_value:.3f})",
                        'metric': 'correlation',
                        'value': corr_value,
                        'variables': [var1, var2]
                    })
        
        return insights
    
    def _generate_distribution_insights(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generate distribution insights."""
        insights = []
        numeric_data = data.select_dtypes(include=[np.number])
        
        for col in numeric_data.columns:
            values = numeric_data[col].dropna()
            if len(values) < 10:
                continue
            
            # Test for normality
            if len(values) > 3:
                shapiro_stat, shapiro_p = stats.shapiro(values)
                if shapiro_p < 0.05:
                    insights.append({
                        'type': 'distribution',
                        'importance': 'low',
                        'description': f"{col} does not follow normal distribution (Shapiro-Wilk p={shapiro_p:.3f})",
                        'metric': 'normality_test',
                        'value': shapiro_p,
                        'variable': col
                    })
            
            # Detect bimodal distribution
            if len(values) > 20:
                hist, bins = np.histogram(values, bins=20)
                peaks = self._find_peaks(hist)
                if len(peaks) >= 2:
                    insights.append({
                        'type': 'distribution',
                        'importance': 'medium',
                        'description': f"{col} shows bimodal or multimodal distribution",
                        'metric': 'modality',
                        'value': len(peaks),
                        'variable': col
                    })
        
        return insights
    
    def _generate_pattern_insights(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generate pattern recognition insights."""
        insights = []
        
        # Time series patterns
        time_columns = [col for col in data.columns if any(keyword in col.lower() 
                       for keyword in ['time', 'date', 'day', 'month', 'year'])]
        
        for time_col in time_columns:
            if data[time_col].dtype == 'object':
                try:
                    data[time_col] = pd.to_datetime(data[time_col])
                    # Look for temporal patterns in numeric columns
                    numeric_cols = data.select_dtypes(include=[np.number]).columns
                    for num_col in numeric_cols:
                        if len(data) > 10:
                            # Simple trend detection
                            x = np.arange(len(data))
                            y = data[num_col].values
                            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                            
                            if p_value < 0.05:
                                trend_type = "increasing" if slope > 0 else "decreasing"
                                insights.append({
                                    'type': 'trend',
                                    'importance': 'medium',
                                    'description': f"{trend_type} trend in {num_col} over time (slope={slope:.3f}, p={p_value:.3f})",
                                    'metric': 'trend',
                                    'value': slope,
                                    'variable': num_col,
                                    'time_variable': time_col
                                })
                except:
                    continue
        
        return insights
    
    def _generate_clustering_insights(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generate clustering insights."""
        insights = []
        numeric_data = data.select_dtypes(include=[np.number])
        
        if numeric_data.shape[1] < 2 or len(numeric_data) < 10:
            return insights
        
        # Try different numbers of clusters
        best_k = 2
        best_silhouette = -1
        
        for k in range(2, min(6, len(numeric_data)//2)):
            try:
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                labels = kmeans.fit_predict(numeric_data)
                silhouette = silhouette_score(numeric_data, labels)
                
                if silhouette > best_silhouette:
                    best_silhouette = silhouette
                    best_k = k
            except:
                continue
        
        if best_silhouette > 0.3:  # Good clustering
            insights.append({
                'type': 'cluster',
                'importance': 'high',
                'description': f"Data shows {best_k} distinct clusters with silhouette score {best_silhouette:.3f}",
                'metric': 'clustering',
                'value': best_silhouette,
                'cluster_count': best_k
            })
        
        return insights
    
    def _find_peaks(self, hist: np.ndarray) -> List[int]:
        """Find peaks in histogram."""
        peaks = []
        for i in range(1, len(hist) - 1):
            if hist[i] > hist[i-1] and hist[i] > hist[i+1] and hist[i] > np.mean(hist):
                peaks.append(i)
        return peaks
    
    def _rank_insights(self, insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank insights by importance."""
        importance_weights = {'high': 3, 'medium': 2, 'low': 1}
        
        for insight in insights:
            insight['score'] = importance_weights.get(insight.get('importance', 'low'), 1)
        
        return sorted(insights, key=lambda x: x['score'], reverse=True)


class AutomatedReportBuilder:
    """Build automated reports with AI-generated insights."""
    
    def __init__(self, config: VisualizationConfig = None):
        self.config = config or VisualizationConfig()
        self.insight_generator = AIInsightGenerator(config)
        
    def build_analysis_report(self, data: pd.DataFrame, 
                            analysis_type: str = "comprehensive") -> Dict[str, Any]:
        """Build comprehensive analysis report."""
        logger.info(f"Building {analysis_type} analysis report")
        
        report = {
            'metadata': {
                'data_shape': data.shape,
                'analysis_type': analysis_type,
                'timestamp': pd.Timestamp.now().isoformat(),
                'columns': list(data.columns)
            },
            'summary_statistics': self._generate_summary_statistics(data),
            'visualizations': self._generate_visualizations(data, analysis_type),
            'insights': self.insight_generator.generate_insights(data),
            'recommendations': self._generate_recommendations(data)
        }
        
        return report
    
    def _generate_summary_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generate summary statistics."""
        summary = {
            'data_overview': {
                'total_rows': len(data),
                'total_columns': len(data.columns),
                'missing_values': data.isnull().sum().sum(),
                'duplicate_rows': data.duplicated().sum()
            },
            'column_types': data.dtypes.value_counts().to_dict(),
            'numeric_summary': {},
            'categorical_summary': {}
        }
        
        # Numeric columns summary
        numeric_data = data.select_dtypes(include=[np.number])
        if not numeric_data.empty:
            summary['numeric_summary'] = numeric_data.describe().to_dict()
        
        # Categorical columns summary
        categorical_data = data.select_dtypes(include=['object'])
        if not categorical_data.empty:
            for col in categorical_data.columns:
                summary['categorical_summary'][col] = {
                    'unique_values': categorical_data[col].nunique(),
                    'most_frequent': categorical_data[col].mode().iloc[0] if not categorical_data[col].mode().empty else None,
                    'frequency': categorical_data[col].value_counts().head().to_dict()
                }
        
        return summary
    
    def _generate_visualizations(self, data: pd.DataFrame, 
                               analysis_type: str) -> Dict[str, Any]:
        """Generate visualizations for the report."""
        visualizations = {}
        
        if analysis_type in ["comprehensive", "exploratory"]:
            # Distribution plots
            visualizations['distributions'] = self._create_distribution_plots(data)
            
            # Correlation heatmap
            visualizations['correlation'] = self._create_correlation_plot(data)
            
            # Pair plots
            visualizations['pairs'] = self._create_pair_plots(data)
        
        if analysis_type in ["comprehensive", "clustering"]:
            # Clustering visualization
            visualizations['clustering'] = self._create_clustering_plots(data)
        
        if analysis_type in ["comprehensive", "time_series"]:
            # Time series plots
            visualizations['time_series'] = self._create_time_series_plots(data)
        
        return visualizations
    
    def _create_distribution_plots(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Create distribution plots."""
        plots = {}
        numeric_data = data.select_dtypes(include=[np.number])
        
        for col in numeric_data.columns:
            fig = px.histogram(data, x=col, title=f"Distribution of {col}")
            plots[col] = fig.to_dict()
        
        return plots
    
    def _create_correlation_plot(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Create correlation heatmap."""
        numeric_data = data.select_dtypes(include=[np.number])
        
        if numeric_data.shape[1] < 2:
            return {}
        
        corr_matrix = numeric_data.corr()
        fig = px.imshow(corr_matrix, 
                       text_auto=True, 
                       aspect="auto",
                       title="Correlation Matrix")
        
        return fig.to_dict()
    
    def _create_pair_plots(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Create pair plots for numeric data."""
        numeric_data = data.select_dtypes(include=[np.number])
        
        if numeric_data.shape[1] < 2:
            return {}
        
        # Limit to first 5 columns to avoid overcrowding
        if numeric_data.shape[1] > 5:
            numeric_data = numeric_data.iloc[:, :5]
        
        fig = px.scatter_matrix(numeric_data, title="Pair Plot")
        return fig.to_dict()
    
    def _create_clustering_plots(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Create clustering visualization."""
        numeric_data = data.select_dtypes(include=[np.number])
        
        if numeric_data.shape[1] < 2 or len(numeric_data) < 10:
            return {}
        
        # Perform PCA for visualization
        pca = PCA(n_components=2)
        pca_data = pca.fit_transform(numeric_data)
        
        # Perform clustering
        kmeans = KMeans(n_clusters=3, random_state=42)
        clusters = kmeans.fit_predict(numeric_data)
        
        # Create scatter plot
        fig = px.scatter(x=pca_data[:, 0], 
                        y=pca_data[:, 1],
                        color=clusters,
                        title="Clustering Visualization (PCA)")
        
        return fig.to_dict()
    
    def _create_time_series_plots(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Create time series plots."""
        plots = {}
        
        # Look for time columns
        time_columns = [col for col in data.columns if any(keyword in col.lower() 
                       for keyword in ['time', 'date', 'day', 'month', 'year'])]
        
        for time_col in time_columns:
            try:
                data[time_col] = pd.to_datetime(data[time_col])
                numeric_cols = data.select_dtypes(include=[np.number]).columns
                
                for num_col in numeric_cols:
                    fig = px.line(data, x=time_col, y=num_col, 
                                title=f"{num_col} over {time_col}")
                    plots[f"{num_col}_vs_{time_col}"] = fig.to_dict()
            except:
                continue
        
        return plots
    
    def _generate_recommendations(self, data: pd.DataFrame) -> List[str]:
        """Generate recommendations based on data analysis."""
        recommendations = []
        
        # Missing data recommendations
        missing_pct = (data.isnull().sum().sum() / (data.shape[0] * data.shape[1])) * 100
        if missing_pct > 20:
            recommendations.append("High missing data percentage. Consider data imputation strategies.")
        elif missing_pct > 5:
            recommendations.append("Moderate missing data. Review data collection process.")
        
        # Duplicate recommendations
        duplicate_pct = (data.duplicated().sum() / len(data)) * 100
        if duplicate_pct > 5:
            recommendations.append("High duplicate percentage. Implement deduplication procedures.")
        
        # Feature selection recommendations
        numeric_data = data.select_dtypes(include=[np.number])
        if numeric_data.shape[1] > 50:
            recommendations.append("Large number of features. Consider dimensionality reduction techniques.")
        
        # Correlation recommendations
        if numeric_data.shape[1] > 1:
            corr_matrix = numeric_data.corr()
            high_corr_count = 0
            for i in range(len(corr_matrix.columns)):
                for j in range(i+1, len(corr_matrix.columns)):
                    if abs(corr_matrix.iloc[i, j]) > 0.95:
                        high_corr_count += 1
            
            if high_corr_count > 5:
                recommendations.append("High correlation between features. Consider feature selection.")
        
        return recommendations


class InteractiveVisualizationAI:
    """Create interactive visualizations with AI-powered features."""
    
    def __init__(self, config: VisualizationConfig = None):
        self.config = config or VisualizationConfig()
        
    def create_interactive_dashboard(self, data: pd.DataFrame, 
                                   dashboard_type: str = "genomics") -> Dict[str, Any]:
        """Create interactive dashboard with AI features."""
        logger.info(f"Creating {dashboard_type} interactive dashboard")
        
        dashboard = {
            'type': dashboard_type,
            'components': [],
            'interactions': [],
            'ai_features': []
        }
        
        if dashboard_type == "genomics":
            dashboard['components'] = self._create_genomics_components(data)
        elif dashboard_type == "clinical":
            dashboard['components'] = self._create_clinical_components(data)
        elif dashboard_type == "multi_omics":
            dashboard['components'] = self._create_multi_omics_components(data)
        
        # Add AI-powered interactions
        dashboard['interactions'] = self._create_ai_interactions(data)
        dashboard['ai_features'] = self._create_ai_features(data)
        
        return dashboard
    
    def _create_genomics_components(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Create genomics-specific dashboard components."""
        components = []
        
        # Mutation frequency plot
        if 'mutation_type' in data.columns:
            mutation_counts = data['mutation_type'].value_counts()
            fig = px.bar(x=mutation_counts.index, y=mutation_counts.values,
                        title="Mutation Type Distribution")
            components.append({
                'type': 'bar_chart',
                'title': 'Mutation Types',
                'data': fig.to_dict(),
                'interactive': True
            })
        
        # Gene expression heatmap
        expression_cols = [col for col in data.columns if 'expression' in col.lower()]
        if len(expression_cols) > 1:
            expression_data = data[expression_cols]
            fig = px.imshow(expression_data.T, 
                           title="Gene Expression Heatmap",
                           color_continuous_scale='RdBu_r')
            components.append({
                'type': 'heatmap',
                'title': 'Gene Expression',
                'data': fig.to_dict(),
                'interactive': True
            })
        
        # Survival analysis plot
        if 'survival_time' in data.columns and 'event' in data.columns:
            fig = self._create_survival_plot(data)
            components.append({
                'type': 'survival_curve',
                'title': 'Survival Analysis',
                'data': fig.to_dict(),
                'interactive': True
            })
        
        return components
    
    def _create_clinical_components(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Create clinical-specific dashboard components."""
        components = []
        
        # Patient demographics
        if 'age' in data.columns:
            fig = px.histogram(data, x='age', title="Age Distribution")
            components.append({
                'type': 'histogram',
                'title': 'Patient Age Distribution',
                'data': fig.to_dict(),
                'interactive': True
            })
        
        # Treatment response
        if 'treatment_response' in data.columns:
            response_counts = data['treatment_response'].value_counts()
            fig = px.pie(values=response_counts.values, 
                        names=response_counts.index,
                        title="Treatment Response Distribution")
            components.append({
                'type': 'pie_chart',
                'title': 'Treatment Response',
                'data': fig.to_dict(),
                'interactive': True
            })
        
        return components
    
    def _create_multi_omics_components(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Create multi-omics dashboard components."""
        components = []
        
        # Omics data integration plot
        omics_types = ['genomics', 'transcriptomics', 'proteomics', 'metabolomics']
        available_omics = [omics for omics in omics_types if any(col.startswith(omics) for col in data.columns)]
        
        if len(available_omics) > 1:
            # Create correlation plot between omics types
            omics_data = {}
            for omics in available_omics:
                omics_cols = [col for col in data.columns if col.startswith(omics)]
                if omics_cols:
                    omics_data[omics] = data[omics_cols].mean(axis=1)
            
            omics_df = pd.DataFrame(omics_data)
            corr_matrix = omics_df.corr()
            
            fig = px.imshow(corr_matrix, 
                           title="Multi-Omics Correlation",
                           color_continuous_scale='RdBu_r')
            components.append({
                'type': 'correlation_heatmap',
                'title': 'Multi-Omics Integration',
                'data': fig.to_dict(),
                'interactive': True
            })
        
        return components
    
    def _create_survival_plot(self, data: pd.DataFrame) -> go.Figure:
        """Create survival curve plot."""
        # Simple survival curve implementation
        survival_data = data[['survival_time', 'event']].dropna()
        
        # Sort by survival time
        survival_data = survival_data.sort_values('survival_time')
        
        # Calculate survival probabilities
        n_total = len(survival_data)
        survival_prob = []
        time_points = []
        
        for i, (time, event) in enumerate(survival_data.values):
            if event == 1:  # Death event
                prob = (n_total - i) / n_total
                survival_prob.append(prob)
                time_points.append(time)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=time_points, y=survival_prob,
                               mode='lines',
                               name='Survival Curve'))
        
        fig.update_layout(title="Survival Analysis",
                         xaxis_title="Time",
                         yaxis_title="Survival Probability")
        
        return fig
    
    def _create_ai_interactions(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Create AI-powered interactive features."""
        interactions = []
        
        # Smart filtering
        interactions.append({
            'type': 'smart_filter',
            'description': 'AI-powered data filtering based on patterns',
            'features': ['outlier_detection', 'pattern_matching', 'anomaly_highlighting']
        })
        
        # Dynamic insights
        interactions.append({
            'type': 'dynamic_insights',
            'description': 'Real-time insight generation as user explores data',
            'features': ['correlation_detection', 'trend_analysis', 'pattern_recognition']
        })
        
        # Intelligent recommendations
        interactions.append({
            'type': 'intelligent_recommendations',
            'description': 'AI-suggested next analysis steps',
            'features': ['workflow_suggestions', 'visualization_recommendations', 'statistical_tests']
        })
        
        return interactions
    
    def _create_ai_features(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Create AI-powered features for the dashboard."""
        features = []
        
        # Auto-clustering
        numeric_data = data.select_dtypes(include=[np.number])
        if numeric_data.shape[1] > 1 and len(numeric_data) > 10:
            features.append({
                'type': 'auto_clustering',
                'description': 'Automatic cluster detection and visualization',
                'implementation': 'kmeans_with_optimal_k'
            })
        
        # Anomaly detection
        features.append({
            'type': 'anomaly_detection',
            'description': 'Real-time anomaly detection and highlighting',
            'implementation': 'isolation_forest'
        })
        
        # Predictive insights
        features.append({
            'type': 'predictive_insights',
            'description': 'ML-based predictions and forecasts',
            'implementation': 'ensemble_methods'
        })
        
        return features


class PatternRecognitionEngine:
    """AI-powered pattern recognition for genomic data."""
    
    def __init__(self, config: VisualizationConfig = None):
        self.config = config or VisualizationConfig()
        
    def detect_patterns(self, data: pd.DataFrame, 
                       pattern_types: List[str] = None) -> Dict[str, Any]:
        """Detect various patterns in genomic data."""
        if pattern_types is None:
            pattern_types = ["temporal", "spatial", "clustering", "correlation", "anomaly"]
        
        logger.info(f"Detecting patterns: {pattern_types}")
        
        patterns = {}
        
        for pattern_type in pattern_types:
            try:
                if pattern_type == "temporal":
                    patterns['temporal'] = self._detect_temporal_patterns(data)
                elif pattern_type == "spatial":
                    patterns['spatial'] = self._detect_spatial_patterns(data)
                elif pattern_type == "clustering":
                    patterns['clustering'] = self._detect_clustering_patterns(data)
                elif pattern_type == "correlation":
                    patterns['correlation'] = self._detect_correlation_patterns(data)
                elif pattern_type == "anomaly":
                    patterns['anomaly'] = self._detect_anomaly_patterns(data)
            except Exception as e:
                logger.error(f"Error detecting {pattern_type} patterns: {e}")
                continue
        
        return patterns
    
    def _detect_temporal_patterns(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Detect temporal patterns in data."""
        patterns = {
            'trends': [],
            'seasonality': [],
            'cyclical': []
        }
        
        # Look for time columns
        time_columns = [col for col in data.columns if any(keyword in col.lower() 
                       for keyword in ['time', 'date', 'day', 'month', 'year'])]
        
        for time_col in time_columns:
            try:
                data[time_col] = pd.to_datetime(data[time_col])
                numeric_cols = data.select_dtypes(include=[np.number]).columns
                
                for num_col in numeric_cols:
                    if len(data) > 10:
                        # Trend detection
                        x = np.arange(len(data))
                        y = data[num_col].values
                        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                        
                        if p_value < 0.05:
                            trend_type = "increasing" if slope > 0 else "decreasing"
                            patterns['trends'].append({
                                'variable': num_col,
                                'time_variable': time_col,
                                'trend_type': trend_type,
                                'slope': slope,
                                'p_value': p_value,
                                'strength': abs(r_value)
                            })
            except:
                continue
        
        return patterns
    
    def _detect_spatial_patterns(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Detect spatial patterns in genomic data."""
        patterns = {
            'chromosomal_distribution': {},
            'genomic_hotspots': [],
            'spatial_clustering': []
        }
        
        # Look for genomic coordinates
        coord_columns = [col for col in data.columns if any(keyword in col.lower() 
                        for keyword in ['chr', 'chromosome', 'position', 'start', 'end'])]
        
        if len(coord_columns) >= 2:
            # Simple spatial clustering
            try:
                coords = data[coord_columns[:2]].values
                if len(coords) > 10:
                    # Use DBSCAN for spatial clustering
                    clustering = DBSCAN(eps=1000, min_samples=3).fit(coords)
                    labels = clustering.labels_
                    
                    # Count clusters
                    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
                    if n_clusters > 0:
                        patterns['spatial_clustering'].append({
                            'n_clusters': n_clusters,
                            'cluster_labels': labels.tolist(),
                            'coordinates': coords.tolist()
                        })
            except:
                pass
        
        return patterns
    
    def _detect_clustering_patterns(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Detect clustering patterns."""
        patterns = {
            'optimal_clusters': 0,
            'cluster_quality': 0.0,
            'cluster_characteristics': []
        }
        
        numeric_data = data.select_dtypes(include=[np.number])
        if numeric_data.shape[1] < 2 or len(numeric_data) < 10:
            return patterns
        
        # Find optimal number of clusters
        best_k = 2
        best_silhouette = -1
        
        for k in range(2, min(6, len(numeric_data)//2)):
            try:
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                labels = kmeans.fit_predict(numeric_data)
                silhouette = silhouette_score(numeric_data, labels)
                
                if silhouette > best_silhouette:
                    best_silhouette = silhouette
                    best_k = k
            except:
                continue
        
        patterns['optimal_clusters'] = best_k
        patterns['cluster_quality'] = best_silhouette
        
        # Analyze cluster characteristics
        if best_silhouette > 0.3:
            kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(numeric_data)
            
            for i in range(best_k):
                cluster_data = numeric_data[labels == i]
                characteristics = {
                    'cluster_id': i,
                    'size': len(cluster_data),
                    'centroid': cluster_data.mean().to_dict(),
                    'variance': cluster_data.var().to_dict()
                }
                patterns['cluster_characteristics'].append(characteristics)
        
        return patterns
    
    def _detect_correlation_patterns(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Detect correlation patterns."""
        patterns = {
            'strong_correlations': [],
            'correlation_clusters': [],
            'network_patterns': []
        }
        
        numeric_data = data.select_dtypes(include=[np.number])
        if numeric_data.shape[1] < 2:
            return patterns
        
        corr_matrix = numeric_data.corr()
        
        # Find strong correlations
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                corr_value = corr_matrix.iloc[i, j]
                if abs(corr_value) > 0.7:
                    patterns['strong_correlations'].append({
                        'variable1': corr_matrix.columns[i],
                        'variable2': corr_matrix.columns[j],
                        'correlation': corr_value,
                        'strength': 'strong' if abs(corr_value) > 0.8 else 'moderate'
                    })
        
        return patterns
    
    def _detect_anomaly_patterns(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Detect anomaly patterns."""
        patterns = {
            'outliers': [],
            'anomaly_clusters': [],
            'anomaly_types': []
        }
        
        numeric_data = data.select_dtypes(include=[np.number])
        if numeric_data.empty:
            return patterns
        
        # Use Isolation Forest for anomaly detection
        try:
            from sklearn.ensemble import IsolationForest
            
            detector = IsolationForest(contamination=0.1, random_state=42)
            labels = detector.fit_predict(numeric_data)
            scores = detector.decision_function(numeric_data)
            
            # Find outliers
            outlier_indices = np.where(labels == -1)[0]
            for idx in outlier_indices:
                patterns['outliers'].append({
                    'index': int(idx),
                    'anomaly_score': float(scores[idx]),
                    'values': numeric_data.iloc[idx].to_dict()
                })
        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")
        
        return patterns
