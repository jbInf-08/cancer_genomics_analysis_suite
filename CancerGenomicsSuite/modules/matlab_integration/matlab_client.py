"""
MATLAB Integration Client

Provides functionality to execute MATLAB code and interact with MATLAB
for numerical computing and signal processing operations.
"""

import subprocess
import tempfile
import os
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Union
import logging
import matlab.engine
import matlab

logger = logging.getLogger(__name__)

class MATLABClient:
    """Client for executing MATLAB code and accessing MATLAB functions"""
    
    def __init__(self):
        """Initialize MATLAB client"""
        self.engine = None
        self.available_toolboxes = []
        self._initialize_matlab()
    
    def _initialize_matlab(self):
        """Initialize MATLAB engine"""
        try:
            # Start MATLAB engine
            self.engine = matlab.engine.start_matlab()
            logger.info("MATLAB engine started successfully")
            
            # Get available toolboxes
            self.available_toolboxes = self._get_available_toolboxes()
            
        except Exception as e:
            logger.error(f"Failed to initialize MATLAB engine: {e}")
            self.engine = None
    
    def _get_available_toolboxes(self) -> List[str]:
        """Get list of available MATLAB toolboxes"""
        try:
            if self.engine is None:
                return []
            
            # Get toolbox information
            result = self.engine.ver()
            toolboxes = []
            
            for toolbox in result:
                toolboxes.append(toolbox['Name'])
            
            return toolboxes
            
        except Exception as e:
            logger.error(f"Error getting MATLAB toolboxes: {e}")
            return []
    
    def execute_matlab_script(self, matlab_code: str, return_data: bool = True) -> Dict[str, Any]:
        """
        Execute MATLAB code and return results
        
        Args:
            matlab_code: MATLAB code to execute
            return_data: Whether to return data objects
            
        Returns:
            Dictionary containing results and any errors
        """
        if self.engine is None:
            return {
                'success': False,
                'error': 'MATLAB engine not available',
                'output': '',
                'error_output': 'MATLAB engine not initialized'
            }
        
        try:
            # Create temporary file for MATLAB script
            with tempfile.NamedTemporaryFile(mode='w', suffix='.m', delete=False) as f:
                f.write(matlab_code)
                temp_file = f.name
            
            # Execute MATLAB script
            result = subprocess.run(
                ['matlab', '-batch', f"run('{temp_file}')"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Clean up temporary file
            os.unlink(temp_file)
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error_output': result.stderr,
                'returncode': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            logger.error("MATLAB script execution timed out")
            return {
                'success': False,
                'error': 'Script execution timed out',
                'output': '',
                'error_output': 'Timeout after 5 minutes'
            }
        except Exception as e:
            logger.error(f"Error executing MATLAB script: {e}")
            return {
                'success': False,
                'error': str(e),
                'output': '',
                'error_output': str(e)
            }
    
    def execute_matlab_code(self, matlab_code: str) -> Any:
        """
        Execute MATLAB code using MATLAB engine and return result
        
        Args:
            matlab_code: MATLAB code to execute
            
        Returns:
            Result from MATLAB execution
        """
        if self.engine is None:
            raise RuntimeError("MATLAB engine not available")
        
        try:
            return self.engine.eval(matlab_code)
        except Exception as e:
            logger.error(f"Error executing MATLAB code: {e}")
            raise
    
    def load_data(self, data: Union[np.ndarray, pd.DataFrame, List], name: str = "data") -> bool:
        """
        Load Python data into MATLAB workspace
        
        Args:
            data: Python data structure to load
            name: Variable name in MATLAB
            
        Returns:
            True if successful, False otherwise
        """
        if self.engine is None:
            return False
        
        try:
            if isinstance(data, pd.DataFrame):
                # Convert DataFrame to MATLAB struct
                matlab_data = {}
                for col in data.columns:
                    matlab_data[col] = matlab.double(data[col].values.tolist())
                self.engine.workspace[name] = matlab_data
            elif isinstance(data, np.ndarray):
                # Convert numpy array to MATLAB array
                matlab_array = matlab.double(data.tolist())
                self.engine.workspace[name] = matlab_array
            elif isinstance(data, list):
                # Convert list to MATLAB cell array
                matlab_list = matlab.cell(data)
                self.engine.workspace[name] = matlab_list
            else:
                # Try direct conversion
                self.engine.workspace[name] = data
            
            return True
        except Exception as e:
            logger.error(f"Error loading data to MATLAB: {e}")
            return False
    
    def get_data(self, name: str) -> Any:
        """
        Get data from MATLAB workspace
        
        Args:
            name: Variable name in MATLAB
            
        Returns:
            Data from MATLAB workspace
        """
        if self.engine is None:
            return None
        
        try:
            return self.engine.workspace[name]
        except Exception as e:
            logger.error(f"Error getting data from MATLAB: {e}")
            return None
    
    def create_plot(self, plot_code: str, output_file: Optional[str] = None) -> str:
        """
        Create plot using MATLAB and return base64 encoded image
        
        Args:
            plot_code: MATLAB code to create plot
            output_file: Optional output file path
            
        Returns:
            Base64 encoded image or file path
        """
        if self.engine is None:
            return ""
        
        try:
            if output_file:
                # Save plot to file
                full_code = f"{plot_code}\nsaveas(gcf, '{output_file}');"
                self.engine.eval(full_code)
                return output_file
            else:
                # Create temporary file
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                    temp_file = f.name
                
                full_code = f"{plot_code}\nsaveas(gcf, '{temp_file}');"
                self.engine.eval(full_code)
                
                # Read file and convert to base64
                import base64
                with open(temp_file, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode()
                
                os.unlink(temp_file)
                return f"data:image/png;base64,{image_data}"
                
        except Exception as e:
            logger.error(f"Error creating plot: {e}")
            return ""
    
    def run_signal_processing(self, signal_data: np.ndarray, 
                             operation: str = "fft",
                             **kwargs) -> Dict[str, Any]:
        """
        Run signal processing operations on data
        
        Args:
            signal_data: Input signal data
            operation: Signal processing operation (fft, filter, etc.)
            **kwargs: Additional parameters for the operation
            
        Returns:
            Dictionary containing processed data and results
        """
        if self.engine is None:
            return {'success': False, 'error': 'MATLAB engine not available'}
        
        try:
            # Load data into MATLAB
            self.load_data(signal_data, "signal_data")
            
            if operation == "fft":
                # Fast Fourier Transform
                result_code = """
                fft_result = fft(signal_data);
                magnitude = abs(fft_result);
                phase = angle(fft_result);
                """
            elif operation == "filter":
                # Digital filtering
                filter_type = kwargs.get('filter_type', 'lowpass')
                cutoff = kwargs.get('cutoff', 0.5)
                
                result_code = f"""
                [b, a] = butter(4, {cutoff});
                filtered_signal = filter(b, a, signal_data);
                """
            elif operation == "spectrogram":
                # Spectrogram analysis
                window_size = kwargs.get('window_size', 256)
                overlap = kwargs.get('overlap', 128)
                
                result_code = f"""
                [S, F, T] = spectrogram(signal_data, {window_size}, {overlap});
                """
            else:
                return {'success': False, 'error': f'Unknown operation: {operation}'}
            
            # Execute MATLAB code
            self.engine.eval(result_code)
            
            # Get results
            results = {}
            if operation == "fft":
                results['fft_result'] = self.get_data('fft_result')
                results['magnitude'] = self.get_data('magnitude')
                results['phase'] = self.get_data('phase')
            elif operation == "filter":
                results['filtered_signal'] = self.get_data('filtered_signal')
            elif operation == "spectrogram":
                results['S'] = self.get_data('S')
                results['F'] = self.get_data('F')
                results['T'] = self.get_data('T')
            
            return {
                'success': True,
                'results': results,
                'operation': operation
            }
            
        except Exception as e:
            logger.error(f"Error running signal processing: {e}")
            return {
                'success': False,
                'error': str(e),
                'operation': operation
            }
    
    def run_statistical_analysis(self, data: np.ndarray,
                                analysis_type: str = "descriptive",
                                **kwargs) -> Dict[str, Any]:
        """
        Run statistical analysis on data
        
        Args:
            data: Input data
            analysis_type: Type of analysis (descriptive, regression, etc.)
            **kwargs: Additional parameters
            
        Returns:
            Dictionary containing analysis results
        """
        if self.engine is None:
            return {'success': False, 'error': 'MATLAB engine not available'}
        
        try:
            # Load data into MATLAB
            self.load_data(data, "data")
            
            if analysis_type == "descriptive":
                # Descriptive statistics
                result_code = """
                mean_val = mean(data);
                std_val = std(data);
                median_val = median(data);
                min_val = min(data);
                max_val = max(data);
                skewness_val = skewness(data);
                kurtosis_val = kurtosis(data);
                """
            elif analysis_type == "regression":
                # Linear regression
                x_data = kwargs.get('x_data', None)
                if x_data is not None:
                    self.load_data(x_data, "x_data")
                    result_code = """
                    mdl = fitlm(x_data, data);
                    coefficients = mdl.Coefficients.Estimate;
                    r_squared = mdl.Rsquared.Ordinary;
                    p_values = mdl.Coefficients.pValue;
                    """
                else:
                    return {'success': False, 'error': 'x_data required for regression'}
            elif analysis_type == "correlation":
                # Correlation analysis
                y_data = kwargs.get('y_data', None)
                if y_data is not None:
                    self.load_data(y_data, "y_data")
                    result_code = """
                    corr_coef = corrcoef(data, y_data);
                    correlation = corr_coef(1, 2);
                    """
                else:
                    return {'success': False, 'error': 'y_data required for correlation'}
            else:
                return {'success': False, 'error': f'Unknown analysis type: {analysis_type}'}
            
            # Execute MATLAB code
            self.engine.eval(result_code)
            
            # Get results
            results = {}
            if analysis_type == "descriptive":
                results['mean'] = self.get_data('mean_val')
                results['std'] = self.get_data('std_val')
                results['median'] = self.get_data('median_val')
                results['min'] = self.get_data('min_val')
                results['max'] = self.get_data('max_val')
                results['skewness'] = self.get_data('skewness_val')
                results['kurtosis'] = self.get_data('kurtosis_val')
            elif analysis_type == "regression":
                results['coefficients'] = self.get_data('coefficients')
                results['r_squared'] = self.get_data('r_squared')
                results['p_values'] = self.get_data('p_values')
            elif analysis_type == "correlation":
                results['correlation'] = self.get_data('correlation')
            
            return {
                'success': True,
                'results': results,
                'analysis_type': analysis_type
            }
            
        except Exception as e:
            logger.error(f"Error running statistical analysis: {e}")
            return {
                'success': False,
                'error': str(e),
                'analysis_type': analysis_type
            }
    
    def run_optimization(self, objective_function: str,
                        initial_guess: List[float],
                        method: str = "fminsearch",
                        **kwargs) -> Dict[str, Any]:
        """
        Run optimization using MATLAB
        
        Args:
            objective_function: MATLAB function string for objective
            initial_guess: Initial parameter values
            method: Optimization method (fminsearch, fminunc, etc.)
            **kwargs: Additional optimization parameters
            
        Returns:
            Dictionary containing optimization results
        """
        if self.engine is None:
            return {'success': False, 'error': 'MATLAB engine not available'}
        
        try:
            # Load initial guess
            self.load_data(initial_guess, "x0")
            
            # Set up optimization
            if method == "fminsearch":
                opt_code = f"""
                options = optimset('Display', 'iter');
                [x_opt, fval, exitflag] = fminsearch(@(x) {objective_function}, x0, options);
                """
            elif method == "fminunc":
                opt_code = f"""
                options = optimoptions('fminunc', 'Display', 'iter');
                [x_opt, fval, exitflag] = fminunc(@(x) {objective_function}, x0, options);
                """
            else:
                return {'success': False, 'error': f'Unknown optimization method: {method}'}
            
            # Execute optimization
            self.engine.eval(opt_code)
            
            # Get results
            results = {
                'optimal_parameters': self.get_data('x_opt'),
                'optimal_value': self.get_data('fval'),
                'exit_flag': self.get_data('exitflag'),
                'method': method
            }
            
            return {
                'success': True,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error running optimization: {e}")
            return {
                'success': False,
                'error': str(e),
                'method': method
            }
    
    def is_available(self) -> bool:
        """Check if MATLAB engine is available"""
        return self.engine is not None
    
    def get_version(self) -> str:
        """Get MATLAB version"""
        if self.engine is None:
            return "Not available"
        
        try:
            version_info = self.engine.version()
            return version_info
        except Exception as e:
            logger.error(f"Error getting MATLAB version: {e}")
            return "Unknown"
    
    def close(self):
        """Close MATLAB engine"""
        if self.engine is not None:
            try:
                self.engine.quit()
                self.engine = None
                logger.info("MATLAB engine closed")
            except Exception as e:
                logger.error(f"Error closing MATLAB engine: {e}")
