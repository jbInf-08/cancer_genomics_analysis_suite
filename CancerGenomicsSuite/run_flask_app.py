#!/usr/bin/env python3
"""
Cancer Genomics Analysis Suite - Flask Application Runner

This script provides a simple way to run the Flask application for development
and testing purposes. It creates the Flask app using the application factory
pattern and runs it with the appropriate configuration.

Usage:
    python run_flask_app.py

Environment Variables:
    FLASK_ENV: Set to 'development', 'production', or 'testing'
    PORT: Port number to run the application on (default: 5000)
    HOST: Host to bind the application to (default: 0.0.0.0)
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app import create_app
from config.settings import settings

def main():
    """Main function to run the Flask application."""
    
    # Create Flask application
    app = create_app()
    
    # Get configuration from settings
    host = settings.host
    port = settings.port
    debug = settings.dash_debug_mode
    
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Environment: {settings.flask_env}")
    print(f"Debug mode: {debug}")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Database: {settings.get_database_url()}")
    print("-" * 50)
    
    # Run the application
    try:
        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\nShutting down Flask application...")
    except Exception as e:
        print(f"Error running Flask application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
