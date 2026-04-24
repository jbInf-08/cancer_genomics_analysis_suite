"""
Scopus Research Database Client

This module provides integration with the Scopus research database for
searching and retrieving scientific literature, citations, and research
metrics for cancer genomics research.

Features:
- Literature search and discovery
- Citation analysis and metrics
- Author and affiliation information
- Journal impact factors and rankings
- Research trend analysis
- Reference management
- Export functionality

API Documentation: https://dev.elsevier.com/sc_apis.html
"""

import hashlib
import json
import logging
import os
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
class ScopusArticle:
    """Data class for Scopus article information."""
    scopus_id: str
    eid: str
    title: str
    abstract: str
    authors: List[Dict[str, Any]]
    affiliations: List[Dict[str, Any]]
    journal: str
    journal_issn: str
    volume: str
    issue: str
    pages: str
    publication_date: datetime
    doi: str
    pmid: str
    keywords: List[str]
    subject_areas: List[str]
    citation_count: int
    references: List[str]
    funding: List[Dict[str, Any]]
    language: str
    document_type: str
    open_access: bool
    source_type: str


@dataclass
class ScopusAuthor:
    """Data class for Scopus author information."""
    author_id: str
    name: str
    given_name: str
    surname: str
    initials: str
    affiliation_ids: List[str]
    h_index: int
    citation_count: int
    document_count: int
    co_author_count: int
    subject_areas: List[str]
    orcid: str
    scopus_url: str


@dataclass
class ScopusAffiliation:
    """Data class for Scopus affiliation information."""
    affiliation_id: str
    name: str
    city: str
    country: str
    address: str
    postal_code: str
    url: str
    document_count: int
    author_count: int


