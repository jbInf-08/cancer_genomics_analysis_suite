"""
Genome Browser Dash Dashboard

This module provides a Dash-based web interface for the genome browser,
allowing users to interactively browse genomic data, visualize features,
and navigate through genomic regions.
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import json
from typing import Dict, List, Any, Optional
import logging

from .browser import GenomeBrowser, GenomicRegion, GenomicFeature, create_sample_genome_browser
from CancerGenomicsSuite.modules.gene_annotation.gene_location_predictor import (
    GeneLocationPredictor,
)
from CancerGenomicsSuite.modules.gene_annotation.dash_error_display import (
    structured_error_to_dash,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GenomeBrowserDashboard:
    """
    Dash dashboard for genome browser functionality.
    """
    
    def __init__(self, app_name: str = "Genome Browser"):
        """
        Initialize the genome browser dashboard.
        
        Args:
            app_name: Name of the Dash app
        """
        self.app = dash.Dash(__name__)
        self.app.title = app_name
        self.browser = create_sample_genome_browser()
        self._gene_loc = GeneLocationPredictor()
        self._ensembl_banner: Optional[Any] = None
        self.setup_layout()
        self.setup_callbacks()
    
    def setup_layout(self):
        """Set up the dashboard layout."""
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1("Genome Browser", className="header-title"),
                html.P("Interactive genomic data visualization and navigation", className="header-subtitle")
            ], className="header"),
            
            # Control Panel
            html.Div([
                html.Div([
                    html.Label("Reference Genome:"),
                    dcc.Dropdown(
                        id="reference-genome-dropdown",
                        options=[
                            {"label": "Human (GRCh38)", "value": "hg38"},
                            {"label": "Human (GRCh37)", "value": "hg19"},
                            {"label": "Mouse (GRCm38)", "value": "mm10"},
                            {"label": "Mouse (NCBIM37)", "value": "mm9"},
                            {"label": "Drosophila (BDGP6)", "value": "dm6"},
                            {"label": "C. elegans (WBcel235)", "value": "ce11"}
                        ],
                        value="hg38",
                        clearable=False
                    )
                ], className="control-item"),
                
                html.Div([
                    html.Label("Chromosome:"),
                    dcc.Input(
                        id="chromosome-input",
                        type="text",
                        value="chr17",
                        placeholder="e.g., chr1, chrX, chrM"
                    )
                ], className="control-item"),
                
                html.Div([
                    html.Label("Start Position:"),
                    dcc.Input(
                        id="start-input",
                        type="number",
                        value=43000000,
                        min=0
                    )
                ], className="control-item"),
                
                html.Div([
                    html.Label("End Position:"),
                    dcc.Input(
                        id="end-input",
                        type="number",
                        value=43100000,
                        min=0
                    )
                ], className="control-item"),
                
                html.Div([
                    html.Label("Region Name (optional):"),
                    dcc.Input(
                        id="region-name-input",
                        type="text",
                        placeholder="e.g., BRCA1 region"
                    )
                ], className="control-item"),
                
                html.Button("Set Region", id="set-region-button", className="control-button"),
                html.Button("Reset to Sample", id="reset-button", className="control-button"),
                html.Button(
                    "Fetch overlapping genes (Ensembl)",
                    id="ensembl-annotate-button",
                    className="control-button",
                    title=(
                        "Uses overlap/region for the current interval. hg19 queries GRCh37 Ensembl host. "
                        "Errors (rate limits, bad coordinates) appear in the banner below."
                    ),
                ),
            ], className="control-panel"),
            html.Div(id="ensembl-annotate-banner", className="region-display"),
            
            # Navigation Controls
            html.Div([
                html.Button("← Pan Left", id="pan-left-button", className="nav-button"),
                html.Button("Zoom Out", id="zoom-out-button", className="nav-button"),
                html.Button("Zoom In", id="zoom-in-button", className="nav-button"),
                html.Button("Pan Right →", id="pan-right-button", className="nav-button"),
                html.Div([
                    html.Label("Pan Distance:"),
                    dcc.Input(
                        id="pan-distance-input",
                        type="number",
                        value=10000,
                        min=1,
                        style={"width": "100px"}
                    )
                ], className="nav-control")
            ], className="navigation-panel"),
            
            # Current Region Display
            html.Div([
                html.H3("Current Region"),
                html.Div(id="current-region-display", className="region-display")
            ], className="region-panel"),
            
            # Main Visualization Area
            html.Div([
                dcc.Graph(
                    id="genome-browser-plot",
                    config={
                        'displayModeBar': True,
                        'displaylogo': False,
                        'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d']
                    }
                )
            ], className="visualization-area"),
            
            # Feature Search
            html.Div([
                html.H3("Feature Search"),
                html.Div([
                    dcc.Input(
                        id="search-input",
                        type="text",
                        placeholder="Search features by name or description...",
                        style={"width": "300px"}
                    ),
                    html.Button("Search", id="search-button", className="search-button")
                ], className="search-controls"),
                html.Div(id="genome-search-results", className="search-results")
            ], className="search-panel"),
            
            # Feature Table
            html.Div([
                html.H3("Features in Current Region"),
                html.Div(id="feature-table-container")
            ], className="feature-panel"),
            
            # Export Controls
            html.Div([
                html.H3("Export Data"),
                html.Div([
                    html.Label("Format:"),
                    dcc.Dropdown(
                        id="export-format-dropdown",
                        options=[
                            {"label": "JSON", "value": "json"},
                            {"label": "BED", "value": "bed"},
                            {"label": "GFF3", "value": "gff3"}
                        ],
                        value="json",
                        clearable=False,
                        style={"width": "150px"}
                    ),
                    html.Button("Export", id="export-button", className="export-button")
                ], className="export-controls"),
                html.Div(id="export-output", className="export-output")
            ], className="export-panel"),
            
            # Statistics Panel
            html.Div([
                html.H3("Browser Statistics"),
                html.Div(id="statistics-display", className="statistics-display")
            ], className="statistics-panel"),
            
            # Hidden div to store browser state
            html.Div(id="browser-state", style={"display": "none"})
        ], className="main-container")
    
    def setup_callbacks(self):
        """Set up Dash callbacks for interactivity."""
        
        @self.app.callback(
            [Output("browser-state", "children"),
             Output("current-region-display", "children"),
             Output("genome-browser-plot", "figure"),
             Output("feature-table-container", "children"),
             Output("statistics-display", "children"),
             Output("ensembl-annotate-banner", "children")],
            [Input("set-region-button", "n_clicks"),
             Input("reset-button", "n_clicks"),
             Input("ensembl-annotate-button", "n_clicks"),
             Input("pan-left-button", "n_clicks"),
             Input("pan-right-button", "n_clicks"),
             Input("zoom-in-button", "n_clicks"),
             Input("zoom-out-button", "n_clicks")],
            [State("reference-genome-dropdown", "value"),
             State("chromosome-input", "value"),
             State("start-input", "value"),
             State("end-input", "value"),
             State("region-name-input", "value"),
             State("pan-distance-input", "value"),
             State("browser-state", "children")]
        )
        def update_browser(region_clicks, reset_clicks, ensembl_clicks, pan_left_clicks, pan_right_clicks,
                          zoom_in_clicks, zoom_out_clicks, ref_genome, chromosome, start, end,
                          region_name, pan_distance, browser_state):
            """Update browser state and visualizations."""
            
            ctx = callback_context
            self._ensembl_banner = None
            if not ctx.triggered:
                # Initial load
                self.browser = create_sample_genome_browser()
            else:
                button_id = ctx.triggered[0]["prop_id"].split(".")[0]
                if ref_genome:
                    self.browser.reference_genome = ref_genome

                if button_id == "set-region-button" and region_clicks:
                    # Set new region
                    try:
                        self.browser.set_region(
                            chromosome=chromosome,
                            start=start,
                            end=end,
                            name=region_name if region_name else None
                        )
                    except ValueError as e:
                        logger.error(f"Invalid region: {e}")
                
                elif button_id == "reset-button" and reset_clicks:
                    # Reset to sample data
                    self.browser = create_sample_genome_browser()
                    if ref_genome:
                        self.browser.reference_genome = ref_genome

                elif button_id == "ensembl-annotate-button" and ensembl_clicks:
                    try:
                        if self.browser.current_region is None and chromosome is not None:
                            self.browser.set_region(
                                chromosome=chromosome,
                                start=int(start),
                                end=int(end),
                                name=region_name if region_name else None,
                            )
                        region = self.browser.current_region
                        if region is None:
                            logger.warning("No region for Ensembl annotation")
                        else:
                            self.browser.remove_features_by_attribute("source", "ensembl_overlap")
                            ref_asm = ref_genome or self.browser.reference_genome
                            genes = self._gene_loc.predict_genes_in_region(
                                region.chromosome,
                                region.start,
                                region.end,
                                reference_genome=ref_asm,
                            )
                            if genes and (
                                genes[0].get("error_kind") or genes[0].get("user_message")
                            ):
                                self._ensembl_banner = structured_error_to_dash(genes[0])
                            for row in genes:
                                if row.get("error_kind") or row.get("user_message"):
                                    continue
                                sym = row.get("symbol") or row.get("gene_id") or "gene"
                                gs = row.get("start")
                                ge = row.get("end")
                                if gs is None or ge is None:
                                    continue
                                st = row.get("strand")
                                strand = "+" if st == 1 else ("-" if st == -1 else "+")
                                feat = GenomicFeature(
                                    region=GenomicRegion(
                                        chromosome=region.chromosome,
                                        start=int(gs) - 1,
                                        end=int(ge),
                                        strand=strand,
                                        name=sym,
                                        description=row.get("description") or row.get("biotype"),
                                    ),
                                    feature_type="gene",
                                    attributes={
                                        "source": "ensembl_overlap",
                                        "gene_id": row.get("gene_id"),
                                        "biotype": row.get("biotype"),
                                    },
                                )
                                self.browser.add_feature(feat)
                    except Exception as e:
                        logger.error("Ensembl annotation failed: %s", e)

                elif button_id == "pan-left-button" and pan_left_clicks:
                    self.browser.pan_left(pan_distance)
                
                elif button_id == "pan-right-button" and pan_right_clicks:
                    self.browser.pan_right(pan_distance)
                
                elif button_id == "zoom-in-button" and zoom_in_clicks:
                    self.browser.zoom_in()
                
                elif button_id == "zoom-out-button" and zoom_out_clicks:
                    self.browser.zoom_out()
            
            # Update visualizations
            region_display = self._create_region_display()
            plot_figure = self._create_genome_plot()
            feature_table = self._create_feature_table()
            statistics = self._create_statistics_display()
            
            # Store browser state
            browser_state_json = json.dumps({
                "reference_genome": self.browser.reference_genome,
                "current_region": {
                    "chromosome": self.browser.current_region.chromosome if self.browser.current_region else None,
                    "start": self.browser.current_region.start if self.browser.current_region else None,
                    "end": self.browser.current_region.end if self.browser.current_region else None,
                    "name": self.browser.current_region.name if self.browser.current_region else None
                } if self.browser.current_region else None
            })
            
            banner = self._ensembl_banner or ""
            return (
                browser_state_json,
                region_display,
                plot_figure,
                feature_table,
                statistics,
                banner,
            )
        
        @self.app.callback(
            Output("genome-search-results", "children"),
            [Input("search-button", "n_clicks")],
            [State("search-input", "value")]
        )
        def search_features(search_clicks, query):
            """Search for features."""
            if not search_clicks or not query:
                return ""
            
            results = self.browser.search_features(query)
            
            if not results:
                return html.P("No features found matching your search.")
            
            result_items = []
            for feature in results[:10]:  # Limit to 10 results
                result_items.append(html.Div([
                    html.Strong(f"{feature.feature_type}: {feature.region.name or 'Unnamed'}"),
                    html.Br(),
                    html.Span(f"{feature.region.chromosome}:{feature.region.start}-{feature.region.end}"),
                    html.Br(),
                    html.Span(f"Description: {feature.region.description or 'No description'}", className="feature-description")
                ], className="search-result-item"))
            
            return html.Div(result_items, className="search-results-list")
        
        @self.app.callback(
            Output("export-output", "children"),
            [Input("export-button", "n_clicks")],
            [State("export-format-dropdown", "value")]
        )
        def export_data(export_clicks, format_type):
            """Export current region data."""
            if not export_clicks:
                return ""
            
            try:
                exported_data = self.browser.export_region_data(format_type)
                
                if format_type == "json":
                    # Pretty print JSON
                    data_dict = json.loads(exported_data)
                    formatted_data = json.dumps(data_dict, indent=2)
                else:
                    formatted_data = exported_data
                
                return html.Div([
                    html.H4(f"Exported Data ({format_type.upper()})"),
                    html.Pre(formatted_data, className="export-data")
                ])
                
            except Exception as e:
                return html.Div([
                    html.H4("Export Error"),
                    html.P(f"Error exporting data: {str(e)}")
                ], className="error-message")
    
    def _create_region_display(self) -> html.Div:
        """Create current region display."""
        if not self.browser.current_region:
            return html.P("No region selected")
        
        region = self.browser.current_region
        region_size = region.end - region.start
        
        return html.Div([
            html.P([
                html.Strong("Chromosome: "), region.chromosome,
                html.Br(),
                html.Strong("Coordinates: "), f"{region.start:,} - {region.end:,}",
                html.Br(),
                html.Strong("Size: "), f"{region_size:,} bp",
                html.Br(),
                html.Strong("Strand: "), region.strand
            ]),
            html.P([
                html.Strong("Name: "), region.name or "Unnamed"
            ]) if region.name else None
        ])
    
    def _create_genome_plot(self) -> go.Figure:
        """Create the main genome browser plot."""
        if not self.browser.current_region:
            return go.Figure().add_annotation(
                text="No region selected",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
        
        region = self.browser.current_region
        features = self.browser.get_features_in_region()
        
        # Create figure
        fig = go.Figure()
        
        # Add features as horizontal bars
        y_positions = {}
        y_counter = 0
        
        for feature in features:
            feature_type = feature.feature_type
            if feature_type not in y_positions:
                y_positions[feature_type] = y_counter
                y_counter += 1
            
            y_pos = y_positions[feature_type]
            
            # Color by feature type
            color_map = {
                "gene": "#1f77b4",
                "exon": "#ff7f0e",
                "intron": "#2ca02c",
                "cds": "#d62728",
                "utr": "#9467bd",
                "promoter": "#8c564b",
                "enhancer": "#e377c2"
            }
            color = color_map.get(feature_type, "#17becf")
            
            fig.add_trace(go.Scatter(
                x=[feature.region.start, feature.region.end],
                y=[y_pos, y_pos],
                mode="lines+markers",
                line=dict(color=color, width=8),
                marker=dict(size=10, color=color),
                name=feature_type,
                text=f"{feature.region.name or 'Unnamed'}<br>{feature.region.chromosome}:{feature.region.start}-{feature.region.end}",
                hovertemplate="<b>%{text}</b><br>Type: " + feature_type + "<extra></extra>",
                showlegend=feature_type not in [trace.name for trace in fig.data]
            ))
        
        # Update layout
        fig.update_layout(
            title=f"Genome Browser: {region.chromosome}:{region.start:,}-{region.end:,}",
            xaxis_title="Genomic Position (bp)",
            yaxis_title="Feature Type",
            height=400,
            showlegend=True,
            hovermode="closest",
            xaxis=dict(
                range=[region.start, region.end],
                tickformat=","
            ),
            yaxis=dict(
                tickmode="array",
                tickvals=list(range(len(y_positions))),
                ticktext=list(y_positions.keys())
            )
        )
        
        return fig
    
    def _create_feature_table(self) -> html.Div:
        """Create feature table for current region."""
        features = self.browser.get_features_in_region()
        
        if not features:
            return html.P("No features in current region")
        
        # Prepare data for table
        table_data = []
        for feature in features:
            table_data.append({
                "Name": feature.region.name or "Unnamed",
                "Type": feature.feature_type,
                "Chromosome": feature.region.chromosome,
                "Start": f"{feature.region.start:,}",
                "End": f"{feature.region.end:,}",
                "Strand": feature.region.strand,
                "Size": f"{feature.region.end - feature.region.start:,} bp",
                "Description": feature.region.description or ""
            })
        
        return dash_table.DataTable(
            data=table_data,
            columns=[{"name": col, "id": col} for col in table_data[0].keys()],
            style_cell={"textAlign": "left", "padding": "10px"},
            style_header={"backgroundColor": "#f0f0f0", "fontWeight": "bold"},
            style_data_conditional=[
                {
                    "if": {"row_index": "odd"},
                    "backgroundColor": "#f9f9f9"
                }
            ],
            page_size=10,
            sort_action="native",
            filter_action="native"
        )
    
    def _create_statistics_display(self) -> html.Div:
        """Create statistics display."""
        stats = self.browser.get_statistics()
        
        return html.Div([
            html.P([
                html.Strong("Reference Genome: "), stats["reference_genome"],
                html.Br(),
                html.Strong("Total Features: "), str(stats["total_features"]),
                html.Br(),
                html.Strong("Total Tracks: "), str(stats["total_tracks"]),
                html.Br(),
                html.Strong("Features in Current Region: "), str(stats["features_in_current_region"])
            ]),
            html.Details([
                html.Summary("Feature Type Breakdown"),
                html.Ul([
                    html.Li(f"{feature_type}: {count}")
                    for feature_type, count in stats["feature_type_counts"].items()
                ])
            ])
        ])
    
    def run(self, debug: bool = True, port: int = 8050):
        """
        Run the dashboard.
        
        Args:
            debug: Enable debug mode
            port: Port to run the app on
        """
        logger.info(f"Starting Genome Browser Dashboard on port {port}")
        self.app.run_server(debug=debug, port=port)


# CSS Styles
external_stylesheets = [
    {
        "href": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
        "rel": "stylesheet"
    }
]

# Add custom CSS
custom_css = """
.main-container {
    fontFamily: 'Inter', sans-serif;
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
}

