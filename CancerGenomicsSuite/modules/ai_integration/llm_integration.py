"""
Large Language Model Integration for Cancer Genomics Analysis

This module provides comprehensive LLM integration for processing scientific literature,
clinical notes, generating reports, and answering genomic queries using state-of-the-art
language models.
"""

import os
import json
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import asyncio
import aiohttp
import re
from pathlib import Path

# LLM and NLP libraries
try:
    import openai
except ImportError:
    openai = None

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

try:
    from transformers import (
        AutoTokenizer, AutoModel, AutoModelForCausalLM,
        pipeline, TextGenerationPipeline
    )
except ImportError:
    AutoTokenizer = AutoModel = AutoModelForCausalLM = None
    pipeline = TextGenerationPipeline = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    import torch
    import numpy as np
except ImportError:
    torch = None
    np = None

try:
    from langchain import LLMChain, PromptTemplate
    from langchain_community.llms import OpenAI, Anthropic as LangChainAnthropic
    from langchain_community.embeddings import OpenAIEmbeddings, HuggingFaceEmbeddings
    from langchain_community.vectorstores import Chroma, FAISS
    from langchain_community.document_loaders import TextLoader, PyPDFLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError:
    LLMChain = PromptTemplate = None
    OpenAI = LangChainAnthropic = None
    OpenAIEmbeddings = HuggingFaceEmbeddings = None
    Chroma = FAISS = None
    TextLoader = PyPDFLoader = None
    RecursiveCharacterTextSplitter = None

try:
    from langchain.chains import RetrievalQA, ConversationalRetrievalChain
    from langchain.memory import ConversationBufferMemory
except ImportError:
    RetrievalQA = ConversationalRetrievalChain = None
    ConversationBufferMemory = None

# Scientific text processing
try:
    import spacy
    from spacy import displacy
except ImportError:
    spacy = None
    displacy = None

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import sent_tokenize, word_tokenize
except ImportError:
    nltk = None
    stopwords = None
    sent_tokenize = word_tokenize = None

try:
    from textblob import TextBlob
except ImportError:
    TextBlob = None

try:
    import gensim
    from gensim import corpora, models
except ImportError:
    gensim = None
    corpora = models = None

# Data processing
try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.cluster import KMeans
    from sklearn.decomposition import LatentDirichletAllocation
except ImportError:
    TfidfVectorizer = cosine_similarity = None
    KMeans = LatentDirichletAllocation = None

# Vector databases
try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None
    Settings = None

try:
    import faiss
