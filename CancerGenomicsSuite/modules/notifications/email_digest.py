"""
Email Digest Module

Handles email notifications and digest creation for the Cancer Genomics Analysis Suite.
Supports both individual notifications and periodic digest emails.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class EmailDigest:
    """
    Handles email notifications and digest creation.
    
    Features:
    - Individual email notifications
    - Periodic digest emails
    - HTML and plain text support
    - Attachment support
    - Template-based email generation
    """
    
    def __init__(self, smtp_server: str = None, smtp_port: int = 587, 
                 username: str = None, password: str = None):
        """
        Initialize EmailDigest with SMTP configuration.
        
        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP server port
            username: Email username
            password: Email password
        """
        self.smtp_server = smtp_server or os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = smtp_port or int(os.getenv('SMTP_PORT', '587'))
        self.username = username or os.getenv('EMAIL_USERNAME')
        self.password = password or os.getenv('EMAIL_PASSWORD')
        
        # Email templates directory
        self.templates_dir = Path(__file__).parent / 'templates'
        self.templates_dir.mkdir(exist_ok=True)
        
        # Initialize default templates
        self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default email templates if they don't exist."""
        # Analysis completion template
        analysis_template = """
        <html>
        <body>
            <h2>Analysis Complete</h2>
            <p>Your cancer genomics analysis has been completed successfully.</p>
            <h3>Analysis Details:</h3>
            <ul>
                <li><strong>Analysis ID:</strong> {analysis_id}</li>
                <li><strong>Type:</strong> {analysis_type}</li>
                <li><strong>Completed:</strong> {completion_time}</li>
                <li><strong>Results:</strong> {results_summary}</li>
            </ul>
            <p>You can view the full results in the dashboard.</p>
            <p>Best regards,<br>Cancer Genomics Analysis Suite</p>
        </body>
        </html>
        """
        
        # Error notification template
        error_template = """
        <html>
        <body>
            <h2>Analysis Error</h2>
            <p>An error occurred during your cancer genomics analysis.</p>
            <h3>Error Details:</h3>
            <ul>
                <li><strong>Analysis ID:</strong> {analysis_id}</li>
                <li><strong>Error:</strong> {error_message}</li>
                <li><strong>Time:</strong> {error_time}</li>
            </ul>
            <p>Please check the analysis logs for more details.</p>
            <p>Best regards,<br>Cancer Genomics Analysis Suite</p>
        </body>
        </html>
        """
        
        # Daily digest template
        digest_template = """
        <html>
        <body>
            <h2>Daily Analysis Digest</h2>
            <p>Here's a summary of your cancer genomics analyses for {date}:</p>
            
            <h3>Completed Analyses ({completed_count})</h3>
            {completed_analyses}
            
            <h3>Failed Analyses ({failed_count})</h3>
            {failed_analyses}
            
            <h3>System Status</h3>
            <ul>
                <li><strong>Queue Status:</strong> {queue_status}</li>
                <li><strong>Active Workers:</strong> {active_workers}</li>
            </ul>
            
            <p>Best regards,<br>Cancer Genomics Analysis Suite</p>
        </body>
        </html>
        """
        
        # Save templates
        templates = {
            'analysis_complete.html': analysis_template,
            'error_notification.html': error_template,
            'daily_digest.html': digest_template
        }
        
        for filename, content in templates.items():
            template_path = self.templates_dir / filename
            if not template_path.exists():
                template_path.write_text(content.strip())
    
    def send_email(self, to_addresses: List[str], subject: str, 
                   body: str, is_html: bool = True, 
                   attachments: List[str] = None) -> bool:
        """
        Send an email notification.
        
        Args:
            to_addresses: List of recipient email addresses
            subject: Email subject
            body: Email body content
            is_html: Whether body is HTML format
            attachments: List of file paths to attach
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.username
            msg['To'] = ', '.join(to_addresses)
            msg['Subject'] = subject
            
            # Add body
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Add attachments
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {os.path.basename(file_path)}'
                            )
                            msg.attach(part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_addresses}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
    
    def send_analysis_completion_notification(self, to_addresses: List[str], 
                                            analysis_id: str, analysis_type: str,
                                            results_summary: str) -> bool:
        """
        Send analysis completion notification.
        
        Args:
            to_addresses: List of recipient email addresses
            analysis_id: Unique analysis identifier
            analysis_type: Type of analysis performed
            results_summary: Summary of results
            
        Returns:
            bool: True if notification sent successfully
        """
        template_path = self.templates_dir / 'analysis_complete.html'
        template = template_path.read_text()
        
        body = template.format(
            analysis_id=analysis_id,
            analysis_type=analysis_type,
            completion_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            results_summary=results_summary
        )
        
        subject = f"Analysis Complete: {analysis_type} - {analysis_id}"
        return self.send_email(to_addresses, subject, body)
    
    def send_error_notification(self, to_addresses: List[str], 
                              analysis_id: str, error_message: str) -> bool:
        """
        Send error notification.
        
        Args:
            to_addresses: List of recipient email addresses
            analysis_id: Analysis identifier where error occurred
            error_message: Error message details
            
        Returns:
            bool: True if notification sent successfully
        """
        template_path = self.templates_dir / 'error_notification.html'
        template = template_path.read_text()
        
        body = template.format(
            analysis_id=analysis_id,
            error_message=error_message,
            error_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        subject = f"Analysis Error: {analysis_id}"
        return self.send_email(to_addresses, subject, body)
    
    def create_daily_digest(self, completed_analyses: List[Dict], 
                          failed_analyses: List[Dict],
                          queue_status: str, active_workers: int) -> str:
        """
        Create daily digest email content.
        
        Args:
            completed_analyses: List of completed analysis data
            failed_analyses: List of failed analysis data
            queue_status: Current queue status
            active_workers: Number of active workers
            
        Returns:
            str: HTML content for digest email
        """
        template_path = self.templates_dir / 'daily_digest.html'
        template = template_path.read_text()
        
        # Format completed analyses
        completed_html = ""
        for analysis in completed_analyses:
            completed_html += f"""
            <li><strong>{analysis.get('type', 'Unknown')}</strong> - 
                {analysis.get('id', 'Unknown ID')} 
                ({analysis.get('completion_time', 'Unknown time')})</li>
            """
        
        # Format failed analyses
        failed_html = ""
        for analysis in failed_analyses:
            failed_html += f"""
            <li><strong>{analysis.get('type', 'Unknown')}</strong> - 
                {analysis.get('id', 'Unknown ID')} 
                ({analysis.get('error', 'Unknown error')})</li>
            """
        
        body = template.format(
            date=datetime.now().strftime('%Y-%m-%d'),
            completed_count=len(completed_analyses),
            completed_analyses=completed_html or "<li>No completed analyses</li>",
            failed_count=len(failed_analyses),
            failed_analyses=failed_html or "<li>No failed analyses</li>",
            queue_status=queue_status,
            active_workers=active_workers
        )
        
        return body
    
    def send_daily_digest(self, to_addresses: List[str], 
                         completed_analyses: List[Dict],
                         failed_analyses: List[Dict],
                         queue_status: str, active_workers: int) -> bool:
        """
        Send daily digest email.
        
        Args:
            to_addresses: List of recipient email addresses
            completed_analyses: List of completed analysis data
            failed_analyses: List of failed analysis data
            queue_status: Current queue status
            active_workers: Number of active workers
            
        Returns:
            bool: True if digest sent successfully
        """
        body = self.create_daily_digest(
            completed_analyses, failed_analyses, 
            queue_status, active_workers
        )
        
        subject = f"Daily Analysis Digest - {datetime.now().strftime('%Y-%m-%d')}"
        return self.send_email(to_addresses, subject, body)
    
    def test_email_configuration(self, test_address: str) -> bool:
        """
        Test email configuration by sending a test email.
        
        Args:
            test_address: Email address to send test to
            
        Returns:
            bool: True if test email sent successfully
        """
        test_body = """
        <html>
        <body>
            <h2>Email Configuration Test</h2>
            <p>This is a test email to verify the email configuration 
            for the Cancer Genomics Analysis Suite.</p>
            <p>If you receive this email, the configuration is working correctly.</p>
            <p>Test time: {}</p>
        </body>
        </html>
        """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        subject = "Email Configuration Test - Cancer Genomics Suite"
        return self.send_email([test_address], subject, test_body)
