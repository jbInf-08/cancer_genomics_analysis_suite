"""
Drug Response Prediction System for Cancer Genomics

This module provides comprehensive drug response prediction capabilities
integrating genomic, transcriptomic, and clinical data.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
from dataclasses import dataclass
from abc import ABC, abstractmethod
import warnings
warnings.filterwarnings('ignore')

# Machine Learning
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier
from sklearn.svm import SVC, SVR
from sklearn.linear_model import LogisticRegression, ElasticNet, Ridge
from sklearn.model_selection import cross_val_score, GridSearchCV, train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler, LabelEncoder, RobustScaler
from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif, RFE
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier, CatBoostRegressor

# Deep Learning
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import pytorch_lightning as pl

# Statistical Analysis
import scipy.stats as stats
from scipy.stats import pearsonr, spearmanr
from statsmodels.stats.multitest import multipletests

logger = logging.getLogger(__name__)


@dataclass
class DrugResponseData:
    """Data class for drug response data."""
    drug_id: str
    patient_id: str
    response_value: float
    response_type: str  # 'binary', 'continuous', 'categorical'
    response_category: str  # 'sensitive', 'resistant', 'partial', etc.
    genomic_features: Dict[str, float]
    clinical_features: Dict[str, Any]
    treatment_features: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class PredictionModel:
    """Data class for prediction model information."""
    model_id: str
    model_type: str
    model_name: str
    performance_metrics: Dict[str, float]
    feature_importance: Dict[str, float]
    training_data_size: int
    validation_metrics: Dict[str, float]
    model_parameters: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class DrugResponseConfig:
    """Configuration for drug response prediction."""
    response_threshold: float = 0.5
    min_training_samples: int = 50
    cross_validation_folds: int = 5
    test_size: float = 0.2
    random_state: int = 42
    feature_selection_method: str = 'mutual_info'
    n_top_features: int = 100
    model_types: List[str] = None
    ensemble_method: str = 'voting'  # 'voting', 'stacking', 'bagging'


class DrugResponsePredictor:
    """Main drug response prediction system."""
    
    def __init__(self, config: Optional[DrugResponseConfig] = None):
        """Initialize the drug response predictor."""
        self.config = config or DrugResponseConfig()
        if self.config.model_types is None:
            self.config.model_types = ['random_forest', 'xgboost', 'lightgbm', 'logistic_regression']
        
        self.models = {}
        self.feature_importance = {}
        self.performance_metrics = {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize model classes
        self.model_classes = {
            'random_forest': RandomForestClassifier,
            'xgboost': xgb.XGBClassifier,
            'lightgbm': lgb.LGBMClassifier,
            'logistic_regression': LogisticRegression,
            'svm': SVC,
            'gradient_boosting': GradientBoostingClassifier,
            'catboost': CatBoostClassifier
        }
    
    def train_models(self, 
                    training_data: List[DrugResponseData],
                    drug_id: str,
                    response_type: str = 'binary') -> Dict[str, PredictionModel]:
        """
        Train drug response prediction models.
        
        Args:
            training_data: List of drug response data
            drug_id: Drug identifier
            response_type: Type of response ('binary', 'continuous', 'categorical')
            
        Returns:
            Dictionary of trained models
        """
        self.logger.info(f"Training drug response models for {drug_id}")
        
        if len(training_data) < self.config.min_training_samples:
            self.logger.warning(f"Insufficient training data: {len(training_data)} samples")
            return {}
        
        # Prepare training data
        X, y, feature_names = self._prepare_training_data(training_data, response_type)
        
        # Feature selection
        selected_features = self._select_features(X, y, feature_names)
        X_selected = X[:, selected_features]
        feature_names_selected = [feature_names[i] for i in selected_features]
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_selected, y, test_size=self.config.test_size, 
            random_state=self.config.random_state, stratify=y if response_type == 'binary' else None
        )
        
        # Scale features
        scaler = RobustScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train models
        trained_models = {}
        
        for model_type in self.config.model_types:
            try:
                model = self._train_single_model(
                    model_type, X_train_scaled, y_train, X_test_scaled, y_test, response_type
                )
                
                if model:
                    trained_models[model_type] = model
                    
            except Exception as e:
                self.logger.warning(f"Error training {model_type}: {e}")
                continue
        
        # Store models and metadata
        self.models[drug_id] = trained_models
        self.feature_importance[drug_id] = dict(zip(feature_names_selected, 
                                                   np.mean([X_selected[:, i] for i in range(X_selected.shape[1])], axis=1)))
        
        self.logger.info(f"Successfully trained {len(trained_models)} models for {drug_id}")
        
        return trained_models
    
    def _prepare_training_data(self, 
                             training_data: List[DrugResponseData], 
                             response_type: str) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """Prepare training data for model training."""
        # Extract features
        all_features = set()
        for data in training_data:
            all_features.update(data.genomic_features.keys())
            all_features.update(data.clinical_features.keys())
            all_features.update(data.treatment_features.keys())
        
        feature_names = sorted(list(all_features))
        n_features = len(feature_names)
        n_samples = len(training_data)
        
        # Create feature matrix
        X = np.zeros((n_samples, n_features))
        y = np.zeros(n_samples)
        
        for i, data in enumerate(training_data):
            # Genomic features
            for j, feature in enumerate(feature_names):
                if feature in data.genomic_features:
                    X[i, j] = data.genomic_features[feature]
                elif feature in data.clinical_features:
                    X[i, j] = float(data.clinical_features[feature]) if isinstance(data.clinical_features[feature], (int, float)) else 0.0
                elif feature in data.treatment_features:
                    X[i, j] = float(data.treatment_features[feature]) if isinstance(data.treatment_features[feature], (int, float)) else 0.0
            
            # Response variable
            if response_type == 'binary':
                y[i] = 1 if data.response_value > self.config.response_threshold else 0
            else:
                y[i] = data.response_value
        
        return X, y, feature_names
    
    def _select_features(self, 
                        X: np.ndarray, 
                        y: np.ndarray, 
                        feature_names: List[str]) -> List[int]:
        """Select top features for model training."""
        if self.config.feature_selection_method == 'mutual_info':
            selector = SelectKBest(score_func=mutual_info_classif, k=min(self.config.n_top_features, X.shape[1]))
        else:
            selector = SelectKBest(score_func=f_classif, k=min(self.config.n_top_features, X.shape[1]))
        
        selector.fit(X, y)
        selected_indices = selector.get_support(indices=True)
        
        return selected_indices.tolist()
    
    def _train_single_model(self, 
                          model_type: str,
                          X_train: np.ndarray,
                          y_train: np.ndarray,
                          X_test: np.ndarray,
                          y_test: np.ndarray,
                          response_type: str) -> Optional[PredictionModel]:
        """Train a single model."""
        try:
            # Get model class
            model_class = self.model_classes.get(model_type)
            if not model_class:
                self.logger.warning(f"Unknown model type: {model_type}")
                return None
            
            # Initialize model with appropriate parameters
            if model_type == 'random_forest':
                model = model_class(n_estimators=100, random_state=self.config.random_state, n_jobs=-1)
            elif model_type == 'xgboost':
                model = model_class(random_state=self.config.random_state, n_jobs=-1)
            elif model_type == 'lightgbm':
                model = model_class(random_state=self.config.random_state, n_jobs=-1, verbose=-1)
            elif model_type == 'logistic_regression':
                model = model_class(random_state=self.config.random_state, max_iter=1000)
            elif model_type == 'svm':
                model = model_class(random_state=self.config.random_state, probability=True)
            elif model_type == 'gradient_boosting':
                model = model_class(random_state=self.config.random_state)
            elif model_type == 'catboost':
                model = model_class(random_seed=self.config.random_state, verbose=False)
            else:
                model = model_class(random_state=self.config.random_state)
            
            # Train model
            model.fit(X_train, y_train)
            
            # Make predictions
            y_pred = model.predict(X_test)
            y_pred_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else y_pred
            
            # Calculate performance metrics
            if response_type == 'binary':
                performance_metrics = {
                    'accuracy': accuracy_score(y_test, y_pred),
                    'precision': precision_score(y_test, y_pred, average='weighted'),
                    'recall': recall_score(y_test, y_pred, average='weighted'),
                    'f1_score': f1_score(y_test, y_pred, average='weighted'),
                    'auc': roc_auc_score(y_test, y_pred_proba) if len(np.unique(y_test)) > 1 else 0.0
                }
            else:
                performance_metrics = {
                    'mse': mean_squared_error(y_test, y_pred),
                    'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
                    'r2': r2_score(y_test, y_pred),
                    'mae': np.mean(np.abs(y_test - y_pred))
                }
            
            # Cross-validation
            cv_scores = cross_val_score(
                model, X_train, y_train, 
                cv=self.config.cross_validation_folds,
                scoring='roc_auc' if response_type == 'binary' else 'r2'
            )
            
            validation_metrics = {
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std(),
                'cv_scores': cv_scores.tolist()
            }
            
            # Feature importance
            feature_importance = {}
            if hasattr(model, 'feature_importances_'):
                feature_importance = dict(zip(range(X_train.shape[1]), model.feature_importances_))
            elif hasattr(model, 'coef_'):
                feature_importance = dict(zip(range(X_train.shape[1]), np.abs(model.coef_[0])))
            
            # Create prediction model
            prediction_model = PredictionModel(
                model_id=f"{model_type}_{len(self.models)}",
                model_type=model_type,
                model_name=f"{model_type}_model",
                performance_metrics=performance_metrics,
                feature_importance=feature_importance,
                training_data_size=len(X_train),
                validation_metrics=validation_metrics,
                model_parameters=model.get_params() if hasattr(model, 'get_params') else {},
                metadata={
                    'response_type': response_type,
                    'n_features': X_train.shape[1],
                    'training_timestamp': pd.Timestamp.now().isoformat()
                }
            )
            
            return prediction_model
            
        except Exception as e:
            self.logger.error(f"Error training {model_type}: {e}")
            return None
    
    def predict_response(self, 
                        patient_data: Dict[str, Any],
                        drug_id: str,
                        use_ensemble: bool = True) -> Dict[str, Any]:
        """
        Predict drug response for a patient.
        
        Args:
            patient_data: Patient's genomic and clinical data
            drug_id: Drug identifier
            use_ensemble: Whether to use ensemble prediction
            
        Returns:
            Prediction results
        """
        self.logger.info(f"Predicting response for drug {drug_id}")
        
        if drug_id not in self.models:
            self.logger.error(f"No trained models found for drug {drug_id}")
            return {'error': f'No trained models for {drug_id}'}
        
        # Prepare patient data
        X_patient = self._prepare_patient_data(patient_data, drug_id)
        
        if X_patient is None:
            return {'error': 'Could not prepare patient data'}
        
        # Make predictions
        predictions = {}
        probabilities = {}
        
        for model_type, model_info in self.models[drug_id].items():
            try:
                # Load model (in practice, would load from saved model)
                model = self._load_model(model_info)
                
                if model:
                    pred = model.predict(X_patient.reshape(1, -1))[0]
                    proba = model.predict_proba(X_patient.reshape(1, -1))[0] if hasattr(model, 'predict_proba') else [1-pred, pred]
                    
                    predictions[model_type] = pred
                    probabilities[model_type] = proba[1] if len(proba) > 1 else proba[0]
                    
            except Exception as e:
                self.logger.warning(f"Error predicting with {model_type}: {e}")
                continue
        
        if not predictions:
            return {'error': 'No successful predictions'}
        
        # Ensemble prediction
        if use_ensemble and len(predictions) > 1:
            ensemble_prediction = self._ensemble_predict(predictions, probabilities)
        else:
            # Use best performing model
            best_model = max(self.models[drug_id].items(), 
                           key=lambda x: x[1].performance_metrics.get('auc', x[1].performance_metrics.get('r2', 0)))
            ensemble_prediction = {
                'predicted_response': predictions[best_model[0]],
                'response_probability': probabilities[best_model[0]],
                'confidence_score': best_model[1].performance_metrics.get('auc', best_model[1].performance_metrics.get('r2', 0))
            }
        
        # Generate additional insights
        insights = self._generate_prediction_insights(patient_data, drug_id, ensemble_prediction)
        
        return {
            'drug_id': drug_id,
            'patient_id': patient_data.get('patient_id', 'Unknown'),
            'predicted_response': ensemble_prediction['predicted_response'],
            'response_probability': ensemble_prediction['response_probability'],
            'confidence_score': ensemble_prediction['confidence_score'],
            'individual_predictions': predictions,
            'individual_probabilities': probabilities,
            'insights': insights,
            'feature_importance': self.feature_importance.get(drug_id, {}),
            'model_performance': {model_type: model.performance_metrics 
                                for model_type, model in self.models[drug_id].items()}
        }
    
    def _prepare_patient_data(self, 
                            patient_data: Dict[str, Any], 
                            drug_id: str) -> Optional[np.ndarray]:
        """Prepare patient data for prediction."""
        # Get feature names from trained models
        if drug_id not in self.models:
            return None
        
        # Extract features (simplified - in practice would match exactly with training features)
        genomic_features = patient_data.get('genomic_features', {})
        clinical_features = patient_data.get('clinical_features', {})
        treatment_features = patient_data.get('treatment_features', {})
        
        # Combine all features
        all_features = {}
        all_features.update(genomic_features)
        all_features.update(clinical_features)
        all_features.update(treatment_features)
        
        # Convert to array (simplified - would need proper feature alignment)
        feature_values = list(all_features.values())
        
        return np.array(feature_values) if feature_values else None
    
    def _load_model(self, model_info: PredictionModel):
        """Load a trained model (mock implementation)."""
        # In practice, this would load the actual trained model from storage
        # For now, return None to indicate model loading is not implemented
        return None
    
    def _ensemble_predict(self, 
                         predictions: Dict[str, Any], 
                         probabilities: Dict[str, float]) -> Dict[str, Any]:
        """Create ensemble prediction from individual model predictions."""
        if self.config.ensemble_method == 'voting':
            # Majority voting for classification, average for regression
            if all(isinstance(p, (int, float)) and p in [0, 1] for p in predictions.values()):
                # Binary classification
                avg_prob = np.mean(list(probabilities.values()))
                predicted_response = 1 if avg_prob > 0.5 else 0
            else:
                # Regression
                predicted_response = np.mean(list(predictions.values()))
            
            response_probability = np.mean(list(probabilities.values()))
            confidence_score = 1.0 - np.std(list(probabilities.values()))
            
        else:
            # Simple averaging
            predicted_response = np.mean(list(predictions.values()))
            response_probability = np.mean(list(probabilities.values()))
            confidence_score = 1.0 - np.std(list(probabilities.values()))
        
        return {
            'predicted_response': predicted_response,
            'response_probability': response_probability,
            'confidence_score': confidence_score
        }
    
    def _generate_prediction_insights(self, 
                                    patient_data: Dict[str, Any],
                                    drug_id: str,
                                    prediction: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights from prediction results."""
        insights = {
            'key_biomarkers': [],
            'biomarker_values': {},
            'predicted_side_effects': [],
            'dose_recommendation': 'standard',
            'monitoring_requirements': [],
            'alternative_treatments': []
        }
        
        # Analyze key biomarkers
        genomic_features = patient_data.get('genomic_features', {})
        if genomic_features:
            # Get top features by importance
            feature_importance = self.feature_importance.get(drug_id, {})
            if feature_importance:
                top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]
                insights['key_biomarkers'] = [feature for feature, importance in top_features]
                insights['biomarker_values'] = {feature: genomic_features.get(feature, 0.0) 
                                              for feature, importance in top_features}
        
        # Predict side effects (mock implementation)
        if prediction['response_probability'] > 0.7:
            insights['predicted_side_effects'] = ['mild_nausea', 'fatigue']
        elif prediction['response_probability'] > 0.5:
            insights['predicted_side_effects'] = ['moderate_nausea', 'fatigue', 'skin_rash']
        else:
            insights['predicted_side_effects'] = ['severe_nausea', 'fatigue', 'skin_rash', 'liver_toxicity']
        
        # Dose recommendation
        if prediction['response_probability'] > 0.8:
            insights['dose_recommendation'] = 'standard_dose'
        elif prediction['response_probability'] > 0.6:
            insights['dose_recommendation'] = 'reduced_dose'
        else:
            insights['dose_recommendation'] = 'minimal_dose_or_alternative'
        
        # Monitoring requirements
        insights['monitoring_requirements'] = [
            'liver_function_tests',
            'complete_blood_count',
            'kidney_function_tests'
        ]
        
        return insights


