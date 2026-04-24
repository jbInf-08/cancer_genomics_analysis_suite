"""
PubMed Data Collector

This module provides data collection capabilities for PubMed, the biomedical literature
database maintained by the National Center for Biotechnology Information (NCBI).
"""

import pandas as pd
import requests
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from .base_collector import DataCollectorBase


class PubMedCollector(DataCollectorBase):
    """
    Data collector for PubMed biomedical literature database.
    
    PubMed provides:
    - Biomedical literature citations
    - Article abstracts
    - MeSH terms and keywords
    - Author information
    - Journal information
    - Publication dates and types
    """
    
    def __init__(self, output_dir: str = "data/external_sources/pubmed", **kwargs):
        """Initialize PubMed collector."""
        super().__init__(output_dir, **kwargs)
        self.base_url = self.config.get("base_url", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils")
        self.sample_limit = self.config.get("sample_limit", 100)
        self.search_terms = self.config.get("search_terms", ["cancer biomarkers", "genomics", "precision medicine"])
        self.data_types = self.config.get("data_types", ["publications", "abstracts", "mesh_terms"])
    
    def collect_data(self, 
                    search_term: str = "cancer biomarkers",
                    data_type: str = "publications",
                    max_results: Optional[int] = None,
                    **kwargs) -> Dict[str, Any]:
        """
        Collect data from PubMed.
        
        Args:
            search_term: Search term for literature
            data_type: Type of data to collect
            max_results: Maximum number of results to collect
            
        Returns:
            Dictionary containing collection results
        """
        if max_results is None:
            max_results = self.sample_limit
        
        self.logger.info(f"Collecting {data_type} data for '{search_term}' from PubMed")
        
        try:
            if data_type == "publications":
                return self._collect_publications(search_term, max_results)
            elif data_type == "abstracts":
                return self._collect_abstracts(search_term, max_results)
            elif data_type == "mesh_terms":
                return self._collect_mesh_terms(search_term, max_results)
            else:
                raise ValueError(f"Unsupported data type: {data_type}")
                
        except Exception as e:
            self.logger.error(f"Failed to collect {data_type} data: {e}")
            raise
    
    def _search_pubmed(self, search_term: str, max_results: int = 100) -> List[str]:
        """Search PubMed for articles matching the search term."""
        self.logger.info(f"Searching PubMed for articles matching '{search_term}'")
        
        # Search for articles
        search_params = {
            "db": "pubmed",
            "term": search_term,
            "retmax": max_results,
            "retmode": "xml",
            "sort": "relevance"
        }
        
        search_response = self.make_request(
            f"{self.base_url}/esearch.fcgi",
            params=search_params
        )
        
        # Parse XML response
        root = ET.fromstring(search_response.text)
        article_ids = []
        
        for id_elem in root.findall(".//Id"):
            if id_elem.text:
                article_ids.append(id_elem.text)
        
        self.logger.info(f"Found {len(article_ids)} articles matching search term")
        return article_ids
    
    def _get_article_details(self, article_ids: List[str]) -> List[Dict[str, Any]]:
        """Get detailed information for a list of articles."""
        if not article_ids:
            return []
        
        # Fetch article details
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(article_ids),
            "retmode": "xml",
            "rettype": "abstract"
        }
        
        fetch_response = self.make_request(
            f"{self.base_url}/efetch.fcgi",
            params=fetch_params
        )
        
        # Parse XML response
        root = ET.fromstring(fetch_response.text)
        articles = []
        
        for article in root.findall(".//PubmedArticle"):
            article_data = self._parse_article_xml(article)
            if article_data:
                articles.append(article_data)
        
        return articles
    
    def _parse_article_xml(self, article_elem) -> Optional[Dict[str, Any]]:
        """Parse a single article from XML."""
        try:
            article_data = {
                "pmid": "",
                "title": "",
                "abstract": "",
                "authors": [],
                "journal": "",
                "publication_date": "",
                "publication_type": "",
                "mesh_terms": [],
                "keywords": [],
                "doi": "",
                "pmc": "",
                "language": "",
                "country": ""
            }
            
            # Get PMID
            pmid_elem = article_elem.find(".//PMID")
            if pmid_elem is not None:
                article_data["pmid"] = pmid_elem.text or ""
            
            # Get title
            title_elem = article_elem.find(".//ArticleTitle")
            if title_elem is not None:
                article_data["title"] = title_elem.text or ""
            
            # Get abstract
            abstract_elem = article_elem.find(".//AbstractText")
            if abstract_elem is not None:
                article_data["abstract"] = abstract_elem.text or ""
            
            # Get authors
            authors = []
            for author in article_elem.findall(".//Author"):
                author_data = {
                    "last_name": "",
                    "first_name": "",
                    "initials": "",
                    "affiliation": ""
                }
                
                last_name = author.find("LastName")
                if last_name is not None:
                    author_data["last_name"] = last_name.text or ""
                
                first_name = author.find("ForeName")
                if first_name is not None:
                    author_data["first_name"] = first_name.text or ""
                
                initials = author.find("Initials")
                if initials is not None:
                    author_data["initials"] = initials.text or ""
                
                affiliation = author.find("Affiliation")
                if affiliation is not None:
                    author_data["affiliation"] = affiliation.text or ""
                
                authors.append(author_data)
            article_data["authors"] = authors
            
            # Get journal
            journal_elem = article_elem.find(".//Journal/Title")
            if journal_elem is not None:
                article_data["journal"] = journal_elem.text or ""
            
            # Get publication date
            pub_date = article_elem.find(".//PubDate")
            if pub_date is not None:
                year = pub_date.find("Year")
                month = pub_date.find("Month")
                day = pub_date.find("Day")
                
                date_parts = []
                if year is not None and year.text:
                    date_parts.append(year.text)
                if month is not None and month.text:
                    date_parts.append(month.text)
                if day is not None and day.text:
                    date_parts.append(day.text)
                
                article_data["publication_date"] = "-".join(date_parts)
            
            # Get publication type
            pub_type_elem = article_elem.find(".//PublicationType")
            if pub_type_elem is not None:
                article_data["publication_type"] = pub_type_elem.text or ""
            
            # Get MeSH terms
            mesh_terms = []
            for mesh in article_elem.findall(".//MeshHeading"):
                descriptor = mesh.find("DescriptorName")
                if descriptor is not None:
                    mesh_terms.append(descriptor.text or "")
            article_data["mesh_terms"] = mesh_terms
            
            # Get keywords
            keywords = []
            for keyword in article_elem.findall(".//Keyword"):
                if keyword.text:
                    keywords.append(keyword.text)
            article_data["keywords"] = keywords
            
            # Get DOI
            doi_elem = article_elem.find(".//ELocationID[@EIdType='doi']")
            if doi_elem is not None:
                article_data["doi"] = doi_elem.text or ""
            
            # Get PMC ID
            pmc_elem = article_elem.find(".//ELocationID[@EIdType='pmc']")
            if pmc_elem is not None:
                article_data["pmc"] = pmc_elem.text or ""
            
            # Get language
            lang_elem = article_elem.find(".//Language")
            if lang_elem is not None:
                article_data["language"] = lang_elem.text or ""
            
            # Get country
            country_elem = article_elem.find(".//Country")
            if country_elem is not None:
                article_data["country"] = country_elem.text or ""
            
            return article_data
            
        except Exception as e:
            self.logger.warning(f"Failed to parse article XML: {e}")
            return None
    
    def _collect_publications(self, search_term: str, max_results: int) -> Dict[str, Any]:
        """Collect publication data."""
        self.logger.info(f"Collecting publication data for '{search_term}'")
        
        # Search for articles
        article_ids = self._search_pubmed(search_term, max_results)
        
        if not article_ids:
            self.logger.warning(f"No articles found for search term: {search_term}")
            return {"samples_collected": 0, "files_created": []}
        
        # Get article details
        articles = self._get_article_details(article_ids)
        
        if articles:
            # Convert to DataFrame
            df = pd.DataFrame(articles)
            
            # Save data
            filename = self.generate_filename(
                f"publications_{search_term.replace(' ', '_')}",
                sample_count=len(df)
            )
            filepath = self.save_data(df, filename, "csv")
            
            self.collection_metadata["samples_collected"] = len(df)
            
            return {
                "articles_collected": len(df),
                "unique_journals": len(df['journal'].unique()) if 'journal' in df.columns else 0,
                "publication_years": len(df['publication_date'].str[:4].unique()) if 'publication_date' in df.columns else 0,
                "files_created": [filepath]
            }
        else:
            return {"samples_collected": 0, "files_created": []}
    
    def _collect_abstracts(self, search_term: str, max_results: int) -> Dict[str, Any]:
        """Collect abstract data."""
        self.logger.info(f"Collecting abstract data for '{search_term}'")
        
        # Search for articles
        article_ids = self._search_pubmed(search_term, max_results)
        
        if not article_ids:
            self.logger.warning(f"No articles found for search term: {search_term}")
            return {"samples_collected": 0, "files_created": []}
        
        # Get article details
        articles = self._get_article_details(article_ids)
        
        if articles:
            # Extract abstracts
            abstracts_data = []
            for article in articles:
                if article.get("abstract"):
                    abstracts_data.append({
                        "pmid": article.get("pmid", ""),
                        "title": article.get("title", ""),
                        "abstract": article.get("abstract", ""),
                        "journal": article.get("journal", ""),
                        "publication_date": article.get("publication_date", ""),
                        "authors": str(article.get("authors", [])),
                        "mesh_terms": str(article.get("mesh_terms", [])),
                        "keywords": str(article.get("keywords", []))
                    })
            
            if abstracts_data:
                # Convert to DataFrame
                df = pd.DataFrame(abstracts_data)
                
                # Save data
                filename = self.generate_filename(
                    f"abstracts_{search_term.replace(' ', '_')}",
                    sample_count=len(df)
                )
                filepath = self.save_data(df, filename, "csv")
                
                self.collection_metadata["samples_collected"] = len(df)
                
                return {
                    "abstracts_collected": len(df),
                    "total_abstract_length": df['abstract'].str.len().sum() if 'abstract' in df.columns else 0,
                    "files_created": [filepath]
                }
            else:
                return {"samples_collected": 0, "files_created": []}
        else:
            return {"samples_collected": 0, "files_created": []}
    
    def _collect_mesh_terms(self, search_term: str, max_results: int) -> Dict[str, Any]:
        """Collect MeSH terms data."""
        self.logger.info(f"Collecting MeSH terms data for '{search_term}'")
        
        # Search for articles
        article_ids = self._search_pubmed(search_term, max_results)
        
        if not article_ids:
            self.logger.warning(f"No articles found for search term: {search_term}")
            return {"samples_collected": 0, "files_created": []}
        
        # Get article details
        articles = self._get_article_details(article_ids)
        
        if articles:
            # Extract MeSH terms
            mesh_data = []
            mesh_term_counts = {}
            
            for article in articles:
                pmid = article.get("pmid", "")
                mesh_terms = article.get("mesh_terms", [])
                
                for term in mesh_terms:
                    mesh_data.append({
                        "pmid": pmid,
                        "title": article.get("title", ""),
                        "mesh_term": term,
                        "journal": article.get("journal", ""),
                        "publication_date": article.get("publication_date", "")
                    })
                    
                    # Count term frequency
                    mesh_term_counts[term] = mesh_term_counts.get(term, 0) + 1
            
            if mesh_data:
                # Convert to DataFrame
                df = pd.DataFrame(mesh_data)
                
                # Save data
                filename = self.generate_filename(
                    f"mesh_terms_{search_term.replace(' ', '_')}",
                    sample_count=len(df)
                )
                filepath = self.save_data(df, filename, "csv")
                
                # Save term frequency data
                freq_df = pd.DataFrame([
                    {"mesh_term": term, "frequency": count}
                    for term, count in mesh_term_counts.items()
                ]).sort_values("frequency", ascending=False)
                
                freq_filename = self.generate_filename(
                    f"mesh_term_frequencies_{search_term.replace(' ', '_')}",
                    sample_count=len(freq_df)
                )
                freq_filepath = self.save_data(freq_df, freq_filename, "csv")
                
                self.collection_metadata["samples_collected"] = len(df)
                
                return {
                    "mesh_terms_collected": len(df),
                    "unique_mesh_terms": len(mesh_term_counts),
                    "top_mesh_terms": dict(list(mesh_term_counts.items())[:10]),
                    "files_created": [filepath, freq_filepath]
                }
            else:
                return {"samples_collected": 0, "files_created": []}
        else:
            return {"samples_collected": 0, "files_created": []}
    
    def get_available_datasets(self) -> List[Dict[str, Any]]:
        """Get list of available datasets from PubMed."""
        datasets = []
        
        for search_term in self.search_terms:
            for data_type in self.data_types:
                datasets.append({
                    "search_term": search_term,
                    "data_type": data_type,
                    "description": f"PubMed {data_type} data for {search_term}",
                    "estimated_results": self.sample_limit,
                    "source": "PubMed"
                })
        
        return datasets
