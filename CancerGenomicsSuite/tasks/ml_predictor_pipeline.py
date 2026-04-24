"""
ML Predictor Pipeline Module

This module provides comprehensive machine learning prediction pipeline capabilities
for the Cancer Genomics Analysis Suite, including model training, prediction,
and evaluation workflows for various genomics analysis tasks.
"""

import os
import pickle
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.pipeline import Pipeline
import joblib
import matplotlib.pyplot as plt
import seaborn as sns


@dataclass
class MLConfig:
    """Machine learning configuration parameters."""
    model_type: str = "random_forest"  # random_forest, svm, logistic_regression, gradient_boosting
    test_size: float = 0.2
    random_state: int = 42
    cv_folds: int = 5
    n_jobs: int = -1
    scoring: str = "accuracy"
    feature_selection: bool = True
    feature_selection_method: str = "mutual_info"  # mutual_info, chi2, f_classif
    n_features: Optional[int] = None
    hyperparameter_tuning: bool = True
    save_model: bool = True
    model_save_path: Optional[str] = None


@dataclass
class ModelPerformance:
    """Model performance metrics."""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    roc_auc: float
    confusion_matrix: np.ndarray
    classification_report: str
    cross_val_scores: List[float]
    feature_importance: Optional[Dict[str, float]] = None


