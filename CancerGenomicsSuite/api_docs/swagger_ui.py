#!/usr/bin/env python3
"""
Swagger UI Integration for Cancer Genomics Analysis Suite

This module provides Swagger UI integration for the Flask application,
allowing interactive API documentation and testing.
"""

import os
import json
import yaml
from flask import Blueprint, render_template, jsonify, request, current_app
from pathlib import Path

# Create blueprint for API documentation
api_docs_bp = Blueprint('api_docs', __name__, url_prefix='/api/docs')

def load_openapi_spec():
    """Load OpenAPI specification from YAML file."""
    try:
        # Get the path to the OpenAPI spec file
        spec_path = Path(__file__).parent / 'openapi.yaml'
        
        if not spec_path.exists():
            current_app.logger.error(f"OpenAPI spec file not found: {spec_path}")
            return None
        
        # Load YAML file
        with open(spec_path, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f)
        
        # Update server URLs based on current environment
        if current_app.config.get('ENVIRONMENT') == 'development':
            spec['servers'] = [
                {
                    'url': f'http://localhost:{current_app.config.get("PORT", 8050)}',
                    'description': 'Development server'
                }
            ]
        elif current_app.config.get('ENVIRONMENT') == 'staging':
            spec['servers'] = [
                {
                    'url': 'https://staging-api.cancer-genomics.com/v1',
                    'description': 'Staging server'
                }
            ]
        else:
            spec['servers'] = [
                {
                    'url': 'https://api.cancer-genomics.com/v1',
                    'description': 'Production server'
                }
            ]
        
        return spec
    
    except Exception as e:
        current_app.logger.error(f"Error loading OpenAPI spec: {e}")
        return None

@api_docs_bp.route('/')
def swagger_ui():
    """Serve Swagger UI interface."""
    return render_template('swagger_ui.html')

@api_docs_bp.route('/openapi.json')
def openapi_json():
    """Serve OpenAPI specification as JSON."""
    spec = load_openapi_spec()
    if spec is None:
        return jsonify({'error': 'OpenAPI specification not found'}), 404
    
    return jsonify(spec)

@api_docs_bp.route('/openapi.yaml')
def openapi_yaml():
    """Serve OpenAPI specification as YAML."""
    try:
        spec_path = Path(__file__).parent / 'openapi.yaml'
        
        if not spec_path.exists():
            return jsonify({'error': 'OpenAPI specification not found'}), 404
        
        with open(spec_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return content, 200, {'Content-Type': 'application/x-yaml'}
    
    except Exception as e:
        current_app.logger.error(f"Error serving OpenAPI YAML: {e}")
        return jsonify({'error': 'Error loading OpenAPI specification'}), 500

@api_docs_bp.route('/health')
def docs_health():
    """Health check for API documentation service."""
    spec = load_openapi_spec()
    return jsonify({
        'status': 'healthy' if spec is not None else 'unhealthy',
        'openapi_version': spec.get('openapi', 'unknown') if spec else 'unknown',
        'api_version': spec.get('info', {}).get('version', 'unknown') if spec else 'unknown'
    })

def register_api_docs(app):
    """Register API documentation blueprint with Flask app."""
    app.register_blueprint(api_docs_bp)
    
    # Add CORS headers for API documentation
    @app.after_request
    def after_request(response):
        if request.endpoint and request.endpoint.startswith('api_docs'):
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

# Swagger UI HTML template
SWAGGER_UI_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ title or 'API Documentation' }}</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css" />
    <style>
        html {
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }
        *, *:before, *:after {
            box-sizing: inherit;
        }
        body {
            margin:0;
            background: #fafafa;
        }
        .swagger-ui .topbar {
            background-color: #2c3e50;
        }
        .swagger-ui .topbar .download-url-wrapper {
            display: none;
        }
        .swagger-ui .info .title {
            color: #2c3e50;
        }
        .swagger-ui .scheme-container {
            background: #2c3e50;
            padding: 10px 0;
        }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {
            const ui = SwaggerUIBundle({
                url: '{{ url_for('api_docs.openapi_json') }}',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                validatorUrl: null,
                tryItOutEnabled: true,
                requestInterceptor: function(request) {
                    // Add authentication token if available
                    const token = localStorage.getItem('auth_token');
                    if (token) {
                        request.headers['Authorization'] = 'Bearer ' + token;
                    }
                    return request;
                },
                responseInterceptor: function(response) {
                    // Store authentication token if received
                    if (response.headers && response.headers['authorization']) {
                        const token = response.headers['authorization'].replace('Bearer ', '');
                        localStorage.setItem('auth_token', token);
                    }
                    return response;
                }
            });
            
            // Add custom CSS for better styling
            const style = document.createElement('style');
            style.textContent = `
                .swagger-ui .topbar {
                    background-color: #2c3e50;
                }
                .swagger-ui .topbar .download-url-wrapper {
                    display: none;
                }
                .swagger-ui .info .title {
                    color: #2c3e50;
                }
                .swagger-ui .scheme-container {
                    background: #2c3e50;
                    padding: 10px 0;
                }
                .swagger-ui .btn.authorize {
                    background-color: #3498db;
                    border-color: #3498db;
                }
                .swagger-ui .btn.authorize:hover {
                    background-color: #2980b9;
                    border-color: #2980b9;
                }
            `;
            document.head.appendChild(style);
        };
    </script>
