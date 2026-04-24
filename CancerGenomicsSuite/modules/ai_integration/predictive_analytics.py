"""
Advanced Predictive Analytics for Cancer Genomics

This module provides state-of-the-art predictive analytics capabilities including
ensemble methods, hyperparameter optimization, model interpretability, and
automated machine learning pipelines for cancer genomics analysis.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
from dataclasses import dataclass, asdict
import warnings
warnings.filterwarnings('ignore')

# Machine Learning
from sklearn.ensemble import (
    RandomForestClassifier, RandomForestRegressor,
    GradientBoostingClassifier, GradientBoostingRegressor,
    VotingClassifier, VotingRegressor, StackingClassifier, StackingRegressor
)
from sklearn.model_selection import (
    train_test_split, cross_val_score, GridSearchCV, 
    RandomizedSearchCV, StratifiedKFold, KFold
)
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
    mean_squared_error, mean_absolute_error, r2_score,
    classification_report, confusion_matrix
)
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.feature_selection import SelectKBest, SelectFromModel, RFE

# Advanced ML libraries
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier, CatBoostRegressor

# Hyperparameter optimization
import optuna
from optuna.samplers import TPESampler
from optuna.pruners import MedianPruner

# Model interpretability
import shap
import lime
import lime.lime_tabular
from sklearn.inspection import permutation_importance

# Deep Learning
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import pytorch_lightning as pl
from pytorch_lightning.callbacks import EarlyStopping, ModelCheckpoint

# Statistical analysis
import scipy.stats as stats
from scipy.optimize import minimize

# Model persistence
import joblib
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for predictive models."""
    task_type: str = "classification"  # classification, regression, survival
    target_column: str = "target"
    test_size: float = 0.2
    random_state: int = 42
    cv_folds: int = 5
    scoring_metric: str = "auto"  # auto, accuracy, f1, roc_auc, mse, r2
    feature_selection: bool = True
    n_features: int = 100
    hyperparameter_optimization: bool = True
    n_trials: int = 100
    model_interpretability: bool = True


@dataclass
class ModelResult:
    """Result structure for model training."""
    model_name: str
    model: Any
    performance_metrics: Dict[str, float]
    feature_importance: Dict[str, float]
    predictions: np.ndarray
    probabilities: Optional[np.ndarray] = None
    cross_val_scores: Optional[List[float]] = None
    hyperparameters: Optional[Dict[str, Any]] = None
    training_time: float = 0.0


