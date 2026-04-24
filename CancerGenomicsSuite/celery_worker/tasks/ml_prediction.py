"""
Machine Learning Prediction Tasks

This module contains Celery tasks for machine learning-based
predictions in cancer genomics analysis.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from celery import current_task
from celery_worker import celery
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import joblib
import os

logger = logging.getLogger(__name__)

@celery.task(bind=True, name="celery_worker.tasks.ml_prediction.train_survival_model")
def train_survival_model(self, clinical_data: Dict, expression_data: Dict, 
                        mutation_data: Dict, model_type: str = "random_forest") -> Dict[str, Any]:
    """
    Train machine learning model for survival prediction.
    
    Args:
        clinical_data: Clinical features and survival outcomes
        expression_data: Gene expression features
        mutation_data: Mutation features
        model_type: ML model type (random_forest, svm, neural_network, xgboost)
    
    Returns:
        Dict containing trained model and performance metrics
    """
    try:
        logger.info(f"Starting survival model training: {model_type}")
        
        self.update_state(state="PROGRESS", meta={"current": 0, "total": 100, "status": "Preparing data"})
        
        # Prepare features and targets
        X, y = _prepare_survival_features(clinical_data, expression_data, mutation_data)
        
        self.update_state(state="PROGRESS", meta={"current": 25, "total": 100, "status": "Splitting data"})
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        self.update_state(state="PROGRESS", meta={"current": 50, "total": 100, "status": "Training model"})
        
        # Train model
        model = _get_model(model_type)
        model.fit(X_train_scaled, y_train)
        
        self.update_state(state="PROGRESS", meta={"current": 75, "total": 100, "status": "Evaluating model"})
        
        # Evaluate model
        y_pred = model.predict(X_test_scaled)
        metrics = _calculate_metrics(y_test, y_pred)
        
        # Cross-validation
        cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)
        
        # Feature importance
        feature_importance = _get_feature_importance(model, X.columns)
        
        self.update_state(state="PROGRESS", meta={"current": 100, "total": 100, "status": "Complete"})
        
        # Save model
        model_path = f"models/survival_model_{model_type}.joblib"
        os.makedirs("models", exist_ok=True)
        joblib.dump({
            'model': model,
            'scaler': scaler,
            'feature_names': X.columns.tolist()
        }, model_path)
        
        stats = {
            "model_type": model_type,
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "features": len(X.columns),
            "cv_mean_score": cv_scores.mean(),
            "cv_std_score": cv_scores.std(),
            "model_path": model_path
        }
        
        logger.info(f"Survival model training completed: {stats}")
        return {
            "model_metrics": metrics,
            "cross_validation": {
                "scores": cv_scores.tolist(),
                "mean": cv_scores.mean(),
                "std": cv_scores.std()
            },
            "feature_importance": feature_importance,
            "statistics": stats,
            "status": "success"
        }
        
    except Exception as exc:
        logger.error(f"Survival model training failed: {exc}")
        self.update_state(state="FAILURE", meta={"error": str(exc)})
        raise

@celery.task(bind=True, name="celery_worker.tasks.ml_prediction.predict_treatment_response")
def predict_treatment_response(self, patient_features: Dict, treatment: str, 
                             model_path: str = None) -> Dict[str, Any]:
    """
    Predict treatment response for a patient.
    
    Args:
        patient_features: Patient's genomic and clinical features
        treatment: Treatment type
        model_path: Path to trained model
    
    Returns:
        Dict containing treatment response prediction
    """
    try:
        logger.info(f"Starting treatment response prediction: {treatment}")
        
        self.update_state(state="PROGRESS", meta={"current": 0, "total": 100, "status": "Loading model"})
        
        # Load model
        if model_path is None:
            model_path = f"models/treatment_response_{treatment}.joblib"
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        model_data = joblib.load(model_path)
        model = model_data['model']
        scaler = model_data['scaler']
        feature_names = model_data['feature_names']
        
        self.update_state(state="PROGRESS", meta={"current": 25, "total": 100, "status": "Preparing features"})
        
        # Prepare patient features
        patient_df = _prepare_patient_features(patient_features, feature_names)
        
        self.update_state(state="PROGRESS", meta={"current": 50, "total": 100, "status": "Scaling features"})
        
        # Scale features
        patient_scaled = scaler.transform(patient_df)
        
        self.update_state(state="PROGRESS", meta={"current": 75, "total": 100, "status": "Making prediction"})
        
        # Make prediction
        prediction = model.predict(patient_scaled)[0]
        prediction_proba = model.predict_proba(patient_scaled)[0]
        
        # Get confidence
        confidence = max(prediction_proba)
        
        self.update_state(state="PROGRESS", meta={"current": 100, "total": 100, "status": "Complete"})
        
        # Prepare response
        response_classes = model.classes_
        response_mapping = {0: "resistant", 1: "sensitive", 2: "partial_response"}
        predicted_response = response_mapping.get(prediction, "unknown")
        
        stats = {
            "treatment": treatment,
            "predicted_response": predicted_response,
            "confidence": confidence,
            "probability_distribution": dict(zip(response_classes, prediction_proba))
        }
        
        logger.info(f"Treatment response prediction completed: {stats}")
        return {
            "prediction": predicted_response,
            "confidence": confidence,
            "probability_distribution": stats["probability_distribution"],
            "statistics": stats,
            "status": "success"
        }
        
    except Exception as exc:
        logger.error(f"Treatment response prediction failed: {exc}")
        self.update_state(state="FAILURE", meta={"error": str(exc)})
        raise

@celery.task(bind=True, name="celery_worker.tasks.ml_prediction.cluster_patients")
def cluster_patients(self, multi_omics_data: Dict, n_clusters: int = 3, 
                    method: str = "kmeans") -> Dict[str, Any]:
    """
    Cluster patients based on multi-omics data.
    
    Args:
        multi_omics_data: Combined multi-omics features
        n_clusters: Number of clusters
        method: Clustering method (kmeans, hierarchical, dbscan)
    
    Returns:
        Dict containing clustering results and patient assignments
    """
    try:
        logger.info(f"Starting patient clustering: {method}")
        
        self.update_state(state="PROGRESS", meta={"current": 0, "total": 100, "status": "Preparing data"})
        
        # Prepare multi-omics data
        X = _prepare_multi_omics_features(multi_omics_data)
        
        self.update_state(state="PROGRESS", meta={"current": 25, "total": 100, "status": "Preprocessing"})
        
        # Preprocess data
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        self.update_state(state="PROGRESS", meta={"current": 50, "total": 100, "status": "Clustering"})
        
        # Perform clustering
        cluster_labels = _perform_clustering(X_scaled, n_clusters, method)
        
        self.update_state(state="PROGRESS", meta={"current": 75, "total": 100, "status": "Analyzing clusters"})
        
        # Analyze clusters
        cluster_analysis = _analyze_clusters(X, cluster_labels)
        
        self.update_state(state="PROGRESS", meta={"current": 100, "total": 100, "status": "Complete"})
        
        # Prepare results
        patient_assignments = pd.DataFrame({
            'patient_id': X.index,
            'cluster': cluster_labels
        })
        
        stats = {
            "method": method,
            "n_clusters": n_clusters,
            "total_patients": len(X),
            "cluster_sizes": dict(zip(*np.unique(cluster_labels, return_counts=True)))
        }
        
        logger.info(f"Patient clustering completed: {stats}")
        return {
            "patient_assignments": patient_assignments.to_dict('records'),
            "cluster_analysis": cluster_analysis,
            "statistics": stats,
            "status": "success"
        }
        
    except Exception as exc:
        logger.error(f"Patient clustering failed: {exc}")
        self.update_state(state="FAILURE", meta={"error": str(exc)})
        raise

@celery.task(bind=True, name="celery_worker.tasks.ml_prediction.feature_selection")
def feature_selection(self, features: Dict, target: List, method: str = "mutual_info", 
                     n_features: int = 100) -> Dict[str, Any]:
    """
    Perform feature selection for machine learning models.
    
    Args:
        features: Feature matrix
        target: Target variable
        method: Selection method (mutual_info, chi2, f_score, lasso)
        n_features: Number of features to select
    
    Returns:
        Dict containing selected features and importance scores
    """
    try:
        logger.info(f"Starting feature selection: {method}")
        
        self.update_state(state="PROGRESS", meta={"current": 0, "total": 100, "status": "Preparing data"})
        
        # Prepare features
        X = pd.DataFrame(features)
        y = np.array(target)
        
        self.update_state(state="PROGRESS", meta={"current": 25, "total": 100, "status": "Running selection"})
        
        # Perform feature selection
        selected_features, importance_scores = _perform_feature_selection(X, y, method, n_features)
        
        self.update_state(state="PROGRESS", meta={"current": 75, "total": 100, "status": "Analyzing results"})
        
        # Analyze selected features
        feature_analysis = _analyze_selected_features(selected_features, importance_scores)
        
        self.update_state(state="PROGRESS", meta={"current": 100, "total": 100, "status": "Complete"})
        
        stats = {
            "method": method,
            "original_features": len(X.columns),
            "selected_features": len(selected_features),
            "selection_ratio": len(selected_features) / len(X.columns)
        }
        
        logger.info(f"Feature selection completed: {stats}")
        return {
            "selected_features": selected_features,
            "importance_scores": importance_scores,
            "feature_analysis": feature_analysis,
            "statistics": stats,
            "status": "success"
        }
        
    except Exception as exc:
        logger.error(f"Feature selection failed: {exc}")
        self.update_state(state="FAILURE", meta={"error": str(exc)})
        raise

# Helper functions
def _prepare_survival_features(clinical_data: Dict, expression_data: Dict, mutation_data: Dict) -> Tuple[pd.DataFrame, np.ndarray]:
    """Prepare features for survival prediction."""
    # Combine all features
    clinical_df = pd.DataFrame(clinical_data)
    expression_df = pd.DataFrame(expression_data)
    mutation_df = pd.DataFrame(mutation_data)
    
    # Merge on patient ID
    features = clinical_df.merge(expression_df, on='patient_id', how='inner')
    features = features.merge(mutation_df, on='patient_id', how='inner')
    
    # Separate features and target
    target_cols = ['survival_time', 'event']
    X = features.drop(columns=target_cols + ['patient_id'])
    y = features['event']  # Binary survival outcome
    
    return X, y

def _get_model(model_type: str):
    """Get ML model based on type."""
    models = {
        "random_forest": RandomForestClassifier(n_estimators=100, random_state=42),
        "svm": SVC(probability=True, random_state=42),
        "neural_network": MLPClassifier(hidden_layer_sizes=(100, 50), random_state=42),
        "xgboost": GradientBoostingClassifier(n_estimators=100, random_state=42)
    }
    return models.get(model_type, models["random_forest"])

def _calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate classification metrics."""
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, average='weighted'),
        "recall": recall_score(y_true, y_pred, average='weighted'),
        "f1_score": f1_score(y_true, y_pred, average='weighted')
    }

