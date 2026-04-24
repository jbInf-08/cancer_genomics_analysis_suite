#!/usr/bin/env python3
"""
User Manager

This module provides user management capabilities for OAuth2 authentication
in the cancer genomics analysis suite.
"""

import logging
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import hashlib
import secrets

logger = logging.getLogger(__name__)


class UserManager:
    """
    User manager for OAuth2 authentication.
    
    Provides functionality to:
    - Create and manage users
    - Handle user roles and permissions
    - Store and retrieve user information
    - Manage user sessions and preferences
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize user manager.
        
        Args:
            config: User management configuration
        """
        self.config = config or {}
        
        # User storage (in production, this would be a database)
        self.users = {}
        self.user_sessions = {}
        
        # User roles and permissions
        self.roles = {
            "admin": ["read", "write", "delete", "manage_users", "manage_system"],
            "researcher": ["read", "write", "analyze_data", "create_reports"],
            "viewer": ["read"],
            "guest": ["read_public"]
        }
        
        # Default user settings
        self.default_settings = {
            "theme": "light",
            "language": "en",
            "notifications": True,
            "email_notifications": True,
            "dashboard_layout": "default"
        }
        
        # Statistics
        self.user_stats = {
            "total_users": 0,
            "active_users": 0,
            "users_by_role": {},
            "last_updated": datetime.now()
        }
    
    def init_app(self, app):
        """
        Initialize user manager with Flask app.
        
        Args:
            app: Flask application instance
        """
        # Load users from app config if available
        if hasattr(app, 'config') and app.config.get('USERS'):
            self.load_users_from_config(app.config['USERS'])
        
        logger.info("User manager initialized with Flask app")
    
    def create_or_update_user(
        self,
        user_info: Dict[str, Any],
        provider: str = "oauth2"
    ) -> Dict[str, Any]:
        """
        Create or update user from OAuth2 provider.
        
        Args:
            user_info: User information from OAuth2 provider
            provider: OAuth2 provider name
            
        Returns:
            User information
        """
        user_id = user_info.get("id")
        username = user_info.get("username")
        email = user_info.get("email")
        
        if not user_id or not username:
            raise ValueError("User ID and username are required")
        
        # Check if user exists
        existing_user = self.get_user_by_id(user_id)
        
        if existing_user:
            # Update existing user
            user = self._update_user(existing_user, user_info, provider)
        else:
            # Create new user
            user = self._create_user(user_info, provider)
        
        # Update statistics
        self._update_user_stats()
        
        logger.info(f"Created/updated user: {username} ({user_id})")
        return user
    
    def _create_user(
        self,
        user_info: Dict[str, Any],
        provider: str
    ) -> Dict[str, Any]:
        """Create a new user."""
        user_id = user_info.get("id")
        username = user_info.get("username")
        email = user_info.get("email")
        
        # Generate internal user ID if not provided
        if not user_id:
            user_id = self._generate_user_id(username, email)
        
        # Determine user role based on email domain or other criteria
        role = self._determine_user_role(user_info)
        
        # Create user object
        user = {
            "id": user_id,
            "username": username,
            "email": email,
            "first_name": user_info.get("first_name", ""),
            "last_name": user_info.get("last_name", ""),
            "full_name": user_info.get("full_name", ""),
            "roles": [role],
            "groups": user_info.get("groups", []),
            "provider": provider,
            "provider_id": user_info.get("id"),
            "email_verified": user_info.get("email_verified", False),
            "created_at": datetime.now().isoformat(),
            "last_login": datetime.now().isoformat(),
            "login_count": 1,
            "is_active": True,
            "settings": self.default_settings.copy(),
            "permissions": self._get_user_permissions([role]),
            "attributes": user_info.get("attributes", {})
        }
        
        # Store user
        self.users[user_id] = user
        
        return user
    
    def _update_user(
        self,
        existing_user: Dict[str, Any],
        user_info: Dict[str, Any],
        provider: str
    ) -> Dict[str, Any]:
        """Update existing user."""
        user_id = existing_user["id"]
        
        # Update user information
        existing_user.update({
            "username": user_info.get("username", existing_user["username"]),
            "email": user_info.get("email", existing_user["email"]),
            "first_name": user_info.get("first_name", existing_user.get("first_name", "")),
            "last_name": user_info.get("last_name", existing_user.get("last_name", "")),
            "full_name": user_info.get("full_name", existing_user.get("full_name", "")),
            "groups": user_info.get("groups", existing_user.get("groups", [])),
            "email_verified": user_info.get("email_verified", existing_user.get("email_verified", False)),
            "last_login": datetime.now().isoformat(),
            "login_count": existing_user.get("login_count", 0) + 1,
            "attributes": {**existing_user.get("attributes", {}), **user_info.get("attributes", {})}
        })
        
        # Update roles if provided
        if "roles" in user_info and user_info["roles"]:
            existing_user["roles"] = user_info["roles"]
            existing_user["permissions"] = self._get_user_permissions(existing_user["roles"])
        
        # Store updated user
        self.users[user_id] = existing_user
        
        return existing_user
    
    def _generate_user_id(self, username: str, email: str) -> str:
        """Generate internal user ID."""
        # Create hash from username and email
        data = f"{username}:{email}:{datetime.now().isoformat()}"
        hash_object = hashlib.sha256(data.encode())
        return f"user_{hash_object.hexdigest()[:16]}"
    
    def _determine_user_role(self, user_info: Dict[str, Any]) -> str:
        """Determine user role based on available information."""
        # Check if roles are provided by OAuth2 provider
        provider_roles = user_info.get("roles", [])
        if provider_roles:
            # Map provider roles to internal roles
            role_mapping = {
                "admin": "admin",
                "administrator": "admin",
                "researcher": "researcher",
                "scientist": "researcher",
                "viewer": "viewer",
                "user": "viewer",
                "guest": "guest"
            }
            
            for provider_role in provider_roles:
                if provider_role.lower() in role_mapping:
                    return role_mapping[provider_role.lower()]
        
        # Check email domain for role assignment
        email = user_info.get("email", "")
        if email:
            domain = email.split("@")[-1].lower()
            
            # Define domain-based role mapping
            domain_roles = {
                "admin": ["admin.company.com", "administrator.org"],
                "researcher": ["research.university.edu", "scientist.org"],
                "viewer": ["company.com", "organization.org"]
            }
            
            for role, domains in domain_roles.items():
                if domain in domains:
                    return role
        
        # Default role
        return "viewer"
    
    def _get_user_permissions(self, roles: List[str]) -> List[str]:
        """Get user permissions based on roles."""
        permissions = set()
        
        for role in roles:
            if role in self.roles:
                permissions.update(self.roles[role])
        
        return list(permissions)
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User information or None if not found
        """
        return self.users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user by username.
        
        Args:
            username: Username
            
        Returns:
            User information or None if not found
        """
        for user in self.users.values():
            if user["username"] == username:
                return user
        return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user by email.
        
        Args:
            email: Email address
            
        Returns:
            User information or None if not found
        """
        for user in self.users.values():
            if user["email"] == email:
                return user
        return None
    
    def search_users(
        self,
        query: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search users by username, email, or name.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching users
        """
        query_lower = query.lower()
        matches = []
        
        for user in self.users.values():
            if not user.get("is_active", True):
                continue
            
            # Search in username, email, first name, last name
            if (query_lower in user["username"].lower() or
                query_lower in user["email"].lower() or
                query_lower in user.get("first_name", "").lower() or
                query_lower in user.get("last_name", "").lower()):
                
                matches.append({
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "first_name": user.get("first_name", ""),
                    "last_name": user.get("last_name", ""),
                    "roles": user["roles"],
                    "last_login": user.get("last_login"),
                    "is_active": user.get("is_active", True)
                })
        
        # Sort by last login (most recent first)
        matches.sort(key=lambda x: x.get("last_login", ""), reverse=True)
        
        return matches[:limit]
    
    def update_user_role(self, user_id: str, roles: List[str]) -> bool:
        """
        Update user roles.
        
        Args:
            user_id: User ID
            roles: List of new roles
            
        Returns:
            True if update was successful
        """
        if user_id not in self.users:
            return False
        
        # Validate roles
        valid_roles = set(self.roles.keys())
        if not all(role in valid_roles for role in roles):
            return False
        
        # Update user
        user = self.users[user_id]
        user["roles"] = roles
        user["permissions"] = self._get_user_permissions(roles)
        user["updated_at"] = datetime.now().isoformat()
        
        self.users[user_id] = user
        
        logger.info(f"Updated roles for user {user_id}: {roles}")
        return True
    
    def update_user_settings(self, user_id: str, settings: Dict[str, Any]) -> bool:
        """
        Update user settings.
        
        Args:
            user_id: User ID
            settings: Settings to update
            
        Returns:
            True if update was successful
        """
        if user_id not in self.users:
            return False
        
        user = self.users[user_id]
        user["settings"].update(settings)
        user["updated_at"] = datetime.now().isoformat()
        
        self.users[user_id] = user
        
        logger.info(f"Updated settings for user {user_id}")
        return True
    
    def deactivate_user(self, user_id: str) -> bool:
        """
        Deactivate user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if deactivation was successful
        """
        if user_id not in self.users:
            return False
        
        user = self.users[user_id]
        user["is_active"] = False
        user["deactivated_at"] = datetime.now().isoformat()
        
        self.users[user_id] = user
        
        logger.info(f"Deactivated user {user_id}")
        return True
    
    def activate_user(self, user_id: str) -> bool:
        """
        Activate user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if activation was successful
        """
        if user_id not in self.users:
            return False
        
        user = self.users[user_id]
        user["is_active"] = True
        if "deactivated_at" in user:
            del user["deactivated_at"]
        user["activated_at"] = datetime.now().isoformat()
        
        self.users[user_id] = user
        
        logger.info(f"Activated user {user_id}")
        return True
    
    def delete_user(self, user_id: str) -> bool:
        """
        Delete user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if deletion was successful
        """
        if user_id not in self.users:
            return False
        
        del self.users[user_id]
        
        # Remove user sessions
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
        
        logger.info(f"Deleted user {user_id}")
        return True
    
    def has_permission(self, user_id: str, permission: str) -> bool:
        """
        Check if user has specific permission.
        
        Args:
            user_id: User ID
            permission: Permission to check
            
        Returns:
            True if user has permission
        """
        user = self.get_user_by_id(user_id)
        if not user or not user.get("is_active", True):
            return False
        
        return permission in user.get("permissions", [])
    
    def has_role(self, user_id: str, role: str) -> bool:
        """
        Check if user has specific role.
        
        Args:
            user_id: User ID
            role: Role to check
            
        Returns:
            True if user has role
        """
        user = self.get_user_by_id(user_id)
        if not user or not user.get("is_active", True):
            return False
        
        return role in user.get("roles", [])
    
    def get_user_count(self) -> int:
        """
        Get total number of users.
        
        Returns:
            Number of users
        """
        return len(self.users)
    
    def get_active_user_count(self) -> int:
        """
        Get number of active users.
        
        Returns:
            Number of active users
        """
        return sum(1 for user in self.users.values() if user.get("is_active", True))
    
    def get_users_by_role(self, role: str) -> List[Dict[str, Any]]:
        """
        Get users with specific role.
        
        Args:
            role: Role name
            
        Returns:
            List of users with the role
        """
        users = []
        for user in self.users.values():
            if role in user.get("roles", []) and user.get("is_active", True):
                users.append({
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "first_name": user.get("first_name", ""),
                    "last_name": user.get("last_name", ""),
                    "last_login": user.get("last_login")
                })
        
        return users
    
    def get_recent_users(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get users who logged in recently.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of recent users
        """
        cutoff_date = datetime.now().timestamp() - (days * 24 * 3600)
        recent_users = []
        
        for user in self.users.values():
            if not user.get("is_active", True):
                continue
            
            last_login = user.get("last_login")
            if last_login:
                try:
                    login_time = datetime.fromisoformat(last_login).timestamp()
                    if login_time > cutoff_date:
                        recent_users.append({
                            "id": user["id"],
                            "username": user["username"],
                            "email": user["email"],
                            "last_login": last_login,
                            "login_count": user.get("login_count", 0)
                        })
                except ValueError:
                    continue
        
        # Sort by last login (most recent first)
        recent_users.sort(key=lambda x: x["last_login"], reverse=True)
        
        return recent_users
    
    def _update_user_stats(self):
        """Update user statistics."""
        self.user_stats["total_users"] = len(self.users)
        self.user_stats["active_users"] = self.get_active_user_count()
        
        # Count users by role
        role_counts = {}
        for user in self.users.values():
            if user.get("is_active", True):
                for role in user.get("roles", []):
                    role_counts[role] = role_counts.get(role, 0) + 1
        
        self.user_stats["users_by_role"] = role_counts
        self.user_stats["last_updated"] = datetime.now()
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """
        Get user statistics.
        
        Returns:
            Dictionary with user statistics
        """
        self._update_user_stats()
        return self.user_stats.copy()
    
    def load_users_from_config(self, users_config: List[Dict[str, Any]]):
        """
        Load users from configuration.
        
        Args:
            users_config: List of user configurations
        """
        for user_config in users_config:
            user_id = user_config.get("id")
            if not user_id:
                continue
            
            # Create user from config
            user = {
                "id": user_id,
                "username": user_config.get("username", ""),
                "email": user_config.get("email", ""),
                "first_name": user_config.get("first_name", ""),
                "last_name": user_config.get("last_name", ""),
                "roles": user_config.get("roles", ["viewer"]),
                "groups": user_config.get("groups", []),
                "provider": "config",
                "email_verified": user_config.get("email_verified", False),
                "created_at": datetime.now().isoformat(),
                "last_login": None,
                "login_count": 0,
                "is_active": user_config.get("is_active", True),
                "settings": {**self.default_settings, **user_config.get("settings", {})},
                "permissions": self._get_user_permissions(user_config.get("roles", ["viewer"])),
                "attributes": user_config.get("attributes", {})
            }
            
            self.users[user_id] = user
        
        logger.info(f"Loaded {len(users_config)} users from configuration")
    
    def export_users(self, include_sensitive: bool = False) -> List[Dict[str, Any]]:
        """
        Export user data.
        
        Args:
            include_sensitive: Whether to include sensitive information
            
        Returns:
            List of user data
        """
        exported_users = []
        
        for user in self.users.values():
            if include_sensitive:
                exported_users.append(user.copy())
            else:
                # Export only non-sensitive information
                exported_user = {
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "first_name": user.get("first_name", ""),
                    "last_name": user.get("last_name", ""),
                    "roles": user["roles"],
                    "groups": user.get("groups", []),
                    "created_at": user["created_at"],
                    "last_login": user.get("last_login"),
                    "login_count": user.get("login_count", 0),
                    "is_active": user.get("is_active", True)
                }
                exported_users.append(exported_user)
        
        return exported_users
