#!/usr/bin/env python3
"""
Test script for the Cancer Genomics Dashboard
This script tests the dashboard without requiring all dependencies to be installed.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_plugin_registry():
    """Test the plugin registry functionality."""
    print("Testing plugin registry...")
    
    try:
        from plugin_registry import get_registered_plugins, get_plugins_by_category
        plugins = get_registered_plugins()
        print(f"✓ Plugin registry loaded successfully")
        print(f"✓ Found {len(plugins)} plugins")
        
        if plugins:
            print("Available plugins:")
            for name, data in plugins.items():
                print(f"  - {name}: {data['metadata']['description']}")
        
        categories = get_plugins_by_category()
        print(f"✓ Plugin categories: {list(categories.keys())}")
        
        return True
    except Exception as e:
        print(f"✗ Plugin registry test failed: {e}")
        return False

def test_settings():
    """Test the settings configuration."""
    print("\nTesting settings...")
    
    try:
        from config.settings import settings
        print(f"✓ Settings loaded successfully")
        print(f"✓ App name: {settings.app_name}")
        print(f"✓ Host: {settings.host}")
        print(f"✓ Port: {settings.port}")
        print(f"✓ Debug mode: {settings.dash_debug_mode}")
        return True
    except Exception as e:
        print(f"✗ Settings test failed: {e}")
        return False

def test_dashboard_import():
    """Test importing the main dashboard."""
    print("\nTesting dashboard import...")
    
    try:
        # Mock dash components for testing
        class MockDash:
            def __init__(self, *args, **kwargs):
                self.layout = None
                self.callbacks = []
            
            def callback(self, *args, **kwargs):
                def decorator(func):
                    self.callbacks.append(func)
                    return func
                return decorator
            
            def run_server(self, *args, **kwargs):
                print("Mock server would start here")
        
        class MockHtml:
            def Div(self, *args, **kwargs):
                return f"<div>{args}</div>"
            
            def Header(self, *args, **kwargs):
                return f"<header>{args}</header>"
            
            def Link(self, *args, **kwargs):
                return f"<link {kwargs}>"
            
            def Img(self, *args, **kwargs):
                return f"<img {kwargs}>"
            
            def H1(self, *args, **kwargs):
                return f"<h1>{args}</h1>"
            
            def Button(self, *args, **kwargs):
                return f"<button {kwargs}>{args}</button>"
            
            def Script(self, *args, **kwargs):
                return f"<script {kwargs}>{args}</script>"
        
        class MockDcc:
            def Tabs(self, *args, **kwargs):
                return f"<tabs {kwargs}>{args}</tabs>"
            
            def Tab(self, *args, **kwargs):
                return f"<tab {kwargs}>{args}</tab>"
        
        # Mock the imports
        sys.modules['dash'] = MockDash()
        sys.modules['dash.html'] = MockHtml()
        sys.modules['dash.dcc'] = MockDcc()
        sys.modules['dash.dependencies'] = type('MockDeps', (), {
            'Input': lambda x: f"input:{x}",
            'Output': lambda x: f"output:{x}"
        })()
        
        # Now try to import the dashboard
        from main_dashboard import app, server, plugins
        print(f"✓ Dashboard imported successfully")
        print(f"✓ Flask server created")
        print(f"✓ Dash app created")
        print(f"✓ Plugins loaded: {len(plugins)}")
        return True
    except Exception as e:
        print(f"✗ Dashboard import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_static_files():
    """Test that static files exist."""
    print("\nTesting static files...")
    
    static_files = [
        "static/css/dashboard_light.css",
        "static/css/dashboard_dark.css",
        "static/js/sidebar_toggle.js",
        "static/js/theme_toggle.js",
        "static/icons/favicon.ico",
        "static/images/logo.png"
    ]
    
    all_exist = True
    for file_path in static_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path} exists")
        else:
            print(f"✗ {file_path} missing")
            all_exist = False
    
    return all_exist

def main():
    """Run all tests."""
    print("Cancer Genomics Dashboard - Test Suite")
    print("=" * 50)
    
    tests = [
        test_settings,
        test_plugin_registry,
        test_static_files,
        test_dashboard_import
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Dashboard is ready to use.")
        return True
    else:
        print("❌ Some tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
