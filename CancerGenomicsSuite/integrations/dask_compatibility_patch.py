"""
Dask compatibility patch for pandas 2.1.1 compatibility issue.

This module patches the dask compatibility issue that causes:
TypeError: descriptor '__call__' for 'type' objects doesn't apply to a 'property' object
"""

import sys
import inspect
from typing import Any, Callable


def patch_dask_compatibility():
    """Patch dask compatibility issues with pandas 2.1.1."""
    
    # Check if we're dealing with the problematic dask version
    try:
        import dask
        if dask.__version__ == "2023.11.0":
            print("Applying dask compatibility patch for version 2023.11.0")
            _apply_dask_patch()
    except ImportError:
        pass


def _apply_dask_patch():
    """Apply the specific patch for dask 2023.11.0."""
    
    # Patch the problematic function in dask.utils
    try:
        import dask.utils
        
        # Store the original get_named_args function
        original_get_named_args = dask.utils.get_named_args
        
        def patched_get_named_args(func: Callable) -> list:
            """Patched version of get_named_args that handles property objects."""
            try:
                # Try the original function first
                return original_get_named_args(func)
            except TypeError as e:
                if "descriptor '__call__' for 'type' objects doesn't apply to a 'property' object" in str(e):
                    # Handle the specific error case
                    try:
                        # For property objects, return empty list
                        if isinstance(func, property):
                            return []
                        
                        # Try to get signature with different approach
                        sig = inspect.signature(func, follow_wrapped=False)
                        return list(sig.parameters.keys())
                    except Exception:
                        # If all else fails, return empty list
                        return []
                else:
                    # Re-raise if it's a different error
                    raise
        
        # Apply the patch
        dask.utils.get_named_args = patched_get_named_args
        try:
            print("Applied dask.utils.get_named_args patch")
        except UnicodeEncodeError:
            print("[OK] Applied dask.utils.get_named_args patch")
        
    except Exception as e:
        error_msg = str(e)
        try:
            print(f"Warning: Could not apply dask patch: {error_msg}")
        except UnicodeEncodeError:
            print(f"Warning: Could not apply dask patch: {error_msg.encode('ascii', 'replace').decode('ascii')}")


def patch_lightgbm_import():
    """Patch lightgbm import to handle dask compatibility issues."""
    
    # Apply dask patch before importing lightgbm
    patch_dask_compatibility()
    
    try:
        import lightgbm
        try:
            print(f"LightGBM imported successfully (version: {lightgbm.__version__})")
        except UnicodeEncodeError:
            print(f"[OK] LightGBM imported successfully (version: {lightgbm.__version__})")
        return True
    except Exception as e:
        error_msg = str(e)
        try:
            print(f"LightGBM import failed: {error_msg}")
        except UnicodeEncodeError:
            print(f"[ERROR] LightGBM import failed: {error_msg.encode('ascii', 'replace').decode('ascii')}")
        return False


def patch_xgboost_import():
    """Patch xgboost import."""
    
    try:
        import xgboost
        try:
            print(f"XGBoost imported successfully (version: {xgboost.__version__})")
        except UnicodeEncodeError:
            print(f"[OK] XGBoost imported successfully (version: {xgboost.__version__})")
        return True
    except Exception as e:
        error_msg = str(e)
        try:
            print(f"XGBoost import failed: {error_msg}")
        except UnicodeEncodeError:
            print(f"[ERROR] XGBoost import failed: {error_msg.encode('ascii', 'replace').decode('ascii')}")
        return False


# Apply patches when this module is imported
patch_dask_compatibility()