class MLPredictorPipeline:
    """
    A comprehensive machine learning prediction pipeline for cancer genomics analysis.
    
    This class provides methods for data preprocessing, model training, prediction,
    and evaluation for various genomics analysis tasks.
    """
    
    def __init__(self, config: MLConfig):
        """
        Initialize the ML predictor pipeline.
        
        Args:
            config (MLConfig): ML configuration parameters
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_selector = None
        self.feature_names = None
        self.target_names = None
        self.performance_metrics = None
        
        # Model parameter grids for hyperparameter tuning
        self.param_grids = {
            'random_forest': {
                'n_estimators': [100, 200, 300],
                'max_depth': [10, 20, None],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4]
            },
            'svm': {
                'C': [0.1, 1, 10, 100],
                'gamma': ['scale', 'auto', 0.001, 0.01, 0.1, 1],
                'kernel': ['rbf', 'linear', 'poly']
            },
            'logistic_regression': {
                'C': [0.1, 1, 10, 100],
                'penalty': ['l1', 'l2'],
                'solver': ['liblinear', 'saga']
            },
            'gradient_boosting': {
                'n_estimators': [100, 200, 300],
                'learning_rate': [0.01, 0.1, 0.2],
                'max_depth': [3, 5, 7],
                'subsample': [0.8, 0.9, 1.0]
            }
        }
    
    def _get_model(self):
        """Get the appropriate model based on configuration."""
        if self.config.model_type == "random_forest":
            return RandomForestClassifier(random_state=self.config.random_state)
        elif self.config.model_type == "svm":
            return SVC(random_state=self.config.random_state, probability=True)
        elif self.config.model_type == "logistic_regression":
            return LogisticRegression(random_state=self.config.random_state, max_iter=1000)
        elif self.config.model_type == "gradient_boosting":
            return GradientBoostingClassifier(random_state=self.config.random_state)
        else:
            raise ValueError(f"Unsupported model type: {self.config.model_type}")
    
    def preprocess_data(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Preprocess the input data.
        
        Args:
            X (pd.DataFrame): Feature matrix
            y (pd.Series, optional): Target variable
            
        Returns:
            Tuple[np.ndarray, Optional[np.ndarray]]: Preprocessed features and targets
        """
        self.logger.info("Preprocessing data...")
        
        # Store feature names
        self.feature_names = X.columns.tolist()
        
        # Handle missing values
        X_processed = X.fillna(X.mean())
        
        # Encode categorical variables
        categorical_columns = X_processed.select_dtypes(include=['object', 'category']).columns
        if len(categorical_columns) > 0:
            self.logger.info(f"Encoding {len(categorical_columns)} categorical columns")
            X_processed = pd.get_dummies(X_processed, columns=categorical_columns, drop_first=True)
        
        # Update feature names after encoding
        self.feature_names = X_processed.columns.tolist()
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X_processed)
        
        # Process target variable if provided
        y_processed = None
        if y is not None:
            if y.dtype == 'object' or y.dtype.name == 'category':
                y_processed = self.label_encoder.fit_transform(y)
                self.target_names = self.label_encoder.classes_
            else:
                y_processed = y.values
        
        self.logger.info(f"Preprocessed data shape: {X_scaled.shape}")
        return X_scaled, y_processed
    
    def select_features(self, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        """
        Perform feature selection.
        
        Args:
            X (np.ndarray): Feature matrix
            y (np.ndarray): Target variable
            
        Returns:
            np.ndarray: Selected features
        """
        if not self.config.feature_selection:
            return X
        
        self.logger.info("Performing feature selection...")
        
        from sklearn.feature_selection import SelectKBest, mutual_info_classif, chi2, f_classif
        
        # Select feature selection method
        if self.config.feature_selection_method == "mutual_info":
            score_func = mutual_info_classif
        elif self.config.feature_selection_method == "chi2":
            score_func = chi2
        elif self.config.feature_selection_method == "f_classif":
            score_func = f_classif
        else:
            raise ValueError(f"Unsupported feature selection method: {self.config.feature_selection_method}")
        
        # Determine number of features to select
        n_features = self.config.n_features
        if n_features is None:
            n_features = min(50, X.shape[1])  # Default to 50 or all features if less
        
        # Perform feature selection
        self.feature_selector = SelectKBest(score_func=score_func, k=n_features)
        X_selected = self.feature_selector.fit_transform(X, y)
        
        # Update feature names
        if self.feature_selector.get_support() is not None:
            selected_indices = self.feature_selector.get_support(indices=True)
            self.feature_names = [self.feature_names[i] for i in selected_indices]
        
        self.logger.info(f"Selected {X_selected.shape[1]} features from {X.shape[1]} original features")
        return X_selected
    
    def train_model(self, X: pd.DataFrame, y: pd.Series) -> ModelPerformance:
        """
        Train the machine learning model.
        
        Args:
            X (pd.DataFrame): Feature matrix
            y (pd.Series): Target variable
            
        Returns:
            ModelPerformance: Model performance metrics
        """
        self.logger.info(f"Training {self.config.model_type} model...")
        
        # Preprocess data
        X_processed, y_processed = self.preprocess_data(X, y)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_processed, y_processed,
            test_size=self.config.test_size,
            random_state=self.config.random_state,
            stratify=y_processed
        )
        
        # Feature selection
        X_train_selected = self.select_features(X_train, y_train)
        X_test_selected = self.select_features(X_test, y_test)
        
        # Get base model
        base_model = self._get_model()
        
        # Hyperparameter tuning
        if self.config.hyperparameter_tuning:
            self.logger.info("Performing hyperparameter tuning...")
            param_grid = self.param_grids.get(self.config.model_type, {})
            
            if param_grid:
                grid_search = GridSearchCV(
                    base_model,
                    param_grid,
                    cv=self.config.cv_folds,
                    scoring=self.config.scoring,
                    n_jobs=self.config.n_jobs,
                    verbose=1
                )
                grid_search.fit(X_train_selected, y_train)
                self.model = grid_search.best_estimator_
                self.logger.info(f"Best parameters: {grid_search.best_params_}")
            else:
                self.model = base_model
        else:
            self.model = base_model
            self.model.fit(X_train_selected, y_train)
        
        # Cross-validation
        cv_scores = cross_val_score(
            self.model, X_train_selected, y_train,
            cv=self.config.cv_folds,
            scoring=self.config.scoring
        )
        
        # Make predictions
        y_pred = self.model.predict(X_test_selected)
        y_pred_proba = self.model.predict_proba(X_test_selected)
        
        # Calculate metrics
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average='weighted')
        recall = recall_score(y_test, y_pred, average='weighted')
        f1 = f1_score(y_test, y_pred, average='weighted')
        
        # ROC AUC (handle multi-class)
        if len(np.unique(y_test)) == 2:
            roc_auc = roc_auc_score(y_test, y_pred_proba[:, 1])
        else:
            roc_auc = roc_auc_score(y_test, y_pred_proba, multi_class='ovr', average='weighted')
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        
        # Classification report
        class_report = classification_report(y_test, y_pred, target_names=self.target_names)
        
        # Feature importance
        feature_importance = None
        if hasattr(self.model, 'feature_importances_'):
            feature_importance = dict(zip(self.feature_names, self.model.feature_importances_))
        
        # Store performance metrics
        self.performance_metrics = ModelPerformance(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            roc_auc=roc_auc,
            confusion_matrix=cm,
            classification_report=class_report,
            cross_val_scores=cv_scores.tolist(),
            feature_importance=feature_importance
        )
        
        self.logger.info(f"Model training completed. Accuracy: {accuracy:.4f}")
        
        # Save model if configured
        if self.config.save_model:
            self.save_model()
        
        return self.performance_metrics
    
    def predict(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make predictions on new data.
        
        Args:
            X (pd.DataFrame): Feature matrix
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: Predictions and prediction probabilities
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train_model() first.")
        
        self.logger.info("Making predictions...")
        
        # Preprocess data
        X_processed, _ = self.preprocess_data(X)
        
        # Apply feature selection
        if self.feature_selector is not None:
            X_processed = self.feature_selector.transform(X_processed)
        
        # Make predictions
        predictions = self.model.predict(X_processed)
        prediction_probas = self.model.predict_proba(X_processed)
        
        # Convert predictions back to original labels if needed
        if self.target_names is not None:
            predictions = self.label_encoder.inverse_transform(predictions)
        
        return predictions, prediction_probas
    
    def save_model(self, filepath: Optional[str] = None):
        """
        Save the trained model and preprocessing objects.
        
        Args:
            filepath (str, optional): Path to save the model
        """
        if self.model is None:
            raise ValueError("No model to save. Train the model first.")
        
        if filepath is None:
            filepath = self.config.model_save_path or f"model_{self.config.model_type}.pkl"
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'label_encoder': self.label_encoder,
            'feature_selector': self.feature_selector,
            'feature_names': self.feature_names,
            'target_names': self.target_names,
            'config': self.config,
            'performance_metrics': self.performance_metrics
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        self.logger.info(f"Model saved to: {filepath}")
    
    def load_model(self, filepath: str):
        """
        Load a trained model and preprocessing objects.
        
        Args:
            filepath (str): Path to the model file
        """
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.label_encoder = model_data['label_encoder']
        self.feature_selector = model_data['feature_selector']
        self.feature_names = model_data['feature_names']
        self.target_names = model_data['target_names']
        self.config = model_data['config']
        self.performance_metrics = model_data['performance_metrics']
        
        self.logger.info(f"Model loaded from: {filepath}")
    
    def plot_feature_importance(self, top_n: int = 20, save_path: Optional[str] = None):
        """
        Plot feature importance.
        
        Args:
            top_n (int): Number of top features to display
            save_path (str, optional): Path to save the plot
        """
        if not self.performance_metrics or not self.performance_metrics.feature_importance:
            self.logger.warning("No feature importance data available")
            return
        
        # Get top features
        importance_dict = self.performance_metrics.feature_importance
        sorted_features = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
        features, importances = zip(*sorted_features)
        
        # Create plot
        plt.figure(figsize=(10, 8))
        plt.barh(range(len(features)), importances)
        plt.yticks(range(len(features)), features)
        plt.xlabel('Feature Importance')
        plt.title(f'Top {top_n} Feature Importances')
        plt.gca().invert_yaxis()
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            self.logger.info(f"Feature importance plot saved to: {save_path}")
        
        plt.show()
    
    def plot_confusion_matrix(self, save_path: Optional[str] = None):
        """
        Plot confusion matrix.
        
        Args:
            save_path (str, optional): Path to save the plot
        """
        if not self.performance_metrics:
            self.logger.warning("No performance metrics available")
            return
        
        cm = self.performance_metrics.confusion_matrix
        
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                   xticklabels=self.target_names,
                   yticklabels=self.target_names)
        plt.title('Confusion Matrix')
        plt.xlabel('Predicted')
        plt.ylabel('Actual')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            self.logger.info(f"Confusion matrix plot saved to: {save_path}")
        
        plt.show()
    
    def generate_report(self, output_path: str):
        """
        Generate a comprehensive model performance report.
        
        Args:
            output_path (str): Path to save the report
        """
        if not self.performance_metrics:
            self.logger.warning("No performance metrics available")
            return
        
        with open(output_path, 'w') as f:
            f.write("Machine Learning Model Performance Report\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Model Type: {self.config.model_type}\n")
            f.write(f"Test Size: {self.config.test_size}\n")
            f.write(f"Cross-Validation Folds: {self.config.cv_folds}\n")
            f.write(f"Feature Selection: {self.config.feature_selection}\n")
            if self.config.feature_selection:
                f.write(f"Feature Selection Method: {self.config.feature_selection_method}\n")
                f.write(f"Number of Features: {len(self.feature_names)}\n")
            f.write("\n")
            
            f.write("Performance Metrics:\n")
            f.write(f"  Accuracy: {self.performance_metrics.accuracy:.4f}\n")
            f.write(f"  Precision: {self.performance_metrics.precision:.4f}\n")
            f.write(f"  Recall: {self.performance_metrics.recall:.4f}\n")
            f.write(f"  F1-Score: {self.performance_metrics.f1_score:.4f}\n")
            f.write(f"  ROC AUC: {self.performance_metrics.roc_auc:.4f}\n\n")
            
            f.write("Cross-Validation Scores:\n")
            f.write(f"  Mean: {np.mean(self.performance_metrics.cross_val_scores):.4f}\n")
            f.write(f"  Std: {np.std(self.performance_metrics.cross_val_scores):.4f}\n")
            f.write(f"  Scores: {self.performance_metrics.cross_val_scores}\n\n")
            
            f.write("Classification Report:\n")
            f.write(self.performance_metrics.classification_report)
            f.write("\n")
            
            if self.performance_metrics.feature_importance:
                f.write("Top 10 Feature Importances:\n")
                sorted_features = sorted(
                    self.performance_metrics.feature_importance.items(),
                    key=lambda x: x[1], reverse=True
                )[:10]
                
                for feature, importance in sorted_features:
                    f.write(f"  {feature}: {importance:.4f}\n")
        
        self.logger.info(f"Performance report saved to: {output_path}")
    
    def batch_predict(self, data_files: List[str], output_dir: str) -> Dict[str, str]:
        """
        Perform batch prediction on multiple data files.
        
        Args:
            data_files (List[str]): List of data file paths
            output_dir (str): Output directory for predictions
            
        Returns:
            Dict[str, str]: Mapping of input file to output file
        """
        os.makedirs(output_dir, exist_ok=True)
        results = {}
        
        for data_file in data_files:
            self.logger.info(f"Processing data file: {data_file}")
            
            try:
                # Load data
                if data_file.endswith('.csv'):
                    data = pd.read_csv(data_file)
                elif data_file.endswith('.xlsx'):
                    data = pd.read_excel(data_file)
                else:
                    self.logger.warning(f"Unsupported file format: {data_file}")
                    continue
                
                # Make predictions
                predictions, probabilities = self.predict(data)
                
                # Create results DataFrame
                results_df = data.copy()
                results_df['prediction'] = predictions
                
                # Add probability columns
                if self.target_names is not None:
                    for i, class_name in enumerate(self.target_names):
                        results_df[f'probability_{class_name}'] = probabilities[:, i]
                
                # Save results
                output_file = os.path.join(output_dir, f"predictions_{os.path.basename(data_file)}")
                results_df.to_csv(output_file, index=False)
                results[data_file] = output_file
                
                self.logger.info(f"Predictions saved to: {output_file}")
                
            except Exception as e:
                self.logger.error(f"Error processing {data_file}: {e}")
                results[data_file] = None
        
        return results
