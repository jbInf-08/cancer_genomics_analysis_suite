"""
Ensembl Data Collector

This module provides data collection capabilities for the Ensembl REST API.
Ensembl is a genome browser for vertebrate genomes that supports research
in comparative genomics, evolution, sequence variation and transcriptional regulation.

API Documentation: https://rest.ensembl.org/documentation
Rate Limits: 15 requests/second (55,000/hour)
"""

import pandas as pd
import requests
import time
from typing import Dict, List, Any, Optional
from .base_collector import DataCollectorBase


class EnsemblCollector(DataCollectorBase):
    """
    Data collector for Ensembl REST API.
    
    Ensembl provides:
    - Gene information and annotations
    - Transcript data
    - Variant effect predictions
    - Regulatory features
    - Sequence data
    - Comparative genomics
    - Cross-references to external databases
    
    Note: Ensembl REST API is publicly available without authentication.
    Rate limit: 15 requests/second, 55,000 requests/hour.
    """
    
    # Cancer-related genes for focused queries
    CANCER_GENES = [
        'TP53', 'BRCA1', 'BRCA2', 'EGFR', 'KRAS', 'BRAF', 'PIK3CA',
        'PTEN', 'APC', 'RB1', 'MYC', 'ERBB2', 'ALK', 'CDKN2A', 'NF1',
        'ATM', 'NRAS', 'HRAS', 'VHL', 'WT1', 'RET', 'MET', 'KIT',
        'FGFR1', 'FGFR2', 'FGFR3', 'IDH1', 'IDH2', 'MLH1', 'MSH2'
    ]
    
    def __init__(self, output_dir: str = "data/external_sources/ensembl", **kwargs):
        """Initialize Ensembl collector."""
        super().__init__(output_dir, **kwargs)
        self.base_url = self.config.get("base_url", "https://rest.ensembl.org")
        self.sample_limit = self.config.get("sample_limit", 100)
        self.cancer_types = self.config.get("cancer_types", [])
        self.data_types = self.config.get("data_types", 
            ['genes', 'transcripts', 'variants', 'regulatory_features', 'sequences'])
        self.species = self.config.get("species", "human")
        
        # Ensembl-specific rate limiting (15 req/sec)
        self.min_request_interval = 0.07  # ~14 req/sec to be safe
    
    def _get_gene_info(self, gene_symbol: str) -> Optional[Dict]:
        """
        Get gene information by symbol.
        
        Args:
            gene_symbol: Gene symbol (e.g., 'TP53')
            
        Returns:
            Gene information dictionary or None
        """
        url = f"{self.base_url}/lookup/symbol/{self.species}/{gene_symbol}"
        
        try:
            response = self.make_request(
                url, 
                headers={'Content-Type': 'application/json'},
                auth_type='none'  # Ensembl is public
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'gene_id': data.get('id', ''),
                    'gene_symbol': gene_symbol,
                    'display_name': data.get('display_name', ''),
                    'description': data.get('description', ''),
                    'biotype': data.get('biotype', ''),
                    'chromosome': data.get('seq_region_name', ''),
                    'start': data.get('start', ''),
                    'end': data.get('end', ''),
                    'strand': data.get('strand', ''),
                    'assembly': data.get('assembly_name', ''),
                    'source': data.get('source', ''),
                    'version': data.get('version', ''),
                }
            else:
                self.logger.debug(f"Gene {gene_symbol} not found: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.warning(f"Failed to get gene info for {gene_symbol}: {e}")
            return None
    
    def _get_gene_by_id(self, ensembl_id: str, expand: bool = True) -> Optional[Dict]:
        """
        Get gene information by Ensembl ID.
        
        Args:
            ensembl_id: Ensembl gene ID (e.g., 'ENSG00000141510')
            expand: Whether to expand to include transcripts
            
        Returns:
            Gene information dictionary or None
        """
        url = f"{self.base_url}/lookup/id/{ensembl_id}"
        params = {'expand': 1} if expand else {}
        
        try:
            response = self.make_request(
                url, 
                params=params,
                headers={'Content-Type': 'application/json'},
                auth_type='none'
            )
            
            if response.status_code == 200:
                return response.json()
            return None
                
        except Exception as e:
            self.logger.warning(f"Failed to get gene by ID {ensembl_id}: {e}")
            return None
    
    def _get_transcripts(self, gene_id: str) -> List[Dict]:
        """
        Get transcripts for a gene.
        
        Args:
            gene_id: Ensembl gene ID
            
        Returns:
            List of transcript dictionaries
        """
        url = f"{self.base_url}/lookup/id/{gene_id}"
        params = {'expand': 1}
        
        try:
            response = self.make_request(
                url, 
                params=params,
                headers={'Content-Type': 'application/json'},
                auth_type='none'
            )
            
            if response.status_code == 200:
                data = response.json()
                transcripts = data.get('Transcript', [])
                
                return [{
                    'transcript_id': t.get('id', ''),
                    'gene_id': gene_id,
                    'display_name': t.get('display_name', ''),
                    'biotype': t.get('biotype', ''),
                    'is_canonical': t.get('is_canonical', 0),
                    'start': t.get('start', ''),
                    'end': t.get('end', ''),
                    'length': t.get('length', ''),
                    'version': t.get('version', ''),
                    'source': t.get('source', ''),
                } for t in transcripts]
            return []
                
        except Exception as e:
            self.logger.warning(f"Failed to get transcripts for {gene_id}: {e}")
            return []
    
    def _get_variants(self, gene_symbol: str, species: str = "human") -> List[Dict]:
        """
        Get known variants for a gene.
        
        Args:
            gene_symbol: Gene symbol
            species: Species name
            
        Returns:
            List of variant dictionaries
        """
        # First get gene info to get location
        gene_info = self._get_gene_info(gene_symbol)
        if not gene_info:
            return []
        
        chrom = gene_info.get('chromosome', '')
        start = gene_info.get('start', '')
        end = gene_info.get('end', '')
        
        if not all([chrom, start, end]):
            return []
        
        # Get variants in the region
        url = f"{self.base_url}/overlap/region/{species}/{chrom}:{start}-{end}"
        params = {
            'feature': 'variation',
            'content-type': 'application/json'
        }
        
        try:
            response = self.make_request(
                url, 
                params=params,
                headers={'Content-Type': 'application/json'},
                auth_type='none'
            )
            
            if response.status_code == 200:
                variants = response.json()
                
                # Limit number of variants returned
                variants = variants[:min(len(variants), self.sample_limit)]
                
                return [{
                    'variant_id': v.get('id', ''),
                    'gene_symbol': gene_symbol,
                    'chromosome': chrom,
                    'start': v.get('start', ''),
                    'end': v.get('end', ''),
                    'alleles': v.get('alleles', ''),
                    'consequence_type': v.get('consequence_type', ''),
                    'clinical_significance': v.get('clinical_significance', []),
                    'source': v.get('source', ''),
                    'assembly': v.get('assembly_name', ''),
                } for v in variants]
            return []
                
        except Exception as e:
            self.logger.warning(f"Failed to get variants for {gene_symbol}: {e}")
            return []
    
    def _get_variant_consequences(self, variants: List[str]) -> List[Dict]:
        """
        Get variant effect predictions using VEP (Variant Effect Predictor).
        
        Args:
            variants: List of variant IDs (e.g., ['rs699'])
            
        Returns:
            List of consequence dictionaries
        """
        if not variants:
            return []
        
        url = f"{self.base_url}/vep/{self.species}/id"
        
        # VEP accepts POST with list of IDs
        consequences = []
        
        # Process in batches of 200 (VEP limit)
        batch_size = 200
        for i in range(0, len(variants), batch_size):
            batch = variants[i:i+batch_size]
            
            try:
                response = self.make_request(
                    url,
                    method='POST',
                    json_data={'ids': batch},
                    headers={'Content-Type': 'application/json'},
                    auth_type='none'
                )
                
                if response.status_code == 200:
                    data = response.json()
                    for item in data:
                        for tc in item.get('transcript_consequences', []):
                            consequences.append({
                                'variant_id': item.get('id', ''),
                                'gene_symbol': tc.get('gene_symbol', ''),
                                'gene_id': tc.get('gene_id', ''),
                                'transcript_id': tc.get('transcript_id', ''),
                                'consequence_terms': '; '.join(tc.get('consequence_terms', [])),
                                'impact': tc.get('impact', ''),
                                'biotype': tc.get('biotype', ''),
                                'amino_acids': tc.get('amino_acids', ''),
                                'codons': tc.get('codons', ''),
                                'protein_position': tc.get('protein_position', ''),
                                'sift_prediction': tc.get('sift_prediction', ''),
                                'sift_score': tc.get('sift_score', ''),
                                'polyphen_prediction': tc.get('polyphen_prediction', ''),
                                'polyphen_score': tc.get('polyphen_score', ''),
                            })
                            
            except Exception as e:
                self.logger.warning(f"Failed to get VEP consequences for batch: {e}")
                continue
        
        return consequences
    
    def _get_sequence(self, gene_id: str, seq_type: str = "cdna") -> Optional[Dict]:
        """
        Get sequence for a gene or transcript.
        
        Args:
            gene_id: Ensembl gene or transcript ID
            seq_type: Sequence type ('cdna', 'cds', 'protein', 'genomic')
            
        Returns:
            Sequence dictionary or None
        """
        url = f"{self.base_url}/sequence/id/{gene_id}"
        params = {'type': seq_type}
        
        try:
            response = self.make_request(
                url,
                params=params,
                headers={'Content-Type': 'application/json'},
                auth_type='none'
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'id': data.get('id', ''),
                    'seq_type': seq_type,
                    'sequence': data.get('seq', ''),
                    'molecule': data.get('molecule', ''),
                    'description': data.get('desc', ''),
                }
            return None
                
        except Exception as e:
            self.logger.warning(f"Failed to get sequence for {gene_id}: {e}")
            return None
    
    def _get_xrefs(self, gene_id: str) -> List[Dict]:
        """
        Get cross-references for a gene.
        
        Args:
            gene_id: Ensembl gene ID
            
        Returns:
            List of cross-reference dictionaries
        """
        url = f"{self.base_url}/xrefs/id/{gene_id}"
        
        try:
            response = self.make_request(
                url,
                headers={'Content-Type': 'application/json'},
                auth_type='none'
            )
            
            if response.status_code == 200:
                xrefs = response.json()
                return [{
                    'ensembl_id': gene_id,
                    'dbname': x.get('dbname', ''),
                    'primary_id': x.get('primary_id', ''),
                    'display_id': x.get('display_id', ''),
                    'description': x.get('description', ''),
                    'info_type': x.get('info_type', ''),
                } for x in xrefs]
            return []
                
        except Exception as e:
            self.logger.warning(f"Failed to get xrefs for {gene_id}: {e}")
            return []
    
    def collect_data(self, 
                    data_type: str = "genes",
                    genes: Optional[List[str]] = None,
                    **kwargs) -> Dict[str, Any]:
        """
        Collect data from Ensembl.
        
        Args:
            data_type: Type of data to collect ('genes', 'transcripts', 'variants', 
                      'sequences', 'xrefs', 'vep')
            genes: List of gene symbols to query (defaults to CANCER_GENES)
            **kwargs: Additional parameters for collection
            
        Returns:
            Dictionary containing collection results
        """
        self.logger.info(f"Collecting {data_type} data from Ensembl")
        
        if genes is None:
            genes = self.CANCER_GENES[:min(len(self.CANCER_GENES), self.sample_limit)]
        
        try:
            all_data = []
            
            if data_type == "genes":
                for gene in genes:
                    info = self._get_gene_info(gene)
                    if info:
                        all_data.append(info)
                        
            elif data_type == "transcripts":
                for gene in genes:
                    info = self._get_gene_info(gene)
                    if info and info.get('gene_id'):
                        transcripts = self._get_transcripts(info['gene_id'])
                        all_data.extend(transcripts)
                        
            elif data_type == "variants":
                for gene in genes[:10]:  # Limit variant queries
                    variants = self._get_variants(gene)
                    all_data.extend(variants)
                    
            elif data_type == "sequences":
                seq_type = kwargs.get('seq_type', 'cdna')
                for gene in genes[:20]:  # Limit sequence queries
                    info = self._get_gene_info(gene)
                    if info and info.get('gene_id'):
                        seq = self._get_sequence(info['gene_id'], seq_type)
                        if seq:
                            seq['gene_symbol'] = gene
                            all_data.append(seq)
                            
            elif data_type == "xrefs":
                for gene in genes:
                    info = self._get_gene_info(gene)
                    if info and info.get('gene_id'):
                        xrefs = self._get_xrefs(info['gene_id'])
                        for xref in xrefs:
                            xref['gene_symbol'] = gene
                        all_data.extend(xrefs)
                        
            elif data_type == "vep":
                # Get variants first, then VEP predictions
                variant_ids = kwargs.get('variant_ids', [])
                if not variant_ids:
                    # Get some variants from cancer genes
                    for gene in genes[:5]:
                        variants = self._get_variants(gene)
                        variant_ids.extend([v['variant_id'] for v in variants if v['variant_id'].startswith('rs')])
                variant_ids = variant_ids[:self.sample_limit]
                all_data = self._get_variant_consequences(variant_ids)
            
            else:
                raise ValueError(f"Unsupported data type: {data_type}")
            
            if all_data:
                df = pd.DataFrame(all_data)
                
                filename = self.generate_filename(
                    data_type,
                    sample_count=len(df)
                )
                filepath = self.save_data(df, filename, "csv")
                
                # Also save as JSON for complex fields
                json_filepath = self.save_data(all_data, filename.replace('.csv', ''), "json")
                
                self.collection_metadata["samples_collected"] = len(df)
                
                return {
                    "samples_collected": len(df),
                    "data_type": data_type,
                    "genes_queried": len(genes),
                    "files_created": [filepath, json_filepath]
                }
            else:
                return {"samples_collected": 0, "files_created": [], "data_type": data_type}
                
        except Exception as e:
            self.logger.error(f"Failed to collect {data_type} data: {e}")
            raise
    
    def get_available_datasets(self) -> List[Dict[str, Any]]:
        """Get list of available datasets from Ensembl."""
        datasets = []
        
        data_type_descriptions = {
            'genes': 'Gene annotations and metadata',
            'transcripts': 'Transcript isoforms and features',
            'variants': 'Known genetic variants in gene regions',
            'sequences': 'cDNA, CDS, and protein sequences',
            'xrefs': 'Cross-references to external databases',
            'vep': 'Variant Effect Predictor consequences',
        }
        
        for data_type in self.data_types:
            datasets.append({
                "data_type": data_type,
                "description": f"Ensembl {data_type_descriptions.get(data_type, data_type)}",
                "cancer_genes_available": len(self.CANCER_GENES),
                "source": "Ensembl REST API",
                "requires_auth": False
            })
        
        return datasets
    
    def lookup_gene(self, gene_symbol: str) -> Optional[Dict]:
        """
        Quick lookup for a single gene.
        
        Args:
            gene_symbol: Gene symbol to look up
            
        Returns:
            Gene information or None
        """
        return self._get_gene_info(gene_symbol)
    
    def get_vep_annotation(self, variant: str) -> List[Dict]:
        """
        Get VEP annotation for a single variant.
        
        Args:
            variant: Variant ID (e.g., 'rs699') or HGVS notation
            
        Returns:
            List of consequence annotations
        """
        return self._get_variant_consequences([variant])
