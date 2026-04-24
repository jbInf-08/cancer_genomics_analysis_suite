#!/usr/bin/env python3
"""
Keycloak Client

This module provides Keycloak-specific OAuth2 client functionality
for the cancer genomics analysis suite.
"""

import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class KeycloakClient:
    """
    Keycloak OAuth2 client for cancer genomics analysis suite.
    
    Provides functionality to:
    - Authenticate with Keycloak
    - Get user information
    - Manage tokens
    - Handle Keycloak-specific features
    """
    
    def __init__(
        self,
        server_url: str,
        realm: str,
        client_id: str,
        client_secret: str
    ):
        """
        Initialize Keycloak client.
        
        Args:
            server_url: Keycloak server URL
            realm: Keycloak realm
            client_id: Client ID
            client_secret: Client secret
        """
        self.server_url = server_url.rstrip('/')
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret
        
        # Keycloak endpoints
        self.realm_url = f"{self.server_url}/realms/{realm}"
        self.token_url = f"{self.realm_url}/protocol/openid-connect/token"
        self.userinfo_url = f"{self.realm_url}/protocol/openid-connect/userinfo"
        self.logout_url = f"{self.realm_url}/protocol/openid-connect/logout"
        self.well_known_url = f"{self.realm_url}/.well-known/openid_configuration"
        
        # Cache for well-known configuration
        self._well_known_config = None
        self._config_cache_time = None
    
    def get_well_known_config(self) -> Dict[str, Any]:
        """
        Get OpenID Connect well-known configuration.
        
        Returns:
            Well-known configuration
        """
        # Check cache
        if (self._well_known_config and self._config_cache_time and 
            datetime.now() - self._config_cache_time < timedelta(hours=1)):
            return self._well_known_config
        
        try:
            response = requests.get(self.well_known_url, timeout=10)
            response.raise_for_status()
            
            self._well_known_config = response.json()
            self._config_cache_time = datetime.now()
            
            return self._well_known_config
        
        except Exception as e:
            logger.error(f"Failed to get well-known configuration: {e}")
            return {}
    
    def get_authorization_url(
        self,
        redirect_uri: str,
        state: str,
        scopes: List[str] = None
    ) -> str:
        """
        Get authorization URL for Keycloak.
        
        Args:
            redirect_uri: Redirect URI
            state: State parameter
            scopes: OAuth2 scopes
            
        Returns:
            Authorization URL
        """
        config = self.get_well_known_config()
        auth_endpoint = config.get("authorization_endpoint", f"{self.realm_url}/protocol/openid-connect/auth")
        
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": " ".join(scopes or ["openid", "email", "profile"])
        }
        
        return f"{auth_endpoint}?{requests.compat.urlencode(params)}"
    
    def exchange_code_for_token(
        self,
        code: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code
            redirect_uri: Redirect URI
            
        Returns:
            Token response
        """
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri
        }
        
        try:
            response = requests.post(self.token_url, data=data, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Add token expiration time
            if "expires_in" in token_data:
                token_data["expires_at"] = datetime.now() + timedelta(seconds=token_data["expires_in"])
            
            return token_data
        
        except Exception as e:
            logger.error(f"Failed to exchange code for token: {e}")
            raise
    
    def refresh_token(self, token: Dict[str, Any]) -> Dict[str, Any]:
        """
        Refresh access token.
        
        Args:
            token: Current token data
            
        Returns:
            New token data
        """
        if "refresh_token" not in token:
            raise ValueError("No refresh token available")
        
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": token["refresh_token"]
        }
        
        try:
            response = requests.post(self.token_url, data=data, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Add token expiration time
            if "expires_in" in token_data:
                token_data["expires_at"] = datetime.now() + timedelta(seconds=token_data["expires_in"])
            
            return token_data
        
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            raise
    
    def get_user_info(self, token: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get user information from Keycloak.
        
        Args:
            token: Access token
            
        Returns:
            User information
        """
        headers = {
            "Authorization": f"Bearer {token['access_token']}"
        }
        
        try:
            response = requests.get(self.userinfo_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            user_info = response.json()
            
            # Normalize user information
            normalized_user = {
                "id": user_info.get("sub"),
                "username": user_info.get("preferred_username") or user_info.get("sub"),
                "email": user_info.get("email"),
                "first_name": user_info.get("given_name"),
                "last_name": user_info.get("family_name"),
                "full_name": user_info.get("name"),
                "roles": self._extract_roles(user_info),
                "groups": self._extract_groups(user_info),
                "attributes": user_info.get("attributes", {}),
                "email_verified": user_info.get("email_verified", False),
                "provider": "keycloak",
                "last_login": datetime.now().isoformat()
            }
            
            return normalized_user
        
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            raise
    
    def _extract_roles(self, user_info: Dict[str, Any]) -> List[str]:
        """Extract roles from user info."""
        roles = []
        
        # Extract realm roles
        realm_access = user_info.get("realm_access", {})
        realm_roles = realm_access.get("roles", [])
        roles.extend(realm_roles)
        
        # Extract client roles
        resource_access = user_info.get("resource_access", {})
        for client_id, client_info in resource_access.items():
            client_roles = client_info.get("roles", [])
            roles.extend([f"{client_id}:{role}" for role in client_roles])
        
        # Remove default roles
        default_roles = ["offline_access", "uma_authorization"]
        roles = [role for role in roles if role not in default_roles]
        
        return roles
    
    def _extract_groups(self, user_info: Dict[str, Any]) -> List[str]:
        """Extract groups from user info."""
        groups = user_info.get("groups", [])
        return groups
    
    def logout(self, token: Dict[str, Any]) -> bool:
        """
        Logout user from Keycloak.
        
        Args:
            token: Token data
            
        Returns:
            True if logout was successful
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": token.get("refresh_token", "")
        }
        
        try:
            response = requests.post(self.logout_url, data=data, timeout=10)
            response.raise_for_status()
            return True
        
        except Exception as e:
            logger.error(f"Failed to logout: {e}")
            return False
    
    def get_user_by_id(self, user_id: str, admin_token: str) -> Dict[str, Any]:
        """
        Get user by ID using admin API.
        
        Args:
            user_id: User ID
            admin_token: Admin access token
            
        Returns:
            User information
        """
        url = f"{self.server_url}/admin/realms/{self.realm}/users/{user_id}"
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            user_data = response.json()
            
            # Normalize user data
            normalized_user = {
                "id": user_data.get("id"),
                "username": user_data.get("username"),
                "email": user_data.get("email"),
                "first_name": user_data.get("firstName"),
                "last_name": user_data.get("lastName"),
                "enabled": user_data.get("enabled", True),
                "email_verified": user_data.get("emailVerified", False),
                "created_timestamp": user_data.get("createdTimestamp"),
                "attributes": user_data.get("attributes", {}),
                "groups": [group.get("name") for group in user_data.get("groups", [])],
                "roles": [role.get("name") for role in user_data.get("roles", [])]
            }
            
            return normalized_user
        
        except Exception as e:
            logger.error(f"Failed to get user by ID: {e}")
            raise
    
    def search_users(
        self,
        query: str,
        admin_token: str,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search users using admin API.
        
        Args:
            query: Search query
            admin_token: Admin access token
            max_results: Maximum number of results
            
        Returns:
            List of user information
        """
        url = f"{self.server_url}/admin/realms/{self.realm}/users"
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
        
        params = {
            "search": query,
            "max": max_results
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            users_data = response.json()
            
            # Normalize user data
            normalized_users = []
            for user_data in users_data:
                normalized_user = {
                    "id": user_data.get("id"),
                    "username": user_data.get("username"),
                    "email": user_data.get("email"),
                    "first_name": user_data.get("firstName"),
                    "last_name": user_data.get("lastName"),
                    "enabled": user_data.get("enabled", True),
                    "email_verified": user_data.get("emailVerified", False),
                    "created_timestamp": user_data.get("createdTimestamp")
                }
                normalized_users.append(normalized_user)
            
            return normalized_users
        
        except Exception as e:
            logger.error(f"Failed to search users: {e}")
            raise
    
    def get_admin_token(self) -> str:
        """
        Get admin access token for Keycloak admin API.
        
        Returns:
            Admin access token
        """
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            response = requests.post(self.token_url, data=data, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            return token_data["access_token"]
        
        except Exception as e:
            logger.error(f"Failed to get admin token: {e}")
            raise
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate access token.
        
        Args:
            token: Access token to validate
            
        Returns:
            Token validation result
        """
        config = self.get_well_known_config()
        introspection_url = config.get("introspection_endpoint")
        
        if not introspection_url:
            raise ValueError("Token introspection not supported")
        
        data = {
            "token": token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            response = requests.post(introspection_url, data=data, timeout=10)
            response.raise_for_status()
            
            return response.json()
        
        except Exception as e:
            logger.error(f"Failed to validate token: {e}")
            raise
    
    def get_realm_info(self) -> Dict[str, Any]:
        """
        Get realm information.
        
        Returns:
            Realm information
        """
        url = f"{self.server_url}/admin/realms/{self.realm}"
        admin_token = self.get_admin_token()
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            return response.json()
        
        except Exception as e:
            logger.error(f"Failed to get realm info: {e}")
            raise
    
    def get_client_info(self) -> Dict[str, Any]:
        """
        Get client information.
        
        Returns:
            Client information
        """
        url = f"{self.server_url}/admin/realms/{self.realm}/clients"
        admin_token = self.get_admin_token()
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
        
        params = {
            "clientId": self.client_id
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            clients = response.json()
            if clients:
                return clients[0]
            
            return {}
        
        except Exception as e:
            logger.error(f"Failed to get client info: {e}")
            raise
