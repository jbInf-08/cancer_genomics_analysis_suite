#!/usr/bin/env python3
"""
Authentication Package for Cancer Genomics Analysis Suite

This package provides comprehensive authentication and authorization functionality
for the cancer genomics analysis suite. It includes user management, session
handling, security utilities, and integration with Flask-Login.

Features:
- User authentication and session management
- Password hashing and validation
- Role-based access control
- Security utilities and decorators
- Input validation and sanitization
- Audit logging for security events
- Integration with Flask-Login
- JWT token support (optional)
- Two-factor authentication support (optional)

Usage:
    from app.auth import login_user, logout_user, require_auth
    from app.auth.models import User
    from app.auth.utils import hash_password, verify_password
"""

import os
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Dict, Any, List, Union

from flask import current_app, request, session, g, jsonify, abort
from flask_login import current_user, login_required, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import Unauthorized, Forbidden

# Configure logging
logger = logging.getLogger(__name__)

# Import auth models and routes
from .models import User
from .routes import auth_bp

# Security configuration
DEFAULT_PASSWORD_MIN_LENGTH = 8
DEFAULT_SESSION_TIMEOUT = 3600  # 1 hour
DEFAULT_MAX_LOGIN_ATTEMPTS = 5
DEFAULT_LOCKOUT_DURATION = 900  # 15 minutes

# Password requirements
PASSWORD_REQUIREMENTS = {
    'min_length': DEFAULT_PASSWORD_MIN_LENGTH,
    'require_uppercase': True,
    'require_lowercase': True,
    'require_numbers': True,
    'require_special_chars': True,
    'forbidden_patterns': ['password', '123456', 'qwerty', 'admin']
}

# Role definitions
ROLES = {
    'admin': {
        'level': 100,
        'permissions': ['*'],  # All permissions
        'description': 'System administrator with full access'
    },
    'researcher': {
        'level': 80,
        'permissions': [
            'read_data', 'write_data', 'run_analysis', 'export_results',
            'manage_own_data', 'view_reports'
        ],
        'description': 'Research scientist with full analysis capabilities'
    },
    'analyst': {
        'level': 60,
        'permissions': [
            'read_data', 'run_analysis', 'export_results', 'view_reports'
        ],
        'description': 'Data analyst with analysis and reporting capabilities'
    },
    'viewer': {
        'level': 40,
        'permissions': ['read_data', 'view_reports'],
        'description': 'Read-only access to data and reports'
    },
    'guest': {
        'level': 20,
        'permissions': ['view_public_data'],
        'description': 'Limited access to public data only'
    }
}

# Permission definitions
PERMISSIONS = {
    'read_data': 'Read genomic and clinical data',
    'write_data': 'Upload and modify data',
    'run_analysis': 'Execute analysis workflows',
    'export_results': 'Export analysis results',
    'manage_own_data': 'Manage personal data and projects',
    'view_reports': 'View generated reports',
    'manage_users': 'Manage user accounts and permissions',
    'system_admin': 'System administration tasks',
    'view_public_data': 'View publicly available data',
    'api_access': 'Access to API endpoints'
}


class AuthError(Exception):
    """Base exception for authentication errors."""
    pass


class AuthenticationError(AuthError):
    """Exception raised for authentication failures."""
    pass


class AuthorizationError(AuthError):
    """Exception raised for authorization failures."""
    pass


class ValidationError(AuthError):
    """Exception raised for input validation failures."""
    pass


class SecurityError(AuthError):
    """Exception raised for security-related errors."""
    pass


# Utility Functions
def hash_password(password: str) -> str:
    """
    Hash a password using Werkzeug's secure hashing.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password
        password_hash: Hashed password to verify against
        
    Returns:
        True if password matches, False otherwise
    """
    return check_password_hash(password_hash, password)