.header {
    text-align: center;
    margin-bottom: 30px;
    padding: 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 10px;
}

.header-title {
    margin: 0;
    font-size: 2.5em;
    font-weight: 700;
}

.header-subtitle {
    margin: 10px 0 0 0;
    font-size: 1.1em;
    opacity: 0.9;
}

.control-panel {
    display: flex;
    flex-wrap: wrap;
    gap: 15px;
    margin-bottom: 20px;
    padding: 20px;
    background: #f8f9fa;
    border-radius: 8px;
    border: 1px solid #e9ecef;
}

.control-item {
    display: flex;
    flex-direction: column;
    min-width: 150px;
}

.control-item label {
    font-weight: 500;
    margin-bottom: 5px;
    color: #495057;
}

.control-button {
    background: #007bff;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 5px;
    cursor: pointer;
    font-weight: 500;
    transition: background-color 0.2s;
}

.control-button:hover {
    background: #0056b3;
}

.navigation-panel {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 20px;
    padding: 15px;
    background: #e9ecef;
    border-radius: 8px;
}

.nav-button {
    background: #6c757d;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-weight: 500;
}

.nav-button:hover {
    background: #545b62;
}

.nav-control {
    display: flex;
    align-items: center;
    gap: 5px;
    margin-left: auto;
}

