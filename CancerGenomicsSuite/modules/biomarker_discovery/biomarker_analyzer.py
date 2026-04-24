"""
Biomarker Analyzer for Cancer Genomics Analysis

This module provides comprehensive biomarker discovery and analysis capabilities
including statistical analysis, machine learning, and validation methods.
"""

import numpy as np
import pandas as pd
import scipy.stats as stats
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
from dataclasses import dataclass
from abc import ABC, abstractmethod
import warnings
warnings.filterwarnings('ignore')

# Machine Learning
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.svm import SVC, SVR
from sklearn.linear_model import LogisticRegression, ElasticNet
from sklearn.model_selection import cross_val_score, StratifiedKFold, GridSearchCV
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score, f1_score
from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif
from sklearn.preprocessing import StandardScaler, LabelEncoder

# Apply compatibility patches before importing ML libraries
try:
    import sys
    import os
    # Add the integrations directory to path to import the patch
    integrations_path = os.path.join(os.path.dirname(__file__), '..', '..', 'integrations')
    if integrations_path not in sys.path:
        sys.path.insert(0, integrations_path)
    
    from dask_compatibility_patch import patch_lightgbm_import, patch_xgboost_import
except ImportError:
    # If patch is not available, use standard imports
    def patch_lightgbm_import():
        try:
            import lightgbm
            return True
        except ImportError:
            return False
    
    def patch_xgboost_import():
        try:
            import xgboost
            return True
        except ImportError:
            return False

# Import ML libraries with patches
XGBOOST_AVAILABLE = patch_xgboost_import()
if XGBOOST_AVAILABLE:
    import xgboost as xgb
else:
    xgb = None

LIGHTGBM_AVAILABLE = patch_lightgbm_import()
if LIGHTGBM_AVAILABLE:
    import lightgbm as lgb
else:
    lgb = None

# Statistical Analysis
from scipy.stats import ttest_ind, mannwhitneyu, chi2_contingency, pearsonr, spearmanr
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.contingency_tables import mcnemar

# Bioinformatics
from Bio import Entrez
from Bio.Entrez import efetch, esearch

logger = logging.getLogger(__name__)


@dataclass
class BiomarkerResult:
    """Data class for biomarker analysis results."""
    biomarker_id: str
    biomarker_name: str
    biomarker_type: str
    p_value: float
    effect_size: float
    confidence_interval: Tuple[float, float]
    sensitivity: float
    specificity: float
    auc_score: float
    clinical_significance: str
    validation_status: str
    supporting_evidence: List[str]
    metadata: Dict[str, Any]


@dataclass
class BiomarkerDiscoveryConfig:
    """Configuration for biomarker discovery analysis."""
    p_value_threshold: float = 0.05
    effect_size_threshold: float = 0.2
    auc_threshold: float = 0.7
    multiple_testing_correction: str = 'fdr_bh'
    cross_validation_folds: int = 5
    random_state: int = 42
    min_samples_per_group: int = 10
    feature_selection_method: str = 'mutual_info'
    n_top_features: int = 100