def validate_password(password: str) -> Dict[str, Any]:
    """
    Validate password against security requirements.
    
    Args:
        password: Password to validate
        
    Returns:
        Dictionary with validation results
    """
    errors = []
    warnings = []
    
    # Check minimum length
    if len(password) < PASSWORD_REQUIREMENTS['min_length']:
        errors.append(f"Password must be at least {PASSWORD_REQUIREMENTS['min_length']} characters long")
    
    # Check for uppercase letters
    if PASSWORD_REQUIREMENTS['require_uppercase'] and not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    
    # Check for lowercase letters
    if PASSWORD_REQUIREMENTS['require_lowercase'] and not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    
    # Check for numbers
    if PASSWORD_REQUIREMENTS['require_numbers'] and not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")
    
    # Check for special characters
    if PASSWORD_REQUIREMENTS['require_special_chars']:
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            errors.append("Password must contain at least one special character")
    
    # Check for forbidden patterns
    password_lower = password.lower()
    for pattern in PASSWORD_REQUIREMENTS['forbidden_patterns']:
        if pattern in password_lower:
            errors.append(f"Password cannot contain common patterns like '{pattern}'")
    
    # Additional security checks
    if len(password) < 12:
        warnings.append("Consider using a longer password (12+ characters) for better security")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'strength': calculate_password_strength(password)
    }


def calculate_password_strength(password: str) -> str:
    """
    Calculate password strength.
    
    Args:
        password: Password to analyze
        
    Returns:
        Strength level: 'weak', 'medium', 'strong', or 'very_strong'
    """
    score = 0
    
    # Length scoring
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if len(password) >= 16:
        score += 1
    
    # Character variety scoring
    if any(c.isupper() for c in password):
        score += 1
    if any(c.islower() for c in password):
        score += 1
    if any(c.isdigit() for c in password):
        score += 1
    if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        score += 1
    
    # Determine strength level
    if score < 3:
        return 'weak'
    elif score < 5:
        return 'medium'
    elif score < 7:
        return 'strong'
    else:
        return 'very_strong'


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Length of the token in bytes
        
    Returns:
        Hex-encoded random token
    """
    return secrets.token_hex(length)


def generate_api_key() -> str:
    """
    Generate a secure API key.
    
    Returns:
        API key string
    """
    return f"cg_{secrets.token_urlsafe(32)}"


def sanitize_input(input_string: str) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        input_string: Input string to sanitize
        
    Returns:
        Sanitized string
    """
    if not input_string:
        return ""
    
    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '|', '`', '$']
    sanitized = input_string
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
    
    # Limit length
    if len(sanitized) > 1000:
        sanitized = sanitized[:1000]
    
    return sanitized.strip()


# Authentication Functions
def authenticate_user(username: str, password: str) -> Optional[User]:
    """
    Authenticate a user with username and password.
    
    Args:
        username: Username or email
        password: Plain text password
        
    Returns:
        User object if authentication successful, None otherwise
    """
    try:
        # Find user by username or email
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user:
            logger.warning(f"Authentication failed: user '{username}' not found")
            return None
        
        if not user.is_active:
            logger.warning(f"Authentication failed: user '{username}' is inactive")
            return None
        
        # Check password
        if not verify_password(password, user.password_hash):
            logger.warning(f"Authentication failed: invalid password for user '{username}'")
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        user.save()
        
        logger.info(f"User '{username}' authenticated successfully")
        return user
        
    except Exception as e:
        logger.error(f"Authentication error for user '{username}': {e}")
        return None


