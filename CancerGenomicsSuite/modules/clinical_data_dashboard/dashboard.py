"""
Clinical Data Dashboard Module

This module provides comprehensive functionality for analyzing and visualizing
clinical data in cancer genomics research.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import seaborn as sns
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional, Any, Union
import json
import logging
from pathlib import Path
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.linear_model import LogisticRegression, CoxPHRegressor
from lifelines import KaplanMeierFitter, CoxPHFitter
from lifelines.statistics import logrank_test
import scipy.stats as stats
from scipy.stats import chi2_contingency, fisher_exact
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClinicalDataAnalyzer:
    """
    A comprehensive class for analyzing clinical data in cancer genomics.
    """
    
    def __init__(self):
        """Initialize the clinical data analyzer."""
        self.clinical_data = None
        self.survival_data = None
        self.feature_importance = {}
        self.analysis_results = {}
        self.encoders = {}
        self.scalers = {}
        
    def load_clinical_data(self, file_path: str, 
                          patient_id_col: str = 'patient_id') -> pd.DataFrame:
        """
        Load clinical data from various file formats.
        
        Args:
            file_path: Path to the clinical data file
            patient_id_col: Column name containing patient IDs
            
        Returns:
            DataFrame containing the clinical data
        """
        try:
            # Load data based on file extension
            if file_path.endswith('.csv'):
                data = pd.read_csv(file_path)
            elif file_path.endswith('.tsv'):
                data = pd.read_csv(file_path, sep='\t')
            elif file_path.endswith('.xlsx'):
                data = pd.read_excel(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_path}")
            
            # Set patient ID as index if specified
            if patient_id_col in data.columns:
                data = data.set_index(patient_id_col)
            
            self.clinical_data = data
            
            logger.info(f"Loaded clinical data: {data.shape[0]} patients, {data.shape[1]} features")
            return data
            
        except Exception as e:
            logger.error(f"Error loading clinical data: {e}")
            raise
    
    def load_survival_data(self, file_path: str,
                          patient_id_col: str = 'patient_id',
                          time_col: str = 'survival_time',
                          event_col: str = 'death') -> pd.DataFrame:
        """
        Load survival data.
        
        Args:
            file_path: Path to the survival data file
            patient_id_col: Column name containing patient IDs
            time_col: Column name containing survival time
            event_col: Column name containing event indicator
            
        Returns:
            DataFrame containing survival data
        """
        try:
            if file_path.endswith('.csv'):
                data = pd.read_csv(file_path)
            elif file_path.endswith('.tsv'):
                data = pd.read_csv(file_path, sep='\t')
            elif file_path.endswith('.xlsx'):
                data = pd.read_excel(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_path}")
            
            # Set patient ID as index
            if patient_id_col in data.columns:
                data = data.set_index(patient_id_col)
            
            # Validate required columns
            if time_col not in data.columns:
                raise ValueError(f"Time column '{time_col}' not found")
            if event_col not in data.columns:
                raise ValueError(f"Event column '{event_col}' not found")
            
            self.survival_data = data
            
            logger.info(f"Loaded survival data: {data.shape[0]} patients")
            return data
            
        except Exception as e:
            logger.error(f"Error loading survival data: {e}")
            raise
    
    def preprocess_clinical_data(self, 
                               categorical_cols: List[str] = None,
                               numerical_cols: List[str] = None,
                               handle_missing: str = 'drop') -> pd.DataFrame:
        """
        Preprocess clinical data for analysis.
        
        Args:
            categorical_cols: List of categorical column names
            numerical_cols: List of numerical column names
            handle_missing: Strategy for handling missing values ('drop', 'fill', 'impute')
            
        Returns:
            Preprocessed DataFrame
        """
        if self.clinical_data is None:
            raise ValueError("No clinical data loaded")
        
        data = self.clinical_data.copy()
        
        try:
            # Auto-detect column types if not specified
            if categorical_cols is None:
                categorical_cols = data.select_dtypes(include=['object', 'category']).columns.tolist()
            
            if numerical_cols is None:
                numerical_cols = data.select_dtypes(include=[np.number]).columns.tolist()
            
            # Handle missing values
            if handle_missing == 'drop':
                data = data.dropna()
            elif handle_missing == 'fill':
                # Fill categorical with mode, numerical with median
                for col in categorical_cols:
                    if col in data.columns:
                        data[col] = data[col].fillna(data[col].mode()[0] if not data[col].mode().empty else 'Unknown')
                
                for col in numerical_cols:
                    if col in data.columns:
                        data[col] = data[col].fillna(data[col].median())
            
            # Encode categorical variables
            for col in categorical_cols:
                if col in data.columns:
                    if col not in self.encoders:
                        self.encoders[col] = LabelEncoder()
                        data[col] = self.encoders[col].fit_transform(data[col].astype(str))
                    else:
                        data[col] = self.encoders[col].transform(data[col].astype(str))
            
            # Scale numerical variables
            for col in numerical_cols:
                if col in data.columns:
                    if col not in self.scalers:
                        self.scalers[col] = StandardScaler()
                        data[col] = self.scalers[col].fit_transform(data[[col]]).flatten()
                    else:
                        data[col] = self.scalers[col].transform(data[[col]]).flatten()
            
            self.clinical_data = data
            
            logger.info(f"Preprocessed clinical data: {data.shape[0]} patients, {data.shape[1]} features")
            return data
            
        except Exception as e:
            logger.error(f"Error preprocessing clinical data: {e}")
            raise
    
    def perform_survival_analysis(self, 
                                 time_col: str = 'survival_time',
                                 event_col: str = 'death',
                                 group_col: str = None) -> Dict[str, Any]:
        """
        Perform survival analysis using Kaplan-Meier and Cox regression.
        
        Args:
            time_col: Column name containing survival time
            event_col: Column name containing event indicator
            group_col: Column name for grouping (optional)
            
        Returns:
            Dictionary containing survival analysis results
        """
        if self.survival_data is None:
            raise ValueError("No survival data loaded")
        
        try:
            results = {}
            
            # Kaplan-Meier analysis
            kmf = KaplanMeierFitter()
            
            if group_col and group_col in self.survival_data.columns:
                # Grouped survival analysis
                groups = self.survival_data[group_col].unique()
                km_results = {}
                
                for group in groups:
                    group_data = self.survival_data[self.survival_data[group_col] == group]
                    kmf.fit(group_data[time_col], group_data[event_col], label=f'Group {group}')
                    km_results[f'group_{group}'] = {
                        'survival_function': kmf.survival_function_,
                        'median_survival': kmf.median_survival_time_,
                        'confidence_interval': kmf.confidence_interval_survival_function_
                    }
                
                # Log-rank test
                if len(groups) == 2:
                    group1_data = self.survival_data[self.survival_data[group_col] == groups[0]]
                    group2_data = self.survival_data[self.survival_data[group_col] == groups[1]]
                    
                    logrank_result = logrank_test(
                        group1_data[time_col], group2_data[time_col],
                        group1_data[event_col], group2_data[event_col]
                    )
                    
                    results['logrank_test'] = {
                        'p_value': logrank_result.p_value,
                        'test_statistic': logrank_result.test_statistic
                    }
                
                results['kaplan_meier'] = km_results
                
            else:
                # Overall survival analysis
                kmf.fit(self.survival_data[time_col], self.survival_data[event_col])
                results['kaplan_meier'] = {
                    'overall': {
                        'survival_function': kmf.survival_function_,
                        'median_survival': kmf.median_survival_time_,
                        'confidence_interval': kmf.confidence_interval_survival_function_
                    }
                }
            
            # Cox proportional hazards regression
            if self.clinical_data is not None:
                # Merge clinical and survival data
                merged_data = pd.merge(
                    self.survival_data[[time_col, event_col]], 
                    self.clinical_data, 
                    left_index=True, 
                    right_index=True, 
                    how='inner'
                )
                
                # Prepare data for Cox regression
                cox_data = merged_data.copy()
                cox_data = cox_data.dropna()
                
                if len(cox_data) > 0:
                    # Select features for Cox regression
                    feature_cols = [col for col in cox_data.columns 
                                  if col not in [time_col, event_col]]
                    
                    if feature_cols:
                        cph = CoxPHFitter()
                        cph.fit(cox_data, duration_col=time_col, event_col=event_col)
                        
                        results['cox_regression'] = {
                            'summary': cph.summary,
                            'concordance_index': cph.concordance_index_,
                            'hazard_ratios': cph.hazard_ratios_
                        }
            
            self.analysis_results['survival'] = results
            
            logger.info("Completed survival analysis")
            return results
            
        except Exception as e:
            logger.error(f"Error in survival analysis: {e}")
            raise
    
    def perform_clinical_correlations(self, 
                                    target_col: str = None,
                                    method: str = 'pearson') -> Dict[str, Any]:
        """
        Perform correlation analysis on clinical variables.
        
        Args:
            target_col: Target column for correlation analysis
            method: Correlation method ('pearson', 'spearman', 'kendall')
            
        Returns:
            Dictionary containing correlation results
        """
        if self.clinical_data is None:
            raise ValueError("No clinical data loaded")
        
        try:
            data = self.clinical_data.select_dtypes(include=[np.number])
            
            if data.empty:
                return {"error": "No numerical data available for correlation analysis"}
            
            results = {}
            
            if target_col and target_col in data.columns:
                # Correlation with specific target
                correlations = data.corrwith(data[target_col], method=method).sort_values(
                    key=abs, ascending=False
                )
                
                results['target_correlations'] = {
                    'target': target_col,
                    'correlations': correlations.to_dict(),
                    'top_positive': correlations.head(10).to_dict(),
                    'top_negative': correlations.tail(10).to_dict()
                }
            else:
                # Full correlation matrix
                corr_matrix = data.corr(method=method)
                results['correlation_matrix'] = corr_matrix.to_dict()
                
                # Find highly correlated pairs
                high_corr_pairs = []
                for i in range(len(corr_matrix.columns)):
                    for j in range(i+1, len(corr_matrix.columns)):
                        corr_val = corr_matrix.iloc[i, j]
                        if abs(corr_val) > 0.7:  # High correlation threshold
                            high_corr_pairs.append({
                                'var1': corr_matrix.columns[i],
                                'var2': corr_matrix.columns[j],
                                'correlation': corr_val
                            })
                
                results['high_correlations'] = high_corr_pairs
            
            self.analysis_results['correlations'] = results
            
            logger.info("Completed correlation analysis")
            return results
            
        except Exception as e:
            logger.error(f"Error in correlation analysis: {e}")
            raise
    
    def perform_clinical_associations(self, 
                                    categorical_cols: List[str] = None,
                                    numerical_cols: List[str] = None) -> Dict[str, Any]:
        """
        Perform association tests between clinical variables.
        
        Args:
            categorical_cols: List of categorical columns
            numerical_cols: List of numerical columns
            
        Returns:
            Dictionary containing association test results
        """
        if self.clinical_data is None:
            raise ValueError("No clinical data loaded")
        
        try:
            data = self.clinical_data.copy()
            
            # Auto-detect column types
            if categorical_cols is None:
                categorical_cols = data.select_dtypes(include=['object', 'category']).columns.tolist()
            
            if numerical_cols is None:
                numerical_cols = data.select_dtypes(include=[np.number]).columns.tolist()
            
            results = {}
            
            # Categorical vs Categorical associations
            if len(categorical_cols) >= 2:
                cat_associations = []
                for i, col1 in enumerate(categorical_cols):
                    for col2 in categorical_cols[i+1:]:
                        if col1 in data.columns and col2 in data.columns:
                            contingency_table = pd.crosstab(data[col1], data[col2])
                            
                            # Chi-square test
                            chi2, p_value, dof, expected = chi2_contingency(contingency_table)
                            
                            # Cramer's V
                            n = contingency_table.sum().sum()
                            cramers_v = np.sqrt(chi2 / (n * (min(contingency_table.shape) - 1)))
                            
                            cat_associations.append({
                                'var1': col1,
                                'var2': col2,
                                'chi2_statistic': chi2,
                                'p_value': p_value,
                                'cramers_v': cramers_v,
                                'contingency_table': contingency_table.to_dict()
                            })
                
                results['categorical_associations'] = cat_associations
            
            # Numerical vs Categorical associations
            if numerical_cols and categorical_cols:
                num_cat_associations = []
                for num_col in numerical_cols:
                    for cat_col in categorical_cols:
                        if num_col in data.columns and cat_col in data.columns:
                            # ANOVA test
                            groups = [group[num_col].dropna() for name, group in data.groupby(cat_col)]
                            if len(groups) >= 2 and all(len(group) > 0 for group in groups):
                                f_stat, p_value = stats.f_oneway(*groups)
                                
                                num_cat_associations.append({
                                    'numerical_var': num_col,
                                    'categorical_var': cat_col,
                                    'f_statistic': f_stat,
                                    'p_value': p_value,
                                    'group_means': data.groupby(cat_col)[num_col].mean().to_dict()
                                })
                
                results['numerical_categorical_associations'] = num_cat_associations
            
            # Numerical vs Numerical associations
            if len(numerical_cols) >= 2:
                num_associations = []
                for i, col1 in enumerate(numerical_cols):
                    for col2 in numerical_cols[i+1:]:
                        if col1 in data.columns and col2 in data.columns:
                            # Pearson correlation
                            corr, p_value = stats.pearsonr(data[col1].dropna(), data[col2].dropna())
                            
                            num_associations.append({
                                'var1': col1,
                                'var2': col2,
                                'correlation': corr,
                                'p_value': p_value
                            })
                
                results['numerical_associations'] = num_associations
            
            self.analysis_results['associations'] = results
            
            logger.info("Completed association analysis")
            return results
            
        except Exception as e:
            logger.error(f"Error in association analysis: {e}")
            raise
    
    def build_predictive_model(self, 
                              target_col: str,
                              model_type: str = 'classification',
                              test_size: float = 0.2) -> Dict[str, Any]:
        """
        Build predictive models for clinical outcomes.
        
        Args:
            target_col: Target column for prediction
            model_type: Type of model ('classification', 'regression')
            test_size: Proportion of data for testing
            
        Returns:
            Dictionary containing model results
        """
        if self.clinical_data is None:
            raise ValueError("No clinical data loaded")
        
        if target_col not in self.clinical_data.columns:
            raise ValueError(f"Target column '{target_col}' not found")
        
        try:
            # Prepare data
            X = self.clinical_data.drop(columns=[target_col])
            y = self.clinical_data[target_col]
            
            # Remove non-numerical columns
            X = X.select_dtypes(include=[np.number])
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42, stratify=y if model_type == 'classification' else None
            )
            
            # Build model
            if model_type == 'classification':
                model = RandomForestClassifier(n_estimators=100, random_state=42)
            else:
                model = RandomForestRegressor(n_estimators=100, random_state=42)
            
            # Train model
            model.fit(X_train, y_train)
            
            # Make predictions
            y_pred = model.predict(X_test)
            y_pred_proba = model.predict_proba(X_test) if model_type == 'classification' else None
            
            # Calculate metrics
            if model_type == 'classification':
                # Classification metrics
                accuracy = model.score(X_test, y_test)
                auc_score = roc_auc_score(y_test, y_pred_proba[:, 1]) if y_pred_proba is not None else None
                
                # Cross-validation
                cv_scores = cross_val_score(model, X, y, cv=5, scoring='accuracy')
                
                results = {
                    'model_type': 'classification',
                    'accuracy': accuracy,
                    'auc_score': auc_score,
                    'cv_scores': cv_scores.tolist(),
                    'cv_mean': cv_scores.mean(),
                    'cv_std': cv_scores.std(),
                    'classification_report': classification_report(y_test, y_pred, output_dict=True),
                    'confusion_matrix': confusion_matrix(y_test, y_pred).tolist()
                }
            else:
                # Regression metrics
                mse = np.mean((y_test - y_pred) ** 2)
                r2_score = model.score(X_test, y_test)
                
                # Cross-validation
                cv_scores = cross_val_score(model, X, y, cv=5, scoring='r2')
                
                results = {
                    'model_type': 'regression',
                    'mse': mse,
                    'r2_score': r2_score,
                    'cv_scores': cv_scores.tolist(),
                    'cv_mean': cv_scores.mean(),
                    'cv_std': cv_scores.std()
                }
            
            # Feature importance
            feature_importance = pd.DataFrame({
                'feature': X.columns,
                'importance': model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            results['feature_importance'] = feature_importance.to_dict('records')
            self.feature_importance[target_col] = feature_importance
            
            self.analysis_results['predictive_model'] = results
            
            logger.info(f"Built {model_type} model for {target_col}")
            return results
            
        except Exception as e:
            logger.error(f"Error building predictive model: {e}")
            raise
    
    def create_survival_plot(self, 
                           time_col: str = 'survival_time',
                           event_col: str = 'death',
                           group_col: str = None) -> go.Figure:
        """
        Create Kaplan-Meier survival plot.
        
        Args:
            time_col: Column name containing survival time
            event_col: Column name containing event indicator
            group_col: Column name for grouping (optional)
            
        Returns:
            Plotly figure object
        """
        if self.survival_data is None:
            raise ValueError("No survival data loaded")
        
        try:
            fig = go.Figure()
            
            if group_col and group_col in self.survival_data.columns:
                # Grouped survival curves
                groups = self.survival_data[group_col].unique()
                colors = px.colors.qualitative.Set1
                
                for i, group in enumerate(groups):
                    group_data = self.survival_data[self.survival_data[group_col] == group]
                    
                    kmf = KaplanMeierFitter()
                    kmf.fit(group_data[time_col], group_data[event_col])
                    
                    fig.add_trace(go.Scatter(
                        x=kmf.survival_function_.index,
                        y=kmf.survival_function_[group],
                        mode='lines',
                        name=f'Group {group}',
                        line=dict(color=colors[i % len(colors)], width=3),
                        hovertemplate=f'<b>Group {group}</b><br>' +
                                    'Time: %{x}<br>' +
                                    'Survival: %{y:.3f}<extra></extra>'
                    ))
                    
                    # Add confidence intervals
                    ci = kmf.confidence_interval_survival_function_
                    fig.add_trace(go.Scatter(
                        x=ci.index,
                        y=ci[group],
                        mode='lines',
                        line=dict(width=0),
                        showlegend=False,
                        hoverinfo='skip'
                    ))
                    
                    fig.add_trace(go.Scatter(
                        x=ci.index,
                        y=ci[group],
                        mode='lines',
                        line=dict(width=0),
                        fill='tonexty',
                        fillcolor=f'rgba({colors[i % len(colors)].replace("#", "")}, 0.2)',
                        showlegend=False,
                        hoverinfo='skip'
                    ))
            else:
                # Overall survival curve
                kmf = KaplanMeierFitter()
                kmf.fit(self.survival_data[time_col], self.survival_data[event_col])
                
                fig.add_trace(go.Scatter(
                    x=kmf.survival_function_.index,
                    y=kmf.survival_function_['KM_estimate'],
                    mode='lines',
                    name='Overall Survival',
                    line=dict(color='blue', width=3),
                    hovertemplate='<b>Overall Survival</b><br>' +
                                'Time: %{x}<br>' +
                                'Survival: %{y:.3f}<extra></extra>'
                ))
            
            fig.update_layout(
                title='Kaplan-Meier Survival Curves',
                xaxis_title='Time',
                yaxis_title='Survival Probability',
                width=800,
                height=600,
                hovermode='x unified'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating survival plot: {e}")
            raise
    
    def create_correlation_heatmap(self, 
                                 method: str = 'pearson') -> go.Figure:
        """
        Create correlation heatmap for clinical variables.
        
        Args:
            method: Correlation method ('pearson', 'spearman', 'kendall')
            
        Returns:
            Plotly heatmap figure
        """
        if self.clinical_data is None:
            raise ValueError("No clinical data loaded")
        
        try:
            # Select numerical columns
            data = self.clinical_data.select_dtypes(include=[np.number])
            
            if data.empty:
                return go.Figure()
            
            # Calculate correlation matrix
            corr_matrix = data.corr(method=method)
            
            # Create heatmap
            fig = go.Figure(data=go.Heatmap(
                z=corr_matrix.values,
                x=corr_matrix.columns,
                y=corr_matrix.columns,
                colorscale='RdBu',
                zmid=0,
                text=np.round(corr_matrix.values, 3),
                texttemplate="%{text}",
                textfont={"size": 10},
                hoverongaps=False
            ))
            
            fig.update_layout(
                title=f'Clinical Variables Correlation Matrix ({method.title()})',
                width=800,
                height=800
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating correlation heatmap: {e}")
            raise
    
    def create_clinical_overview_plot(self) -> go.Figure:
        """
        Create overview plot of clinical data distribution.
        
        Returns:
            Plotly figure with subplots
        """
        if self.clinical_data is None:
            raise ValueError("No clinical data loaded")
        
        try:
            # Get column types
            categorical_cols = self.clinical_data.select_dtypes(include=['object', 'category']).columns
            numerical_cols = self.clinical_data.select_dtypes(include=[np.number]).columns
            
            # Create subplots
            n_cat = len(categorical_cols)
            n_num = len(numerical_cols)
            
            if n_cat == 0 and n_num == 0:
                return go.Figure()
            
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=['Categorical Variables', 'Numerical Variables', 
                              'Missing Data', 'Data Summary'],
                specs=[[{"type": "bar"}, {"type": "histogram"}],
                       [{"type": "bar"}, {"type": "table"}]]
            )
            
            # Categorical variables distribution
            if n_cat > 0:
                cat_counts = [self.clinical_data[col].nunique() for col in categorical_cols]
                fig.add_trace(
                    go.Bar(x=list(categorical_cols), y=cat_counts, name='Unique Values'),
                    row=1, col=1
                )
            
            # Numerical variables distribution
            if n_num > 0:
                # Sample from first numerical column
                sample_col = numerical_cols[0]
                sample_data = self.clinical_data[sample_col].dropna()
                fig.add_trace(
                    go.Histogram(x=sample_data, name=f'{sample_col} Distribution', nbinsx=30),
                    row=1, col=2
                )
            
            # Missing data
            missing_counts = self.clinical_data.isnull().sum()
            missing_pct = (missing_counts / len(self.clinical_data)) * 100
            
            fig.add_trace(
                go.Bar(x=list(missing_counts.index), y=missing_pct, name='Missing %'),
                row=2, col=1
            )
            
            # Data summary table
            summary_data = [
                ['Total Patients', len(self.clinical_data)],
                ['Total Features', len(self.clinical_data.columns)],
                ['Categorical Features', len(categorical_cols)],
                ['Numerical Features', len(numerical_cols)],
                ['Missing Values', self.clinical_data.isnull().sum().sum()]
            ]
            
            fig.add_trace(
                go.Table(
                    header=dict(values=['Metric', 'Value']),
                    cells=dict(values=list(zip(*summary_data)))
                ),
                row=2, col=2
            )
            
            fig.update_layout(
                title='Clinical Data Overview',
                height=600,
                showlegend=False
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating overview plot: {e}")
            raise
    
    def export_analysis_results(self, output_path: str) -> None:
        """
        Export analysis results to JSON file.
        
        Args:
            output_path: Path to save the results
        """
        try:
            # Prepare results for export
            export_data = {
                'analysis_results': self.analysis_results,
                'feature_importance': {k: v.to_dict('records') for k, v in self.feature_importance.items()},
                'data_summary': {
                    'clinical_data_shape': self.clinical_data.shape if self.clinical_data is not None else None,
                    'survival_data_shape': self.survival_data.shape if self.survival_data is not None else None,
                    'categorical_columns': list(self.clinical_data.select_dtypes(include=['object', 'category']).columns) if self.clinical_data is not None else [],
                    'numerical_columns': list(self.clinical_data.select_dtypes(include=[np.number]).columns) if self.clinical_data is not None else []
                }
            }
            
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Exported analysis results to {output_path}")
            
        except Exception as e:
            logger.error(f"Error exporting results: {e}")
            raise
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the analysis results.
        
        Returns:
            Dictionary containing analysis summary
        """
        summary = {
            'has_clinical_data': self.clinical_data is not None,
            'has_survival_data': self.survival_data is not None,
            'analyses_performed': list(self.analysis_results.keys()),
            'feature_importance_available': list(self.feature_importance.keys())
        }
        
        if self.clinical_data is not None:
            summary['clinical_data'] = {
                'n_patients': len(self.clinical_data),
                'n_features': len(self.clinical_data.columns),
                'categorical_features': len(self.clinical_data.select_dtypes(include=['object', 'category']).columns),
                'numerical_features': len(self.clinical_data.select_dtypes(include=[np.number]).columns)
            }
        
        if self.survival_data is not None:
            summary['survival_data'] = {
                'n_patients': len(self.survival_data),
                'n_features': len(self.survival_data.columns)
            }
        
        return summary


