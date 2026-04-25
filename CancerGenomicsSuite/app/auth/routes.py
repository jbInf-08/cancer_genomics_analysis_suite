#!/usr/bin/env python3
"""
Authentication Routes for Cancer Genomics Analysis Suite

This module provides authentication-related routes including login, logout,
registration, and user management functionality.
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden

# Import app components
from .. import db
from .models import User

# Import auth functions and utilities
try:
    from . import (
        authenticate_user, create_user, update_user_password, create_session, 
        destroy_session, validate_session, log_auth_event, require_permission,
        require_admin, ValidationError, AuthenticationError, AuthorizationError
    )
except ImportError:
    # Fallback for circular import issues
    authenticate_user = None
    create_user = None
    update_user_password = None
    create_session = None
    destroy_session = None
    validate_session = None
    log_auth_event = lambda event, user, details=None: None
    require_permission = lambda perm: lambda f: f
    require_admin = lambda f: f
    ValidationError = Exception
    AuthenticationError = Exception
    AuthorizationError = Exception

# Create blueprint
auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["POST"])
def login():
    """Handle user login."""
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"message": "Username and password are required"}), 400

        # Find user by username
        user = User.query.filter_by(username=username).first()

        # Check credentials
        if not user or not check_password_hash(user.password_hash, password):
            # Log failed login attempt
            log_auth_event('failed_login', username or 'unknown', {'reason': 'invalid_credentials'})
            return jsonify({"message": "Invalid credentials"}), 401

        # Check if user is active
        if not user.is_active:
            log_auth_event('failed_login', username, {'reason': 'account_inactive'})
            return jsonify({"message": "Account is inactive"}), 401

        # Update last login
        from datetime import datetime
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Log successful login
        log_auth_event('login', username)

        return jsonify({
            "message": "Login successful",
            "user_id": user.id,
            "username": user.username,
            "is_admin": user.is_admin
        }), 200

    except Exception as e:
        return jsonify({"message": "Login failed"}), 500

@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Handle user logout."""
    try:
        # Log logout event
        log_auth_event('logout', 'user')
        
        return jsonify({"message": "Logout successful"}), 200
        
    except Exception as e:
        return jsonify({"message": "Logout failed"}), 500

@auth_bp.route("/register", methods=["POST"])
def register():
    """Handle user registration."""
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        email = data.get("email", "")
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")

        # Validate required fields
        if not username or not password:
            return jsonify({"message": "Username and password are required"}), 400

        # Check if user already exists
        if User.query.filter_by(username=username).first():
            return jsonify({"message": "User already exists"}), 400

        # Create new user with enhanced functionality
        try:
            # Use the enhanced create_user function for better validation
            new_user = create_user(
                username=username,
                email=email or f"{username}@example.com",  # Default email if not provided
                password=password,
                first_name=first_name or None,
                last_name=last_name or None,
                role='viewer'  # Default role
            )
            
            # Log registration event
            log_auth_event('user_registered', username, {'email': email})
            
            return jsonify({
                "message": "User registered successfully",
                "user_id": new_user.id,
                "username": new_user.username
            }), 201
            
        except ValidationError as e:
            return jsonify({"message": str(e)}), 400
        except Exception as e:
            return jsonify({"message": "Registration failed"}), 500

    except Exception as e:
        return jsonify({"message": "Invalid request data"}), 400

@auth_bp.route("/status", methods=["GET"])
def auth_status():
    """Get authentication status."""
    try:
        return jsonify({
            "message": "Authentication system is operational",
            "endpoints": {
                "login": "/auth/login",
                "register": "/auth/register", 
                "logout": "/auth/logout",
                "status": "/auth/status"
            }
        }), 200
        
    except Exception as e:
        return jsonify({"message": "Status check failed"}), 500