class AdvancedMLPipeline:
    """Advanced machine learning pipeline with automated feature engineering and model selection."""
    
    def __init__(self, config: ModelConfig = None):
        self.config = config or ModelConfig()
        self.models = {}
        self.results = {}
        self.feature_selector = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.is_fitted = False
        
    def fit(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, ModelResult]:
        """Fit multiple models and return results."""
        logger.info(f"Training advanced ML pipeline on {X.shape[0]} samples with {X.shape[1]} features")
        
        # Preprocess data
        X_processed, y_processed = self._preprocess_data(X, y)
        
        # Feature selection
        if self.config.feature_selection:
            X_processed = self._select_features(X_processed, y_processed)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_processed, y_processed, test_size=self.config.test_size, 
            random_state=self.config.random_state, stratify=y_processed if self.config.task_type == "classification" else None
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train models
        models_to_train = self._get_models()
        
        for model_name, model in models_to_train.items():
            logger.info(f"Training {model_name}...")
            
            start_time = pd.Timestamp.now()
            
            # Hyperparameter optimization
            if self.config.hyperparameter_optimization:
                model = self._optimize_hyperparameters(model, X_train_scaled, y_train)
            
            # Train model
            model.fit(X_train_scaled, y_train)
            
            # Make predictions
            y_pred = model.predict(X_test_scaled)
            y_prob = None
            if hasattr(model, 'predict_proba') and self.config.task_type == "classification":
                y_prob = model.predict_proba(X_test_scaled)
            
            # Calculate performance metrics
            metrics = self._calculate_metrics(y_test, y_pred, y_prob)
            
            # Cross-validation
            cv_scores = self._cross_validate(model, X_train_scaled, y_train)
            
            # Feature importance
            feature_importance = self._calculate_feature_importance(model, X_train_scaled, y_train)
            
            training_time = (pd.Timestamp.now() - start_time).total_seconds()
            
            # Store results
            result = ModelResult(
                model_name=model_name,
                model=model,
                performance_metrics=metrics,
                feature_importance=feature_importance,
                predictions=y_pred,
                probabilities=y_prob,
                cross_val_scores=cv_scores,
                hyperparameters=model.get_params() if hasattr(model, 'get_params') else None,
                training_time=training_time
            )
            
            self.results[model_name] = result
            self.models[model_name] = model
        
        self.is_fitted = True
        return self.results
    
    def _preprocess_data(self, X: pd.DataFrame, y: pd.Series) -> Tuple[np.ndarray, np.ndarray]:
        """Preprocess input data."""
        # Handle missing values
        X_processed = X.fillna(X.median())
        
        # Encode categorical variables
        categorical_columns = X.select_dtypes(include=['object']).columns
        for col in categorical_columns:
            X_processed[col] = LabelEncoder().fit_transform(X_processed[col].astype(str))
        
        # Encode target variable for classification
        if self.config.task_type == "classification":
            y_processed = self.label_encoder.fit_transform(y)
        else:
            y_processed = y.values
        
        return X_processed.values, y_processed
    
    def _select_features(self, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Select most important features."""
        if X.shape[1] <= self.config.n_features:
            return X
        
        # Use random forest for feature selection
        selector = SelectFromModel(
            RandomForestClassifier(n_estimators=100, random_state=self.config.random_state),
            max_features=self.config.n_features
        )
        
        X_selected = selector.fit_transform(X, y)
        self.feature_selector = selector
        
        logger.info(f"Selected {X_selected.shape[1]} features from {X.shape[1]} original features")
        return X_selected
    
    def _get_models(self) -> Dict[str, Any]:
        """Get models to train based on task type."""
        if self.config.task_type == "classification":
            return {
                'random_forest': RandomForestClassifier(random_state=self.config.random_state),
                'gradient_boosting': GradientBoostingClassifier(random_state=self.config.random_state),
                'xgboost': xgb.XGBClassifier(random_state=self.config.random_state, eval_metric='logloss'),
                'lightgbm': lgb.LGBMClassifier(random_state=self.config.random_state, verbose=-1),
                'catboost': CatBoostClassifier(random_state=self.config.random_state, verbose=False)
            }
        else:  # regression
            return {
                'random_forest': RandomForestRegressor(random_state=self.config.random_state),
                'gradient_boosting': GradientBoostingRegressor(random_state=self.config.random_state),
                'xgboost': xgb.XGBRegressor(random_state=self.config.random_state),
                'lightgbm': lgb.LGBMRegressor(random_state=self.config.random_state, verbose=-1),
                'catboost': CatBoostRegressor(random_state=self.config.random_state, verbose=False)
            }
    
    def _optimize_hyperparameters(self, model: Any, X: np.ndarray, y: np.ndarray) -> Any:
        """Optimize hyperparameters using Optuna."""
        def objective(trial):
            # Define hyperparameter space based on model type
            if isinstance(model, RandomForestClassifier):
                params = {
                    'n_estimators': trial.suggest_int('n_estimators', 50, 500),
                    'max_depth': trial.suggest_int('max_depth', 3, 20),
                    'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
                    'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 10)
                }
            elif isinstance(model, xgb.XGBClassifier):
                params = {
                    'n_estimators': trial.suggest_int('n_estimators', 50, 500),
                    'max_depth': trial.suggest_int('max_depth', 3, 10),
                    'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
                    'subsample': trial.suggest_float('subsample', 0.6, 1.0)
                }
            else:
                # Default parameters for other models
                return model
            
            # Create model with suggested parameters
            model_copy = model.__class__(**params, random_state=self.config.random_state)
            
            # Cross-validation score
            scores = cross_val_score(model_copy, X, y, cv=3, scoring='accuracy' if self.config.task_type == "classification" else 'r2')
            return scores.mean()
        
        study = optuna.create_study(direction='maximize', sampler=TPESampler(), pruner=MedianPruner())
        study.optimize(objective, n_trials=self.config.n_trials)
        
        # Return model with best parameters
        best_params = study.best_params
        return model.__class__(**best_params, random_state=self.config.random_state)
    
    def _calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, y_prob: Optional[np.ndarray] = None) -> Dict[str, float]:
        """Calculate performance metrics."""
        metrics = {}
        
        if self.config.task_type == "classification":
            metrics['accuracy'] = accuracy_score(y_true, y_pred)
            metrics['precision'] = precision_score(y_true, y_pred, average='weighted')
            metrics['recall'] = recall_score(y_true, y_pred, average='weighted')
            metrics['f1_score'] = f1_score(y_true, y_pred, average='weighted')
            
            if y_prob is not None:
                metrics['roc_auc'] = roc_auc_score(y_true, y_prob, multi_class='ovr', average='weighted')
        else:  # regression
            metrics['mse'] = mean_squared_error(y_true, y_pred)
            metrics['rmse'] = np.sqrt(metrics['mse'])
            metrics['mae'] = mean_absolute_error(y_true, y_pred)
            metrics['r2'] = r2_score(y_true, y_pred)
        
        return metrics
    
    def _cross_validate(self, model: Any, X: np.ndarray, y: np.ndarray) -> List[float]:
        """Perform cross-validation."""
        cv = StratifiedKFold(n_splits=self.config.cv_folds, shuffle=True, random_state=self.config.random_state) if self.config.task_type == "classification" else KFold(n_splits=self.config.cv_folds, shuffle=True, random_state=self.config.random_state)
        
        scoring = 'accuracy' if self.config.task_type == "classification" else 'r2'
        scores = cross_val_score(model, X, y, cv=cv, scoring=scoring)
        
        return scores.tolist()
    
    def _calculate_feature_importance(self, model: Any, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """Calculate feature importance."""
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
        else:
            # Use permutation importance as fallback
            perm_importance = permutation_importance(model, X, y, random_state=self.config.random_state)
            importances = perm_importance.importances_mean
        
        # Create feature names
        feature_names = [f"feature_{i}" for i in range(len(importances))]
        
        return dict(zip(feature_names, importances))
    
    def predict(self, X: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Make predictions using all trained models."""
        if not self.is_fitted:
            raise ValueError("Pipeline must be fitted before making predictions")
        
        # Preprocess data
        X_processed = X.fillna(X.median())
        categorical_columns = X.select_dtypes(include=['object']).columns
        for col in categorical_columns:
            X_processed[col] = LabelEncoder().fit_transform(X_processed[col].astype(str))
        
        X_processed = X_processed.values
        
        # Apply feature selection
        if self.feature_selector is not None:
            X_processed = self.feature_selector.transform(X_processed)
        
        # Scale features
        X_scaled = self.scaler.transform(X_processed)
        
        # Make predictions
        predictions = {}
        for model_name, model in self.models.items():
            pred = model.predict(X_scaled)
            if self.config.task_type == "classification":
                pred = self.label_encoder.inverse_transform(pred)
            predictions[model_name] = pred
        
        return predictions
    
    def get_best_model(self) -> Tuple[str, Any]:
        """Get the best performing model."""
        if not self.results:
            raise ValueError("No models have been trained yet")
        
        # Determine best model based on primary metric
        if self.config.task_type == "classification":
            primary_metric = 'f1_score'
        else:
            primary_metric = 'r2'
        
        best_model_name = max(self.results.keys(), 
                            key=lambda x: self.results[x].performance_metrics.get(primary_metric, 0))
        
        return best_model_name, self.results[best_model_name]


class EnsemblePredictor:
    """Advanced ensemble methods for improved predictions."""
    
    def __init__(self, config: ModelConfig = None):
        self.config = config or ModelConfig()
        self.ensemble_model = None
        self.base_models = {}
        self.is_fitted = False
        
    def create_ensemble(self, X: pd.DataFrame, y: pd.Series, 
                       ensemble_type: str = "voting") -> Dict[str, Any]:
        """Create ensemble model."""
        logger.info(f"Creating {ensemble_type} ensemble")
        
        # Preprocess data
        X_processed, y_processed = self._preprocess_data(X, y)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_processed, y_processed, test_size=self.config.test_size,
            random_state=self.config.random_state,
            stratify=y_processed if self.config.task_type == "classification" else None
        )
        
        # Create base models
        base_models = self._create_base_models()
        
        # Create ensemble
        if ensemble_type == "voting":
            self.ensemble_model = self._create_voting_ensemble(base_models)
        elif ensemble_type == "stacking":
            self.ensemble_model = self._create_stacking_ensemble(base_models)
        elif ensemble_type == "blending":
            self.ensemble_model = self._create_blending_ensemble(base_models, X_train, y_train)
        
        # Train ensemble
        self.ensemble_model.fit(X_train, y_train)
        
        # Evaluate ensemble
        y_pred = self.ensemble_model.predict(X_test)
        y_prob = None
        if hasattr(self.ensemble_model, 'predict_proba') and self.config.task_type == "classification":
            y_prob = self.ensemble_model.predict_proba(X_test)
        
        metrics = self._calculate_metrics(y_test, y_pred, y_prob)
        
        self.is_fitted = True
        
        return {
            'ensemble_type': ensemble_type,
            'performance_metrics': metrics,
            'base_models': list(base_models.keys()),
            'ensemble_model': self.ensemble_model
        }
    
    def _preprocess_data(self, X: pd.DataFrame, y: pd.Series) -> Tuple[np.ndarray, np.ndarray]:
        """Preprocess data."""
        X_processed = X.fillna(X.median())
        categorical_columns = X.select_dtypes(include=['object']).columns
        for col in categorical_columns:
            X_processed[col] = LabelEncoder().fit_transform(X_processed[col].astype(str))
        
        if self.config.task_type == "classification":
            y_processed = LabelEncoder().fit_transform(y)
        else:
            y_processed = y.values
        
        return X_processed.values, y_processed
    
    def _create_base_models(self) -> Dict[str, Any]:
        """Create base models for ensemble."""
        if self.config.task_type == "classification":
            return {
                'rf': RandomForestClassifier(n_estimators=100, random_state=self.config.random_state),
                'gb': GradientBoostingClassifier(random_state=self.config.random_state),
                'xgb': xgb.XGBClassifier(random_state=self.config.random_state, eval_metric='logloss'),
                'lgb': lgb.LGBMClassifier(random_state=self.config.random_state, verbose=-1)
            }
        else:
            return {
                'rf': RandomForestRegressor(n_estimators=100, random_state=self.config.random_state),
                'gb': GradientBoostingRegressor(random_state=self.config.random_state),
                'xgb': xgb.XGBRegressor(random_state=self.config.random_state),
                'lgb': lgb.LGBMRegressor(random_state=self.config.random_state, verbose=-1)
            }
    
    def _create_voting_ensemble(self, base_models: Dict[str, Any]) -> Any:
        """Create voting ensemble."""
        if self.config.task_type == "classification":
            return VotingClassifier(
                estimators=list(base_models.items()),
                voting='soft'  # Use predicted probabilities
            )
        else:
            return VotingRegressor(
                estimators=list(base_models.items())
            )
    
    def _create_stacking_ensemble(self, base_models: Dict[str, Any]) -> Any:
        """Create stacking ensemble."""
        if self.config.task_type == "classification":
            meta_model = LogisticRegression(random_state=self.config.random_state)
            return StackingClassifier(
                estimators=list(base_models.items()),
                final_estimator=meta_model,
                cv=3
            )
        else:
            meta_model = LinearRegression()
            return StackingRegressor(
                estimators=list(base_models.items()),
                final_estimator=meta_model,
                cv=3
            )
    
    def _create_blending_ensemble(self, base_models: Dict[str, Any], 
                                X_train: np.ndarray, y_train: np.ndarray) -> Any:
        """Create blending ensemble."""
        # Train base models and get out-of-fold predictions
        oof_predictions = np.zeros((len(X_train), len(base_models)))
        
        kf = StratifiedKFold(n_splits=5, shuffle=True, random_state=self.config.random_state) if self.config.task_type == "classification" else KFold(n_splits=5, shuffle=True, random_state=self.config.random_state)
        
        for i, (model_name, model) in enumerate(base_models.items()):
            fold_predictions = np.zeros(len(X_train))
            
            for train_idx, val_idx in kf.split(X_train, y_train):
                X_fold_train, X_fold_val = X_train[train_idx], X_train[val_idx]
                y_fold_train = y_train[train_idx]
                
                model.fit(X_fold_train, y_fold_train)
                
                if self.config.task_type == "classification" and hasattr(model, 'predict_proba'):
                    fold_predictions[val_idx] = model.predict_proba(X_fold_val)[:, 1]
                else:
                    fold_predictions[val_idx] = model.predict(X_fold_val)
            
            oof_predictions[:, i] = fold_predictions
        
        # Train meta-model on out-of-fold predictions
        if self.config.task_type == "classification":
            meta_model = LogisticRegression(random_state=self.config.random_state)
        else:
            meta_model = LinearRegression()
        
        meta_model.fit(oof_predictions, y_train)
        
        # Store base models and meta-model
        self.base_models = base_models
        self.meta_model = meta_model
        
        return self
    
    def _calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, y_prob: Optional[np.ndarray] = None) -> Dict[str, float]:
        """Calculate performance metrics."""
        metrics = {}
        
        if self.config.task_type == "classification":
            metrics['accuracy'] = accuracy_score(y_true, y_pred)
            metrics['precision'] = precision_score(y_true, y_pred, average='weighted')
            metrics['recall'] = recall_score(y_true, y_pred, average='weighted')
            metrics['f1_score'] = f1_score(y_true, y_pred, average='weighted')
            
            if y_prob is not None:
                metrics['roc_auc'] = roc_auc_score(y_true, y_prob, multi_class='ovr', average='weighted')
        else:
            metrics['mse'] = mean_squared_error(y_true, y_pred)
            metrics['rmse'] = np.sqrt(metrics['mse'])
            metrics['mae'] = mean_absolute_error(y_true, y_pred)
            metrics['r2'] = r2_score(y_true, y_pred)
        
        return metrics
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions using ensemble."""
        if not self.is_fitted:
            raise ValueError("Ensemble must be fitted before making predictions")
        
        # Preprocess data
        X_processed = X.fillna(X.median())
        categorical_columns = X.select_dtypes(include=['object']).columns
        for col in categorical_columns:
            X_processed[col] = LabelEncoder().fit_transform(X_processed[col].astype(str))
        
        X_processed = X_processed.values
        
        # Make predictions
        if hasattr(self, 'meta_model'):  # Blending ensemble
            base_predictions = np.zeros((len(X_processed), len(self.base_models)))
            
            for i, (model_name, model) in enumerate(self.base_models.items()):
                if self.config.task_type == "classification" and hasattr(model, 'predict_proba'):
                    base_predictions[:, i] = model.predict_proba(X_processed)[:, 1]
                else:
                    base_predictions[:, i] = model.predict(X_processed)
            
            return self.meta_model.predict(base_predictions)
        else:  # Voting or stacking ensemble
            return self.ensemble_model.predict(X_processed)


class HyperparameterOptimizer:
    """Advanced hyperparameter optimization using Optuna."""
    
    def __init__(self, config: ModelConfig = None):
        self.config = config or ModelConfig()
        self.studies = {}
        
    def optimize_model(self, model: Any, X: pd.DataFrame, y: pd.Series, 
                      model_name: str = "model") -> Dict[str, Any]:
        """Optimize hyperparameters for a specific model."""
        logger.info(f"Optimizing hyperparameters for {model_name}")
        
        # Preprocess data
        X_processed, y_processed = self._preprocess_data(X, y)
        
        def objective(trial):
            # Get hyperparameter suggestions based on model type
            params = self._suggest_hyperparameters(trial, model)
            
            # Create model with suggested parameters
            model_copy = model.__class__(**params, random_state=self.config.random_state)
            
            # Cross-validation score
            cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=self.config.random_state) if self.config.task_type == "classification" else KFold(n_splits=3, shuffle=True, random_state=self.config.random_state)
            
            scoring = 'accuracy' if self.config.task_type == "classification" else 'r2'
            scores = cross_val_score(model_copy, X_processed, y_processed, cv=cv, scoring=scoring)
            
            return scores.mean()
        
        # Create study
        study = optuna.create_study(
            direction='maximize',
            sampler=TPESampler(),
            pruner=MedianPruner()
        )
        
        # Optimize
        study.optimize(objective, n_trials=self.config.n_trials)
        
        # Store study
        self.studies[model_name] = study
        
        return {
            'model_name': model_name,
            'best_params': study.best_params,
            'best_score': study.best_value,
            'n_trials': len(study.trials),
            'study': study
        }
    
    def _preprocess_data(self, X: pd.DataFrame, y: pd.Series) -> Tuple[np.ndarray, np.ndarray]:
        """Preprocess data."""
        X_processed = X.fillna(X.median())
        categorical_columns = X.select_dtypes(include=['object']).columns
        for col in categorical_columns:
            X_processed[col] = LabelEncoder().fit_transform(X_processed[col].astype(str))
        
        if self.config.task_type == "classification":
            y_processed = LabelEncoder().fit_transform(y)
        else:
            y_processed = y.values
        
        return X_processed.values, y_processed
    
    def _suggest_hyperparameters(self, trial, model: Any) -> Dict[str, Any]:
        """Suggest hyperparameters based on model type."""
        model_name = model.__class__.__name__
        
        if model_name == "RandomForestClassifier":
            return {
                'n_estimators': trial.suggest_int('n_estimators', 50, 500),
                'max_depth': trial.suggest_int('max_depth', 3, 20),
                'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
                'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 10),
                'max_features': trial.suggest_categorical('max_features', ['sqrt', 'log2', None])
            }
        elif model_name == "XGBClassifier":
            return {
                'n_estimators': trial.suggest_int('n_estimators', 50, 500),
                'max_depth': trial.suggest_int('max_depth', 3, 10),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0)
            }
        elif model_name == "LGBMClassifier":
            return {
                'n_estimators': trial.suggest_int('n_estimators', 50, 500),
                'max_depth': trial.suggest_int('max_depth', 3, 10),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0)
            }
        else:
            # Default parameters
            return {}


class ModelInterpretabilityEngine:
    """Model interpretability and explainability engine."""
    
    def __init__(self, config: ModelConfig = None):
        self.config = config or ModelConfig()
        self.explainers = {}
        
    def explain_model(self, model: Any, X: pd.DataFrame, y: pd.Series = None, 
                     explanation_type: str = "shap") -> Dict[str, Any]:
        """Generate model explanations."""
        logger.info(f"Generating {explanation_type} explanations")
        
        # Preprocess data
        X_processed = X.fillna(X.median())
        categorical_columns = X.select_dtypes(include=['object']).columns
        for col in categorical_columns:
            X_processed[col] = LabelEncoder().fit_transform(X_processed[col].astype(str))
        
        X_processed = X_processed.values
        
        explanations = {}
        
        if explanation_type == "shap":
            explanations = self._generate_shap_explanations(model, X_processed)
        elif explanation_type == "lime":
            explanations = self._generate_lime_explanations(model, X_processed, y)
        elif explanation_type == "permutation":
            explanations = self._generate_permutation_explanations(model, X_processed, y)
        elif explanation_type == "all":
            explanations['shap'] = self._generate_shap_explanations(model, X_processed)
            explanations['lime'] = self._generate_lime_explanations(model, X_processed, y)
            explanations['permutation'] = self._generate_permutation_explanations(model, X_processed, y)
        
        return explanations
    
    def _generate_shap_explanations(self, model: Any, X: np.ndarray) -> Dict[str, Any]:
        """Generate SHAP explanations."""
        try:
            # Create SHAP explainer
            if hasattr(model, 'predict_proba'):
                explainer = shap.TreeExplainer(model)
            else:
                explainer = shap.Explainer(model)
            
            # Calculate SHAP values
            shap_values = explainer.shap_values(X)
            
            # Get feature names
            feature_names = [f"feature_{i}" for i in range(X.shape[1])]
            
            return {
                'shap_values': shap_values,
                'feature_names': feature_names,
                'explainer': explainer,
                'summary_plot_data': self._prepare_summary_plot_data(shap_values, X, feature_names)
            }
        except Exception as e:
            logger.error(f"Error generating SHAP explanations: {e}")
            return {'error': str(e)}
    
    def _generate_lime_explanations(self, model: Any, X: np.ndarray, y: np.ndarray = None) -> Dict[str, Any]:
        """Generate LIME explanations."""
        try:
            # Create LIME explainer
            explainer = lime.lime_tabular.LimeTabularExplainer(
                X, 
                feature_names=[f"feature_{i}" for i in range(X.shape[1])],
                class_names=['class_0', 'class_1'] if self.config.task_type == "classification" else None,
                mode='classification' if self.config.task_type == "classification" else 'regression'
            )
            
            # Generate explanations for a few samples
            explanations = []
            for i in range(min(5, len(X))):
                exp = explainer.explain_instance(X[i], model.predict, num_features=10)
                explanations.append({
                    'sample_index': i,
                    'explanation': exp.as_list(),
                    'prediction': model.predict([X[i]])[0]
                })
            
            return {
                'explainer': explainer,
                'explanations': explanations
            }
        except Exception as e:
            logger.error(f"Error generating LIME explanations: {e}")
            return {'error': str(e)}
    
    def _generate_permutation_explanations(self, model: Any, X: np.ndarray, y: np.ndarray = None) -> Dict[str, Any]:
        """Generate permutation importance explanations."""
        try:
            # Calculate permutation importance
            perm_importance = permutation_importance(
                model, X, y, 
                n_repeats=10, 
                random_state=self.config.random_state
            )
            
            feature_names = [f"feature_{i}" for i in range(X.shape[1])]
            
            return {
                'importances_mean': perm_importance.importances_mean,
                'importances_std': perm_importance.importances_std,
                'feature_names': feature_names,
                'importance_ranking': sorted(
                    zip(feature_names, perm_importance.importances_mean),
                    key=lambda x: x[1], reverse=True
                )
            }
        except Exception as e:
            logger.error(f"Error generating permutation explanations: {e}")
            return {'error': str(e)}
    
    def _prepare_summary_plot_data(self, shap_values: np.ndarray, X: np.ndarray, 
                                 feature_names: List[str]) -> Dict[str, Any]:
        """Prepare data for SHAP summary plot."""
        if len(shap_values.shape) == 3:  # Multi-class classification
            shap_values = shap_values[1]  # Use positive class
        
        return {
            'shap_values': shap_values,
            'feature_values': X,
            'feature_names': feature_names
        }
    
    def create_explanation_report(self, explanations: Dict[str, Any], 
                                output_path: str = None) -> str:
        """Create a comprehensive explanation report."""
        report = "# Model Interpretability Report\n\n"
        
        for method, explanation in explanations.items():
            if 'error' in explanation:
                report += f"## {method.upper()} Explanations\n\n"
                report += f"Error: {explanation['error']}\n\n"
                continue
            
            report += f"## {method.upper()} Explanations\n\n"
            
            if method == "shap":
                report += "### SHAP Summary\n"
                report += "SHAP (SHapley Additive exPlanations) values show the contribution of each feature to the model's prediction.\n\n"
                
                if 'summary_plot_data' in explanation:
                    report += "### Feature Importance Ranking\n"
                    # Add feature importance ranking here
                    report += "Top features by SHAP importance:\n\n"
            
            elif method == "lime":
                report += "### LIME Summary\n"
                report += "LIME (Local Interpretable Model-agnostic Explanations) provides local explanations for individual predictions.\n\n"
                
                if 'explanations' in explanation:
                    report += f"Generated explanations for {len(explanation['explanations'])} samples.\n\n"
            
            elif method == "permutation":
                report += "### Permutation Importance Summary\n"
                report += "Permutation importance shows how much the model's performance decreases when a feature is randomly shuffled.\n\n"
                
                if 'importance_ranking' in explanation:
                    report += "### Top Features by Permutation Importance\n"
                    for i, (feature, importance) in enumerate(explanation['importance_ranking'][:10]):
                        report += f"{i+1}. {feature}: {importance:.4f}\n"
                    report += "\n"
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report)
            logger.info(f"Explanation report saved to {output_path}")
        
        return report