def create_mock_clinical_data() -> pd.DataFrame:
    """
    Create mock clinical data for testing and demonstration.
    
    Returns:
        DataFrame containing mock clinical data
    """
    np.random.seed(42)
    n_patients = 200
    
    # Patient IDs
    patient_ids = [f'Patient_{i:03d}' for i in range(n_patients)]
    
    # Generate mock clinical data
    data = {
        'patient_id': patient_ids,
        'age': np.random.normal(65, 15, n_patients).astype(int),
        'gender': np.random.choice(['Male', 'Female'], n_patients),
        'stage': np.random.choice(['I', 'II', 'III', 'IV'], n_patients, p=[0.3, 0.3, 0.25, 0.15]),
        'grade': np.random.choice(['Low', 'Intermediate', 'High'], n_patients, p=[0.4, 0.4, 0.2]),
        'tumor_size': np.random.lognormal(2, 0.5, n_patients),
        'lymph_nodes': np.random.poisson(2, n_patients),
        'ki67': np.random.beta(2, 5, n_patients) * 100,
        'er_status': np.random.choice(['Positive', 'Negative'], n_patients, p=[0.7, 0.3]),
        'pr_status': np.random.choice(['Positive', 'Negative'], n_patients, p=[0.6, 0.4]),
        'her2_status': np.random.choice(['Positive', 'Negative'], n_patients, p=[0.2, 0.8]),
        'treatment': np.random.choice(['Chemotherapy', 'Radiation', 'Surgery', 'Combined'], n_patients),
        'response': np.random.choice(['Complete', 'Partial', 'Stable', 'Progressive'], n_patients, p=[0.3, 0.3, 0.2, 0.2])
    }
    
    return pd.DataFrame(data).set_index('patient_id')