def create_user(username: str, email: str, password: str, 
                first_name: str = None, last_name: str = None,
                role: str = 'viewer') -> User:
    """
    Create a new user account.
    
    Args:
        username: Username
        email: Email address
        password: Plain text password
        first_name: First name (optional)
        last_name: Last name (optional)
        role: User role (default: 'viewer')
        
    Returns:
        Created User object
        
    Raises:
        ValidationError: If validation fails
        SecurityError: If security checks fail
    """
    # Validate inputs
    if not username or not email or not password:
        raise ValidationError("Username, email, and password are required")
    
    # Sanitize inputs
    username = sanitize_input(username)
    email = sanitize_input(email)
    first_name = sanitize_input(first_name) if first_name else None
    last_name = sanitize_input(last_name) if last_name else None
    
    # Validate password
    password_validation = validate_password(password)
    if not password_validation['valid']:
        raise ValidationError(f"Password validation failed: {', '.join(password_validation['errors'])}")
    
    # Check if user already exists
    if User.query.filter_by(username=username).first():
        raise ValidationError("Username already exists")
    
    if User.query.filter_by(email=email).first():
        raise ValidationError("Email already exists")
    
    # Validate role
    if role not in ROLES:
        raise ValidationError(f"Invalid role: {role}")
    
    try:
        # Create user
        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            is_active=True,
            is_admin=(role == 'admin')
        )
        
        user.save()
        
        logger.info(f"User '{username}' created successfully with role '{role}'")
        return user
        
    except Exception as e:
        logger.error(f"Error creating user '{username}': {e}")
        raise SecurityError(f"Failed to create user: {str(e)}")


def update_user_password(user: User, old_password: str, new_password: str) -> bool:
    """
    Update user password.
    
    Args:
        user: User object
        old_password: Current password
        new_password: New password
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Verify old password
        if not verify_password(old_password, user.password_hash):
            logger.warning(f"Password update failed: invalid old password for user '{user.username}'")
            return False
        
        # Validate new password
        password_validation = validate_password(new_password)
        if not password_validation['valid']:
            logger.warning(f"Password update failed: validation failed for user '{user.username}'")
            return False
        
        # Update password
        user.password_hash = hash_password(new_password)
        user.save()
        
        logger.info(f"Password updated successfully for user '{user.username}'")
        return True
        
    except Exception as e:
        logger.error(f"Error updating password for user '{user.username}': {e}")
        return False


# Authorization Functions
def has_permission(user: User, permission: str) -> bool:
    """
    Check if user has a specific permission.
    
    Args:
        user: User object
        permission: Permission to check
        
    Returns:
        True if user has permission, False otherwise
    """
    if not user or not user.is_active:
        return False
    
    # Admin users have all permissions
    if user.is_admin:
        return True
    
    # Get user role (simplified - in real implementation, you'd have a role field)
    user_role = 'admin' if user.is_admin else 'researcher'  # Default role
    
    if user_role in ROLES:
        role_permissions = ROLES[user_role]['permissions']
        return '*' in role_permissions or permission in role_permissions
    
    return False


def require_permission(permission: str):
    """
    Decorator to require a specific permission.
    
    Args:
        permission: Required permission
        
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if not has_permission(current_user, permission):
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_role(role: str):
    """
    Decorator to require a specific role.
    
    Args:
        role: Required role
        
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            # Check role level (higher number = more privileges)
            user_role = 'admin' if current_user.is_admin else 'researcher'
            required_level = ROLES.get(role, {}).get('level', 0)
            user_level = ROLES.get(user_role, {}).get('level', 0)
            
            if user_level < required_level:
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_admin(f):
    """
    Decorator to require admin privileges.
    
    Args:
        f: Function to decorate
        
    Returns:
        Decorated function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        
        if not current_user.is_admin:
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function


# Session Management
def create_session(user: User, remember: bool = False) -> Dict[str, Any]:
    """
    Create a user session.
    
    Args:
        user: User object
        remember: Whether to remember the session
        
    Returns:
        Session information
    """
    try:
        # Generate session token
        session_token = generate_secure_token()
        
        # Set session data
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = 'admin' if user.is_admin else 'researcher'
        session['session_token'] = session_token
        session['created_at'] = datetime.utcnow().isoformat()
        session.permanent = remember
        
        # Log session creation
        logger.info(f"Session created for user '{user.username}'")
        
        return {
            'user_id': user.id,
            'username': user.username,
            'role': session['role'],
            'session_token': session_token,
            'remember': remember
        }
        
    except Exception as e:
        logger.error(f"Error creating session for user '{user.username}': {e}")
        raise SecurityError(f"Failed to create session: {str(e)}")