class BiomarkerAnalyzer:
    """Main biomarker analyzer class."""
    
    def __init__(self, config: Optional[BiomarkerDiscoveryConfig] = None):
        """Initialize the biomarker analyzer."""
        self.config = config or BiomarkerDiscoveryConfig()
        self.results = []
        self.logger = logging.getLogger(__name__)
        
    def discover_biomarkers(self, 
                          data: pd.DataFrame, 
                          labels: pd.Series, 
                          biomarker_type: str = 'gene_expression',
                          **kwargs) -> List[BiomarkerResult]:
        """
        Discover biomarkers from omics data.
        
        Args:
            data: Feature matrix (samples x features)
            labels: Binary or continuous labels
            biomarker_type: Type of biomarker data
            **kwargs: Additional parameters
            
        Returns:
            List of discovered biomarkers
        """
        self.logger.info(f"Starting biomarker discovery for {biomarker_type}")
        
        # Statistical analysis
        statistical_results = self._statistical_analysis(data, labels)
        
        # Machine learning analysis
        ml_results = self._ml_analysis(data, labels)
        
        # Combine and rank results
        combined_results = self._combine_results(statistical_results, ml_results)
        
        # Validate biomarkers
        validated_results = self._validate_biomarkers(combined_results, data, labels)
        
        self.results = validated_results
        self.logger.info(f"Discovered {len(validated_results)} biomarkers")
        
        return validated_results
    
    def _statistical_analysis(self, 
                            data: pd.DataFrame, 
                            labels: pd.Series) -> List[BiomarkerResult]:
        """Perform statistical analysis for biomarker discovery."""
        results = []
        
        # Determine if labels are continuous or categorical
        is_continuous = pd.api.types.is_numeric_dtype(labels) and len(labels.unique()) > 2
        
        for feature in data.columns:
            try:
                feature_data = data[feature].dropna()
                feature_labels = labels[feature_data.index]
                
                if len(feature_data) < self.config.min_samples_per_group:
                    continue
                
                if is_continuous:
                    # Correlation analysis for continuous labels
                    correlation, p_value = pearsonr(feature_data, feature_labels)
                    effect_size = abs(correlation)
                else:
                    # Group comparison for categorical labels
                    groups = [feature_data[feature_labels == label] for label in feature_labels.unique()]
                    if len(groups) == 2:
                        # Two-group comparison
                        stat, p_value = ttest_ind(groups[0], groups[1])
                        effect_size = self._calculate_cohens_d(groups[0], groups[1])
                    else:
                        # Multiple group comparison (ANOVA)
                        stat, p_value = stats.f_oneway(*groups)
                        effect_size = self._calculate_eta_squared(groups)
                
                # Calculate performance metrics
                auc_score = self._calculate_auc(feature_data, feature_labels)
                sensitivity, specificity = self._calculate_sensitivity_specificity(
                    feature_data, feature_labels
                )
                
                # Determine clinical significance
                clinical_significance = self._assess_clinical_significance(
                    p_value, effect_size, auc_score
                )
                
                result = BiomarkerResult(
                    biomarker_id=feature,
                    biomarker_name=feature,
                    biomarker_type='statistical',
                    p_value=p_value,
                    effect_size=effect_size,
                    confidence_interval=self._calculate_confidence_interval(
                        feature_data, feature_labels
                    ),
                    sensitivity=sensitivity,
                    specificity=specificity,
                    auc_score=auc_score,
                    clinical_significance=clinical_significance,
                    validation_status='discovered',
                    supporting_evidence=[],
                    metadata={'statistical_test': 'ttest' if not is_continuous else 'correlation'}
                )
                
                results.append(result)
                
            except Exception as e:
                self.logger.warning(f"Error analyzing feature {feature}: {e}")
                continue
        
        # Multiple testing correction
        p_values = [r.p_value for r in results]
        corrected_p_values = multipletests(
            p_values, 
            method=self.config.multiple_testing_correction
        )[1]
        
        for i, result in enumerate(results):
            result.p_value = corrected_p_values[i]
        
        return results
    
    def _ml_analysis(self, 
                    data: pd.DataFrame, 
                    labels: pd.Series) -> List[BiomarkerResult]:
        """Perform machine learning analysis for biomarker discovery."""
        results = []
        
        # Feature selection
        n_features = min(self.config.n_top_features, len(data.columns))
        selected_features = self._select_features(data, labels, n_features)
        
        # Train models and evaluate feature importance
        models = {
            'random_forest': RandomForestClassifier(n_estimators=100, random_state=self.config.random_state)
        }
        
        # Add optional models if available
        if XGBOOST_AVAILABLE:
            models['xgboost'] = xgb.XGBClassifier(random_state=self.config.random_state)
        if LIGHTGBM_AVAILABLE:
            models['lightgbm'] = lgb.LGBMClassifier(random_state=self.config.random_state)
        
        for model_name, model in models.items():
            try:
                # Train model
                model.fit(data[selected_features], labels)
                
                # Get feature importance
                if hasattr(model, 'feature_importances_'):
                    importances = model.feature_importances_
                else:
                    importances = np.abs(model.coef_[0]) if hasattr(model, 'coef_') else np.zeros(len(selected_features))
                
                # Cross-validation performance
                cv_scores = cross_val_score(
                    model, data[selected_features], labels, 
                    cv=StratifiedKFold(n_splits=self.config.cross_validation_folds),
                    scoring='roc_auc'
                )
                
                # Create results for top features
                feature_importance_pairs = list(zip(selected_features, importances))
                feature_importance_pairs.sort(key=lambda x: x[1], reverse=True)
                
                for feature, importance in feature_importance_pairs[:self.config.n_top_features]:
                    # Calculate performance metrics for this feature
                    feature_data = data[feature].dropna()
                    feature_labels = labels[feature_data.index]
                    
                    auc_score = self._calculate_auc(feature_data, feature_labels)
                    sensitivity, specificity = self._calculate_sensitivity_specificity(
                        feature_data, feature_labels
                    )
                    
                    result = BiomarkerResult(
                        biomarker_id=f"{feature}_{model_name}",
                        biomarker_name=feature,
                        biomarker_type='ml',
                        p_value=1.0 - (importance / max(importances)),  # Convert importance to p-value-like metric
                        effect_size=importance,
                        confidence_interval=self._calculate_confidence_interval(
                            feature_data, feature_labels
                        ),
                        sensitivity=sensitivity,
                        specificity=specificity,
                        auc_score=auc_score,
                        clinical_significance=self._assess_clinical_significance(
                            1.0 - importance, importance, auc_score
                        ),
                        validation_status='discovered',
                        supporting_evidence=[f'{model_name}_importance'],
                        metadata={
                            'model': model_name,
                            'importance': importance,
                            'cv_score_mean': cv_scores.mean(),
                            'cv_score_std': cv_scores.std()
                        }
                    )
                    
                    results.append(result)
                    
            except Exception as e:
                self.logger.warning(f"Error with {model_name}: {e}")
                continue
        
        return results
    
    def _select_features(self, data: pd.DataFrame, labels: pd.Series, n_features: int = None) -> List[str]:
        """Select top features using specified method."""
        if n_features is None:
            n_features = self.config.n_top_features
        
        if self.config.feature_selection_method == 'mutual_info':
            selector = SelectKBest(score_func=mutual_info_classif, k=n_features)
        else:
            selector = SelectKBest(score_func=f_classif, k=n_features)
        
        selector.fit(data, labels)
        selected_features = data.columns[selector.get_support()].tolist()
        
        return selected_features
    
    def _combine_results(self, 
                        statistical_results: List[BiomarkerResult], 
                        ml_results: List[BiomarkerResult]) -> List[BiomarkerResult]:
        """Combine and rank results from different methods."""
        all_results = statistical_results + ml_results
        
        # Create a scoring system
        for result in all_results:
            score = (
                (1 - result.p_value) * 0.3 +  # P-value component
                result.effect_size * 0.3 +    # Effect size component
                result.auc_score * 0.4        # AUC component
            )
            result.metadata['combined_score'] = score
        
        # Sort by combined score
        all_results.sort(key=lambda x: x.metadata['combined_score'], reverse=True)
        
        return all_results
    
    def _validate_biomarkers(self, 
                           results: List[BiomarkerResult], 
                           data: pd.DataFrame, 
                           labels: pd.Series) -> List[BiomarkerResult]:
        """Validate discovered biomarkers."""
        validated_results = []
        
        for result in results:
            # Apply thresholds
            if (result.p_value < self.config.p_value_threshold and 
                result.effect_size > self.config.effect_size_threshold and
                result.auc_score > self.config.auc_threshold):
                
                # Add validation information
                result.validation_status = 'validated'
                result.supporting_evidence.append('threshold_validation')
                
                # Cross-validation validation
                cv_auc = self._cross_validate_biomarker(
                    data[result.biomarker_name], labels
                )
                result.metadata['cv_auc'] = cv_auc
                
                if cv_auc > self.config.auc_threshold:
                    result.supporting_evidence.append('cross_validation')
                
                validated_results.append(result)
        
        return validated_results
    
    def _cross_validate_biomarker(self, feature_data: pd.Series, labels: pd.Series) -> float:
        """Perform cross-validation for a single biomarker."""
        try:
            # Remove NaN values
            valid_indices = feature_data.notna()
            feature_clean = feature_data[valid_indices]
            labels_clean = labels[valid_indices]
            
            if len(feature_clean) < 10:
                return 0.0
            
            # Simple logistic regression cross-validation
            from sklearn.linear_model import LogisticRegression
            from sklearn.model_selection import cross_val_score
            
            model = LogisticRegression(random_state=self.config.random_state)
            cv_scores = cross_val_score(
                model, feature_clean.values.reshape(-1, 1), labels_clean,
                cv=min(5, len(feature_clean) // 2),
                scoring='roc_auc'
            )
            
            return cv_scores.mean()
            
        except Exception as e:
            self.logger.warning(f"Error in cross-validation: {e}")
            return 0.0
    
    def _calculate_cohens_d(self, group1: pd.Series, group2: pd.Series) -> float:
        """Calculate Cohen's d effect size."""
        n1, n2 = len(group1), len(group2)
        s1, s2 = group1.std(), group2.std()
        
        # Pooled standard deviation
        pooled_std = np.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
        
        # Cohen's d
        d = (group1.mean() - group2.mean()) / pooled_std
        
        return abs(d)
    
    def _calculate_eta_squared(self, groups: List[pd.Series]) -> float:
        """Calculate eta squared effect size for ANOVA."""
        # Simplified implementation
        all_data = pd.concat(groups)
        grand_mean = all_data.mean()
        
        # Between-group sum of squares
        ss_between = sum(len(group) * (group.mean() - grand_mean)**2 for group in groups)
        
        # Total sum of squares
        ss_total = sum((all_data - grand_mean)**2)
        
        return ss_between / ss_total if ss_total > 0 else 0.0
    
    def _calculate_auc(self, feature_data: pd.Series, labels: pd.Series) -> float:
        """Calculate AUC score for a feature."""
        try:
            from sklearn.metrics import roc_auc_score
            
            # Handle binary classification
            if len(labels.unique()) == 2:
                return roc_auc_score(labels, feature_data)
            else:
                # For continuous labels, use correlation as proxy
                correlation, _ = pearsonr(feature_data, labels)
                return (abs(correlation) + 1) / 2  # Convert to 0-1 scale
                
        except Exception as e:
            self.logger.warning(f"Error calculating AUC: {e}")
            return 0.5
    
    def _calculate_sensitivity_specificity(self, 
                                         feature_data: pd.Series, 
                                         labels: pd.Series) -> Tuple[float, float]:
        """Calculate sensitivity and specificity."""
        try:
            if len(labels.unique()) != 2:
                return 0.5, 0.5
            
            # Use median as threshold
            threshold = feature_data.median()
            
            # Binary predictions
            predictions = (feature_data > threshold).astype(int)
            
            # Calculate confusion matrix elements
            tp = ((predictions == 1) & (labels == 1)).sum()
            tn = ((predictions == 0) & (labels == 0)).sum()
            fp = ((predictions == 1) & (labels == 0)).sum()
            fn = ((predictions == 0) & (labels == 1)).sum()
            
            sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
            
            return sensitivity, specificity
            
        except Exception as e:
            self.logger.warning(f"Error calculating sensitivity/specificity: {e}")
            return 0.5, 0.5
    
    def _calculate_confidence_interval(self, 
                                     feature_data: pd.Series, 
                                     labels: pd.Series) -> Tuple[float, float]:
        """Calculate 95% confidence interval for effect size."""
        try:
            # Simple implementation using bootstrap
            n_bootstrap = 100
            effect_sizes = []
            
            for _ in range(n_bootstrap):
                # Bootstrap sample
                indices = np.random.choice(len(feature_data), size=len(feature_data), replace=True)
                boot_data = feature_data.iloc[indices]
                boot_labels = labels.iloc[indices]
                
                # Calculate effect size
                if len(boot_labels.unique()) == 2:
                    groups = [boot_data[boot_labels == label] for label in boot_labels.unique()]
                    if len(groups) == 2:
                        effect_size = self._calculate_cohens_d(groups[0], groups[1])
                        effect_sizes.append(effect_size)
            
            if effect_sizes:
                ci_lower = np.percentile(effect_sizes, 2.5)
                ci_upper = np.percentile(effect_sizes, 97.5)
                return (ci_lower, ci_upper)
            else:
                return (0.0, 0.0)
                
        except Exception as e:
            self.logger.warning(f"Error calculating confidence interval: {e}")
            return (0.0, 0.0)
    
    def _assess_clinical_significance(self, 
                                    p_value: float, 
                                    effect_size: float, 
                                    auc_score: float) -> str:
        """Assess clinical significance of biomarker."""
        if p_value < 0.001 and effect_size > 0.8 and auc_score > 0.9:
            return 'high'
        elif p_value < 0.01 and effect_size > 0.5 and auc_score > 0.8:
            return 'moderate'
        elif p_value < 0.05 and effect_size > 0.2 and auc_score > 0.7:
            return 'low'
        else:
            return 'minimal'
    
    def get_top_biomarkers(self, n: int = 10) -> List[BiomarkerResult]:
        """Get top N biomarkers by combined score."""
        if not self.results:
            return []
        
        return self.results[:n]
    
    def export_results(self, filepath: str, format: str = 'csv') -> None:
        """Export biomarker results to file."""
        if not self.results:
            self.logger.warning("No results to export")
            return
        
        # Convert results to DataFrame
        results_data = []
        for result in self.results:
            row = {
                'biomarker_id': result.biomarker_id,
                'biomarker_name': result.biomarker_name,
                'biomarker_type': result.biomarker_type,
                'p_value': result.p_value,
                'effect_size': result.effect_size,
                'sensitivity': result.sensitivity,
                'specificity': result.specificity,
                'auc_score': result.auc_score,
                'clinical_significance': result.clinical_significance,
                'validation_status': result.validation_status,
                'supporting_evidence': '; '.join(result.supporting_evidence)
            }
            row.update(result.metadata)
            results_data.append(row)
        
        df = pd.DataFrame(results_data)
        
        if format.lower() == 'csv':
            df.to_csv(filepath, index=False)
        elif format.lower() == 'excel':
            df.to_excel(filepath, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        self.logger.info(f"Results exported to {filepath}")


class StatisticalBiomarkerDiscovery(BiomarkerAnalyzer):
    """Specialized class for statistical biomarker discovery."""
    
    def __init__(self, config: Optional[BiomarkerDiscoveryConfig] = None):
        super().__init__(config)
        self.statistical_tests = {
            'ttest': ttest_ind,
            'mannwhitney': mannwhitneyu,
            'chi2': chi2_contingency
        }
    
    def discover_biomarkers(self, 
                          data: pd.DataFrame, 
                          labels: pd.Series, 
                          test_type: str = 'ttest',
                          **kwargs) -> List[BiomarkerResult]:
        """Discover biomarkers using statistical tests."""
        self.logger.info(f"Starting statistical biomarker discovery using {test_type}")
        
        results = []
        
        for feature in data.columns:
            try:
                feature_data = data[feature].dropna()
                feature_labels = labels[feature_data.index]
                
                if len(feature_data) < self.config.min_samples_per_group:
                    continue
                
                # Perform statistical test
                if test_type == 'ttest':
                    stat, p_value = ttest_ind(
                        feature_data[feature_labels == feature_labels.unique()[0]],
                        feature_data[feature_labels == feature_labels.unique()[1]]
                    )
                elif test_type == 'mannwhitney':
                    stat, p_value = mannwhitneyu(
                        feature_data[feature_labels == feature_labels.unique()[0]],
                        feature_data[feature_labels == feature_labels.unique()[1]]
                    )
                else:
                    continue
                
                # Calculate effect size
                effect_size = self._calculate_cohens_d(
                    feature_data[feature_labels == feature_labels.unique()[0]],
                    feature_data[feature_labels == feature_labels.unique()[1]]
                )
                
                # Calculate performance metrics
                auc_score = self._calculate_auc(feature_data, feature_labels)
                sensitivity, specificity = self._calculate_sensitivity_specificity(
                    feature_data, feature_labels
                )
                
                result = BiomarkerResult(
                    biomarker_id=feature,
                    biomarker_name=feature,
                    biomarker_type='statistical',
                    p_value=p_value,
                    effect_size=effect_size,
                    confidence_interval=self._calculate_confidence_interval(
                        feature_data, feature_labels
                    ),
                    sensitivity=sensitivity,
                    specificity=specificity,
                    auc_score=auc_score,
                    clinical_significance=self._assess_clinical_significance(
                        p_value, effect_size, auc_score
                    ),
                    validation_status='discovered',
                    supporting_evidence=[f'{test_type}_test'],
                    metadata={'statistical_test': test_type, 'test_statistic': stat}
                )
                
                results.append(result)
                
            except Exception as e:
                self.logger.warning(f"Error analyzing feature {feature}: {e}")
                continue
        
        # Multiple testing correction
        p_values = [r.p_value for r in results]
        corrected_p_values = multipletests(
            p_values, 
            method=self.config.multiple_testing_correction
        )[1]
        
        for i, result in enumerate(results):
            result.p_value = corrected_p_values[i]
        
        # Filter by thresholds
        filtered_results = [
            r for r in results 
            if (r.p_value < self.config.p_value_threshold and 
                r.effect_size > self.config.effect_size_threshold)
        ]
        
        self.results = filtered_results
        self.logger.info(f"Discovered {len(filtered_results)} statistical biomarkers")
        
        return filtered_results


class MLBiomarkerDiscovery(BiomarkerAnalyzer):
    """Specialized class for machine learning-based biomarker discovery."""
    
    def __init__(self, config: Optional[BiomarkerDiscoveryConfig] = None):
        super().__init__(config)
        self.models = {
            'random_forest': RandomForestClassifier,
            'svm': SVC,
            'logistic': LogisticRegression
        }
        
        # Add optional models if available
        if XGBOOST_AVAILABLE:
            self.models['xgboost'] = xgb.XGBClassifier
        if LIGHTGBM_AVAILABLE:
            self.models['lightgbm'] = lgb.LGBMClassifier
    
    def discover_biomarkers(self, 
                          data: pd.DataFrame, 
                          labels: pd.Series, 
                          model_type: str = 'random_forest',
                          **kwargs) -> List[BiomarkerResult]:
        """Discover biomarkers using machine learning."""
        self.logger.info(f"Starting ML biomarker discovery using {model_type}")
        
        # Feature selection
        n_features = min(self.config.n_top_features, len(data.columns))
        selected_features = self._select_features(data, labels, n_features)
        
        # Train model
        model_class = self.models.get(model_type, RandomForestClassifier)
        model = model_class(random_state=self.config.random_state)
        
        try:
            model.fit(data[selected_features], labels)
            
            # Get feature importance
            if hasattr(model, 'feature_importances_'):
                importances = model.feature_importances_
            else:
                importances = np.abs(model.coef_[0]) if hasattr(model, 'coef_') else np.zeros(len(selected_features))
            
            # Cross-validation performance
            cv_scores = cross_val_score(
                model, data[selected_features], labels, 
                cv=StratifiedKFold(n_splits=self.config.cross_validation_folds),
                scoring='roc_auc'
            )
            
            # Create results
            results = []
            feature_importance_pairs = list(zip(selected_features, importances))
            feature_importance_pairs.sort(key=lambda x: x[1], reverse=True)
            
            for feature, importance in feature_importance_pairs:
                feature_data = data[feature].dropna()
                feature_labels = labels[feature_data.index]
                
                auc_score = self._calculate_auc(feature_data, feature_labels)
                sensitivity, specificity = self._calculate_sensitivity_specificity(
                    feature_data, feature_labels
                )
                
                result = BiomarkerResult(
                    biomarker_id=f"{feature}_{model_type}",
                    biomarker_name=feature,
                    biomarker_type='ml',
                    p_value=1.0 - (importance / max(importances)),
                    effect_size=importance,
                    confidence_interval=self._calculate_confidence_interval(
                        feature_data, feature_labels
                    ),
                    sensitivity=sensitivity,
                    specificity=specificity,
                    auc_score=auc_score,
                    clinical_significance=self._assess_clinical_significance(
                        1.0 - importance, importance, auc_score
                    ),
                    validation_status='discovered',
                    supporting_evidence=[f'{model_type}_importance'],
                    metadata={
                        'model': model_type,
                        'importance': importance,
                        'cv_score_mean': cv_scores.mean(),
                        'cv_score_std': cv_scores.std()
                    }
                )
                
                results.append(result)
            
            # Filter by thresholds
            filtered_results = [
                r for r in results 
                if (r.effect_size > self.config.effect_size_threshold and
                    r.auc_score > self.config.auc_threshold)
            ]
            
            self.results = filtered_results
            self.logger.info(f"Discovered {len(filtered_results)} ML biomarkers")
            
            return filtered_results
            
        except Exception as e:
            self.logger.error(f"Error in ML biomarker discovery: {e}")
            return []


class BiomarkerValidator:
    """Class for validating discovered biomarkers."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_biomarker(self, 
                         biomarker: BiomarkerResult, 
                         validation_data: pd.DataFrame, 
                         validation_labels: pd.Series) -> Dict[str, Any]:
        """Validate a single biomarker on independent data."""
        try:
            feature_data = validation_data[biomarker.biomarker_name].dropna()
            feature_labels = validation_labels[feature_data.index]
            
            # Calculate performance metrics
            auc_score = self._calculate_auc(feature_data, feature_labels)
            sensitivity, specificity = self._calculate_sensitivity_specificity(
                feature_data, feature_labels
            )
            
            # Statistical test
            if len(feature_labels.unique()) == 2:
                groups = [feature_data[feature_labels == label] for label in feature_labels.unique()]
                if len(groups) == 2:
                    _, p_value = ttest_ind(groups[0], groups[1])
                else:
                    p_value = 1.0
            else:
                correlation, p_value = pearsonr(feature_data, feature_labels)
            
            validation_result = {
                'biomarker_id': biomarker.biomarker_id,
                'validation_auc': auc_score,
                'validation_sensitivity': sensitivity,
                'validation_specificity': specificity,
                'validation_p_value': p_value,
                'validation_status': 'validated' if auc_score > 0.7 and p_value < 0.05 else 'failed',
                'performance_change': {
                    'auc_change': auc_score - biomarker.auc_score,
                    'sensitivity_change': sensitivity - biomarker.sensitivity,
                    'specificity_change': specificity - biomarker.specificity
                }
            }
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Error validating biomarker {biomarker.biomarker_id}: {e}")
            return {'error': str(e)}
    
    def _calculate_auc(self, feature_data: pd.Series, labels: pd.Series) -> float:
        """Calculate AUC score."""
        try:
            from sklearn.metrics import roc_auc_score
            if len(labels.unique()) == 2:
                return roc_auc_score(labels, feature_data)
            else:
                correlation, _ = pearsonr(feature_data, labels)
                return (abs(correlation) + 1) / 2
        except:
            return 0.5
    
    def _calculate_sensitivity_specificity(self, 
                                         feature_data: pd.Series, 
                                         labels: pd.Series) -> Tuple[float, float]:
        """Calculate sensitivity and specificity."""
        try:
            if len(labels.unique()) != 2:
                return 0.5, 0.5
            
            threshold = feature_data.median()
            predictions = (feature_data > threshold).astype(int)
            
            tp = ((predictions == 1) & (labels == 1)).sum()
            tn = ((predictions == 0) & (labels == 0)).sum()
            fp = ((predictions == 1) & (labels == 0)).sum()
            fn = ((predictions == 0) & (labels == 1)).sum()
            
            sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
            
            return sensitivity, specificity
        except:
            return 0.5, 0.5