class BiomarkerBasedPredictor:
    """Biomarker-based drug response predictor."""
    
    def __init__(self, config: Optional[DrugResponseConfig] = None):
        self.config = config or DrugResponseConfig()
        self.biomarker_models = {}
        self.logger = logging.getLogger(__name__)
    
    def train_biomarker_model(self, 
                            biomarker_data: pd.DataFrame,
                            response_data: pd.Series,
                            drug_id: str) -> Dict[str, Any]:
        """Train biomarker-based prediction model."""
        self.logger.info(f"Training biomarker model for {drug_id}")
        
        # Feature selection based on biomarker importance
        selected_features = self._select_biomarker_features(biomarker_data, response_data)
        
        # Train model
        X = biomarker_data[selected_features]
        y = response_data
        
        model = RandomForestClassifier(n_estimators=100, random_state=self.config.random_state)
        model.fit(X, y)
        
        # Calculate performance
        cv_scores = cross_val_score(model, X, y, cv=self.config.cross_validation_folds)
        
        # Store model
        self.biomarker_models[drug_id] = {
            'model': model,
            'features': selected_features,
            'performance': {
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std()
            }
        }
        
        return {
            'drug_id': drug_id,
            'selected_features': selected_features,
            'performance': {
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std()
            }
        }
    
    def _select_biomarker_features(self, 
                                 biomarker_data: pd.DataFrame, 
                                 response_data: pd.Series) -> List[str]:
        """Select most important biomarker features."""
        # Use mutual information for feature selection
        selector = SelectKBest(score_func=mutual_info_classif, k=self.config.n_top_features)
        selector.fit(biomarker_data, response_data)
        
        selected_features = biomarker_data.columns[selector.get_support()].tolist()
        return selected_features
    
    def predict_biomarker_response(self, 
                                 patient_biomarkers: Dict[str, float],
                                 drug_id: str) -> Dict[str, Any]:
        """Predict response based on biomarkers."""
        if drug_id not in self.biomarker_models:
            return {'error': f'No biomarker model for {drug_id}'}
        
        model_info = self.biomarker_models[drug_id]
        model = model_info['model']
        features = model_info['features']
        
        # Prepare patient data
        patient_features = []
        for feature in features:
            patient_features.append(patient_biomarkers.get(feature, 0.0))
        
        X_patient = np.array(patient_features).reshape(1, -1)
        
        # Make prediction
        prediction = model.predict(X_patient)[0]
        probability = model.predict_proba(X_patient)[0]
        
        return {
            'drug_id': drug_id,
            'predicted_response': prediction,
            'response_probability': probability[1] if len(probability) > 1 else probability[0],
            'key_biomarkers': features,
            'biomarker_values': {feature: patient_biomarkers.get(feature, 0.0) for feature in features}
        }


