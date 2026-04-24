"""
Data Preprocessing and Cleaning Utilities

This module provides comprehensive data preprocessing and cleaning utilities
for cancer genomics data collected from various sources.

Features:
- Missing value handling
- Outlier detection and handling
- Data normalization and standardization
- Gene name/ID mapping and standardization
- Variant annotation standardization
- Quality control metrics
- Data transformation utilities
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
import logging
import re
from collections import defaultdict

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """
    Comprehensive data preprocessing and cleaning utilities.
    
    Provides methods for cleaning, transforming, and validating
    cancer genomics data from various sources.
    """
    
    # Standard gene name mappings (aliases to official symbols)
    GENE_ALIASES = {
        'p53': 'TP53', 'P53': 'TP53',
        'HER2': 'ERBB2', 'HER-2': 'ERBB2', 'NEU': 'ERBB2',
        'VEGF': 'VEGFA',
        'c-MYC': 'MYC', 'cMYC': 'MYC',
        'BCL-2': 'BCL2',
        'c-KIT': 'KIT', 'CD117': 'KIT',
        'PDGFR': 'PDGFRA',
        'FLT-3': 'FLT3',
        'c-MET': 'MET', 'HGFR': 'MET',
        'BRAFV600E': 'BRAF',
    }
    
    # Standard clinical significance mappings
    CLINICAL_SIGNIFICANCE_MAP = {
        # Pathogenic variants
        'pathogenic': 'Pathogenic',
        'pathogenic/likely pathogenic': 'Pathogenic/Likely pathogenic',
        'likely pathogenic': 'Likely pathogenic',
        'likely_pathogenic': 'Likely pathogenic',
        # Benign variants
        'benign': 'Benign',
        'likely benign': 'Likely benign',
        'likely_benign': 'Likely benign',
        'benign/likely benign': 'Benign/Likely benign',
        # Uncertain
        'uncertain significance': 'Uncertain significance',
        'uncertain_significance': 'Uncertain significance',
        'vus': 'Uncertain significance',
        'vous': 'Uncertain significance',
        # Other
        'drug response': 'Drug response',
        'risk factor': 'Risk factor',
        'protective': 'Protective',
        'conflicting': 'Conflicting interpretations',
        'not provided': 'Not provided',
    }
    
    # Chromosome standardization
    CHROMOSOME_MAP = {
        'chr1': '1', 'chr2': '2', 'chr3': '3', 'chr4': '4', 'chr5': '5',
        'chr6': '6', 'chr7': '7', 'chr8': '8', 'chr9': '9', 'chr10': '10',
        'chr11': '11', 'chr12': '12', 'chr13': '13', 'chr14': '14', 'chr15': '15',
        'chr16': '16', 'chr17': '17', 'chr18': '18', 'chr19': '19', 'chr20': '20',
        'chr21': '21', 'chr22': '22', 'chrX': 'X', 'chrY': 'Y', 'chrM': 'MT',
        'chrMT': 'MT', 'chr23': 'X', 'chr24': 'Y',
    }
    
    def __init__(self):
        """Initialize the data preprocessor."""
        self.stats = defaultdict(int)
        self.warnings = []
    
    def clean_dataframe(self, 
                        df: pd.DataFrame,
                        drop_duplicates: bool = True,
                        handle_missing: str = 'keep',
                        standardize_columns: bool = True) -> pd.DataFrame:
        """
        Clean a DataFrame with common preprocessing steps.
        
        Args:
            df: Input DataFrame
            drop_duplicates: Whether to drop duplicate rows
            handle_missing: How to handle missing values ('keep', 'drop', 'fill')
            standardize_columns: Whether to standardize column names
            
        Returns:
            Cleaned DataFrame
        """
        df_clean = df.copy()
        original_rows = len(df_clean)
        
        # Standardize column names
        if standardize_columns:
            df_clean.columns = [self._standardize_column_name(col) for col in df_clean.columns]
        
        # Drop duplicates
        if drop_duplicates:
            df_clean = df_clean.drop_duplicates()
            self.stats['duplicates_removed'] = original_rows - len(df_clean)
        
        # Handle missing values
        if handle_missing == 'drop':
            df_clean = df_clean.dropna()
        elif handle_missing == 'fill':
            # Fill numeric columns with median, categorical with mode
            for col in df_clean.columns:
                if df_clean[col].dtype in ['float64', 'int64']:
                    df_clean[col] = df_clean[col].fillna(df_clean[col].median())
                else:
                    mode_val = df_clean[col].mode()
                    if len(mode_val) > 0:
                        df_clean[col] = df_clean[col].fillna(mode_val[0])
        
        self.stats['rows_after_cleaning'] = len(df_clean)
        self.stats['rows_removed'] = original_rows - len(df_clean)
        
        logger.info(f"Cleaned DataFrame: {original_rows} -> {len(df_clean)} rows")
        return df_clean
    
    def _standardize_column_name(self, name: str) -> str:
        """Standardize column name to snake_case."""
        # Convert to lowercase
        name = name.lower()
        # Replace spaces and special characters with underscores
        name = re.sub(r'[\s\-\.]+', '_', name)
        # Remove non-alphanumeric characters except underscores
        name = re.sub(r'[^a-z0-9_]', '', name)
        # Remove consecutive underscores
        name = re.sub(r'_+', '_', name)
        # Remove leading/trailing underscores
        name = name.strip('_')
        return name
    
    def standardize_gene_names(self, 
                               df: pd.DataFrame,
                               gene_column: str = 'gene',
                               use_mygene: bool = False) -> pd.DataFrame:
        """
        Standardize gene names/symbols in a DataFrame.
        
        Args:
            df: Input DataFrame
            gene_column: Name of the column containing gene names
            use_mygene: Whether to use MyGene.info API for validation
            
        Returns:
            DataFrame with standardized gene names
        """
        if gene_column not in df.columns:
            logger.warning(f"Column '{gene_column}' not found in DataFrame")
            return df
        
        df_clean = df.copy()
        standardized = []
        
        for gene in df_clean[gene_column]:
            if pd.isna(gene):
                standardized.append(gene)
                continue
            
            gene_str = str(gene).strip().upper()
            
            # Check alias map
            if gene_str in self.GENE_ALIASES:
                standardized.append(self.GENE_ALIASES[gene_str])
                self.stats['gene_names_standardized'] += 1
            else:
                standardized.append(gene_str)
        
        df_clean[gene_column] = standardized
        df_clean[f'{gene_column}_original'] = df[gene_column]
        
        logger.info(f"Standardized {self.stats['gene_names_standardized']} gene names")
        return df_clean
    
    def standardize_clinical_significance(self,
                                         df: pd.DataFrame,
                                         column: str = 'clinical_significance') -> pd.DataFrame:
        """
        Standardize clinical significance annotations.
        
        Args:
            df: Input DataFrame
            column: Name of the clinical significance column
            
        Returns:
            DataFrame with standardized clinical significance
        """
        if column not in df.columns:
            logger.warning(f"Column '{column}' not found in DataFrame")
            return df
        
        df_clean = df.copy()
        
        def standardize_sig(value):
            if pd.isna(value):
                return 'Not provided'
            value_lower = str(value).lower().strip()
            return self.CLINICAL_SIGNIFICANCE_MAP.get(value_lower, str(value))
        
        df_clean[column] = df_clean[column].apply(standardize_sig)
        df_clean[f'{column}_original'] = df[column]
        
        return df_clean
    
    def standardize_chromosomes(self,
                               df: pd.DataFrame,
                               column: str = 'chromosome') -> pd.DataFrame:
        """
        Standardize chromosome notation.
        
        Args:
            df: Input DataFrame
            column: Name of the chromosome column
            
        Returns:
            DataFrame with standardized chromosomes
        """
        if column not in df.columns:
            logger.warning(f"Column '{column}' not found in DataFrame")
            return df
        
        df_clean = df.copy()
        
        def standardize_chr(value):
            if pd.isna(value):
                return value
            value_str = str(value).strip()
            return self.CHROMOSOME_MAP.get(value_str, value_str)
        
        df_clean[column] = df_clean[column].apply(standardize_chr)
        
        return df_clean
    
    def detect_outliers(self,
                       df: pd.DataFrame,
                       columns: Optional[List[str]] = None,
                       method: str = 'iqr',
                       threshold: float = 1.5) -> Dict[str, List[int]]:
        """
        Detect outliers in numeric columns.
        
        Args:
            df: Input DataFrame
            columns: Columns to check (None = all numeric)
            method: Detection method ('iqr', 'zscore', 'mad')
            threshold: Threshold for outlier detection
            
        Returns:
            Dictionary mapping column names to lists of outlier indices
        """
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        outliers = {}
        
        for col in columns:
            if col not in df.columns:
                continue
            
            values = df[col].dropna()
            
            if len(values) == 0:
                continue
            
            if method == 'iqr':
                Q1 = values.quantile(0.25)
                Q3 = values.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - threshold * IQR
                upper_bound = Q3 + threshold * IQR
                outlier_mask = (df[col] < lower_bound) | (df[col] > upper_bound)
            
            elif method == 'zscore':
                z_scores = np.abs((values - values.mean()) / values.std())
                outlier_mask = df[col].index.isin(values[z_scores > threshold].index)
            
            elif method == 'mad':
                median = values.median()
                mad = np.median(np.abs(values - median))
                if mad == 0:
                    continue
                modified_z = 0.6745 * (values - median) / mad
                outlier_mask = df[col].index.isin(values[np.abs(modified_z) > threshold].index)
            
            else:
                raise ValueError(f"Unknown method: {method}")
            
            outlier_indices = df[outlier_mask].index.tolist()
            if outlier_indices:
                outliers[col] = outlier_indices
        
        return outliers
    
    def handle_outliers(self,
                       df: pd.DataFrame,
                       outliers: Dict[str, List[int]],
                       method: str = 'clip') -> pd.DataFrame:
        """
        Handle detected outliers.
        
        Args:
            df: Input DataFrame
            outliers: Dictionary of outlier indices from detect_outliers
            method: How to handle outliers ('clip', 'remove', 'median', 'nan')
            
        Returns:
            DataFrame with handled outliers
        """
        df_clean = df.copy()
        
        for col, indices in outliers.items():
            if col not in df_clean.columns:
                continue
            
            if method == 'clip':
                Q1 = df_clean[col].quantile(0.25)
                Q3 = df_clean[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                df_clean[col] = df_clean[col].clip(lower_bound, upper_bound)
            
            elif method == 'remove':
                df_clean = df_clean.drop(indices)
            
            elif method == 'median':
                median_val = df_clean[col].median()
                df_clean.loc[indices, col] = median_val
            
            elif method == 'nan':
                df_clean.loc[indices, col] = np.nan
        
        return df_clean
    
    def normalize_expression_data(self,
                                  df: pd.DataFrame,
                                  method: str = 'log2',
                                  gene_column: str = None,
                                  sample_columns: List[str] = None) -> pd.DataFrame:
        """
        Normalize gene expression data.
        
        Args:
            df: Expression matrix (genes x samples or long format)
            method: Normalization method ('log2', 'zscore', 'quantile', 'tpm')
            gene_column: Column containing gene names (for long format)
            sample_columns: Columns containing sample values
            
        Returns:
            Normalized expression data
        """
        df_norm = df.copy()
        
        if sample_columns is None:
            # Assume all numeric columns are samples
            sample_columns = df_norm.select_dtypes(include=[np.number]).columns.tolist()
        
        if method == 'log2':
            # Log2 transform with pseudocount
            for col in sample_columns:
                df_norm[col] = np.log2(df_norm[col] + 1)
        
        elif method == 'zscore':
            # Z-score normalization per gene (row)
            for col in sample_columns:
                df_norm[col] = (df_norm[col] - df_norm[col].mean()) / df_norm[col].std()
        
        elif method == 'quantile':
            # Quantile normalization across samples
            from scipy import stats
            ranks = df_norm[sample_columns].rank(method='average')
            sorted_means = df_norm[sample_columns].apply(lambda x: sorted(x)).mean(axis=1)
            for col in sample_columns:
                df_norm[col] = ranks[col].map(lambda x: sorted_means.iloc[int(x)-1] if not pd.isna(x) else np.nan)
        
        elif method == 'tpm':
            # Transcripts Per Million (simplified)
            for col in sample_columns:
                total = df_norm[col].sum()
                df_norm[col] = (df_norm[col] / total) * 1e6
        
        return df_norm
    
    def merge_datasets(self,
                       dfs: List[pd.DataFrame],
                       on: Union[str, List[str]],
                       how: str = 'outer',
                       suffixes: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Merge multiple datasets with conflict resolution.
        
        Args:
            dfs: List of DataFrames to merge
            on: Column(s) to merge on
            how: Merge type ('inner', 'outer', 'left', 'right')
            suffixes: Suffixes for conflicting columns
            
        Returns:
            Merged DataFrame
        """
        if len(dfs) == 0:
            return pd.DataFrame()
        
        if len(dfs) == 1:
            return dfs[0].copy()
        
        if suffixes is None:
            suffixes = [f'_source{i}' for i in range(len(dfs))]
        
        result = dfs[0].copy()
        
        for i, df in enumerate(dfs[1:], 1):
            result = pd.merge(
                result, df, 
                on=on, 
                how=how, 
                suffixes=(suffixes[i-1], suffixes[i])
            )
        
        return result
    
    def calculate_quality_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate data quality metrics.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Dictionary of quality metrics
        """
        metrics = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'missing_values': {},
            'missing_percentage': {},
            'data_types': {},
            'duplicates': df.duplicated().sum(),
            'memory_usage_mb': df.memory_usage(deep=True).sum() / 1024 / 1024,
        }
        
        for col in df.columns:
            missing = df[col].isna().sum()
            metrics['missing_values'][col] = missing
            metrics['missing_percentage'][col] = (missing / len(df)) * 100 if len(df) > 0 else 0
            metrics['data_types'][col] = str(df[col].dtype)
        
        # Overall completeness
        total_cells = len(df) * len(df.columns)
        total_missing = sum(metrics['missing_values'].values())
        metrics['overall_completeness'] = ((total_cells - total_missing) / total_cells * 100) if total_cells > 0 else 0
        
        return metrics
    
    def generate_quality_report(self, df: pd.DataFrame, output_path: Optional[str] = None) -> str:
        """
        Generate a quality report for the data.
        
        Args:
            df: Input DataFrame
            output_path: Optional path to save the report
            
        Returns:
            Quality report as string
        """
        metrics = self.calculate_quality_metrics(df)
        
        report = []
        report.append("=" * 60)
        report.append("DATA QUALITY REPORT")
        report.append("=" * 60)
        report.append(f"\nDataset Overview:")
        report.append(f"  Total Rows: {metrics['total_rows']:,}")
        report.append(f"  Total Columns: {metrics['total_columns']}")
        report.append(f"  Duplicate Rows: {metrics['duplicates']:,}")
        report.append(f"  Memory Usage: {metrics['memory_usage_mb']:.2f} MB")
        report.append(f"  Overall Completeness: {metrics['overall_completeness']:.1f}%")
        
        report.append(f"\nMissing Values by Column:")
        for col, missing in sorted(metrics['missing_values'].items(), key=lambda x: x[1], reverse=True):
            if missing > 0:
                pct = metrics['missing_percentage'][col]
                report.append(f"  {col}: {missing:,} ({pct:.1f}%)")
        
        report.append(f"\nData Types:")
        type_counts = defaultdict(int)
        for dtype in metrics['data_types'].values():
            type_counts[dtype] += 1
        for dtype, count in sorted(type_counts.items()):
            report.append(f"  {dtype}: {count} columns")
        
        report.append("\n" + "=" * 60)
        
        report_str = "\n".join(report)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report_str)
            logger.info(f"Quality report saved to {output_path}")
        
        return report_str


class VariantAnnotator:
    """
    Utilities for variant annotation and standardization.
    """
    
    @staticmethod
    def parse_hgvs_notation(hgvs: str) -> Dict[str, str]:
        """
        Parse HGVS notation into components.
        
        Args:
            hgvs: HGVS notation string (e.g., 'NM_000546.5:c.215C>G')
            
        Returns:
            Dictionary with parsed components
        """
        result = {
            'transcript': '',
            'type': '',
            'position': '',
            'ref': '',
            'alt': '',
            'original': hgvs
        }
        
        if pd.isna(hgvs) or not hgvs:
            return result
        
        try:
            # Split transcript and change
            if ':' in hgvs:
                result['transcript'], change = hgvs.split(':', 1)
            else:
                change = hgvs
            
            # Determine type (c. = coding, p. = protein, g. = genomic)
            if change.startswith('c.'):
                result['type'] = 'coding'
                change = change[2:]
            elif change.startswith('p.'):
                result['type'] = 'protein'
                change = change[2:]
            elif change.startswith('g.'):
                result['type'] = 'genomic'
                change = change[2:]
            
            # Parse substitution (e.g., 215C>G)
            match = re.match(r'(\d+)([A-Z])>([A-Z])', change)
            if match:
                result['position'] = match.group(1)
                result['ref'] = match.group(2)
                result['alt'] = match.group(3)
            
        except Exception as e:
            logger.debug(f"Failed to parse HGVS notation '{hgvs}': {e}")
        
        return result
    
    @staticmethod
    def standardize_variant_type(variant_type: str) -> str:
        """
        Standardize variant type notation.
        
        Args:
            variant_type: Input variant type
            
        Returns:
            Standardized variant type
        """
        if pd.isna(variant_type):
            return 'Unknown'
        
        type_map = {
            'snp': 'SNV',
            'snv': 'SNV',
            'single nucleotide variant': 'SNV',
            'substitution': 'SNV',
            'ins': 'Insertion',
            'insertion': 'Insertion',
            'del': 'Deletion',
            'deletion': 'Deletion',
            'indel': 'Indel',
            'delins': 'Indel',
            'complex': 'Complex',
            'mnv': 'MNV',
            'mnp': 'MNV',
            'frameshift': 'Frameshift',
            'splice': 'Splice site',
            'nonsense': 'Nonsense',
            'missense': 'Missense',
            'silent': 'Silent',
            'synonymous': 'Silent',
        }
        
        return type_map.get(variant_type.lower().strip(), variant_type)


# Convenience functions
def preprocess_mutation_data(df: pd.DataFrame) -> pd.DataFrame:
    """Convenience function to preprocess mutation data."""
    preprocessor = DataPreprocessor()
    
    df = preprocessor.clean_dataframe(df)
    
    # Standardize common columns if present
    if 'gene' in df.columns or 'gene_symbol' in df.columns:
        gene_col = 'gene' if 'gene' in df.columns else 'gene_symbol'
        df = preprocessor.standardize_gene_names(df, gene_col)
    
    if 'chromosome' in df.columns or 'chr' in df.columns:
        chr_col = 'chromosome' if 'chromosome' in df.columns else 'chr'
        df = preprocessor.standardize_chromosomes(df, chr_col)
    
    if 'clinical_significance' in df.columns:
        df = preprocessor.standardize_clinical_significance(df)
    
    return df


def preprocess_expression_data(df: pd.DataFrame, 
                               normalize: str = 'log2') -> pd.DataFrame:
    """Convenience function to preprocess expression data."""
    preprocessor = DataPreprocessor()
    
    df = preprocessor.clean_dataframe(df)
    df = preprocessor.normalize_expression_data(df, method=normalize)
    
    return df