def destroy_session():
    """
    Destroy the current session.
    """
    try:
        username = session.get('username', 'unknown')
        session.clear()
        logger.info(f"Session destroyed for user '{username}'")
    except Exception as e:
        logger.error(f"Error destroying session: {e}")


def validate_session() -> bool:
    """
    Validate the current session.
    
    Returns:
        True if session is valid, False otherwise
    """
    try:
        if not session.get('user_id'):
            return False
        
        # Check session timeout
        created_at_str = session.get('created_at')
        if created_at_str:
            created_at = datetime.fromisoformat(created_at_str)
            if datetime.utcnow() - created_at > timedelta(seconds=DEFAULT_SESSION_TIMEOUT):
                logger.warning("Session expired")
                return False
        
        # Verify user still exists and is active
        user = User.query.get(session['user_id'])
        if not user or not user.is_active:
            logger.warning("Session invalid: user not found or inactive")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating session: {e}")
        return False


# Audit Logging
def log_auth_event(event_type: str, username: str, details: Dict[str, Any] = None):
    """
    Log authentication events for security auditing.
    
    Args:
        event_type: Type of event (login, logout, failed_login, etc.)
        username: Username involved
        details: Additional event details
    """
    try:
        event_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'username': username,
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None,
            'details': details or {}
        }
        
        logger.info(f"Auth event: {event_type} for user '{username}' - {event_data}")
        
        # In a real implementation, you would store this in a database
        # for security auditing and compliance
        
    except Exception as e:
        logger.error(f"Error logging auth event: {e}")


# API Key Management
def generate_user_api_key(user: User) -> str:
    """
    Generate an API key for a user.
    
    Args:
        user: User object
        
    Returns:
        API key string
    """
    try:
        api_key = generate_api_key()
        # In a real implementation, you would store this in the database
        # with proper expiration and access controls
        
        log_auth_event('api_key_generated', user.username, {'api_key': api_key})
        return api_key
        
    except Exception as e:
        logger.error(f"Error generating API key for user '{user.username}': {e}")
        raise SecurityError(f"Failed to generate API key: {str(e)}")


def validate_api_key(api_key: str) -> Optional[User]:
    """
    Validate an API key and return the associated user.
    
    Args:
        api_key: API key to validate
        
    Returns:
        User object if valid, None otherwise
    """
    try:
        # In a real implementation, you would look up the API key in the database
        # and return the associated user
        
        if not api_key or not api_key.startswith('cg_'):
            return None
        
        # For now, return None (API key validation not implemented)
        return None
        
    except Exception as e:
        logger.error(f"Error validating API key: {e}")
        return None


# Export public API
__all__ = [
    # Models
    'User',
    
    # Blueprints
    'auth_bp',
    
    # Exceptions
    'AuthError',
    'AuthenticationError', 
    'AuthorizationError',
    'ValidationError',
    'SecurityError',
    
    # Utility Functions
    'hash_password',
    'verify_password',
    'validate_password',
    'calculate_password_strength',
    'generate_secure_token',
    'generate_api_key',
    'sanitize_input',
    
    # Authentication Functions
    'authenticate_user',
    'create_user',
    'update_user_password',
    
    # Authorization Functions
    'has_permission',
    'require_permission',
    'require_role',
    'require_admin',
    
    # Session Management
    'create_session',
    'destroy_session',
    'validate_session',
    
    # Audit Logging
    'log_auth_event',
    
    # API Key Management
    'generate_user_api_key',
    'validate_api_key',
    
    # Configuration
    'ROLES',
    'PERMISSIONS',
    'PASSWORD_REQUIREMENTS'
]