except ImportError:
    faiss = None

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM integration."""
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    model_name: str = "gpt-3.5-turbo"
    max_tokens: int = 2000
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    chunk_size: int = 1000
    chunk_overlap: int = 200
    vector_db_path: str = "./vector_db"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass
class Document:
    """Document structure for scientific literature."""
    title: str
    abstract: str
    content: str
    authors: List[str]
    journal: str
    year: int
    doi: str
    keywords: List[str]
    metadata: Dict[str, Any]


@dataclass
class QueryResult:
    """Result structure for genomic queries."""
    query: str
    answer: str
    sources: List[str]
    confidence: float
    timestamp: datetime
    metadata: Dict[str, Any]


class ScientificLiteratureProcessor:
    """Process and analyze scientific literature using LLMs."""
    
    def __init__(self, config: LLMConfig = None):
        self.config = config or LLMConfig()
        self.llm = None
        self.embeddings = None
        self.vectorstore = None
        self.nlp = None
        self._initialize_models()
        
    def _initialize_models(self):
        """Initialize LLM and NLP models."""
        try:
            # Initialize OpenAI
            if self.config.openai_api_key:
                openai.api_key = self.config.openai_api_key
                self.llm = OpenAI(
                    model_name=self.config.model_name,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens
                )
            
            # Initialize embeddings
            self.embeddings = HuggingFaceEmbeddings(
                model_name=self.config.embedding_model
            )
            
            # Initialize spaCy
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("spaCy model not found. Install with: python -m spacy download en_core_web_sm")
                self.nlp = None
            
            # Initialize NLTK
            try:
                nltk.data.find('tokenizers/punkt')
                nltk.data.find('corpora/stopwords')
            except LookupError:
                nltk.download('punkt')
                nltk.download('stopwords')
            
            logger.info("LLM models initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing LLM models: {e}")
    
    def process_paper(self, paper_path: str) -> Document:
        """Process a scientific paper and extract structured information."""
        logger.info(f"Processing paper: {paper_path}")
        
        try:
            # Load document
            if paper_path.endswith('.pdf'):
                loader = PyPDFLoader(paper_path)
            else:
                loader = TextLoader(paper_path)
            
            documents = loader.load()
            content = documents[0].page_content
            
            # Extract metadata using LLM
            metadata = self._extract_metadata_with_llm(content)
            
            # Create document object
            doc = Document(
                title=metadata.get('title', 'Unknown'),
                abstract=metadata.get('abstract', ''),
                content=content,
                authors=metadata.get('authors', []),
                journal=metadata.get('journal', 'Unknown'),
                year=metadata.get('year', 2023),
                doi=metadata.get('doi', ''),
                keywords=metadata.get('keywords', []),
                metadata=metadata
            )
            
            return doc
            
        except Exception as e:
            logger.error(f"Error processing paper {paper_path}: {e}")
            return None
    
    def _extract_metadata_with_llm(self, content: str) -> Dict[str, Any]:
        """Extract metadata from paper content using LLM."""
        if not self.llm:
            return {}
        
        prompt = f"""
        Extract the following information from this scientific paper:
        
        Content: {content[:2000]}...
        
        Please provide a JSON response with:
        - title: The paper title
        - abstract: The abstract (if available)
        - authors: List of authors
        - journal: Journal name
        - year: Publication year
        - doi: DOI if available
        - keywords: List of key terms
        
        JSON Response:
        """
        
        try:
            response = self.llm(prompt)
            # Parse JSON response
            metadata = json.loads(response)
            return metadata
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            return {}
    
    def analyze_genomic_mentions(self, content: str) -> Dict[str, Any]:
        """Analyze genomic mentions in scientific text."""
        if not self.nlp:
            return {}
        
        doc = self.nlp(content)
        
        # Extract entities
        entities = {
            'genes': [],
            'proteins': [],
            'mutations': [],
            'diseases': [],
            'drugs': []
        }
        
        for ent in doc.ents:
            if ent.label_ == "GENE":
                entities['genes'].append(ent.text)
            elif ent.label_ == "PROTEIN":
                entities['proteins'].append(ent.text)
            elif ent.label_ == "DISEASE":
                entities['diseases'].append(ent.text)
            elif ent.label_ == "CHEMICAL":
                entities['drugs'].append(ent.text)
        
        # Extract mutations using regex
        mutation_pattern = r'[A-Z]\d+[A-Z]|[A-Z]\d+[a-z]|[a-z]\d+[A-Z]'
        mutations = re.findall(mutation_pattern, content)
        entities['mutations'] = list(set(mutations))
        
        # Analyze sentiment
        sentiment = TextBlob(content).sentiment
        
        return {
            'entities': entities,
            'sentiment': {
                'polarity': sentiment.polarity,
                'subjectivity': sentiment.subjectivity
            },
            'word_count': len(content.split()),
            'sentence_count': len(sent_tokenize(content))
        }
    
    def build_literature_database(self, papers_dir: str) -> str:
        """Build a searchable database from scientific papers."""
        logger.info(f"Building literature database from {papers_dir}")
        
        papers_path = Path(papers_dir)
        documents = []
        
        # Process all papers
        for paper_path in papers_path.glob("**/*.pdf"):
            doc = self.process_paper(str(paper_path))
            if doc:
                documents.append(doc)
        
        # Create text splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap
        )
        
        # Split documents
        texts = []
        metadatas = []
        for doc in documents:
            chunks = text_splitter.split_text(doc.content)
            texts.extend(chunks)
            metadatas.extend([asdict(doc)] * len(chunks))
        
        # Create vector store
        self.vectorstore = Chroma.from_texts(
            texts=texts,
            embedding=self.embeddings,
            metadatas=metadatas,
            persist_directory=self.config.vector_db_path
        )
        
        logger.info(f"Created vector database with {len(texts)} chunks from {len(documents)} papers")
        return self.config.vector_db_path
    
    def search_literature(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search scientific literature using semantic similarity."""
        if not self.vectorstore:
            logger.error("Literature database not built. Call build_literature_database first.")
            return []
        
        # Perform similarity search
        docs = self.vectorstore.similarity_search(query, k=k)
        
        results = []
        for doc in docs:
            results.append({
                'content': doc.page_content,
                'metadata': doc.metadata,
                'relevance_score': self._calculate_relevance_score(query, doc.page_content)
            })
        
        return sorted(results, key=lambda x: x['relevance_score'], reverse=True)
    
    def _calculate_relevance_score(self, query: str, content: str) -> float:
        """Calculate relevance score between query and content."""
        # Simple TF-IDF based similarity
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform([query, content])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return similarity


