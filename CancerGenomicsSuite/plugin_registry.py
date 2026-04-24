import importlib
import logging
import sys
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# List all modules that provide Dash interfaces
DASH_MODULES = [
    # Demo Module (always works)
    "modules.demo_module.demo_dash",
    
    # Core Analysis Modules
    "modules.dna_sequence_analyzer.dna_dash",
    "modules.gene_expression_plotter.expression_dash",
    "modules.mutation_predictor.mutation_dash",
    "modules.mutation_effect_predictor.predictor_dash",
    "modules.microarray_analyzer.microarray_dash",
    "modules.ml_outcome_predictor.ml_dash",
    
    # Visualization Modules
    "modules.protein_structure_visualizer.structure_dash",
    "modules.protein_sequence_viewer.sequence_dash",
    "modules.genome_browser.genome_dash",
    "modules.phylogenetic_tree_viewer.tree_dash",
    "modules.metabolic_pathway_mapper.pathway_dash",
    
    # Data Integration Modules
    "modules.multi_omics_integrator.integrator_dash",
    "modules.clinical_data_dashboard.clinical_dash",
    "modules.external_data_integrators.encode_integration",
    "modules.external_data_integrators.scopus_integration",
    "modules.external_data_integrators.checkv_integration",
    
    # Utility Modules
    "modules.sequence_search_tool.blast_dash",
    "modules.batch_processing.batch_dash",
    "modules.article_manager.manager_dash",
    "modules.article_scraper.scraper_dash",
    "modules.reporting.reporting_dash",
    "modules.notifications.alert_monitor",
    "modules.interactive_dashboards.dashboard_loader",
    
    # New Bioinformatics Tools Integration
    "modules.galaxy_integration.galaxy_dash",
    "modules.r_integration.r_dash",
    "modules.matlab_integration.matlab_dash",
    "modules.pymol_integration.pymol_dash",
    "modules.text_editors.editor_dash",
    "modules.ape_editor.ape_dash",
    "modules.igv_integration.igv_dash",
    "modules.gromacs_integration.gromacs_dash",
    "modules.wgsim_tools.wgsim_dash",
    "modules.neurosnap_integration.neurosnap_dash",
    "modules.tamarind_bio.tamarind_dash",
]

