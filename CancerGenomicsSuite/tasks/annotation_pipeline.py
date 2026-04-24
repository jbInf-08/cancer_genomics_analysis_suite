"""
Annotation Pipeline Module

This module provides comprehensive genomic annotation pipeline capabilities
for the Cancer Genomics Analysis Suite, including variant annotation,
gene annotation, and functional analysis workflows.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
from pathlib import Path
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


@dataclass
class AnnotationConfig:
    """Annotation pipeline configuration parameters."""
    # Database paths
    refseq_path: Optional[str] = None
    ensembl_path: Optional[str] = None
    uniprot_path: Optional[str] = None
    clinvar_path: Optional[str] = None
    cosmic_path: Optional[str] = None
    
    # API endpoints
    ensembl_api: str = "https://rest.ensembl.org"
    uniprot_api: str = "https://www.uniprot.org/uniprot"
    clinvar_api: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    # Processing parameters
    batch_size: int = 100
    max_workers: int = 4
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 1
    
    # Output options
    output_format: str = "csv"  # csv, json, vcf
    include_metadata: bool = True
    save_intermediate: bool = False


@dataclass
class VariantAnnotation:
    """Variant annotation data structure."""
    variant_id: str
    chromosome: str
    position: int
    ref_allele: str
    alt_allele: str
    gene_symbol: Optional[str] = None
    gene_id: Optional[str] = None
    transcript_id: Optional[str] = None
    protein_change: Optional[str] = None
    consequence: Optional[str] = None
    impact: Optional[str] = None
    sift_score: Optional[float] = None
    polyphen_score: Optional[float] = None
    cadd_score: Optional[float] = None
    clinvar_significance: Optional[str] = None
    cosmic_id: Optional[str] = None
    population_frequency: Optional[float] = None
    functional_prediction: Optional[str] = None


@dataclass
class GeneAnnotation:
    """Gene annotation data structure."""
    gene_id: str
    gene_symbol: str
    chromosome: str
    start_position: int
    end_position: int
    strand: str
    gene_type: Optional[str] = None
    description: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    pathways: List[str] = field(default_factory=list)
    go_terms: List[str] = field(default_factory=list)
    protein_domains: List[str] = field(default_factory=list)
    expression_tissues: List[str] = field(default_factory=list)
    disease_associations: List[str] = field(default_factory=list)


class AnnotationPipeline:
    """
    A comprehensive genomic annotation pipeline for cancer genomics analysis.
    
    This class provides methods for variant annotation, gene annotation,
    and functional analysis using various databases and APIs.
    """
    
    def __init__(self, config: AnnotationConfig):
        """
        Initialize the annotation pipeline.
        
        Args:
            config (AnnotationConfig): Annotation configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.annotation_cache = {}
        self.api_cache = {}
        
        # Initialize databases
        self._load_databases()
    
    def _load_databases(self):
        """Load annotation databases if paths are provided."""
        self.databases = {}
        
        if self.config.refseq_path and os.path.exists(self.config.refseq_path):
            self.logger.info("Loading RefSeq database...")
            self.databases['refseq'] = self._load_refseq_db(self.config.refseq_path)
        
        if self.config.ensembl_path and os.path.exists(self.config.ensembl_path):
            self.logger.info("Loading Ensembl database...")
            self.databases['ensembl'] = self._load_ensembl_db(self.config.ensembl_path)
        
        if self.config.uniprot_path and os.path.exists(self.config.uniprot_path):
            self.logger.info("Loading UniProt database...")
            self.databases['uniprot'] = self._load_uniprot_db(self.config.uniprot_path)
        
        if self.config.clinvar_path and os.path.exists(self.config.clinvar_path):
            self.logger.info("Loading ClinVar database...")
            self.databases['clinvar'] = self._load_clinvar_db(self.config.clinvar_path)
        
        if self.config.cosmic_path and os.path.exists(self.config.cosmic_path):
            self.logger.info("Loading COSMIC database...")
            self.databases['cosmic'] = self._load_cosmic_db(self.config.cosmic_path)
    
    def _load_refseq_db(self, filepath: str) -> pd.DataFrame:
        """Load RefSeq database from file."""
        try:
            if filepath.endswith('.csv'):
                return pd.read_csv(filepath)
            elif filepath.endswith('.tsv'):
                return pd.read_csv(filepath, sep='\t')
            else:
                self.logger.warning(f"Unsupported RefSeq file format: {filepath}")
                return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"Error loading RefSeq database: {e}")
            return pd.DataFrame()
    
    def _load_ensembl_db(self, filepath: str) -> pd.DataFrame:
        """Load Ensembl database from file."""
        try:
            if filepath.endswith('.csv'):
                return pd.read_csv(filepath)
            elif filepath.endswith('.tsv'):
                return pd.read_csv(filepath, sep='\t')
            else:
                self.logger.warning(f"Unsupported Ensembl file format: {filepath}")
                return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"Error loading Ensembl database: {e}")
            return pd.DataFrame()
    
    def _load_uniprot_db(self, filepath: str) -> pd.DataFrame:
        """Load UniProt database from file."""
        try:
            if filepath.endswith('.csv'):
                return pd.read_csv(filepath)
            elif filepath.endswith('.tsv'):
                return pd.read_csv(filepath, sep='\t')
            else:
                self.logger.warning(f"Unsupported UniProt file format: {filepath}")
                return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"Error loading UniProt database: {e}")
            return pd.DataFrame()
    
    def _load_clinvar_db(self, filepath: str) -> pd.DataFrame:
        """Load ClinVar database from file."""
        try:
            if filepath.endswith('.csv'):
                return pd.read_csv(filepath)
            elif filepath.endswith('.tsv'):
                return pd.read_csv(filepath, sep='\t')
            else:
                self.logger.warning(f"Unsupported ClinVar file format: {filepath}")
                return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"Error loading ClinVar database: {e}")
            return pd.DataFrame()
    
    def _load_cosmic_db(self, filepath: str) -> pd.DataFrame:
        """Load COSMIC database from file."""
        try:
            if filepath.endswith('.csv'):
                return pd.read_csv(filepath)
            elif filepath.endswith('.tsv'):
                return pd.read_csv(filepath, sep='\t')
            else:
                self.logger.warning(f"Unsupported COSMIC file format: {filepath}")
                return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"Error loading COSMIC database: {e}")
            return pd.DataFrame()
    
    def annotate_variants(self, variants: Union[pd.DataFrame, List[Dict]]) -> List[VariantAnnotation]:
        """
        Annotate genomic variants.
        
        Args:
            variants (Union[pd.DataFrame, List[Dict]]): Variants to annotate
            
        Returns:
            List[VariantAnnotation]: Annotated variants
        """
        self.logger.info("Starting variant annotation...")
        
        # Convert to DataFrame if needed
        if isinstance(variants, list):
            variants_df = pd.DataFrame(variants)
        else:
            variants_df = variants.copy()
        
        # Validate required columns
        required_columns = ['chromosome', 'position', 'ref_allele', 'alt_allele']
        missing_columns = [col for col in required_columns if col not in variants_df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Process variants in batches
        annotated_variants = []
        total_variants = len(variants_df)
        
        for i in range(0, total_variants, self.config.batch_size):
            batch = variants_df.iloc[i:i + self.config.batch_size]
            self.logger.info(f"Processing batch {i//self.config.batch_size + 1}/{(total_variants-1)//self.config.batch_size + 1}")
            
            batch_annotations = self._annotate_variant_batch(batch)
            annotated_variants.extend(batch_annotations)
        
        self.logger.info(f"Completed annotation of {len(annotated_variants)} variants")
        return annotated_variants
    
    def _annotate_variant_batch(self, batch: pd.DataFrame) -> List[VariantAnnotation]:
        """Annotate a batch of variants."""
        annotations = []
        
        for _, variant in batch.iterrows():
            annotation = VariantAnnotation(
                variant_id=f"{variant['chromosome']}:{variant['position']}:{variant['ref_allele']}:{variant['alt_allele']}",
                chromosome=str(variant['chromosome']),
                position=int(variant['position']),
                ref_allele=variant['ref_allele'],
                alt_allele=variant['alt_allele']
            )
            
            # Add gene annotation
            annotation = self._add_gene_annotation(annotation)
            
            # Add functional prediction
            annotation = self._add_functional_prediction(annotation)
            
            # Add population frequency
            annotation = self._add_population_frequency(annotation)
            
            # Add clinical significance
            annotation = self._add_clinical_significance(annotation)
            
            annotations.append(annotation)
        
        return annotations
    
    def _add_gene_annotation(self, annotation: VariantAnnotation) -> VariantAnnotation:
        """Add gene annotation to variant."""
        try:
            # Check local databases first
            if 'ensembl' in self.databases:
                gene_info = self._get_gene_from_ensembl_db(annotation)
                if gene_info:
                    annotation.gene_symbol = gene_info.get('gene_symbol')
                    annotation.gene_id = gene_info.get('gene_id')
                    annotation.transcript_id = gene_info.get('transcript_id')
                    annotation.consequence = gene_info.get('consequence')
                    annotation.impact = gene_info.get('impact')
            
            # Use API if not found in local database
            if not annotation.gene_symbol:
                gene_info = self._get_gene_from_ensembl_api(annotation)
                if gene_info:
                    annotation.gene_symbol = gene_info.get('gene_symbol')
                    annotation.gene_id = gene_info.get('gene_id')
                    annotation.transcript_id = gene_info.get('transcript_id')
                    annotation.consequence = gene_info.get('consequence')
                    annotation.impact = gene_info.get('impact')
        
        except Exception as e:
            self.logger.warning(f"Error adding gene annotation: {e}")
        
        return annotation
    
    def _get_gene_from_ensembl_db(self, annotation: VariantAnnotation) -> Optional[Dict]:
        """Get gene information from local Ensembl database."""
        if 'ensembl' not in self.databases:
            return None
        
        db = self.databases['ensembl']
        
        # Simple lookup based on chromosome and position
        matches = db[
            (db['chromosome'] == annotation.chromosome) &
            (db['start'] <= annotation.position) &
            (db['end'] >= annotation.position)
        ]
        
        if not matches.empty:
            match = matches.iloc[0]
            return {
                'gene_symbol': match.get('gene_symbol'),
                'gene_id': match.get('gene_id'),
                'transcript_id': match.get('transcript_id'),
                'consequence': match.get('consequence'),
                'impact': match.get('impact')
            }
        
        return None
    
    def _get_gene_from_ensembl_api(self, annotation: VariantAnnotation) -> Optional[Dict]:
        """Get gene information from Ensembl API."""
        try:
            # Check cache first
            cache_key = f"ensembl_{annotation.chromosome}_{annotation.position}_{annotation.ref_allele}_{annotation.alt_allele}"
            if cache_key in self.api_cache:
                return self.api_cache[cache_key]
            
            # Make API request
            url = f"{self.config.ensembl_api}/vep/human/id/{annotation.variant_id}"
            params = {
                'content-type': 'application/json',
                'hgvs': 1,
                'protein': 1,
                'canonical': 1
            }
            
            response = requests.get(url, params=params, timeout=self.config.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if data and len(data) > 0:
                result = data[0]
                gene_info = {
                    'gene_symbol': result.get('gene_symbol'),
                    'gene_id': result.get('gene_id'),
                    'transcript_id': result.get('transcript_id'),
                    'consequence': result.get('consequence_terms', [None])[0] if result.get('consequence_terms') else None,
                    'impact': result.get('impact')
                }
                
                # Cache the result
                self.api_cache[cache_key] = gene_info
                return gene_info
        
        except Exception as e:
            self.logger.warning(f"Error querying Ensembl API: {e}")
        
        return None
    
    def _add_functional_prediction(self, annotation: VariantAnnotation) -> VariantAnnotation:
        """Add functional prediction scores to variant."""
        try:
            # This would typically involve calling tools like SIFT, PolyPhen, CADD
            # For now, we'll add placeholder values
            annotation.sift_score = np.random.uniform(0, 1)  # Placeholder
            annotation.polyphen_score = np.random.uniform(0, 1)  # Placeholder
            annotation.cadd_score = np.random.uniform(0, 30)  # Placeholder
            
            # Determine functional prediction based on scores
            if annotation.sift_score and annotation.sift_score < 0.05:
                annotation.functional_prediction = "Deleterious"
            elif annotation.polyphen_score and annotation.polyphen_score > 0.5:
                annotation.functional_prediction = "Probably Damaging"
            else:
                annotation.functional_prediction = "Benign"
        
        except Exception as e:
            self.logger.warning(f"Error adding functional prediction: {e}")
        
        return annotation
    
    def _add_population_frequency(self, annotation: VariantAnnotation) -> VariantAnnotation:
        """Add population frequency information to variant."""
        try:
            # This would typically query databases like gnomAD, 1000 Genomes
            # For now, we'll add a placeholder value
            annotation.population_frequency = np.random.uniform(0, 0.1)  # Placeholder
        
        except Exception as e:
            self.logger.warning(f"Error adding population frequency: {e}")
        
        return annotation
    
    def _add_clinical_significance(self, annotation: VariantAnnotation) -> VariantAnnotation:
        """Add clinical significance information to variant."""
        try:
            # Check ClinVar database
            if 'clinvar' in self.databases:
                clinvar_info = self._get_clinvar_info(annotation)
                if clinvar_info:
                    annotation.clinvar_significance = clinvar_info.get('significance')
            
            # Check COSMIC database
            if 'cosmic' in self.databases:
                cosmic_info = self._get_cosmic_info(annotation)
                if cosmic_info:
                    annotation.cosmic_id = cosmic_info.get('cosmic_id')
        
        except Exception as e:
            self.logger.warning(f"Error adding clinical significance: {e}")
        
        return annotation
    
    def _get_clinvar_info(self, annotation: VariantAnnotation) -> Optional[Dict]:
        """Get ClinVar information for variant."""
        if 'clinvar' not in self.databases:
            return None
        
        db = self.databases['clinvar']
        
        # Look for variant in ClinVar database
        matches = db[
            (db['chromosome'] == annotation.chromosome) &
            (db['position'] == annotation.position) &
            (db['ref_allele'] == annotation.ref_allele) &
            (db['alt_allele'] == annotation.alt_allele)
        ]
        
        if not matches.empty:
            match = matches.iloc[0]
            return {
                'significance': match.get('clinical_significance')
            }
        
        return None
    
    def _get_cosmic_info(self, annotation: VariantAnnotation) -> Optional[Dict]:
        """Get COSMIC information for variant."""
        if 'cosmic' not in self.databases:
            return None
        
        db = self.databases['cosmic']
        
        # Look for variant in COSMIC database
        matches = db[
            (db['chromosome'] == annotation.chromosome) &
            (db['position'] == annotation.position) &
            (db['ref_allele'] == annotation.ref_allele) &
            (db['alt_allele'] == annotation.alt_allele)
        ]
        
        if not matches.empty:
            match = matches.iloc[0]
            return {
                'cosmic_id': match.get('cosmic_id')
            }
        
        return None
    
    def annotate_genes(self, genes: Union[List[str], pd.DataFrame]) -> List[GeneAnnotation]:
        """
        Annotate genes with functional information.
        
        Args:
            genes (Union[List[str], pd.DataFrame]): Genes to annotate
            
        Returns:
            List[GeneAnnotation]: Annotated genes
        """
        self.logger.info("Starting gene annotation...")
        
        # Convert to list of gene symbols
        if isinstance(genes, pd.DataFrame):
            if 'gene_symbol' in genes.columns:
                gene_symbols = genes['gene_symbol'].tolist()
            elif 'gene_id' in genes.columns:
                gene_symbols = genes['gene_id'].tolist()
            else:
                raise ValueError("DataFrame must contain 'gene_symbol' or 'gene_id' column")
        else:
            gene_symbols = genes
        
        # Process genes in batches
        annotated_genes = []
        total_genes = len(gene_symbols)
        
        for i in range(0, total_genes, self.config.batch_size):
            batch = gene_symbols[i:i + self.config.batch_size]
            self.logger.info(f"Processing batch {i//self.config.batch_size + 1}/{(total_genes-1)//self.config.batch_size + 1}")
            
            batch_annotations = self._annotate_gene_batch(batch)
            annotated_genes.extend(batch_annotations)
        
        self.logger.info(f"Completed annotation of {len(annotated_genes)} genes")
        return annotated_genes
    
    def _annotate_gene_batch(self, gene_symbols: List[str]) -> List[GeneAnnotation]:
        """Annotate a batch of genes."""
        annotations = []
        
        for gene_symbol in gene_symbols:
            annotation = GeneAnnotation(
                gene_id=gene_symbol,
                gene_symbol=gene_symbol
            )
            
            # Add basic gene information
            annotation = self._add_basic_gene_info(annotation)
            
            # Add functional annotations
            annotation = self._add_functional_annotations(annotation)
            
            # Add disease associations
            annotation = self._add_disease_associations(annotation)
            
            annotations.append(annotation)
        
        return annotations
    
    def _add_basic_gene_info(self, annotation: GeneAnnotation) -> GeneAnnotation:
        """Add basic gene information."""
        try:
            # Check local databases first
            if 'ensembl' in self.databases:
                gene_info = self._get_basic_gene_info_from_db(annotation)
                if gene_info:
                    annotation.chromosome = gene_info.get('chromosome')
                    annotation.start_position = gene_info.get('start_position')
                    annotation.end_position = gene_info.get('end_position')
                    annotation.strand = gene_info.get('strand')
                    annotation.gene_type = gene_info.get('gene_type')
                    annotation.description = gene_info.get('description')
            
            # Use API if not found in local database
            if not annotation.chromosome:
                gene_info = self._get_basic_gene_info_from_api(annotation)
                if gene_info:
                    annotation.chromosome = gene_info.get('chromosome')
                    annotation.start_position = gene_info.get('start_position')
                    annotation.end_position = gene_info.get('end_position')
                    annotation.strand = gene_info.get('strand')
                    annotation.gene_type = gene_info.get('gene_type')
                    annotation.description = gene_info.get('description')
        
        except Exception as e:
            self.logger.warning(f"Error adding basic gene info: {e}")
        
        return annotation
    
    def _get_basic_gene_info_from_db(self, annotation: GeneAnnotation) -> Optional[Dict]:
        """Get basic gene information from local database."""
        if 'ensembl' not in self.databases:
            return None
        
        db = self.databases['ensembl']
        
        # Look for gene in database
        matches = db[db['gene_symbol'] == annotation.gene_symbol]
        
        if not matches.empty:
            match = matches.iloc[0]
            return {
                'chromosome': match.get('chromosome'),
                'start_position': match.get('start'),
                'end_position': match.get('end'),
                'strand': match.get('strand'),
                'gene_type': match.get('gene_type'),
                'description': match.get('description')
            }
        
        return None
    
    def _get_basic_gene_info_from_api(self, annotation: GeneAnnotation) -> Optional[Dict]:
        """Get basic gene information from API."""
        try:
            # Check cache first
            cache_key = f"gene_info_{annotation.gene_symbol}"
            if cache_key in self.api_cache:
                return self.api_cache[cache_key]
            
            # Make API request to Ensembl
            url = f"{self.config.ensembl_api}/lookup/symbol/human/{annotation.gene_symbol}"
            params = {'content-type': 'application/json'}
            
            response = requests.get(url, params=params, timeout=self.config.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if data:
                gene_info = {
                    'chromosome': data.get('seq_region_name'),
                    'start_position': data.get('start'),
                    'end_position': data.get('end'),
                    'strand': data.get('strand'),
                    'gene_type': data.get('biotype'),
                    'description': data.get('description')
                }
                
                # Cache the result
                self.api_cache[cache_key] = gene_info
                return gene_info
        
        except Exception as e:
            self.logger.warning(f"Error querying gene info API: {e}")
        
        return None
    
    def _add_functional_annotations(self, annotation: GeneAnnotation) -> GeneAnnotation:
        """Add functional annotations to gene."""
        try:
            # Add GO terms, pathways, protein domains
            # This would typically involve querying multiple databases
            annotation.go_terms = ["GO:0008150", "GO:0003674"]  # Placeholder
            annotation.pathways = ["KEGG:04010", "Reactome:R-HSA-73857"]  # Placeholder
            annotation.protein_domains = ["PF00001", "PF00002"]  # Placeholder
            annotation.expression_tissues = ["brain", "liver", "heart"]  # Placeholder
        
        except Exception as e:
            self.logger.warning(f"Error adding functional annotations: {e}")
        
        return annotation
    
    def _add_disease_associations(self, annotation: GeneAnnotation) -> GeneAnnotation:
        """Add disease associations to gene."""
        try:
            # This would typically query databases like OMIM, DisGeNET
            annotation.disease_associations = ["cancer", "diabetes"]  # Placeholder
        
        except Exception as e:
            self.logger.warning(f"Error adding disease associations: {e}")
        
        return annotation
    
    def save_annotations(self, annotations: List[Union[VariantAnnotation, GeneAnnotation]], 
                        output_path: str):
        """
        Save annotations to file.
        
        Args:
            annotations (List[Union[VariantAnnotation, GeneAnnotation]]): Annotations to save
            output_path (str): Output file path
        """
        if not annotations:
            self.logger.warning("No annotations to save")
            return
        
        # Convert annotations to DataFrame
        data = []
        for annotation in annotations:
            if isinstance(annotation, VariantAnnotation):
                data.append({
                    'variant_id': annotation.variant_id,
                    'chromosome': annotation.chromosome,
                    'position': annotation.position,
                    'ref_allele': annotation.ref_allele,
                    'alt_allele': annotation.alt_allele,
                    'gene_symbol': annotation.gene_symbol,
                    'gene_id': annotation.gene_id,
                    'transcript_id': annotation.transcript_id,
                    'protein_change': annotation.protein_change,
                    'consequence': annotation.consequence,
                    'impact': annotation.impact,
                    'sift_score': annotation.sift_score,
                    'polyphen_score': annotation.polyphen_score,
                    'cadd_score': annotation.cadd_score,
                    'clinvar_significance': annotation.clinvar_significance,
                    'cosmic_id': annotation.cosmic_id,
                    'population_frequency': annotation.population_frequency,
                    'functional_prediction': annotation.functional_prediction
                })
            elif isinstance(annotation, GeneAnnotation):
                data.append({
                    'gene_id': annotation.gene_id,
                    'gene_symbol': annotation.gene_symbol,
                    'chromosome': annotation.chromosome,
                    'start_position': annotation.start_position,
                    'end_position': annotation.end_position,
                    'strand': annotation.strand,
                    'gene_type': annotation.gene_type,
                    'description': annotation.description,
                    'aliases': ';'.join(annotation.aliases),
                    'pathways': ';'.join(annotation.pathways),
                    'go_terms': ';'.join(annotation.go_terms),
                    'protein_domains': ';'.join(annotation.protein_domains),
                    'expression_tissues': ';'.join(annotation.expression_tissues),
                    'disease_associations': ';'.join(annotation.disease_associations)
                })
        
        df = pd.DataFrame(data)
        
        # Save based on format
        if output_path.endswith('.csv'):
            df.to_csv(output_path, index=False)
        elif output_path.endswith('.json'):
            df.to_json(output_path, orient='records', indent=2)
        elif output_path.endswith('.tsv'):
            df.to_csv(output_path, sep='\t', index=False)
        else:
            # Default to CSV
            df.to_csv(output_path, index=False)
        
        self.logger.info(f"Saved {len(annotations)} annotations to {output_path}")
    
    def generate_annotation_report(self, annotations: List[Union[VariantAnnotation, GeneAnnotation]], 
                                 output_path: str):
        """
        Generate an annotation summary report.
        
        Args:
            annotations (List[Union[VariantAnnotation, GeneAnnotation]]): Annotations to summarize
            output_path (str): Output report path
        """
        with open(output_path, 'w') as f:
            f.write("Genomic Annotation Summary Report\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Total annotations: {len(annotations)}\n\n")
            
            # Separate variant and gene annotations
            variant_annotations = [a for a in annotations if isinstance(a, VariantAnnotation)]
            gene_annotations = [a for a in annotations if isinstance(a, GeneAnnotation)]
            
            if variant_annotations:
                f.write(f"Variant annotations: {len(variant_annotations)}\n")
                
                # Count by consequence
                consequences = {}
                for ann in variant_annotations:
                    if ann.consequence:
                        consequences[ann.consequence] = consequences.get(ann.consequence, 0) + 1
                
                if consequences:
                    f.write("\nConsequence distribution:\n")
                    for consequence, count in sorted(consequences.items(), key=lambda x: x[1], reverse=True):
                        f.write(f"  {consequence}: {count}\n")
                
                # Count by impact
                impacts = {}
                for ann in variant_annotations:
                    if ann.impact:
                        impacts[ann.impact] = impacts.get(ann.impact, 0) + 1
                
                if impacts:
                    f.write("\nImpact distribution:\n")
                    for impact, count in sorted(impacts.items(), key=lambda x: x[1], reverse=True):
                        f.write(f"  {impact}: {count}\n")
            
            if gene_annotations:
                f.write(f"\nGene annotations: {len(gene_annotations)}\n")
                
                # Count by gene type
                gene_types = {}
                for ann in gene_annotations:
                    if ann.gene_type:
                        gene_types[ann.gene_type] = gene_types.get(ann.gene_type, 0) + 1
                
                if gene_types:
                    f.write("\nGene type distribution:\n")
                    for gene_type, count in sorted(gene_types.items(), key=lambda x: x[1], reverse=True):
                        f.write(f"  {gene_type}: {count}\n")
            
            f.write(f"\nReport generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        self.logger.info(f"Annotation report saved to: {output_path}")
