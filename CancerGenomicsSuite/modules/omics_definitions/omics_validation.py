"""
Omics Data Validation and Quality Control

This module provides comprehensive validation and quality control for all omics data types,
including data format validation, quality metrics calculation, and automated quality control.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
import logging
from dataclasses import dataclass, field
from pathlib import Path
import json
import warnings
warnings.filterwarnings('ignore')

from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from scipy import stats
from scipy.stats import normaltest, shapiro
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from .omics_registry import OmicsFieldRegistry, OmicsFieldDefinition, OmicsDataType
from .omics_metadata import OmicsMetadataManager

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of data validation."""
    is_valid: bool
    validation_score: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    quality_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class QualityControlResult:
    """Result of quality control analysis."""
    passed_qc: bool
    qc_score: float
    quality_metrics: Dict[str, float] = field(default_factory=dict)
    failed_samples: List[str] = field(default_factory=list)
    failed_features: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    plots: Dict[str, go.Figure] = field(default_factory=dict)


class OmicsDataValidator:
    """Comprehensive validator for omics data."""
    
    def __init__(self, registry: OmicsFieldRegistry):
        """Initialize the validator."""
        self.registry = registry
        self.validation_rules = self._initialize_validation_rules()
    
    def _initialize_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize validation rules for different omics types."""
        return {
            'genomics': {
                'min_samples': 10,
                'min_features': 100,
                'max_missing_rate': 0.5,
                'required_columns': ['sample_id'],
                'data_types': ['numeric', 'categorical'],
                'value_ranges': {'coverage': (0, 1000), 'quality': (0, 100)}
            },
            'transcriptomics': {
                'min_samples': 5,
                'min_features': 50,
                'max_missing_rate': 0.3,
                'required_columns': ['sample_id'],
                'data_types': ['numeric'],
                'value_ranges': {'expression': (0, 1000000)}
            },
            'proteomics': {
                'min_samples': 5,
                'min_features': 20,
                'max_missing_rate': 0.4,
                'required_columns': ['sample_id'],
                'data_types': ['numeric'],
                'value_ranges': {'intensity': (0, 1000000)}
            },
            'metabolomics': {
                'min_samples': 5,
                'min_features': 10,
                'max_missing_rate': 0.5,
                'required_columns': ['sample_id'],
                'data_types': ['numeric'],
                'value_ranges': {'abundance': (0, 1000000)}
            },
            'epigenomics': {
                'min_samples': 5,
                'min_features': 1000,
                'max_missing_rate': 0.2,
                'required_columns': ['sample_id'],
                'data_types': ['numeric'],
                'value_ranges': {'beta_value': (0, 1), 'm_value': (-10, 10)}
            }
        }
    
    def validate_data(self, data: pd.DataFrame, omics_type: str, 
                     metadata: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Comprehensive validation of omics data."""
        try:
            errors = []
            warnings = []
            recommendations = []
            quality_metrics = {}
            
            # Get validation rules for omics type
            rules = self.validation_rules.get(omics_type, {})
            if not rules:
                errors.append(f"No validation rules defined for omics type: {omics_type}")
                return ValidationResult(False, 0.0, errors, warnings, recommendations, quality_metrics)
            
            # Basic structure validation
            structure_result = self._validate_data_structure(data, rules)
            errors.extend(structure_result['errors'])
            warnings.extend(structure_result['warnings'])
            recommendations.extend(structure_result['recommendations'])
            quality_metrics.update(structure_result['quality_metrics'])
            
            # Data type validation
            dtype_result = self._validate_data_types(data, rules)
            errors.extend(dtype_result['errors'])
            warnings.extend(dtype_result['warnings'])
            recommendations.extend(dtype_result['recommendations'])
            quality_metrics.update(dtype_result['quality_metrics'])
            
            # Value range validation
            range_result = self._validate_value_ranges(data, rules)
            errors.extend(range_result['errors'])
            warnings.extend(range_result['warnings'])
            recommendations.extend(range_result['recommendations'])
            quality_metrics.update(range_result['quality_metrics'])
            
            # Missing data validation
            missing_result = self._validate_missing_data(data, rules)
            errors.extend(missing_result['errors'])
            warnings.extend(missing_result['warnings'])
            recommendations.extend(missing_result['recommendations'])
            quality_metrics.update(missing_result['quality_metrics'])
            
            # Statistical validation
            stats_result = self._validate_statistical_properties(data, omics_type)
            errors.extend(stats_result['errors'])
            warnings.extend(stats_result['warnings'])
            recommendations.extend(stats_result['recommendations'])
            quality_metrics.update(stats_result['quality_metrics'])
            
            # Metadata validation
            if metadata:
                metadata_result = self._validate_metadata(metadata, omics_type)
                errors.extend(metadata_result['errors'])
                warnings.extend(metadata_result['warnings'])
                recommendations.extend(metadata_result['recommendations'])
                quality_metrics.update(metadata_result['quality_metrics'])
            
            # Calculate overall validation score
            validation_score = self._calculate_validation_score(errors, warnings, quality_metrics)
            
            # Determine if data is valid
            is_valid = len(errors) == 0 and validation_score >= 0.7
            
            return ValidationResult(
                is_valid=is_valid,
                validation_score=validation_score,
                errors=errors,
                warnings=warnings,
                recommendations=recommendations,
                quality_metrics=quality_metrics
            )
            
        except Exception as e:
            logger.error(f"Error in data validation: {e}")
            return ValidationResult(
                is_valid=False,
                validation_score=0.0,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                recommendations=[],
                quality_metrics={}
            )
    
    def _validate_data_structure(self, data: pd.DataFrame, rules: Dict[str, Any]) -> Dict[str, Any]:
        """Validate basic data structure."""
        result = {'errors': [], 'warnings': [], 'recommendations': [], 'quality_metrics': {}}
        
        # Check if data is empty
        if data.empty:
            result['errors'].append("Data is empty")
            return result
        
        # Check minimum samples
        min_samples = rules.get('min_samples', 1)
        if data.shape[1] < min_samples:
            result['errors'].append(f"Insufficient samples: {data.shape[1]} < {min_samples}")
        else:
            result['quality_metrics']['sample_count'] = data.shape[1]
        
        # Check minimum features
        min_features = rules.get('min_features', 1)
        if data.shape[0] < min_features:
            result['errors'].append(f"Insufficient features: {data.shape[0]} < {min_features}")
        else:
            result['quality_metrics']['feature_count'] = data.shape[0]
        
        # Check for required columns
        required_columns = rules.get('required_columns', [])
        for col in required_columns:
            if col not in data.columns:
                result['errors'].append(f"Missing required column: {col}")
        
        # Check for duplicate samples/features
        if data.columns.duplicated().any():
            result['warnings'].append("Duplicate sample names found")
            result['recommendations'].append("Remove or rename duplicate samples")
        
        if data.index.duplicated().any():
            result['warnings'].append("Duplicate feature names found")
            result['recommendations'].append("Remove or rename duplicate features")
        
        return result
    
    def _validate_data_types(self, data: pd.DataFrame, rules: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data types."""
        result = {'errors': [], 'warnings': [], 'recommendations': [], 'quality_metrics': {}}
        
        expected_types = rules.get('data_types', ['numeric'])
        
        # Check if data is numeric when expected
        if 'numeric' in expected_types:
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            non_numeric_cols = data.select_dtypes(exclude=[np.number]).columns
            
            if len(non_numeric_cols) > 0:
                result['warnings'].append(f"Non-numeric columns found: {list(non_numeric_cols)}")
                result['recommendations'].append("Convert non-numeric columns to numeric or remove them")
            
            result['quality_metrics']['numeric_ratio'] = len(numeric_cols) / len(data.columns)
        
        return result
    
    def _validate_value_ranges(self, data: pd.DataFrame, rules: Dict[str, Any]) -> Dict[str, Any]:
        """Validate value ranges."""
        result = {'errors': [], 'warnings': [], 'recommendations': [], 'quality_metrics': {}}
        
        value_ranges = rules.get('value_ranges', {})
        
        for metric, (min_val, max_val) in value_ranges.items():
            # This is a simplified check - in practice, you'd have more sophisticated range validation
            if data.select_dtypes(include=[np.number]).size > 0:
                data_min = data.select_dtypes(include=[np.number]).min().min()
                data_max = data.select_dtypes(include=[np.number]).max().max()
                
                if data_min < min_val or data_max > max_val:
                    result['warnings'].append(f"Values outside expected range for {metric}: [{data_min}, {data_max}] vs [{min_val}, {max_val}]")
                
                result['quality_metrics'][f'{metric}_range_compliance'] = 1.0 if min_val <= data_min <= data_max <= max_val else 0.5
        
        return result
    
    def _validate_missing_data(self, data: pd.DataFrame, rules: Dict[str, Any]) -> Dict[str, Any]:
        """Validate missing data patterns."""
        result = {'errors': [], 'warnings': [], 'recommendations': [], 'quality_metrics': {}}
        
        max_missing_rate = rules.get('max_missing_rate', 0.5)
        
        # Calculate missing data rates
        missing_rate = data.isnull().sum().sum() / data.size
        result['quality_metrics']['missing_rate'] = missing_rate
        
        if missing_rate > max_missing_rate:
            result['errors'].append(f"Too much missing data: {missing_rate:.2%} > {max_missing_rate:.2%}")
        elif missing_rate > max_missing_rate * 0.5:
            result['warnings'].append(f"High missing data rate: {missing_rate:.2%}")
            result['recommendations'].append("Consider imputation or removal of features/samples with high missing rates")
        
        # Check for systematic missing patterns
        missing_by_sample = data.isnull().sum(axis=0) / data.shape[0]
        missing_by_feature = data.isnull().sum(axis=1) / data.shape[1]
        
        if missing_by_sample.max() > 0.8:
            result['warnings'].append("Some samples have >80% missing data")
            result['recommendations'].append("Consider removing samples with high missing rates")
        
        if missing_by_feature.max() > 0.8:
            result['warnings'].append("Some features have >80% missing data")
            result['recommendations'].append("Consider removing features with high missing rates")
        
        return result
    
    def _validate_statistical_properties(self, data: pd.DataFrame, omics_type: str) -> Dict[str, Any]:
        """Validate statistical properties of the data."""
        result = {'errors': [], 'warnings': [], 'recommendations': [], 'quality_metrics': {}}
        
        numeric_data = data.select_dtypes(include=[np.number])
        if numeric_data.empty:
            return result
        
        # Check for constant features
        constant_features = (numeric_data.var(axis=1) == 0).sum()
        if constant_features > 0:
            result['warnings'].append(f"{constant_features} constant features found")
            result['recommendations'].append("Remove constant features before analysis")
        
        result['quality_metrics']['constant_features'] = constant_features
        
        # Check for normal distribution (for some omics types)
        if omics_type in ['transcriptomics', 'proteomics']:
            # Sample a few features for normality testing
            sample_features = numeric_data.sample(min(10, numeric_data.shape[0]), axis=0)
            normal_pvalues = []
            
            for feature in sample_features.index:
                values = sample_features.loc[feature].dropna()
                if len(values) > 3:
                    _, p_value = normaltest(values)
                    normal_pvalues.append(p_value)
            
            if normal_pvalues:
                mean_normal_p = np.mean(normal_pvalues)
                result['quality_metrics']['normality_pvalue'] = mean_normal_p
                
                if mean_normal_p < 0.05:
                    result['warnings'].append("Data may not be normally distributed")
                    result['recommendations'].append("Consider log transformation or non-parametric methods")
        
        # Check for outliers
        outlier_count = 0
        for feature in numeric_data.index:
            values = numeric_data.loc[feature].dropna()
            if len(values) > 4:
                Q1 = values.quantile(0.25)
                Q3 = values.quantile(0.75)
                IQR = Q3 - Q1
                outliers = ((values < (Q1 - 1.5 * IQR)) | (values > (Q3 + 1.5 * IQR))).sum()
                outlier_count += outliers
        
        result['quality_metrics']['outlier_count'] = outlier_count
        
        if outlier_count > numeric_data.size * 0.05:  # More than 5% outliers
            result['warnings'].append(f"High number of outliers detected: {outlier_count}")
            result['recommendations'].append("Consider outlier detection and treatment")
        
        return result
    
    def _validate_metadata(self, metadata: Dict[str, Any], omics_type: str) -> Dict[str, Any]:
        """Validate metadata."""
        result = {'errors': [], 'warnings': [], 'recommendations': [], 'quality_metrics': {}}
        
        # Check required metadata fields
        required_fields = ['samples', 'features', 'data_type']
        for field in required_fields:
            if field not in metadata:
                result['errors'].append(f"Missing required metadata field: {field}")
        
        # Validate data type consistency
        if 'data_type' in metadata and metadata['data_type'] != omics_type:
            result['errors'].append(f"Metadata data_type mismatch: {metadata['data_type']} vs {omics_type}")
        
        return result
    
    def _calculate_validation_score(self, errors: List[str], warnings: List[str], 
                                  quality_metrics: Dict[str, float]) -> float:
        """Calculate overall validation score."""
        base_score = 1.0
        
        # Deduct for errors
        error_penalty = len(errors) * 0.2
        base_score -= error_penalty
        
        # Deduct for warnings
        warning_penalty = len(warnings) * 0.05
        base_score -= warning_penalty
        
        # Add quality metric bonuses
        for metric, value in quality_metrics.items():
            if isinstance(value, (int, float)) and 0 <= value <= 1:
                base_score += value * 0.1
        
        return max(0.0, min(1.0, base_score))


class OmicsQualityControl:
    """Comprehensive quality control for omics data."""
    
    def __init__(self, registry: OmicsFieldRegistry):
        """Initialize the quality control system."""
        self.registry = registry
        self.qc_methods = self._initialize_qc_methods()
    
    def _initialize_qc_methods(self) -> Dict[str, List[str]]:
        """Initialize QC methods for different omics types."""
        return {
            'genomics': ['coverage_check', 'mapping_rate', 'duplicate_rate', 'gc_bias'],
            'transcriptomics': ['mapping_rate', 'duplicate_rate', 'strand_bias', 'gene_body_coverage'],
            'proteomics': ['missing_values', 'coefficient_variation', 'reproducibility', 'intensity_distribution'],
            'metabolomics': ['missing_values', 'rsd', 'batch_effects', 'intensity_distribution'],
            'epigenomics': ['detection_pvalue', 'bisulfite_conversion', 'dye_bias', 'beta_distribution']
        }
    
    def perform_quality_control(self, data: pd.DataFrame, omics_type: str,
                              metadata: Optional[Dict[str, Any]] = None) -> QualityControlResult:
        """Perform comprehensive quality control."""
        try:
            quality_metrics = {}
            failed_samples = []
            failed_features = []
            recommendations = []
            plots = {}
            
            # Get QC methods for omics type
            qc_methods = self.qc_methods.get(omics_type, [])
            
            # Perform standard QC checks
            for method in qc_methods:
                method_result = self._perform_qc_method(data, method, omics_type)
                quality_metrics.update(method_result['metrics'])
                failed_samples.extend(method_result['failed_samples'])
                failed_features.extend(method_result['failed_features'])
                recommendations.extend(method_result['recommendations'])
                if 'plot' in method_result:
                    plots[method] = method_result['plot']
            
            # Perform omics-specific QC
            omics_specific_result = self._perform_omics_specific_qc(data, omics_type)
            quality_metrics.update(omics_specific_result['metrics'])
            failed_samples.extend(omics_specific_result['failed_samples'])
            failed_features.extend(omics_specific_result['failed_features'])
            recommendations.extend(omics_specific_result['recommendations'])
            plots.update(omics_specific_result['plots'])
            
            # Calculate overall QC score
            qc_score = self._calculate_qc_score(quality_metrics)
            
            # Determine if QC passed
            passed_qc = qc_score >= 0.7 and len(failed_samples) == 0
            
            return QualityControlResult(
                passed_qc=passed_qc,
                qc_score=qc_score,
                quality_metrics=quality_metrics,
                failed_samples=failed_samples,
                failed_features=failed_features,
                recommendations=recommendations,
                plots=plots
            )
            
        except Exception as e:
            logger.error(f"Error in quality control: {e}")
            return QualityControlResult(
                passed_qc=False,
                qc_score=0.0,
                quality_metrics={},
                failed_samples=[],
                failed_features=[],
                recommendations=[f"QC error: {str(e)}"],
                plots={}
            )
    
    def _perform_qc_method(self, data: pd.DataFrame, method: str, omics_type: str) -> Dict[str, Any]:
        """Perform a specific QC method."""
        result = {
            'metrics': {},
            'failed_samples': [],
            'failed_features': [],
            'recommendations': [],
            'plot': None
        }
        
        if method == 'missing_values':
            missing_rate = data.isnull().sum().sum() / data.size
            result['metrics']['missing_rate'] = missing_rate
            
            if missing_rate > 0.3:
                result['recommendations'].append("High missing value rate detected")
        
        elif method == 'coefficient_variation':
            cv_values = data.std(axis=1) / data.mean(axis=1)
            high_cv_features = cv_values[cv_values > 0.5].index.tolist()
            result['metrics']['high_cv_features'] = len(high_cv_features)
            result['failed_features'].extend(high_cv_features)
            
            if high_cv_features:
                result['recommendations'].append("Features with high coefficient of variation detected")
        
        elif method == 'reproducibility':
            # Calculate correlation between replicates (simplified)
            correlations = data.T.corr()
            mean_correlation = correlations.values[np.triu_indices_from(correlations.values, k=1)].mean()
            result['metrics']['mean_correlation'] = mean_correlation
            
            if mean_correlation < 0.8:
                result['recommendations'].append("Low reproducibility detected")
        
        elif method == 'intensity_distribution':
            # Create intensity distribution plot
            fig = go.Figure()
            for i, sample in enumerate(data.columns[:5]):  # Show first 5 samples
                values = data[sample].dropna()
                fig.add_trace(go.Histogram(x=values, name=sample, opacity=0.7))
            
            fig.update_layout(
                title="Intensity Distribution",
                xaxis_title="Intensity",
                yaxis_title="Count"
            )
            result['plot'] = fig
        
        return result
    
    def _perform_omics_specific_qc(self, data: pd.DataFrame, omics_type: str) -> Dict[str, Any]:
        """Perform omics-specific quality control."""
        result = {
            'metrics': {},
            'failed_samples': [],
            'failed_features': [],
            'recommendations': [],
            'plots': {}
        }
        
        if omics_type == 'genomics':
            # Coverage check
            if 'coverage' in data.index or data.values.min() >= 0:
                mean_coverage = data.mean().mean()
                result['metrics']['mean_coverage'] = mean_coverage
                
                if mean_coverage < 10:
                    result['recommendations'].append("Low mean coverage detected")
        
        elif omics_type == 'transcriptomics':
            # Gene expression distribution
            fig = go.Figure()
            sample_means = data.mean(axis=0)
            fig.add_trace(go.Histogram(x=sample_means, name="Sample Means"))
            fig.update_layout(
                title="Gene Expression Distribution",
                xaxis_title="Mean Expression",
                yaxis_title="Count"
            )
            result['plots']['expression_distribution'] = fig
        
        elif omics_type == 'proteomics':
            # Protein abundance check
            low_abundance_features = data[data.mean(axis=1) < data.mean().mean() * 0.1].index.tolist()
            result['metrics']['low_abundance_features'] = len(low_abundance_features)
            result['failed_features'].extend(low_abundance_features)
        
        elif omics_type == 'metabolomics':
            # Metabolite abundance distribution
            fig = go.Figure()
            feature_means = data.mean(axis=1)
            fig.add_trace(go.Histogram(x=feature_means, name="Feature Means"))
            fig.update_layout(
                title="Metabolite Abundance Distribution",
                xaxis_title="Mean Abundance",
                yaxis_title="Count"
            )
            result['plots']['abundance_distribution'] = fig
        
        elif omics_type == 'epigenomics':
            # Beta value distribution
            if data.values.min() >= 0 and data.values.max() <= 1:
                fig = go.Figure()
                sample_means = data.mean(axis=0)
                fig.add_trace(go.Histogram(x=sample_means, name="Sample Means"))
                fig.update_layout(
                    title="Beta Value Distribution",
                    xaxis_title="Mean Beta Value",
                    yaxis_title="Count"
                )
                result['plots']['beta_distribution'] = fig
        
        return result
    
    def _calculate_qc_score(self, quality_metrics: Dict[str, float]) -> float:
        """Calculate overall QC score."""
        if not quality_metrics:
            return 0.0
        
        # Weight different metrics
        weights = {
            'missing_rate': 0.3,
            'mean_correlation': 0.2,
            'mean_coverage': 0.2,
            'high_cv_features': 0.1,
            'low_abundance_features': 0.1,
            'constant_features': 0.1
        }
        
        score = 0.0
        total_weight = 0.0
        
        for metric, value in quality_metrics.items():
            if metric in weights:
                weight = weights[metric]
                
                # Normalize metric to 0-1 scale
                if metric == 'missing_rate':
                    normalized_value = max(0, 1 - value)  # Lower is better
                elif metric == 'mean_correlation':
                    normalized_value = value  # Higher is better
                elif metric == 'mean_coverage':
                    normalized_value = min(1, value / 50)  # Normalize to reasonable range
                elif metric in ['high_cv_features', 'low_abundance_features', 'constant_features']:
                    normalized_value = max(0, 1 - value / 100)  # Lower is better
                else:
                    normalized_value = value
                
                score += normalized_value * weight
                total_weight += weight
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def generate_qc_report(self, qc_result: QualityControlResult, omics_type: str) -> str:
        """Generate a comprehensive QC report."""
        report = f"""
# Quality Control Report
Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- Omics Type: {omics_type}
- QC Status: {'PASSED' if qc_result.passed_qc else 'FAILED'}
- QC Score: {qc_result.qc_score:.3f}

## Quality Metrics
"""
        
        for metric, value in qc_result.quality_metrics.items():
            if isinstance(value, (int, float)):
                report += f"- {metric}: {value:.3f}\n"
            else:
                report += f"- {metric}: {value}\n"
        
        if qc_result.failed_samples:
            report += f"""
## Failed Samples
{', '.join(qc_result.failed_samples)}
"""
        
        if qc_result.failed_features:
            report += f"""
## Failed Features
{len(qc_result.failed_features)} features failed QC
"""
        
        if qc_result.recommendations:
            report += f"""
## Recommendations
"""
            for i, rec in enumerate(qc_result.recommendations, 1):
                report += f"{i}. {rec}\n"
        
        return report


class OmicsValidationPipeline:
    """Complete validation pipeline for omics data."""
    
    def __init__(self, registry: OmicsFieldRegistry, metadata_manager: OmicsMetadataManager):
        """Initialize the validation pipeline."""
        self.registry = registry
        self.metadata_manager = metadata_manager
        self.validator = OmicsDataValidator(registry)
        self.qc = OmicsQualityControl(registry)
    
    def run_validation_pipeline(self, data: pd.DataFrame, omics_type: str,
                              metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run the complete validation pipeline."""
        try:
            # Step 1: Data validation
            validation_result = self.validator.validate_data(data, omics_type, metadata)
            
            # Step 2: Quality control (only if validation passed)
            qc_result = None
            if validation_result.is_valid:
                qc_result = self.qc.perform_quality_control(data, omics_type, metadata)
            else:
                qc_result = QualityControlResult(
                    passed_qc=False,
                    qc_score=0.0,
                    quality_metrics={},
                    failed_samples=[],
                    failed_features=[],
                    recommendations=["Skipped QC due to validation failures"],
                    plots={}
                )
            
            # Step 3: Generate reports
            validation_report = self._generate_validation_report(validation_result, omics_type)
            qc_report = self.qc.generate_qc_report(qc_result, omics_type)
            
            return {
                'validation_result': validation_result,
                'qc_result': qc_result,
                'validation_report': validation_report,
                'qc_report': qc_report,
                'overall_status': 'PASSED' if validation_result.is_valid and qc_result.passed_qc else 'FAILED',
                'overall_score': (validation_result.validation_score + qc_result.qc_score) / 2
            }
            
        except Exception as e:
            logger.error(f"Error in validation pipeline: {e}")
            return {
                'validation_result': ValidationResult(False, 0.0, [f"Pipeline error: {str(e)}"]),
                'qc_result': QualityControlResult(False, 0.0, recommendations=[f"Pipeline error: {str(e)}"]),
                'validation_report': f"Error: {str(e)}",
                'qc_report': f"Error: {str(e)}",
                'overall_status': 'ERROR',
                'overall_score': 0.0
            }
    
    def _generate_validation_report(self, validation_result: ValidationResult, omics_type: str) -> str:
        """Generate validation report."""
        report = f"""
# Data Validation Report
Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- Omics Type: {omics_type}
- Validation Status: {'PASSED' if validation_result.is_valid else 'FAILED'}
- Validation Score: {validation_result.validation_score:.3f}

## Quality Metrics
"""
        
        for metric, value in validation_result.quality_metrics.items():
            if isinstance(value, (int, float)):
                report += f"- {metric}: {value:.3f}\n"
            else:
                report += f"- {metric}: {value}\n"
        
        if validation_result.errors:
            report += f"""
## Errors
"""
            for i, error in enumerate(validation_result.errors, 1):
                report += f"{i}. {error}\n"
        
        if validation_result.warnings:
            report += f"""
## Warnings
"""
            for i, warning in enumerate(validation_result.warnings, 1):
                report += f"{i}. {warning}\n"
        
        if validation_result.recommendations:
            report += f"""
## Recommendations
"""
            for i, rec in enumerate(validation_result.recommendations, 1):
                report += f"{i}. {rec}\n"
        
        return report


# Global validation pipeline instance
def get_omics_validation_pipeline() -> OmicsValidationPipeline:
    """Get the global omics validation pipeline instance."""
    from .omics_registry import get_omics_registry
    from .omics_metadata import get_omics_metadata_manager
    return OmicsValidationPipeline(get_omics_registry(), get_omics_metadata_manager())
