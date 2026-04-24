"""
Article Scraper Module

This module provides comprehensive functionality for scraping and analyzing
scientific articles from various sources in cancer genomics research.
"""

import requests
import pandas as pd
import numpy as np
import json
import time
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from pathlib import Path
from datetime import datetime, timedelta
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import feedparser
from dataclasses import dataclass, asdict
import hashlib
import sqlite3
from contextlib import contextmanager
import xml.etree.ElementTree as ET
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Article:
    """Data class for storing article information."""
    title: str
    authors: List[str]
    abstract: str
    doi: Optional[str] = None
    pmid: Optional[str] = None
    url: Optional[str] = None
    journal: Optional[str] = None
    publication_date: Optional[str] = None
    keywords: List[str] = None
    citations: Optional[int] = None
    source: Optional[str] = None
    scraped_date: Optional[str] = None
    content: Optional[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.scraped_date is None:
            self.scraped_date = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert article to dictionary."""
        return asdict(self)
    
    def get_hash(self) -> str:
        """Get unique hash for article."""
        content = f"{self.title}{self.doi}{self.pmid}{self.url}"
        return hashlib.md5(content.encode()).hexdigest()


class ArticleScraper:
    """
    A comprehensive class for scraping scientific articles from various sources.
    """
    
    def __init__(self, db_path: str = "articles.db"):
        """
        Initialize the article scraper.
        
        Args:
            db_path: Path to SQLite database for storing articles
        """
        self.db_path = db_path
        self.session = self._create_session()
        self.articles = []
        self.scraping_stats = {
            'total_scraped': 0,
            'successful': 0,
            'failed': 0,
            'sources': {}
        }
        
        # Initialize database
        self._init_database()
        
        # Common headers for web scraping
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _init_database(self):
        """Initialize SQLite database for storing articles."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hash TEXT UNIQUE,
                    title TEXT,
                    authors TEXT,
                    abstract TEXT,
                    doi TEXT,
                    pmid TEXT,
                    url TEXT,
                    journal TEXT,
                    publication_date TEXT,
                    keywords TEXT,
                    citations INTEGER,
                    source TEXT,
                    scraped_date TEXT,
                    content TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS scraping_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    source TEXT,
                    action TEXT,
                    status TEXT,
                    message TEXT
                )
            ''')
    
    @contextmanager
    def get_db_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()
    
    def scrape_pubmed(self, 
                     query: str,
                     max_results: int = 100,
                     date_range: Tuple[str, str] = None) -> List[Article]:
        """
        Scrape articles from PubMed.
        
        Args:
            query: Search query
            max_results: Maximum number of results to retrieve
            date_range: Tuple of (start_date, end_date) in YYYY/MM/DD format
            
        Returns:
            List of Article objects
        """
        try:
            articles = []
            
            # Build PubMed API URL
            base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
            
            # Search for PMIDs
            search_url = f"{base_url}esearch.fcgi"
            search_params = {
                'db': 'pubmed',
                'term': query,
                'retmax': max_results,
                'retmode': 'json',
                'sort': 'relevance'
            }
            
            if date_range:
                search_params['mindate'] = date_range[0].replace('/', '')
                search_params['maxdate'] = date_range[1].replace('/', '')
            
            response = self.session.get(search_url, params=search_params, timeout=30)
            response.raise_for_status()
            
            search_data = response.json()
            pmids = search_data.get('esearchresult', {}).get('idlist', [])
            
            if not pmids:
                logger.info(f"No articles found for query: {query}")
                return articles
            
            # Fetch article details in batches
            batch_size = 200
            for i in range(0, len(pmids), batch_size):
                batch_pmids = pmids[i:i + batch_size]
                
                # Fetch article details
                fetch_url = f"{base_url}efetch.fcgi"
                fetch_params = {
                    'db': 'pubmed',
                    'id': ','.join(batch_pmids),
                    'retmode': 'xml'
                }
                
                response = self.session.get(fetch_url, params=fetch_params, timeout=30)
                response.raise_for_status()
                
                # Parse XML response
                root = ET.fromstring(response.content)
                
                for article in root.findall('.//PubmedArticle'):
                    try:
                        article_data = self._parse_pubmed_article(article)
                        if article_data:
                            articles.append(article_data)
                    except Exception as e:
                        logger.warning(f"Error parsing PubMed article: {e}")
                        continue
                
                # Rate limiting
                time.sleep(0.1)
            
            self._log_scraping('pubmed', 'scrape', 'success', f"Scraped {len(articles)} articles")
            self.scraping_stats['successful'] += len(articles)
            self.scraping_stats['sources']['pubmed'] = len(articles)
            
            return articles
            
        except Exception as e:
            logger.error(f"Error scraping PubMed: {e}")
            self._log_scraping('pubmed', 'scrape', 'error', str(e))
            return []
    
    def _parse_pubmed_article(self, article_xml) -> Optional[Article]:
        """Parse a single PubMed article from XML."""
        try:
            # Extract basic information
            title_elem = article_xml.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else "No title"
            
            # Extract authors
            authors = []
            for author in article_xml.findall('.//Author'):
                last_name = author.find('LastName')
                first_name = author.find('ForeName')
                if last_name is not None:
                    author_name = last_name.text
                    if first_name is not None:
                        author_name = f"{first_name.text} {author_name}"
                    authors.append(author_name)
            
            # Extract abstract
            abstract_elem = article_xml.find('.//AbstractText')
            abstract = abstract_elem.text if abstract_elem is not None else ""
            
            # Extract DOI
            doi_elem = article_xml.find('.//ELocationID[@EIdType="doi"]')
            doi = doi_elem.text if doi_elem is not None else None
            
            # Extract PMID
            pmid_elem = article_xml.find('.//PMID')
            pmid = pmid_elem.text if pmid_elem is not None else None
            
            # Extract journal
            journal_elem = article_xml.find('.//Journal/Title')
            journal = journal_elem.text if journal_elem is not None else None
            
            # Extract publication date
            pub_date = None
            pub_date_elem = article_xml.find('.//PubDate')
            if pub_date_elem is not None:
                year = pub_date_elem.find('Year')
                month = pub_date_elem.find('Month')
                day = pub_date_elem.find('Day')
                if year is not None:
                    pub_date = year.text
                    if month is not None:
                        pub_date += f"-{month.text.zfill(2)}"
                        if day is not None:
                            pub_date += f"-{day.text.zfill(2)}"
            
            # Extract keywords
            keywords = []
            for keyword in article_xml.findall('.//Keyword'):
                if keyword.text:
                    keywords.append(keyword.text)
            
            # Create article object
            article = Article(
                title=title,
                authors=authors,
                abstract=abstract,
                doi=doi,
                pmid=pmid,
                journal=journal,
                publication_date=pub_date,
                keywords=keywords,
                source='pubmed'
            )
            
            return article
            
        except Exception as e:
            logger.warning(f"Error parsing PubMed article: {e}")
            return None
    
    def scrape_arxiv(self, 
                    query: str,
                    max_results: int = 100,
                    category: str = 'cs.AI') -> List[Article]:
        """
        Scrape articles from arXiv.
        
        Args:
            query: Search query
            max_results: Maximum number of results to retrieve
            category: arXiv category (default: cs.AI)
            
        Returns:
            List of Article objects
        """
        try:
            articles = []
            
            # Build arXiv API URL
            base_url = "http://export.arxiv.org/api/query"
            
            params = {
                'search_query': f'cat:{category} AND all:{query}',
                'start': 0,
                'max_results': max_results,
                'sortBy': 'relevance',
                'sortOrder': 'descending'
            }
            
            response = self.session.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.content)
            
            for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
                try:
                    article_data = self._parse_arxiv_article(entry)
                    if article_data:
                        articles.append(article_data)
                except Exception as e:
                    logger.warning(f"Error parsing arXiv article: {e}")
                    continue
            
            self._log_scraping('arxiv', 'scrape', 'success', f"Scraped {len(articles)} articles")
            self.scraping_stats['successful'] += len(articles)
            self.scraping_stats['sources']['arxiv'] = len(articles)
            
            return articles
            
        except Exception as e:
            logger.error(f"Error scraping arXiv: {e}")
            self._log_scraping('arxiv', 'scrape', 'error', str(e))
            return []
    
    def _parse_arxiv_article(self, entry_xml) -> Optional[Article]:
        """Parse a single arXiv article from XML."""
        try:
            # Extract title
            title_elem = entry_xml.find('.//{http://www.w3.org/2005/Atom}title')
            title = title_elem.text.strip() if title_elem is not None else "No title"
            
            # Extract authors
            authors = []
            for author in entry_xml.findall('.//{http://www.w3.org/2005/Atom}author'):
                name_elem = author.find('.//{http://www.w3.org/2005/Atom}name')
                if name_elem is not None:
                    authors.append(name_elem.text)
            
            # Extract abstract
            abstract_elem = entry_xml.find('.//{http://www.w3.org/2005/Atom}summary')
            abstract = abstract_elem.text.strip() if abstract_elem is not None else ""
            
            # Extract arXiv ID
            id_elem = entry_xml.find('.//{http://www.w3.org/2005/Atom}id')
            arxiv_id = id_elem.text.split('/')[-1] if id_elem is not None else None
            
            # Extract publication date
            published_elem = entry_xml.find('.//{http://www.w3.org/2005/Atom}published')
            pub_date = published_elem.text[:10] if published_elem is not None else None
            
            # Extract categories
            categories = []
            for category in entry_xml.findall('.//{http://www.w3.org/2005/Atom}category'):
                term = category.get('term')
                if term:
                    categories.append(term)
            
            # Create article object
            article = Article(
                title=title,
                authors=authors,
                abstract=abstract,
                doi=arxiv_id,
                url=id_elem.text if id_elem is not None else None,
                publication_date=pub_date,
                keywords=categories,
                source='arxiv'
            )
            
            return article
            
        except Exception as e:
            logger.warning(f"Error parsing arXiv article: {e}")
            return None
    
    def scrape_google_scholar(self, 
                            query: str,
                            max_results: int = 100) -> List[Article]:
        """
        Scrape articles from Google Scholar (basic implementation).
        
        Args:
            query: Search query
            max_results: Maximum number of results to retrieve
            
        Returns:
            List of Article objects
        """
        try:
            articles = []
            
            # Note: Google Scholar has anti-bot measures, so this is a basic implementation
            # In practice, you might need to use specialized tools or APIs
            
            base_url = "https://scholar.google.com/scholar"
            params = {
                'q': query,
                'hl': 'en',
                'as_sdt': '0,5'
            }
            
            response = self.session.get(base_url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Parse search results
            for result in soup.find_all('div', class_='gs_ri'):
                try:
                    article_data = self._parse_google_scholar_article(result)
                    if article_data:
                        articles.append(article_data)
                except Exception as e:
                    logger.warning(f"Error parsing Google Scholar article: {e}")
                    continue
            
            self._log_scraping('google_scholar', 'scrape', 'success', f"Scraped {len(articles)} articles")
            self.scraping_stats['successful'] += len(articles)
            self.scraping_stats['sources']['google_scholar'] = len(articles)
            
            return articles
            
        except Exception as e:
            logger.error(f"Error scraping Google Scholar: {e}")
            self._log_scraping('google_scholar', 'scrape', 'error', str(e))
            return []
    
    def _parse_google_scholar_article(self, result_html) -> Optional[Article]:
        """Parse a single Google Scholar article from HTML."""
        try:
            # Extract title
            title_elem = result_html.find('h3', class_='gs_rt')
            title = title_elem.get_text().strip() if title_elem else "No title"
            
            # Extract authors and journal
            authors_elem = result_html.find('div', class_='gs_a')
            authors_text = authors_elem.get_text() if authors_elem else ""
            
            # Simple parsing of authors (this could be improved)
            authors = []
            if authors_text:
                # Split by common separators
                author_parts = re.split(r'[,;]', authors_text)
                for part in author_parts[:3]:  # Limit to first 3 authors
                    author = part.strip()
                    if author and not any(word in author.lower() for word in ['journal', 'conference', 'proceedings']):
                        authors.append(author)
            
            # Extract abstract
            abstract_elem = result_html.find('div', class_='gs_rs')
            abstract = abstract_elem.get_text().strip() if abstract_elem else ""
            
            # Extract URL
            link_elem = result_html.find('h3', class_='gs_rt').find('a')
            url = link_elem.get('href') if link_elem else None
            
            # Create article object
            article = Article(
                title=title,
                authors=authors,
                abstract=abstract,
                url=url,
                source='google_scholar'
            )
            
            return article
            
        except Exception as e:
            logger.warning(f"Error parsing Google Scholar article: {e}")
            return None
    
    def scrape_rss_feeds(self, 
                        feed_urls: List[str],
                        max_articles_per_feed: int = 50) -> List[Article]:
        """
        Scrape articles from RSS feeds.
        
        Args:
            feed_urls: List of RSS feed URLs
            max_articles_per_feed: Maximum articles to retrieve per feed
            
        Returns:
            List of Article objects
        """
        try:
            articles = []
            
            for feed_url in feed_urls:
                try:
                    feed = feedparser.parse(feed_url)
                    
                    for entry in feed.entries[:max_articles_per_feed]:
                        try:
                            article_data = self._parse_rss_article(entry, feed_url)
                            if article_data:
                                articles.append(article_data)
                        except Exception as e:
                            logger.warning(f"Error parsing RSS article: {e}")
                            continue
                    
                    self._log_scraping('rss', 'scrape', 'success', f"Scraped {len(feed.entries)} articles from {feed_url}")
                    
                except Exception as e:
                    logger.warning(f"Error parsing RSS feed {feed_url}: {e}")
                    continue
            
            self.scraping_stats['successful'] += len(articles)
            self.scraping_stats['sources']['rss'] = len(articles)
            
            return articles
            
        except Exception as e:
            logger.error(f"Error scraping RSS feeds: {e}")
            self._log_scraping('rss', 'scrape', 'error', str(e))
            return []
    
    def _parse_rss_article(self, entry, feed_url: str) -> Optional[Article]:
        """Parse a single RSS article entry."""
        try:
            title = entry.get('title', 'No title')
            summary = entry.get('summary', '')
            link = entry.get('link', '')
            
            # Extract authors
            authors = []
            if hasattr(entry, 'authors'):
                authors = [author.name for author in entry.authors]
            elif hasattr(entry, 'author'):
                authors = [entry.author]
            
            # Extract publication date
            pub_date = None
            if hasattr(entry, 'published'):
                pub_date = entry.published
            elif hasattr(entry, 'updated'):
                pub_date = entry.updated
            
            # Extract tags/keywords
            keywords = []
            if hasattr(entry, 'tags'):
                keywords = [tag.term for tag in entry.tags]
            
            # Create article object
            article = Article(
                title=title,
                authors=authors,
                abstract=summary,
                url=link,
                publication_date=pub_date,
                keywords=keywords,
                source='rss'
            )
            
            return article
            
        except Exception as e:
            logger.warning(f"Error parsing RSS article: {e}")
            return None
    
    def save_articles_to_db(self, articles: List[Article]) -> int:
        """
        Save articles to database.
        
        Args:
            articles: List of Article objects to save
            
        Returns:
            Number of articles saved
        """
        saved_count = 0
        
        with self.get_db_connection() as conn:
            for article in articles:
                try:
                    article_dict = article.to_dict()
                    article_dict['hash'] = article.get_hash()
                    
                    # Convert lists to JSON strings
                    article_dict['authors'] = json.dumps(article_dict['authors'])
                    article_dict['keywords'] = json.dumps(article_dict['keywords'])
                    
                    # Insert article
                    conn.execute('''
                        INSERT OR IGNORE INTO articles 
                        (hash, title, authors, abstract, doi, pmid, url, journal, 
                         publication_date, keywords, citations, source, scraped_date, content)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        article_dict['hash'],
                        article_dict['title'],
                        article_dict['authors'],
                        article_dict['abstract'],
                        article_dict['doi'],
                        article_dict['pmid'],
                        article_dict['url'],
                        article_dict['journal'],
                        article_dict['publication_date'],
                        article_dict['keywords'],
                        article_dict['citations'],
                        article_dict['source'],
                        article_dict['scraped_date'],
                        article_dict['content']
                    ))
                    
                    saved_count += 1
                    
                except Exception as e:
                    logger.warning(f"Error saving article to database: {e}")
                    continue
            
            conn.commit()
        
        logger.info(f"Saved {saved_count} articles to database")
        return saved_count
    
    def load_articles_from_db(self, 
                            source: str = None,
                            limit: int = None) -> List[Article]:
        """
        Load articles from database.
        
        Args:
            source: Filter by source (optional)
            limit: Maximum number of articles to load (optional)
            
        Returns:
            List of Article objects
        """
        articles = []
        
        with self.get_db_connection() as conn:
            query = "SELECT * FROM articles"
            params = []
            
            if source:
                query += " WHERE source = ?"
                params.append(source)
            
            query += " ORDER BY scraped_date DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor = conn.execute(query, params)
            
            for row in cursor.fetchall():
                try:
                    article_dict = dict(zip([col[0] for col in cursor.description], row))
                    
                    # Convert JSON strings back to lists
                    article_dict['authors'] = json.loads(article_dict['authors'] or '[]')
                    article_dict['keywords'] = json.loads(article_dict['keywords'] or '[]')
                    
                    # Remove hash from dict
                    article_dict.pop('hash', None)
                    article_dict.pop('id', None)
                    
                    article = Article(**article_dict)
                    articles.append(article)
                    
                except Exception as e:
                    logger.warning(f"Error loading article from database: {e}")
                    continue
        
        logger.info(f"Loaded {len(articles)} articles from database")
        return articles
    
    def search_articles(self, 
                       query: str,
                       fields: List[str] = None) -> List[Article]:
        """
        Search articles in database.
        
        Args:
            query: Search query
            fields: Fields to search in (default: title, abstract, authors)
            
        Returns:
            List of matching Article objects
        """
        if fields is None:
            fields = ['title', 'abstract', 'authors']
        
        articles = []
        
        with self.get_db_connection() as conn:
            # Build search query
            search_conditions = []
            params = []
            
            for field in fields:
                if field == 'authors':
                    search_conditions.append("authors LIKE ?")
                    params.append(f"%{query}%")
                else:
                    search_conditions.append(f"{field} LIKE ?")
                    params.append(f"%{query}%")
            
            query_sql = f"SELECT * FROM articles WHERE {' OR '.join(search_conditions)} ORDER BY scraped_date DESC"
            
            cursor = conn.execute(query_sql, params)
            
            for row in cursor.fetchall():
                try:
                    article_dict = dict(zip([col[0] for col in cursor.description], row))
                    
                    # Convert JSON strings back to lists
                    article_dict['authors'] = json.loads(article_dict['authors'] or '[]')
                    article_dict['keywords'] = json.loads(article_dict['keywords'] or '[]')
                    
                    # Remove hash from dict
                    article_dict.pop('hash', None)
                    article_dict.pop('id', None)
                    
                    article = Article(**article_dict)
                    articles.append(article)
                    
                except Exception as e:
                    logger.warning(f"Error loading article from database: {e}")
                    continue
        
        logger.info(f"Found {len(articles)} articles matching query: {query}")
        return articles
    
    def get_scraping_stats(self) -> Dict[str, Any]:
        """
        Get scraping statistics.
        
        Returns:
            Dictionary containing scraping statistics
        """
        with self.get_db_connection() as conn:
            # Get total articles in database
            cursor = conn.execute("SELECT COUNT(*) FROM articles")
            total_articles = cursor.fetchone()[0]
            
            # Get articles by source
            cursor = conn.execute("SELECT source, COUNT(*) FROM articles GROUP BY source")
            articles_by_source = dict(cursor.fetchall())
            
            # Get recent scraping activity
            cursor = conn.execute("""
                SELECT DATE(scraped_date) as date, COUNT(*) as count 
                FROM articles 
                WHERE scraped_date >= date('now', '-30 days')
                GROUP BY DATE(scraped_date)
                ORDER BY date DESC
            """)
            recent_activity = dict(cursor.fetchall())
        
        stats = {
            'total_articles': total_articles,
            'articles_by_source': articles_by_source,
            'recent_activity': recent_activity,
            'scraping_stats': self.scraping_stats
        }
        
        return stats
    
    def _log_scraping(self, source: str, action: str, status: str, message: str):
        """Log scraping activity to database."""
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO scraping_log (timestamp, source, action, status, message)
                VALUES (?, ?, ?, ?, ?)
            ''', (datetime.now().isoformat(), source, action, status, message))
            conn.commit()
    
    def export_articles(self, 
                       output_path: str,
                       format: str = 'csv',
                       source: str = None) -> None:
        """
        Export articles to file.
        
        Args:
            output_path: Path to save the exported file
            format: Export format ('csv', 'json', 'excel')
            source: Filter by source (optional)
        """
        try:
            articles = self.load_articles_from_db(source=source)
            
            if not articles:
                logger.warning("No articles to export")
                return
            
            # Convert articles to DataFrame
            articles_data = [article.to_dict() for article in articles]
            df = pd.DataFrame(articles_data)
            
            # Export based on format
            if format == 'csv':
                df.to_csv(output_path, index=False)
            elif format == 'json':
                df.to_json(output_path, orient='records', indent=2)
            elif format == 'excel':
                df.to_excel(output_path, index=False)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Exported {len(articles)} articles to {output_path}")
            
        except Exception as e:
            logger.error(f"Error exporting articles: {e}")
            raise


def create_mock_articles() -> List[Article]:
    """
    Create mock articles for testing and demonstration.
    
    Returns:
        List of mock Article objects
    """
    mock_articles = [
        Article(
            title="Machine Learning Approaches in Cancer Genomics",
            authors=["John Smith", "Jane Doe", "Bob Johnson"],
            abstract="This paper presents novel machine learning approaches for analyzing cancer genomics data...",
            doi="10.1000/example1",
            journal="Nature Cancer",
            publication_date="2024-01-15",
            keywords=["machine learning", "cancer", "genomics", "bioinformatics"],
            citations=45,
            source="pubmed"
        ),
        Article(
            title="Deep Learning for Drug Discovery in Oncology",
            authors=["Alice Brown", "Charlie Wilson"],
            abstract="We propose a deep learning framework for accelerating drug discovery in oncology...",
            doi="10.1000/example2",
            journal="Cell Reports",
            publication_date="2024-01-10",
            keywords=["deep learning", "drug discovery", "oncology", "AI"],
            citations=32,
            source="pubmed"
        ),
        Article(
            title="Multi-omics Integration for Precision Medicine",
            authors=["David Lee", "Sarah Chen", "Mike Davis"],
            abstract="This study demonstrates the integration of multiple omics data types for precision medicine...",
            doi="10.1000/example3",
            journal="Science Translational Medicine",
            publication_date="2024-01-05",
            keywords=["multi-omics", "precision medicine", "integration", "biomarkers"],
            citations=28,
            source="pubmed"
        )
    ]
    
    return mock_articles


def main():
    """Main function for testing the article scraper."""
    # Create scraper instance
    scraper = ArticleScraper()
    
    # Create mock articles
    mock_articles = create_mock_articles()
    
    # Save mock articles to database
    scraper.save_articles_to_db(mock_articles)
    
    # Load articles from database
    loaded_articles = scraper.load_articles_from_db()
    
    # Search articles
    search_results = scraper.search_articles("machine learning")
    
    # Get statistics
    stats = scraper.get_scraping_stats()
    
    print("Article Scraper Test Results:")
    print(f"Mock articles created: {len(mock_articles)}")
    print(f"Articles loaded from DB: {len(loaded_articles)}")
    print(f"Search results: {len(search_results)}")
    print(f"Database statistics: {stats}")


if __name__ == "__main__":
    main()
