"""
Article Manager Dashboard Module

This module provides a comprehensive Dash-based dashboard for article management,
search, analysis, and visualization.
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import json
from typing import Dict, List, Any, Optional
import logging
import base64
import io
from datetime import datetime, timedelta

from .article_db import ArticleDatabaseManager, ArticleMetadata, create_mock_articles

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ManagerDashboard:
    """
    A comprehensive dashboard for article management and analysis.
    """
    
    def __init__(self, app: dash.Dash, db_path: str = "article_manager.db"):
        """
        Initialize the manager dashboard.
        
        Args:
            app: Dash application instance
            db_path: Path to SQLite database file
        """
        self.app = app
        self.db_manager = ArticleDatabaseManager(db_path)
        self.current_articles = []
        self.setup_callbacks()
    
    def create_layout(self) -> html.Div:
        """
        Create the main dashboard layout.
        
        Returns:
            HTML div containing the dashboard layout
        """
        return html.Div([
            # Header
            html.Div([
                html.H1("Article Manager Dashboard", 
                       className="text-center mb-4"),
                html.P("Comprehensive article management and analysis for cancer genomics research",
                      className="text-center text-muted mb-4")
            ], className="container-fluid"),
            
            # Control Panel
            html.Div([
                html.Div([
                    html.H4("Article Management", className="card-title"),
                    
                    # Quick actions
                    html.Div([
                        html.Button('Load Mock Data', id='load-mock-data', 
                                  className='btn btn-primary me-2'),
                        html.Button('Refresh Database', id='refresh-db', 
                                  className='btn btn-info me-2'),
                        html.Button('Export Articles', id='export-articles', 
                                  className='btn btn-success me-2'),
                        html.Button('Clear Database', id='clear-db', 
                                  className='btn btn-danger')
                    ], className="d-flex flex-wrap gap-2 mb-3"),
                    
                    # Search and filters
                    html.Div([
                        html.Label("Search Articles:"),
                        dcc.Input(
                            id='search-input',
                            type='text',
                            placeholder='Search in title, abstract, authors...',
                            className="form-control mb-2"
                        ),
                        html.Div([
                            html.Div([
                                html.Label("Source:"),
                                dcc.Dropdown(
                                    id='filter-source',
                                    options=[
                                        {'label': 'All Sources', 'value': ''},
                                        {'label': 'PubMed', 'value': 'pubmed'},
                                        {'label': 'arXiv', 'value': 'arxiv'},
                                        {'label': 'Google Scholar', 'value': 'google_scholar'},
                                        {'label': 'RSS', 'value': 'rss'}
                                    ],
                                    value='',
                                    className="mb-2"
                                )
                            ], className="col-md-3"),
                            html.Div([
                                html.Label("Read Status:"),
                                dcc.Dropdown(
                                    id='filter-read-status',
                                    options=[
                                        {'label': 'All', 'value': ''},
                                        {'label': 'Read', 'value': 'read'},
                                        {'label': 'Unread', 'value': 'unread'}
                                    ],
                                    value='',
                                    className="mb-2"
                                )
                            ], className="col-md-3"),
                            html.Div([
                                html.Label("Rating:"),
                                dcc.Dropdown(
                                    id='filter-rating',
                                    options=[
                                        {'label': 'All Ratings', 'value': ''},
                                        {'label': '5 Stars', 'value': '5'},
                                        {'label': '4+ Stars', 'value': '4'},
                                        {'label': '3+ Stars', 'value': '3'}
                                    ],
                                    value='',
                                    className="mb-2"
                                )
                            ], className="col-md-3"),
                            html.Div([
                                html.Label("Date Range:"),
                                dcc.DatePickerRange(
                                    id='filter-date-range',
                                    start_date=datetime.now() - timedelta(days=365),
                                    end_date=datetime.now(),
                                    display_format='YYYY-MM-DD'
                                )
                            ], className="col-md-3")
                        ], className="row mb-3"),
                        html.Button("Search", id="search-button", 
                                  className="btn btn-primary")
                    ])
                    
                ], className="card-body")
            ], className="card mb-4"),
            
            # Main content area
            html.Div([
                # Tabs for different views
                dcc.Tabs(id="main-tabs", value="articles", children=[
                    dcc.Tab(label="Articles", value="articles"),
                    dcc.Tab(label="Collections", value="collections"),
                    dcc.Tab(label="Tags", value="tags"),
                    dcc.Tab(label="Analytics", value="analytics"),
                    dcc.Tab(label="Similarity", value="similarity"),
                    dcc.Tab(label="Topic Modeling", value="topics")
                ]),
                
                # Tab content
                html.Div(id="manager-tab-content", className="mt-3")
                
            ], className="container-fluid"),
            
            # Hidden divs for storing data
            html.Div(id='search-results', style={'display': 'none'}),
            html.Div(id='current-article', style={'display': 'none'}),
            
            # Download components
            dcc.Download(id="download-export"),
            
            # Modals
            self.create_article_modal(),
            self.create_collection_modal(),
            self.create_tag_modal()
        ])
    
    def create_article_modal(self) -> html.Div:
        """Create modal for article details and editing."""
        return html.Div([
            html.Div([
                html.Div([
                    html.Div([
                        html.H4("Article Details", className="modal-title"),
                        html.Button("×", className="btn-close", id="close-article-modal")
                    ], className="modal-header"),
                    html.Div([
                        html.Div(id="article-details-content")
                    ], className="modal-body"),
                    html.Div([
                        html.Button("Close", className="btn btn-secondary", id="close-article-modal-btn"),
                        html.Button("Save Changes", className="btn btn-primary", id="save-article-changes")
                    ], className="modal-footer")
                ], className="modal-content")
            ], className="modal-dialog")
        ], className="modal fade", id="article-modal", tabindex="-1")
    
    def create_collection_modal(self) -> html.Div:
        """Create modal for collection management."""
        return html.Div([
            html.Div([
                html.Div([
                    html.Div([
                        html.H4("Manage Collections", className="modal-title"),
                        html.Button("×", className="btn-close", id="close-collection-modal")
                    ], className="modal-header"),
                    html.Div([
                        html.Div(id="collection-content")
                    ], className="modal-body"),
                    html.Div([
                        html.Button("Close", className="btn btn-secondary", id="close-collection-modal-btn")
                    ], className="modal-footer")
                ], className="modal-content")
            ], className="modal-dialog")
        ], className="modal fade", id="collection-modal", tabindex="-1")
    
    def create_tag_modal(self) -> html.Div:
        """Create modal for tag management."""
        return html.Div([
            html.Div([
                html.Div([
                    html.Div([
                        html.H4("Manage Tags", className="modal-title"),
                        html.Button("×", className="btn-close", id="close-tag-modal")
                    ], className="modal-header"),
                    html.Div([
                        html.Div(id="tag-content")
                    ], className="modal-body"),
                    html.Div([
                        html.Button("Close", className="btn btn-secondary", id="close-tag-modal-btn")
                    ], className="modal-footer")
                ], className="modal-content")
            ], className="modal-dialog")
        ], className="modal fade", id="tag-modal", tabindex="-1")
    
    def create_articles_tab(self) -> html.Div:
        """Create the articles tab content."""
        return html.Div([
            html.Div([
                html.H4("Article List"),
                html.Div([
                    html.Label("Sort by:"),
                    dcc.Dropdown(
                        id="sort-articles",
                        options=[
                            {'label': 'Date Added', 'value': 'created_at'},
                            {'label': 'Title', 'value': 'title'},
                            {'label': 'Journal', 'value': 'journal'},
                            {'label': 'Rating', 'value': 'rating'},
                            {'label': 'Citations', 'value': 'citations'}
                        ],
                        value='created_at',
                        className="mb-2"
                    )
                ], className="mb-3"),
                html.Div(id="articles-list")
            ], className="card")
        ])
    
    def create_collections_tab(self) -> html.Div:
        """Create the collections tab content."""
        return html.Div([
            html.Div([
                html.H4("Collections"),
                html.Div([
                    html.Button("Create New Collection", id="create-collection-btn", 
                              className="btn btn-primary mb-3"),
                    html.Div(id="collections-list")
                ])
            ], className="card")
        ])
    
    def create_tags_tab(self) -> html.Div:
        """Create the tags tab content."""
        return html.Div([
            html.Div([
                html.H4("Tags"),
                html.Div([
                    html.Button("Manage Tags", id="manage-tags-btn", 
                              className="btn btn-primary mb-3"),
                    html.Div(id="tags-list")
                ])
            ], className="card")
        ])
    
    def create_analytics_tab(self) -> html.Div:
        """Create the analytics tab content."""
        return html.Div([
            html.Div([
                html.H4("Article Analytics"),
                dcc.Graph(id="analytics-chart")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Publication Trends"),
                dcc.Graph(id="publication-trends-chart")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Top Journals"),
                dcc.Graph(id="top-journals-chart")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Source Distribution"),
                dcc.Graph(id="source-distribution-chart")
            ], className="card")
        ])
    
    def create_similarity_tab(self) -> html.Div:
        """Create the similarity analysis tab content."""
        return html.Div([
            html.Div([
                html.H4("Article Similarity Analysis"),
                html.Div([
                    html.Label("Select Article:"),
                    dcc.Dropdown(
                        id="similarity-article-selector",
                        placeholder="Select an article...",
                        className="mb-2"
                    ),
                    html.Button("Find Similar Articles", id="find-similar-btn", 
                              className="btn btn-primary mb-3")
                ], className="mb-3"),
                html.Div(id="similarity-results")
            ], className="card")
        ])
    
    def create_topics_tab(self) -> html.Div:
        """Create the topic modeling tab content."""
        return html.Div([
            html.Div([
                html.H4("Topic Modeling"),
                html.Div([
                    html.Label("Number of Topics:"),
                    dcc.Slider(
                        id='n-topics',
                        min=5,
                        max=20,
                        step=1,
                        value=10,
                        marks={i: str(i) for i in range(5, 21, 5)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                    html.Button("Run Topic Modeling", id="run-topic-modeling", 
                              className="btn btn-primary mt-2")
                ], className="mb-3"),
                html.Div(id="topic-modeling-results")
            ], className="card")
        ])
    
    def setup_callbacks(self):
        """Set up all dashboard callbacks."""
        
        @self.app.callback(
            [Output('search-results', 'children'),
             Output('articles-list', 'children')],
            [Input('search-button', 'n_clicks'),
             Input('load-mock-data', 'n_clicks'),
             Input('refresh-db', 'n_clicks')],
            [State('search-input', 'value'),
             State('filter-source', 'value'),
             State('filter-read-status', 'value'),
             State('filter-rating', 'value'),
             State('filter-date-range', 'start_date'),
             State('filter-date-range', 'end_date')]
        )
        def search_articles(n_search, n_mock, n_refresh, query, source, read_status, rating, start_date, end_date):
            """Search and display articles."""
            ctx = callback_context
            if not ctx.triggered:
                return "", html.Div("Use the search form to find articles", className="text-muted")
            
            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
            
            try:
                if trigger_id == 'load-mock-data':
                    # Load mock data
                    mock_articles = create_mock_articles()
                    for article in mock_articles:
                        self.db_manager.add_article(article)
                    
                    articles, total = self.db_manager.search_articles(limit=100)
                    return json.dumps([article.to_dict() for article in articles]), self.create_articles_display(articles)
                
                elif trigger_id == 'refresh-db':
                    # Refresh database
                    articles, total = self.db_manager.search_articles(limit=100)
                    return json.dumps([article.to_dict() for article in articles]), self.create_articles_display(articles)
                
                else:
                    # Search articles
                    filters = {}
                    if source:
                        filters['source'] = source
                    if read_status:
                        filters['read_status'] = read_status
                    if rating:
                        filters['rating'] = int(rating)
                    if start_date:
                        filters['date_from'] = start_date
                    if end_date:
                        filters['date_to'] = end_date
                    
                    articles, total = self.db_manager.search_articles(
                        query=query or "",
                        filters=filters,
                        limit=100
                    )
                    
                    return json.dumps([article.to_dict() for article in articles]), self.create_articles_display(articles)
                
            except Exception as e:
                logger.error(f"Error in search: {e}")
                return "", html.Div(f"Error: {str(e)}", className="alert alert-danger")
        
        @self.app.callback(
            Output('manager-tab-content', 'children'),
            [Input('main-tabs', 'value')]
        )
        def render_tab_content(active_tab):
            """Render content based on active tab."""
            if active_tab == 'articles':
                return self.create_articles_tab()
            elif active_tab == 'collections':
                return self.create_collections_tab()
            elif active_tab == 'tags':
                return self.create_tags_tab()
            elif active_tab == 'analytics':
                return self.create_analytics_tab()
            elif active_tab == 'similarity':
                return self.create_similarity_tab()
            elif active_tab == 'topics':
                return self.create_topics_tab()
            else:
                return html.Div("Select a tab to view content")
        
        @self.app.callback(
            [Output('analytics-chart', 'figure'),
             Output('publication-trends-chart', 'figure'),
             Output('top-journals-chart', 'figure'),
             Output('source-distribution-chart', 'figure')],
            [Input('main-tabs', 'value')]
        )
        def update_analytics_charts(active_tab):
            """Update analytics charts."""
            if active_tab == 'analytics':
                try:
                    stats = self.db_manager.get_statistics()
                    
                    # Analytics overview
                    analytics_fig = go.Figure(data=[
                        go.Bar(x=['Total Articles', 'Read Articles', 'Collections', 'Tags'],
                              y=[stats['total_articles'], stats['read_articles'], 
                                stats['total_collections'], stats['total_tags']],
                              name='Count')
                    ])
                    analytics_fig.update_layout(title="Database Overview")
                    
                    # Publication trends
                    if stats['articles_by_year']:
                        years = list(stats['articles_by_year'].keys())
                        counts = list(stats['articles_by_year'].values())
                        trends_fig = go.Figure(data=[
                            go.Scatter(x=years, y=counts, mode='lines+markers', name='Publications')
                        ])
                        trends_fig.update_layout(title="Publication Trends by Year")
                    else:
                        trends_fig = go.Figure()
                        trends_fig.update_layout(title="Publication Trends by Year")
                    
                    # Top journals
                    if stats['top_journals']:
                        journals = list(stats['top_journals'].keys())
                        counts = list(stats['top_journals'].values())
                        journals_fig = go.Figure(data=[
                            go.Bar(x=journals, y=counts, name='Articles')
                        ])
                        journals_fig.update_layout(title="Top Journals", xaxis_tickangle=-45)
                    else:
                        journals_fig = go.Figure()
                        journals_fig.update_layout(title="Top Journals")
                    
                    # Source distribution
                    if stats['articles_by_source']:
                        sources = list(stats['articles_by_source'].keys())
                        counts = list(stats['articles_by_source'].values())
                        source_fig = px.pie(values=counts, names=sources, title="Articles by Source")
                    else:
                        source_fig = go.Figure()
                        source_fig.update_layout(title="Articles by Source")
                    
                    return analytics_fig, trends_fig, journals_fig, source_fig
                    
                except Exception as e:
                    logger.error(f"Error updating analytics: {e}")
                    empty_fig = go.Figure()
                    return empty_fig, empty_fig, empty_fig, empty_fig
            
            return go.Figure(), go.Figure(), go.Figure(), go.Figure()
        
        @self.app.callback(
            Output('similarity-results', 'children'),
            [Input('find-similar-btn', 'n_clicks')],
            [State('similarity-article-selector', 'value')]
        )
        def find_similar_articles(n_clicks, article_id):
            """Find similar articles."""
            if n_clicks and article_id:
                try:
                    similar_articles = self.db_manager.get_article_similarity(int(article_id), limit=10)
                    
                    if similar_articles:
                        results = []
                        for similar_id, similarity_score in similar_articles:
                            article = self.db_manager.get_article(similar_id)
                            if article:
                                results.append({
                                    'article': article,
                                    'similarity': similarity_score
                                })
                        
                        return self.create_similarity_display(results)
                    else:
                        return html.Div("No similar articles found", className="text-muted")
                        
                except Exception as e:
                    logger.error(f"Error finding similar articles: {e}")
                    return html.Div(f"Error: {str(e)}", className="alert alert-danger")
            
            return html.Div("Select an article and click 'Find Similar Articles'", className="text-muted")
        
        @self.app.callback(
            Output('topic-modeling-results', 'children'),
            [Input('run-topic-modeling', 'n_clicks')],
            [State('n-topics', 'value')]
        )
        def run_topic_modeling(n_clicks, n_topics):
            """Run topic modeling analysis."""
            if n_clicks:
                try:
                    results = self.db_manager.get_topic_modeling(n_topics)
                    
                    if results:
                        return self.create_topic_modeling_display(results)
                    else:
                        return html.Div("No articles available for topic modeling", className="text-muted")
                        
                except Exception as e:
                    logger.error(f"Error in topic modeling: {e}")
                    return html.Div(f"Error: {str(e)}", className="alert alert-danger")
            
            return html.Div("Click 'Run Topic Modeling' to analyze article topics", className="text-muted")
    
    def create_articles_display(self, articles: List[ArticleMetadata]) -> html.Div:
        """Create display for articles list."""
        if not articles:
            return html.Div("No articles found", className="text-muted")
        
        article_cards = []
        for article in articles:
            card = self.create_article_card(article)
            article_cards.append(card)
        
        return html.Div(article_cards)
    
    def create_article_card(self, article: ArticleMetadata) -> html.Div:
        """Create a card for displaying article information."""
        # Create rating stars
        rating_stars = ""
        if article.rating:
            for i in range(1, 6):
                if i <= article.rating:
                    rating_stars += "★"
                else:
                    rating_stars += "☆"
        
        # Create tags display
        tags_display = ""
        if article.tags:
            for tag in article.tags[:3]:  # Show first 3 tags
                tags_display += html.Span(tag, className="badge bg-secondary me-1")
        
        return html.Div([
            html.Div([
                html.Div([
                    html.H5(article.title, className="card-title"),
                    html.P(f"Authors: {', '.join(article.authors[:3])}{'...' if len(article.authors) > 3 else ''}", 
                          className="card-text"),
                    html.P(f"Journal: {article.journal or 'N/A'}", className="card-text"),
                    html.P(f"Source: {article.source or 'N/A'}", className="card-text"),
                    html.P(article.abstract[:200] + "..." if len(article.abstract) > 200 else article.abstract, 
                          className="card-text"),
                    html.Div([
                        html.Span(f"Rating: {rating_stars}", className="badge bg-warning me-2"),
                        html.Span(f"Status: {article.read_status}", className="badge bg-info me-2"),
                        html.Span(f"Citations: {article.citations or 'N/A'}", className="badge bg-primary me-2"),
                        tags_display
                    ], className="mt-2"),
                    html.Div([
                        html.Button("View Details", className="btn btn-sm btn-outline-primary me-2",
                                  id={"type": "view-article", "index": article.id}),
                        html.Button("Edit", className="btn btn-sm btn-outline-secondary me-2",
                                  id={"type": "edit-article", "index": article.id}),
                        html.Button("Delete", className="btn btn-sm btn-outline-danger",
                                  id={"type": "delete-article", "index": article.id})
                    ], className="mt-3")
                ], className="card-body")
            ], className="card mb-3")
        ])
    
    def create_similarity_display(self, results: List[Dict[str, Any]]) -> html.Div:
        """Create display for similarity results."""
        cards = []
        for result in results:
            article = result['article']
            similarity = result['similarity']
            
            card = html.Div([
                html.Div([
                    html.H6(article.title, className="card-title"),
                    html.P(f"Similarity: {similarity:.3f}", className="card-text"),
                    html.P(f"Journal: {article.journal or 'N/A'}", className="card-text"),
                    html.P(article.abstract[:150] + "..." if len(article.abstract) > 150 else article.abstract,
                          className="card-text")
                ], className="card-body")
            ], className="card mb-2")
            cards.append(card)
        
        return html.Div(cards)
    
    def create_topic_modeling_display(self, results: Dict[str, Any]) -> html.Div:
        """Create display for topic modeling results."""
        topics = results.get('topics', [])
        
        topic_cards = []
        for topic in topics:
            words = topic['words'][:10]  # Show top 10 words
            weights = topic['weights'][:10]
            
            # Create word cloud-like display
            word_elements = []
            for word, weight in zip(words, weights):
                size = max(12, int(weight * 20))  # Scale font size
                word_elements.append(
                    html.Span(word, style={'font-size': f'{size}px', 'margin-right': '5px'})
                )
            
            card = html.Div([
                html.Div([
                    html.H6(f"Topic {topic['topic_id'] + 1}", className="card-title"),
                    html.Div(word_elements, className="card-text")
                ], className="card-body")
            ], className="card mb-2")
            topic_cards.append(card)
        
        return html.Div([
            html.H5("Identified Topics"),
            html.Div(topic_cards)
        ])


def create_manager_dashboard(app: dash.Dash, db_path: str = "article_manager.db") -> ManagerDashboard:
    """
    Create and configure an article manager dashboard.
    
    Args:
        app: Dash application instance
        db_path: Path to SQLite database file
        
    Returns:
        Configured ManagerDashboard instance
    """
    dashboard = ManagerDashboard(app, db_path)
    return dashboard


def main():
    """Main function for testing the dashboard."""
    app = dash.Dash(__name__)
    dashboard = create_manager_dashboard(app)
    app.layout = dashboard.create_layout()
    
    if __name__ == "__main__":
        app.run_server(debug=True)


if __name__ == "__main__":
    main()
