"""
Reporting Pipeline Module

This module provides comprehensive automated reporting pipeline capabilities
for the Cancer Genomics Analysis Suite, including report generation,
scheduling, and distribution workflows.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path
import json
import schedule
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Import reporting engine components
from ..reporting_engine import PDFBuilder, HTMLReporter, TemplateUtils


@dataclass
class ReportConfig:
    """Report configuration parameters."""
    # Report settings
    report_type: str = "analysis"  # analysis, summary, dashboard, custom
    output_format: str = "pdf"  # pdf, html, both
    template_name: Optional[str] = None
    
    # Scheduling
    schedule_enabled: bool = False
    schedule_frequency: str = "daily"  # daily, weekly, monthly, custom
    schedule_time: str = "09:00"  # HH:MM format
    schedule_days: List[str] = field(default_factory=lambda: ["monday", "tuesday", "wednesday", "thursday", "friday"])
    
    # Output settings
    output_directory: str = "outputs/reports"
    filename_template: str = "report_{date}_{type}"
    include_timestamp: bool = True
    
    # Email settings
    email_enabled: bool = False
    email_recipients: List[str] = field(default_factory=list)
    email_subject: str = "Cancer Genomics Analysis Report"
    email_body_template: Optional[str] = None
    
    # Data sources
    data_sources: List[str] = field(default_factory=list)
    data_filters: Dict[str, Any] = field(default_factory=dict)
    
    # Customization
    include_charts: bool = True
    include_tables: bool = True
    include_summary: bool = True
    chart_types: List[str] = field(default_factory=lambda: ["bar", "line", "scatter"])
    max_rows_per_table: int = 1000


@dataclass
class ReportJob:
    """Report job data structure."""
    job_id: str
    config: ReportConfig
    status: str = "pending"  # pending, running, completed, failed
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_files: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReportingPipeline:
    """
    A comprehensive automated reporting pipeline for cancer genomics analysis.
    
    This class provides methods for generating, scheduling, and distributing
    various types of reports including analysis summaries, dashboards, and
    custom reports.
    """
    
    def __init__(self, config: ReportConfig):
        """
        Initialize the reporting pipeline.
        
        Args:
            config (ReportConfig): Report configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.jobs: Dict[str, ReportJob] = {}
        self.template_utils = TemplateUtils()
        self.scheduler_running = False
        
        # Create output directory
        os.makedirs(self.config.output_directory, exist_ok=True)
        
        # Initialize email settings if enabled
        if self.config.email_enabled:
            self._setup_email_config()
    
    def _setup_email_config(self):
        """Setup email configuration."""
        # This would typically load from environment variables or config file
        self.email_config = {
            'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', 587)),
            'username': os.getenv('EMAIL_USERNAME'),
            'password': os.getenv('EMAIL_PASSWORD'),
            'from_email': os.getenv('FROM_EMAIL')
        }
    
    def generate_report(self, data: Optional[Dict[str, Any]] = None, 
                       custom_config: Optional[ReportConfig] = None) -> ReportJob:
        """
        Generate a report based on configuration.
        
        Args:
            data (Dict[str, Any], optional): Custom data to include in report
            custom_config (ReportConfig, optional): Override default configuration
            
        Returns:
            ReportJob: Report job object
        """
        config = custom_config or self.config
        
        # Create job
        job_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        job = ReportJob(job_id=job_id, config=config)
        self.jobs[job_id] = job
        
        try:
            job.status = "running"
            job.started_at = datetime.now()
            
            self.logger.info(f"Starting report generation: {job_id}")
            
            # Load data if not provided
            if data is None:
                data = self._load_report_data(config)
            
            # Generate report based on format
            if config.output_format in ["pdf", "both"]:
                pdf_file = self._generate_pdf_report(data, config, job_id)
                job.output_files.append(pdf_file)
            
            if config.output_format in ["html", "both"]:
                html_file = self._generate_html_report(data, config, job_id)
                job.output_files.append(html_file)
            
            job.status = "completed"
            job.completed_at = datetime.now()
            
            self.logger.info(f"Report generation completed: {job_id}")
            
            # Send email if enabled
            if config.email_enabled and config.email_recipients:
                self._send_report_email(job)
            
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now()
            self.logger.error(f"Report generation failed: {job_id} - {e}")
        
        return job
    
    def _load_report_data(self, config: ReportConfig) -> Dict[str, Any]:
        """Load data for report generation."""
        data = {
            'title': f"Cancer Genomics Analysis Report - {datetime.now().strftime('%Y-%m-%d')}",
            'generated_date': datetime.now().isoformat(),
            'summary': "This report contains comprehensive analysis results from the Cancer Genomics Analysis Suite.",
            'tables': [],
            'charts': [],
            'conclusions': []
        }
        
        # Load data from configured sources
        for source in config.data_sources:
            try:
                source_data = self._load_data_source(source, config.data_filters)
                data.update(source_data)
            except Exception as e:
                self.logger.warning(f"Failed to load data source {source}: {e}")
        
        return data
    
    def _load_data_source(self, source: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Load data from a specific source."""
        # This would typically load from databases, files, or APIs
        # For now, we'll return mock data
        
        if source == "mutations":
            return self._load_mutation_data(filters)
        elif source == "expression":
            return self._load_expression_data(filters)
        elif source == "clinical":
            return self._load_clinical_data(filters)
        else:
            return {}
    
    def _load_mutation_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Load mutation data."""
        # Mock mutation data
        mutations_df = pd.DataFrame({
            'gene': ['TP53', 'BRCA1', 'EGFR', 'KRAS', 'PIK3CA'] * 20,
            'mutation_type': ['missense', 'nonsense', 'frameshift', 'splice_site', 'silent'] * 20,
            'chromosome': ['17', '17', '7', '12', '3'] * 20,
            'position': np.random.randint(1000000, 10000000, 100),
            'impact': ['high', 'moderate', 'low'] * 33 + ['high'],
            'frequency': np.random.uniform(0.01, 0.5, 100)
        })
        
        return {
            'mutation_data': mutations_df,
            'tables': [{
                'title': 'Mutation Summary',
                'data': mutations_df.head(10)
            }],
            'charts': [{
                'title': 'Mutation Types Distribution',
                'type': 'bar',
                'data': {
                    'categories': mutations_df['mutation_type'].value_counts().index.tolist(),
                    'values': mutations_df['mutation_type'].value_counts().values.tolist()
                }
            }]
        }
    
    def _load_expression_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Load gene expression data."""
        # Mock expression data
        expression_df = pd.DataFrame({
            'gene': ['TP53', 'BRCA1', 'EGFR', 'KRAS', 'PIK3CA'] * 20,
            'sample_id': [f'sample_{i}' for i in range(100)],
            'expression_value': np.random.lognormal(5, 1, 100),
            'tissue_type': ['tumor', 'normal'] * 50,
            'patient_id': [f'patient_{i//2}' for i in range(100)]
        })
        
        return {
            'expression_data': expression_df,
            'tables': [{
                'title': 'Expression Summary',
                'data': expression_df.groupby('gene')['expression_value'].agg(['mean', 'std']).reset_index()
            }],
            'charts': [{
                'title': 'Gene Expression by Tissue Type',
                'type': 'box',
                'data': expression_df
            }]
        }
    
    def _load_clinical_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Load clinical data."""
        # Mock clinical data
        clinical_df = pd.DataFrame({
            'patient_id': [f'patient_{i}' for i in range(50)],
            'age': np.random.randint(30, 80, 50),
            'gender': np.random.choice(['M', 'F'], 50),
            'stage': np.random.choice(['I', 'II', 'III', 'IV'], 50),
            'survival_days': np.random.randint(30, 2000, 50),
            'treatment_response': np.random.choice(['CR', 'PR', 'SD', 'PD'], 50)
        })
        
        return {
            'clinical_data': clinical_df,
            'tables': [{
                'title': 'Clinical Summary',
                'data': clinical_df.describe()
            }],
            'charts': [{
                'title': 'Survival by Stage',
                'type': 'scatter',
                'data': clinical_df[['stage', 'survival_days']]
            }]
        }
    
    def _generate_pdf_report(self, data: Dict[str, Any], config: ReportConfig, job_id: str) -> str:
        """Generate PDF report."""
        filename = self._generate_filename(config, job_id, "pdf")
        output_path = os.path.join(config.output_directory, filename)
        
        # Create PDF builder
        pdf_builder = PDFBuilder(output_path)
        
        # Add title and metadata
        pdf_builder.add_title(data['title'])
        pdf_builder.add_metadata(
            author="Cancer Genomics Analysis Suite",
            subject="Genomics Analysis Report",
            keywords="genomics, cancer, analysis, mutations, expression"
        )
        
        # Add summary
        if config.include_summary:
            pdf_builder.add_heading("Executive Summary")
            pdf_builder.add_paragraph(data['summary'])
        
        # Add tables
        if config.include_tables and 'tables' in data:
            for table_info in data['tables']:
                if isinstance(table_info['data'], pd.DataFrame):
                    pdf_builder.add_dataframe_table(
                        table_info['data'].head(config.max_rows_per_table),
                        table_info.get('title', 'Data Table')
                    )
        
        # Add charts
        if config.include_charts and 'charts' in data:
            for chart_info in data['charts']:
                if chart_info['type'] in config.chart_types:
                    pdf_builder.add_chart(
                        chart_info['data'],
                        chart_info['type'],
                        chart_info.get('title', 'Chart')
                    )
        
        # Add conclusions
        if 'conclusions' in data and data['conclusions']:
            pdf_builder.add_heading("Conclusions")
            for conclusion in data['conclusions']:
                pdf_builder.add_paragraph(conclusion)
        
        # Build PDF
        pdf_builder.build()
        
        self.logger.info(f"PDF report generated: {output_path}")
        return output_path
    
    def _generate_html_report(self, data: Dict[str, Any], config: ReportConfig, job_id: str) -> str:
        """Generate HTML report."""
        filename = self._generate_filename(config, job_id, "html")
        output_path = os.path.join(config.output_directory, filename)
        
        # Create HTML reporter
        html_reporter = HTMLReporter()
        
        # Set metadata
        html_reporter.set_metadata(
            title=data['title'],
            description=data['summary']
        )
        
        # Add summary section
        if config.include_summary:
            html_reporter.add_text_section("Executive Summary", data['summary'])
        
        # Add tables
        if config.include_tables and 'tables' in data:
            for table_info in data['tables']:
                if isinstance(table_info['data'], pd.DataFrame):
                    html_reporter.add_table_section(
                        table_info.get('title', 'Data Table'),
                        table_info['data'].head(config.max_rows_per_table)
                    )
        
        # Add charts
        if config.include_charts and 'charts' in data:
            for chart_info in data['charts']:
                if chart_info['type'] in config.chart_types:
                    if chart_info['type'] == 'bar':
                        fig = html_reporter.create_bar_chart(
                            chart_info['data'],
                            chart_info.get('title', 'Chart')
                        )
                    elif chart_info['type'] == 'line':
                        fig = html_reporter.create_line_chart(
                            chart_info['data'],
                            chart_info.get('title', 'Chart')
                        )
                    elif chart_info['type'] == 'scatter':
                        fig = html_reporter.create_scatter_plot(
                            chart_info['data'],
                            chart_info.get('title', 'Chart')
                        )
                    else:
                        continue
                    
                    html_reporter.add_chart_section(
                        chart_info.get('title', 'Chart'),
                        fig
                    )
        
        # Add conclusions
        if 'conclusions' in data and data['conclusions']:
            conclusions_text = '<br>'.join([f"• {c}" for c in data['conclusions']])
            html_reporter.add_text_section("Conclusions", conclusions_text)
        
        # Save report
        html_reporter.save_report(output_path)
        
        self.logger.info(f"HTML report generated: {output_path}")
        return output_path
    
    def _generate_filename(self, config: ReportConfig, job_id: str, extension: str) -> str:
        """Generate filename for report."""
        if config.filename_template:
            filename = config.filename_template.format(
                date=datetime.now().strftime('%Y%m%d'),
                type=config.report_type,
                job_id=job_id
            )
        else:
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if config.include_timestamp:
            filename += f"_{datetime.now().strftime('%H%M%S')}"
        
        return f"{filename}.{extension}"
    
    def _send_report_email(self, job: ReportJob):
        """Send report via email."""
        if not self.config.email_enabled or not self.config.email_recipients:
            return
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_config['from_email']
            msg['To'] = ', '.join(self.config.email_recipients)
            msg['Subject'] = self.config.email_subject
            
            # Add body
            body = self.config.email_body_template or f"""
            Please find attached the Cancer Genomics Analysis Report.
            
            Report ID: {job.job_id}
            Generated: {job.completed_at.strftime('%Y-%m-%d %H:%M:%S')}
            
            Best regards,
            Cancer Genomics Analysis Suite
            """
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach files
            for file_path in job.output_files:
                if os.path.exists(file_path):
                    with open(file_path, "rb") as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                    
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {os.path.basename(file_path)}'
                    )
                    msg.attach(part)
            
            # Send email
            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['username'], self.email_config['password'])
            text = msg.as_string()
            server.sendmail(self.email_config['from_email'], self.config.email_recipients, text)
            server.quit()
            
            self.logger.info(f"Report email sent for job {job.job_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to send report email: {e}")
    
    def schedule_report(self, custom_config: Optional[ReportConfig] = None):
        """Schedule report generation."""
        config = custom_config or self.config
        
        if not config.schedule_enabled:
            self.logger.warning("Scheduling is not enabled in configuration")
            return
        
        # Clear existing schedule
        schedule.clear()
        
        # Schedule based on frequency
        if config.schedule_frequency == "daily":
            schedule.every().day.at(config.schedule_time).do(
                self._scheduled_report_generation, config
            )
        elif config.schedule_frequency == "weekly":
            for day in config.schedule_days:
                getattr(schedule.every(), day.lower()).at(config.schedule_time).do(
                    self._scheduled_report_generation, config
                )
        elif config.schedule_frequency == "monthly":
            schedule.every().month.do(self._scheduled_report_generation, config)
        
        self.logger.info(f"Report scheduled: {config.schedule_frequency} at {config.schedule_time}")
    
    def _scheduled_report_generation(self, config: ReportConfig):
        """Generate report on schedule."""
        self.logger.info("Generating scheduled report...")
        job = self.generate_report(custom_config=config)
        self.logger.info(f"Scheduled report completed: {job.job_id}")
    
    def start_scheduler(self):
        """Start the report scheduler."""
        if self.scheduler_running:
            return
        
        self.scheduler_running = True
        self.logger.info("Starting report scheduler...")
        
        # Schedule reports
        self.schedule_report()
        
        # Run scheduler in separate thread
        import threading
        scheduler_thread = threading.Thread(target=self._run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
    
    def stop_scheduler(self):
        """Stop the report scheduler."""
        self.scheduler_running = False
        schedule.clear()
        self.logger.info("Report scheduler stopped")
    
    def _run_scheduler(self):
        """Run the scheduler loop."""
        while self.scheduler_running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def get_job_status(self, job_id: str) -> Optional[ReportJob]:
        """Get status of a report job."""
        return self.jobs.get(job_id)
    
    def list_jobs(self, status_filter: Optional[str] = None) -> List[ReportJob]:
        """List report jobs with optional status filter."""
        jobs = list(self.jobs.values())
        
        if status_filter:
            jobs = [job for job in jobs if job.status == status_filter]
        
        return sorted(jobs, key=lambda x: x.created_at, reverse=True)
    
    def cleanup_old_jobs(self, days: int = 30):
        """Clean up old completed jobs."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        jobs_to_remove = []
        for job_id, job in self.jobs.items():
            if (job.status in ['completed', 'failed'] and 
                job.completed_at and 
                job.completed_at < cutoff_date):
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            job = self.jobs[job_id]
            
            # Remove output files
            for file_path in job.output_files:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    self.logger.warning(f"Could not remove file {file_path}: {e}")
            
            # Remove job from memory
            del self.jobs[job_id]
        
        self.logger.info(f"Cleaned up {len(jobs_to_remove)} old jobs")
    
    def export_job_history(self, output_path: str):
        """Export job history to file."""
        job_data = []
        
        for job in self.jobs.values():
            job_data.append({
                'job_id': job.job_id,
                'status': job.status,
                'created_at': job.created_at.isoformat(),
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'output_files': job.output_files,
                'error_message': job.error_message,
                'report_type': job.config.report_type,
                'output_format': job.config.output_format
            })
        
        df = pd.DataFrame(job_data)
        df.to_csv(output_path, index=False)
        
        self.logger.info(f"Job history exported to: {output_path}")
    
    def generate_custom_report(self, template_name: str, data: Dict[str, Any], 
                              output_path: str) -> str:
        """Generate a custom report using a template."""
        try:
            # Get template
            template = self.template_utils.get_template(template_name)
            if not template:
                raise ValueError(f"Template not found: {template_name}")
            
            # Substitute variables
            html_content = self.template_utils.substitute_variables(template, data)
            
            # Save report
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"Custom report generated: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate custom report: {e}")
            raise
