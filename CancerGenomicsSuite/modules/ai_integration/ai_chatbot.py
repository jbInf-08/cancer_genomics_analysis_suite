"""
AI-Powered Chatbot Assistant for Cancer Genomics Analysis

This module provides an intelligent chatbot assistant that can answer questions,
provide analysis guidance, and assist users with genomic data analysis tasks.
"""

import os
import json
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import asyncio
import re
from pathlib import Path

# LLM and NLP libraries
import openai
from anthropic import Anthropic
from transformers import (
    AutoTokenizer, AutoModelForCausalLM, 
    pipeline, TextGenerationPipeline
)
from sentence_transformers import SentenceTransformer
import torch
import numpy as np

# LangChain for conversational AI
from langchain import LLMChain, PromptTemplate
from langchain.llms import OpenAI, Anthropic as LangChainAnthropic
from langchain.embeddings import OpenAIEmbeddings, HuggingFaceEmbeddings
from langchain.vectorstores import Chroma, FAISS
from langchain.chains import ConversationalRetrievalChain, RetrievalQA
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.tools import BaseTool

# Natural Language Processing
import spacy
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from textblob import TextBlob

# Data processing
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Vector databases
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class ChatbotConfig:
    """Configuration for the AI chatbot."""
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    model_name: str = "gpt-3.5-turbo"
    max_tokens: int = 1000
    temperature: float = 0.7
    memory_type: str = "buffer"  # buffer, summary
    knowledge_base_path: str = "./knowledge_base"
    context_window: int = 10
    response_style: str = "professional"  # professional, casual, technical


@dataclass
class ChatMessage:
    """Chat message structure."""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = None


@dataclass
class ChatResponse:
    """Chat response structure."""
    message: str
    confidence: float
    sources: List[str]
    suggestions: List[str]
    metadata: Dict[str, Any]


