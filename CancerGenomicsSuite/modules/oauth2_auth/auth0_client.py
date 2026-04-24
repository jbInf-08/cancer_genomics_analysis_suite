#!/usr/bin/env python3
"""
Auth0 Client

This module provides Auth0-specific OAuth2 client functionality
for the cancer genomics analysis suite.
"""

import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class Auth0Client:
    """
    Auth0 OAuth2 client for cancer genomics analysis suite.
    
    Provides functionality to:
    - Authenticate with Auth0
    - Get user information
    - Manage tokens
    - Handle Auth0-specific features
    """
    
    def __init__(
        self,
        domain: str,
        client_id: str,
        client_secret: str
    ):
        """
        Initialize Auth0 client.
        
        Args:
            domain: Auth0 domain
            client_id: Client ID
            client_secret: Client secret
        """
        self.domain = domain.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        
        # Auth0 endpoints
        self.base_url = f"https://{self.domain}"
        self.token_url = f"{self.base_url}/oauth/token"
        self.userinfo_url = f"{self.base_url}/userinfo"
        self.logout_url = f"{self.base_url}/v2/logout"
        self.well_known_url = f"{self.base_url}/.well-known/openid_configuration"
        self.management_url = f"{self.base_url}/api/v2"
        
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
        Get authorization URL for Auth0.
        
        Args:
            redirect_uri: Redirect URI
            state: State parameter
            scopes: OAuth2 scopes
            
        Returns:
            Authorization URL
        """
        config = self.get_well_known_config()
        auth_endpoint = config.get("authorization_endpoint", f"{self.base_url}/authorize")
        
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
        Get user information from Auth0.
        
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
                "username": user_info.get("nickname") or user_info.get("sub"),
                "email": user_info.get("email"),
                "first_name": user_info.get("given_name"),
                "last_name": user_info.get("family_name"),
                "full_name": user_info.get("name"),
                "roles": self._extract_roles(user_info),
                "groups": self._extract_groups(user_info),
                "attributes": user_info.get("user_metadata", {}),
                "email_verified": user_info.get("email_verified", False),
                "provider": "auth0",
                "last_login": datetime.now().isoformat()
            }
            
            return normalized_user
        
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            raise
    
    def _extract_roles(self, user_info: Dict[str, Any]) -> List[str]:
        """Extract roles from user info."""
        # Auth0 roles are typically in app_metadata or user_metadata
        roles = []
        
        # Check app_metadata for roles
        app_metadata = user_info.get("app_metadata", {})
        if "roles" in app_metadata:
            roles.extend(app_metadata["roles"])
        
        # Check user_metadata for roles
        user_metadata = user_info.get("user_metadata", {})
        if "roles" in user_metadata:
            roles.extend(user_metadata["roles"])
        
        # Check for roles in custom claims
        if "https://cancer-genomics.com/roles" in user_info:
            roles.extend(user_info["https://cancer-genomics.com/roles"])
        
        return roles
    
    def _extract_groups(self, user_info: Dict[str, Any]) -> List[str]:
        """Extract groups from user info."""
        groups = []
        
        # Check app_metadata for groups
        app_metadata = user_info.get("app_metadata", {})
        if "groups" in app_metadata:
            groups.extend(app_metadata["groups"])
        
        # Check user_metadata for groups
        user_metadata = user_info.get("user_metadata", {})
        if "groups" in user_metadata:
            groups.extend(user_metadata["groups"])
        
        # Check for groups in custom claims
        if "https://cancer-genomics.com/groups" in user_info:
            groups.extend(user_info["https://cancer-genomics.com/groups"])
        
        return groups
    
    def logout(self, token: Dict[str, Any]) -> bool:
        """
        Logout user from Auth0.
        
        Args:
            token: Token data
            
        Returns:
            True if logout was successful
        """
        # Auth0 logout is typically handled client-side
        # This method can be used to revoke tokens if needed
        return True
    
    def get_management_token(self) -> str:
        """
        Get management API access token.
        
        Returns:
            Management access token
        """
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": f"{self.management_url}/"
        }
        
        try:
            response = requests.post(self.token_url, data=data, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            return token_data["access_token"]
        
        except Exception as e:
            logger.error(f"Failed to get management token: {e}")
            raise
    
    def get_user_by_id(self, user_id: str, management_token: str) -> Dict[str, Any]:
        """
        Get user by ID using management API.
        
        Args:
            user_id: User ID
            management_token: Management access token
            
        Returns:
            User information
        """
        url = f"{self.management_url}/users/{user_id}"
        headers = {
            "Authorization": f"Bearer {management_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            user_data = response.json()
            
            # Normalize user data
            normalized_user = {
                "id": user_data.get("user_id"),
                "username": user_data.get("nickname") or user_data.get("username"),
                "email": user_data.get("email"),
                "first_name": user_data.get("given_name"),
                "last_name": user_data.get("family_name"),
                "full_name": user_data.get("name"),
                "enabled": not user_data.get("blocked", False),
                "email_verified": user_data.get("email_verified", False),
                "created_at": user_data.get("created_at"),
                "last_login": user_data.get("last_login"),
                "login_count": user_data.get("logins_count", 0),
                "attributes": user_data.get("user_metadata", {}),
                "roles": self._extract_roles_from_management(user_data),
                "groups": self._extract_groups_from_management(user_data)
            }
            
            return normalized_user
        
        except Exception as e:
            logger.error(f"Failed to get user by ID: {e}")
            raise
    
    def _extract_roles_from_management(self, user_data: Dict[str, Any]) -> List[str]:
        """Extract roles from management API user data."""
        roles = []
        
        # Check app_metadata for roles
        app_metadata = user_data.get("app_metadata", {})
        if "roles" in app_metadata:
            roles.extend(app_metadata["roles"])
        
        # Check user_metadata for roles
        user_metadata = user_data.get("user_metadata", {})
        if "roles" in user_metadata:
            roles.extend(user_metadata["roles"])
        
        return roles
    
    def _extract_groups_from_management(self, user_data: Dict[str, Any]) -> List[str]:
        """Extract groups from management API user data."""
        groups = []
        
        # Check app_metadata for groups
        app_metadata = user_data.get("app_metadata", {})
        if "groups" in app_metadata:
            groups.extend(app_metadata["groups"])
        
        # Check user_metadata for groups
        user_metadata = user_data.get("user_metadata", {})
        if "groups" in user_metadata:
            groups.extend(user_metadata["groups"])
        
        return groups
    
    def search_users(
        self,
        query: str,
        management_token: str,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search users using management API.
        
        Args:
            query: Search query
            management_token: Management access token
            max_results: Maximum number of results
            
        Returns:
            List of user information
        """
        url = f"{self.management_url}/users"
        headers = {
            "Authorization": f"Bearer {management_token}",
            "Content-Type": "application/json"
        }
        
        params = {
            "q": query,
            "per_page": min(max_results, 100),
            "page": 0
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            users_data = response.json()
            
            # Normalize user data
            normalized_users = []
            for user_data in users_data:
                normalized_user = {
                    "id": user_data.get("user_id"),
                    "username": user_data.get("nickname") or user_data.get("username"),
                    "email": user_data.get("email"),
                    "first_name": user_data.get("given_name"),
                    "last_name": user_data.get("family_name"),
                    "full_name": user_data.get("name"),
                    "enabled": not user_data.get("blocked", False),
                    "email_verified": user_data.get("email_verified", False),
                    "created_at": user_data.get("created_at"),
                    "last_login": user_data.get("last_login")
                }
                normalized_users.append(normalized_user)
            
            return normalized_users
        
        except Exception as e:
            logger.error(f"Failed to search users: {e}")
            raise
    
    def update_user_metadata(
        self,
        user_id: str,
        metadata: Dict[str, Any],
        management_token: str
    ) -> bool:
        """
        Update user metadata.
        
        Args:
            user_id: User ID
            metadata: Metadata to update
            management_token: Management access token
            
        Returns:
            True if update was successful
        """
        url = f"{self.management_url}/users/{user_id}"
        headers = {
            "Authorization": f"Bearer {management_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "user_metadata": metadata
        }
        
        try:
            response = requests.patch(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            return True
        
        except Exception as e:
            logger.error(f"Failed to update user metadata: {e}")
            return False
    
    def assign_roles_to_user(
        self,
        user_id: str,
        roles: List[str],
        management_token: str
    ) -> bool:
        """
        Assign roles to user.
        
        Args:
            user_id: User ID
            roles: List of roles to assign
            management_token: Management access token
            
        Returns:
            True if assignment was successful
        """
        # Get current user data
        user_data = self.get_user_by_id(user_id, management_token)
        current_metadata = user_data.get("attributes", {})
        
        # Update roles in metadata
        current_metadata["roles"] = roles
        
        # Update user metadata
        return self.update_user_metadata(user_id, current_metadata, management_token)
    
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
    
    def get_application_info(self) -> Dict[str, Any]:
        """
        Get application information.
        
        Returns:
            Application information
        """
        url = f"{self.management_url}/clients"
        management_token = self.get_management_token()
        headers = {
            "Authorization": f"Bearer {management_token}",
            "Content-Type": "application/json"
        }
        
        params = {
            "client_id": self.client_id
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            clients = response.json()
            if clients:
                return clients[0]
            
            return {}
        
        except Exception as e:
            logger.error(f"Failed to get application info: {e}")
            raise