.region-panel, .search-panel, .feature-panel, .export-panel, .statistics-panel {
    margin-bottom: 20px;
    padding: 20px;
    background: white;
    border-radius: 8px;
    border: 1px solid #e9ecef;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.region-display {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 5px;
    border-left: 4px solid #007bff;
}

.visualization-area {
    margin-bottom: 20px;
    background: white;
    border-radius: 8px;
    border: 1px solid #e9ecef;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    overflow: hidden;
}

.search-controls {
    display: flex;
    gap: 10px;
    align-items: center;
    margin-bottom: 15px;
}

.search-button {
    background: #28a745;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 5px;
    cursor: pointer;
    font-weight: 500;
}

.search-button:hover {
    background: #1e7e34;
}

.search-results-list {
    max-height: 300px;
    overflow-y: auto;
}

.search-result-item {
    padding: 10px;
    margin-bottom: 10px;
    background: #f8f9fa;
    border-radius: 5px;
    border-left: 3px solid #007bff;
}

.feature-description {
    color: #6c757d;
    font-size: 0.9em;
}

.export-controls {
    display: flex;
    gap: 10px;
    align-items: center;
    margin-bottom: 15px;
}

.export-button {
    background: #17a2b8;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 5px;
    cursor: pointer;
    font-weight: 500;
}

