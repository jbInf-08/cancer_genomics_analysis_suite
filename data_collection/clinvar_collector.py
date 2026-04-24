"""
ClinVar Data Collector

This module provides data collection capabilities for ClinVar via NCBI's E-utilities API.
ClinVar is a public archive of reports of the relationships among human variations
and phenotypes, with supporting evidence.

API Documentation: https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/
E-utilities: https://www.ncbi.nlm.nih.gov/books/NBK25501/
"""

import pandas as pd
import requests
import xml.etree.ElementTree as ET
import time
from typing import Dict, List, Any, Optional
from .base_collector import DataCollectorBase


class ClinvarCollector(DataCollectorBase):
    """
    Data collector for ClinVar via NCBI E-utilities API.
    
    ClinVar provides:
    - Variant-disease associations
    - Clinical significance assessments
    - Submission data from clinical labs
    - Gene-variant-phenotype relationships
    
    Authentication:
    - Uses NCBI API key (optional but recommended for higher rate limits)
    - Set NCBI_API_KEY environment variable or pass in auth_config
    - Without API key: 3 requests/second
    - With API key: 10 requests/second
    """
    
    # Cancer-related search terms
    CANCER_SEARCH_TERMS = {
        'breast': 'breast cancer[disease] OR breast neoplasm[disease] OR BRCA[gene]',
        'lung': 'lung cancer[disease] OR lung neoplasm[disease] OR EGFR[gene] OR KRAS[gene]',
        'colon': 'colorectal cancer[disease] OR colon cancer[disease] OR APC[gene] OR MLH1[gene]',
        'prostate': 'prostate cancer[disease] OR prostate neoplasm[disease]',
        'melanoma': 'melanoma[disease] OR BRAF[gene]',
        'leukemia': 'leukemia[disease] OR BCR-ABL[gene]',
        'lymphoma': 'lymphoma[disease]',
        'ovarian': 'ovarian cancer[disease] OR BRCA1[gene] OR BRCA2[gene]',
        'pancreatic': 'pancreatic cancer[disease] OR KRAS[gene]',
        'general': 'cancer[disease] OR neoplasm[disease] OR oncogenic[property]',
    }
    
    # Clinical significance categories
    CLINICAL_SIGNIFICANCE = [
        'Pathogenic',
        'Likely pathogenic',
        'Uncertain significance',
        'Likely benign',
        'Benign',
        'drug response',
        'risk factor',
        'protective'
    ]
    
    def __init__(self, output_dir: str = "data/external_sources/clinvar", **kwargs):
        """
        Initialize ClinVar collector.
        
        Args:
            output_dir: Directory to save collected data
            **kwargs: Additional configuration
        """
        super().__init__(output_dir, **kwargs)
        self.base_url = self.config.get("base_url", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils")
        self.sample_limit = self.config.get("sample_limit", 100)
        self.cancer_types = self.config.get("cancer_types", ['general', 'breast', 'lung', 'colon'])
        self.data_types = self.config.get("data_types", ['variants', 'clinical_significance', 'gene_variant'])
        
        # ClinVar-specific settings
        self.db = 'clinvar'
        self.retmax = min(self.sample_limit, 500)  # Max records per request
        
        # Rate limiting (NCBI allows 3/sec without key, 10/sec with key)
        has_api_key = self.auth_manager.has_credentials('ncbi') or self.auth_manager.has_credentials('clinvar')
        self.min_request_interval = 0.1 if has_api_key else 0.34
    
    def _search_clinvar(self, query: str, retmax: int = 100) -> List[str]:
        """
        Search ClinVar and return list of variant IDs.
        
        Args:
            query: Search query string
            retmax: Maximum number of results to return
            
        Returns:
            List of ClinVar variation IDs
        """
        url = f"{self.base_url}/esearch.fcgi"
        params = {
            'db': self.db,
            'term': query,
            'retmax': retmax,
            'retmode': 'json',
            'usehistory': 'y'
        }
        
        try:
            response = self.make_request(url, params=params, source_override='ncbi')
            data = response.json()
            
            result = data.get('esearchresult', {})
            id_list = result.get('idlist', [])
            
            self.logger.info(f"Found {len(id_list)} variants for query: {query[:50]}...")
            return id_list
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []
    
    def _fetch_variant_summaries(self, id_list: List[str]) -> List[Dict]:
        """
        Fetch summary data for a list of variant IDs.
        
        Args:
            id_list: List of ClinVar variation IDs
            
        Returns:
            List of variant summary dictionaries
        """
        if not id_list:
            return []
        
        variants = []
        
        # Process in batches of 200
        batch_size = 200
        for i in range(0, len(id_list), batch_size):
            batch_ids = id_list[i:i+batch_size]
            
            url = f"{self.base_url}/esummary.fcgi"
            params = {
                'db': self.db,
                'id': ','.join(batch_ids),
                'retmode': 'json'
            }
            
            try:
                response = self.make_request(url, params=params, source_override='ncbi')
                data = response.json()
                
                result = data.get('result', {})
                
                for uid in batch_ids:
                    if uid in result and uid != 'uids':
                        variant_data = result[uid]
                        variants.append(self._parse_variant_summary(variant_data))
                        
            except Exception as e:
                self.logger.warning(f"Failed to fetch batch {i//batch_size + 1}: {e}")
                continue
        
        return variants
    
    def _parse_variant_summary(self, data: Dict) -> Dict:
        """
        Parse variant summary data into standardized format.
        
        Args:
            data: Raw variant data from API
            
        Returns:
            Parsed variant dictionary
        """
        # Extract gene information
        genes = data.get('genes', [])
        gene_symbols = [g.get('symbol', '') for g in genes] if genes else []
        
        # Extract clinical significance
        clinical_sig = data.get('clinical_significance', {})
        description = clinical_sig.get('description', 'Not provided') if clinical_sig else 'Not provided'
        
        # Extract variation set
        variation_set = data.get('variation_set', [{}])
        first_var = variation_set[0] if variation_set else {}
        
        return {
            'variation_id': data.get('uid', ''),
            'title': data.get('title', ''),
            'gene_symbols': '; '.join(gene_symbols),
            'clinical_significance': description,
            'review_status': clinical_sig.get('review_status', '') if clinical_sig else '',
            'variation_type': first_var.get('variation_type', ''),
            'chromosome': first_var.get('chr', ''),
            'start': first_var.get('start', ''),
            'stop': first_var.get('stop', ''),
            'ref_allele': first_var.get('ref', ''),
            'alt_allele': first_var.get('alt', ''),
            'assembly': first_var.get('assembly', ''),
            'accession': data.get('accession', ''),
            'trait_names': '; '.join([t.get('trait_name', '') for t in data.get('trait_set', [])]),
            'molecular_consequence': data.get('molecular_consequence_list', []),
            'protein_change': data.get('protein_change', ''),
            'last_evaluated': clinical_sig.get('last_evaluated', '') if clinical_sig else '',
            'submission_count': data.get('supporting_submissions', {}).get('scv', 0) if data.get('supporting_submissions') else 0,
        }
    
    def _fetch_variant_details(self, id_list: List[str]) -> List[Dict]:
        """
        Fetch detailed variant data including all submissions.
        
        Args:
            id_list: List of ClinVar variation IDs
            
        Returns:
            List of detailed variant dictionaries
        """
        if not id_list:
            return []
        
        variants = []
        
        # Process in batches of 50 for detailed fetch
        batch_size = 50
        for i in range(0, len(id_list), batch_size):
            batch_ids = id_list[i:i+batch_size]
            
            url = f"{self.base_url}/efetch.fcgi"
            params = {
                'db': self.db,
                'id': ','.join(batch_ids),
                'rettype': 'vcv',
                'retmode': 'xml'
            }
            
            try:
                response = self.make_request(
                    url, params=params, source_override='ncbi',
                    headers={'Accept': 'application/xml'}
                )
                
                # Parse XML response
                root = ET.fromstring(response.content)
                
                for record in root.findall('.//VariationArchive'):
                    variant = self._parse_xml_variant(record)
                    if variant:
                        variants.append(variant)
                        
            except Exception as e:
                self.logger.warning(f"Failed to fetch details batch {i//batch_size + 1}: {e}")
                continue
        
        return variants
    
    def _parse_xml_variant(self, record: ET.Element) -> Optional[Dict]:
        """
        Parse XML variant record.
        
        Args:
            record: XML element for a variant
            
        Returns:
            Parsed variant dictionary or None
        """
        try:
            # Get basic info
            var_id = record.get('VariationID', '')
            accession = record.get('Accession', '')
            
            # Get interpreted record
            interp = record.find('.//InterpretedRecord')
            if interp is None:
                interp = record.find('.//IncludedRecord')
            
            if interp is None:
                return None
            
            # Get simple allele
            simple_allele = interp.find('.//SimpleAllele')
            
            # Gene info
            genes = []
            for gene in interp.findall('.//Gene'):
                genes.append({
                    'symbol': gene.get('Symbol', ''),
                    'id': gene.get('GeneID', '')
                })
            
            # Clinical significance
            clin_sig = interp.find('.//ClinicalSignificance')
            significance = ''
            review_status = ''
            if clin_sig is not None:
                desc = clin_sig.find('Description')
                significance = desc.text if desc is not None else ''
                review = clin_sig.find('ReviewStatus')
                review_status = review.text if review is not None else ''
            
            # Conditions/traits
            conditions = []
            for condition in interp.findall('.//TraitSet/Trait'):
                name = condition.find('.//Name/ElementValue')
                if name is not None:
                    conditions.append(name.text)
            
            # Location
            location = interp.find('.//Location/SequenceLocation[@Assembly="GRCh38"]')
            if location is None:
                location = interp.find('.//Location/SequenceLocation[@Assembly="GRCh37"]')
            
            chr_val = location.get('Chr', '') if location is not None else ''
            start = location.get('start', '') if location is not None else ''
            stop = location.get('stop', '') if location is not None else ''
            
            return {
                'variation_id': var_id,
                'accession': accession,
                'gene_symbols': '; '.join([g['symbol'] for g in genes]),
                'gene_ids': '; '.join([g['id'] for g in genes]),
                'clinical_significance': significance,
                'review_status': review_status,
                'conditions': '; '.join(conditions),
                'chromosome': chr_val,
                'start': start,
                'stop': stop,
            }
            
        except Exception as e:
            self.logger.debug(f"Failed to parse variant record: {e}")
            return None
    
    def collect_data(self, 
                    data_type: str = "variants",
                    cancer_type: str = "general",
                    gene: Optional[str] = None,
                    clinical_significance: Optional[str] = None,
                    **kwargs) -> Dict[str, Any]:
        """
        Collect data from ClinVar.
        
        Args:
            data_type: Type of data ('variants', 'clinical_significance', 'gene_variant')
            cancer_type: Cancer type to search for (key from CANCER_SEARCH_TERMS)
            gene: Specific gene to search for
            clinical_significance: Filter by clinical significance
            **kwargs: Additional parameters
            
        Returns:
            Dictionary containing collection results
        """
        self.logger.info(f"Collecting {data_type} data from ClinVar for {cancer_type}")
        
        try:
            # Build search query
            if gene:
                query = f"{gene}[gene]"
                if cancer_type in self.CANCER_SEARCH_TERMS:
                    query += f" AND ({self.CANCER_SEARCH_TERMS[cancer_type]})"
            else:
                query = self.CANCER_SEARCH_TERMS.get(cancer_type, self.CANCER_SEARCH_TERMS['general'])
            
            # Add clinical significance filter
            if clinical_significance:
                query += f' AND "{clinical_significance}"[clinical_significance]'
            
            # Search for variants
            id_list = self._search_clinvar(query, retmax=self.retmax)
            
            if not id_list:
                self.logger.warning(f"No variants found for query: {query}")
                return {"samples_collected": 0, "files_created": [], "data_type": data_type}
            
            # Fetch variant data
            if data_type == "variants" or data_type == "clinical_significance":
                variants = self._fetch_variant_summaries(id_list)
            else:
                variants = self._fetch_variant_details(id_list)
            
            if variants:
                # Convert to DataFrame
                df = pd.DataFrame(variants)
                
                # Save data
                filename = self.generate_filename(
                    data_type,
                    cancer_type=cancer_type,
                    sample_count=len(df)
                )
                filepath = self.save_data(df, filename, "csv")
                
                # Also save as JSON for complex fields
                json_filename = filename.replace('.csv', '')
                json_filepath = self.save_data(variants, json_filename, "json")
                
                self.collection_metadata["samples_collected"] = len(df)
                
                return {
                    "samples_collected": len(df),
                    "data_type": data_type,
                    "cancer_type": cancer_type,
                    "query": query,
                    "files_created": [filepath, json_filepath]
                }
            else:
                return {"samples_collected": 0, "files_created": [], "data_type": data_type}
                
        except Exception as e:
            self.logger.error(f"Failed to collect {data_type} data: {e}")
            raise
    
    def collect_gene_variants(self, 
                             genes: List[str],
                             clinical_significance: str = "Pathogenic") -> Dict[str, Any]:
        """
        Collect variants for specific genes.
        
        Args:
            genes: List of gene symbols
            clinical_significance: Filter by clinical significance
            
        Returns:
            Dictionary containing collection results
        """
        all_variants = []
        files_created = []
        
        for gene in genes:
            self.logger.info(f"Collecting variants for gene: {gene}")
            
            query = f"{gene}[gene]"
            if clinical_significance:
                query += f' AND "{clinical_significance}"[clinical_significance]'
            
            id_list = self._search_clinvar(query, retmax=self.retmax)
            
            if id_list:
                variants = self._fetch_variant_summaries(id_list)
                for v in variants:
                    v['query_gene'] = gene
                all_variants.extend(variants)
        
        if all_variants:
            df = pd.DataFrame(all_variants)
            
            filename = self.generate_filename(
                "gene_variants",
                sample_count=len(df)
            )
            filepath = self.save_data(df, filename, "csv")
            files_created.append(filepath)
            
            self.collection_metadata["samples_collected"] = len(df)
        
        return {
            "samples_collected": len(all_variants),
            "genes_queried": genes,
            "files_created": files_created
        }
    
    def get_available_datasets(self) -> List[Dict[str, Any]]:
        """Get list of available datasets from ClinVar."""
        datasets = []
        
        for data_type in self.data_types:
            for cancer_type in self.cancer_types:
                datasets.append({
                    "data_type": data_type,
                    "cancer_type": cancer_type,
                    "description": f"ClinVar {data_type} data for {cancer_type}",
                    "search_query": self.CANCER_SEARCH_TERMS.get(cancer_type, ''),
                    "estimated_samples": self.sample_limit,
                    "source": "ClinVar"
                })
        
        return datasets
    
    def search_variants(self, query: str, max_results: int = 100) -> pd.DataFrame:
        """
        Search ClinVar with custom query and return DataFrame.
        
        Args:
            query: Custom search query
            max_results: Maximum number of results
            
        Returns:
            DataFrame of variant summaries
        """
        id_list = self._search_clinvar(query, retmax=max_results)
        
        if not id_list:
            return pd.DataFrame()
        
        variants = self._fetch_variant_summaries(id_list)
        return pd.DataFrame(variants)
