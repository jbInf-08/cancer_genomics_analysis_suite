"""
Dashboard Callbacks Module

This module contains all the Dash callbacks for the Cancer Genomics Analysis Suite dashboard.
Callbacks are organized by functionality to maintain clean separation of concerns.

Modules:
- gene_expression_callbacks: Callbacks for gene expression analysis and visualization
- mutation_effect_callbacks: Callbacks for mutation effect prediction and analysis
- sequence_search_callbacks: Callbacks for sequence search and analysis tools
- reporting_callbacks: Callbacks for report generation and export functionality

Each callback module should follow these conventions:
1. Import necessary Dash components and dependencies
2. Define callback functions with proper decorators
3. Include error handling and validation
4. Document callback functionality and parameters
5. Use consistent naming conventions
"""

from .gene_expression_callbacks import *
from .mutation_effect_callbacks import *
from .sequence_search_callbacks import *
from .reporting_callbacks import *

__all__ = [
    # Gene expression callbacks
    'register_gene_expression_callbacks',
    
    # Mutation effect callbacks
    'register_mutation_effect_callbacks',
    
    # Sequence search callbacks
    'register_sequence_search_callbacks',
    
    # Reporting callbacks
    'register_reporting_callbacks',
]
