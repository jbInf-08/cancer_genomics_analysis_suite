import os
from pathlib import Path
from flask import Flask, jsonify
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
from plugin_registry import get_registered_plugins
from config.settings import settings

# Import AI integration components (temporarily disabled due to dependency issues)
# try:
#     from modules.ai_integration import (
#         GenomicAnalysisAssistant, AIInsightGenerator, 
#         AutomatedReportBuilder, InteractiveVisualizationAI
#     )
#     from config.ai_config import get_config
#     AI_AVAILABLE = True
# except ImportError as e:
#     print(f"Warning: AI integration not available: {e}")
#     AI_AVAILABLE = False
#     # Create dummy classes
#     class GenomicAnalysisAssistant:
#         def __init__(self): pass
#     class AIInsightGenerator:
#         def __init__(self): pass
#     class AutomatedReportBuilder:
#         def __init__(self): pass
#     class InteractiveVisualizationAI:
#         def __init__(self): pass
#     def get_config(env): return {}

# Create dummy AI classes for now
class GenomicAnalysisAssistant:
    def __init__(self): pass
class AIInsightGenerator:
    def __init__(self): pass
class AutomatedReportBuilder:
    def __init__(self): pass
class InteractiveVisualizationAI:
    def __init__(self): pass
def get_config(env): return {}
AI_AVAILABLE = False

# Create Flask server, point to static folder
# Get the directory where this file is located
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

server = Flask(
    __name__,
    static_folder=str(STATIC_DIR),
    static_url_path="/static"
)

# Add a test route to verify server is working (before Dash initialization)
@server.route('/test')
def test_route():
    """Test route to verify server is responding."""
    print("DEBUG: Test route accessed")
    return jsonify({'status': 'ok', 'message': 'Server is responding'})

# Add a before_request handler to log all requests
@server.before_request
def log_request():
    """Log all incoming requests."""
    from flask import request
    print(f"DEBUG: Incoming request: {request.method} {request.path}")

# Dash app - initialize with Flask server
app = dash.Dash(
    __name__,
    server=server,
    suppress_callback_exceptions=True,
    title="Cancer Genomics Dashboard"
)

# Note: Dash handles its own errors, so we don't add Flask error handlers here
# This allows Dash to display errors in its own format

# Load modules/plugins
plugins = get_registered_plugins()

# Initialize AI components
if AI_AVAILABLE:
    ai_config = get_config('development')
    ai_chatbot = GenomicAnalysisAssistant()
    ai_insight_generator = AIInsightGenerator()
    ai_report_builder = AutomatedReportBuilder()
    ai_visualization = InteractiveVisualizationAI()
else:
    ai_config = {}
    ai_chatbot = GenomicAnalysisAssistant()
    ai_insight_generator = AIInsightGenerator()
    ai_report_builder = AutomatedReportBuilder()
    ai_visualization = InteractiveVisualizationAI()