class MultiOmicsPredictor:
    """Multi-omics drug response predictor."""
    
    def __init__(self, config: Optional[DrugResponseConfig] = None):
        self.config = config or DrugResponseConfig()
        self.omics_models = {}
        self.logger = logging.getLogger(__name__)
    
    def train_multi_omics_model(self, 
                              genomics_data: pd.DataFrame,
                              transcriptomics_data: pd.DataFrame,
                              response_data: pd.Series,
                              drug_id: str,
                              proteomics_data: Optional[pd.DataFrame] = None,
                              metabolomics_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Train multi-omics prediction model."""
        self.logger.info(f"Training multi-omics model for {drug_id}")
        
        # Integrate omics data
        integrated_data = self._integrate_omics_data(
            genomics_data, transcriptomics_data, proteomics_data, metabolomics_data
        )
        
        # Feature selection
        selected_features = self._select_multi_omics_features(integrated_data, response_data)
        
        # Train model
        X = integrated_data[selected_features]
        y = response_data
        
        model = xgb.XGBClassifier(random_state=self.config.random_state)
        model.fit(X, y)
        
        # Calculate performance
        cv_scores = cross_val_score(model, X, y, cv=self.config.cross_validation_folds)
        
        # Store model
        self.omics_models[drug_id] = {
            'model': model,
            'features': selected_features,
            'performance': {
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std()
            }
        }
        
        return {
            'drug_id': drug_id,
            'selected_features': selected_features,
            'performance': {
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std()
            }
        }
    
    def _integrate_omics_data(self, 
                            genomics_data: pd.DataFrame,
                            transcriptomics_data: pd.DataFrame,
                            proteomics_data: Optional[pd.DataFrame] = None,
                            metabolomics_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Integrate multi-omics data."""
        # Start with genomics data
        integrated_data = genomics_data.copy()
        
        # Add transcriptomics data
        transcriptomics_data_prefixed = transcriptomics_data.add_prefix('trans_')
        integrated_data = integrated_data.join(transcriptomics_data_prefixed, how='outer')
        
        # Add proteomics data if available
        if proteomics_data is not None:
            proteomics_data_prefixed = proteomics_data.add_prefix('prot_')
            integrated_data = integrated_data.join(proteomics_data_prefixed, how='outer')
        
        # Add metabolomics data if available
        if metabolomics_data is not None:
            metabolomics_data_prefixed = metabolomics_data.add_prefix('metab_')
            integrated_data = integrated_data.join(metabolomics_data_prefixed, how='outer')
        
        # Fill missing values
        integrated_data = integrated_data.fillna(0.0)
        
        return integrated_data
    
    def _select_multi_omics_features(self, 
                                   integrated_data: pd.DataFrame, 
                                   response_data: pd.Series) -> List[str]:
        """Select features from integrated multi-omics data."""
        # Use feature importance from XGBoost
        temp_model = xgb.XGBClassifier(random_state=self.config.random_state)
        temp_model.fit(integrated_data, response_data)
        
        # Get feature importance
        feature_importance = temp_model.feature_importances_
        feature_names = integrated_data.columns
        
        # Select top features
        importance_pairs = list(zip(feature_names, feature_importance))
        importance_pairs.sort(key=lambda x: x[1], reverse=True)
        
        selected_features = [feature for feature, importance in importance_pairs[:self.config.n_top_features]]
        
        return selected_features
    
    def predict_multi_omics_response(self, 
                                   patient_omics_data: Dict[str, Dict[str, float]],
                                   drug_id: str) -> Dict[str, Any]:
        """Predict response using multi-omics data."""
        if drug_id not in self.omics_models:
            return {'error': f'No multi-omics model for {drug_id}'}
        
        model_info = self.omics_models[drug_id]
        model = model_info['model']
        features = model_info['features']
        
        # Prepare patient data
        patient_features = []
        for feature in features:
            # Determine which omics layer this feature belongs to
            if feature.startswith('trans_'):
                omics_data = patient_omics_data.get('transcriptomics', {})
                feature_name = feature[6:]  # Remove 'trans_' prefix
            elif feature.startswith('prot_'):
                omics_data = patient_omics_data.get('proteomics', {})
                feature_name = feature[5:]  # Remove 'prot_' prefix
            elif feature.startswith('metab_'):
                omics_data = patient_omics_data.get('metabolomics', {})
                feature_name = feature[6:]  # Remove 'metab_' prefix
            else:
                omics_data = patient_omics_data.get('genomics', {})
                feature_name = feature
            
            patient_features.append(omics_data.get(feature_name, 0.0))
        
        X_patient = np.array(patient_features).reshape(1, -1)
        
        # Make prediction
        prediction = model.predict(X_patient)[0]
        probability = model.predict_proba(X_patient)[0]
        
        return {
            'drug_id': drug_id,
            'predicted_response': prediction,
            'response_probability': probability[1] if len(probability) > 1 else probability[0],
            'key_features': features,
            'feature_values': {feature: patient_features[i] for i, feature in enumerate(features)}
        }