.export-button:hover {
    background: #138496;
}

.export-data {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 5px;
    border: 1px solid #e9ecef;
    max-height: 400px;
    overflow-y: auto;
    fontFamily: 'Courier New', monospace;
    font-size: 0.9em;
}

.statistics-display {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 5px;
}

.error-message {
    color: #dc3545;
    background: #f8d7da;
    padding: 10px;
    border-radius: 5px;
    border: 1px solid #f5c6cb;
}
"""


def create_genome_browser_dashboard() -> GenomeBrowserDashboard:
    """
    Create and return a genome browser dashboard instance.
    
    Returns:
        GenomeBrowserDashboard instance
    """
    return GenomeBrowserDashboard()


if __name__ == "__main__":
    # Create and run the dashboard
    dashboard = create_genome_browser_dashboard()
    
    # Add custom CSS
    dashboard.app.index_string = f"""
    <!DOCTYPE html>
    <html>
        <head>
            {{%metas%}}
            <title>{{%title%}}</title>
            {{%favicon%}}
            {{%css%}}
            <style>{custom_css}</style>
        </head>
        <body>
            {{%app_entry%}}
            <footer>
                {{%config%}}
                {{%scripts%}}
                {{%renderer%}}
            </footer>
        </body>
    </html>
    """
    
    dashboard.run(debug=True, port=8050)
