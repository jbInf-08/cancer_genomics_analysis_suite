"""
ClinVar Database Synchronization

This module provides integration with the ClinVar database for synchronizing
clinical variant annotations, pathogenicity assessments, and clinical
significance data for cancer genomics research.

Features:
- Clinical variant annotation synchronization
- Pathogenicity assessment updates
- Clinical significance data retrieval
- Variant interpretation tracking
- Batch synchronization and updates
- Conflict resolution and validation
- Progress tracking and logging

API Documentation: https://www.ncbi.nlm.nih.gov/clinvar/docs/api/
"""

import hashlib
import json
import logging
import os
import sqlite3
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode, urljoin

import pandas as pd
import requests

logger = logging.getLogger(__name__)


@dataclass
class ClinVarVariant:
    """Data class for ClinVar variant information."""
    variant_id: str
    gene_symbol: str
    variant_name: str
    chromosome: str
    position: int
    ref_allele: str
    alt_allele: str
    clinical_significance: str
    pathogenicity: str
    review_status: str
    last_evaluated: Optional[datetime]
    condition: str
    phenotype: str
    inheritance: str
    age_of_onset: str
    prevalence: str
    penetrance: str
    modifiers: str
    evidence: List[Dict[str, Any]]
    submissions: List[Dict[str, Any]]