# Module metadata for better organization and display
MODULE_METADATA = {
    "modules.demo_module.demo_dash": {
        "name": "Demo Module",
        "category": "Demo",
        "description": "Demonstration module showing dashboard functionality",
        "icon": "🎯"
    },
    "modules.dna_sequence_analyzer.dna_dash": {
        "name": "DNA Sequence Analyzer",
        "category": "Core Analysis",
        "description": "Analyze DNA sequences for mutations, patterns, and annotations",
        "icon": "🧬"
    },
    "modules.gene_expression_plotter.expression_dash": {
        "name": "Gene Expression Plotter",
        "category": "Core Analysis", 
        "description": "Visualize and analyze gene expression data",
        "icon": "📊"
    },
    "modules.mutation_predictor.mutation_dash": {
        "name": "Mutation Predictor",
        "category": "Core Analysis",
        "description": "Predict and analyze genetic mutations",
        "icon": "🔬"
    },
    "modules.mutation_effect_predictor.predictor_dash": {
        "name": "Mutation Effect Predictor",
        "category": "Core Analysis",
        "description": "Predict the functional effects of mutations",
        "icon": "⚡"
    },
    "modules.microarray_analyzer.microarray_dash": {
        "name": "Microarray Analyzer",
        "category": "Core Analysis",
        "description": "Analyze microarray gene expression data",
        "icon": "🔍"
    },
    "modules.ml_outcome_predictor.ml_dash": {
        "name": "ML Outcome Predictor",
        "category": "Core Analysis",
        "description": "Machine learning models for outcome prediction",
        "icon": "🤖"
    },
    "modules.protein_structure_visualizer.structure_dash": {
        "name": "Protein Structure Visualizer",
        "category": "Visualization",
        "description": "3D visualization of protein structures",
        "icon": "🏗️"
    },
    "modules.protein_sequence_viewer.sequence_dash": {
        "name": "Protein Sequence Viewer",
        "category": "Visualization",
        "description": "View and analyze protein sequences",
        "icon": "📋"
    },
    "modules.genome_browser.genome_dash": {
        "name": "Genome Browser",
        "category": "Visualization",
        "description": "Interactive genome browser interface",
        "icon": "🌐"
    },
    "modules.phylogenetic_tree_viewer.tree_dash": {
        "name": "Phylogenetic Tree Viewer",
        "category": "Visualization",
        "description": "Visualize evolutionary relationships",
        "icon": "🌳"
    },
    "modules.metabolic_pathway_mapper.pathway_dash": {
        "name": "Metabolic Pathway Mapper",
        "category": "Visualization",
        "description": "Map and visualize metabolic pathways",
        "icon": "🛤️"
    },
    "modules.multi_omics_integrator.integrator_dash": {
        "name": "Multi-Omics Integrator",
        "category": "Data Integration",
        "description": "Integrate multiple omics data types",
        "icon": "🔗"
    },
    "modules.clinical_data_dashboard.clinical_dash": {
        "name": "Clinical Data Dashboard",
        "category": "Data Integration",
        "description": "Clinical data analysis and visualization",
        "icon": "🏥"
    },
    "modules.external_data_integrators.encode_integration": {
        "name": "ENCODE Integration",
        "category": "Data Integration",
        "description": "Integrate ENCODE database data",
        "icon": "📚"
    },
    "modules.external_data_integrators.scopus_integration": {
        "name": "Scopus Integration",
        "category": "Data Integration",
        "description": "Access Scopus research database",
        "icon": "📖"
    },
    "modules.external_data_integrators.checkv_integration": {
        "name": "CheckV Integration",
        "category": "Data Integration",
        "description": "Viral genome quality assessment",
        "icon": "🦠"
    },
    "modules.sequence_search_tool.blast_dash": {
        "name": "Sequence Search Tool",
        "category": "Utilities",
        "description": "BLAST and sequence alignment tools",
        "icon": "🔎"
    },
    "modules.batch_processing.batch_dash": {
        "name": "Batch Processing",
        "category": "Utilities",
        "description": "Process multiple files in batch",
        "icon": "⚙️"
    },
    "modules.article_manager.manager_dash": {
        "name": "Article Manager",
        "category": "Utilities",
        "description": "Manage research articles and references",
        "icon": "📄"
    },
    "modules.article_scraper.scraper_dash": {
        "name": "Article Scraper",
        "category": "Utilities",
        "description": "Scrape research articles from databases",
        "icon": "🕷️"
    },
    "modules.reporting.reporting_dash": {
        "name": "Reporting",
        "category": "Utilities",
        "description": "Generate analysis reports",
        "icon": "📊"
    },
    "modules.notifications.alert_monitor": {
        "name": "Alert Monitor",
        "category": "Utilities",
        "description": "Monitor and manage system alerts",
        "icon": "🔔"
    },
    "modules.interactive_dashboards.dashboard_loader": {
        "name": "Interactive Dashboards",
        "category": "Utilities",
        "description": "Load and manage custom dashboards",
        "icon": "📱"
    },
    
    # New Bioinformatics Tools Integration
    "modules.galaxy_integration.galaxy_dash": {
        "name": "Galaxy Integration",
        "category": "External Tools",
        "description": "Access Galaxy workflows, tools, and data analysis capabilities",
        "icon": "🌌"
    },
    "modules.r_integration.r_dash": {
        "name": "R Integration",
        "category": "Statistical Analysis",
        "description": "Execute R code, run statistical analyses, and create visualizations",
        "icon": "📊"
    },
    "modules.matlab_integration.matlab_dash": {
        "name": "MATLAB Integration",
        "category": "Numerical Computing",
        "description": "Execute MATLAB code, run numerical computations, and perform signal processing",
        "icon": "🔢"
    },
    "modules.pymol_integration.pymol_dash": {
        "name": "PyMOL Integration",
        "category": "Molecular Visualization",
        "description": "Molecular visualization, structure analysis, and protein modeling",
        "icon": "🧬"
    },
    "modules.text_editors.editor_dash": {
        "name": "Text Editors",
        "category": "Utilities",
        "description": "File editing, text processing, and editor management",
        "icon": "📝"
    },
    "modules.ape_editor.ape_dash": {
        "name": "A Plasmid Editor (APE)",
        "category": "Molecular Biology",
        "description": "Plasmid design, analysis, and visualization",
        "icon": "🧬"
    },
    "modules.igv_integration.igv_dash": {
        "name": "IGV Integration",
        "category": "Genomic Visualization",
        "description": "Genomic data visualization and analysis",
        "icon": "🧬"
    },
    "modules.gromacs_integration.gromacs_dash": {
        "name": "GROMACS Integration",
        "category": "Molecular Dynamics",
        "description": "Molecular dynamics simulations and analysis",
        "icon": "⚛️"
    },
    "modules.wgsim_tools.wgsim_dash": {
        "name": "WGSIM Tools",
        "category": "Read Simulation",
        "description": "Read simulation and variant calling tools",
        "icon": "🧬"
    },
    "modules.neurosnap_integration.neurosnap_dash": {
        "name": "Neurosnap Integration",
        "category": "Neuroscience",
        "description": "Neuroscience data analysis and processing",
        "icon": "🧠"
    },
    "modules.tamarind_bio.tamarind_dash": {
        "name": "Tamarind Bio",
        "category": "Bioinformatics Workflows",
        "description": "Bioinformatics workflows and analysis",
        "icon": "🌿"
    }
}

