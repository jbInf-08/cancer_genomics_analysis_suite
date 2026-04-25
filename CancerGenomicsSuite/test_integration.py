#!/usr/bin/env python3
"""
Test script for the integrated biomarker analysis system.

This script tests the integration between CGAS and biomarker_identifier
to ensure everything works properly.
"""

import sys
import pandas as pd
import numpy as np
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_imports():
    """Test that all integration modules can be imported."""
    print("🧪 Testing imports...")
    
    try:
        from CancerGenomicsSuite.integrations import (
            UnifiedBiomarkerInterface,
            BiomarkerAnalysisOptions,
            discover_biomarkers_compatible,
            get_compatibility_manager,
            get_config
        )
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_configuration():
    """Test configuration loading."""
    print("\n🧪 Testing configuration...")
    
    try:
        from CancerGenomicsSuite.integrations import get_config
        config = get_config()
        print(f"✅ Configuration loaded: {type(config).__name__}")
        print(f"   Biomarker Identifier URL: {config.biomarker_identifier.url}")
        print(f"   CGAS enabled: {config.cgas.enabled}")
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False


def test_compatibility_manager():
    """Test the compatibility manager."""
    print("\n🧪 Testing compatibility manager...")
    
    try:
        from CancerGenomicsSuite.integrations import get_compatibility_manager
        manager = get_compatibility_manager()
        
        available_services = manager.get_available_services()
        print(f"✅ Compatibility manager initialized")
        print(f"   Available services: {available_services}")
        
        return True
    except Exception as e:
        print(f"❌ Compatibility manager error: {e}")
        return False


def test_unified_interface():
    """Test the unified interface."""
    print("\n🧪 Testing unified interface...")
    
    try:
        from CancerGenomicsSuite.integrations import (
            UnifiedBiomarkerInterface,
            BiomarkerAnalysisOptions,
        )
        
        # Create interface
        interface = UnifiedBiomarkerInterface()
        print("✅ Unified interface created")
        
        # Check service status
        status = interface.get_service_status()
        print(f"   Service status retrieved: {len(status)} components")
        
        # Test analysis options
        options = BiomarkerAnalysisOptions(
            p_value_threshold=0.05,
            effect_size_threshold=0.2
        )
        print(f"✅ Analysis options created: p-value threshold = {options.p_value_threshold}")
        
        return True
    except Exception as e:
        print(f"❌ Unified interface error: {e}")
        return False


def create_sample_biomarker_data():
    """Create sample data for biomarker discovery (not a pytest test)."""
    print("\n🧪 Testing data creation...")
    
    try:
        # Create sample data
        np.random.seed(42)
        n_samples, n_features = 50, 25
        
        data = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f"Gene_{i}" for i in range(n_features)],
            index=[f"Sample_{i}" for i in range(n_samples)]
        )
        
        labels = np.random.choice([0, 1], size=n_samples, p=[0.6, 0.4])
        
        print(f"✅ Sample data created: {data.shape[0]} samples, {data.shape[1]} features")
        print(f"   Labels: {np.sum(labels)} positive, {n_samples - np.sum(labels)} negative")
        
        return data, labels
    except Exception as e:
        print(f"❌ Data creation error: {e}")
        return None, None


def run_biomarker_discovery(data, labels):
    """Run biomarker discovery with sample data (not a pytest test)."""
    print("\n🧪 Testing biomarker discovery...")
    
    if data is None or labels is None:
        print("❌ No data available for testing")
        return False
    
    try:
        from CancerGenomicsSuite.integrations import discover_biomarkers_compatible

        # Test biomarker discovery
        biomarkers = discover_biomarkers_compatible(data, labels)
        print(f"✅ Biomarker discovery completed")
        print(f"   Found {len(biomarkers)} biomarkers")
        
        if biomarkers:
            # Show best biomarker
            best = min(biomarkers, key=lambda x: x.get('p_value', 1.0))
            print(f"   Best biomarker: {best.get('name', 'Unknown')} "
                  f"(p-value: {best.get('p_value', 'N/A'):.6f})")
        
        return True
    except Exception as e:
        print(f"❌ Biomarker discovery error: {e}")
        return False


def test_service_status():
    """Test service status checking."""
    print("\n🧪 Testing service status...")
    
    try:
        from CancerGenomicsSuite.integrations import UnifiedBiomarkerInterface

        interface = UnifiedBiomarkerInterface()
        status = interface.get_service_status()
        
        print("✅ Service status retrieved:")
        
        # Gateway status
        gateway_status = status.get('gateway_status', {})
        for service, info in gateway_status.items():
            available = "✅" if info.get('available', False) else "❌"
            response_time = info.get('response_time', 0)
            print(f"   {available} {service}: {response_time:.3f}s")
        
        # Discovery status
        discovery_status = status.get('discovery_status', {})
        total_services = discovery_status.get('total_services', 0)
        healthy_services = discovery_status.get('healthy_services', 0)
        print(f"   Discovery: {healthy_services}/{total_services} services healthy")
        
        return True
    except Exception as e:
        print(f"❌ Service status error: {e}")
        return False


def test_error_handling():
    """Test error handling with invalid data."""
    print("\n🧪 Testing error handling...")
    
    try:
        from CancerGenomicsSuite.integrations import discover_biomarkers_compatible

        # Test with empty data
        try:
            biomarkers = discover_biomarkers_compatible(pd.DataFrame(), [])
            print("❌ Should have failed with empty data")
            return False
        except Exception as e:
            print(f"✅ Correctly handled empty data: {type(e).__name__}")
        
        # Test with mismatched data and labels
        try:
            data = pd.DataFrame(np.random.randn(10, 5))
            labels = [0, 1]  # Wrong length
            biomarkers = discover_biomarkers_compatible(data, labels)
            print("❌ Should have failed with mismatched data/labels")
            return False
        except Exception as e:
            print(f"✅ Correctly handled mismatched data: {type(e).__name__}")
        
        return True
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


def run_all_tests():
    """Run all tests."""
    print("🧬 Integrated Biomarker Analysis System Tests")
    print("=" * 60)
    
    tests = [
        ("Import Test", test_imports),
        ("Configuration Test", test_configuration),
        ("Compatibility Manager Test", test_compatibility_manager),
        ("Unified Interface Test", test_unified_interface),
        ("Service Status Test", test_service_status),
        ("Error Handling Test", test_error_handling)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Sample data creation and biomarker discovery
    data, labels = create_sample_biomarker_data()
    if data is not None and labels is not None:
        biomarker_result = run_biomarker_discovery(data, labels)
        results.append(("Biomarker Discovery Test", biomarker_result))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! The integration is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please check the errors above.")
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