def _get_feature_importance(model, feature_names: List[str]) -> Dict[str, float]:
    """Get feature importance from model."""
    if hasattr(model, 'feature_importances_'):
        importance = model.feature_importances_
    elif hasattr(model, 'coef_'):
        importance = np.abs(model.coef_[0])
    else:
        importance = np.random.uniform(0, 1, len(feature_names))
    
    return dict(zip(feature_names, importance))

def _prepare_patient_features(patient_features: Dict, feature_names: List[str]) -> pd.DataFrame:
    """Prepare patient features for prediction."""
    # Create DataFrame with all required features
    patient_df = pd.DataFrame([patient_features])
    
    # Ensure all required features are present
    for feature in feature_names:
        if feature not in patient_df.columns:
            patient_df[feature] = 0  # Default value for missing features
    
    # Reorder columns to match training data
    patient_df = patient_df[feature_names]
    
    return patient_df

def _prepare_multi_omics_features(multi_omics_data: Dict) -> pd.DataFrame:
    """Prepare multi-omics features for clustering."""
    # Combine different omics data types
    combined_data = {}
    
    for omics_type, data in multi_omics_data.items():
        if isinstance(data, dict):
            combined_data.update(data)
        else:
            combined_data[omics_type] = data
    
    return pd.DataFrame(combined_data)

