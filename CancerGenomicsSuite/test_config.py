#!/usr/bin/env python3
"""Test the configuration package."""

def test_config_import():
    """Test importing the configuration package."""
    print("Testing configuration package import...")
    
    try:
        from CancerGenomicsSuite.config import settings, validate_configuration
        print(f"✓ Configuration imported successfully")
        print(f"✓ App name: {settings.app_name}")
        print(f"✓ App version: {settings.app_version}")
        print(f"✓ Environment: {settings.flask_env}")
        print(f"✓ Host: {settings.host}")
        print(f"✓ Port: {settings.port}")
        print(f"✓ Debug mode: {settings.dash_debug_mode}")
        return True
    except Exception as e:
        print(f"✗ Configuration import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config_validation():
    """Test configuration validation."""
    print("\nTesting configuration validation...")
    
    try:
        from CancerGenomicsSuite.config import validate_configuration
        results = validate_configuration()
        
        print(f"✓ Configuration validation completed")
        print(f"✓ Valid: {results['valid']}")
        print(f"✓ Errors: {len(results['errors'])}")
        print(f"✓ Warnings: {len(results['warnings'])}")
        print(f"✓ Info messages: {len(results['info'])}")
        
        if results['errors']:
            print("Errors:")
            for error in results['errors']:
                print(f"  - {error}")
        
        if results['warnings']:
            print("Warnings:")
            for warning in results['warnings']:
                print(f"  - {warning}")
        
        if results['info']:
            print("Info:")
            for info in results['info']:
                print(f"  - {info}")
        
        return results['valid']
    except Exception as e:
        print(f"✗ Configuration validation failed: {e}")
        return False

def test_config_utilities():
    """Test configuration utility functions."""
    print("\nTesting configuration utilities...")
    
    try:
        from CancerGenomicsSuite.config import (
            get_environment, is_development, is_production, is_testing,
            get_database_url, get_redis_url, get_feature_status
        )
        
        print(f"✓ Environment: {get_environment()}")
        print(f"✓ Is development: {is_development()}")
        print(f"✓ Is production: {is_production()}")
        print(f"✓ Is testing: {is_testing()}")
        print(f"✓ Database URL: {get_database_url()}")
        print(f"✓ Redis URL: {get_redis_url()}")
        print(f"✓ Gene expression analysis enabled: {get_feature_status('enable_gene_expression_analysis')}")
        
        return True
    except Exception as e:
        print(f"✗ Configuration utilities test failed: {e}")
        return False

def main():
    """Run all configuration tests."""
    print("Cancer Genomics Configuration - Test Suite")
    print("=" * 50)
    
    tests = [
        test_config_import,
        test_config_validation,
        test_config_utilities
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
        print("🎉 All configuration tests passed!")
        return True
    else:
        print("❌ Some configuration tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
