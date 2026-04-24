"""
MATLAB Integration Dashboard

Provides a Dash interface for executing MATLAB code, running numerical computations,
and performing signal processing operations.
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import numpy as np
import json
import base64
from typing import Dict, List, Any
import logging

from .matlab_client import MATLABClient

logger = logging.getLogger(__name__)

# Initialize MATLAB client
matlab_client = MATLABClient()

# Dashboard layout
layout = html.Div([
    html.Div([
        html.H2("🔢 MATLAB Integration", className="section-title"),
        html.P("Execute MATLAB code, run numerical computations, and perform signal processing", className="section-description"),
    ], className="section-header"),
    
    # MATLAB Status section
    html.Div([
        html.H3("MATLAB Status", className="subsection-title"),
        html.Div([
            html.Div([
                html.Span("Status: ", className="status-label"),
                html.Span(id="matlab-status", className="status-value"),
            ], className="status-item"),
            html.Div([
                html.Span("Version: ", className="status-label"),
                html.Span(id="matlab-version", className="status-value"),
            ], className="status-item"),
            html.Div([
                html.Span("Toolboxes: ", className="status-label"),
                html.Span(id="matlab-toolboxes", className="status-value"),
            ], className="status-item"),
        ], className="status-container"),
        html.Button("Refresh Status", id="refresh-matlab-status", className="button secondary"),
    ], className="matlab-status-section"),
    
    # MATLAB Code Editor section
    html.Div([
        html.H3("MATLAB Code Editor", className="subsection-title"),
        html.Div([
            html.Label("MATLAB Code:", className="input-label"),
            dcc.Textarea(
                id="matlab-code-editor",
                placeholder="# Enter your MATLAB code here...\n# Example:\n# x = 0:0.1:2*pi;\n# y = sin(x);\n# plot(x, y);\n# title('Sine Wave');",
                style={'width': '100%', 'height': '300px', 'fontFamily': 'monospace'},
                className="code-editor"
            ),
        ], className="input-group"),
        html.Div([
            html.Button("Execute MATLAB Code", id="execute-matlab-code", className="button primary"),
            html.Button("Clear", id="clear-matlab-code", className="button secondary"),
            html.Button("Load Example", id="load-matlab-example", className="button secondary"),
        ], className="button-group"),
        html.Div(id="matlab-execution-status", className="execution-status"),
    ], className="code-editor-section"),
    
    # Signal Processing section
    html.Div([
        html.H3("Signal Processing", className="subsection-title"),
        dcc.Tabs(id="signal-processing-tabs", value="fft", children=[
            dcc.Tab(label="FFT Analysis", value="fft"),
            dcc.Tab(label="Filtering", value="filter"),
            dcc.Tab(label="Spectrogram", value="spectrogram"),
        ]),
        html.Div(id="signal-processing-content", className="signal-processing-content"),
    ], className="signal-processing-section"),
    
    # Statistical Analysis section
    html.Div([
        html.H3("Statistical Analysis", className="subsection-title"),
        dcc.Tabs(id="statistical-analysis-tabs", value="descriptive", children=[
            dcc.Tab(label="Descriptive Statistics", value="descriptive"),
            dcc.Tab(label="Regression Analysis", value="regression"),
            dcc.Tab(label="Correlation Analysis", value="correlation"),
        ]),
        html.Div(id="statistical-analysis-content", className="statistical-analysis-content"),
    ], className="statistical-analysis-section"),
    
    # Optimization section
    html.Div([
        html.H3("Optimization", className="subsection-title"),
        html.Div([
            html.Div([
                html.Label("Objective Function:", className="input-label"),
                dcc.Textarea(
                    id="objective-function",
                    placeholder="x(1)^2 + x(2)^2",
                    style={'width': '100%', 'height': '100px', 'fontFamily': 'monospace'},
                    className="code-editor"
                ),
            ], className="input-group"),
            html.Div([
                html.Label("Initial Guess (comma-separated):", className="input-label"),
                dcc.Input(
                    id="initial-guess",
                    type="text",
                    placeholder="1, 1",
                    className="input-field"
                ),
            ], className="input-group"),
            html.Div([
                html.Label("Method:", className="input-label"),
                dcc.Dropdown(
                    id="optimization-method",
                    options=[
                        {'label': 'fminsearch', 'value': 'fminsearch'},
                        {'label': 'fminunc', 'value': 'fminunc'},
                    ],
                    value='fminsearch',
                    className="dropdown"
                ),
            ], className="input-group"),
            html.Button("Run Optimization", id="run-optimization", className="button primary"),
            html.Div(id="optimization-results", className="optimization-results"),
        ], className="optimization-section"),
    ], className="optimization-section"),
    
    # Data Upload section
    html.Div([
        html.H3("Data Upload", className="subsection-title"),
        dcc.Upload(
            id="matlab-data-upload",
            children=html.Div([
                "Drag and Drop or ",
                html.A("Select Data Files")
            ]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            multiple=True
        ),
        html.Div(id="matlab-uploaded-data", className="uploaded-data"),
    ], className="data-upload-section"),
    
    # Results section
    html.Div([
        html.H3("Results", className="subsection-title"),
        html.Div(id="matlab-results", className="results-container"),
    ], className="results-section"),
    
    # Hidden divs for storing data
    html.Div(id="matlab-data", style={"display": "none"}),
])

def register_callbacks(app):
    """Register callbacks for the MATLAB dashboard"""
    
    @app.callback(
        [Output("matlab-status", "children"),
         Output("matlab-version", "children"),
         Output("matlab-toolboxes", "children")],
        [Input("refresh-matlab-status", "n_clicks")]
    )
    def update_matlab_status(n_clicks):
        if matlab_client.is_available():
            status = "✅ Available"
            version = matlab_client.get_version()
            toolboxes = f"{len(matlab_client.available_toolboxes)} toolboxes"
        else:
            status = "❌ Not Available"
            version = "Not available"
            toolboxes = "0 toolboxes"
        
        return status, version, toolboxes
    
    @app.callback(
        [Output("matlab-execution-status", "children"),
         Output("matlab-results", "children")],
        [Input("execute-matlab-code", "n_clicks")],
        [State("matlab-code-editor", "value")]
    )
    def execute_matlab_code(n_clicks, matlab_code):
        if n_clicks is None or not matlab_code:
            return "", ""
        
        if not matlab_client.is_available():
            status = html.Span("❌ MATLAB engine not available", className="error-message")
            return status, ""
        
        try:
            # Execute MATLAB code
            result = matlab_client.execute_matlab_script(matlab_code)
            
            if result['success']:
                status = html.Div([
                    html.Span("✅ MATLAB code executed successfully", className="success-message"),
                    html.Br(),
                    html.Span(f"Return code: {result['returncode']}", className="info-message")
                ])
                
                # Display output
                output_content = []
                if result['output']:
                    output_content.append(html.H4("Output:"))
                    output_content.append(html.Pre(result['output'], className="code-output"))
                
                if result['error_output']:
                    output_content.append(html.H4("Messages:"))
                    output_content.append(html.Pre(result['error_output'], className="code-messages"))
                
                return status, html.Div(output_content)
            else:
                status = html.Div([
                    html.Span("❌ MATLAB code execution failed", className="error-message"),
                    html.Br(),
                    html.Span(f"Error: {result.get('error', 'Unknown error')}", className="error-details")
                ])
                return status, html.Pre(result['error_output'], className="error-output")
                
        except Exception as e:
            logger.error(f"Error executing MATLAB code: {e}")
            status = html.Span(f"❌ Error: {str(e)}", className="error-message")
            return status, ""
    
    @app.callback(
        Output("matlab-code-editor", "value"),
        [Input("clear-matlab-code", "n_clicks"),
         Input("load-matlab-example", "n_clicks")]
    )
    def manage_matlab_code(clear_clicks, example_clicks):
        ctx = callback_context
        if not ctx.triggered:
            return ""
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if button_id == "clear-matlab-code":
            return ""
        elif button_id == "load-matlab-example":
            example_code = """
