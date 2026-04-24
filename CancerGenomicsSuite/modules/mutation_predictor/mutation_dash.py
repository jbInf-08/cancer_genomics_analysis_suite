from dash import html, dcc

layout = html.Div([
    html.H1("Mutation Predictor"),
    html.P("This module will provide mutation effect prediction tools."),
    html.Div([
        html.Label("Input Mutation:"),
        dcc.Input(id='mutation-input', type='text', placeholder='e.g., c.215C>G'),
        html.Button('Predict Effect', id='predict-btn', n_clicks=0),
        html.Div(id='mutation-output')
    ])
])

def register_callbacks(app):
    """Register callbacks for this module."""
    pass