class ClinVarSync:
    """
    Client for synchronizing data with the ClinVar database.
    
    This class provides methods to retrieve and synchronize clinical
    variant annotations, pathogenicity assessments, and related data.
    """
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    CLINVAR_URL = "https://www.ncbi.nlm.nih.gov/clinvar/"
    
    def __init__(self, api_key: Optional[str] = None, cache_dir: str = "cache/clinvar"):
        """
        Initialize ClinVar synchronizer.
        
        Args:
            api_key: NCBI API key (optional but recommended)
            cache_dir: Directory for caching responses
        """
        self.api_key = api_key
        self.cache_dir = cache_dir
        self.session = requests.Session()
        self.rate_limit_delay = 0.34  # NCBI rate limit: 3 requests per second
        self.last_request_time = 0
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        
        # Set up session headers
        self.session.headers.update({
            'User-Agent': 'CancerGenomicsSuite/1.0',
            'Accept': 'application/xml'
        })
        
        # Initialize local database for tracking
        self._init_local_db()
    
    def _init_local_db(self):
        """Initialize local SQLite database for tracking variants."""
        db_path = os.path.join(self.cache_dir, 'clinvar_sync.db')
        self.db_path = db_path
        
        with sqlite3.connect(db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS variants (
                    variant_id TEXT PRIMARY KEY,
                    gene_symbol TEXT,
                    variant_name TEXT,
                    chromosome TEXT,
                    position INTEGER,
                    ref_allele TEXT,
                    alt_allele TEXT,
                    clinical_significance TEXT,
                    pathogenicity TEXT,
                    review_status TEXT,
                    last_evaluated TEXT,
                    condition TEXT,
                    phenotype TEXT,
                    inheritance TEXT,
                    age_of_onset TEXT,
                    prevalence TEXT,
                    penetrance TEXT,
                    modifiers TEXT,
                    evidence TEXT,
                    submissions TEXT,
                    last_updated TEXT,
                    sync_status TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    operation TEXT,
                    variant_id TEXT,
                    status TEXT,
                    message TEXT
                )
            ''')
    
    @staticmethod
    def _build_query_params(d: Dict[str, Any]) -> Dict[str, Any]:
        return dict(d)

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
    
    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Get cached XML response if available."""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.xml")
        
        if os.path.exists(cache_file):
            try:
                # Check if cache is still valid (7 days for ClinVar)
                cache_time = os.path.getmtime(cache_file)
                if time.time() - cache_time < 7 * 24 * 3600:  # 7 days
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        return f.read()
            except Exception as e:
                logger.warning(f"Failed to read cache file {cache_file}: {e}")
        
        return None
    
    def _cache_response(self, cache_key: str, xml_content: str):
        """Cache XML response data."""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.xml")
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(xml_content)
        except Exception as e:
            logger.warning(f"Failed to cache response to {cache_file}: {e}")
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None, 
                     use_cache: bool = True) -> str:
        """
        Make API request with rate limiting and caching.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            use_cache: Whether to use cached responses
            
        Returns:
            XML response content
        """
        params = params or {}
        if self.api_key:
            params['api_key'] = self.api_key
        
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
        url = urljoin(self.BASE_URL, endpoint)
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            xml_content = response.text
            
            # Cache successful response
            if use_cache:
                self._cache_response(cache_key, xml_content)
            
            return xml_content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {endpoint}: {e}")
            raise
    
    def search_variants(self, query: str, max_results: int = 100) -> List[str]:
        """
        Search for ClinVar variants using text query.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of ClinVar variant IDs
        """
        params = {
            'db': 'clinvar',
            'term': query,
            'retmax': min(max_results, 10000),  # NCBI limit
            'retmode': 'xml'
        }
        
        try:
            xml_content = self._make_request('esearch.fcgi', params)
            root = ET.fromstring(xml_content)
            
            variant_ids = []
            for id_elem in root.findall('.//Id'):
                variant_ids.append(id_elem.text)
            
            return variant_ids
            
        except Exception as e:
            logger.error(f"Failed to search variants with query '{query}': {e}")
            return []
    
    def get_variant_details(self, variant_id: str) -> Optional[ClinVarVariant]:
        """
        Get detailed information for a ClinVar variant.
        
        Args:
            variant_id: ClinVar variant ID
            
        Returns:
            ClinVarVariant object or None if not found
        """
        params = {
            'db': 'clinvar',
            'id': variant_id,
            'retmode': 'xml'
        }
        
        try:
            xml_content = self._make_request('efetch.fcgi', params)
            return self._parse_variant_xml(xml_content, variant_id)
            
        except Exception as e:
            logger.error(f"Failed to fetch variant details for {variant_id}: {e}")
            return None
    
    def _parse_variant_xml(self, xml_content: str, variant_id: str) -> Optional[ClinVarVariant]:
        """
        Parse ClinVar XML response into ClinVarVariant object.
        
        Args:
            xml_content: XML response content
            variant_id: Variant ID
            
        Returns:
            ClinVarVariant object or None
        """
        try:
            root = ET.fromstring(xml_content)
            
            # Find the variant record
            variant_elem = root.find('.//VariationArchive')
            if variant_elem is None:
                return None
            
            # Extract basic variant information
            gene_symbol = self._extract_text(variant_elem, './/Gene/Symbol')
            variant_name = self._extract_text(variant_elem, './/VariationName')
            
            # Extract genomic coordinates
            location_elem = variant_elem.find('.//Location')
            chromosome = self._extract_text(location_elem, './/Chr')
            position = self._extract_int(location_elem, './/Start')
            ref_allele = self._extract_text(location_elem, './/RefAllele')
            alt_allele = self._extract_text(location_elem, './/AltAllele')
            
            # Extract clinical information
            clinical_elem = variant_elem.find('.//ClinicalAssertion')
            clinical_significance = self._extract_text(clinical_elem, './/ClinicalSignificance/Description')
            review_status = self._extract_text(clinical_elem, './/ReviewStatus')
            last_evaluated = self._extract_text(clinical_elem, './/DateLastEvaluated')
            
            # Extract condition information
            condition = self._extract_text(clinical_elem, './/Condition/Name')
            phenotype = self._extract_text(clinical_elem, './/PhenotypeList/Phenotype/Name')
            
            # Extract inheritance and other details
            inheritance = self._extract_text(clinical_elem, './/ModeOfInheritance')
            age_of_onset = self._extract_text(clinical_elem, './/AgeOfOnset')
            prevalence = self._extract_text(clinical_elem, './/Prevalence')
            penetrance = self._extract_text(clinical_elem, './/Penetrance')
            modifiers = self._extract_text(clinical_elem, './/Modifiers')
            
            # Extract evidence and submissions
            evidence = self._extract_evidence_list(clinical_elem)
            submissions = self._extract_submissions_list(clinical_elem)
            
            # Determine pathogenicity
            pathogenicity = self._determine_pathogenicity(clinical_significance)
            
            return ClinVarVariant(
                variant_id=variant_id,
                gene_symbol=gene_symbol or '',
                variant_name=variant_name or '',
                chromosome=chromosome or '',
                position=position or 0,
                ref_allele=ref_allele or '',
                alt_allele=alt_allele or '',
                clinical_significance=clinical_significance or '',
                pathogenicity=pathogenicity,
                review_status=review_status or '',
                last_evaluated=self._parse_date(last_evaluated) if last_evaluated else None,
                condition=condition or '',
                phenotype=phenotype or '',
                inheritance=inheritance or '',
                age_of_onset=age_of_onset or '',
                prevalence=prevalence or '',
                penetrance=penetrance or '',
                modifiers=modifiers or '',
                evidence=evidence,
                submissions=submissions
            )
            
        except Exception as e:
            logger.error(f"Failed to parse variant XML for {variant_id}: {e}")
            return None
    
    def _extract_text(self, elem: ET.Element, xpath: str) -> Optional[str]:
        """Extract text content from XML element."""
        if elem is None:
            return None
        
        target_elem = elem.find(xpath)
        return target_elem.text if target_elem is not None else None
    
    def _extract_int(self, elem: ET.Element, xpath: str) -> Optional[int]:
        """Extract integer content from XML element."""
        text = self._extract_text(elem, xpath)
        try:
            return int(text) if text else None
        except ValueError:
            return None
    
    def _extract_evidence_list(self, elem: ET.Element) -> List[Dict[str, Any]]:
        """Extract evidence list from XML element."""
        evidence_list = []
        
        for evidence_elem in elem.findall('.//Evidence'):
            evidence = {
                'type': self._extract_text(evidence_elem, './/Type'),
                'description': self._extract_text(evidence_elem, './/Description'),
                'source': self._extract_text(evidence_elem, './/Source')
            }
            evidence_list.append(evidence)
        
        return evidence_list
    
    def _extract_submissions_list(self, elem: ET.Element) -> List[Dict[str, Any]]:
        """Extract submissions list from XML element."""
        submissions_list = []
        
        for submission_elem in elem.findall('.//Submission'):
            submission = {
                'submitter': self._extract_text(submission_elem, './/SubmitterName'),
                'date': self._extract_text(submission_elem, './/SubmissionDate'),
                'status': self._extract_text(submission_elem, './/SubmissionStatus')
            }
            submissions_list.append(submission)
        
        return submissions_list
    
    def _determine_pathogenicity(self, clinical_significance: str) -> str:
        """Determine pathogenicity from clinical significance."""
        if not clinical_significance:
            return 'unknown'
        
        significance_lower = clinical_significance.lower()
        
        if any(term in significance_lower for term in ['pathogenic', 'likely pathogenic']):
            return 'pathogenic'
        elif any(term in significance_lower for term in ['benign', 'likely benign']):
            return 'benign'
        elif 'uncertain' in significance_lower or 'vus' in significance_lower:
            return 'uncertain'
        else:
            return 'unknown'
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object."""
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            try:
                return datetime.strptime(date_str, '%Y-%m')
            except ValueError:
                return None
    
    def sync_variant(self, variant_id: str) -> bool:
        """
        Synchronize a single variant with local database.
        
        Args:
            variant_id: ClinVar variant ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get variant details from ClinVar
            variant = self.get_variant_details(variant_id)
            if not variant:
                self._log_sync_operation('sync_variant', variant_id, 'failed', 'Variant not found')
                return False
            
            # Store in local database
            self._store_variant(variant)
            
            self._log_sync_operation('sync_variant', variant_id, 'success', 'Variant synchronized')
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync variant {variant_id}: {e}")
            self._log_sync_operation('sync_variant', variant_id, 'failed', str(e))
            return False
    
    def _store_variant(self, variant: ClinVarVariant):
        """Store variant in local database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO variants (
                    variant_id, gene_symbol, variant_name, chromosome, position,
                    ref_allele, alt_allele, clinical_significance, pathogenicity,
                    review_status, last_evaluated, condition, phenotype, inheritance,
                    age_of_onset, prevalence, penetrance, modifiers, evidence,
                    submissions, last_updated, sync_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                variant.variant_id, variant.gene_symbol, variant.variant_name,
                variant.chromosome, variant.position, variant.ref_allele,
                variant.alt_allele, variant.clinical_significance, variant.pathogenicity,
                variant.review_status, variant.last_evaluated.isoformat() if variant.last_evaluated else None,
                variant.condition, variant.phenotype, variant.inheritance,
                variant.age_of_onset, variant.prevalence, variant.penetrance,
                variant.modifiers, json.dumps(variant.evidence),
                json.dumps(variant.submissions), datetime.now().isoformat(), 'synced'
            ))
    
    def _log_sync_operation(self, operation: str, variant_id: str, status: str, message: str):
        """Log synchronization operation."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO sync_log (timestamp, operation, variant_id, status, message)
                VALUES (?, ?, ?, ?, ?)
            ''', (datetime.now().isoformat(), operation, variant_id, status, message))
    
    def batch_sync_variants(self, variant_ids: List[str]) -> Dict[str, bool]:
        """
        Batch synchronize multiple variants.
        
        Args:
            variant_ids: List of ClinVar variant IDs
            
        Returns:
            Dictionary mapping variant IDs to sync success status
        """
        results = {}
        
        for variant_id in variant_ids:
            logger.info(f"Synchronizing variant: {variant_id}")
            success = self.sync_variant(variant_id)
            results[variant_id] = success
            
            # Add delay between requests
            time.sleep(self.rate_limit_delay)
        
        return results
    
    def get_local_variants(self, gene_symbol: Optional[str] = None) -> List[ClinVarVariant]:
        """
        Get variants from local database.
        
        Args:
            gene_symbol: Optional gene symbol filter
            
        Returns:
            List of ClinVarVariant objects
        """
        with sqlite3.connect(self.db_path) as conn:
            if gene_symbol:
                cursor = conn.execute(
                    'SELECT * FROM variants WHERE gene_symbol = ?', (gene_symbol,)
                )
            else:
                cursor = conn.execute('SELECT * FROM variants')
            
            variants = []
            for row in cursor.fetchall():
                variant = self._row_to_variant(row)
                if variant:
                    variants.append(variant)
            
            return variants
    
    def _row_to_variant(self, row: Tuple) -> Optional[ClinVarVariant]:
        """Convert database row to ClinVarVariant object."""
        try:
            return ClinVarVariant(
                variant_id=row[0],
                gene_symbol=row[1],
                variant_name=row[2],
                chromosome=row[3],
                position=row[4],
                ref_allele=row[5],
                alt_allele=row[6],
                clinical_significance=row[7],
                pathogenicity=row[8],
                review_status=row[9],
                last_evaluated=datetime.fromisoformat(row[10]) if row[10] else None,
                condition=row[11],
                phenotype=row[12],
                inheritance=row[13],
                age_of_onset=row[14],
                prevalence=row[15],
                penetrance=row[16],
                modifiers=row[17],
                evidence=json.loads(row[18]) if row[18] else [],
                submissions=json.loads(row[19]) if row[19] else []
            )
        except Exception as e:
            logger.error(f"Failed to convert row to variant: {e}")
            return None
    
    def export_to_dataframe(self, variants: List[ClinVarVariant]) -> pd.DataFrame:
        """
        Convert variants to pandas DataFrame.
        
        Args:
            variants: List of ClinVarVariant objects
            
        Returns:
            DataFrame with variant data
        """
        if not variants:
            return pd.DataFrame()
        
        data = []
        for variant in variants:
            data.append({
                'variant_id': variant.variant_id,
                'gene_symbol': variant.gene_symbol,
                'variant_name': variant.variant_name,
                'chromosome': variant.chromosome,
                'position': variant.position,
                'ref_allele': variant.ref_allele,
                'alt_allele': variant.alt_allele,
                'clinical_significance': variant.clinical_significance,
                'pathogenicity': variant.pathogenicity,
                'review_status': variant.review_status,
                'last_evaluated': variant.last_evaluated,
                'condition': variant.condition,
                'phenotype': variant.phenotype,
                'inheritance': variant.inheritance,
                'age_of_onset': variant.age_of_onset,
                'prevalence': variant.prevalence,
                'penetrance': variant.penetrance,
                'modifiers': variant.modifiers,
                'evidence_count': len(variant.evidence),
                'submission_count': len(variant.submissions)
            })
        
        return pd.DataFrame(data)
    
    def get_sync_statistics(self) -> Dict[str, Any]:
        """
        Get synchronization statistics.
        
        Returns:
            Dictionary with sync statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            # Get variant counts
            total_variants = conn.execute('SELECT COUNT(*) FROM variants').fetchone()[0]
            synced_variants = conn.execute(
                'SELECT COUNT(*) FROM variants WHERE sync_status = "synced"'
            ).fetchone()[0]
            
            # Get recent sync operations
            recent_syncs = conn.execute('''
                SELECT COUNT(*) FROM sync_log 
                WHERE timestamp > datetime('now', '-7 days')
            ''').fetchone()[0]
            
            # Get success rate
            successful_syncs = conn.execute('''
                SELECT COUNT(*) FROM sync_log 
                WHERE status = 'success' AND timestamp > datetime('now', '-7 days')
            ''').fetchone()[0]
            
            success_rate = (successful_syncs / recent_syncs * 100) if recent_syncs > 0 else 0
            
            return {
                'total_variants': total_variants,
                'synced_variants': synced_variants,
                'recent_syncs': recent_syncs,
                'success_rate': success_rate
            }
    
    def clear_cache(self):
        """Clear all cached responses."""
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.xml'):
                    os.remove(os.path.join(self.cache_dir, filename))
            logger.info("ClinVar cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")


# Utility functions for common operations

def sync_gene_variants(gene_symbol: str, sync_client: Optional[ClinVarSync] = None) -> List[ClinVarVariant]:
    """
    Synchronize all variants for a specific gene.
    
    Args:
        gene_symbol: Gene symbol
        sync_client: Optional ClinVarSync instance
        
    Returns:
        List of synchronized variants
    """
    if sync_client is None:
        sync_client = ClinVarSync()
    
    # Search for variants in the gene
    query = f"{gene_symbol}[gene]"
    variant_ids = sync_client.search_variants(query)
    
    # Sync all found variants
    results = sync_client.batch_sync_variants(variant_ids)
    
    # Return successfully synced variants
    successful_ids = [vid for vid, success in results.items() if success]
    return sync_client.get_local_variants(gene_symbol)


def get_pathogenic_variants(gene_symbol: str, sync_client: Optional[ClinVarSync] = None) -> List[ClinVarVariant]:
    """
    Get pathogenic variants for a specific gene.
    
    Args:
        gene_symbol: Gene symbol
        sync_client: Optional ClinVarSync instance
        
    Returns:
        List of pathogenic variants
    """
    if sync_client is None:
        sync_client = ClinVarSync()
    
    variants = sync_client.get_local_variants(gene_symbol)
    return [v for v in variants if v.pathogenicity == 'pathogenic']


# Export the main class and utility functions
__all__ = [
    'ClinVarSync',
    'ClinVarVariant',
    'sync_gene_variants',
    'get_pathogenic_variants'
]
