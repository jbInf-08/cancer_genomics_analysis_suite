"""
Article Scraper Dashboard Module

This module provides a comprehensive Dash-based dashboard for article scraping,
management, and analysis.
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

from .scraper import ArticleScraper, Article, create_mock_articles

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScraperDashboard:
    """
    A comprehensive dashboard for article scraping and management.
    """
    
    def __init__(self, app: dash.Dash):
        """
        Initialize the scraper dashboard.
        
        Args:
            app: Dash application instance
        """
        self.app = app
        self.scraper = ArticleScraper()
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
                html.H1("Article Scraper Dashboard", 
                       className="text-center mb-4"),
                html.P("Comprehensive article scraping and management for cancer genomics research",
                      className="text-center text-muted mb-4")
            ], className="container-fluid"),
            
            # Control Panel
            html.Div([
                html.Div([
                    html.H4("Scraping Configuration", className="card-title"),
                    
                    # Source selection
                    html.Div([
                        html.Label("Select Source:"),
                        dcc.Dropdown(
                            id='scraping-source',
                            options=[
                                {'label': 'PubMed', 'value': 'pubmed'},
                                {'label': 'arXiv', 'value': 'arxiv'},
                                {'label': 'Google Scholar', 'value': 'google_scholar'},
                                {'label': 'RSS Feeds', 'value': 'rss'}
                            ],
                            value='pubmed',
                            className="mb-2"
                        )
                    ], className="mb-3"),
                    
                    # Search query
                    html.Div([
                        html.Label("Search Query:"),
                        dcc.Input(
                            id='search-query',
                            type='text',
                            placeholder='e.g., "cancer genomics machine learning"',
                            className="form-control mb-2"
                        )
                    ], className="mb-3"),
                    
                    # Advanced options
                    html.Div([
                        html.Label("Max Results:"),
                        dcc.Slider(
                            id='max-results',
                            min=10,
                            max=500,
                            step=10,
                            value=100,
                            marks={i: str(i) for i in range(10, 501, 50)},
                            tooltip={"placement": "bottom", "always_visible": True}
                        )
                    ], className="mb-3"),
                    
                    # Date range for PubMed
                    html.Div([
                        html.Label("Date Range (PubMed only):"),
                        dcc.DatePickerRange(
                            id='date-range',
                            start_date=datetime.now() - timedelta(days=365),
                            end_date=datetime.now(),
                            display_format='YYYY-MM-DD'
                        )
                    ], className="mb-3", id='date-range-container', style={'display': 'none'}),
                    
                    # RSS feed URLs
                    html.Div([
                        html.Label("RSS Feed URLs (one per line):"),
                        dcc.Textarea(
                            id='rss-feeds',
                            placeholder='https://example.com/feed1.xml\nhttps://example.com/feed2.xml',
                            style={'width': '100%', 'height': '100px'},
                            className="mb-2"
                        )
                    ], className="mb-3", id='rss-feeds-container', style={'display': 'none'}),
                    
                    # Action buttons
                    html.Div([
                        html.Button('Load Mock Data', id='load-mock-data', 
                                  className='btn btn-primary me-2'),
                        html.Button('Start Scraping', id='start-scraping', 
                                  className='btn btn-success me-2'),
                        html.Button('Load from Database', id='load-database', 
                                  className='btn btn-info me-2'),
                        html.Button('Export Articles', id='export-articles', 
                                  className='btn btn-warning me-2'),
                        html.Button('Clear Database', id='clear-database', 
                                  className='btn btn-danger')
                    ], className="d-flex flex-wrap gap-2")
                    
                ], className="card-body")
            ], className="card mb-4"),
            
            # Main content area
            html.Div([
                # Tabs for different views
                dcc.Tabs(id="main-tabs", value="articles", children=[
                    dcc.Tab(label="Articles", value="articles"),
                    dcc.Tab(label="Search & Filter", value="search"),
                    dcc.Tab(label="Statistics", value="statistics"),
                    dcc.Tab(label="Scraping Log", value="logs"),
                    dcc.Tab(label="Export", value="export")
                ]),
                
                # Tab content
                html.Div(id="scraper-tab-content", className="mt-3")
                
            ], className="container-fluid"),
            
            # Hidden divs for storing data
            html.Div(id='scraped-articles', style={'display': 'none'}),
            html.Div(id='scraping-progress', style={'display': 'none'}),
            
            # Download components
            dcc.Download(id="download-articles"),
            dcc.Download(id="download-export")
        ])
    
    def create_articles_tab(self) -> html.Div:
        """Create the articles tab content."""
        return html.Div([
            html.Div([
                html.H4("Scraped Articles"),
                html.Div([
                    html.Label("Filter by Source:"),
                    dcc.Dropdown(
                        id="filter-source",
                        options=[
                            {'label': 'All Sources', 'value': 'all'},
                            {'label': 'PubMed', 'value': 'pubmed'},
                            {'label': 'arXiv', 'value': 'arxiv'},
                            {'label': 'Google Scholar', 'value': 'google_scholar'},
                            {'label': 'RSS', 'value': 'rss'}
                        ],
                        value='all',
                        className="mb-2"
                    )
                ], className="mb-3"),
                html.Div(id="articles-list")
            ], className="card")
        ])
    
    def create_search_tab(self) -> html.Div:
        """Create the search and filter tab content."""
        return html.Div([
            html.Div([
                html.H4("Search Articles"),
                html.Div([
                    html.Label("Search Query:"),
                    dcc.Input(
                        id="search-input",
                        type="text",
                        placeholder="Search in title, abstract, authors...",
                        className="form-control mb-2"
                    ),
                    html.Label("Search Fields:"),
                    dcc.Checklist(
                        id="search-fields",
                        options=[
                            {'label': 'Title', 'value': 'title'},
                            {'label': 'Abstract', 'value': 'abstract'},
                            {'label': 'Authors', 'value': 'authors'},
                            {'label': 'Keywords', 'value': 'keywords'}
                        ],
                        value=['title', 'abstract'],
                        className="mb-2"
                    ),
                    html.Button("Search", id="search-button", 
                              className="btn btn-primary mb-3")
                ], className="mb-3"),
                html.Div(id="scraper-search-results")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Advanced Filters"),
                html.Div([
                    html.Label("Publication Date Range:"),
                    dcc.DatePickerRange(
                        id="filter-date-range",
                        start_date=datetime.now() - timedelta(days=365),
                        end_date=datetime.now(),
                        display_format='YYYY-MM-DD'
                    ),
                    html.Label("Journal:"),
                    dcc.Dropdown(
                        id="filter-journal",
                        placeholder="Select journal...",
                        className="mb-2"
                    ),
                    html.Label("Min Citations:"),
                    dcc.Slider(
                        id='min-citations',
                        min=0,
                        max=100,
                        step=1,
                        value=0,
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], className="mb-3"),
                html.Button("Apply Filters", id="apply-filters", 
                          className="btn btn-secondary")
            ], className="card")
        ])
    
    def create_statistics_tab(self) -> html.Div:
        """Create the statistics tab content."""
        return html.Div([
            html.Div([
                html.H4("Scraping Statistics"),
                dcc.Graph(id="scraping-stats-chart")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Articles by Source"),
                dcc.Graph(id="articles-by-source-chart")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Publication Trends"),
                dcc.Graph(id="publication-trends-chart")
            ], className="card mb-4"),
            
            html.Div([
                html.H4("Top Journals"),
                dcc.Graph(id="top-journals-chart")
            ], className="card")
        ])
    
    def create_logs_tab(self) -> html.Div:
        """Create the scraping logs tab content."""
        return html.Div([
            html.Div([
                html.H4("Scraping Activity Log"),
                html.Div([
                    html.Label("Filter by Source:"),
                    dcc.Dropdown(
                        id="log-filter-source",
                        options=[
                            {'label': 'All Sources', 'value': 'all'},
                            {'label': 'PubMed', 'value': 'pubmed'},
                            {'label': 'arXiv', 'value': 'arxiv'},
                            {'label': 'Google Scholar', 'value': 'google_scholar'},
                            {'label': 'RSS', 'value': 'rss'}
                        ],
                        value='all',
                        className="mb-2"
                    ),
                    html.Label("Filter by Status:"),
                    dcc.Dropdown(
                        id="log-filter-status",
                        options=[
                            {'label': 'All Status', 'value': 'all'},
                            {'label': 'Success', 'value': 'success'},
                            {'label': 'Error', 'value': 'error'}
                        ],
                        value='all',
                        className="mb-2"
                    )
                ], className="mb-3"),
                html.Div(id="scraping-logs")
            ], className="card")
        ])
    
    def create_export_tab(self) -> html.Div:
        """Create the export tab content."""
        return html.Div([
            html.Div([
                html.H4("Export Articles"),
                html.Div([
                    html.Label("Export Format:"),
                    dcc.Dropdown(
                        id="export-format",
                        options=[
                            {'label': 'CSV', 'value': 'csv'},
                            {'label': 'JSON', 'value': 'json'},
                            {'label': 'Excel', 'value': 'excel'}
                        ],
                        value='csv',
                        className="mb-2"
                    ),
                    html.Label("Filter by Source:"),
                    dcc.Dropdown(
                        id="export-filter-source",
                        options=[
                            {'label': 'All Sources', 'value': 'all'},
                            {'label': 'PubMed', 'value': 'pubmed'},
                            {'label': 'arXiv', 'value': 'arxiv'},
                            {'label': 'Google Scholar', 'value': 'google_scholar'},
                            {'label': 'RSS', 'value': 'rss'}
                        ],
                        value='all',
                        className="mb-2"
                    ),
                    html.Label("Date Range:"),
                    dcc.DatePickerRange(
                        id="export-date-range",
                        start_date=datetime.now() - timedelta(days=30),
                        end_date=datetime.now(),
                        display_format='YYYY-MM-DD'
                    )
                ], className="mb-3"),
                html.Button("Export Articles", id="export-button", 
                          className="btn btn-primary"),
                html.Div(id="export-status", className="mt-3")
            ], className="card")
        ])
    
    def setup_callbacks(self):
        """Set up all dashboard callbacks."""
        
        @self.app.callback(
            Output('date-range-container', 'style'),
            [Input('scraping-source', 'value')]
        )
        def toggle_date_range(source):
            """Show/hide date range for PubMed."""
            if source == 'pubmed':
                return {'display': 'block'}
            else:
                return {'display': 'none'}
        
        @self.app.callback(
            Output('rss-feeds-container', 'style'),
            [Input('scraping-source', 'value')]
        )
        def toggle_rss_feeds(source):
            """Show/hide RSS feeds input for RSS source."""
            if source == 'rss':
                return {'display': 'block'}
            else:
                return {'display': 'none'}
        
        @self.app.callback(
            [Output('scraped-articles', 'children'),
             Output('scraping-progress', 'children')],
            [Input('start-scraping', 'n_clicks')],
            [State('scraping-source', 'value'),
             State('search-query', 'value'),
             State('max-results', 'value'),
             State('date-range', 'start_date'),
             State('date-range', 'end_date'),
             State('rss-feeds', 'value')]
        )
        def start_scraping(n_clicks, source, query, max_results, start_date, end_date, rss_feeds):
            """Start article scraping based on selected source."""
            if n_clicks and query:
                try:
                    articles = []
                    
                    if source == 'pubmed':
                        date_range = None
                        if start_date and end_date:
                            date_range = (start_date, end_date)
                        articles = self.scraper.scrape_pubmed(
                            query=query,
                            max_results=max_results,
                            date_range=date_range
                        )
                    
                    elif source == 'arxiv':
                        articles = self.scraper.scrape_arxiv(
                            query=query,
                            max_results=max_results
                        )
                    
                    elif source == 'google_scholar':
                        articles = self.scraper.scrape_google_scholar(
                            query=query,
                            max_results=max_results
                        )
                    
                    elif source == 'rss' and rss_feeds:
                        feed_urls = [url.strip() for url in rss_feeds.split('\n') if url.strip()]
                        articles = self.scraper.scrape_rss_feeds(
                            feed_urls=feed_urls,
                            max_articles_per_feed=max_results // len(feed_urls) if feed_urls else max_results
                        )
                    
                    # Save articles to database
                    if articles:
                        saved_count = self.scraper.save_articles_to_db(articles)
                        progress_msg = f"Scraped {len(articles)} articles, saved {saved_count} to database"
                    else:
                        progress_msg = "No articles found"
                    
                    # Store articles data
                    articles_json = json.dumps([article.to_dict() for article in articles])
                    
                    return articles_json, html.Div(progress_msg, className="alert alert-success")
                    
                except Exception as e:
                    logger.error(f"Error in scraping: {e}")
                    return "", html.Div(f"Error: {str(e)}", className="alert alert-danger")
            
            return "", html.Div("Click 'Start Scraping' to begin", className="text-muted")
        
        @self.app.callback(
            [Output('scraped-articles', 'children', allow_duplicate=True),
             Output('scraping-progress', 'children', allow_duplicate=True)],
            [Input('load-mock-data', 'n_clicks')],
            prevent_initial_call=True
        )
        def load_mock_data(n_clicks):
            """Load mock articles for demonstration."""
            if n_clicks:
                try:
                    mock_articles = create_mock_articles()
                    saved_count = self.scraper.save_articles_to_db(mock_articles)
                    
                    articles_json = json.dumps([article.to_dict() for article in mock_articles])
                    progress_msg = f"Loaded {len(mock_articles)} mock articles, saved {saved_count} to database"
                    
                    return articles_json, html.Div(progress_msg, className="alert alert-info")
                    
                except Exception as e:
                    logger.error(f"Error loading mock data: {e}")
                    return "", html.Div(f"Error: {str(e)}", className="alert alert-danger")
            
            return "", html.Div("Click 'Load Mock Data' to begin", className="text-muted")
        
        @self.app.callback(
            Output('scraper-tab-content', 'children'),
            [Input('main-tabs', 'value')]
        )
        def render_tab_content(active_tab):
            """Render content based on active tab."""
            if active_tab == 'articles':
                return self.create_articles_tab()
            elif active_tab == 'search':
                return self.create_search_tab()
            elif active_tab == 'statistics':
                return self.create_statistics_tab()
            elif active_tab == 'logs':
                return self.create_logs_tab()
            elif active_tab == 'export':
                return self.create_export_tab()
            else:
                return html.Div("Select a tab to view content")
        
        @self.app.callback(
            Output('articles-list', 'children'),
            [Input('scraped-articles', 'children'),
             Input('filter-source', 'value')]
        )
        def update_articles_list(articles_json, filter_source):
            """Update the articles list display."""
            if articles_json:
                try:
                    articles_data = json.loads(articles_json)
                    
                    # Filter by source if specified
                    if filter_source != 'all':
                        articles_data = [article for article in articles_data 
                                       if article.get('source') == filter_source]
                    
                    # Create article cards
                    article_cards = []
                    for article in articles_data:
                        card = self.create_article_card(article)
                        article_cards.append(card)
                    
                    return article_cards
                    
                except Exception as e:
                    logger.error(f"Error updating articles list: {e}")
                    return html.Div(f"Error: {str(e)}", className="alert alert-danger")
            
            return html.Div("No articles loaded. Start scraping to see articles here.", 
                          className="text-muted")
        
        @self.app.callback(
            [Output('scraping-stats-chart', 'figure'),
             Output('articles-by-source-chart', 'figure'),
             Output('publication-trends-chart', 'figure'),
             Output('top-journals-chart', 'figure')],
            [Input('main-tabs', 'value')]
        )
        def update_statistics_charts(active_tab):
            """Update statistics charts."""
            if active_tab == 'statistics':
                try:
                    # Get statistics
                    stats = self.scraper.get_scraping_stats()
                    
                    # Scraping stats chart
                    stats_fig = go.Figure(data=[
                        go.Bar(x=list(stats['scraping_stats']['sources'].keys()),
                              y=list(stats['scraping_stats']['sources'].values()),
                              name='Articles by Source')
                    ])
                    stats_fig.update_layout(title="Articles Scraped by Source")
                    
                    # Articles by source pie chart
                    source_fig = px.pie(
                        values=list(stats['articles_by_source'].values()),
                        names=list(stats['articles_by_source'].keys()),
                        title="Articles by Source"
                    )
                    
                    # Publication trends (placeholder)
                    trends_fig = go.Figure()
                    trends_fig.update_layout(title="Publication Trends Over Time")
                    
                    # Top journals (placeholder)
                    journals_fig = go.Figure()
                    journals_fig.update_layout(title="Top Journals")
                    
                    return stats_fig, source_fig, trends_fig, journals_fig
                    
                except Exception as e:
                    logger.error(f"Error updating statistics: {e}")
                    empty_fig = go.Figure()
                    return empty_fig, empty_fig, empty_fig, empty_fig
            
            return go.Figure(), go.Figure(), go.Figure(), go.Figure()
    
    def create_article_card(self, article_data: Dict[str, Any]) -> html.Div:
        """Create a card for displaying article information."""
        return html.Div([
            html.Div([
                html.H5(article_data.get('title', 'No title'), className="card-title"),
                html.P(f"Authors: {', '.join(article_data.get('authors', []))}", 
                      className="card-text"),
                html.P(f"Journal: {article_data.get('journal', 'N/A')}", 
                      className="card-text"),
                html.P(f"Source: {article_data.get('source', 'N/A')}", 
                      className="card-text"),
                html.P(f"DOI: {article_data.get('doi', 'N/A')}", 
                      className="card-text"),
                html.P(article_data.get('abstract', 'No abstract available')[:200] + "...", 
                      className="card-text"),
                html.Div([
                    html.Span(f"Citations: {article_data.get('citations', 'N/A')}", 
                            className="badge bg-primary me-2"),
                    html.Span(f"Date: {article_data.get('publication_date', 'N/A')}", 
                            className="badge bg-secondary")
                ], className="mt-2")
            ], className="card-body")
        ], className="card mb-3")


def create_scraper_dashboard(app: dash.Dash) -> ScraperDashboard:
    """
    Create and configure an article scraper dashboard.
    
    Args:
        app: Dash application instance
        
    Returns:
        Configured ScraperDashboard instance
    """
    dashboard = ScraperDashboard(app)
    return dashboard


def main():
    """Main function for testing the dashboard."""
    app = dash.Dash(__name__)
    dashboard = create_scraper_dashboard(app)
    app.layout = dashboard.create_layout()
    
    if __name__ == "__main__":
        app.run_server(debug=True)


if __name__ == "__main__":
    main()
