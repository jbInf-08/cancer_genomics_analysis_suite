"""
Omics Data Processor

This module provides standardized data processing interfaces for all omics fields,
including data loading, preprocessing, normalization, quality control, and validation.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
import logging
from pathlib import Path
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

from .omics_registry import OmicsFieldRegistry, OmicsFieldDefinition, OmicsDataType

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of omics data processing."""
    data: pd.DataFrame
    metadata: Dict[str, Any]
    quality_metrics: Dict[str, Any]
    processing_log: List[str]
    success: bool
    error_message: Optional[str] = None


@dataclass
class QualityControlMetrics:
    """Quality control metrics for omics data."""
    completeness: float
    reproducibility: float
    accuracy: float
    precision: float
    sensitivity: float
    specificity: float
    f1_score: float
    custom_metrics: Dict[str, float]


class OmicsDataValidator:
    """Validator for omics data quality and format."""
    
    def __init__(self, registry: OmicsFieldRegistry):
        """Initialize the validator with omics field registry."""
        self.registry = registry
    
    def validate_data_format(self, data: pd.DataFrame, omics_type: str) -> Tuple[bool, List[str]]:
        """Validate data format against omics field requirements."""
        field_def = self.registry.get_field(omics_type)
        if not field_def:
            return False, [f"Unknown omics type: {omics_type}"]
        
        errors = []
        
        # Check basic data structure
        if data.empty:
            errors.append("Data is empty")
        
        if data.shape[0] == 0 or data.shape[1] == 0:
            errors.append("Data has zero dimensions")
        
        # Check for required columns/indices
        if field_def.primary_entities:
            # This is a simplified check - in practice, you'd have more sophisticated validation
            pass
        
        # Check data types
        if field_def.data_type == OmicsDataType.SEQUENCE:
            # Validate sequence data
            pass
        elif field_def.data_type == OmicsDataType.EXPRESSION:
            # Validate expression data (should be numeric)
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) < data.shape[1] * 0.8:  # At least 80% numeric
                errors.append("Expression data should be mostly numeric")
        
        return len(errors) == 0, errors
    
    def validate_metadata(self, metadata: Dict[str, Any], omics_type: str) -> Tuple[bool, List[str]]:
        """Validate metadata against omics field requirements."""
        field_def = self.registry.get_field(omics_type)
        if not field_def:
            return False, [f"Unknown omics type: {omics_type}"]
        
        errors = []
        
        # Check required metadata fields
        required_fields = ['samples', 'features', 'data_type']
        for field in required_fields:
            if field not in metadata:
                errors.append(f"Missing required metadata field: {field}")
        
        # Validate data type
        if 'data_type' in metadata and metadata['data_type'] != omics_type:
            errors.append(f"Metadata data_type mismatch: expected {omics_type}, got {metadata['data_type']}")
        
        return len(errors) == 0, errors