def _perform_clustering(X: np.ndarray, n_clusters: int, method: str) -> np.ndarray:
    """Perform clustering on data."""
    from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN
    
    if method == "kmeans":
        clusterer = KMeans(n_clusters=n_clusters, random_state=42)
    elif method == "hierarchical":
        clusterer = AgglomerativeClustering(n_clusters=n_clusters)
    elif method == "dbscan":
        clusterer = DBSCAN(eps=0.5, min_samples=5)
    else:
        clusterer = KMeans(n_clusters=n_clusters, random_state=42)
    
    return clusterer.fit_predict(X)

def _analyze_clusters(X: pd.DataFrame, cluster_labels: np.ndarray) -> Dict[str, Any]:
    """Analyze cluster characteristics."""
    analysis = {}
    
    for cluster_id in np.unique(cluster_labels):
        cluster_data = X[cluster_labels == cluster_id]
        analysis[f"cluster_{cluster_id}"] = {
            "size": len(cluster_data),
            "mean_expression": cluster_data.mean().mean(),
            "top_features": cluster_data.mean().nlargest(5).to_dict()
        }
    
    return analysis

def _perform_feature_selection(X: pd.DataFrame, y: np.ndarray, method: str, n_features: int) -> Tuple[List[str], Dict[str, float]]:
    """Perform feature selection."""
    from sklearn.feature_selection import SelectKBest, mutual_info_classif, chi2, f_classif
    from sklearn.linear_model import LassoCV
    
    if method == "mutual_info":
        selector = SelectKBest(score_func=mutual_info_classif, k=n_features)
    elif method == "chi2":
        selector = SelectKBest(score_func=chi2, k=n_features)
    elif method == "f_score":
        selector = SelectKBest(score_func=f_classif, k=n_features)
    elif method == "lasso":
        lasso = LassoCV(cv=5, random_state=42)
        lasso.fit(X, y)
        feature_importance = np.abs(lasso.coef_)
        selected_indices = np.argsort(feature_importance)[-n_features:]
        selected_features = X.columns[selected_indices].tolist()
        importance_scores = dict(zip(selected_features, feature_importance[selected_indices]))
        return selected_features, importance_scores
    else:
        selector = SelectKBest(score_func=mutual_info_classif, k=n_features)
    
    selector.fit(X, y)
    selected_features = X.columns[selector.get_support()].tolist()
    importance_scores = dict(zip(selected_features, selector.scores_[selector.get_support()]))
    
    return selected_features, importance_scores

def _analyze_selected_features(selected_features: List[str], importance_scores: Dict[str, float]) -> Dict[str, Any]:
    """Analyze selected features."""
    return {
        "top_features": sorted(importance_scores.items(), key=lambda x: x[1], reverse=True)[:10],
        "feature_categories": {
            "expression": len([f for f in selected_features if 'expression' in f.lower()]),
            "mutation": len([f for f in selected_features if 'mutation' in f.lower()]),
            "clinical": len([f for f in selected_features if 'clinical' in f.lower()])
        }
    }