def get_registered_plugins() -> Dict[str, Dict[str, Any]]:
    """
    Get all registered plugins with their layouts and callbacks.
    
    Returns:
        Dict containing plugin information with keys:
        - layout: Dash layout component
        - register_callbacks: Callback registration function
        - metadata: Module metadata (name, category, description, icon)
    """
    plugins = {}
    failed_modules = []
    
    for module_path in DASH_MODULES:
        try:
            mod = importlib.import_module(module_path)
            
            # Get module metadata
            metadata = MODULE_METADATA.get(module_path, {
                "name": mod.__name__.split('.')[-2].replace("_", " ").title(),
                "category": "Other",
                "description": "Module for cancer genomics analysis",
                "icon": "🧬"
            })
            
            # Check if module has required components
            if not hasattr(mod, 'layout'):
                logger.warning(f"Module {module_path} missing 'layout' attribute")
                failed_modules.append(module_path)
                continue
            
            plugins[metadata["name"]] = {
                "layout": mod.layout,
                "register_callbacks": getattr(mod, "register_callbacks", None),
                "metadata": metadata,
                "module_path": module_path
            }
            
            logger.info(f"Successfully loaded module: {metadata['name']}")
            
        except ImportError as e:
            logger.warning(f"Could not import {module_path}: {e}")
            failed_modules.append(module_path)
            continue
        except Exception as e:
            logger.error(f"Error loading module {module_path}: {e}")
            failed_modules.append(module_path)
            continue
    
    if failed_modules:
        logger.info(f"Failed to load {len(failed_modules)} modules: {failed_modules}")
    
    logger.info(f"Successfully loaded {len(plugins)} modules")
    return plugins

def get_plugins_by_category() -> Dict[str, Dict[str, Any]]:
    """
    Get plugins organized by category.
    
    Returns:
        Dict with categories as keys and lists of plugins as values
    """
    plugins = get_registered_plugins()
    categories = {}
    
    for plugin_name, plugin_data in plugins.items():
        category = plugin_data["metadata"]["category"]
        if category not in categories:
            categories[category] = []
        categories[category].append({
            "name": plugin_name,
            "metadata": plugin_data["metadata"],
            "module_path": plugin_data["module_path"]
        })
    
    return categories

def get_plugin_info(plugin_name: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific plugin.
    
    Args:
        plugin_name: Name of the plugin
        
    Returns:
        Dict with plugin information or None if not found
    """
    plugins = get_registered_plugins()
    return plugins.get(plugin_name)

def reload_plugin(module_path: str) -> bool:
    """
    Reload a specific plugin module.
    
    Args:
        module_path: Path to the module to reload
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if module_path in sys.modules:
            importlib.reload(sys.modules[module_path])
            logger.info(f"Successfully reloaded module: {module_path}")
            return True
        else:
            logger.warning(f"Module {module_path} not found in sys.modules")
            return False
    except Exception as e:
        logger.error(f"Error reloading module {module_path}: {e}")
        return False


