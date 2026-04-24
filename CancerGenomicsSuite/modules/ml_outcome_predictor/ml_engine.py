"""
Machine Learning Engine for Cancer Outcome Prediction

This module contains the core machine learning models and training pipelines
for predicting cancer treatment outcomes, survival rates, and drug responses.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier
from sklearn.svm import SVC, SVR
from sklearn.linear_model import LogisticRegression, CoxPHFitter
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import joblib
import logging
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Try to import lifelines for survival analysis
try:
    from lifelines import CoxPHFitter as LifelinesCoxPHFitter
    from lifelines.utils import concordance_index
    LIFELINES_AVAILABLE = True
except ImportError:
    LIFELINES_AVAILABLE = False
    logging.warning("lifelines not available. Survival analysis features will be limited.")

logger = logging.getLogger(__name__)


class MLOutcomePredictor:
    """
    Base class for machine learning outcome prediction models.
    """
    
    def __init__(self, model_type: str = "random_forest", random_state: int = 42):
        """
        Initialize the ML outcome predictor.
        
        Args:
            model_type: Type of model to use ('random_forest', 'svm', 'logistic', 'neural_network')
            random_state: Random state for reproducibility
        """
        self.model_type = model_type
        self.random_state = random_state
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.is_trained = False
        self.feature_names = None
        self.model_params = {}
        
    def _initialize_model(self, task_type: str = "classification"):
        """Initialize the appropriate model based on type and task."""
        if self.model_type == "random_forest":
            if task_type == "classification":
                self.model = RandomForestClassifier(
                    n_estimators=100,
                    random_state=self.random_state,
                    max_depth=10,
                    min_samples_split=5,
                    min_samples_leaf=2
                )
            else:
                self.model = RandomForestRegressor(
                    n_estimators=100,
                    random_state=self.random_state,
                    max_depth=10,
                    min_samples_split=5,
                    min_samples_leaf=2
                )
                
        elif self.model_type == "svm":
            if task_type == "classification":
                self.model = SVC(
                    random_state=self.random_state,
                    probability=True,
                    kernel='rbf',
                    C=1.0,
                    gamma='scale'
                )
            else:
                self.model = SVR(
                    kernel='rbf',
                    C=1.0,
                    gamma='scale'
                )
                
        elif self.model_type == "logistic":
            if task_type == "classification":
                self.model = LogisticRegression(
                    random_state=self.random_state,
                    max_iter=1000,
                    C=1.0
                )
            else:
                raise ValueError("Logistic regression is only for classification tasks")
                
        elif self.model_type == "neural_network":
            if task_type == "classification":
                self.model = MLPClassifier(
                    random_state=self.random_state,
                    hidden_layer_sizes=(100, 50),
                    max_iter=500,
                    learning_rate_init=0.001
                )
            else:
                self.model = MLPRegressor(
                    random_state=self.random_state,
                    hidden_layer_sizes=(100, 50),
                    max_iter=500,
                    learning_rate_init=0.001
                )
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
    
    def train(self, X: pd.DataFrame, y: pd.Series, task_type: str = "classification") -> Dict[str, Any]:
        """
        Train the machine learning model.
        
        Args:
            X: Feature matrix
            y: Target variable
            task_type: Type of task ('classification' or 'regression')
            
        Returns:
            Dictionary containing training metrics
        """
        try:
            # Store feature names
            self.feature_names = X.columns.tolist()
            
            # Initialize model
            self._initialize_model(task_type)
            
            # Handle missing values
            X = X.fillna(X.mean())
            y = y.fillna(y.median() if task_type == "regression" else y.mode()[0])
            
            # Encode categorical variables in target for classification
            if task_type == "classification":
                y_encoded = self.label_encoder.fit_transform(y)
            else:
                y_encoded = y
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y_encoded, test_size=0.2, random_state=self.random_state, stratify=y_encoded if task_type == "classification" else None
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model
            self.model.fit(X_train_scaled, y_train)
            
            # Make predictions
            y_pred = self.model.predict(X_test_scaled)
            
            # Calculate metrics
            metrics = self._calculate_metrics(y_test, y_pred, task_type)
            
            self.is_trained = True
            logger.info(f"Model trained successfully. {task_type} task completed.")
            
            return {
                "status": "success",
                "metrics": metrics,
                "model_type": self.model_type,
                "task_type": task_type,
                "feature_count": len(self.feature_names),
                "training_samples": len(X_train),
                "test_samples": len(X_test)
            }
            
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Make predictions on new data.
        
        Args:
            X: Feature matrix
            
        Returns:
            Predictions array
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Handle missing values
        X = X.fillna(X.mean())
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Make predictions
        predictions = self.model.predict(X_scaled)
        
        # Decode predictions if classification
        if hasattr(self.model, 'predict_proba'):
            predictions = self.label_encoder.inverse_transform(predictions)
        
        return predictions
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Get prediction probabilities (for classification models).
        
        Args:
            X: Feature matrix
            
        Returns:
            Prediction probabilities
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        if not hasattr(self.model, 'predict_proba'):
            raise ValueError("Model does not support probability predictions")
        
        # Handle missing values
        X = X.fillna(X.mean())
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Get probabilities
        probabilities = self.model.predict_proba(X_scaled)
        
        return probabilities
    
    def _calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, task_type: str) -> Dict[str, float]:
        """Calculate appropriate metrics based on task type."""
        metrics = {}
        
        if task_type == "classification":
            metrics.update({
                "accuracy": accuracy_score(y_true, y_pred),
                "precision": precision_score(y_true, y_pred, average='weighted', zero_division=0),
                "recall": recall_score(y_true, y_pred, average='weighted', zero_division=0),
                "f1_score": f1_score(y_true, y_pred, average='weighted', zero_division=0)
            })
            
            # Add AUC if binary classification
            if len(np.unique(y_true)) == 2 and hasattr(self.model, 'predict_proba'):
                try:
                    y_proba = self.model.predict_proba(self.scaler.transform(
                        pd.DataFrame(np.random.randn(len(y_true), len(self.feature_names)), 
                                   columns=self.feature_names)
                    ))[:, 1]
                    metrics["roc_auc"] = roc_auc_score(y_true, y_proba)
                except:
                    pass
                    
        else:  # regression
            metrics.update({
                "mse": mean_squared_error(y_true, y_pred),
                "rmse": np.sqrt(mean_squared_error(y_true, y_pred)),
                "mae": mean_absolute_error(y_true, y_pred),
                "r2": r2_score(y_true, y_pred)
            })
        
        return metrics
    
    def save_model(self, filepath: str):
        """Save the trained model to disk."""
        if not self.is_trained:
            raise ValueError("Model must be trained before saving")
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'label_encoder': self.label_encoder,
            'model_type': self.model_type,
            'feature_names': self.feature_names,
            'model_params': self.model_params,
            'is_trained': self.is_trained
        }
        
        joblib.dump(model_data, filepath)
        logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """Load a trained model from disk."""
        model_data = joblib.load(filepath)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.label_encoder = model_data['label_encoder']
        self.model_type = model_data['model_type']
        self.feature_names = model_data['feature_names']
        self.model_params = model_data['model_params']
        self.is_trained = model_data['is_trained']
        
        logger.info(f"Model loaded from {filepath}")


class SurvivalPredictor:
    """
    Specialized predictor for survival analysis using Cox proportional hazards model.
    """
    
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.model = None
        self.is_trained = False
        self.feature_names = None
        
    def train(self, X: pd.DataFrame, duration: pd.Series, event: pd.Series) -> Dict[str, Any]:
        """
        Train survival prediction model.
        
        Args:
            X: Feature matrix
            duration: Time to event or censoring
            event: Event indicator (1 for event, 0 for censored)
            
        Returns:
            Training results
        """
        try:
            if not LIFELINES_AVAILABLE:
                # Fallback to simple regression approach
                return self._train_fallback(X, duration, event)
            
            self.feature_names = X.columns.tolist()
            
            # Prepare data
            data = X.copy()
            data['duration'] = duration
            data['event'] = event
            
            # Remove rows with missing values
            data = data.dropna()
            
            if len(data) == 0:
                raise ValueError("No valid data after removing missing values")
            
            # Initialize and fit Cox model
            self.model = LifelinesCoxPHFitter()
            self.model.fit(data, duration_col='duration', event_col='event')
            
            self.is_trained = True
            
            # Calculate concordance index
            c_index = concordance_index(
                data['duration'], 
                -self.model.predict_partial_hazard(data), 
                data['event']
            )
            
            return {
                "status": "success",
                "concordance_index": c_index,
                "feature_count": len(self.feature_names),
                "sample_count": len(data),
                "model_summary": self.model.summary.to_dict() if hasattr(self.model, 'summary') else {}
            }
            
        except Exception as e:
            logger.error(f"Error training survival model: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _train_fallback(self, X: pd.DataFrame, duration: pd.Series, event: pd.Series) -> Dict[str, Any]:
        """Fallback training method when lifelines is not available."""
        try:
            self.feature_names = X.columns.tolist()
            
            # Use random forest regressor as fallback
            from sklearn.ensemble import RandomForestRegressor
            
            # Prepare data
            data = X.fillna(X.mean())
            data['event'] = event.fillna(0)
            
            # Train model to predict duration
            self.model = RandomForestRegressor(n_estimators=100, random_state=self.random_state)
            self.model.fit(data, duration.fillna(duration.median()))
            
            self.is_trained = True
            
            # Calculate R² score
            predictions = self.model.predict(data)
            r2 = r2_score(duration.fillna(duration.median()), predictions)
            
            return {
                "status": "success",
                "r2_score": r2,
                "feature_count": len(self.feature_names),
                "sample_count": len(data),
                "note": "Using Random Forest fallback (lifelines not available)"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def predict_survival(self, X: pd.DataFrame) -> np.ndarray:
        """Predict survival times."""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        if LIFELINES_AVAILABLE and hasattr(self.model, 'predict_partial_hazard'):
            # Use Cox model
            data = X.fillna(X.mean())
            return -self.model.predict_partial_hazard(data)
        else:
            # Use fallback model
            data = X.fillna(X.mean())
            return self.model.predict(data)


class DrugResponsePredictor(MLOutcomePredictor):
    """
    Specialized predictor for drug response prediction.
    """
    
    def __init__(self, model_type: str = "random_forest", random_state: int = 42):
        super().__init__(model_type, random_state)
        self.drug_features = None
        self.genomic_features = None
        
    def train_drug_response(self, X: pd.DataFrame, y: pd.Series, 
                          drug_features: List[str] = None, 
                          genomic_features: List[str] = None) -> Dict[str, Any]:
        """
        Train model for drug response prediction.
        
        Args:
            X: Feature matrix
            y: Drug response (binary or continuous)
            drug_features: List of drug-related feature names
            genomic_features: List of genomic feature names
            
        Returns:
            Training results
        """
        self.drug_features = drug_features or []
        self.genomic_features = genomic_features or []
        
        # Determine task type based on target variable
        if y.dtype == 'object' or len(y.unique()) <= 10:
            task_type = "classification"
        else:
            task_type = "regression"
        
        return self.train(X, y, task_type)
    
    def predict_drug_response(self, X: pd.DataFrame, drug_name: str = None) -> Dict[str, Any]:
        """
        Predict drug response with additional context.
        
        Args:
            X: Feature matrix
            drug_name: Name of the drug (for context)
            
        Returns:
            Prediction results with confidence
        """
        predictions = self.predict(X)
        
        result = {
            "predictions": predictions.tolist(),
            "drug_name": drug_name,
            "model_type": self.model_type
        }
        
        # Add probabilities if available
        if hasattr(self.model, 'predict_proba'):
            probabilities = self.predict_proba(X)
            result["probabilities"] = probabilities.tolist()
            result["confidence"] = np.max(probabilities, axis=1).tolist()
        
        return result


class TreatmentOutcomeClassifier(MLOutcomePredictor):
    """
    Specialized classifier for treatment outcome prediction.
    """
    
    def __init__(self, model_type: str = "random_forest", random_state: int = 42):
        super().__init__(model_type, random_state)
        self.outcome_classes = None
        
    def train_outcome_classification(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """
        Train model for treatment outcome classification.
        
        Args:
            X: Feature matrix
            y: Treatment outcome classes
            
        Returns:
            Training results
        """
        self.outcome_classes = y.unique().tolist()
        return self.train(X, y, "classification")
    
    def predict_outcome_with_confidence(self, X: pd.DataFrame) -> Dict[str, Any]:
        """
        Predict treatment outcome with confidence scores.
        
        Args:
            X: Feature matrix
            
        Returns:
            Predictions with confidence scores
        """
        predictions = self.predict(X)
        
        result = {
            "predictions": predictions.tolist(),
            "outcome_classes": self.outcome_classes,
            "model_type": self.model_type
        }
        
        # Add probabilities and confidence
        if hasattr(self.model, 'predict_proba'):
            probabilities = self.predict_proba(X)
            result["probabilities"] = probabilities.tolist()
            result["confidence"] = np.max(probabilities, axis=1).tolist()
            
            # Add class-wise probabilities
            if self.outcome_classes:
                class_probs = {}
                for i, class_name in enumerate(self.outcome_classes):
                    class_probs[class_name] = probabilities[:, i].tolist()
                result["class_probabilities"] = class_probs
        
        return result


class ModelTrainer:
    """
    Comprehensive model trainer with hyperparameter optimization.
    """
    
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.best_models = {}
        self.training_history = []
        
    def optimize_hyperparameters(self, X: pd.DataFrame, y: pd.Series, 
                               model_type: str = "random_forest",
                               task_type: str = "classification",
                               cv_folds: int = 5) -> Dict[str, Any]:
        """
        Optimize hyperparameters using grid search.
        
        Args:
            X: Feature matrix
            y: Target variable
            model_type: Type of model to optimize
            task_type: Type of task
            cv_folds: Number of cross-validation folds
            
        Returns:
            Optimization results
        """
        try:
            # Define parameter grids
            param_grids = self._get_param_grids(model_type, task_type)
            
            # Initialize base model
            base_model = self._get_base_model(model_type, task_type)
            
            # Perform grid search
            grid_search = GridSearchCV(
                base_model,
                param_grids,
                cv=cv_folds,
                scoring=self._get_scoring_metric(task_type),
                n_jobs=-1,
                random_state=self.random_state
            )
            
            # Handle missing values
            X_clean = X.fillna(X.mean())
            y_clean = y.fillna(y.median() if task_type == "regression" else y.mode()[0])
            
            # Fit grid search
            grid_search.fit(X_clean, y_clean)
            
            # Store best model
            self.best_models[f"{model_type}_{task_type}"] = grid_search.best_estimator_
            
            # Record training history
            self.training_history.append({
                "timestamp": datetime.now().isoformat(),
                "model_type": model_type,
                "task_type": task_type,
                "best_score": grid_search.best_score_,
                "best_params": grid_search.best_params_,
                "cv_scores": grid_search.cv_results_['mean_test_score'].tolist()
            })
            
            return {
                "status": "success",
                "best_score": grid_search.best_score_,
                "best_params": grid_search.best_params_,
                "cv_results": grid_search.cv_results_,
                "model_type": model_type,
                "task_type": task_type
            }
            
        except Exception as e:
            logger.error(f"Error optimizing hyperparameters: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _get_param_grids(self, model_type: str, task_type: str) -> Dict[str, List]:
        """Get parameter grids for different model types."""
        if model_type == "random_forest":
            if task_type == "classification":
                return {
                    'n_estimators': [50, 100, 200],
                    'max_depth': [5, 10, 15, None],
                    'min_samples_split': [2, 5, 10],
                    'min_samples_leaf': [1, 2, 4]
                }
            else:
                return {
                    'n_estimators': [50, 100, 200],
                    'max_depth': [5, 10, 15, None],
                    'min_samples_split': [2, 5, 10],
                    'min_samples_leaf': [1, 2, 4]
                }
        
        elif model_type == "svm":
            return {
                'C': [0.1, 1, 10, 100],
                'gamma': ['scale', 'auto', 0.001, 0.01, 0.1, 1],
                'kernel': ['rbf', 'linear', 'poly']
            }
        
        elif model_type == "neural_network":
            return {
                'hidden_layer_sizes': [(50,), (100,), (100, 50), (200, 100)],
                'learning_rate_init': [0.001, 0.01, 0.1],
                'alpha': [0.0001, 0.001, 0.01]
            }
        
        else:
            return {}
    
    def _get_base_model(self, model_type: str, task_type: str):
        """Get base model for hyperparameter optimization."""
        if model_type == "random_forest":
            return RandomForestClassifier(random_state=self.random_state) if task_type == "classification" else RandomForestRegressor(random_state=self.random_state)
        elif model_type == "svm":
            return SVC(random_state=self.random_state, probability=True) if task_type == "classification" else SVR()
        elif model_type == "neural_network":
            return MLPClassifier(random_state=self.random_state) if task_type == "classification" else MLPRegressor(random_state=self.random_state)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
    
    def _get_scoring_metric(self, task_type: str) -> str:
        """Get appropriate scoring metric for task type."""
        return "accuracy" if task_type == "classification" else "r2"


class PredictionPipeline:
    """
    End-to-end prediction pipeline for cancer outcome prediction.
    """
    
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.preprocessor = None
        self.models = {}
        self.pipeline_config = {}
        
    def setup_pipeline(self, config: Dict[str, Any]):
        """
        Setup the prediction pipeline configuration.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.pipeline_config = config
        
        # Initialize models based on config
        for model_name, model_config in config.get("models", {}).items():
            model_type = model_config.get("type", "random_forest")
            task_type = model_config.get("task_type", "classification")
            
            if task_type == "survival":
                self.models[model_name] = SurvivalPredictor(self.random_state)
            elif task_type == "drug_response":
                self.models[model_name] = DrugResponsePredictor(model_type, self.random_state)
            elif task_type == "outcome_classification":
                self.models[model_name] = TreatmentOutcomeClassifier(model_type, self.random_state)
            else:
                self.models[model_name] = MLOutcomePredictor(model_type, self.random_state)
    
    def train_pipeline(self, data: Dict[str, pd.DataFrame], targets: Dict[str, pd.Series]) -> Dict[str, Any]:
        """
        Train all models in the pipeline.
        
        Args:
            data: Dictionary of feature matrices for each model
            targets: Dictionary of target variables for each model
            
        Returns:
            Training results for all models
        """
        results = {}
        
        for model_name, model in self.models.items():
            if model_name in data and model_name in targets:
                try:
                    if isinstance(model, SurvivalPredictor):
                        # For survival models, expect duration and event columns
                        target_data = targets[model_name]
                        if isinstance(target_data, dict) and 'duration' in target_data and 'event' in target_data:
                            result = model.train(data[model_name], target_data['duration'], target_data['event'])
                        else:
                            result = {"status": "error", "error": "Survival model requires duration and event data"}
                    else:
                        result = model.train(data[model_name], targets[model_name])
                    
                    results[model_name] = result
                    
                except Exception as e:
                    results[model_name] = {
                        "status": "error",
                        "error": str(e)
                    }
        
        return results
    
    def predict_pipeline(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Make predictions using all trained models.
        
        Args:
            data: Dictionary of feature matrices for each model
            
        Returns:
            Predictions from all models
        """
        predictions = {}
        
        for model_name, model in self.models.items():
            if model_name in data and model.is_trained:
                try:
                    if isinstance(model, SurvivalPredictor):
                        pred = model.predict_survival(data[model_name])
                        predictions[model_name] = {
                            "predictions": pred.tolist(),
                            "model_type": "survival"
                        }
                    elif isinstance(model, DrugResponsePredictor):
                        predictions[model_name] = model.predict_drug_response(data[model_name])
                    elif isinstance(model, TreatmentOutcomeClassifier):
                        predictions[model_name] = model.predict_outcome_with_confidence(data[model_name])
                    else:
                        pred = model.predict(data[model_name])
                        predictions[model_name] = {
                            "predictions": pred.tolist(),
                            "model_type": model.model_type
                        }
                        
                except Exception as e:
                    predictions[model_name] = {
                        "status": "error",
                        "error": str(e)
                    }
        
        return predictions
    
    def save_pipeline(self, filepath: str):
        """Save the entire pipeline to disk."""
        pipeline_data = {
            'models': self.models,
            'pipeline_config': self.pipeline_config,
            'random_state': self.random_state
        }
        
        joblib.dump(pipeline_data, filepath)
        logger.info(f"Pipeline saved to {filepath}")
    
    def load_pipeline(self, filepath: str):
        """Load a pipeline from disk."""
        pipeline_data = joblib.load(filepath)
        
        self.models = pipeline_data['models']
        self.pipeline_config = pipeline_data['pipeline_config']
        self.random_state = pipeline_data['random_state']
        
        logger.info(f"Pipeline loaded from {filepath}")
