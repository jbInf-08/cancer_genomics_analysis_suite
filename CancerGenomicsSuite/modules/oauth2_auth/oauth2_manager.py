#!/usr/bin/env python3
"""
OAuth2 Manager

This module provides comprehensive OAuth2 authentication management
for the cancer genomics analysis suite.
"""

import logging
import json
import time
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timedelta
import threading
from urllib.parse import urlencode, parse_qs, urlparse
import secrets

try:
    from authlib.integrations.flask_client import OAuth
    from authlib.integrations.requests_client import OAuth2Session
    from authlib.oauth2.rfc6749 import OAuth2Token
    from jose import jwt, JWTError
    OAUTH2_AVAILABLE = True
except ImportError:
    OAUTH2_AVAILABLE = False
    logging.warning("OAuth2 libraries not available. Install authlib and python-jose packages.")

from .keycloak_client import KeycloakClient
from .auth0_client import Auth0Client
from .token_handler import TokenHandler
from .user_manager import UserManager

logger = logging.getLogger(__name__)


class OAuth2Manager:
    """
    OAuth2 authentication manager for cancer genomics analysis suite.
    
    Provides functionality to:
    - Manage OAuth2 providers (Keycloak, Auth0)
    - Handle authentication flows
    - Manage tokens and sessions
    - Integrate with user management
    - Provide authentication middleware
    """
    
    def __init__(
        self,
        app=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize OAuth2 manager.
        
        Args:
            app: Flask application instance
            config: OAuth2 configuration
        """
        if not OAUTH2_AVAILABLE:
            raise ImportError("OAuth2 libraries not available. Install authlib and python-jose packages.")
        
        self.app = app
        self.config = config or {}
        
        # OAuth2 providers
        self.providers = {}
        self.active_provider = None
        
        # OAuth2 clients
        self.oauth = None
        self.keycloak_client = None
        self.auth0_client = None
        
        # Token and session management
        self.token_handler = TokenHandler(self.config.get("token_config", {}))
        self.user_manager = UserManager(self.config.get("user_config", {}))
        
        # Authentication state
        self.sessions = {}
        self.session_timeout = self.config.get("session_timeout", 3600)  # 1 hour
        
        # Security settings
        self.csrf_protection = self.config.get("csrf_protection", True)
        self.state_storage = {}
        
        # Initialize if app is provided
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """
        Initialize OAuth2 manager with Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        
        # Initialize OAuth2 client
        self.oauth = OAuth(app)
        
        # Configure providers
        self._configure_providers()
        
        # Register routes
        self._register_routes()
        
        # Initialize token handler
        self.token_handler.init_app(app)
        
        # Initialize user manager
        self.user_manager.init_app(app)
        
        logger.info("OAuth2 manager initialized with Flask app")
    
    def _configure_providers(self):
        """Configure OAuth2 providers."""
        # Configure Keycloak
        keycloak_config = self.config.get("keycloak", {})
        if keycloak_config.get("enabled", False):
            self._configure_keycloak(keycloak_config)
        
        # Configure Auth0
        auth0_config = self.config.get("auth0", {})
        if auth0_config.get("enabled", False):
            self._configure_auth0(auth0_config)
    
    def _configure_keycloak(self, config: Dict[str, Any]):
        """Configure Keycloak provider."""
        try:
            server_url = config["server_url"]
            realm = config["realm"]
            client_id = config["client_id"]
            client_secret = config["client_secret"]
            
            # Configure OAuth2 client
            self.oauth.register(
                name='keycloak',
                client_id=client_id,
                client_secret=client_secret,
                server_metadata_url=f"{server_url}/realms/{realm}/.well-known/openid_configuration",
                client_kwargs={
                    'scope': 'openid email profile'
                }
            )
            
            # Initialize Keycloak client
            self.keycloak_client = KeycloakClient(
                server_url=server_url,
                realm=realm,
                client_id=client_id,
                client_secret=client_secret
            )
            
            self.providers["keycloak"] = {
                "type": "keycloak",
                "client": self.keycloak_client,
                "config": config
            }
            
            if not self.active_provider:
                self.active_provider = "keycloak"
            
            logger.info("Keycloak provider configured")
        
        except Exception as e:
            logger.error(f"Failed to configure Keycloak: {e}")
    
    def _configure_auth0(self, config: Dict[str, Any]):
        """Configure Auth0 provider."""
        try:
            domain = config["domain"]
            client_id = config["client_id"]
            client_secret = config["client_secret"]
            
            # Configure OAuth2 client
            self.oauth.register(
                name='auth0',
                client_id=client_id,
                client_secret=client_secret,
                server_metadata_url=f"https://{domain}/.well-known/openid_configuration",
                client_kwargs={
                    'scope': 'openid email profile'
                }
            )
            
            # Initialize Auth0 client
            self.auth0_client = Auth0Client(
                domain=domain,
                client_id=client_id,
                client_secret=client_secret
            )
            
            self.providers["auth0"] = {
                "type": "auth0",
                "client": self.auth0_client,
                "config": config
            }
            
            if not self.active_provider:
                self.active_provider = "auth0"
            
            logger.info("Auth0 provider configured")
        
        except Exception as e:
            logger.error(f"Failed to configure Auth0: {e}")
    
    def _register_routes(self):
        """Register OAuth2 routes."""
        if not self.app:
            return
        
        @self.app.route('/auth/login')
        def login():
            """Initiate OAuth2 login."""
            if not self.active_provider:
                return {"error": "No OAuth2 provider configured"}, 400
            
            provider = self.providers[self.active_provider]
            
            # Generate state for CSRF protection
            state = secrets.token_urlsafe(32)
            self.state_storage[state] = {
                "created_at": datetime.now(),
                "provider": self.active_provider
            }
            
            # Get authorization URL
            redirect_uri = self._get_redirect_uri()
            auth_url = self.oauth.__getattr__(self.active_provider).authorize_redirect(
                redirect_uri=redirect_uri,
                state=state
            )
            
            return {"auth_url": auth_url.location}
        
        @self.app.route('/auth/callback')
        def callback():
            """Handle OAuth2 callback."""
            try:
                # Get authorization code and state
                code = self.app.request.args.get('code')
                state = self.app.request.args.get('state')
                error = self.app.request.args.get('error')
                
                if error:
                    return {"error": f"Authorization error: {error}"}, 400
                
                if not code or not state:
                    return {"error": "Missing authorization code or state"}, 400
                
                # Verify state
                if not self._verify_state(state):
                    return {"error": "Invalid state parameter"}, 400
                
                # Get provider from state
                state_info = self.state_storage.get(state, {})
                provider_name = state_info.get("provider", self.active_provider)
                
                if provider_name not in self.providers:
                    return {"error": "Invalid provider"}, 400
                
                # Exchange code for token
                provider = self.providers[provider_name]
                token = self.oauth.__getattr__(provider_name).authorize_access_token()
                
                # Get user information
                user_info = self._get_user_info(provider_name, token)
                
                # Create or update user
                user = self.user_manager.create_or_update_user(user_info)
                
                # Create session
                session_id = self._create_session(user, token)
                
                # Clean up state
                del self.state_storage[state]
                
                return {
                    "message": "Authentication successful",
                    "user": {
                        "id": user["id"],
                        "username": user["username"],
                        "email": user["email"],
                        "roles": user.get("roles", [])
                    },
                    "session_id": session_id
                }
            
            except Exception as e:
                logger.error(f"OAuth2 callback error: {e}")
                return {"error": "Authentication failed"}, 500
        
        @self.app.route('/auth/logout')
        def logout():
            """Logout user."""
            session_id = self.app.request.headers.get('Authorization', '').replace('Bearer ', '')
            
            if session_id and session_id in self.sessions:
                del self.sessions[session_id]
            
            return {"message": "Logged out successfully"}
        
        @self.app.route('/auth/user')
        def get_user():
            """Get current user information."""
            session_id = self.app.request.headers.get('Authorization', '').replace('Bearer ', '')
            
            if not session_id or session_id not in self.sessions:
                return {"error": "Not authenticated"}, 401
            
            session = self.sessions[session_id]
            user = session["user"]
            
            return {
                "user": {
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "roles": user.get("roles", []),
                    "last_login": user.get("last_login")
                }
            }
        
        @self.app.route('/auth/refresh')
        def refresh_token():
            """Refresh access token."""
            session_id = self.app.request.headers.get('Authorization', '').replace('Bearer ', '')
            
            if not session_id or session_id not in self.sessions:
                return {"error": "Not authenticated"}, 401
            
            session = self.sessions[session_id]
            token = session["token"]
            
            try:
                # Refresh token
                new_token = self._refresh_token(session["provider"], token)
                
                # Update session
                session["token"] = new_token
                session["last_activity"] = datetime.now()
                
                return {"message": "Token refreshed successfully"}
            
            except Exception as e:
                logger.error(f"Token refresh error: {e}")
                return {"error": "Token refresh failed"}, 500
    
    def _get_redirect_uri(self) -> str:
        """Get OAuth2 redirect URI."""
        base_url = self.config.get("base_url", "http://localhost:5000")
        return f"{base_url}/auth/callback"
    
    def _verify_state(self, state: str) -> bool:
        """Verify OAuth2 state parameter."""
        if state not in self.state_storage:
            return False
        
        state_info = self.state_storage[state]
        created_at = state_info["created_at"]
        
        # Check if state is not too old (5 minutes)
        if datetime.now() - created_at > timedelta(minutes=5):
            del self.state_storage[state]
            return False
        
        return True
    
    def _get_user_info(self, provider_name: str, token: Dict[str, Any]) -> Dict[str, Any]:
        """Get user information from provider."""
        provider = self.providers[provider_name]
        
        if provider_name == "keycloak":
            return self.keycloak_client.get_user_info(token)
        elif provider_name == "auth0":
            return self.auth0_client.get_user_info(token)
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
    
    def _create_session(self, user: Dict[str, Any], token: Dict[str, Any]) -> str:
        """Create user session."""
        session_id = secrets.token_urlsafe(32)
        
        session = {
            "user": user,
            "token": token,
            "provider": self.active_provider,
            "created_at": datetime.now(),
            "last_activity": datetime.now()
        }
        
        self.sessions[session_id] = session
        
        # Clean up expired sessions
        self._cleanup_sessions()
        
        return session_id
    
    def _refresh_token(self, provider_name: str, token: Dict[str, Any]) -> Dict[str, Any]:
        """Refresh access token."""
        provider = self.providers[provider_name]
        
        if provider_name == "keycloak":
            return self.keycloak_client.refresh_token(token)
        elif provider_name == "auth0":
            return self.auth0_client.refresh_token(token)
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
    
    def _cleanup_sessions(self):
        """Clean up expired sessions."""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if current_time - session["last_activity"] > timedelta(seconds=self.session_timeout):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
    
    def authenticate_request(self, request) -> Optional[Dict[str, Any]]:
        """
        Authenticate a request.
        
        Args:
            request: Flask request object
            
        Returns:
            User information if authenticated, None otherwise
        """
        # Get session ID from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None
        
        session_id = auth_header.replace('Bearer ', '')
        
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        # Check if session is expired
        if datetime.now() - session["last_activity"] > timedelta(seconds=self.session_timeout):
            del self.sessions[session_id]
            return None
        
        # Update last activity
        session["last_activity"] = datetime.now()
        
        return session["user"]
    
    def require_auth(self, roles: Optional[List[str]] = None):
        """
        Decorator to require authentication.
        
        Args:
            roles: Optional list of required roles
            
        Returns:
            Decorator function
        """
        def decorator(f):
            def decorated_function(*args, **kwargs):
                from flask import request, jsonify
                
                user = self.authenticate_request(request)
                if not user:
                    return jsonify({"error": "Authentication required"}), 401
                
                # Check roles if specified
                if roles:
                    user_roles = user.get("roles", [])
                    if not any(role in user_roles for role in roles):
                        return jsonify({"error": "Insufficient permissions"}), 403
                
                # Add user to request context
                request.user = user
                
                return f(*args, **kwargs)
            
            decorated_function.__name__ = f.__name__
            return decorated_function
        
        return decorator
    
    def get_provider_info(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get provider information.
        
        Args:
            provider_name: Provider name (uses active provider if None)
            
        Returns:
            Provider information
        """
        if not provider_name:
            provider_name = self.active_provider
        
        if provider_name not in self.providers:
            return {}
        
        provider = self.providers[provider_name]
        return {
            "name": provider_name,
            "type": provider["type"],
            "config": {
                "enabled": True,
                "scopes": provider["config"].get("scopes", ["openid", "email", "profile"])
            }
        }
    
    def list_providers(self) -> List[Dict[str, Any]]:
        """
        List all configured providers.
        
        Returns:
            List of provider information
        """
        return [
            self.get_provider_info(provider_name)
            for provider_name in self.providers.keys()
        ]
    
    def switch_provider(self, provider_name: str) -> bool:
        """
        Switch active OAuth2 provider.
        
        Args:
            provider_name: Name of provider to switch to
            
        Returns:
            True if switch was successful
        """
        if provider_name not in self.providers:
            logger.error(f"Provider {provider_name} not found")
            return False
        
        self.active_provider = provider_name
        logger.info(f"Switched to provider: {provider_name}")
        return True
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session information.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session information or None if not found
        """
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        return {
            "user_id": session["user"]["id"],
            "username": session["user"]["username"],
            "provider": session["provider"],
            "created_at": session["created_at"].isoformat(),
            "last_activity": session["last_activity"].isoformat()
        }
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Get all active sessions.
        
        Returns:
            List of active session information
        """
        sessions = []
        for session_id, session in self.sessions.items():
            sessions.append({
                "session_id": session_id,
                "user_id": session["user"]["id"],
                "username": session["user"]["username"],
                "provider": session["provider"],
                "created_at": session["created_at"].isoformat(),
                "last_activity": session["last_activity"].isoformat()
            })
        
        return sessions
    
    def revoke_session(self, session_id: str) -> bool:
        """
        Revoke a session.
        
        Args:
            session_id: Session ID to revoke
            
        Returns:
            True if session was revoked
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Revoked session: {session_id}")
            return True
        
        return False
    
    def revoke_all_sessions(self, user_id: Optional[str] = None) -> int:
        """
        Revoke all sessions for a user or all sessions.
        
        Args:
            user_id: User ID (revokes all sessions if None)
            
        Returns:
            Number of sessions revoked
        """
        revoked_count = 0
        
        if user_id:
            # Revoke sessions for specific user
            sessions_to_remove = [
                session_id for session_id, session in self.sessions.items()
                if session["user"]["id"] == user_id
            ]
        else:
            # Revoke all sessions
            sessions_to_remove = list(self.sessions.keys())
        
        for session_id in sessions_to_remove:
            del self.sessions[session_id]
            revoked_count += 1
        
        logger.info(f"Revoked {revoked_count} sessions")
        return revoked_count
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get OAuth2 manager statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "providers_configured": len(self.providers),
            "active_provider": self.active_provider,
            "active_sessions": len(self.sessions),
            "total_users": self.user_manager.get_user_count(),
            "csrf_protection_enabled": self.csrf_protection,
            "session_timeout": self.session_timeout
        }
