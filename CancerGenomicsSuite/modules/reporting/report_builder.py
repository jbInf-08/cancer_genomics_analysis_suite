"""
Report Builder Module

Provides comprehensive report generation capabilities for the Cancer Genomics Analysis Suite.
Supports multiple report formats, automated generation, and customizable templates.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path
import json
import uuid
from datetime import datetime, timedelta
import base64
import io
import zipfile
from jinja2 import Template, Environment, FileSystemLoader
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import weasyprint
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger(__name__)


class ReportType(Enum):
    """Types of reports."""
    ANALYSIS_SUMMARY = "analysis_summary"
    QUALITY_CONTROL = "quality_control"
    DIFFERENTIAL_EXPRESSION = "differential_expression"
    PATHWAY_ANALYSIS = "pathway_analysis"
    MUTATION_ANALYSIS = "mutation_analysis"
    SURVIVAL_ANALYSIS = "survival_analysis"
    CLINICAL_REPORT = "clinical_report"
    CUSTOM = "custom"


class ReportFormat(Enum):
    """Report output formats."""
    HTML = "html"
    PDF = "pdf"
    DOCX = "docx"
    EXCEL = "excel"
    JSON = "json"
    MARKDOWN = "markdown"


@dataclass
class ReportSection:
    """Represents a section of a report."""
    id: str
    title: str
    content_type: str  # 'text', 'table', 'chart', 'image', 'html'
    content: Any
    order: int = 0
    visible: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert section to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'content_type': self.content_type,
            'content': self.content,
            'order': self.order,
            'visible': self.visible,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReportSection':
        """Create section from dictionary."""
        return cls(**data)


class ReportBuilder:
    """
    Builds comprehensive reports for genomics analysis results.
    
    Features:
    - Multiple report types and formats
    - Template-based generation
    - Automated section creation
    - Chart and table integration
    - Export functionality
    - Email distribution
    - Custom styling and branding
    """
    
    def __init__(self, output_dir: str = None):
        """
        Initialize ReportBuilder.
        
        Args:
            output_dir: Directory for report output
        """
        self.output_dir = Path(output_dir) if output_dir else Path("outputs/reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Template directories
        self.template_dir = Path(__file__).parent / "templates"
        self.template_dir.mkdir(exist_ok=True)
        
        # Initialize Jinja2 environment
        self.jinja_env = Environment(loader=FileSystemLoader(str(self.template_dir)))
        
        # Report storage
        self.reports = {}
        self.templates = {}
        
        # Initialize default templates
        self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default report templates."""
        # HTML template
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body { fontFamily: Arial, sans-serif; margin: 40px; line-height: 1.6; }
        .header { border-bottom: 2px solid #333; padding-bottom: 20px; margin-bottom: 30px; }
        .title { color: #2c3e50; font-size: 28px; margin: 0; }
        .subtitle { color: #7f8c8d; font-size: 16px; margin: 5px 0; }
        .section { margin: 30px 0; }
        .section-title { color: #34495e; font-size: 20px; border-left: 4px solid #3498db; padding-left: 15px; }
        .content { margin: 15px 0; }
        .table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .table th, .table td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        .table th { background-color: #f2f2f2; font-weight: bold; }
        .chart { margin: 20px 0; text-align: center; }
        .footer { margin-top: 50px; padding-top: 20px; border-top: 1px solid #ddd; color: #7f8c8d; font-size: 12px; }
        .metadata { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1 class="title">{{ title }}</h1>
        <p class="subtitle">{{ subtitle }}</p>
        <p class="subtitle">Generated on: {{ generated_at }}</p>
    </div>
    
    {% if metadata %}
    <div class="metadata">
        <h3>Report Metadata</h3>
        <ul>
            {% for key, value in metadata.items() %}
            <li><strong>{{ key }}:</strong> {{ value }}</li>
            {% endfor %}
        </ul>
    </div>
    {% endif %}
    
    {% for section in sections %}
    {% if section.visible %}
    <div class="section">
        <h2 class="section-title">{{ section.title }}</h2>
        <div class="content">
            {% if section.content_type == 'text' %}
                {{ section.content }}
            {% elif section.content_type == 'html' %}
                {{ section.content|safe }}
            {% elif section.content_type == 'table' %}
                <table class="table">
                    <thead>
                        <tr>
                            {% for header in section.content.columns %}
                            <th>{{ header }}</th>
                            {% endfor %}
                        </tr>
                    </thead>
                    <tbody>
                        {% for _, row in section.content.iterrows() %}
                        <tr>
                            {% for value in row %}
                            <td>{{ value }}</td>
                            {% endfor %}
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            {% elif section.content_type == 'chart' %}
                <div class="chart">
                    {{ section.content|safe }}
                </div>
            {% elif section.content_type == 'image' %}
                <div class="chart">
                    <img src="{{ section.content }}" alt="{{ section.title }}" style="max-width: 100%; height: auto;">
                </div>
            {% endif %}
        </div>
    </div>
    {% endif %}
    {% endfor %}
    
    <div class="footer">
        <p>Report generated by Cancer Genomics Analysis Suite</p>
        <p>Generated at: {{ generated_at }}</p>
    </div>
</body>
</html>
        """
        
        # Markdown template
        markdown_template = """
# {{ title }}

**{{ subtitle }}**

*Generated on: {{ generated_at }}*

{% if metadata %}
## Report Metadata
{% for key, value in metadata.items() %}
- **{{ key }}:** {{ value }}
{% endfor %}
{% endif %}

{% for section in sections %}
{% if section.visible %}
## {{ section.title }}

{% if section.content_type == 'text' %}
{{ section.content }}
{% elif section.content_type == 'table' %}
{% for _, row in section.content.iterrows() %}
| {% for value in row %}{{ value }} | {% endfor %}
{% endfor %}
{% elif section.content_type == 'html' %}
{{ section.content }}
{% endif %}

{% endif %}
{% endfor %}

---
*Report generated by Cancer Genomics Analysis Suite*
        """
        
        # Save templates
        (self.template_dir / "html_template.html").write_text(html_template)
        (self.template_dir / "markdown_template.md").write_text(markdown_template)
    
    def create_report(self, report_id: str, title: str, report_type: ReportType = ReportType.CUSTOM,
                     subtitle: str = "", metadata: Dict[str, Any] = None) -> str:
        """
        Create a new report.
        
        Args:
            report_id: Unique identifier for the report
            title: Report title
            report_type: Type of report
            subtitle: Report subtitle
            metadata: Additional metadata
            
        Returns:
            str: Report ID
        """
        report_data = {
            'id': report_id,
            'title': title,
            'subtitle': subtitle,
            'report_type': report_type,
            'sections': [],
            'metadata': metadata or {},
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        self.reports[report_id] = report_data
        logger.info(f"Created report: {title}")
        return report_id
    
    def add_section(self, report_id: str, section: ReportSection):
        """
        Add a section to a report.
        
        Args:
            report_id: Report to add section to
            section: Section to add
        """
        if report_id not in self.reports:
            raise ValueError(f"Report {report_id} not found")
        
        self.reports[report_id]['sections'].append(section.to_dict())
        self.reports[report_id]['updated_at'] = datetime.now()
        
        # Sort sections by order
        self.reports[report_id]['sections'].sort(key=lambda x: x['order'])
        
        logger.info(f"Added section '{section.title}' to report {report_id}")
    
    def add_text_section(self, report_id: str, title: str, content: str, order: int = 0):
        """Add a text section to a report."""
        section = ReportSection(
            id=str(uuid.uuid4()),
            title=title,
            content_type='text',
            content=content,
            order=order
        )
        self.add_section(report_id, section)
    
    def add_table_section(self, report_id: str, title: str, data: pd.DataFrame, order: int = 0):
        """Add a table section to a report."""
        section = ReportSection(
            id=str(uuid.uuid4()),
            title=title,
            content_type='table',
            content=data,
            order=order
        )
        self.add_section(report_id, section)
    
    def add_chart_section(self, report_id: str, title: str, chart_html: str, order: int = 0):
        """Add a chart section to a report."""
        section = ReportSection(
            id=str(uuid.uuid4()),
            title=title,
            content_type='chart',
            content=chart_html,
            order=order
        )
        self.add_section(report_id, section)
    
    def add_image_section(self, report_id: str, title: str, image_path: str, order: int = 0):
        """Add an image section to a report."""
        section = ReportSection(
            id=str(uuid.uuid4()),
            title=title,
            content_type='image',
            content=image_path,
            order=order
        )
        self.add_section(report_id, section)
    
    def add_html_section(self, report_id: str, title: str, html_content: str, order: int = 0):
        """Add an HTML section to a report."""
        section = ReportSection(
            id=str(uuid.uuid4()),
            title=title,
            content_type='html',
            content=html_content,
            order=order
        )
        self.add_section(report_id, section)
    
    def generate_analysis_summary_report(self, report_id: str, analysis_data: Dict[str, Any]) -> str:
        """
        Generate an analysis summary report.
        
        Args:
            report_id: Report identifier
            analysis_data: Analysis results data
            
        Returns:
            str: Generated report content
        """
        report = self.reports.get(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")
        
        # Add summary statistics
        if 'summary_stats' in analysis_data:
            stats_df = pd.DataFrame(list(analysis_data['summary_stats'].items()), 
                                  columns=['Metric', 'Value'])
            self.add_table_section(report_id, "Summary Statistics", stats_df, 1)
        
        # Add quality metrics
        if 'quality_metrics' in analysis_data:
            quality_df = pd.DataFrame(analysis_data['quality_metrics'])
            self.add_table_section(report_id, "Quality Metrics", quality_df, 2)
        
        # Add sample information
        if 'sample_info' in analysis_data:
            sample_df = pd.DataFrame(analysis_data['sample_info'])
            self.add_table_section(report_id, "Sample Information", sample_df, 3)
        
        # Add analysis parameters
        if 'parameters' in analysis_data:
            params_text = "\n".join([f"- **{k}:** {v}" for k, v in analysis_data['parameters'].items()])
            self.add_text_section(report_id, "Analysis Parameters", params_text, 4)
        
        logger.info(f"Generated analysis summary report: {report_id}")
        return report_id
    
    def generate_quality_control_report(self, report_id: str, qc_data: Dict[str, Any]) -> str:
        """
        Generate a quality control report.
        
        Args:
            report_id: Report identifier
            qc_data: Quality control data
            
        Returns:
            str: Generated report content
        """
        report = self.reports.get(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")
        
        # Add QC summary
        if 'qc_summary' in qc_data:
            qc_text = f"""
            Quality Control Summary:
            - Total samples: {qc_data['qc_summary'].get('total_samples', 'N/A')}
            - Passed samples: {qc_data['qc_summary'].get('passed_samples', 'N/A')}
            - Failed samples: {qc_data['qc_summary'].get('failed_samples', 'N/A')}
            - Pass rate: {qc_data['qc_summary'].get('pass_rate', 'N/A')}%
            """
            self.add_text_section(report_id, "QC Summary", qc_text, 1)
        
        # Add failed samples
        if 'failed_samples' in qc_data:
            failed_df = pd.DataFrame(qc_data['failed_samples'])
            self.add_table_section(report_id, "Failed Samples", failed_df, 2)
        
        # Add QC metrics
        if 'qc_metrics' in qc_data:
            metrics_df = pd.DataFrame(qc_data['qc_metrics'])
            self.add_table_section(report_id, "QC Metrics", metrics_df, 3)
        
        logger.info(f"Generated quality control report: {report_id}")
        return report_id
    
    def generate_differential_expression_report(self, report_id: str, de_data: Dict[str, Any]) -> str:
        """
        Generate a differential expression report.
        
        Args:
            report_id: Report identifier
            de_data: Differential expression data
            
        Returns:
            str: Generated report content
        """
        report = self.reports.get(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")
        
        # Add DE summary
        if 'de_summary' in de_data:
            de_text = f"""
            Differential Expression Analysis Summary:
            - Total genes analyzed: {de_data['de_summary'].get('total_genes', 'N/A')}
            - Significantly differentially expressed: {de_data['de_summary'].get('significant_genes', 'N/A')}
            - Upregulated genes: {de_data['de_summary'].get('upregulated', 'N/A')}
            - Downregulated genes: {de_data['de_summary'].get('downregulated', 'N/A')}
            - Fold change threshold: {de_data['de_summary'].get('fc_threshold', 'N/A')}
            - P-value threshold: {de_data['de_summary'].get('pvalue_threshold', 'N/A')}
            """
            self.add_text_section(report_id, "DE Analysis Summary", de_text, 1)
        
        # Add top differentially expressed genes
        if 'top_genes' in de_data:
            top_genes_df = pd.DataFrame(de_data['top_genes'])
            self.add_table_section(report_id, "Top Differentially Expressed Genes", top_genes_df, 2)
        
        # Add volcano plot if available
        if 'volcano_plot' in de_data:
            self.add_chart_section(report_id, "Volcano Plot", de_data['volcano_plot'], 3)
        
        # Add MA plot if available
        if 'ma_plot' in de_data:
            self.add_chart_section(report_id, "MA Plot", de_data['ma_plot'], 4)
        
        logger.info(f"Generated differential expression report: {report_id}")
        return report_id
    
    def export_report(self, report_id: str, format: ReportFormat, 
                     output_path: str = None) -> str:
        """
        Export a report to the specified format.
        
        Args:
            report_id: Report to export
            format: Export format
            output_path: Custom output path
            
        Returns:
            str: Path to exported file
        """
        if report_id not in self.reports:
            raise ValueError(f"Report {report_id} not found")
        
        report = self.reports[report_id]
        
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{report_id}_{timestamp}.{format.value}"
            output_path = self.output_dir / filename
        else:
            output_path = Path(output_path)
        
        if format == ReportFormat.HTML:
            return self._export_html(report, output_path)
        elif format == ReportFormat.PDF:
            return self._export_pdf(report, output_path)
        elif format == ReportFormat.MARKDOWN:
            return self._export_markdown(report, output_path)
        elif format == ReportFormat.JSON:
            return self._export_json(report, output_path)
        elif format == ReportFormat.EXCEL:
            return self._export_excel(report, output_path)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_html(self, report: Dict[str, Any], output_path: Path) -> str:
        """Export report as HTML."""
        template = self.jinja_env.get_template('html_template.html')
        
        # Convert sections back to objects for template
        sections = [ReportSection.from_dict(section) for section in report['sections']]
        
        html_content = template.render(
            title=report['title'],
            subtitle=report['subtitle'],
            generated_at=report['updated_at'].strftime('%Y-%m-%d %H:%M:%S'),
            metadata=report['metadata'],
            sections=sections
        )
        
        output_path.write_text(html_content, encoding='utf-8')
        logger.info(f"Exported HTML report to {output_path}")
        return str(output_path)
    
    def _export_pdf(self, report: Dict[str, Any], output_path: Path) -> str:
        """Export report as PDF."""
        doc = SimpleDocTemplate(str(output_path), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.darkblue
        )
        story.append(Paragraph(report['title'], title_style))
        story.append(Spacer(1, 12))
        
        # Subtitle
        if report['subtitle']:
            story.append(Paragraph(report['subtitle'], styles['Normal']))
            story.append(Spacer(1, 12))
        
        # Generated date
        story.append(Paragraph(f"Generated on: {report['updated_at'].strftime('%Y-%m-%d %H:%M:%S')}", 
                              styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Sections
        for section_data in report['sections']:
            if not section_data['visible']:
                continue
            
            section = ReportSection.from_dict(section_data)
            
            # Section title
            story.append(Paragraph(section.title, styles['Heading2']))
            story.append(Spacer(1, 12))
            
            # Section content
            if section.content_type == 'text':
                story.append(Paragraph(section.content, styles['Normal']))
            elif section.content_type == 'table':
                # Convert DataFrame to table
                data = section.content
                table_data = [list(data.columns)]
                for _, row in data.iterrows():
                    table_data.append([str(val) for val in row])
                
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(table)
            
            story.append(Spacer(1, 20))
        
        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph("Report generated by Cancer Genomics Analysis Suite", 
                              styles['Normal']))
        
        doc.build(story)
        logger.info(f"Exported PDF report to {output_path}")
        return str(output_path)
    
    def _export_markdown(self, report: Dict[str, Any], output_path: Path) -> str:
        """Export report as Markdown."""
        template = self.jinja_env.get_template('markdown_template.md')
        
        # Convert sections back to objects for template
        sections = [ReportSection.from_dict(section) for section in report['sections']]
        
        markdown_content = template.render(
            title=report['title'],
            subtitle=report['subtitle'],
            generated_at=report['updated_at'].strftime('%Y-%m-%d %H:%M:%S'),
            metadata=report['metadata'],
            sections=sections
        )
        
        output_path.write_text(markdown_content, encoding='utf-8')
        logger.info(f"Exported Markdown report to {output_path}")
        return str(output_path)
    
    def _export_json(self, report: Dict[str, Any], output_path: Path) -> str:
        """Export report as JSON."""
        # Convert datetime objects to strings for JSON serialization
        export_data = report.copy()
        export_data['created_at'] = export_data['created_at'].isoformat()
        export_data['updated_at'] = export_data['updated_at'].isoformat()
        
        # Convert DataFrame objects to dictionaries
        for section in export_data['sections']:
            if section['content_type'] == 'table':
                section['content'] = section['content'].to_dict('records')
        
        output_path.write_text(json.dumps(export_data, indent=2, default=str), encoding='utf-8')
        logger.info(f"Exported JSON report to {output_path}")
        return str(output_path)
    
    def _export_excel(self, report: Dict[str, Any], output_path: Path) -> str:
        """Export report as Excel."""
        with pd.ExcelWriter(str(output_path), engine='openpyxl') as writer:
            # Summary sheet
            summary_data = {
                'Title': [report['title']],
                'Subtitle': [report['subtitle']],
                'Report Type': [report['report_type'].value],
                'Created At': [report['created_at'].strftime('%Y-%m-%d %H:%M:%S')],
                'Updated At': [report['updated_at'].strftime('%Y-%m-%d %H:%M:%S')]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Metadata sheet
            if report['metadata']:
                metadata_df = pd.DataFrame(list(report['metadata'].items()), 
                                         columns=['Key', 'Value'])
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
            
            # Sections
            for i, section_data in enumerate(report['sections']):
                if not section_data['visible']:
                    continue
                
                section = ReportSection.from_dict(section_data)
                sheet_name = f"Section_{i+1}_{section.title[:30]}"  # Limit sheet name length
                
                if section.content_type == 'table':
                    section.content.to_excel(writer, sheet_name=sheet_name, index=False)
                elif section.content_type == 'text':
                    text_df = pd.DataFrame({'Content': [section.content]})
                    text_df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        logger.info(f"Exported Excel report to {output_path}")
        return str(output_path)
    
    def create_report_package(self, report_id: str, include_data: bool = True) -> str:
        """
        Create a complete report package with all files.
        
        Args:
            report_id: Report to package
            include_data: Whether to include raw data files
            
        Returns:
            str: Path to package file
        """
        if report_id not in self.reports:
            raise ValueError(f"Report {report_id} not found")
        
        report = self.reports[report_id]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        package_path = self.output_dir / f"{report_id}_package_{timestamp}.zip"
        
        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add report in multiple formats
            for format in [ReportFormat.HTML, ReportFormat.PDF, ReportFormat.MARKDOWN]:
                try:
                    export_path = self.export_report(report_id, format)
                    zipf.write(export_path, f"report.{format.value}")
                except Exception as e:
                    logger.warning(f"Failed to export {format.value}: {e}")
            
            # Add data files if requested
            if include_data:
                for section_data in report['sections']:
                    section = ReportSection.from_dict(section_data)
                    if section.content_type == 'table':
                        data_path = self.output_dir / f"{section.id}_data.csv"
                        section.content.to_csv(data_path, index=False)
                        zipf.write(data_path, f"data/{section.title.replace(' ', '_')}.csv")
        
        logger.info(f"Created report package: {package_path}")
        return str(package_path)
    
    def get_report_summary(self, report_id: str) -> Dict[str, Any]:
        """Get summary information about a report."""
        if report_id not in self.reports:
            raise ValueError(f"Report {report_id} not found")
        
        report = self.reports[report_id]
        
        return {
            'id': report_id,
            'title': report['title'],
            'type': report['report_type'].value,
            'sections_count': len(report['sections']),
            'visible_sections': len([s for s in report['sections'] if s['visible']]),
            'created_at': report['created_at'].isoformat(),
            'updated_at': report['updated_at'].isoformat(),
            'metadata': report['metadata']
        }
    
    def list_reports(self) -> List[Dict[str, Any]]:
        """List all reports with summary information."""
        return [self.get_report_summary(report_id) for report_id in self.reports.keys()]
    
    def delete_report(self, report_id: str) -> bool:
        """Delete a report."""
        if report_id in self.reports:
            del self.reports[report_id]
            logger.info(f"Deleted report: {report_id}")
            return True
        return False
