"""
Article Database Manager Module

This module provides comprehensive functionality for managing and analyzing
scientific articles in a database system for cancer genomics research.
"""

import sqlite3
import pandas as pd
import numpy as np
import json
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from pathlib import Path
from datetime import datetime, timedelta
import hashlib
from contextlib import contextmanager
from dataclasses import dataclass, asdict
import re
from collections import Counter, defaultdict
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from sklearn.decomposition import LatentDirichletAllocation
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ArticleMetadata:
    """Data class for storing article metadata."""
    id: Optional[int] = None
    title: str = ""
    authors: List[str] = None
    abstract: str = ""
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
    tags: List[str] = None
    notes: Optional[str] = None
    rating: Optional[int] = None
    read_status: str = "unread"
    relevance_score: Optional[float] = None
    
    def __post_init__(self):
        if self.authors is None:
            self.authors = []
        if self.keywords is None:
            self.keywords = []
        if self.tags is None:
            self.tags = []
        if self.scraped_date is None:
            self.scraped_date = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert article metadata to dictionary."""
        return asdict(self)
    
    def get_hash(self) -> str:
        """Get unique hash for article."""
        content = f"{self.title}{self.doi}{self.pmid}{self.url}"
        return hashlib.md5(content.encode()).hexdigest()


class ArticleDatabaseManager:
    """
    A comprehensive class for managing scientific articles in a database.
    """
    
    def __init__(self, db_path: str = "article_manager.db"):
        """
        Initialize the article database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.article_vectors = None
        self.article_titles = []
        self.lda_model = None
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with required tables."""
        with self.get_db_connection() as conn:
            # Main articles table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hash TEXT UNIQUE,
                    title TEXT NOT NULL,
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
                    content TEXT,
                    tags TEXT,
                    notes TEXT,
                    rating INTEGER,
                    read_status TEXT DEFAULT 'unread',
                    relevance_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tags table for tag management
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    description TEXT,
                    color TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Article-tag relationships
            conn.execute('''
                CREATE TABLE IF NOT EXISTS article_tags (
                    article_id INTEGER,
                    tag_id INTEGER,
                    PRIMARY KEY (article_id, tag_id),
                    FOREIGN KEY (article_id) REFERENCES articles (id),
                    FOREIGN KEY (tag_id) REFERENCES tags (id)
                )
            ''')
            
            # Collections table for organizing articles
            conn.execute('''
                CREATE TABLE IF NOT EXISTS collections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Article-collection relationships
            conn.execute('''
                CREATE TABLE IF NOT EXISTS article_collections (
                    article_id INTEGER,
                    collection_id INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (article_id, collection_id),
                    FOREIGN KEY (article_id) REFERENCES articles (id),
                    FOREIGN KEY (collection_id) REFERENCES collections (id)
                )
            ''')
            
            # Citations table for tracking article relationships
            conn.execute('''
                CREATE TABLE IF NOT EXISTS citations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    citing_article_id INTEGER,
                    cited_article_id INTEGER,
                    citation_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (citing_article_id) REFERENCES articles (id),
                    FOREIGN KEY (cited_article_id) REFERENCES articles (id)
                )
            ''')
            
            # Search history table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT,
                    filters TEXT,
                    results_count INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_articles_title ON articles(title)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_articles_journal ON articles(journal)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_articles_publication_date ON articles(publication_date)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_articles_read_status ON articles(read_status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_articles_rating ON articles(rating)')
    
    @contextmanager
    def get_db_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def add_article(self, article: ArticleMetadata) -> int:
        """
        Add a new article to the database.
        
        Args:
            article: ArticleMetadata object
            
        Returns:
            Article ID
        """
        with self.get_db_connection() as conn:
            try:
                article_dict = article.to_dict()
                article_dict['hash'] = article.get_hash()
                
                # Convert lists to JSON strings
                article_dict['authors'] = json.dumps(article_dict['authors'])
                article_dict['keywords'] = json.dumps(article_dict['keywords'])
                article_dict['tags'] = json.dumps(article_dict['tags'])
                
                # Insert article
                cursor = conn.execute('''
                    INSERT OR REPLACE INTO articles 
                    (hash, title, authors, abstract, doi, pmid, url, journal, 
                     publication_date, keywords, citations, source, scraped_date, 
                     content, tags, notes, rating, read_status, relevance_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    article_dict['content'],
                    article_dict['tags'],
                    article_dict['notes'],
                    article_dict['rating'],
                    article_dict['read_status'],
                    article_dict['relevance_score']
                ))
                
                article_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Added article: {article.title}")
                return article_id
                
            except Exception as e:
                logger.error(f"Error adding article: {e}")
                raise
    
    def get_article(self, article_id: int) -> Optional[ArticleMetadata]:
        """
        Get an article by ID.
        
        Args:
            article_id: Article ID
            
        Returns:
            ArticleMetadata object or None
        """
        with self.get_db_connection() as conn:
            cursor = conn.execute('SELECT * FROM articles WHERE id = ?', (article_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_article(row)
            return None
    
    def update_article(self, article_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update an article.
        
        Args:
            article_id: Article ID
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        with self.get_db_connection() as conn:
            try:
                # Prepare update fields
                set_clauses = []
                values = []
                
                for key, value in updates.items():
                    if key in ['authors', 'keywords', 'tags'] and isinstance(value, list):
                        value = json.dumps(value)
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
                
                values.append(article_id)
                
                query = f"UPDATE articles SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
                cursor = conn.execute(query, values)
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Updated article {article_id}")
                    return True
                return False
                
            except Exception as e:
                logger.error(f"Error updating article: {e}")
                return False
    
    def delete_article(self, article_id: int) -> bool:
        """
        Delete an article.
        
        Args:
            article_id: Article ID
            
        Returns:
            True if successful, False otherwise
        """
        with self.get_db_connection() as conn:
            try:
                # Delete related records first
                conn.execute('DELETE FROM article_tags WHERE article_id = ?', (article_id,))
                conn.execute('DELETE FROM article_collections WHERE article_id = ?', (article_id,))
                conn.execute('DELETE FROM citations WHERE citing_article_id = ? OR cited_article_id = ?', 
                           (article_id, article_id))
                
                # Delete article
                cursor = conn.execute('DELETE FROM articles WHERE id = ?', (article_id,))
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Deleted article {article_id}")
                    return True
                return False
                
            except Exception as e:
                logger.error(f"Error deleting article: {e}")
                return False
    
    def search_articles(self, 
                       query: str = "",
                       filters: Dict[str, Any] = None,
                       limit: int = 100,
                       offset: int = 0) -> Tuple[List[ArticleMetadata], int]:
        """
        Search articles with filters.
        
        Args:
            query: Search query
            filters: Dictionary of filters
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            Tuple of (articles, total_count)
        """
        with self.get_db_connection() as conn:
            try:
                # Build query
                where_clauses = []
                params = []
                
                # Text search
                if query:
                    where_clauses.append("""
                        (title LIKE ? OR abstract LIKE ? OR authors LIKE ? OR keywords LIKE ?)
                    """)
                    query_param = f"%{query}%"
                    params.extend([query_param, query_param, query_param, query_param])
                
                # Apply filters
                if filters:
                    if 'source' in filters and filters['source']:
                        where_clauses.append("source = ?")
                        params.append(filters['source'])
                    
                    if 'journal' in filters and filters['journal']:
                        where_clauses.append("journal = ?")
                        params.append(filters['journal'])
                    
                    if 'read_status' in filters and filters['read_status']:
                        where_clauses.append("read_status = ?")
                        params.append(filters['read_status'])
                    
                    if 'rating' in filters and filters['rating']:
                        where_clauses.append("rating >= ?")
                        params.append(filters['rating'])
                    
                    if 'date_from' in filters and filters['date_from']:
                        where_clauses.append("publication_date >= ?")
                        params.append(filters['date_from'])
                    
                    if 'date_to' in filters and filters['date_to']:
                        where_clauses.append("publication_date <= ?")
                        params.append(filters['date_to'])
                    
                    if 'tags' in filters and filters['tags']:
                        tag_conditions = []
                        for tag in filters['tags']:
                            tag_conditions.append("tags LIKE ?")
                            params.append(f"%{tag}%")
                        if tag_conditions:
                            where_clauses.append(f"({' OR '.join(tag_conditions)})")
                
                # Build final query
                where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
                
                # Count total results
                count_query = f"SELECT COUNT(*) FROM articles WHERE {where_clause}"
                total_count = conn.execute(count_query, params).fetchone()[0]
                
                # Get results
                search_query = f"""
                    SELECT * FROM articles 
                    WHERE {where_clause}
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                """
                params.extend([limit, offset])
                
                cursor = conn.execute(search_query, params)
                articles = [self._row_to_article(row) for row in cursor.fetchall()]
                
                # Log search
                self._log_search(query, filters, total_count)
                
                return articles, total_count
                
            except Exception as e:
                logger.error(f"Error searching articles: {e}")
                return [], 0
    
    def get_articles_by_collection(self, collection_id: int) -> List[ArticleMetadata]:
        """
        Get articles in a collection.
        
        Args:
            collection_id: Collection ID
            
        Returns:
            List of ArticleMetadata objects
        """
        with self.get_db_connection() as conn:
            cursor = conn.execute('''
                SELECT a.* FROM articles a
                JOIN article_collections ac ON a.id = ac.article_id
                WHERE ac.collection_id = ?
                ORDER BY ac.added_at DESC
            ''', (collection_id,))
            
            return [self._row_to_article(row) for row in cursor.fetchall()]
    
    def get_articles_by_tag(self, tag_name: str) -> List[ArticleMetadata]:
        """
        Get articles with a specific tag.
        
        Args:
            tag_name: Tag name
            
        Returns:
            List of ArticleMetadata objects
        """
        with self.get_db_connection() as conn:
            cursor = conn.execute('''
                SELECT a.* FROM articles a
                JOIN article_tags at ON a.id = at.article_id
                JOIN tags t ON at.tag_id = t.id
                WHERE t.name = ?
                ORDER BY a.updated_at DESC
            ''', (tag_name,))
            
            return [self._row_to_article(row) for row in cursor.fetchall()]
    
    def create_collection(self, name: str, description: str = "") -> int:
        """
        Create a new collection.
        
        Args:
            name: Collection name
            description: Collection description
            
        Returns:
            Collection ID
        """
        with self.get_db_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO collections (name, description)
                VALUES (?, ?)
            ''', (name, description))
            
            conn.commit()
            return cursor.lastrowid
    
    def add_article_to_collection(self, article_id: int, collection_id: int) -> bool:
        """
        Add an article to a collection.
        
        Args:
            article_id: Article ID
            collection_id: Collection ID
            
        Returns:
            True if successful, False otherwise
        """
        with self.get_db_connection() as conn:
            try:
                conn.execute('''
                    INSERT OR IGNORE INTO article_collections (article_id, collection_id)
                    VALUES (?, ?)
                ''', (article_id, collection_id))
                
                conn.commit()
                return True
                
            except Exception as e:
                logger.error(f"Error adding article to collection: {e}")
                return False
    
    def create_tag(self, name: str, description: str = "", color: str = "#007bff") -> int:
        """
        Create a new tag.
        
        Args:
            name: Tag name
            description: Tag description
            color: Tag color
            
        Returns:
            Tag ID
        """
        with self.get_db_connection() as conn:
            try:
                cursor = conn.execute('''
                    INSERT OR IGNORE INTO tags (name, description, color)
                    VALUES (?, ?, ?)
                ''', (name, description, color))
                
                conn.commit()
                return cursor.lastrowid
                
            except Exception as e:
                logger.error(f"Error creating tag: {e}")
                return 0
    
    def add_tag_to_article(self, article_id: int, tag_name: str) -> bool:
        """
        Add a tag to an article.
        
        Args:
            article_id: Article ID
            tag_name: Tag name
            
        Returns:
            True if successful, False otherwise
        """
        with self.get_db_connection() as conn:
            try:
                # Get or create tag
                tag_id = self.create_tag(tag_name)
                if tag_id == 0:
                    cursor = conn.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
                    row = cursor.fetchone()
                    if row:
                        tag_id = row[0]
                    else:
                        return False
                
                # Add tag to article
                conn.execute('''
                    INSERT OR IGNORE INTO article_tags (article_id, tag_id)
                    VALUES (?, ?)
                ''', (article_id, tag_id))
                
                conn.commit()
                return True
                
            except Exception as e:
                logger.error(f"Error adding tag to article: {e}")
                return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary containing statistics
        """
        with self.get_db_connection() as conn:
            stats = {}
            
            # Basic counts
            cursor = conn.execute('SELECT COUNT(*) FROM articles')
            stats['total_articles'] = cursor.fetchone()[0]
            
            cursor = conn.execute('SELECT COUNT(*) FROM articles WHERE read_status = "read"')
            stats['read_articles'] = cursor.fetchone()[0]
            
            cursor = conn.execute('SELECT COUNT(*) FROM collections')
            stats['total_collections'] = cursor.fetchone()[0]
            
            cursor = conn.execute('SELECT COUNT(*) FROM tags')
            stats['total_tags'] = cursor.fetchone()[0]
            
            # Articles by source
            cursor = conn.execute('SELECT source, COUNT(*) FROM articles GROUP BY source')
            stats['articles_by_source'] = dict(cursor.fetchall())
            
            # Articles by journal
            cursor = conn.execute('SELECT journal, COUNT(*) FROM articles WHERE journal IS NOT NULL GROUP BY journal ORDER BY COUNT(*) DESC LIMIT 10')
            stats['top_journals'] = dict(cursor.fetchall())
            
            # Articles by year
            cursor = conn.execute('''
                SELECT substr(publication_date, 1, 4) as year, COUNT(*) 
                FROM articles 
                WHERE publication_date IS NOT NULL 
                GROUP BY year 
                ORDER BY year DESC
            ''')
            stats['articles_by_year'] = dict(cursor.fetchall())
            
            # Recent activity
            cursor = conn.execute('''
                SELECT DATE(created_at) as date, COUNT(*) 
                FROM articles 
                WHERE created_at >= date('now', '-30 days')
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            ''')
            stats['recent_activity'] = dict(cursor.fetchall())
            
            return stats
    
    def get_article_similarity(self, article_id: int, limit: int = 10) -> List[Tuple[int, float]]:
        """
        Find similar articles using TF-IDF and cosine similarity.
        
        Args:
            article_id: Article ID
            limit: Maximum number of similar articles
            
        Returns:
            List of (article_id, similarity_score) tuples
        """
        try:
            # Get all articles with abstracts
            with self.get_db_connection() as conn:
                cursor = conn.execute('SELECT id, title, abstract FROM articles WHERE abstract IS NOT NULL AND abstract != ""')
                articles_data = cursor.fetchall()
            
            if len(articles_data) < 2:
                return []
            
            # Prepare text data
            texts = []
            article_ids = []
            
            for row in articles_data:
                text = f"{row[1]} {row[2]}"  # title + abstract
                texts.append(text)
                article_ids.append(row[0])
            
            # Vectorize texts
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            
            # Find target article index
            target_idx = article_ids.index(article_id)
            
            # Calculate similarities
            similarities = cosine_similarity(tfidf_matrix[target_idx:target_idx+1], tfidf_matrix).flatten()
            
            # Get top similar articles (excluding self)
            similar_indices = np.argsort(similarities)[::-1][1:limit+1]
            
            similar_articles = []
            for idx in similar_indices:
                if similarities[idx] > 0.1:  # Minimum similarity threshold
                    similar_articles.append((article_ids[idx], similarities[idx]))
            
            return similar_articles
            
        except Exception as e:
            logger.error(f"Error calculating article similarity: {e}")
            return []
    
    def get_topic_modeling(self, n_topics: int = 10) -> Dict[str, Any]:
        """
        Perform topic modeling on article abstracts.
        
        Args:
            n_topics: Number of topics
            
        Returns:
            Dictionary containing topic modeling results
        """
        try:
            # Get all articles with abstracts
            with self.get_db_connection() as conn:
                cursor = conn.execute('SELECT id, title, abstract FROM articles WHERE abstract IS NOT NULL AND abstract != ""')
                articles_data = cursor.fetchall()
            
            if len(articles_data) < n_topics:
                return {}
            
            # Prepare text data
            texts = []
            article_ids = []
            
            for row in articles_data:
                text = f"{row[1]} {row[2]}"  # title + abstract
                texts.append(text)
                article_ids.append(row[0])
            
            # Vectorize texts
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            
            # Perform LDA
            self.lda_model = LatentDirichletAllocation(n_components=n_topics, random_state=42)
            lda_matrix = self.lda_model.fit_transform(tfidf_matrix)
            
            # Get topic words
            feature_names = self.vectorizer.get_feature_names_out()
            topics = []
            
            for topic_idx, topic in enumerate(self.lda_model.components_):
                top_words_idx = topic.argsort()[-10:][::-1]
                top_words = [feature_names[i] for i in top_words_idx]
                topics.append({
                    'topic_id': topic_idx,
                    'words': top_words,
                    'weights': topic[top_words_idx].tolist()
                })
            
            # Assign topics to articles
            article_topics = []
            for i, article_id in enumerate(article_ids):
                topic_scores = lda_matrix[i]
                dominant_topic = np.argmax(topic_scores)
                article_topics.append({
                    'article_id': article_id,
                    'dominant_topic': dominant_topic,
                    'topic_scores': topic_scores.tolist()
                })
            
            return {
                'topics': topics,
                'article_topics': article_topics,
                'n_topics': n_topics
            }
            
        except Exception as e:
            logger.error(f"Error in topic modeling: {e}")
            return {}
    
    def export_articles(self, 
                       output_path: str,
                       format: str = 'csv',
                       filters: Dict[str, Any] = None) -> None:
        """
        Export articles to file.
        
        Args:
            output_path: Path to save the exported file
            format: Export format ('csv', 'json', 'excel')
            filters: Optional filters for export
        """
        try:
            articles, _ = self.search_articles(filters=filters, limit=10000)
            
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
    
    def _row_to_article(self, row) -> ArticleMetadata:
        """Convert database row to ArticleMetadata object."""
        article_dict = dict(row)
        
        # Convert JSON strings back to lists
        for field in ['authors', 'keywords', 'tags']:
            if article_dict[field]:
                try:
                    article_dict[field] = json.loads(article_dict[field])
                except (json.JSONDecodeError, TypeError):
                    article_dict[field] = []
            else:
                article_dict[field] = []
        
        return ArticleMetadata(**article_dict)
    
    def _log_search(self, query: str, filters: Dict[str, Any], results_count: int):
        """Log search activity."""
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO search_history (query, filters, results_count)
                VALUES (?, ?, ?)
            ''', (query, json.dumps(filters or {}), results_count))
            conn.commit()


def create_mock_articles() -> List[ArticleMetadata]:
    """
    Create mock articles for testing and demonstration.
    
    Returns:
        List of mock ArticleMetadata objects
    """
    mock_articles = [
        ArticleMetadata(
            title="Machine Learning Approaches in Cancer Genomics",
            authors=["John Smith", "Jane Doe", "Bob Johnson"],
            abstract="This paper presents novel machine learning approaches for analyzing cancer genomics data...",
            doi="10.1000/example1",
            journal="Nature Cancer",
            publication_date="2024-01-15",
            keywords=["machine learning", "cancer", "genomics", "bioinformatics"],
            citations=45,
            source="pubmed",
            tags=["ml", "cancer", "genomics"],
            rating=5,
            read_status="read"
        ),
        ArticleMetadata(
            title="Deep Learning for Drug Discovery in Oncology",
            authors=["Alice Brown", "Charlie Wilson"],
            abstract="We propose a deep learning framework for accelerating drug discovery in oncology...",
            doi="10.1000/example2",
            journal="Cell Reports",
            publication_date="2024-01-10",
            keywords=["deep learning", "drug discovery", "oncology", "AI"],
            citations=32,
            source="pubmed",
            tags=["deep-learning", "drug-discovery", "oncology"],
            rating=4,
            read_status="unread"
        ),
        ArticleMetadata(
            title="Multi-omics Integration for Precision Medicine",
            authors=["David Lee", "Sarah Chen", "Mike Davis"],
            abstract="This study demonstrates the integration of multiple omics data types for precision medicine...",
            doi="10.1000/example3",
            journal="Science Translational Medicine",
            publication_date="2024-01-05",
            keywords=["multi-omics", "precision medicine", "integration", "biomarkers"],
            citations=28,
            source="pubmed",
            tags=["multi-omics", "precision-medicine", "integration"],
            rating=5,
            read_status="read"
        )
    ]
    
    return mock_articles


def main():
    """Main function for testing the article database manager."""
    # Create database manager
    db_manager = ArticleDatabaseManager()
    
    # Create mock articles
    mock_articles = create_mock_articles()
    
    # Add articles to database
    for article in mock_articles:
        article_id = db_manager.add_article(article)
        print(f"Added article {article_id}: {article.title}")
    
    # Search articles
    articles, total = db_manager.search_articles(query="machine learning")
    print(f"Found {total} articles matching 'machine learning'")
    
    # Get statistics
    stats = db_manager.get_statistics()
    print("Database Statistics:")
    print(json.dumps(stats, indent=2))
    
    # Test similarity
    if articles:
        similar = db_manager.get_article_similarity(articles[0].id)
        print(f"Similar articles to '{articles[0].title}': {len(similar)}")


if __name__ == "__main__":
    main()
