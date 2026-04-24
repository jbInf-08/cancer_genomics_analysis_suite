"""
Template Utilities Module

This module provides utilities for managing and formatting templates used in
report generation, including template loading, variable substitution, and
formatting helpers.
"""

import os
import re
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import pandas as pd
from pathlib import Path


class TemplateUtils:
    """
    Utility class for template management and formatting operations.
    
    This class provides methods for loading templates, performing variable
    substitution, formatting data, and managing template resources.
    """
    
    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize the template utilities.
        
        Args:
            template_dir (str, optional): Directory containing templates
        """
        self.template_dir = template_dir or os.path.join(os.path.dirname(__file__), 'templates')
        self.templates = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load all templates from the template directory."""
        if not os.path.exists(self.template_dir):
            os.makedirs(self.template_dir, exist_ok=True)
            return
        
        for file_path in Path(self.template_dir).glob('*.html'):
            template_name = file_path.stem
            with open(file_path, 'r', encoding='utf-8') as f:
                self.templates[template_name] = f.read()
    
    def get_template(self, template_name: str) -> Optional[str]:
        """
        Get a template by name.
        
        Args:
            template_name (str): Name of the template
            
        Returns:
            str: Template content or None if not found
        """
        return self.templates.get(template_name)
    
    def set_template(self, template_name: str, content: str):
        """
        Set or update a template.
        
        Args:
            template_name (str): Name of the template
            content (str): Template content
        """
        self.templates[template_name] = content
    
    def save_template(self, template_name: str, content: str):
        """
        Save a template to disk.
        
        Args:
            template_name (str): Name of the template
            content (str): Template content
        """
        template_path = os.path.join(self.template_dir, f"{template_name}.html")
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Update in-memory templates
        self.templates[template_name] = content
    
    def substitute_variables(self, template: str, variables: Dict[str, Any]) -> str:
        """
        Substitute variables in a template using {{ variable }} syntax.
        
        Args:
            template (str): Template content
            variables (Dict[str, Any]): Variables to substitute
            
        Returns:
            str: Template with substituted variables
        """
        def replace_var(match):
            var_name = match.group(1).strip()
            if var_name in variables:
                value = variables[var_name]
                if isinstance(value, (list, dict)):
                    return json.dumps(value)
                return str(value)
            return match.group(0)  # Return original if variable not found
        
        # Replace {{ variable }} patterns
        result = re.sub(r'\{\{\s*([^}]+)\s*\}\}', replace_var, template)
        
        # Replace {% if condition %} ... {% endif %} blocks
        result = self._process_conditionals(result, variables)
        
        # Replace {% for item in list %} ... {% endfor %} blocks
        result = self._process_loops(result, variables)
        
        return result
    
    def _process_conditionals(self, template: str, variables: Dict[str, Any]) -> str:
        """
        Process conditional blocks in template.
        
        Args:
            template (str): Template content
            variables (Dict[str, Any]): Variables for evaluation
            
        Returns:
            str: Template with processed conditionals
        """
        def evaluate_condition(condition: str) -> bool:
            """Evaluate a condition string."""
            try:
                # Simple condition evaluation
                if '==' in condition:
                    left, right = condition.split('==', 1)
                    left = left.strip()
                    right = right.strip().strip('"\'')
                    return str(variables.get(left, '')) == right
                elif '!=' in condition:
                    left, right = condition.split('!=', 1)
                    left = left.strip()
                    right = right.strip().strip('"\'')
                    return str(variables.get(left, '')) != right
                elif 'in' in condition:
                    var_name, list_name = condition.split('in', 1)
                    var_name = var_name.strip()
                    list_name = list_name.strip()
                    return variables.get(var_name) in variables.get(list_name, [])
                else:
                    # Simple truthiness check
                    return bool(variables.get(condition.strip()))
            except:
                return False
        
        # Process {% if condition %} ... {% endif %} blocks
        pattern = r'\{%\s*if\s+([^%]+)\s*%\}(.*?)\{%\s*endif\s*%\}'
        
        def replace_conditional(match):
            condition = match.group(1)
            content = match.group(2)
            
            if evaluate_condition(condition):
                return content
            return ''
        
        return re.sub(pattern, replace_conditional, template, flags=re.DOTALL)
    
    def _process_loops(self, template: str, variables: Dict[str, Any]) -> str:
        """
        Process loop blocks in template.
        
        Args:
            template (str): Template content
            variables (Dict[str, Any]): Variables for evaluation
            
        Returns:
            str: Template with processed loops
        """
        # Process {% for item in list %} ... {% endfor %} blocks
        pattern = r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}(.*?)\{%\s*endfor\s*%\}'
        
        def replace_loop(match):
            item_var = match.group(1)
            list_var = match.group(2)
            content = match.group(3)
            
            items = variables.get(list_var, [])
            if not isinstance(items, (list, tuple)):
                return ''
            
            result = ''
            for i, item in enumerate(items):
                loop_vars = {
                    **variables,
                    item_var: item,
                    'loop': {
                        'index': i + 1,
                        'index0': i,
                        'first': i == 0,
                        'last': i == len(items) - 1,
                        'length': len(items)
                    }
                }
                result += self.substitute_variables(content, loop_vars)
            
            return result
        
        return re.sub(pattern, replace_loop, template, flags=re.DOTALL)
    
    def format_number(self, value: Union[int, float], precision: int = 2, 
                     use_thousands_separator: bool = True) -> str:
        """
        Format a number for display.
        
        Args:
            value (Union[int, float]): Number to format
            precision (int): Decimal precision
            use_thousands_separator (bool): Whether to use thousands separator
            
        Returns:
            str: Formatted number string
        """
        if isinstance(value, (int, float)):
            if use_thousands_separator:
                return f"{value:,.{precision}f}"
            else:
                return f"{value:.{precision}f}"
        return str(value)
    
    def format_percentage(self, value: Union[int, float], precision: int = 1) -> str:
        """
        Format a number as a percentage.
        
        Args:
            value (Union[int, float]): Number to format (0-1 or 0-100)
            precision (int): Decimal precision
            
        Returns:
            str: Formatted percentage string
        """
        if isinstance(value, (int, float)):
            # Assume value is between 0-1 if less than 1, otherwise 0-100
            if value <= 1:
                value *= 100
            return f"{value:.{precision}f}%"
        return str(value)
    
    def format_currency(self, value: Union[int, float], currency: str = "$") -> str:
        """
        Format a number as currency.
        
        Args:
            value (Union[int, float]): Number to format
            currency (str): Currency symbol
            
        Returns:
            str: Formatted currency string
        """
        if isinstance(value, (int, float)):
            return f"{currency}{value:,.2f}"
        return str(value)
    
    def format_date(self, date_value: Union[str, datetime], 
                   format_string: str = "%Y-%m-%d") -> str:
        """
        Format a date for display.
        
        Args:
            date_value (Union[str, datetime]): Date to format
            format_string (str): Date format string
            
        Returns:
            str: Formatted date string
        """
        if isinstance(date_value, str):
            try:
                date_value = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            except:
                return date_value
        
        if isinstance(date_value, datetime):
            return date_value.strftime(format_string)
        
        return str(date_value)
    
    def format_dataframe(self, df: pd.DataFrame, 
                        max_rows: int = 1000,
                        max_cols: int = 20) -> pd.DataFrame:
        """
        Format a DataFrame for display in reports.
        
        Args:
            df (pd.DataFrame): DataFrame to format
            max_rows (int): Maximum number of rows to display
            max_cols (int): Maximum number of columns to display
            
        Returns:
            pd.DataFrame: Formatted DataFrame
        """
        # Limit rows and columns
        if len(df) > max_rows:
            df = df.head(max_rows)
        
        if len(df.columns) > max_cols:
            df = df.iloc[:, :max_cols]
        
        # Format numeric columns
        for col in df.select_dtypes(include=['float64', 'int64']).columns:
            if df[col].dtype == 'float64':
                df[col] = df[col].round(3)
        
        return df
    
    def create_table_html(self, df: pd.DataFrame, 
                         table_id: str = "data_table",
                         css_classes: str = "table table-striped table-hover",
                         include_index: bool = False) -> str:
        """
        Create HTML table from DataFrame.
        
        Args:
            df (pd.DataFrame): DataFrame to convert
            table_id (str): HTML id for the table
            css_classes (str): CSS classes for the table
            include_index (bool): Whether to include DataFrame index
            
        Returns:
            str: HTML table string
        """
        return df.to_html(
            table_id=table_id,
            classes=css_classes,
            index=include_index,
            escape=False
        )
    
    def create_summary_stats(self, data: Union[List, pd.Series, pd.DataFrame]) -> Dict[str, Any]:
        """
        Create summary statistics for data.
        
        Args:
            data (Union[List, pd.Series, pd.DataFrame]): Data to summarize
            
        Returns:
            Dict[str, Any]: Summary statistics
        """
        if isinstance(data, pd.DataFrame):
            return {
                'shape': data.shape,
                'columns': list(data.columns),
                'dtypes': data.dtypes.to_dict(),
                'missing_values': data.isnull().sum().to_dict(),
                'numeric_summary': data.describe().to_dict() if len(data.select_dtypes(include=['number']).columns) > 0 else {}
            }
        elif isinstance(data, pd.Series):
            return {
                'count': len(data),
                'dtype': str(data.dtype),
                'missing_values': data.isnull().sum(),
                'unique_values': data.nunique(),
                'summary': data.describe().to_dict() if data.dtype in ['int64', 'float64'] else {}
            }
        elif isinstance(data, list):
            return {
                'count': len(data),
                'unique_values': len(set(data)),
                'type': type(data[0]).__name__ if data else 'empty'
            }
        else:
            return {'error': 'Unsupported data type'}
    
    def validate_template(self, template: str) -> Dict[str, Any]:
        """
        Validate a template for syntax errors.
        
        Args:
            template (str): Template content to validate
            
        Returns:
            Dict[str, Any]: Validation results
        """
        errors = []
        warnings = []
        
        # Check for unmatched braces
        open_braces = template.count('{{')
        close_braces = template.count('}}')
        if open_braces != close_braces:
            errors.append(f"Unmatched variable braces: {open_braces} open, {close_braces} close")
        
        # Check for unmatched if/endif
        if_blocks = len(re.findall(r'\{%\s*if\s+[^%]+\s*%\}', template))
        endif_blocks = len(re.findall(r'\{%\s*endif\s*%\}', template))
        if if_blocks != endif_blocks:
            errors.append(f"Unmatched if/endif blocks: {if_blocks} if, {endif_blocks} endif")
        
        # Check for unmatched for/endfor
        for_blocks = len(re.findall(r'\{%\s*for\s+[^%]+\s*%\}', template))
        endfor_blocks = len(re.findall(r'\{%\s*endfor\s*%\}', template))
        if for_blocks != endfor_blocks:
            errors.append(f"Unmatched for/endfor blocks: {for_blocks} for, {endfor_blocks} endfor")
        
        # Check for undefined variables (warnings only)
        variables = re.findall(r'\{\{\s*([^}]+)\s*\}\}', template)
        for var in variables:
            var = var.strip()
            if '.' in var or '[' in var:
                warnings.append(f"Complex variable reference: {var}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'variable_count': len(set(variables))
        }
    
    def get_default_templates(self) -> Dict[str, str]:
        """
        Get default template content.
        
        Returns:
            Dict[str, str]: Dictionary of default templates
        """
        return {
            'simple_report': """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        .section { margin: 20px 0; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    <p>Generated on: {{ date }}</p>
    
    {% for section in sections %}
    <div class="section">
        <h2>{{ section.title }}</h2>
        {{ section.content }}
    </div>
    {% endfor %}
</body>
</html>
            """,
            
            'data_table': """
<div class="table-container">
    <h3>{{ table_title }}</h3>
    <table class="data-table">
        <thead>
            <tr>
                {% for header in headers %}
                <th>{{ header }}</th>
                {% endfor %}
            </tr>
        </thead>
        <tbody>
            {% for row in rows %}
            <tr>
                {% for cell in row %}
                <td>{{ cell }}</td>
                {% endfor %}
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
            """
        }
