"""
Utility functions for ML outcome prediction

This module provides data preprocessing, feature selection, model validation,
and outcome metrics calculation utilities for cancer outcome prediction.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from sklearn.feature_selection import SelectKBest, f_classif, f_regression, mutual_info_classif, mutual_info_regression
from sklearn.feature_selection import RFE, SelectFromModel
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, LabelEncoder
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.model_selection import cross_val_score, StratifiedKFold, KFold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error, confusion_matrix
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import logging
import warnings
from scipy import stats
from scipy.stats import chi2_contingency
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class DataPreprocessor:
    """
    Comprehensive data preprocessing utilities for cancer outcome prediction.
    """
    
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.scalers = {}
        self.imputers = {}
        self.encoders = {}
        self.preprocessing_config = {}
        
    def preprocess_data(self, X: pd.DataFrame, y: pd.Series = None, 
                       config: Dict[str, Any] = None) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Comprehensive data preprocessing pipeline.
        
        Args:
            X: Feature matrix
            y: Target variable (optional)
            config: Preprocessing configuration
            
        Returns:
            Preprocessed feature matrix and target variable
        """
        if config is None:
            config = self._get_default_config()
        
        self.preprocessing_config = config
        
        # Store original data
        X_processed = X.copy()
        y_processed = y.copy() if y is not None else None
        
        # Handle missing values
        if config.get("handle_missing", True):
            X_processed = self._handle_missing_values(X_processed, config.get("missing_strategy", "mean"))
        
        # Handle outliers
        if config.get("handle_outliers", True):
            X_processed = self._handle_outliers(X_processed, config.get("outlier_method", "iqr"))
        
        # Encode categorical variables
        if config.get("encode_categorical", True):
            X_processed = self._encode_categorical_variables(X_processed)
        
        # Scale features
        if config.get("scale_features", True):
            X_processed = self._scale_features(X_processed, config.get("scaling_method", "standard"))
        
        # Feature engineering
        if config.get("feature_engineering", True):
            X_processed = self._engineer_features(X_processed)
        
        # Handle target variable
        if y_processed is not None and config.get("encode_target", True):
            y_processed = self._encode_target_variable(y_processed)
        
        return X_processed, y_processed
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default preprocessing configuration."""
        return {
            "handle_missing": True,
            "missing_strategy": "mean",  # mean, median, mode, knn
            "handle_outliers": True,
            "outlier_method": "iqr",  # iqr, zscore, isolation_forest
            "encode_categorical": True,
            "scale_features": True,
            "scaling_method": "standard",  # standard, minmax, robust
            "feature_engineering": True,
            "encode_target": True
        }
    
    def _handle_missing_values(self, X: pd.DataFrame, strategy: str) -> pd.DataFrame:
        """Handle missing values in the dataset."""
        if X.isnull().sum().sum() == 0:
            return X
        
        logger.info(f"Handling missing values using {strategy} strategy")
        
        if strategy == "mean":
            imputer = SimpleImputer(strategy='mean')
        elif strategy == "median":
            imputer = SimpleImputer(strategy='median')
        elif strategy == "mode":
            imputer = SimpleImputer(strategy='most_frequent')
        elif strategy == "knn":
            imputer = KNNImputer(n_neighbors=5)
        else:
            raise ValueError(f"Unsupported missing value strategy: {strategy}")
        
        # Fit and transform
        X_imputed = pd.DataFrame(
            imputer.fit_transform(X),
            columns=X.columns,
            index=X.index
        )
        
        self.imputers['missing_values'] = imputer
        return X_imputed
    
    def _handle_outliers(self, X: pd.DataFrame, method: str) -> pd.DataFrame:
        """Handle outliers in the dataset."""
        X_processed = X.copy()
        
        if method == "iqr":
            for column in X_processed.select_dtypes(include=[np.number]).columns:
                Q1 = X_processed[column].quantile(0.25)
                Q3 = X_processed[column].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                # Cap outliers instead of removing them
                X_processed[column] = X_processed[column].clip(lower=lower_bound, upper=upper_bound)
        
        elif method == "zscore":
            for column in X_processed.select_dtypes(include=[np.number]).columns:
                z_scores = np.abs(stats.zscore(X_processed[column].dropna()))
                threshold = 3
                X_processed[column] = X_processed[column].where(z_scores < threshold)
        
        logger.info(f"Handled outliers using {method} method")
        return X_processed
    
    def _encode_categorical_variables(self, X: pd.DataFrame) -> pd.DataFrame:
        """Encode categorical variables."""
        X_encoded = X.copy()
        
        for column in X_encoded.select_dtypes(include=['object', 'category']).columns:
            if X_encoded[column].nunique() > 10:
                # High cardinality - use target encoding or drop
                logger.warning(f"High cardinality column {column} - consider feature engineering")
                continue
            
            # Label encoding for ordinal or low cardinality categorical
            encoder = LabelEncoder()
            X_encoded[column] = encoder.fit_transform(X_encoded[column].astype(str))
            self.encoders[column] = encoder
        
        return X_encoded
    
    def _scale_features(self, X: pd.DataFrame, method: str) -> pd.DataFrame:
        """Scale features using specified method."""
        numeric_columns = X.select_dtypes(include=[np.number]).columns
        
        if method == "standard":
            scaler = StandardScaler()
        elif method == "minmax":
            scaler = MinMaxScaler()
        elif method == "robust":
            scaler = RobustScaler()
        else:
            raise ValueError(f"Unsupported scaling method: {method}")
        
        X_scaled = X.copy()
        X_scaled[numeric_columns] = scaler.fit_transform(X[numeric_columns])
        
        self.scalers['feature_scaling'] = scaler
        return X_scaled
    
    def _engineer_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """Engineer new features from existing ones."""
        X_engineered = X.copy()
        
        # Add polynomial features for numeric columns
        numeric_columns = X_engineered.select_dtypes(include=[np.number]).columns
        
        for col in numeric_columns[:5]:  # Limit to first 5 to avoid explosion
            if X_engineered[col].std() > 0:  # Avoid division by zero
                X_engineered[f"{col}_squared"] = X_engineered[col] ** 2
                X_engineered[f"{col}_log"] = np.log1p(np.abs(X_engineered[col]))
        
        # Add interaction features for top correlated pairs
        if len(numeric_columns) > 1:
            corr_matrix = X_engineered[numeric_columns].corr().abs()
            high_corr_pairs = []
            
            for i in range(len(corr_matrix.columns)):
                for j in range(i+1, len(corr_matrix.columns)):
                    if corr_matrix.iloc[i, j] > 0.7:  # High correlation threshold
                        high_corr_pairs.append((corr_matrix.columns[i], corr_matrix.columns[j]))
            
            # Add interaction features for top 3 pairs
            for col1, col2 in high_corr_pairs[:3]:
                X_engineered[f"{col1}_{col2}_interaction"] = X_engineered[col1] * X_engineered[col2]
        
        logger.info(f"Engineered {len(X_engineered.columns) - len(X.columns)} new features")
        return X_engineered
    
    def _encode_target_variable(self, y: pd.Series) -> pd.Series:
        """Encode target variable if categorical."""
        if y.dtype == 'object' or y.dtype.name == 'category':
            encoder = LabelEncoder()
            y_encoded = pd.Series(encoder.fit_transform(y), index=y.index, name=y.name)
            self.encoders['target'] = encoder
            return y_encoded
        return y
    
    def inverse_transform_target(self, y_encoded: pd.Series) -> pd.Series:
        """Inverse transform encoded target variable."""
        if 'target' in self.encoders:
            return pd.Series(
                self.encoders['target'].inverse_transform(y_encoded),
                index=y_encoded.index,
                name=y_encoded.name
            )
        return y_encoded


class FeatureSelector:
    """
    Advanced feature selection utilities for cancer outcome prediction.
    """
    
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.selected_features = {}
        self.feature_scores = {}
        
    def select_features(self, X: pd.DataFrame, y: pd.Series, 
                       method: str = "mutual_info", 
                       k: int = None,
                       task_type: str = "classification") -> pd.DataFrame:
        """
        Select features using specified method.
        
        Args:
            X: Feature matrix
            y: Target variable
            method: Feature selection method
            k: Number of features to select
            task_type: Type of task (classification or regression)
            
        Returns:
            Feature matrix with selected features
        """
        if k is None:
            k = min(50, len(X.columns) // 2)  # Default to half the features or 50
        
        if method == "mutual_info":
            return self._mutual_information_selection(X, y, k, task_type)
        elif method == "f_score":
            return self._f_score_selection(X, y, k, task_type)
        elif method == "rfe":
            return self._rfe_selection(X, y, k, task_type)
        elif method == "random_forest":
            return self._random_forest_selection(X, y, k, task_type)
        elif method == "correlation":
            return self._correlation_selection(X, y, k)
        else:
            raise ValueError(f"Unsupported feature selection method: {method}")
    
    def _mutual_information_selection(self, X: pd.DataFrame, y: pd.Series, 
                                    k: int, task_type: str) -> pd.DataFrame:
        """Select features using mutual information."""
        if task_type == "classification":
            scores = mutual_info_classif(X, y, random_state=self.random_state)
        else:
            scores = mutual_info_regression(X, y, random_state=self.random_state)
        
        # Select top k features
        selector = SelectKBest(score_func=mutual_info_classif if task_type == "classification" else mutual_info_regression, k=k)
        X_selected = selector.fit_transform(X, y)
        
        # Store results
        selected_features = X.columns[selector.get_support()].tolist()
        self.selected_features['mutual_info'] = selected_features
        self.feature_scores['mutual_info'] = dict(zip(X.columns, scores))
        
        return pd.DataFrame(X_selected, columns=selected_features, index=X.index)
    
    def _f_score_selection(self, X: pd.DataFrame, y: pd.Series, 
                          k: int, task_type: str) -> pd.DataFrame:
        """Select features using F-score."""
        if task_type == "classification":
            scores = f_classif(X, y)[0]
        else:
            scores = f_regression(X, y)[0]
        
        # Select top k features
        selector = SelectKBest(score_func=f_classif if task_type == "classification" else f_regression, k=k)
        X_selected = selector.fit_transform(X, y)
        
        # Store results
        selected_features = X.columns[selector.get_support()].tolist()
        self.selected_features['f_score'] = selected_features
        self.feature_scores['f_score'] = dict(zip(X.columns, scores))
        
        return pd.DataFrame(X_selected, columns=selected_features, index=X.index)
    
    def _rfe_selection(self, X: pd.DataFrame, y: pd.Series, 
                      k: int, task_type: str) -> pd.DataFrame:
        """Select features using Recursive Feature Elimination."""
        if task_type == "classification":
            estimator = RandomForestClassifier(n_estimators=50, random_state=self.random_state)
        else:
            estimator = RandomForestRegressor(n_estimators=50, random_state=self.random_state)
        
        selector = RFE(estimator, n_features_to_select=k)
        X_selected = selector.fit_transform(X, y)
        
        # Store results
        selected_features = X.columns[selector.get_support()].tolist()
        self.selected_features['rfe'] = selected_features
        
        return pd.DataFrame(X_selected, columns=selected_features, index=X.index)
    
    def _random_forest_selection(self, X: pd.DataFrame, y: pd.Series, 
                                k: int, task_type: str) -> pd.DataFrame:
        """Select features using Random Forest feature importance."""
        if task_type == "classification":
            rf = RandomForestClassifier(n_estimators=100, random_state=self.random_state)
        else:
            rf = RandomForestRegressor(n_estimators=100, random_state=self.random_state)
        
        rf.fit(X, y)
        
        # Get feature importance
        importance_scores = rf.feature_importances_
        
        # Select top k features
        feature_importance = list(zip(X.columns, importance_scores))
        feature_importance.sort(key=lambda x: x[1], reverse=True)
        selected_features = [feat[0] for feat in feature_importance[:k]]
        
        # Store results
        self.selected_features['random_forest'] = selected_features
        self.feature_scores['random_forest'] = dict(feature_importance)
        
        return X[selected_features]
    
    def _correlation_selection(self, X: pd.DataFrame, y: pd.Series, k: int) -> pd.DataFrame:
        """Select features based on correlation with target."""
        numeric_columns = X.select_dtypes(include=[np.number]).columns
        
        if y.dtype == 'object':
            # For categorical targets, use correlation with encoded version
            y_encoded = pd.get_dummies(y).iloc[:, 0]  # Take first dummy variable
        else:
            y_encoded = y
        
        correlations = []
        for col in numeric_columns:
            corr = abs(X[col].corr(y_encoded))
            if not np.isnan(corr):
                correlations.append((col, corr))
        
        # Sort by correlation and select top k
        correlations.sort(key=lambda x: x[1], reverse=True)
        selected_features = [feat[0] for feat in correlations[:k]]
        
        # Store results
        self.selected_features['correlation'] = selected_features
        self.feature_scores['correlation'] = dict(correlations)
        
        return X[selected_features]
    
    def get_feature_importance_plot(self, method: str = "random_forest", top_n: int = 20):
        """Generate feature importance plot."""
        if method not in self.feature_scores:
            raise ValueError(f"No feature scores available for method: {method}")
        
        scores = self.feature_scores[method]
        sorted_features = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
        features, importances = zip(*sorted_features)
        
        plt.figure(figsize=(10, 8))
        plt.barh(range(len(features)), importances)
        plt.yticks(range(len(features)), features)
        plt.xlabel('Importance Score')
        plt.title(f'Top {top_n} Features - {method.title()} Method')
        plt.gca().invert_yaxis()
        plt.tight_layout()
        
        return plt.gcf()


class ModelValidator:
    """
    Comprehensive model validation utilities.
    """
    
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.validation_results = {}
        
    def cross_validate_model(self, model, X: pd.DataFrame, y: pd.Series, 
                           cv_folds: int = 5, task_type: str = "classification") -> Dict[str, Any]:
        """
        Perform cross-validation on a model.
        
        Args:
            model: Trained model
            X: Feature matrix
            y: Target variable
            cv_folds: Number of cross-validation folds
            task_type: Type of task
            
        Returns:
            Cross-validation results
        """
        if task_type == "classification":
            cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=self.random_state)
            scoring = ['accuracy', 'precision_weighted', 'recall_weighted', 'f1_weighted']
        else:
            cv = KFold(n_splits=cv_folds, shuffle=True, random_state=self.random_state)
            scoring = ['neg_mean_squared_error', 'neg_mean_absolute_error', 'r2']
        
        try:
            cv_scores = {}
            for score in scoring:
                scores = cross_val_score(model, X, y, cv=cv, scoring=score, n_jobs=-1)
                cv_scores[score] = {
                    'mean': scores.mean(),
                    'std': scores.std(),
                    'scores': scores.tolist()
                }
            
            return {
                "status": "success",
                "cv_scores": cv_scores,
                "cv_folds": cv_folds,
                "task_type": task_type
            }
            
        except Exception as e:
            logger.error(f"Error in cross-validation: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def validate_model_performance(self, model, X_test: pd.DataFrame, y_test: pd.Series,
                                 task_type: str = "classification") -> Dict[str, Any]:
        """
        Validate model performance on test set.
        
        Args:
            model: Trained model
            X_test: Test feature matrix
            y_test: Test target variable
            task_type: Type of task
            
        Returns:
            Validation results
        """
        try:
            y_pred = model.predict(X_test)
            
            if task_type == "classification":
                metrics = {
                    "accuracy": accuracy_score(y_test, y_pred),
                    "precision": precision_score(y_test, y_pred, average='weighted', zero_division=0),
                    "recall": recall_score(y_test, y_pred, average='weighted', zero_division=0),
                    "f1_score": f1_score(y_test, y_pred, average='weighted', zero_division=0)
                }
                
                # Add confusion matrix
                cm = confusion_matrix(y_test, y_pred)
                metrics["confusion_matrix"] = cm.tolist()
                
                # Add ROC AUC if binary classification
                if len(np.unique(y_test)) == 2 and hasattr(model, 'predict_proba'):
                    try:
                        y_proba = model.predict_proba(X_test)[:, 1]
                        metrics["roc_auc"] = roc_auc_score(y_test, y_proba)
                    except:
                        pass
                        
            else:  # regression
                metrics = {
                    "mse": mean_squared_error(y_test, y_pred),
                    "rmse": np.sqrt(mean_squared_error(y_test, y_pred)),
                    "mae": mean_absolute_error(y_test, y_pred),
                    "r2": r2_score(y_test, y_pred)
                }
            
            return {
                "status": "success",
                "metrics": metrics,
                "task_type": task_type,
                "test_samples": len(y_test)
            }
            
        except Exception as e:
            logger.error(f"Error in model validation: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def learning_curve_analysis(self, model, X: pd.DataFrame, y: pd.Series,
                              task_type: str = "classification", 
                              train_sizes: List[float] = None) -> Dict[str, Any]:
        """
        Perform learning curve analysis.
        
        Args:
            model: Model to analyze
            X: Feature matrix
            y: Target variable
            task_type: Type of task
            train_sizes: Training set sizes to test
            
        Returns:
            Learning curve results
        """
        if train_sizes is None:
            train_sizes = np.linspace(0.1, 1.0, 10)
        
        try:
            from sklearn.model_selection import learning_curve
            
            if task_type == "classification":
                scoring = 'accuracy'
            else:
                scoring = 'neg_mean_squared_error'
            
            train_sizes_abs, train_scores, val_scores = learning_curve(
                model, X, y, train_sizes=train_sizes, cv=5, scoring=scoring, n_jobs=-1
            )
            
            return {
                "status": "success",
                "train_sizes": train_sizes_abs.tolist(),
                "train_scores_mean": train_scores.mean(axis=1).tolist(),
                "train_scores_std": train_scores.std(axis=1).tolist(),
                "val_scores_mean": val_scores.mean(axis=1).tolist(),
                "val_scores_std": val_scores.std(axis=1).tolist(),
                "scoring": scoring
            }
            
        except Exception as e:
            logger.error(f"Error in learning curve analysis: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }


class OutcomeMetrics:
    """
    Specialized metrics for cancer outcome prediction.
    """
    
    @staticmethod
    def calculate_survival_metrics(y_true: np.ndarray, y_pred: np.ndarray, 
                                 duration: np.ndarray, event: np.ndarray) -> Dict[str, float]:
        """
        Calculate survival-specific metrics.
        
        Args:
            y_true: True survival times
            y_pred: Predicted survival times
            duration: Duration of follow-up
            event: Event indicator
            
        Returns:
            Survival metrics
        """
        try:
            # Concordance index (C-index)
            from lifelines.utils import concordance_index
            c_index = concordance_index(duration, y_pred, event)
            
            # Integrated Brier Score (simplified)
            brier_score = np.mean((event - y_pred) ** 2)
            
            return {
                "concordance_index": c_index,
                "brier_score": brier_score,
                "mean_absolute_error": np.mean(np.abs(y_true - y_pred))
            }
            
        except ImportError:
            # Fallback metrics when lifelines is not available
            return {
                "mean_absolute_error": np.mean(np.abs(y_true - y_pred)),
                "mean_squared_error": np.mean((y_true - y_pred) ** 2),
                "r2_score": 1 - np.sum((y_true - y_pred) ** 2) / np.sum((y_true - np.mean(y_true)) ** 2)
            }
    
    @staticmethod
    def calculate_drug_response_metrics(y_true: np.ndarray, y_pred: np.ndarray,
                                      drug_names: List[str] = None) -> Dict[str, Any]:
        """
        Calculate drug response-specific metrics.
        
        Args:
            y_true: True drug responses
            y_pred: Predicted drug responses
            drug_names: List of drug names
            
        Returns:
            Drug response metrics
        """
        metrics = {
            "overall_accuracy": accuracy_score(y_true, y_pred),
            "overall_precision": precision_score(y_true, y_pred, average='weighted', zero_division=0),
            "overall_recall": recall_score(y_true, y_pred, average='weighted', zero_division=0),
            "overall_f1": f1_score(y_true, y_pred, average='weighted', zero_division=0)
        }
        
        # Per-drug metrics if drug names provided
        if drug_names is not None:
            drug_metrics = {}
            unique_drugs = np.unique(drug_names)
            
            for drug in unique_drugs:
                drug_mask = np.array(drug_names) == drug
                if np.sum(drug_mask) > 1:  # Need at least 2 samples
                    drug_y_true = y_true[drug_mask]
                    drug_y_pred = y_pred[drug_mask]
                    
                    drug_metrics[drug] = {
                        "accuracy": accuracy_score(drug_y_true, drug_y_pred),
                        "precision": precision_score(drug_y_true, drug_y_pred, average='weighted', zero_division=0),
                        "recall": recall_score(drug_y_true, drug_y_pred, average='weighted', zero_division=0),
                        "f1": f1_score(drug_y_true, drug_y_pred, average='weighted', zero_division=0),
                        "sample_count": np.sum(drug_mask)
                    }
            
            metrics["per_drug_metrics"] = drug_metrics
        
        return metrics
    
    @staticmethod
    def calculate_treatment_outcome_metrics(y_true: np.ndarray, y_pred: np.ndarray,
                                          outcome_classes: List[str] = None) -> Dict[str, Any]:
        """
        Calculate treatment outcome-specific metrics.
        
        Args:
            y_true: True treatment outcomes
            y_pred: Predicted treatment outcomes
            outcome_classes: List of outcome class names
            
        Returns:
            Treatment outcome metrics
        """
        metrics = {
            "accuracy": accuracy_score(y_true, y_pred),
            "precision_macro": precision_score(y_true, y_pred, average='macro', zero_division=0),
            "precision_weighted": precision_score(y_true, y_pred, average='weighted', zero_division=0),
            "recall_macro": recall_score(y_true, y_pred, average='macro', zero_division=0),
            "recall_weighted": recall_score(y_true, y_pred, average='weighted', zero_division=0),
            "f1_macro": f1_score(y_true, y_pred, average='macro', zero_division=0),
            "f1_weighted": f1_score(y_true, y_pred, average='weighted', zero_division=0)
        }
        
        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        metrics["confusion_matrix"] = cm.tolist()
        
        # Per-class metrics
        if outcome_classes is not None:
            class_metrics = {}
            for i, class_name in enumerate(outcome_classes):
                if i < len(cm):
                    class_metrics[class_name] = {
                        "precision": precision_score(y_true, y_pred, labels=[i], average='macro', zero_division=0),
                        "recall": recall_score(y_true, y_pred, labels=[i], average='macro', zero_division=0),
                        "f1": f1_score(y_true, y_pred, labels=[i], average='macro', zero_division=0),
                        "support": np.sum(y_true == i)
                    }
            
            metrics["per_class_metrics"] = class_metrics
        
        return metrics


class DataValidator:
    """
    Data validation utilities for cancer outcome prediction.
    """
    
    @staticmethod
    def validate_dataset(X: pd.DataFrame, y: pd.Series = None) -> Dict[str, Any]:
        """
        Validate dataset for ML outcome prediction.
        
        Args:
            X: Feature matrix
            y: Target variable (optional)
            
        Returns:
            Validation results
        """
        validation_results = {
            "status": "success",
            "warnings": [],
            "errors": [],
            "dataset_info": {}
        }
        
        # Basic dataset info
        validation_results["dataset_info"] = {
            "n_samples": len(X),
            "n_features": len(X.columns),
            "feature_types": X.dtypes.value_counts().to_dict(),
            "memory_usage": X.memory_usage(deep=True).sum()
        }
        
        # Check for missing values
        missing_values = X.isnull().sum()
        if missing_values.sum() > 0:
            validation_results["warnings"].append(f"Found {missing_values.sum()} missing values")
            validation_results["dataset_info"]["missing_values"] = missing_values[missing_values > 0].to_dict()
        
        # Check for constant features
        constant_features = X.columns[X.nunique() <= 1].tolist()
        if constant_features:
            validation_results["warnings"].append(f"Found {len(constant_features)} constant features: {constant_features}")
        
        # Check for high cardinality categorical features
        categorical_features = X.select_dtypes(include=['object', 'category']).columns
        high_cardinality = []
        for col in categorical_features:
            if X[col].nunique() > len(X) * 0.5:  # More than 50% unique values
                high_cardinality.append(col)
        
        if high_cardinality:
            validation_results["warnings"].append(f"Found {len(high_cardinality)} high cardinality features: {high_cardinality}")
        
        # Check for duplicate rows
        duplicate_rows = X.duplicated().sum()
        if duplicate_rows > 0:
            validation_results["warnings"].append(f"Found {duplicate_rows} duplicate rows")
        
        # Validate target variable if provided
        if y is not None:
            validation_results["dataset_info"]["target_info"] = {
                "n_classes": y.nunique() if y.dtype == 'object' else None,
                "class_distribution": y.value_counts().to_dict() if y.dtype == 'object' else None,
                "missing_values": y.isnull().sum(),
                "data_type": str(y.dtype)
            }
            
            # Check for class imbalance
            if y.dtype == 'object':
                class_counts = y.value_counts()
                max_class_ratio = class_counts.max() / class_counts.min()
                if max_class_ratio > 10:  # Severe imbalance
                    validation_results["warnings"].append(f"Severe class imbalance detected (ratio: {max_class_ratio:.2f})")
        
        return validation_results
    
    @staticmethod
    def check_feature_quality(X: pd.DataFrame) -> Dict[str, Any]:
        """
        Check feature quality and provide recommendations.
        
        Args:
            X: Feature matrix
            
        Returns:
            Feature quality report
        """
        quality_report = {
            "feature_quality": {},
            "recommendations": []
        }
        
        for column in X.columns:
            feature_info = {
                "data_type": str(X[column].dtype),
                "n_unique": X[column].nunique(),
                "missing_pct": (X[column].isnull().sum() / len(X)) * 100,
                "zero_pct": (X[column] == 0).sum() / len(X) * 100 if X[column].dtype in ['int64', 'float64'] else 0
            }
            
            # Add quality score
            quality_score = 100
            if feature_info["missing_pct"] > 20:
                quality_score -= 30
            if feature_info["n_unique"] <= 1:
                quality_score -= 50
            if feature_info["zero_pct"] > 80:
                quality_score -= 20
            
            feature_info["quality_score"] = max(0, quality_score)
            quality_report["feature_quality"][column] = feature_info
        
        # Generate recommendations
        low_quality_features = [col for col, info in quality_report["feature_quality"].items() 
                              if info["quality_score"] < 50]
        
        if low_quality_features:
            quality_report["recommendations"].append(
                f"Consider removing or engineering {len(low_quality_features)} low-quality features"
            )
        
        high_missing_features = [col for col, info in quality_report["feature_quality"].items() 
                               if info["missing_pct"] > 50]
        
        if high_missing_features:
            quality_report["recommendations"].append(
                f"Consider imputation strategies for {len(high_missing_features)} features with >50% missing values"
            )
        
        return quality_report


class FeatureEngineering:
    """
    Advanced feature engineering utilities for cancer outcome prediction.
    """
    
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        
    def create_genomic_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Create genomic-specific features.
        
        Args:
            X: Feature matrix with genomic data
            
        Returns:
            Feature matrix with engineered genomic features
        """
        X_engineered = X.copy()
        
        # Look for common genomic feature patterns
        genomic_patterns = {
            'mutation': ['mut', 'variant', 'snp', 'indel'],
            'expression': ['expr', 'rna', 'mrna', 'transcript'],
            'copy_number': ['cnv', 'copy', 'amplification', 'deletion'],
            'methylation': ['meth', 'methyl', 'dna_meth']
        }
        
        for pattern_type, patterns in genomic_patterns.items():
            matching_cols = [col for col in X.columns 
                           if any(pattern in col.lower() for pattern in patterns)]
            
            if len(matching_cols) > 1:
                # Create summary statistics for each pattern type
                X_engineered[f'{pattern_type}_mean'] = X[matching_cols].mean(axis=1)
                X_engineered[f'{pattern_type}_std'] = X[matching_cols].std(axis=1)
                X_engineered[f'{pattern_type}_count'] = (X[matching_cols] != 0).sum(axis=1)
        
        return X_engineered
    
    def create_clinical_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Create clinical-specific features.
        
        Args:
            X: Feature matrix with clinical data
            
        Returns:
            Feature matrix with engineered clinical features
        """
        X_engineered = X.copy()
        
        # Look for age-related features
        age_cols = [col for col in X.columns if 'age' in col.lower()]
        if age_cols:
            age_col = age_cols[0]
            X_engineered['age_group'] = pd.cut(X[age_col], bins=[0, 50, 65, 100], labels=['young', 'middle', 'elderly'])
            X_engineered['age_squared'] = X[age_col] ** 2
        
        # Look for stage-related features
        stage_cols = [col for col in X.columns if 'stage' in col.lower()]
        if stage_cols:
            stage_col = stage_cols[0]
            if X[stage_col].dtype == 'object':
                # Create ordinal encoding for stages
                stage_mapping = {'I': 1, 'II': 2, 'III': 3, 'IV': 4}
                X_engineered[f'{stage_col}_numeric'] = X[stage_col].map(stage_mapping)
        
        # Create interaction features between clinical variables
        numeric_cols = X_engineered.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) >= 2:
            # Create top 3 most correlated interactions
            corr_matrix = X_engineered[numeric_cols].corr().abs()
            high_corr_pairs = []
            
            for i in range(len(corr_matrix.columns)):
                for j in range(i+1, len(corr_matrix.columns)):
                    if corr_matrix.iloc[i, j] > 0.5:
                        high_corr_pairs.append((corr_matrix.columns[i], corr_matrix.columns[j]))
            
            for col1, col2 in high_corr_pairs[:3]:
                X_engineered[f'{col1}_{col2}_interaction'] = X_engineered[col1] * X_engineered[col2]
        
        return X_engineered
    
    def create_temporal_features(self, X: pd.DataFrame, time_columns: List[str] = None) -> pd.DataFrame:
        """
        Create temporal features from time-based columns.
        
        Args:
            X: Feature matrix
            time_columns: List of time-based column names
            
        Returns:
            Feature matrix with temporal features
        """
        X_engineered = X.copy()
        
        if time_columns is None:
            # Auto-detect time columns
            time_columns = [col for col in X.columns 
                          if any(keyword in col.lower() for keyword in ['date', 'time', 'day', 'month', 'year'])]
        
        for col in time_columns:
            if X[col].dtype == 'object':
                try:
                    # Try to convert to datetime
                    X[col] = pd.to_datetime(X[col], errors='coerce')
                except:
                    continue
            
            if pd.api.types.is_datetime64_any_dtype(X[col]):
                X_engineered[f'{col}_year'] = X[col].dt.year
                X_engineered[f'{col}_month'] = X[col].dt.month
                X_engineered[f'{col}_day'] = X[col].dt.day
                X_engineered[f'{col}_dayofweek'] = X[col].dt.dayofweek
                X_engineered[f'{col}_quarter'] = X[col].dt.quarter
        
        return X_engineered
    
    def create_aggregated_features(self, X: pd.DataFrame, group_columns: List[str] = None) -> pd.DataFrame:
        """
        Create aggregated features by grouping.
        
        Args:
            X: Feature matrix
            group_columns: Columns to group by
            
        Returns:
            Feature matrix with aggregated features
        """
        X_engineered = X.copy()
        
        if group_columns is None:
            # Auto-detect potential grouping columns
            categorical_cols = X.select_dtypes(include=['object', 'category']).columns
            group_columns = [col for col in categorical_cols if X[col].nunique() < 20]
        
        for group_col in group_columns:
            numeric_cols = X.select_dtypes(include=[np.number]).columns
            
            for num_col in numeric_cols:
                if num_col != group_col:
                    # Create group statistics
                    group_stats = X.groupby(group_col)[num_col].agg(['mean', 'std', 'min', 'max'])
                    
                    # Map back to original dataframe
                    X_engineered[f'{num_col}_group_mean'] = X[group_col].map(group_stats['mean'])
                    X_engineered[f'{num_col}_group_std'] = X[group_col].map(group_stats['std'])
                    X_engineered[f'{num_col}_group_min'] = X[group_col].map(group_stats['min'])
                    X_engineered[f'{num_col}_group_max'] = X[group_col].map(group_stats['max'])
        
        return X_engineered
