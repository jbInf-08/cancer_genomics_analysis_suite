"""
COSMIC (Catalogue of Somatic Mutations in Cancer) Data Fetcher

This module provides integration with the COSMIC database for fetching
somatic mutation data, cancer gene census information, and related
genomics data for cancer research.

Features:
- Somatic mutation data retrieval
- Cancer gene census information
- Mutation frequency and prevalence data
- Tissue-specific mutation patterns
- Drug sensitivity and resistance data
- Batch processing and caching
- Rate limiting and error handling

API Documentation: https://cancer.sanger.ac.uk/cosmic/help/api
"""

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode, urljoin

import pandas as pd
import requests

logger = logging.getLogger(__name__)


class COSMICFetcher:
    """
    Client for fetching data from the COSMIC database.
    
    This class provides methods to retrieve somatic mutation data,
    cancer gene information, and related genomics data from COSMIC.
    """
    
    BASE_URL = "https://cancer.sanger.ac.uk/cosmic/"
    API_BASE = "https://cancer.sanger.ac.uk/cosmic/api/"
    
    def __init__(self, api_key: Optional[str] = None, cache_dir: str = "cache/cosmic"):
        """
        Initialize COSMIC fetcher.
        
        Args:
            api_key: COSMIC API key (optional for public endpoints)
            cache_dir: Directory for caching responses
        """
        self.api_key = api_key
        self.cache_dir = cache_dir
        self.session = requests.Session()
        self.rate_limit_delay = 1.0  # seconds between requests
        self.last_request_time = 0
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        
        # Set up session headers
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})

        self.session.headers.update(
            {
                "User-Agent": "CancerGenomicsSuite/1.0",
                "Accept": "application/json",
            }
        )

    @property
    def base_url(self) -> str:
        return str(self.BASE_URL)
    
    def _rate_limit(self):
        """Implement rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _get_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate cache key for request."""
        cache_data = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response if available."""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                
                # Check if cache is still valid (24 hours)
                cache_time = datetime.fromisoformat(cached_data['timestamp'])
                if datetime.now() - cache_time < timedelta(hours=24):
                    return cached_data['data']
            except Exception as e:
                logger.warning(f"Failed to read cache file {cache_file}: {e}")
        
        return None
    
    def _cache_response(self, cache_key: str, data: Dict[str, Any]):
        """Cache response data."""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to cache response to {cache_file}: {e}")
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None, 
                     use_cache: bool = True) -> Dict[str, Any]:
        """
        Make API request with rate limiting and caching.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            use_cache: Whether to use cached responses
            
        Returns:
            API response data
        """
        params = params or {}
        
        # Check cache first
        if use_cache:
            cache_key = self._get_cache_key(endpoint, params)
            cached_data = self._get_cached_response(cache_key)
            if cached_data:
                logger.debug(f"Using cached data for {endpoint}")
                return cached_data
        
        # Rate limiting
        self._rate_limit()
        
        # Make request
        url = urljoin(self.API_BASE, endpoint)
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Cache successful response
            if use_cache:
                self._cache_response(cache_key, data)
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {endpoint}: {e}")
            raise
    
    def get_mutations_by_gene(self, gene_symbol: str, 
                            cancer_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get somatic mutations for a specific gene.
        
        Args:
            gene_symbol: Gene symbol (e.g., 'TP53', 'BRCA1')
            cancer_type: Optional cancer type filter
            
        Returns:
            List of mutation records
        """
        params = {'gene': gene_symbol}
        if cancer_type:
            params['cancer_type'] = cancer_type
        
        try:
            data = self._make_request('mutations', params)
            return data.get('mutations', [])
        except Exception as e:
            logger.error(f"Failed to fetch mutations for gene {gene_symbol}: {e}")
            return []
    
    def get_mutation_details(self, mutation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific mutation.
        
        Args:
            mutation_id: COSMIC mutation ID
            
        Returns:
            Mutation details or None if not found
        """
        try:
            data = self._make_request(f'mutations/{mutation_id}')
            return data
        except Exception as e:
            logger.error(f"Failed to fetch mutation details for {mutation_id}: {e}")
            return None
    
    def get_cancer_gene_census(self, gene_symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get cancer gene census information.
        
        Args:
            gene_symbol: Optional gene symbol filter
            
        Returns:
            List of cancer gene census records
        """
        params = {}
        if gene_symbol:
            params['gene'] = gene_symbol
        
        try:
            data = self._make_request('cancer_gene_census', params)
            return data.get('genes', [])
        except Exception as e:
            logger.error(f"Failed to fetch cancer gene census: {e}")
            return []
    
    def get_mutation_frequency(self, gene_symbol: str, 
                             cancer_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get mutation frequency data for a gene.
        
        Args:
            gene_symbol: Gene symbol
            cancer_type: Optional cancer type filter
            
        Returns:
            Mutation frequency statistics
        """
        params = {'gene': gene_symbol}
        if cancer_type:
            params['cancer_type'] = cancer_type
        
        try:
            data = self._make_request('mutation_frequency', params)
            return data
        except Exception as e:
            logger.error(f"Failed to fetch mutation frequency for {gene_symbol}: {e}")
            return {}
    
    def get_tissue_mutation_patterns(self, tissue_type: str) -> List[Dict[str, Any]]:
        """
        Get mutation patterns for a specific tissue type.
        
        Args:
            tissue_type: Tissue type (e.g., 'breast', 'lung', 'colon')
            
        Returns:
            List of tissue-specific mutation patterns
        """
        params = {'tissue': tissue_type}
        
        try:
            data = self._make_request('tissue_mutations', params)
            return data.get('mutations', [])
        except Exception as e:
            logger.error(f"Failed to fetch tissue mutation patterns for {tissue_type}: {e}")
            return []
    
    def get_drug_sensitivity_data(self, gene_symbol: str) -> List[Dict[str, Any]]:
        """
        Get drug sensitivity data for a gene.
        
        Args:
            gene_symbol: Gene symbol
            
        Returns:
            List of drug sensitivity records
        """
        params = {'gene': gene_symbol}
        
        try:
            data = self._make_request('drug_sensitivity', params)
            return data.get('drugs', [])
        except Exception as e:
            logger.error(f"Failed to fetch drug sensitivity data for {gene_symbol}: {e}")
            return []
    
    def search_mutations(self, query: str, 
                        filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for mutations using text query.
        
        Args:
            query: Search query
            filters: Optional filters (gene, cancer_type, etc.)
            
        Returns:
            List of matching mutations
        """
        params = {'q': query}
        if filters:
            params.update(filters)
        
        try:
            data = self._make_request('search/mutations', params)
            return data.get('results', [])
        except Exception as e:
            logger.error(f"Failed to search mutations with query '{query}': {e}")
            return []
    
    def get_cancer_types(self) -> List[Dict[str, Any]]:
        """
        Get list of available cancer types.
        
        Returns:
            List of cancer type information
        """
        try:
            data = self._make_request('cancer_types')
            return data.get('cancer_types', [])
        except Exception as e:
            logger.error(f"Failed to fetch cancer types: {e}")
            return []
    
    def get_gene_list(self, cancer_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of genes with mutation data.
        
        Args:
            cancer_type: Optional cancer type filter
            
        Returns:
            List of gene information
        """
        params = {}
        if cancer_type:
            params['cancer_type'] = cancer_type
        
        try:
            data = self._make_request('genes', params)
            return data.get('genes', [])
        except Exception as e:
            logger.error(f"Failed to fetch gene list: {e}")
            return []
    
    def batch_fetch_mutations(self, gene_symbols: List[str], 
                            cancer_type: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Batch fetch mutations for multiple genes.
        
        Args:
            gene_symbols: List of gene symbols
            cancer_type: Optional cancer type filter
            
        Returns:
            Dictionary mapping gene symbols to mutation lists
        """
        results = {}
        
        for gene_symbol in gene_symbols:
            logger.info(f"Fetching mutations for gene: {gene_symbol}")
            mutations = self.get_mutations_by_gene(gene_symbol, cancer_type)
            results[gene_symbol] = mutations
            
            # Add delay between genes to respect rate limits
            time.sleep(self.rate_limit_delay)
        
        return results
    
    def export_to_dataframe(self, mutations: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Convert mutation data to pandas DataFrame.
        
        Args:
            mutations: List of mutation records
            
        Returns:
            DataFrame with mutation data
        """
        if not mutations:
            return pd.DataFrame()
        
        # Flatten nested data and create DataFrame
        flattened_data = []
        for mutation in mutations:
            flat_mutation = {}
            for key, value in mutation.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        flat_mutation[f"{key}_{sub_key}"] = sub_value
                elif isinstance(value, list):
                    flat_mutation[key] = json.dumps(value)
                else:
                    flat_mutation[key] = value
            
            flattened_data.append(flat_mutation)
        
        return pd.DataFrame(flattened_data)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get COSMIC database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        try:
            data = self._make_request('statistics')
            return data
        except Exception as e:
            logger.error(f"Failed to fetch COSMIC statistics: {e}")
            return {}

    @staticmethod
    def _validate_response(response: Any) -> bool:
        code = getattr(response, "status_code", None)
        return code is not None and int(code) == 200

    def fetch_mutations_by_gene(
        self, gene_symbol: str, cancer_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Return mutation list with a success/error wrapper (used by integrations/tests).
        """
        try:
            params: Dict[str, Any] = {"gene": gene_symbol}
            if cancer_type:
                params["cancer_type"] = cancer_type
            data = self._make_request("mutations", params)
            muts = data.get("mutations", [])
            return {"status": "success", "data": muts, "mutations": muts}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def fetch_mutations_by_sample(self, sample_id: str) -> Dict[str, Any]:
        try:
            data = self._make_request(f"mutations/sample/{sample_id}", use_cache=False)
            return {"status": "success", "data": data, "mutations": data.get("mutations", [])}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def fetch_cancer_types(self) -> Dict[str, Any]:
        try:
            data = self._make_request("cancer_types", use_cache=False)
            types = data.get("cancer_types", [])
            return {
                "status": "success",
                "data": types,
                "cancer_types": types,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def parse_mutation_data(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for m in raw_data.get("mutations", []):
            out.append(
                {
                    "gene": m.get("gene_name", ""),
                    "mutation_id": m.get("mutation_id", ""),
                    "mutation_cds": m.get("mutation_cds", ""),
                    "mutation_aa": m.get("mutation_aa", ""),
                    "tumour_site": m.get("tumour_site", ""),
                }
            )
        return out

    def clear_cache(self):
        """Clear all cached responses."""
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    os.remove(os.path.join(self.cache_dir, filename))
            logger.info("COSMIC cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")


# Utility functions for common operations

def fetch_cancer_genes(cancer_type: str, fetcher: Optional[COSMICFetcher] = None) -> pd.DataFrame:
    """
    Fetch cancer genes for a specific cancer type.
    
    Args:
        cancer_type: Cancer type
        fetcher: Optional COSMICFetcher instance
        
    Returns:
        DataFrame with cancer gene data
    """
    if fetcher is None:
        fetcher = COSMICFetcher()
    
    genes = fetcher.get_cancer_gene_census()
    gene_df = pd.DataFrame(genes)
    
    if cancer_type and not gene_df.empty:
        # Filter by cancer type if specified
        gene_df = gene_df[gene_df['cancer_types'].str.contains(cancer_type, case=False, na=False)]
    
    return gene_df


def fetch_mutation_summary(gene_symbol: str, fetcher: Optional[COSMICFetcher] = None) -> Dict[str, Any]:
    """
    Fetch comprehensive mutation summary for a gene.
    
    Args:
        gene_symbol: Gene symbol
        fetcher: Optional COSMICFetcher instance
        
    Returns:
        Dictionary with mutation summary
    """
    if fetcher is None:
        fetcher = COSMICFetcher()
    
    summary = {
        'gene': gene_symbol,
        'mutations': fetcher.get_mutations_by_gene(gene_symbol),
        'frequency': fetcher.get_mutation_frequency(gene_symbol),
        'drug_sensitivity': fetcher.get_drug_sensitivity_data(gene_symbol),
        'cancer_gene_info': fetcher.get_cancer_gene_census(gene_symbol)
    }
    
    return summary


# Backwards-compatible alias for tests and older imports
CosmicFetcher = COSMICFetcher

# Export the main class and utility functions
__all__ = [
    "COSMICFetcher",
    "CosmicFetcher",
    "fetch_cancer_genes",
    "fetch_mutation_summary",
]