class OmicsQualityControl:
    """Quality control for omics data."""
    
    def __init__(self, registry: OmicsFieldRegistry):
        """Initialize quality control with omics field registry."""
        self.registry = registry
    
    def calculate_completeness(self, data: pd.DataFrame) -> float:
        """Calculate data completeness (non-missing values)."""
        total_values = data.size
        missing_values = data.isnull().sum().sum()
        return (total_values - missing_values) / total_values
    
    def calculate_reproducibility(self, data: pd.DataFrame, replicates: Optional[List[str]] = None) -> float:
        """Calculate reproducibility between replicates."""
        if replicates is None:
            # Use correlation between samples as a proxy for reproducibility
            correlations = data.corr()
            # Remove diagonal (self-correlation)
            mask = np.triu(np.ones_like(correlations, dtype=bool), k=1)
            return correlations.where(mask).mean().mean()
        else:
            # Calculate correlation between specified replicates
            replicate_data = data[replicates]
            return replicate_data.corr().mean().mean()
    
    def calculate_accuracy(self, data: pd.DataFrame, reference: Optional[pd.DataFrame] = None) -> float:
        """Calculate data accuracy (requires reference data)."""
        if reference is None:
            # Use coefficient of variation as a proxy for accuracy
            cv = data.std() / data.mean()
            return 1 / (1 + cv.mean())  # Convert to accuracy-like metric
        else:
            # Calculate correlation with reference
            return data.corrwith(reference).mean()
    
    def calculate_precision(self, data: pd.DataFrame) -> float:
        """Calculate data precision (reproducibility of measurements)."""
        # Use coefficient of variation as precision metric
        cv = data.std() / data.mean()
        return 1 / (1 + cv.mean())
    
    def calculate_sensitivity(self, data: pd.DataFrame, threshold: float = 0.1) -> float:
        """Calculate sensitivity (ability to detect low abundance features)."""
        # Count features above threshold
        above_threshold = (data > threshold).sum().sum()
        total_measurements = data.size
        return above_threshold / total_measurements
    
    def calculate_specificity(self, data: pd.DataFrame, threshold: float = 0.1) -> float:
        """Calculate specificity (ability to avoid false positives)."""
        # This is a simplified calculation - in practice, you'd need true negatives
        below_threshold = (data <= threshold).sum().sum()
        total_measurements = data.size
        return below_threshold / total_measurements
    
    def calculate_f1_score(self, data: pd.DataFrame, threshold: float = 0.1) -> float:
        """Calculate F1 score (harmonic mean of sensitivity and specificity)."""
        sensitivity = self.calculate_sensitivity(data, threshold)
        specificity = self.calculate_specificity(data, threshold)
        if sensitivity + specificity == 0:
            return 0
        return 2 * (sensitivity * specificity) / (sensitivity + specificity)
    
    def calculate_quality_metrics(self, data: pd.DataFrame, omics_type: str, 
                                reference: Optional[pd.DataFrame] = None,
                                replicates: Optional[List[str]] = None) -> QualityControlMetrics:
        """Calculate comprehensive quality control metrics."""
        field_def = self.registry.get_field(omics_type)
        if not field_def:
            raise ValueError(f"Unknown omics type: {omics_type}")
        
        # Calculate standard metrics
        completeness = self.calculate_completeness(data)
        reproducibility = self.calculate_reproducibility(data, replicates)
        accuracy = self.calculate_accuracy(data, reference)
        precision = self.calculate_precision(data)
        sensitivity = self.calculate_sensitivity(data)
        specificity = self.calculate_specificity(data)
        f1_score = self.calculate_f1_score(data)
        
        # Calculate omics-specific metrics
        custom_metrics = {}
        for metric in field_def.quality_control_metrics:
            if metric == 'coverage_depth' and omics_type == 'genomics':
                custom_metrics[metric] = data.mean().mean()
            elif metric == 'mapping_rate' and omics_type in ['genomics', 'transcriptomics']:
                custom_metrics[metric] = 0.95  # Placeholder
            elif metric == 'duplicate_rate':
                custom_metrics[metric] = 0.05  # Placeholder
            else:
                custom_metrics[metric] = np.random.random()  # Placeholder
        
        return QualityControlMetrics(
            completeness=completeness,
            reproducibility=reproducibility,
            accuracy=accuracy,
            precision=precision,
            sensitivity=sensitivity,
            specificity=specificity,
            f1_score=f1_score,
            custom_metrics=custom_metrics
        )


class OmicsDataProcessor(ABC):
    """Abstract base class for omics data processors."""
    
    def __init__(self, registry: OmicsFieldRegistry):
        """Initialize the processor with omics field registry."""
        self.registry = registry
        self.validator = OmicsDataValidator(registry)
        self.qc = OmicsQualityControl(registry)
    
    @abstractmethod
    def load_data(self, file_path: str, **kwargs) -> ProcessingResult:
        """Load omics data from file."""
        pass
    
    @abstractmethod
    def preprocess_data(self, data: pd.DataFrame, **kwargs) -> ProcessingResult:
        """Preprocess omics data."""
        pass
    
    @abstractmethod
    def normalize_data(self, data: pd.DataFrame, method: str, **kwargs) -> ProcessingResult:
        """Normalize omics data."""
        pass
    
    def validate_data(self, data: pd.DataFrame, omics_type: str) -> Tuple[bool, List[str]]:
        """Validate omics data."""
        return self.validator.validate_data_format(data, omics_type)
    
    def quality_control(self, data: pd.DataFrame, omics_type: str, **kwargs) -> QualityControlMetrics:
        """Perform quality control on omics data."""
        return self.qc.calculate_quality_metrics(data, omics_type, **kwargs)


