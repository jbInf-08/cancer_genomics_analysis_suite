"""
R Integration Dashboard

Provides a Dash interface for executing R code, running statistical analyses,
and creating visualizations using R packages.
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import json
import base64
from typing import Dict, List, Any
import logging

from .r_client import RClient

logger = logging.getLogger(__name__)

# Initialize R client
r_client = RClient()

# Dashboard layout
layout = html.Div([
    html.Div([
        html.H2("📊 R Integration", className="section-title"),
        html.P("Execute R code, run statistical analyses, and create visualizations", className="section-description"),
    ], className="section-header"),
    
    # R Code Editor section
    html.Div([
        html.H3("R Code Editor", className="subsection-title"),
        html.Div([
            html.Label("R Code:", className="input-label"),
            dcc.Textarea(
                id="r-code-editor",
                placeholder="# Enter your R code here...\n# Example:\n# library(ggplot2)\n# data <- data.frame(x = 1:10, y = rnorm(10))\n# ggplot(data, aes(x, y)) + geom_point()",
                style={'width': '100%', 'height': '300px', 'fontFamily': 'monospace'},
                className="code-editor"
            ),
        ], className="input-group"),
        html.Div([
            html.Button("Execute R Code", id="execute-r-code", className="button primary"),
            html.Button("Clear", id="clear-r-code", className="button secondary"),
            html.Button("Load Example", id="load-example", className="button secondary"),
        ], className="button-group"),
        html.Div(id="r-execution-status", className="execution-status"),
    ], className="code-editor-section"),
    
    # Package Management section
    html.Div([
        html.H3("Package Management", className="subsection-title"),
        html.Div([
            html.Div([
                html.Label("Install Package:", className="input-label"),
                dcc.Input(
                    id="package-name",
                    type="text",
                    placeholder="e.g., ggplot2, DESeq2",
                    className="input-field"
                ),
            ], className="input-group"),
            html.Div([
                html.Label("Source:", className="input-label"),
                dcc.Dropdown(
                    id="package-source",
                    options=[
                        {'label': 'CRAN', 'value': 'CRAN'},
                        {'label': 'Bioconductor', 'value': 'Bioconductor'},
                        {'label': 'GitHub', 'value': 'GitHub'}
                    ],
                    value='CRAN',
                    className="dropdown"
                ),
            ], className="input-group"),
            html.Button("Install Package", id="install-package", className="button primary"),
        ], className="package-install-section"),
        html.Div([
            html.H4("Installed Packages"),
            html.Div(id="installed-packages", className="packages-list"),
        ], className="packages-section"),
    ], className="package-management-section"),
    
    # Statistical Analysis section
    html.Div([
        html.H3("Statistical Analysis", className="subsection-title"),
        dcc.Tabs(id="analysis-tabs", value="deseq2", children=[
            dcc.Tab(label="DESeq2", value="deseq2"),
            dcc.Tab(label="Limma", value="limma"),
            dcc.Tab(label="GO Enrichment", value="go"),
        ]),
        html.Div(id="r-analysis-content", className="analysis-content"),
    ], className="statistical-analysis-section"),
    
    # Data Upload section
    html.Div([
        html.H3("Data Upload", className="subsection-title"),
        dcc.Upload(
            id="data-upload",
            children=html.Div([
                "Drag and Drop or ",
                html.A("Select Data Files")
            ]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            multiple=True
        ),
        html.Div(id="uploaded-data", className="uploaded-data"),
    ], className="data-upload-section"),
    
    # Results section
    html.Div([
        html.H3("Results", className="subsection-title"),
        html.Div(id="r-results", className="results-container"),
    ], className="results-section"),
    
    # Hidden divs for storing data
    html.Div(id="r-data", style={"display": "none"}),
    html.Div(id="analysis-data", style={"display": "none"}),
])

def register_callbacks(app):
    """Register callbacks for the R dashboard"""
    
    @app.callback(
        [Output("r-execution-status", "children"),
         Output("r-results", "children")],
        [Input("execute-r-code", "n_clicks")],
        [State("r-code-editor", "value")]
    )
    def execute_r_code(n_clicks, r_code):
        if n_clicks is None or not r_code:
            return "", ""
        
        try:
            # Execute R code
            result = r_client.execute_r_script(r_code)
            
            if result['success']:
                status = html.Div([
                    html.Span("✅ R code executed successfully", className="success-message"),
                    html.Br(),
                    html.Span(f"Return code: {result['returncode']}", className="info-message")
                ])
                
                # Display output
                output_content = []
                if result['stdout']:
                    output_content.append(html.H4("Output:"))
                    output_content.append(html.Pre(result['stdout'], className="code-output"))
                
                if result['stderr']:
                    output_content.append(html.H4("Messages:"))
                    output_content.append(html.Pre(result['stderr'], className="code-messages"))
                
                return status, html.Div(output_content)
            else:
                status = html.Div([
                    html.Span("❌ R code execution failed", className="error-message"),
                    html.Br(),
                    html.Span(f"Error: {result.get('error', 'Unknown error')}", className="error-details")
                ])
                return status, html.Pre(result['stderr'], className="error-output")
                
        except Exception as e:
            logger.error(f"Error executing R code: {e}")
            status = html.Span(f"❌ Error: {str(e)}", className="error-message")
            return status, ""
    
    @app.callback(
        Output("r-code-editor", "value"),
        [Input("clear-r-code", "n_clicks"),
         Input("load-example", "n_clicks")]
    )
    def manage_r_code(clear_clicks, example_clicks):
        ctx = callback_context
        if not ctx.triggered:
            return ""
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if button_id == "clear-r-code":
            return ""
        elif button_id == "load-example":
            example_code = """