def create_mock_survival_data() -> pd.DataFrame:
    """
    Create mock survival data for testing and demonstration.
    
    Returns:
        DataFrame containing mock survival data
    """
    np.random.seed(42)
    n_patients = 200
    
    # Patient IDs
    patient_ids = [f'Patient_{i:03d}' for i in range(n_patients)]
    
    # Generate survival times (exponential distribution)
    survival_times = np.random.exponential(24, n_patients)  # Mean 24 months
    
    # Generate death events (censoring)
    death_events = np.random.binomial(1, 0.6, n_patients)  # 60% death rate
    
    # Add some censoring
    censoring_times = np.random.uniform(12, 60, n_patients)
    censored = survival_times > censoring_times
    survival_times[censored] = censoring_times[censored]
    death_events[censored] = 0
    
    data = {
        'patient_id': patient_ids,
        'survival_time': survival_times,
        'death': death_events,
        'risk_group': np.random.choice(['Low', 'High'], n_patients, p=[0.6, 0.4])
    }
    
    return pd.DataFrame(data).set_index('patient_id')


def main():
    """Main function for testing the clinical data analyzer."""
    # Create analyzer instance
    analyzer = ClinicalDataAnalyzer()
    
    # Create mock data
    clinical_data = create_mock_clinical_data()
    survival_data = create_mock_survival_data()
    
    # Load data
    analyzer.clinical_data = clinical_data
    analyzer.survival_data = survival_data
    
    # Preprocess data
    analyzer.preprocess_clinical_data()
    
    # Perform analyses
    survival_results = analyzer.perform_survival_analysis(group_col='risk_group')
    correlation_results = analyzer.perform_clinical_correlations()
    association_results = analyzer.perform_clinical_associations()
    
    # Build predictive model
    model_results = analyzer.build_predictive_model('response', model_type='classification')
    
    # Get summary
    summary = analyzer.get_analysis_summary()
    print("Analysis Summary:")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