# App layout - wrap in try-except to catch any layout errors
try:
    app_layout_content = [
        # Include Google Fonts (Roboto) - Simon Sexton Style
        html.Link(rel="preconnect", href="https://fonts.googleapis.com"),
        html.Link(rel="preconnect", href="https://fonts.gstatic.com", crossOrigin=""),
        html.Link(rel="stylesheet", href="https://fonts.googleapis.com/css2?family=Roboto:wght@100;500&display=swap"),
        # Include FontAwesome for icons
        html.Link(rel="stylesheet", href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"),
        # Include CSS links for light/dark themes and favicon
        html.Link(rel="stylesheet", href="/static/css/dashboard_light.css", id="light-theme", media="all"),
        html.Link(rel="stylesheet", href="/static/css/dashboard_dark.css", id="dark-theme", media="none"),
        # Favicon - use gene.png if favicon.ico doesn't exist
        html.Link(rel="icon", href="/static/icons/gene.png", type="image/png"),

        # Header with logo, sidebar & theme toggles - Simon Sexton Style
        html.Header(
            [
                html.Div([
                    html.Img(src="/static/icons/gene.png", height="40px", className="logo", alt="Cancer Genomics"),
                    html.H1("Cancer Genomics Analysis Suite", className="app-title"),
                ], style={"display": "flex", "alignItems": "center", "flex": "1"}),
                html.Div([
                    html.Button("☰", id="sidebar-toggle", className="sidebar-toggle", title="Toggle Sidebar"),
                    html.Div([
                        html.I(className="fa-solid fa-sun dark-light-switch clickable purple-on-hover", id="light-mode-icon", title="Light Mode", n_clicks=0),
                        html.Span("|", className="dark-light-switch"),
                        html.I(className="fa-solid fa-moon dark-light-switch clickable purple-on-hover", id="dark-mode-icon", title="Dark Mode", n_clicks=0),
                    ], id="dark-light-switch-container", className="dark-light-switch-container"),
                ], className="header-controls", style={"display": "flex", "alignItems": "center", "gap": "1rem"})
            ],
            className="header"
        ),

        # Sidebar
        html.Div(
            [
                html.Div([
                    html.H3("Modules", className="sidebar-title"),
                    html.Ul([
                        html.Li([
                            html.A(label, href="#", className="sidebar-link", **{"data-tab": label})
                        ]) for label in (plugins.keys() if plugins else [])
                    ], className="sidebar-menu") if plugins and len(plugins) > 0 else html.Ul([], className="sidebar-menu"),
                    
                    html.H3("AI Features", className="sidebar-title"),
                    html.Ul([
                        html.Li([
                            html.A("🤖 AI Assistant", href="#", className="sidebar-link", **{"data-tab": "ai-assistant"})
                        ]),
                        html.Li([
                            html.A("🧠 Deep Learning", href="#", className="sidebar-link", **{"data-tab": "deep-learning"})
                        ]),
                        html.Li([
                            html.A("📊 AI Insights", href="#", className="sidebar-link", **{"data-tab": "ai-insights"})
                        ]),
                        html.Li([
                            html.A("🔍 Pattern Recognition", href="#", className="sidebar-link", **{"data-tab": "pattern-recognition"})
                        ]),
                        html.Li([
                            html.A("📝 AI Reports", href="#", className="sidebar-link", **{"data-tab": "ai-reports"})
                        ])
                    ], className="sidebar-menu")
                ], className="sidebar-content")
            ],
            id="sidebar",
            className="sidebar"
        ),

        # Main content - Simon Sexton Style
        html.Div(
            [
                html.Div([
                    dcc.Tabs(
                        id="tabs",
                        value=list(plugins.keys())[0] if plugins and len(plugins) > 0 else "welcome",
                        children=[dcc.Tab(label=label, value=label) for label in plugins.keys()] if plugins and len(plugins) > 0 else [dcc.Tab(label="Welcome", value="welcome")],
                        className="main-tabs"
                    ),
                    html.Div([
                        html.H3("Welcome"),
                        html.P("Please select a module from the tabs above.")
                    ], id="tab-content", className="tab-content"),
                ], className="max-w-1026"),
            ],
            className="main-content centering-container"
        ),

        # Welcome message if no plugins are loaded
        html.Div([
            html.H2("Welcome to Cancer Genomics Analysis Suite"),
            html.P("No modules are currently available. Please check the plugin registry configuration."),
            html.P(f"Environment: {settings.flask_env} | Debug: {settings.dash_debug_mode}")
        ], id="welcome-message", className="welcome-message", style={"display": "none" if plugins else "block"}),
        
        # Include JavaScript files - Load theme toggle first so functions are available
        html.Script(src="/static/js/theme_toggle.js"),
        html.Script(src="/static/js/sidebar_toggle.js"),
    ]
    app.layout = html.Div(app_layout_content)
    print("DEBUG: App layout created successfully")
except Exception as e:
    import traceback
    error_trace = traceback.format_exc()
    print(f"ERROR: Failed to create app layout: {e}")
    print(error_trace)
    # Create a minimal error layout
    app.layout = html.Div([
        html.H1("Error Loading Dashboard"),
        html.P(f"An error occurred while creating the dashboard layout: {str(e)}"),
        html.Pre(error_trace, style={"fontSize": "10px", "overflow": "auto", "maxHeight": "400px"})
    ])

# Theme toggle callbacks using ClientsideCallback
app.clientside_callback(
    """
    function(light_clicks, dark_clicks) {
        if (light_clicks > 0 && window.selectLightMode) {
            window.selectLightMode();
        }
        if (dark_clicks > 0 && window.selectDarkMode) {
            window.selectDarkMode();
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("dark-light-switch-container", "id"),  # Dummy output, we just need to trigger
    [Input("light-mode-icon", "n_clicks"),
     Input("dark-mode-icon", "n_clicks")]
)

# Callback to render selected tab
@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "value"),
    prevent_initial_call=True  # Prevent initial call to avoid errors on page load
)
def render_tab(tab_name):
    import traceback
    try:
        print(f"DEBUG: render_tab called with tab_name={tab_name}")
        print(f"DEBUG: plugins available: {list(plugins.keys()) if plugins else 'None'}")
        print(f"DEBUG: plugins type: {type(plugins)}")
        print(f"DEBUG: plugins length: {len(plugins) if plugins else 0}")
        
        # Ensure plugins is available
        if plugins is None:
            print("ERROR: plugins is None!")
            return html.Div([
                html.H3("Configuration Error"),
                html.P("Plugins were not loaded correctly. Please check the server logs.")
            ])
        
        # Handle None or empty tab_name
        if tab_name is None or tab_name == "":
            print("DEBUG: tab_name is None or empty")
            if plugins and len(plugins) > 0:
                tab_name = list(plugins.keys())[0]
                print(f"DEBUG: Using first plugin: {tab_name}")
            else:
                print("DEBUG: No plugins available, returning welcome message")
                return html.Div([
                    html.H3("Welcome"),
                    html.P("Please select a module from the tabs above.")
                ])
        
        if not plugins or len(plugins) == 0:
            print("DEBUG: No plugins loaded")
            return html.Div([
                html.H3("No modules available"),
                html.P("Please check the plugin registry configuration.")
            ])
        
        if tab_name not in plugins:
            print(f"DEBUG: tab_name '{tab_name}' not in plugins, available: {list(plugins.keys())}")
            # Try to find a valid tab name
            if plugins and len(plugins) > 0:
                tab_name = list(plugins.keys())[0]
                print(f"DEBUG: Using first available plugin: {tab_name}")
            else:
                return html.Div([
                    html.H3("Module not found"),
                    html.P(f"The module '{tab_name}' could not be loaded."),
                    html.P(f"Available modules: {', '.join(plugins.keys()) if plugins else 'None'}")
                ])
        
        print(f"DEBUG: Getting plugin for '{tab_name}'")
        plugin = plugins[tab_name]
        layout = plugin.get("layout")
        
        if layout is None:
            print(f"DEBUG: Layout is None for '{tab_name}'")
            return html.Div([
                html.H3("Module Error"),
                html.P(f"The module '{tab_name}' has no layout defined.")
            ])
        
        print(f"DEBUG: Rendering layout for '{tab_name}'")
        # Try to render the layout
        try:
            result = layout
            print(f"DEBUG: Successfully got layout for '{tab_name}'")
            return result
        except Exception as layout_error:
            error_trace = traceback.format_exc()
            print(f"ERROR: Error rendering layout for '{tab_name}': {str(layout_error)}")
            print(error_trace)
            return html.Div([
                html.H3("Error Rendering Module"),
                html.P(f"Error rendering layout for '{tab_name}': {str(layout_error)}"),
                html.Pre(error_trace, style={"fontSize": "10px", "overflow": "auto", "maxHeight": "400px"})
            ])
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        print(f"ERROR: Exception in render_tab with tab_name='{tab_name}': {error_msg}")
        print(error_trace)
        return html.Div([
            html.H3("Error Loading Module"),
            html.P(f"An error occurred while loading '{tab_name}': {error_msg}"),
            html.Pre(error_trace, style={"fontSize": "10px", "overflow": "auto", "maxHeight": "400px"})
        ])

# Register module-specific callbacks
print(f"DEBUG: Registering callbacks for {len(plugins)} plugins")
for plugin_name, plugin in plugins.items():
    if plugin.get("register_callbacks"):
        try:
            print(f"DEBUG: Registering callbacks for plugin: {plugin_name}")
            plugin["register_callbacks"](app)
            print(f"DEBUG: Successfully registered callbacks for plugin: {plugin_name}")
        except Exception as e:
            import traceback
            print(f"ERROR: Failed to register callbacks for plugin {plugin_name}: {e}")
            print(traceback.format_exc())

if __name__ == "__main__":
    print(f"DEBUG: Starting Dash server on {settings.host}:{settings.port}")
    print(f"DEBUG: Plugins loaded: {list(plugins.keys()) if plugins else 'None'}")
    print(f"DEBUG: Settings object: {settings}")
    print(f"DEBUG: Settings type: {type(settings)}")
    try:
        print("DEBUG: About to call app.run_server()")
        app.run_server(
            debug=settings.dash_debug_mode,
            host=settings.host,
            port=settings.port
        )
    except Exception as e:
        import traceback
        print(f"ERROR: Failed to start server: {e}")
        print(traceback.format_exc())
        raise