% Example MATLAB code for signal processing and analysis
% Generate sample data
t = 0:0.01:10;
signal = sin(2*pi*5*t) + 0.5*sin(2*pi*10*t) + 0.1*randn(size(t));

% Plot original signal
figure;
subplot(2,2,1);
plot(t, signal);
title('Original Signal');
xlabel('Time (s)');
ylabel('Amplitude');

% FFT analysis
fft_result = fft(signal);
frequencies = (0:length(fft_result)-1) * (1/0.01) / length(fft_result);

subplot(2,2,2);
plot(frequencies(1:length(frequencies)/2), abs(fft_result(1:length(fft_result)/2)));
title('Frequency Spectrum');
xlabel('Frequency (Hz)');
ylabel('Magnitude');

% Filter the signal
[b, a] = butter(4, 0.1);
filtered_signal = filter(b, a, signal);

subplot(2,2,3);
plot(t, filtered_signal);
title('Filtered Signal');
xlabel('Time (s)');
ylabel('Amplitude');

% Statistical analysis
mean_val = mean(signal);
std_val = std(signal);
fprintf('Mean: %.4f\\n', mean_val);
fprintf('Standard Deviation: %.4f\\n', std_val);
"""
            return example_code
        
        return ""
    
    @app.callback(
        Output("signal-processing-content", "children"),
        [Input("signal-processing-tabs", "value")]
    )
    def update_signal_processing_content(active_tab):
        if active_tab == "fft":
            return html.Div([
                html.H4("Fast Fourier Transform Analysis"),
                html.P("Analyze frequency components of signals"),
                html.Div([
                    html.Label("Signal Length:", className="input-label"),
                    dcc.Input(
                        id="fft-signal-length",
                        type="number",
                        value=1000,
                        min=100,
                        max=10000,
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Sampling Rate (Hz):", className="input-label"),
                    dcc.Input(
                        id="fft-sampling-rate",
                        type="number",
                        value=1000,
                        min=1,
                        max=10000,
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Button("Run FFT Analysis", id="run-fft", className="button primary"),
                html.Div(id="fft-results", className="analysis-results"),
            ])
        
        elif active_tab == "filter":
            return html.Div([
                html.H4("Digital Filtering"),
                html.P("Apply digital filters to signals"),
                html.Div([
                    html.Label("Filter Type:", className="input-label"),
                    dcc.Dropdown(
                        id="filter-type",
                        options=[
                            {'label': 'Lowpass', 'value': 'lowpass'},
                            {'label': 'Highpass', 'value': 'highpass'},
                            {'label': 'Bandpass', 'value': 'bandpass'},
                        ],
                        value='lowpass',
                        className="dropdown"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Cutoff Frequency:", className="input-label"),
                    dcc.Input(
                        id="filter-cutoff",
                        type="number",
                        value=0.5,
                        min=0.01,
                        max=0.99,
                        step=0.01,
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Button("Apply Filter", id="apply-filter", className="button primary"),
                html.Div(id="filter-results", className="analysis-results"),
            ])
        
        elif active_tab == "spectrogram":
            return html.Div([
                html.H4("Spectrogram Analysis"),
                html.P("Generate time-frequency representation of signals"),
                html.Div([
                    html.Label("Window Size:", className="input-label"),
                    dcc.Input(
                        id="spectrogram-window",
                        type="number",
                        value=256,
                        min=64,
                        max=1024,
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Overlap:", className="input-label"),
                    dcc.Input(
                        id="spectrogram-overlap",
                        type="number",
                        value=128,
                        min=32,
                        max=512,
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Button("Generate Spectrogram", id="generate-spectrogram", className="button primary"),
                html.Div(id="spectrogram-results", className="analysis-results"),
            ])
    
    @app.callback(
        Output("fft-results", "children"),
        [Input("run-fft", "n_clicks")],
        [State("fft-signal-length", "value"),
         State("fft-sampling-rate", "value")]
    )
    def run_fft_analysis(n_clicks, signal_length, sampling_rate):
        if n_clicks is None:
            return ""
        
        if not matlab_client.is_available():
            return html.P("❌ MATLAB engine not available")
        
        try:
            # Generate sample signal
            t = np.linspace(0, 1, signal_length)
            signal = np.sin(2 * np.pi * 5 * t) + 0.5 * np.sin(2 * np.pi * 10 * t)
            
            # Run FFT analysis
            result = matlab_client.run_signal_processing(signal, "fft")
            
            if result['success']:
                return html.Div([
                    html.H5("✅ FFT Analysis Completed"),
                    html.P(f"Analyzed signal of length {signal_length}"),
                    html.P(f"Sampling rate: {sampling_rate} Hz"),
                    html.Button("Download Results", className="button secondary"),
                ])
            else:
                return html.Div([
                    html.H5("❌ FFT Analysis Failed"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error running FFT analysis: {e}")
            return html.Div([
                html.H5("❌ Error"),
                html.P(f"Error: {str(e)}"),
            ])
    
    @app.callback(
        Output("statistical-analysis-content", "children"),
        [Input("statistical-analysis-tabs", "value")]
    )
    def update_statistical_analysis_content(active_tab):
        if active_tab == "descriptive":
            return html.Div([
                html.H4("Descriptive Statistics"),
                html.P("Calculate basic statistical measures"),
                html.Button("Run Descriptive Analysis", id="run-descriptive", className="button primary"),
                html.Div(id="descriptive-results", className="analysis-results"),
            ])
        
        elif active_tab == "regression":
            return html.Div([
                html.H4("Linear Regression Analysis"),
                html.P("Perform linear regression analysis"),
                html.Div([
                    html.Label("X Variable Name:", className="input-label"),
                    dcc.Input(
                        id="regression-x",
                        type="text",
                        placeholder="x_data",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Y Variable Name:", className="input-label"),
                    dcc.Input(
                        id="regression-y",
                        type="text",
                        placeholder="y_data",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Button("Run Regression", id="run-regression", className="button primary"),
                html.Div(id="regression-results", className="analysis-results"),
            ])
        
        elif active_tab == "correlation":
            return html.Div([
                html.H4("Correlation Analysis"),
                html.P("Calculate correlation between variables"),
                html.Div([
                    html.Label("Variable 1 Name:", className="input-label"),
                    dcc.Input(
                        id="correlation-var1",
                        type="text",
                        placeholder="var1",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Div([
                    html.Label("Variable 2 Name:", className="input-label"),
                    dcc.Input(
                        id="correlation-var2",
                        type="text",
                        placeholder="var2",
                        className="input-field"
                    ),
                ], className="input-group"),
                html.Button("Calculate Correlation", id="calculate-correlation", className="button primary"),
                html.Div(id="correlation-results", className="analysis-results"),
            ])
    
    @app.callback(
        Output("descriptive-results", "children"),
        [Input("run-descriptive", "n_clicks")]
    )
    def run_descriptive_analysis(n_clicks):
        if n_clicks is None:
            return ""
        
        if not matlab_client.is_available():
            return html.P("❌ MATLAB engine not available")
        
        try:
            # Generate sample data
            data = np.random.normal(100, 15, 1000)
            
            # Run descriptive analysis
            result = matlab_client.run_statistical_analysis(data, "descriptive")
            
            if result['success']:
                results = result['results']
                return html.Div([
                    html.H5("✅ Descriptive Statistics Completed"),
                    html.Div([
                        html.P(f"Mean: {results['mean']:.4f}"),
                        html.P(f"Standard Deviation: {results['std']:.4f}"),
                        html.P(f"Median: {results['median']:.4f}"),
                        html.P(f"Min: {results['min']:.4f}"),
                        html.P(f"Max: {results['max']:.4f}"),
                        html.P(f"Skewness: {results['skewness']:.4f}"),
                        html.P(f"Kurtosis: {results['kurtosis']:.4f}"),
                    ], className="statistics-results"),
                ])
            else:
                return html.Div([
                    html.H5("❌ Descriptive Analysis Failed"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error running descriptive analysis: {e}")
            return html.Div([
                html.H5("❌ Error"),
                html.P(f"Error: {str(e)}"),
            ])
    
    @app.callback(
        Output("optimization-results", "children"),
        [Input("run-optimization", "n_clicks")],
        [State("objective-function", "value"),
         State("initial-guess", "value"),
         State("optimization-method", "value")]
    )
    def run_optimization(n_clicks, objective_function, initial_guess, method):
        if n_clicks is None or not objective_function or not initial_guess:
            return ""
        
        if not matlab_client.is_available():
            return html.P("❌ MATLAB engine not available")
        
        try:
            # Parse initial guess
            initial_values = [float(x.strip()) for x in initial_guess.split(',')]
            
            # Run optimization
            result = matlab_client.run_optimization(objective_function, initial_values, method)
            
            if result['success']:
                results = result['results']
                return html.Div([
                    html.H5("✅ Optimization Completed"),
                    html.P(f"Method: {results['method']}"),
                    html.P(f"Optimal Parameters: {results['optimal_parameters']}"),
                    html.P(f"Optimal Value: {results['optimal_value']:.6f}"),
                    html.P(f"Exit Flag: {results['exit_flag']}"),
                ])
            else:
                return html.Div([
                    html.H5("❌ Optimization Failed"),
                    html.P(f"Error: {result['error']}"),
                ])
                
        except Exception as e:
            logger.error(f"Error running optimization: {e}")
            return html.Div([
                html.H5("❌ Error"),
                html.P(f"Error: {str(e)}"),
            ])
    
    @app.callback(
        Output("matlab-uploaded-data", "children"),
        [Input("matlab-data-upload", "contents")],
        [State("matlab-data-upload", "filename")]
    )
    def handle_matlab_data_upload(contents, filename):
        if contents is None:
            return ""
        
        try:
            # Process uploaded files
            uploaded_files = []
            for content, name in zip(contents, filename):
                # Parse CSV data
                if name.endswith('.csv'):
                    import base64
                    import io
                    
                    content_type, content_string = content.split(',')
                    decoded = base64.b64decode(content_string)
                    
                    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
                    
                    # Load data into MATLAB
                    matlab_client.load_data(df, name.replace('.csv', ''))
                    
                    uploaded_files.append(html.Div([
                        html.H5(f"✅ {name}"),
                        html.P(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns"),
                        html.P(f"Columns: {', '.join(df.columns[:5])}{'...' if len(df.columns) > 5 else ''}"),
                    ], className="uploaded-file"))
            
            return html.Div(uploaded_files)
            
        except Exception as e:
            logger.error(f"Error handling MATLAB data upload: {e}")
            return html.P(f"❌ Upload failed: {str(e)}")