class ClinicalNotesAnalyzer:
    """Analyze clinical notes using LLMs."""
    
    def __init__(self, config: LLMConfig = None):
        self.config = config or LLMConfig()
        self.llm = None
        self.nlp = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize models for clinical note analysis."""
        if self.config.openai_api_key:
            openai.api_key = self.config.openai_api_key
            self.llm = OpenAI(
                model_name=self.config.model_name,
                temperature=0.1,  # Lower temperature for clinical accuracy
                max_tokens=self.config.max_tokens
            )
        
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found")
    
    def extract_clinical_entities(self, note: str) -> Dict[str, Any]:
        """Extract clinical entities from notes."""
        if not self.nlp:
            return {}
        
        doc = self.nlp(note)
        
        entities = {
            'symptoms': [],
            'diagnoses': [],
            'medications': [],
            'procedures': [],
            'vital_signs': [],
            'lab_values': []
        }
        
        for ent in doc.ents:
            if ent.label_ in ["SYMPTOM", "DISEASE"]:
                entities['symptoms'].append(ent.text)
            elif ent.label_ == "MEDICATION":
                entities['medications'].append(ent.text)
            elif ent.label_ == "PROCEDURE":
                entities['procedures'].append(ent.text)
        
        # Extract vital signs and lab values using regex
        vital_patterns = {
            'blood_pressure': r'(\d+/\d+)\s*mmHg',
            'heart_rate': r'HR[:\s]*(\d+)\s*bpm',
            'temperature': r'temp[erature]*[:\s]*(\d+\.?\d*)\s*[°F°C]',
            'weight': r'weight[:\s]*(\d+\.?\d*)\s*(?:kg|lb|lbs)',
            'height': r'height[:\s]*(\d+\.?\d*)\s*(?:cm|in|inches)'
        }
        
        for key, pattern in vital_patterns.items():
            matches = re.findall(pattern, note, re.IGNORECASE)
            entities['vital_signs'].extend([{key: match} for match in matches])
        
        return entities
    
    def analyze_sentiment(self, note: str) -> Dict[str, Any]:
        """Analyze sentiment and emotional tone of clinical notes."""
        blob = TextBlob(note)
        sentiment = blob.sentiment
        
        # Categorize sentiment
        if sentiment.polarity > 0.1:
            sentiment_category = "Positive"
        elif sentiment.polarity < -0.1:
            sentiment_category = "Negative"
        else:
            sentiment_category = "Neutral"
        
        return {
            'polarity': sentiment.polarity,
            'subjectivity': sentiment.subjectivity,
            'category': sentiment_category,
            'confidence': abs(sentiment.polarity)
        }
    
    def summarize_note(self, note: str) -> str:
        """Generate a summary of clinical notes using LLM."""
        if not self.llm:
            return "LLM not available for summarization"
        
        prompt = f"""
        Summarize the following clinical note in a clear, concise manner:
        
        Note: {note}
        
        Please provide a summary that includes:
        - Key symptoms and findings
        - Diagnoses or assessments
        - Treatment plans or recommendations
        - Important follow-up items
        
        Summary:
        """
        
        try:
            summary = self.llm(prompt)
            return summary
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return "Error generating summary"
    
    def extract_genomic_references(self, note: str) -> Dict[str, Any]:
        """Extract genomic references from clinical notes."""
        genomic_patterns = {
            'genes': r'\b[A-Z]{2,}[0-9]*[A-Z]*\b',  # Gene symbols
            'mutations': r'[A-Z]\d+[A-Z]|[A-Z]\d+[a-z]',  # Mutation notation
            'variants': r'rs\d+',  # SNP IDs
            'chromosomes': r'chr[0-9XY]+',  # Chromosome references
            'genetic_tests': r'(?:genetic|genomic|molecular|sequencing|NGS|WGS|WES)',
            'pharmacogenomics': r'(?:pharmacogenomic|drug.*gene|gene.*drug)'
        }
        
        findings = {}
        for category, pattern in genomic_patterns.items():
            matches = re.findall(pattern, note, re.IGNORECASE)
            findings[category] = list(set(matches))
        
        return findings


class GenomicQueryEngine:
    """AI-powered genomic query engine."""
    
    def __init__(self, config: LLMConfig = None):
        self.config = config or LLMConfig()
        self.llm = None
        self.vectorstore = None
        self.qa_chain = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize the query engine."""
        if self.config.openai_api_key:
            openai.api_key = self.config.openai_api_key
            self.llm = OpenAI(
                model_name=self.config.model_name,
                temperature=0.1,
                max_tokens=self.config.max_tokens
            )
        
        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.config.embedding_model
        )
    
    def setup_knowledge_base(self, documents: List[str], metadatas: List[Dict] = None):
        """Setup knowledge base for genomic queries."""
        if metadatas is None:
            metadatas = [{}] * len(documents)
        
        # Create vector store
        self.vectorstore = Chroma.from_texts(
            texts=documents,
            embedding=self.embeddings,
            metadatas=metadatas
        )
        
        # Create QA chain
        if self.llm:
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.vectorstore.as_retriever(),
                return_source_documents=True
            )
    
    def answer_query(self, query: str) -> QueryResult:
        """Answer genomic queries using the knowledge base."""
        if not self.qa_chain:
            return QueryResult(
                query=query,
                answer="Knowledge base not set up. Please call setup_knowledge_base first.",
                sources=[],
                confidence=0.0,
                timestamp=datetime.now(),
                metadata={}
            )
        
        try:
            # Get answer from QA chain
            result = self.qa_chain({"query": query})
            
            # Extract sources
            sources = []
            if 'source_documents' in result:
                sources = [doc.metadata.get('source', 'Unknown') for doc in result['source_documents']]
            
            # Calculate confidence (simplified)
            confidence = self._calculate_confidence(query, result['result'])
            
            return QueryResult(
                query=query,
                answer=result['result'],
                sources=sources,
                confidence=confidence,
                timestamp=datetime.now(),
                metadata={'model': self.config.model_name}
            )
            
        except Exception as e:
            logger.error(f"Error answering query: {e}")
            return QueryResult(
                query=query,
                answer=f"Error processing query: {str(e)}",
                sources=[],
                confidence=0.0,
                timestamp=datetime.now(),
                metadata={'error': str(e)}
            )
    
    def _calculate_confidence(self, query: str, answer: str) -> float:
        """Calculate confidence score for the answer."""
        # Simple heuristic based on answer length and keyword overlap
        query_words = set(query.lower().split())
        answer_words = set(answer.lower().split())
        
        overlap = len(query_words.intersection(answer_words))
        total_query_words = len(query_words)
        
        if total_query_words == 0:
            return 0.0
        
        base_confidence = overlap / total_query_words
        
        # Adjust based on answer length (longer answers might be more comprehensive)
        length_factor = min(len(answer.split()) / 50, 1.0)
        
        return min(base_confidence * length_factor, 1.0)
    
    def explain_genomic_concept(self, concept: str) -> str:
        """Explain genomic concepts in simple terms."""
        if not self.llm:
            return "LLM not available for explanations"
        
        prompt = f"""
        Explain the following genomic concept in simple, understandable terms:
        
        Concept: {concept}
        
        Please provide:
        1. A clear definition
        2. Why it's important in cancer research
        3. How it's used in clinical practice
        4. Any relevant examples
        
        Explanation:
        """
        
        try:
            explanation = self.llm(prompt)
            return explanation
        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            return "Error generating explanation"


