"""
HTML Reporter Module

This module provides functionality for generating interactive HTML reports with
embedded visualizations, interactive charts, and responsive design for cancer
genomics analysis results.
"""

import os
import json
import base64
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder
import jinja2


class HTMLReporter:
    """
    A comprehensive HTML report generator for cancer genomics analysis results.
    
    This class provides methods to create interactive HTML reports with embedded
    visualizations, responsive design, and customizable templates.
    """
    
    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize the HTML reporter.
        
        Args:
            template_dir (str, optional): Directory containing custom templates
        """
        self.template_dir = template_dir or os.path.join(os.path.dirname(__file__), 'templates')
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_dir),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
        self.sections = []
        self.metadata = {}
    
    def set_metadata(self, title: str, author: str = "Cancer Genomics Analysis Suite",
                    description: str = "Genomics Analysis Report", 
                    keywords: List[str] = None):
        """
        Set report metadata.
        
        Args:
            title (str): Report title
            author (str): Report author
            description (str): Report description
            keywords (List[str]): Report keywords
        """
        self.metadata = {
            'title': title,
            'author': author,
            'description': description,
            'keywords': keywords or ['genomics', 'cancer', 'analysis'],
            'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def add_section(self, title: str, content: str, section_type: str = "text"):
        """
        Add a section to the report.
        
        Args:
            title (str): Section title
            content (str): Section content
            section_type (str): Type of section (text, chart, table, etc.)
        """
        self.sections.append({
            'title': title,
            'content': content,
            'type': section_type,
            'id': f"section_{len(self.sections)}"
        })
    
    def add_text_section(self, title: str, text: str):
        """
        Add a text section to the report.
        
        Args:
            title (str): Section title
            text (str): Text content
        """
        self.add_section(title, text, "text")
    
    def add_table_section(self, title: str, df: pd.DataFrame, 
                         interactive: bool = True):
        """
        Add a table section to the report.
        
        Args:
            title (str): Section title
            df (pd.DataFrame): DataFrame to display
            interactive (bool): Whether to make table interactive
        """
        if interactive:
            # Create interactive table HTML
            table_html = df.to_html(
                classes='table table-striped table-hover',
                table_id=f"table_{len(self.sections)}",
                escape=False
            )
        else:
            # Create simple table HTML
            table_html = df.to_html(classes='table table-bordered', escape=False)
        
        self.add_section(title, table_html, "table")
    
    def add_chart_section(self, title: str, fig: go.Figure, 
                         chart_type: str = "plotly"):
        """
        Add a chart section to the report.
        
        Args:
            title (str): Section title
            fig (go.Figure): Plotly figure object
            chart_type (str): Type of chart (plotly, static)
        """
        if chart_type == "plotly":
            # Convert plotly figure to JSON
            chart_json = json.dumps(fig, cls=PlotlyJSONEncoder)
            chart_html = f"""
            <div id="chart_{len(self.sections)}" class="chart-container">
                <script>
                    var chartData = {chart_json};
                    Plotly.newPlot('chart_{len(self.sections)}', chartData.data, chartData.layout);
                </script>
            </div>
            """
        else:
            # Convert to static image
            img_bytes = fig.to_image(format="png", width=800, height=600)
            img_base64 = base64.b64encode(img_bytes).decode()
            chart_html = f'<img src="data:image/png;base64,{img_base64}" class="img-fluid">'
        
        self.add_section(title, chart_html, "chart")
    
    def create_bar_chart(self, data: Dict[str, Any], title: str = "Bar Chart") -> go.Figure:
        """
        Create a bar chart using Plotly.
        
        Args:
            data (Dict[str, Any]): Chart data
            title (str): Chart title
            
        Returns:
            go.Figure: Plotly figure object
        """
        fig = go.Figure(data=[
            go.Bar(
                x=data.get('categories', []),
                y=data.get('values', []),
                marker_color=data.get('colors', 'steelblue')
            )
        ])
        
        fig.update_layout(
            title=title,
            xaxis_title=data.get('x_title', 'Categories'),
            yaxis_title=data.get('y_title', 'Values'),
            template='plotly_white'
        )
        
        return fig
    
    def create_line_chart(self, data: Dict[str, Any], title: str = "Line Chart") -> go.Figure:
        """
        Create a line chart using Plotly.
        
        Args:
            data (Dict[str, Any]): Chart data
            title (str): Chart title
            
        Returns:
            go.Figure: Plotly figure object
        """
        fig = go.Figure()
        
        for series_name, series_data in data.get('series', {}).items():
            fig.add_trace(go.Scatter(
                x=series_data.get('x', []),
                y=series_data.get('y', []),
                mode='lines+markers',
                name=series_name,
                line=dict(width=2)
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title=data.get('x_title', 'X Axis'),
            yaxis_title=data.get('y_title', 'Y Axis'),
            template='plotly_white'
        )
        
        return fig
    
    def create_scatter_plot(self, data: Dict[str, Any], title: str = "Scatter Plot") -> go.Figure:
        """
        Create a scatter plot using Plotly.
        
        Args:
            data (Dict[str, Any]): Chart data
            title (str): Chart title
            
        Returns:
            go.Figure: Plotly figure object
        """
        fig = go.Figure(data=go.Scatter(
            x=data.get('x', []),
            y=data.get('y', []),
            mode='markers',
            marker=dict(
                size=data.get('sizes', 8),
                color=data.get('colors', 'steelblue'),
                opacity=0.7
            ),
            text=data.get('labels', []),
            hovertemplate='%{text}<br>X: %{x}<br>Y: %{y}<extra></extra>'
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title=data.get('x_title', 'X Axis'),
            yaxis_title=data.get('y_title', 'Y Axis'),
            template='plotly_white'
        )
        
        return fig
    
    def create_heatmap(self, data: pd.DataFrame, title: str = "Heatmap") -> go.Figure:
        """
        Create a heatmap using Plotly.
        
        Args:
            data (pd.DataFrame): Data for heatmap
            title (str): Chart title
            
        Returns:
            go.Figure: Plotly figure object
        """
        fig = go.Figure(data=go.Heatmap(
            z=data.values,
            x=data.columns,
            y=data.index,
            colorscale='Viridis'
        ))
        
        fig.update_layout(
            title=title,
            template='plotly_white'
        )
        
        return fig
    
    def generate_html(self, template_name: str = "report_template.html") -> str:
        """
        Generate the complete HTML report.
        
        Args:
            template_name (str): Name of the template file
            
        Returns:
            str: Complete HTML content
        """
        try:
            template = self.jinja_env.get_template(template_name)
        except jinja2.TemplateNotFound:
            # Use default template if custom template not found
            template = self._get_default_template()
        
        html_content = template.render(
            metadata=self.metadata,
            sections=self.sections,
            total_sections=len(self.sections)
        )
        
        return html_content
    
    def _get_default_template(self) -> jinja2.Template:
        """
        Get the default HTML template.
        
        Returns:
            jinja2.Template: Default template
        """
        default_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ metadata.title }}</title>
    <meta name="author" content="{{ metadata.author }}">
    <meta name="description" content="{{ metadata.description }}">
    <meta name="keywords" content="{{ metadata.keywords | join(', ') }}">
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Plotly.js -->
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <!-- Custom CSS -->
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .report-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem 0; }
        .section-title { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 0.5rem; }
        .chart-container { margin: 2rem 0; }
        .table-container { overflow-x: auto; }
        .metadata { background-color: #f8f9fa; padding: 1rem; border-radius: 0.5rem; margin-bottom: 2rem; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <!-- Header -->
        <div class="report-header text-center">
            <h1>{{ metadata.title }}</h1>
            <p class="lead">Generated by {{ metadata.author }}</p>
            <p><small>{{ metadata.generated_date }}</small></p>
        </div>
        
        <!-- Metadata -->
        <div class="metadata">
            <h5>Report Information</h5>
            <div class="row">
                <div class="col-md-6">
                    <strong>Author:</strong> {{ metadata.author }}<br>
                    <strong>Generated:</strong> {{ metadata.generated_date }}
                </div>
                <div class="col-md-6">
                    <strong>Description:</strong> {{ metadata.description }}<br>
                    <strong>Sections:</strong> {{ total_sections }}
                </div>
            </div>
        </div>
        
        <!-- Content -->
        <div class="row">
            <div class="col-12">
                {% for section in sections %}
                <div class="section mb-5">
                    <h2 class="section-title">{{ section.title }}</h2>
                    <div class="section-content">
                        {% if section.type == 'chart' %}
                            {{ section.content | safe }}
                        {% elif section.type == 'table' %}
                            <div class="table-container">
                                {{ section.content | safe }}
                            </div>
                        {% else %}
                            <div class="text-content">
                                {{ section.content | safe }}
                            </div>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <!-- Footer -->
        <footer class="text-center py-4 mt-5" style="background-color: #f8f9fa;">
            <p>&copy; 2024 {{ metadata.author }}. All rights reserved.</p>
        </footer>
    </div>
    
    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
        """
        return jinja2.Template(default_template)
    
    def save_report(self, output_path: str, template_name: str = "report_template.html") -> str:
        """
        Generate and save the HTML report to a file.
        
        Args:
            output_path (str): Path where to save the HTML file
            template_name (str): Name of the template file
            
        Returns:
            str: Path to the saved HTML file
        """
        html_content = self.generate_html(template_name)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_path
    
    def create_analysis_report(self, analysis_data: Dict[str, Any], 
                              output_path: str) -> str:
        """
        Create a comprehensive analysis report.
        
        Args:
            analysis_data (Dict[str, Any]): Analysis data to include in report
            output_path (str): Path where to save the HTML file
            
        Returns:
            str: Path to the saved HTML file
        """
        # Set metadata
        self.set_metadata(
            title=analysis_data.get('title', 'Cancer Genomics Analysis Report'),
            description=analysis_data.get('description', 'Comprehensive genomics analysis results')
        )
        
        # Add summary section
        if 'summary' in analysis_data:
            self.add_text_section("Analysis Summary", analysis_data['summary'])
        
        # Add results tables
        if 'tables' in analysis_data:
            for table_info in analysis_data['tables']:
                self.add_table_section(
                    table_info.get('title', 'Results Table'),
                    table_info['data']
                )
        
        # Add charts
        if 'charts' in analysis_data:
            for chart_info in analysis_data['charts']:
                chart_type = chart_info.get('type', 'bar')
                title = chart_info.get('title', 'Chart')
                
                if chart_type == 'bar':
                    fig = self.create_bar_chart(chart_info['data'], title)
                elif chart_type == 'line':
                    fig = self.create_line_chart(chart_info['data'], title)
                elif chart_type == 'scatter':
                    fig = self.create_scatter_plot(chart_info['data'], title)
                elif chart_type == 'heatmap':
                    fig = self.create_heatmap(chart_info['data'], title)
                else:
                    continue
                
                self.add_chart_section(title, fig)
        
        # Add conclusions
        if 'conclusions' in analysis_data:
            conclusions_text = '<br>'.join([f"• {c}" for c in analysis_data['conclusions']])
            self.add_text_section("Conclusions", conclusions_text)
        
        return self.save_report(output_path)