class ScopusClient:
    """
    Client for accessing the Scopus research database.
    
    This class provides methods to search and retrieve scientific
    literature, citations, and research metrics from Scopus.
    """
    
    BASE_URL = "https://api.elsevier.com/content/"
    SEARCH_URL = "https://api.elsevier.com/content/search/"
    
    def __init__(self, api_key: Optional[str] = None, insttoken: Optional[str] = None, 
                 cache_dir: str = "cache/scopus"):
        """
        Initialize Scopus client.
        
        Args:
            api_key: Scopus API key (optional in tests; required for live API)
            insttoken: Institution token (optional)
            cache_dir: Directory for caching responses
        """
        self.api_key = api_key
        self.insttoken = insttoken
        self.cache_dir = cache_dir
        self.session = requests.Session()
        self.rate_limit_delay = 0.2  # 5 requests per second
        self.last_request_time = 0
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        
        # Set up session headers
        headers = {
            'User-Agent': 'CancerGenomicsSuite/1.0',
            'Accept': 'application/json',
            'X-ELS-APIKey': api_key or '',
        }
        
        if insttoken:
            headers['X-ELS-Insttoken'] = insttoken
        
        self.session.headers.update(headers)

    @property
    def base_url(self) -> str:
        return str(self.BASE_URL)

    def get_author_publications(
        self, author_id: str, max_results: int = 100
    ) -> List["ScopusArticle"]:
        q = f"AUTH({author_id})"
        return self.search_articles(q, max_results=max_results)

    def parse_article_data(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for ent in raw_data.get("search-results", {}).get("entry", []):
            try:
                citations = int(str(ent.get("citedby-count", "0")))
            except ValueError:
                citations = 0
            out.append(
                {
                    "title": ent.get("dc:title", ""),
                    "author": ent.get("dc:creator", ""),
                    "journal": ent.get("prism:publicationName", ""),
                    "citations": citations,
                }
            )
        return out

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
        url = urljoin(self.SEARCH_URL, endpoint)
        
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
    
    def search_articles(self, query: str, 
                       date_range: Optional[Tuple[str, str]] = None,
                       subject_areas: Optional[List[str]] = None,
                       document_types: Optional[List[str]] = None,
                       max_results: int = 100) -> List[ScopusArticle]:
        """
        Search for articles in Scopus.
        
        Args:
            query: Search query
            date_range: Optional date range tuple (start_date, end_date)
            subject_areas: Optional list of subject areas
            document_types: Optional list of document types
            max_results: Maximum number of results
            
        Returns:
            List of ScopusArticle objects
        """
        params = {
            'query': query,
            'count': min(max_results, 200),  # Scopus API limit
            'start': 0,
            'sort': 'pubyear'
        }
        
        # Add date range filter
        if date_range:
            start_date, end_date = date_range
            params['date'] = f"{start_date}-{end_date}"
        
        # Add subject area filter
        if subject_areas:
            subject_query = ' OR '.join([f'SUBJAREA("{area}")' for area in subject_areas])
            params['query'] = f"({query}) AND ({subject_query})"
        
        # Add document type filter
        if document_types:
            doc_type_query = ' OR '.join([f'DOCTYPE("{doc_type}")' for doc_type in document_types])
            params['query'] = f"({params['query']}) AND ({doc_type_query})"
        
        try:
            data = self._make_request('scopus', params)
            articles = []
            
            for entry in data.get('search-results', {}).get('entry', []):
                article = self._parse_article(entry)
                if article:
                    articles.append(article)
            
            return articles
            
        except Exception as e:
            logger.error(f"Failed to search articles with query '{query}': {e}")
            return []
    
    def get_article_details(self, scopus_id: str) -> Optional[ScopusArticle]:
        """
        Get detailed information for a specific article.
        
        Args:
            scopus_id: Scopus article ID
            
        Returns:
            ScopusArticle object or None if not found
        """
        try:
            data = self._make_request(f'scopus/{scopus_id}')
            entry = data.get('abstracts-retrieval-response', {})
            return self._parse_article_details(entry)
            
        except Exception as e:
            logger.error(f"Failed to fetch article details for {scopus_id}: {e}")
            return None
    
    def _parse_article(self, entry: Dict[str, Any]) -> Optional[ScopusArticle]:
        """
        Parse article entry from search results.
        
        Args:
            entry: Article entry from API response
            
        Returns:
            ScopusArticle object or None
        """
        try:
            scopus_id = entry.get('dc:identifier', '').replace('SCOPUS_ID:', '')
            eid = entry.get('eid', '')
            title = entry.get('dc:title', '')
            
            # Extract authors
            authors = []
            for author in entry.get('author', []):
                author_info = {
                    'author_id': author.get('@auid', ''),
                    'name': author.get('authname', ''),
                    'given_name': author.get('given-name', ''),
                    'surname': author.get('surname', ''),
                    'initials': author.get('initials', ''),
                    'affiliation_ids': [aff.get('@id', '') for aff in author.get('affiliation', [])]
                }
                authors.append(author_info)
            
            # Extract affiliations
            affiliations = []
            for aff in entry.get('affiliation', []):
                aff_info = {
                    'affiliation_id': aff.get('@id', ''),
                    'name': aff.get('affilname', ''),
                    'city': aff.get('affiliation-city', ''),
                    'country': aff.get('affiliation-country', '')
                }
                affiliations.append(aff_info)
            
            # Extract publication information
            journal = entry.get('prism:publicationName', '')
            journal_issn = entry.get('prism:issn', '')
            volume = entry.get('prism:volume', '')
            issue = entry.get('prism:issueIdentifier', '')
            pages = entry.get('prism:pageRange', '')
            
            # Parse publication date
            pub_date_str = entry.get('prism:coverDate', '')
            publication_date = self._parse_date(pub_date_str)
            
            # Extract identifiers
            doi = entry.get('prism:doi', '')
            pmid = entry.get('pubmed-id', '')
            
            # Extract keywords and subject areas
            keywords = [kw.get('$', '') for kw in entry.get('authkeywords', [])]
            subject_areas = [sa.get('$', '') for sa in entry.get('subject-area', [])]
            
            # Extract citation count
            citation_count = int(entry.get('citedby-count', 0))
            
            # Extract other information
            language = entry.get('prism:language', '')
            document_type = entry.get('subtypeDescription', '')
            source_type = entry.get('source-type', '')
            
            return ScopusArticle(
                scopus_id=scopus_id,
                eid=eid,
                title=title,
                abstract='',  # Abstract not available in search results
                authors=authors,
                affiliations=affiliations,
                journal=journal,
                journal_issn=journal_issn,
                volume=volume,
                issue=issue,
                pages=pages,
                publication_date=publication_date,
                doi=doi,
                pmid=pmid,
                keywords=keywords,
                subject_areas=subject_areas,
                citation_count=citation_count,
                references=[],
                funding=[],
                language=language,
                document_type=document_type,
                open_access=False,
                source_type=source_type
            )
            
        except Exception as e:
            logger.error(f"Failed to parse article: {e}")
            return None
    
    def _parse_article_details(self, entry: Dict[str, Any]) -> Optional[ScopusArticle]:
        """
        Parse detailed article information.
        
        Args:
            entry: Detailed article entry from API response
            
        Returns:
            ScopusArticle object or None
        """
        try:
            # Extract basic information
            scopus_id = entry.get('coredata', {}).get('dc:identifier', '').replace('SCOPUS_ID:', '')
            eid = entry.get('coredata', {}).get('eid', '')
            title = entry.get('coredata', {}).get('dc:title', '')
            abstract = entry.get('coredata', {}).get('dc:description', '')
            
            # Extract authors with detailed information
            authors = []
            for author in entry.get('authors', {}).get('author', []):
                author_info = {
                    'author_id': author.get('@auid', ''),
                    'name': author.get('preferred-name', {}).get('ce:indexed-name', ''),
                    'given_name': author.get('preferred-name', {}).get('ce:given-name', ''),
                    'surname': author.get('preferred-name', {}).get('ce:surname', ''),
                    'initials': author.get('preferred-name', {}).get('ce:initials', ''),
                    'affiliation_ids': [aff.get('@id', '') for aff in author.get('affiliation', [])]
                }
                authors.append(author_info)
            
            # Extract affiliations with detailed information
            affiliations = []
            for aff in entry.get('affiliation', []):
                aff_info = {
                    'affiliation_id': aff.get('@id', ''),
                    'name': aff.get('affilname', ''),
                    'city': aff.get('affiliation-city', ''),
                    'country': aff.get('affiliation-country', ''),
                    'address': aff.get('address', ''),
                    'postal_code': aff.get('postal-code', ''),
                    'url': aff.get('url', '')
                }
                affiliations.append(aff_info)
            
            # Extract publication information
            coredata = entry.get('coredata', {})
            journal = coredata.get('prism:publicationName', '')
            journal_issn = coredata.get('prism:issn', '')
            volume = coredata.get('prism:volume', '')
            issue = coredata.get('prism:issueIdentifier', '')
            pages = coredata.get('prism:pageRange', '')
            
            # Parse publication date
            pub_date_str = coredata.get('prism:coverDate', '')
            publication_date = self._parse_date(pub_date_str)
            
            # Extract identifiers
            doi = coredata.get('prism:doi', '')
            pmid = coredata.get('pubmed-id', '')
            
            # Extract keywords and subject areas
            keywords = [kw.get('$', '') for kw in coredata.get('authkeywords', [])]
            subject_areas = [sa.get('$', '') for sa in coredata.get('subject-area', [])]
            
            # Extract citation count
            citation_count = int(coredata.get('citedby-count', 0))
            
            # Extract references
            references = []
            for ref in entry.get('references', {}).get('reference', []):
                ref_id = ref.get('@id', '')
                if ref_id:
                    references.append(ref_id)
            
            # Extract funding information
            funding = []
            for fund in entry.get('funding', {}).get('funding-list', {}).get('funding', []):
                fund_info = {
                    'agency': fund.get('funding-agency', {}).get('funding-agency-name', ''),
                    'grant_number': fund.get('funding-agency', {}).get('funding-agency-grant-number', ''),
                    'country': fund.get('funding-agency', {}).get('funding-agency-country', '')
                }
                funding.append(fund_info)
            
            # Extract other information
            language = coredata.get('prism:language', '')
            document_type = coredata.get('subtypeDescription', '')
            source_type = coredata.get('source-type', '')
            open_access = coredata.get('openaccess', 0) == 1
            
            return ScopusArticle(
                scopus_id=scopus_id,
                eid=eid,
                title=title,
                abstract=abstract,
                authors=authors,
                affiliations=affiliations,
                journal=journal,
                journal_issn=journal_issn,
                volume=volume,
                issue=issue,
                pages=pages,
                publication_date=publication_date,
                doi=doi,
                pmid=pmid,
                keywords=keywords,
                subject_areas=subject_areas,
                citation_count=citation_count,
                references=references,
                funding=funding,
                language=language,
                document_type=document_type,
                open_access=open_access,
                source_type=source_type
            )
            
        except Exception as e:
            logger.error(f"Failed to parse article details: {e}")
            return None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime object."""
        if not date_str:
            return None
        
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            try:
                return datetime.strptime(date_str, '%Y')
            except ValueError:
                return None
    
    def get_author_details(self, author_id: str) -> Optional[ScopusAuthor]:
        """
        Get detailed information for a specific author.
        
        Args:
            author_id: Scopus author ID
            
        Returns:
            ScopusAuthor object or None if not found
        """
        try:
            data = self._make_request(f'author/{author_id}')
            entry = data.get('author-retrieval-response', {}).get('author-profile', {})
            return self._parse_author(entry)
            
        except Exception as e:
            logger.error(f"Failed to fetch author details for {author_id}: {e}")
            return None
    
    def _parse_author(self, entry: Dict[str, Any]) -> Optional[ScopusAuthor]:
        """
        Parse author information from API response.
        
        Args:
            entry: Author entry from API response
            
        Returns:
            ScopusAuthor object or None
        """
        try:
            author_id = entry.get('@auid', '')
            name = entry.get('preferred-name', {}).get('ce:indexed-name', '')
            given_name = entry.get('preferred-name', {}).get('ce:given-name', '')
            surname = entry.get('preferred-name', {}).get('ce:surname', '')
            initials = entry.get('preferred-name', {}).get('ce:initials', '')
            
            # Extract affiliation IDs
            affiliation_ids = [aff.get('@id', '') for aff in entry.get('affiliation-history', {}).get('affiliation', [])]
            
            # Extract metrics
            h_index = int(entry.get('h-index', 0))
            citation_count = int(entry.get('coredata', {}).get('citation-count', 0))
            document_count = int(entry.get('coredata', {}).get('document-count', 0))
            co_author_count = int(entry.get('coauthor-count', 0))
            
            # Extract subject areas
            subject_areas = [sa.get('$', '') for sa in entry.get('subject-area', [])]
            
            # Extract ORCID
            orcid = entry.get('orcid', '')
            
            # Extract Scopus URL
            scopus_url = entry.get('coredata', {}).get('link', [{}])[0].get('@href', '')
            
            return ScopusAuthor(
                author_id=author_id,
                name=name,
                given_name=given_name,
                surname=surname,
                initials=initials,
                affiliation_ids=affiliation_ids,
                h_index=h_index,
                citation_count=citation_count,
                document_count=document_count,
                co_author_count=co_author_count,
                subject_areas=subject_areas,
                orcid=orcid,
                scopus_url=scopus_url
            )
            
        except Exception as e:
            logger.error(f"Failed to parse author: {e}")
            return None
    
    def get_affiliation_details(self, affiliation_id: str) -> Optional[ScopusAffiliation]:
        """
        Get detailed information for a specific affiliation.
        
        Args:
            affiliation_id: Scopus affiliation ID
            
        Returns:
            ScopusAffiliation object or None if not found
        """
        try:
            data = self._make_request(f'affiliation/{affiliation_id}')
            entry = data.get('affiliation-retrieval-response', {}).get('affiliation', {})
            return self._parse_affiliation(entry)
            
        except Exception as e:
            logger.error(f"Failed to fetch affiliation details for {affiliation_id}: {e}")
            return None
    
    def _parse_affiliation(self, entry: Dict[str, Any]) -> Optional[ScopusAffiliation]:
        """
        Parse affiliation information from API response.
        
        Args:
            entry: Affiliation entry from API response
            
        Returns:
            ScopusAffiliation object or None
        """
        try:
            affiliation_id = entry.get('@id', '')
            name = entry.get('affilname', '')
            city = entry.get('affiliation-city', '')
            country = entry.get('affiliation-country', '')
            address = entry.get('address', '')
            postal_code = entry.get('postal-code', '')
            url = entry.get('url', '')
            
            # Extract metrics
            document_count = int(entry.get('document-count', 0))
            author_count = int(entry.get('author-count', 0))
            
            return ScopusAffiliation(
                affiliation_id=affiliation_id,
                name=name,
                city=city,
                country=country,
                address=address,
                postal_code=postal_code,
                url=url,
                document_count=document_count,
                author_count=author_count
            )
            
        except Exception as e:
            logger.error(f"Failed to parse affiliation: {e}")
            return None
    
    def search_authors(self, query: str, max_results: int = 100) -> List[ScopusAuthor]:
        """
        Search for authors in Scopus.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of ScopusAuthor objects
        """
        params = {
            'query': f'AUTH({query})',
            'count': min(max_results, 200),
            'start': 0
        }
        
        try:
            data = self._make_request('scopus', params)
            authors = []
            
            for entry in data.get('search-results', {}).get('entry', []):
                author = self._parse_author_search_result(entry)
                if author:
                    authors.append(author)
            
            return authors
            
        except Exception as e:
            logger.error(f"Failed to search authors with query '{query}': {e}")
            return []
    
    def _parse_author_search_result(self, entry: Dict[str, Any]) -> Optional[ScopusAuthor]:
        """
        Parse author from search results.
        
        Args:
            entry: Author entry from search results
            
        Returns:
            ScopusAuthor object or None
        """
        try:
            author_id = entry.get('dc:identifier', '').replace('AUTHOR_ID:', '')
            name = entry.get('preferred-name', {}).get('ce:indexed-name', '')
            given_name = entry.get('preferred-name', {}).get('ce:given-name', '')
            surname = entry.get('preferred-name', {}).get('ce:surname', '')
            initials = entry.get('preferred-name', {}).get('ce:initials', '')
            
            # Extract affiliation IDs
            affiliation_ids = [aff.get('@id', '') for aff in entry.get('affiliation', [])]
            
            # Extract metrics
            h_index = int(entry.get('h-index', 0))
            citation_count = int(entry.get('citedby-count', 0))
            document_count = int(entry.get('document-count', 0))
            co_author_count = int(entry.get('coauthor-count', 0))
            
            # Extract subject areas
            subject_areas = [sa.get('$', '') for sa in entry.get('subject-area', [])]
            
            # Extract ORCID
            orcid = entry.get('orcid', '')
            
            # Extract Scopus URL
            scopus_url = entry.get('link', [{}])[0].get('@href', '')
            
            return ScopusAuthor(
                author_id=author_id,
                name=name,
                given_name=given_name,
                surname=surname,
                initials=initials,
                affiliation_ids=affiliation_ids,
                h_index=h_index,
                citation_count=citation_count,
                document_count=document_count,
                co_author_count=co_author_count,
                subject_areas=subject_areas,
                orcid=orcid,
                scopus_url=scopus_url
            )
            
        except Exception as e:
            logger.error(f"Failed to parse author search result: {e}")
            return None
    
    def get_citation_metrics(self, scopus_id: str) -> Dict[str, Any]:
        """
        Get citation metrics for an article.
        
        Args:
            scopus_id: Scopus article ID
            
        Returns:
            Dictionary with citation metrics
        """
        try:
            data = self._make_request(f'scopus/{scopus_id}')
            coredata = data.get('abstracts-retrieval-response', {}).get('coredata', {})
            
            return {
                'citation_count': int(coredata.get('citedby-count', 0)),
                'h_index': int(coredata.get('h-index', 0)),
                'impact_factor': coredata.get('source', {}).get('sourcetitle', ''),
                'journal_rank': coredata.get('source', {}).get('sourcetitle', '')
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch citation metrics for {scopus_id}: {e}")
            return {}
    
    def export_articles_to_dataframe(self, articles: List[ScopusArticle]) -> pd.DataFrame:
        """
        Convert articles to pandas DataFrame.
        
        Args:
            articles: List of ScopusArticle objects
            
        Returns:
            DataFrame with article data
        """
        if not articles:
            return pd.DataFrame()
        
        data = []
        for article in articles:
            data.append({
                'scopus_id': article.scopus_id,
                'eid': article.eid,
                'title': article.title,
                'abstract': article.abstract,
                'authors': '; '.join([author['name'] for author in article.authors]),
                'journal': article.journal,
                'journal_issn': article.journal_issn,
                'volume': article.volume,
                'issue': article.issue,
                'pages': article.pages,
                'publication_date': article.publication_date,
                'doi': article.doi,
                'pmid': article.pmid,
                'keywords': '; '.join(article.keywords),
                'subject_areas': '; '.join(article.subject_areas),
                'citation_count': article.citation_count,
                'language': article.language,
                'document_type': article.document_type,
                'open_access': article.open_access,
                'source_type': article.source_type
            })
        
        return pd.DataFrame(data)
    
    def export_authors_to_dataframe(self, authors: List[ScopusAuthor]) -> pd.DataFrame:
        """
        Convert authors to pandas DataFrame.
        
        Args:
            authors: List of ScopusAuthor objects
            
        Returns:
            DataFrame with author data
        """
        if not authors:
            return pd.DataFrame()
        
        data = []
        for author in authors:
            data.append({
                'author_id': author.author_id,
                'name': author.name,
                'given_name': author.given_name,
                'surname': author.surname,
                'initials': author.initials,
                'h_index': author.h_index,
                'citation_count': author.citation_count,
                'document_count': author.document_count,
                'co_author_count': author.co_author_count,
                'subject_areas': '; '.join(author.subject_areas),
                'orcid': author.orcid,
                'scopus_url': author.scopus_url
            })
        
        return pd.DataFrame(data)
    
    def clear_cache(self):
        """Clear all cached responses."""
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    os.remove(os.path.join(self.cache_dir, filename))
            logger.info("Scopus cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")


# Utility functions for common operations

def search_cancer_genomics_literature(query: str, 
                                     client: Optional[ScopusClient] = None,
                                     max_results: int = 100) -> List[ScopusArticle]:
    """
    Search for cancer genomics literature.
    
    Args:
        query: Search query
        client: Optional ScopusClient instance
        max_results: Maximum number of results
        
    Returns:
        List of ScopusArticle objects
    """
    if client is None:
        # This would need to be configured with actual API key
        raise ValueError("ScopusClient instance required")
    
    # Add cancer genomics specific filters
    cancer_genomics_query = f"({query}) AND (cancer OR oncology OR tumor OR neoplasm) AND (genomics OR genetics OR molecular)"
    
    return client.search_articles(
        cancer_genomics_query,
        subject_areas=['Biochemistry, Genetics and Molecular Biology', 'Medicine'],
        document_types=['Article', 'Review'],
        max_results=max_results
    )


def get_author_publications(author_name: str, 
                           client: Optional[ScopusClient] = None,
                           max_results: int = 100) -> List[ScopusArticle]:
    """
    Get publications for a specific author.
    
    Args:
        author_name: Author name
        client: Optional ScopusClient instance
        max_results: Maximum number of results
        
    Returns:
        List of ScopusArticle objects
    """
    if client is None:
        raise ValueError("ScopusClient instance required")
    
    # Search for author first
    authors = client.search_authors(author_name, max_results=10)
    
    if not authors:
        return []
    
    # Get publications for the first matching author
    author_id = authors[0].author_id
    query = f"AUTH({author_id})"
    
    return client.search_articles(query, max_results=max_results)


# Export the main class and utility functions
__all__ = [
    'ScopusClient',
    'ScopusArticle',
    'ScopusAuthor',
    'ScopusAffiliation',
    'search_cancer_genomics_literature',
    'get_author_publications'
]