class ReportGenerator:
    """AI-powered report generation for genomic analysis."""
    
    def __init__(self, config: LLMConfig = None):
        self.config = config or LLMConfig()
        self.llm = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize the report generator."""
        if self.config.openai_api_key:
            openai.api_key = self.config.openai_api_key
            self.llm = OpenAI(
                model_name=self.config.model_name,
                temperature=0.3,
                max_tokens=self.config.max_tokens
            )
    
    def generate_analysis_report(self, analysis_data: Dict[str, Any], 
                               report_type: str = "comprehensive") -> str:
        """Generate analysis report from genomic data."""
        if not self.llm:
            return "LLM not available for report generation"
        
        # Create report template based on type
        if report_type == "comprehensive":
            template = self._get_comprehensive_template()
        elif report_type == "clinical":
            template = self._get_clinical_template()
        elif report_type == "research":
            template = self._get_research_template()
        else:
            template = self._get_basic_template()
        
        # Format data for LLM
        formatted_data = self._format_analysis_data(analysis_data)
        
        prompt = f"""
        Generate a {report_type} genomic analysis report based on the following data:
        
        {formatted_data}
        
        Use this template structure:
        {template}
        
        Please provide a well-structured, professional report that includes:
        - Executive summary
        - Key findings
        - Detailed analysis
        - Clinical implications
        - Recommendations
        - References (if applicable)
        
        Report:
        """
        
        try:
            report = self.llm(prompt)
            return report
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return "Error generating report"
    
    def _get_comprehensive_template(self) -> str:
        """Get comprehensive report template."""
        return """
        1. Executive Summary
        2. Methodology
        3. Genomic Findings
           3.1 Mutation Analysis
           3.2 Copy Number Variations
           3.3 Gene Expression
           3.4 Pathway Analysis
        4. Clinical Interpretation
        5. Therapeutic Implications
        6. Prognostic Factors
        7. Recommendations
        8. Limitations
        9. References
        """
    
    def _get_clinical_template(self) -> str:
        """Get clinical report template."""
        return """
        1. Patient Summary
        2. Genomic Profile
        3. Clinical Significance
        4. Treatment Options
        5. Monitoring Recommendations
        6. Genetic Counseling
        """
    
    def _get_research_template(self) -> str:
        """Get research report template."""
        return """
        1. Abstract
        2. Introduction
        3. Methods
        4. Results
        5. Discussion
        6. Conclusions
        7. Future Directions
        8. References
        """
    
    def _get_basic_template(self) -> str:
        """Get basic report template."""
        return """
        1. Summary
        2. Key Findings
        3. Analysis
        4. Recommendations
        """
    
    def _format_analysis_data(self, data: Dict[str, Any]) -> str:
        """Format analysis data for LLM processing."""
        formatted = []
        
        for key, value in data.items():
            if isinstance(value, dict):
                formatted.append(f"{key}:")
                for subkey, subvalue in value.items():
                    formatted.append(f"  {subkey}: {subvalue}")
            elif isinstance(value, list):
                formatted.append(f"{key}: {', '.join(map(str, value))}")
            else:
                formatted.append(f"{key}: {value}")
        
        return "\n".join(formatted)
    
    def generate_patient_summary(self, patient_data: Dict[str, Any]) -> str:
        """Generate patient summary from genomic and clinical data."""
        if not self.llm:
            return "LLM not available for patient summary generation"
        
        prompt = f"""
        Generate a concise patient summary based on the following data:
        
        Patient Data: {json.dumps(patient_data, indent=2)}
        
        Please provide:
        1. Patient demographics
        2. Clinical presentation
        3. Genomic findings
        4. Key mutations/variants
        5. Clinical implications
        6. Treatment considerations
        
        Patient Summary:
        """
        
        try:
            summary = self.llm(prompt)
            return summary
        except Exception as e:
            logger.error(f"Error generating patient summary: {e}")
            return "Error generating patient summary"
    
    def generate_literature_review(self, topic: str, papers: List[Dict[str, Any]]) -> str:
        """Generate literature review from scientific papers."""
        if not self.llm:
            return "LLM not available for literature review generation"
        
        # Format papers data
        papers_text = ""
        for i, paper in enumerate(papers, 1):
            papers_text += f"\n{i}. {paper.get('title', 'Unknown Title')}\n"
            papers_text += f"   Authors: {', '.join(paper.get('authors', []))}\n"
            papers_text += f"   Journal: {paper.get('journal', 'Unknown')}\n"
            papers_text += f"   Year: {paper.get('year', 'Unknown')}\n"
            papers_text += f"   Abstract: {paper.get('abstract', 'No abstract available')}\n"
        
        prompt = f"""
        Generate a comprehensive literature review on the topic: {topic}
        
        Based on the following papers:
        {papers_text}
        
        Please provide:
        1. Introduction and background
        2. Current state of research
        3. Key findings from the papers
        4. Gaps in current knowledge
        5. Future research directions
        6. Conclusions
        
        Literature Review:
        """
        
        try:
            review = self.llm(prompt)
            return review
        except Exception as e:
            logger.error(f"Error generating literature review: {e}")
            return "Error generating literature review"
