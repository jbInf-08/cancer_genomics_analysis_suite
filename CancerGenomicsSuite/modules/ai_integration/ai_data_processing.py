"""
AI-Powered Data Processing for Cancer Genomics Analysis

This module provides intelligent data preprocessing, feature engineering,
quality control, and anomaly detection using advanced AI techniques.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
from dataclasses import dataclass
from abc import ABC, abstractmethod
import warnings
warnings.filterwarnings('ignore')

# Machine Learning and AI
from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler, LabelEncoder
from sklearn.impute import KNNImputer, IterativeImputer
from sklearn.ensemble import IsolationForest, RandomForestRegressor, RandomForestClassifier
from sklearn.svm import OneClassSVM
from sklearn.cluster import DBSCAN, KMeans
from sklearn.decomposition import PCA, FastICA, TruncatedSVD
from sklearn.feature_selection import SelectKBest, SelectFromModel, RFE
from sklearn.metrics import silhouette_score, calinski_harabasz_score
from sklearn.model_selection import cross_val_score
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostRegressor, CatBoostClassifier

# Deep Learning
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import pytorch_lightning as pl

# Statistical Analysis
import scipy.stats as stats
from scipy import signal
from scipy.cluster.hierarchy import linkage, dendrogram, fcluster
from scipy.spatial.distance import pdist, squareform

# Time Series Analysis
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.arima.model import ARIMA

# Bioinformatics
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqUtils import molecular_weight, GC

# Visualization
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


@dataclass
class ProcessingConfig:
    """Configuration for AI data processing."""
    missing_value_threshold: float = 0.3
    outlier_detection_method: str = "isolation_forest"
    feature_selection_method: str = "random_forest"
    n_features_to_select: int = 100
    scaling_method: str = "robust"
    imputation_method: str = "knn"
    clustering_method: str = "dbscan"
    anomaly_threshold: float = 0.1
    quality_threshold: float = 0.8


class IntelligentDataPreprocessor:
    """AI-powered data preprocessing for genomic data."""
    
    def __init__(self, config: ProcessingConfig = None):
        self.config = config or ProcessingConfig()
        self.scalers = {}
        self.imputers = {}
        self.feature_selectors = {}
        self.is_fitted = False
        
    def preprocess_genomic_data(self, data: pd.DataFrame, 
                              data_type: str = "genomics") -> Dict[str, Any]:
        """Preprocess genomic data with AI-powered methods."""
        logger.info(f"Preprocessing {data_type} data with shape {data.shape}")
        
        results = {
            'original_shape': data.shape,
            'preprocessing_steps': [],
            'quality_metrics': {},
            'processed_data': None
        }
        
        # Step 1: Quality assessment
        quality_metrics = self._assess_data_quality(data)
        results['quality_metrics'] = quality_metrics
        results['preprocessing_steps'].append("Quality assessment completed")
        
        # Step 2: Handle missing values
        if quality_metrics['missing_percentage'] > 0:
            data = self._handle_missing_values(data, data_type)
            results['preprocessing_steps'].append("Missing value imputation completed")
        
        # Step 3: Outlier detection and handling
        outliers = self._detect_outliers(data)
        if len(outliers) > 0:
            data = self._handle_outliers(data, outliers)
            results['preprocessing_steps'].append(f"Outlier handling completed ({len(outliers)} outliers)")
        
        # Step 4: Feature scaling
        data = self._scale_features(data, data_type)
        results['preprocessing_steps'].append("Feature scaling completed")
        
        # Step 5: Feature selection
        if data.shape[1] > self.config.n_features_to_select:
            data = self._select_features(data, data_type)
            results['preprocessing_steps'].append("Feature selection completed")
        
        results['processed_data'] = data
        results['final_shape'] = data.shape
        
        self.is_fitted = True
        return results
    
    def _assess_data_quality(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Assess data quality using multiple metrics."""
        quality_metrics = {}
        
        # Missing values
        missing_counts = data.isnull().sum()
        missing_percentage = (missing_counts.sum() / (data.shape[0] * data.shape[1])) * 100
        quality_metrics['missing_percentage'] = missing_percentage
        quality_metrics['missing_by_column'] = missing_counts.to_dict()
        
        # Duplicate rows
        duplicate_count = data.duplicated().sum()
        quality_metrics['duplicate_percentage'] = (duplicate_count / data.shape[0]) * 100
        
        # Data types
        quality_metrics['data_types'] = data.dtypes.value_counts().to_dict()
        
        # Variance analysis
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        if len(numeric_columns) > 0:
            variances = data[numeric_columns].var()
            quality_metrics['low_variance_features'] = (variances < 0.01).sum()
            quality_metrics['high_variance_features'] = (variances > 100).sum()
        
        # Correlation analysis
        if len(numeric_columns) > 1:
            corr_matrix = data[numeric_columns].corr()
            high_corr_pairs = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i+1, len(corr_matrix.columns)):
                    if abs(corr_matrix.iloc[i, j]) > 0.95:
                        high_corr_pairs.append((corr_matrix.columns[i], corr_matrix.columns[j]))
            quality_metrics['highly_correlated_pairs'] = len(high_corr_pairs)
        
        return quality_metrics
    
    def _handle_missing_values(self, data: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """Handle missing values using AI-powered imputation."""
        if data_type not in self.imputers:
            if self.config.imputation_method == "knn":
                self.imputers[data_type] = KNNImputer(n_neighbors=5)
            elif self.config.imputation_method == "iterative":
                self.imputers[data_type] = IterativeImputer(random_state=42)
            else:
                # Default to median imputation
                return data.fillna(data.median())
        
        # Apply imputation to numeric columns only
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        if len(numeric_columns) > 0:
            data_imputed = data.copy()
            data_imputed[numeric_columns] = self.imputers[data_type].fit_transform(data[numeric_columns])
            return data_imputed
        
        return data
    
    def _detect_outliers(self, data: pd.DataFrame) -> List[int]:
        """Detect outliers using AI methods."""
        numeric_data = data.select_dtypes(include=[np.number])
        if numeric_data.empty:
            return []
        
        outliers = set()
        
        if self.config.outlier_detection_method == "isolation_forest":
            detector = IsolationForest(contamination=self.config.anomaly_threshold, random_state=42)
            outlier_labels = detector.fit_predict(numeric_data)
            outliers.update(np.where(outlier_labels == -1)[0])
        
        elif self.config.outlier_detection_method == "one_class_svm":
            detector = OneClassSVM(nu=self.config.anomaly_threshold)
            outlier_labels = detector.fit_predict(numeric_data)
            outliers.update(np.where(outlier_labels == -1)[0])
        
        elif self.config.outlier_detection_method == "dbscan":
            detector = DBSCAN(eps=0.5, min_samples=5)
            cluster_labels = detector.fit_predict(numeric_data)
            outliers.update(np.where(cluster_labels == -1)[0])
        
        return list(outliers)
    
    def _handle_outliers(self, data: pd.DataFrame, outliers: List[int]) -> pd.DataFrame:
        """Handle outliers by capping or removing them."""
        if len(outliers) / len(data) > 0.1:  # If more than 10% outliers, cap them
            return self._cap_outliers(data)
        else:  # Otherwise, remove them
            return data.drop(index=outliers).reset_index(drop=True)
    
    def _cap_outliers(self, data: pd.DataFrame) -> pd.DataFrame:
        """Cap outliers using IQR method."""
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        data_capped = data.copy()
        
        for col in numeric_columns:
            Q1 = data[col].quantile(0.25)
            Q3 = data[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            data_capped[col] = data_capped[col].clip(lower=lower_bound, upper=upper_bound)
        
        return data_capped
    
    def _scale_features(self, data: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """Scale features using appropriate method."""
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        if len(numeric_columns) == 0:
            return data
        
        if data_type not in self.scalers:
            if self.config.scaling_method == "standard":
                self.scalers[data_type] = StandardScaler()
            elif self.config.scaling_method == "robust":
                self.scalers[data_type] = RobustScaler()
            elif self.config.scaling_method == "minmax":
                self.scalers[data_type] = MinMaxScaler()
            else:
                return data
        
        data_scaled = data.copy()
        data_scaled[numeric_columns] = self.scalers[data_type].fit_transform(data[numeric_columns])
        
        return data_scaled
    
    def _select_features(self, data: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """Select most important features using AI methods."""
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        if len(numeric_columns) <= self.config.n_features_to_select:
            return data
        
        if self.config.feature_selection_method == "random_forest":
            selector = SelectFromModel(
                RandomForestRegressor(n_estimators=100, random_state=42),
                max_features=self.config.n_features_to_select
            )
        elif self.config.feature_selection_method == "xgboost":
            selector = SelectFromModel(
                xgb.XGBRegressor(n_estimators=100, random_state=42),
                max_features=self.config.n_features_to_select
            )
        else:
            selector = SelectKBest(k=self.config.n_features_to_select)
        
        # Fit selector
        X_selected = selector.fit_transform(data[numeric_columns], np.zeros(len(data)))
        selected_features = numeric_columns[selector.get_support()]
        
        # Create new dataframe with selected features
        data_selected = data[selected_features].copy()
        
        # Add non-numeric columns back
        non_numeric_columns = data.select_dtypes(exclude=[np.number]).columns
        if len(non_numeric_columns) > 0:
            data_selected = pd.concat([data_selected, data[non_numeric_columns]], axis=1)
        
        return data_selected


class FeatureEngineeringEngine:
    """AI-powered feature engineering for genomic data."""
    
    def __init__(self):
        self.feature_generators = {}
        self.is_fitted = False
    
    def engineer_genomic_features(self, data: pd.DataFrame, 
                                feature_types: List[str] = None) -> pd.DataFrame:
        """Engineer features for genomic data."""
        if feature_types is None:
            feature_types = ["statistical", "sequence", "interaction", "temporal"]
        
        logger.info(f"Engineering features: {feature_types}")
        
        engineered_data = data.copy()
        
        for feature_type in feature_types:
            if feature_type == "statistical":
                engineered_data = self._add_statistical_features(engineered_data)
            elif feature_type == "sequence":
                engineered_data = self._add_sequence_features(engineered_data)
            elif feature_type == "interaction":
                engineered_data = self._add_interaction_features(engineered_data)
            elif feature_type == "temporal":
                engineered_data = self._add_temporal_features(engineered_data)
        
        self.is_fitted = True
        return engineered_data
    
    def _add_statistical_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add statistical features."""
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        
        for col in numeric_columns:
            # Rolling statistics
            if len(data) > 10:
                data[f"{col}_rolling_mean_5"] = data[col].rolling(window=5).mean()
                data[f"{col}_rolling_std_5"] = data[col].rolling(window=5).std()
                data[f"{col}_rolling_skew_5"] = data[col].rolling(window=5).skew()
            
            # Percentile features
            data[f"{col}_percentile_25"] = (data[col] <= data[col].quantile(0.25)).astype(int)
            data[f"{col}_percentile_75"] = (data[col] >= data[col].quantile(0.75)).astype(int)
            
            # Z-score features
            data[f"{col}_zscore"] = (data[col] - data[col].mean()) / data[col].std()
            
            # Log transformation
            if (data[col] > 0).all():
                data[f"{col}_log"] = np.log1p(data[col])
        
        return data
    
    def _add_sequence_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add sequence-based features for genomic data."""
        # Look for sequence columns
        sequence_columns = [col for col in data.columns if 'sequence' in col.lower() or 'seq' in col.lower()]
        
        for col in sequence_columns:
            if data[col].dtype == 'object':  # String sequences
                # GC content
                data[f"{col}_gc_content"] = data[col].apply(self._calculate_gc_content)
                
                # Sequence length
                data[f"{col}_length"] = data[col].str.len()
                
                # Nucleotide composition
                data[f"{col}_A_count"] = data[col].str.count('A')
                data[f"{col}_T_count"] = data[col].str.count('T')
                data[f"{col}_G_count"] = data[col].str.count('G')
                data[f"{col}_C_count"] = data[col].str.count('C')
                
                # Dinucleotide frequency
                data[f"{col}_AA_freq"] = data[col].str.count('AA') / data[col].str.len()
                data[f"{col}_TT_freq"] = data[col].str.count('TT') / data[col].str.len()
                data[f"{col}_GG_freq"] = data[col].str.count('GG') / data[col].str.len()
                data[f"{col}_CC_freq"] = data[col].str.count('CC') / data[col].str.len()
        
        return data
    
    def _calculate_gc_content(self, sequence: str) -> float:
        """Calculate GC content of a sequence."""
        if pd.isna(sequence) or len(sequence) == 0:
            return 0.0
        
        gc_count = sequence.upper().count('G') + sequence.upper().count('C')
        total_count = len(sequence)
        
        return gc_count / total_count if total_count > 0 else 0.0
    
    def _add_interaction_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add interaction features between variables."""
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        
        # Create pairwise interactions for top correlated features
        if len(numeric_columns) > 1:
            corr_matrix = data[numeric_columns].corr()
            
            # Find highly correlated pairs
            high_corr_pairs = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i+1, len(corr_matrix.columns)):
                    if abs(corr_matrix.iloc[i, j]) > 0.7:
                        high_corr_pairs.append((corr_matrix.columns[i], corr_matrix.columns[j]))
            
            # Create interaction features
            for col1, col2 in high_corr_pairs[:5]:  # Limit to top 5 interactions
                data[f"{col1}_x_{col2}"] = data[col1] * data[col2]
                data[f"{col1}_div_{col2}"] = data[col1] / (data[col2] + 1e-8)  # Avoid division by zero
        
        return data
    
    def _add_temporal_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add temporal features if time series data is available."""
        # Look for time-related columns
        time_columns = [col for col in data.columns if any(keyword in col.lower() 
                       for keyword in ['time', 'date', 'day', 'month', 'year'])]
        
        for col in time_columns:
            if data[col].dtype == 'object':
                try:
                    # Convert to datetime
                    data[col] = pd.to_datetime(data[col])
                    
                    # Extract temporal features
                    data[f"{col}_year"] = data[col].dt.year
                    data[f"{col}_month"] = data[col].dt.month
                    data[f"{col}_day"] = data[col].dt.day
                    data[f"{col}_dayofweek"] = data[col].dt.dayofweek
                    data[f"{col}_is_weekend"] = (data[col].dt.dayofweek >= 5).astype(int)
                    
                except:
                    continue
        
        return data
    
    def create_polynomial_features(self, data: pd.DataFrame, degree: int = 2) -> pd.DataFrame:
        """Create polynomial features for numeric columns."""
        from sklearn.preprocessing import PolynomialFeatures
        
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        if len(numeric_columns) == 0:
            return data
        
        # Limit to avoid too many features
        if len(numeric_columns) > 10:
            numeric_columns = numeric_columns[:10]
        
        poly = PolynomialFeatures(degree=degree, include_bias=False, interaction_only=True)
        poly_features = poly.fit_transform(data[numeric_columns])
        
        # Create feature names
        feature_names = poly.get_feature_names_out(numeric_columns)
        
        # Create new dataframe with polynomial features
        poly_df = pd.DataFrame(poly_features, columns=feature_names, index=data.index)
        
        # Combine with original data
        result = pd.concat([data, poly_df], axis=1)
        
        return result


class QualityControlAI:
    """AI-powered quality control for genomic data."""
    
    def __init__(self):
        self.quality_models = {}
        self.thresholds = {}
        self.is_fitted = False
    
    def assess_data_quality(self, data: pd.DataFrame, 
                          data_type: str = "genomics") -> Dict[str, Any]:
        """Comprehensive quality assessment using AI."""
        logger.info(f"Assessing quality for {data_type} data")
        
        quality_report = {
            'overall_quality_score': 0.0,
            'quality_metrics': {},
            'issues_found': [],
            'recommendations': [],
            'data_quality_class': 'Unknown'
        }
        
        # Basic quality metrics
        basic_metrics = self._calculate_basic_metrics(data)
        quality_report['quality_metrics']['basic'] = basic_metrics
        
        # Statistical quality metrics
        statistical_metrics = self._calculate_statistical_metrics(data)
        quality_report['quality_metrics']['statistical'] = statistical_metrics
        
        # Consistency checks
        consistency_issues = self._check_consistency(data)
        quality_report['issues_found'].extend(consistency_issues)
        
        # Completeness assessment
        completeness_score = self._assess_completeness(data)
        quality_report['quality_metrics']['completeness'] = completeness_score
        
        # Accuracy assessment (if reference data available)
        accuracy_score = self._assess_accuracy(data)
        quality_report['quality_metrics']['accuracy'] = accuracy_score
        
        # Calculate overall quality score
        overall_score = self._calculate_overall_quality_score(quality_report)
        quality_report['overall_quality_score'] = overall_score
        
        # Classify data quality
        quality_class = self._classify_quality(overall_score)
        quality_report['data_quality_class'] = quality_class
        
        # Generate recommendations
        recommendations = self._generate_recommendations(quality_report)
        quality_report['recommendations'] = recommendations
        
        return quality_report
    
    def _calculate_basic_metrics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate basic quality metrics."""
        metrics = {}
        
        # Missing values
        missing_count = data.isnull().sum().sum()
        missing_percentage = (missing_count / (data.shape[0] * data.shape[1])) * 100
        metrics['missing_percentage'] = missing_percentage
        
        # Duplicates
        duplicate_count = data.duplicated().sum()
        duplicate_percentage = (duplicate_count / data.shape[0]) * 100
        metrics['duplicate_percentage'] = duplicate_percentage
        
        # Data types
        metrics['numeric_columns'] = len(data.select_dtypes(include=[np.number]).columns)
        metrics['categorical_columns'] = len(data.select_dtypes(include=['object']).columns)
        
        # Memory usage
        metrics['memory_usage_mb'] = data.memory_usage(deep=True).sum() / 1024 / 1024
        
        return metrics
    
    def _calculate_statistical_metrics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate statistical quality metrics."""
        metrics = {}
        numeric_data = data.select_dtypes(include=[np.number])
        
        if numeric_data.empty:
            return metrics
        
        # Variance analysis
        variances = numeric_data.var()
        metrics['low_variance_features'] = (variances < 0.01).sum()
        metrics['high_variance_features'] = (variances > 100).sum()
        
        # Skewness analysis
        skewness = numeric_data.skew()
        metrics['highly_skewed_features'] = (abs(skewness) > 2).sum()
        
        # Kurtosis analysis
        kurtosis = numeric_data.kurtosis()
        metrics['high_kurtosis_features'] = (abs(kurtosis) > 3).sum()
        
        # Correlation analysis
        corr_matrix = numeric_data.corr()
        high_corr_count = 0
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                if abs(corr_matrix.iloc[i, j]) > 0.95:
                    high_corr_count += 1
        metrics['highly_correlated_pairs'] = high_corr_count
        
        return metrics
    
    def _check_consistency(self, data: pd.DataFrame) -> List[str]:
        """Check data consistency."""
        issues = []
        
        # Check for impossible values
        numeric_data = data.select_dtypes(include=[np.number])
        for col in numeric_data.columns:
            if 'age' in col.lower():
                if (numeric_data[col] < 0).any() or (numeric_data[col] > 150).any():
                    issues.append(f"Impossible age values found in {col}")
            
            elif 'count' in col.lower() or 'number' in col.lower():
                if (numeric_data[col] < 0).any():
                    issues.append(f"Negative values found in count column {col}")
            
            elif 'percentage' in col.lower() or 'rate' in col.lower():
                if (numeric_data[col] < 0).any() or (numeric_data[col] > 1).any():
                    issues.append(f"Invalid percentage/rate values in {col}")
        
        # Check for inconsistent categorical values
        categorical_data = data.select_dtypes(include=['object'])
        for col in categorical_data.columns:
            unique_values = categorical_data[col].unique()
            # Check for similar values that might be typos
            for i, val1 in enumerate(unique_values):
                for val2 in unique_values[i+1:]:
                    if pd.notna(val1) and pd.notna(val2):
                        # Simple similarity check
                        if len(val1) > 3 and len(val2) > 3:
                            similarity = len(set(val1.lower()) & set(val2.lower())) / len(set(val1.lower()) | set(val2.lower()))
                            if similarity > 0.8:
                                issues.append(f"Similar categorical values in {col}: '{val1}' and '{val2}'")
        
        return issues
    
    def _assess_completeness(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Assess data completeness."""
        completeness = {}
        
        # Overall completeness
        total_cells = data.shape[0] * data.shape[1]
        missing_cells = data.isnull().sum().sum()
        completeness['overall_completeness'] = 1 - (missing_cells / total_cells)
        
        # Column-wise completeness
        column_completeness = {}
        for col in data.columns:
            missing_count = data[col].isnull().sum()
            column_completeness[col] = 1 - (missing_count / len(data))
        
        completeness['column_completeness'] = column_completeness
        
        # Row-wise completeness
        row_completeness = []
        for idx, row in data.iterrows():
            missing_count = row.isnull().sum()
            row_completeness.append(1 - (missing_count / len(row)))
        
        completeness['row_completeness'] = {
            'mean': np.mean(row_completeness),
            'min': np.min(row_completeness),
            'max': np.max(row_completeness),
            'std': np.std(row_completeness)
        }
        
        return completeness
    
    def _assess_accuracy(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Assess data accuracy (placeholder for reference-based validation)."""
        # This would typically compare against reference datasets
        # For now, return basic accuracy indicators
        accuracy = {
            'reference_available': False,
            'accuracy_score': 0.0,
            'validation_method': 'Not available'
        }
        
        return accuracy
    
    def _calculate_overall_quality_score(self, quality_report: Dict[str, Any]) -> float:
        """Calculate overall quality score."""
        # Weight different quality aspects
        weights = {
            'completeness': 0.3,
            'consistency': 0.25,
            'statistical': 0.2,
            'basic': 0.15,
            'accuracy': 0.1
        }
        
        score = 0.0
        
        # Completeness score
        if 'completeness' in quality_report['quality_metrics']:
            completeness = quality_report['quality_metrics']['completeness']
            if 'overall_completeness' in completeness:
                score += weights['completeness'] * completeness['overall_completeness']
        
        # Consistency score (inverse of issues)
        issues_count = len(quality_report['issues_found'])
        consistency_score = max(0, 1 - (issues_count / 10))  # Normalize to 0-1
        score += weights['consistency'] * consistency_score
        
        # Statistical score
        if 'statistical' in quality_report['quality_metrics']:
            statistical = quality_report['quality_metrics']['statistical']
            # Simple scoring based on variance and correlation issues
            variance_issues = statistical.get('low_variance_features', 0) + statistical.get('high_variance_features', 0)
            corr_issues = statistical.get('highly_correlated_pairs', 0)
            statistical_score = max(0, 1 - (variance_issues + corr_issues) / 20)
            score += weights['statistical'] * statistical_score
        
        # Basic score
        if 'basic' in quality_report['quality_metrics']:
            basic = quality_report['quality_metrics']['basic']
            missing_penalty = basic.get('missing_percentage', 0) / 100
            duplicate_penalty = basic.get('duplicate_percentage', 0) / 100
            basic_score = max(0, 1 - missing_penalty - duplicate_penalty)
            score += weights['basic'] * basic_score
        
        # Accuracy score
        if 'accuracy' in quality_report['quality_metrics']:
            accuracy = quality_report['quality_metrics']['accuracy']
            score += weights['accuracy'] * accuracy.get('accuracy_score', 0.5)
        
        return min(1.0, max(0.0, score))
    
    def _classify_quality(self, score: float) -> str:
        """Classify data quality based on score."""
        if score >= 0.9:
            return "Excellent"
        elif score >= 0.8:
            return "Good"
        elif score >= 0.7:
            return "Fair"
        elif score >= 0.6:
            return "Poor"
        else:
            return "Very Poor"
    
    def _generate_recommendations(self, quality_report: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on quality assessment."""
        recommendations = []
        
        # Missing data recommendations
        if 'basic' in quality_report['quality_metrics']:
            missing_pct = quality_report['quality_metrics']['basic'].get('missing_percentage', 0)
            if missing_pct > 20:
                recommendations.append("High missing data percentage. Consider data imputation or collection.")
            elif missing_pct > 5:
                recommendations.append("Moderate missing data. Review data collection process.")
        
        # Duplicate recommendations
        duplicate_pct = quality_report['quality_metrics']['basic'].get('duplicate_percentage', 0)
        if duplicate_pct > 5:
            recommendations.append("High duplicate percentage. Review data deduplication process.")
        
        # Statistical recommendations
        if 'statistical' in quality_report['quality_metrics']:
            statistical = quality_report['quality_metrics']['statistical']
            if statistical.get('low_variance_features', 0) > 5:
                recommendations.append("Many low-variance features detected. Consider feature selection.")
            if statistical.get('highly_correlated_pairs', 0) > 10:
                recommendations.append("High correlation between features. Consider dimensionality reduction.")
        
        # Consistency recommendations
        if len(quality_report['issues_found']) > 5:
            recommendations.append("Multiple consistency issues found. Review data validation rules.")
        
        # Overall recommendations
        if quality_report['overall_quality_score'] < 0.7:
            recommendations.append("Overall data quality is below acceptable threshold. Comprehensive data cleaning recommended.")
        
        return recommendations


class AnomalyDetector:
    """AI-powered anomaly detection for genomic data."""
    
    def __init__(self):
        self.detectors = {}
        self.is_fitted = False
    
    def detect_anomalies(self, data: pd.DataFrame, 
                        methods: List[str] = None) -> Dict[str, Any]:
        """Detect anomalies using multiple AI methods."""
        if methods is None:
            methods = ["isolation_forest", "one_class_svm", "dbscan", "autoencoder"]
        
        logger.info(f"Detecting anomalies using methods: {methods}")
        
        results = {
            'anomaly_scores': {},
            'anomaly_labels': {},
            'consensus_anomalies': [],
            'anomaly_summary': {}
        }
        
        numeric_data = data.select_dtypes(include=[np.number])
        if numeric_data.empty:
            logger.warning("No numeric data found for anomaly detection")
            return results
        
        # Apply each detection method
        for method in methods:
            try:
                if method == "isolation_forest":
                    scores, labels = self._isolation_forest_detection(numeric_data)
                elif method == "one_class_svm":
                    scores, labels = self._one_class_svm_detection(numeric_data)
                elif method == "dbscan":
                    scores, labels = self._dbscan_detection(numeric_data)
                elif method == "autoencoder":
                    scores, labels = self._autoencoder_detection(numeric_data)
                else:
                    continue
                
                results['anomaly_scores'][method] = scores
                results['anomaly_labels'][method] = labels
                
            except Exception as e:
                logger.error(f"Error in {method} detection: {e}")
                continue
        
        # Create consensus
        if len(results['anomaly_labels']) > 1:
            results['consensus_anomalies'] = self._create_consensus(results['anomaly_labels'])
        
        # Generate summary
        results['anomaly_summary'] = self._generate_anomaly_summary(results)
        
        self.is_fitted = True
        return results
    
    def _isolation_forest_detection(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Detect anomalies using Isolation Forest."""
        detector = IsolationForest(contamination=0.1, random_state=42)
        labels = detector.fit_predict(data)
        scores = detector.decision_function(data)
        
        # Convert to anomaly scores (higher = more anomalous)
        scores = -scores
        
        return scores, labels
    
    def _one_class_svm_detection(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Detect anomalies using One-Class SVM."""
        detector = OneClassSVM(nu=0.1, kernel='rbf')
        labels = detector.fit_predict(data)
        scores = detector.decision_function(data)
        
        # Convert to anomaly scores
        scores = -scores
        
        return scores, labels
    
    def _dbscan_detection(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Detect anomalies using DBSCAN."""
        detector = DBSCAN(eps=0.5, min_samples=5)
        labels = detector.fit_predict(data)
        
        # Create scores based on distance to nearest cluster
        scores = np.zeros(len(data))
        for i, label in enumerate(labels):
            if label == -1:  # Noise point
                scores[i] = 1.0
            else:
                # Calculate distance to cluster center
                cluster_points = data[labels == label]
                if len(cluster_points) > 0:
                    center = cluster_points.mean()
                    scores[i] = np.linalg.norm(data.iloc[i] - center)
        
        return scores, labels
    
    def _autoencoder_detection(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Detect anomalies using Autoencoder."""
        # Simple autoencoder implementation
        input_dim = data.shape[1]
        encoding_dim = max(2, input_dim // 2)
        
        # Normalize data
        scaler = StandardScaler()
        data_scaled = scaler.fit_transform(data)
        
        # Create autoencoder
        class Autoencoder(nn.Module):
            def __init__(self, input_dim, encoding_dim):
                super(Autoencoder, self).__init__()
                self.encoder = nn.Sequential(
                    nn.Linear(input_dim, encoding_dim),
                    nn.ReLU()
                )
                self.decoder = nn.Sequential(
                    nn.Linear(encoding_dim, input_dim),
                    nn.Sigmoid()
                )
            
            def forward(self, x):
                encoded = self.encoder(x)
                decoded = self.decoder(encoded)
                return decoded
        
        # Train autoencoder
        model = Autoencoder(input_dim, encoding_dim)
        criterion = nn.MSELoss()
        optimizer = optim.Adam(model.parameters(), lr=0.001)
        
        data_tensor = torch.FloatTensor(data_scaled)
        
        for epoch in range(100):
            optimizer.zero_grad()
            output = model(data_tensor)
            loss = criterion(output, data_tensor)
            loss.backward()
            optimizer.step()
        
        # Calculate reconstruction errors
        with torch.no_grad():
            reconstructed = model(data_tensor)
            reconstruction_errors = torch.mean((data_tensor - reconstructed) ** 2, dim=1).numpy()
        
        # Convert to anomaly scores
        scores = reconstruction_errors
        
        # Create labels based on threshold
        threshold = np.percentile(scores, 90)
        labels = np.where(scores > threshold, -1, 1)
        
        return scores, labels
    
    def _create_consensus(self, anomaly_labels: Dict[str, np.ndarray]) -> List[int]:
        """Create consensus anomaly list from multiple methods."""
        consensus = []
        
        # Get all anomaly indices
        all_anomalies = set()
        for method, labels in anomaly_labels.items():
            anomalies = np.where(labels == -1)[0]
            all_anomalies.update(anomalies)
        
        # Count votes for each anomaly
        votes = {}
        for anomaly in all_anomalies:
            votes[anomaly] = 0
            for method, labels in anomaly_labels.items():
                if labels[anomaly] == -1:
                    votes[anomaly] += 1
        
        # Consensus: anomaly if voted by majority of methods
        majority_threshold = len(anomaly_labels) / 2
        consensus = [anomaly for anomaly, vote_count in votes.items() 
                    if vote_count > majority_threshold]
        
        return consensus
    
    def _generate_anomaly_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of anomaly detection results."""
        summary = {
            'total_anomalies': 0,
            'anomaly_percentage': 0.0,
            'method_agreement': {},
            'top_anomalous_features': []
        }
        
        if 'consensus_anomalies' in results:
            summary['total_anomalies'] = len(results['consensus_anomalies'])
            # Calculate percentage (assuming we know total data size)
            if 'anomaly_scores' in results and results['anomaly_scores']:
                total_samples = len(list(results['anomaly_scores'].values())[0])
                summary['anomaly_percentage'] = (summary['total_anomalies'] / total_samples) * 100
        
        # Calculate method agreement
        if 'anomaly_labels' in results and len(results['anomaly_labels']) > 1:
            methods = list(results['anomaly_labels'].keys())
            for i, method1 in enumerate(methods):
                for method2 in methods[i+1:]:
                    labels1 = results['anomaly_labels'][method1]
                    labels2 = results['anomaly_labels'][method2]
                    agreement = np.mean(labels1 == labels2)
                    summary['method_agreement'][f"{method1}_vs_{method2}"] = agreement
        
        return summary