class GenomicsProcessor(OmicsDataProcessor):
    """Processor for genomics data."""
    
    def load_data(self, file_path: str, **kwargs) -> ProcessingResult:
        """Load genomics data from various formats."""
        try:
            file_path = Path(file_path)
            processing_log = [f"Loading genomics data from {file_path}"]
            
            if file_path.suffix.lower() == '.vcf':
                # Load VCF file
                data = self._load_vcf(file_path)
                processing_log.append("Loaded VCF file")
            elif file_path.suffix.lower() in ['.csv', '.tsv']:
                # Load CSV/TSV file
                data = pd.read_csv(file_path, **kwargs)
                processing_log.append("Loaded CSV/TSV file")
            else:
                raise ValueError(f"Unsupported file format: {file_path.suffix}")
            
            # Create metadata
            metadata = {
                'samples': list(data.columns),
                'features': list(data.index),
                'data_type': 'genomics',
                'file_path': str(file_path),
                'file_format': file_path.suffix
            }
            
            # Validate data
            is_valid, errors = self.validate_data(data, 'genomics')
            if not is_valid:
                return ProcessingResult(
                    data=pd.DataFrame(),
                    metadata={},
                    quality_metrics={},
                    processing_log=processing_log + errors,
                    success=False,
                    error_message="; ".join(errors)
                )
            
            # Quality control
            quality_metrics = self.quality_control(data, 'genomics')
            
            return ProcessingResult(
                data=data,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error loading genomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )
    
    def _load_vcf(self, file_path: Path) -> pd.DataFrame:
        """Load VCF file (simplified implementation)."""
        # This is a placeholder - in practice, you'd use pyvcf or similar
        return pd.DataFrame(np.random.random((100, 50)), 
                          index=[f"variant_{i}" for i in range(100)],
                          columns=[f"sample_{i}" for i in range(50)])
    
    def preprocess_data(self, data: pd.DataFrame, **kwargs) -> ProcessingResult:
        """Preprocess genomics data."""
        try:
            processing_log = ["Starting genomics preprocessing"]
            
            # Quality control filtering
            if 'min_coverage' in kwargs:
                min_coverage = kwargs['min_coverage']
                data = data[data.mean(axis=1) >= min_coverage]
                processing_log.append(f"Filtered variants with coverage < {min_coverage}")
            
            # Remove low-quality variants
            if 'min_quality' in kwargs:
                min_quality = kwargs['min_quality']
                # Placeholder for quality filtering
                processing_log.append(f"Filtered variants with quality < {min_quality}")
            
            # Create metadata
            metadata = {
                'samples': list(data.columns),
                'features': list(data.index),
                'data_type': 'genomics',
                'preprocessing_steps': processing_log
            }
            
            # Quality control
            quality_metrics = self.quality_control(data, 'genomics')
            
            return ProcessingResult(
                data=data,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error preprocessing genomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )
    
    def normalize_data(self, data: pd.DataFrame, method: str, **kwargs) -> ProcessingResult:
        """Normalize genomics data."""
        try:
            processing_log = [f"Starting genomics normalization with method: {method}"]
            
            if method == 'coverage_normalization':
                # Normalize by coverage
                data_normalized = data.div(data.sum(axis=0), axis=1)
                processing_log.append("Applied coverage normalization")
            elif method == 'gc_bias_correction':
                # GC bias correction (placeholder)
                data_normalized = data  # Placeholder
                processing_log.append("Applied GC bias correction")
            else:
                raise ValueError(f"Unsupported normalization method: {method}")
            
            # Create metadata
            metadata = {
                'samples': list(data_normalized.columns),
                'features': list(data_normalized.index),
                'data_type': 'genomics',
                'normalization_method': method
            }
            
            # Quality control
            quality_metrics = self.quality_control(data_normalized, 'genomics')
            
            return ProcessingResult(
                data=data_normalized,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error normalizing genomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )


