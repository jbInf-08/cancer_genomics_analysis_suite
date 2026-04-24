"""
Omics Metadata Management

This module provides comprehensive metadata management for omics datasets,
including sample metadata, feature metadata, and experimental design information.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union, Tuple
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
import yaml
from datetime import datetime
import uuid

from .omics_registry import OmicsFieldRegistry, OmicsFieldDefinition

logger = logging.getLogger(__name__)


@dataclass
class OmicsSampleMetadata:
    """Metadata for omics samples."""
    
    # Basic sample information
    sample_id: str
    sample_name: Optional[str] = None
    sample_type: Optional[str] = None
    sample_source: Optional[str] = None
    
    # Experimental information
    experiment_id: Optional[str] = None
    batch_id: Optional[str] = None
    treatment: Optional[str] = None
    time_point: Optional[str] = None
    replicate: Optional[int] = None
    
    # Clinical information
    patient_id: Optional[str] = None
    age: Optional[float] = None
    sex: Optional[str] = None
    disease_status: Optional[str] = None
    disease_stage: Optional[str] = None
    
    # Technical information
    platform: Optional[str] = None
    protocol: Optional[str] = None
    technician: Optional[str] = None
    date_collected: Optional[str] = None
    date_processed: Optional[str] = None
    
    # Quality information
    quality_score: Optional[float] = None
    pass_qc: Optional[bool] = None
    notes: Optional[str] = None
    
    # Additional properties
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OmicsFeatureMetadata:
    """Metadata for omics features (genes, proteins, metabolites, etc.)."""
    
    # Basic feature information
    feature_id: str
    feature_name: Optional[str] = None
    feature_type: Optional[str] = None
    feature_description: Optional[str] = None
    
    # Genomic information
    chromosome: Optional[str] = None
    start_position: Optional[int] = None
    end_position: Optional[int] = None
    strand: Optional[str] = None
    gene_symbol: Optional[str] = None
    gene_id: Optional[str] = None
    
    # Functional information
    pathway: Optional[str] = None
    function: Optional[str] = None
    ontology_terms: List[str] = field(default_factory=list)
    
    # Expression information
    expression_level: Optional[float] = None
    expression_variance: Optional[float] = None
    detection_rate: Optional[float] = None
    
    # Quality information
    quality_score: Optional[float] = None
    reliability: Optional[str] = None
    
    # Additional properties
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OmicsExperimentMetadata:
    """Metadata for omics experiments."""
    
    # Basic experiment information
    experiment_id: str
    experiment_name: Optional[str] = None
    experiment_description: Optional[str] = None
    experiment_type: Optional[str] = None
    
    # Study information
    study_id: Optional[str] = None
    study_name: Optional[str] = None
    study_description: Optional[str] = None
    principal_investigator: Optional[str] = None
    
    # Experimental design
    design_type: Optional[str] = None  # e.g., case-control, time-series, dose-response
    factors: List[str] = field(default_factory=list)
    levels: Dict[str, List[str]] = field(default_factory=dict)
    
    # Technical information
    platform: Optional[str] = None
    protocol: Optional[str] = None
    data_processing_pipeline: Optional[str] = None
    
    # Data information
    data_types: List[str] = field(default_factory=list)
    sample_count: Optional[int] = None
    feature_count: Optional[int] = None
    
    # Quality information
    quality_control_passed: Optional[bool] = None
    quality_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Additional properties
    properties: Dict[str, Any] = field(default_factory=dict)


class OmicsMetadataManager:
    """Manager for omics metadata."""
    
    def __init__(self, registry: OmicsFieldRegistry):
        """Initialize the metadata manager with omics field registry."""
        self.registry = registry
        self.sample_metadata: Dict[str, OmicsSampleMetadata] = {}
        self.feature_metadata: Dict[str, Dict[str, OmicsFeatureMetadata]] = {}
        self.experiment_metadata: Dict[str, OmicsExperimentMetadata] = {}
    
    def add_sample_metadata(self, sample_metadata: OmicsSampleMetadata):
        """Add sample metadata."""
        self.sample_metadata[sample_metadata.sample_id] = sample_metadata
    
    def get_sample_metadata(self, sample_id: str) -> Optional[OmicsSampleMetadata]:
        """Get sample metadata by ID."""
        return self.sample_metadata.get(sample_id)
    
    def get_all_sample_metadata(self) -> Dict[str, OmicsSampleMetadata]:
        """Get all sample metadata."""
        return self.sample_metadata.copy()
    
    def add_feature_metadata(self, omics_type: str, feature_metadata: OmicsFeatureMetadata):
        """Add feature metadata for a specific omics type."""
        if omics_type not in self.feature_metadata:
            self.feature_metadata[omics_type] = {}
        self.feature_metadata[omics_type][feature_metadata.feature_id] = feature_metadata
    
    def get_feature_metadata(self, omics_type: str, feature_id: str) -> Optional[OmicsFeatureMetadata]:
        """Get feature metadata by omics type and feature ID."""
        return self.feature_metadata.get(omics_type, {}).get(feature_id)
    
    def get_all_feature_metadata(self, omics_type: str) -> Dict[str, OmicsFeatureMetadata]:
        """Get all feature metadata for a specific omics type."""
        return self.feature_metadata.get(omics_type, {}).copy()
    
    def add_experiment_metadata(self, experiment_metadata: OmicsExperimentMetadata):
        """Add experiment metadata."""
        self.experiment_metadata[experiment_metadata.experiment_id] = experiment_metadata
    
    def get_experiment_metadata(self, experiment_id: str) -> Optional[OmicsExperimentMetadata]:
        """Get experiment metadata by ID."""
        return self.experiment_metadata.get(experiment_id)
    
    def get_all_experiment_metadata(self) -> Dict[str, OmicsExperimentMetadata]:
        """Get all experiment metadata."""
        return self.experiment_metadata.copy()
    
    def create_sample_metadata_from_dataframe(self, df: pd.DataFrame, 
                                            sample_id_col: str = 'sample_id') -> Dict[str, OmicsSampleMetadata]:
        """Create sample metadata from a DataFrame."""
        sample_metadata = {}
        
        for _, row in df.iterrows():
            sample_id = row[sample_id_col]
            metadata = OmicsSampleMetadata(
                sample_id=sample_id,
                sample_name=row.get('sample_name'),
                sample_type=row.get('sample_type'),
                sample_source=row.get('sample_source'),
                experiment_id=row.get('experiment_id'),
                batch_id=row.get('batch_id'),
                treatment=row.get('treatment'),
                time_point=row.get('time_point'),
                replicate=row.get('replicate'),
                patient_id=row.get('patient_id'),
                age=row.get('age'),
                sex=row.get('sex'),
                disease_status=row.get('disease_status'),
                disease_stage=row.get('disease_stage'),
                platform=row.get('platform'),
                protocol=row.get('protocol'),
                technician=row.get('technician'),
                date_collected=row.get('date_collected'),
                date_processed=row.get('date_processed'),
                quality_score=row.get('quality_score'),
                pass_qc=row.get('pass_qc'),
                notes=row.get('notes'),
                properties={k: v for k, v in row.items() if k not in [
                    'sample_id', 'sample_name', 'sample_type', 'sample_source',
                    'experiment_id', 'batch_id', 'treatment', 'time_point', 'replicate',
                    'patient_id', 'age', 'sex', 'disease_status', 'disease_stage',
                    'platform', 'protocol', 'technician', 'date_collected', 'date_processed',
                    'quality_score', 'pass_qc', 'notes'
                ]}
            )
            sample_metadata[sample_id] = metadata
        
        return sample_metadata
    
    def create_feature_metadata_from_dataframe(self, df: pd.DataFrame, omics_type: str,
                                             feature_id_col: str = 'feature_id') -> Dict[str, OmicsFeatureMetadata]:
        """Create feature metadata from a DataFrame."""
        feature_metadata = {}
        
        for _, row in df.iterrows():
            feature_id = row[feature_id_col]
            metadata = OmicsFeatureMetadata(
                feature_id=feature_id,
                feature_name=row.get('feature_name'),
                feature_type=row.get('feature_type'),
                feature_description=row.get('feature_description'),
                chromosome=row.get('chromosome'),
                start_position=row.get('start_position'),
                end_position=row.get('end_position'),
                strand=row.get('strand'),
                gene_symbol=row.get('gene_symbol'),
                gene_id=row.get('gene_id'),
                pathway=row.get('pathway'),
                function=row.get('function'),
                ontology_terms=row.get('ontology_terms', []),
                expression_level=row.get('expression_level'),
                expression_variance=row.get('expression_variance'),
                detection_rate=row.get('detection_rate'),
                quality_score=row.get('quality_score'),
                reliability=row.get('reliability'),
                properties={k: v for k, v in row.items() if k not in [
                    'feature_id', 'feature_name', 'feature_type', 'feature_description',
                    'chromosome', 'start_position', 'end_position', 'strand',
                    'gene_symbol', 'gene_id', 'pathway', 'function', 'ontology_terms',
                    'expression_level', 'expression_variance', 'detection_rate',
                    'quality_score', 'reliability'
                ]}
            )
            feature_metadata[feature_id] = metadata
        
        return feature_metadata
    
    def create_experiment_metadata_from_dataframe(self, df: pd.DataFrame,
                                                experiment_id_col: str = 'experiment_id') -> Dict[str, OmicsExperimentMetadata]:
        """Create experiment metadata from a DataFrame."""
        experiment_metadata = {}
        
        for _, row in df.iterrows():
            experiment_id = row[experiment_id_col]
            metadata = OmicsExperimentMetadata(
                experiment_id=experiment_id,
                experiment_name=row.get('experiment_name'),
                experiment_description=row.get('experiment_description'),
                experiment_type=row.get('experiment_type'),
                study_id=row.get('study_id'),
                study_name=row.get('study_name'),
                study_description=row.get('study_description'),
                principal_investigator=row.get('principal_investigator'),
                design_type=row.get('design_type'),
                factors=row.get('factors', []),
                levels=row.get('levels', {}),
                platform=row.get('platform'),
                protocol=row.get('protocol'),
                data_processing_pipeline=row.get('data_processing_pipeline'),
                data_types=row.get('data_types', []),
                sample_count=row.get('sample_count'),
                feature_count=row.get('feature_count'),
                quality_control_passed=row.get('quality_control_passed'),
                quality_metrics=row.get('quality_metrics', {}),
                properties={k: v for k, v in row.items() if k not in [
                    'experiment_id', 'experiment_name', 'experiment_description', 'experiment_type',
                    'study_id', 'study_name', 'study_description', 'principal_investigator',
                    'design_type', 'factors', 'levels', 'platform', 'protocol',
                    'data_processing_pipeline', 'data_types', 'sample_count', 'feature_count',
                    'quality_control_passed', 'quality_metrics'
                ]}
            )
            experiment_metadata[experiment_id] = metadata
        
        return experiment_metadata
    
    def export_sample_metadata(self, file_path: str, format: str = 'csv'):
        """Export sample metadata to file."""
        if not self.sample_metadata:
            logger.warning("No sample metadata to export")
            return
        
        # Convert to DataFrame
        data = []
        for metadata in self.sample_metadata.values():
            row = {
                'sample_id': metadata.sample_id,
                'sample_name': metadata.sample_name,
                'sample_type': metadata.sample_type,
                'sample_source': metadata.sample_source,
                'experiment_id': metadata.experiment_id,
                'batch_id': metadata.batch_id,
                'treatment': metadata.treatment,
                'time_point': metadata.time_point,
                'replicate': metadata.replicate,
                'patient_id': metadata.patient_id,
                'age': metadata.age,
                'sex': metadata.sex,
                'disease_status': metadata.disease_status,
                'disease_stage': metadata.disease_stage,
                'platform': metadata.platform,
                'protocol': metadata.protocol,
                'technician': metadata.technician,
                'date_collected': metadata.date_collected,
                'date_processed': metadata.date_processed,
                'quality_score': metadata.quality_score,
                'pass_qc': metadata.pass_qc,
                'notes': metadata.notes
            }
            row.update(metadata.properties)
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # Export based on format
        if format.lower() == 'csv':
            df.to_csv(file_path, index=False)
        elif format.lower() == 'tsv':
            df.to_csv(file_path, sep='\t', index=False)
        elif format.lower() == 'json':
            df.to_json(file_path, orient='records', indent=2)
        elif format.lower() == 'yaml':
            with open(file_path, 'w') as f:
                yaml.dump(df.to_dict('records'), f, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Exported sample metadata to {file_path}")
    
    def export_feature_metadata(self, omics_type: str, file_path: str, format: str = 'csv'):
        """Export feature metadata to file."""
        if omics_type not in self.feature_metadata:
            logger.warning(f"No feature metadata for omics type: {omics_type}")
            return
        
        # Convert to DataFrame
        data = []
        for metadata in self.feature_metadata[omics_type].values():
            row = {
                'feature_id': metadata.feature_id,
                'feature_name': metadata.feature_name,
                'feature_type': metadata.feature_type,
                'feature_description': metadata.feature_description,
                'chromosome': metadata.chromosome,
                'start_position': metadata.start_position,
                'end_position': metadata.end_position,
                'strand': metadata.strand,
                'gene_symbol': metadata.gene_symbol,
                'gene_id': metadata.gene_id,
                'pathway': metadata.pathway,
                'function': metadata.function,
                'ontology_terms': metadata.ontology_terms,
                'expression_level': metadata.expression_level,
                'expression_variance': metadata.expression_variance,
                'detection_rate': metadata.detection_rate,
                'quality_score': metadata.quality_score,
                'reliability': metadata.reliability
            }
            row.update(metadata.properties)
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # Export based on format
        if format.lower() == 'csv':
            df.to_csv(file_path, index=False)
        elif format.lower() == 'tsv':
            df.to_csv(file_path, sep='\t', index=False)
        elif format.lower() == 'json':
            df.to_json(file_path, orient='records', indent=2)
        elif format.lower() == 'yaml':
            with open(file_path, 'w') as f:
                yaml.dump(df.to_dict('records'), f, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Exported feature metadata for {omics_type} to {file_path}")
    
    def export_experiment_metadata(self, file_path: str, format: str = 'csv'):
        """Export experiment metadata to file."""
        if not self.experiment_metadata:
            logger.warning("No experiment metadata to export")
            return
        
        # Convert to DataFrame
        data = []
        for metadata in self.experiment_metadata.values():
            row = {
                'experiment_id': metadata.experiment_id,
                'experiment_name': metadata.experiment_name,
                'experiment_description': metadata.experiment_description,
                'experiment_type': metadata.experiment_type,
                'study_id': metadata.study_id,
                'study_name': metadata.study_name,
                'study_description': metadata.study_description,
                'principal_investigator': metadata.principal_investigator,
                'design_type': metadata.design_type,
                'factors': metadata.factors,
                'levels': metadata.levels,
                'platform': metadata.platform,
                'protocol': metadata.protocol,
                'data_processing_pipeline': metadata.data_processing_pipeline,
                'data_types': metadata.data_types,
                'sample_count': metadata.sample_count,
                'feature_count': metadata.feature_count,
                'quality_control_passed': metadata.quality_control_passed,
                'quality_metrics': metadata.quality_metrics
            }
            row.update(metadata.properties)
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # Export based on format
        if format.lower() == 'csv':
            df.to_csv(file_path, index=False)
        elif format.lower() == 'tsv':
            df.to_csv(file_path, sep='\t', index=False)
        elif format.lower() == 'json':
            df.to_json(file_path, orient='records', indent=2)
        elif format.lower() == 'yaml':
            with open(file_path, 'w') as f:
                yaml.dump(df.to_dict('records'), f, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Exported experiment metadata to {file_path}")
    
    def import_sample_metadata(self, file_path: str, format: str = 'csv'):
        """Import sample metadata from file."""
        file_path = Path(file_path)
        
        # Import based on format
        if format.lower() == 'csv':
            df = pd.read_csv(file_path)
        elif format.lower() == 'tsv':
            df = pd.read_csv(file_path, sep='\t')
        elif format.lower() == 'json':
            df = pd.read_json(file_path)
        elif format.lower() == 'yaml':
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
            df = pd.DataFrame(data)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        # Create metadata objects
        sample_metadata = self.create_sample_metadata_from_dataframe(df)
        
        # Add to manager
        for metadata in sample_metadata.values():
            self.add_sample_metadata(metadata)
        
        logger.info(f"Imported {len(sample_metadata)} sample metadata records from {file_path}")
    
    def import_feature_metadata(self, omics_type: str, file_path: str, format: str = 'csv'):
        """Import feature metadata from file."""
        file_path = Path(file_path)
        
        # Import based on format
        if format.lower() == 'csv':
            df = pd.read_csv(file_path)
        elif format.lower() == 'tsv':
            df = pd.read_csv(file_path, sep='\t')
        elif format.lower() == 'json':
            df = pd.read_json(file_path)
        elif format.lower() == 'yaml':
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
            df = pd.DataFrame(data)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        # Create metadata objects
        feature_metadata = self.create_feature_metadata_from_dataframe(df, omics_type)
        
        # Add to manager
        for metadata in feature_metadata.values():
            self.add_feature_metadata(omics_type, metadata)
        
        logger.info(f"Imported {len(feature_metadata)} feature metadata records for {omics_type} from {file_path}")
    
    def import_experiment_metadata(self, file_path: str, format: str = 'csv'):
        """Import experiment metadata from file."""
        file_path = Path(file_path)
        
        # Import based on format
        if format.lower() == 'csv':
            df = pd.read_csv(file_path)
        elif format.lower() == 'tsv':
            df = pd.read_csv(file_path, sep='\t')
        elif format.lower() == 'json':
            df = pd.read_json(file_path)
        elif format.lower() == 'yaml':
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
            df = pd.DataFrame(data)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        # Create metadata objects
        experiment_metadata = self.create_experiment_metadata_from_dataframe(df)
        
        # Add to manager
        for metadata in experiment_metadata.values():
            self.add_experiment_metadata(metadata)
        
        logger.info(f"Imported {len(experiment_metadata)} experiment metadata records from {file_path}")
    
    def get_metadata_summary(self) -> Dict[str, Any]:
        """Get summary of all metadata."""
        summary = {
            'sample_metadata_count': len(self.sample_metadata),
            'feature_metadata_count': sum(len(metadata) for metadata in self.feature_metadata.values()),
            'experiment_metadata_count': len(self.experiment_metadata),
            'omics_types': list(self.feature_metadata.keys()),
            'sample_ids': list(self.sample_metadata.keys()),
            'experiment_ids': list(self.experiment_metadata.keys())
        }
        
        # Add feature counts by omics type
        summary['feature_counts_by_omics_type'] = {
            omics_type: len(metadata) 
            for omics_type, metadata in self.feature_metadata.items()
        }
        
        return summary
    
    def validate_metadata_consistency(self) -> Dict[str, List[str]]:
        """Validate consistency of metadata across different types."""
        issues = {
            'sample_issues': [],
            'feature_issues': [],
            'experiment_issues': [],
            'consistency_issues': []
        }
        
        # Validate sample metadata
        for sample_id, metadata in self.sample_metadata.items():
            if not metadata.sample_id:
                issues['sample_issues'].append(f"Sample {sample_id} has no sample_id")
            
            if metadata.experiment_id and metadata.experiment_id not in self.experiment_metadata:
                issues['consistency_issues'].append(
                    f"Sample {sample_id} references non-existent experiment {metadata.experiment_id}"
                )
        
        # Validate feature metadata
        for omics_type, features in self.feature_metadata.items():
            for feature_id, metadata in features.items():
                if not metadata.feature_id:
                    issues['feature_issues'].append(f"Feature {feature_id} in {omics_type} has no feature_id")
        
        # Validate experiment metadata
        for experiment_id, metadata in self.experiment_metadata.items():
            if not metadata.experiment_id:
                issues['experiment_issues'].append(f"Experiment {experiment_id} has no experiment_id")
        
        return issues
    
    def generate_metadata_report(self) -> str:
        """Generate a comprehensive metadata report."""
        summary = self.get_metadata_summary()
        issues = self.validate_metadata_consistency()
        
        report = f"""
# Omics Metadata Report
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- Total samples: {summary['sample_metadata_count']}
- Total features: {summary['feature_metadata_count']}
- Total experiments: {summary['experiment_metadata_count']}
- Omics types: {', '.join(summary['omics_types'])}

## Feature Counts by Omics Type
"""
        
        for omics_type, count in summary['feature_counts_by_omics_type'].items():
            report += f"- {omics_type}: {count} features\n"
        
        report += "\n## Issues\n"
        
        for issue_type, issue_list in issues.items():
            if issue_list:
                report += f"\n### {issue_type.replace('_', ' ').title()}\n"
                for issue in issue_list:
                    report += f"- {issue}\n"
        
        if not any(issues.values()):
            report += "No issues found.\n"
        
        return report


# Global metadata manager instance
def get_omics_metadata_manager() -> OmicsMetadataManager:
    """Get the global omics metadata manager instance."""
    from .omics_registry import get_omics_registry
    return OmicsMetadataManager(get_omics_registry())