class GenomicAnalysisAssistant:
    """AI-powered assistant for genomic analysis."""
    
    def __init__(self, config: ChatbotConfig = None):
        self.config = config or ChatbotConfig()
        self.llm = None
        self.memory = None
        self.knowledge_base = None
        self.qa_chain = None
        self.tools = []
        self.conversation_history = []
        self._initialize_models()
        self._setup_tools()
        
    def _initialize_models(self):
        """Initialize LLM and memory models."""
        try:
            # Initialize LLM
            if self.config.openai_api_key:
                openai.api_key = self.config.openai_api_key
                self.llm = OpenAI(
                    model_name=self.config.model_name,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens
                )
            elif self.config.anthropic_api_key:
                self.llm = LangChainAnthropic(
                    model="claude-2",
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens
                )
            
            # Initialize memory
            if self.config.memory_type == "buffer":
                self.memory = ConversationBufferMemory(
                    memory_key="chat_history",
                    return_messages=True
                )
            elif self.config.memory_type == "summary":
                self.memory = ConversationSummaryMemory(
                    llm=self.llm,
                    memory_key="chat_history",
                    return_messages=True
                )
            
            # Initialize embeddings
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            
            logger.info("Chatbot models initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing chatbot models: {e}")
    
    def _setup_tools(self):
        """Setup tools for the chatbot."""
        self.tools = [
            Tool(
                name="genomic_analysis",
                description="Perform genomic data analysis including mutation analysis, gene expression analysis, and pathway analysis",
                func=self._perform_genomic_analysis
            ),
            Tool(
                name="data_visualization",
                description="Create visualizations for genomic data including plots, charts, and interactive dashboards",
                func=self._create_visualization
            ),
            Tool(
                name="literature_search",
                description="Search scientific literature for genomic information and research papers",
                func=self._search_literature
            ),
            Tool(
                name="statistical_analysis",
                description="Perform statistical analysis on genomic data including hypothesis testing and correlation analysis",
                func=self._perform_statistical_analysis
            ),
            Tool(
                name="data_preprocessing",
                description="Preprocess genomic data including quality control, normalization, and feature engineering",
                func=self._preprocess_data
            ),
            Tool(
                name="model_training",
                description="Train machine learning models for genomic prediction tasks",
                func=self._train_model
            )
        ]
    
    def setup_knowledge_base(self, documents: List[str], metadatas: List[Dict] = None):
        """Setup knowledge base for the chatbot."""
        if metadatas is None:
            metadatas = [{}] * len(documents)
        
        # Create vector store
        self.knowledge_base = Chroma.from_texts(
            texts=documents,
            embedding=self.embeddings,
            metadatas=metadatas,
            persist_directory=self.config.knowledge_base_path
        )
        
        # Create QA chain
        if self.llm:
            self.qa_chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=self.knowledge_base.as_retriever(),
                memory=self.memory,
                return_source_documents=True
            )
        
        logger.info(f"Knowledge base setup with {len(documents)} documents")
    
    def chat(self, user_message: str, context: Dict[str, Any] = None) -> ChatResponse:
        """Main chat interface."""
        logger.info(f"Processing user message: {user_message[:100]}...")
        
        # Add user message to conversation history
        user_msg = ChatMessage(
            role="user",
            content=user_message,
            timestamp=datetime.now(),
            metadata=context or {}
        )
        self.conversation_history.append(user_msg)
        
        # Determine intent and generate response
        intent = self._classify_intent(user_message)
        response = self._generate_response(user_message, intent, context)
        
        # Add assistant response to conversation history
        assistant_msg = ChatMessage(
            role="assistant",
            content=response.message,
            timestamp=datetime.now(),
            metadata={
                'intent': intent,
                'confidence': response.confidence,
                'sources': response.sources
            }
        )
        self.conversation_history.append(assistant_msg)
        
        return response
    
    def _classify_intent(self, message: str) -> str:
        """Classify user intent from message."""
        message_lower = message.lower()
        
        # Define intent patterns
        intent_patterns = {
            'analysis': ['analyze', 'analysis', 'examine', 'study', 'investigate'],
            'visualization': ['plot', 'chart', 'graph', 'visualize', 'show'],
            'explanation': ['explain', 'what is', 'how does', 'why', 'meaning'],
            'help': ['help', 'assist', 'guide', 'how to', 'tutorial'],
            'data_processing': ['process', 'clean', 'preprocess', 'normalize'],
            'statistics': ['statistical', 'correlation', 'significance', 'test'],
            'literature': ['paper', 'research', 'study', 'publication', 'literature'],
            'model': ['model', 'predict', 'train', 'machine learning', 'ai']
        }
        
        # Score each intent
        intent_scores = {}
        for intent, keywords in intent_patterns.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            intent_scores[intent] = score
        
        # Return intent with highest score
        if intent_scores:
            return max(intent_scores, key=intent_scores.get)
        else:
            return 'general'
    
    def _generate_response(self, message: str, intent: str, context: Dict[str, Any] = None) -> ChatResponse:
        """Generate response based on intent and context."""
        try:
            if intent == 'analysis' and self._has_analysis_tools():
                return self._handle_analysis_request(message, context)
            elif intent == 'visualization' and self._has_visualization_tools():
                return self._handle_visualization_request(message, context)
            elif intent == 'explanation':
                return self._handle_explanation_request(message)
            elif intent == 'help':
                return self._handle_help_request(message)
            elif intent == 'literature' and self.qa_chain:
                return self._handle_literature_request(message)
            else:
                return self._handle_general_request(message)
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return ChatResponse(
                message=f"I apologize, but I encountered an error while processing your request: {str(e)}",
                confidence=0.0,
                sources=[],
                suggestions=["Try rephrasing your question", "Check if the required data is available"],
                metadata={'error': str(e)}
            )
    
    def _handle_analysis_request(self, message: str, context: Dict[str, Any] = None) -> ChatResponse:
        """Handle genomic analysis requests."""
        # Extract analysis parameters from message
        analysis_type = self._extract_analysis_type(message)
        parameters = self._extract_parameters(message)
        
        # Generate analysis prompt
        prompt = f"""
        Based on the user's request: "{message}"
        
        Analysis type: {analysis_type}
        Parameters: {parameters}
        
        Please provide a detailed analysis plan and explain what genomic analysis would be most appropriate.
        """
        
        if self.llm:
            response_text = self.llm(prompt)
        else:
            response_text = f"I can help you with {analysis_type} analysis. Here's what I would recommend..."
        
        return ChatResponse(
            message=response_text,
            confidence=0.8,
            sources=["Genomic analysis knowledge base"],
            suggestions=[
                "Would you like me to perform this analysis on your data?",
                "Do you need help with data preprocessing first?",
                "Would you like to see example visualizations?"
            ],
            metadata={'analysis_type': analysis_type, 'parameters': parameters}
        )
    
    def _handle_visualization_request(self, message: str, context: Dict[str, Any] = None) -> ChatResponse:
        """Handle visualization requests."""
        # Extract visualization type
        viz_type = self._extract_visualization_type(message)
        
        prompt = f"""
        The user wants to create a visualization: "{message}"
        
        Visualization type: {viz_type}
        
        Please provide guidance on the best visualization approach and explain what type of plot would be most effective.
        """
        
        if self.llm:
            response_text = self.llm(prompt)
        else:
            response_text = f"For {viz_type} visualization, I recommend using appropriate plot types..."
        
        return ChatResponse(
            message=response_text,
            confidence=0.7,
            sources=["Data visualization best practices"],
            suggestions=[
                "Would you like me to create this visualization?",
                "Do you have the data ready for visualization?",
                "Would you like to see example plots?"
            ],
            metadata={'visualization_type': viz_type}
        )
    
    def _handle_explanation_request(self, message: str) -> ChatResponse:
        """Handle explanation requests."""
        # Extract concept to explain
        concept = self._extract_concept(message)
        
        prompt = f"""
        The user is asking for an explanation: "{message}"
        
        Concept to explain: {concept}
        
        Please provide a clear, comprehensive explanation suitable for someone working in cancer genomics.
        Include relevant examples and practical applications.
        """
        
        if self.llm:
            response_text = self.llm(prompt)
        else:
            response_text = f"Let me explain {concept} in the context of cancer genomics..."
        
        return ChatResponse(
            message=response_text,
            confidence=0.9,
            sources=["Genomic knowledge base", "Scientific literature"],
            suggestions=[
                "Would you like more details on any specific aspect?",
                "Do you have questions about practical applications?",
                "Would you like to see related concepts?"
            ],
            metadata={'concept': concept}
        )
    
    def _handle_help_request(self, message: str) -> ChatResponse:
        """Handle help requests."""
        help_topics = [
            "Genomic data analysis",
            "Data visualization",
            "Statistical analysis",
            "Machine learning models",
            "Literature search",
            "Data preprocessing"
        ]
        
        response_text = """
        I'm here to help you with cancer genomics analysis! Here are the main areas I can assist with:
        
        • **Genomic Analysis**: Mutation analysis, gene expression analysis, pathway analysis
        • **Data Visualization**: Creating plots, charts, and interactive dashboards
        • **Statistical Analysis**: Hypothesis testing, correlation analysis, significance testing
        • **Machine Learning**: Training models for prediction and classification
        • **Literature Search**: Finding relevant research papers and scientific information
        • **Data Preprocessing**: Quality control, normalization, feature engineering
        
        You can ask me questions like:
        - "How do I analyze gene expression data?"
        - "What's the best way to visualize mutation data?"
        - "Can you explain what a p-value means?"
        - "Help me find papers about BRCA1 mutations"
        """
        
        return ChatResponse(
            message=response_text,
            confidence=1.0,
            sources=["Help documentation"],
            suggestions=help_topics,
            metadata={'help_type': 'general'}
        )
    
    def _handle_literature_request(self, message: str) -> ChatResponse:
        """Handle literature search requests."""
        if not self.qa_chain:
            return ChatResponse(
                message="I don't have access to a literature knowledge base. Please set up the knowledge base first.",
                confidence=0.0,
                sources=[],
                suggestions=["Set up knowledge base with scientific papers"],
                metadata={'error': 'No knowledge base available'}
            )
        
        try:
            result = self.qa_chain({"question": message})
            response_text = result['answer']
            sources = [doc.metadata.get('source', 'Unknown') for doc in result.get('source_documents', [])]
            
            return ChatResponse(
                message=response_text,
                confidence=0.8,
                sources=sources,
                suggestions=[
                    "Would you like more details on any of these sources?",
                    "Do you need help finding related papers?",
                    "Would you like me to summarize the key findings?"
                ],
                metadata={'search_query': message}
            )
        except Exception as e:
            logger.error(f"Error in literature search: {e}")
            return ChatResponse(
                message="I encountered an error while searching the literature. Please try rephrasing your question.",
                confidence=0.0,
                sources=[],
                suggestions=["Try a different search query", "Check if the knowledge base is properly set up"],
                metadata={'error': str(e)}
            )
    
    def _handle_general_request(self, message: str) -> ChatResponse:
        """Handle general requests."""
        prompt = f"""
        The user has asked: "{message}"
        
        Please provide a helpful response related to cancer genomics analysis. 
        If the question is not related to genomics, politely redirect to genomic topics.
        """
        
        if self.llm:
            response_text = self.llm(prompt)
        else:
            response_text = "I'm here to help with cancer genomics analysis. Could you please ask a question related to genomic data analysis, visualization, or research?"
        
        return ChatResponse(
            message=response_text,
            confidence=0.6,
            sources=["General knowledge"],
            suggestions=[
                "Ask about genomic analysis methods",
                "Request help with data visualization",
                "Inquire about statistical analysis"
            ],
            metadata={'request_type': 'general'}
        )
    
    def _extract_analysis_type(self, message: str) -> str:
        """Extract analysis type from message."""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['mutation', 'variant', 'snp']):
            return 'mutation_analysis'
        elif any(word in message_lower for word in ['expression', 'transcript', 'rna']):
            return 'expression_analysis'
        elif any(word in message_lower for word in ['pathway', 'enrichment', 'go']):
            return 'pathway_analysis'
        elif any(word in message_lower for word in ['survival', 'prognosis', 'outcome']):
            return 'survival_analysis'
        elif any(word in message_lower for word in ['correlation', 'association']):
            return 'correlation_analysis'
        else:
            return 'general_analysis'
    
    def _extract_visualization_type(self, message: str) -> str:
        """Extract visualization type from message."""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['heatmap', 'heat map']):
            return 'heatmap'
        elif any(word in message_lower for word in ['scatter', 'scatter plot']):
            return 'scatter_plot'
        elif any(word in message_lower for word in ['bar', 'bar chart']):
            return 'bar_chart'
        elif any(word in message_lower for word in ['line', 'line plot']):
            return 'line_plot'
        elif any(word in message_lower for word in ['box', 'box plot']):
            return 'box_plot'
        elif any(word in message_lower for word in ['volcano', 'volcano plot']):
            return 'volcano_plot'
        else:
            return 'general_visualization'
    
    def _extract_concept(self, message: str) -> str:
        """Extract concept to explain from message."""
        # Simple extraction - look for "what is", "explain", etc.
        patterns = [
            r'what is (.+?)\?',
            r'explain (.+?)(?:\?|$)',
            r'define (.+?)(?:\?|$)',
            r'meaning of (.+?)(?:\?|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message.lower())
            if match:
                return match.group(1).strip()
        
        return 'general concept'
    
    def _extract_parameters(self, message: str) -> Dict[str, Any]:
        """Extract parameters from message."""
        parameters = {}
        
        # Look for numbers
        numbers = re.findall(r'\d+\.?\d*', message)
        if numbers:
            parameters['numbers'] = [float(n) for n in numbers]
        
        # Look for file names or data sources
        file_patterns = [
            r'file (.+?)(?:\s|$)',
            r'data (.+?)(?:\s|$)',
            r'dataset (.+?)(?:\s|$)'
        ]
        
        for pattern in file_patterns:
            match = re.search(pattern, message.lower())
            if match:
                parameters['data_source'] = match.group(1).strip()
                break
        
        return parameters
    
    def _has_analysis_tools(self) -> bool:
        """Check if analysis tools are available."""
        return any(tool.name == 'genomic_analysis' for tool in self.tools)
    
    def _has_visualization_tools(self) -> bool:
        """Check if visualization tools are available."""
        return any(tool.name == 'data_visualization' for tool in self.tools)
    
    def _perform_genomic_analysis(self, query: str) -> str:
        """Tool function for genomic analysis."""
        return f"Performing genomic analysis based on: {query}"
    
    def _create_visualization(self, query: str) -> str:
        """Tool function for data visualization."""
        return f"Creating visualization based on: {query}"
    
    def _search_literature(self, query: str) -> str:
        """Tool function for literature search."""
        return f"Searching literature for: {query}"
    
    def _perform_statistical_analysis(self, query: str) -> str:
        """Tool function for statistical analysis."""
        return f"Performing statistical analysis: {query}"
    
    def _preprocess_data(self, query: str) -> str:
        """Tool function for data preprocessing."""
        return f"Preprocessing data: {query}"
    
    def _train_model(self, query: str) -> str:
        """Tool function for model training."""
        return f"Training model: {query}"
    
    def get_conversation_history(self) -> List[ChatMessage]:
        """Get conversation history."""
        return self.conversation_history
    
    def clear_conversation(self):
        """Clear conversation history."""
        self.conversation_history = []
        if self.memory:
            self.memory.clear()
    
    def export_conversation(self, filepath: str):
        """Export conversation to file."""
        conversation_data = [asdict(msg) for msg in self.conversation_history]
        
        with open(filepath, 'w') as f:
            json.dump(conversation_data, f, indent=2, default=str)
        
        logger.info(f"Conversation exported to {filepath}")


class QueryProcessor:
    """Process and understand user queries."""
    
    def __init__(self):
        self.intent_classifier = None
        self.entity_extractor = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize NLP models for query processing."""
        try:
            # Initialize spaCy for entity extraction
            self.entity_extractor = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found. Entity extraction will be limited.")
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """Process user query and extract information."""
        result = {
            'original_query': query,
            'intent': self._classify_intent(query),
            'entities': self._extract_entities(query),
            'parameters': self._extract_parameters(query),
            'complexity': self._assess_complexity(query),
            'domain': self._identify_domain(query)
        }
        
        return result
    
    def _classify_intent(self, query: str) -> str:
        """Classify user intent."""
        query_lower = query.lower()
        
        intent_patterns = {
            'question': ['what', 'how', 'why', 'when', 'where', 'which', 'who'],
            'request': ['can you', 'please', 'help me', 'show me', 'create'],
            'command': ['analyze', 'plot', 'generate', 'run', 'execute'],
            'explanation': ['explain', 'describe', 'tell me about'],
            'comparison': ['compare', 'difference', 'versus', 'vs'],
            'validation': ['is this', 'are these', 'does this', 'do these']
        }
        
        for intent, patterns in intent_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                return intent
        
        return 'general'
    
    def _extract_entities(self, query: str) -> List[Dict[str, Any]]:
        """Extract entities from query."""
        entities = []
        
        if self.entity_extractor:
            doc = self.entity_extractor(query)
            for ent in doc.ents:
                entities.append({
                    'text': ent.text,
                    'label': ent.label_,
                    'start': ent.start_char,
                    'end': ent.end_char
                })
        
        # Extract genomic entities using regex
        genomic_patterns = {
            'gene': r'\b[A-Z]{2,}[0-9]*[A-Z]*\b',
            'mutation': r'[A-Z]\d+[A-Z]|[A-Z]\d+[a-z]',
            'chromosome': r'chr[0-9XY]+',
            'protein': r'\b[A-Z][a-z]+[A-Z][a-z]+\b'
        }
        
        for entity_type, pattern in genomic_patterns.items():
            matches = re.finditer(pattern, query)
            for match in matches:
                entities.append({
                    'text': match.group(),
                    'label': entity_type,
                    'start': match.start(),
                    'end': match.end()
                })
        
        return entities
    
    def _extract_parameters(self, query: str) -> Dict[str, Any]:
        """Extract parameters from query."""
        parameters = {}
        
        # Extract numbers
        numbers = re.findall(r'\d+\.?\d*', query)
        if numbers:
            parameters['numbers'] = [float(n) for n in numbers]
        
        # Extract file paths
        file_paths = re.findall(r'[a-zA-Z0-9_/\\]+\.(?:csv|tsv|vcf|bam|fastq)', query)
        if file_paths:
            parameters['files'] = file_paths
        
        # Extract thresholds
        threshold_patterns = [
            r'p[<>=]\s*(\d+\.?\d*)',
            r'fold change[<>=]\s*(\d+\.?\d*)',
            r'fdr[<>=]\s*(\d+\.?\d*)'
        ]
        
        for pattern in threshold_patterns:
            matches = re.findall(pattern, query.lower())
            if matches:
                parameters['thresholds'] = [float(m) for m in matches]
        
        return parameters
    
    def _assess_complexity(self, query: str) -> str:
        """Assess query complexity."""
        word_count = len(query.split())
        sentence_count = len(sent_tokenize(query))
        
        if word_count < 5:
            return 'simple'
        elif word_count < 15 and sentence_count == 1:
            return 'moderate'
        else:
            return 'complex'
    
    def _identify_domain(self, query: str) -> str:
        """Identify the domain of the query."""
        query_lower = query.lower()
        
        domain_keywords = {
            'genomics': ['gene', 'mutation', 'variant', 'genome', 'dna', 'rna'],
            'proteomics': ['protein', 'peptide', 'proteome', 'mass spec'],
            'transcriptomics': ['transcript', 'expression', 'mrna', 'rna-seq'],
            'clinical': ['patient', 'clinical', 'diagnosis', 'treatment', 'survival'],
            'statistics': ['statistical', 'correlation', 'significance', 'p-value'],
            'visualization': ['plot', 'chart', 'graph', 'visualize', 'figure']
        }
        
        domain_scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            domain_scores[domain] = score
        
        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        else:
            return 'general'


class ContextManager:
    """Manage conversation context and memory."""
    
    def __init__(self, max_context_length: int = 10):
        self.max_context_length = max_context_length
        self.context_history = []
        self.current_context = {}
        
    def add_context(self, key: str, value: Any):
        """Add context information."""
        self.current_context[key] = value
        
    def get_context(self, key: str) -> Any:
        """Get context information."""
        return self.current_context.get(key)
    
    def update_context(self, new_context: Dict[str, Any]):
        """Update context with new information."""
        self.current_context.update(new_context)
        
    def save_context_snapshot(self):
        """Save current context as a snapshot."""
        snapshot = {
            'timestamp': datetime.now(),
            'context': self.current_context.copy()
        }
        self.context_history.append(snapshot)
        
        # Keep only recent snapshots
        if len(self.context_history) > self.max_context_length:
            self.context_history = self.context_history[-self.max_context_length:]
    
    def get_relevant_context(self, query: str) -> Dict[str, Any]:
        """Get context relevant to the current query."""
        relevant_context = {}
        
        # Simple relevance based on keyword matching
        query_lower = query.lower()
        
        for key, value in self.current_context.items():
            if isinstance(value, str) and any(word in value.lower() for word in query_lower.split()):
                relevant_context[key] = value
        
        return relevant_context
    
    def clear_context(self):
        """Clear current context."""
        self.current_context = {}
    
    def get_context_summary(self) -> str:
        """Get a summary of current context."""
        if not self.current_context:
            return "No context available"
        
        summary_parts = []
        for key, value in self.current_context.items():
            if isinstance(value, str) and len(value) < 100:
                summary_parts.append(f"{key}: {value}")
            else:
                summary_parts.append(f"{key}: {type(value).__name__}")
        
        return "; ".join(summary_parts)
