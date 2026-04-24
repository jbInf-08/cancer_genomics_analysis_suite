"""
PDF Builder Module

This module provides functionality for generating PDF reports with various content types
including text, tables, charts, and images. It supports multiple output formats and
customizable styling options.
"""

import os
import io
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart


class PDFBuilder:
    """
    A comprehensive PDF report builder for cancer genomics analysis results.
    
    This class provides methods to create professional PDF reports with various
    content types including text, tables, charts, and images.
    """
    
    def __init__(self, output_path: str, page_size: str = "A4"):
        """
        Initialize the PDF builder.
        
        Args:
            output_path (str): Path where the PDF will be saved
            page_size (str): Page size for the PDF (A4 or letter)
        """
        self.output_path = output_path
        self.page_size = A4 if page_size.upper() == "A4" else letter
        self.styles = getSampleStyleSheet()
        self.story = []
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for the report."""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,  # Center alignment
            textColor=colors.darkblue
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.darkred
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        ))
    
    def add_title(self, title: str, subtitle: Optional[str] = None):
        """
        Add a title and optional subtitle to the report.
        
        Args:
            title (str): Main title of the report
            subtitle (str, optional): Subtitle text
        """
        self.story.append(Paragraph(title, self.styles['CustomTitle']))
        if subtitle:
            self.story.append(Paragraph(subtitle, self.styles['CustomHeading']))
        self.story.append(Spacer(1, 20))
    
    def add_heading(self, heading: str, level: int = 2):
        """
        Add a heading to the report.
        
        Args:
            heading (str): Heading text
            level (int): Heading level (1-6)
        """
        style_name = f'Heading{level}'
        if level == 1:
            style_name = 'CustomTitle'
        elif level == 2:
            style_name = 'CustomHeading'
        
        self.story.append(Paragraph(heading, self.styles[style_name]))
        self.story.append(Spacer(1, 12))
    
    def add_paragraph(self, text: str):
        """
        Add a paragraph of text to the report.
        
        Args:
            text (str): Text content
        """
        self.story.append(Paragraph(text, self.styles['CustomBody']))
        self.story.append(Spacer(1, 6))
    
    def add_table(self, data: List[List[str]], headers: Optional[List[str]] = None, 
                  title: Optional[str] = None):
        """
        Add a table to the report.
        
        Args:
            data (List[List[str]]): Table data as list of rows
            headers (List[str], optional): Column headers
            title (str, optional): Table title
        """
        if title:
            self.add_heading(title, level=3)
        
        # Prepare table data
        table_data = []
        if headers:
            table_data.append(headers)
        table_data.extend(data)
        
        # Create table
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        self.story.append(table)
        self.story.append(Spacer(1, 12))
    
    def add_dataframe_table(self, df: pd.DataFrame, title: Optional[str] = None):
        """
        Add a pandas DataFrame as a table to the report.
        
        Args:
            df (pd.DataFrame): DataFrame to convert to table
            title (str, optional): Table title
        """
        # Convert DataFrame to list format
        data = df.values.tolist()
        headers = df.columns.tolist()
        self.add_table(data, headers, title)
    
    def add_chart(self, chart_data: Dict[str, Any], chart_type: str = "bar", 
                  title: Optional[str] = None):
        """
        Add a chart to the report.
        
        Args:
            chart_data (Dict[str, Any]): Chart data
            chart_type (str): Type of chart (bar, line)
            title (str, optional): Chart title
        """
        if title:
            self.add_heading(title, level=3)
        
        # Create drawing
        drawing = Drawing(400, 200)
        
        if chart_type == "bar":
            chart = VerticalBarChart()
            chart.x = 50
            chart.y = 50
            chart.height = 125
            chart.width = 300
            chart.data = chart_data.get('data', [])
            chart.categoryAxis.categoryNames = chart_data.get('categories', [])
            drawing.add(chart)
        
        elif chart_type == "line":
            chart = HorizontalLineChart()
            chart.x = 50
            chart.y = 50
            chart.height = 125
            chart.width = 300
            chart.data = chart_data.get('data', [])
            chart.categoryAxis.categoryNames = chart_data.get('categories', [])
            drawing.add(chart)
        
        self.story.append(drawing)
        self.story.append(Spacer(1, 12))
    
    def add_image(self, image_path: str, width: float = 6*inch, 
                  height: float = 4*inch, caption: Optional[str] = None):
        """
        Add an image to the report.
        
        Args:
            image_path (str): Path to the image file
            width (float): Image width in inches
            height (float): Image height in inches
            caption (str, optional): Image caption
        """
        if os.path.exists(image_path):
            img = Image(image_path, width=width, height=height)
            self.story.append(img)
            if caption:
                self.story.append(Paragraph(f"<i>{caption}</i>", self.styles['CustomBody']))
            self.story.append(Spacer(1, 12))
    
    def add_page_break(self):
        """Add a page break to the report."""
        from reportlab.platypus import PageBreak
        self.story.append(PageBreak())
    
    def add_metadata(self, author: str = "Cancer Genomics Analysis Suite", 
                     subject: str = "Genomics Analysis Report", 
                     keywords: str = "genomics, cancer, analysis"):
        """
        Add metadata to the PDF.
        
        Args:
            author (str): Document author
            subject (str): Document subject
            keywords (str): Document keywords
        """
        self.metadata = {
            'author': author,
            'subject': subject,
            'keywords': keywords,
            'creator': 'Cancer Genomics Analysis Suite',
            'title': 'Genomics Analysis Report'
        }
    
    def build(self) -> str:
        """
        Build and save the PDF report.
        
        Returns:
            str: Path to the generated PDF file
        """
        # Create the PDF document
        doc = SimpleDocTemplate(
            self.output_path,
            pagesize=self.page_size,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Add metadata if provided (API varies by reportlab version)
        if hasattr(self, "metadata"):
            setter = getattr(doc, "setMetadata", None)
            if callable(setter):
                setter(self.metadata)
        
        # Build the PDF
        doc.build(self.story)
        
        return self.output_path
    
    def create_analysis_report(self, analysis_data: Dict[str, Any], 
                              output_path: Optional[str] = None) -> str:
        """
        Create a comprehensive analysis report.
        
        Args:
            analysis_data (Dict[str, Any]): Analysis data to include in report
            output_path (str, optional): Override default output path
            
        Returns:
            str: Path to the generated PDF file
        """
        if output_path:
            self.output_path = output_path
        
        # Add title and metadata
        self.add_title(
            "Cancer Genomics Analysis Report",
            f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Add analysis summary
        if 'summary' in analysis_data:
            self.add_heading("Analysis Summary")
            self.add_paragraph(analysis_data['summary'])
        
        # Add results tables
        if 'tables' in analysis_data:
            for table_info in analysis_data['tables']:
                self.add_dataframe_table(
                    table_info['data'], 
                    table_info.get('title', 'Results Table')
                )
        
        # Add charts
        if 'charts' in analysis_data:
            for chart_info in analysis_data['charts']:
                self.add_chart(
                    chart_info['data'],
                    chart_info.get('type', 'bar'),
                    chart_info.get('title', 'Chart')
                )
        
        # Add conclusions
        if 'conclusions' in analysis_data:
            self.add_heading("Conclusions")
            for conclusion in analysis_data['conclusions']:
                self.add_paragraph(conclusion)
        
        return self.build()