</body>
</html>
"""

# Create templates directory if it doesn't exist
def create_swagger_template(app):
    """Create Swagger UI template file."""
    templates_dir = Path(app.template_folder)
    templates_dir.mkdir(exist_ok=True)
    
    template_file = templates_dir / 'swagger_ui.html'
    with open(template_file, 'w', encoding='utf-8') as f:
        f.write(SWAGGER_UI_TEMPLATE)

# API Documentation Routes
@api_docs_bp.route('/examples')
def api_examples():
    """Provide API usage examples."""
    examples = {
        "authentication": {
            "login": {
                "url": "/auth/login",
                "method": "POST",
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": {
                    "username": "user@example.com",
                    "password": "secure_password",
                    "remember": False
                }
            }
        },
        "blast_analysis": {
            "analyze_sequences": {
                "url": "/blast/analyze",
                "method": "POST",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer <your-jwt-token>"
                },
                "body": {
                    "sequences": [
                        {
                            "id": "seq_001",
                            "sequence": "ATGCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG",
                            "description": "Sample sequence 1"
                        }
                    ],
                    "database": "cancer_genes",
                    "parameters": {
                        "evalue": 1e-5,
                        "max_target_seqs": 100
                    }
                }
            }
        },
        "variant_annotation": {
            "annotate_variants": {
                "url": "/annotation/annotate",
                "method": "POST",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer <your-jwt-token>"
                },
                "body": {
                    "variants": [
                        {
                            "chromosome": "17",
                            "position": 7574003,
                            "reference": "G",
                            "alternate": "A",
                            "gene_symbol": "TP53"
                        }
                    ],
                    "annotation_sources": ["ensembl", "clinvar", "cosmic"]
                }
            }
        }
    }
    
    return jsonify(examples)

@api_docs_bp.route('/status')
def api_status():
    """Get API documentation status."""
    spec = load_openapi_spec()
    
    status = {
        "documentation_available": spec is not None,
        "openapi_version": spec.get('openapi', 'unknown') if spec else 'unknown',
        "api_title": spec.get('info', {}).get('title', 'unknown') if spec else 'unknown',
        "api_version": spec.get('info', {}).get('version', 'unknown') if spec else 'unknown',
        "endpoints_count": len(spec.get('paths', {})) if spec else 0,
        "tags": [tag.get('name', '') for tag in spec.get('tags', [])] if spec else []
    }
    
    return jsonify(status)