# Example R code for gene expression analysis
library(ggplot2)
library(dplyr)

# Create sample data
set.seed(123)
data <- data.frame(
    gene = paste0("Gene_", 1:100),
    expression = rnorm(100, mean = 10, sd = 2),
    condition = rep(c("Control", "Treatment"), each = 50)
)

# Create boxplot
p <- ggplot(data, aes(x = condition, y = expression, fill = condition)) +
    geom_boxplot() +
    geom_jitter(width = 0.2, alpha = 0.6) +
    labs(title = "Gene Expression by Condition",
         x = "Condition",
         y = "Expression Level") +
    theme_minimal()

print(p)

# Summary statistics
summary_stats <- data %>%
    group_by(condition) %>%
    summarise(
        mean_expr = mean(expression),
        sd_expr = sd(expression),
        n = n()
    )

print(summary_stats)
"""
            return example_code
        
        return ""
    
    @app.callback(
        [Output("install-package", "children"),
         Output("installed-packages", "children")],
        [Input("install-package", "n_clicks")],
        [State("package-name", "value"),
         State("package-source", "value")]
    )
    def install_r_package(n_clicks, package_name, source):
        if n_clicks is None or not package_name:
            # Return current installed packages
            packages_html = []
            for package in r_client.available_packages[:20]:  # Show first 20
                packages_html.append(html.Span(package, className="package-tag"))
            
            return "Install Package", html.Div(packages_html)
        
        try:
            # Install package
            success = r_client.install_package(package_name, source)
            
            if success:
                button_text = f"✅ Installed {package_name}"
                # Update installed packages list
                packages_html = []
                for package in r_client.available_packages[:20]:
                    packages_html.append(html.Span(package, className="package-tag"))
                
                return button_text, html.Div(packages_html)
            else:
                return f"❌ Failed to install {package_name}", ""
                
        except Exception as e:
            logger.error(f"Error installing package: {e}")
            return f"❌ Error: {str(e)}", ""
    
    @app.callback(
        Output("r-analysis-content", "children"),
        [Input("analysis-tabs", "value")]
    )
    def update_analysis_content(active_tab):
        if active_tab == "deseq2":
            return html.Div([
                html.H4("DESeq2 Differential Expression Analysis"),
                html.P("Upload count data and metadata to run DESeq2 analysis"),
                html.Div([
                    html.Label("Design Formula:", className="input-label"),
                    dcc.Input(
                        id="deseq2-design",
                        value="~ condition",
                        placeholder="~ condition",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Button("Run DESeq2", id="run-deseq2", className="button primary"),
                html.Div(id="deseq2-results", className="analysis-results"),
            ])
        
        elif active_tab == "limma":
            return html.Div([
                html.H4("Limma Differential Expression Analysis"),
                html.P("Upload expression data and metadata to run limma analysis"),
                html.Button("Run Limma", id="run-limma", className="button primary"),
                html.Div(id="limma-results", className="analysis-results"),
            ])
        
        elif active_tab == "go":
            return html.Div([
                html.H4("GO Enrichment Analysis"),
                html.P("Enter gene list for GO enrichment analysis"),
                html.Div([
                    html.Label("Gene List (one per line):", className="input-label"),
                    dcc.Textarea(
                        id="gene-list",
                        placeholder="TP53\nBRCA1\nBRCA2\n...",
                        style={'width': '100%', 'height': '150px'},
                        className="textarea-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("P-value Cutoff:", className="input-label"),
                    dcc.Input(
                        id="pvalue-cutoff",
                        type="number",
                        value=0.05,
                        min=0.001,
                        max=0.1,
                        step=0.001,
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Button("Run GO Enrichment", id="run-go", className="button primary"),
                html.Div(id="go-results", className="analysis-results"),
            ])
    
    @app.callback(
        Output("deseq2-results", "children"),
        [Input("run-deseq2", "n_clicks")],
        [State("deseq2-design", "value")]
    )
    def run_deseq2_analysis(n_clicks, design_formula):
        if n_clicks is None:
            return ""
        
        try:
            # Create sample data for demonstration
            import numpy as np
            np.random.seed(42)
            
            # Generate sample count data
            n_genes = 1000
            n_samples = 12
            count_data = pd.DataFrame(
                np.random.negative_binomial(5, 0.3, (n_genes, n_samples)),
                columns=[f"Sample_{i+1}" for i in range(n_samples)],
                index=[f"Gene_{i+1}" for i in range(n_genes)]
            )
            
            # Generate sample metadata
            metadata = pd.DataFrame({
                'condition': ['Control'] * 6 + ['Treatment'] * 6,
                'batch': ['A', 'B'] * 6
            }, index=count_data.columns)
            
            # Run DESeq2 analysis
            result = r_client.run_deseq2_analysis(count_data, metadata, design_formula)
            
            if result['success']:
                return html.Div([
                    html.H5("✅ DESeq2 Analysis Completed"),
                    html.P("Differential expression analysis completed successfully"),
                    html.P(f"Found {len(result['results'])} genes"),
                    html.Button("Download Results", className="button secondary"),
                ])
            else:
                return html.Div([
                    html.H5("❌ DESeq2 Analysis Failed"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error running DESeq2: {e}")
            return html.Div([
                html.H5("❌ Error"),
                html.P(f"Error: {str(e)}"),
            ])
    
    @app.callback(
        Output("go-results", "children"),
        [Input("run-go", "n_clicks")],
        [State("gene-list", "value"),
         State("pvalue-cutoff", "value")]
    )
    def run_go_enrichment(n_clicks, gene_list, pvalue_cutoff):
        if n_clicks is None or not gene_list:
            return ""
        
        try:
            # Parse gene list
            genes = [gene.strip() for gene in gene_list.split('\n') if gene.strip()]
            
            # Run GO enrichment
            result = r_client.run_go_enrichment(genes, pvalue_cutoff=pvalue_cutoff)
            
            if result['success']:
                return html.Div([
                    html.H5("✅ GO Enrichment Analysis Completed"),
                    html.P(f"Analyzed {len(genes)} genes"),
                    html.P(f"Found {len(result['results'])} enriched GO terms"),
                    html.Button("Download Results", className="button secondary"),
                ])
            else:
                return html.Div([
                    html.H5("❌ GO Enrichment Analysis Failed"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error running GO enrichment: {e}")
            return html.Div([
                html.H5("❌ Error"),
                html.P(f"Error: {str(e)}"),
            ])
    
    @app.callback(
        Output("uploaded-data", "children"),
        [Input("data-upload", "contents")],
        [State("data-upload", "filename")]
    )
    def handle_data_upload(contents, filename):
        if contents is None:
            return ""
        
        try:
            # Process uploaded files
            uploaded_files = []
            for content, name in zip(contents, filename):
                # Parse CSV data
                if name.endswith('.csv'):
                    import base64
                    import io
                    
                    content_type, content_string = content.split(',')
                    decoded = base64.b64decode(content_string)
                    
                    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
                    
                    # Load data into R
                    r_client.load_data(df, name.replace('.csv', ''))
                    
                    uploaded_files.append(html.Div([
                        html.H5(f"✅ {name}"),
                        html.P(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns"),
                        html.P(f"Columns: {', '.join(df.columns[:5])}{'...' if len(df.columns) > 5 else ''}"),
                    ], className="uploaded-file"))
            
            return html.Div(uploaded_files)
            
        except Exception as e:
            logger.error(f"Error handling data upload: {e}")
            return html.P(f"❌ Upload failed: {str(e)}")
