#!/usr/bin/env python3
"""Test the settings API configuration."""

def test_api_tokens():
    """Test that API tokens are properly configured."""
    print("Testing API token configuration...")
    
    try:
        from config import settings
        
        # Test basic API configuration
        print(f"✓ COSMIC API Token: {'Set' if settings.external_apis.cosmic_api_token else 'Not set'}")
        print(f"✓ COSMIC API Key: {'Set' if settings.external_apis.cosmic_api_key else 'Not set'}")
        print(f"✓ Scopus API Key: {'Set' if settings.external_apis.scopus_api_key else 'Not set'}")
        print(f"✓ ENCODE API Base: {settings.external_apis.encode_api_base}")
        print(f"✓ NCBI API Key: {'Set' if settings.external_apis.ncbi_api_key else 'Not set'}")
        
        # Test API URLs
        print(f"✓ Ensembl API URL: {settings.external_apis.ensembl_api_url}")
        print(f"✓ UniProt API URL: {settings.external_apis.uniprot_api_url}")
        print(f"✓ PubMed API URL: {settings.external_apis.pubmed_api_url}")
        
        return True
    except Exception as e:
        print(f"✗ API configuration test failed: {e}")
        return False

def test_simple_config_compatibility():
    """Test that the simple configuration works with the original structure."""
    print("\nTesting simple configuration compatibility...")
    
    try:
        from config import settings
        
        # Test original Config class attributes
        if hasattr(settings, 'APP_NAME'):
            print(f"✓ APP_NAME: {settings.APP_NAME}")
        if hasattr(settings, 'SQLALCHEMY_DATABASE_URI'):
            print(f"✓ SQLALCHEMY_DATABASE_URI: {settings.SQLALCHEMY_DATABASE_URI[:30]}...")
        if hasattr(settings, 'CELERY_BROKER_URL'):
            print(f"✓ CELERY_BROKER_URL: {settings.CELERY_BROKER_URL}")
        if hasattr(settings, 'SECRET_KEY'):
            print(f"✓ SECRET_KEY: {'Set' if settings.SECRET_KEY else 'Not set'}")
        
        # Test API tokens in original format
        if hasattr(settings, 'COSMIC_API_TOKEN'):
            print(f"✓ COSMIC_API_TOKEN: {'Set' if settings.COSMIC_API_TOKEN else 'Not set'}")
        if hasattr(settings, 'SCOPUS_API_KEY'):
            print(f"✓ SCOPUS_API_KEY: {'Set' if settings.SCOPUS_API_KEY else 'Not set'}")
        if hasattr(settings, 'ENCODE_API_BASE'):
            print(f"✓ ENCODE_API_BASE: {settings.ENCODE_API_BASE}")
        
        return True
    except Exception as e:
        print(f"✗ Simple configuration compatibility test failed: {e}")
        return False

def main():
    """Run all settings API tests."""
    print("Cancer Genomics Settings API - Test Suite")
    print("=" * 50)
    
    tests = [
        test_api_tokens,
        test_simple_config_compatibility
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
        print("🎉 All settings API tests passed!")
        return True
    else:
        print("❌ Some settings API tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