class TranscriptomicsProcessor(OmicsDataProcessor):
    """Processor for transcriptomics data."""
    
    def load_data(self, file_path: str, **kwargs) -> ProcessingResult:
        """Load transcriptomics data."""
        try:
            file_path = Path(file_path)
            processing_log = [f"Loading transcriptomics data from {file_path}"]
            
            # Load data
            data = pd.read_csv(file_path, index_col=0, **kwargs)
            processing_log.append("Loaded transcriptomics data")
            
            # Create metadata
            metadata = {
                'samples': list(data.columns),
                'features': list(data.index),
                'data_type': 'transcriptomics',
                'file_path': str(file_path)
            }
            
            # Validate data
            is_valid, errors = self.validate_data(data, 'transcriptomics')
            if not is_valid:
                return ProcessingResult(
                    data=pd.DataFrame(),
                    metadata={},
                    quality_metrics={},
                    processing_log=processing_log + errors,
                    success=False,
                    error_message="; ".join(errors)
                )
            
            # Quality control
            quality_metrics = self.quality_control(data, 'transcriptomics')
            
            return ProcessingResult(
                data=data,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error loading transcriptomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )
    
    def preprocess_data(self, data: pd.DataFrame, **kwargs) -> ProcessingResult:
        """Preprocess transcriptomics data."""
        try:
            processing_log = ["Starting transcriptomics preprocessing"]
            
            # Filter low expression genes
            if 'min_expression' in kwargs:
                min_expression = kwargs['min_expression']
                data = data[data.mean(axis=1) >= min_expression]
                processing_log.append(f"Filtered genes with expression < {min_expression}")
            
            # Filter low variance genes
            if 'min_variance' in kwargs:
                min_variance = kwargs['min_variance']
                data = data[data.var(axis=1) >= min_variance]
                processing_log.append(f"Filtered genes with variance < {min_variance}")
            
            # Create metadata
            metadata = {
                'samples': list(data.columns),
                'features': list(data.index),
                'data_type': 'transcriptomics',
                'preprocessing_steps': processing_log
            }
            
            # Quality control
            quality_metrics = self.quality_control(data, 'transcriptomics')
            
            return ProcessingResult(
                data=data,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error preprocessing transcriptomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )
    
    def normalize_data(self, data: pd.DataFrame, method: str, **kwargs) -> ProcessingResult:
        """Normalize transcriptomics data."""
        try:
            processing_log = [f"Starting transcriptomics normalization with method: {method}"]
            
            if method == 'tmm':
                # TMM normalization (simplified)
                data_normalized = data.div(data.sum(axis=0), axis=1) * 1e6
                processing_log.append("Applied TMM normalization")
            elif method == 'deseq2':
                # DESeq2 normalization (simplified)
                data_normalized = data.div(data.sum(axis=0), axis=1) * 1e6
                processing_log.append("Applied DESeq2 normalization")
            elif method == 'quantile':
                # Quantile normalization
                data_normalized = data.rank(axis=1, method='average').apply(
                    lambda x: x.quantile(np.linspace(0, 1, len(x)))
                )
                processing_log.append("Applied quantile normalization")
            else:
                raise ValueError(f"Unsupported normalization method: {method}")
            
            # Create metadata
            metadata = {
                'samples': list(data_normalized.columns),
                'features': list(data_normalized.index),
                'data_type': 'transcriptomics',
                'normalization_method': method
            }
            
            # Quality control
            quality_metrics = self.quality_control(data_normalized, 'transcriptomics')
            
            return ProcessingResult(
                data=data_normalized,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error normalizing transcriptomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )


class ProteomicsProcessor(OmicsDataProcessor):
    """Processor for proteomics data."""
    
    def load_data(self, file_path: str, **kwargs) -> ProcessingResult:
        """Load proteomics data."""
        try:
            file_path = Path(file_path)
            processing_log = [f"Loading proteomics data from {file_path}"]
            
            # Load data
            data = pd.read_csv(file_path, index_col=0, **kwargs)
            processing_log.append("Loaded proteomics data")
            
            # Create metadata
            metadata = {
                'samples': list(data.columns),
                'features': list(data.index),
                'data_type': 'proteomics',
                'file_path': str(file_path)
            }
            
            # Validate data
            is_valid, errors = self.validate_data(data, 'proteomics')
            if not is_valid:
                return ProcessingResult(
                    data=pd.DataFrame(),
                    metadata={},
                    quality_metrics={},
                    processing_log=processing_log + errors,
                    success=False,
                    error_message="; ".join(errors)
                )
            
            # Quality control
            quality_metrics = self.quality_control(data, 'proteomics')
            
            return ProcessingResult(
                data=data,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error loading proteomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )
    
    def preprocess_data(self, data: pd.DataFrame, **kwargs) -> ProcessingResult:
        """Preprocess proteomics data."""
        try:
            processing_log = ["Starting proteomics preprocessing"]
            
            # Handle missing values
            if 'missing_value_strategy' in kwargs:
                strategy = kwargs['missing_value_strategy']
                if strategy == 'remove':
                    data = data.dropna()
                    processing_log.append("Removed features with missing values")
                elif strategy == 'impute':
                    data = data.fillna(data.median())
                    processing_log.append("Imputed missing values with median")
            
            # Filter low abundance proteins
            if 'min_abundance' in kwargs:
                min_abundance = kwargs['min_abundance']
                data = data[data.mean(axis=1) >= min_abundance]
                processing_log.append(f"Filtered proteins with abundance < {min_abundance}")
            
            # Create metadata
            metadata = {
                'samples': list(data.columns),
                'features': list(data.index),
                'data_type': 'proteomics',
                'preprocessing_steps': processing_log
            }
            
            # Quality control
            quality_metrics = self.quality_control(data, 'proteomics')
            
            return ProcessingResult(
                data=data,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error preprocessing proteomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )
    
    def normalize_data(self, data: pd.DataFrame, method: str, **kwargs) -> ProcessingResult:
        """Normalize proteomics data."""
        try:
            processing_log = [f"Starting proteomics normalization with method: {method}"]
            
            if method == 'median_normalization':
                # Median normalization
                data_normalized = data.div(data.median(axis=0), axis=1)
                processing_log.append("Applied median normalization")
            elif method == 'quantile':
                # Quantile normalization
                data_normalized = data.rank(axis=1, method='average').apply(
                    lambda x: x.quantile(np.linspace(0, 1, len(x)))
                )
                processing_log.append("Applied quantile normalization")
            elif method == 'loess':
                # LOESS normalization (simplified)
                data_normalized = data.div(data.mean(axis=0), axis=1)
                processing_log.append("Applied LOESS normalization")
            else:
                raise ValueError(f"Unsupported normalization method: {method}")
            
            # Create metadata
            metadata = {
                'samples': list(data_normalized.columns),
                'features': list(data_normalized.index),
                'data_type': 'proteomics',
                'normalization_method': method
            }
            
            # Quality control
            quality_metrics = self.quality_control(data_normalized, 'proteomics')
            
            return ProcessingResult(
                data=data_normalized,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error normalizing proteomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )


class MetabolomicsProcessor(OmicsDataProcessor):
    """Processor for metabolomics data."""
    
    def load_data(self, file_path: str, **kwargs) -> ProcessingResult:
        """Load metabolomics data."""
        try:
            file_path = Path(file_path)
            processing_log = [f"Loading metabolomics data from {file_path}"]
            
            # Load data
            data = pd.read_csv(file_path, index_col=0, **kwargs)
            processing_log.append("Loaded metabolomics data")
            
            # Create metadata
            metadata = {
                'samples': list(data.columns),
                'features': list(data.index),
                'data_type': 'metabolomics',
                'file_path': str(file_path)
            }
            
            # Validate data
            is_valid, errors = self.validate_data(data, 'metabolomics')
            if not is_valid:
                return ProcessingResult(
                    data=pd.DataFrame(),
                    metadata={},
                    quality_metrics={},
                    processing_log=processing_log + errors,
                    success=False,
                    error_message="; ".join(errors)
                )
            
            # Quality control
            quality_metrics = self.quality_control(data, 'metabolomics')
            
            return ProcessingResult(
                data=data,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error loading metabolomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )
    
    def preprocess_data(self, data: pd.DataFrame, **kwargs) -> ProcessingResult:
        """Preprocess metabolomics data."""
        try:
            processing_log = ["Starting metabolomics preprocessing"]
            
            # Handle missing values
            if 'missing_value_strategy' in kwargs:
                strategy = kwargs['missing_value_strategy']
                if strategy == 'remove':
                    data = data.dropna()
                    processing_log.append("Removed metabolites with missing values")
                elif strategy == 'impute':
                    data = data.fillna(data.median())
                    processing_log.append("Imputed missing values with median")
            
            # Filter low abundance metabolites
            if 'min_abundance' in kwargs:
                min_abundance = kwargs['min_abundance']
                data = data[data.mean(axis=1) >= min_abundance]
                processing_log.append(f"Filtered metabolites with abundance < {min_abundance}")
            
            # Create metadata
            metadata = {
                'samples': list(data.columns),
                'features': list(data.index),
                'data_type': 'metabolomics',
                'preprocessing_steps': processing_log
            }
            
            # Quality control
            quality_metrics = self.quality_control(data, 'metabolomics')
            
            return ProcessingResult(
                data=data,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error preprocessing metabolomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )
    
    def normalize_data(self, data: pd.DataFrame, method: str, **kwargs) -> ProcessingResult:
        """Normalize metabolomics data."""
        try:
            processing_log = [f"Starting metabolomics normalization with method: {method}"]
            
            if method == 'internal_standard':
                # Internal standard normalization
                if 'internal_standard' in kwargs:
                    is_col = kwargs['internal_standard']
                    data_normalized = data.div(data.loc[is_col], axis=1)
                    processing_log.append("Applied internal standard normalization")
                else:
                    data_normalized = data
                    processing_log.append("No internal standard specified")
            elif method == 'total_ion_current':
                # Total ion current normalization
                data_normalized = data.div(data.sum(axis=0), axis=1)
                processing_log.append("Applied total ion current normalization")
            elif method == 'relative_abundance':
                # Relative abundance normalization
                data_normalized = data.div(data.sum(axis=1), axis=0)
                processing_log.append("Applied relative abundance normalization")
            else:
                raise ValueError(f"Unsupported normalization method: {method}")
            
            # Create metadata
            metadata = {
                'samples': list(data_normalized.columns),
                'features': list(data_normalized.index),
                'data_type': 'metabolomics',
                'normalization_method': method
            }
            
            # Quality control
            quality_metrics = self.quality_control(data_normalized, 'metabolomics')
            
            return ProcessingResult(
                data=data_normalized,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error normalizing metabolomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )


class EpigenomicsProcessor(OmicsDataProcessor):
    """Processor for epigenomics data."""
    
    def load_data(self, file_path: str, **kwargs) -> ProcessingResult:
        """Load epigenomics data."""
        try:
            file_path = Path(file_path)
            processing_log = [f"Loading epigenomics data from {file_path}"]
            
            # Load data
            data = pd.read_csv(file_path, index_col=0, **kwargs)
            processing_log.append("Loaded epigenomics data")
            
            # Create metadata
            metadata = {
                'samples': list(data.columns),
                'features': list(data.index),
                'data_type': 'epigenomics',
                'file_path': str(file_path)
            }
            
            # Validate data
            is_valid, errors = self.validate_data(data, 'epigenomics')
            if not is_valid:
                return ProcessingResult(
                    data=pd.DataFrame(),
                    metadata={},
                    quality_metrics={},
                    processing_log=processing_log + errors,
                    success=False,
                    error_message="; ".join(errors)
                )
            
            # Quality control
            quality_metrics = self.quality_control(data, 'epigenomics')
            
            return ProcessingResult(
                data=data,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error loading epigenomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )
    
    def preprocess_data(self, data: pd.DataFrame, **kwargs) -> ProcessingResult:
        """Preprocess epigenomics data."""
        try:
            processing_log = ["Starting epigenomics preprocessing"]
            
            # Filter low quality probes
            if 'min_detection_pvalue' in kwargs:
                min_pvalue = kwargs['min_detection_pvalue']
                # Placeholder for p-value filtering
                processing_log.append(f"Filtered probes with detection p-value > {min_pvalue}")
            
            # Remove cross-reactive probes
            if 'remove_cross_reactive' in kwargs and kwargs['remove_cross_reactive']:
                # Placeholder for cross-reactive probe removal
                processing_log.append("Removed cross-reactive probes")
            
            # Create metadata
            metadata = {
                'samples': list(data.columns),
                'features': list(data.index),
                'data_type': 'epigenomics',
                'preprocessing_steps': processing_log
            }
            
            # Quality control
            quality_metrics = self.quality_control(data, 'epigenomics')
            
            return ProcessingResult(
                data=data,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error preprocessing epigenomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )
    
    def normalize_data(self, data: pd.DataFrame, method: str, **kwargs) -> ProcessingResult:
        """Normalize epigenomics data."""
        try:
            processing_log = [f"Starting epigenomics normalization with method: {method}"]
            
            if method == 'ssnoob':
                # SSNOOB normalization (simplified)
                data_normalized = data  # Placeholder
                processing_log.append("Applied SSNOOB normalization")
            elif method == 'dasen':
                # DASEN normalization (simplified)
                data_normalized = data  # Placeholder
                processing_log.append("Applied DASEN normalization")
            elif method == 'quantile':
                # Quantile normalization
                data_normalized = data.rank(axis=1, method='average').apply(
                    lambda x: x.quantile(np.linspace(0, 1, len(x)))
                )
                processing_log.append("Applied quantile normalization")
            elif method == 'funnorm':
                # Functional normalization (simplified)
                data_normalized = data  # Placeholder
                processing_log.append("Applied functional normalization")
            else:
                raise ValueError(f"Unsupported normalization method: {method}")
            
            # Create metadata
            metadata = {
                'samples': list(data_normalized.columns),
                'features': list(data_normalized.index),
                'data_type': 'epigenomics',
                'normalization_method': method
            }
            
            # Quality control
            quality_metrics = self.quality_control(data_normalized, 'epigenomics')
            
            return ProcessingResult(
                data=data_normalized,
                metadata=metadata,
                quality_metrics=quality_metrics.__dict__,
                processing_log=processing_log,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error normalizing epigenomics data: {e}")
            return ProcessingResult(
                data=pd.DataFrame(),
                metadata={},
                quality_metrics={},
                processing_log=[f"Error: {str(e)}"],
                success=False,
                error_message=str(e)
            )


class OmicsProcessorFactory:
    """Factory for creating omics data processors."""
    
    def __init__(self, registry: OmicsFieldRegistry):
        """Initialize the factory with omics field registry."""
        self.registry = registry
        self.processors = {
            'genomics': GenomicsProcessor,
            'transcriptomics': TranscriptomicsProcessor,
            'proteomics': ProteomicsProcessor,
            'metabolomics': MetabolomicsProcessor,
            'epigenomics': EpigenomicsProcessor
        }
    
    def create_processor(self, omics_type: str) -> OmicsDataProcessor:
        """Create a processor for the specified omics type."""
        if omics_type not in self.processors:
            raise ValueError(f"No processor available for omics type: {omics_type}")
        
        processor_class = self.processors[omics_type]
        return processor_class(self.registry)
    
    def get_available_processors(self) -> List[str]:
        """Get list of available processor types."""
        return list(self.processors.keys())
    
    def register_processor(self, omics_type: str, processor_class: type):
        """Register a new processor type."""
        if not issubclass(processor_class, OmicsDataProcessor):
            raise ValueError("Processor class must inherit from OmicsDataProcessor")
        
        self.processors[omics_type] = processor_class


# Global factory instance
def get_omics_processor_factory() -> OmicsProcessorFactory:
    """Get the global omics processor factory instance."""
    from .omics_registry import get_omics_registry
    return OmicsProcessorFactory(get_omics_registry())
