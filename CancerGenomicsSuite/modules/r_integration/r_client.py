"""
R Integration Client

Provides functionality to execute R scripts and interact with R packages
for statistical analysis and bioinformatics computations.
"""

import subprocess
import tempfile
import os
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union
import logging

logger = logging.getLogger(__name__)

# Try to import rpy2, with graceful fallback if not available
RPY2_AVAILABLE = False
robjects = None
pandas2ri = None
numpy2ri = None
importr = None
default_converter = None

try:
    import rpy2.robjects as robjects
    from rpy2.robjects import pandas2ri, numpy2ri
    from rpy2.robjects.packages import importr
    from rpy2.robjects.conversion import localconverter
    import rpy2.rinterface as rinterface
    
    # Get the default converter for use in context managers
    default_converter = robjects.default_converter
    RPY2_AVAILABLE = True
    logger.info("rpy2 successfully imported")
except ImportError as e:
    logger.warning(f"rpy2 not available: {e}. R integration will use subprocess fallback.")
except Exception as e:
    logger.warning(f"Error initializing rpy2: {e}. R integration will use subprocess fallback.")

class RClient:
    """Client for executing R code and accessing R packages"""
    
    def __init__(self):
        """Initialize R client"""
        self.rpy2_available = RPY2_AVAILABLE
        self.r = None
        self.available_packages = []
        self.packages = {}
        
        if self.rpy2_available:
            try:
                self.r = robjects.r
                self.available_packages = self._get_installed_packages()
                # Import common bioinformatics packages
                self._import_common_packages()
                logger.info("R client initialized with rpy2 support")
            except Exception as e:
                logger.warning(f"Failed to initialize rpy2: {e}. Using subprocess fallback.")
                self.rpy2_available = False
                self.r = None
        else:
            logger.info("R client initialized in subprocess-only mode (rpy2 not available)")
    
    def _get_installed_packages(self) -> List[str]:
        """Get list of installed R packages"""
        if not self.rpy2_available or self.r is None:
            return []
        try:
            installed = self.r('installed.packages()')
            return list(installed.rx(True, 1)) if installed else []
        except Exception as e:
            logger.warning(f"Could not get installed packages: {e}")
            return []
    
    def _import_common_packages(self):
        """Import commonly used bioinformatics packages"""
        self.packages = {}
        
        if not self.rpy2_available:
            logger.info("Skipping package imports: rpy2 not available")
            return
        
        # Common bioinformatics packages
        common_packages = [
            'BiocManager', 'Biobase', 'limma', 'edgeR', 'DESeq2',
            'ggplot2', 'dplyr', 'tidyr', 'stringr', 'readr',
            'pheatmap', 'VennDiagram', 'clusterProfiler', 'org.Hs.eg.db'
        ]
        
        for package in common_packages:
            try:
                self.packages[package] = importr(package)
                logger.info(f"Successfully imported R package: {package}")
            except Exception as e:
                logger.debug(f"Could not import R package {package}: {e}")
    
    def execute_r_script(self, r_code: str, return_data: bool = True) -> Dict[str, Any]:
        """
        Execute R code and return results
        
        Args:
            r_code: R code to execute
            return_data: Whether to return data objects
            
        Returns:
            Dictionary containing results and any errors
        """
        try:
            # Create temporary file for R script
            with tempfile.NamedTemporaryFile(mode='w', suffix='.R', delete=False) as f:
                f.write(r_code)
                temp_file = f.name
            
            # Execute R script
            result = subprocess.run(
                ['Rscript', temp_file],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Clean up temporary file
            os.unlink(temp_file)
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            logger.error("R script execution timed out")
            return {
                'success': False,
                'error': 'Script execution timed out',
                'stdout': '',
                'stderr': 'Timeout after 5 minutes'
            }
        except Exception as e:
            logger.error(f"Error executing R script: {e}")
            return {
                'success': False,
                'error': str(e),
                'stdout': '',
                'stderr': str(e)
            }
    
    def execute_r_code(self, r_code: str) -> Any:
        """
        Execute R code using rpy2 and return result
        
        Args:
            r_code: R code to execute
            
        Returns:
            Result from R execution
        """
        if not self.rpy2_available or self.r is None:
            # Fallback to subprocess execution
            result = self.execute_r_script(r_code)
            if result['success']:
                return result['stdout']
            else:
                raise RuntimeError(f"R execution failed: {result.get('stderr', result.get('error', 'Unknown error'))}")
        
        try:
            # Use localconverter for data conversion during execution
            with localconverter(default_converter + pandas2ri.converter + numpy2ri.converter):
                return self.r(r_code)
        except Exception as e:
            logger.error(f"Error executing R code: {e}")
            raise
    
    def install_package(self, package_name: str, source: str = "CRAN") -> bool:
        """
        Install R package
        
        Args:
            package_name: Name of package to install
            source: Source of package (CRAN, Bioconductor, GitHub)
            
        Returns:
            True if successful, False otherwise
        """
        # Use subprocess for package installation (more reliable)
        try:
            if source == "CRAN":
                r_code = f'install.packages("{package_name}", repos="https://cloud.r-project.org/")'
            elif source == "Bioconductor":
                r_code = f'''
                if (!requireNamespace("BiocManager", quietly = TRUE))
                    install.packages("BiocManager", repos="https://cloud.r-project.org/")
                BiocManager::install("{package_name}")
                '''
            elif source == "GitHub":
                r_code = f'''
                if (!requireNamespace("devtools", quietly = TRUE))
                    install.packages("devtools", repos="https://cloud.r-project.org/")
                devtools::install_github("{package_name}")
                '''
            else:
                logger.error(f"Unknown package source: {source}")
                return False
            
            result = self.execute_r_script(r_code)
            
            if result['success']:
                # Update available packages
                self.available_packages = self._get_installed_packages()
                logger.info(f"Successfully installed package {package_name} from {source}")
                return True
            else:
                logger.error(f"Failed to install package {package_name}: {result.get('stderr', '')}")
                return False
            
        except Exception as e:
            logger.error(f"Error installing package {package_name}: {e}")
            return False
    
    def load_data(self, data: Union[pd.DataFrame, np.ndarray, List], name: str = "data") -> bool:
        """
        Load Python data into R environment
        
        Args:
            data: Python data structure to load
            name: Variable name in R
            
        Returns:
            True if successful, False otherwise
        """
        if not self.rpy2_available:
            logger.warning("Cannot load data to R: rpy2 not available")
            return False
            
        try:
            # Use localconverter context manager for modern rpy2 API
            with localconverter(default_converter + pandas2ri.converter + numpy2ri.converter):
                if isinstance(data, pd.DataFrame):
                    robjects.globalenv[name] = pandas2ri.py2rpy(data)
                elif isinstance(data, np.ndarray):
                    robjects.globalenv[name] = numpy2ri.numpy2rpy(data)
                elif isinstance(data, list):
                    robjects.globalenv[name] = robjects.StrVector(data)
                else:
                    robjects.globalenv[name] = data
            
            return True
        except Exception as e:
            logger.error(f"Error loading data to R: {e}")
            return False
    
    def get_data(self, name: str) -> Any:
        """
        Get data from R environment
        
        Args:
            name: Variable name in R
            
        Returns:
            Data from R environment (converted to pandas DataFrame if applicable)
        """
        if not self.rpy2_available:
            logger.warning("Cannot get data from R: rpy2 not available")
            return None
            
        try:
            with localconverter(default_converter + pandas2ri.converter + numpy2ri.converter):
                r_obj = robjects.globalenv[name]
                # Try to convert to pandas DataFrame if it's a data.frame
                try:
                    return pandas2ri.rpy2py(r_obj)
                except:
                    return r_obj
        except Exception as e:
            logger.error(f"Error getting data from R: {e}")
            return None
    
    def create_plot(self, plot_code: str, output_file: Optional[str] = None) -> str:
        """
        Create plot using R and return base64 encoded image
        
        Args:
            plot_code: R code to create plot
            output_file: Optional output file path
            
        Returns:
            Base64 encoded image or file path
        """
        import base64
        
        try:
            # Use subprocess for plotting (more reliable across environments)
            if output_file:
                temp_file = output_file
            else:
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                    temp_file = f.name
            
            # Wrap plot code with PNG device
            full_code = f'''
            png("{temp_file.replace(os.sep, '/')}", width=800, height=600)
            {plot_code}
            dev.off()
            '''
            
            result = self.execute_r_script(full_code)
            
            if not result['success']:
                logger.error(f"Plot creation failed: {result.get('stderr', '')}")
                return ""
            
            if output_file:
                return output_file
            else:
                # Read file and convert to base64
                with open(temp_file, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode()
                
                os.unlink(temp_file)
                return f"data:image/png;base64,{image_data}"
                
        except Exception as e:
            logger.error(f"Error creating plot: {e}")
            return ""
    
    def run_deseq2_analysis(self, count_data: pd.DataFrame, 
                           metadata: pd.DataFrame,
                           design_formula: str = "~ condition") -> Dict[str, Any]:
        """
        Run DESeq2 differential expression analysis
        
        Args:
            count_data: Count matrix (genes x samples)
            metadata: Sample metadata
            design_formula: Design formula for DESeq2
            
        Returns:
            Dictionary containing DESeq2 results
        """
        try:
            # Load data into R
            self.load_data(count_data, "count_data")
            self.load_data(metadata, "metadata")
            
            # Run DESeq2 analysis
            deseq2_code = f"""
            library(DESeq2)
            
            # Create DESeqDataSet
            dds <- DESeqDataSetFromMatrix(countData = count_data,
                                        colData = metadata,
                                        design = as.formula("{design_formula}"))
            
            # Run DESeq2
            dds <- DESeq(dds)
            
            # Get results
            res <- results(dds)
            res_df <- as.data.frame(res)
            
            # Return results
            res_df
            """
            
            result = self.execute_r_code(deseq2_code)
            return {
                'success': True,
                'results': result,
                'message': 'DESeq2 analysis completed successfully'
            }
            
        except Exception as e:
            logger.error(f"Error running DESeq2 analysis: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'DESeq2 analysis failed'
            }
    
    def run_limma_analysis(self, expression_data: pd.DataFrame,
                          metadata: pd.DataFrame,
                          design_matrix: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Run limma differential expression analysis
        
        Args:
            expression_data: Expression matrix (genes x samples)
            metadata: Sample metadata
            design_matrix: Optional design matrix
            
        Returns:
            Dictionary containing limma results
        """
        try:
            # Load data into R
            self.load_data(expression_data, "expression_data")
            self.load_data(metadata, "metadata")
            
            if design_matrix is not None:
                self.load_data(design_matrix, "design_matrix")
            
            # Run limma analysis
            limma_code = """
            library(limma)
            
            # Create design matrix if not provided
            if (!exists("design_matrix")) {
                design_matrix <- model.matrix(~ condition, data = metadata)
            }
            
            # Fit linear model
            fit <- lmFit(expression_data, design_matrix)
            fit <- eBayes(fit)
            
            # Get results
            results <- topTable(fit, number = Inf)
            
            # Return results
            results
            """
            
            result = self.execute_r_code(limma_code)
            return {
                'success': True,
                'results': result,
                'message': 'Limma analysis completed successfully'
            }
            
        except Exception as e:
            logger.error(f"Error running limma analysis: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Limma analysis failed'
            }
    
    def create_heatmap(self, data: pd.DataFrame, 
                      title: str = "Heatmap",
                      clustering: bool = True) -> str:
        """
        Create heatmap using R
        
        Args:
            data: Data matrix for heatmap
            title: Plot title
            clustering: Whether to perform clustering
            
        Returns:
            Base64 encoded image
        """
        try:
            self.load_data(data, "heatmap_data")
            
            plot_code = f"""
            library(pheatmap)
            
            # Create heatmap
            pheatmap(heatmap_data,
                    main = "{title}",
                    cluster_rows = {str(clustering).lower()},
                    cluster_cols = {str(clustering).lower()},
                    scale = "row",
                    color = colorRampPalette(c("blue", "white", "red"))(100))
            """
            
            return self.create_plot(plot_code)
            
        except Exception as e:
            logger.error(f"Error creating heatmap: {e}")
            return ""
    
    def run_go_enrichment(self, gene_list: List[str], 
                         organism: str = "org.Hs.eg.db",
                         pvalue_cutoff: float = 0.05) -> Dict[str, Any]:
        """
        Run GO enrichment analysis
        
        Args:
            gene_list: List of gene symbols
            organism: Organism database
            pvalue_cutoff: P-value cutoff for significance
            
        Returns:
            Dictionary containing GO enrichment results
        """
        try:
            self.load_data(gene_list, "gene_list")
            
            go_code = f"""
            library(clusterProfiler)
            library({organism})
            
            # Convert gene symbols to ENTREZ IDs
            gene_ids <- bitr(gene_list, fromType = "SYMBOL", 
                           toType = "ENTREZID", 
                           OrgDb = {organism})
            
            # Run GO enrichment
            go_results <- enrichGO(gene = gene_ids$ENTREZID,
                                 OrgDb = {organism},
                                 ont = "ALL",
                                 pAdjustMethod = "BH",
                                 pvalueCutoff = {pvalue_cutoff},
                                 qvalueCutoff = 0.2,
                                 readable = TRUE)
            
            # Convert to data frame
            go_df <- as.data.frame(go_results)
            
            # Return results
            go_df
            """
            
            result = self.execute_r_code(go_code)
            return {
                'success': True,
                'results': result,
                'message': 'GO enrichment analysis completed successfully'
            }
            
        except Exception as e:
            logger.error(f"Error running GO enrichment: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'GO enrichment analysis failed'
            }
    
    def get_r_status(self) -> Dict[str, Any]:
        """
        Get the current status of R integration
        
        Returns:
            Dictionary containing R environment status
        """
        status = {
            'rpy2_available': self.rpy2_available,
            'r_version': None,
            'rscript_available': False,
            'installed_packages_count': len(self.available_packages),
            'loaded_packages': list(self.packages.keys()),
            'mode': 'rpy2' if self.rpy2_available else 'subprocess'
        }
        
        # Check Rscript availability
        try:
            result = subprocess.run(['Rscript', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            status['rscript_available'] = True
            # Parse R version from output
            version_output = result.stderr or result.stdout
            if version_output:
                status['r_version'] = version_output.strip().split('\n')[0]
        except Exception as e:
            logger.debug(f"Rscript not available: {e}")
        
        return status
    
    def check_package_installed(self, package_name: str) -> bool:
        """
        Check if an R package is installed
        
        Args:
            package_name: Name of the package to check
            
        Returns:
            True if installed, False otherwise
        """
        if package_name in self.available_packages:
            return True
        
        # Try checking via Rscript
        try:
            r_code = f'cat(requireNamespace("{package_name}", quietly = TRUE))'
            result = self.execute_r_script(r_code)
            return result['success'] and 'TRUE' in result['stdout']
        except Exception:
            return False
    
    def get_required_packages(self) -> List[str]:
        """
        Get list of required R packages for cancer genomics analysis
        
        Returns:
            List of required package names
        """
        return [
            # Core Bioconductor packages
            'BiocManager', 'Biobase', 'BiocGenerics', 'S4Vectors',
            # Differential expression
            'DESeq2', 'limma', 'edgeR',
            # Data manipulation
            'dplyr', 'tidyr', 'tibble', 'readr', 'stringr',
            # Visualization  
            'ggplot2', 'pheatmap', 'ComplexHeatmap', 'VennDiagram',
            # Enrichment analysis
            'clusterProfiler', 'enrichplot', 'org.Hs.eg.db', 'DOSE',
            # Survival analysis
            'survival', 'survminer',
            # Gene set analysis
            'fgsea', 'msigdbr',
        ]
    
    def install_required_packages(self, skip_installed: bool = True) -> Dict[str, bool]:
        """
        Install all required R packages for cancer genomics analysis
        
        Args:
            skip_installed: Skip packages that are already installed
            
        Returns:
            Dictionary mapping package names to installation success
        """
        results = {}
        required = self.get_required_packages()
        
        for package in required:
            if skip_installed and self.check_package_installed(package):
                results[package] = True
                logger.info(f"Package {package} already installed, skipping")
                continue
            
            # Determine source (Bioconductor or CRAN)
            bioc_packages = [
                'BiocManager', 'Biobase', 'BiocGenerics', 'S4Vectors',
                'DESeq2', 'limma', 'edgeR', 'clusterProfiler', 'enrichplot',
                'org.Hs.eg.db', 'DOSE', 'ComplexHeatmap', 'fgsea'
            ]
            
            source = 'Bioconductor' if package in bioc_packages else 'CRAN'
            results[package] = self.install_package(package, source)
        
        return results
