"""
Demo module to showcase the dashboard functionality
This module provides a simple example of how to create a dashboard module.
"""

# Mock dash components for demonstration
class MockHtml:
    def Div(self, *args, **kwargs):
        return f"<div class='{kwargs.get('className', '')}'>{args}</div>"
    
    def H1(self, *args, **kwargs):
        return f"<h1 class='{kwargs.get('className', '')}'>{args}</h1>"
    
    def H2(self, *args, **kwargs):
        return f"<h2 class='{kwargs.get('className', '')}'>{args}</h2>"
    
    def H3(self, *args, **kwargs):
        return f"<h3 class='{kwargs.get('className', '')}'>{args}</h3>"
    
    def P(self, *args, **kwargs):
        return f"<p class='{kwargs.get('className', '')}'>{args}</p>"
    
    def Button(self, *args, **kwargs):
        return f"<button id='{kwargs.get('id', '')}' class='{kwargs.get('className', '')}'>{args}</button>"
    
    def Label(self, *args, **kwargs):
        return f"<label class='{kwargs.get('className', '')}'>{args}</label>"
    
    def Textarea(self, *args, **kwargs):
        return f"<textarea id='{kwargs.get('id', '')}' class='{kwargs.get('className', '')}' placeholder='{kwargs.get('placeholder', '')}'>{args}</textarea>"
    
    def Ul(self, *args, **kwargs):
        return f"<ul class='{kwargs.get('className', '')}'>{args}</ul>"
    
    def Li(self, *args, **kwargs):
        return f"<li class='{kwargs.get('className', '')}'>{args}</li>"

class MockDcc:
    def Tabs(self, *args, **kwargs):
        return f"<div class='tabs'>{args}</div>"
    
    def Tab(self, *args, **kwargs):
        return f"<div class='tab' data-value='{kwargs.get('value', '')}'>{args}</div>"

# Only mock dash modules if they're not already available
import sys
if 'dash' not in sys.modules:
    sys.modules['dash'] = type('MockDash', (), {})()
    sys.modules['dash.html'] = MockHtml()
    sys.modules['dash.dcc'] = MockDcc()
    sys.modules['dash.dependencies'] = type('MockDeps', (), {
        'Input': lambda x: f"input:{x}",
        'Output': lambda x: f"output:{x}",
        'State': lambda x: f"state:{x}"
    })()

# Now import the actual dash components
try:
    from dash import html, dcc
    from dash.dependencies import Input, Output, State
except ImportError:
    # Use mock components if dash is not available
    html = MockHtml()
    dcc = MockDcc()
    Input = lambda x: f"input:{x}"
    Output = lambda x: f"output:{x}"
    State = lambda x: f"state:{x}"

# Demo layout
layout = html.Div([
    html.H1("🧬 Demo Module", className="module-title"),
    html.P("This is a demonstration module showing how to create a dashboard component.", className="module-description"),
    
    html.Div([
        html.H2("Sample Analysis Tool", className="section-title"),
        html.Label("Enter your data here:", className="input-label"),
        html.Textarea(
            id='demo-input',
            placeholder='Enter some data to analyze...',
            className="demo-textarea"
        ),
        html.Button('Analyze Data', id='demo-analyze-btn', className="demo-button"),
        html.Div(id='demo-output', className="demo-output")
    ], className="demo-container"),
    
    html.Div([
        html.H2("Module Information", className="section-title"),
        html.P("This module demonstrates:", className="info-text"),
        html.Ul([
            html.Li("How to create a Dash layout"),
            html.Li("How to structure module components"),
            html.Li("How to integrate with the main dashboard"),
            html.Li("How to handle user interactions")
        ], className="info-list")
    ], className="info-container")
])

def register_callbacks(app):
    """Register callbacks for this module."""
    try:
        @app.callback(
            Output('demo-output', 'children'),
            Input('demo-analyze-btn', 'n_clicks'),
            State('demo-input', 'value')
        )
        def analyze_data(n_clicks, input_data):
            if n_clicks and n_clicks > 0 and input_data:
                return html.Div([
                    html.H3("Analysis Results"),
                    html.P(f"Analyzed {len(input_data)} characters of data"),
                    html.P(f"Data preview: {input_data[:100]}..."),
                    html.P("✅ Analysis completed successfully!")
                ], className="analysis-results")
            return html.P("Enter some data and click 'Analyze Data' to see results.", className="placeholder-text")
    except Exception as e:
        print(f"Warning: Could not register callbacks for demo module: {e}")
        # Create a mock callback function
        def mock_callback(*args, **kwargs):
            return html.P("Demo module loaded (callbacks not available)")
        return mock_callback
